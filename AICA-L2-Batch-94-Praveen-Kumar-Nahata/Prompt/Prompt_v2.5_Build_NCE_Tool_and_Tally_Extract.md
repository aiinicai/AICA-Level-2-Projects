# MASTER PROMPT v2.5 - Build the "NCE Tool" and "Tally Extract" (offline Python tools for Indian CAs)

> READ THIS FIRST (for the person sharing / using this prompt)
> * The only way to get *byte-for-byte the same* tool is to share the finished `NCE_Tool.zip`. A prompt can make another AI rebuild a tool with the SAME features, layout, rules and tests, but not identical code. This prompt is written so that the rebuilt tool behaves identically on the points that matter; section 11 lists the acceptance tests that prove it.
> * ATTACH before sending: (1) the ICAI Non-Corporate-Entity (NCE) illustrative-format Excel ("the template"), (2) two Tally trial balances in the ODBC format of section 3A (one per year), (3) the Tally Balance Sheet and Profit & Loss PDFs of both years (4 PDFs), (4) optionally a screenshot of a reference "Trial Balance" mapping sheet. If something is not attached the AI must say so and label its assumptions - never invent data.
> * Use an AI that can run code and create files (Claude with file tools, etc.). Then paste everything below the line.

---------------------------------------------------------------------------------------------------

## 0. ROLE AND RULES

You are a senior Python developer who knows Indian accounting (partnership firms / LLPs / proprietorships audited by a Chartered Accountant; ICAI Guidance Note on the Non-Corporate-Entity (NCE) format, Schedule III style) and Tally (Tally.ERP 9 / TallyPrime).

1. Study ALL attachments before coding. Reply first with a short summary of each file (sheets, columns, sign convention, sample rows, PDF layout) and your plan. If I say "just study", only study.
2. Accuracy before cleverness. Never fabricate numbers. Missing data -> derive by a stated rule, label it "derived", surface it on the Review sheet.
3. Test everything yourself: run the tools on the attached samples, recalculate with LibreOffice (`soffice --headless --convert-to xlsx`), show the built-in checks pass, and state plainly what you could NOT test (live Tally, GUI windows if tkinter is missing in your sandbox).
4. Errors in the generated financials are acceptable at this stage, but EVERY figure must be correctable by me through dropdowns / editable cells (sections 5.4, 5.6, 5.7).
5. Offline tools for Windows (Mac bonus), Python already installed. Libraries: `openpyxl`, `pypdf` (fallbacks: `pdftotext -layout`, `pdfplumber`), `pyodbc` for Tally Extract. No internet at run time except one-time `pip install`.
6. Deliver ONE folder/zip named `NCE_Tool`: `nce_tool.py`, `tally_extract.py`, `NCE_ICAI_Template.xlsx` (cleaned, see 3C), `run_nce_tool.bat`, `run_nce_tool.command`, `run_tally_extract.bat`, `run_tally_extract.command`, `README.txt` (with a changelog). `.bat` files check Python, `pip install` missing libraries (`openpyxl pypdf` for the NCE tool; `openpyxl pyodbc` for Tally Extract) and start the tool. Every GUI field also has a CLI option. No `__pycache__`, no settings json in the zip.
7. Use absolute paths in your own scripts (your shell may reset its directory between calls). Version string: `VERSION` constant in each script (NCE Tool 2.5, Tally Extract 1.0).

## 1. THE TWO TOOLS

**Tool A - Tally Extract (`tally_extract.py`)**: reads a running Tally through ODBC (the user's own query) for two financial years and writes, per year, `<Client> FY24-25 Trial Balance.xlsx` (same layout as the user's manual Excel > Get Data > ODBC output + an "Info" sheet) and `<Client> FY24-25 Balance Sheet.pdf` / `<Client> FY24-25 Profit and Loss.pdf`.

**Tool B - NCE Tool (`nce_tool.py`)**: takes the two trial-balance Excel files (+ optional Tally PDFs) and generates ONE workbook in ICAI NCE format, fully formula-linked, with a "Trial Balance" control sheet of dropdowns, checks, auditor/assessee signature blocks and a units selector. Output name `NCE_<Client>_FY<latest year>.xlsx`, e.g. `NCE_ABC_Traders_FY2025-26.xlsx`.

