# PraNam E-Invoice Converter - Version 2.2

> **Install once before using this version:** double-click `install_requirements.bat`.
> Version 2.0 added OpenCV, NumPy and pypdfium2; without them PDF scans and images cannot open.

**Select any invoice file -> files are generated.** No data entry.

Accepted inputs: **Excel (.xlsx/.xlsm), PDF and Word (.docx)**, in any layout. A PDF or Word invoice is
converted internally into the same row/column grid used for Excel, so one set of mapping rules serves
every format: fields are found by their printed labels and item columns by their headings, wherever they
sit on the page. Wrapped lines in a PDF (an amount printed on the next line, a description running over
two lines) are stitched back into one item. Scanned/photographed PDFs hold no text and are reported as
such - use the Excel, Word or a digitally created PDF.

For each invoice the tool creates, in the `Output` folder:
| File | Use |
|---|---|
| `<InvoiceNo>_eInvoice.json` | Upload on the e-Invoice portal (bulk upload) to obtain the IRN |
| `<InvoiceNo>_NIC_READY.xlsm` | Same data inside the NIC-GePP utility (open with macros enabled -> Validate -> Generate JSON), if you prefer that route |
| `<InvoiceNo>_Validation_Report.xlsx` | Field-by-field source, reconciliation and notes |

The JSON follows the key order and code look-ups of the JSON writer inside NIC-GePP V2.0 (schema 1.1).
The IRN is issued only by the e-Invoice portal; this tool does not log in anywhere and uses no internet.

## Offline GST/IRP preflight (2.2)
Before generation, the converter now performs offline JSON Schema 1.1 validation plus GST/IRP business-rule checks. Optional empty JSON fields are omitted rather than written as `null`. Supplier GSTIN, Reverse Charge, IGST-on-Intra and the current supply types can be corrected on the check screen. Dynamic portal checks (GSTIN active status, e-invoice enablement, duplicate IRN, etc.) are intentionally not performed because this application remains offline.

## Scanned invoices: table reconstruction (new in 2.0)
A scan is not read as a stream of words. The page goes through:

1. **Preprocessing** (`pec/table_ocr.py`): grayscale, upscale below 1700 px, CLAHE contrast on flat or
   photographed pages, speckle removal, and deskew from the ruling lines (or the text baselines when the
   page has none). A clean, large scan is left almost untouched; the original file is never modified.
2. **Ruled-line detection** with OpenCV morphology: horizontal and vertical rules are isolated and reduced
   to line segments.
3. **Table blocks**: every horizontal strip is described by the vertical rules crossing it, and consecutive
   strips with the same column pattern become one table. This is what separates the item grid from the
   address, bank and tax-summary blocks, which have a different pattern.
4. **Borderless fallback**: with no usable rules, rows come from the vertical position of the OCR boxes and
   columns from the x positions that repeat down the page.
5. **Cell filling**: every OCR word carries text, box and confidence, and is placed in the cell containing its
   centre; a cell that holds ink but received no word is re-read on its own (`--psm 7`).
6. **Choosing the item table**: candidates are scored on header synonyms (description / HSN / qty / unit /
   rate / value / tax) and on how many rows look like data, with a penalty for bank, transport, declaration,
   buyer-detail and tax-summary wording.
7. The chosen table's rows and columns are written into the same grid the Excel and PDF readers produce, so
   the existing synonym matching, multi-line stitching, validation and JSON generation all apply unchanged.
   Cell confidence travels with the values: anything below 70% is reported for checking.

## How the transaction type is decided (2.1)
Never by default. The tool looks for evidence and says so:
* **Domestic (B2B)** - a buyer GSTIN on the invoice, or CGST/SGST charged, or rupee amounts with nothing
  pointing to an export. Exchange rate is then 1 and you are never asked for one.
* **Export** - export wording (LUT, without/with payment of IGST, zero rated, export of goods, shipping bill,
  port of loading), a foreign currency, or a foreign destination. EXPWP when IGST is charged, otherwise EXPWOP.
* **Not determined** - none of the above. The tool says so and you choose on the check screen; it does not guess.

