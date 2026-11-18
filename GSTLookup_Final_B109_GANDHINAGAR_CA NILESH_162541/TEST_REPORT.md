# Test report — v1.3, 18 November 2026

Environment: Windows 11 x64, Python 3.15.2. Dependencies installed successfully in a newly created virtual environment. PyInstaller 6.22.3 built the final executable from that clean environment.

| Test group | Result | Tests |
|---|---|---:|
| Offline validators, all state codes, checksum, PAN, normalization, deduplication | PASS | 62 |
| Parser JSON/HTML fixtures, goods/services and jurisdiction | PASS | 10 |
| Mock HTTP end-to-end: correct/wrong CAPTCHA, three failures, not found, timeout, 500, 429/backoff, batch, PAN expansion, cap, new batch | PASS | 12 |
| Excel headings, sheets, row counts, missing values, real dates, injection safety | PASS | 6 |
| Web form/CSRF/host validation and three file upload formats | PASS | 4 |
| Minimum live request interval | PASS | 1 |
| Bulk file persistence/deletion, column selection, offline preview, input-type gating, PAN expansion, blank cells and relative-path downloads | PASS | 9 |
| Return-year mapping, format normalization, error/retry recovery, separate CAPTCHA, image validation and response-contract tests | PASS | 12 |
| Legal name, task lifecycle/migration, background-worker responsiveness, stop semantics, CAPTCHA local checks, effective dates and Excel | PASS | 19 |
| **pytest total** | **PASS** | **135** |
| Fresh venv, pinned dependency installation and application HTTP startup | PASS | 1 workflow |
| Chromium UI: page, controls, loaded CAPTCHA image; screenshot inspected | PASS | 1 workflow |
| Chromium provider against synthetic portal: same-session CAPTCHA submission, goods and returns | PASS | 1 workflow |
| PyInstaller one-file build and executable HTTP smoke test | PASS | 1 workflow |
| Final executable: UI, CSRF form, invalid input, history and Excel download | PASS | 1 workflow |
| Live initial HTML/templates/controller source retrieval | PASS (partial inspection) | not a live lookup |
| Live Chromium network inspection | INCOMPLETE: navigation timed out | 1 attempt |
| Live human-CAPTCHA taxpayer lookup | NOT VERIFIED | 0 completed |
| Native pywebview renderer | NOT VERIFIED | 0 |
| macOS/Linux and other Windows PCs | NOT VERIFIED | 0 |

Actual final pytest output:
```text
........................................................................ [ 53%]
...............................................................          [100%]
135 passed in 27.66s
```
The full output is test-output.txt; machine-readable results are test-results.xml. Additional evidence is in browser-transport-test.txt, exe-smoke-test.txt and exe-e2e-test.txt. screen-demo.png shows the UI using synthetic data, and sample-demo.xlsx is explicitly synthetic.

## Interpretation and limitations

All mock end-to-end cases use a real loopback Flask server and HTTP session. Mock CAPTCHA answers are read through the test server's own signing key inside tests; no OCR or live CAPTCHA bypass exists. Fixtures use field names observed in the retrieved portal source; they are not captured live successful taxpayer responses.

The web reader received HTTP 403. Python retrieved the public page, router, template, GSTIN controller, PAN controller and CAPTCHA directive. The subsequent Chromium navigation timed out, so the browser response capture PORTAL_NETWORK.json is empty. Endpoint paths are source-observed; a successful live network/submission contract remains unverified. Do not infer live compatibility from mock tests.

The final executable was built and started on this Windows environment, including a loopback form/Excel workflow. It is unsigned. Chromium was installed during development and is not embedded in the executable. The first-use automatic installation branch and native desktop renderer were not separately exercised. The browser UI was observed in Chromium; automatic default-browser launch was not visually verified. run.bat's venv/install/start operations were executed as equivalent commands, not through a double-click. run.sh was not executed on macOS/Linux.

The requested ABCDE1234F examples conflict with the holder-type rule (fourth character D). They are rejected consistently, including lowercase/space-normalized forms. Valid test examples use AAACT1234K and AABCU9603R.

Dependency installation and build failures found during development were fixed before the final clean-environment run. The test temporary directory was moved into the writable workspace after the host's default temporary directory denied access. None of those earlier failed attempts are reported as passing checks.

To rerun from the project folder:
```bat
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python main.py --demo --no-browser --smoke-test --port 0
build_exe.bat
```

## Bulk-upload update verification

The updated source passed 104 pytest tests. A real headless Chromium UI workflow uploaded a multi-column CSV, selected its PAN column, validated without network lookup, previewed the file, entered synthetic CAPTCHA answers directly in the UI, expanded one PAN to three GSTINs, skipped a duplicate, logged an invalid row, downloaded Excel and deleted the saved file. The screenshot was visually inspected. See bulk-browser-test.txt.

The rebuilt Windows executable passed HTTP startup and a bulk workflow: add file, preview, choose a column and GSTIN-only mode, validate, reject PAN/type mismatches offline, download Excel with validation logs and delete the saved file. See exe-bulk-test.txt. The earlier source browser workflow also exposed a relative data-folder download bug; this was fixed and covered by a regression test before the final build.

