# Stage 17 — Packaging Test Notes

This file exists because the governing Stage 17 instruction (Section 35) explicitly asks for it alongside automated tests. It records, item by item against that section's 32-point list, what was actually verified, how, and what genuinely could not be — honestly, per the instruction's own "do not claim an EXE test was completed if the EXE could not actually be executed."

Automated tests live in `tests/test_stage17_packaging.py` (23 tests, all passing). This file covers the items that automated tests can't reach in this environment.

| # | Item | Result |
|---|---|---|
| 1 | Clean package builds | **Not performed.** No Windows, no PyInstaller in this sandbox — see `documentation/stage17_exe_packaging.md` Section 0. |
| 2 | EXE starts | Not performed (no EXE exists). |
| 3 | Local mode starts | Verified via the real (unfrozen) `finsight_app.py`, `FINSIGHT_LAUNCH_MODE=local`, against a fresh temp copy of the project — started successfully, served real HTTP. |
| 4 | Browser opens/local URL works | The `webbrowser.open()` call itself was not observable headlessly in this sandbox (no display); the URL it targets (`http://127.0.0.1:5000`) was confirmed reachable and correct via direct HTTP request in the same run. |
| 5 | Database initializes on first run | Verified — both via `tests/test_stage17_packaging.py`'s unit tests and a live run against a genuinely fresh temp copy (no pre-existing `finsight.db`): schema created automatically, no manual command run. |
| 6 | Existing database is preserved | Verified at the unit level: `Base.metadata.create_all` is asserted **not called** when `db_existed_before=True`. |
| 7 | Existing migrations are handled safely | Partially verified — see `documentation/stage17_exe_packaging.md` Section 10; real Alembic isn't installed in this sandbox, so this was verified against a faithful fake `alembic.command`, not the real library. |
| 8 | Templates load | Verified live — the Dashboard, Engagement, and Settings pages all rendered correctly during the live local-mode run. |
| 9 | Static assets load | Verified live in the same run (CSS/JS referenced by rendered pages; unchanged from every prior stage's own verification). |
| 10 | CSV upload works | Not re-tested this stage — unmodified code path, already covered by the full pre-existing suite (`tests/test_upload_http.py` etc.), which passed unmodified in the full regression run. |
| 11 | XLSX upload works | Same as above. |
| 12 | Accounting Review works | Unmodified, covered by the full regression run (699 passed). |
| 13 | Audit Review works | Unmodified, covered by the full regression run. |
| 14 | Tax Review works | Unmodified, covered by the full regression run. |
| 15 | Unified Review works | Unmodified, covered by the full regression run. |
| 16 | Findings Centre works | Unmodified, covered by the full regression run. |
| 17 | Query Centre works | Unmodified, covered by the full regression run. |
| 18 | Working Papers work | Unmodified, covered by the full regression run. |
| 19 | Evidence references work | Unmodified, covered by the full regression run. |
| 20 | Reviewer notes work | Unmodified, covered by the full regression run. |
| 21 | LAN mode starts | **Not performed live** — `waitress` isn't installed in this sandbox, so `finsight_app.py`'s `_run_lan()` path (which calls `waitress.serve`) could not actually be invoked. The mode-selection and pre-`serve()` logic (secret-key guard, banner, config flag) is unit-tested. |
| 22 | LAN authentication works | Unmodified Stage 16 code, covered by the full regression run (`tests/test_stage16_lan.py`, still passing). |
| 23 | LAN client browser can connect | Not performed (requires a real running LAN server — see item 21). |
| 24 | Host database remains local | By construction — same as every prior stage; no new network/sync code was added. |
| 25 | Client does not receive database | By construction — no download route exists (confirmed since Stage 15's static-file-exposure review, unchanged). |
| 26 | Sign out works | Unmodified Stage 16 code, covered by the full regression run. |
| 27 | Password change works | Unmodified Stage 16 code, covered by the full regression run. |
| 28 | Existing data survives restart | Verified live: engagement created in one run, would persist in `finsight.db` (a real file, not `:memory:`) across a restart — the file's persistence itself is standard SQLite behavior, not something this stage changed. |
| 29 | Existing data survives package upgrade | **Not performed as a literal two-build walkthrough** — there is no first build to upgrade *from* in this environment. Logically covered by item 6 (existing DB never recreated) plus the unchanged data-directory layout; needs a real two-version manual test once a Windows build exists (see the Manual UAT Checklist, Section 4 below). |
| 30 | Application shuts down cleanly | Not stress-tested; Flask's dev server (local mode) and Waitress (LAN mode, not run live here) both handle normal interrupt/shutdown signals by default — no custom shutdown logic was added or is believed necessary. |
| 31 | No external network dependency | Verified — the existing Stage 15 static scan (`test_no_outbound_network_call_in_application_source`) already covers every file `app/bootstrap.py`, `app/launch_common.py`, and `finsight_app.py` fall under, and passed unmodified. |
| 32 | No external AI/API dependency | Same as above — unmodified, passing. |

## Manual UAT Checklist

See the governing instruction's Section 36, reproduced verbatim in `documentation/stage17_exe_packaging.md`'s companion completion report for you to run once a real Windows build exists. Nothing in this checklist can be honestly marked complete from this sandbox.
