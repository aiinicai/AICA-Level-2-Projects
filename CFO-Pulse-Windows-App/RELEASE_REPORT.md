# CFO Pulse Release Report

## 2026-09-27 upload and extraction correction

The home page's multipart workbook form now submits the session's hidden `csrf_token`. The browser's broad `Accept` header no longer makes `/upload` return raw JSON; JSON responses require an explicit JSON media type, while browser uploads redirect to the ingestion report.

Some subtotal cells in the unstructured workbook have formulas with no saved calculated values and stale references after the workbook was reshaped. The analyzer now reconstructs supported P&L totals from recognized source line items and stores their exact contributing cells and raw values as lineage. Unsupported uncached formulas produce an ingestion warning. AR/AP calculated lineage now lists the contributing source values and avoids ranges that include subtotal rows.

Incomplete Drafts created by the prior importer can be repaired by uploading the same workbook again. The app reuses the report ID, refreshes its facts and lineage transactionally, appends an ingest-run record, and audits the repair. Reviewed or approved reports are not automatically rewritten. A regression simulates the old zero-P&L Draft and proves that re-upload restores the dashboard series.

Latest command: `py -3.13 scripts/verify.py` (2026-09-27; 87.12 seconds; exit 0). All 13 checks passed: compile, lint, unit tests, placeholder scan, dependencies, vendor integrity, template safety, ingest scan, server boot, golden ingest, robustness ingest, smoke e2e, and audit chain.

Latest Windows executable: `dist/CFOPulse-Verified.exe`; 25,689,507 bytes; SHA-256 `F42E1EFAA3633A50F4D3E24B64190C48C7BCC20AA5044ED09D3186B3274E662E`. Rebuilt with `py -3.13 build_exe.py --name CFOPulse-Verified`. Packaged smoke passed, including browser-style form upload and redirect, golden values, three-period and unstructured schedules, dashboard routes, PDF/PPTX export, watcher, scenarios, and occupied-port fallback. Authenticode remains `NotSigned`.

Both `CFO-Pulse-Windows-App.zip` and `CFO-Pulse-GitHub-Ready.zip` were refreshed from this build and passed ZIP integrity checks. Use the updated Windows ZIP/executable; a previously running app instance can continue serving the old code on port 8765.

## Result

The final source verification harness passes all 13 checks, the refreshed Windows executable passes packaged smoke including the structured and unstructured three-period uploads, and the clean-checkout bootstrap passes. This run adds period focus across dashboard sections; filtered schedule drill-through with source lineage; paginated PDF and PPTX rendering of ordered saved reports; same-month YoY seasonal signals; price, volume, materials-cost, margin, and DSO sensitivities; configurable admin thresholds, units, branding, and session lifetimes; and compact sample workbooks with all dashboard schedules. This is still a partial product release: remaining product gates and external release actions are listed below.

## Verification evidence

Command: `py -3.13 scripts/verify.py` (2026-09-26; 91.57 seconds; exit 0)

```text
CFO Pulse verification
CHECK                              STATUS
------------------------------------------------------------------------------------------
Python compile                     PASS
Lint                               PASS
Unit tests                         PASS
Placeholder scan                   PASS
Pinned dependencies                PASS
Vendored ECharts SHA-256           PASS
Template safety scan               PASS
Ingest hard-coded sample scan      PASS
Server boot probe                  PASS
Golden ingest                      PASS
Robustness ingest                  PASS
Smoke e2e                          PASS
Audit chain verify                 PASS
Runtime: 143.01s | Exit: 0
```

Windows executable:

- Build command: `py -3.13 build_exe.py --name CFOPulse-Verified`
- Output: `dist/CFOPulse-Verified.exe` (rebuilt 2026-09-26 with three-period schedule extraction and current dashboard, scenario, report export, and admin changes)
- Artifact size: 25,686,935 bytes. SHA-256: `513AEE087B9D6AE1879B830677DEE1C79EFFB9E53A511DF67B11FFDE3C62F3DF`. Authenticode: `NotSigned`.
- Smoke command: `py -3.13 scripts/smoke_exe.py --exe dist/CFOPulse-Verified.exe`
- Result: `PASS: executable health, authentication, all sample workbooks, three-period schedules, unstructured mapping, Working Capital dashboard, PDF/PPTX export, watcher, saved what-if, and occupied-port fallback`
- Authenticode status: `NotSigned`; a trusted signing certificate and signed distribution verification are not available in this release run.
- `py -3.13 scripts/fresh_checkout_smoke.py` passed: clean checkout booted twice, health/login responded, migrations were current, and first-run Admin creation was idempotent.
- `samples/CFO_Pulse_Three_Period_Sample_Jun-Aug2026.xlsx` was uploaded through CLI dry-run and the packaged executable. Its three monthly actuals were recognized for Jun–Aug 2026; all dashboard schedule datasets were extracted, including DSO 68.4, DIO 45.8, and DPO 52.0.
- `samples/CFO_Pulse_Unstructured_MIS_Upload.xlsx` uses renamed tabs and a reordered invoice register. CLI analysis and packaged upload both mapped every dashboard schedule and retained the June–August periods and working-capital values.

The app prints the actual URL and selected port. An older app process may continue serving port 8765; use the URL printed by the executable instance just launched.

PowerPoint compatibility repair:

