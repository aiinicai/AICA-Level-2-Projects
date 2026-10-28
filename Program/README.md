# Ind AS 116 Lease Accounting Tool (Offline Desktop Application)

An institutional-grade, **100% offline desktop application** designed for Indian Chartered Accountants, Corporate Controllers, and Financial Auditors to automate lease accounting compliance under **Indian Accounting Standard 116 (Ind AS 116 - Leases)**.

---

## 🌟 Key Features

1. **Complete Offline Privacy & Security**:
   - Zero cloud API calls, zero external data transmissions.
   - All uploaded PDF contracts, OCR images, extracted text, amortization math, and exported reports stay strictly on the user's local workstation.
2. **Dual PDF Ingestion (Digital & Scanned)**:
   - Detects whether PDF contracts are digital vector text or scanned images.
   - Native PyMuPDF rendering converts pages to images directly on Windows without requiring external Poppler binaries.
   - High-contrast image enhancement with local Tesseract OCR integration.
   - Page-level citation preserves contract audit traceability.
3. **Local AI & NLP Information Extraction**:
   - High-precision offline heuristic extraction engine extracts 20+ lease parameters (Lessor, Lessee, Demised Asset, Commencement Date, Lease Term, Fixed Rent, Frequency, Advance/Arrears timing, Escalation clauses, Deposits, Incentives, Initial Direct Costs, Restoration Provisions, Renewal/Termination Options, Purchase Options, and CAM charges).
   - Every field includes confidence scoring and source page numbers.
   - Unclear or missing fields are automatically flagged with `Requires Review`.
   - Optional local Ollama integration (`localhost:11434`) allows connecting offline LLMs (Mistral, LLaMA 3, Phi-3).
4. **Ind AS 116 Accounting Classification Engine**:
   - Evaluates the 3 core criteria for a lease under Ind AS 116.9 (Identified Asset, Substantially All Economic Benefits, Right to Direct Use).
   - Automatic evaluation of the Short-Term Lease Exemption (term $\le$ 12 months with no purchase option) under Ind AS 116.5(a).
   - Automatic evaluation of the Low-Value Asset Exemption under Ind AS 116.5(b).
   - Practical expedient support (Ind AS 116.15) to combine lease and non-lease components (e.g., CAM).
   - Avoids legacy "operating vs finance lease" confusion for lessees by providing a clear on-balance sheet conclusion.
5. **Actuarial Amortisation & Financial Engine**:
   - Calculates present value of lease liabilities and initial Right-of-Use (ROU) assets including initial direct costs, incentives, and restoration provisions (Ind AS 37).
   - Generates period-by-period schedules supporting Monthly, Quarterly, Half-Yearly, and Annual frequencies.
   - Supports both In Advance (annuity due) and In Arrears (ordinary annuity) timing conventions.
   - Handles multi-year escalation structures, rent-free fit-out holidays, uneven cash flows, and terminal options.
   - Computes Current vs Non-Current lease liability balance sheet splits.
6. **Double-Entry Journal Vouchers**:
   - Chronological accounting vouchers with debits, credits, account heads, and standard narrations.
   - Initial recognition entry at commencement date.
   - Periodic lease payments (principal reduction + interest expense).
   - Periodic straight-line ROU asset depreciation.
   - Straight-line rent entries for exempt leases.
   - Final period settlement and gross block derecognition.
7. **Offline Guidance Library (RAG Search)**:
   - Pre-indexes ICAI Educational Material, Ind AS 116 Standards, PwC Manuals, and KPMG Technical Documents located in `..\Knowlege`.
   - Fuzzy token and phrase matching provides instant citation and paragraph references without internet connectivity.
8. **Client-Ready Deliverables**:
   - **`Lease_Accounting_Schedule.xlsx`**: An audit-ready 9-tab Excel workbook formatted with corporate styles, number formatting, and formula totals:
     1. *Input Summary*
     2. *Extracted Agreement Data*
     3. *Ind AS 116 Analysis*
     4. *Lease Liability Schedule*
     5. *ROU Asset Schedule*
     6. *Journal Entries*
     7. *Fin Statement Presentation*
     8. *Disclosures*
     9. *Audit Review Points*
   - **`Lease_Summary.docx`**: A comprehensive Word memorandum including executive summary, contract terms, technical classification, journal vouchers, balance sheet/P&L presentation, and a Chartered Accountant sign-off block.

---

## 📁 Project Folder Structure

