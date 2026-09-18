# CAPITAL GAINS TAX COMPARISON – 12.5% vs 20%
### Professional Windows Desktop Tax Advisory & Calculation Suite
**Designed for Chartered Accountants, Income Tax Practitioners, Tax Auditors, and Real Estate Consultants**

---

## 1. Statutory Background & Purpose

The **Finance (No. 2) Act, 2024** introduced fundamental changes to the taxation of Long-Term Capital Gains (LTCG) under **Section 112** of the Income-tax Act, 1961, effective from **23rd July 2024**:

1. **New Regime (12.5% without indexation)**: The general statutory tax rate on long-term capital gains was reduced from 20% to **12.5%**, and the second proviso to Section 48 (providing for inflation indexation) was omitted for transfers taking place on or after 23-07-2024.
2. **Grandfathering / Transitional Relief (20% with indexation)**: Under the amended second proviso to Section 112(1)(a), a special grandfathering mechanism was enacted for **Resident Individuals and HUFs** selling **Land, Building, or Land & Building** acquired prior to **23rd July 2024**.
3. **Statutory Relief Mandate**: The statute mandates that for qualifying immovable properties, the tax payable under the 12.5% unindexed regime **shall not exceed the tax computed under the pre-amendment provisions (i.e. 20% with indexation)**. The assessee is entitled to pay the **lower of the two tax liabilities**.

This software computes capital gains under **both statutory methods simultaneously**, checks legal eligibility safeguards, determines the exact tax liability (including applicable surcharge and 4% Health & Education Cess), and automatically recommends the **most beneficial method for the assessee with the exact tax saving amount**.

---

## 2. Key Features

- **Modern PyQt6 Desktop GUI**: Clean, colourful, professional light blue-and-white CA office theme.
- **Dual Computation Engine**: Calculates Capital Gains and Tax under both:
  - 12.5% Method without Indexation
  - 20% Method with Cost Inflation Indexation
- **Prominent Recommendation Card**: Highlights the winning option and tax saving prominently (e.g. `₹7,35,458`).
- **Cost of Acquisition**:
  - Automatic Financial Year and Cost Inflation Index (CII) lookup from acquisition date.
  - Pre-01/04/2001 grandfathering (Section 55(2)(b)): Option to adopt Fair Market Value (FMV) capped at Stamp Duty Value (SDV) as of 01-04-2001. Base CII = 100.
- **Cost of Improvement**:
  - Add multiple improvement line items with individual dates and financial years.
  - Individual indexation calculated for each expenditure based on improvement year's CII.
  - Statutory filtering: Excludes pre-01/04/2001 improvement expenses under Section 55(1)(b).
  - Excel import and export for multi-year improvement records.
- **Transfer Expenses / Direct Cost**:
  - Breakdown dialog for Brokerage, Legal fees, Sale commission, Registration expenses.
  - Safeguard toggle: *"Net Sale Price already after transfer expenses"* to prevent double deduction.
- **CII Master Database (SQLite)**:
  - Pre-seeded with official CBDT Cost Inflation Index values from FY 2001-02 to FY 2025-26 (and editable FY 2026-27).
  - Full CRUD: Add, Edit, Delete, Search, Excel Import, and Excel Export.
- **Configurable Tax Rule Engine**:
  - Rates (12.5%, 20%), Surcharge caps (15% for Section 112), Surcharge slabs, Cess (4%), and holding period thresholds are configuration-driven.
- **Multi-Format Report Generation**:
  - **PDF Report (ReportLab)**: Branded multi-page CA audit memorandum with tables, highlight callouts, and confidentiality headers.
  - **Excel Workbook (openpyxl)**: Formatted workbook with side-by-side computation, numbers formatted as currency, and separate improvement sheets.
  - **Word Memorandum (python-docx)**: Advisory memo ready to be issued on CA firm letterhead.
- **Audit Trail & Calculation History**:
  - Complete historical log with timestamps, inputs, CII values used, and results.
  - Instant one-click re-loading of past calculations back into the calculator.

---

## 3. Project Architecture & Modules

```
CGT CALCULATOR/
│
├── database.py              # SQLite database manager (schema creation, seeding, audit logging)
├── cii_master.py             # CII table manager, date-to-FY conversion, Excel import/export
├── tax_rules.py             # Statutory tax rules, classification (STCA/LTCA), Section 112 eligibility
├── capital_gain_engine.py   # Core capital gain computations (12.5% & 20% indexed methods)
├── tax_calculator.py        # Tax liability engine (surcharge slabs, cess, method comparison)
├── validation.py            # Input validation, date chronology, double-deduction safeguards
├── report_generator.py      # PDF, Excel, and Word export generators
├── utils.py                 # Indian currency numbering system formatter (₹1,00,00,000)
│
├── ui/
│   ├── __init__.py
│   ├── theme.py             # Professional Blue & White stylesheet and color tokens
│   ├── widgets.py           # MetricCard, RecommendationBanner, IndianCurrencyInput
│   ├── dashboard_view.py    # Executive overview, KPI cards, recent activity
│   ├── calculator_view.py   # Transaction, acquisition, improvement, and expense inputs
│   ├── comparison_view.py   # Side-by-side comparison table & detailed 19-item breakdown
│   ├── cii_view.py          # Interactive CII master table manager
│   ├── tax_rules_view.py    # Admin Tax Rule Master configuration screen
│   └── history_view.py      # Searchable calculation history & audit trail
│
├── tests/
│   ├── __init__.py
│   └── test_tax_engine.py   # Automated pytest suite covering all 12 quality control scenarios
│
├── requirements.txt         # Project dependencies
├── run_cgt_calculator.bat   # Windows one-click batch launcher
└── README.md                # Comprehensive documentation
```

