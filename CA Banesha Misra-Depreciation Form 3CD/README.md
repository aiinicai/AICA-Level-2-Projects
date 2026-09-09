# Depreciation — Form 3CB / 3CD (Clause 18)

Single-file Windows app (Python + PyQt6 + openpyxl) for block-wise
Income-tax depreciation and Form 3CD Clause 18 Excel output.

## Features
- Colourful GUI; Asset/Block dropdown auto-fills rate (`DEP_RATES`, editable).
- Assessee Name + Financial Year, printed on every Excel sheet.
- Auto 180-day full/half-rate classification from Addition Amount+Date.
- Out-of-FY dates excluded, highlighted red, and flagged.
- One Deduction field covers removal + sale consideration.
- Save/Load records by Assessee+FY (local JSON).
- Copy-paste (Ctrl+C/V) from Excel.
- Handles comma-formatted amounts correctly.
- Errors show a message box, never fail silently.

## Files
`Depreciation-3CB-3CD.py` (app) · `requirements.txt` · `run.bat` (install +
run) · `build_exe.bat` (build standalone .exe via PyInstaller)

## Getting Started
- **Run directly:** double-click `run.bat` (needs Python).
- **Standalone app:** double-click `build_exe.bat` → `.exe` appears in `dist`.

## Using the App

1. Enter Assessee Name and Financial Year.
2. Per block: pick Asset (rate auto-fills), enter Opening WDV, Addition
   Amount+Date, Deduction Amount+Date, Business Use % (blank = 100%).
3. Click **Calculate** — Period Used, Depreciation, Closing WDV fill in.
4. **Save/Load Record** to store or recall a Name+FY's data.
5. **Generate Form 3CD Excel** → `Form_3CD_Depreciation_Report.xlsx` with 5
   sheets: Form 3CD Clause 18, Copy-Paste Data (primary), Block Summary,
   Depreciation Working, Reconciliation.

## Calculation Logic
Standard WDV method: full rate on Opening WDV and additions in use ≥180
days; half rate for additions <180 days; deductions reduce the base before
depreciation; Business Use % scales the result. Rates live in `DEP_RATES` —
no tax rule beyond this mechanism is invented.

## Disclaimer
Covers the standard 180-day WDV mechanism only, not every Income-tax
provision. Review output before use in a tax filing.
