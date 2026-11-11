# Petrosuite

Windows desktop application for daily management of a petrol pump and GST reporting.
Capstone project, AICA Level 2.

**Author:** Pramod Mishra

**Demo video:** [Watch on Google Drive](https://drive.google.com/file/d/1GWGkNDsj3mZMaqftdyYXe-s14TbN77pI/view?usp=sharing)

## What it does

| Area | Details |
|---|---|
| Daily operations | Daily entries for a petrol pump, credit sales with editable slip numbers, receipts, discounts, customer TDS, bowser sales, expenses (including testing-expense columns) |
| GST reporting | GST report including E85 (18% GST), purchases and product dropdowns |
| Invoices | Tax invoice with an account summary strip (Opening Balance, Purchase, Discount, TDS, Receipts, Closing Balance), editable with reset |
| Exports | Monthly Excel workbook with TOTAL rows, nil sheets omitted, totals re-verified with mismatches marked red; invoice PDF |
| Multi-company | Separate data per company; backup import as a new company or as an overwrite |
| Access control | Admin / User login; offline, machine-locked activation |

## Architecture

| Layer | Technology |
|---|---|
| Shell | Python 3 + PySide6 (QtWebEngine) |
| User interface | Single-file HTML/JS app: `pyapp/web/app.html` |
| Storage | SQLite (companies, key-value store, licence), via `pyapp/db.py` |
| Python-to-JS bridge | `pyapp/bridge.py` |
| Packaging | PyInstaller (`pyapp/Petrosuite.spec`) and Inno Setup (`pyapp/Petrosuite.iss`) |

Main files in `pyapp/`: `main.py`, `db.py`, `bridge.py`, `company_dialog.py`,
`import_backup_dialog.py`, `login_dialog.py`, `activation_dialog.py`, `auth.py`,
`license_common.py`, `web/app.html`.

## Run from source (Windows)

```
cd pyapp
py -m pip install -r requirements.txt
py main.py
```

This public copy runs with **demo** credentials and a **demo** licence secret:

| Item | Value |
|---|---|
| Admin password | `Admin@Demo1` |
| User password | `User@Demo1` |
| Activation | The activation screen shows a Machine ID. Generate the key with `py tools\generate_key.py <MACHINE-ID>` (run from the repository folder) |

These demo values are for review only. See `BUILD.md` for production builds.

## Security note

The real licence secret, real password hashes, client backups and databases are
deliberately **not** in this repository. They are loaded from untracked local files
(`pyapp/license_secret_local.py`, `pyapp/auth_local.py`), see the `.example` files.

## How AI was used

This project was built for an AI course, with the help of an AI coding assistant.

| Area | Role of the AI assistant | Role of the author |
|---|---|---|
| Tool | Claude (Anthropic) | |
| Requirements | | Defined the accounting, GST and TDS rules, report formats and reconciliation logic |
| First version | Built the app as a single-file HTML application from the author's instructions | Described each screen and report, and tested them |
| Desktop app | Converted the HTML app into a Python (PySide6) desktop application with SQLite storage, login, activation and multi-company support | Decided the features and tested them |
| Executable | Set up packaging into a Windows executable (PyInstaller) and installer (Inno Setup) | Built and installed it on Windows |
| Verification | Added automatic re-checks of totals in the monthly Excel export (row, column, cross-foot and GST report sections) | Checked reports against manual working and the customer ledger |
| Publishing | Scanned the project for secrets and prepared this clean public copy | Decided what to publish |

## Third-party components

See `THIRD_PARTY_NOTICES.md`.

## Licence

No licence has been granted for this code yet. All rights are reserved by the author
unless a licence file is added.
