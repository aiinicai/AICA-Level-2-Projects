# CA Firm Invoice & Practice Automation Pro

**ICAI Artificial Intelligence in CA Practice (AICA) — Level 2 Capstone Project**

---

### Project & Candidate Details
- **Project Title:** CA Firm Invoice & Practice Automation Pro
- **Candidate Name:** CA Pritesh Gajanand Agarwal
- **ICAI Membership No. (MRN):** 150239
- **Batch:** AICA Level 2 — Batch 106 (Vasai Branch)
- **Presentation Group:** B106G5
- **Submission Target Repository:** `aiinicai/AICA-Level-2-Projects`
- **Contributor Repository:** `agarwalpritesh-byte/AICA-Level-2-Projects`

---

## Executive Summary

**CA Firm Invoice & Practice Automation Pro** is an enterprise-grade desktop practice management, billing, compliance, and collection tracking software engineered specifically for Indian Chartered Accountant (CA) firms and tax practitioners.

Built on high-performance **Python 3 / PyQt6**, the software integrates statutory GST invoicing, Form 26AS/AIS TDS reconciliation, bank statement auto-matching, WhatsApp/Email reminder automation, and GSTR-1 direct upload compliance into a unified, secure, local-first workflow.

---

## Key Modules & Capabilities

### 1. Multi-Disciplinary Practice Billing & Invoicing
- **Practice Categories:** Pre-configured service master covering Statutory Audit, Tax Audit, Internal Audit, Direct Tax Litigation, Corporate RoC/MCA Compliance, GST Advisory & Filing, Transfer Pricing, and Project Financing.
- **Dynamic Fee Models:** Fixed fee, milestone-based, hourly billing, and out-of-pocket expense reimbursement.
- **Automated Tax Calculations:** Exact SGST + CGST (intra-state) or IGST (inter-state) computation based on official 2-digit Indian State Codes.
- **Professional PDF Engine:** Native ReportLab integration generating professional CA Tax Invoices with firm letterhead, banking details, QR code, and UPI payment links.

### 2. Statutory GSTR-1 Direct Upload & Compliance
- **Official JSON Schema Export:** Generates GSTR-1 upload-ready JSON (`b2b`, `b2cs`, `hsn`, `docs`) conforming to official GST portal schema for 1-click filing.
- **Multi-Sheet GST Excel Workbook:** Automated generation of GSTR-1 Excel template compatible with the GST Offline Tool.

### 3. Form 26AS / AIS TDS Auto-Linking & Reconciliation
- **Automated TAN/PAN Deduction Matching:** Imports Form 26AS / AIS / TDS summaries (Excel/CSV) downloaded from TRACES / Income Tax Portal.
- **Section-wise Reconciliations:** Auto-reconciles TDS deducted under Sections 194J (Professional fees) and 194C (Contractual fees) against client ledger accounts.
- **1-Click Batch Credit Posting:** Automatically records TDS withholding receipts against unpaid invoices.

### 4. Bank Statement & Payment Notification Reconciliation
- **Smart Credit Matching:** Parses bank statement feeds (Excel/CSV) to match credit transactions against outstanding receivables.
- **Regex Notification Parser:** Auto-extracts Amount, Date, UTR number, and Remitter details from Bank SMS and WhatsApp transaction alerts.
- **Digital Counterfoil / Proofs:** Secure local storage for payment screenshots, NEFT counterfoils, and bank slips.

### 5. Multi-Channel Client Communication
- **WhatsApp Synchronization:** Instant 1-click WhatsApp message dispatch to clients with payment reminders, invoice summaries, and overdue aging details.
- **Automated Email Dispatch:** Secure SMTP SSL/TLS client emailer with customized templates and auto-attached PDF invoices.

### 6. Executive Analytics & Visual Management Dashboard
- **6 Real-time KPI Cards:** Total Invoiced, Realized Collections, TDS Credits, Outstanding Due, Realization Rate %, and Active Client Count.
- **Vector Visualizations (QPainter):**
  - Accounts Receivable Aging Risk Radar (0-30, 31-60, 61-90, 90+ days).
  - Monthly Billed vs Realized Collections Trend.
  - Practice Area Fee Distribution.
  - Collection Status Donut Analysis.
- **Critical Overdue Debtors Table:** Instant "Collect" and "Remind" action buttons for high-risk accounts.

---

## Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **GUI Framework** | Python 3.10+ / PyQt6 | Hardware-accelerated High-DPI desktop interface |
| **Database** | SQLite3 | Local, encrypted-at-rest single-file database engine |
| **PDF Generation** | ReportLab | Programmatic vector PDF invoice and receipt rendering |
| **Excel Engine** | OpenPyXL | High-speed multi-sheet spreadsheet read/write |
| **Networking** | Requests / SMTPLib | GSTIN API verification and SSL/TLS secure email dispatch |
| **Compilation** | PyInstaller & Inno Setup | 1-Click standalone `.exe` builder and Windows setup installer |

---

## Directory Structure

```text
├── README.md                          # Comprehensive project documentation
├── README_HOW_TO_MAKE_APP.md          # Guide to compile standalone .exe
├── ca_firm_invoice_automation_pro.py  # Core application source code (PyQt6)
├── build_exe.bat                      # 1-Click automated Windows .exe compiler
├── build_executable.py                # Cross-platform build script
├── CA_Firm_Invoice_Pro.spec           # PyInstaller build specification
├── installer_setup.iss                # Inno Setup professional installer script
├── app_icon.ico                       # High-resolution application icon
├── app_icon.png                       # Application branding asset
└── sample_data/                       # Sample datasets for live demonstration
    ├── clients.xlsx                   # Sample CA client database
    ├── invoices.xlsx                  # Sample billed invoices
    ├── DayBook.xlsx                   # Sample cash/bank day book
    └── GSTR1_Direct_Upload.json       # Generated GSTR-1 upload schema
```

---

## Installation & Running Instructions

### Method 1: Running from Python Source Code

1. Ensure Python 3.10 or later is installed.
2. Install required packages:
   ```bash
   pip install PyQt6 reportlab openpyxl requests
   ```
3. Launch the application:
   ```bash
   python ca_firm_invoice_automation_pro.py
   ```

### Method 2: 1-Click Standalone Windows Executable (.exe)

1. Double-click **`build_exe.bat`**.
2. PyInstaller compiles the entire application, dependencies, and icons into a single executable located at:
   ```text
   dist\CA_Firm_Invoice_Pro.exe
   ```
3. Run `CA_Firm_Invoice_Pro.exe` directly on any Windows PC without needing Python or external libraries.

---

## Submission Checklist Verification

- [x] **Single Folder Structure:** All project code, build scripts, documentation, and sample data reside in one dedicated folder.
- [x] **Descriptive README.md:** Comprehensive documentation detailing purpose, architecture, candidate credentials, and run instructions.
- [x] **No Internal Git Folder:** Clean project tree with no inner `.git` submodules.
- [x] **File Size Compliant:** All files are strictly optimized within repository limits.
- [x] **Fork & PR Workflow:** Submitted via Fork (`agarwalpritesh-byte/AICA-Level-2-Projects`) to upstream repository (`aiinicai/AICA-Level-2-Projects`).
- [x] **Candidate Credentials Verified:** CA Pritesh Gajanand Agarwal (MRN: 150239, Batch 106 Vasai).
