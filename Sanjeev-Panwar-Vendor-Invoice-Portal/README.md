# Vendor Invoice Portal

A Windows Django demonstration for vendor registration, Finance approval, invoice/PO submission, local text extraction and Finance-reviewed CSV export. Prepared as a sanitized source submission for ICAI AICA Level 2 using the supplied repository upload guide.

Author: **Sanjeev Panwar**

GitHub username: **Sanjeev-Panwar899** This is a localhost demonstration, not a production deployment.

## What it does
- Vendors register with a legal name, Kenyan-format KRA PIN and email; Finance staff must approve them before uploads.
- An approved vendor submits one invoice and one purchase order, plus an optional supporting document (PDF/JPG/PNG), with a 20,000,000-byte combined limit.
- Digital PDF text is extracted locally with PyMuPDF; scanned documents/images need an independently installed Tesseract executable. No cloud OCR or external model API is called by this source.
- Recipient PIN/context checks and heuristic field parsing precede invoice acceptance. Duplicate invoice-number checks are scoped to vendor and company.
- Finance verifies/corrects fields and approves or rejects invoices. Net + VAT must match total within 0.02 before approval.
- Approved invoices can be exported once to an ERP staging CSV; exported records are locked through the Finance review page. The Django admin remains privileged and is not a tamper-proof audit boundary.
- Vendor invoice details and documents are access-controlled; audit records are stored locally.

## Quick start on Windows
Extract this folder to a NEW location under your Documents folder. Do not merge it with the running portal. Install Python 3.13 if needed; the setup script uses `py -3.13`. An internet connection is needed for package installation; Tesseract is optional for digital PDFs.

1. Double-click **SETUP_WINDOWS.bat**. It creates a new `.venv`, installs pinned requirements, migrates a fresh demo database, seeds ten fictional companies, collects static assets and generates synthetic sample PDFs.
2. Double-click **CREATE_FINANCE_ADMIN.bat**. Choose a new local username/password. Nothing is preconfigured; do not reuse a real account password.
3. Double-click **START_PORTAL.bat** and open **http://127.0.0.1:8002**. Keep its window open; press Ctrl+C there to stop it. This uses a different port from the earlier portal.
4. Follow [the demo walkthrough](docs/DEMO.md). Everything generated locally stays under `local_demo/`, which must never be uploaded.

If a batch window reports an error, stop there and read it; do not proceed using an incomplete setup. If `py -3.13` is unavailable, install/register Python 3.13 or create `.venv` with a known Python 3.13 executable before rerunning setup. If port 8002 is occupied, do not stop an unknown process; select another loopback port in the clean copy's START_PORTAL.bat.

Equivalent terminal setup from this folder:
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DJANGO_SETTINGS_MODULE = 'portal.settings'
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe scripts\create_demo_pdf.py
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8002 portal.wsgi:application
```
Stop if any command fails. These commands use this copy's isolated settings. WhiteNoise serves collected Django admin static assets with DEBUG=False; the public portal uses inline CSS. Password-reset emails are files under local_demo/test_emails, not messages sent to real recipients.

## Configuration and validation
No .env file is required or automatically loaded. Settings generate a fresh local secret and use a fixed demo database/storage directory. See [configuration](docs/CONFIGURATION.md), [architecture and security](docs/ARCHITECTURE-SECURITY.md), and [validation evidence and limitations](docs/VALIDATION.md).

To run the seven synthetic regression tests:
```powershell
.\.venv\Scripts\python.exe manage.py test billing
```
The tests passed in the available isolated Python 3.12 environment, with Pillow 13.0.0. The original project used Python 3.13 and Pillow 12.3.0; its exact pinned environment has not been reinstalled/tested here. Package availability and current security advisories have not been checked online.

## AI and OCR disclosure
This project was developed with ChatGPT assistance, and this sanitized submission copy was prepared with Codex assistance. The owner should review this statement and add the particular development tasks they wish to describe. The running source performs local PDF extraction, optional Tesseract OCR and rule-based parsing; it does not integrate a generative AI model. Do not present heuristic extraction as an AI model or claim unmeasured accuracy. This upload guide alone does not establish the course's assessment or AI eligibility criteria.

## Repository contents
`portal/` configuration and entry points; `billing/` models, forms, views, migrations and regression tests; `templates/` pages; `scripts/create_demo_pdf.py` synthetic document generator; setup/start batch files; pinned requirements; `.env.example`; and `docs/`.

The submitted copy excludes private_data, SQLite databases, real PDFs, credentials, .env files, logs, virtual environments, generated static assets, backup source files and existing Git history. Review again after running locally: .gitignore is not a substitute for checking uploads.

## Submission
Use [GITHUB-SUBMISSION.md](docs/GITHUB-SUBMISSION.md). The guide calls for one named project folder and a README, uploaded to your fork and proposed to aiinicai/AICA-Level-2-Projects by pull request. A video is optional under that guide. No repository/PR has been created by this preparation.

## Known limits and licensing
Heuristic extraction is layout-dependent; Finance must verify every field. Tesseract/image OCR and a public/production deployment have not been validated. SQLite, in-process parsing and filesystem/database writes are prototype choices. There is no transactional rollback of saved files if later persistence fails, no malware scanning, no concurrency-proof duplicate/export guarantee, and no production role/retention policy. See the security notes before considering real data.

Confirm ownership and third-party licensing before public submission. No new license is imposed by this preparation. PyMuPDF licensing and any obligations for the intended distribution should be reviewed by the owner; no legal assessment has been performed.

## Project presentation

[View the capstone presentation PDF](docs/presentation/Sanjeev-Panwar-Vendor-Portal-Capstone.pdf). It includes fictional-data screenshots, the workflow and validation checks. Speaking notes have been removed. This is optional supporting material under the supplied upload guide.