Country, port and exchange rate are asked for only where they matter (exports). Currency is read from the
symbols and words actually printed (Rs., INR, rupee sign, $, USD, Euro, GBP, AED...).

## Check and correct before generating
Any invoice that still has a blocking problem opens the **check screen**: the header fields and an editable
item table (description, HSN/SAC, qty, unit, rate, taxable value, GST %), with add/delete row and a
"set GST % for all". Press Re-check to validate again; Generate is enabled only when nothing is blocking.
The same screen can be opened any time with "Check / correct...". Where the column headings on a scan cannot
be read at all, the table rows are handed to this screen as text rather than being discarded or guessed.

## Scans and images (OCR)
A PDF that holds only a picture of the invoice, and .png/.jpg/.tif files, are read by OCR on this computer.
Install **Tesseract** once (Windows: https://github.com/UB-Mannheim/tesseract/wiki, the
`tesseract-ocr-w64-setup` installer); the tool finds it automatically, or you can give the path in Settings.
Nothing leaves the machine. Expect to check the result: a scan of a ruled table often loses the column
boundaries, so header fields usually come through but the item grid may not. A digital PDF, Excel or Word
copy of the same invoice is always more reliable.

Also handled: invoices whose PDF text carries no spaces ("DateofSupply"), and landscape invoices whose
text is printed sideways in a portrait page.

## Also handled
* **Many invoices in one PDF** - each page that carries its own document number is converted separately,
  and the screen lists what was produced and what needs a correction.
* **Service invoices** - a SAC code printed as a field (not a column) is applied to every line, Is_Service = Yes,
  quantity 1 and unit OTHERS. Where no port of loading is printed (usual for services) currency, country and port
  are left blank, because the NIC utility demands a port as soon as any export detail is filled.
* **Domestic (B2B) invoices** - a buyer GSTIN on the invoice, or CGST/SGST charged, switches the supply to B2B:
  place of supply from the buyer's GSTIN, CGST+SGST or IGST as the invoice charges them. The tool objects when
  CGST+SGST is charged to a buyer in another State.
* **Debit / credit notes** are recognised from the heading; one carrying a negative amount is reported, not converted.
* Tax lines printed *under* the table (CGST @ 9%, IGST @ 18%, GRAND TOTAL, "TAXABLE VALUE IN INR @ 82.40") are read.

## What is read from the invoice
Invoice no./date, exporter name, address, GSTIN, state, PIN; consignee name, address, city, e-mail;
country of final destination -> NIC country code; port of loading -> NIC port code; currency from the
amount heading; line items (description, HS code, no. of boxes, GST %, GST amount, amount);
export type (EXPWP when the invoice says "IGST refund"/charges IGST, EXPWOP when it says LUT or charges none);
refund claim; totals and amount in words (cross-checked).

## The only things an invoice must show
* **Foreign-currency invoices:** an exchange rate somewhere in the file, e.g. `EXCHANGE RATE : 83.50`
  (if absent, the tool asks once for the figure).
* A port of loading the NIC master spells differently (e.g. Nhava Sheva = "Jawaharlal Nehru") is asked once
  and remembered for that wording.
* Recommended: a `GST %` column (as in invoice 004). Without it, EXPWOP invoices are reported at rate 0.
* Optional: `SHIPPING BILL NO :` / `SHIPPING BILL DATE :` if known at invoicing time.

## Run / build
* Run: double-click `run_app.bat` (needs Python 3.11+ once).
* EXE: double-click `build_exe.bat` -> `dist\PraNam E-Invoice Converter.exe`. Copy the `Template` folder next to the EXE.

The NIC template is bundled in `Template\` and found automatically - no browsing.
`Settings` (rarely needed): template location, output folder, UQC used for "No of Box" quantity.

## AICA Level 2 Project Submission

**Project:** PraNam E-Invoice Converter v2.2.8 (Offline Validation)  
**Submitted by:** Pratik Trivedi  
**Project demonstration:** https://youtu.be/FmWUJsVXWHQ

This repository contains the project source code, configuration, tests, requirements and the bundled NIC-GePP template required by the application.

