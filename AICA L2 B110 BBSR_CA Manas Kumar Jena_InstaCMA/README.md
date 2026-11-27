# InstaCMA

Developed by CA Manas Kumar Jena  |  Contact: +91 9337820330


InstaCMA is a Windows desktop application that prepares **CMA data for bank loan proposals** (cash credit, term loan, or both) in the firm's own CMA format, which is built into the app.

You upload the client's statements as PDF (normal or scanned), Excel (any layout) or photos. The tool then:
- reads and groups every line (Schedule III for companies, T-form for others),
- tallies each actual year to the rupee,
- builds the estimated and projected years,
- applies the drawing-power rule,
- runs every bank test.

It produces **one formula-linked Excel workbook and one A4 PDF of all pages**.

## Quick CMA (one screen)

1. **Choose file** – the client's P&L and balance sheet (Excel or PDF).
2. Enter the **CC limit** and, if any, the **term loan** (amount, rate, tenure, EMI or equal principal).
3. Press **1. Calculate** – bank tests are shown; set each actual year as Audited, Actual or Provisional.
4. Press **2. Make Excel** and **3. Make PDF** – each asks where to save.

In the estimated and projected years InstaCMA keeps every bank rule met automatically, without touching
audited / actual / provisional figures:

| Rule | Requirement | Met by |
|---|---|---|
| Drawing power | above the CC limit | debtor days from the actual trend |
| Turnover | at least 5x the CC limit | sales growth raised where short |
| DSCR | 1.5 to 2.5 | gross profit % set year by year |
| Cash and bank balance | positive (min. 2% of sales) | advances realised, creditors / outstanding expenses, capital introduced |
| Current ratio | at least 1.33 | capital introduced |
| TOL / TNW | at most 3 | capital introduced |

Every adjustment is listed in the result box and shown in the workbook as a blue input with a comment.

## Key Features

**Input**
- **PDF, scanned PDF, Excel or photo**, mixed freely. Excel is read directly. PDFs and photos are read by **any AI model** you choose:
  - Google Gemini, Anthropic Claude or OpenAI;
  - any OpenAI-compatible service, such as OpenRouter, Groq or DeepSeek;
  - a **local Ollama model**, which keeps everything offline;
  - a backup provider, used if the first fails.

  Without AI, the tool falls back to OCR (Tesseract) and keyword rules.
- **The firm's own T-form layout is understood**:
  - inner and outer columns;
  - the capital account (opening capital / net profit / drawings / closing capital);
  - fixed assets shown as "less depreciation";
  - "(As certified by proprietor)" and other notes;
  - the Trading and P&L sections.
- **Year types chosen by the user**: Audited, Provisional, Estimated, Projected (up to 7 years). An estimated or projected year can use the **client's own figures** instead of the tool's.

**Grouping and review**
- Each line keeps the client's own ledger name and gets a CMA head and a group: Schedule III for companies, T-form for proprietorships and firms.
- A review grid lets you change heads, correct amounts and add missed lines. Your corrections are remembered on the PC.
- **Tally to the rupee** for every statement year, plus a net-profit check against the statement. Differences are never plugged.
- The actual years can be locked once they tally.

**Projections** (the firm's CMA rules)
- Sales grow by the growth rate.
- Expenses are switchable line by line: variable (V) with sales, or fixed (F).
- Purchases are worked back so the previous year's gross profit % is kept.
- Stock, debtor and creditor days start from the client's own trend.
- **Drawing-power rule**: debtor days are raised only as far as needed for drawing power to exceed the CC limit plus 2% (capped at 90 days).
- Depreciation is on WDV, line by line, with term-loan capex added in the year of purchase.
- CC interest runs from the month after preparation (part-year in the first year).
- Term-loan interest comes from its schedule. Existing loans are worked out from their EMI, rate and end date.
- **Cash at bank is the balancing figure**, and every opening balance equals the previous closing balance.

**Bank tests**
- Drawing power (separate margins on stock and debtors; creditors deducted or not; debtors over 90 days excluded or not).
- Turnover method: fail below 4x, amber 4x–5x, pass from 5x.
- **DSCR**, with a per-client switch for deducting drawings (default **No**, as banks do), plus a memo line on the other basis.
- MPBF (Tandon II), sensitivity, break-even, and red flags.
- Suggestions for the highest safe CC limit and the highest term loan.
- Defaults (DSCR 1.5–2.5, turnover 4x / 5x, margins 25%, growth 20%, debtor-days cap 90) apply only where the user leaves a value blank.

**Output: one Excel workbook and one PDF**
- `CMA data - <Client>.xlsx`, built on the **built-in master format**:
  - Covering Letter and Assessment Note (the firm's details; no UDIN, because the figures are estimates);
  - **the bank format sheets kept exactly**: FORM-II, FORM-III, FORM-IV, FORM-VI, ABF, CHECK, RATIOS, CRA-DATA, ANALYSIS;
  - T-form Profit and Loss and Balance Sheet for every year, each signed for the client, with the right note for audited, provisional and projected years;
  - Term Loan (single schedule for the chosen method, with a drop-down to switch), CMA Tests, DSCR, Projection Basis;
  - extra sheets: FORM-V MPBF, Cash Flow, Break-even, Sensitivity, GST Cross-check, Red Flags, Projected vs Actual, Source Mapping, Audit Trail.

  Every projected figure is a live formula, and the bank's own CHECK sheet reads "Yes" for every year. The unit drop-down in FORM-II cell G6 offers **Actual (default)**, '000, Lakh and Crore.
- `CMA data - <Client>.pdf`:
  - **all pages in one file**, A4, portrait (Projection Basis landscape);
  - all columns fit the page width, with narrow margins;
  - footer with client, sheet and page x of y;
  - **checked page by page** before saving: a sheet that would end on a near-empty page is squeezed back automatically.

**Offline and private.** The master format ships inside the app, and everything except optional AI reading works without internet.

## Project Structure
```
CMA_Builder_V2/
├── main.py                     # entry point
├── requirements.txt            # libraries
├── build_exe.bat               # one-click Windows build
├── InstaCMA.spec         # PyInstaller specification
├── README.md
├── templates/cma_master.xlsx   # built-in master CMA format (bank sheets, no client data)
├── config/                     # CMA heads & keyword taxonomy, settings
├── core/                       # data model (years, lines, inputs), audit trail, sample clients
├── extraction/                 # Excel / PDF / OCR readers, T-form rules, reading pipeline
├── ai/                         # any-model AI layer (Gemini, Claude, OpenAI, compatible, Ollama)
├── analysis/                   # mapper, grouping, line-level engine, term loan, validator
├── reports/                    # workbook writer, extra sheets, page setup, PDF export, master update
├── gui/                        # PyQt5 desktop interface (12 pages)
├── samples/                    # sample statements (T-form Excel, Schedule III Excel and PDF) + input template
├── test_output/                # workbooks produced by the tests
├── tests/                      # automated tests (recalculate the workbook and compare with the engine)
└── user_manual/USER_MANUAL.md
```

## Running
```
python -m pip install -r requirements.txt
python main.py
python -m unittest tests/test_all.py
```

## Building the Windows application
Double-click **`build_exe.bat`**. The application is created in `dist\InstaCMA\InstaCMA.exe`. Copy that folder to any Windows PC; Python is not needed there.

The PDF is made with Microsoft Excel if it is installed, otherwise with LibreOffice.

## Disclaimer
The estimated and projected figures are prepared from the statements furnished and the assumptions entered by the preparer. They are estimates, not audited or certified, and actual results will differ. The lending bank's own norms prevail over the tests shown. The preparer must verify the source figures and every assumption before submission.
