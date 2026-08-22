# Ind AS 116 — Lease Accounting Suite

A modular, GUI-based lease accounting model for Chartered Accountancy
practices, covering **Day-0 measurement** of the Right-of-Use (ROU)
asset and Lease Liability under **Ind AS 116**, plus month-wise
liability amortisation and ROU depreciation schedules.

## Requirements
- Python 3.9 or later
- Tkinter (ships with standard Python installers on Windows/macOS; on
  some Linux distributions install via `sudo apt install python3-tk`)

All other third-party packages (`pandas`, `openpyxl`,
`python-dateutil`) are detected and installed **automatically the
first time you run the app** — you will see a live installation log
window while this happens. This only happens once per machine.

## Running the application
```
python main.py
```

## What it does
1. **Lease Inputs tab** — enter monthly rental, lease term, escalation,
   payment timing (advance/arrears), the Interest Rate Implicit in the
   Lease (or Incremental Borrowing Rate if not determinable), initial
   direct costs, incentives, restoration costs, etc.
2. **Run Model** computes:
   - Lease Liability at Day 0 = PV of unpaid lease payments
   - ROU Asset at Day 0 = Lease Liability + prepaid rentals + initial
     direct costs − incentives + PV of restoration costs
   - Month-wise lease liability amortisation (effective interest method)
   - Month-wise ROU depreciation (straight-line over the lease term)
3. **Export to Excel** — saves all schedules to a multi-sheet workbook
   suitable for client working papers.
4. **Save/Load Template** — save a lease's input set as a `.json` file
   so recurring engagements (e.g. annual re-runs, similar leases across
   branches) can be reloaded instantly instead of re-keyed.

## Project structure (for maintenance)
```
ind_as_116_suite/
├── main.py                  Entry point (run this)
├── README.md
└── ind_as_116/
    ├── __init__.py           Package metadata
    ├── bootstrap.py          First-run dependency detection & install
    ├── models.py             LeaseInputs / LeaseResult data structures
    ├── engine.py             All Ind AS 116 calculations (no I/O)
    ├── excel_export.py       Excel workbook export
    └── gui.py                Tkinter GUI (install log + main window)
```

The calculation engine (`engine.py`) is fully decoupled from the GUI —
it can be imported and run headlessly (e.g. from a script that batch-
processes many client leases from a CSV, or from a future web/CLI
front-end) without any Tkinter dependency:

```python
from datetime import date
from ind_as_116.models import LeaseInputs
from ind_as_116.engine import LeaseEngine
from ind_as_116.excel_export import export_to_excel

inputs = LeaseInputs(
    lease_commencement_date=date(2025, 4, 1),
    lease_term_months=60,
    monthly_rental=100000,
    incremental_borrowing_rate_annual=0.10,
)
result = LeaseEngine(inputs).run()
print(result.summary)
export_to_excel(result, "lease_model.xlsx")
```

## Key accounting reference
Ind AS 116 (Leases) — lessee recognition and initial measurement:
the Right-of-Use asset is measured at cost, and the lease liability
at the present value of lease payments not paid at the commencement
date, discounted using the interest rate implicit in the lease if
readily determinable, or otherwise the lessee's incremental
borrowing rate.

## Notes on assumptions built into this model
- Depreciation is charged straight-line over the full lease term. If
  the underlying asset's useful life is shorter and ownership does not
  transfer, adjust `build_depreciation_schedule()` accordingly.
- Variable lease payments (not based on an index/rate), sublease
  accounting, and lease modification/reassessment are **not** yet
  modelled — flagged here so future maintainers know the current scope
  boundary.
- All amounts are assumed to be in a single currency (no FX translation
  built in).

## Extending this suite
Because the engine, GUI, and export layers are separate modules,
common extensions are isolated to one file each:
- New calculation logic (e.g. lease modifications) → `engine.py`
- New input fields → add to `LeaseInputs` in `models.py` and to the
  `FIELDS` list in `gui.py`
- New export formats (e.g. PDF working paper) → new module alongside
  `excel_export.py`
