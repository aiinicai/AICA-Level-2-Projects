Customer Ageing Analysis
Business Unit-wise Ageing Splitter
A desktop application for finance/accounting teams that reads a customer-wise ageing Excel workbook, splits it Business-Unit-wise, and produces one professionally formatted Excel file per Business Unit — each containing a full Ageing sheet, a >180 Days review sheet, and a Negative Balances review sheet.
This is the single-file edition — everything lives in `customer_ageing_app.py`, so it can be run directly from IDLE or the command line with no other project files required.
---
1. Required Libraries
Library	Why it's needed
`pandas`	Reads/parses the Excel data and performs grouping and summary calculations.
`openpyxl`	The Excel engine used both to read `.xlsx` files and to build the professionally formatted output workbooks (fonts, fills, borders, freeze panes, autofilter, conditional formatting).
`customtkinter`	The modern, professional-looking GUI framework the desktop application is built with.
`matplotlib`	Renders the Business-Unit-wise pie chart on the pre-generation dashboard (embedded inside the CustomTkinter window).
`pillow`	Image-handling dependency required by `customtkinter`.
`python-dateutil`	Fuzzy-extracts a period-end date embedded in title text (e.g. "...as at 30-Sep-2026"). Already installed as a `pandas` dependency, but listed explicitly to be safe.
Install everything with one command:
```bash
pip install pandas openpyxl customtkinter matplotlib pillow python-dateutil
```
---
2. Folder Structure
```
customer_ageing_app.py   <- the entire application (single file)
logs/                     <- a timestamped log file is written here every run
output/                   <- suggested default output folder (you choose any
                             folder you like from within the app)
README.md                 <- this file
```
---
3. How to Run the Application
From IDLE:
Install the libraries above in the same Python environment IDLE uses.
Open `customer_ageing_app.py` in IDLE.
Press F5 (or Run → Run Module).
From a terminal / command prompt:
```bash
pip install pandas openpyxl customtkinter matplotlib pillow python-dateutil
python customer_ageing_app.py
```
Either way, the application window opens and a `logs/` folder is created next to the file, containing a timestamped log of that run.
---
4. Step-by-Step Usage
Click Browse next to Customer Ageing Workbook and select your input `.xlsx` file.
Click Browse next to Output Folder and choose where the generated Business Unit files should be saved.
Click Validate Data.
The app loads the workbook and tries to automatically identify the Business Name, Customer Code, Customer Name, Outstanding Amount, Profit Centre, and ageing-bucket columns purely from their header text — no fixed column positions.
Any title/description rows above the real header row (e.g. a company name or report title) are detected and skipped automatically.
If any required field can't be identified with high confidence, a Confirm Column Mapping screen appears — pick the correct column from the dropdown for each field and click Confirm & Continue.
Validation issues are shown in the log: warnings (e.g. a few missing customer names) don't stop the process; critical issues (e.g. no Business Name column at all) stop processing with a clear explanation so you can fix the file and try again.
A Dashboard window opens automatically once validation succeeds, showing:
The detected period-end date — read from a dedicated date column if one exists, otherwise extracted from descriptive title text (e.g. "...Customer Wise Ageing Report as at 30-Sep-2026").
A Business-Unit-wise outstanding-balance pie chart.
The Top 5 balance customers.
A Business-Unit-wise summary table (records, total outstanding, >180 days, negative balance).
Review the numbers here before anything is written to disk.
Click Generate BU Files (on the dashboard, or the button in the main window once validation has completed). One Excel file is created per Business Unit in your chosen output folder.
Click Open Output Folder to jump straight to the generated files.
---
5. How to Prepare the Customer Ageing Excel File
Use a single worksheet containing one row per customer record (a customer may legitimately appear more than once — the app does not auto-consolidate duplicate customers).
Include a Business Name / Business Unit column — every unique value becomes a separate output file.
Include Customer Code and Customer Name columns.
Include a Total Outstanding Amount column (recommended). If missing, the app calculates it automatically by summing all detected ageing bucket columns.
Include ageing bucket columns using descriptive headers that mention "days" and the day thresholds, e.g.:
`Amount in < 90 days bucket`
`Amount in > 90 days and <=180 days`
`Amount in > 180 days and <= 360 days bucket`
`Amount in > 360 days`
A 5-bucket layout (e.g. adding `> 360 and <= 730` / `> 730`) is also fully supported — the app reads the day numbers straight from the header text, so wording and bucket count can differ from file to file.
A Profit Centre column is optional but enables profit-centre-wise sub-summaries on the >180 Days sheet.
A date column, or a period-end date embedded in a title/description row above the table, is optional but lets the dashboard display the period automatically.
Title/description rows (company name, report title, "Confidential", etc.) are fine above the actual table — the app detects the real header row automatically.
Example input structure
Business Name	Profit Centre	Customer Code	Customer Name	Amount in <90 days	Amount in >90 and <=180	Amount in >180 and <=360	Amount in >360 days	Total Outstanding Amount	As at Date
Business A	PC-North	CUST0001	Alpha Traders	5,000	2,000	1,200	300	8,500	31-Mar-2026
---
6. The ">180 Days" Logic
For every ageing-bucket column, the app reads the header text and extracts the day thresholds mentioned in it (e.g. "> 180 and <= 360" → lower bound 180). Any bucket whose lower day-bound is 180 or more is classified as an "over 180 days" bucket. The app sums all such bucket amounts for each customer record to get Amount > 180 Days. Any record where this sum is greater than zero is included on the >180 Days sheet, together with:
Total Outstanding Amount
Amount > 180 Days
% of Balance > 180 Days (`Amount > 180 Days ÷ Total Outstanding Amount`)
A summary block at the top of the sheet shows the record count, total >180 amount, and (where available) profit-centre-wise and customer-wise subtotals.
---
7. The Negative Balance Logic
Any record whose Outstanding Amount is less than zero is extracted onto the Negative Balances sheet. These are labelled:
> **"Negative Balance – Review Required / Possible Advance"**
The application deliberately does not assume these are customer advances — a negative balance could equally be a credit note, an excess receipt, a credit balance, or a data-entry issue. It is flagged for finance/business review only. A summary block shows the record count and total negative balance, plus a customer-wise breakdown.
---
8. How to Package as a Windows .exe
```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "CustomerAgeingAnalysis" customer_ageing_app.py
```
The standalone `.exe` is created in the generated `dist` folder. Distribute `dist/CustomerAgeingAnalysis.exe` — end users don't need Python installed to run it.
Notes:
If matplotlib's charting fonts look different when run from the `.exe`, that's cosmetic and doesn't affect the generated Excel files.
If Windows SmartScreen warns about an "unrecognized app" the first time the `.exe` runs, that's normal for unsigned executables built with PyInstaller — click More info → Run anyway.
---
9. Troubleshooting
"No module named 'customtkinter'" (or pandas / openpyxl / matplotlib / dateutil)
→ Run: `pip install pandas openpyxl customtkinter matplotlib pillow python-dateutil`
Column mapping screen keeps appearing / a required field can't be found
→ Your header wording is unusual. Pick the right column manually in the mapping screen — the app remembers your choice for that run. Consider renaming the header in the source file for future runs.
"No ageing-bucket columns detected"
→ Make sure your bucket column headers mention "days" and clear numeric thresholds (e.g. "Amount in > 180 days and <= 360 days"). Headers with no numbers at all can't be auto-classified.
"Period not detected in source file"
→ Make sure a date appears either in a dedicated date column, or somewhere in a title/description row above the table (e.g. "...as at 30-Sep-2026"). Very ambiguous formats (e.g. a month/year with no day) may not parse reliably.
">180 Days" or "Negative Balances" sheet is empty for a Business Unit
→ Expected if that Business Unit genuinely has no records meeting the condition — not an error.
Generated Excel file won't open / looks corrupted
→ Make sure no other program (e.g. a previous run's file open in Excel) is locking a file with the same name in the output folder, then try again.
The application window appears blank or fonts look off
→ Update customtkinter: `pip install --upgrade customtkinter`
Very large input files (100,000+ rows) run slowly
→ Expected with pure-Python/openpyxl Excel writing; let the progress bar and log run to completion — each Business Unit is processed and logged individually so you can track progress.
---
10. Workflow Summary
```
Customer-wise Ageing Excel
        ↓
   Validation
        ↓
  Column Mapping (auto, with manual override if needed)
        ↓
  Business Unit Identification
        ↓
  BU-wise Ageing Split
        ↓
  >180 Days Extraction
        ↓
  Negative Balance Extraction
        ↓
  BU Excel Files (Ageing / >180 Days / Negative Balances)
```
