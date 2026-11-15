# Open the sample company in TallyPrime

A small **fictional** company, “Sample Trading Co”, with 421 vouchers from **April 2024 to September 2025**
(two financial years, so the “vs same period last year” comparison works). It is made to import cleanly, even in
**TallyPrime Educational mode**: every voucher is dated the 1st, 2nd or 31st of a month, and there is no stock and no GST.

| File | What it is |
|---|---|
| `1_Masters_Ledgers.xml` | 29 ledgers: bank, capital, loan, furniture, 6 customers, 4 suppliers, sales, purchases, expenses |
| `2_Vouchers.xml` | 421 vouchers: sales, purchases, receipts, payments, journals, contra — bill-wise, so ageing works |
| `EXPECTED_FIGURES.md` | The correct totals, worked out separately, to check Tally and Tally MIS against |

## Step 1 — Create an empty company in TallyPrime
1. Press **Alt+F3** (Company) → **Create**.
2. Name: `Sample Trading Co`. Financial year beginning: **01-04-2024**. Books beginning: **01-04-2024**.
3. Maintain: **Accounts only**. Enable GST: **No**. Save the company.

*(Use a new, empty company. Do not import into a real company.)*

## Step 2 — Import the ledgers, then the vouchers
Do them in this order — ledgers first.
1. With the company open, press **Alt+O** (Import). Choose **Masters** (older Tally: *Gateway → Import Data → Masters*).
2. Type the full path of the file, for example  
   `C:\path\to\sample_tally_data\1_Masters_Ledgers.xml`  
   (no quotation marks). Set *Behaviour of import* to **Combine opening balances**, then accept.
3. Press **Alt+O** again and choose **Transactions** (older Tally: *Import Data → Vouchers*). Use `2_Vouchers.xml`.
4. When it finishes it shows how many were imported. Anything that failed is listed in the import log file **`Tally.imp`** in
   Tally's installation folder.

## Step 3 — Check it in Tally
Open **Display More Reports → Profit & Loss** and **Balance Sheet** and compare with `EXPECTED_FIGURES.md`:
FY 2024-25 sales of ₹46,71,960 and net profit of ₹12,16,120 should show, and the Day Book should list 421 vouchers in total. The trial balance should balance.

## Step 4 — Test Tally MIS against the same company
1. In TallyPrime: **F1 (Help) → Settings → Connectivity** → TallyPrime acts as **Server** (or Both), port **9000**.
   Keep `Sample Trading Co` open.
2. Start Tally MIS → **Data sources & sync**. Tally and the company should appear.
3. Tick **Apr 2024 … Sep 2025** (the “All months” button) and press **Sync**.
4. Open the **Executive overview**, **Profit & loss** and **Receivables & payables** and compare with `EXPECTED_FIGURES.md`
   (use the year selector at the top: FY 2024-25 and FY 2025-26).

If numbers differ between Tally and Tally MIS, tell me which screen and figure.

## If something goes wrong
* **“Ledger not found” / vouchers rejected** — the ledgers were not imported first. Import `1_Masters_Ledgers.xml`, then the vouchers again.
* **Nothing imported** — check the path (no quotation marks) and that the company is open.
* **Date errors** — in Educational mode only dates 1, 2 and 31 are accepted; the files already follow this rule.
* **Anything else** — send me the `Tally.imp` log and a screenshot. These files were checked for balance and against the
  Tally MIS engine, but I could not run them through a live TallyPrime here.

*All names and amounts are made up.*
