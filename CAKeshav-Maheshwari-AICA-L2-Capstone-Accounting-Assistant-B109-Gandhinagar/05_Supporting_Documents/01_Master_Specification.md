# Accounting Assistant — Master Specification (v6 / v7)

This is the single source of truth for the project. It holds every requirement and decision made so far, word for word where it matters, so nothing gets lost when a chat is summarised. Read it before building. Update it when a decision changes.

---

## A. Who it is for and the original brief (unchanged since day 1)

- **Users:** a CA practice handling multiple client companies, each with a large and growing volume of invoices every month. More than one person in the office uses it.
- **Runs offline:** a Python desktop app on Windows with a PyQt6 UI.
- **What it should feel like:** beautiful, with great UX. It must be faster than typing the entry directly in Tally, or nobody will use it.
- **Inputs:** any invoice format (PDF, scanned PDF, image, Word, Excel), read from a folder per company.
- **Tally link:**
  - TallyPrime 7+ on port 9000, on the same PC or on a LAN server.
  - Pulls ledgers, groups, stock items, units, godowns, voucher types and voucher history live from Tally.
  - Posts entries by XML import.
- **Review before posting:** always show Dr/Cr before posting. Nothing is posted silently.
- **Memory per company:**
  - remembers ledger choices and suggests the previous ledger next time
  - shared across the office (LAN PostgreSQL) with a local SQLite copy on each PC so it works when the LAN is down; outbox sync
- **Voucher style:** varies by company and by supplier. Global default entry type is **Journal** (the user said invoices are mostly booked as Journal), configurable per company and per supplier. A choice applied in the Book-as combo is remembered.
- **Line level:** stock-item level for some companies, ledger level for others; mixed is allowed.
- **Tax:** TDS, RCM and 17(5) blocked credit are all required. No cost centres. Narration is required on every voucher. Bill-wise is on where the party ledger has it (New Ref / Agst Ref / On Account).
- **Journals:** multi-ledger journals by cloning previous entries AND by rules learned from history. Examples:
  - expense + GST
  - rent with TDS + RCM
  - salary with many allowance and deduction heads
- **Gemini:** paid tier, cheapest model (`gemini-3.5-flash-lite`), escalating to full Flash only when validation still fails. Used for invoice parsing only. PAN, bank details and similar are rasterised and redacted before upload; the upload log is kept.
- **GSTR-2B cross-check:** must **never block posting**; it only flags.
- **Accuracy target:** 95% is acceptable.
- **Real-layout debugging:** debug bundles ("Export for Claude") with masked names, GSTIN (state code kept), PAN, bank, phone, PIN and email.
- **Create missing masters in Tally from the app:** supplier, and new ledgers via the "+ New ledger" button.
- **Resync Tally** button.
- **TDS suggested from the vendor's history:** ledger and rate, then section defaults with thresholds and FY aggregate. Section numbers must be checked against ITA 2025 (s.393) mapping.
- **Supplier in Tally card** (built in v5):
  - live ledger balance
  - last 5 journal or payment entries
  - Copy from a previous entry
- **Multi-user, the full version, comes later.** For now there is a posting lock per company with a heartbeat.

## B. Hard technical constraints (learned the hard way — do not regress)

- **Smart App Control / WDAC on the user's PC blocks unsigned native binaries:**
  - No PyInstaller exe. Launch via a `pythonw.exe` desktop shortcut (`tools/make_shortcut.py`).
  - Use `python -m pip`, never `pip.exe`.
  - Pure-Python dependencies only: pypdf, openpyxl, xlrd, pg8000, requests, keyring.
  - No lxml, psycopg, pdfminer or cryptography.
  - SQLAlchemy `_cy` modules are loaded as their pure-Python twins (hook in `app/__init__.py`).
  - OCR and PDF rendering go through PowerShell WinRT (Windows.Media.Ocr using `TryCreateFromUserProfileLanguages`, and Windows.Data.Pdf). Tesseract is the fallback. Close mkstemp file descriptors before PowerShell touches the files.
- **Desktop path:** may be under OneDrive. Use `desktop_dir()`.
- **Laptop scaling:**
  - The window must fit: `show_fitted()`, a responsive layout, and a collapsible document pane.
  - Every new screen must be checked at 1366×768 at 125% scaling.
- **Tally XML gotchas:**
  - Type the dates (`<SVFROMDATE TYPE="Date">`) or Tally silently uses the current FY.
  - Fetch voucher history month by month and filter by date again in Python.
  - Flatten `UDF:` namespace prefixes. Handle cp1252 and bare `&`/`<`, and salvage per record.
  - GSTIN on TallyPrime 3.0+ lives in TaxUnit (GST Registration) masters.
  - Debit amounts are negative with `ISDEEMEDPOSITIVE Yes`.
  - Accounting voucher view uses `ALLLEDGERENTRIES.LIST`. Invoice view uses `LEDGERENTRIES.LIST` plus `ALLINVENTORYENTRIES.LIST`.
  - On failure, save the raw reply to diagnostics.
