# Audit & Bug-Fix Report — Auto Bank Statement Entry (WPF)

Date: 26-Nov-2026. Scope: every source file (`BankStatementParser`, `TallyConnector`, `ContraDedupEngine`,
`LedgerClassifier`, `DatabaseService`, `MainWindow`, `App`, `Models`, tests, build script).

## How this was verified — read first

* **The C# could not be compiled in the audit environment** (no .NET SDK there). The code was checked with a
  bracket/string lexer and line-by-line review. The first build on Windows is the real compile check:
  run `build_office_exe.bat`, which runs every test before publishing.
* The parser logic was **ported line-by-line to Python** (`Tests/Fixtures/_generator/harness.py`) and run against 29
  synthetic statements with known answers. All 29 now give every row, the right Dr/Cr, exact totals, the right
  opening/closing, and zero balance breaks. The 14 statement-parsing tests from the original suite also give their expected results (the other original tests cover the database and ML, and need .NET to run).
* The fixtures are **synthetic files modelled on each bank's published layout**, not real customer statements.
  Before go-live, run 2–3 real statements from each bank you use and check the green "Reconciled ✓" banner.
* PDF fixtures are read in C# by PdfPig and in Python by pdfplumber. The two split words slightly differently, so the
  7 PDF tests are the most likely to need a small fix on the first Windows run.

## Bank coverage (fixtures in `Tests/Fixtures`, tested by `AuditRegressionTests.BankFixture_ParsesEveryDebitAndCreditExactly`)

| Bank | Format(s) | What the fixture checks |
|---|---|---|
| SBI | TSV-as-.xls, PDF | "1 Apr 2025" 3-word dates, blank-space cells, 2 identical same-day charges, bordered PDF, wrapped text |
| HDFC | XLSX, PDF | numeric cells, `*****` rows, summary block, borderless right-aligned PDF |
| ICICI | XLSX, PDF | table starting in column B, 0.00 placeholders, 3-line wrapped PDF headers |
| Axis | CSV, PDF | OPENING/CLOSING rows, TRANSACTION TOTAL row, vector grid lines |
| Kotak | CSV, PDF | single Amount + Dr/Cr, **separate balance Dr/Cr column**, overdraft, `82,000.00(Cr)` |
| PNB | CSV | overdraft `12,500.00 Dr` balances |
| Bank of Baroda | CSV | `1,20,749.50Cr` (no space) |
| Canara | HTML-as-.xls | colspan title row, `&nbsp;`/`&amp;` |
| Union | CSV | `500.00 (Dr)` single Amount |
| Bank of India | HTML-as-.xls | Brought / Carried Forward |
| IndusInd | CSV | "Withdrawl" header, `Rs. 1,000.00` amounts |
| IDBI | CSV | `Dr.` / `Cr.` indicator column |
| Yes Bank | XLSX | real Excel date cells |
| Indian Bank | CSV | `01 Sept 2025` |
| Central Bank | CSV | Post Date / Account Description |
| IOB | CSV | `01-APR-2025`, ` CR` balance suffix |
| UCO | HTML-as-.xls | **no closing `</td>`/`</tr>` tags** |
| Federal | CSV | Tran Type + balance-side DR/CR, overdraft |
| IDFC FIRST | PDF | `-` placeholders in empty amount columns |
| Bank of Maharashtra | CSV | `-` placeholders |
| RBL | CSV | signed Amount (negative = withdrawal) |
| Bandhan | CSV | date printed only on the first row of each day |
| Karnataka | CSV | balance printed only on the last row of each day |
| AU SFB | PDF | reverse chronological |

## Bugs fixed — debits/credits (highest impact)

1. **`Rs. 1,000.00` / `INR 1,000.00` amounts were unparseable.** Stripping everything except digits and dots left
   `.1000.00`, so the row was dropped without any message. The parser now reads the first number in the cell.
2. **`1,250.00Dr` (Dr/Cr with no space) was not recognised.** It used a `\b` word boundary. Overdraft balances became
   positive, and the running-balance auto-correct could then **flip correct credits into debits**.
3. **Signed single-Amount statements:** every positive amount was booked as a debit. Positive is now a credit when the
   statement prints withdrawals as negatives.
4. **Same-day rows with no date printed were thrown away** when the previous row already had an amount. They are now
   kept when the line has its own running balance, so the balance check still proves them.
5. **Day-end-only balances caused false "balance breaks"**, and a wrong opening balance. The running-balance check now
   carries the balance across rows that don't print one.
6. **HDFC summary row:** the opening balance was read from the "Closing Balance : x" cell. Labels are now matched to
   their own numbers.