Tool A's output must be accepted by Tool B, and Tool B must also accept hand-made files and the older Tally "Trial Balance" export (group rows + ledger rows with Debit/Credit columns).

## 2. CONTEXT (replace with your own)

Client e.g. a partnership firm / LLP / proprietorship (name, PAN, address), auditor = CA firm (name, FRN, partner/proprietor, membership no., UDIN). FY 1 April - 31 March. Capital and current accounts of partners, no share capital. Client examples seen so far: a trading + services firm (GST heavy) and a software LLP whose income sits under Direct/Indirect Incomes (see 5.3 income rules).

## 3. INPUT FORMATS - STUDY CAREFULLY

### 3A. Trial balance (Excel, ODBC extract)
Produced by Excel > Get Data > ODBC with `SELECT $Name, $Parent, $_PrimaryGroup, $ClosingBalance FROM Ledger WHERE $ClosingBalance != 0`.
Columns (headers literally `$Name`, `$Parent`, `$_PrimaryGroup`, `$ClosingBalance`; sheet usually "Query1"; header row may not be row 1; accept with/without `$`): ledger; immediate parent group; PRIMARY GROUP = the nearest *standard (reserved)* Tally group above the ledger (Sundry Creditors, Duties & Taxes, Bank Accounts, Stock-in-Hand, Sales Accounts, Capital Account ...) - not necessarily the top group (a user group under Current Liabilities has primary group "Current Liabilities"); closing balance SIGNED: debit (assets, expenses) NEGATIVE, credit POSITIVE.
The extract does NOT contain: the Profit & Loss A/c balance, opening stock, the closing-stock credit of the P&L. Names can have double spaces, trailing spaces, year prefixes ("24-25 Pending Bills ..."), typos ("Staff Salares", "GST Purhcase"), and differ between years; the stock ledger name changes between years ("Stock A/c" / "Opening Stock A/c") - its closing balance is the closing stock.
Support the legacy export as well.

### 3B. Tally PDFs
Condensed two-column Profit & Loss and Balance Sheet per year. Parse: kind (P&L/BS), period (`1-Apr-25 to 31-Mar-26`), entity, address lines, opening stock, closing stock, sales, purchases, nett profit, balance-sheet total. pypdf returns text WITHOUT whitespace between label and amount and sometimes spaced letters ("T o t a l"): use `\s*` in regexes, `max()` for totals, entity cut at "Profit & Loss/Balance Sheet/#", fallbacks `pdftotext -layout` then `pdfplumber`. Tally company names look like `NAME ( 25-26) (A)` or `NAME -(2024-25)`: clean year/(A) suffixes for display and file names; if the name is all upper-case use title case but keep "LLP".

### 3C. The ICAI NCE template
Open and map every sheet/formula before building. Traps:
 * ~80 broken external links + ~3,700 junk defined names cause Excel's "We found a problem with some content... repair" and a save prompt on close. FIX when loading: `load_workbook(path, keep_links=False)`, `wb._external_links = []`, delete ALL global defined names, never set `fullCalcOnLoad`. Verify the saved xlsx contains no `externalLinks` parts and opens without repair.
 * Delete the template's "Note" sheet. Keep Balance Sheet, Statement of P&L, Note 1 to 3, Notes to BS 4 to 6 / 7 to 10 / 11 / 12 to 18, Notes to P & L 19 to 26; add Review, Details, Disclosures, Trial Balance, Workings, Lists. Sheet order: Review, Details, Balance Sheet, Statement of P&L, Note 1 to 3, Notes to BS 4 to 6, 7 to 10, 11, 12 to 18, Notes to P & L 19 to 26, Disclosures, Trial Balance, Workings, Lists. Review is the active, selected sheet.
 * The template's Balance Sheet has an empty merged block G1:K4 - unmerge it before using column H (section 5.8).

## 4. TOOL A - TALLY EXTRACT (ODBC ONLY)

