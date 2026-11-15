# Full sample company for TallyPrime — 4½ years, with stock

A **fictional** trading company, “Full Sample Trading Co”, that exercises every screen of Tally MIS:

| | |
|---|---|
| **Period** | 1-Apr-2021 to 30-Sep-2025 (FY 2021-22, 2022-23, 2023-24, 2024-25 and Apr–Sep 2025) |
| **Vouchers** | 6,094 — sales 1,831 · purchases 631 · receipts 1,879 · payments 1,390 · journals 150 · contra 105 · credit notes 100 · debit notes 8 |
| **Stock** | 30 items in 6 groups, 2 godowns, opening stock, purchases, sales, sales returns and purchase returns |
| **Parties** | 25 customers and 12 suppliers, bill-wise (credit periods, late payers, part payments, an advance, supplier discounts) |
| **Also** | GST (CGST/SGST/IGST) with monthly set-off · 2 cost centres · term loan (repaid) · cash credit · fixed assets with depreciation · income-tax provisions |

It is built to import cleanly even in **TallyPrime Educational mode**: every voucher date is the 1st, 2nd or 31st of a month.
All names and amounts are made up. Use a **new, empty company** — never a real one.

| File | What it is |
|---|---|
| `1_Masters_and_Stock_Items.xml` | groups, ledgers (with opening balances and opening bills), cost centres, units, stock groups, godown, 30 stock items |
| `2_…` to `6_Vouchers_FY….xml` | the vouchers, one file per financial year |
| `EXPECTED_FIGURES.md` | correct totals per year, worked out separately, to check Tally and Tally MIS against |
| `expected_figures.json` | the same figures for the automatic test |

## Step 1 — Create an empty company
1. In TallyPrime: **Alt+F3 (Company) → Create**.
2. Name `Full Sample Trading Co`. Financial year beginning **01-04-2021**, books beginning **01-04-2021**.
3. **Maintain: Accounts with Inventory**. Enable GST: **No**. Save.

## Step 2 — Switch on two features
Press **F11 (Features)** with the company open and set (wording can differ a little between versions):
* **Accounting features → Maintain cost centres: Yes**
* **Inventory features → Maintain multiple godowns (locations): Yes**

Leave batches and expiry dates **off**. Accept and save.

## Step 3 — Import (in this order)
1. **Alt+O (Import) → Masters** (older Tally: *Gateway → Import Data → Masters*). Enter the full path, no quotation marks, e.g.  
   `C:\path\to\sample_tally_data_full\1_Masters_and_Stock_Items.xml`  
   Behaviour of import: **Combine opening balances**.
2. **Alt+O → Transactions** (older: *Import Data → Vouchers*). Import the five voucher files **in number order**: `2_…FY2021-22`, `3_…FY2022-23`,
   `4_…FY2023-24`, `5_…FY2024-25`, `6_…FY2025-26_Apr-Sep`. Each takes a minute or two.
3. After each file Tally shows how many vouchers were created. Anything that failed is written to **`Tally.imp`** in Tally's folder.

**Important:** import each voucher file **once only**. Importing a file twice creates every voucher twice. If something goes wrong half-way,
delete the company and start again from Step 1.

## Step 4 — Check it in Tally
* **Day Book** should hold 6,094 vouchers. **Trial Balance** should balance.
* Compare **Profit & Loss** for FY 2024-25 with `EXPECTED_FIGURES.md`: net revenue **₹4,63,18,062** (sales ₹4,64,01,109 less returns ₹83,046); purchases and expenses match to the rupee.
  Stock figures (and so gross profit and net profit) can differ by a few thousand rupees because Tally uses its own costing method.
  The stock items use the **Last Purchase Cost** method on purpose: with *Average Cost*, TallyPrime's valuation goes wrong whenever an item is sold down to nothing
  between purchases (closing stock of crores). Checked in TallyPrime: FY 2024-25 closing stock ≈ ₹68.5 lakh and net profit ≈ ₹63.9 lakh.
* **Stock Summary** should list 30 items with positive balances.

## Step 5 — Bring it into Tally MIS
1. TallyPrime: **F1 → Settings → Connectivity** → act as **Server**, port **9000**. Keep the company open.
2. Tally MIS → **Data sources & sync**. Tick months and press **Sync**.
   Start with **FY 2024-25 and FY 2023-24** (24 months) so that comparisons work, then add earlier months — or press **All months** (54 months) and be patient.
3. Pick a year at the top and compare with `EXPECTED_FIGURES.md`.

## A tour of what the data shows (FY 2024-25)
| Screen | What to look at |
|---|---|
| **Executive overview** | Revenue ≈ ₹4.6 crore, gross margin ≈ 25%, net margin ≈ 14%, current ratio ≈ 5.9, receivable days ≈ 56, inventory days ≈ 72, ROCE ≈ 22%. Switch comparison between *previous year* and *previous period*; filter by cost centre. |
| **Profit & loss** | *Revenue* tab: Shree Ganesh Traders is the largest customer, the top 5 customers are ≈ 49% of sales; Mumbai Branch earns more than Pune Branch. *Costs & expenses* tab: salaries, rent, freight and finance cost. |
| **Product profitability** (P&L tab) | **Inverter Battery 150Ah** is the biggest seller yet loses money (≈ −5% margin) — a “strong sales, weak margin” case. LAN Cable and Solar Panel earn ≈ 29–34%. |
| **Balance sheet** | Statement with comparison; *Liquidity* and *Solvency* trends (the term loan is repaid, so debt-to-equity falls to ≈ 0); *Asset quality & returns*; *Risk & integrity checks* flags the suspense item and period-end journals; *Cash flow* by activity. |
| **Receivables & payables** | **Sunrise Electronics** is the chronic slow payer (₹13.9 lakh outstanding at 30-Sep-2025; ₹11.0 lakh of it overdue, about 70% of all ₹15.9 lakh overdue receivables). Bills carry their credit periods (30–60 days), so the ageing buckets, the overdue figure and the collection-priority list all work. Payables overdue is small (₹32,073). |
| **Assistant** | “Why did revenue change?”, “Who owes us the most?”, “What are the biggest expenses?” |

## If something goes wrong
* **Vouchers rejected for a godown or cost centre** — the features in Step 2 are off. Delete the company, switch them on, start again.
* **“Ledger not found” / “stock item not found”** — the masters were not imported first.
* **Date errors** — Educational mode accepts only the 1st, 2nd and 31st; these files already follow that rule.
* **Anything else** — send me the `Tally.imp` log and a screenshot. The files were checked for balance and reproduced by Tally MIS to the rupee
  (stock aside), but I could not run them through a live TallyPrime here.
