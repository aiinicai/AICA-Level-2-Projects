# Schedule III Ratio Analyser — Desktop Application

A production-grade, offline desktop application built for Chartered Accountants and statutory audit teams to automatically compute and report the **11 Analytical Ratios** mandated under **Schedule III to the Companies Act, 2013** (inserted by MCA Notification G.S.R. 207(E) dated 24 March 2021, applicable from FY 2021-22).

---

## 1. Zero-Intervention Workflow

The application completes a full statutory ratio analysis with **exactly three user actions**:
1. **Enter Client Name:** (Screen 2)
2. **Upload Current Year Financials (.xlsx/.xlsm):** (Screen 3)
3. **Upload Previous Year Financials (.xlsx/.xlsm):** (Screen 3)

Upon upload of the second file, the analysis runs to completion automatically and advances directly to the results screen with Word and Excel export options immediately available.

- **No blocking mapping prompts:** Deterministic ambiguity resolution rules (Rules 1–6) resolve duplicate captions, sub-lines, and synonyms unattended.
- **No blocking missing figures:** Automatically applies and discloses standard ICAI accounting assumptions.
- **Full disclosure:** Every assumption, ambiguity resolution, and derived figure is documented on the face of the Word export.
- **Overridable:** Overrides can be edited live with immediate table recalculation.

