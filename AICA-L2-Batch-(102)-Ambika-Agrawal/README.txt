SURL CHECKER + OCR CAPSTONE PACKAGE
==================================

WHAT THIS PROJECT DOES
----------------------
The Search for Unrecorded Liabilities (SURL) Checker is a Streamlit prototype that screens subsequent disbursements against year-end AP aging and, where available, unprocessed invoices/vouchers. It identifies records that warrant auditor follow-up; it does not conclude that a liability is unrecorded.

SUPPORTED INPUT FORMATS
-----------------------
- CSV
- Excel: XLSX and XLS (first worksheet only)
- PDF: text-based PDF and scanned/image PDF
- Images: PNG, JPG/JPEG, TIFF/TIF and BMP
- DOCX and TXT

HOW EXTRACTION WORKS
--------------------
1. CSV/Excel are loaded as tabular data.
2. PDF tables are attempted first using pdfplumber.
3. Text PDFs are read from their text layer.
4. Scanned PDFs are rendered page-by-page and passed to OCR when text extraction is unavailable/poor.
5. Image files are passed to OCR.
6. DOCX tables are extracted where present; otherwise paragraph text is processed.
7. For invoice-like text and OCR output, vendor/invoice/date/amount fields are estimated using simple patterns. The full extracted text is retained for review. The app also presents an editable OCR-candidate table; after you correct/verify the fields against the source, you can explicitly choose to include those candidates in the unprocessed-invoice screening population. They are not included automatically.

IMPORTANT OCR REQUIREMENT
------------------------
The Python package pytesseract is only a connector. The Tesseract OCR engine must also be installed on the computer and accessible on PATH.
- Windows: install Tesseract OCR using a trusted distribution; if it is not added to PATH, configure pytesseract.pytesseract.tesseract_cmd in the app.
- macOS: if Homebrew is installed, run: brew install tesseract
- Debian/Ubuntu: run: sudo apt-get install tesseract-ocr
Then restart the terminal and run: tesseract --version to confirm it is available.

RUN THE APP
-----------
1. Install Python 3.10 or later.
2. Extract this ZIP.
3. Open Terminal / Command Prompt in the app folder.
4. (Recommended) create and activate a virtual environment.
   Windows: py -m venv .venv  then  .venv\\Scripts\\activate
   macOS/Linux: python3 -m venv .venv  then  source .venv/bin/activate
5. Install Python dependencies: pip install -r requirements.txt
6. Install the separate Tesseract OCR engine as described above for scanned PDFs/images.
7. Run: streamlit run surl_checker_app.py
8. Upload the year-end AP aging and subsequent disbursement register. Add complementary populations if available.
9. Review each extraction preview, especially OCR results, before relying on screening flags.
10. Download the Excel report and complete the workpaper template with evidence and conclusions.

EXPECTED STRUCTURED FIELDS
--------------------------
Year-end AP aging: vendor/supplier, invoice number, open balance. Helpful extras: vendor ID, invoice date, service/receipt date, invoice amount.
Subsequent disbursements: payment/transaction date, payee/vendor and amount. Invoice/reference is helpful but some bank registers may not contain invoice numbers; descriptions/narrations can be useful supporting evidence.
Unprocessed invoices/vouchers: vendor and amount; invoice reference and service/receipt date are helpful.
Subsequent AP aging: vendor, invoice number and open balance.

The app tries to recognize common alternate column headings. If a document is an invoice scan rather than a structured population, upload it in the optional supporting-documents slot to view the extraction. It will not reliably transform every complex invoice layout or every multi-invoice PDF into a clean population automatically. Correct OCR fields and create/review a structured extract before using it for matching.

KNOWN LIMITATIONS / SAFEGUARDS
------------------------------
- OCR and pattern-based field extraction can misread vendor names, invoice numbers, dates, decimals, currency symbols and totals. Verify every field against the original page.
- Handwriting, low-resolution images, rotated pages, password-protected PDFs, complex multi-column statements and unusual layouts may not extract properly.
- Excel reads only the first worksheet. Upload the relevant worksheet separately if necessary.
- The matching logic is a screening aid. Vendor/invoice matching can miss variants and can create false matches; review unmatched and matched records.
- The illustrative sample-count helper is non-statistical and is not an audit-standard formula.
- Default dates, thresholds and materiality values are fictional demo settings. Replace them with engagement-approved values.
- Do not upload confidential client information unless the use is expressly permitted by your firm's policies and data-processing requirements. Use fictional or approved redacted data for the capstone demo.
- This is a prototype and is not represented as ICAI-approved, production-grade, or a substitute for professional judgment.

PACKAGE CONTENTS
----------------
- app/surl_checker_app.py: Streamlit app with multi-format extraction and OCR fallback
- app/requirements.txt: Python dependencies
- SURL_Master_Workpaper_Template.xlsx: workpaper template
- input_samples/: fictional structured sample populations and test cases
- sample_invoices/: fictional invoice PDF pack
- CAPSTONE_PROJECT_SUMMARY.docx: project summary
- SUBMISSION_STEPS.txt: setup, testing and submission guidance
- VIDEO_DEMO_SCRIPT.txt: suggested demo script
