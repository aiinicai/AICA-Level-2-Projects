ICAI AI LLC - DUMMY DATA PROJECT (Jan - Mar 2026)
====================================================

All names, ISINs, prices and trades are FICTIONAL and were created only for testing the
FIFO fixed income tool. Entity: ICAI AI LLC (the tool shows it as 'LLC', taken from the file name).
Assumption: NO coupons were received during the three months (so no coupon file is loaded).
Opening position: none - every bond starts from zero.

FOLDERS
  Input\    6 files to load into the tool (3 trade files + 3 closing price files)
  Output\   4 Excel files the tool produced from those inputs (3 monthly + 1 period report)
  Program\  the tool itself (fifo_gui.py, fifo_fixed_income.py, fifo_report.py) - the exact code
            that produced the Output files. Needs Python 3.10+ with pandas and openpyxl.

THE BONDS (fictional)
  XS9100000011   NORDBK 5 1/4 03/15/29
  XS9100000029   SUNRIS 6.375 09/30/30
  XS9100000037   ATLASC 4 7/8 06/01/28
  XS9100000045   PACFIN 7 PERP
  XS9100000052   ZENITH 5.5 11/20/31
  XS9100000060   MERIDN 6 1/8 02/10/30
  XS9100000078   COBALT 4.75 07/12/27
  XS9100000086   ORIENT 8 3/8 PERP

INPUT FILES
  '<MON> 2026 trades ICAI AI LLC.xlsx'          broker download layout (header on row 3):
        Trade Dt, Status, Side, Quantity, Price (Dec), Security, ISIN, Principal, Acc Int, Net, SetDt, ...
        Side uses B / S in January and March and [B] / [S] in February (both must work).
        Quantity is face value; price is per 100; coupons are read from the Security name.
        Some dates are text (MM/DD/YY) and some are Excel dates, as in a real broker file.
  '<MON> 2026 closing prices ICAI AI LLC.xlsx'  ISIN, Bond, Closing Price, Price Date (month-end)

STARTING THE TOOL
  Open the Program folder and double-click "Run FIFO Tool.bat"  (or run:  python fifo_gui.py).
  The first run installs pandas and openpyxl if they are missing (needs internet once:
  python -m pip install -r requirements.txt). The tool creates its own "positions" and "data"
  folders inside Program\ the first time you click Run - delete them to start again from zero.

HOW TO RUN IT IN THE TOOL  (run the months in order)
  Settings: Interest on = Face value | Day count = 30E/360 | Entity = LLC (default from the file name)
  For each month, JAN then FEB then MAR:
    1. Load trades              -> pick the month's trades file
    2. Load closing prices      -> pick the same month's closing price file (sets the valuation date)
    3. Run                      (leave 'Save positions and data after Run' ticked)
    4. Export to Excel          -> compare with the Output file of the same month
  After March: Period report -> From 2026-01 To 2026-03 -> Generate -> Export to Excel
  Start with an empty 'positions' folder, otherwise earlier saved positions will be picked up.

WHAT THE DATA IS DESIGNED TO TEST
  - partial sales and a full sale (SUNRIS in Feb), FIFO across two lots (NORDBK), no short positions
  - trades done in one month that settle in the next (trade-date accounting, interest from settlement):
      MERIDN and ORIENT bought 29/30 Jan settle 3 Feb | SUNRIS bought and ORIENT sold in late Feb settle in Mar |
      SUNRIS sold and ATLASC bought in late Mar settle in April
  - month-end positions carried into the next month automatically, and the period report
  - bonds sold in one month and re-bought in a later month

EXPECTED RESULTS  (USD; interest on face value, 30E/360, from settlement date)
  Unrealized P&L is cumulative against cost; '(period)' is the change since the previous month-end.

  January 2026
     Closing face value                             13,000,000
     Closing market value                        13,043,000.00
     Unrealized P&L (cumulative vs cost)             43,750.00
     Unrealized P&L (period)                         43,750.00
     Realized P&L on sales in the month               3,500.00
     Interest since purchase, bonds held             21,892.36
     Interest in the month, bonds held               21,892.36
     Interest since purchase, bonds sold              2,031.25
     Accrued since last coupon (= since purchase, no coupons)  21,892.36

  February 2026
     Closing face value                             13,200,000
     Closing market value                        13,227,650.00
     Unrealized P&L (cumulative vs cost)             45,400.00
     Unrealized P&L (period)                         18,400.00
     Realized P&L on sales in the month              22,150.00
     Interest since purchase, bonds held             55,339.24
     Interest in the month, bonds held               44,129.51
     Interest since purchase, bonds sold             21,189.93
     Accrued since last coupon (= since purchase, no coupons)  55,339.24

  March 2026
     Closing face value                             10,900,000
     Closing market value                        10,944,200.00
     Unrealized P&L (cumulative vs cost)             25,000.00
     Unrealized P&L (period)                          5,450.00
     Realized P&L on sales in the month              24,350.00
     Interest since purchase, bonds held             71,240.28
     Interest in the month, bonds held               42,735.42
     Interest since purchase, bonds sold             45,215.97
     Accrued since last coupon (= since purchase, no coupons)  71,240.28

  Closing positions by bond (face)
     ISIN                     Jan           Feb           Mar
     XS9100000011       3,000,000     1,500,000     1,800,000
     XS9100000029       1,500,000     1,000,000       500,000
     XS9100000037       2,000,000     2,500,000     2,000,000
     XS9100000045       1,000,000       600,000     1,100,000
     XS9100000052       2,500,000     3,500,000     2,500,000
     XS9100000060       2,000,000     1,500,000       800,000
     XS9100000078               0     2,000,000     1,000,000
     XS9100000086       1,000,000       600,000     1,200,000

  Period report JAN-MAR 2026 (From 2026-01 To 2026-03)
     Closing face value                             10,900,000
     Closing market value                        10,944,200.00
     Realized P&L on sales in the period             50,000.00   (= Jan + Feb + Mar)
     Unrealized P&L (cumulative = period)            25,000.00
     Interest, bonds held                            71,240.28
     Interest, bonds sold                            68,437.15

VERIFICATION
  The Output files were produced by running the tool on these inputs. The totals were also
  re-computed independently from the raw trades with separate FIFO code, and agree to the cent.
  Every Output sheet ends with a TOTAL row.

Note: if you change any setting (Interest on = Market value, Day count = Actual or 30/360 US),
interest figures will differ from the ones above; P&L and positions do not change.