7. **Two identical genuine transactions in one statement** (for example two ₹11.80 SMS charges on one day) got the same
   hash and the same Tally REMOTEID. The second was unticked as a "duplicate". If re-ticked, it **overwrote the first
   voucher in Tally**. Each now gets its own occurrence number. The first occurrence keeps the old hash, so existing
   posted history still matches.
8. **A balance-side Dr/Cr column was ignored** (Kotak / Federal), so overdraft balances lost their sign.
9. **PDF: a number at the end of a wrapped narration** (for example "…INVOICE 371") landed in the Debit column. Numbers
   left of the real amount column are now kept as narration. A stray "-" in a money column no longer makes the
   balance negative. `(Cr)` suffix tokens are now recognised.
10. **PDF page text** used `page.Text`, which runs lines together. The "Closing Bal" label then picked up the next
    line's opening figure. Page text is now rebuilt from the positioned lines.
11. **HTML `.xls` exports without closing tags gave 0 rows.** Colspan headers also shifted the columns. Both now parse.
12. **Excel serial-date check:** any number from 35,000 to 65,000 (for example `45,000.00`) could be read as a date.
    Only plain 5-digit cells count now. `Sept`, ISO date-times and a few more formats are accepted.
13. **Vendors whose name starts with "TOTAL"** (TOTAL ENVIRONMENT PVT LTD) lost their narration. They now keep it.
14. **Bank detection** matched IFSC codes as substrings ("sury" in Surya, "ratn" in Ratnakar, "sibl" in "possible").
    It now matches whole names, or full IFSC codes only.
15. Dr/Cr corrections, inherited dates and guessed directions now show a **parser note** on the row, with a
    "Parser Warnings" filter. They are listed in the Debug report.

## Bugs fixed — Tally posting

16. **Voucher XML amounts used the PC's regional format.** On a PC set to use a comma decimal separator,
    `1234.50` became `1234,50`. All XML amounts and hashes are now culture-invariant.
17. **Existing-voucher read doubled every amount.** It read both ALLLEDGERENTRIES and LEDGERENTRIES, so overlap
    detection missed entries and the Tally balance came out wrong. The period is also enforced on our side now.
18. **Silent Tally read failures.** A timeout (4 s before) returned an empty list, which **switched off the duplicate
    check without telling anyone**. After posting it also showed every entry as "Missing". You now get an explicit
    warning, the timeouts are 60–120 s, and the check shows "could not verify" instead of "missing".
19. When the voucher read failed, the Tally opening balance fell back to the ledger master. That gave false mismatch
    warnings. It is now reported as "not available".
20. **Backup** could zip a **different loaded company** when the name didn't match exactly. Zipping now runs off the
    UI thread, and a half-written zip is deleted if the backup fails.
21. **Error diagnosis** read the raw XML, so any `<DATE>` tag gave the "Educational mode" message. It now reads only
    Tally's error text. Exceptions and ignored entries are reported.
22. **Rollback** cleared every duplicate-guard hash even when some deletes failed. Now only the deleted vouchers are
    cleared, and the batch stays open so you can retry the rest. Deletion now uses REMOTEID.
23. **Bank / party ledgers** were classified by "parent group contains 'bank'". Ledgers under a "Bank Charges" group
    became bank accounts. Parties in sub-groups (for example "Debtors - Delhi") got no bill-wise options. The group
    tree is now walked up to the primary group.
24. Bill allocations are never sent on Contra vouchers. **Changing a row's ledger clears the bills picked for the
    previous party.**

## Bugs fixed — contra / ML / data / UI

25. **Contra false positives:** matching the last 4 account digits as a substring triggered on UPI reference numbers,
    amounts and years. It now needs an account-like reference (XXXX1234, a stand-alone 1234, or a 9–18 digit run).
    "ATM AMC / annual fee / decline charges" are no longer cash withdrawals.
26. **A self-transfer with 2+ other banks** went to the alphabetically first bank. You now pick, and posting is blocked
    while the ledger is empty.
27. The fallback ledger "Sundry Debtors" (and the defaults "Sundry Debtors/Creditors") are **Tally groups, not
    ledgers**. They are replaced with "Suspense Account".
28. **ML retrain was dense (documents × vocabulary)** and ran on the UI thread at every post. It would freeze the app
    as the shared table grows with 5–7 users. It is now an equivalent sparse model, runs in the background, and is
    capped at the latest 150,000 user examples. A background save also no longer hides other PCs' updates.
