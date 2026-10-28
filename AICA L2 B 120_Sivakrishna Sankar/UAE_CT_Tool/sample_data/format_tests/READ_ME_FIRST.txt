SYNTHETIC test files (fictional company "Sample Gulf Trading LLC") - not real client data.
Each pair is a Trial Balance (TB) + General Ledger (GL) in a different system layout. All six hold the same underlying figures.

1_Tally_TB_AED.xlsx / 1_Tally_GL_AED.xlsx   - Tally Prime style. Currency: AED.
    TB: group-wise layout (Capital Account, Current Assets > Sundry Debtors ...) with the group total printed above its ledgers,
        "Closing Balance" heading over Debit / Credit, customer and supplier ledgers by party name, Grand Total.
    GL: "Ledger Vouchers" - one block per ledger with Opening / Closing Balance rows.
    Expect: 49 ledgers; the 19 group-total rows are excluded (warning); party ledgers map via their group; Suspense Account stays UNMAPPED.

2_Oracle_TB_USD.xlsx / 2_Oracle_GL_USD.xlsx - Oracle General Ledger style. Currency: USD (peg 3.6725 pre-filled).
    TB: report banner, account as segments 101.000.1000.0000.000 + description, Beginning / Period Activity / Ending Dr-Cr columns,
        repeated page heading, Company and Report totals.
    GL: journal line detail with Entered and Accounted Dr/Cr columns (the second pair is ignored with a note).
    Expect: 43 accounts; Suspense account UNMAPPED.

3_Random_TB_EUR.xlsx / 3_Random_GL_EUR.xlsx - ad-hoc Excel. Currency: EUR (non-peg: you must enter rates).
    TB: cover sheet, one amount column + separate Dr/Cr marker, some amounts typed as text ("EUR 1,200.00"), notes column, section totals.
    GL: abbreviated headings (Dt, Ledger, Narr, Dr, Cr), dates as text dd.mm.yyyy, code and name in one cell.
    For a test run you may type any illustrative rates, e.g. P&L 4.00 / closing 4.20 / equity 3.90, source "test only", then approve the
    translation difference. (With those rates profit = AED 16,842,000.)

Expected profit before tax in the TB currency: 4,210,500.00  (= AED 4,210,500 / USD file AED 15,463,061.25 / EUR file AED 16,842,000 at the rates above).
expected_figures.json lists every account balance the files were built from.
Regenerate: python sample_data/make_format_samples.py
