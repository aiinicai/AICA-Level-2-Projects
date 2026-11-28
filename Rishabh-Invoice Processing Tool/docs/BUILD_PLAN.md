# IPT build plan for Google Antigravity

Give the agent **one task at a time**. Start every task with the prompt shown,
review the result, run the app and the tests, then move to the next task.
Phase 1 is already complete.

Standard opener (prefix for every task):

> Read AGENTS.md, docs/PROGRESS.md and the documents named in this task first.
> Then do task **<ID>** from docs/BUILD_PLAN.md exactly. Follow the layer rules,
> write complete code and tests, run the tests, launch the app to check the screen,
> and update docs/PROGRESS.md. Ask me before changing anything outside this task.

---

## PHASE 2 – Invoice processing

### 2A – Alembic + documents + upload queue
- Add Alembic (`ipt/db/migrations/`), baseline migration for the Phase 1 tables,
  and make `Database.create_schema()` run `alembic upgrade head`. Existing Phase 1
  databases must upgrade without data loss (test this with a copied DB).
- Tables `documents`, `extraction_results` (docs/DB_SCHEMA.md).
- `services/document_service.py`: add files (PDF, JPG, JPEG, PNG), copy original into
  `FY_xx/Invoices/`, SHA-256 hash, page count (PyMuPDF), duplicate-file detection per company,
  remove from queue, list queue.
- Page **Invoice Processing**: Browse files, drag & drop, Add folder, queue table
  (file, pages, size, status, duplicate warning), Remove selected, Clear queue (confirm).
  Extraction buttons are added in 2B – do not add them yet.
- Tests: hashing, duplicate detection, storage path, company isolation, migration upgrade.

### 2B – Extraction pipeline (offline first, AI optional)
- `services/extraction/`: `pdf_text.py` (PyMuPDF text layer), `ocr.py` (OpenCV deskew /
  threshold → pytesseract; detect Tesseract path, clear error if missing),
  `parser.py` (regex + layout rules → fields with per-field confidence 0–1),
  `ai_provider.py` (interface + one provider, disabled by default), `pipeline.py`
  (Automatic: text → OCR → AI if enabled and confidence low → manual review).
- AI consent: before any external call show a dialog naming the provider; settings
  switch "Never send documents to cloud AI" (default ON).
- Extract every field in the master list (supplier, buyer, invoice header, line items,
  taxes, charges, totals, IRN, e-way bill, currency, exchange rate). Unknown → None.
- Tables `suppliers`, `invoices`, `invoice_items`, `invoice_charges`.
- Queue buttons: Start extraction, Pause, Resume, Cancel, Retry failed – worker thread with
  per-file progress. Extraction starts only when the user clicks Start.
- Tests: parser on text fixtures made from the user's own anonymised sample invoices
  (ask the user to place them in `tests/fixtures/invoices/`); never invent fixtures.

### 2C – GST & accounting validation engine
- `services/validation/`: GSTIN (core.gstin), POS vs supplier state → CGST/SGST/UTGST or
  IGST, date-effective `gst_rate_master` table (seed with rates and effective dates,
  editable by admin), line totals vs invoice totals with configurable tolerance,
  round-off, negative values, invalid dates (outside FY), missing GSTIN, HSN/SAC format,
  credit/debit note sign handling, duplicate invoice (GSTIN + normalised no + doc type).
- Store results in `validation_results`; never modify invoice values.
- Tests: one test per rule with passing and failing cases.

### 2D – Review screen + Excel export
- Page **Processed Invoices**: list with filters (status, date, supplier, doc type);
  bulk approve / reject (remark).
- Review window: left = document preview (page images, zoom, rotate, page nav);
  right = tabs Summary (all header fields, colour by confidence: green ≥0.90 & valid,
  amber 0.60–0.89 or warning, red <0.60 / missing / invalid), Items (editable grid, add/delete
  row, totals), Validation (list, click to focus field), History (audit).
  Foreign-currency block labelled "Invoice currency" vs "Accounting value (INR)".
- Actions: Save, Validate, Reprocess, Approve (blocked by errors unless admin override
  with remark), Reject, Delete (confirm), Next/Previous, Ctrl+S.
- Page **Supplier Masters**: list, edit, invoices per supplier.
- Export selected invoices to XLSX (Invoice Summary + Item Details sheets).
- Tests: service-level save/approve rules; smoke test opens review window.

---

## PHASE 3 – Tally integration (test against a TEST company in Tally)

### 3A – Tally connection + master extraction
- `services/tally/client.py`: HTTP POST XML to host:port (company settings), timeouts,
  clear errors when Tally is closed or the port is wrong. `adapters/` for TallyPrime and
  Tally.ERP 9 (detect product/version; read GSTIN from both field layouts).
- Read open companies; warn if the IPT company's Tally name is not open.
- Sync masters into `tally_masters`: ledgers (with parent group, GSTIN), groups, stock items
  (HSN, GST rate, unit), stock groups, units, godowns, voucher types, cost centres/categories,
  GST registrations. Refresh button. Read-only: never alter Tally masters here.
- Page **Tally Integration**: connect/test/disconnect, status, open companies, sync
  checkboxes with progress, masters browser tabs. Help text for enabling port 9000.
