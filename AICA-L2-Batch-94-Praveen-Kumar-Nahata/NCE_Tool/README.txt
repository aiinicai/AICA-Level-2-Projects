NCE TOOL v3.0  -  ONE application: Tally  ->  ICAI Non-Corporate-Entity financial statements (Excel)
==========================================================================================================
Reads the previous-year and current-year trial balances straight from Tally (ODBC) - or from files you already have - and writes ONE Excel
workbook in the ICAI NCE format: Review, Details, Balance Sheet, Statement of P&L, Notes 1-26, Disclosures, Trial Balance (drop-downs),
Workings, Lists.  Everything is formula-linked.  The ICAI template is built into nce_tool.py, so this folder needs nothing else.

ONE-TIME SETUP (Windows)
  1. Install Python 3.9+ (64-bit) from python.org - tick "Add python.exe to PATH".
  2. Double-click run_nce_tool.bat.  The first time it installs openpyxl, pypdf and pyodbc (internet needed once).
  3. For "Extract from Tally": Tally must be open with the company loaded and its ODBC server on (TallyPrime: F1 Help > Settings > Connectivity;
     port 9000).  The ODBC data source is normally "TallyODBC64_9000" (the same one your Excel query uses).  Use 64-bit Python with 64-bit Tally ODBC.

EVERY CLIENT (about 5 minutes)
  Tab 1  Source          "Extract from Tally now" (press "Test connection / list companies" once)  -OR-  "Use files I already have".
  Tab 2  Client          PAN, nature of business, signatories, auditor details (auditor/place/folder are remembered), units, date.
  Tab 3  Create          Choose the folder, press "Create NCE financial statements".
                         Tally mode: when asked, switch Tally to the PREVIOUS year (Alt+F3 company / Alt+F2 period), press OK; then the CURRENT year, press OK.
                         Output: NCE_<Client>_FY<year>.xlsx (never overwrites - a second run becomes "... (2).xlsx") and, in sub-folder Tally_data, the
                         extracted trial balances and computed Balance Sheet / Profit & Loss PDFs.
  Then open the workbook and read the sheet "Review" first.  (If Excel shows a yellow "Protected View" bar press "Enable Editing" so formulas calculate.)
  Help tab: "System check" shows what is installed; "Install missing libraries" installs openpyxl / pypdf / pyodbc.

COMMAND LINE (optional)
  python nce_tool.py                                   window
  python nce_tool.py TB_FY24-25.xlsx TB_FY25-26.xlsx [PL.pdf BS.pdf ...] -o folder --entity "..." --pan ... --nature "..." --units Lakhs
  python nce_tool.py --from-tally --fy 2026 -o folder --dsn TallyODBC64_9000 [--company "X (2025-26)" --company-py "X (2024-25)"]
  python nce_tool.py --check | --list-companies | --extract-only ...
  Signature options: --address --signer "Name, Designation" (repeat) --aud-firm --aud-frn --aud-name --aud-desig --aud-mno --udin --place --date dd/mm/yyyy
  --py-opening-stock 126460  (previous-year opening stock when no previous-year P&L PDF exists)

INPUT FILES THE TOOL ACCEPTS
  * Tally ODBC extract (Excel):  $Name, $Parent, $_PrimaryGroup, $ClosingBalance  (debits negative).  Optional "Info" sheet (company, period, stock).
  * The older Tally "Trial Balance" export (group rows + ledger rows, Debit / Credit columns).
  * Tally Profit & Loss and Balance Sheet PDFs (optional): they supply opening stock, nett profit and the cross-checks on sheet Workings E.

CORRECTING FIGURES
  Sheet "Lists" (yellow panel, columns Q-U): EASIEST WAY TO MOVE A LEDGER - pick the Ledger, then the Note, then the Line item from the drop-downs; column U must say "Active". Clear the row to undo.
  Sheet "Trial Balance": for any ledger choose another Note Label and Line Item (yellow drop-downs) - everything updates.  Orange = the tool guessed.
  Sheet "Workings": closing stock (derived / override), fixed-asset classes and depreciation rates, partners' ratios, remuneration, interest.
  Sheet "Balance Sheet" cell H3: Actuals / Hundreds / Thousands / Lakhs / Crores (totals use unrounded values, so displayed lines may differ by rounding).
  Sheet "Details": firm/auditor/signatory/place/date printed under the Balance Sheet and P&L.   Sheet "Disclosures": related parties, contingent liabilities.

WHAT A TRIAL BALANCE CANNOT TELL (the tool states its assumptions - see "Review")
  Original cost of fixed assets (Note 11 is at WDV), partners' profit-sharing ratio and remuneration split (equal by default), MSME split, debtor ageing,
  long/short-term split of loans and deposits, previous-year opening stock (give the P&L PDF or --py-opening-stock), where current-year profit sits when
  Tally's own "Profit & Loss A/c" ledger is in the extract.  The Balance Sheet total is larger than Tally's because Tally nets debit/credit balances inside
  a group while the ICAI format shows each ledger on its natural side.

IF SOMETHING GOES WRONG  A plain message explains it; the log is saved as NCE_Tool_log.txt in the output folder.  Send a screenshot of the log box.

CHANGES IN v3.0 (this release)
  * Tally Extract and NCE Tool merged into ONE program (nce_tool.py) with ONE window and a one-click flow: Tally -> files -> Excel.  ICAI template embedded.
  * Runs in the background (window never freezes), progress bar, "System check", "Install missing libraries", settings kept in your home folder.
  * Units selector in the window; never overwrites an existing workbook; clear checks for same file twice, wrong/corrupt files, unwritable folder.
  * Review sheet now lists every assumption/warning; Sales/Purchases cross-check made exact; Drawing no longer flagged as unusual.
  * Mapping: Tally typos (Expensess, Softwear, Intrest, Payble, G S T ...), Bank OCC A/c, Retained Earnings, partner ledgers named "A Contribution" /
    "B Current A/c" / "Drawing", income tax, bad debts, consultants, vehicles/AC/building classes; service firms (no purchases/stock) map "Gross Receipt" to services.
  * Handles Tally's own "Profit & Loss A/c" ledger in the extract (retained earnings), service entities with no stock, and printing titles of Note 11.
  Earlier: v2.5 units selector, v2.4 income mapping, v2.3 class drop-down, v2.2 Tally Extract, v2.1 repair-prompt fix + signature blocks.