- **Not yet verified on the real Tally (verify first in v6 testing notes):**
  - ledger-creation XML
  - Payment / Receipt / Contra / Sales / Debit Note / Credit Note voucher XML acceptance
  - live balance sign and format

## C. Data safety rules

- **Banking never touches Gemini.** Bank statements and banking entries are processed fully offline. This is a **hard block in code**, not just a setting: the bank module must not import or call `extract.gemini`, and a unit test enforces it.
- **Gemini is for invoices only.** It is gated by the `use_gemini` setting, with redaction always on unless `allow_unredacted_image` is explicitly set.
- **The system must learn so it relies on Gemini less over time.** For each supplier the app memorises the invoice layout (label positions and value patterns for invoice no., date, taxable amount, tax and total, plus GSTIN or HSN anchors). Once a supplier's layout is learned and the local read passes validation, it skips Gemini entirely and works fully offline.
- **Keys in Windows keyring only.** Upload log is kept.

---

## D. Release v6 — Entry, Bank, Reports, UI   — BUILT 13-Nov-2026 (81 tests); real-Tally checks listed in README

### D1. Gemini restriction and offline learning
- Hard block for banking, as in section C, with a test.
- **Supplier layout memory (`SupplierLayout` model, synced):**
  - What it stores: vendor_key, anchors (label texts with relative positions), regexes for each field, sample count and success count.
  - How it is learned: from each approved invoice, combining the final corrected values with the document's text.
  - How it is used: in `pipeline.process`, try the layout first. If the layout read passes the validator (arithmetic within ₹1, GST type, rate plausibility), use it with source `layout` and skip Gemini.
- Settings show for each supplier whether it is "Offline-ready".

### D2. All voucher types (typed entry, option A)
- New **Entry** page with tabs or a picker:
  - Payment (F5)
  - Receipt (F6)
  - Contra (F4)
  - Sales (F8)
  - Purchase (F9)
  - Journal (F7)
  - Debit Note (Alt+F5)
  - Credit Note (Alt+F6)
- Sales, Purchase, Debit Note and Credit Note support both ledger-level and item-level lines, with GST auto-split by state and place of supply, plus round-off and narration.
- Voucher type names come from the Tally master (companies may have custom types such as "Purchase GST"). Pick by base type.
- **Option B is NOT in v6:** reading sales invoices or notes from documents comes later.

### D3. Payment, Receipt and Contra restrictions (like Tally)
- **Cash/bank-side groups:** Bank Accounts, Bank OD A/c, Cash-in-Hand, including their sub-groups.
- **Credit cards** are treated as **Bank OD / CC**. The user confirmed this. Card ledgers kept under any other group can be ticked as "Treat as bank/card" per company, and then appear on the cash/bank side.
- **Which side is locked:**
  - Payment: the Cr side is locked to cash/bank ledgers.
  - Receipt: the Dr side is locked to cash/bank ledgers.
  - Contra: both sides come only from cash/bank ledgers.
- **Default:** the last cash/bank ledger used for that company and voucher type.

### D4. Bank ledger suggestions (strengthen existing)
- Suggestion order:
  1. learned BankRule
  2. a party or ledger name found in the narration (fuzzy, including UPI/NEFT/IMPS/RTGS name extraction)
  3. similar past narrations in Tally history
  4. keyword patterns (charges, interest, GST, TDS, salary, and so on)
- Show the confidence and the reason. Learn on post.

### D5. Any Indian bank's statement → Tally banking
- Auto-detect the header and columns for any bank: .xlsx, .xls, .csv, HTML-as-xls, and text PDF.
- If detection is unsure, open a **drag-and-drop mapping template**:
  - The file's columns are shown as chips; drag each one onto Date / Narration / Ref / Withdrawal / Deposit / Amount+Dr/Cr / Balance.
  - Preview the first 10 rows live.
  - The mapping is **saved per bank** (fingerprinted by header signature) and reused automatically next time.
- Keep the existing safeguards:
  - wrapped-narration join
  - balance-check warnings
  - line-hash dedupe
  - "already in Tally" detection (amount within ±3 days)
- **HDFC note:** the user's HDFC feed is already integrated in Tally by Tally itself, so it is a low priority, but the app must still be able to read it. IndusInd is the main bank to support.

### D6. Bank: match vs categorise (Zoho #2)
- For each line:
  - **Match** it to an existing Tally voucher, either one voucher or several (one receipt against several invoices), within an amount and date window.
  - **Or categorise** it as a new Payment / Receipt / Contra.
- Matched lines are marked `in_tally` and never posted again.

### D7. Bill-wise settlement on payments and receipts (Zoho #1)
- When the party ledger is bill-wise, list its open bills from Tally (Bills Outstanding for that party).
- Tick the bills to settle → Agst Ref allocations. Part payment is allowed. Any extra goes to an Advance (New Ref) or On Account.
- Works on the Entry page and in the Bank flow.

### D8. Trial Balance, Balance Sheet and P&L, read live from Tally
- Use Tally's own report export (live; no local calculation of balances).
- Drill-down: group → sub-groups → ledgers → vouchers (ledger statement) → voucher detail.
- Excel export with indentation and totals (openpyxl).
- Period picker as in D9.