- Use docs/TALLY_XML.md. Tests: parse saved real Tally responses (ask the user to export
  them from their test company) – mock HTTP only in tests.

### 3B – Master mapping
- Table `mapping_rules`. `services/mapping/matcher.py`: supplier by GSTIN exact → saved rule →
  exact name → rapidfuzz token_set_ratio; items by saved rule → name + HSN + rate.
  Return candidates with score and reason text.
- Page **Master Mapping**: grouped by entity (party, stock item, purchase ledger, GST ledgers,
  expense ledger, unit, godown, cost centre); combobox of Tally masters; Approve, Approve all
  ≥95, Bulk apply, Ignore; Mapping Memory tab (edit/delete rules).
- "Create in Tally" for missing ledger/stock item: double confirmation, then import master XML,
  verify response. Never create masters without confirmation.

### 3C – Purchase vouchers, XML and import
- Tables `vouchers`, `tally_imports`. `services/tally/xml_builder.py` for accounting and
  inventory modes, local / interstate / RCM / exempt / nil / bill of supply / credit & debit
  notes / multi-rate / freight & charges / round-off / narration / supplier invoice no & date /
  cost centres. Assert Dr = Cr (sum of AMOUNT = 0.00) before sending.
- Pre-check: duplicate in IPT and in Tally (party + REFERENCE), missing ledgers/items, GST
  config, balance, totals.
- Page **Purchase Vouchers**: select → mode → pre-check → voucher preview (Dr/Cr) → XML view →
  Save XML. Page **XML Import**: Import selected/all (confirm), store request XML + raw
  response, parse CREATED/ALTERED/ERRORS/LINEERROR, re-query voucher, retry failed, failed report.
- Acceptance: import each voucher type into the Tally test company and open it in Tally.
  Record results in PROGRESS.md (which Tally version, which cases passed/failed).

---

## PHASE 4 – GST reconciliation

### 4A – GSTR-2B upload
- Tables `gstr2b_uploads`, `gstr2b_records`. Parse portal JSON and Excel: B2B, B2BA, CDNR, CDNRA,
  IMPG, IMPGSEZ, ISD, ISDA; keep original doc refs for amendments; ITC availability + reason.
- One active upload per company + period; re-upload asks to Replace (confirm), old kept as history.
- Page **GSTR-2B Upload**: upload, periods list with counts by section, records with section tabs.
- Tests use the user's own downloaded 2B files (anonymised), including an amendment month.

### 4B – Tally purchase register upload
- Tables `purchase_register_uploads`, `purchase_register_records`, `purchase_register_rejects`,
  `pr_templates`. Wizard: file → sheet + header row (preview) → column mapping (saved as template)
  → validate → import; rejected rows listed with reasons and exportable.

### 4C – Reconciliation engine
- Tables `recon_settings`, `recon_runs`, `recon_rows`. Implement docs/RECON_RULES.md exactly:
  normalisation, 5 stages, tolerances, status order, confidence, reasons, suggested actions.
  Modes: IPT vs Tally, IPT vs 2B, Tally vs 2B, three-way.
- Tests: one test per status and per stage, plus ambiguity (two candidates → not matched).

### 4D – Reconciliation screen, exceptions, ITC
- Page **GST Reconciliation**: run panel + tolerance settings, status summary chips, grid with
  IPT / Tally / 2B columns (invoice no, date, taxable, CGST, SGST, IGST), difference, status,
  reason, suggested action, action status (Pending / Under Review / Resolved / Accepted /
  Rejected), remarks; expand row to compare the three sources; manual match / unmatch with remark
  (audited); export view to XLSX.
- Page **ITC Analysis** (`itc_analysis` table) with eligibility review fields and the banner
  that final eligibility needs professional review. Page **Exception Management** inbox.

---

## PHASE 5 – Reporting
- **Dashboard**: purchase KPIs and charts (QtCharts) and reconciliation KPIs, filters by month,
  supplier, GSTIN, rate, ledger, status – all from real records.
- **MIS Reports**: supplier-wise, ledger-wise, HSN summary, rate summary, monthly purchases,
  recon summary/details, exceptions, ITC, import log.
- **Export Centre**: 12-sheet workbook (Invoice Summary, Item Details, Supplier Master, Purchase
  Register, GST Summary, HSN Summary, Ledger Mapping, Stock Item Mapping, Recon Summary, Recon
  Details, Exception Report, ITC Analysis), CSV, PDF (reportlab), Tally XML batch; templates for
  TallyPrime, Tally ERP 9, Zoho Books, Marg (only where the real import format is known).
- Acceptance: export totals = dashboard totals = Tally purchase register for a test month.

## PHASE 6 – Production release
- Backup: manual + scheduled (SQLite online backup API + documents zip), list, verify,
  restore into a new file then swap after confirmation, integrity check. Never overwrite
  without confirmation.
- Application Settings page: data folder, OCR settings, AI provider (API key in Windows
  Credential Manager via keyring), rounding tolerance, auto-backup schedule.
- Error handling review, performance check with 5,000 invoices.
- Packaging: PyInstaller one-folder build with bundled Tesseract; Inno Setup installer with
  Start-menu shortcut; uninstall keeps IPT_DATA; upgrade runs migrations after auto-backup.
- Docs: user manual, Tally setup guide, backup/restore guide, troubleshooting, test report.
