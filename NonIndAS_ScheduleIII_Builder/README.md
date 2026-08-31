# Non Ind AS Schedule III Financial Statements Builder

> **A local Windows desktop application** to import a Tally Trial Balance and prepare **draft standalone financial statements** compliant with **Schedule III of the Companies Act, 2013 (Division I – Non Ind AS)**.

---

## 📋 What This Application Does

- **Import** Tally Trial Balance from Excel (`.xlsx`/`.xls`), CSV (`.csv`), or Tally XML (`.xml`)
- **Auto-map** each ledger to Schedule III Balance Sheet / P&L line items
- **Generate** draft financial statements:
  - Balance Sheet
  - Statement of Profit & Loss
  - Cash Flow Statement (Indirect Method)
  - **11 Mandatory Schedule III Financial Ratios**
- **Export** final reports to Excel (`.xlsx`), Word (`.docx`), and PDF (`.pdf`)
- **Audit & Exceptions** checklist with Balance Sheet equation verification

> ⚠️ This is a preparation and review tool only — not a substitute for professional CA judgement, audit, or statutory sign-off.

---

## 🗂️ Project Structure

```
NonIndAS_ScheduleIII_Builder/
│
├── src/                        ← Python backend
│   ├── app.py                  ← Flask REST API + server launcher
│   ├── db.py                   ← SQLite database schema & queries
│   ├── import_engine.py        ← Tally file parsers (Excel/CSV/XML)
│   ├── mapping_engine.py       ← Auto-mapping engine (Tally → Schedule III)
│   ├── reconciliation_engine.py← Balance sheet checks & audit checklist
│   ├── statement_generator.py  ← Financial statement generators
│   └── export_engine.py        ← Excel / Word / PDF export engine
│
├── static/                     ← Frontend (HTML + CSS + JavaScript)
│   ├── index.html              ← Single-page application UI
│   ├── styles.css              ← All visual styling
│   └── app.js                  ← Browser-side logic & API calls
│
├── tests/                      ← Automated unit tests
│   ├── test_reconciliation.py  ← Reconciliation & BS equation tests (4/4 pass)
│   └── test_notes.py           ← Notes data tests
│
├── templates/                  ← Flask HTML templates (if any)
├── exports/                    ← Generated report outputs go here
│
├── requirements.txt            ← Python package dependencies
├── run.bat                     ← ✅ Double-click to launch the application
└── build_exe.py                ← PyInstaller standalone EXE builder
```

---

## 🚀 How to Run

### Prerequisites
- **Python 3.10 or higher** must be installed  
  Download from: https://www.python.org/downloads/

### Step 1 — Install Dependencies
Open a Command Prompt in this folder and run:
```
pip install -r requirements.txt
```

### Step 2 — Launch the Application
Simply **double-click `run.bat`** — it will:
1. Start the local Flask web server
2. Automatically open your browser at `http://127.0.0.1:5000`

### Step 3 — Use the Guided Wizard
Follow the 5-step workflow bar at the top:

| Step | What To Do |
|------|-----------|
| **1. Setup** | Fill in entity name, financial year, rounding unit, CIN |
| **2. Import TB** | Upload your Tally Trial Balance file, or load demo data |
| **3. Map Ledgers** | Review auto-mapped Schedule III classifications |
| **4. Audit & Exceptions** | Check Balance Sheet equation and mandatory disclosures |
| **5. Financial Statements** | View and export Balance Sheet, P&L, Cash Flow, Ratios |

---

## 📦 Supported Import Formats

| Format | Details |
|--------|---------|
| `.xlsx` / `.xls` | Tally Excel export (standard columnar format) |
| `.csv` | Comma-separated Trial Balance |
| `.xml` | Tally XML data export |

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Database | SQLite (embedded, no installation needed) |
| Frontend | HTML5, Vanilla CSS, Vanilla JavaScript |
| Excel Export | openpyxl |
| Word Export | python-docx |
| PDF Export | reportlab |
| Launcher | Windows Batch Script |

---

## 📊 Financial Statements Generated

1. **Balance Sheet** — Per Schedule III Division I format
2. **Statement of Profit & Loss** — With current and comparative year
3. **Cash Flow Statement** — Indirect method
4. **Mandatory Ratios** — All 11 ratios required by MCA notification (Mar 2022)

---

## ⚖️ Disclaimer

This tool is built for **internal preparation and review purposes only**. The financial statements generated must be reviewed, adjusted, and signed off by a **qualified Chartered Accountant** before filing or publication. The developers accept no liability for statutory compliance.

---

## 👥 Developed By

AICA Level 2 Group Project  
*Companies Act 2013 | Schedule III | Non Ind AS Division I*
