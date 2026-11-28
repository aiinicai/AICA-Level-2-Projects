# IPT – Invoice Processing Tool (Desktop)

Local-first Windows desktop application for purchase invoice processing, Tally
voucher import and three-way GST reconciliation. All data stays on this computer.

**Status:** Phase 1 (Foundation) complete and tested. Phases 2–6 are built with
Google Antigravity using `AGENTS.md` and `docs/BUILD_PLAN.md`.

## Run on Windows 10/11

1. Install **Python 3.11** from python.org (tick *Add python.exe to PATH*).
2. Unzip this folder, e.g. to `C:\IPT`.
3. Double-click **setup.bat** (one time, needs internet).
4. Double-click **run_ipt.bat**.
5. First launch asks you to create the **admin** account, then log in.
6. Go to **Company Settings → Add company**, then **Add financial year**.
   Use the top-bar switchers to change company / FY.

Data folder: `%LOCALAPPDATA%\IPT_DATA` (database `ipt.db`, logs, and
`Companies\<Company>_<id>\FY_2026_27\{Invoices,GSTR2B,Purchase_Register,XML,Reports}`).
Set environment variable `IPT_DATA_DIR` to use another location.

Run tests: **run_tests.bat** (or `python -m pytest -q`).

## Continue in Google Antigravity

1. Open this folder as the workspace in Antigravity.
2. Make sure the agent reads `AGENTS.md` (project rules). If your Antigravity
   version does not load it automatically, add its contents as a workspace rule,
   or start each task with: *"Read AGENTS.md and docs/BUILD_PLAN.md first."*
3. Give the agent one task at a time from `docs/BUILD_PLAN.md`
   (e.g. "Do task 2A"). Review, run the app, run tests, then move on.
4. After each task the agent updates `docs/PROGRESS.md`.

## Project layout

```
ipt/
  app.py               entry point (login -> main window)
  config.py            data folder, db path, logs
  core/                pure logic: gstin, states, money, permissions, security
  db/                  SQLAlchemy base + models
  services/            business logic (no Qt imports) – the only layer that touches the DB
  ui/                  PySide6 windows, dialogs, pages
tests/                 pytest (services + offscreen UI smoke test)
docs/                  BUILD_PLAN, DB_SCHEMA, TALLY_XML, RECON_RULES, PROGRESS
```