IMPORTANT DESIGN DECISION (learned on a real Tally): do NOT implement an XML-export extraction method. Ledger requests over Tally's XML/HTTP interface timed out on a real company. Extraction is by ODBC only. The only use of Tally's HTTP port (default 9000) is an optional, short, 30-second "List of Companies" collection request to fill the company boxes; if it fails, ignore it with a note.

### 4.1 ODBC extraction
`pyodbc`, DSN default `TallyODBC64_9000` (editable), run the user's exact query. ODBC reads only the company and period currently OPEN in Tally. Therefore, for each year (previous year first, then current), the GUI shows a prompt naming the expected company and period, e.g. `Open the previous year in Tally: "X -(2024-25)" (period 1-Apr-24 to 31-Mar-25). In Tally: Alt+F3 / Select Company, choose it, and go to the Gateway of Tally. Then press OK here.` Cancel aborts. Also query `$Name FROM Company` (all rows, `companies()`), the stock ledger's `$OpeningBalance` (best effort) and `SELECT $Name, $Parent FROM Group` (best effort - if unavailable synthesise the tree: every parent that is not the ledger's primary group and not a known group is attached under that primary group).
Clear errors if pyodbc/DSN is missing (list available DSNs from `pyodbc.dataSources()`), or Tally returns nothing.
SAFEGUARD: if the two years return IDENTICAL (name, closing balance) data, stop with: "Both years returned IDENTICAL data - Tally was still showing the same company when the second year was read. Run again and really switch the company in Tally before pressing OK."

### 4.2 Companies and years
Helper `company_end_year(name)` parses `(2024-25)`, `( 25-26)`, `(2024-2025)` -> end year (2025 etc.); `pick_companies(names, end_year)` returns (current, previous). GUI "Connect / list companies": union of ODBC companies and the HTTP list, fill both editable comboboxes; set the financial-year box to the latest year found; select current/previous by the year in names; log what was found. Company box blank = read the name from Tally. File names use `clean_entity(company)`.

### 4.3 Group tree / primary group
`Tree` from groups; `head(group)` = nearest reserved group walking up. Built-in default reserved groups and default parents (Sundry Creditors, Duties & Taxes, Provisions -> Current Liabilities; Sundry Debtors, Bank Accounts, Cash-in-Hand, Stock-in-Hand, Deposits (Asset), Loans & Advances (Asset) -> Current Assets; Bank OD A/c, Secured Loans, Unsecured Loans -> Loans (Liability); Reserves & Surplus -> Capital Account; primary: Capital Account, Current Assets, Current Liabilities, Fixed Assets, Investments, Loans (Liability), Misc. Expenses (ASSET), Suspense A/c, Branch / Divisions, Sales Accounts, Purchase Accounts, Direct/Indirect Expenses, Direct/Indirect Incomes). Tolerate parent "&#4; Primary" / "Primary" / empty (apply the default parent for standard groups). Sanitise illegal XML characters (`&#4;` etc.) in any XML text you parse.

### 4.4 Outputs
* Trial balance workbook: sheet "Query1" with header `$Name, $Parent, $_PrimaryGroup, $ClosingBalance` and one row per ledger with non-zero balance (debit negative / credit positive, numeric). Sheet "Info": key/value rows `company` (cleaned), `address`, `pan`, `period_from`, `period_to` (ISO dates), `opening_stock`, `closing_stock`, `nett_profit_computed`, `source`, `extracted_on`, `tool`. File name `<Client> FY25-26 Trial Balance.xlsx`.
* Stock and profit: closing stock = sum of Stock-in-Hand ledgers (debit). Current-year opening stock = PREVIOUS year's closing stock (override the ledger's own opening balance; log it). Previous-year opening stock is unknown: log a note (user gives the real P&L PDF or `--py-opening-stock` to Tool B). Nett profit (computed) = net credit of Sales/Purchase/Direct+Indirect Expenses/Incomes groups + closing stock - opening stock. Process the previous year first and pass its closing stock to the current year.
* PDFs (ODBC cannot make Tally print): compute them with a minimal dependency-free PDF writer (Helvetica, A4 landscape, multi-page) in Tally's condensed T-format. Balance Sheet: Liabilities (Capital Account, Loans (Liability), Current Liabilities, Suspense, Profit & Loss A/c with "Current Period" and "Less: Transferred") vs Assets (Fixed Assets, Investments, Current Assets with Closing Stock first, Misc. Expenses); sub-groups in standard order, ledgers alphabetically; Indian number format (1,23,456.00); sides equal. P&L: two blocks (trading, profit & loss) with opening stock, purchases, direct expenses, closing stock, sales, gross profit, indirect expenses/incomes, nett profit/loss. Footer: "Computed by Tally Extract vX from ledger closing balances (condensed Tally layout) - not a Tally print-out." Must parse back with Tool B's PDF parser and reproduce the real Tally totals (acceptance test 3).