29. **New posting guards:**
    * Tally is not connected.
    * The **company or bank ledger changed after Analyze**.
    * A row has no ledger.
    * Payment is used on a deposit, or Receipt on a withdrawal.
    * The **statement doesn't reconcile**, has balance breaks or parser notes, has no running balance, or wasn't
      checked against Tally.
30. When several files are selected for one bank ledger, a **different account or bank** now gives a warning.
31. **Any unhandled exception used to close the app** and lose the reviewed grid. It is now caught, shown and logged
    in `%LOCALAPPDATA%\AutoBankStatementEntry\logs`. A missing server share at startup now shows a clear message.
32. "Delete Backups" deleted **every file** in the chosen folder. It now deletes only `*.zip` backups.
    "Clear XML" now asks for confirmation first.
33. Posting history is saved off the UI thread. If the save fails, you're told plainly that the vouchers are already
    in Tally. RowId collisions no longer crash after a push.

## Changes approved and implemented (follow-up)

34. **Contra by IFSC alone is no longer accepted.** IFSC identifies a branch, so a vendor at the same branch matched.
    An IFSC match now counts only with self / own-account wording ("TO SELF", "OWN A/C", "SELF TRANSFER"). An
    account-number match (XXXX1234 etc.) still works on its own. NEFT / RTGS / IMPS narrations are never treated as
    cash withdrawals, so "NEFT … TRF TO SELF" goes to the bank, not to Cash.
35. **The ML stores one example per transaction**, keyed by the transaction's hash and company:
    * Analysing the same statement again, or editing a row and then posting it, adds nothing — the transaction was
      already learned with that ledger.
    * If the ledger was corrected, the new label **replaces** the old one instead of both competing.
    * Different transactions of the same party have different hashes, so each still adds a vote. Rows without a hash,
      older data and other companies are unaffected.
    * Retraining is skipped when nothing new was written.
    * Tests: `Learning_SameTransactionTwice_IsStoredOnce_CorrectionReplaces_OtherTransactionsStillCount` and
      `IfscAlone_IsNotContra_ButIfscWithSelfWordingIs`.

## Follow-up from a real ICICI "Transactions List" PDF

36. **Row 1 was a credit booked as a debit.** Three things combined:
    * The column reader did not recognise the header, so the fallback reader was used.
    * The fallback ignored the **Cr/Dr column** and guessed Dr for the first row.
    * The opening balance was derived from that guess, so the statement still showed "BALANCED".

    Fixes:
    * Header words separated by a drawn border are never merged, and a "Cr/Dr" heading never swallows the next column.
    * Wrapped headers ("Transactio n ID") and "ChequeNo." are now recognised.
    * The fallback reads the Cr/Dr column, and finds the date even after a serial number and a transaction-ID column.
    * When the opening is not printed and the first row's direction is only a guess, the statement shows
      **"could not be proven"** instead of "BALANCED", and posting asks for confirmation.
37. **Centred descriptions went to the wrong row.** Each description's first line sat above the date line and was glued
    onto the previous transaction, which also fed the wrong party name to the ML. The table's horizontal borders now
    group each row's lines together. Times ("12:04:10 PM") and empty "-" cheque cells no longer appear in the narration.
38. **The bank label came from the other party's IFSC.** An IFSC code now counts only when printed with an "IFSC" label.
    Otherwise the bank is detected from its name, or shown as "Scheduled Bank (Auto)".
39. **The Debug report now has a "PDF Layout Detection" section.** It lists the header found on each page, the columns
    detected and the drawn borders, or the first lines of a page where no header was found.
40. New fixtures:
    * `icici_txnlist_statement.pdf` — bordered.
    * `icici_txnlist_tight.pdf` — squeezed headers.
    * `icici_txnlist_borderless.pdf`.

    Update: borderless PDFs are now handled too. Rows are separated by the larger vertical gap between rows, used only
    when that gives exactly one dated line per row.

## Debit/Credit is asked, never guessed

41. **When the statement doesn't state a row's Debit/Credit and the running balance can't prove it, the app asks.**
    * **Which rows:** typically the first row when no opening balance is printed, or rows around a balance gap. The
      fallback reader's guesses are included.
    * **When:** right after parsing, before duplicate, contra and ML checks.
    * **The dialog:** each row with date, narration, amount and balance, and a Debit / Credit choice pre-set to the
      parser's guess.
    * **After "Confirm & Continue":** the opening, closing and running-balance proof are recalculated with the answers.
      Printed opening and closing balances are kept.
    * **"Cancel Analysis":** stops the analysis, and nothing is guessed silently.
    * Rows with a Debit/Credit or Cr/Dr column, or proven by the running balance, are never asked.
    * Tests: `UnstatedDirection_IsFlaggedForTheUser_AndConfirmationRecomputesBalances` and
      `ExplicitDebitCreditColumns_NeverAskTheUser`.

