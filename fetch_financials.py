#!/usr/bin/env python3
"""
fetch_financials.py
-------------------
Auto-fetches the latest quarterly financials for every supplier in data.json
using Yahoo Finance (via the yfinance library). Writes updated values back to
data.json and recomputes operating-income margins.

Fields updated automatically (from Yahoo Finance):
  revenue, revenue_growth, operating_income, profit_growth,
  capex (TTM), capex_growth, earnings_period

Fields intentionally NOT touched (require human judgement):
  shortage_level, supply_sufficient, duration_label, shortage_summary,
  overall_status, headline, supply_chain, subcomponents, capacity_expansion,
  growth_reason, and all tier / supply-chain narrative fields.
"""

import json, re, datetime, sys

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance is not installed.")
    print("Run:  pip install yfinance")
    sys.exit(1)

DATA_FILE = "data.json"

# ── Currency conversion ──────────────────────────────────────────────────────
# Yahoo Finance returns values in the company's native reporting currency.
# These rates convert to USD.  Update periodically if precision is critical.
FX_TO_USD = {
    "USD": 1.0,
    "KRW": 1430.0,   # South Korean Won  (KRW per 1 USD)
    "JPY": 155.0,    # Japanese Yen      (JPY per 1 USD)
    "TWD": 32.5,     # Taiwan Dollar     (TWD per 1 USD)
    "EUR": 0.917,    # Euro              (EUR per 1 USD)
    "GBP": 0.79,     # British Pound     (GBP per 1 USD)
    "HKD": 7.78,     # Hong Kong Dollar  (HKD per 1 USD)
    "CNY": 7.20,     # Chinese Yuan      (CNY per 1 USD)
}


def to_usd(val, currency):
    """Convert val from currency to USD.  Returns None if val is None."""
    if val is None:
        return None
    ccy = (currency or "USD").upper()
    rate = FX_TO_USD.get(ccy, 1.0)
    return val / rate


# ── Helpers ───────────────────────────────────────────────────────────────────

def try_row(df, candidates):
    """Return the first row name from `candidates` that exists in df.index."""
    for name in candidates:
        if name in df.index:
            return name
    return None


def safe_float(val):
    """Convert to float, returning None for NaN / non-numeric."""
    try:
        v = float(val)
        return None if v != v else v   # v != v  ↔  NaN
    except Exception:
        return None


def fmt_val(val):
    """Format a raw dollar amount as a readable string: $39.3B, $665M, etc."""
    if val is None:
        return None
    a = abs(val)
    if   a >= 1e12:  return f"${a / 1e12:.1f}T"
    elif a >= 1e9:   return f"${a / 1e9:.2g}B"
    elif a >= 1e6:   return f"${a / 1e6:.0f}M"
    else:            return f"${a:.0f}"


def parse_stored(s):
    """
    Parse a stored string value back to raw dollars.
    Handles ranges like '$52-56B' (uses midpoint) and plain '$39.3B'.
    """
    if not s:
        return None
    s = str(s).strip().replace("$", "").replace(",", "")
    # Range  e.g. "52-56B"
    m = re.match(r"^([\d.]+)-([\d.]+)([TBMK]?)$", s)
    if m:
        lo, hi, u = float(m.group(1)), float(m.group(2)), m.group(3)
        v = (lo + hi) / 2
    else:
        m = re.match(r"^([\d.]+)([TBMK]?)$", s)
        if not m:
            return None
        v, u = float(m.group(1)), m.group(2)
    return v * {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3, "": 1}.get(u, 1)


# ── Core fetch logic ──────────────────────────────────────────────────────────

