# InstaCMA

Developed by CA Manas Kumar Jena  |  Contact: +91 9337820330
 – User Manual

## Quick CMA (the fast way)

1. Open the app. It starts on **Quick CMA**.
2. Press **Choose file...** and pick the client's P&L and balance sheet (Excel or PDF).
3. Type the cash credit limit and, if any, the term loan amount, rate and tenure.
4. Press **1. Calculate, 2. Make Excel, 3. Make PDF**.

The app reads the years, client name and proprietor from the file, adds the estimated years up to the current
financial year and two projected years, applies the default bank norms, and saves the Excel and PDF in a folder
"CMA - <client>" next to the client's file. If the client's own balance sheet does not tally, it says so: where
one line explains the difference exactly (for example Cash at Bank counted twice) it leaves that line out and
tells you; otherwise it asks before carrying the difference as a separate line.

## 1. Installing
1. Install **Python 3.11 (64-bit)** from python.org. Tick **"Add Python to PATH"** during installation.
2. Double-click **`build_exe.bat`** in the project folder. Wait 5–10 minutes; it installs the libraries, runs the tests and builds the app.
3. Open **`dist\InstaCMA\InstaCMA.exe`**. You can copy that folder to any Windows PC.

**For the PDF:** Microsoft Excel, if installed, is used automatically. Otherwise install the free **LibreOffice**.

**For scanned PDFs without an AI model:** install the free **Tesseract OCR** (UB-Mannheim build). Its path is set in Settings.

## 2. First-time settings
Open **Settings** and fill in:
- **CA firm**:
  - firm name, FRN, partner / proprietor, designation, membership number
  - address, phone, email, place
  - letterhead image (optional)

  These details print on the covering letter and the assessment note. There is no UDIN, because the projections are estimates.
- **AI model** (optional, used only to read PDFs and photos):
  - Choose a provider: Google Gemini, Anthropic Claude, OpenAI, an OpenAI-compatible service (OpenRouter, Groq, DeepSeek… – enter its base URL), or **Ollama**, a local model that keeps data on your PC.
  - Paste the API key, pick a model, and click **Test connection**.
  - Set a backup provider if you like; it is used if the main one fails.
- **Default bank norms**: these apply only where you leave a client's value blank. The factory values are DSCR 1.5–2.5, turnover 4x / 5x, margins 25%, growth 20%, CC 10%, term loan 10.5%.
- **Note under audited statements**: the text printed under each audited P&L and Balance Sheet.
- **Master CMA format (admin)**:
  - The built-in format is used by default.
  - "Update master format" loads a new bank format from a filled workbook in that format. It needs the admin password (factory value `admin` – change it).

Click **Save settings**.

## 3. Preparing a CMA
### 3.1 Client & years
1. Enter the borrower's name, signatory, constitution, nature of business, address, PAN, GSTIN, bank, branch, case type and date of preparation.
2. Set up the **years**. Use "Quick set" (first year plus how many of each type) or add years one by one. Choose the type of each year:
   - **Audited** – from audited statements
   - **Provisional** – from unaudited statements
   - **Estimated** – the current year, built by the tool
   - **Projected** – future years, built by the tool

   Tick **"client figures"** if the client has given its own estimated or projected statements; those years are then read like the actual years. You can have at most 7 years, consecutive and oldest first.
3. Click **Apply**.

### 3.2 Upload statements
1. Add the P&L and Balance Sheet of every Audited / Provisional year (and of any "client figures" years), as **PDF, scanned PDF, Excel or photo**.
2. Tick **"Read PDFs and photos with the AI model"** if a model is set.
3. If a file does not show its year, set the year and tick the option.
4. Click **Read files and group heads**. The log shows what was read from each page or sheet.

The **CMA Input Template** (button on the Upload page) is the exact route: key one figure per CMA head per year.

