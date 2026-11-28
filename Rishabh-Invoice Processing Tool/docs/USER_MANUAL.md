# IPT – Invoice Processing Tool · User manual

IPT runs only on your computer. Your data is in `%LOCALAPPDATA%\IPT_DATA` (Settings & Backup → Open folder).

## 1. First start
1. Open IPT (Start menu → IPT, or `run_ipt.bat` in the project folder).
2. First time only: create the admin user. Keep the password safe – nobody can recover it.
3. **Company Settings** → add the company (name, state, GSTIN, Tally company name exactly as in Tally) and the
   financial year. Choose company and year in the top bar; every screen works on that company + year only.

## 2. Invoices (Processing)
1. **Invoice Processing** → Add files / Add folder (PDF, JPG, PNG). Originals are copied and never changed.
   A PDF with several bills is split into one invoice per bill.
2. Click **Start extraction**. The status line shows the page being read. Scans use OCR (Tesseract + OpenCV).
3. **Processed Invoices** → double-click an invoice. The document is on the left, fields on the right:
   - green = read with confidence, amber = please check, red = missing or failed a check;
   - the supplier name is taken from the Tally ledger with the same GSTIN when there is one;
   - fix fields, then **Approve** (an admin override needs a remark).
4. Wrongly read invoices can be deleted (Delete selected) and their pages extracted again.
   An invoice already imported into Tally cannot be deleted.

## 3. Tally (import purchase vouchers)
See `TALLY_SETUP.md` once. Then:
1. **Tally Integration** → Test connection → Sync masters.
2. **Master Mapping** → for each approved invoice confirm party ledger, purchase ledger, GST ledgers, stock items
   and godown. Your choices are remembered for the next invoices.
3. **Purchase Vouchers** → select the invoice → check the preview → **Import into Tally**. IPT reports success only
   when Tally created the voucher and IPT found it again.
4. **XML Import** → the log of every import with Tally's answer. "Re-check in Tally" verifies an import again; if
   the voucher was deleted in Tally, the invoice goes back to *approved* so it can be imported again.

## 4. GST reconciliation
1. **GSTR-2B Upload** → choose the GSTR-2B **Excel** (or JSON) downloaded from the GST portal. IPT shows the month
   and the number of documents per table before importing. The same month again replaces the old file after
   you confirm; the old one stays in history.
2. **Purchase Register** → **Fetch from Tally** (recommended – reads Purchase / Debit Note vouchers, read-only) or
   **Import Excel** (choose sheet, header row and columns; save the mapping as a template for next month).
   Rows that cannot be read are listed with the reason ("Export rejected rows").
3. **GST Reconciliation** → choose the mode (three-way, Tally vs 2B, IPT vs 2B, IPT vs Tally) and months →
   **Run reconciliation**.
   - Click a status chip to filter. Select a row to compare IPT / Tally / 2B side by side (differences in red).
   - Statuses: Matched, Partially matched, Amount mismatch, Not in 2B, Not in books, Not in IPT, GSTIN mismatch,
     Duplicate, Amended, CDN difference. Each row shows the reasons and a suggested action.
   - **Set action / remarks** (Pending, Under Review, Resolved, Accepted, Rejected) – kept when you run again.
   - **Manual match** (select the 2–3 rows that are the same document, remark required) and **Unmatch**.
     A manual match still shows every difference; it never hides a mismatch.
   - **Export view to Excel**.
   Tolerances (default ₹1 per amount, same date, 90% number similarity) are under **Tolerances…**.
4. **ITC Analysis** → ITC in books vs in GSTR-2B per document. Review each document and record your decision
   (Eligible / Ineligible / Blocked / Deferred / Reversed) with a reason. IPT never decides eligibility.
5. **Exception Management** → everything still open: invoices needing review, failed Tally imports and
   reconciliation items not Resolved/Accepted.

## 5. Reports
- **Dashboard** – documents, taxable value, GST, ITC, open reconciliation items and charts, from the Tally
  purchase register or from IPT invoices, for the year or one month.
- **MIS Reports** – supplier-wise, monthly, ledger-wise, GST rate, HSN, reconciliation summary/details, exceptions,
  ITC, Tally import log. Each can be saved as Excel, CSV or PDF.
- **Export Centre** – the 12-sheet workbook and a Tally XML file for several approved invoices.
Dashboard, reports and exports use the same figures, so their totals agree.

## 6. Users and audit
**Users** (admin): admin = everything; accountant = processing, Tally, GST, reports, backups; reviewer =
view, approve and reconciliation actions. **Audit Trail** lists every change, import, export and backup.

## 7. Backup
See `BACKUP_RESTORE.md`. Short version: Settings & Backup → choose a backup folder outside this PC
(OneDrive/pen drive), keep "Automatic backup: weekly", and click **Back up now** before big changes.

