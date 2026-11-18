# GST Taxpayer Lookup

A local Python/Flask application with manual CAPTCHA entry, batch validation, a native-window option and Excel export. **Live taxpayer retrieval has not been verified.** The included demo and automated end-to-end tests use synthetic records. Do not treat demo results as taxpayer information.

## Project tree
```text
GSTLookup/
  main.py                 # browser/native launcher
  ui_web.py               # local Flask UI
  config.py               # portal URLs, request names, response aliases, policy
  core/
    validators.py         # offline PAN and GSTIN/checksum validation
    portal_client.py      # session HTTP, retries, browser fallback, DataProvider
    captcha.py            # human challenge attempt tracking
    parser.py             # payload conversion and missing-value handling
    exporter.py           # styled, formula-safe Excel export
    engine.py             # resumable sequential batch queue
    storage.py            # local history and persistent daily budget
    mock_portal.py        # synthetic Flask portal for tests/demo
  templates/index.html
  tests/                  # pytest tests and seven synthetic JSON fixtures
  requirements.txt
  requirements-desktop.txt
  run.bat / run.sh
  RUN_GST_LOOKUP.bat / RUN_DEMO.bat
  core/batches.py          # persistent files, column mapping, validation preview
  templates/preview.html
  build_exe.bat
  dist/GSTLookup.exe      # Windows executable
  screen-demo.png
  TEST_REPORT.md
  test-results.xml
  PORTAL_NETWORK.json
```

## Five-step quick start (Windows)
1. Extract the ZIP to a folder you can write to, such as Documents/GSTLookupApp.
2. Double-click `RUN_GST_LOOKUP.bat` for normal mode, or use a terminal to run `dist\GSTLookup.exe --demo` for synthetic practice. The executable includes Python. Source users need Python 3.10+ installed for their own account and can double-click `run.bat` instead. First source launch needs Internet to install dependencies.
3. In the local browser page, click Add batch files to save one or more .xlsx/.csv/.txt files. Preview each file, select its PAN/GSTIN column and check the files to include. Choose GST / GSTIN only, PAN only, or Auto-detect. Click Validate & preview, then Run extraction. Select a financial year, e.g. 2025-26.
4. Read the CAPTCHA image and type directly in the Enter CAPTCHA box. Click Submit CAPTCHA & run next, or press Enter. Refresh is also available. A PAN search adds the returned GSTINs to the queue; each taxpayer lookup needs its own CAPTCHA. In demo mode use PAN `AAACT1234K`.
5. Review Results and download Excel before starting another batch. Expand History for previous searches. Closing the terminal stops the app.

## Commands
```bat
run.bat
run.bat --demo
run.bat --desktop
.venv\Scripts\python -m pip install -r requirements-desktop.txt
.venv\Scripts\python -m pytest -q
build_exe.bat
```
macOS/Linux:
```sh
chmod +x run.sh
./run.sh
./run.sh --demo
./run.sh --desktop
```
Manual setup:
```sh
python -m venv .venv
# Windows:
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
# macOS/Linux equivalents: .venv/bin/python
```
`--port 8502` chooses another port. `--no-browser` suppresses browser opening. `--data-dir PATH` overrides the user data folder. `--smoke-test --no-browser --port 0` starts, checks and stops the local HTTP server.

## Screen guide
* **Batch files:** add multiple uploads, select files for a combined run, preview their original rows and delete saved uploads. CSV/XLSX have an optional header-row checkbox. Preview pages show 200 rows at a time. Deleting a saved upload never deletes your original file or changes a running queue.
* **Validate and run:** choose GSTIN, PAN or Auto-detect, select one input column per file, optionally paste more identifiers, choose a year, and click Validate & preview. The validation preview shows up to 500 rows with error messages and duplicate flags; the summary covers all rows. Other columns are ignored. Run extraction validates every selected identifier again, logs invalid rows, removes duplicate identifiers and starts the CAPTCHA queue.
* **CAPTCHA:** the current PAN/GSTIN, progress number and attempt count, the session's image, an entry box, Submit and Refresh. Amber means manual input/retry. Three rejected answers produce CAPTCHA FAILED and advance the queue.
* **Results:** a horizontally scrolling table and Download Excel. Green indicates success; red indicates invalid/not found/error. Missing public data appears as Not Available.
* **History:** an expandable local history panel with timestamp, input, result and message. See `screen-demo.png` for the rendered demo UI.