### D9. Period picker everywhere it matters (user: "Must Must Must")
- **Shared widget.** Default is the **current FY**. Quick picks: This month / Last month / This quarter / This FY / Last FY / Custom (from–to).
- **Used on:** reports, Tally sync history range, bank lines, invoice queue, GSTR-2B, journals, Supplier in Tally card (balance and entries), dashboards, and search.
- Remember the last choice per page.

### D10. Simpler purchase and journal screen
- Why: the current screen is hard to follow, and a user might decide to post directly in Tally instead.
- **Form first:** Supplier, Bill no., Bill date, Amount, Expense head (or items), Book-as.
- **Automatic items shown as small labels**, which you open to edit:
  - GST split (IGST, or CGST+SGST)
  - TDS (section, rate, amount)
  - RCM
  - 17(5) blocked credit
  - round-off
  - narration
- **Dr/Cr grid** is hidden behind a "Show entry" toggle; it stays available for review and editing.
- **Keyboard:** Tally-style shortcuts — Enter moves to the next field, Alt+C creates a ledger, Ctrl+A posts, Esc goes back.
- **Green-confidence suggestions:** one **Accept & Post** button.
- Keep: the Supplier in Tally card, the missing-supplier banner, the document pane toggle, and duplicate and validation warnings.

### D11. Period lock per company (Zoho #4)
- Lock up to a date for each company (for example after GST filing).
- Posting into a locked period needs an override with a reason, which is written to the audit log.

### D12. Recurring entries with reminders (Zoho #5)
- Templates for rent, salary, AMC, EMI and similar: frequency, day of month, and amounts (fixed, or "last + editable").
- A due list appears on the 1st, or on the chosen day, with pre-filled vouchers. One click posts after review.
- Builds on the existing journals.py recurring and clone logic.

### D13. Original document linked to each posted voucher (Zoho #9)
- Store the voucher GUID or number against the stored invoice file.
- Clicking any posted voucher (in reports drill-down, search or the Supplier card) opens the original document.

### D14. Home dashboard per company (Zoho #10)
- Cash and bank position (live).
- Payables due this week.
- Overdue receivables.
- Estimated GST and TDS payable for the period.
- Pending invoices and bank lines.
- Recurring entries due.
- Period-aware (D9).

---

## E. Release v7 — Dashboards and Controls   — BUILT 13-Nov-2026 with F1-F5 below (96 tests)

- **E1. TDS tracker:** deducted vs paid by section; challan due on the 7th (30 April for March); unpaid TDS; vendors nearing the threshold; 26Q-ready export.
- **E2. GST control panel:** ITC reversal under the 180-day unpaid rule (Rule 37), RCM liability for the month, 17(5) blocked credit summary, and 2B mismatches. It never blocks posting.
- **E3. AP/AR ageing:** vendor payment schedule and customer reminder emails drafted (not sent automatically).
- **E4. Global search across all companies:** amount, bill no., party, GSTIN, narration.
- **E5. Month-end close checklist per company:**
  - items: bank recon, 2B recon, TDS paid, GST filed, depreciation, recurring posted
  - each item shows its status, who did it and when

### v6 feedback to include in v7 (user, 13-Nov-2026 10:19 - verbatim intent, do not drop)
- **F1. Automatic lines in every Dr/Cr grid** (Workbench, New entry Journal, Journals page): no need for
  + Line / − Line. While Dr ≠ Cr, pressing Tab past the last line adds a new line (pre-filled with the balancing
  amount on the short side, like Tally). A new line left empty disappears when you leave it. Keep the buttons
  only as a fallback.
- **F2. Bank duplicate protection before posting to Tally.** Example: bank already entered in Tally up to 15-10,
  user imports a statement for 01-10 to 31-10 by mistake. The app must eliminate the duplicates before anything
  is posted. Check from all aspects: date, amount, direction, narration, cheque/UTR reference, and running
  balance, against (a) lines already imported and (b) vouchers already in Tally for that bank ledger. Show
  duplicates clearly and exclude them by default.
- **F3. Bank closing balance must agree with Tally.** Compare the statement closing balance (on its last date)
  with the Tally bank ledger closing balance on the same date (live). Show both figures, the difference and the
  lines that explain it (in statement not in Tally / in Tally not in statement). Re-check after posting.
- **F4. Ledger fields keyboard-friendly everywhere** (every LedgerCombo: Workbench form, grids, New entry,
  Bank, Journals, Settings): reachable by Tab, the text is fully selected on focus (Tab or click), so typing
  one letter replaces it and the matching ledger list pops up immediately.
- **F5. Schedule III Balance Sheet and Statement of Profit & Loss.** Map each Tally ledger once (per company) to a
  Schedule III heading / sub-heading / note. The app suggests the heading from the Tally group and ledger name;
  the user can change it, and the mapping is remembered (new ledgers are suggested, unmapped ones flagged).
  Both statements are built live from Tally for the period, with Notes. Export to Excel.
  **Decided: Division I (AS) only for now**, with the previous-year column read from Tally. Division II (Ind AS)
  later.

