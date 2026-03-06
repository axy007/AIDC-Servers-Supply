#!/usr/bin/env python3
"""
generate_dashboard.py
---------------------
Reads data.json and produces index.html — the self-contained dashboard.
Run this after fetch_financials.py to publish an updated dashboard.
"""
import json, html as html_mod

DATA_FILE = "data.json"
OUT_FILE  = "index.html"

with open(DATA_FILE) as f:
    data = json.load(f)

def h(s): return html_mod.escape(str(s))

def status_badge(status):
    labels = {'red':'🔴 Critical','yellow':'🟡 Moderate','green':'🟢 Adequate'}
    return f'<span class="sc-badge badge-{status}">{labels.get(status,"")}</span>'

def tier_badge(tier):
    cls = 'tier-t1' if tier == 'T1' else 'tier-t2'
    return f'<span class="tier-badge {cls}">{tier}</span>'

def shortage_bar(level, status):
    color = {'red':'var(--red)','yellow':'var(--yellow)','green':'var(--green)'}.get(status,'var(--green)')
    return (f'<div class="shortage-bar-wrap">'
            f'<div class="shortage-bar-bg"><div class="shortage-bar-fill" '
            f'style="width:{level}%;background:{color}"></div></div>'
            f'<span class="shortage-pct" style="color:{color}">{level}%</span></div>')

def comp_icon(icon):
    return {'chip':'🖥️','network':'🌐','cpu':'⚡','bolt':'🌡️'}.get(icon,'📦')

def delta_cell(val, unit='%', threshold_hi=5, threshold_lo=0):
    if val is None:
        return '<td class="fin-td" style="color:var(--text-dim)">—</td>'
    sign = '+' if val >= 0 else ''
    color = ('#3fb950' if val > threshold_hi
             else '#58a6ff' if val >= threshold_lo
             else '#f85149')
    return f'<td class="fin-td fin-delta" style="color:{color}">{sign}{val}{unit}</td>'

def growth_cell(pct):
    if pct is None:
        return '<td class="fin-td" style="color:var(--text-dim)">—</td>'
    sign  = '+' if pct >= 0 else ''
    color = '#3fb950' if pct >= 30 else ('#58a6ff' if pct >= 0 else '#f85149')
    return f'<td class="fin-td fin-delta" style="color:{color}">{sign}{pct}%</td>'

# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs_html = ''
for i, comp in enumerate(data['components']):
    active     = 'active' if i == 0 else ''
    dot_color  = {'red':'var(--red)','yellow':'var(--yellow)','green':'var(--green)'}.get(comp['overall_status'],'var(--green)')
    tabs_html += (f'<button class="tab-btn {active}" onclick="switchTab(\'{comp["id"]}\')" '
                  f'id="tab-{comp["id"]}">'
                  f'<span class="tab-dot" style="background:{dot_color}"></span>'
                  f'{h(comp["name"])}</button>\n')