## Local storage and privacy
Default data folder: `Documents/GSTLookup/` under your user account. It contains `settings.json`, rotating `app.log`, `history.sqlite`, saved uploads in `batches/`, and the last downloaded `exports/task-<id>.xlsx`. Search history and daily counts survive restarts. Completed task results are saved automatically in history.sqlite. Pending CAPTCHA challenges stay in memory. The Completed tasks panel can download or delete saved tasks; deleting a task removes its saved results, associated search log rows and app-managed task export. Copies already downloaded to your browser remain yours to manage. Downloads also go to your browser's configured download location.

There is no telemetry or remote storage. Live mode necessarily submits the taxpayer identifier and your typed CAPTCHA to the official GST portal. Demo mode uses a loopback mock server. Only one UI batch is active per app process. Do not run multiple instances against the same data folder.

Settings default to a three-second interval and 100 lookup challenges per local calendar day. Live intervals are clamped to at least two seconds. The cap counts challenge starts, including failures; retries of the same challenge do not reserve another lookup. HTTP retries use exponential backoff and at most three attempts. Retry-After is not currently interpreted.

## Excel workbook
Taxpayers preserves the original 17 headings in order and adds `Legal Name of Business` as column 18. When additional response keys exist, an optional nineteenth `Other` column preserves them as JSON. Return_Detail has one row per published return entry, with GSTIN, return type, tax period, status, filing date and year. Run_Log records each input outcome. Registration/filing dates are real Excel dates. Formula-like strings are prefixed with an apostrophe on every sheet. Missing values use Not Available.

## Portal observations and changes
The initial portal HTML, its router, public taxpayer template, CAPTCHA directive and GSTIN/PAN controller scripts were retrieved on 17 November 2026. The current source refers to `/services/api/search/taxpayerDetails`, `/services/api/get/gstndtls`, `/services/api/search/taxpayerReturnDetails`, `/services/api/search/goodservice` and `/services/captcha`. Those paths were taken from source, not invented. A Chromium network inspection was attempted but navigation timed out; `PORTAL_NETWORK.json` contains its captured responses (empty on timeout). No successful live submission is claimed, and fixtures are synthetic approximations based on observed field names.

If the portal changes, start with `config.py`: PATHS, HEADERS, FIELDS, ALIASES, RETURN_FIELDS and error-code sets. Update nested goods/address handling in `core/parser.py` if response structure changes, then update fixtures and run pytest. The transport shares one cookie session for image and submission. It falls back to a Chromium context on HTTP 403/503 and installs Chromium for the current user if missing. Browser automation executes the public page and uses its cookie context; it does not solve CAPTCHA or remove access checks. Application-level challenges or major portal changes may require further adapter work.

`DataProvider` is the protocol in `core/portal_client.py`: implement captcha(), lookup(), goods(), returns(), close(), then inject it into Engine at launch to integrate a separately authorized GSP. The UI has no provider-specific code.