def fetch_ticker(ticker):
    """
    Pull quarterly income statement + cash flow for `ticker` from Yahoo Finance.

    Returns a dict with updated financial fields, or None if the data is
    unavailable (e.g. non-US ticker with limited coverage).
    """
    t = yf.Ticker(ticker)

    # Detect reporting currency (KRW, JPY, TWD, EUR, USD, etc.)
    currency = "USD"
    try:
        currency = t.fast_info.currency or "USD"
    except Exception:
        try:
            currency = t.info.get("currency", "USD") or "USD"
        except Exception:
            pass
    currency = (currency or "USD").upper()

    # ── Income statement ──────────────────────────────────────────────────────
    inc = None
    for attr in ("quarterly_income_stmt", "quarterly_financials"):
        try:
            df = getattr(t, attr)
            if df is not None and not df.empty:
                inc = df
                break
        except Exception:
            pass

    if inc is None or inc.empty or len(inc.columns) < 5:
        return None   # Need at least 5 quarters for a clean YoY comparison

    rev_row = try_row(inc, ["Total Revenue", "Revenue", "Revenues"])
    oi_row  = try_row(inc, ["Operating Income", "EBIT", "Operating Profit",
                             "Operating Income Or Loss"])
    if not rev_row or not oi_row:
        return None

    cols = inc.columns.tolist()   # sorted most-recent first

    rev_curr = to_usd(safe_float(inc.loc[rev_row, cols[0]]), currency)
    rev_prev = to_usd(safe_float(inc.loc[rev_row, cols[4]]), currency)  # same quarter, prior yr
    oi_curr  = to_usd(safe_float(inc.loc[oi_row,  cols[0]]), currency)
    oi_prev  = to_usd(safe_float(inc.loc[oi_row,  cols[4]]), currency)

    if not rev_curr:
        return None

    rev_growth  = (round((rev_curr / rev_prev - 1) * 100)
                   if rev_prev and rev_prev > 0 else None)
    prof_growth = (round((oi_curr  / oi_prev  - 1) * 100)
                   if oi_curr and oi_prev and oi_prev > 0 else None)

    # ── Cash flow → TTM capex ─────────────────────────────────────────────────
    capex_ttm = capex_prev_ttm = None
    for attr in ("quarterly_cash_flow", "quarterly_cashflow"):
        try:
            cf = getattr(t, attr)
            if cf is None or cf.empty:
                continue
            cap_row = try_row(cf, [
                "Capital Expenditure",
                "Capital Expenditures",
                "Purchase Of Property Plant And Equipment",
                "Purchases Of Property And Equipment",
            ])
            if not cap_row:
                continue
            cf_cols = cf.columns.tolist()
            if len(cf_cols) >= 4:
                raw_ttm = abs(
                    sum(safe_float(cf.loc[cap_row, c]) or 0.0 for c in cf_cols[:4])
                )
                capex_ttm = to_usd(raw_ttm, currency)
            if len(cf_cols) >= 8:
                raw_prev = abs(
                    sum(safe_float(cf.loc[cap_row, c]) or 0.0 for c in cf_cols[4:8])
                )
                capex_prev_ttm = to_usd(raw_prev, currency)
            break
        except Exception:
            pass

    capex_growth = (
        round((capex_ttm / capex_prev_ttm - 1) * 100)
        if capex_ttm and capex_prev_ttm and capex_prev_ttm > 0 else None
    )

    # ── Earnings period label ─────────────────────────────────────────────────
    period = cols[0]
    period_str = (period.strftime("Q ending %b %Y")
                  if hasattr(period, "strftime") else str(period)[:7])

    return {
        "revenue":          fmt_val(rev_curr),
        "revenue_growth":   rev_growth,
        "operating_income": fmt_val(oi_curr),
        "profit_growth":    prof_growth,
        "capex":            fmt_val(capex_ttm) if capex_ttm else None,
        "capex_growth":     capex_growth,
        "earnings_period":  period_str,
    }


# ── Margin recompute ──────────────────────────────────────────────────────────

def recompute_margins(sup):
    """
    Recalculate oi_margin_pct and oi_margin_chg_pp from the (now-updated)
    revenue, operating_income, revenue_growth, and profit_growth fields.
    """
    rev = parse_stored(sup.get("revenue", ""))
    oi  = parse_stored(sup.get("operating_income", ""))
    rg  = sup.get("revenue_growth", 0) / 100.0
    pg  = sup.get("profit_growth",  0) / 100.0

    if rev and oi and rev > 0:
        cur_margin = round(oi / rev * 100, 1)
        if rg != -1 and pg != -1:
            prior_rev = rev / (1 + rg)
            prior_oi  = oi  / (1 + pg)
            chg = round(cur_margin - (prior_oi / prior_rev * 100), 1) if prior_rev > 0 else None
        else:
            chg = None
    else:
        cur_margin = chg = None

    sup["oi_margin_pct"]    = cur_margin
    sup["oi_margin_chg_pp"] = chg


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    with open(DATA_FILE) as f:
        data = json.load(f)

    fetched   = {}   # ticker → result dict (deduplicated — NVIDIA appears twice)
    n_updated = 0
    n_skipped = 0

    for comp in data["components"]:
        for sup in comp["suppliers"]:
            ticker = sup.get("ticker", "").strip()
            if not ticker:
                continue

            # Fetch once per unique ticker
            if ticker not in fetched:
                print(f"  Fetching {sup['name']:25s} ({ticker}) ...", end=" ", flush=True)
                try:
                    fetched[ticker] = fetch_ticker(ticker)
                    print("✓" if fetched[ticker] else "— no data, keeping existing values")
                except Exception as exc:
                    fetched[ticker] = None
                    print(f"— error ({exc}), keeping existing values")

            result = fetched[ticker]

            if result:
                # Overwrite only the fields we fetched — preserve all others
                for field in ("revenue", "operating_income"):
                    if result.get(field):
                        sup[field] = result[field]
                for field in ("revenue_growth", "profit_growth", "capex_growth"):
                    if result.get(field) is not None:
                        sup[field] = result[field]
                if result.get("capex"):
                    sup["capex"] = result["capex"]
                if result.get("earnings_period"):
                    sup["earnings_period"] = result["earnings_period"]
                n_updated += 1
            else:
                n_skipped += 1

            # Always recompute derived margin fields
            recompute_margins(sup)

    data["last_updated"] = datetime.date.today().isoformat()

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n✓ data.json updated — {n_updated} supplier(s) refreshed, "
          f"{n_skipped} kept existing values")
    print(f"  last_updated set to {data['last_updated']}")
    print("\nNext step: run  python generate_dashboard.py  to rebuild index.html")


if __name__ == "__main__":
    main()
