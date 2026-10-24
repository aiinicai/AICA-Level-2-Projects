# Master Prompt: Multi-Company & Multi-Year WDV Roll-Forward Depreciation & Deferred Tax Suite (v3.0)

## Role & Objective
Act as a Senior Chartered Accountant (CA) and Principal Software Architect. Build a complete **Multi-Company & Multi-Year WDV Roll-Forward Depreciation & Deferred Tax Suite** in two synchronized formats:
1. **Self-Contained Browser Web App (`depreciation_deferred_tax_app.html`)** with dynamic multi-year WDV roll-forward/roll-back (`FY 2022-23` to `FY 2034-35`), `localStorage` auto-persistence, JSON database file save/load, and CSV exports.
2. **Standalone Python Desktop Application (`taxshield_ca_desktop.py` + `.exe` builder)** using Python `tkinter`/`ttk` and embedded `sqlite3` (`taxshield_ca_data.db`) that compiles into a single-file Windows `.exe` via PyInstaller.

## Key Functional Modules

### 1. Dynamic Multi-Year WDV Roll-Forward & Roll-Back Engine (`FY 2022-23` to `FY 2034-35`)
- **Chronological Year-by-Year Simulation**:
  - When the user changes the **Financial Year** dropdown (or clicks `◀ Prev FY` / `Next FY ▶`), every asset in the register is simulated chronologically from its acquisition date (or base anchor year) up to the selected Financial Year:
    - **If Selected FY < Acquisition FY**: The asset is marked as `Future Addition (Not Yet Put to Use)` and contributes ₹0 Opening WDV, ₹0 Depreciation, and ₹0 Closing WDV in that earlier year.
    - **If Selected FY == Acquisition FY**: The asset enters the block as a **New Addition in FY** at its Original Cost, claiming exact day-wise pro-rata Book Depreciation (Companies Act) and 180-day Full/Half Rate + Sec 32(1)(iia) 20%/10% Additional Depreciation (Income Tax Act).
    - **If Selected FY > Acquisition FY**: The asset's **Closing Book WDV** and **Closing Tax WDV** from the immediately preceding Financial Year automatically roll forward to become the **Opening Book WDV** and **Opening Tax WDV** of the selected Financial Year, and full-year subsequent depreciation is calculated (stopping at the 5% residual value floor under Companies Act).
  - **Automatic Opening Net DTL/(DTA) Roll-Forward**: Switching the Financial Year automatically updates the Opening Net DTL/(DTA) to equal the prior year's Closing Net DTL/(DTA) (`Opening Temp Diff × Effective Tax Rate`).

### 2. Multi-Company Master Module
- Add, edit, switch, and delete multiple corporate entities with CIN, PAN, TAN, Registered Address, Financial Year, Companies Act Method (`WDV` or `SLM`), Corporate Tax Regime (`Sec 115BAA`, `Sec 115BAB`, `Normal <=400Cr`, `Normal >400Cr`, `Custom`), Effective Tax Rate, and isolated Fixed Asset Registers.

### 3. Fixed Asset Register CRUD & Persistent Storage
- Add, edit, delete single assets, bulk-delete selected assets, or reset sample data.
- Auto-saves to `localStorage` (Web) / `taxshield_ca_data.db` (Python Desktop) plus one-click `.json` database export/import and `.csv` schedule export.
