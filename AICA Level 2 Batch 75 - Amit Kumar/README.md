# FS Builder Lite v0.2

**FS Builder Lite v0.2** is a standalone, office-usable IGAAP financial statement preparation application designed for Indian Chartered Accountants (ICAI AI Level 2 project & CA internal office use).

It prepares first-draft Schedule III Division I financial statements (Balance Sheet, Profit & Loss, Notes to Accounts, Ratio Analysis, Validation Matrix) directly from trial balance and supporting Excel schedules.

---

## Key Features

1. **Localhost & Security First**:
   - 100% standalone localhost execution.
   - Zero network egress & zero external AI API dependencies.
   - All accounting logic, sign conventions, mappings, notes, ratios, and validations are computed deterministically in Python.

2. **Schedule III Division I Financial Statements**:
   - Standard IGAAP Balance Sheet (Shareholders' Funds, Non-current Liabilities, Current Liabilities, Non-current Assets, Current Assets).
   - Statement of Profit & Loss (Revenue, Other Income, Expenses, PBT, Tax, PAT).
   - Instant Balance Sheet Tally Verification (`Total Assets = Equity & Liabilities`).

3. **Rule-Based Mapping Engine**:
   - Auto-suggests Schedule III line items based on keyword/pattern matching.
   - User overrides for any ledger.
   - Automatically saves custom mapping rules into SQLite database (`app.db`) for future uploads.

4. **20 Draft Notes & Rule-Based Footnote Engine**:
   - Pre-populates 20 standard Schedule III draft notes.
   - Trigger-based Footnotes:
     - **Delayed CWIP**: Triggers note when CWIP projects exceed 2 years.
     - **Doubtful Receivables**: Triggers recoverability note for receivables > 6 months.
     - **MSME Disclosures**: Triggers MSMED interest & disclosure note when MSME vendors exist.
     - **Related Party Disclosures**: Triggers AS-18 RPT disclosure note.
     - **Borrowing Defaults**: Triggers default disclosure note.
     - **Contingent Liabilities**: Triggers litigation claims note.
   - Editable text area with **Reset to Suggested** option.

5. **Schedule III Ratio Analysis**:
   - 8 key financial ratios (Current Ratio, Debt Equity, Net Profit %, EBITDA Margin %, Return on Equity %, Receivable Days, Payable Days, Inventory Days).
   - CY vs PY comparison and visual bar charts.
   - Rule-based audit interpretations for movement.

6. **20 Automated Audit Validation Checks**:
   - Categorized as `Passed`, `Warning`, or `Critical`.
   - Checks balance sheet tally, unmapped ledgers, missing note numbers, negative cash balances, borrowing defaults, CWIP delays, etc.

7. **Formula-Linked Excel & PDF Exporters**:
   - **Excel Workbook**: 16 formatted worksheets (`01_Client_Info` through `16_Management_Queries`) with `=SUMIFS(...)` dynamic formula linking from Balance Sheet & P&L to the Mapping sheet.
   - **PDF Review Pack**: Print-ready PDF report with cover page, financial tables, ratio analysis, validation summary, management queries, and mandatory legal disclaimer.

---

## Directory Structure

```
fs-builder-lite/
├── backend/
│   ├── main.py                   # FastAPI server & API endpoints
│   ├── database.py               # SQLite connection setup
│   ├── models.py                 # SQLAlchemy ORM models
│   ├── schemas.py                # Pydantic schemas
│   ├── services/
│   │   ├── excel_parser.py       # Parsers for 7 schedule Excel files & sample data
│   │   ├── mapping_engine.py     # Rule-based auto-mapping engine
│   │   ├── fs_generator.py       # Schedule III Balance Sheet & P&L generator
│   │   ├── notes_engine.py       # Draft notes & rule-based footnote engine
│   │   ├── ratio_engine.py       # Financial ratio analysis engine
│   │   ├── validation_engine.py  # 20 automated validation checks
│   │   └── export_service.py     # openpyxl formula-linked Excel & ReportLab PDF exporters
│   ├── uploads/                  # Uploaded client Excel files
│   ├── exports/                  # Exported .xlsx and .pdf files
│   ├── sample_data/              # Sample Excel templates & data
│   └── app.db                    # SQLite Database
├── frontend/
│   ├── src/
│   │   ├── components/           # Header and Sidebar navigation components
│   │   ├── pages/                # 11 Main Screens
│   │   ├── services/             # API client service
│   │   └── types/                # TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

---

## How to Run

### 1. Start the Backend Server (Python FastAPI)

Navigate to the `backend` directory and run:

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```
Backend API will be live at: `http://localhost:8000`

### 2. Start the Frontend Application (React + Vite)

Navigate to the `frontend` directory and run:

```bash
cd frontend
npm run dev
```
Frontend web application will be live at: `http://localhost:5173`

---

## Verification & Testing Workflow

1. Open `http://localhost:5173`.
2. Click **"Use Pre-Packaged Sample Data"** on the Upload Center or Dashboard to populate demo trial balance and 6 supporting schedules.
3. Go to **Ledger Mapping** to view auto-classified ledgers and modify any line item.
4. Open **Financial Statements** to verify Schedule III Division I Balance Sheet & Profit and Loss with Balance Sheet Tally status.
5. Open **Notes to Accounts** to review 20 draft notes and triggered rule footnotes.
6. Open **Ratio Analysis** & **Validation Checks** for audit health monitoring.
7. Click **Export Reports** to download the formula-linked `.xlsx` workbook and `.pdf` review pack!
