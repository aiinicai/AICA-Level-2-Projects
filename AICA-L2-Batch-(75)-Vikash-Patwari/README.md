# The 45-Day Clock
## AICA Level 2 – Batch 75 Capstone Project

**Participant:** CA Vikash Patwari  
**Project:** The 45-Day Clock  
**Category:** Offline Desktop Compliance & Audit Automation Tool  
**Version:** 1.2.0

---

## Project Overview

**The 45-Day Clock** is an offline desktop application designed to assist Chartered Accountants and audit teams in reviewing MSME payable exposure, Section 43B(h) implications, delayed-payment interest under the MSMED Act, and related audit working-paper requirements.

The application converts purchase-ledger data, payment information and vendor/Udyam evidence into an invoice-level review trail and produces structured audit outputs.

**Privacy by design:** the application runs locally. Purchase ledgers, vendor details, Udyam evidence and computation results are not sent to a cloud service as part of the application workflow.

---

## Problem Addressed

A reliable MSME payable review may require the audit team to reconcile:

- purchase invoices;
- payment dates;
- vendor identity;
- Udyam registration and enterprise class;
- NIC / activity information;
- registration timing;
- credit period / due-date logic;
- year-end outstanding balances;
- exclusions from the applicable coverage gates; and
- delayed-payment interest.

Manual review across spreadsheets and supporting documents can be time-consuming and can make traceability difficult. The 45-Day Clock brings these steps into one controlled workflow.

---

## Desktop Workflow

1. **Home** – configure report identity and create a new analysis.
2. **Load Ledger** – import Excel/CSV, Tally XML or manually pasted rows.
3. **Vendors** – review vendor identity, Udyam/class/activity/evidence and coverage.
4. **Assumptions** – explicitly select and confirm the acceptance-date policy.
5. **Results** – review year-end exposure, delayed-payment interest and action priorities.
6. **Exclusion Register** – review vendors/invoices excluded by the four coverage gates.
7. **Export** – generate individual reports or a structured Complete Audit Pack.

The application blocks or flags important review points rather than silently treating incomplete evidence as final.

---

## Key Features

- Excel / CSV purchase-ledger import
- Tally XML import
- Manual data entry
- Control-total validation
- Financial-year scope validation
- Vendor-name normalisation
- Udyam / enterprise-class review
- NIC / activity review
- Four-gate exclusion framework
- Evidence-strength tracking
- Human confirmation for vendor classification changes
- Acceptance-date policy confirmation
- Section 43B(h) exposure computation
- MSMED delayed-payment interest computation
- 31 March Action List
- Exclusion Register
- Clause 22 Workbook
- Audit Working Paper PDF
- Immutable run hash across outputs
- Source SHA-256 fingerprinting
- Local SQLite persistence
- Structured Complete Audit Pack
- Offline desktop operation

---

## Four Coverage Gates

The Exclusion Register is organised around four review gates:

1. **Enterprise class**
2. **Trader activity**
3. **Udyam registration**
4. **Registration timing**

The tool records the gate that failed, the evidence available, and the amount affected so the review trail remains visible.

---

## Audit Trail and Controls

The generated reports record items such as:

- source filename / source description;
- source SHA-256 fingerprint;
- financial-year scope totals;
- control-total status;
- selected acceptance-date wording;
- rule-pack version;
- run hash;
- evidence exceptions;
- document status; and
- preparer / reviewer fields.

Completed outputs from one analysis carry the same run hash so that the reports can be tied back to the same computation run.

---

## AICA Level 2 Learning Applied

This capstone applies concepts covered in AICA Level 2, including:

- Python application development;
- AI-assisted software development;
- full-stack application design;
- structured-data processing;
- workflow automation;
- validation and exception handling;
- local/offline data architecture; and
- Windows desktop packaging.

AI tools were used as development and research assistants. The statutory computation path itself is deterministic and rule-based; an LLM is not used to invent or alter the final tax calculation.

---

## Project Structure

```text
clock45/
  __init__.py
  classify.py
  demo_data.py
  engine.py
  export.py
  ingest.py
  license.py
  normalise.py
  rules.py
  store.py
  udyam.py

web/
  ... local desktop UI files ...

assets/
  ... application icons/assets ...

samples/
  ... synthetic input samples ...

tests/
  ... deterministic test cases ...

outputs/
  demo/
    ... synthetic demonstration outputs / audit pack ...

app.py
run_demo.py
requirements.txt
clock45.spec
README.md
INSTALL.md
```

Temporary folders, virtual environments, real client databases and private licence-signing material are intentionally excluded from the repository.

---

## Quick Evaluation – Run from Source

### Requirements

- Windows 10 or Windows 11
- Python 3.11 or later

Open Command Prompt in the project folder and run:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

The application should open as a desktop window.

For a quick capstone walkthrough, create/open the synthetic demo analysis and select **Load demonstration dataset**, then follow:

```text
Home → Load Ledger → Vendors → Assumptions → Results → Exclusion Register → Export
```

---

## Console Demonstration

The repository also includes an end-to-end console demonstration:

```bat
python run_demo.py
```

Where applicable, run the rule tests before a demonstration:

```bat
python tests/test_rules.py
```

---

## Synthetic Demonstration Dataset

The repository contains **synthetic demonstration data only**.

Demonstration client:

**Sample Auto Components Pvt Ltd**  
**Financial year:** 2025-26

Validated demonstration run:

- Purchase lines reviewed: **5,578**
- Purchase value: **₹74,36,10,500**
- Section 43B(h) exposure shown by the demo: **₹22,63,000**
- MSMED s.16 interest exposure shown by the demo: **₹7,97,566.60**
- Correctly not disallowed in the demo: **₹13,70,000**

These figures relate only to the built-in synthetic demonstration dataset and are not client advice.

---

## Demonstration Outputs

The application produces four principal deliverables:

1. **Clause 22 Workbook.xlsx**
2. **31 March Action List.xlsx**
3. **Exclusion Register.xlsx**
4. **Working Paper.pdf**

It can also export a structured Complete Audit Pack, organised into:

```text
01_Input
02_Evidence
03_Calculations
04_Results
05_Working_Papers
```

The synthetic demonstration reports are retained under `outputs/demo` for evaluator reference.

---

## Evidence and Human Review

The demonstration intentionally includes some weak / incomplete evidence scenarios so that the application's review controls are visible.

A weak-evidence vendor is not silently treated as final. The working paper remains **DRAFT** while evidence exceptions remain unresolved.

Scanned/image-only Udyam certificates may require manual review where text extraction is unavailable.

---

## Build a Windows Application

The supplied `clock45.spec` is a PyInstaller specification for a Windows onedir build.

Typical build command:

```bat
pyinstaller clock45.spec
```

The source-code capstone can be evaluated without building the installer.

---

## Important Privacy / Repository Note

This repository should contain only synthetic demonstration data.

Do **not** commit:

- real client ledgers;
- real PAN/GSTIN/Udyam documents;
- SQLite production databases;
- `.env` files;
- passwords or API keys;
- private signing keys;
- licence-generation secrets; or
- confidential client evidence.

---

## Professional Use Disclaimer

The 45-Day Clock is a **computation and audit-workpaper aid**, not professional advice.

The engagement team remains responsible for validating source data, vendor evidence, legal classification, acceptance-date assumptions, applicable tax positions, interest assumptions and the conclusions recorded in the audit file.

The rule pack should be reviewed and updated whenever the applicable legal or regulatory position changes.

---

## Capstone Submission

**AICA Level 2 – Batch 75**  
**Participant:** CA Vikash Patwari  
**Project:** The 45-Day Clock