## F. Parked / later

- **Maker–checker approval (Zoho #3):** parked by the user ("ignore for now").
- **Option B:** reading sales invoices, debit notes and credit notes from documents.
- **Full multi-user mode.**
- IMS actions.
- Code signing.
- Client portal, budgets, expense claims.

## G. Definition of done for each release

- All existing tests stay green, and new tests cover each new item:
  - the Gemini banking block test
  - restriction of the cash/bank side for Payment / Receipt / Contra
  - mapping fingerprint save and reuse
  - bill-wise Agst Ref XML
  - period lock override
- New XML runs against `tests/fake_tally.py` routes, including a Bills Outstanding route and report routes.
- Screenshot smoke test of every new screen at 1366×768 at 125% scaling, with no overflow.
- Packaged as a zip with README notes on what to verify on the real Tally.

## G. v8 — Suspicious transactions repository (red flags)   — BUILT 13-Nov-2026 with H1-H7 and the new UI (104 tests)
User request 13-Nov-2026: a repository of suspicious transactions red-flagged by the system, using Income-tax,
GST, SFT (old AIR) and other rule sets, able to spot rule-bypassing and round tripping. To be built in v8 after
v7 feedback. Rule list proposed in chat (categories A-L): cash limits, structuring, SFT thresholds, TDS evasion
patterns, related parties / deemed dividend, round tripping and circular flows (graph cycles), accommodation
entries / bogus purchases, year-end window dressing, GST fake ITC / circular trading / e-way bill splitting,
MSME 45-day rule, personal / capital expenditure, statistical anomalies (Benford, duplicates, round amounts).
Each flag: rule, severity, score, evidence, status (open / explained / false positive) with reviewer sign-off;
explained patterns suppress repeats. Indicators for review, never conclusions. Offline only (no Gemini).
Section numbers to be verified against ITA 2025 (cash rules s.185-188 per secondary sources) before coding.
**v8 decisions (user, 13-Nov-2026 11:01):**
1. Build ALL rule groups (A-J as proposed in chat: cash limits, SFT thresholds, TDS bypassing, related parties,
   round tripping / circular flows, timing & book quality, GST, banking patterns, expenditure nature, statistics).
2. Related parties: the user will supply the list per company (enter / import); the app shows every transaction
   with each related party (party-wise view across ledgers) in addition to the 40A(2) / deemed dividend /
   s.185 checks.
3. Flags live in a SEPARATE "Red Flags" repository page (not shown on Workbench / Bank posting screens).
**v8 UI feedback (user, 13-Nov-2026 11:04):** "UI needs to look like a professional tool and not like a native
tool developed by some school boy. Add more colors to it."
  Agreed design (user: "looks good to me"): deep navy sidebar with icons; an accent colour per module (e.g. teal
  Bank, violet Reports, amber Compliance, red Red Flags); coloured stat tiles on Home; cleaner tables; a proper app
  icon; optional dark mode. Keep it fitting 1366x768 @125%.

### v7 feedback for v8 (user, 13-Nov-2026 11:46) - fix all
- **H1. Invoice folder can't be chosen from the main screen** (folder label in the top bar is display-only; the
  setting is buried in Company settings). Make the folder label clickable → folder picker; also a "Change
  folder" button on the Workbench; show the full path as tooltip.
- **H2. Bank and Reports pages load very slowly.** Causes in v7: Bank recomputes suggestions for every line on
  each reload, each scanning the whole voucher history; Reports fetches live on every show (two full ledger
  collections + stock). Fix: index history once per company (token -> vouchers, amount/date index), cache
  suggestions per line until history/rules change, load in background with the table shown at once, Reports only
  on Refresh (keep last result per company + period, show "as of hh:mm").
- **H3. Trial Balance not picked up correctly** - details awaited from the user (which figures differ vs Tally).
  Suspects: ledger collection closing ignoring the period; opening balances; groups reaching Primary under a
  different parent label; ledgers under reserved sub-groups. Verify against Tally's own Trial Balance export
  (TALLYREQUEST Export, Report "Trial Balance") and use that as the source / cross-check.
- **H4. P&L must include the Trading Account**, as Tally shows it: Trading A/c (Opening stock, Purchases,
  Direct expenses | Sales, Direct incomes, Closing stock) -> Gross Profit c/o, then Profit & Loss A/c
  (Gross Profit b/f, Indirect incomes | Indirect expenses) -> Nett Profit. Closing stock for accounting-only
  companies comes from the Stock-in-Hand ledger balance when there are no stock items.
- **H5. TDS sections: everything shows 194C and can't be changed / set to N.A.** Fix: guess the section from the
  expense ledgers used with the party (professional/consultancy -> 194J, rent -> 194-I, commission -> 194H,
  contract/labour/job work/transport -> 194C, goods purchase -> 194Q only above the limit), mark insurance
  premium, hotel / travel, utilities, govt fees, bank charges, GST-only parties etc. as "Not applicable" by
  default, and let the user set Section / Not applicable per party (dropdown), remembered for the company and
  used everywhere (tracker, threshold watch, invoice suggestions).
