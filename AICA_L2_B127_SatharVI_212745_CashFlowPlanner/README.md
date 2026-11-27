# Construction Cash Flow Planner

A local Windows desktop prototype for preparing a construction contractor’s weekly management cash-flow forecast. The supplied company, projects, instruments, dates and amounts form a fictional training case. All processing takes place on the computer.

## Use a dated weekly cash-flow folder

Select the weekly folder containing the ACTCF, CF-Detailed, CF-Proj and PDC PDFs, together with the net creditors, other creditors, LC and material purchase workbooks. The app identifies a prior `CF-DD-MM-YYYY.xlsx` supplied alongside them or finds the preceding dated weekly folder. It displays the baseline filename before export. **Choose baseline…** handles a workbook stored separately or an ambiguous choice. An existing workbook dated for the current snapshot is treated as the output.

Click **Generate Excel…** to save the new dated workbook. If the normal output already exists, the app suggests a separate review filename. The active cash-flow sheet retains its formulas and layout. **Refresh review** records the input hashes, actual cutoff, source controls and any management decisions requiring review. The **Sources and review notes…** button shows this information before export.

The dated importer supports the ERP report and CF-YY worksheet family tested with the November workflow. It reads figures directly from the eight reports. For a completed run it can reuse management decisions after matching all eight source hashes and the preceding workbook hash. An available prior source archive also lets it track account and expense rows when they move. A copied folder works with an included baseline; keeping access to the preceding archive helps preserve the management adjustments. Files with unresolved exclusions or inconsistent cost headings produce a labelled draft or identify the exact dependency that needs attention. Month rollover requires a baseline with the new month's actual and remaining columns already prepared. The source reports, previous workbook and existing output are preserved.

## Try the demo

1. Extract the ZIP to an ordinary folder. Keep `CashFlowPlanner.exe` beside `demo_week`.
2. Double-click `CashFlowPlanner.exe`. Choose **Use demo folder**, or choose **Select folder…** and select `demo_week` itself.
3. Select **View monthly cash flow**. The current month opens with separate actual-to-date and remaining-forecast columns. Select **Combine current month** to see the opening balance, movements for the whole month and forecast closing cash. The toggle changes the screen view. The Excel workbook retains its split columns.
4. Choose **Generate Excel…** and save a new `.xlsx` file. Choose **Open saved workbook** to inspect it. The file in `example_output` is a reference run.

The portable Windows x64 executable includes its Python runtime. Excel is useful for reviewing formulas. The app can prepare the workbook without opening Excel.

## Test the monthly controls

- **Compare with previous week** compares the same calendar month across two cutoffs. The dated workflow uses the preceding CF workbook. The demo includes a fictional 13 November export, `demo_week/Previous cash flow.xlsx`. Select November to see previous closing cash of OMR 38,899.375 and current closing cash of OMR 33,899.375. Canal Works moved OMR 5,000 of collections from November to December. The variance is this week less the preceding week. An em dash marks an unavailable comparison.
- **View supporting detail** follows the selected amount. In the November remaining forecast, select **Post-dated cheques**. CH-020 and CH-021 contribute OMR (6,000.375) together. Replacement and security cheques show zero included cash. Double-click a record to read its complete source location and treatment. For figures supplied as workbook assumptions, the detail gives the sheet, cell and available formula.
- Use the scrollbars to move across months and down the worksheet. Cash-flow item labels and month headings stay visible. Click an amount, use the arrow keys to move, and press Enter to see its support. **Overview** returns to folder selection.

## Expected results

All figures below are OMR. The source cutoff is 20 November 2026. Parentheses indicate outflows or deficits.

| Period | Opening | Receipts | Payments | Net funding | Closing |
|---|---:|---:|---:|---:|---:|
| October 2026 closed | 39,000.000 | 32,000.000 | (26,600.000) | 0.000 | 44,400.000 |
| November actual through the 20th | 44,400.000 | 42,000.000 | (35,250.250) | (900.000) | 50,249.750 |
| November remaining forecast | 50,249.750 | 24,500.000 | (40,850.375) | 0.000 | 33,899.375 |
| December forecast | 33,899.375 | 40,250.000 | (81,200.125) | 0.000 | (7,050.750) |
| January 2027 forecast | (7,050.750) | 47,000.000 | (40,450.000) | 15,000.000 | 14,499.250 |

Closing cash equals opening cash plus receipts, signed payments and signed funding. December has the lowest projected period-end balance. The monthly data cannot identify a lower daily balance within a period.

## Two hands-on checks

**Defer a collection.** Copy the entire `demo_week` folder. In the copy, open `Starting Model.xlsx`, go to **Plan**, and change the month in C3 for PLAN-001 from `2026-11` to `2027-01`. Save and close the source workbook. Select the copied folder and generate a second output. The November projected close should fall to **17,899.375**, the December projected close should fall to **(23,050.750)**, and the January close should remain **14,499.250**. This moves a receipt without changing the contract total.