## New in v0.7.0

### Tally
- **Import several bills at once** – Purchase Vouchers: *Select all ready* (or Ctrl/Shift + click), then *Import
  selected*. One confirmation for the batch; every voucher is checked for duplicates first and found again in Tally
  afterwards. A bill that may already be in Tally is **skipped** (import it alone, with a reason, if it is not).
- **Duplicate check against the purchase register** – a bill already in the register fetched from Tally (any voucher
  type, e.g. a Journal) with the same GSTIN and invoice no. – or the same GSTIN, date and total – is not imported
  without a reason.
- **Create in Tally** – Master Mapping: select a *Party* or *Stock item* row that has no Tally master and click
  *Create in Tally…*. Supplier ledgers go under Sundry Creditors with GSTIN and state; stock items get unit, HSN and
  GST rate. IPT reads the masters back from Tally and uses the new one only if Tally really has it.

### GSTR-2B and reconciliation
- **Several months at once** – Upload accepts many files; one month per file.
- **GSTIN check** – a file whose GSTIN is not valid, or whose file name carries another GSTIN, is imported only after
  you confirm.
- **Supplier follow-up list** – GST Reconciliation → *Supplier follow-up list…*: Excel with ITC at stake per supplier
  and the bill-wise list (not in 2B / amount or number different / other GSTIN) with what to ask the supplier.
- **ITC timing** – the ITC Analysis shows *Timing / note*: time-barred per 2B (Sec 16(4)), not available per 2B,
  reported late by the supplier, or not in 2B yet.

### Review screen
- **Click to fill** – click a field, then click its value on the bill image; Shift+click takes the whole line. For
  scans the value comes from the same OCR reading used for extraction. Always check it.
- **Re-open for editing** – an approved (not yet imported) invoice can be re-opened with a reason, corrected (e.g. a
  missing quantity) and approved again.
- **Shortcuts** – Ctrl+S save, Ctrl+Enter approve, Alt+→ / Alt+← next / previous.
- **Select validated** (Processed Invoices) and *Approve selected* – approves only invoices read with confidence;
  ones that need review must be opened.

## New in v0.8.0
- **Credit / debit notes into Tally** – set *Document type* to Credit note / Debit note and fill *Original invoice
  ref.*. A supplier **credit note** becomes a **Debit Note** voucher (party Dr; purchase and input GST Cr); a supplier
  **debit note** becomes a **Purchase** voucher. Both are imported without items. When the original bill is known
  to be in Tally (imported by IPT, or in the fetched purchase register) the note is booked *Agst Ref* to it,
  otherwise as a *New Ref*. Choose the voucher type once in Master Mapping. (RCM bills are still entered in Tally.)
- **Invoice Processing** – tick boxes and *Select all*. New files come ticked; *Extract ticked* reads only them, so
  older files are not read again. *Remove ticked* removes files without bills and **archives** files whose bills are
  already extracted (hidden, never read again; the bills stay). *Show archived* lists them.
- **Scanned item tables** – headers spread over two lines, OCR phrases such as '25210090 28.130 MT', the item name
  printed below the numbers, and a rate misread by one digit (checked by quantity × rate = amount) are handled.
  On the 58-page sample, complete item rows went from 20 to 29 of 46 bills, none wrong.
- E-invoice QR codes on photocopied bills could not be decoded (too blurred) – not used.

## New in v0.9.0
- **Faster scanned bills** – pages are read by OCR in parallel (up to 4 at a time; set `IPT_OCR_THREADS` to
  change). The 9-page Majisa sample went from 77 s to 43 s on 2 cores, with the same values read.
- **IPT learns each supplier's layout** – when you approve a scanned bill, IPT remembers where that supplier prints
  the invoice number, date, taxable value, taxes and total (and the label next to each, e.g. *Invoice No*,
  *Total*, because scans shift). On the next bill of the same supplier, a field OCR left empty or unsure is read
  from that spot. Such values have the tooltip *Read from where this supplier usually prints it*; they stay
  **red (please check)** until three approved bills agree, when the date is outside the year in the invoice
  number, or when the amounts do not add up. A confident reading is never replaced.
  On the 58-page sample (learning from 5 bills): 38 of 51 removed fields filled correctly, none wrong unmarked.
- **GSTR-3B ITC working** (*ITC Analysis → GSTR-3B working…*) – choose the month: Table 4 head-wise (IGST, CGST,
  SGST, Cess). 4(A)(5) is what GSTR-2B carries (credit notes reduce it, RCM and *ITC not available* kept out),
  4(A)(3) RCM from your books, 4(A)(1) imports, 4(A)(4) ISD; 4(B)(1) bills you marked blocked / ineligible,
  4(B)(2) bills you deferred plus 2B bills not in your books; 4(C) net; 4(D)(2) ITC not available / Sec 16(4).
  Below it, every bill to check: in 2B not in books, in books not in 2B yet (carry forward), late-reported,
  not available. *Export to Excel* gives both sheets. It is a **working for review, not a filing**.