- **H6. Rule 37 ITC reversal flags bills that are already paid.** Payments are often entered On Account /
  without Agst Ref, so Tally's pending bills overstate dues. Fix: per supplier, take the actual ledger closing
  balance and settle bills FIFO (oldest first) against all payments / debit notes; only the part of the newest
  bills not covered by the real balance counts as unpaid. No flag when the party's balance is nil or debit.
  Show the working (bill, payments applied, balance) on the row.
- **H7. TDS section labels by date of the transaction (user, 11:50).** Income-tax Act 2025 applies from
  01-04-2026: TDS on non-salary payments is consolidated in s.393 (residents: 393(1) table serial numbers;
  non-residents 393(2)); salary s.392; TCS s.394. Show the label by the voucher date:
  before 01-04-2026 -> old section ("194C"); on/after -> new reference with the old one in brackets, e.g.
  "393(1) Sl. 6(i) (old 194C)". Same in the tracker, 26Q / new-form export (use the new payment codes for the
  return), vendor settings and invoice suggestions. Keep the mapping (old section -> 393 table entry, payment code,
  rate, threshold) in one editable table. Secondary sources DISAGREE on serial numbers / payment codes and some
  rates (e.g. 194H), so verify every row against the bare Act text and the CBDT payment-code notification
  before coding; the user reviews the table once.

## v8.1 — Speed fixes (user: "Bank tab takes a lot of time… fast processing of every tab")
Causes found:
- Every table row built its own widget (dropdown/checkbox) with its own style sheet: ~50 ms per row, so 150 bank lines ≈ 16 s.
- Many features re-read the whole Tally voucher history from the database on every open.
- Fuzzy ledger matching compared every line against every ledger.
Fixes:
- Tables draw dropdowns/checkboxes on demand (delegates): Bank ledger column, vendors, TDS sections, Sch III mapping, bill-wise dialog.
- Colours via properties (`tone()`) instead of per-widget style sheets (Workbench, Entry, chips).
- In-memory voucher history index per company, rebuilt only when history changes (engine/history.py).
- Ledger list cached per company; fuzzy matching cached with a trigram prefilter.
- Workbench verdict cache + painted invoice queue.
Rule for future work: never setCellWidget/setStyleSheet per row; use delegates and tone().
Measured (2,500 ledgers, 12,000 vouchers, 300 bank lines, 400 invoices): Bank 16.5 s→0.34 s; Workbench 32 s→0.5 s (first open ~1.9 s); other tabs ≤0.2 s; Journals ~0.1–0.7 s.

## v8.2 — feedback on v8.1 (13-11-2026)
- K1 Home didn't refresh after posting: Home re-reads every time it is shown if anything changed (posting, sync, set-aside) or after 2 minutes; counts always fresh. One `st.changed(company)` signal drops all caches; Reports, Compliance, Red flags reload on next show.
- K2 Home showed one bank only: every Cash/Bank/OD/card ledger listed (zero balances too, names matched loosely), plus bank ledgers Tally has that weren't synced yet.
- K3 Cleared invoices still pending on Home: same cause as K1.
- K4 Red flags counted bill + payment twice: party volume uses only the business side (supplier credits, customer debits); D17 amount = larger side, Dr/Cr still shown.
- K5 Bank ledger overtype: landing on the ledger cell (Tab/arrows/Enter) opens it with the whole name selected; typing replaces; typing on a closed cell opens it with that letter; Enter takes the highlighted match and moves to the next line's ledger (Tally-like).
- K6 False balance difference: statement closing worked out from the running-balance chain (row order changed when lines were posted). If the difference equals unposted lines it says so.
- K7 Sync not reflecting: (a) posted vouchers now added to the local history at once; (b) history cache could survive a re-sync (SQLite reused ids) - generation counter; (c) Sync always pulls up to today and at least the current FY regardless of the period picker; (d) every screen refreshed after Sync, summary shows the date range.

## v8.3 — foreign-currency amounts (13-11-2026, client company data)
- Root cause of: IndusInd balance 0, Sales missing in Trading/P&L, one of two Share Capital ledgers missing, TB/BS not matching (H3).
- Tally sends forex amounts as `-$ 50000.00 @ ₹ 90.5291/$ = -₹ 4526455.00` (₹ often arrives as '?'). The old reader cut at '@' and failed on '$' -> 0. Every ledger whose opening or any entry was in USD read as nil.
- parsers.amount now takes the rupee figure after '='; with no '=' it uses forex qty x rate; strips any currency symbol. Applies to ledger balances, voucher entries, bill allocations and the TB report.
- Verified against the real voucher export in diagnostics: all vouchers balanced, USD sales now read in rupees.

## v8.4 — P&L A/c in Trial Balance / Balance Sheet
- Tally's ledger closing for "Profit & Loss A/c" already includes the current FY profit (closing = brought forward + current FY profit). The app put that in the TB *and* listed revenue/expense ledgers -> TB difference equal to the profit; BS counted the profit twice.
- Now: TB and BS use the brought-forward part only (closing minus FY-to-date profit incl. stock movement); BS adds "Current period" separately. Verified on the client's diagnostics: every TB group equals Tally's own TB, Dr = Cr, BS balances.

