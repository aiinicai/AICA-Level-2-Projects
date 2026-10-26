# Tally to Financial Statements: Schedule III and Non-Corporate Financials with Depreciation Calculator

**AICA Level 2 Capstone Project** | Sreejith K S, Chartered Accountant and Registered Valuer | Sreejith Jaison and Associates, Kochi

## 1. The problem

Preparing year-end financial statements from Tally is repetitive and error-prone:

- The trial balance is exported, ledgers are re-mapped to Schedule III heads by hand, and the mapping is redone every year.
- Notes to accounts are rebuilt manually and often do not agree to the Balance Sheet.
- Depreciation under Schedule II and the Income Tax Act is worked out in separate sheets and not tied to the books.
- Previous-year comparatives are pulled from a different file and frequently break the opening balances.

## 2. The solution

A Streamlit application that connects to Tally Prime on the same computer, reads the trial balance, classifies every ledger, adds the previous year, runs a depreciation calculator and produces the Balance Sheet, Profit and Loss and Notes in Excel, in the firm's format, with live formulas.

Two reporting models, selected in the sidebar:

| Model | Frameworks | Entities |
|---|---|---|
| Corporate | AS (Schedule III, Division I) and Ind AS (Schedule III, Division II) | Company |
| Non-corporate | ICAI framework for non-corporate entities | Partnership firm / LLP and Proprietorship |

## 3. What the application does

1. **Pull from Tally**: reads groups, ledgers, closing balances and stock items through Tally's XML interface on `localhost:9000`.
2. **Classification**: maps every ledger to a Schedule III head using the Tally group, then ledger-name rules. Unclassified ledgers can be fixed on screen.
3. **Previous year**: comparatives come from Tally (previous period), an uploaded trial balance, or last year's workbook produced by this application. Last year's classification is reused for matching ledgers. A roll-forward check compares current-year opening reserves with previous-year closing reserves.
4. **Depreciation calculator**
   - Companies Act, Schedule II: straight-line or written-down value, pro-rata by days for additions and disposals, depreciation up to the date of sale, remaining-life override, profit or loss on disposal.
   - Income Tax Act: block of assets on WDV, half rate for assets used under 180 days, short-term capital gain when a block ceases.
   - Reconciliation of calculator inputs to the fixed-asset balances in Tally, and an option to apply the difference to the statements after review.
   - Deferred tax on the book/tax difference (information only).
5. **Statements**: Balance Sheet and Profit and Loss in the selected framework, with opposite balances shown gross as Schedule III requires (for example debtors with credit balances under liabilities).
6. **Notes, in separate sheets** (numbered, Balance Sheet first, then Profit and Loss):
   - *Accounting Policies*: general information and significant accounting policies for the selected framework.
   - *Notes - Balance Sheet* and *Notes - Profit and Loss*: a ledger-wise breakup for every line, grouped by Tally group, for both years. Every total is checked against the statement (a check column outside the print area). Reserves movement, changes in inventories, tax provision and earnings per share. Notes never split across printed pages.
   - *Notes - Ratios* (companies): the nine analytical ratios with numerator, denominator and variance.
   - *Fixed Assets Schedule*: gross block, additions, deductions, depreciation (opening, for the year, on deductions, closing) and net block by asset class, linked to the Depreciation Schedule sheet.
7. **CA and signatories**: firm, UDIN, client signatories, CIN and PAN, shown on the statements.
8. **Checks and export**: balance, reserve roll-forward, depreciation reconciliation and notes checks, then three downloads:
   - **Financial statements (Excel)**: the file for signing. Statements, policies and notes are set up for A4 printing with page numbers, print areas and signature blocks; the grey working-paper tabs (mapping and depreciation) are not part of the signed set.
   - **Financial statements (PDF for signing)**: the same statements, notes and fixed-asset schedule as an A4 PDF with the signature blocks.
   - **Auditor action list (Excel)**: a separate file, not part of the statements: findings from this run, standard audit procedures by area with SA references, the application's checks, and a list of balances for confirmation.
