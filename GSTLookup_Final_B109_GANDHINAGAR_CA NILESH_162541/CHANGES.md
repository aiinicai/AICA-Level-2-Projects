# GST Lookup v1.3 — 18 November 2026

- Added **Legal Name of Business** from the published `lgnm` field to the dashboard and Excel. The Excel heading is column 18; the original first 17 columns remain in order.
- Cancelled/suspended statuses now include the published `cxdt` effective date. Missing dates are explicitly marked Not Available.
- Moved all portal work to a single background worker. The UI can load files and display status during slow requests, with live progress, retries and duplicate-submit protection.
- Reuse the session's initial page load when refreshing CAPTCHA. Incomplete six-digit entries and stale image tokens are rejected locally. Manual CAPTCHA entry remains required.
- Read configurable network timeout/retry settings; keep the portal's rate limits. Stop task prevents further requests after the in-flight request returns/times out.
- Save completed/stopped tasks automatically. Download or delete saved tasks, then use New task to clear current results and choose fresh inputs. Task deletion removes its saved results, associated search history and app-managed export, while retaining uploaded source copies and the daily budget.
- Limit dashboard rows for smoother rendering while exporting all rows to Excel.
- Omit unused optional pandas/numpy/lxml packages from the executable. The source requirements retain them; Excel export uses openpyxl's standard Python fallback in the executable.

Testing: 135 automated tests passed. The browser workflow verified response during simulated portal delay, legal-name export, suspension effective date, completed-task download/deletion, new-task flow and mobile layout. See TEST_REPORT.md for build and executable checks.

Government response time cannot be guaranteed. Completed live taxpayer/filing retrieval remains unverified. No automatic CAPTCHA solver is included.

Close older app windows/terminals, extract into a new folder and double-click RUN_GST_LOOKUP.bat. RUN_DEMO.bat uses synthetic practice data. Version 1.3 appears at the top of the dashboard.