## Troubleshooting and limits
* **Live retrieval:** not verified in this environment. Validate the adapter on your network with a real taxpayer and human-entered CAPTCHA before operational use. A successful mock test does not prove live compatibility.
* **Conflicting examples:** ABCDE1234F and its lowercase form fail the requested holder-type rule because character four is D. The request calls them valid but also excludes D. The app consistently enforces the stated holder-type rule; AAACT1234K is a valid demonstration PAN. Shape/checksum validation does not prove registration exists.
* **Network/proxy/firewall:** check Internet access to services.gst.gov.in, PyPI and Playwright's download CDN. Requests honors HTTP_PROXY/HTTPS_PROXY. TLS verification remains enabled. The browser may need separate proxy configuration in a managed environment. Never disable verification to hide a certificate problem.
* **Chromium download:** first fallback can take several minutes and requires Internet plus user-writable browser storage. A one-file executable does not embed Chromium. Offline demo/normal HTTP routes do not need that download.
* **Native window:** install requirements-desktop.txt and use --desktop. pywebview can require WebView2 or platform GUI libraries. If import is unavailable, the app opens your browser. Native renderer initialization failures need the platform runtime installed; use normal browser mode meanwhile. Native desktop rendering and macOS/Linux execution were not tested here.
* **Port busy:** close the earlier process or select --port 8502.
* **Missing fields/returns:** only published fields are displayed. A return-detail request failure leaves return cells Not Available and records its reason in Run_Log. Unpublished addresses, additional places or descriptions are never synthesized.
* **Daily cap:** wait until the next local calendar day or deliberately change daily_cap in settings.json while stopped.
* **Python/venv:** use a current supported Python with venv/pip. Some Linux distributions package venv separately. User-level Python installation may be needed; this cannot guarantee installation on every managed PC without IT assistance. The Windows EXE avoids the Python prerequisite.
* **Antivirus:** unsigned PyInstaller one-file apps may trigger reputation warnings. Verify provenance and scan the file; do not disable protection. If blocked, use the source launcher or ask your IT team to assess/sign the build.
* **Testing:** TEST_REPORT.md records exact checks and limitations. Automated tests never solve a live CAPTCHA; they inspect only their own synthetic mock session.

## Bulk workflow update
Double-click RUN_GST_LOOKUP.bat to open normal mode, or RUN_DEMO.bat to practice locally. Both use the included executable when available and fall back to the source launcher. Saved uploads survive restarts; file selections and validation previews belong to the current app session. Upload limits: 5 MB per request, 20,000 rows per file, 200 columns, and 50,000 combined rows per run. For Excel, only the first worksheet is used. TXT files contain identifiers separated by whitespace, commas or semicolons. Blank identifier cells in otherwise populated rows are flagged INVALID. GSTIN-only/PAN-only modes reject mismatched input types before any portal call. PAN expansion may then fetch the GSTINs returned by that PAN.

The examples/ folder contains synthetic demo files and a blank CSV layout. Type CAPTCHA text yourself; no automatic solving is included. Live lookup remains unverified from this environment.

## Dashboard and return-filing repair

The dashboard now includes navigation, summary counters, graphics, a prominent CAPTCHA panel, record-count bars and a Return filing centre with return type, tax period, status and filing date. Graphics and styles are bundled locally; there are no remote font or chart requests.

The return lookup now initializes the portal's financial-year dropdown and sends the selected entry's value rather than assuming the displayed year string is the API value. Equivalent year labels are normalized before filtering, including 2025-26, 2025-2026 and compact forms. Filing lists inside response wrappers are recognized, as are case/separator variants of the requested return types. Unexpected response structures produce a visible error rather than silently appearing as unavailable data.

If return retrieval fails, the taxpayer row is retained and the Return filing centre shows ERROR with its reason. Retry filings reruns that lookup without repeating the taxpayer search. If the portal asks for a separate return CAPTCHA, the app displays a new image for manual entry. A failed or missing return lookup never invents filing dates or statuses. Not Available remains appropriate for data that was not published or could not be retrieved; the lookup status tells you which situation occurred.

CAPTCHA images are decoded and served as PNG with a fresh cache token on refresh. On 17 November 2026 the live CAPTCHA image was fetched and decoded successfully. No live answer or taxpayer lookup was submitted in that check. Automatic CAPTCHA recognition/filling or bypass is not implemented; a person must enter the portal image text. For a future interaction-free workflow, integrate a separately authorized API provider through DataProvider.