## v8.5 — "Memory Access Violation" on connecting a newly opened company
- The app asked Tally for the Company object's GST sub-list (COMPANYGSTREGDETAILS.LIST) when listing companies, and for *all* methods of Company / GST Registration (NATIVEMETHOD *) when looking for the GSTIN. Both are known to crash some TallyPrime releases/companies.
- Now only plain fields are requested; GSTIN lookup stops at the first source that has it; if Tally falls over during that lookup the company is remembered (gst_probe_skip.json) and the step is skipped next time (enter GSTIN in Setup).
- Clearer message when Tally drops the connection mid-reply.

## v8.6 — Receipts refused by Tally ("0 errors")
- Postings log (local.db) showed all 6 Receipts of the second client company returned CREATED 0, ERRORS 0, EXCEPTIONS 1 - a silent refusal; tally.imp (TallyPrime Edit Log folder) had no reason either. The same XML shape posted fine in the first company, and the second company's Payments (numbering "Automatic") posted; its Receipt type is "Automatic (Manual Override)".
- Now: for types numbered "...Manual..." the app sends the next voucher number itself (engine/numbering.py continues the last number's pattern within the FY, prefix/padding/year kept). On a silent exception it retries: with number -> credits first (Tally's own order) -> both; the variant that works is remembered per company + voucher type (company.settings.post_variants). Only silent exceptions are retried (never after a create or a real error), so no duplicates.
- If all fail, the message says Tally gave no reason and to enter one by hand to see Tally's own message.
- v8.6.1: Journal still refused - the app sent No. 135, which already existed (entered in Tally after the last Sync). The next number is now read live from Tally (voucher_numbers collection: that type, current FY) together with the local copy, and an existing number is never reused. Receipts confirmed working with numbers.

## v8.7 — Real-data safety net (agreed 14-11-2026)
1. Real-data fixtures: during development, recorded Tally replies from client companies were kept as test fixtures. In this submission copy they are replaced by tests/demodata/ + tests/test_demodata.py (fictional): the demo company's closings, groups, a Trial Balance file in Tally's report shape computed directly from the demo books, the demo day book, and small hand-made Tally replies for a USD export invoice, a Latin-1 narration and a numbering series. Asserts: every TB line = Tally's TB; Dr = Cr; Balance Sheet and Schedule III balance; known figures from the answer key; vouchers parse and balance; next journal No. 137.
2. "Check company" (toolbar): read-only, live: company open; day book complete (Tally master IDs vs app); TB vs Tally TB line by line; Balance Sheet; Schedule III; each bank vs its statement; voucher numbering (types with Manual Override, next number); GSTIN. Optionally saves every request + raw reply to diagnostics/capture_<company>_<time>/ - new real-data fixtures come from there.
3. Fixed while building it (found only by the real data):
   - Tally adds a computed line "Unadjusted Forex Gain/Loss" for foreign-currency balances - now taken from Tally's TB report into TB and Balance Sheet.
   - Schedule III ignored Profit & Loss A/c (brought-forward surplus) - now always Reserves & Surplus with the b/f part only; forex line included; Suspense shown (not ignored) under other current assets/liabilities with a note.

### Release rule (every build)
- All tests pass, including tests/test_demodata.py.
- Each fix is checked against the user's real Tally (Tally connection / diagnostics / capture folders) before it is called done - not only against the simulated Tally.
- A Tally reply that broke something is added as a test fixture (anonymised or fictional) before the fix ships.

## v9 plan (agreed 14-11-2026) - NOT started; build only on the user's go-ahead
Chosen: 2 Office dashboard, 3 Setup wizard + installer, 5 Reimbursements/petty cash in bulk, 7 Export receivables & forex.
Declined for now: maker-checker roles (would slow the process). Later candidates: client query sheet, salary JV, month-end one-click, bank auto-post, audit/MIS packs.

### 2 Office dashboard (all companies on one screen)
- One row per company: invoices waiting, bank lines unposted (per bank), last Sync, Check-company status (last run, problems), GST/TDS due dates and status, period lock date.
- Click a cell -> opens that company on that page. Runs from local data (fast); "Refresh live" re-checks Tally for the companies open in Tally.
- Sort/filter: "needs attention", by due date. Export to Excel.

### 3 Setup wizard + installer
- First-run wizard: Tally host/port test -> companies list -> pick companies -> first Sync -> bank ledger + mapping -> invoice folder -> Gemini key (optional, invoices only) -> run Check company.
- Installer: must work under Smart App Control (unsigned .exe from PyInstaller gets blocked). Approach: one setup .bat/.ps1 that installs official Python (signed) if missing, creates venv, pip-installs pure-Python deps, creates the shortcut; "Update" = same script pulling the new zip. Settings/data untouched.

