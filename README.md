# Ledger Reconciliation & Reporting Desktop App

## Files
- `reconciliation_app.py` - desktop application
- `requirements.txt` - Python dependencies
- `Install_and_Run.bat` - installs dependencies and opens the app

## Usage
1. Install Python 3.10+.
2. Double-click `Install_and_Run.bat`.
3. Select Company Books and Party Books.
4. Enter the reconciliation/cut-off date.
5. Select an output folder.
6. Click Run Reconciliation & Generate Reports.

## Supported input
Excel, CSV, PDF and JPEG/PNG images.

## Important OCR note
For image OCR, install the Tesseract OCR Windows engine separately and ensure it is available in PATH. The application does not fabricate unreadable transactions. Complex scanned PDFs may require manual review.

## Current matching logic
The app normalizes dates, references, narrations, debit/credit values and balances, then attempts evidence-based transaction matching. Ambiguous matches are flagged as review items rather than silently accepted.

This is a practical starter version and should be validated against your accounting workflow before relying on it for statutory or final financial reporting.
