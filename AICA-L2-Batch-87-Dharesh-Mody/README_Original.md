# CA IPO Compass — Desktop

A standalone Windows desktop app (PySide6 GUI + SQLite database) that scores
IPOs using the same weighted framework as your original HTML tool, and
pulls live IPO/GMP data from NSE, BSE, Moneycontrol, Chittorgarh and
InvestorGain — no server, no hosting, everything runs on your own PC.

## 1. What actually runs where

- **Database**: a single SQLite file, auto-created at
  `~/CA_IPO_Compass/ipo_compass.db` (i.e. `C:\Users\<you>\CA_IPO_Compass\`
  on Windows). No install, no server — it's just a file.
- **GUI**: PySide6 (Qt for Python) — native window, five tabs: Dashboard,
  IPO Issues, Analysis, Manual Import, Data Sources.
- **Live data**: a background thread refreshes all five sources on the
  schedule you set (default every 5 minutes while the app is open), so
  the window never freezes during a refresh.

## 2. A source-by-source reality check (please read before relying on this)

I checked each site live before building this. Here's what that means for reliability:

| Source | Method used | Why |
|---|---|---|
| **NSE** | Direct JSON API call, with a cookie handshake first | Official data, but NSE actively blocks bot-like traffic — expect this to fail sometimes even with correct code. |
| **BSE** | Direct HTTP + table parse | Best-effort; BSE's page structure changes without notice. |
| **Moneycontrol** | Direct HTTP + table parse | Best-effort; same caveat. |
| **Chittorgarh** (GMP) | Headless Chromium (Playwright) | Confirmed: its GMP table is filled in by JavaScript *after* the page loads — plain HTTP requests only see a "Loading…" skeleton, so this needs a real (headless) browser. |
| **InvestorGain** (GMP) | Headless Chromium (Playwright) | Same — confirmed live: the page ships with "0 records" and populates via AJAX. |

None of these sites offer a public, stable, documented API for this data —
they're websites, not data feeds — so **every scraper here can break the
day any of these sites changes its HTML.** That's not a flaw specific to
this app; it's true of every GMP tracker. That's why every scraped source
also logs *why* it failed (in the Dashboard activity log) and why the
**Manual Import** tab exists — paste a CSV/JSON export or the saved HTML
of any of these pages and it parses the same way. Treat live scraping as
"usually works, sometimes needs a manual top-up," not "always works."

## 3. Setup (one-time)

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS/Linux, if you ever run it there

# 2. Install dependencies
pip install -r requirements.txt

# 3. One-time: install the headless browser Playwright needs
#    (only needed for Chittorgarh/InvestorGain scraping)
python -m playwright install chromium
```

## 4. Run it

```bash
python main.py
```

The database and its scoring logic are fully local — try it now, before
building the .exe, to confirm live sources work on your network (some
corporate/ISP firewalls block automated requests to NSE in particular).

## 5. Build a single .exe (do this ON YOUR WINDOWS PC)

PyInstaller builds for whatever OS it runs on — build the .exe on Windows
itself, not on a Linux/Mac machine, or colleagues on Windows won't be able
to run it.

```bash
pip install pyinstaller
python -m PyInstaller build.spec
```

The finished file appears at `dist\CA_IPO_Compass.exe`. Copy that single
file anywhere — no Python install needed on the machine that runs it.

**Important:** Playwright's Chromium binary is *not* bundled by
PyInstaller automatically (it's downloaded separately, not part of the
`playwright` pip package). Two options:
- **Simplest**: after installing the exe on a machine, run once from a
  terminal: `playwright install chromium` (needs internet, one-time,
  ~150 MB). The exe will then work normally afterwards.
- **Fully offline exe**: copy the Chromium folder from
  `%USERPROFILE%\AppData\Local\ms-playwright` alongside the .exe and add
  it to `datas=[]` in `build.spec`, then rebuild. This makes the .exe
  much larger (~300 MB) but removes the one-time browser download step.

If you'd rather skip the headless-browser dependency entirely, use the
**Manual Import** tab exclusively for Chittorgarh/InvestorGain (save the
page as HTML from your regular browser, then import the file) — NSE/BSE/
Moneycontrol scraping doesn't need Playwright at all.

## 6. Project layout

```
main.py                     — entry point
app/db.py                   — SQLite schema + CRUD (all persistence)
app/scoring.py              — the weighted scoring engine (ported from your HTML tool, same weights/verdicts)
app/refresh_worker.py       — background-thread refresh so the GUI never freezes
app/scrapers/base.py        — CSV/JSON/HTML table parsing shared by every source + manual import
app/scrapers/browser.py     — headless Chromium fetch helper (Playwright)
app/scrapers/nse.py         — NSE JSON API (official)
app/scrapers/bse.py         — BSE HTML table (official)
app/scrapers/moneycontrol.py, chittorgarh.py, investorgain.py — GMP/secondary sources
app/ui/main_window.py       — the PySide6 GUI (5 tabs)
build.spec                  — PyInstaller build config
```

## 7. If a site changes its layout

Each scraper is a small, separate file — e.g. if InvestorGain redesigns
their table, you only need to adjust `app/scrapers/investorgain.py` and/or
the header-matching keywords in `app/scrapers/base.py`
(`HEADER_ALIASES`), not the rest of the app. Send me the new page's HTML
and I can update the selector for you.

## 8. Scoring engine

Same weights and verdict bands as your original tool (`app/scoring.py`):
`STRONG APPLY` ≥ 8.2, `APPLY` ≥ 7.5, `WAIT/WATCH` ≥ 6.8, `CAUTIOUS` ≥ 6,
else `SKIP` — with a "Research needed" override whenever data coverage is
below 60% of the total weight, exactly as before.

---
*GMP figures are unofficial grey-market indicators, not guaranteed listing
outcomes. Always verify issue terms on BSE/NSE and financials in the RHP
before advising on any IPO application.*
