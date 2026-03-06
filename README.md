# AI Data Center Supply Shortage Tracker

A live, self-updating dashboard tracking supply shortages for AI data center
components — GPU boards, networking, and cooling — with supplier financials.

**Live at:** `https://YOUR_USERNAME.github.io/supply-dashboard/`
*(replace YOUR_USERNAME after completing setup)*

---

## How it works

| Layer | What it does |
|---|---|
| **`data.json`** | Master data file. Shortage intelligence (severity, timelines, summaries) lives here. Edit this manually when the supply picture changes. |
| **`fetch_financials.py`** | Pulls the latest quarterly revenue, operating income, and capex for each supplier from Yahoo Finance. Runs automatically. |
| **`generate_dashboard.py`** | Reads `data.json` and builds `index.html` — the complete self-contained dashboard. Runs automatically after the fetch. |
| **GitHub Actions** | Schedules the two scripts above to run automatically after each earnings season (mid-Feb, May, Aug, Nov). |
| **GitHub Pages** | Serves `index.html` as a public website. Every time a new `index.html` is committed, the live site updates within ~1 minute. |

### What updates automatically
- Revenue, operating income, capex figures (from Yahoo Finance)
- "Last updated" date

### What you update manually
- Shortage severity percentages and status (🔴/🟡/🟢)
- "Consistent Supply By" dates
- Component summaries and headlines
- Supply chain narrative entries

To do a manual update: edit `data.json`, save it, commit and push to GitHub
(or edit it directly in the GitHub web editor). The site rebuilds automatically.

---

## One-time setup (~10 minutes)

### Step 1 — Create a GitHub repository

1. Go to [github.com](https://github.com) and sign in
2. Click the **+** icon (top-right) → **New repository**
3. Fill in:
   - Repository name: `supply-dashboard` (or any name you like)
   - Visibility: **Public** *(required for free GitHub Pages)*
   - Leave "Initialize this repository" **unchecked**
4. Click **Create repository**

You'll land on an empty repository page. Keep this tab open.

---

### Step 2 — Upload the files

**Option A — Drag and drop (no command line needed)**

1. On your empty repository page, click **uploading an existing file**
2. Drag the entire `live-dashboard` folder contents into the upload area
   *(all files including the hidden `.github` folder)*
3. Scroll down, add a commit message like `Initial dashboard`, click **Commit changes**

> **Note for the `.github/workflows/` folder:** The web uploader may not
> show hidden folders. If the workflow file doesn't appear, use Option B or
> create it manually via the GitHub web editor after uploading the rest:
> New file → name it `.github/workflows/update.yml` → paste the contents.

**Option B — Git command line**

```bash
cd path/to/live-dashboard
git init
git remote add origin https://github.com/YOUR_USERNAME/supply-dashboard.git
git add .
git commit -m "Initial dashboard"
git branch -M main
git push -u origin main
```

---

### Step 3 — Enable GitHub Pages

1. In your repository, click **Settings** (top navigation bar)
2. In the left sidebar, click **Pages**
3. Under **Source**, select **Deploy from a branch**
4. Set Branch to **main** and folder to **/ (root)**
5. Click **Save**

GitHub will show a banner: *"Your site is live at https://YOUR_USERNAME.github.io/supply-dashboard/"*

It takes about 1–2 minutes for the first deployment to complete.

---

### Step 4 — Allow the workflow to write back to the repository

By default, GitHub Actions can read your repo but not write to it.
You need to grant write permission once:

1. In your repository, click **Settings**
2. In the left sidebar, click **Actions** → **General**
3. Scroll to **Workflow permissions**
4. Select **Read and write permissions**
5. Click **Save**

That's it — setup is complete.

---

## Running a manual refresh

You can trigger a financial data refresh at any time without waiting for the
quarterly schedule:

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. In the left sidebar, click **Refresh Dashboard**
4. Click the **Run workflow** button (top-right of the workflow table)
5. Click **Run workflow** in the dropdown

The workflow takes about 2–3 minutes. When it finishes, the live site updates
automatically.

---

## Editing shortage data manually

The shortage intelligence (severity, timelines, summaries) won't update itself
because it requires human judgement. When you want to update it:

**Via the GitHub web editor (easiest):**

1. Open your repository on GitHub
2. Click on `data.json`
3. Click the pencil icon (✏️) to edit
4. Make your changes to the relevant fields
5. Click **Commit changes**

The site will rebuild and go live within ~1 minute.

**Fields you'll typically update each quarter:**

```json
"shortage_level": 90,            ← percentage, 0–100
"status": "red",                 ← "red", "yellow", or "green"
"supply_sufficient": "2027",     ← free text: "Q3 2026", "2028", "Adequate now"
"shortage_summary": "...",       ← one sentence
"overall_status": "red",         ← the tab-level status badge
"headline": "Critical — ..."     ← the tab-level summary line
```

---

## File reference

```
live-dashboard/
├── index.html              Dashboard (auto-generated — don't edit directly)
├── data.json               Master data — edit this to update content
├── fetch_financials.py     Fetches supplier financials from Yahoo Finance
├── generate_dashboard.py   Builds index.html from data.json
├── requirements.txt        Python dependencies (yfinance)
└── .github/
    └── workflows/
        └── update.yml      Automation schedule and deploy logic
```

---

## Automatic update schedule

The workflow runs on the **15th of February, May, August, and November** —
roughly 2–3 weeks after each quarterly earnings season ends, when most
suppliers in the dashboard have reported.

If a company reports late or you want fresher data, use the manual trigger
described above.