- Fixed duplicate OOXML shape IDs and Office-invalid group properties (`p:cGrpSpPr` → `p:cNvGrpSpPr`). Corrected slide IDs to start at 256, layout IDs to the reserved high range, added the presentation-to-theme relationship, and removed invalid slide-size metadata.
- Regression checks parse every package XML/relationship, verify targets and content types, check per-slide shape IDs, and assert the PresentationML IDs and group-property element.
- Microsoft PowerPoint opened the regenerated four-slide golden-workbook deck and rendered all slides to PNG without repair. All four renders were visually reviewed for clipping and overlap. The earlier COM failure corresponded to malformed OOXML that has since been corrected.
- Removed the repeated section title from the dashboard template; the page title appears once while the description and controls remain.
- This host has no detectable Microsoft PowerPoint or LibreOffice executable. The new saved-report PPTX was package-validated by regression tests and exercised through the packaged export smoke, but a fresh Office visual/render review of these new table slides could not be performed here. The earlier dashboard export Office review remains recorded above.

## Requirement status

| Functional requirement | Status | Evidence / remaining work |
|---|---|---|
| F1 — workbook discovery and ingestion | Partial | `tests.test_golden`, `tests.test_transforms`, verifier golden/robustness gates pass. Arbitrary workbook generalization, full mapping-template reuse, complete DQ scoring, and universal sub-10-second ingest remain. |
| F2 — normalized facts and lineage | Partial | `tests.test_loader.LoaderTests.test_report_load_is_transactional_and_keeps_lineage` checks normalized schedule facts and source lineage across major schedules. Sales invoice facts include invoice/customer/region/product/date/quantity/value fields and exact cell coordinates; unique sales sum and duplicate exclusion are checked. Some derived and less-structured facts still fall back to block-level ranges. |
| F3 — 15 dashboard pages and interaction | Partial | `tests.test_smoke.ProductSmokeTests.test_login_upload_all_dashboard_pages_builder_and_audit` checks all pages, P&L period focus propagation, revenue/P&L and schedule fact drill-through, and source lineage. Schedule filters use tagged periods and normalized entities; source schedules without a month tag are explicitly unfilterable by month. Board Pack print mode and richer linked chart selections remain. |
| F4 — custom view and report builder | Partial | `tests.test_report_builder.MultiPageReportBuilderTests.test_create_version_clone_export_and_import_report` now covers saved-report PDF/PPTX exports. `tests.test_exports.DashboardExportTests.test_multi_page_report_exports_format_fact_amounts_and_keep_each_page` proves pagination and INR unit formatting; existing sharing, canvas, pivot, and formula-safe export tests remain. Saved-view edit history, advanced visual formatting, and the full Board Pack workflow remain. |
| F5 — report repository and live mode | Partial | Watcher tests prove unattended local change -> Draft plus SSE. `tests.test_report_lifecycle.ReportLifecycleTests.test_version_comparison_and_archive_restore_are_audited` covers materiality-filtered P&L comparison and archived status restoration with audit events. Version compare is currently P&L-only; watcher heartbeats and polling fallback remain. |
| F6 — security and RBAC | Partial | `tests.test_rbac_matrix.RuntimeRoleMatrixTests.test_every_protected_route_for_every_runtime_role` covers protected routes against all five roles. `tests.test_rate_limits.RequestRateLimitTests.test_api_rate_limit_returns_retry_after_and_login_page_is_not_limited` proves bounded API throttling. Auth, CSRF, sessions, TOTP, lockout, and upload guards have tests. HTTPS and complete deployment security review remain. |
| F7 — insights, alerts, forecast, what-if | Partial | `tests.test_narrative.NarrativeTests.test_sample_produces_report_evidence_and_driver_bridge` now verifies seasonal same-month YoY outlier detail and source cells. `tests.test_periods.PeriodEngineTests.test_price_volume_and_dso_sensitivities_are_separate_and_bounded` checks separated revenue, cost, and cash effects; smoke covers the saved scenario API. Full-year cash outlook and some expected findings remain. |
| F8 — administration, backup, hardening | Partial | `tests.test_admin_views.AdminOperationsTests.test_admin_health_and_redacted_log_views_are_role_protected` proves Admin settings persistence, timeout bounds and expiry, plus health/log access and redaction. Clean restore, role matrix, and health/log views remain tested; further deployment hardening remains. |
| F9 — audit trail | Partial | `tests.test_app.AppSmokeTests.test_scrypt_and_audit_chain`, audit mutation tests, and verifier audit-chain check pass. Events for the newly added report lifecycle, watcher, admin, and export actions are included; independent operational review remains. |
| Offline/local UX and release packaging | Partial | Offline vendor integrity, template safety, server boot, full app smoke, EXE smoke, Office render review, and `scripts/fresh_checkout_smoke.py` pass. Authenticode signing, antivirus, and organization distribution checks remain. |

## Outstanding work

- Complete saved-view edit history, advanced builder visuals/formatting, and Board Pack print mode. Multi-page saved report PDF/PPTX rendering now paginates every view with selected INR units; canvas reorder/span controls, pivot totals/drill, and audited sharing are implemented.
- Extend exact cell lineage to remaining derived/non-sales facts. P&L period focus now propagates across sections; schedule drill-through filters by available normalized period/entity dimensions and audits results.
- Complete the full-year cash outlook and remaining expected insight details. Seasonal same-month YoY statistical screening and separate price/volume/material-cost/margin/DSO sensitivities now exist. No cause is asserted without workbook evidence.
- Perform a fresh visual Office review of the new multi-page saved-report PPTX slides on a host with PowerPoint or LibreOffice, then sign the executable with the organization’s trusted certificate and complete distribution review.
- Complete Authenticode signing, antivirus review, and organization-specific distribution checks before a production release.

Do not mark M0–M9 complete until their full gates are met. Continue tracking remaining work in `docs/PROGRESS.md` and `docs/KNOWN_ISSUES.md`.