Run RUN_GST_LOOKUP.bat for the live portal or RUN_DEMO.bat for synthetic practice. See screen-dashboard.png and screen-captcha.png for the updated screens. Live return retrieval remains unverified; test with human CAPTCHA entry on your network before relying on the output.

## v1.3 — Legal name, responsive processing and task lifecycle (18 November 2026)

- The portal's `lgnm` is exported under the exact heading **Legal Name of Business**. It is column 18, preserving the original first 17 columns. The results dashboard places the legal name beside GSTIN and trade name for readability. Missing legal names remain Not Available.
- Cancelled and suspended GSTIN statuses include their published effective date, e.g. `Cancelled (Effective date: 02/08/2024)` or `Suspended (Effective date: 02/08/2024)`. The date comes from the portal's `cxdt` field. If not published or unparseable, the status explicitly says `Effective date: Not Available`. Active status remains unchanged. The same text appears in Excel.
- A single background worker handles all portal operations, including Chromium fallback, while the local web server can serve the dashboard and status checks. This keeps the interface available during slow requests. Status polling runs only against localhost; it does not poll the government portal.
- A loading banner displays the current request, retry/backoff and elapsed time. Duplicate operations are rejected. Invalid or incomplete CAPTCHA entries are checked locally before submission. A stale image token is rejected rather than submitting against a refreshed challenge. CAPTCHA text is still entered manually.
- Portal initialization is reused within the session, avoiding an unnecessary page fetch each time the CAPTCHA is refreshed. Requests remain sequential with the configured interval (three seconds by default; at least two seconds in live mode).
- New settings `timeout` (default 45 seconds, configurable from 2 to 60) and `retries` (maximum 3) are read from settings.json. Network requests use a separate bounded connect timeout and retain retry/backoff. These controls cannot make an unavailable or slow government service respond faster.
- **Completed tasks** lists saved tasks and their result counts. Download Excel retrieves a saved task after a restart. **Delete task** removes that task's saved results, its search log records and its app-managed export. Uploaded source copies stay in Batch files until deleted there; original user files and browser downloads are not deleted. Deleting tasks does not reset the daily portal budget.
- **New task** clears the current working results and pasted values, deselects saved uploads and lets you choose new inputs. It keeps older completed tasks until you delete them. Finish or stop the active task first.
- **Stop task** asks the worker to stop after the in-flight request returns or times out, prevents further portal calls, and retains completed partial results under a STOPPED task. A pending network request is not forcibly killed. Pending CAPTCHA work can be stopped immediately. Closing normally also asks the worker to stop safely.
- The dashboard shows up to 200 taxpayer rows and 500 filing rows for responsiveness. Every result is included in Excel. Completed tasks show the latest 100 saved tasks. Existing search logs are migrated without deletion; historical rows from older versions cannot be retroactively assigned to a task.

Extract this release into a new folder, close older app windows/terminals, then run RUN_GST_LOOKUP.bat. The header identifies this version as v1.3. RUN_DEMO.bat runs synthetic practice data. Default user storage remains Documents/GSTLookup/.

135 tests passed. A Chromium workflow checked the loading state under simulated latency, legal-name Excel export, suspension date text, completed-task download/deletion, a clean new task and the mobile layout. Government availability and completed live return retrieval remain outside this test; no zero-bug or guaranteed response-time claim is made.

### Local address performance
The launcher opens `http://127.0.0.1:<port>` directly. On the test Windows host, `localhost` took about 2.047 seconds for a local status request while the direct loopback address took 0.015 seconds. This avoids that host's local name/IPv6 fallback delay. It does not accelerate the government server. Use the address opened by RUN_GST_LOOKUP.bat rather than an old browser bookmark.

The bundled sample-demo.xlsx and sample-status-date.xlsx are synthetic examples showing the new legal-name column and effective-date status formatting.
