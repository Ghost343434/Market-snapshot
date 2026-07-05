# Market Snapshot

A one-screen dashboard: overall market theme, major indices, sector relative
strength, and a few macro readings. A GitHub Action refreshes the data
automatically — no server to run yourself.

## How it works

- `scripts/fetch_data.py` pulls current prices (via `yfinance`) and writes `data.json`.
- `.github/workflows/update-data.yml` runs that script on a schedule and commits the result.
- `index.html` just reads `data.json` and renders it. No API keys, no backend.

## Setup (~5 minutes)

1. **Create a new repo on GitHub** (public), e.g. `market-snapshot`.
2. **Upload these files**, keeping the folder structure exactly as-is:
   - `index.html`
   - `data.json`
   - `requirements.txt`
   - `scripts/fetch_data.py`
   - `.github/workflows/update-data.yml`
3. **Allow the Action to commit back to the repo:**
   Repo → **Settings → Actions → General** → scroll to *Workflow permissions* →
   select **Read and write permissions** → Save.
4. **Turn on GitHub Pages:**
   Repo → **Settings → Pages** → Source: **Deploy from a branch** →
   Branch: `main`, folder: `/ (root)` → Save.
   GitHub will give you a URL like `https://<your-username>.github.io/market-snapshot/`.
5. **Run it once manually** so real data shows up right away:
   Repo → **Actions** tab → **Update Market Data** → **Run workflow**.
   Refresh your Pages URL after ~30 seconds.
6. Bookmark that URL. It'll pull fresh numbers each time you load it, and the
   underlying data refreshes automatically at 5am and 2pm MST on weekdays.

## Changing the schedule

Edit the two `cron` lines in `.github/workflows/update-data.yml`. Times are in
UTC — the comments in that file explain the Mountain Time conversion and the
daylight-saving caveat (GitHub Actions cron doesn't shift for DST, so the
local time will drift by an hour for part of the year unless you adjust it
twice a year).

## Changing what it tracks

Add or remove tickers in the `INDICES` / `SECTORS` / `MACRO` lists at the top
of `scripts/fetch_data.py` — any valid Yahoo Finance ticker works.
