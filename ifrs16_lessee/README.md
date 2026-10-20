# IFRS 16 Lessee Accounting (desktop)

Local desktop application for lessee accounting under IFRS 16 with a TallyPrime connector. Python 3.9+ · PySide6 · SQLite · Decimal arithmetic.
**Privacy:** everything stays on your computer (local SQLite file `~/.ifrs16_lessee/lessee.db`, or the path in `IFRS16_DB`). The only network traffic is the HTTP call to your own Tally when *you* click Post/Test.

## Run (one command)
```
python run.py          # Windows: run.bat    macOS/Linux: ./run.sh
```
First run creates `.venv` and installs `requirements.txt` (PySide6, openpyxl). Without a UI:
```
python -m ifrs16lessee --sample-report sample_report.xlsx --company "My Company"
python -m unittest discover -s tests -t .
```

## Using the app
1. **Dashboard → Load sample lease** (monthly payments, one reassessment, one partial termination) or **Lease entry** to add your own. Fields marked ‡ are IFRS 16 judgments/policy choices.
2. **Calculation schedule:** schedule on the left; select a row to see its journals and the trace to inputs on the right. *Initial measurement* shows each discounted payment.
3. **Reassessment / modification** and **Termination:** enter the event, *Preview* (decision, discount-rate rule applied, before/after, bridge, journals), then *Commit*. Nothing is saved until you commit.
4. **Journals:** Approve → *Preview voucher* → *Post to Tally…* (explicit confirmation). Failures keep entries pending; use *Export Tally XML* and import via Gateway of Tally > Import > Vouchers.
5. **Tally connector:** host/port, company, voucher type, account→ledger mapping, *Test connection*, *Validate ledgers*, posting log.
6. **Reports:** formatted Excel workbook (schedules, roll-forwards, bridges, termination calcs, journals, posting log, audit history).

## Layout
```
ifrs16lessee/  money.py models.py engine.py journals.py store.py tally.py reports.py sample.py __main__.py
               ui/ common.py pages.py workspaces.py app.py
tests/         test_lessee.py (engine, store, Tally mock server, reports)  test_ui_smoke.py + fake_qt.py (headless UI logic)
docs/          ASSUMPTIONS.md  (read this: assumptions, sources, out-of-scope, Tally caveats)
```
See `docs/ASSUMPTIONS.md` for accounting conventions, citations and what is deliberately out of scope (lessor accounting, sale-and-leaseback, sub-leases, FX remeasurement, restoration-provision unwinding, impairment).

## Honest limits
* The PySide6 screens could not be run where this was built (no Qt/display); UI logic is covered by a fake-Qt smoke test only. Please run the app and report any layout/behaviour issues.
* Live TallyPrime was not available; the connector is tested against a mock server. Validate with a test company first.
* IFRS 16 paragraph references should be checked against the IFRS Foundation text; this software does not replace professional judgment.
