# Accounting Assistant - v9.2

**v9:** Office page (all companies), setup wizard + one-click setup/update scripts, Claims (reimbursements / petty cash in bulk), Exports (foreign-currency receivables, FIRC/e-BRC, exchange differences, revaluation). See SPEC.md "v9".

**v8.1:** all tabs open in well under a second on large data (Bank 16 s → 0.3 s). See SPEC.md "v8.1".

Reads purchase and expense invoices from a folder and proposes the Tally entry. You check it, approve it, and it is posted to TallyPrime through port 9000. The app learns your ledger choices for each company.

**How to start:** see START_HERE.txt. Daily: double-click "Accounting Assistant" on the Desktop.

## New in v8
- **Red flags** (sidebar): suspicious-transaction indicators in 10 groups - cash limits (ITA 2025 s.185-188,
  old 269SS/269ST/269T; s.34(3), old 40A(3)), SFT thresholds, TDS bypassing, related parties, round tripping /
  accommodation entries, timing & book quality, GST (fake ITC, circular trading, e-way bill splitting, blocked
  credit, RCM), banking patterns, nature of expenditure (personal, capital, MSME 45 days) and statistical tests
  (Benford, duplicates, dormant / new parties, volume jumps). Each flag shows evidence and the law reference;
  mark it Explained or False positive with a note (optionally for every such flag of that party); Party risk
  scores; Excel export; editable thresholds. Indicators for review, not conclusions. Runs offline.
- **Related parties**: enter or import (Excel: Name, Relation, Ledger) per company; see every transaction with
  each related party; used by the related-party checks.
- **New look**: navy sidebar with icons, a colour per module, coloured Home tiles, app icon (also on the Desktop
  shortcut - run make_shortcut.py again), Light / Dark theme (Setup → App settings → Appearance).
- **Invoice folder**: click the 📁 path in the top bar to choose it.
- **Faster Bank and Reports**: bank suggestions use a one-time index; reports open instantly when already read
  (Refresh for the latest).
- **P&L with Trading Account** (Tally layout: Trading A/c → Gross Profit c/o; P&L A/c → Nett Profit). Closing
  stock from stock items, or from the Stock-in-Hand ledger in accounting-only companies.
- **Trial Balance cross-check**: compared with Tally's own Trial Balance report; any group that differs is
  shown and both sides are saved in the diagnostics folder (%APPDATA%\AccountingAssistant\diagnostics) -
  please send those files if you see a difference.
- **TDS sections**: guessed from the expense ledgers (insurance, hotel, travel, utilities etc. = Not
  applicable); change any party's section or set Not applicable (Compliance → TDS → Party TDS sections, or the
  dropdown on each row) - remembered. Labels follow the voucher date: old section before 01-04-2026, Income-tax
  Act 2025 s.393 reference with the old section in brackets from 01-04-2026 (seed table - verify rows).
- **Rule 37**: each supplier's real ledger balance is matched to its newest bills first, so payments entered On
  Account no longer show bills as unpaid. Hover a row for the working.

## New in v7
- **Dr/Cr grids add and remove lines by themselves**: while Dr and Cr differ, Tab past the last line adds a line
  carrying the difference (like Tally); a line you leave empty disappears.
- **Ledger fields**: reachable with Tab, the name is fully selected when you land on it, and matching ledgers pop
  up as soon as you type one letter (anywhere in the name).
- **Bank duplicates stopped before import**: every statement line is checked against earlier imports and
  against Tally (date, amount, direction, narration, cheque / UTR, running balance). A review screen shows New /
  Duplicate / Already in Tally / Possibly in Tally; duplicates are left out and lines already in Tally are never
  posted. So a 01-10 to 31-10 statement over books done to 15-10 only brings in 16-10 onwards.
- **Bank balance check**: statement closing balance vs the Tally bank ledger on the same date (live), with the
  difference and the lines that explain it (on the statement not in Tally / in Tally not on the statement).
  Re-checked after posting.
- **Schedule III (Division I)**: Reports → Schedule III. Balance Sheet and Statement of Profit and Loss with
  notes and previous-year figures, live from Tally. Mapping tab: every ledger gets a suggested line item (from
  its Tally group and name); change any, Save mapping once per company (shared with the office). Export to Excel
  (Balance Sheet, P&L, Notes).
- **Compliance**: TDS tracker (deducted vs deposited by section and month, due 7th / 30 April, overdue, parties
  near the limit with no TDS, 26Q data export), GST control (Rule 37 180-day unpaid ITC reversal, RCM liability,
  17(5) blocked credit, 2B mismatches), AP / AR ageing with drafted reminders (never sent by the app).
