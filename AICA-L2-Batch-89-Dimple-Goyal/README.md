# FinRecon India – Receivables & Reconciliation Platform

**AICA Level 2 – Capstone Project**  
**Batch:** 89  
**Participant:** Dimple Goyal  
**Project Folder:** `AICA-L2-Batch-89-Dimple-Goyal`

---

## 1. Project Overview

**FinRecon India** is a web-based receivables management and reconciliation platform designed for Indian businesses and finance teams.

The application brings customer master data, sales invoices, bank/payment information, TDS/Form 26AS/AIS information and GST/GSTR-1 information into a centralized platform for analysis, reconciliation, ageing and exception review.

The objective is to reduce manual spreadsheet-based reconciliation and provide users with a structured view of receivables, payments, statutory reconciliation and accounting-related exceptions.

The application is developed as an AICA Level 2 Capstone Project based on the practical application of concepts covered during the course.

---

## 2. Problem Statement

Businesses, particularly small and medium-sized businesses, may maintain financial and statutory information across multiple files and systems. This can make it difficult to obtain a consolidated view of receivables and reconcile different datasets.

Key challenges include:

- Mapping customer payments against sales invoices.
- Identifying outstanding customer balances.
- Preparing customer-wise and invoice-wise receivables ageing.
- Reconciling bank receipts with invoices.
- Comparing expected TDS with TDS information reported in Form 26AS/AIS.
- Comparing books/invoices with GSTR-1 debtor-wise information.
- Identifying unmatched and discrepant transactions.
- Generating management and audit-oriented reports.
- Controlling access to financial information based on user roles.

---

## 3. Objective

The primary objective of FinRecon India is to provide a centralized platform for receivables monitoring and reconciliation.

The application aims to:

- Reduce manual reconciliation effort.
- Centralize customer, invoice and payment information.
- Facilitate payment-to-invoice reconciliation.
- Provide receivables ageing analysis.
- Facilitate TDS/Form 26AS/AIS verification.
- Facilitate GST/GSTR-1 debtor-wise reconciliation.
- Identify exceptions and discrepancies.
- Provide structured financial and audit reports.
- Support multiple companies/entities within the platform.
- Restrict access to modules based on user roles.

---

## 4. Proposed Solution

The application follows a centralized data-processing and reconciliation approach.

```text
                 ┌─────────────────────┐
                 │ Customer Master     │
                 └──────────┬──────────┘
                            │
                 ┌──────────▼──────────┐
                 │ Sales / Invoices    │
                 └──────────┬──────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
   Bank / Payments      TDS / 26AS       GST / GSTR-1
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼
                  Reconciliation & Analysis
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
          Ageing        Exceptions       Reports
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                    Management Review
```

The application uses data provided through the platform to perform analysis and reconciliation. It is not intended to replace professional review or accounting judgement.

---

## 5. Key Features

### 5.1 Multi-Company / Entity Management

The platform supports management of multiple companies/entities within the application.

Users can:

- View the active company/entity.
- Switch between available companies.
- Add a new company/entity.
- Maintain company-level financial data.
- Work with company-specific reconciliation information.

### 5.2 User Authentication and Role-Based Access

The application includes user authentication and role-based access control.

The implemented roles include:

- **Business Owner / Admin**
- **Finance Manager**
- **Operational Accountant**
- **Chartered Accountant / Tax Auditor**
- **Read-Only Viewer**

Access to application modules and actions varies according to the assigned role.

Examples of controlled activities include:

- Invoice uploads.
- Bank statement uploads.
- 26AS uploads.
- GSTR-1 uploads.
- Reconciliation.
- Invoice creation.
- Customer editing.
- Exception resolution.
- Settings and user management.
- Record deletion.

### 5.3 Executive Dashboard

The dashboard provides a consolidated view of important receivables and reconciliation information.

It is intended to help users obtain a high-level view of:

- Receivables.
- Invoice status.
- Payment information.
- Reconciliation position.
- Exceptions.
- Other relevant financial indicators.

