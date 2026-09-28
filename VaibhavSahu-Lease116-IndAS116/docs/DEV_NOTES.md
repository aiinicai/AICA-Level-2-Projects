# Developer notes (build log)

## Layout
- `app/engine/` — pure accounting engine (Decimal). Entry: `lessee.calculate_lessee(LesseeLeaseInput)`.
  - `models.py` dataclasses; `payments.py` generator + inclusion; `lease_term.py`; `rates.py` (day count, PV, solve_rate);
    `exemptions.py`, `lessor.py`, `sublease.py`, `sale_leaseback.py`, `tax.py`, `journals.py` (GL role catalogue),
    `disclosures.py` (aggregator), `references.py` (paragraph catalogue).
- `app/docintel/` — agreement reader (ingest → vision → OCR → rules → LLM → verify → pipeline).
- `app/db`, `app/services`, `app/api` — SQLAlchemy models, services, FastAPI routers. `app/main.py` serves the API and `app/static`.
- `app/static/js` — Vue 3 (global build, no bundler): `app.js` shell/router, `components.js`, `pages/*.js`.
- Conventions: dates = start of day; period end E closes at E+1; events processed at START of effective date unless
  `LeaseEvent.apply_after_payments=True`; payment on commencement date = paid at commencement (policy flag).
- Rounding: balance-driven (closing rounded, movement = difference) — rows always reconcile; INTEREST_TRUEUP optional.
- Reader evidence: `DocText.sentence()` / `ends_sentence()` — a '.' closes a sentence unless it follows an abbreviation
  (`ABBREV`) or a clause number ("1.", "2.3") at a line start / after ':' ';' '.'; figures ("2025.", "9,00,000.") do close it.
- Stale detection: `Lease.inputs_changed_at` (set only by input-editing endpoints) vs the current run's `created_at`.
- Schema changes after v1: add to `_ADDED_COLUMNS` in `app/db/base.py` (applied on start-up).
- Lessor (v1.1, `lessor.py` engine 2.0.0): `calculate_lessor(LessorLeaseInput)` → `LessorResult`; month-end simulation with
  event points (payments, events, deposit dates, residual date) recomputed after each step; finance leases grow the net
  investment with `Discounter.growth`; operating leases use segments `{start, end, I, W}` (I = remaining payments − accrued
  balance; W = `month_weight` or days) so para 87 modifications carry the accrued balance forward; balance-driven rounding
  for finance income, straight-line income, IDC and deposit unwinding. `position_at(summary, as_of)` rebuilds maturity /
  reconciliation from the stored JSON (segment lines, R, UGR). Services: `build_lessor_input`, `build_lessor_events`
  (`LESSOR_EVENT_TYPES`), `serialize_lessor`; lessor data lives in `Lease.lessor_details` (JSON) and `Deposit` — no schema
  change. Non-dealer FV − carrying amount → `GAIN_DERECOGNITION_LESSOR` (43090), dealer → revenue / cost of sale.

## Tests
`python -m pytest -q` → 101 passed (engine 25 spec cases incl. IFRS 16 IE13/16/17/18/19/24, invariants, lessor worked
examples with independent float cross-checks (`test_lessor.py`), doc-intel, API incl. lessor flows, ledger integrity for
lessee and lessor leases). UI verified with Playwright scripts (not shipped).

## Status
- [x] Engine
- [x] Document intelligence
- [x] DB / services / API
- [x] Frontend
- [x] Packaging (Setup.bat / installer/Setup.ps1 / Start.bat; x64 Python preferred on ARM64 for OCR wheels)
- [x] Windows launcher `Lease116.exe` (C#, .NET Framework 4.x, AnyCPU — runs natively on x64 and ARM64): source
  `installer/launcher/Lease116Launcher.cs`; build with `build_launcher.sh` (Mono `mcs`) or `build_launcher.cmd` (Windows
  `csc.exe`). Starts `venv\Scripts\python.exe -m app --no-browser` hidden, logs to `%LOCALAPPDATA%\Lease116\logs\server.log`,
  polls `/api/health`, opens the browser, tray icon (Open / Show log / Stop). Stop = `POST /api/system/shutdown` with the
  per-launch token passed in `LEASE116_LAUNCHER_TOKEN` (header `X-Lease116-Token`); forced stop kills the process tree
  (the venv python.exe is a redirector with a child interpreter). First run retargets the Desktop / Start-menu
  `Lease116.lnk` from Start.bat to the exe.