- **Close**: month-end checklist per company - the app shows what it can see, you tick the rest.
- **Search all companies** (top bar, Ctrl+F): amount, bill no., party, GSTIN, narration.

## New in v6
- **Home** (per company, any period): cash & bank balances live from Tally, payables due this week, overdue
  receivables, GST / TDS position, invoices and bank lines waiting, recurring entries due.
- **New entry** for every voucher type - Payment F5, Receipt F6, Contra F4, Sales F8, Purchase F9, Journal F7,
  Debit Note Alt+F5, Credit Note Alt+F6 (the keys work from any page). Ctrl+A accepts and posts, Alt+C creates a
  ledger, Enter moves to the next field.
  - Payment / Receipt / Contra: the bank side only offers bank, cash, CC/OD and credit-card ledgers, like Tally.
    Credit cards count as Bank OD / CC; card ledgers kept under another group can be ticked in Company settings.
    The last bank used is pre-selected.
  - Sales / Purchase / notes: GST split automatically (CGST+SGST or IGST from the party's state), round-off,
    ledger-level or stock-item lines.
  - **Settle bills…**: tick the open bills (live from Tally) a payment / receipt settles - Agst Ref, part payments,
    the rest On Account.
  - **Recurring…**: save rent / salary / AMC / EMI as a schedule; Journals → Recurring shows what's due.
- **Workbench** entry is now a simple form (supplier, expense head, date) with GST / TDS / RCM / round-off shown as
  labels; the Dr/Cr grid opens on demand. Green invoices: **Accept & post** (Ctrl+A).
- **Reports**: Trial Balance, Profit & Loss, Balance Sheet live from Tally for any period; double-click a ledger
  for its vouchers, double-click a voucher for the entry and the original invoice; Export to Excel.
- **Bank**: any bank's Excel/CSV - auto-detected, or **Map columns…** (drag the columns onto the fields; saved
  for that bank's layout). **Match…** marks a line as already in Tally (one voucher, or 2-3 that add up to it).
  **Bills…** settles bills bill-wise. Ledger suggestions also read the name inside UPI / NEFT / IMPS narrations.
- **Banking never goes to Gemini** - blocked in code. Gemini is for invoices only.
- **Offline learning**: after you post an invoice, the app remembers where that supplier prints the invoice no.,
  date and totals. Their next invoice is read on this PC without Gemini whenever every check passes
  (Memory → Vendors → "Offline reading").
- **Period picker** on Home, Workbench, Bank, Reports, Journals, GSTR-2B and Tally sync - default this FY, quick
  picks This month / Last month / This quarter / This FY / Last FY / Custom; each page remembers its choice.
- **Period lock** per company (Company settings): posting into a locked month asks for a reason, kept in the
  audit log.

## Please verify on your real TallyPrime (first use of v8)
1. Reports → Trial Balance: does it say "agrees with Tally's own Trial Balance"? If not, send the two files from
   the diagnostics folder.
2. P&L: compare Gross and Nett profit with Tally.
3. Red flags: run for this FY and review a few flags of each group; tune Thresholds.
4. Compliance → TDS → Party TDS sections: correct any guessed sections once.
5. TDS 393 references: check the seed table (app/engine/tds_map.py) against the Act.

## Please verify on your real TallyPrime (first use of v7)
1. Schedule III: compare totals with Tally's Balance Sheet / P&L for the same period; review the Mapping tab.
2. Bank: import a statement that overlaps entries already in Tally - check the review screen; Check balance.
3. TDS tracker: check deducted / deposited per month against your TDS ledgers.

## Please verify on your real TallyPrime (first use of v6)
1. Post one Payment, Receipt and Contra from New entry - check them in Day Book.
2. Settle bills: does the list match Tally's Bills Outstanding for that party? (If Tally can't be read the app
   falls back to bills worked out from synced vouchers and says so.)
3. Reports: compare Trial Balance totals and Nett Profit with Tally's own reports for the same period.
4. Sales with GST and a Debit / Credit Note: check the GST ledgers Tally shows.
5. Home: bank balances and bills due should match Tally.

## Setup (Windows)
    python -m pip install -r requirements.txt     (always "python -m": Smart App Control blocks pip.exe)
    python tools\check_env.py                     (every required line should say OK; Gemini line shows the model chosen)
    python tools\make_shortcut.py                 (Desktop icon "Accounting Assistant", no console window)

The .exe build is parked: on PCs with Smart App Control every compiled file inside it must be code-signed.
Until there is a signing certificate, use the Desktop shortcut (it runs the signed pythonw.exe).

In TallyPrime: F1 Help > Settings > Connectivity > Client/Server configuration > act as Server/Both, port 9000.

