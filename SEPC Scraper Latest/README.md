# SEPC Member Directory Scraper

A Playwright + Tkinter application for extracting publicly displayed SEPC member information.

## What it does

- Opens the SEPC Service Exporters/member directory.
- Reads sector options from the real HTML `<select>` when available.
- Processes A-Z or one selected letter.
- Discovers entity links/buttons from the DOM rather than hard-coding company names.
- Supports both normal detail-page links and JS/modal profile implementations.
- Extracts:
  - Company/Organization Name
  - City
  - State
  - Senior Officer
  - Mobile Number
  - Email ID
  - Source URL
  - Industry/Sector
  - Alphabet
- Retries failed entities.
- Stores progress in SQLite so an interrupted run can resume.
- Exports:
  - `sepc_members.xlsx`
  - `sepc_members.csv`
  - `scraping_errors.csv`

## Installation (Windows)

1. Install Python 3.10+.
2. Open Command Prompt in this folder.
3. Run:

```text
py -m pip install -r requirements.txt
py -m playwright install chromium
```

If `py` is unavailable, use `python` instead.

## Run

```text
py sepc_scraper.py
```

## First test

1. Click **Load sectors**.
2. Select the required industry/sector.
3. Select **A-Z** or a specific letter.
4. Tick **Test mode (first 3 entities)**.
5. Click **Start Scraping**.
6. Check the generated Excel/CSV files.
7. Untick test mode for the full run.

## Resume

The application creates:

`sepc_progress.sqlite3`

inside the output folder.

A successful entity is keyed by its canonical source URL (or by letter + normalized company name if no URL is exposed). On a later run with **Resume completed records** enabled, successful records are skipped.

## Conservative scraping

The default delay is 1.2 seconds between entities and retries use increasing waits. You can increase the delay from the UI. The scraper should only be used for information that the website publicly displays and in accordance with the site's terms and applicable law.

## DOM/selector assumptions

The application intentionally avoids fragile screen coordinates and avoids hard-coded company names. It discovers:

- Sector `<select>` options from `select option`.
- Alphabet navigation from the page URL/listing controls.
- Entity candidates from actual anchors/buttons in the rendered DOM.
- Profile data from tables, `<dt>/<dd>`, labels, and visible text.

Because the site's implementation can change, `discover_entities()` is deliberately broad and filters out navigation/alphabet/footer elements. If SEPC changes its DOM significantly, that function is the first place to adjust.

## Important note about sector IDs

The URL supplied by the user contains `sector_id=8`, while current indexed SEPC pages can expose a different sector ID for a similarly named service. Therefore the program does not hard-code a sector ID. It reads the selected sector's option value from the live page whenever possible; otherwise it uses the `sector_id` in the URL.

## Files

- `sepc_scraper.py` - application
- `requirements.txt` - dependencies
- `README.md` - instructions
