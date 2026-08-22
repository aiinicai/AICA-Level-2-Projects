# Tally MCP Multi-Source Import Tool

A staging-and-approval tool that imports **Bank Statements** (Excel/CSV/PDF), **Journal Entries**, **GSTR-2B**, and **GSTR-1** data into **Tally Prime** as vouchers — nothing posts until you've reviewed and explicitly approved it.

Built as a capstone project for AICA Level 2.

## Why this exists

Manually re-typing bank statements, purchase reconciliations (GSTR-2B), and sales reconciliations (GSTR-1) into Tally is slow and error-prone. This tool:

- Reads real-world export formats (not a rigid fixed template) and lets you map columns yourself
- Matches vendors/customers/ledgers against your **live Tally company** by GSTIN first, then by name
- Flags anything it can't match instead of guessing or silently creating wrong data
- Checks for duplicates against Tally's own voucher history before posting
- Stages every row for review — you select, edit, and approve before anything is written to Tally

## Architecture

```
Browser (React, no build step)
        │  fetch() JSON/multipart
        ▼
Flask backend (this repo)
        │  XML/HTTP  (localhost:9000)
        ▼
Tally Prime  (Gateway of Tally → F12 → Advanced Configuration → enable ODBC/HTTP)
```

Both **reads** (ledger list, chart of accounts, duplicate-check voucher history) and **writes** (voucher/master posting) go through Tally's own XML/HTTP Gateway — no separate database, no Tally add-on required.

## Features

| Source | What it does |
|---|---|
| **Bank Statement** | Upload any real export (Excel/CSV/PDF) — map which column is Date/Narration/Debit/Credit (or a signed Amount + Dr/Cr indicator) and which bank ledger it's for. Auto-classifies Payment/Receipt/Contra. Optional narration-pattern rules ("if narration contains X, use ledger Y") persist across imports. PDF statements are read via `pdfplumber` (with password support via `pypdf`), including a fallback for statements with no visible table borders. |
| **Journal Entry** | Exact ledger names required — no fuzzy matching, straight to a Journal voucher. |
| **GSTR-2B** | Handles the real month-block "mismatch reconciliation" export format (invoice + note sheets), not just a flat table. Vendor matched by GSTIN first. Per-row Purchase/Direct Expense/Indirect Expense/Capital Asset classification, with a "vendor → expense ledger" learning table that improves with use. ITC eligible/ineligible toggle per row. |
| **GSTR-1** | Handles both a per-invoice format (B2B) and month-by-month consolidated formats (B2C Small, NIL-rated), auto-detected from the file's actual layout. |

**Readiness check**: before posting, tells you exactly which ledgers, tax ledgers, and voucher types (custom "Indirect Expense"/"Capital Asset" types under the Purchase base type) are missing from Tally — and can create them for you (or export a Tally-native import file if you'd rather review before creating).

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5050`. In Tally Prime: **Gateway of Tally → F12 → Advanced Configuration → Enable ODBC/HTTP** (port 9000).

## Project structure

```
app.py                      Flask entry point
templates/index.html        Standalone page shell
static/js/tools_tally.js    React UI (no build step, loaded via CDN)
tally_import/
  routes.py                 REST API (stateless — the browser holds staging rows)
  gateway.py                Tally XML/HTTP Gateway client (reads + writes)
  voucher_xml.py             Builds Payment/Receipt/Contra/Journal/Purchase/Sales voucher XML
  masters_xml.py            Builds ledger/voucher-type creation XML
  classify.py                Ledger group classification + vendor→expense learning
  mapping.py                 Fuzzy ledger name matching + persistent overrides
  bank_rules.py               Narration-pattern → ledger rules
  pdf_bank.py                 PDF table extraction (password unlock + table detection)
  parsers/                    One parser per source (bank, journal, gstr2b, gstr1)
```

## Notes on the Tally XML integration

A few things that aren't obvious from Tally's public docs and were found by reverse-engineering real exported vouchers/ledgers from a live Tally company:

- A ledger entry's `AMOUNT` must be **negative for a debit, positive for a credit** — the reverse of what many examples online suggest.
- New master creation (ledgers, voucher types) needs the name inside a `LANGUAGENAME.LIST` block — the `NAME="..."` XML attribute alone isn't enough and is silently rejected.
- GST registration details on a ledger live in a nested `LEDGSTREGDETAILS.LIST` (with `APPLICABLEFROM` and `PLACEOFSUPPLY` required), not flat `PARTYGSTIN`/`GSTREGISTRATIONTYPE` tags.
- Reading data back reliably needed Tally's TDL Collection export rather than the simpler named reports (`List of Accounts`, `Ledger Vouchers`), which silently returned nothing on this Tally version even with real data present.

## Disclaimer

This tool writes accounting vouchers into a live Tally company. Always review the staging grid and readiness check before approving a posting run, and test against a non-production company first.