---

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| GUI | PySide6 (Qt 6), native desktop |
| Excel Ingestion | `openpyxl` (dynamic header & column detection) |
| Data Processing | Pure calculation engine (no hardcoded figures) |
| Word Export | `python-docx` (A4 landscape, Schedule III table, corporate `#0B4F8C` theme) |
| Excel Export | `openpyxl` (live variance formulas `=(CY-PY)/ABS(PY)`) |
| Local Storage | SQLite via `sqlite3` (stored at `%APPDATA%\ScheduleIIIRatioAnalyser\`) |
| Fuzzy Matching | `rapidfuzz` |
| Packaging | PyInstaller |

Constraints: **100% offline, zero network calls, zero telemetry.**

---

## 3. Installation & Running

### Prerequisites
- Python 3.11 or higher

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Launch the Desktop Application
```bash
python run.py
```

### Run Automated Tests
```bash
pytest -v
```

---

## 4. Expected Excel Workbook Format (§4)

The application dynamically detects sheets and figures without assuming fixed row or column positions:
- **Sheet Names:** Matched flexibly (case-insensitive, whitespace-trimmed, and synonym matched):
  - **Balance Sheet:** `BS`, `Balance Sheet`, `B/S`, `Balancesheet`
  - **Profit and Loss:** `PL `, `PL`, `P&L`, `Profit and Loss`, `Statement of Profit and Loss` (handles trailing space)
  - **Cash Flow:** `CF`, `Cash Flow`, `Cash Flow Statement`
- **Header Rows:** Automatically located by scanning the first 15 rows for `Particulars`.
- **Period Columns:** Bound dynamically by parsing date headers (e.g. `As at March 31 2026`, `For the year ended 31.03.2026`).
- **Cash Flow Statement:** Header at row 4, figures read from columns E (CY) and G (PY), with sub-total indicator column D ignored.

---

## 5. The 11 Schedule III Mandated Ratios (§6)

| # | Ratio | Numerator | Denominator | Unit | Schedule III Clause |
|---|---|---|---|---|---|
| 1 | **Current Ratio** | Current Assets | Current Liabilities | x | Clause 6(L)(i) |
| 2 | **Debt-Equity Ratio** | Total Debt (LT + ST + Current Maturities) | Shareholders' Equity (Capital + Reserves) | x | Clause 6(L)(ii) |
| 3 | **Debt Service Coverage Ratio (DSCR)** | Earnings Available for Debt Service (PAT + Depr + Finance Cost + Misc W/off) | Debt Service (Interest Paid + Principal Repayment + Lease Payments) | x | Clause 6(L)(iii) |
| 4 | **Return on Equity (ROE)** | Net Profit after Tax − Preference Dividend | Average Shareholders' Equity | % | Clause 6(L)(iv) |
| 5 | **Inventory Turnover Ratio** | Cost of Goods Sold (Materials + Purchases + Inventory Change) | Average Inventories | x | Clause 6(L)(v) |
| 6 | **Trade Receivables Turnover Ratio** | Net Credit Sales (Net Revenue × Credit Sales %) | Average Trade Receivables | x | Clause 6(L)(vi) |
| 7 | **Trade Payables Turnover Ratio** | Net Credit Purchases (Materials + Purchases) × Credit Purchases % | Average Trade Payables | x | Clause 6(L)(vii) |
| 8 | **Net Capital Turnover Ratio** | Net Revenue from Operations | Average Working Capital (Current Assets − Current Liabilities) | x | Clause 6(L)(viii) |
| 9 | **Net Profit Ratio** | Profit After Tax (PAT) | Net Revenue from Operations | % | Clause 6(L)(ix) |
| 10 | **Return on Capital Employed (ROCE)** | EBIT (PBT + Finance Costs) | Capital Employed (Tangible Net Worth + Total Debt + DTL) | % | Clause 6(L)(x) |
| 11 | **Return on Investment (ROI)** | Income from Investments | Average Total Investments (Current + Non-Current) | % | Clause 6(L)(xi) |

*Note on Denominator Handling:* Where the denominator is zero or negative, the application outputs the string **`Not meaningful`** (never `nan`, `inf`, or `0.00`) and includes an automatic footnote.

---

## 6. Standard Accounting Assumptions (§8)

| Assumption | Default | Statutory Disclosure Text |
|---|---|---|
| **Credit Sales %** | 100% | "The split between cash and credit sales is not disclosed in the financial statements. All sales have been treated as credit sales." |
| **Credit Purchases %** | 100% | "The split between cash and credit purchases is not disclosed. All purchases have been treated as credit purchases." |
| **Lease Payments** | Nil | "Lease payments falling due during the year are not separately disclosed and have been taken as nil." |
| **Preference Dividend** | Nil | "No preference share capital is in issue; preference dividend is nil." |
| **Investment Income** | Nil | "The entity holds no investments; income from investments is nil." |
| **Include ST Repayment in DSCR** | Excluded (0) | "Repayment of short-term borrowings represents revolving working capital facilities and has been excluded from debt service." |
| **Variance Threshold** | 25% | Schedule III requires explanation where the change is 25% or more. |
| **Principal Repayment Waterfall** | 3-step waterfall | Step 1: Read from CF -> Step 2: Derive from borrowings movement -> Step 3: Validate articulation against tolerance. |

---

## 7. Word & Excel Exports (§10)

- **Word Export (`.docx`):** Audit-ready A4 landscape document formatted with corporate Navy header (`#0B4F8C`), repeating header rows, alternating row tints (`#F2F7FC`), bold flagged variances, statutory footnotes, and mandatory **Assumptions and Basis of Preparation** and **Integrity Exceptions** sections.
- **Excel Export (`.xlsx`):** Formatted ratio table with live Excel formulas in the `% Variance` column (`=(CY-PY)/ABS(PY)`) and separate Assumptions tab.

---

## 8. Verification & Acceptance Test Suite

The test suite in `tests/test_acceptance.py` automates verification for all 20 acceptance tests:
- `test_no_hardcoded_figures`: Scans `src/` to guarantee no sample figures exist in source code.
- `test_engine_is_data_independent`: Verifies engine correctness on synthetic datasets.
- `test_swapped_inputs`: Tests input inversion.
- `test_golden_values_reproduction`: Verifies all 11 ratio figures within statutory tolerance.
- `test_unpopulated_template`: Ensures zero-figure templates return `Not meaningful` without crashing.
