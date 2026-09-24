# CA IPO Compass - Local Dashboard Edition

## Start on Windows

1. Close the previous IPO Compass application.
2. Extract the entire ZIP into a new folder, for example `D:\CA_IPO_Compass_Dashboard`.
3. Open the extracted `ca_ipo_compass` folder and double-click **START_IPO_COMPASS.cmd**. Running the command from Windows' ZIP preview is detected and stopped with extraction instructions.
4. Your default browser opens the dashboard. Keep the command window open while using it.

Use your existing Python installation. The default dashboard does not need PySide6, Playwright, pip installation, a domain, hosting, an account, or an API key. A pure-Python PDF reader is included with its licence. Do not open index.html directly: launch START_IPO_COMPASS.cmd so the local updater can run.

The address starts with `http://127.0.0.1:`. This is your own computer. The application listens only on the loopback interface and does not publish your dashboard on the internet. Live retrieval needs an internet connection; saved research remains accessible when sources are unavailable.

The launcher explicitly opens Microsoft Edge or Google Chrome, even if Internet Explorer is still registered as the Windows default. Source links therefore open from the same modern browser. If neither browser is found, copy the local address printed in the command window into Edge or Chrome. If launch fails, double-click **CHECK_SETUP.cmd** and share the resulting diagnostic text. You do not need to run as Administrator.

## Existing records

Your database remains at `%USERPROFILE%\CA_IPO_Compass\ipo_compass.db`. Opening this revision under the same Windows account reuses it. Do not delete that folder. The earlier schema migration creates a database backup if it needs to add research fields.

On the Data & sources page, Export JSON backup saves your records, notes, sources and evidence. Import JSON restores this backup format. A plain JSON array imports manual records and records them as user-provided information. A matching dated issue is updated; other issues are retained. Export before intentionally restoring older data.

Watchlist preferences are saved beside your database in `dashboard_preferences.json`, so they survive browser restarts and changes to the local port. Company notes and financial records are saved in SQLite. The JSON data export contains company records; keep the preferences file as well if transferring your watchlist to another computer.

## What's changed (this build)

- **SmartScreen ("Unknown Publisher") prompt.** Windows asks this only for files carrying the "downloaded from the internet" flag, and it asks before any launcher code runs, so an app cannot switch it off for a fresh download. What changed: the launcher now clears the flag from every file in the folder (PowerShell first, then a plain-`cmd` fallback for PCs where PowerShell is restricted; folder names with apostrophes no longer break it), and it **checks the result and tells you** if the flag is still set instead of failing silently. It only does this work when the launcher is still flagged, so normal launches start faster. Every new ZIP is a new download and is flagged again, so to avoid the prompt for good, right-click the ZIP > Properties > **Unblock** *before* extracting, or update your existing unblocked folder by copying the new `app` folder and `.py` files over it. See START_HERE.txt.

## What's changed (this build)

- **IPOJI (and other GMP sites) showing "Unavailable" - now diagnosable and fixable.** "Unavailable" is shown only when the *fetch itself* failed, never when a company's name did not match (that case says "No quote published"). Until now the real reason was stored but hidden. Three changes:
  1. **The GMP tab now shows the exact reason** under every Unavailable/Blocked source, e.g. *"Plain request: HTTP 200, 1 KB, 0 table(s) with data ... browser rendering is not enabled"*. The same text is in Data & sources > Recent source responses.
  2. **Requests now look like a real browser** (full Chrome user-agent, Accept and language headers). The old bare `Mozilla/5.0` client is what many sites turn away.
  3. **IPOJI is read three ways**: its table; if the table markup changes, its `/ipo-gmp/<company>` quote links (independent of layout); and the headless browser when Playwright is installed. A failure names the step that failed.