**Trace a replacement.** In the exported workbook, filter **Cash entries** by party **Birch Steel**. CH-022 and CH-023 have zero included cash. Their amounts total **3,750.125**, which appears once as a December payment under LTR-704. **Reconciliations** shows the instrument match. To test an error, change the LTR-704 amount in a copy of the LC file and reselect that folder. The app identifies the mismatch before export.

## Weekly inputs

Use the demonstrated headers, worksheet names, field types and PDF layouts. Each workbook input tab starts with the source role, ISO cutoff date and currency in A1:C1. Headers are in row 2 and data starts in row 3. The PDFs contain an internal cutoff, currency, printed column headings and a per-page record count. Optional filename suffixes of the form `-DD-MM-YYYY` are accepted. The internal dates govern the run.

| File | Use |
|---|---|
| Starting Model.xlsx | **Settings** sets company and forecast horizon. **History** supplies signed cash flows and opening/closing controls for completed months. **Projects** has billable values including retention and cumulative collections before the current month. **Plan** supplies manual receipts, retention, overhead, funding, tax and other budget entries. |
| CF.pdf | Opening cash, closing cash and every signed month-to-date category control, including explicit zero values. The ACTCF filename is also accepted. |
| CF-Detailed.pdf | Dated transactions with reference, project, category and signed amount. Project-level entries sum to the summary controls. |
| PDC.pdf | Cheque number, party, cheque date, amount, status and optional replacement LTR. The cheques outstanding before or within the current month enter the remaining forecast. |
| CF-Proj.pdf | Supplies future PDC Payable only. The future totals must agree to eligible cheques in this demo’s full register. |
| Creditors.xlsx | **Net** holds payment schedules after netting issued commitments. A row marked Deferred is excluded. The Ceditors spelling is supported. |
| Other Creditors.xlsx | **Payables** holds other expense obligations with an explicit due date and settlement status. |
| LC.xlsx | **Maturities** holds outstanding LC/LTR amounts by maturity date. A replacement must match the reference, party and total of the replaced cheques. |
| Material Purchase.xlsx | **CF-DTLD** holds remaining materials, labour and site overhead by project and month. Each project/category/month needs an explicit amount, including zero. |

Identifiers and month labels are text. Amounts are entered as numbers with up to three decimals. Payment schedules use positive magnitudes. History, actuals and manual plans use signed cash movements. The model treats a blank required amount as an error. The manual plan is a list of scheduled items. An absent optional budget line contributes zero.

## What the workbook contains

- **Cash flow** shows the completed months, actuals to cutoff, the remaining current-month forecast and the following months. Each period’s closing cash becomes the next opening balance.
- **Period summary** combines both current-month columns and gives totals for each covered calendar year. A year’s opening and closing balances come from its first and last covered periods.
- **Cash entries** links each included or excluded movement to its source file and PDF page/row or workbook sheet/row.
- **Reconciliations** records actual-category checks, opening and closing controls, replacement matches, future PDC totals and project collection totals as checked at generation.
- **Sources** records the internal date and content hash for each of the nine files.

The app reads one folder per run. Selecting the folder again refreshes the preview. Export checks that its source versions match the preview, writes a new file, and reopens it to check the closing balances.

## Prototype scope

The fictional **Demo v1** workflow uses a fresh output workbook in OMR and keeps historical amounts and manual forecast assumptions from its starting model. The dated workflow described above exports a copy of the native model and updates its mapped inputs and link caches. Original text PDFs are supported. Scans, macro-enabled workbooks and unrelated ledger layouts need their own mappings. Tax figures represent management planning assumptions.

The project collection control assumes all remaining billable collections, including retention, are scheduled within the model horizon. The demo uses one stable obligation reference across its schedules. Settlement and replacement statuses and the net-of-commitments basis of the supplied schedules are source assumptions. A human still needs to review liabilities described under different references or source data with incorrect classifications.

The question box uses offline TF-IDF text matching to select among five supported questions. Answers use the reconciled figures and cite cells in the generated workbook. It requires no API key or language model.

## Run from Python

From this project folder, using a Python installation with Tk support:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python app.py
```

For a command-line run:

```powershell
.\.venv\Scripts\python app.py --input demo_week --output my-test.xlsx
```

For the regression tests:

```powershell
.\.venv\Scripts\python -m pip install -r tests/requirements.txt
.\.venv\Scripts\python -m unittest discover -s tests -v
```

The Windows executable was built with Python 3.15.2 and PyInstaller 6.22.3. To rebuild, install that PyInstaller version in the project environment and run the following command from the project folder. Place the resulting executable next to a copy of `demo_week`.

```powershell
.\.venv\Scripts\python -m PyInstaller --onefile --windowed --noupx --icon assets/cashflow.ico --add-data "assets:assets" --exclude-module numpy --exclude-module PIL --exclude-module cryptography --exclude-module reportlab --name CashFlowPlanner app.py
```