9. **Auditor review before filing**: the auditor completes the action list (Status, Done by / date, Working paper / remarks, reviewer name and date) and the file is uploaded back in the application. The application reads every line and reports items closed, exceptions (unanswered, in progress, Done without remarks, Not applicable without a reason, items added since the list was issued, missing sign-off, wrong entity), lets the exceptions be downloaded as CSV, and adds the check "Auditor action list cleared" to the checks list. The signing downloads show a warning until the list is cleared.

## 4. How to run

1. Install Python 3.10 or later (tick "Add python.exe to PATH" during installation).
2. Keep `tb_demo_app.py` and `run_demo.py` in one folder.
3. Run `python run_demo.py`. The first run installs the libraries listed in `requirements.txt`; the browser then opens the application.

Manual alternative: `pip install -r requirements.txt` and then `python -m streamlit run tb_demo_app.py`.

### Demonstration without Tally

Click **Load sample company** in the sidebar. This loads an invented company with two years of data, sample signatories and depreciation inputs. No Tally and no real client data is needed. Switch the framework in the sidebar to compare AS, Ind AS and the non-corporate model.

For the auditor-review step in the demonstration, open **Checks and export** and use **Use sample answers (with gaps)** to show exceptions, then **Use sample answers (complete)** to show clearance. Answered sample files are in `sample_output` to try the upload button.

### Sample Tally company (for a demonstration with Tally)

`sample_tally_company` holds import files for an invented company, Sample Engineering Private Limited, with two financial years (1-Apr-2024 to 31-Mar-2026) in one Tally company: `1_Masters.xml`, `2_Vouchers_FY2024-25.xml`, `3_Vouchers_FY2025-26.xml`, `Expected_Trial_Balance.csv` and `HOW_TO_IMPORT.txt`. `make_sample_tally_company.py` regenerates them. After importing into a new, empty Tally company, the application pulls the current year and the previous year from the same company and produces the same statements as **Load sample company**.

### With Tally

Open the company in Tally Prime, then press F1 (Help), Settings, Connectivity, Client/Server configuration, and set the port to 9000. Click **Pull from Tally** in the application.

## 5. Sample output

The `sample_output` folder holds files generated from the synthetic company: Excel for signing (Corporate AS, Corporate Ind AS, Non-corporate firm), the matching PDFs for signing (Corporate AS and firm), the Auditor Action List for the corporate AS case, and the same list answered completely and answered with gaps.

Screenshots of the application are in the `screenshots` folder.

## 6. Technology

Python, Streamlit (user interface), pandas (data), requests (Tally XML over HTTP), openpyxl (Excel with live formulas), reportlab (PDF). Tally Prime is the data source.

## 7. Data privacy

- The application talks only to Tally on the same computer. No data is sent to any server.
- The sample company, names, ledgers, amounts and signatories in this repository are invented. No client information is included.
- Signatory details are saved only in `client_profile.json` on the local computer, and that file is excluded from the repository.

## 8. Limitations

- Income tax is not computed; the provision is entered by the user.
- Ageing of debtors and creditors, the MSME disclosure and loan terms need bill-wise data or sanction letters; they are listed for the auditor in the Auditor Action List and are not in the notes.
- Share capital details (authorised capital, shareholding pattern) are not available from Tally and must be added by the reviewer.
- The sample Tally import files have been checked by reading the XML back and recomputing the balances (they reproduce the sample statements exactly), but they have not been tried in a live Tally Prime installation yet.
- The previous-period pull from Tally and Ind AS-specific disclosures such as other comprehensive income details are basic and need review.
- The output is a working draft for a chartered accountant's review; it does not replace professional judgement or the audit.

## 9. AI tools used

The application was built with AI assistance (Claude) under the author's direction. The author specified the accounting logic, classification rules and the report format, and reviewed the output against Tally and against statements prepared manually.
