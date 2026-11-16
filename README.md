# Smart Billing Manager

Double-click **Start Smart Billing Manager.bat** to start on this computer.
Requires Python 3.10+ on other computers. The launcher installs missing PyQt6, PyMuPDF (preview/print rendering), and ReportLab into `.vendor` on the first run only (internet required for installation). After installation, billing works entirely offline. If installation fails, run `python -m pip install -r requirements.txt` and retry.

1. Open **Seller Details**, enter your trade name, address, contact and GST details, bank details, declaration and optional PNG/JPEG logo.
2. Enter the customer name and address, date, and invoice items. Quantity must be positive. Rates exclude GST; fractional quantities are supported. Mobile and GSTIN are optional.
3. Add or remove rows as needed. Amount and GST are rounded to two decimals per line using decimal arithmetic. Optionally round the final total to the nearest rupee.
4. **Save** assigns a permanent number. **Search** opens saved invoices for editing. **New** and **Clear** start a blank invoice after confirming unsaved changes.
5. **Invoice Preview** displays the current form, including unsaved changes. **Export PDF** and **Print** save first. Export PDFs default to `invoices_pdf`. Printing uses the same ReportLab PDF and your system print dialog.

## Files and backup

`database/billing.json` stores seller settings, customer information, items, tax summaries and invoices. Folders and the JSON file are created automatically. Every write uses a temporary file, atomic replacement and a backup of the previous version at `database/billing.json.bak`. A single-instance lock prevents simultaneous app writers in the same folder.

Copy the whole `database` folder regularly to a safe place. A corrupt database is never silently overwritten: close the app and restore a reviewed backup manually. The `.bak` file is the previous save, not a full backup history. Deleting an invoice retains exported PDFs and does not reuse the number. New invoices use current seller settings; saved invoices retain their seller snapshot. Saving Seller Details also applies those settings to the currently open invoice.

Store the application in a writable folder. JSON is local plain text; protect the computer and backups appropriately. Amounts are INR. GST is shown as a single total per rate; this version does not split CGST/SGST/IGST or implement e-invoicing. Built-in PDF fonts support Latin text; use Latin characters for invoice text. Physical printing depends on your installed printer and driver.

## Verification

Run `python test_app.py` using the same Python interpreter as the app. Tests exercise money rounding and validation, create/edit/delete persistence, corruption protection, the real Qt editor, multipage PDFs and printing to a virtual PDF printer. `python test_app.py --sample` generates a sample PDF and PNG, without adding sample data to your real database.

## Windows executable

Run **Smart Billing Manager.exe** in this folder. All runtime libraries are bundled in this single file; no Python installation is required. The writable database remains external at `database/billing.json`. Read **EXE_AND_DATABASE.md** for database selection and trial activation instructions. Keep **OWNER_ACTIVATION_KEYS.txt** private.

To rebuild, install standard Python with PATH enabled and double-click **Build EXE.bat**. It creates an isolated build environment and builds `dist/Smart Billing Manager.exe`. Build on Windows for Windows.