## Daily flow
1. **Setup → Companies & Tally:** Connect, select companies, Sync (masters + 12 months of vouchers; learns supplier→ledger rules from history). **Company settings…**: invoice folder, voucher style, round-off/TCS/TDS ledgers, narration template.
2. **Setup → App settings:** paste the Gemini API key (model "auto" picks the newest Flash model your key can use).
3. **Workbench:** pick the company in the top bar → **Read new invoices**. Each invoice is read by Gemini (page image with PAN/bank/IFSC blacked out + masked text, company name as hint). If Gemini's numbers fail the GST arithmetic it is asked once to re-check. The local reading is the offline backup and a cross-check: disagreements are shown to you.
4. The queue sorts invoices by what they need: **To fix** (chip says what: "Pick ledger", "Total doesn't add up", "Possible duplicate"…), **Ready**, **Posted**. Click one: document in the middle, entry on the right. Ctrl+Enter posts, Alt+↓ next, Ctrl+E sets aside.
5. **Post all ready** posts every invoice whose figures, ledgers and Dr = Cr all check out.
6. **Export for Claude** (on any invoice): saves a text file with names, GSTINs, PAN, bank, phones and PIN codes masked; amounts, dates, rates and layout kept. Check it, then send it when an invoice is read wrongly.
7. **Missing supplier?** The entry shows "Create supplier in Tally": it creates the ledger (group, GSTIN, state, PAN, bill-wise) directly in TallyPrime and uses it at once. "+ New ledger in Tally" does the same for expense ledgers.
8. **Purchase or Journal:** Setup → App settings → Default entry type (and "Apply to all existing companies"); per company in Company settings; per invoice with "Book as" - remembered for that supplier.
9. **TDS:** if the supplier had TDS deducted in past Tally entries, the same TDS ledger and rate are applied automatically (shown with the history it's based on). Approving teaches it; removing the TDS line stops it.
10. **Bank:** pick the bank ledger, Import statement (IndusInd .xlsx, HDFC .xls, any CSV, or text PDF; "Map columns" if a layout isn't recognised). Each line gets a ledger from learned rules, party names in the narration, or similar past Tally entries; lines already in Tally (same amount within 3 days) are never posted again. Post selected / Post all ready creates Payment, Receipt or Contra.
11. **Sync Tally** (top bar) refreshes the current company's ledgers and vouchers any time.
12. **Journals / GSTR-2B / Memory** as before (Memory now shows each supplier's Book-as and learned TDS).

## Checks done before posting
- GSTIN checksum.
- Invoice billed to this company's GSTIN.
- IGST vs CGST/SGST against supplier state and place of supply.
- CGST equals SGST.
- Taxable + tax + TCS + round-off = total (within Rs 1).
- Tax matches rate per slab.
- Round-off no more than Rs 1.
- Invoice number up to 16 characters.
- s.16(4) ITC deadline.
- Possible duplicate already in Tally (same supplier invoice number).
- Dr = Cr, and every ledger and stock item exists in Tally.

## Tax handling
- Input CGST/SGST/IGST ledgers are matched by rate.
- RCM posts input and output lines. For an unregistered supplier it computes the tax and reminds you about the self-invoice.
- s.17(5): GST is added to the cost.
- TDS uses the vendor's section, PAN type (1% individual/HUF vs 2% others for 194C), and single and aggregate thresholds based on this FY's Tally history.
- TCS charged by the supplier goes to the TCS receivable ledger.
- **TDS rates and thresholds are editable defaults: verify them against the Income-tax Act 2025 and the Rules before go-live.**

## OCR for scanned invoices
- The default is Windows' built-in OCR, run through PowerShell. Nothing to install, and it works offline.
- If that is unavailable (check_env shows it), install Tesseract (UB Mannheim build). The app picks it up automatically.
- Gemini: paste a paid-tier API key in Settings. Uploads are logged in %APPDATA%\AccountingAssistant\gemini_uploads.log.

## Not built yet / known limits
- Item-invoice mode: stock items are matched by name. Edit quantities and rates in the small table on the Review screen.
- Several people posting to the same company at once is blocked by a company lock: one poster per company. Full multi-user editing is a later phase.
- IMS actions, the 180-day unpaid-bill report, and code signing of the .exe are still pending.

## Tests
    python -m pytest -q        (138 tests: a fake Tally server, synthetic invoices and the fictional demo company)

All test data is fictional. tests/demodata/ holds Tally replies for the demo company Aarohan Infotech Private
Limited (the same books as the separate demo data pack, Aarohan_Infotech_Demo_Data), including a Trial Balance file
computed directly from the demo books, so the app's reports are checked against figures it did not produce.