# ── Tab content ───────────────────────────────────────────────────────────────
content_html = ''
for i, comp in enumerate(data['components']):
    active = 'active' if i == 0 else ''

    # Subcomponent rows
    rows = ''
    for sub in comp['subcomponents']:
        rows += f'''
        <tr>
          <td>
            <div class="comp-name-cell">{tier_badge(sub.get("tier","T1"))} <span>{h(sub["name"])}</span></div>
            <div class="comp-summary">{h(sub.get("shortage_summary",""))}</div>
          </td>
          <td class="bar-cell">{shortage_bar(sub["shortage_level"], sub["status"])}</td>
          <td>{status_badge(sub["status"])}</td>
          <td class="date-cell">{h(sub.get("supply_sufficient","—"))}</td>
          <td class="dur-cell">{h(sub.get("duration_label","—"))}</td>
        </tr>'''

    # Supply chain rows
    sc_rows = ''
    for j, stage in enumerate(comp['supply_chain']):
        arrow    = '' if j == len(comp['supply_chain']) - 1 else '<div class="sc-arrow-con">↓</div>'
        sc_rows += f'''
        <div class="sc-row">
          <div class="sc-stage-num">{j+1}</div>
          <div style="flex:1">
            <div class="sc-stage-name">{h(stage["stage"])}</div>
            <div class="sc-stage-player">{h(stage["player"])}</div>
            <div class="sc-stage-notes">{h(stage.get("notes",""))}</div>
          </div>{arrow}
        </div>'''

    # Supplier financials rows
    fin_rows = ''
    for sup in comp['suppliers']:
        fin_rows += f'''
        <tr>
          <td class="fin-td fin-name-cell"><strong>{h(sup["name"])}</strong><br>
            <span class="fin-sub">{h(sup["ticker"])} · {h(sup.get("earnings_period",""))}</span></td>
          <td class="fin-td fin-rev">{h(sup.get("revenue","—"))}</td>
          {growth_cell(sup.get("revenue_growth"))}
          <td class="fin-td fin-margin">{f"{sup['oi_margin_pct']}%" if sup.get("oi_margin_pct") is not None else "—"}</td>
          {delta_cell(sup.get("oi_margin_chg_pp"), "pp", threshold_hi=3, threshold_lo=0)}
          <td class="fin-td fin-capex">{h(sup.get("capex","—"))}</td>
          {growth_cell(sup.get("capex_growth"))}
        </tr>'''

    content_html += f'''
  <div class="tab-content {active}" id="content-{comp["id"]}">

    <div class="section-hdr">
      <div>
        <div class="section-title">Component-Level Shortage Status</div>
        <div class="section-sub">{h(comp["headline"])}</div>
      </div>
      <div class="tier-legend">
        <span class="tier-badge tier-t1">T1</span> Primary Components &nbsp;·&nbsp;
        <span class="tier-badge tier-t2">T2</span> Sub-Components / Supply Chain Inputs
      </div>
    </div>

    <table class="subcomp-table">
      <thead><tr>
        <th style="width:38%">Component</th>
        <th style="width:17%">Shortage Level</th>
        <th style="width:12%">Status</th>
        <th style="width:18%">Consistent Supply By</th>
        <th style="width:15%">Duration</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>

    <div class="section-hdr">
      <div><div class="section-title">Supply Chain Breakdown</div>
      <div class="section-sub">Key players at each stage of the production chain</div></div>
    </div>
    <div class="supply-chain">
      <div class="sc-header">Production stages — {h(comp["name"])}</div>
      {sc_rows}
    </div>

    <div class="section-hdr" style="margin-top:24px">
      <div><div class="section-title">Supplier Financials</div>
      <div class="section-sub">Latest reported period · OI margin = Operating Income ÷ Revenue · pp = percentage-point change YoY</div></div>
    </div>
    <div class="fin-table-wrap">
      <table class="fin-table">
        <thead><tr>
          <th class="th-left">Supplier</th>
          <th>Revenue</th><th>Revenue Growth</th>
          <th>OI Margin</th><th>OI Margin Δ YoY</th>
          <th>FY CapEx Guidance</th><th>CapEx Growth (Implied)</th>
        </tr></thead>
        <tbody>{fin_rows}</tbody>
      </table>
    </div>

  </div>'''

# Summary cards
summary_cards = ''
for comp in data['components']:
    summary_cards += f'''
    <div class="summary-card status-{comp["overall_status"]}" data-tab="{comp["id"]}">
      <div class="sc-top"><div class="sc-icon">{comp_icon(comp["icon"])}</div>{status_badge(comp["overall_status"])}</div>
      <div class="sc-name">{h(comp["name"])}</div>
      <div class="sc-headline">{h(comp["headline"])}</div>
      <div class="sc-arrow">View full analysis →</div>
    </div>'''

data_json = json.dumps(data, ensure_ascii=False)

