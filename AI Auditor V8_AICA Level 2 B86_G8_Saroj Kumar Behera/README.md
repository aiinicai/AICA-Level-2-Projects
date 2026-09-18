# AI Auditor V8

**AI Auditor V8** is a comprehensive offline Windows desktop application for financial statement analysis, ratio computation, multi-period trend & variance analysis, Chartered Accountant audit evidence suggestion, and multi-format reporting (Excel & Word).

Developed from the combined expertise of a Senior Chartered Accountant, Python Desktop Application Developer, and Software Architect / QA Engineer.

---

## Key Features

1. **Multi-Format Ingestion**:
   - Supports multi-sheet and single-sheet Excel files (`.xlsx`, `.xls`, `.xlsm`).
   - Supports searchable vector PDFs and scanned image-based PDFs (via embedded OCR preprocessing and Tesseract integration).

2. **Automated Taxonomy Mapping**:
   - Classifies Balance Sheet, Profit & Loss, and Cash Flow line items into standard Schedule III / Ind AS / IFRS taxonomy using RapidFuzz heuristics.
   - Interactive Data Review & Override Grid allowing auditors to correct amounts, remap lines, or add custom schedules.

3. **30 Financial Ratios**:
   - **Liquidity**: Current Ratio, Quick Ratio, Cash Ratio, Net Working Capital.
   - **Profitability**: Gross Margin, EBITDA Margin, Operating Profit (EBIT) Margin, Net Profit (PAT) Margin, Return on Equity (ROE), Return on Capital Employed (ROCE), Return on Assets (ROA).
   - **Solvency & Leverage**: Debt-Equity Ratio, Total Debt to Total Assets, Interest Coverage Ratio (ICR), Debt Service Coverage Ratio (DSCR), Proprietary Ratio.
   - **Activity & Efficiency**: Inventory Turnover & DSI, Receivables Turnover & DSO, Payables Turnover & DPO, Working Capital Turnover, Total Asset Turnover.
   - **Cash Flow & Key Metrics**: Net Debt, Cash Conversion Cycle (CCC), Operating Cash Flow to Total Debt, Operating Cash Flow to Net Profit (Quality of Earnings).
   - Full formula transparency, previous vs current period figures, benchmarks, and health tags.

4. **Horizontal & Vertical Trend Analysis**:
   - Year-on-Year absolute differences and percentage changes.
   - Vertical Common-Size statements (% of Revenue for P&L, % of Total Assets for Balance Sheet).

5. **Significant Variation & CA Possible Reasons (Default 5% Threshold)**:
   - Configurable sensitivity threshold (slider/spinbox).
   - Non-conclusive, professional **Possible Reasons** strictly based on accounting principles.
   - **Audit Verification Requirements** specifying required documents (GST reconciliations, debtor ageing, external confirmations, fixed asset registers) and **WHY** each document is required as per Standards on Auditing (SA 520 / SA 505 / SA 500).

6. **Potential Risk & Red Flag Matrix**:
   - Identifies cash-profit divergences (positive PAT with negative OCF), excessive leverage, negative working capital, receivables growth outstripping sales, and interest coverage strain.

7. **Multi-Tab Excel & Word Report Generation**:
   - **Excel Report (.xlsx)**: 12 structured worksheets with formatting, freeze panes, formulas, and alert shading.
   - **Word Report (.docx)**: Formal audit diagnostic document with title page, executive summary, tables, variance analysis, and audit checklists.

8. **100% Offline & Private**:
   - Operates completely without internet connectivity or cloud API dependencies.

---

## Project Structure

```
AI_Auditor_V8/
├── main.py                         # Application entry point
├── requirements.txt                # Dependency list
├── build_exe.bat                   # Standalone PyInstaller build script
├── README.md                       # Main documentation
│
├── config/                         # Configuration & accounting taxonomy
│   ├── constants.py
│   └── settings.py
│
├── core/                           # Financial data models & audit trail
│   ├── models.py
│   └── audit_trail.py
│
├── extraction/                     # File ingestion & parsing
│   ├── excel_extractor.py
│   ├── pdf_extractor.py
│   ├── ocr_engine.py
│   └── statement_detector.py
│
├── analysis/                       # Financial calculation & CA rule engine
│   ├── mapper.py
│   ├── ratio_engine.py
│   ├── trend_engine.py
│   ├── variance_engine.py
│   ├── audit_rules.py
│   └── risk_engine.py
│
├── reports/                        # Multi-format report generators
│   ├── excel_generator.py
│   ├── word_generator.py
│   └── chart_generator.py
│
├── gui/                            # Modern PyQt5 Desktop UI
│   ├── main_window.py
│   ├── theme.py
│   ├── widgets/
│   │   ├── metric_card.py
│   │   └── table_view.py
│   └── pages/
│       ├── dashboard_page.py
│       ├── upload_page.py
│       ├── review_page.py
│       ├── ratio_page.py
│       ├── trend_page.py
│       ├── variance_page.py
│       ├── risk_page.py
│       ├── audit_verification_page.py
│       ├── export_page.py
│       ├── settings_page.py
│       └── help_page.py
│
├── samples/                        # Test financial statements
│   ├── generate_samples.py
│   ├── sample_manufacturing_financial_statements.xlsx
│   └── sample_trading_financial_statements.pdf
│
├── user_manual/                    # Comprehensive user guide
│   └── USER_MANUAL.md
│
└── tests/                          # Automated unit test suite
    └── test_all_engines.py
```

---

## Running the Application

### 1. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 2. Launch the Desktop Application
```powershell
python main.py
```

### 3. Run Automated Tests
```powershell
python -m unittest tests/test_all_engines.py
```

---

## Building the Standalone Windows Executable (.exe)

To package the entire application into a standalone executable that runs without requiring Python to be installed:

```powershell
.\build_exe.bat
```

The output will be created inside:
`dist\AI Auditor V8\AI Auditor V8.exe`

---

## Statutory Disclaimer

> **DISCLAIMER & LIMITATIONS:** This analytical report is generated by AI Auditor V8 based strictly upon financial figures uploaded by the user and mathematical / financial calculations. All identified variations, interpretations, possible reasons, and suggested audit verification requirements are designed to assist in professional audit planning, credit appraisal, and financial review. They do NOT constitute a conclusive statutory audit opinion, proof of fraud, or legal finding. Independent verification of physical records, primary vouchers, bank statements, and statutory filings by a qualified Chartered Accountant or auditor is mandatory.