## New in v0.10.0 – Claude Code check
For bills that extraction could not read with confidence. **Off by default**, set per company in
*Settings & Backup → Claude Code check*:
- *Off* – nothing leaves this PC.
- *Prepare cases* – after extraction each bill that needs review is written to `<data folder>\claude_queue\inv-<id>`
  (page images, OCR text, what IPT read and what looks wrong). Open Claude Code in that folder and say
  "process the cases" – `CLAUDE.md` there tells it what to do.
- *Automatic* – IPT starts Claude Code itself after extraction (`claude -p`, only allowed to read and write files in
  that folder). Claude Code must be installed and signed in once on this PC.

Claude Code writes `answer.json`; IPT picks it up within 20 seconds and **checks every value**: GSTIN checksum,
buyer GSTIN = this company, date inside the financial year and the year in the invoice number, taxable + taxes =
total, quantity × rate = amount, and whether the value is printed in the OCR text. A confident reading or a value you
typed is never replaced. Values are marked *Read by Claude Code … please verify*; values with only one confirmation
stay red. Refused values and Claude's notes are added to the bill's remarks. **Nothing is approved automatically.**
*Processed Invoices → Check ticked with Claude Code* sends older bills. Every send and every answer is in the audit trail.
Note: Claude Code sends the page images to Anthropic – keep it Off for clients who do not allow that.

## New in v0.10.4
- **Purchase Vouchers – check many in Tally at once**: tick several *Imported* invoices; the button becomes
  *Check Tally / import again (N)*. IPT asks Tally about each one; those whose voucher was deleted in Tally become
  *Ready* again (then *Select all ready* → *Import ticked*). Those still in Tally stay *Imported*.
- **Settings & Backup → Reset company data…** (admin): deletes the selected company's IPT data – uploaded bills
  and invoices (with Tally import history), GSTR-2B, purchase register, reconciliation and ITC review. *Setup*
  (Master Mapping, supplier masters, learned layouts, cached Tally ledgers) is a separate tick, off by default.
  A full backup is made first and the company name must be typed. Tally, the company, users and the audit trail
  are never touched.
- **v0.10.5 – Approve ticked, including bills that need review**: if ticked bills still need review (low-confidence
  values or errors), IPT asks *Approve all* or *Only the validated*. *Approve all* asks for a reason, which is added to
  the bill's remarks and the audit trail (earlier remarks are kept). Bills with errors need an admin.

## New in v0.11.0 – edit or delete approved bills
- An **approved** bill that is not yet in Tally can be edited directly (no Re-open). After Save it is checked again:
  still clean → stays approved; an error → goes back to *needs review* with a message.
- An approved bill can also be **deleted** (its pages go back to the extraction queue).
- Both need the approver role and are recorded in the audit trail (*invoice.edit_approved* / *invoice.delete*).
- A bill already **imported into Tally** stays locked: delete its voucher in Tally and use *Check Tally / import
  again* first, so IPT and Tally never disagree.

## New in v0.11.1 – GSTR-3B 'Uncertain transactions' from IPT-made masters
- Supplier ledgers created by IPT now carry the party state in Tally's *Mailing Details* and *GST Registration
  Details* (TallyPrime 3+ reads the state there). Vouchers also carry the country and the company's GST
  registration type and state.
- *Tally Integration → Fix GST details in Tally…* reads all ledgers with a GSTIN and all units from Tally, lists the
  ledgers without a state / GST registration and the units without a UQC (MT → MTS-METRIC TON, KG → KGS-KILOGRAMS,
  NOS → NOS-NUMBERS, …), and after you confirm writes only those details. Tally is read again to confirm.
- Vouchers already in Tally keep the details they were saved with: accept them in GSTR-3B → Uncertain
  Transactions, or delete them in Tally and import again from IPT.

## New in v0.11.3 – problems shown at review, not at Tally import
- Review → *Validation* now also lists what would stop the bill at Tally import (*🔗 Tally import: Not mapped –
  supplier / item / ledger*), when the company is linked to Tally and masters are synced.
- New checks: an item row with no amount (a stray heading such as 'No.' read as an item) is an error; an item with
  no readable name is a warning.
- Tilted scans: one item row split over 2–3 lines ('No. 6,280.00 MT 62,800.00' / '25221000 10.000 MT' /
  '1 QUICK LIME LOOSE') is joined back into one item; the leading serial number is dropped from item names.