RUN_GST_LOOKUP.bat and RUN_DEMO.bat select the executable when available and fall back to the source launcher. Live lookup remains unverified; CAPTCHA entry remains manual. All successful CAPTCHA automation in test evidence uses the synthetic mock server's own session data, not a live portal or CAPTCHA solver.

## Return filing and dashboard update

The final suite passed 116 tests in 19.81 seconds. The public portal controller source was fetched again and confirmed its sequence: GET /services/api/dropdownfinyear with gstin, select an entry by year, then POST taxpayerReturnDetails with that entry's value in fy. The previous code bypassed the dropdown. The repaired client uses the observed sequence and preserves opaque year values. The parser now normalizes equivalent fiscal-year formats instead of dropping matching records.

Return lookups now report AVAILABLE, EMPTY or ERROR separately from the taxpayer result. Network/schema/year failures are visible in the dashboard and Run_Log. Retry filings replaces that GSTIN's old filing entries without duplicating the taxpayer. A separate manual CAPTCHA can be requested for returns, with three attempts; failing it retains the taxpayer record and reports the failure. Images are decoded to PNG and refreshed with a unique cache token.

Actual live image check: LIVE CAPTCHA IMAGE PASS — 6199 bytes, decoded to PNG. No answer or taxpayer lookup submitted. See live-captcha-check.txt. This verifies image loading only; a completed live taxpayer/return lookup remains unverified. Earlier notes about an empty browser-network capture remain historical evidence from the initial inspection.

The redesigned dashboard was checked in Chromium at desktop and mobile widths. A synthetic workflow demonstrated a failed return lookup, visible error, retry, a separate test CAPTCHA entered through the normal input field, then four return types with filing dates. Screenshots were inspected. See dashboard-browser-test.txt, screen-dashboard.png and screen-captcha.png. Bulk add/preview/column selection/validation/extraction/delete and Chromium provider session checks were rerun successfully against the mock portal after this update.

No OCR, automatic CAPTCHA filling or live CAPTCHA bypass is present. Test scripts obtain only their own synthetic mock session answer; this is separate from the application and is never applied to a live CAPTCHA. The dashboard graphs show retrieved record counts, not claimed taxpayer compliance.

## v1.3 legal name, status date, slow-network and task verification

Final pytest result: 135 passed in 27.66 seconds. New coverage checks the exact Legal Name of Business Excel header/value, missing-value handling, saved task snapshots and real dates after reload, archived downloads, task/result/log deletion, retaining uploads and the daily budget, migration of the earlier database, local rejection of incomplete/stale CAPTCHA entries, session reuse, nonblocking request handling, one portal worker thread, duplicate-operation protection, safe stop and further-request prevention. Cancelled/suspended status dates are checked in the parser and exported Excel, including missing dates and active status behavior.

The production application now uses a threaded local HTTP server and one portal executor. The executor publishes stable result snapshots and runs Playwright operations on one thread. A real Chromium UI test used this background mode, with an artificial two-second delay in the mock image loader. Local status plus dashboard requests completed in 0.016 seconds during the wait. This is a localhost responsiveness measurement, not a promise about Internet or government response time.

The browser workflow loaded/validated a bulk file, waited through the loading banner, entered synthetic CAPTCHA text through the normal field, verified four return records, downloaded an Excel file with Legal Name of Business at column 18, downloaded a saved old task, deleted that task and its history, retained the upload, started a clean task and verified a published suspension effective date in both UI and Excel. A mobile-width overflow check also passed. See smooth-browser-test.txt. Screenshots were inspected. The demo records and status dates are synthetic.

The original first 17 Excel columns remain in order; Legal Name of Business is added as column 18. The optional Other column follows it. Pending network requests can finish or time out before a stop completes; subsequent calls are prevented. Existing settings without timeout/retries use the new defaults.

The final executable excludes unused optional numpy/pandas/lxml packages and uses openpyxl's standard Python XML path. Source requirements still include those packages. The executable is checked separately for HTTP startup, bulk validation, the legal-name heading, saved-task download/delete/new-task controls, nonblocking portal status, CAPTCHA image/local format validation and safe stopping. See exe-v13-test.txt and exe-smoke-test.txt.

Live image retrieval was verified in the prior release as documented above. A completed live taxpayer or return lookup remains unverified, and native pywebview rendering, macOS/Linux execution and other Windows PCs were not tested. No zero-bug or guaranteed-speed claim is made.

### Final Windows loopback finding
An initial executable timing check failed its one-second bound. Investigation found that a status GET through localhost took 2.047 seconds, while the identical GET through 127.0.0.1 took 0.015 seconds. The launcher was changed to the direct IPv4 loopback address, and the final executable checks use that exact printed address. The local request tests were restored to a one-second bound after correcting the address; the final measured times are recorded in exe-v13-test.txt. These are local UI timings, not government-service timings.

Final executable result after the direct-loopback fix: PASS. The background start POST returned in 0.042 seconds; the local status/page pair took 0.032 seconds during CAPTCHA loading. Legal-name column 18, archive download/delete, clean new task, CAPTCHA image/local format rejection and safe stop all passed. HTTP smoke test passed. The one-file build completed successfully with the final IPv4 launcher. These measured times apply only to this test host and local HTTP requests.
