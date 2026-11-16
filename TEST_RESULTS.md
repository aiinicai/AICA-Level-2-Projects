# Verification results

Verified 3 November 2026 on Windows with Python 3.12, PyQt6 6.12, ReportLab and PyMuPDF.

`test_app.py`: **4 test groups passed**.

- Decimal calculations: line totals, mixed GST rates, half-up rounding and grand-total round off; rejected zero quantity, negative rates, out-of-range GST, NaN, infinity and empty item names.
- Storage: automatic folder/file creation, seller persistence, invoice numbering, edit/reload, deletion, non-reuse of deleted numbers, previous-save backup and preservation of corrupt source data.
- Real Qt editor: customer/item entry, recalculation, save, reload, edit and unsaved-change tracking. Generated and rendered the invoice PDF and printed it through QPrinter to a virtual PDF file.
- Multi-page export: 90 long-description items, repeated table headers, escaped special characters, final totals and signature content.

Visual inspection completed for the desktop window and generated sample invoice. PDF table width, signature placement and date-field width issues were corrected. The sample invoice is one A4 page. Your real database contains no sample invoices.

Updated EXE verification: five invoice/GUI test groups and one activation test group passed. Database-folder selection, copying the current database, remembered selection and expired billing controls were verified. All 12 signed activation keys were validated using isolated license state; real keys remain unused on the delivered installation.

The single-file EXE was built and tested from a folder without the local `.vendor` libraries. Frozen startup, Qt GUI, JSON save/reload, GST calculations, ReportLab PDF, PDF rendering, virtual printing and the license countdown all passed. See `EXE Smoke Test.json`. A conflicting ICU DLL picked up from an unrelated tool was excluded in the final build specification.

Not verified: physical paper output on your printer and execution on a separate PC. Preview and print rendering use PyMuPDF; PDF authoring uses ReportLab.
