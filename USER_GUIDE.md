# User Guide

## What this app does

Tally Converter takes your accounting files - Excel spreadsheets, CSVs,
PDF invoices, or photographed/scanned invoices (JPG/PNG) - and turns
them into an XML file that TallyPrime can import as vouchers (Sales,
Purchase, Receipt, Payment, Contra, Journal, Credit Note, Debit Note).

Everything happens on your computer. No file, invoice, or accounting
figure is ever sent over the internet.

## The workflow

### 1. Import

Go to **Import**, choose your files (Excel/CSV/PDF/JPG/PNG - you can
select several at once), and click **Upload & Process**. The app reads
each file, runs OCR on scanned documents/images, and extracts
transactions automatically.

### 2. Review

Go to **Review**. Any transaction the app couldn't confidently read
in full - a missing date, an unreadable amount, no party name found,
an invalid GSTIN - is listed here with the specific reason(s) it needs
your attention.

**The app never guesses.** If it shows a field as blank, that means it
genuinely couldn't determine the value from your document - it's not
a bug, it's the app being honest about what it doesn't know. Fill in
or correct the field, choose the correct voucher type from the
dropdown if needed, and click **Save**, or **Save & Approve** once
you're satisfied.

Every edit you make here is permanently recorded in the **Audit Log**.

### 3. Mappings

Before you can export a voucher, the app needs to know which ledger in
*your* TallyPrime company corresponds to each party name in your
documents, and which ledger to use for roles like Sales, CGST, SGST,
IGST, Round Off, and Bank/Cash.

Go to **Mappings**:
- **Parties** tab: map each customer/vendor name from your documents
  to the exact ledger name in Tally (e.g. "ABC Traders" &rarr; "ABC
  Traders Pvt Ltd" if that's how it's spelled in Tally).
- **Ledgers** tab: map each role (SALES, PURCHASE, CGST, SGST, IGST,
  ROUND_OFF, BANK_CASH, SALES_RETURN, PURCHASE_RETURN) to the actual
  ledger name in your Tally company.
- **Items** tab: map item/product names if you're tracking inventory.

The app will never create a ledger in Tally automatically - you always
control what maps to what.

### 4. Validation

Go to **Validation** and click **Run Validation**. This checks every
transaction for:
- required fields (date, party, invoice number, amount)
- GST arithmetic (taxable value + tax + round-off = total)
- possible duplicates
- missing ledger/item mappings

Anything marked **ERROR** blocks that transaction from being exported
to XML until you fix it. **WARNING**s don't block export but are worth
a look.

### 5. Tally Export

Go to **Tally Export**. Select the approved transactions you want to
export and click **Generate XML**. You'll see:
- a preview of the generated XML
- a **Download XML** button (the default way to get your file)
- a **Copy XML** button
- any transactions that were skipped, with the reason why (e.g. a
  missing ledger mapping)

**To import into TallyPrime:** open TallyPrime, go to **Gateway of
Tally &rarr; Import Data &rarr; Vouchers**, and select the downloaded
XML file.

**Optional - Send to Tally directly:** if TallyPrime is running on
this same computer with its HTTP/ODBC server enabled (Gateway of Tally
&rarr; F1 Help &rarr; Settings &rarr; Connectivity), you can click
**SEND TO TALLY** to import directly without downloading a file first.
This requires an extra confirmation click and always defaults to
**off** - downloading the XML and importing manually is the default,
safer path.

## Understanding confidence scores

When a document goes through OCR (scanned PDFs, JPG/PNG images), each
extracted field gets a confidence score:

| Score | Meaning |
|---|---|
| 90-100% | High confidence - still worth a glance, not accounting correctness |
| 70-89% | Review recommended |
| Below 70% | Mandatory review - the field is very likely wrong or incomplete |

**A high OCR confidence score does not mean the accounting is
correct** - it only means the text was read clearly. Always check the
Validation screen too.

## Duplicate detection

If the app finds a transaction that looks like a duplicate of one
already imported (matching invoice number + party, or matching GSTIN +
invoice number, or matching party + date + amount), it will flag it in
Validation rather than silently skip or silently import it. You decide
whether to ignore the warning, mark it as an intentional duplicate, or
treat it as a genuine duplicate to exclude.

## Backups

Go to **Settings** to see where your data lives
(`C:\ProgramData\TallyConverter\`). The database is backed up
automatically before large imports; back up the `database` and
`exports` folders manually before major changes if you want extra
peace of mind.

## Troubleshooting

**"Ledger not found in TallyPrime"** when sending to Tally: the ledger
name in your mapping doesn't exactly match what exists in your Tally
company. Go to Mappings and correct the spelling, or create the ledger
in Tally first.

**"Voucher is not balanced"**: the debit and credit amounts on a
voucher don't add up to the same total - usually caused by a GST
mismatch. Check the transaction in Review and re-run Validation.

**"Invalid Tally date"**: check the transaction's date field in
Review - it may have been left blank or in an unrecognized format.

**OCR isn't finding text well**: make sure Tesseract is installed and
detected (check Settings). Photographed invoices work best when
well-lit, in focus, and not skewed at a steep angle.