# ── Full HTML ─────────────────────────────────────────────────────────────────
HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>AI Data Center Supply Shortage Tracker</title>
  <style>
    :root{{--bg:#0d1117;--surface:#161b22;--surface2:#1c2333;--surface3:#21262d;--border:#30363d;--text:#e6edf3;--text-muted:#8b949e;--text-dim:#6e7681;--red:#f85149;--red-bg:rgba(248,81,73,0.12);--red-border:rgba(248,81,73,0.35);--yellow:#d29922;--yellow-bg:rgba(210,153,34,0.12);--yellow-border:rgba(210,153,34,0.35);--green:#3fb950;--green-bg:rgba(63,185,80,0.12);--green-border:rgba(63,185,80,0.35);--accent:#58a6ff;--accent-bg:rgba(88,166,255,0.1);--t1:#58a6ff;--t1-bg:rgba(88,166,255,0.12);--t2:#8b949e;--t2-bg:rgba(139,148,158,0.12);}}
    *{{box-sizing:border-box;margin:0;padding:0}}body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;font-size:14px;line-height:1.5}}
    .header{{background:var(--surface);border-bottom:1px solid var(--border);padding:16px 28px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}}
    .header-left{{display:flex;align-items:center;gap:14px}}.header-icon{{width:36px;height:36px;background:linear-gradient(135deg,#238636,#1f6feb);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px}}
    .header-title{{font-size:16px;font-weight:700}}.header-subtitle{{font-size:12px;color:var(--text-muted);margin-top:1px}}
    .last-updated{{font-size:12px;color:var(--text-dim)}}.live-dot{{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--green);margin-right:5px;animation:pulse 2s infinite}}
    @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.4}}}}
    .container{{max-width:1440px;margin:0 auto;padding:24px 28px}}
    .summary-strip{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px}}
    .summary-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px 18px;cursor:pointer;transition:all 0.2s}}
    .summary-card:hover{{border-color:var(--accent);transform:translateY(-1px);box-shadow:0 4px 20px rgba(0,0,0,0.4)}}
    .summary-card.status-red{{border-left:3px solid var(--red)}}.summary-card.status-yellow{{border-left:3px solid var(--yellow)}}.summary-card.status-green{{border-left:3px solid var(--green)}}
    .sc-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}}.sc-icon{{font-size:22px}}.sc-name{{font-size:13px;font-weight:600;margin-bottom:4px}}.sc-headline{{font-size:11px;color:var(--text-muted);line-height:1.4}}.sc-arrow{{font-size:10px;color:var(--text-dim);margin-top:10px;text-align:right}}
    .sc-badge{{font-size:10px;font-weight:700;padding:3px 8px;border-radius:20px;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap}}
    .badge-red{{background:var(--red-bg);color:var(--red);border:1px solid var(--red-border)}}.badge-yellow{{background:var(--yellow-bg);color:var(--yellow);border:1px solid var(--yellow-border)}}.badge-green{{background:var(--green-bg);color:var(--green);border:1px solid var(--green-border)}}
    .tabs{{display:flex;gap:4px;margin-bottom:20px;border-bottom:1px solid var(--border)}}.tab-btn{{background:none;border:none;color:var(--text-muted);padding:8px 16px 10px;font-size:13px;font-weight:500;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;transition:color 0.2s;display:flex;align-items:center;gap:6px}}.tab-btn:hover{{color:var(--text)}}.tab-btn.active{{color:var(--accent);border-bottom-color:var(--accent)}}
    .tab-dot{{width:7px;height:7px;border-radius:50%}}.tab-content{{display:none}}.tab-content.active{{display:block}}
    .section-hdr{{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:16px;gap:16px;flex-wrap:wrap}}.section-title{{font-size:14px;font-weight:600}}.section-sub{{font-size:12px;color:var(--text-muted);margin-top:2px}}
    .tier-legend{{font-size:11px;color:var(--text-muted);display:flex;align-items:center;gap:6px;flex-wrap:wrap;padding-top:4px}}
    .tier-badge{{font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;text-transform:uppercase;letter-spacing:0.4px;display:inline-block;flex-shrink:0}}.tier-t1{{background:var(--t1-bg);color:var(--t1);border:1px solid rgba(88,166,255,0.3)}}.tier-t2{{background:var(--t2-bg);color:var(--t2);border:1px solid rgba(139,148,158,0.3)}}
    .subcomp-table{{width:100%;border-collapse:collapse;margin-bottom:28px;background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden}}.subcomp-table th{{text-align:left;font-size:11px;font-weight:600;color:var(--text-dim);text-transform:uppercase;letter-spacing:0.5px;padding:10px 12px;background:var(--surface2);border-bottom:1px solid var(--border)}}.subcomp-table td{{padding:12px;border-bottom:1px solid var(--border);vertical-align:top}}.subcomp-table tr:last-child td{{border-bottom:none}}.subcomp-table tr:hover td{{background:var(--surface2)}}
    .comp-name-cell{{font-size:13px;font-weight:500;display:flex;align-items:flex-start;gap:7px;flex-wrap:wrap;line-height:1.4}}.comp-summary{{font-size:12px;color:var(--text-muted);margin-top:5px;line-height:1.5}}.bar-cell{{vertical-align:middle;padding-top:16px}}.date-cell{{font-size:12px;color:var(--text-muted);white-space:nowrap}}.dur-cell{{font-size:12px;color:var(--text-muted)}}
    .shortage-bar-wrap{{display:flex;align-items:center;gap:8px;min-width:120px}}.shortage-bar-bg{{flex:1;height:6px;background:var(--surface3);border-radius:3px;overflow:hidden}}.shortage-bar-fill{{height:100%;border-radius:3px}}.shortage-pct{{font-size:11px;font-weight:600;min-width:28px;text-align:right}}
    .supply-chain{{background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:0}}.sc-header{{background:var(--surface2);padding:12px 16px;font-size:12px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid var(--border)}}.sc-row{{display:flex;align-items:flex-start;padding:12px 16px;border-bottom:1px solid var(--border)}}.sc-row:last-child{{border-bottom:none}}.sc-row:hover{{background:var(--surface2)}}
    .sc-stage-num{{width:24px;height:24px;background:var(--accent-bg);border:1px solid var(--accent);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:var(--accent);flex-shrink:0;margin-right:12px;margin-top:1px}}.sc-stage-name{{font-size:12px;font-weight:600}}.sc-stage-player{{font-size:12px;color:var(--accent);margin-top:2px}}.sc-stage-notes{{font-size:11px;color:var(--text-muted);margin-top:2px}}.sc-arrow-con{{margin-left:auto;padding-left:12px;font-size:16px;color:var(--text-dim);margin-top:2px}}
    .fin-table-wrap{{background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow-x:auto;margin-bottom:28px}}.fin-table{{width:100%;border-collapse:collapse;min-width:680px}}.fin-table th{{font-size:11px;font-weight:600;color:var(--text-dim);text-transform:uppercase;letter-spacing:0.5px;padding:11px 14px;background:var(--surface2);border-bottom:1px solid var(--border);white-space:nowrap;text-align:right}}.fin-table th.th-left{{text-align:left}}.fin-td{{padding:11px 14px;border-bottom:1px solid var(--border);font-size:12px;color:var(--text-muted);text-align:right;white-space:nowrap}}.fin-table tr:last-child .fin-td{{border-bottom:none}}.fin-table tr:hover .fin-td{{background:var(--surface2)}}.fin-name-cell{{text-align:left!important;color:var(--text)!important;font-size:13px;line-height:1.5}}.fin-sub{{font-size:10px;color:var(--text-dim)}}.fin-delta{{font-weight:600}}.fin-margin{{color:var(--text)!important;font-weight:600}}.fin-rev{{color:var(--text)!important}}.fin-capex{{color:var(--text)!important}}
    .legend{{display:flex;gap:20px;align-items:center;margin-bottom:20px;flex-wrap:wrap}}.legend-item{{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-muted)}}.legend-dot{{width:10px;height:10px;border-radius:50%}}
    @media(max-width:900px){{.summary-strip{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:600px){{.summary-strip{{grid-template-columns:1fr}}.container{{padding:16px}}.header{{padding:12px 16px}}}}
  </style>
</head>
<body>
<header class="header">
  <div class="header-left">
    <div class="header-icon">⚡</div>
    <div>
      <div class="header-title">AI Data Center Supply Shortage Tracker</div>
      <div class="header-subtitle">End-to-end component &amp; supplier intelligence</div>
    </div>
  </div>
  <span class="last-updated"><span class="live-dot"></span>Last updated: {data["last_updated"]} &nbsp;·&nbsp; {h(data["metadata"]["update_note"])}</span>
</header>
<div class="container">
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:var(--red)"></div> Critical Shortage</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--yellow)"></div> Moderate Shortage</div>
    <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div> Adequate / Easing</div>
    <span style="margin-left:auto;font-size:11px;color:var(--text-dim)">Click any card to jump to full analysis →</span>
  </div>
  <div class="summary-strip">{summary_cards}</div>
  <div class="tabs" id="main-tabs">{tabs_html}</div>
  {content_html}
</div>
<script>
const ALL_DATA = {data_json};
function switchTab(id) {{
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('content-' + id).classList.add('active');
  document.getElementById('tab-' + id).classList.add('active');
}}
window.addEventListener('DOMContentLoaded', () => {{
  document.querySelectorAll('.summary-card').forEach(card => {{
    card.addEventListener('click', function() {{
      switchTab(this.getAttribute('data-tab'));
      document.getElementById('main-tabs').scrollIntoView({{behavior:'smooth',block:'start'}});
    }});
  }});
}});
</script>
</body>
</html>'''

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    f.write(HTML)
print(f"✓ Generated: {OUT_FILE}  ({len(HTML)//1024} KB)")