### 4.5 GUI (tkinter, 900x780) - keep exactly these items
1 "How to talk to Tally (Tally must be open with the company loaded)": radio "ODBC (your Excel query; uses the company / year open in Tally; needs pyodbc)" (the only method; no XML radio); fields "Tally host / port" (localhost, 9000) and "ODBC data source name" (TallyODBC64_9000). 2 "Company and year": button "Connect / list companies"; combobox "Company for the CURRENT year (type or pick)"; combobox "Company for the PREVIOUS year - only if it is a different company in Tally (leave blank if same)"; "Current financial year ENDS in (e.g. 2026 = FY 2025-26)". 3 "Output": folder + Browse (default ~/Documents); checkboxes "Also produce the Balance Sheet and Profit & Loss PDFs", "Open the NCE Tool afterwards with these files" (calls `nce_tool.gui(preload=files)`), "Save Tally's raw answers for troubleshooting (folder tally_debug)" (writes the log to `tally_debug/log.txt`, also when an error occurs); scrolling log; big button "Extract from Tally". Errors appear in a dialog AND the log.
CLI: `--method odbc --host --port --dsn --list-companies (prints the company open in Tally) --company --company-py --fy -o --no-pdf --debug --nce`.

## 5. TOOL B - NCE TOOL

### 5.1 Inputs / years
Two trial-balance files (any order) + 0-4 PDFs + optional fields. Current vs previous year from, in order: Info sheet period, PDF periods, file name (FY25-26, 2025-26, "25-26"), closing stock vs PDF closing stock; else assume the second file is current and warn. Read the Info sheet (company, address, pan, period, opening/closing stock); prefer real PDF values; use Info only when PDFs lack them.

### 5.2 Derived entries
Add three grey "derived" rows per year so the TB nets to nil: (1) Opening stock (P&L PDF -> else previous-year closing stock -> else Info -> else user input -> else nil with warning); (2) Profit & Loss A/c (PDF nett profit, else derived); (3) an "Excluded" balancing row for the closing-stock credit. Verify TB nets to nil, Balance Sheet balances, P&L block nil. Log every assumption.

### 5.3 Mapping engine (ledger -> ICAI Note Label -> Line Item)
Rules from head group + parent group + name keywords. Merge ledgers across years: exact name only within the same head group, then fuzzy >= 0.82, then containment pass - never across head groups. Cover capital/current accounts (detect partner names), loans, bank OD, creditors, duties & taxes, outstanding/provisions, fixed assets by class, investments, stock, debtors, cash, bank, FDs ("F.D.", "FDR"), deposits (guarantee/EMD/BG), loans & advances, GST receivable/ITC/refund, TDS, advance tax, prepaid, sales, other income, purchases, direct expenses, employee costs (incl. typo "Salares"), finance costs, depreciation, other expenses, partners' remuneration and interest.
INCOME RULES (important, learned from a software LLP): `SERV` keyword regex = service|job work|labour|contract|consult|rental|repair|software|develop|professional|fee(s)|support|maintenance|amc|subscription|licence|hosting|saas|it|export|outsourc|manpower|training|implementation|website|app|design|testing|royalt|commission.
 * Sales Accounts: SERV match -> Note 19(b) Sale of services (key `N19-r7`), else Note 19(a) Sale of products (`N19-r6`).
 * Direct/Indirect Incomes: interest -> `N20-r15`; dividend -> `N20-r16`; gain on investments -> `N20-r17`; grant/subsidy -> `N19-r8`; discount/rebate/round/forex/exchange/sundry balance/written back/misc/rent received/insurance claim/profit on sale/scrap/incentive/refund -> `N20-r18` (other non-operating income); Direct Incomes otherwise -> Note 19 (services unless the name says sales/goods/product/material and not SERV); Indirect Incomes with "sale(s)/goods/products" -> `N19-r6`; with SERV and not "other/misc" -> `N19-r7`; else `N20-r18`.
