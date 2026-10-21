# CA GST Filing Assistant Pro  (v2.4.9)  -  GSTR-1 utility

Windows desktop tool for Chartered Accountant firms. It prepares **every GSTR-1 table** as CSV files for the official **GST Offline Tool**, from

* **one Master Template** (Excel) that the client fills in, and/or
* the client's invoice files (Excel sales registers, text PDFs, scanned PDFs with OCR).

Everything is processed locally. The application never logs in to, or submits anything to, the GST Portal.

> ### Read this first - what is and is not verified
> \\\\\\\* The CSV \\\\\\\*\\\\\\\*headings, order and drop-down values\\\\\\\*\\\\\\\* are held in `schemas/offline\\\\\\\_tool\\\\\\\_schema.json` and are marked \\\\\\\*\\\\\\\*PROVISIONAL\\\\\\\*\\\\\\\*. They follow the Offline Tool samples as commonly published but were \\\\\\\*\\\\\\\*not verified against the Offline Tool version you use\\\\\\\*\\\\\\\*. Use \\\\\\\*\\\\\\\*Settings > Compare with official Offline Tool samples\\\\\\\*\\\\\\\* (point it to the sample CSV folder from the GST Portal) - matching headings are adopted automatically and differences are listed. Then \\\\\\\*\\\\\\\*test-import every generated file\\\\\\\*\\\\\\\* into the Offline Tool. Value formats (dates, drop-downs) are confirmed only by that test import.
> \\\\\\\* Direct GSTR-1 \\\\\\\*\\\\\\\*JSON\\\\\\\*\\\\\\\* generation is not implemented, by design - use the Offline Tool to create the JSON, then file with your own DSC/EVC.
> \\\\\\\* Tax in the summary is calculated as taxable value x rate (the Offline Tool recalculates it). Compare this application's \\\\\\\*\\\\\\\*GSTR-1 Summary\\\\\\\*\\\\\\\* with the Offline Tool's summary before filing.
> \\\\\\\* PDF/OCR extraction is heuristic: every PDF-derived line is flagged for review.
> \\\\\\\* GSTIN checks cover structure, state code and check digit only, not active registration.
> \\\\\\\* Amendment tables are produced \\\\\\\*\\\\\\\*only\\\\\\\*\\\\\\\* from the Master Template amendment sheets (an invoice file cannot tell what it amends). The amendment differential is not computed.

## 0f. What is new in v2.3.2 - v2.4.9

* **Whole year upload (tab 15).** Choose a folder or a ZIP with one sub-folder per month; every Master Template, register,
invoice file and filed return PDF is given to its month and extracted in one step.
* **Filed returns.** GSTR-1, GSTR-3B and GSTR-9 PDFs from the GST portal are read and listed on tab 15 ("Filed returns uploaded").
* **Reconciliation tables.** 1 Books vs GSTR-1 | 2 GSTR-1 vs GSTR-3B | 3 GSTR-3B tax payable vs paid | 4 GSTR-9 vs GSTR-1+3B |
5 Books vs GSTR-9 | 6 GSTR-9 vs GSTR-9C turnover (the 9C figures are typed in). Double-click a row for the likely reason and the
remedy. Export to Excel includes all tables.
* **Help line on every tab** ("What this tab is for") and a compact tab row so all 15 tab names fit on screen.
* **Scanned PDFs:** very large scans are drawn at a safe size, OCR finds Tesseract in its usual Windows folder, and when OCR
gives no text the message says why. OCR reads printed text, not handwriting.
* **Invoice Review:** "Go to the line" button from the Validation tab.
* **Home tab:** the button row always stays visible.

## 0e. What is new in v2.3.1

* Tab 3 (Return): **Create ALL returns of the financial year (Apr-Mar)** - type the FY (e.g. 2025-26) and click once;
12 returns are created (4 quarter-end returns for a QRMP client). Existing months are kept.

## 0d. What is new in v2.3.0

* **Tab 15 - YTD \& Annual.** Every return of the opened client for one financial year side by side (Apr-Mar): B2B, B2CL,
B2CS, exports, notes, nil/exempt, tax heads, invoices issued, flags for missing / unusual months.
Choose the FY in the box (FY 2025-26 works the same way: create the returns Apr 2025 ... Mar 2026 and upload each month).
* **GSTR-1 vs GSTR-3B vs Books.** Double-click a month, type the GSTR-3B figures and the books taxable value; differences are
shown month by month and for the year (kept per client and FY).
* **GSTR-9 worksheet.** Year totals arranged like GSTR-9 Tables 4A-4J and 5A-5F (worksheet only - verify before filing).
* **Export to Excel** of all three tables.
* Tabs 6 and 7: when the files were summary reports (no invoice lines) tab 6 says so and tab 7 lists the summary tables.
* New validation warning HSN\_PLACEHOLDER: HSN codes starting with 00 (e.g. 00000002) are flagged with the product names.

