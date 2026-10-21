# Complete demo year - FY 2025-26 (all data is made up)

Client: **Demo Traders, GSTIN 33DEMOA1234B1ZD**, Tamil Nadu, Regular, Monthly.
Made by `tools/make_demo_fy2025.py`.

* `2025-04 April` ... `2026-03 March` - one filled Master Template per month (the books)
* `Filed returns` - GSTR-1 and GSTR-3B for all 12 months and the GSTR-9 for the year (portal-style DEMO PDFs)

How to use: open any return of Demo Traders, go to tab 15, choose FY **2025-26**, click
**Upload whole year: folder...** and pick this folder (or **zip file...** and `Demo_Full_Year_FY2025-26.zip`), Import.

What the Reconciliation table shows (everything else is green):

| Period | Row | Difference | Meaning / remedy |
|---|---|---|---|
| Aug 2025 | GSTR-1 vs GSTR-3B 3.1(a) | 10,000 / tax 1,800 | 3B short |
| Sep 2025 | GSTR-1 vs GSTR-3B 3.1(a) | -10,000 / -1,800 | the shortfall made good in the next 3B - the year agrees (interest u/s 50 for the delay) |
| Oct 2025 | Books vs GSTR-1, B2B | 25,000 / 4,500 | invoice in the books, missed in GSTR-1 and 3B |
| Oct 2025 | Documents issued (Table 13) | 1 | the same missed invoice |
| FY 2025-26 | Books vs GSTR-9: 4B B2B | 25,000 / 4,500 | the GSTR-9 is the system-computed draft (auto-filled from GSTR-1 / 3B), so the missed October invoice is not in it either: declare it in GSTR-9 Table 4B |
| FY 2025-26 | Books vs GSTR-9: output tax for the year | 4,500 | the tax on it - pay through DRC-03 with interest before filing GSTR-9 |

GSTR-9 vs GSTR-1 + 3B is all green: the draft is exactly the year's returns. Books vs GSTR-9 therefore shows the same
difference as Books vs GSTR-1 (October).

January has a credit note of 10,000 (Table 9B / GSTR-9 4I) - reported correctly, so it is green.

R Suresh & Associates, Chartered Accountants

In this repository the folder is shipped as Demo_Full_Year_FY2025-26.zip (one file). Upload the zip directly with "Upload whole year: zip file...", or recreate the folders with: python tools/make_demo_fy2025.py sample_data/Demo_Full_Year_FY2025-26
