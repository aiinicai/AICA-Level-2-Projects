# capex-npv

A 10-year Capex investment appraisal toolkit — built for an AICA Level 2 capstone project.

Computes NPV, IRR, Payback Period, Profitability Index, and NPV sensitivity from a
standard set of assumptions (sales growth, EBITDA margin, tax rate, WACC, useful life,
maintenance capex, working capital, terminal growth, salvage value).

## Install

From this folder:

```bash
pip install -e .
```

Or, without installing as a package, just install the requirements and run the files directly:

```bash
pip install -r requirements.txt
```

## Usage

### 1. As a Python library

```python
from capex_npv import CapexNPVModel

model = CapexNPVModel(
    initial_capex=500_000,
    base_revenue=400_000,
    sales_growth=[0.15, 0.10, 0.10, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08],  # or a single flat rate, e.g. 0.08
    ebitda_margin=0.20,           # or a list of 10 values for per-year margin
    tax_rate=0.25,
    discount_rate=0.12,           # WACC
    useful_life=10,
    maintenance_capex_pct=0.02,
    wc_pct_of_sales=0.05,
    terminal_growth=0.0,
    salvage_value=0,
)

model.build_projection()
model.summary()          # prints NPV, IRR, Payback, PI, Accept/Reject
model.plot_cashflows()   # matplotlib chart of FCF + cumulative NPV build-up
```

### 2. Interactive command line

```bash
capex-npv-cli
```
(or, without installing: `python -m capex_npv.cli`)

Prompts you for every assumption, then prints the 10-year projection table, the
summary metrics, a WACC × growth sensitivity table, and saves a chart.

### 3. Interactive dashboard (Streamlit — browser-based)

```bash
capex-npv-dashboard
```
(or, without installing: `streamlit run capex_npv/dashboard.py`)

Opens a browser-based dashboard with sliders for every input, live KPI cards,
an interactive Plotly cash-flow chart, the full projection table, and a
color-coded NPV sensitivity grid.

### 4. Native desktop app (no browser)

```bash
capex-npv-desktop
```
(or, without installing: `python -m capex_npv.desktop_app`)

Opens the same dashboard as its own light-themed desktop window — built with
CustomTkinter, no browser or HTML involved. Requires `python3-tk` to be
available (comes pre-installed on Windows and macOS Python; on Linux install
it with `sudo apt install python3-tk` if it's missing).

## Package structure

```
capex_npv/
├── __init__.py          # exposes CapexNPVModel
├── model.py               # core valuation engine
├── cli.py                  # interactive terminal entry point
├── dashboard.py           # Streamlit dashboard (browser)
├── launch_dashboard.py     # console-script wrapper for `streamlit run`
└── desktop_app.py          # native desktop dashboard (CustomTkinter)
pyproject.toml
requirements.txt
```

## Notes on assumptions

- Depreciation is straight-line over `useful_life` years.
- Tax is applied to positive EBIT only (no loss-carryforward tax shield).
- Terminal value uses the Gordon growth formula and requires `discount_rate > terminal_growth`.
- The sensitivity table always uses a single flat growth rate per scenario, even if
  you've set up a custom per-year growth schedule elsewhere.
