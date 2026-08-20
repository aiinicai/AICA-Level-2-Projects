# 🏛️ Bank of India — Account Opening Audit & Document Scrutiny System

A specialized, professional **Concurrent Audit & Document Scrutiny Web Application** built with **Python**, **Streamlit**, **Pandas**, and **OpenPyXL**. 

This system is designed for **training and demonstration** of Indian banking concurrent audit workflows, RBI KYC Master Direction compliance, dual officer Maker-Checker controls, and zero-tolerance approval gating for Savings and Current accounts.

---

> [!NOTE]
> ### 🛡️ Synthetic Data & Privacy Assurance
> This application operates strictly on **100% synthetic and dummy data**. No real customer bank account numbers, Aadhaar numbers, PAN cards, OTPs, passwords, or confidential banking records are used, stored, or required.

---

## 🌟 Key Capabilities & Features

### 1. 📄 Document Scrutiny & Verification Engine
- **Saving Account Scrutiny (8 Mandatory Checks):**
  1. *Aadhaar Card Verification* (Masked Aadhaar copy, UIDAI QR verification, demographic match)
  2. *PAN Card / Finacle Verification* (PAN validation against ITD database or valid Form 60)
  3. *CKYC Record Status* (14-digit Central KYC Registry search/upload)
  4. *Customer Photograph* (Recent passport-size photo affixed and cross-signed)
  5. *Officer Signature with PF Number* (OSV stamp with verifying official's 6-digit Employee/PF code)
  6. *Customer Profile Sheet (CPS)* (Occupation, income, source of funds, AML risk grading)
  7. *AOF Dual Officer Verification* (Account Opening Form dual check — Maker & Checker signatures)
  8. *Customer Signature / Thumb Impression* (Specimen signature card uploaded to Finacle)
- **Current Account Scrutiny (11 Mandatory Checks):**
  1. *Certificate of Incorporation / Partnership Deed / Registration Certificate*
  2. *PAN of Business Entity*
  3. *GSTIN Registration / Udhyam Certificate / Trade License* (RBI 2-independent document rule)
  4. *Beneficial Ownership (BO) Declaration* (>10%/25% threshold under PMLA)
  5. *Board Resolution / Partner Mandate / Power of Attorney*
  6. *KYC of all Authorized Signatories, Directors & Partners*
  7. *CKYC Search & Download for Entity & Promoters*
  8. *Pre-Opening Site / Business Inspection Report* (Physical visit with geo-tagged photo)
  9. *Credit Facility Undertaking / NOC from Existing Bankers* (RBI circular compliance)
  10. *Customer Profile Sheet & AML Risk Profiling* (Business turnover & transaction limits)
  11. *Dual Officer Verification & PF Signatures* (Branch Maker-Checker sign-off)

### 2. 🚨 Automated Discrepancy Identification & Rectification Workflow
- Instantly detects any incomplete, missing, or unverified documents.
- Supports 5 standardized audit states:
  `Discrepancy Found` ➡️ `Rectification Pending` ➡️ `Rectified` ➡️ `Re-check Completed` ➡️ `Passed`
- Allows auditors and branch officials to record granular scrutiny observations and rectification action notes per checklist item.

### 3. 🛡️ Zero-Tolerance Account Opening Approval Gate
- **Approval Blocked:** If even *one* mandatory checklist item has an active discrepancy or pending check, final approval is strictly blocked with a warning alert banner (`🚫 APPROVAL BLOCKED – DOCUMENTS/CHECKS PENDING`).
- **Ready for Approval:** When all 8 (Saving) or 11 (Current) checks achieve 100% compliance, the system unlocks the green banner (`🟢 READY FOR ACCOUNT OPENING APPROVAL`).
- **Official Sign-off:** The concurrent auditor enters their PF Employee Code and remarks to stamp the account with `✅ APPROVED – OFFICER MAY PROCEED WITH ACCOUNT OPENING`.

### 4. 📈 Audit Summary Dashboard & Real-Time Analytics
- Executive KPI scorecard: Total Accounts Scrutinized, Savings vs. Current breakdown, Total Discrepancies Logged, Pending vs. Rectified count, Ready for Approval, and Fully Approved accounts.
- Interactive status breakdown bar charts and common deficiency category visualizations.
- Searchable master audit register with filters by account type, audit status, and AML risk level.

### 5. 📥 Professional OpenPyXL Multi-Sheet Excel Export
- Generates a 4-sheet formatted `.xlsx` workbook:
  - **Sheet 1 — Executive Summary:** Executive scorecard, audit KPIs, and category deficiency breakdown.
  - **Sheet 2 — Master Account Register:** Complete account audit ledger with compliance rates and approval states.
  - **Sheet 3 — Checklist & Discrepancy Log:** Itemized checklist observations and branch remediation notes.
  - **Sheet 4 — Blocked & High-Risk Accounts:** Escalation register for non-compliant cases and High AML risk accounts.
- Styled with Bank of India corporate palette (Dark Navy `#0B2545`, Orange `#E65100`), cell borders, and status highlights.

### 6. 📖 Operational Guide & RBI SOP Reference
- In-app standard operating procedures for branch auditors.
- Explanations of RBI KYC Master Directions and statutory norms.
- Comprehensive Banking Glossary explaining terms like *AOF*, *CKYCR*, *OSV*, *CPS*, *PF Code*, and *Maker-Checker controls*.

---

## 📁 Project Structure

```
BOI-Audit-Project/
├── app.py                      # Main Streamlit web application entrypoint
├── checklists.py               # 8 Saving & 11 Current Account audit check definitions
├── data_manager.py             # Synthetic datasets, metrics calculation, and state management
├── excel_exporter.py           # Multi-sheet OpenPyXL Excel audit report generator
├── views/
│   ├── __init__.py
│   ├── scrutiny_view.py        # Document Scrutiny, Discrepancy Tracking & Approval Gate UI
│   ├── dashboard_view.py       # High-level Audit Summary Dashboard with KPI metrics & charts
│   ├── export_view.py          # Interactive Excel audit report exporter and data preview
│   └── guide_view.py           # Operational Guide, Checklist Reference & Banking SOP
├── tests/
│   └── test_audit_engine.py    # Unit test suite for audit logic, approval gates, and Excel output
├── requirements.txt            # Python dependencies (streamlit, pandas, openpyxl)
└── README.md                   # Beginner-friendly guide and documentation
```

---

## 🚀 Beginner's Step-by-Step Setup & Run Guide

If you are a complete beginner in Python, follow these simple steps to run the application on your computer:

### Step 1: Open Terminal / PowerShell
1. On Windows, press the `Windows Key + R`, type `powershell` or `cmd`, and press **Enter**.
2. Navigate to this project folder:
   ```powershell
   cd "C:\Users\akmeh\OneDrive\Desktop\BOI-Audit-Project"
   ```

### Step 2: Install Dependencies
Run the following command to install the required libraries (`streamlit`, `pandas`, `openpyxl`):
```powershell
python -m pip install -r requirements.txt
```

### Step 3: Run the Streamlit Application
Start the application by running:
```powershell
streamlit run app.py
```

### Step 4: Open in Your Web Browser
Streamlit will automatically launch your default web browser and open the application at:
```
http://localhost:8501
```
*(If it doesn't open automatically, simply copy and paste the URL into Google Chrome, Microsoft Edge, or Mozilla Firefox).*

To stop the application at any time, go back to your terminal window and press `Ctrl + C`.

---

## 🧪 Running Automated Unit Tests

To verify that the audit compliance calculations, approval gating, and Excel generation are working perfectly, run:

```powershell
python tests/test_audit_engine.py
```

You should see an output showing all 7 unit tests passing:
```
.......
----------------------------------------------------------------------
Ran 7 tests in 0.234s

OK
```

---

## 🎯 Demonstration Scenarios for Presentations / Training

The system comes pre-loaded with realistic synthetic demo accounts to illustrate every audit stage:

| Account Ref ID | Dummy Customer / Entity Name | Account Type | Initial State | Demonstration Purpose |
|---|---|---|---|---|
| `SB-BOI-2026-001` | **Rahul Ramesh Sharma** | Saving Account (8 Checks) | **✅ Approved** | Demonstrates a 100% compliant Savings Bank account with official auditor PF stamp. |
| `SB-BOI-2026-002` | **Sunita Devi Patel** | Saving Account (8 Checks) | **🚫 Approval Blocked** | Demonstrates active discrepancies (CKYC pending, Officer PF missing). Change status to `Passed` to see approval unlock. |
| `CA-BOI-2026-101` | **Apex Star Logistics Pvt Ltd** | Current Account (11 Checks) | **✅ Approved** | Demonstrates a fully verified corporate account with Board Resolution, MCA verification, and Site Inspection. |
| `CA-BOI-2026-102` | **GreenLeaf Agro Traders LLP** | Current Account (11 Checks) | **🚫 Approval Blocked** | Demonstrates missing Pre-Opening Site Inspection and non-standard Credit Facility undertaking. |
| `SB-BOI-2026-003` | **Priya Ananya Deshmukh** | Saving Account (8 Checks) | **⏳ Rectification Pending** | Demonstrates remediated items (`Rectified` and `Re-check Completed` stages). |
| `CA-BOI-2026-103` | **Nexus Cyber Solutions Pvt Ltd** | Current Account (11 Checks) | **❌ Discrepancy Found** | Demonstrates RBI 2-document rule violation (only GSTIN submitted; 2nd proof missing). |

---

## 🏛️ Built with Bank of India Visual Identity
- **Primary Navy:** `#0B2545`
- **Secondary Blue:** `#133E68`
- **Star Orange:** `#E65100`
- **Light Slate:** `#F8FAFC`

---

## 📜 License & Compliance Notice
This project is built for educational, training, and demonstration purposes. It demonstrates banking audit compliance systems using only synthetic data.