- **New `CHECK_GMP_SOURCES.cmd`**: run it on your PC (it contacts IPOJI, unlike CHECK_SETUP) and it prints what the site actually returned to this app, what was parsed, whether your chosen company (default "SS Retail") is found, which tracked IPO it maps to, and a one-line RESULT with the fix. Output is saved to `IPO_Compass_GMP_Check.txt`.
- **New "Import saved GMP page"** (Data & sources page): open the GMP site in your own browser, press Ctrl+S, choose *Webpage, Complete*, and import the file. The site is recognised from the page itself, and its quotes go through the same name matching and GMP tab as a live refresh. This works whatever the reason live fetching fails.
- **Fixed negative GMP read as positive.** `-Rs5 (-5%)` became `+5` because the sign was separated from the digits by the rupee sign, and `Rs25 (27%)` could be read as negative. Both fixed; zero is no longer `-0`.
- **Fixed InvestorGain names** such as `SS Retail IPOC` (IPO + a status letter: O/C/U/L/CT). They only matched by luck for two-word names; single-word companies would have been missed. Also handles `SMEU`, `SMEC` and similar.
- For live rendering of JavaScript-filled sites: `pip install playwright`, then `python -m playwright install chromium`, then restart `START_IPO_COMPASS.cmd`.

## What's changed (this build)

- **Fixed GMP not being fetched when a website spells the company name differently.** Matching between the exchange feeds and the GMP sites (IPOWatch, IPOJI, InvestorGain, IPO Index, IPO Markets, IPO Premium, Chittorgarh) used to strip only "Limited/Ltd" and a trailing "IPO", then required the words to line up exactly. Any other difference meant the GMP row was not linked to the IPO: the GMP tab said "No quote published" and the row could even be discarded as an unknown, dateless IPO. Matching now lives in one place (`app/names.py`) and ignores:
  - legal suffixes (Limited, Ltd, Pvt, Private, Public, LLP, Inc), the word "India", "&" vs "and", and punctuation (`S.M.` = `SM`);
  - website tags and trailing text: `IPO`, `GMP`, `SME`, `NSE SME`, `BSE SME`, `Emerge`, "IPO Date, Price Band, Review", and "(formerly known as ...)" notes;
  - abbreviations and spelling variants: Engg/Engineering, Corp/Corporation, Co/Company, Tech/Technologies, Infra/Infrastructure, Pharma/Pharmaceuticals, Labs/Laboratories, Shri/Shree/Sri/Sree, singular/plural, and names run together (`Sri Lotus` = `Srilotus`);
  - initialisms: `NSE` = National Stock Exchange of India Limited, plus NSDL, CDSL, L&T, SBI, LIC, ONGC and similar.
  Different companies are still kept apart: the rules refuse to match on generic words alone (Om, Shree, Sai, Bharat, ...), so "Om Galaxy" is not "Om Industries" and "Shree Ram Industries" is not "Shree Ram Enterprises". This was checked against 119 real, distinct IPO names with zero false matches.
