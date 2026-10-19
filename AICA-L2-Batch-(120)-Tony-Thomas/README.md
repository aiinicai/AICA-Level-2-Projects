# All in one Accountant

**ICAI AICA Level 2 capstone | Batch 120 | Tony Thomas**

A Python accounting ERP prototype for retail and wholesale businesses, created with assistance from Antigravity. It brings company management, bookkeeping, procurement, sales, inventory and financial reports into a local browser interface.

## Problem and approach

Small businesses often keep separate records for invoices, supplier bills, inventory and reporting. This project explores how one local application can connect those activities with double-entry accounting and a shared chart of accounts.

## Features

- Company profiles and separate local company databases.
- Chart of accounts, opening trial balance and general ledger journals.
- Customers, sales invoices, receipts and credit notes.
- Vendors, purchase requisitions, purchase orders, goods receipts, bills and payments.
- Product inventory, stock movements and adjustments.
- Budgets, approval workflows and illustrative tax summaries.
- Trial balance, profit and loss, balance sheet and dashboard reports.
- Browser-side print, PDF and spreadsheet export interfaces.

## Technology

FastAPI, SQLAlchemy, SQLite, Pydantic and Jinja2 power the Python backend. The interface uses HTML/JavaScript and externally hosted libraries including Tailwind CSS, Chart.js, SheetJS and jsPDF. Internet access is needed for those interface assets; financial records are stored locally.

## Run locally

Use Python 3.10 or later. Validation for this submission used Python 3.14 on Windows.

From this project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 in a browser. API documentation is at http://127.0.0.1:8000/docs. Stop the server with Ctrl+C.

Alternatively, install the requirements in your current Python environment and double-click `run.bat`. The optional `desktop_app.py` launcher starts a local server and opens the default browser.

The application creates its SQLite database, company registry and company data directory automatically. Startup initializes 24 standard accounts and tax codes, without customer/vendor transactions. The default company and all bundled examples are fictional. The demonstration company PIN is **1234**; it is a public example, not a real credential.

## Demonstration workflow

1. Open the dashboard and inspect the clean chart of accounts.
2. Configure a fictional company profile using only sample information.
3. Enter balanced opening balances.
4. Add fictional customers, vendors and inventory items.
5. Record sales, purchases and receipts/payments, then review the ledger and reports.
6. Try the export/print interfaces with sample data.

## Project structure

```text
main.py              FastAPI application and startup
desktop_app.py       Optional local browser launcher
app/api/             Accounting and company endpoints
app/models.py        Database tables
app/schemas.py       Request and response schemas
app/crud.py          Accounting calculations and data operations
app/database.py      SQLite sessions and company selection
app/company_manager.py  Local company registry
app/seed_data.py      Clean initialization and fictional demo examples
app/templates/       Browser interface
app/static/js/       Interface behaviour and export logic
requirements.txt     Python dependencies
run.bat              Windows launcher
```

## Validation

The sanitized submission was copied to an isolated scratch directory for validation. Checks passed for page rendering and ten application routes, including company/account lists, AR/AP lists, inventory and financial reports. Database checks confirmed 24 accounts and zero startup customers, vendors, invoices or journals. A balanced journal was saved and verified in a new database session; an unbalanced journal was rejected.

The original verification scripts are included as development aids. **Run them only in a disposable copy:** several reset the database, seed demo records or change company profiles. The complete legacy test suite and every export/UI workflow have not been certified by the submission preparation checks.

## Data protection and limitations

No original databases, company registry, financial exports, environment files, credentials, executables, build folders or cache files are included. Business contact details and bank/tax identifiers in bundled examples were replaced with fictional placeholders. Generated records and local configuration are excluded by `.gitignore`.

This is a capstone prototype for local demonstration. Its four-digit company PIN and local registry are not a complete authentication/security system. Keep the server bound to `127.0.0.1` and use fictional data for evaluation. Some dashboard charts use simulated/fallback series; they are illustrative, not audited financial results. Tax rates and forms are examples, not validated statutory filing functionality.

## Submission

Prepared folder: `AICA-L2-Batch-(120)-Tony-Thomas`.

The supplied ICAI instructions call for a fork of https://github.com/aiinicai/AICA-Level-2-Projects, a project-folder commit, and a pull request back to upstream `main`. Repository-owner review and merge are separate from opening the PR. After the GitHub submission, complete the ICAI Google Form at https://forms.gle/cucnBGn34bVHFaxt9.