### 5.4 Customer Master and Customer 360

The Customer Master module provides a centralized customer-level view.

The application includes customer information and a Customer 360 view to facilitate review of customer-related financial information.

### 5.5 Sales / Invoice Register

The Invoice module provides a centralized sales/invoice register and supports invoice-level information, customer linkage, invoice status, receivable balances, payment-related information and Excel-based invoice import.

### 5.6 Bank Payments and Statement Management

The Bank Statement module provides functionality for reviewing bank/payment transactions and importing bank statement data for subsequent reconciliation.

### 5.7 Payment Reconciliation Centre

The Reconciliation Centre facilitates matching between payment transactions and sales invoices.

The application provides suggested matches and supports review of reconciliation logic, manual payment allocation and identification of unmatched payments, outstanding invoices and reconciliation exceptions.

### 5.8 Receivables Ageing Analysis

The Receivables Ageing module provides invoice-wise and customer-wise ageing analysis, including outstanding balances, invoice counts, customer-level ageing information and exportable ageing reports.

### 5.9 TDS / Form 26AS & AIS Verification

The TDS module assists in comparing business-side TDS information with uploaded Form 26AS/AIS information.

It includes TDS/Form 26AS import, TDS reconciliation, expected TDS comparison, exception identification, export functionality and reference information for TDS sections available within the application.

### 5.10 GST Reconciliation and Debtor Audit

The GST module provides debtor-wise GST reconciliation and audit-oriented analysis.

The application supports GSTR-1 data import and comparison with invoice information, including customer-wise reconciliation, GSTIN-wise information, invoice-wise comparison, reported taxable value, reported tax amounts, variances and exportable reconciliation reports.

### 5.11 Exceptions and Discrepancies Centre

The Exceptions Centre consolidates discrepancies identified through the application's processes, including unmatched payments, outstanding invoices, reconciliation differences, TDS differences and GST/GSTR-1 differences.

### 5.12 Reports and Export

The Reports module provides financial and reconciliation-oriented reporting capabilities, including customer ledger, receivables ageing, TDS/Form 26AS reconciliation and GST audit/reconciliation reports.

### 5.13 Documents and Proofs

The Documents module provides an area for managing documents/proofs associated with the application workflow and supporting reconciliation review.

### 5.14 Accounting Test & Verification Suite

The application includes an Accounting Test & Verification Suite for performing structured accounting/reconciliation checks and validating application data and accounting-related conditions.

---

## 6. Application Workflow

1. **Login** – Sign in using an authorized user account.
2. **Select Company / Entity** – Select the relevant company/entity.
3. **Review Customer and Invoice Data** – Review or import customer and invoice information.
4. **Import Bank / Payment Information** – Upload bank statement information.
5. **Perform Payment Reconciliation** – Analyse payment transactions against invoices.
6. **Review Receivables Ageing** – Review customer-wise and invoice-wise outstanding balances.
7. **Perform TDS / 26AS / AIS Verification** – Upload and compare relevant TDS information.
8. **Perform GST / GSTR-1 Reconciliation** – Import and compare GSTR-1 information.
9. **Review Exceptions** – Review discrepancies identified by the application.
10. **Generate Reports** – Review/export relevant financial and reconciliation reports.

---

## 7. Technology Stack

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Lucide React
- Recharts
- Motion

### Backend / Server

- Node.js
- Express
- TypeScript / TSX
- dotenv

### Data Processing

- XLSX
- Papa Parse

### AI / API Capability

- Google Gemini API SDK (`@google/genai`)

The actual dependency versions are maintained in `package.json` and the corresponding lock file.

---

## 8. Data Import and Reconciliation

The application is designed around user-provided data files.

Relevant data may include:

- Customer data.
- Sales/invoice data.
- Bank statement/payment data.
- Form 26AS/AIS data.
- GSTR-1 data.

The application processes uploaded information and performs the relevant reconciliation or analytical workflow.