### 3.3 Review & group
- Every line shows its CMA head, its section (Trading or P&L) and its **group** (Schedule III for companies, T-form for others).
- **Amber** rows need a look. Change the head from the list, correct an amount, or add a missed line, then click **Apply and recalculate**.
- The **Tally** table must show **PASS** for every statement year, and the net profit must agree with the reported figure. **Never plug a difference.** The usual causes are:
  - a sub-total read as a line
  - an asset read gross instead of net
  - bank and cash counted twice
- Tick **Lock the actual years** when everything tallies.

### 3.4 Inputs
- **Cash credit**: proposed or not; existing and proposed limit; rate; drawing power margins on stock and debtors; whether creditors are deducted; whether debtors over 90 days are excluded.
- **Term loan**: proposed or not; amount, rate, tenure, moratorium, **Equal EMI or Equal Principal**, purpose, and the asset bought (if capex).
- **Existing loans**: lender, EMI, rate and end date for each loan in the balance sheet. The yearly principal and interest are worked out from these.
- **Projections**: growth %, stock / debtor / creditor days, CC limit, drawings and capital introduced, year by year. **Blank cells use the defaults**: debtor days are solved so that drawing power exceeds the CC limit.
- **Norms & DSCR**:
  - DSCR band, and **"Deduct drawings while calculating DSCR"** (default No)
  - turnover bands, drawing power buffer, debtor-days cap
  - tax rate and interest rate on unsecured loans
  - unit of the FORM sheets (**Actual**, '000, Lakh, Crore)
- **GST turnover**: the GSTR-3B turnover of each actual year, used for the cross-check sheet.

Click **Apply and recalculate**.

### 3.5 Results
- **Projections**: P&L and Balance Sheet for all years. On the Projection basis tab you set each line to V / F or S / H, and the WDV rate of each fixed asset.
- **Term loan**: the year-wise summary and monthly schedule. A button finds the highest loan that keeps DSCR at the minimum.
- **Bank tests**: drawing power, turnover, DSCR (main figure and the figure after drawings), and MPBF.
- **Checks & warnings**:
  - **ERROR** blocks the export.
  - WARN lines and decisions (for example a suggested CC limit) are listed and printed in the assessment note.

### 3.6 Export
1. Choose the folder and the unit.
2. Leave the PDF ticked. All pages are ticked; untick a page only if a particular bank does not want it.
3. Click **Export now**. A folder named after the client is created, containing:
   - `CMA data - <client>.xlsx`
   - `CMA data - <client>.pdf` – one A4 file: covering letter, assessment note, FORM II–VI, ABF, CHECK, ratios, CRA data, analysis, P&L and Balance Sheet for every year, term loan, tests, DSCR, projection basis and the extra sheets
   - `<client>.cma.json` – the client file for next year

The log reports the **page check**: all pages A4, and no blank or spill-over pages.

## 4. The workbook
- Blue cells on yellow are **inputs**:
  - growth, days, drawings (Projection Basis)
  - rates, margins, norms, limits, the DSCR drawings switch (CMA Tests)
  - loan details and the repayment method (Term Loan)

  Change any of them and the whole workbook recalculates.
- The unit drop-down is in **FORM-II cell G6**: Actual / '000 / Lakh / Crore. The P&L and Balance Sheet always stay in rupees.
- The bank's own **CHECK** sheet must read "Yes" for every year.

## 5. Next year
1. Open the client file, set the years again (last year's estimate becomes audited or provisional) and upload the new statements.
2. The **Projected vs Actual** sheet compares last year's projections with the actual results.

## 6. Troubleshooting
| Problem | What to do |
|---|---|
| Tally FAIL | Review & group – look for a sub-total, a gross asset or a double-counted bank line |
| AI reading failed | Check the key / internet, or use the backup provider, Ollama or OCR |
| "Year not found" | Set the year on the Upload page and tick the option |
| Debtor days capped warning | The CC limit is too high for the stock and sales – lower the limit or review stock days |
| DSCR below the minimum | Reduce the loan (use the term-loan button), extend the tenure, or review the assumptions |
| PDF not made | Install Microsoft Excel or LibreOffice; or open the workbook in Excel and save it as PDF |
| Any error | See `%USERPROFILE%\.cma_builder2\error.log` |
