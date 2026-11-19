GST AUTOMATION  -  Sales invoice PDFs  ->  GST Summary  ->  GSTR-1 JSON
=========================================================================

ONE-CLICK USE
-------------
1. Put the month's sales invoice PDFs in the folder  "Input Invoices".
   (25 specimen invoices for October 2026 are already there.)
2. Double-click  "Run GST Automation.bat".
3. When it finishes, the output folder opens by itself:
     Output\<date time>\GST-Sales-Summary.xlsx
     Output\<date time>\GSTR1_<GSTIN>_<MMYYYY>.json
     Output\<date time>\GSTR1_<GSTIN>_<MMYYYY>_checks.xlsx

The first run installs two Python libraries (pdfplumber, openpyxl); it needs
Python 3.9+ and an internet connection once. After that it runs fully
offline - no invoice data leaves the PC.

WHAT HAPPENS
------------
STEP 1  engines\gst_sales_summary.py
        Reads every PDF and takes the invoice-level totals from the tax summary
        table at the foot of each invoice (Tax Rate / Taxable Amt. / CGST /
        SGST). Writes GST-Sales-Summary.xlsx:
          Sheet 1 "Summary"    - one row per invoice (date, invoice no, GSTIN,
                                 party, taxable, IGST, CGST, SGST, value, HSN)
          Sheet 2 "Exceptions" - anything that does not add up
          Sheet 3 "Run Notes"
        Checks: GSTIN check digit, CGST = SGST, IGST vs CGST/SGST, printed
        grand total vs taxable + tax (allowing the printed round-off), invoice
        dated outside the period, duplicate numbers, gaps in the series.

STEP 2  engines\gstr1_json.py
        Takes SHEET 1 of the Step 1 workbook as its input and builds the
        GSTR-1 b2b JSON plus a checking workbook (Checks, Reconciliation,
        Table 12 HSN working, Table 13 documents working). If any row has an
        error the portal would reject, the JSON is NOT written and the rows are
        listed on the Checks sheet instead.

The supplier GSTIN and the return period (MM-YYYY) are read from the invoices
themselves, so nothing has to be typed.

Upload the JSON at: gst.gov.in > Returns Dashboard > GSTR-1 > Prepare Offline
> Upload. Table 12 (HSN) and Table 13 (documents) are not part of the JSON -
key them from the _checks workbook.

CHANGES MADE TO THE ORIGINAL SCRIPTS
------------------------------------
gstr1_json.py
  * read_summary(): reads SHEET 1 of the Step 1 workbook. The original skipped
    any sheet named "Summary" - which is the sheet Step 1 writes - so the two
    scripts could not be chained.
  * read_summary(): "Invoice value" in the Step 1 sheet is an Excel formula,
    which reads as blank until Excel has opened and saved the file. It is now
    taken as taxable + IGST + CGST + SGST, exactly what the formula says.
gst_sales_summary.py
  * The round-off is read whether the invoice prints "Rounded Off (-)" or
    "Rounded Off (+)". Previously a "(+)" round-off was missed and the invoice
    was wrongly reported as not tying to its grand total.

run_gst_automation.py (new) chains the two steps; "Run GST Automation.bat"
is the one-click launcher.

SETTINGS (top of run_gst_automation.py)
---------------------------------------
RCM_RATE = 18         rate for reverse-charge rows that carry no tax
RCM_MODE = computed   declare RCM tax amounts (or "nil")
HSN_DIGITS = 4        4 if turnover up to Rs 5 crore, 6 if above
JSON_VERSION          change only if the portal rejects the file

Command line (optional):
  python run_gst_automation.py --input "D:\Invoices\Oct" --period 10-2026

KNOWN LIMITS
------------
* Written for this invoice layout (tax summary table at the foot). Another
  billing package's PDF may not parse - it is reported on the Exceptions
  sheet rather than guessed.
* Where one invoice carries two SAC codes, the whole invoice is put under the
  first SAC in the Table 12 working; it is flagged "multiple HSN/SAC" on the
  Exceptions sheet so it can be split by hand.
* JSON invoice value = taxable + tax before round-off (differs from the
  printed grand total by under Re 1, which the portal accepts).

The specimen invoices are fictitious (supplier and buyers), made for an
academic project.