- **The GMP tab now says when a quote was matched under a different spelling** (for example: Listed by the source as "NSE IPO"), so a looser match is never hidden.
- **Small typos** (one or two letters, only on names of 12+ characters with identical numbers) are tolerated when locating a GMP quote, but never used to permanently merge two records.
- **Optional `name_aliases.json`** in your data folder (`%USERPROFILE%\CA_IPO_Compass\`) for any pair the rules cannot resolve. Format: `{"Full Company Name Limited": ["Short Name", "ABBR"]}`. It is re-read automatically; no restart needed.
- Behaviour change: `ABC India Limited` and `ABC Limited` are now treated as the same IPO (previously separate). The old test that asserted the opposite was updated.
- What this does **not** fix: a source shown as "Unavailable"/"Blocked" failed to load at all (site down, blocked, or needing the headless browser). IPO Index, IPO Markets and IPO Premium still use unverified placeholder URLs, so those rows will stay "Unavailable" until the correct addresses are set in their `app/scrapers/*.py` files.

## What's changed (this build)

- **Fixed "Listed" showing IPOs listed months ago.** Both `db.display_status()` (backend, sent to the UI on every refresh) and `statusOf()` (frontend, recomputed live in the browser) treated "Listed" as permanent once a listing date was reached — so the Listed filter kept accumulating every past IPO forever. Both now cap the Listed label at 5 days after listing (inclusive), after which the record displays as Closed, matching the 5-day rule you asked for. Covered by a new test, `test_listed_status_display_expires_after_five_days`.
  - Note this is separate from the existing 10-day `in_refresh_scope` window, which controls how long a *listed* IPO keeps getting re-fetched in the background (to catch a late-published listing price) — that's deliberately a bit wider than the 5-day *display* window and was left as-is.
- **Confirmed the 5pm IST close-cutoff rule is already correct.** `db._closed_by_cutoff()` already moves an IPO from Open to Closed at 5:00 PM IST on its close date rather than waiting for the date to roll over, and `test_5pm_ist_closing_cutoff` already covers it (still passing) — no change needed there.

## What's changed (this build)

- **Fixed subscription data genuinely not updating**, root-caused across three separate bugs:
  1. `fetch_rendered_html()`'s "did the plain HTTP fetch already work?" check only recognised a GMP reading (`gmp_amount`/`gmp_pct`). The live-subscription report has neither of those fields, so it always fell through to requiring a headless browser even in the rare case a plain fetch had real numbers. It now recognises subscription and price fields too.
  2. The row parser had no column aliases for sHNI/bHNI or the applications-count columns, so even a successful fetch could only ever populate `sub_total`/`sub_qib`/`sub_nii`/`sub_retail` — never the sHNI/bHNI breakdown the Overview tab already had a place to show. Added, with a guard against "HNI" being mis-matched as a substring of "sHNI"/"bHNI" and double-counting one of them as the combined NII figure.
  3. `db.is_active()` used to require an IPO's open date to be strictly *after* today to count it "upcoming," so an IPO opening exactly today — before its status label had been refreshed from "Upcoming" to "Open" — fell out of the refresh scope entirely and was skipped for a full day. Fixed the boundary (this also matched a pre-existing failing test in this build, `test_refresh_continues`, now passing).
  - Also improved the headless-browser error message to name the actual fix (`python -m playwright install chromium`) when the browser package is installed but its Chromium binary isn't, and added a Playwright/Chromium check to `CHECK_SETUP.cmd`'s diagnostics so this is visible without digging through refresh logs — this is the single most common reason GMP or subscription numbers never move on the default build.
- **Added an Application strategy tab**, matching the reference build: enter capital available and independent PAN applications, and every open/upcoming IPO gets a lot-value/lots/preferred-category/expected-allotment estimate — lottery odds (`1/subscription`) for Retail, proportionate scaling for S-HNI/B-HNI — plus a verdict from the existing score. Approximate by nature (flagged as such in the UI, same as the reference build); it's built from lot size, price and subscription data already in your database, not a probability guarantee.
- **Extended Watchlist into "Watchlist & tracker"**: added an application log (Issue / Category / PAN label / Amount / Status) below the existing star-toggle watchlist, stored only in `localStorage` like the watchlist itself — no server or account involved, matching the reference build's "device-local workspace" model.
- These were compared feature-by-feature against the reference build; the online reference's "Add detailed IPO" modal also exposes many more manual fields (nature of business, EBITDA, peer P/E, promoter pledge, and more) than this build's Add IPO form does. That's a larger, self-contained change I've left for a follow-up rather than rushing into this pass — flag it if you want it done next.

## What's changed (this build)

- **Fixed the launcher forcing a Playwright dependency the default build doesn't have.** `START_IPO_COMPASS.cmd` was unconditionally setting `IPO_COMPASS_BROWSER=1`, so every JavaScript-rendered source (InvestorGain GMP, Chittorgarh GMP, InvestorGain Subscription, and IPOJI's fallback) tried to launch a headless browser and failed with "Playwright is not installed" on every single refresh — even though the README has always said the default dashboard needs no pip installs. This is almost certainly why so many cards were showing "Research needed" with no GMP/price data. The launcher now only enables browser mode when Playwright is actually importable; everyone else gets the normal graceful "Research needed" fallback instead of a repeated hard error. Installing Playwright yourself (`pip install playwright && python -m playwright install chromium`) still turns on live rendering automatically.
- **Fixed raw HTML leaking into a company name.** A hand-edited or manually imported JSON record could carry a table cell's outerHTML (e.g. `<a href="…">Company</a> <span class="badge …">BSE SME</span>`) instead of its plain text, and because the name field of an *existing* record is never overwritten by later refreshes, that garbage stuck around and rendered as literal escaped markup on the card. `validate_incoming()` now strips HTML tags from the name field before accepting a record, and `purge_malformed_records()` (already run automatically every refresh) now also recognises and removes any such record already in your database — it'll be cleanly re-created from a real source on the next successful refresh instead.
- **Fixed a latent bug in `validate_incoming()`** where a redundant local `import re` (used only for the financial-year check) shadowed the module-level import for the whole function, which would raise `UnboundLocalError` the moment `re` was used any earlier in that function — as the markup-stripping fix above now does. Removed the redundant import.
- **Fixed a real data-loss bug in the RHP parser**: it used to stop scanning a prospectus as soon as it found revenue/PAT/CFO/capex/inventory, even if it hadn't reached the balance-sheet page yet — that's why Current assets, Current liabilities (and sometimes Trade receivables/payables) showed "Not disclosed / not retrieved" even though the RHP had them. It now keeps scanning until balance-sheet fields are found too, and the time budget was raised (90s→180s, 800→1200 pages) to match.
- **Added a fallback extractor for rotated/degraded PDF pages.** pypdf's "Rotated text discovered" warning (the message flooding the console in your screenshot) is emitted for pages with landscape tables, watermarks or stamps, and it degrades the position-based column parser those pages depend on. There's now a second, order-based parser that kicks in specifically when a balance-sheet page matches but the strict column parser found nothing.
- **Quieted the console spam.** That warning is informational (pypdf still returns partial text) and was printing once per affected page; it's now suppressed so the terminal doesn't look like it's hung.
- **Broadened label matching** on the secondary sites already being queried (IPO360, IPOPlatform, Chittorgarh) to catch "Current assets" / "Current liabilities" without the "Total" prefix.
- **Added a clearly-labelled last-resort estimate** for Current assets / Current liabilities when no source discloses the true total: Current assets ≈ inventory + receivables + cash, Current liabilities ≈ trade payables. Both are tagged "Estimated… partial total — actual figure will be equal or higher" in the source subtext under each cell, and Net working capital computed from them inherits that caveat — treat these as a floor, not the audited figure.
- Research cache version bumped so existing records re-fetch with these fixes on next refresh instead of serving the old incomplete cache.

## What's changed

- Navy sidebar, teal accents, rounded KPI cards, IPO cards, search and status filters.
- Detailed analysis with point-score ring, 17 weighted factors and research coverage.
- Financials, Cash Flow, Working Capital, Balance Sheet, Scorecard, Sources and Notes tabs.
- Company comparison for up to four IPOs, notes, Add IPO and data backup/import.
- Automatic refresh at launch; Refresh & analyse all refreshes exchange lists and researches every open/upcoming IPO.
- BSE and NSE copies of the same legal company are consolidated into one record with `BSE / NSE` shown as the exchange. Existing duplicates are merged at startup without deleting their source logs.
- Dashboard, analysis, comparison and official-monitor lists show only open and upcoming IPOs. Completed records remain saved in SQLite for audit history but do not appear in active lists.
- An optional 15-minute refresh while the browser page remains open; concurrent refreshes are prevented.
- Progress logs, stop-after-current-request control and source failure messages.
- Responsive layout for different browser widths. This local Windows package does not expose its updater to separate phones/tablets on your network.

## Financial research pipeline

1. **NSE / BSE:** current and upcoming issue terms, dates, prices and subscription where returned by the feeds. Exchange-provided issue terms take priority over secondary sources.
2. **IPO360:** completed annual statement columns, including cash flows, profit, finance cost, depreciation, balance-sheet figures and any supported working-capital rows.
3. **IPOPlatform:** company discovery and annual financial tables, including reported EBITDA, borrowings, net worth, returns and links to offer documents. Quarterly/annualised stub figures are excluded.
4. **Issuer / lead-manager RHP:** follows a linked red-herring prospectus and extracts supported text-based annual restated statements. Current verified document links are also configured for Manika Plastech, Veegaland Developers and Raksan Transformers. These are source URLs, not embedded company financial figures.
5. **Derivations:** operating EBITDA from PBT + finance cost + depreciation - other income; FCF from CFO - cash asset purchases; current assets less current liabilities; and average-balance working-capital days when the required denominator is available.

The first refresh may take several minutes for a full issue list. Financial statements and successful filing extracts are cached for up to 24 hours. Failed sources are retried on later refreshes. Existing source observations retain their original retrieval dates when reused. GMP and issue feed requests run on each full refresh.

Each statement observation stores the financial year, source URL, units, calculation method and, for PDF evidence, physical PDF page number. Primary extracted figures take priority over secondary observations. Material differences are recorded in Sources for review. Scores remain provisional; unresolved differences or missing essential inputs keep the model call at Research needed.

### What cannot be guaranteed

Some websites restrict automated requests or change their tables. Some documents are scanned, encrypted or use unsupported layouts. The PDF parser supports validated three-year March statements and a four-column consolidated layout with a June stub followed by three March years; it does not guess other layouts. It cannot guarantee every figure for every IPO.

No value is fabricated to make a dashboard look complete. Missing inventory stays missing. Net investing outflow and proposed IPO use of proceeds are never substituted for historical cash capex. Annualised interim figures are never treated as completed-year results. Manual evidence can be imported when a source is unavailable.

Source totals can vary by consolidated/standalone basis, rounding and restatement. Inspect recorded differences and the linked filing before relying on the result. Qualitative factors such as governance, customer concentration or anchor quality require actual supporting inputs and are not guessed from a company name.

## Websites used

- NSE: https://www.nseindia.com/market-data/all-upcoming-issues-ipo
- BSE: https://www.bseindia.com/markets/PublicIssues/IPOIssues?Type=p&expandable=4&id=1
- IPO360: https://www.ipo360.in/
- IPOPlatform: https://www.ipoplatform.com/ipo/mainboard
- InvestorGain GMP: https://www.investorgain.com/gmp/
- Moneycontrol IPO: https://www.moneycontrol.com/ipo/
- Chittorgarh GMP: https://www.chittorgarh.com/report/ipo-gmp-grey-market-premium/93/
- Manika issuer RHP: https://manikaplastech.com/wp-content/uploads/2026/09/RHP.pdf
- Veegaland issuer RHP: https://www.veegaland.com/wp-content/uploads/2026/08/VA20260830_Veegaland-RHP_Final.pdf
- Raksan lead-manager RHP: https://hemadmin.hemsecurities.com/images/Files/offer/3088.pdf

GMP is unofficial. It is an observation rather than a promised listing gain. The existing GMP source priority and source history are retained.

## Validation of this revision

Tested in the development environment:

- Automatic Manika research fetched IPO360, IPOPlatform and its issuer RHP successfully in one run.
- Manika FY2026 RHP extraction: CFO 44.30, cash asset purchases 18.95, inventory 60.813 and FCF 25.35 (all INR crore). June interim data was excluded.
- Veegaland FY2026 RHP extraction: CFO -74.2595, cash asset purchases 21.0284, inventory 287.9684 and FCF -95.2879 (INR crore). Values were checked against the financial statement pages.
- Automated checks cover missing values, annual/interim selection, source conflicts, score gates, imports, local API security and refresh continuation after a source failure.
- All dashboard and analysis views passed JavaScript rendering checks with representative records.

The application was not run on your Windows computer. The remote browser environment could not display the local dashboard; a full interactive visual check on Windows is still needed. This ZIP contains Python source and the browser interface, not a compiled Windows executable.

Run `python -m unittest test_app -v` for the packaged regression checks. Run `python main.py --no-refresh` to view saved data without making source requests. The previous Tkinter interface is retained as `python main.py --classic`.

## Third-party component

`vendor/pypdf` is pypdf 6.10.0, distributed under BSD-3-Clause. Its licence is included in `vendor/PYPDF_LICENSE.txt`. Other default runtime modules are from Python's standard library. No paid data API or language-model API is configured.

The old Qt source and original README are retained for reference only. Their installation instructions do not apply to this dashboard edition. The updated PyInstaller spec is provided for developers; a Windows executable build has not been tested or supplied.