## Follow-up from a real SBI 2025 PDF (966 rows booked as huge credits)

42. **Text in an amount column was read as money.** The SBI header row (white text on purple) could not be read, so a
    stray line above the table containing "Date" and "Credit" was taken as the header, with only 2 columns. Each row's
    Details text then landed in "Credit", and its first number became the amount. That produced
    "UPI/DR/509169091433" → ₹5,09,16,90,91,433.00 and the narration "Bank Transaction".
    * **Amount validation:** a Debit/Credit/Amount/Balance cell is used only if it is an amount — no words, and not a
      bare 11+ digit number (UPI RRN or account number).
    * **Columns inferred from the table:** when the header is missing, unreadable, an image, or too weak (no
      narration / amount columns), a bordered table's columns are worked out from their contents. Date columns hold
      dates, the text column holds descriptions, amount columns hold amounts or "-", and the right-most column filled
      on every row is the running balance. Only words between the table's top and bottom borders are counted.
    * The Debug report says when columns were inferred.
    * New fixtures: `sbi_new_statement.pdf` (readable header) and `sbi_new_imgheader.pdf` (header as an image, plus a
      decoy "Date / Credit" line — the exact failure).
    * Tests: `SbiHeaderAsImage_ColumnsInferredFromTable_NoReferenceNumbersAsAmounts` and
      `AmountCells_RejectTextAndReferenceNumbers`.

## Coloured / unreadable headings and "page 1 skipped"

43. **Page 1 entries were lost** when page 1's header could not be read. The columns were fixed page by page, so page 1
    was parsed with the bogus "Date / Credit" layout and the new amount check then rejected every row. The PDF is now
    read in **two passes**: first the best column layout found on any page, then every page is parsed with its own
    readable header, else its own inferred columns, else that best layout. Column inference now only counts
    transaction lines (a date and an amount on the same line), so a bordered account-details box can't skew it.
44. **Coloured headings are read in more cases:**
    * **Headings that run together** ("Value DatePost Date", "DetailsRef No/", "₹ Debit₹ Credit") are split into
      separate columns, within one header line.
    * **Letter-spaced or glyph-by-glyph headings** are rebuilt from individual letters. This is used only to read the
      header; transaction rows keep the normal words.
    * **Headers that are an image or unreadable** are handled for tables with borders (from the borders), tables
      without borders (from the empty gaps between columns), and partial borders (both methods are tried and the more
      complete result is kept).
    * **When nothing works,** the Debug report lists the positioned words at the top of page 1, so the exact layout can
      be fixed.
    * New fixtures: `sbi_new_p1only.pdf`, `sbi_new_runtogether.pdf`, `sbi_new_spaced.pdf`, `sbi_new_img_borderless.pdf`.
      All 38 fixtures pass in the Python port of the parser.
    * Remaining limit: a statement that is a scan or photo, with no text at all, still needs the digital download
      (no OCR).

## First row posted in the wrong direction

45. **SBI: the first row "WDL TFR UPI/DR/…" ₹1,426 was posted as a Receipt.** It is a withdrawal. Every row is checked
    against the previous row's balance, but row 1 has no previous row, so a wrong column mapping there was never
    corrected.
    * **Whole-statement check:** if most rows the running balance can prove are reversed, the Debit/Credit columns
      were swapped. Every row is flipped and re-proven, and the first row is flagged for confirmation.
    * **Narration hint:** when the opening balance is not printed and the first row's narration clearly contradicts
      its column ("WDL", "UPI/DR", "TO TRANSFER" read as a credit, or "BY TRANSFER", "TRFR FROM", "DEP" read as a
      debit), the row goes to the "Confirm Debit / Credit" window instead of being posted on a guess.
    * Tests: `SwappedDebitCreditColumns_AllRowsFixed_FirstRowAskedNotGuessed`,
      `FirstRow_NarrationContradictsColumn_IsAskedNotPosted` and `NarrationDirectionHint_Works`.

46. **Borderless tables: descriptions no longer leak into the neighbouring row.** Without drawn borders, rows are
    told apart by the larger gap between rows than between lines inside a row. This is applied only when it gives one
    dated line per row; account-details and footer lines are ignored. It also prevents false "confirm Dr/Cr" prompts
    caused by a leaked narration such as "CHQ TRFR FROM" on a withdrawal.

## Dr / Cr shown as per Tally