Guessed mappings are orange and listed on Review.

### 5.4 "Trial Balance" control sheet
One row per ledger. Columns: A Sl | B Ledger | C Parent Group (dropdown) | D Head Group (dropdown) | E Note No | F Note Label (dropdown, yellow) | G Line Item (cascading dropdown, yellow) | H/I closing balance CY/PY (Cr-Dr) | J Sign | K/L display amounts CY/PY | M Validation | N Key | O Type | P Nature | Q Appears in | R Auto-map basis | S lookup helper | U/V helper columns for units (5.8). Header row 4, data from row 5. Statements pull by SUMIFS on column N (Key).
 * Note Label list = all ICAI notes; Line Item list = only lines of the chosen label via DV formula `OFFSET(Lists!$B$1,MATCH($F5,Lists!$A$1:$A$N,0)-1,0,COUNTIF(Lists!$A$1:$A$N,$F5),1)` (write DV formulas WITHOUT a leading "="). Parent/Head dropdowns come from Lists J/K and accept free text.
 * Lists sheet: A label, B line, C key, D nature, E type, F appears in, G label|line, H note no, I unique labels, J parents, K heads, M:O unit table (5.8).
 * Validation symbols: OK / label-line mismatch / unusual opposite-side balance / guessed (orange) / derived. Test "derived" BEFORE "abnormal balance". Show Note Label + Line Item text like commercial software. Autofilter, frozen panes, colour legend.

### 5.5 Statements and notes
Balance Sheet and Statement of P&L in ICAI layout, every cell a formula (no hard-coded numbers), CY and PY columns. Notes 1-26 as in the template. Gross presentation (each ledger on its natural side) -> total larger than Tally's netted total; explain on Review. Workings sheet: A closing stock (derived/override; toggle C12 Y/N P&L treatment), B fixed assets (5.6), C partners (ratios, interest, capital introduced; editable), D checks, E Tally PDF cross-check (only real PDFs). Disclosures sheet. Review sheet (read first): live checks - BS balances CY/PY, profit = P&L A/c, closing stock agreement, TB nets to nil, partner ratios 100%, remuneration 100%, PDF nett profit and sales agree, unmapped = 0 - plus assumptions and "still to complete". Details sheet + signature blocks at the bottom of BOTH Balance Sheet (from row 55) and P&L (from row 52): auditor (firm, FRN, CA name, designation, membership no., UDIN), assessee (firm, address, up to 4 signatories with designation), place, date. Auditor details are remembered in `nce_tool_settings.json` next to the script.

### 5.6 Workings B - fixed assets table and the editable Class list
Table from row 16 (title), header row 17, data from row 18: Ledger | Class (Note 11) | Dep. rate (editable) | WDV prior year-end | WDV current year-end | CY additions | CY depreciation | PY dep rate-implied | PY dep allocated | WDV at start of PY | CY deductions | CY dep existing | CY dep new assets; Total row; check rows. Default class from name rules and default rates {Freehold land 0%, Buildings 10%, Plant and Equipment 15%, Office equipment 15%, Furniture & Fixtures 10%, Vehicles 15%, Others 15%}; rate inferred from the ledger movement when plausible (2%-60%).
 * Class column has a data-validation dropdown whose source is the EDITABLE list in Workings O18:O24 (7 slots = the 7 columns of Note 11; header O17 "Class list (drop-down source)", yellow cells; title O16). Note 11 column headings (row 7, C:I) are formulas `=Workings!$O$18..$O$24` and all Note 11 SUMIFS criteria reference those cells, so renaming a class renames the columns and flows through. Check cell O27 (must be 0) counts ledgers whose class is not in the list; O28 explains "re-pick the new name after renaming". Max 7 classes.

