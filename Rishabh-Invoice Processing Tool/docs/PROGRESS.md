# Progress log

## Phase 1 – Foundation ✅ (v0.1.0)

Built:
- Project structure (ui / services / core / db layers), logging to `%LOCALAPPDATA%\IPT_DATA\logs`.
- SQLite database with users, companies, financial_years, audit_log, app_settings, schema_version.
- First-run admin setup, login, roles (admin / accountant / reviewer), password hashing (scrypt).
- Company management: add / edit / enable-disable, GSTIN live validation with check digit,
  state auto-filled from GSTIN, Tally connection details per company.
- Financial years per company (Apr–Mar), books beginning date, lock/unlock, duplicate prevention.
- Folder layout created per company/FY: Invoices, GSTR2B, Purchase_Register, XML, Reports.
- Top-bar company and FY switchers (remembered between sessions), dashboard with real counts.
- User management (add, change role, reset password, activate/deactivate; last admin protected).
- Read-only audit trail viewer.

Tests: 23 passing (GSTIN, money, auth, companies/FY isolation, offscreen UI navigation).

Verify: run_ipt.bat → create admin → add two companies → add FYs → switch in top bar →
check Audit Trail shows each action.

Known limitations: Alembic not yet configured (Phase 2 task 2A does this first).

## Phase 2 – Invoice processing ✅ (v0.2.0)

Built:
- Schema v2 (documents, extraction_results, suppliers, invoices, invoice_items, validation_results) with
  automatic upgrade of v1 databases; the DB file is backed up before every migration.
- Upload queue: files, folders, drag & drop; originals copied to Companies/<co>/FY_xx/Invoices; SHA-256
  duplicate-file warning; locked FY blocks uploads; remove/clear with confirmation.
- Extraction (offline): PDF text layer (PyMuPDF) → Tesseract OCR for scans/images; layout-based parser for
  header fields, GSTINs (company's own GSTIN = buyer), place of supply, totals and line items (multi-line
  headers supported). Per-field confidence; missing fields stay empty. Every attempt stored in history.
- Background worker with Start / Pause / Resume / Cancel / Retry failed.
- Validation engine: GSTIN checksum/state, buyer vs company GSTIN, FY/future dates, POS-based
  CGST+SGST vs IGST, CGST = SGST, GST rate plausibility with 22-09-2025 rate-change warnings, item maths,
  item total vs taxable total, invoice total vs taxable+tax+charges, round-off, negatives, HSN format,
  credit/debit note reference, foreign-currency rate, duplicate invoice (GSTIN + normalised number + type).
- Review window: page preview (zoom/rotate/pages), colour-coded editable fields, items grid, validation
  list (double-click jumps to field), history; Save/Validate/Approve/Reject/Delete; admin override with
  remark; approved invoices locked.
- Processed Invoices list with filters, bulk approve/reject, Excel export (summary + item sheets).
- Supplier Masters (auto-created from valid GSTINs, editable Tally ledger name).

Tests: 44 passing, incl. the user's sample invoice, synthetic intra-state multi-rate / inter-state IGST /
credit-note PDFs, OCR on an image (runs only where Tesseract is installed), v1 → v2 upgrade.

Known limitations:
- Only one real sample invoice so far (₹0 value). Accuracy on other layouts must be checked with more
  real invoices; the parser is rule-based and will need tuning per supplier format.
