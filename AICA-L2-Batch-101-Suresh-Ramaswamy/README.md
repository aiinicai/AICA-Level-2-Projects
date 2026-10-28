# CA GST Filing Assistant Pro

**AICA Level 2 - Capstone Project (Batch 101)** | Author: Suresh Ramaswamy, Chartered Accountant (R Suresh \& Associates, Chartered Accountants)

A desktop tool that turns the different file formats clients send every month (Excel sales registers, one-invoice-per-sheet
workbooks, billing-software summary reports, PDF invoices) into **GSTR-1 CSV files for the official GST Offline Tool**, checks
the data, and reconciles it month by month and for the whole financial year.

> Everything runs \*\*locally on the CA's computer\*\*. The tool never logs in to the GST portal and never files anything.
> It prepares and checks data; the CA reviews it and files with his own DSC/EVC.

## The problem

A GST practitioner receives a different set of files from every client. Each month the data has to be re-typed or re-arranged
into the Offline Tool's formats, tables such as B2B, B2CS, HSN and the document series (Table 13) have to be built, and the
year's figures have to be reconciled with GSTR-3B and GSTR-9. This is slow and error-prone.

## What the tool does

|Area|What it does|
|-|-|
|Intake|Reads Excel registers, invoice-per-sheet workbooks, HSN-wise sales reports, date-wise output registers, text and scanned PDFs, and a one-file Master Template|
|Classification|Puts each invoice in B2B, B2CL, B2CS, exports, credit/debit notes, nil/exempt, advances|
|Validation|GSTIN structure and check digit, place of supply, rate and tax, HSN digits and placeholder codes, duplicates, document-number gaps, period checks|
|Documents (Table 13)|Builds document series from invoice numbers, including prefixes such as `DM/001/2026-2027`, and shows the gaps|
|Output|Writes every GSTR-1 CSV for the Offline Tool, with a CSV preview and a reconciliation report|
|Year view (tab 15)|Upload a whole financial year at once (a folder or ZIP with one sub-folder per month), month-wise YTD grid, and a GSTR-9 Table 4/5 worksheet; one click creates all returns of a financial year|
|Filed returns|Reads the GSTR-1, GSTR-3B and GSTR-9 PDFs downloaded from the GST portal|
|Reconciliation|Books vs GSTR-1, GSTR-1 vs GSTR-3B, GSTR-3B tax payable vs paid, GSTR-9 vs the year's returns, Books vs GSTR-9, and GSTR-9 vs GSTR-9C turnover. Every difference shows the likely reason and the usual remedy|
|Help on screen|A short "What this tab is for" line at the top of every tab|

Full feature list and version history: [docs/FEATURES\_AND\_CHANGELOG.md](docs/FEATURES_AND_CHANGELOG.md).
Design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Demo video

https://drive.google.com/file/d/1Lg8cdCbX8kLiHhi3GDGe-ZjbtPFALvYh/view?usp=drive\_link

## Screenshots (demo client only - no real data)

**Tab 3 - Return:** create one return, or all 12 returns of a financial year in one click.
!\[Return tab](docs/screenshots/01\_return\_tab.png)

**Tab 5 - Invoices (Excel / PDF):** upload files and extract; scanned PDFs are read with OCR and flagged for review.
!\[Invoices tab](docs/screenshots/02\_invoices.png)

**Tab 8 - Validation:** every error and warning, with a message on how to fix it.
!\[Validation tab](docs/screenshots/03\_validation.png)

**Tab 11 - GSTR-1 Summary:** totals by table, to compare with the Offline Tool before filing.
!\[GSTR-1 Summary](docs/screenshots/04\_gstr1\_summary.png)

**Tab 15 - YTD \& Annual:** the whole year side by side, with the reconciliation tables.
!\[YTD and Annual](docs/screenshots/05\_ytd\_annual.png)

## How AI was used

I am a practising Chartered Accountant. This tool automates my monthly GST return work, and I built it with AI
tools (Claude) that wrote the Python code from my instructions. The GST rules, the checks and the testing are mine.

AICA learning applied:

* **Prompting (Level 1, taken further in Level 2):** I explained my real filing workflow step by step, gave real
client files as examples of each format (sales registers, one-invoice-per-sheet workbooks, HSN and output reports),
and described the output I needed. When something was wrong I sent screenshots and specific feedback, and the AI
corrected it, round after round.
* **Day 1 - AI agents and core concepts:** the AI worked as an assistant that wrote, ran and fixed the code, while I
directed it and made the decisions.
* **Day 2 - Claude Cowork and practical AI agents:** I applied the same way of working in practice.
* **Day 3 - Computer vision and Python for automation:** the tool is written in Python and reads clients' Excel files
and scanned PDF invoices (OCR) to prepare GSTR-1 data automatically.
* **Day 5 - Privacy and business use cases:** everything runs on my own computer, no client data goes online, and this
repository contains demo data only.
* **Testing and validation:** I tested every version on real client file layouts, checked the figures against my books
and the Offline Tool, and reviewed each output before filing.

## Quick start (Windows)

1. Install Python 3.12 or later from python.org (tick "Add Python to PATH"; Tkinter is included).
2. Double-click `install.bat` once, then `run.bat`.
Or from a terminal: `pip install -r requirements.txt` then `python main.py`.
3. Try it with the demo files in [`sample\_data/`](sample_data/) (see `sample\_data/README\_SAMPLES.md`):

   * Tab 2: create a client (use any test GSTIN such as a demo one you generate; no real data is needed).
   * Tab 3: create a return, or click **Create ALL returns of the financial year**.
   * Tab 4: upload `Sample\_Master\_Template\_DEMO.xlsx` **after** changing "Sample file" to NO, or tab 5: upload
`Demo\_HSN\_Sales\_Report.xlsx` and `Demo\_GST\_Output\_Register.xlsx` and click Extract Data.
   * Tabs 8, 10, 11: validation, CSV preview, summary. Tab 12: generate the CSV files. Tab 15: year view.

Scanned PDFs need the free **Tesseract** OCR program (Windows installer from the UB Mannheim build). If the app cannot
find it, type the path in tab 14 (Settings), for example `C:\\Program Files\\Tesseract-OCR\\tesseract.exe`, and click Save Settings.

## Tests

`python tests/test\_core.py` and the other `tests/test\_\*.py` files (the UI test uses a stand-in for Tk:
`python -m tests.test\_ui`). All tests use synthetic data.

## Limits (please read)

* Offline Tool CSV headings are **provisional** until compared with the official samples (Settings tab does this).
* Tax is computed as taxable value x rate; compare with the Offline Tool summary before filing.
* PDF/OCR extraction is heuristic and every PDF line is flagged for review. OCR reads **printed** scans only; handwritten bills must be typed in.
* Figures read from the filed GSTR-1 / 3B / 9 PDFs and the typed GSTR-9C turnover figures should be verified on the GST portal.
* Each client's report layout needs a reader; new layouts are added as samples arrive.
* The GSTR-9 sheet is a worksheet, not a return. Tested mainly on Windows 11 with Python 3.12; the author's tests run on Linux with a Tk stand-in.
* Not legal or tax advice. The user is responsible for the returns filed.

## Privacy

No client data is included in this repository. The `sample\_data/` files are made-up. Do not commit real client files
(`.gitignore` already excludes the application's database and `clients/` folder).

## Licence

MIT - see [LICENSE](LICENSE).

R Suresh \& Associates, Chartered Accountants