47. **The review screen now shows Dr / Cr from Tally's side (your bank ledger), not the bank's.** Money received appears
    under **Dr** (Receipt) and money paid under **Cr** (Payment), the opposite of the columns the bank prints. Dr comes
    before Cr, as in Tally. This applies to the main grid, the totals bar, the reconciliation banner
    (Opening + Dr − Cr = Closing), the "Confirm Dr / Cr" dialog and the posted-batches list. Only the display changed:
    parsing, the running-balance proof, ML learning and the vouchers sent to Tally are exactly as before.

48. **Amounts are shown in Indian grouping (lakh / crore):** 12,34,567.89 instead of 1,234,567.89. This covers the grid,
    the totals bar, the banners, all messages, the bill dialog, the posted-batches list and the Debug report. The PC's
    date settings are unchanged. The Tally XML still sends plain amounts (1234567.89), and statements are read the same
    as before. Tests: `IndianNumberFormat_*`.

## Duplicate entries posted to Tally

49. **The same AU Bank payments were posted twice (Vch 34–38 and 88–92).** The duplicate check ran only during Analyze,
    and only against the app's own history and the vouchers read from Tally at that moment. Posting again from a stale grid
    therefore created a second copy. That covers re-posting rows marked "Failed" after Tally saved them but replied too late,
    posting the same statement from another PC, and a newer parser giving a row a different fingerprint. Importing with the
    same voucher ID and ACTION="Create" does not stop Tally creating a second voucher. Fixed:
    * **A new check runs immediately before every post (and every XML export while Tally is connected).** Tally is read again
      for the posting dates, and every selected row that already exists there is listed with its Tally voucher number. Yes
      unticks those rows and posts the rest; No cancels. If Tally cannot be read, posting stops unless you explicitly choose
      to go ahead.
    * **Matching uses two methods.** (1) The voucher ID this app stamps on every entry (REMOTEID/GUID "ABSE-…") gives an
      exact match, even if the entry was later edited in Tally. (2) Otherwise the match is same bank ledger, same amount,
      same direction, and a date within 1 day (3 days when the cheque/UTR number matches). Each Tally voucher can match only
      one row, so a genuine second ₹625.80 payment on the same day is still posted.
    * **Analyze also matches by voucher ID.**
    * **A timed-out entry is now marked "Tally MAY have saved this entry".** Re-posting is safe because of the check above.
    Tests: `PrePostGuard_*`, `Analyze_FlagsRowWhoseVoucherIdIsAlreadyInTally_*`.
    **The existing duplicates (Vch 88–92) must be deleted in Tally by hand.** Delete the later set (88–92) and keep 34–38.

## Tally "timed out", wrong Tally opening balance, SBI cash-credit PDF

50. **"Tally timed out" while Tally was working normally.** Every duplicate check and balance check asked Tally for **every
    voucher in the company** (all ledgers, all voucher types, every ledger line) and filtered them on the PC. Some Tally
    builds ignore the date range on such requests and send the whole history. The Analyze step also sent two of these heavy
    requests at once, and Tally answers one request at a time, so the second waited behind the first and hit its timeout.
    Fixed:
    * Tally is now asked only for the bank ledger's own vouchers (`Vouchers : Ledger` + `CHILDOF`, the index Display >
      Ledger uses), with the date range applied **inside Tally** by a filter.
    * If that request errors (older Tally) or returns nothing for the bank, the app checks again with a company-wide
      request, still date-filtered. An empty answer is never taken as "nothing in Tally".
    * Requests are sent one after another, never in parallel.
    * The opening-balance read (years of data from "Books beginning from") gets 5 minutes.
51. **Wrong Tally opening balance.** It is the ledger's opening plus every bank voucher since books began, computed from
    the same read. A read that timed out or was cut off gave a wrong figure. It now comes from the fast ledger-only read.
    (For the SBI CC file the *statement* opening was also wrong; see 52.)
52. **SBI cash-credit / narrow-column PDF read as ONE row** ("SBIPDF…6687.pdf": one ₹43,888 row whose description was
    the whole statement). Cells wrap in this layout: the date prints as "3 Nov" with "2026" on the next line, big amounts
    as "10,00,000." with "00" underneath, and headings as "Txn"/"Date". No row had a complete date, so the table parse found
    nothing and the last-resort fallback made one giant row. Fixed:
    * Wrapped dates and amounts are re-joined (within a cell and across lines).
    * A row band whose date is split over lines or words still counts as one transaction.
    * "Branch Code" is recognised as its own column, so codes like 16103 are never read as Debit amounts.
    * "Balance as on 1 Nov 2026 :-38,47,078.68" is read as the opening (negative CC/OD balances kept).
    * Any row with a description over 400 characters is flagged "Layout not understood", never shown as BALANCED.
    New fixtures `sbi_cc_narrow_statement / _borderless / _centred` (48 rows each). Tests: `TallyRead_*`,
    `SbiCcNarrow_*`. Python harness: 41/41.

