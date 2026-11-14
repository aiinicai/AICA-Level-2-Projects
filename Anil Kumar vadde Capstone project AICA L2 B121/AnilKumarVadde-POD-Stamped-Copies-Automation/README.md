# Auto-Attaching Customers' Stamped Copies to Sales Invoices

**Author:** CA Anil Kumar Vadde · AICA Level-2 (Batch 121), ICAI Dubai
**Stack:** Python (offline OCR) + Zoho Books Deluge (scheduled automation) · Built with AI assistance (Claude)

> All invoices, customers and data in this repo are dummy test data ("Codex Trading LLC", "ABC Cardo LLC").

## Problem
- Delivery executives post stamped proof-of-delivery copies in a WhatsApp group with names like `WhatsApp Image 2026-10-25 at 10.14.32.jpeg`.
- Each copy had to be matched to its invoice and attached by hand, one by one.
- Access is tight: Sales cannot edit invoices and Finance can only mark them as Sent.
- Invoices waited in **Draft** for the stamped copy, so they were missing from customer statements (SOAs).

**Question:** How do we attach every stamped copy to the right invoice automatically, without giving anyone extra edit rights?

## Solution: two small tools working together

| Offline Python tool (on the PC) | Zoho Books scheduled script (Deluge) |
|---|---|
| Reads the invoice number printed on each scan using local OCR | Runs daily inside Zoho Books |
| Saves it as a PDF named by invoice, e.g. `INV-OCT-000001.pdf` | Reads only the "STAMPED COPIES - SALE INVOICES" folder |
| If it can't read a number, asks the user or moves the file to `unmatched/` | Finds the exact invoice and attaches the file |
| Keeps originals and writes a rename log (CSV) | Adds an audit comment and skips duplicates |

## Workflow
1. **Collect:** save the day's stamped copies from WhatsApp into one folder.
2. **Number:** run the Python tool. OCR renames each file by invoice and converts it to PDF.
3. **Upload:** upload the numbered PDFs to the STAMPED COPIES folder in Zoho Books.
4. **Match:** the daily schedule reads the folder and finds the exact invoice.
5. **Attach:** the file is attached with an audit comment, and repeats are skipped.
6. **Review:** check Workflow Logs and the email summary (attached / unmatched / failed).

## Repository structure
```
presentation/          POD-Stamped-Copies-Automation.pptx
python-ocr-tool/       rename_stamped_copies.py, requirements.txt
zoho-deluge-script/    scheduled Deluge script + notes
sample-data/input/     2 WhatsApp photos + 1 scanned PDF (dummy invoices)
sample-data/output/    numbered PDFs + rename_log.csv
```

## How to run the Python tool
```bash
cd python-ocr-tool
pip install -r requirements.txt
python rename_stamped_copies.py "../sample-data/input"
```
Options: `--no-prompt` (don't ask for unreadable numbers, just log them) and `--move` (move instead of copy).
If RapidOCR won't install, use `pip install pytesseract pymupdf pillow` plus Tesseract-OCR for Windows.

## Test results
- **3 / 3** invoice numbers read by OCR (2 phone photos, 1 rotated scanned PDF), 25 Oct 2026.
- **2 / 2** attached in the Zoho test run on 24 Oct 2026, with 0 skipped, 0 unmatched and 0 failed.
- **0** extra edit rights granted.

## Security and controls
- **Offline:** OCR runs locally. Nothing is uploaded to third parties, and originals are never changed.
- **Stays inside Zoho:** the script runs on Zoho's servers through an authorised connection.
- **Least privilege:** no one gets invoice edit rights.
- **Scoped and auditable:** it reads only the stamped-copies folder, adds audit comments, writes logs and sends a daily email.

## Lessons learned
- The Zoho connection name must be the literal `"books_conn"`, not a variable.
- The Folders API failed, so the script filters documents by folder name.
- Zoho autoscan treats Files-inbox uploads as bills, so files are uploaded straight into the folder.
- Invoice formats vary (`INV-OCT-B-…`), so the full number is taken from the file name.

## Next steps
- Go live with the daily schedule and email summary.
- Auto-set "Stamped Copy Status = Received" on each invoice.
- Extend the same pattern to delivery notes and other clients.

## Video demo
_Link to be added_