- Cloud AI extraction is not built (offline only). OCR needs Tesseract (docs/OCR_SETUP.md).
- Multiple invoices inside one PDF are not split automatically.
## Phase 3 – Tally integration ✅ (v0.4.x, tested on the user's TallyPrime)
Built: connection test, master sync (ledgers, groups, stock items, units, godowns, voucher types), master
mapping with remembered rules, purchase voucher XML (Item Invoice mode, mirrors the user's own vouchers),
import with duplicate check in Tally's Day Book, re-find verification, import log, re-check, creation of
GST ledgers on request.

v0.4.2 fixes:
- Ledger entry order: the party ledger is now the FIRST ledger entry, then GST ledgers, charges, round
  off (as in the user's own vouchers). Before, Tally's invoice view showed the party as an extra line and
  hid Input CGST (seen on the Majisa test voucher SYC/26-27/135). Test asserts the order.
- Re-check of a "success" import whose voucher was deleted in Tally marks it "deleted in Tally" and puts
  the invoice back to "approved" so it can be imported again. Only after Tally confirms the company is
  open and the Day Book answered; a Tally error never counts as "deleted".
- Times in the audit log, import log and invoice history are shown in local time (stored as UTC).
- Invoice Processing shows live status per page ("Reading page 3 of 9", "Second OCR pass").

Not yet: credit/debit notes and reverse-charge invoices (blocked with a clear message), foreign currency.

## OCR improvement (v0.4.2) – measured on the user's 9-bill phone scan (Scanned Document 37.pdf)
Ground truth: 7 fields x 9 bills (invoice no, date, supplier GSTIN, taxable, CGST, SGST, total).
- Before: 6/63 correct, several wrong amounts with 0.75 confidence (e.g. CGST "2.00" read from "2.5%"), 40 s.
- After: 57/63 correct, **0 wrong values**, 28 s. Unreadable fields stay empty for the user.
What changed:
- Pages are rendered to ~2480 px wide whatever their point size (phone scans were blown up 4x), and OCR
  boxes are scaled to an A4 width so the layout rules fit every scan.
- Image cleaning: background flattening, black/white, removal of table rules, deskew (up to ±4°) with
  OpenCV (`install_ocr_boost.bat`, offline wheels); a Pillow-only cleaning is used when OpenCV is missing
  (47/63 on the same bills, also with every inconsistent amount flagged).
- Second OCR pass (sparse text) only for fields still empty; it never replaces a first-pass value.
- Arithmetic check (`services/extraction/reconcile.py`): the unique combination of printed numbers where
  taxable x GST slab = tax and taxable + tax (+ round off up to Rs 1) = total. Fills empty fields; a
  label value that is really another field's number is corrected; any other disagreement is kept and
  marked low-confidence. Amounts in words are candidates too. Rs sign misread as '7' is handled.
- Rates are no longer read as amounts; GSTIN repair handles a stray inserted character, '@', '!', S/8
  (fewest changes wins, only when unique); dates like '6.Oct-26', '18-Oct-2600'; label words located
  inside merged header boxes.
- Line items: tax / round-off / batch rows are no longer items; qty x rate must equal the amount and items
  must add up to the taxable value, otherwise items are flagged (0.55) for review.
On the user's Windows PC (Tesseract 5.5.3, OpenCV 4.14) the same 9 bills give ~53/63; one wrong value is
not flagged (an invoice no. misread 229 -> 2209). v0.4.3 adds: a damaged copy of the company's own GSTIN is
never taken as the supplier; round off above Rs 1 from OCR is rejected; a tax amount equal to a GST rate
(2.50) is replaced by the arithmetic-checked amount; OCR noise as supplier name is flagged;
`ocr_check.bat` runs a read-only OCR check of a file.
v0.4.5: supplier name comes from the Tally ledger with the same GSTIN (or the Tally ledger name set in
the supplier master) at 95%, which also confirms an OCR-repaired GSTIN; label words ('No. Dated') are no
longer taken as names and 'original for recipient' no longer starts the buyer block; a missing invoice
number is re-read from a zoomed box under the 'Invoice No.' label (accepted only when 3+ readings agree,
flagged for checking); a total read with the rupee sign as '2'/'7' is corrected when the arithmetic and
the amount in words agree; GSTINs printed without a label are found. Container: 59/63, 0 wrong values
above the review threshold. Re-extraction of a file re-reads only pages whose invoice was deleted.
Tests: tests/test_ocr_rules.py (synthetic data only). Known limits: invoice numbers printed in light grey
or whose label is lost in OCR stay empty; line items on phone scans usually need manual correction.

## Phase 4 – GST reconciliation ✅ (v0.6.0)
Built:
- 4A GSTR-2B upload: portal **Excel** (sheets B2B, B2BA, B2B-CDNR, B2B-CDNRA, ISD, ISDA, IMPG, IMPGSEZ; headers
  found by their text, two-row headers combined; return month read from the Read-me sheet or asked) and JSON
  (data → docdata, old items[] and new flat layouts, ZIP). One current file per month; replace asks to confirm and
  keeps history; wrong GSTIN / FY refused. Page: GSTR-2B Upload.
- 4B Purchase register: **Fetch from Tally** (Day Book month by month, read-only; Purchase → invoice, Debit Note →
  supplier credit note, supplier Credit Note → debit note; ledger lines classified with the synced masters) or
  **Excel import wizard** (sheet, header row with preview, column mapping incl. several amount columns, saved
  templates, rejected rows with reasons + export). Page: Purchase Register.
- 4C Engine (services/recon/engine.py) per docs/RECON_RULES.md: duplicates, amendments, stages exact / normalised /
  financial / fuzzy, leftover GSTIN-mismatch and doc-type pairing, never matches when 2+ candidates qualify,
  modes three-way / Tally–2B / IPT–2B / IPT–Tally. Deliberate change: NOT_IN_IPT ranks after the books-vs-2B
  statuses (documented in RECON_RULES.md). Invoice-number normalisation fixed: FY fragments like 26-27 are
  removed only when they are real FY pairs (INV/1045 is no longer cut).
- 4D Pages: GST Reconciliation (run panel, tolerances, status chips, three-source grid, compare view, action
  status + remarks kept across runs, manual match / unmatch with remark and audit, export), ITC Analysis (books
  vs 2B, user review, professional-review banner), Exception Management (invoices, Tally imports, recon items).
Tests: test_gstr2b.py, test_recon_engine.py (one per status and stage + ambiguity), test_recon_services.py,
UI smoke. Not yet tested: the portal Excel/JSON of the user's own GSTIN (samples follow the portal layout) and
the Tally purchase-register fetch against the user's TallyPrime (parser tested with Day Book XML).

## Phase 5 – Reporting ✅ (v0.6.0)
- ReportService: one source of figures for Dashboard, MIS Reports and Export Centre (Tally books or IPT invoices;
  credit notes subtracted). Test asserts dashboard total = report total = workbook total = purchase register.
- Dashboard: 8 KPI cards, month filter, supplier filter, charts (monthly taxable, top suppliers, recon status).
- MIS Reports: supplier-wise, monthly, ledger-wise, GST rate, HSN, recon summary/details, exceptions, ITC, import
  log; each to Excel, CSV, PDF (PyMuPDF – no new dependency).
- Export Centre: 12-sheet workbook; Tally XML batch for approved, mapped invoices (unready ones listed).
  Other software formats (Zoho, Marg, ERP 9 variants) not produced: their import formats were not verified.

## Phase 6 – Production release ✅ in code, ⏳ build on Windows
- Backup service: SQLite online backup + documents in one ZIP, checksum + integrity verify, scheduled (daily /
  weekly when IPT opens), retention, restore staged and applied at next start with a safety backup and the
  replaced data kept. Settings & Backup page (tolerance, Tesseract path, backup folder/schedule).
- Packaging: installer/ipt.spec (PyInstaller one-folder, Tesseract bundled when installed), installer/ipt.iss
  (Inno Setup; uninstall keeps IPT_DATA), build_exe.bat. **Not yet built/tested on Windows.**
- Performance (5,000 invoices + 5,000 books + 5,000 2B rows): three-way recon 0.9 s, dashboard 1.8 s,
  workbook 4.4 s, backup 0.2 s. See docs/TEST_REPORT.md.
- Docs: USER_MANUAL.md, TALLY_SETUP.md, BACKUP_RESTORE.md, TROUBLESHOOTING.md, TEST_REPORT.md.
- AI extraction provider / API key storage: not included (extraction is fully offline).

## v0.6.1 – RapidOCR engine
- PP-OCRv6 (RapidOCR, ONNX) is the first OCR pass; Tesseract is the second pass and fallback. Majisa bills: 63/63 fields.
- Settings: OCR engine choice. Offline installer `install_ocr_models.bat`. 116 tests pass.
- Next: RapidTable (table structure) for line items.

## v0.6.2 – multi-invoice scans, ledger-wise suppliers, re-import
- Page splitting: a page after a signed/totalled page starts a new invoice even if its title is unreadable;
  'Page 2' sheets scanned out of order stay separate and are flagged (amounts LOW + remark).
- Invoice no.: OCR-tolerant label ('Imvoice No', 'Inivoice No'); Tally 'Reference No. & Date' used as a
  fallback / cross-check (financial-year pair decides).
- Supplier GSTIN: when unreadable, taken from a known GSTIN (Tally ledger, supplier master, other bills in
  the same file) only with evidence on the page (PAN read exactly → MEDIUM/GUESS; damaged GSTIN or name only → LOW).
- Totals: broken decimals ('24,898 25') tried when clean readings fail; tie-break by exact tax; amount in words
  outranks a misread total. Place of supply from the buyer block's state code (GUESS).
- 58-page Aglow/Balaji scan: 85 of 88 checked fields correct, 3 blank/flagged, 0 wrong unflagged.
- Master Mapping: 'Book this supplier to a ledger (no items)' – Accounting Invoice to e.g. Repair & Maintenance.
  Mode 'Auto (per supplier)'.
- Re-import: an invoice whose voucher was deleted in Tally can be imported again; IPT first checks Tally.
- v0.6.3: place of supply from the state NAME in the buyer block (code only if no name), LOW when it disagrees with
  the buyer GSTIN; supplier-name match ignores 'Private Limited' etc. and uses Tally names plus names seen in the file.
- v0.6.4: item quantity = amount / rate when that exact quantity is printed on the page; warning ITEM_QTY_MISSING before approval.
- v0.6.5: Fetch purchase register from Tally reads the Day Book one day at a time (TallyPrime returns only SVCURRENTDATE's day); April 2026 had 439 vouchers, the old code read 19.
- v0.6.6: purchase register from Tally: taxable value = every debit line except party, GST/duties, round off, bank/cash (freight, repairs, machinery were left blank). April 2026 check: 439 vouchers, total 3,17,70,427.66 = Tally.
- v0.6.7: purchase register = every voucher (any type) with an input GST ledger; untaxed vouchers left out; RCM journals marked [RCM]. RCM records (2B reverse charge = Yes, books [RCM]) are kept out of the reconciliation.
- v0.6.8: one purchase-register load at a time (two parallel fetches both stayed current); 'From' after 'To' refused; after a fetch the table shows that fetch only.
- v0.7.0: batch import, register duplicate check, create ledger/stock item in Tally, multi-file 2B + GSTIN check, supplier follow-up list, ITC timing, click-to-fill review, re-open, shortcuts, select validated. 127 tests.
- v0.7.1: Tally client uses 127.0.0.1 for 'localhost' and never a proxy (Windows waited ~2 s per request on IPv6).
- v0.7.2: tick boxes + Select all / Deselect all in Purchase Vouchers and Processed Invoices; 'Select all ready' / 'Select validated' tick rows (selectRow replaced the selection).
- 27-11-2026: user confirmed on real TallyPrime (Balaji Minerals): Create in Tally (ledger / stock item), batch 'Import ticked' and the faster Fetch from Tally all work.
- v0.8.0: credit/debit note import (Debit Note / Purchase, Agst Ref when the original is known in Tally), Extract ticked + archive old files, scanned item tables (split OCR phrases, 2-line headers, one-digit rate repair: 20 -> 29 of 46 complete, 0 wrong). Header accuracy unchanged (87/88, 0 wrong). 132 tests.
- v0.9.0: parallel OCR (thread-local RapidOCR, 1 ONNX thread each, pool of min(4, cores)): Majisa 9 pages 76.7 s -> 42.9 s, 45/45 fields unchanged. Supplier layout learning (table supplier_layouts, migration v7; label anchor + offset; filled values LOW until 3 samples, date checked against the FY in the invoice no, amounts must add up): 58-page sample 38/51 removed fields filled right, 0 wrong above the review threshold. GSTR-3B Table 4 ITC working (screen + Excel). 139 tests.
- v0.10.0: Claude Code check (claude_queue cases, CLAUDE.md, headless 'claude -p' with Read/Write/Glob only, answers checked by IPT rules, never approves, per-company off/queue/auto, audit). 143 tests.
- v0.10.1: OCR and Claude agreeing = confirmed; disagreeing on an OCR value = marked for review (inv-50 case: taxable 22355.00/+0.22 vs printed 22355.45/-0.23 added up to the same total). Re-check replaces the old note. 145 tests.
- v0.10.2: a value from an earlier Claude check is never counted as OCR agreement (re-check kept blurred values green). 146 tests.
- v0.10.3: OCR/Claude agreement is judged against the OCR reading saved in case.json (before any Claude check). 147 tests.
- v0.10.4: Check Tally for many ticked imported invoices (release_many); Reset company data (backup first, typed name, groups, setup off by default). 151 tests.
- v0.10.5: Approve ticked can include needs-review bills (reason required, remarks appended, audit). 152 tests.
- v0.10.6: IPT did not open: Dashboard ITC crashed on a reconciliation row whose bill/records were deleted after the run (skipped now); a page that fails to load no longer closes IPT (status bar + log). 153 tests.
- v0.10.7: document type defaults to tax invoice (extraction, migration v8 converts 'other'), 'other' no longer blocks Tally import and is not offered in review; re-open reason prefilled. 155 tests.
- v0.10.8: mouse wheel no longer changes an unclicked drop-down / number box (scrolling the review form had changed Document type to 'other' and Place of supply to 09). 156 tests.
- v0.10.9: 'Check ticked with Claude Code' says when bills are already waiting and who reads them (Claude Code not installed -> ask Claude in chat). 156 tests.
- v0.11.0: approved (not imported) invoices can be edited and deleted by approvers; edit re-checks and drops approval on errors; imported stay locked. 159 tests.
- v0.11.1: ledger state in LEDMAILINGDETAILS + LEDGSTREGDETAILS; voucher COUNTRYOFRESIDENCE/CMPGSTREGISTRATIONTYPE/CMPGSTSTATE; 'Fix GST details in Tally' (preview, confirm, alter ledgers + unit UQC, read back). 161 tests.
- v0.11.2: an item with no Tally stock item blocks the voucher (was shown Ready and Tally answered EXCEPTIONS 1); a bare Tally exception is explained in plain words. 162 tests.
- v0.11.3: Tally readiness in review Validation tab; ITEM_NO_AMOUNT / ITEM_DESC_MISSING checks; split item rows merged (tilted scans), serial no. stripped. Majisa p1/p3/p6 items fixed, Aglow unchanged except serial. 164 tests.
- v0.11.4: Fix GST details keeps each ledger's own mailing / GST rows (address, pincode, transporter...) and fills only empty state/country; stops if the first ledger with an address loses it. 165 tests.
- v0.11.5: Processed Invoices 'Tally' column (Ready / Map: party, N items, ledgers / Fix: ... / In Tally); duplicate 'no stock item' message only for unnamed items. 166 tests.