## 0c. What is new in v2.2.22

* **Summary reports from billing software.** An *HSN-wise sales report* (HSN Code, Tax Rate, UQC, Quantity, Base, SGST, CGST) is read into Table 12; a *date-wise GST output register* (Bill Date, Series, From/To BillNo, Exempt, rate-wise bases) is read into Table 7 (B2C others, same state), Table 8 (exempt) and Table 13 (bill series, gaps counted as cancelled with a warning). Upload them on tab 5 and click Extract Data; the rows show on the Master Template tab and in CSV Preview. Inter-state, cess and credit/debit amounts in the register are reported as warnings and not imported.

## 0b. What is new in v2.2.21

* **One printed invoice per sheet.** A workbook where every sheet is one tax invoice (INVOICE NO, DATE, CONSIGNEE, item table, SGST/CGST lines) is now read directly: upload it on tab 5 and click Extract Data. Items, rate, tax, recipient and place of supply are taken from each sheet; totals are cross-checked and differences noted on the line.
* **Document numbers such as VB/001/2026-2027** are now treated as one running series (Table 13) instead of one series per invoice.
* PyMuPDF is loaded under its current name (no more "fitz" warning).

## 0a. What is new in v2.2 - simpler day-to-day use

* **Home: NEXT STEP.** The Home tab tells you what to do next for the open return (upload, extract, review, fix errors, documents, export) with a *Go there* button.
* **Delete a return** (tab 3): *Delete selected return(s)* removes the return with its uploaded files, template data, lines, document register and history. CSV files already written to your output folder are not touched.
* **Column mapping with "same value for every row"**: the mapping screen (opens automatically for unknown layouts, or any time via *Map columns / same value for all rows...* on tab 5) lists YOUR column headings for each item, and below it lets you give one value for the whole file where it has no such column: invoice type (Regular, SEZ with/without payment, Deemed Export, Export with/without payment of tax, Intra-State attracting IGST), GST rate, credit/debit note, reverse charge, nil/exempt/non-GST, place of supply. A column that holds invoice-type words ("Export without payment", "SEZ", "B2B") is translated to the right GSTR-1 value.
* **Invoice Review > Set GST rate / HSN for many rows...**: asks for the rate (and optionally HSN, description, unit) and the scope (all lines / selected / lines with no rate / lines with no HSN / one file), applies it and recalculates IGST or CGST+SGST for every line from its place of supply (taken from the recipient GSTIN). Lines marked Nil/Exempt/Non-GST keep their rate.
* **HSN: descriptions and memory.** Blank HSN descriptions are filled automatically (the client's own remembered text first, then the standard HS chapter / heading or SAC service-group title - suggestions, editable). Approving lines makes the app remember each HSN's description, unit and rate for that client, so the next month's file needs less data (a missing rate is filled from memory). The HSN summary (Table 12) always follows the approved invoice lines.
* **Documents (Table 13) built gap-wise.** *Build series from invoices*: every unbroken run of numbers becomes one series - 1001-1009 and 1014-1023 give two rows (9 and 10 documents, 0 cancelled). Missing numbers are listed below the table (and as information in Validation) so you can enter them as cancelled. *Series by* Auto / Prefix / Customer: when the same plain number is used for different customers, series are built per customer. Credit and debit notes are separate series. Master Template invoices are included.

## 0\. What is new in v2.1 - less typing, faster clean-up

* **Bulk select / delete.** Ctrl+A selects every row in any grid. *Invoice Review*: **Select lines with errors**, **Delete ALL lines with errors**, and the **Delete** key / *Delete selected* for any selection. *Validation*: **Select all errors** then **Delete rows of selected issues** (removes the invoice lines and the Master Template rows the issues point to).
* **Tax = taxable value x rate.** IGST (inter-state, SEZ, deemed export, export with payment) or CGST + SGST (intra-state, half each) is calculated automatically on import, when a line is edited or added, and by *Auto-fill place of supply \& tax*. No tax is calculated for reverse charge, exports/SEZ without payment. A differing tax amount in the client's file is replaced and noted on the line. Switch off in Settings if you prefer the client's amounts.
* **Place of supply from the GSTIN.** Blank place of supply = state code of the recipient GSTIN (editing the GSTIN re-derives it; *Place of supply = GSTIN state (selected)* resets wrongly entered ones). Unregistered customers: exports = 96, otherwise the supplier's own state, flagged on the line for confirmation. A place of supply that differs from the GSTIN state is shown as Information (it can be legitimate).
* **Minimum-data Master Template.** For B2B / credit notes the client only needs recipient GSTIN, number, date, rate and taxable value: Place of Supply, Invoice/Note Value and HSN tax amounts are calculated when blank (each is listed as an Information message).
* **Skip-errors upload.** Tick *skip the invoices/rows that have errors* on the Master Template tab to import the good invoices and get the bad ones listed as warnings (an invoice with one bad row is skipped as a whole). File-level problems (wrong GSTIN/period, missing headings, sample file) still block the upload.

## 1\. What is generated

|Table|CSV file|Source|
|-|-|-|
|4  B2B|`b2b.csv`|Master Template + invoice lines|
|5  B2C Large|`b2cl.csv`|Master Template + invoice lines|
|6A Exports|`exp.csv`|Master Template + invoice lines|
|7  B2C Others|`b2cs.csv`|Master Template + invoice lines (summarised by type / state / rate)|
|8  Exempt / Nil / Non-GST|`exemp.csv`|Master Template + invoice lines|
|9B Credit/Debit notes (registered)|`cdnr.csv`|Master Template + invoice lines|
|9B Credit/Debit notes (unregistered)|`cdnur.csv`|Master Template + invoice lines|
|11A Advances received|`at.csv`|Master Template + invoice lines|
|11B Advances adjusted|`atadj.csv`|Master Template + invoice lines|
|12 HSN summary|`HSN.csv`|Master Template + invoice lines|
|13 Documents issued|`documents.csv`|Master Template (Documents sheet) or stand-alone Documents file|
|9A / 9C / 10 / 11 amendments|`b2ba.csv` `b2cla.csv` `b2csa.csv` `expa.csv` `cdnra.csv` `cdnura.csv` `ata.csv` `atadja.csv`|Master Template amendment sheets|
|Reports|`gstr1\\\\\\\_summary.xlsx` `validation\\\\\\\_report.xlsx` `reconciliation\\\\\\\_report.xlsx` `manifest.json`|generated|

Only tables that contain data are written. HSN (Table 12) and Documents (Table 13) are mandatory in GSTR-1 - the application warns when they are missing.

## 2\. Installation (Windows)

1. Install **Python 3.12+** from python.org (tick *Add python.exe to PATH*; keep *tcl/tk* selected).
2. Unzip this folder, e.g. `C:\\\\\\\\CA\\\\\\\_GST\\\\\\\_Assistant`.
3. Double-click `install.bat`, then `run.bat`.
4. *(Optional, scanned PDFs)* Install Tesseract OCR; set its path in Settings.
5. *(Optional)* `build\\\\\\\_exe.bat` builds `dist\\\\\\\\CA\\\\\\\_GST\\\\\\\_Filing\\\\\\\_Assistant.exe`.

Internal working data (client database, copies of uploaded files, logs, backups) is kept in `C:\\\\\\\\Users\\\\\\\\<you>\\\\\\\\CA\\\\\\\_GST\\\\\\\_Filing\\\\\\\_Assistant` (change with environment variable `CAGST\\\\\\\_DATA`, e.g. `D:\\\\\\\\GSTData`). **Output files are saved only in the folder you select when you generate them.**

## 3\. Operating steps

1. **2 Clients** - New Client (GSTIN is validated). **3 Return** - choose client, month, year, *New Return*.
2. **4 Master Template** - *Download Blank Template*; send it to the client. The client fills the sheets that apply (orange headings = mandatory; drop-downs for state, rate type, units, document nature ...). *Download Sample Template* shows a filled example (it is refused on upload).
3. *Upload Filled Template*. The whole file is checked; if anything is wrong **nothing is imported** and every problem is listed with its **sheet and row**. Checks include dates, numbers, GSTIN, place of supply, allowed values, invoice-number format, same invoice repeated with different details, B2CL rules (inter-state, threshold), export fields, HSN digits, tax vs rate, invoice value vs components, return GSTIN/period match, and duplicates across files.
4. *(Optional)* **5 Invoices** - upload Excel registers / PDFs, *Extract Data*; **6 Invoice Review** - correct and *Approve*; **7 Classification** - review or override sections. Approved invoice lines are merged with the template data (the same invoice in both places is flagged as an error).
5. **8 Validation** - all errors/warnings/information with suggested actions; *Export Exception Report*.
6. **9 Documents** - Table 13 register (also filled from the template's Documents sheet); stand-alone Documents template download/upload and *Generate documents.csv* are available.
7. **10 CSV Preview** - choose any table and see exactly what will be written. **11 GSTR-1 Summary** - tax summary and reconciliation (export to Excel).
8. **12 Export** - *Generate CSV Files*: the application **asks you to select the folder** (any drive). Unresolved errors block export unless you tick override and record a reason (stored in the audit trail and manifest). Existing files are never overwritten without confirmation.
9. Import the CSV files into the **GST Offline Tool** (guide shown on the Export tab), compare its summary with tab 11, generate the JSON and file on the portal yourself.

Output folder:

```
<selected folder>/clients/<GSTIN>/FY\\\\\\\_2026\\\\\\\_27/GSTR1\\\\\\\_2026\\\\\\\_09/
    source\\\\\\\_files/  extracted\\\\\\\_data/  review\\\\\\\_reports/
    output/   b2b.csv b2cl.csv b2cs.csv exp.csv cdnr.csv cdnur.csv exemp.csv at.csv atadj.csv HSN.csv documents.csv
              (+ amendment CSVs)  gstr1\\\\\\\_summary.xlsx  validation\\\\\\\_report.xlsx  reconciliation\\\\\\\_report.xlsx  manifest.json
```

## 4\. Master Template rules (also on its Instructions sheet)

* One row per invoice **per tax rate** for B2B, B2CL, EXP, CDNR, CDNUR; repeat invoice number/date/value/recipient on every row of the invoice.
* B2CS, AT, ATADJ, Exempt-Nil-NonGST and HSN are summary tables (rows with the same key are added together).
* IGST/CGST/SGST are not typed (HSN sheet: optional) - tax is computed from taxable value x rate. Place of Supply and Invoice Value may be left blank for B2B / credit notes. Exports without payment of tax and SEZ supplies without payment carry no tax.
* Credit notes to unregistered customers that are not B2CL are entered in B2CS as negative taxable values.
* Enter HSN/SAC as text (leading zeros). Minimum HSN digits is a setting (4 up to Rs 5 crore turnover, 6 above).

## 5\. Security

Local processing only; no network use by the application. No portal credentials/OTP stored. OCR is in-memory (no temp images). The log holds events/counts only. Settings: backup/restore (zip), delete a return's data, delete a client. Keep encrypted backups and restrict folder access.

## 6\. Code layout

```
main.py                     entry point               install.bat / run.bat / build\\\\\\\_exe.bat
app/gstr1.py                GSTR-1 engine: Master Template writer/reader, normalisation, validation, tables, summary, reconciliation, CSV writer, official-header check
app/schema.py               schema loading (user copy in the data folder is preferred over the bundled one)
schemas/offline\\\\\\\_tool\\\\\\\_schema.json   every table: sheet, CSV file, headings, order, kinds, drop-down values  (edit here, not in code)
app/exporters.py            export orchestration, reports, Documents template
app/autofill.py             place of supply from GSTIN, tax = taxable x rate
app/series.py               document series (Table 13) built gap-wise / per customer
app/hsn.py                  HSN descriptions and per-client HSN memory
app/classifier.py           section rules for invoice lines
app/validation.py           invoice-line validation
app/extractors/             Excel (auto-detect + mapping) and PDF/OCR readers
app/services.py, db.py, models.py, utils.py, gstin.py, config.py
app/ui.py                   Tkinter screens
tests/                      test\\\\\\\_core, test\\\\\\\_master (all 19 tables), test\\\\\\\_ui (UI logic on a stand-in Tk)
```

Run the tests: `python -m tests.test\\\\\\\_core`, `python -m tests.test\\\\\\\_master`, `python -m tests.test\\\\\\\_ui`, `python -m tests.test\\\\\\\_auto`, `python -m tests.test\\\\\\\_v22`.

## 7\. Known limitations

* Headings/values are provisional until verified (see the notice at the top).
* The screens were exercised through a stand-in Tk (logic and file output) but not visually on Windows - run a sample client first.
* B2CL threshold and valid GST rate slabs are editable in Settings; confirm them against the rules for the return period. QRMP/IFF specifics, e-invoice/IRN handling, Table 14/15 (e-commerce operator supplies) and the amendment differential are not covered.