### 5.7 GUI and CLI
tkinter: pick two TB files, up to four PDFs, assessee fields (entity, address, PAN, nature), signatories text box ("Name, Designation" per line), auditor fields (remembered), place, date, previous-year opening stock, "Generate" -> save dialog with suggested file name -> log -> success box. `gui(preload=files)` pre-fills the lists. CLI options: `--entity --pan --nature --py-opening-stock --address --signer (repeat) --aud-firm --aud-frn --aud-name --aud-desig --aud-mno --udin --place --date -o --units`.

### 5.8 UNITS SELECTOR (exact design)
One dropdown converts every figure: Actuals / Hundreds / Thousands / Lakhs / Crores.
 * Selector cell `'Balance Sheet'!H3` (yellow, bold, blue, centred, medium border, DV list "Actuals,Hundreds,Thousands,Lakhs,Crores"), label H2 "SHOW ALL FIGURES IN  (drop-down)", H4 divisor `=IFERROR(INDEX(Lists!$N$2:$N$6,MATCH($H$3,Lists!$M$2:$M$6,0)),1)`, H5 label `=IFERROR(INDEX(Lists!$O$2:$O$6,MATCH($H$3,Lists!$M$2:$M$6,0)),"Rs.")`, H6 grey help text; column H width 34 (outside the print area A:F; unmerge G1:K4 first). Unit table Lists!M1:O6: Unit / Divisor / Label = Actuals 1 "Rs."; Hundreds 100 "Rs. Hundreds"; Thousands 1000 "Rs. Thousands"; Lakhs 100000 "Rs. Lakhs"; Crores 10000000 "Rs. Crores". Default selection Actuals (CLI `--units`).
 * Scaling happens where amounts LEAVE the Trial Balance / Workings, never twice: Trial Balance helper columns U (=IF(ISNUMBER(K5),K5/'Balance Sheet'!$H$4,0)) and V (same for L), same number formats, grey font, for rows 5 to last+60. In the display sheets (Balance Sheet, Statement of P&L, Note 1 to 3, Notes to BS 4 to 6, 7 to 10, 11, 12 to 18, Notes to P & L 19 to 26, Disclosures) rewrite formulas: (a) `'Trial Balance'!$K$a:$K$b` -> `$U$a:$U$b` and `$L` -> `$V`; (b) every SUMIFS whose sum range is a Workings amount column (D-M of the fixed-asset table) -> `(SUMIFS(...)/'Balance Sheet'!$H$4)`; (c) single-cell references to Workings amount cells (number format contains `#,##0` and the cell is not a plain text such as the Y/N toggle; e.g. closing stock C10/D10, opening stock C11/D11, D6, partner capital table) -> `(Workings!X/'Balance Sheet'!$H$4)`; ratios, toggles, class names and criteria ranges are NOT scaled; (d) the Balance Sheet balance test `ABS(D24-D46)<0.01` -> `<0.01/'Balance Sheet'!$H$4`.
 * Workings and Review formulas that read the statements are multiplied back: `('Balance Sheet'!D24*'Balance Sheet'!$H$4)` so all checks stay in rupees.
 * Every "(Amount in Rs.)" heading becomes `="(Amount in "&'Balance Sheet'!$H$5&")"`; the cell "Total capital of the firm (Amount in  Rs.)" likewise (prefix text kept). Typed non-zero amounts in display sheets are NOT rescaled - log a warning; user adjustments belong in rupees in Workings/Disclosures. Totals are computed from unrounded values (displayed lines may differ from totals by rounding) - state this in README.

## 6. THINGS A TRIAL BALANCE CANNOT TELL (label assumptions)
Original cost of fixed assets (Note 11 shown at WDV), partners' profit-sharing ratio / remuneration split (equal by default), MSME split, debtor ageing, long/short-term split of loans and deposits, related parties, contingent liabilities (type into Disclosures).

## 7. README.txt (changelog)
Document usage, Tally set-up (ODBC DSN, port 9000), the prompt-per-year flow, previous-year opening stock limitation, units selector, class list, income rules, and a changelog: v2.1 Excel-repair fix + signature blocks; v2.2 Tally Extract; v2.3 editable class drop-down; v2.4 income mapping; v2.5 units selector.

