# AICA Level 2 Capstone Submission Note

**Participant:** CA Vikash Patwari  
**Batch:** 75  
**Project:** The 45-Day Clock  
**Version:** 1.2.0

## Submission Scope

This repository contains the source code and synthetic demonstration material for **The 45-Day Clock**, an offline desktop application for MSME payable review, Section 43B(h) exposure analysis, delayed-payment interest review and audit working-paper generation.

## Data Safety

The repository is intended to contain **synthetic demonstration data only**.

No real client records, credentials, private signing keys, licence-generation secrets or production SQLite databases should be included.

## Demonstration

The application includes a built-in synthetic demonstration dataset and can generate:

- Clause 22 Workbook
- 31 March Action List
- Exclusion Register
- Audit Working Paper PDF
- Structured Complete Audit Pack

The demonstration outputs under `outputs/demo` are intended to show the application's end-to-end workflow.

## Evaluation Route

Recommended:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Then use:

```text
Home → Load Ledger → Load demonstration dataset → Vendors → Assumptions → Results → Exclusion Register → Export
```

## Important

The application is a computation and audit-workpaper aid. Professional judgement and validation of source data, evidence, legal classification and assumptions remain with the engagement team.