```
IND AS 116/
├── Knowlege/                          # Local Guidance PDFs (ICAI, KPMG, PwC)
│   ├── Ind AS 116.pdf
│   ├── KPMG Ind AS 116.pdf
│   └── PWC Ind AS 116.pdf
└── Program/                           # Application Root
    ├── app.py                         # Streamlit Web Application
    ├── requirements.txt               # Python package dependencies
    ├── run_app.bat                    # 1-Click Windows Launcher
    ├── README.md                      # Documentation & Windows Guide
    ├── modules/                       # Modular Application Engine
    │   ├── __init__.py
    │   ├── config.py                  # Global settings, paths & defaults
    │   ├── pdf_processor.py           # Native MuPDF & Tesseract OCR engine
    │   ├── extractor.py               # Local AI & NLP heuristic extractor
    │   ├── ind_as_116_engine.py       # Ind AS 116 classification & exemption rules
    │   ├── financial_engine.py        # PV, DCF, amortisation & ROU depreciation
    │   ├── journal_entries.py         # Period-wise debit/credit journal vouchers
    │   ├── guidance_rag.py            # Local PDF/DOCX guidance search engine
    │   ├── quality_checks.py          # CA reviewer checklist & accounting checks
    │   └── reporting_engine.py        # Excel (9 tabs) & Word report generator
    ├── sample_data/                   # Test Contracts
    │   ├── sample_commercial_lease.txt
    │   ├── sample_commercial_lease.pdf
    │   └── create_sample_pdf.py
    └── tests/                         # Automated Integration Tests
        └── test_pipeline.py
```

---

## 🛠️ Windows Installation & Setup Guide

### 1. Prerequisites
- **Windows 10 or Windows 11 (64-bit)**
- **Python 3.11, 3.12, or 3.13** (Download from [python.org](https://www.python.org/downloads/windows/) - check *"Add Python to PATH"* during installation).

### 2. Install Python Dependencies
Open PowerShell or Command Prompt in the `Program` directory:
```powershell
pip install -r requirements.txt
```

### 3. Tesseract OCR Installation (For Scanned PDFs)
The tool extracts digital text directly. For scanned agreements, Tesseract OCR is recommended:
1. Download the Windows 64-bit installer from the UB-Mannheim repository:
   - [Tesseract Windows 64-bit Installer](https://github.com/UB-Mannheim/tesseract/wiki)
2. Run the installer and install to the default location:
   `C:\Program Files\Tesseract-OCR\`
3. The application will automatically detect Tesseract at that path. If installed to a custom directory, enter the path in the application sidebar under **Configure Tesseract Path**.

*(Note: Poppler is NOT required. The application uses PyMuPDF's native rendering engine to convert PDF pages to images in memory).*

---

## 🚀 Running the Application

### Method 1: 1-Click Batch File
Double-click `run_app.bat` in the `Program` folder.

### Method 2: Command Line
```powershell
streamlit run app.py
```
The application will launch and open in your default browser at `http://localhost:8501`.

---

## 🧪 Running Automated Tests

Run the full end-to-end unit and integration test suite:
```powershell
python tests/test_pipeline.py
```
This tests:
- PDF processing & page mapping
- NLP heuristic term extraction
- Ind AS 116 lease definition and exemption rules
- Financial DCF, amortisation, and ROU depreciation
- Journal entry balancing ($\sum \text{Debits} = \sum \text{Credits}$)
- Guidance library indexing and offline search
- Excel 9-tab output generation
- Word report (`Lease_Summary.docx`) generation

---

## 📑 Accounting & Reviewer Checklist

Before finalizing reports, review the interactive checklist in Tab 6:
- [x] **CHK-01 (Contract Inception)**: Verified that asset is physically distinct and no substantive supplier substitution rights exist (Ind AS 116.B13-B20).
- [x] **CHK-02 (Lease Term)**: Renewal and termination options evaluated for reasonable certainty of exercise (Ind AS 116.18-21).
- [x] **CHK-03 (Discount Rate)**: Incremental borrowing rate (IBR) substantiated by entity treasury curves for similar term and security (Ind AS 116.26).
- [x] **CHK-04 (ROU Asset Inclusions)**: Initial direct costs, lease incentives received, and restoration provisions (Ind AS 37) correctly adjusted in ROU asset (Ind AS 116.24).
- [x] **CHK-05 (Disclosures)**: Undiscounted maturity analysis and current/non-current balance sheet splits prepared (Ind AS 116.51-60).

---

## ⚖️ Statutory Notice
> **DISCLAIMER**: This software produces automated calculation schedules and draft accounting memoranda to assist qualified finance professionals and auditors. It does not replace professional auditing judgment, technical review by a qualified Chartered Accountant, or formal management assessment of contracts. All inputs and conclusions must be validated against primary executed agreements.
