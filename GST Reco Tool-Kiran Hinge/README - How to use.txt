GST RECO TOOL  -  version 1.0
=============================

WHAT YOU NEED
-------------
* Windows 10 or 11 (64-bit).
* Microsoft Excel 365 (or Excel 2021+) to open the reco workbooks.
* Nothing else - no Python, no installation, no internet.


FIRST TIME ON A PC
------------------
1. Copy "GST Reco Tool.exe" anywhere (Desktop, or a shared folder on the server).
2. Double-click it.
3. Windows may show a blue box "Windows protected your PC" (the exe is not
   code-signed). Click "More info" -> "Run anyway". This happens only once per PC.
   If your antivirus blocks it, ask IT to allow "GST Reco Tool.exe".

The window takes about 5 seconds to open.


HOW TO USE
----------
1. Click "Add files..." (top right) and select all your files together:
     - GSTR-1 Section-wise Summary          (Tax Power)
     - GSTR-2B Section-wise Summary         (Tax Power)
     - GSTR-3B Month-wise Annual Summary    (Tax Power)
     - Sales / DN / CN Register             (Tally)
     - Purchase / DN / CN / Journal Register(Tally)
   The tool recognises each file and puts it in the right box (green dot).
   You can also use the Browse button next to each box.
   Only doing sales? Just give GSTR-1 + Sales (+ GSTR-3B). Same for purchases.

2. Check the "Files read" table: rows and totals for each sheet. Tie these to
   Tally / Tax Power before going ahead.

3. Check Client name, Financial year and "Save reco files to"
   (filled in automatically - change if needed).

4. Click "Generate reco workbooks". Then click "Open Output reco",
   "Open Input reco" or "Open folder".

Files created:
   0. GST Reco Output FY2026 - <Client>.xlsx
   0. GST Reco Input FY2026 - <Client>.xlsx
If a file with the same name is open in Excel, close it first.


THE WORKBOOKS
-------------
* Output Summary / Input Summary - month-wise Tally vs GSTR-3B vs GSTR-1/2B and
  the differences. All formulas - no pivots to refresh.
* Reco File - invoice by invoice: Matched / Not in R1 (2B) / Not in Books (Tally)
  / Difference in TV / Difference in GST.
* All input sheets are inside the workbook as Excel tables.
* Settings sheet - tolerances (Rs.10 taxable, Rs.1 per tax head) and the + / -
  sign used for each note register. Change the yellow cells; everything updates.

Editing data later: change values inside the data sheets, or type/paste new rows
DIRECTLY BELOW a table so the table grows. Do not paste over the whole sheet.
For a fresh month, simply run the tool again.


IF SOMETHING GOES WRONG
-----------------------
* "Could not recognise" a file -> use the Browse button for that box.
* Yellow warnings in the "Messages" tab -> e.g. a register has no GSTIN column, so
  invoice-level matching is not possible for it (month-wise summary still works).
* Error details are saved in:  %LOCALAPPDATA%\GST Reco Tool\error.log
  Send this file along with the input files for support.


FOR WHOEVER MAINTAINS THE TOOL  (folder "Source code")
--------------------------------------------------------
gst_reco_tool.py   reco engine (reading files, formulas, workbook layout)
gst_reco_app.py    desktop window
build_exe.bat      rebuilds "GST Reco Tool.exe" (needs Python 3.11+ on the build PC
                   only; it downloads the libraries itself). Output: dist\
requirements.txt   libraries used
app.ico            icon
Command-line use:  "GST Reco Tool.exe" --cli --gstr1 a.xlsx --sales b.xlsx ...
                   --gstr2b c.xlsx --purchase d.xlsx --gstr3b e.xlsx --outdir folder