## 8. KNOWN PITFALLS (do not repeat)
* Excel repair prompt (external links, junk names). * Apostrophes inside single-quoted strings in sheet text -> use double quotes. * Merging ledgers across head groups gave a wrong PY profit (121,135.50). * pypdf text has no spaces -> regexes with mandatory `\s+` fail. * Typos/odd ledgers ("Staff Salares", "GST Purhcase", "Bank Guarantee", "ICICI F.D.") need explicit rules. * Derived row flagged "!" because the abnormal-balance test ran first. * XML ledger requests time out on real Tally - ODBC only. * Tally's "Primary" is `&#4; Primary`. * Windows ODBC reads only the OPEN company - always prompt per year and keep the identical-data safeguard. * openpyxl workbooks have no cached values - formulas calculate on opening; verify with LibreOffice. * Merged cells are read-only in openpyxl (unmerge before writing). * Sandbox may lack tkinter: test logic by CLI and say the GUI window was not run. * `Print area cannot be set` openpyxl warning on load is harmless.

## 9. COMMUNICATION
Ask clarifying questions ONLY for decisions that change what you build; otherwise choose defaults and state them. Show progress with a task list; send files as produced. Final message: (a) what each tool does in 5 lines, (b) how to run (bat files), (c) Tally settings needed, (d) candid list of what is untested/approximate, (e) how to report a failure (screenshot of the log window; `tally_debug/log.txt`).

## 10. DELIVERABLE CHECK
Folder contents exactly as in section 0.6; scripts compile; `--help` works; README present.

## 11. ACCEPTANCE TESTS (run and report all)
1. `py_compile` both scripts; `--help` both.
2. Mock Tally: replace `pyodbc` with a fake module serving your two TB files (queries: ledgers, stock opening balance, Group (raise to test fallback), Company) and (optionally) a mock HTTP server for the company list. Run Tool A for both years with the prompt callback switching the fake year; show logs. Also test the identical-data safeguard (don't switch the year) and `--list-companies`.
3. Extracted TB files contain the same ledgers/balances as the originals; computed PDFs reproduce the real Tally totals of the attached PDFs (e.g. 8,16,63,259.79 and 6,85,82,726.82; nett profit 72,50,100.84) and parse back in Tool B (kind, period, entity, cs, os, sales, purchases, profit, bs_total).
4. Tool B on the extracted files (TB only, and TB + PDFs): all Review checks OK after LibreOffice recalculation; scan all sheets for #REF!/#NAME?/#VALUE!/#DIV/0!/#N/A (explain false positives such as address text starting with "#").
5. Open-without-repair: no externalLinks parts, no junk names, no fullCalcOnLoad; file a few hundred KB.
6. Dropdown test: change a Note Label/Line Item of one ledger in the saved file, recalc, confirm statements move and still balance.
7. Class list test: rename a slot in Workings O18:O24 and re-pick the class on affected ledgers; Note 11 headings follow, totals unchanged, O27 = 0.
8. Income rules test: `classify()` on sample names (Sales Accounts "Software Development Charges" -> N19-r7; "Sales" -> N19-r6; Direct Incomes "Professional Fees" -> N19-r7; Indirect Incomes "Software Services Income" -> N19-r7, "Discount Received" -> N20-r18, "Interest on FD" -> N20-r15, "Other Income" -> N20-r18, "AMC Charges" -> N19-r7).
9. UNITS TEST (automatic): build the workbook; for each unit in Actuals, Hundreds, Thousands, Lakhs, Crores set `'Balance Sheet'!H3`, recalc with LibreOffice, and compare EVERY numeric cell with a `#,##0` number format in the nine display sheets against the Actuals values divided by the divisor: 0 mismatches (about 1,160 cells on the ABC sample), 0 Excel errors, Review checks unchanged (18 OK / 0 CHECK on the sample), Balance Sheet D52 shows "Balanced", headings read "(Amount in Rs. Lakhs)" etc.
10. Failure modes for Tool A: pyodbc missing, wrong DSN, Tally closed/no company, empty result, cancelled prompt - each gives an understandable message (no raw traceback) and the window stays usable.

Begin by reading the attachments and replying with your study summary and plan. Then build, test and deliver.
