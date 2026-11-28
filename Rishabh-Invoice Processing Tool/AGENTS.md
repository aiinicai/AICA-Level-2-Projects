# AGENTS.md – Rules for AI coding agents working on IPT

You are extending **IPT – Invoice Processing Tool**, a Windows 10/11 desktop app
for Indian Chartered Accountant firms: purchase invoice extraction, Tally voucher
import and three-way GST reconciliation (IPT invoices vs Tally purchase register
vs GSTR-2B). Accuracy beats speed. Read this whole file before every task.

## 1. Architecture (do not change without being asked)

- **Desktop only:** Python 3.11, PySide6 (Qt Widgets), SQLAlchemy 2, SQLite.
  No web server, no React, no cloud database. Everything runs locally.
- Layers, top to bottom; a layer may only import from layers below it:
  1. `ipt/ui/` – PySide6 windows, dialogs, pages. Never opens DB sessions,
     never contains GST/accounting logic. Calls services only.
  2. `ipt/services/` – business logic, one module per domain. **No Qt imports.**
     The only layer that uses `Database.session()`. Enforces permissions with
     `core.permissions.require()` and writes the audit log.
  3. `ipt/core/` – pure functions and constants (gstin, states, money, security).
  4. `ipt/db/` – models and engine.
- Pages are registered in `ui/main_window.py`. When a module from the
  `PLANNED` list is built, replace its `PlaceholderPage` with the real page.
- A `Services` container (`ui/services.py`) holds all services plus the
  `AppContext` (user, company_id, fy_id). Add new services there.
- Long work (OCR, Tally import, reconciliation, exports) runs in a
  `QThreadPool`/`QRunnable` worker with progress signals, pause/cancel where
  required. Never block the UI thread. Workers call services, not the DB.

## 2. Data rules

- Every business table has `company_id` and `fy_id` (FK) and every query filters
  by the active company and FY from `AppContext`. Data of different companies or
  years must never mix.
- Money: `Decimal` and `Numeric(18, 2)` only. Rates: `Numeric(6, 3)`. Never float.
  Use `core.money.to_decimal` / `format_inr`. Show amounts in Indian format, dates as DD-MM-YYYY.
- **Schema changes:** add a numbered function to `ipt/db/migrations.py` (MIGRATIONS dict) for
  every model change; never drop or rename columns holding user data. `Database.create_schema()`
  backs up the DB file and runs pending migrations on start-up. (Chosen instead of Alembic:
  no extra tooling, works inside the packaged .exe.)
- Original uploaded files are kept untouched under the company/FY folder
  (`services/storage_service.py`). Store paths relative to the data folder.
- Audit (`services/audit_service.record`) every create/update/delete, approval,
  mapping change, XML generation, Tally import, manual reconciliation override,
  backup/restore. Never put passwords, API keys or tokens in audit or logs.

## 3. Accounting & GST rules (non-negotiable)

- **Never fabricate data.** If extraction cannot read a field, store `None` with low
  confidence and flag it for review. Never guess GSTINs, amounts or dates.
- Never silently overwrite source invoice values; show computed differences.
- GSTIN: use `core.gstin.validate_gstin` (structure + check digit + state code).
- Intra-state (supplier state = place of supply) → CGST + SGST (UTGST for UTs with
  `is_ut_without_legislature`); inter-state → IGST. Validate, don't assume.
- GST rates come from a date-effective rate table (rates changed from 22-09-2025:
  5/18/40 with legacy 12/28 for earlier dates). Never hard-code one rate list for all dates.
- Duplicates (file hash; GSTIN + normalised invoice no + doc type; existing Tally
  voucher) are shown to the user before XML generation. Overrides need a remark.
- Never report a Tally import as successful unless Tally's response shows
  CREATED ≥ 1 and ERRORS = 0, and the voucher can be found again in Tally.
- ITC eligibility is never decided automatically; the app records the user's review.
- Reconciliation: never force a match when more than one candidate qualifies.
  A GSTIN difference or any tax head outside tolerance can never be MATCHED.

## 4. UI rules

- No non-functional buttons. A module not yet built shows `PlaceholderPage` only.
- Disable or hide controls the user's role cannot use (`has_permission`), and the
  service still enforces it.
- Destructive or irreversible actions (delete, replace GSTR-2B, Tally import,
  restore backup, duplicate override) need a confirmation dialog; overrides need a remark.
- Use `ui/helpers.py` (`make_table`, `fill_table`, `selected_id`, `error`, `confirm`)
  and the shared stylesheet. Simple language for accountants; no technical jargon in messages.
- Every page implements `refresh()` and reloads when company/FY changes.

## 5. Quality gate for every task

1. Implement only the task requested from `docs/BUILD_PLAN.md`.
2. Complete files only – no placeholders like `# TODO implement`, no dummy data in the app.
3. Add pytest tests for every rule/service you add (`tests/`). UI: extend the offscreen smoke test.
4. Run `set QT_QPA_PLATFORM=offscreen && python -m pytest -q` – all tests must pass.
5. Launch the app (`python -m ipt`) and check the new screen manually.
6. Add new dependencies to `requirements.txt` with a version range.
7. Update `docs/PROGRESS.md`: what was built, tests added, how to verify, known limitations.
8. If a requirement is technically impossible or untested (e.g. a Tally version you
   could not test), say so plainly in PROGRESS.md – never claim it works.

## 6. Reference documents

- `docs/BUILD_PLAN.md` – ordered tasks with acceptance tests.
- `docs/DB_SCHEMA.md` – tables to add in each phase.
- `docs/TALLY_XML.md` – Tally request/import XML templates and response parsing.
- `docs/RECON_RULES.md` – matching stages, tolerances, statuses, suggested actions.
