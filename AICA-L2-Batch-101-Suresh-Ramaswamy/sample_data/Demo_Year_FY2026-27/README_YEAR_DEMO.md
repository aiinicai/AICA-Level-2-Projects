# Demo year folder - FY 2026-27 (all data is made up)

Client: **Demo Traders, GSTIN 33DEMOA1234B1ZD**, Tamil Nadu, Regular, Monthly.

How to use it (tab 15 "YTD & Annual"):
1. Create the client on tab 2 and open any one of its returns (tab 3).
2. On tab 15 choose FY 2026-27 and click **Upload whole year: folder...** and pick this folder
   (or **Upload whole year: zip file...** and pick `sample_data/Demo_Year_FY2026-27.zip`).
3. The preview lists every file with its month. Tick "Approve lines without errors after import" and click **Import**.
4. Open the **Reconciliation** table.

| Folder | Files | Month comes from |
|---|---|---|
| 2026-07 July | Master Template (filled) | Return Info sheet |
| 2026-08 August | HSN report + output register (billing software) | the folder name (the files carry no month) |
| 2026-09 September | Sales register + 2 PDF invoices | invoice dates |
| Filed returns | GSTR-1 and GSTR-3B for July and August | the return itself / file name |

What the reconciliation shows:
* **July** - books, GSTR-1 and GSTR-3B agree (green).
* **August** - GSTR-3B 3.1(a) is Rs 30 lower than GSTR-1 (tax Rs 2.40): red, with the likely reason.
* **September** - GSTR-1 / GSTR-3B not uploaded yet: yellow "MISSING".
* **GSTR-9** - yellow "GSTR-9 not uploaded": FY 2026-27 is not over, so there is no GSTR-9 yet. The app leaves out
  a GSTR-9 of a year that has not ended. The GSTR-9 comparison is used for a completed year (FY 2025-26 onwards).
* Double-click the red August row: the reason and the remedy (next GSTR-3B or DRC-03), and an offer to open August
  at its GSTR-1 Summary (August came from summary reports, so it has no invoice lines to review).

The filed-return PDFs here are DEMO files made by `tools/make_demo_returns.py`, laid out like the portal downloads.
Never put real client returns in this repository.

R Suresh & Associates, Chartered Accountants
