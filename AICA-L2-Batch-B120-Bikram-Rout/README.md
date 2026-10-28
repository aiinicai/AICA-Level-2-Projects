# BRS Tool - Enterprise Bank Reconciliation System

**BRS Tool** is a high-performance, full-stack enterprise bank reconciliation application engineered to reconcile transactions across 300+ bank accounts, multiple corporate entities, multiple banks, and multiple currencies.

Built with a **FastAPI (Python 3.14)** backend, **SQLite WAL** persistence, **exact decimal financial math**, and a **light modern UI** styled in navy blue, white, teal, and amber.

---

## 1. Key Business Capabilities

- **Document Processing**: Ingests Oracle General Ledger exports and Bank Statements from:
  - Excel (`.xlsx`, `.xls`)
  - Delimited text (`.csv`, `.tsv`, `.txt`)
  - SWIFT MT940 (`.sta`, `.txt`)
  - Open Financial Exchange (`.ofx`, `.qfx`)
  - ISO 20022 XML (`CAMT.053`)
  - Text-based and password-protected PDF statements
  - Scanned PDF & Image files (`.png`, `.jpg`, `.tiff`) via OCR adapter
- **Exact Decimal Arithmetic**: Employs Python `Decimal` with rounding to eliminate IEEE 754 floating-point errors.
- **Cash Perspective Normalization**:
  - Inflows (Deposits, Receipts) = Positive signed cash movement (`+`)
  - Outflows (Disbursements, Withdrawals, Fees) = Negative signed cash movement (`-`)
  - Automatically accounts for Oracle GL Debit/Credit convention (Debit Cash = `+`, Credit Cash = `-`) versus Bank Statement convention (Credit = `+`, Debit = `-`).
- **8-Tier Reconciliation Matching Engine**:
  1. *Tier 1*: Exact unique reference and exact amount
  2. *Tier 2*: Exact cheque number / payment ID / journal batch and exact amount
  3. *Tier 3*: Exact amount with date tolerance (up to 7 days) and supporting reference evidence
  4. *Tier 4*: Normalized reference / description with exact amount and date tolerance
  5. *Tier 5*: One-to-many match (1 ledger line = multiple bank lines with exact sum)
  6. *Tier 6*: Many-to-one match (multiple ledger lines = 1 bank line with exact sum)
  7. *Tier 7*: Controlled many-to-many match (bounded up to 3 items per side with exact sum)
  8. *Tier 8*: Fuzzy token similarity routed to **Suggested Matches** requiring explicit human confirmation
- **Partial Allocations**: Split and match partial amounts while tracking remaining balances and enforcing overflow protection.
- **Section 15 Acceptance Test Scenario**:
  - Ledger Closing Balance: **100,000.00**
  - Bank Closing Balance: **108,500.00**
  - Ledger-Only Outstanding Payment: **-10,000.00**
  - Ledger-Only Deposit in Transit: **+2,000.00**
  - Bank-Only Charge: **-500.00**
  - Adjusted Bank Balance: `108,500 - 10,000 + 2,000 = 100,500.00`
  - Adjusted Ledger Balance: `100,000 - 500 = 99,500.00`
  - Residual Variance: **1,000.00** (Flagged as UNRECONCILED; no invented adjustments)
- **Period Management & Governance**:
  - Workflow: `Draft` &rarr; `In Progress` &rarr; `Submitted` &rarr; `Reviewed` &rarr; `Approved` &rarr; `Locked`
  - **Segregation of Duties**: Preparers cannot approve their own accounts. Non-zero residual accounts cannot be approved.
  - **Cross-Period Rollover**: Uncleared transactions carry forward to the next period without duplicating records.
  - **Locked-Period Immutability**: Any mutating action on locked periods is blocked unless reopened with a mandatory audit reason.
- **Tamper-Evident Audit Trail**: Every upload, match, unmatch, status change, and unlock is logged with user, timestamp, before/after values, and reason.
- **Formula Injection Sanitization**: All spreadsheet exports escape initial characters (`=`, `+`, `-`, `@`) to prevent CSV/Excel injection attacks.

---

## 2. Quick Start & Execution

### Running the Application

1. Open PowerShell / Command Prompt in the project folder:
   ```powershell
   python main.py
   ```
   Or double-click:
   ```cmd
   Start_BRS_Tool.bat
   ```
2. The server binds to `0.0.0.0:8000`:
   - Local access: `http://localhost:8000`
   - LAN access (same Wi-Fi): `http://<your-lan-ip>:8000` (automatically detected and displayed on console)
3. The default web browser opens automatically.

---

## 3. Running Automated Tests

A comprehensive test suite covering all 17 requirements (Section 15 acceptance criteria, exact decimal arithmetic, grouped matching, partial allocation, carry forward, CAMT.053 XML, segregation of duties, locked period immutability, formula injection protection, etc.) is included:

```powershell
python -m unittest tests/test_brs.py
```

Expected output:
```
----------------------------------------------------------------------
Ran 17 tests in ~2.0s

OK
```

---

## 4. Architecture & Directory Layout

```
BRS Tool/
├── backend/
│   ├── api.py             # FastAPI REST endpoints & workflow handlers
│   ├── database.py        # SQLite database connection, schema & audit logging
│   ├── reconciliation.py  # BRS math, 8-tier matching engine & partial allocations
│   ├── importers.py       # Excel, CSV, TSV, MT940, OFX, CAMT.053 XML & PDF parsers
│   ├── exporters.py       # Multi-sheet Excel & formatted PDF generator
│   └── seed_data.py       # Seed data including Section 15 acceptance scenario
├── frontend/
│   └── static/
│       ├── index.html     # Responsive layout, sidebar navigation & global header
│       └── js/app.js      # Single-page application controller, state & Chart.js
├── tests/
│   └── test_brs.py        # 17 automated acceptance and unit tests
├── data/
│   └── brs.db             # Persistent SQLite database with WAL mode
├── main.py                # Server entry point with LAN IP auto-detection
├── Start_BRS_Tool.bat     # Windows launcher script
├── .env.example           # Environment template
└── README.md              # Project documentation
```

---

## 5. User Roles & Security

Switch roles using the top-left switcher in the UI:
- **Administrator**: Full privileges, master data configuration, system unlocks.
- **Preparer**: Uploads files, runs matching, marks items, submits periods.
- **Reviewer**: Inspects statements, reviews validations and variances.
- **Approver**: Signs off on fully reconciled periods (residual = 0.00). Cannot approve accounts they prepared.
- **Auditor**: Read-only oversight across all companies, accounts, reports, and immutable audit logs.

---

## 6. Troubleshooting

| Problem | Fix |
|---|---|
| Window opens and closes immediately | Start with `Start_BRS_Tool.bat`. It now stays open and shows the error. |
| "Python was not found" | Install Python 3.10+ from python.org and tick **Add python.exe to PATH**. |
| "A required Python package is missing" | Run `python -m pip install -r requirements.txt` in this folder. |
| "Port 8000 is already in use" | An older BRS Tool (or `BRS_Tool.exe`) is still running. The app now uses the next free port automatically (see the console for the URL). To stop the old one, end `BRS_Tool.exe` / `python.exe` in Task Manager. |
| Old dashboard error still appears | You are running an old `BRS_Tool.exe`. Run from source (`Start_BRS_Tool.bat` does this automatically when `main.py` is present), or rebuild with `python build_exe.py`. Press Ctrl+F5 in the browser. |
| Charts / styling missing | The page loads Tailwind, Chart.js and icons from CDNs, so the browser needs internet access. |
