# KSGM and company loan analyzer

Python Windows desktop software with a navy/teal interface, reviewable bank-charge detection, daily interest workings, Excel reporting and optional Gemini reviews.

## Start in baby steps
1. Install Python 3.11 or later from https://www.python.org/downloads/ . Include pip and Tcl/Tk.
2. Extract this entire ZIP into a folder.
3. Double-click **Install_and_Run.bat**. Internet is needed to install packages. Keep all supplied files together.
4. For later use, double-click **Run.bat**.
5. Click **Try sample**, then **Apply column mapping**. For this sample, set opening outstanding to **0**, annual rate to **12**, and calculate for 1–30 April 2026.

## Your statement
- Import CSV, XLSX, XLS or a text-based PDF containing extractable tables. First Excel worksheet is used. Change the header row before loading if necessary. Scanned/image-only or password-protected PDFs are not supported; use the bank's Excel/CSV export instead. No OCR is included.
- Map Date (prefer value date if your contract uses it), Description, Debit, Credit and Balance. Separate non-negative debit and credit columns are required; signed single-amount columns need conversion first. Import errors block analysis rather than silently discarding transactions.
- Select the balance convention: positive outstanding, negative bank balance, or balances explicitly suffixed DR/CR (DR = loan outstanding; CR = credit balance). Negative outstanding is carried forward but accrues zero debit interest.
- Rows are sorted by date. Within a date, original statement order is preserved. For reverse-chronological statements, arrange same-day transactions in correct order before importing. Avoid mixing accounts or including opening/closing summary rows as transactions.
- Review detected categories; select a transaction and click Change selected category. Keywords are candidates and may misclassify ordinary merchant payments. Unrecognised transactions remain Other. Fees and interest reversals can be credited to their original category. A narration combining interest and tax cannot be automatically split: separate it in source data based on evidence.

## Calculation assumptions
Enter opening outstanding immediately before the selected start date, even when there is no transaction on that date. Do not assume the loan sanction limit is the utilized loan. Daily mode requires every transaction balance. Fixed principal mode uses the opening amount throughout and ignores repayments/balance movements for expected interest.

The selected From and To dates are inclusive. Last closing outstanding on each date accrues for that date and is carried through non-transaction days. This is a configurable comparison tool, not a determination of what your lender contract requires. Use the correct annual rate, rate reset dates, value dates, and 365/360/Actual-Actual convention from your sanction letter. Actual/Actual changes the year divisor to 366 in leap years. Rate changes are effective from their entered date; the base rate is used until the first applicable change. No separate compounding is calculated; interest debits already included in daily statement balances continue as part of outstanding. Daily interest is accumulated without rounding; reported totals round to two decimals.

Bank interest is net debit less credit in Interest category. Penal interest, GST, processing, insurance and other bank charges are shown separately and excluded from the interest variance. Total detected costs sums all these reviewed categories. Variance = bank interest less expected interest. Differences can reflect timing, contract terms, missing rows or classification and are not proof of excess or unlawful charging. An implied simple annual interest rate uses a 365-day convention. A full-day movement reconciliation checks opening + debit − credit against each mapped balance. Review every warning before relying on results. Software cannot prove completeness of an imported statement or validate sanction terms automatically.

Excel export includes calculation settings, net categories, transactions, daily calculations and reconciliation warnings. It exports the last completed calculation snapshot; click Calculate again after changing inputs.

## Gemini API key and models
1. Open https://aistudio.google.com/app/apikey and sign in to your own Google account.
2. Create an API key for your Google project. Never share it in a public file.
3. Paste it into the Gemini assistant tab. Click Load available models.
4. Choose a model returned by your key, then click Review analysis after calculating.

The software does not contain or issue an API key. One key is used to retrieve available Gemini models; access, billing, quota and model capabilities depend on your Google project. The model list is loaded from Google's API rather than a hard-coded catalog. Some specialized models may not support this text-only request; choose another model if needed.

Only aggregate figures, calculation settings and warning count are sent when you explicitly request an AI review. Raw statement files, transaction descriptions and account numbers are not sent. The API key is held in memory and can optionally be supplied using GEMINI_API_KEY environment variable. It is not written to reports or configuration. Local calculations need no API key. AI commentary requires professional review and does not control numeric calculations.

Official references: https://ai.google.dev/api/models and https://ai.google.dev/api/generate-content .

## Optional Windows EXE
From a terminal in this folder, after installation:
```
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\python.exe -m PyInstaller --noconfirm --onedir --windowed --name KSGM_Loan_Analyzer --add-data "sample_statement.csv;." app.py
```
Distribute the complete generated dist/KSGM_Loan_Analyzer folder. Building an EXE is optional and has not been performed for this delivery.

## Verification
Run `python -m unittest test_engine.py` to check daily products, leap-year interest, rate changes, reversals, reconciliation and malformed input. Gemini live requests require your own key. No specific bank format has been supplied for validation; test your first real statement against manual workings.
