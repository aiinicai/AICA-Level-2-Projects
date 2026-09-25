# Build 13 Notes

Application version: `0.1.13-dev`.

## Completed
- Added stdlib-only first-run bootstrap progress UI in `app/core/bootstrap_ui.py`.
- `launch_desktop.py` now performs dependency/bootstrap setup before importing PyWebView/FastAPI-dependent desktop modules.
- Added local API v1 status contract exposing offline/local-database posture and disabled internet-updater state.
- Expanded `/api/v1` coverage for client detail/update/status, legal read endpoints, workflow read/recalculation, recommendation generation, forms, backups, plugins, and review decisions.
- Added API, bootstrap, and static visible-control integration tests.
- Audited templates for dead/placeholder visible controls; literal form actions are covered by actual routes.
- Completed user, installation, owner-licensing, developer/integration and API-v1 manuals.
- Internet legal/database downloading/updating remains disabled and unimplemented.
- Primary working database remains local SQLite on the user's computer.

## Validation
- `compileall` succeeds for application, tests, owner tools, scripts and launchers.
- New Build 13 tests: 6/6 passed.
- All test files pass when run in bounded batches: 72 tests total.
- In this Linux sandbox the single monolithic pytest command again did not return before harness timeout despite the individual/batched suites passing. The pinned-dependency Windows full-suite release gate therefore remains open.
- Windows PyInstaller/Inno Setup execution and clean-Windows acceptance remain platform-specific release gates.