## "Teach once" layouts and stricter completeness checks

53. **Teach Columns (saved layouts).** A format the parser does not understand can be taught once, and the layout is
    then used by every PC.
    * The window draws each page from the PDF's own word positions, so nothing has to be rendered or installed.
    * It opens on the page with the most dated lines, not page 1 (cover pages are skipped), and pre-fills the dividers
      from automatic detection.
    * Columns are stored as fractions of the page width with a role each, plus the table heading's words when
      present. They apply to every page, including continuation pages without headings.
    * A layout is chosen only by proof, in this order: (1) a layout whose heading matches and whose result reconciles,
      (2) the automatic read if it reconciles, (3) any other layout of that bank that reconciles. Otherwise the
      automatic read is kept and stays blocked if it is wrong.
    * Saving requires a proven test. A statement without a balance column needs explicit confirmation.
    * Tests: `SavedLayout_*`, `TeachColumns_SuggestsAPageWithTheTable_NotTheCoverPage`, and the new fixture
      `coop_noheader_statement.pdf` (no headings, Balance column before Debit/Credit, a cover page). The automatic read
      of that fixture is wrong and is now blocked; the taught layout reads all 40 rows exactly.
54. **Completeness checks beyond the running balance.**
    * **Printed totals.** "Total Debits/Withdrawals/Payments", "Total Credits/Deposits/Receipts", and the HDFC
      Statement Summary (Dr count, Cr count, debits, credits) must equal what was read. This catches a missing first or
      last row, which keeps the running balance consistent. Page sub-totals that add up are accepted, and vendor names
      such as "TOTAL DEBIT CARD …" are not treated as totals.
    * **Page numbers.** "Page x of N" with fewer pages in the file, or the same page twice, is a failure.
    * **Month to month.** Each proven statement's period and closing balance are recorded when posted. The next
      statement of that bank ledger must open where the last one closed; otherwise Analyze warns before continuing.
    * All checks are shown in the banner and the Debug report ("Completeness checks").
55. **Hard block (approved).** A statement whose balances do not reconcile, or that fails a completeness check, can no
    longer be posted. The message explains what to do: Teach Columns, use the Excel/CSV download, or send the Debug
    report. A statement that cannot be proven either way (no balance column, or the first row's Dr/Cr not stated)
    still asks for confirmation as before.
    Python harness: 41/41 fixtures, with zero false completeness flags (including both HDFC summaries, which are read
    and agree).

## Exact parties, confidence floor, date checks, split entries

56. **Exact party from Tally's own data.** Party ledgers are read with their bank details (`PAYMENTDETAILS.LIST` in
    TallyPrime: account number, IFSC, favouring name; older `BANKDETAILS` / `IFSCODE`). A narration matches a party by
    one of three rules:
    * the party's full account number (99%)
    * a masked account such as "xx910" plus the bank code from its IFSC (97%)
    * the party or beneficiary name as whole words, including a truncated last word (92%)
    The match is used only when exactly one party fits. A name match yields to an ML prediction of 90% or more
    (learned from your corrections). Cascading corrections never override an account-number match.
57. **Confidence floor (60%).** Rows whose ledger is a guess (below 60%, Suspense, or empty) start unticked with
    "⚠ Check ledger". Choosing a ledger (typing, list, Bulk Set Ledger, Ctrl+D), or a correction that makes the
    prediction confident, ticks the row again. Explicitly choosing Suspense keeps it held back. Rows that duplicate a
    Tally entry are never re-ticked.
58. **Dates.**
    * Rows dated outside the period printed on the statement are a completeness failure, so posting is blocked (the
      date was mis-read, usually the year). Testing this caught three of my own test PDFs whose printed period
      ended before their last row.
    * At posting, future dates and dates before Tally's Books Beginning are unticked and listed; the rest are posted.
      This replaces the old "continue anyway?" warning, because Tally rejects those dates anyway.
59. **Split entries.** One bank entry can be posted to two or more ledgers in one voucher (✂ Split Entry).
    * The lines must add up to the paisa. The voucher builder refuses to send one that does not.
    * Party lines get an "On Account" bill line so outstanding reports stay complete.
    * Every guard covers all split lines: missing ledger, self-posting, Suspense, ledger creation and
      post-verification.
    * Bill picking is disabled on split rows.
    * Typing a different single ledger removes the split.