The quality of the output depends on the completeness, accuracy and consistency of the input data.

---

## 9. Reconciliation Approach

The application uses transaction-level information and available identifiers to facilitate reconciliation.

Depending on the relevant module and available data, reconciliation may consider:

- Customer name.
- Customer identifier.
- GSTIN.
- Invoice number.
- Invoice date.
- Payment date.
- Transaction amount.
- TDS amount.
- Taxable value.
- GST/tax amount.
- Other available transaction attributes.

The application provides reconciliation results and exceptions for user review.

A reconciliation result should not be treated as conclusive without appropriate review of the underlying transaction and supporting documents.

---

## 10. Security and Access Control

The application includes role-based access controls to restrict access to selected modules and activities.

The source code uses environment-variable configuration for the Gemini API key.

The repository should contain only placeholder configuration in `.env.example`.

Actual credentials, API keys, passwords or other secrets should **not** be committed to GitHub.

For demonstration purposes, users should use dummy or anonymised information rather than confidential client data.

---

## 11. Government Portal Connectivity

The application is designed as a reconciliation and analytics platform using **user-provided data**.

It does not represent a live integration with government portals.

For example:

```text
User-provided 26AS / AIS data
              +
User-provided business records
              ↓
      FinRecon Reconciliation
              ↓
       Results / Exceptions
```

Similarly, GST/GSTR-1 reconciliation is based on information supplied to the application.

The application should therefore not be interpreted as automatically retrieving information from the Income Tax Department, GST portal or any other government system.

---

## 12. Sample / Demonstration Data

The application includes demonstration data within the project source for testing and presentation of application functionality.

The demonstration dataset contains sample companies, customers, invoices, bank transactions, TDS records, GST records, exceptions, documents and related application information.

Users should not replace demonstration data with confidential client information when using the project for demonstration or evaluation.

---

## 13. Limitations

The current application has the following limitations:

1. Reconciliation results depend on the accuracy and completeness of uploaded data.
2. Data inconsistencies can affect matching and reconciliation results.
3. Reconciliation exceptions require user review.
4. The application does not provide live government-portal connectivity.
5. The application is a capstone/demo platform and should not be treated as a substitute for professional accounting, tax, audit or legal judgement.
6. Authentication, data storage and access controls would require additional hardening before production deployment with sensitive financial or statutory information.
7. The application should be deployed with appropriate secret management and should not expose API credentials.

---

## 14. Project Structure

```text
AICA-L2-Batch-89-Dimple-Goyal/
│
├── README.md
├── package.json
├── bun.lock
├── tsconfig.json
├── vite.config.ts
├── server.ts
├── index.html
├── .gitignore
├── .env.example
├── metadata.json
│
└── src/
    ├── App.tsx
    ├── main.tsx
    ├── index.css
    │
    ├── components/
    │   ├── auth/
    │   ├── company/
    │   ├── customers/
    │   ├── dashboard/
    │   ├── invoices/
    │   ├── payments/
    │   ├── reconciliation/
    │   ├── ageing/
    │   ├── tds/
    │   ├── gst/
    │   ├── exceptions/
    │   ├── reports/
    │   ├── documents/
    │   ├── settings/
    │   ├── tests/
    │   ├── common/
    │   └── layout/
    │
    ├── context/
    ├── data/
    ├── types/
    └── utils/
```

---

## 15. Disclaimer

This project is an **AICA Level 2 Capstone Project** developed for educational, demonstration and analytical purposes.

FinRecon India is intended to assist users in organizing financial information, performing reconciliation, analysing receivables and identifying exceptions.

The application does not constitute professional accounting, tax, audit or legal advice. Users should independently verify source data, reconciliation results and statutory information before relying on any output for financial, accounting, tax, audit or business decisions.

The application should not be considered a substitute for appropriate professional review, internal controls or statutory compliance procedures.

---

## Author

**Dimple Goyal**  
Chartered Accountant  
AICA Level 2 – Batch 89