### 5 Employee reimbursements & petty cash in bulk
- Input: a folder of bills (photos/PDFs) + optional expense sheet (Excel: date, employee, description, amount). Bills read like vendor invoices (Gemini, redacted); sheet rows matched to bills.
- Output: one Journal per claim (or per bill): expense Dr / employee ledger Cr ("Paid by <employee>" in narration, as the user's clients do), GST input only when bill is a valid tax invoice in company's name; review grid before posting; duplicate check by bill no/amount/date.
- Petty cash: same flow with Cash ledger as credit (Payment voucher).

### 7 Export receivables & forex (USD clients)
- Register of export invoices in foreign currency: invoice date, USD amount, rate booked, receipts (from bank lines / Tally), USD outstanding, ageing.
- Realisation: link each inward remittance to invoices (FIFO or chosen), realised exchange gain/loss, FIRC/e-BRC number & date (entered or read OFFLINE from bank advice - banking is never sent to Gemini), LUT number/validity reminder.
- Month-end revaluation: outstanding USD x closing rate (entered) vs book -> proposed forex gain/loss journal for review (clears Tally's "Unadjusted Forex Gain/Loss").
- Reports: realisation status (9-month rule watch under FEMA), Excel export.
### v9 decisions (14-11-2026)
- Reimbursements: one common ledger (e.g. "Employee Reimbursement"), employee name in narration (as the user's clients do).
- Forex closing rate: typed by the user each month; app remembers the last rate.
- Delivery: all four items together as one v9 release.

## v9 — BUILT (14-11-2026)
- Office page (sidebar, 2nd): all companies from local data - invoices waiting, bank lines to post (per bank in tooltip), last sync, last Check company result (saved per company), TDS / GSTR-1 / GSTR-3B for the month just ended (7th / 11th / 20th; done = Close-checklist tick), Close x/8, needs-attention; click a cell -> that company on that page; filter; Excel. engine/office.py.
- Setup wizard (first run, and Setup > Companies & Tally > "Setup wizard…"): Tally test -> tick companies -> Sync -> invoice folder + main bank per company + Gemini key -> Check company. ui/setup_wizard.py.
- Installer: "Setup or update.bat" (official Python via winget if missing -> pip install -r requirements.txt -> check_env -> shortcut) and "Update from Downloads.bat" (newest acct_assistant_v*.zip in Downloads -> Unblock -> copy over -> setup). requirements-dev.txt holds pytest; pyinstaller dropped.
- Claims page: folder of bills (+ optional expense sheet, header auto-detected) -> one entry per bill; reimbursement = Journal Dr expense (+ input GST only if supplier GSTIN valid AND bill in company's GSTIN) / Cr common reimbursement ledger (auto-found: name containing 'reimburs'), narration "<description> (Bill …)\tPaid by <employee>"; petty cash = Payment Cr Cash. Expense ledger learned from past 'Paid by' journals, remembered per supplier, else keyword hints. Duplicates by file, bill no + supplier, date + amount + employee. engine/claims.py, model ClaimLine.
- Exports page: register from the day book (Sync keeps foreign amount, rate, currency per entry), allocation saved > Tally bill ref > FIFO; exchange difference per invoice minus what is already in Tally; 'Enter exchange differences' posts the office's own pattern (voucher type 'Forex' if present: Dr client Agst Ref invoice / Cr 'Forex Gain Or Loss' for a gain; client amount in Tally's forex form "$ 0.00 @ ₹ /$ = -₹ X"); 9-month realisation watch; FIRC / e-BRC per receipt (model ExportRecord); LUT; month-end revaluation at a typed rate (remembered). engine/exports.py.
- Bank: receipts/payments for a foreign-currency party now carry the foreign amount and rate from the bank narration ("USD50000.0@95.1625") - read on this PC only.
- Fixed from real data: invoice-view vouchers carried each entry twice (both entry lists read) -> only one list used; ledger CURRENCYNAME synced.
- Needs one Sync per company after updating (foreign amounts, currency, the duplicate-entry fix).
- Not yet verified on live Tally: posting of the 'Forex' entry and of forex bank receipts (format copied from Tally's own export). First use: check the entry in Tally.

## v9.1 — crashes (14-11-2026)
- App closed on "+ Line" (Workbench/Entry grid): the row was built cell by cell with signals on; the Workbench read all rows half-way (item missing, no meta) -> exception -> PyQt6 aborts the process on any unhandled exception in a slot. Row now built with signals blocked; lines() tolerant.
- Safety net (main.py): unhandled errors are written to %APPDATA%\AccountingAssistant\logs\errors.log and shown in a message; the app keeps running. Native crashes go to logs\crash.log (faulthandler).
- Tally crashes (Memory Access Violation): requests are now sent one at a time per Tally (global lock + 50 ms gap) - background screens, posting and the number lookup used to hit Tally together. Every request logged in logs\tally.log (what, time, result) to pin down any further Tally crash.
- Posting: every caller sends a REMOTEID (bank-<line>, claim-<id>, entry-<uuid per entry>, rec-<id>-<date>, fx-<hash>; invoices already did) -> a repeat after a crash updates the same voucher, never a duplicate. Tally answering "altered" for our REMOTEID = "Was already in Tally - updated" (counted as done; was shown as failure). Silent refusal with a number -> next numbers tried (up to 3).

## v9.2 — fixes from the demo data pack (17-11-2026)
Found by running the Aarohan Infotech demo pack (fictional company, FY 2026-27) through the app; each has a test in tests/test_v9_2.py.
- Bank: a "Debit/Credit" marker column is claimed as the Dr/Cr column before Withdrawal/Deposit matching (was read as all credits). "Debit / Credit" spacing normalised.
- Offline invoice reading: invoice numbers are rejected as dates only if the whole value is a date (CN/INV/26-11/0457 kept); "Note No." / "Credit Note No." labels read; "Against Invoice" never taken as the document number; document type (tax invoice / credit note / debit note / bill of supply) and original invoice number read; per-line GST% column builds rate slabs for mixed-rate invoices; a printed Total on the amount-in-words line is read and kept even when it disagrees (validation flags the difference).
- Supplier credit note -> Debit Note voucher (all sides reversed, stock out, party Agst Ref to the original invoice; TDS not reversed, flagged). Gemini schema has original_invoice_no.
- Validation: place of supply in another state -> warning that ITC is not available in this GSTIN (tick ITC blocked).
- Posting: GST lines that land on the same ledger (one 'Input CGST' for several rates) are merged; a single bill allocation always carries the line amount (edited amounts stay valid).
- Tally voucher reader: item invoices now include the purchase/sales ledgers inside ALLINVENTORYENTRIES accounting allocations (vouchers balance in history; goods purchases visible to TDS/red flags).
- TDS / red flags: salary TDS deductee = "Employees (salary - Form 24Q)", never PF/statutory ledgers; C14 skips 192 and statutory ledgers; C11 treats parties credited mainly through Purchase Accounts as goods (194Q, Rs 50 lakh) instead of 194C; I49 skips depreciation entries.
- PDF text healing (v9.2): splits just before a comma or point ('2 ,78,645.00'), numbers split into several pieces by single spaces ('2 1,2 52.60' -> '21,252.60'; column gaps are wider and stay), reference segments ('SKP/112 5/2 6-2 7') and GSTINs broken by spaces are rejoined. Found when the sample invoice's text layout shifted.
- Item invoices (v9.2): XML now carries <VCHENTRYMODE>Item Invoice</VCHENTRYMODE>. Without it TallyPrime imported the demo hardware purchases as Accounting Invoices - ledger lines kept, stock lines dropped (0 Nos inward) - and every later hardware sale / purchase return became an import exception for want of stock (tally.imp: 389 created, 5 exceptions). Applies to Workbench item-invoice posting too.
- Ledgers created by the app under Purchase Accounts / Sales Accounts now carry AFFECTSSTOCK = Yes (Tally's own default; overridable). It was always No, so item invoices through those ledgers kept the amounts and dropped the quantities - found on the demo company, where even item-invoice entries left stock at nil.
- Bank lines entered in Tally after their import (a transfer posted as Contra from the other bank's statement, a card autopay posted from the bank) are re-checked every time a bank's lines are shown: bank.recheck_new_lines marks them 'in_tally' and a message lists them. Vouchers already explained by that bank's posted / in-Tally lines are set aside first, so a second line of the same amount is not hidden. Same 3-day window and scoring as at import.
- Setup > App settings > Gemini: "Remove saved key" deletes the key from Windows Credential Manager (config.delete_secret) and turns Gemini off. Saving with a blank box keeps the old key, as before.

## v10 — premium look (18-11-2026)
User: "make it extraordinary… 3D labels, mouse hovering, multiple colour themes… should look like a paid app". Reference: a dark neon dashboard mock-up.
- Themes (ui/theme.py): Midnight Neon (default), Aurora Teal, Royal Navy & Gold, Graphite, Pearl (light). Old settings "light"/"dark" map to Pearl/Midnight. Switch live from the top-bar "◐ Theme" menu (swatches) or Setup > App settings; remembered. Values read by QColor() stay hex; translucency only in the stylesheet (GLASS, TOPBAR).
- ui/fx.py: GlowTile (gradient body, gloss + bevel = depth, embossed number, glowing sparkline, lift + glow animation on hover, whole tile clickable), GlassCard (translucent, glowing gradient top edge, accent border + coloured shadow on hover), GradientLabel (accent-gradient heading). Effects only on Home's handful of widgets - never on tables (speed rule).
- Home rebuilt: gradient company title, live pill, 3 tiles with 14-day activity sparklines (dashboard.activity: invoices handled, statement lines, entries posted - local data), Cash & Bank with coloured dots per kind and a Net position bar, GST as a headline figure, payables/receivables with due / overdue chips.
- Shell: grouped sidebar (WORK / OUTCOMES / ACTION / SYSTEM) in a scroll area, glowing active item, status pills, window background gradient. Top bar breakpoints: <1520 px short labels, <1320 px folder + page title hidden. Checked at 1366x768 @125%, 1440, 1600, 1920.