60. **Clean-up.** Removed unused code: `FetchExistingVouchersAsync`, `LedgerClassifier.ClassCount` and
    `DatabaseService.DeleteAllBackups` (the Delete Backups button has its own *.zip-only delete). Ledger and group
    reads at connect now run one after the other (Tally answers one request at a time).
    Tests: `PartyMatcher_*`, `PartyBankDetails_*`, `ConfidenceFloor_*`, `SplitEntry_*`; harness 41/41.

## Exact money, keyboard, anonymised support copy

61. **Money is `decimal` everywhere** (was `double`). This covers parsed amounts, balances, totals, splits, bills, Tally
    amounts and balances, duplicate matching, and the database values. With `double`, 0.1 + 0.2 = 0.30000000000000004,
    so every comparison needed a 5-paise tolerance, which could also hide a real 1–4 paise error. Now:
    * Amounts are parsed exactly from the statement text.
    * Every running-balance and reconciliation check is exact to the paisa.
    * Printed totals, contra pairs and Tally balances are compared for equality.
    * The database keeps its REAL columns (old data readable) and converts at the boundary, rounded to paise.
    * The duplicate fingerprint formats the amount exactly as before ("1426.00"), so earlier postings are still
      recognised.
    Page coordinates and ML scores stay `double` (they are not money). The Python harness was made paisa-exact too:
    41/41 still reconcile. Test: `Money_IsExact_NoFloatingPointDrift`.
62. **Keyboard.** Added Space (tick/untick the highlighted rows), F8 (next row needing a ledger check) and Ctrl+F
    (search), alongside the existing Enter (save and next row) and Ctrl+D (same as above). A one-line key guide is
    shown under the totals.
63. **Anonymised copy for support** (📋 Debug → "anonymised copy").
    * Each page is rebuilt with PdfPig's own PDF writer. Every word stays at its exact position and width (Helvetica
      size chosen per word), right-aligned numbers keep their right edge, and table lines are redrawn.
    * Replaced: names and narration words (dummy letters from Q/X/Z/J/K/V only, so they can never spell a banking
      keyword), and numbers of 6+ digits (same length; leading zero kept so IFSC "SBIN0…" stays recognisable).
    * Kept: dates, amounts, column headings, bank names and banking words.
    * A random salt per file keeps the same name mapped to the same dummy within a file, and prevents anyone reversing
      it by guessing names.
    * Verified with a Python mirror (`_generator/anon_check.py`): all 19 PDF fixtures parse identically after
      anonymising. C# tests: `Anonymiser_*`.

## Group similar + cross-reference sweep

64. **Group similar.** The grid groups rows live by party (from the narration), direction and ledger.
    * Changing a row's ledger moves it out of the group automatically. "Take out of group" and "Put back into its
      group" are on the right-click menu.
    * The header shows the count, the total and "⚠ n to check", plus a "Set ledger for all" button (the same dialog as
      Bulk Set Ledger, which now works on any list of rows).
    * Contra, split, posted and separated rows always stand alone. A group of one has no header.
    * Pressing Enter picks the next row before the save, so a row moving to another group does not throw focus around.
    * Grouping is switched safely even while a cell is being edited.
    * The "Low ML Confidence (<70%)" filter is now "Needs Ledger Check" (the same 60% rule that holds rows back).
      The duplicated key hint was removed, and Tab / right-click were added to the key guide.
    * Removed `FocusNextRowLedgerBox` (replaced by `NextVisibleRow` + `FocusRowLedgerBox`).
    Tests: `Grouping_*`, `GroupHeader_*`.
65. **Cross-reference sweep (no compiler available here, so a checker was written: `_generator/xref_check.py`).** It
    checks five things over the app and test code:
    * every `Type.Member` of a project type exists
    * every call to a project method has a valid argument count and real parameter names
    * every `new Type { Prop = … }` sets real properties
    * every XAML event handler, `StaticResource`, `m:` converter and grid column binding exists
    * every `x:Name` used in code exists in XAML
    It also lists all framework names used, for review by eye; no typos were found. The checker was proven by planting
    five errors in a copy (wrong member, wrong named argument, wrong property, wrong handler, wrong binding): all five
    were reported. On the real code only known false positives remain (an inherited `Window.Owner`, `Math.Log`,
    declaration lines). Every theme resource the code looks up by name exists in App.xaml.

66. **Fixes from the first full Windows build (175/177).**
    * The HDFC "Statement Summary" was not read on Windows. Page text ends lines with "\r\n" there, and the trailing
      "\r" made the last number fail the number check. Lines are now split on both \r and \n.
    * The Teach Columns page suggestion counted a cover-page line such as "Period : 01-10-2026 to …" as a transaction.
      A transaction line must now start with its date, or have it right after a serial number.