---

## 4. Installation & Setup

### Prerequisites
- Windows 10 / 11 (64-bit)
- Python 3.11, 3.12, 3.13, or 3.14

### Step 1: Install Dependencies
Open PowerShell or Command Prompt in the project folder and run:
```powershell
pip install -r requirements.txt
```

---

## 5. Running the Application

### Option A: One-Click Windows Batch Launcher
Double-click `run_cgt_calculator.bat` in File Explorer.

### Option B: Command Line
```powershell
python main.py
```

The application automatically creates the SQLite database (`cgt_calculator.db`) and seeds official CBDT CII values and statutory tax rules on its very first run.

---

## 6. How to Update the CII Master

1. Navigate to **📅 CII Master** from the sidebar.
2. **To Add a New Year**:
   - Click `➕ Add CII`.
   - Enter the Financial Year (e.g. `2026-27`).
   - Enter the notified CII value (e.g. `392`).
   - Specify whether it is officially notified by CBDT.
   - Click `OK`.
3. **To Edit / Update an Existing Year**:
   - Select the row and click `✏ Edit` (or double-click the row).
   - Update the CII value or notification reference and click `OK`.
4. **Excel Import / Export**:
   - Click `📤 Export to Excel` to save the master table to a `.xlsx` file.
   - Click `📥 Import from Excel` to bulk-import new years from a spreadsheet.

---

## 7. How to Configure Tax Rules (Admin Screen)

1. Navigate to **📜 Tax Rule Master** from the sidebar.
2. You will see configuration parameters:
   - `ltcg_rate_new`: 12.5%
   - `ltcg_rate_old`: 20.0%
   - `cess_rate`: 4.0%
   - `surcharge_cap_ltcg_112`: 15.0%
   - `surcharge_slab_1_limit`: ₹50,00,000 (10% rate)
   - `surcharge_slab_2_limit`: ₹1,00,00,000 (15% rate)
   - `holding_period_immovable_months`: 24 months
   - `statutory_cut_off_date`: `2024-07-23`
3. Select any rule and click `✏ Edit Selected Rule` to update its value. All modifications are logged in the SQLite audit trail.

---

## 8. Importing Cost of Improvement from Excel

1. In the **⚡ New Calculation** view, under Section C (Cost of Improvement), click `Import from Excel...`.
2. Prepare an Excel sheet (.xlsx) with columns:
   | Particulars | Date of Improvement | Amount |
   | :--- | :--- | :--- |
   | First Floor Construction | 15/06/2010 | 1000000 |
   | Renovation & Flooring | 20/08/2015 | 500000 |
3. The software validates the dates, looks up the applicable CII for each row, and computes both actual and indexed improvement costs.

---

## 9. Report Generation Instructions

Once a calculation is executed:
1. Navigate to **⚖ Comparison & Results**.
2. Click:
   - **📄 Generate PDF**: Creates a client memorandum formatted with side-by-side comparison tables, recommendation banner, statutory grounds, and CA disclaimer.
   - **📊 Export to Excel**: Creates a formatted multi-tab workbook with separate sheets for computation and improvement schedules.
   - **📝 Export to Word**: Creates a formal Word (.docx) advisory memorandum suitable for issuance on CA letterhead.

---

## 10. Building Standalone Windows Executable (.exe)

To package the entire application into a standalone Windows executable using PyInstaller:

```powershell
pip install pyinstaller

pyinstaller --noconsole --name "CGT_Calculator" --icon=NONE --add-data "cgt_calculator.db;." main.py
```

The resulting standalone application will be located in `dist/CGT_Calculator/CGT_Calculator.exe`.

---

## 11. Automated Quality Control & Test Suite

Run the automated test suite covering all 12 mandatory statutory scenarios:

```powershell
python -m pytest tests/test_tax_engine.py -v
```

### Verified Test Cases:
1. `test_case_1_12_5_beneficial`: Property with high appreciation where flat 12.5% unindexed beats 20% indexed.
2. `test_case_2_20_indexed_beneficial`: Section 15 prompt case (Acq: 20L in FY 05-06, Imp: 10L in FY 12-13, Sale: 1Cr in FY 26-27, Saving: ₹7,35,458).
3. `test_case_3_identical_or_nearly_identical_tax`: Equivalence scenarios.
4. `test_case_4_multiple_improvements`: Multi-year improvements with distinct CII lookups.
5. `test_case_5_missing_cii`: Unregistered future FY fails safely with explicit warning.
6. `test_case_6_invalid_acquisition_date`: Acquisition after sale rejected.
7. `test_case_7_invalid_improvement_date`: Improvement before acquisition or after sale rejected.
8. `test_case_8_zero_improvement_cost`: Clean calculation when no improvements incurred.
9. `test_case_9_transfer_expenses_safeguards`: Gross vs. Net consideration and double-deduction prevention.
10. `test_case_10_pre_2001_grandfathering`: Section 55(2)(b) FMV capped at SDV and pre-2001 improvement filtering.
11. `test_case_11_asset_not_eligible_for_indexation`: Safe statutory rejection for shares, corporate assessees, non-residents, and post-cut-off acquisitions.
12. `test_case_12_different_assessment_years`: AY 2025-26, 2026-27, and 2027-28 validation.

---

## 12. Statutory Disclaimer

*This application is a specialized tax calculation aid designed to evaluate statutory options under the Income-tax Act, 1961 as amended by the Finance (No. 2) Act, 2024. All computations should be reviewed with reference to official CBDT notifications, circulars, rules, and case-specific facts before finalizing income-tax returns.*