## Simpler daily use: bank date, bills, remembered splits, short narration, steps

67. **Bank date (BRS).** Every posted entry carries `<BANKERSDATE>` = the statement date inside its bank allocation, so
    Tally's Bank Reconciliation shows it as reconciled. On by default; switch in More ▾ (saved in the shared database —
    new `app_settings` table).
68. **Automatic bill matching.** Pending bills now keep their side (Tally writes a debit balance as negative: negative =
    owed to us, positive = ours to pay). After Analyze, and after a ledger is changed, a bill is chosen only when exactly
    one open bill of that party has exactly the entry's amount on the right side and no other entry could take the same
    bill. Bills already chosen by hand are never reused; guessed ledgers (⚠ rows) get no bill. (`BillAutoMatcher`)
69. **Remembered splits** per company + party + direction (new `remembered_splits` table), saved with Save Split and
    removed with Remove Split. Same total → same amounts, ticked. Other total → scaled in the same ratio, rounded down to
    the paisa with the remainder on the largest line (always adds up exactly), held back as "⚠ Check split amounts". A
    split that would give a line ₹0 is not applied. (`SplitMemory`)
70. **Short narration** "Party • Mode • Ref" (`NarrationTidier`), optional. ON: shown above the original in the grid and
    posted as the first narration line with the original on the next line (written as `&#13;&#10;` so the line break
    survives XML). OFF: original only. The row's own narration is never changed. Cash, interest and bank-charge rows get
    no short line. Words carrying numbers, IFSC codes, bank codes and mode jargon are never taken as the party.
71. **Step bar, More ▾, drag & drop, colour strip.** Four steps with the current one highlighted (updated once per batch
    of row changes). Teach Columns, Export XML and Debug moved into More ▾; Bank Details and backup controls stay visible.
    Statement files can be dropped on the window (text dragged inside a cell is not affected). Each row has a coloured
    strip (`RowState`: Ready / Check / Skipped / Problem) with a key in the bottom bar; it works in light and dark themes
    and does not change any existing column, width or spacing.
    Tests added: bank date on/off, short narration text + posting, split fitting and applying, remembered split and
    settings round-trip in the database, bill matching (single / ambiguous / hand-picked / wrong side), row colours.

72. **More room for the rows.** The step bar moved into the title bar, the shortcut line became a "⌨ Keys" tooltip,
    the ML/Posted counts moved to the bottom bar, paddings were trimmed, and "▲ Hide setup" folds the two top panels
    (about 150 px more grid). Choosing or dropping a file shows them again, because Analyze is there.
73. **Tally found on any port.** Detection now probes, in order: the ports the running tally.exe has open (read from
    Windows' TCP table with the owning process, `GetExtendedTcpTable`), the usual ports, then every other port listening
    on this PC in 9000–9999. Only a server that answers Tally's company-list request is accepted; the same Tally reached
    by two addresses is listed once. When nothing answers, the status says whether Tally is not open or is open but not
    sharing data, and Detect Tally shows the one-time Client/Server setting. Tests: port order, and a fake Tally on an
    unusual port is found with nothing typed. (`TallyPortFinder`)
74. **ATM withdrawals at another bank's ATM were not recognised.** "NWD-416021XXXXXX7382-TR208703-LAKETOWN" (NWD = non-home
    withdrawal) did not match the cash-withdrawal words (ATM / ATW / NFS / CASH WDL), so it was not made a Contra to Cash.
    Added NWD, EAW (own-bank ATM), CWDR and CSH WDL, both to the Contra check and to the Mode column. ATM fees
    ("NWD CHGS") stay bank charges; a masked card number that ends like one of your own accounts does not turn it into
    a bank-to-bank transfer. Test with the exact narration.

## Still open (not changed)

* ~~Hard-block instead of warn when a statement doesn't reconcile.~~ Done (item 55).
* ~~`decimal` instead of `double` for money.~~ Done (item 61).

## Deployment notes for 5–7 users

* SQLite on an SMB share (`data_path.txt`) works with journal mode DELETE, as configured, but SQLite does not recommend
  it. The safest setup is a **Terminal Server / RDP host** with the data folder on its local disk. If you keep the
  share, use a reliable Windows file server (not a NAS with oplocks disabled), and back up `abse.db` daily.
* Give each user Modify permission on the data folder.
* Tally: enable Client/Server on the port, keep the company open during posting, and keep "Backup Tally" ticked.
