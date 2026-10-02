# BRMCo Accounting Hub — Local Host

Runs on the client's Windows computer as a local web app at **http://127.0.0.1:8000**. It works with Excel files, the local TallyPrime installation and a local SQLite database. It is not an EXE: you run it from source with Python.

Phase 1 is the **Accounting Entry Engine**: Sales, Purchase, Journal, Bank Receipt and Bank Payment, taken from Excel through validation and preview into TallyPrime.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the architecture and [docs/API.md](docs/API.md) for the API reference.

## 1. Setup (once per computer)

Requires Python 3.11 or newer (3.12 recommended) from python.org.

```bash
cd brmco-accounting-local
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # optional
```

## 2. Run

```bash
.venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Keep the terminal window open while you work. Bind only to `127.0.0.1`: the app has no login in Phase 1 and must not be reachable from the network.

Optional: also start the Server Host (see `../brmco-accounting-server`) so the dashboard can show "BRMCo Server: Online". Nothing in Phase 1 depends on it.

## 3. First-time configuration

1. **Settings**: company name, GSTIN, **company state** (needed to check CGST/SGST against IGST), financial year, Tally company name, Tally host/port, GST ledger names, Tally voucher-type names.
2. **TallyPrime**: F1 Help → Settings → Connectivity → set *TallyPrime acts as* **Both**, *Enable ODBC* **Yes**, *Port* **9000** (or your port). Restart TallyPrime and open the company.
3. **Tally → Connection → Test Tally Connection**. You should see **Connected** and the list of open companies.
4. Untick **Demo mode** in Settings.
5. **Tally → Master Sync → Sync all masters**. This caches ledgers, groups, stock items, units and voucher types. Excel data is checked against this cache. The app **never creates masters** in Tally.

## 4. Daily workflow

```
Select voucher type → Download template → Fill in Excel → Upload & Validate
 → Fix errors (row/column shown) → Preview Dr/Cr entries
 → Confirm & Post to Tally  (or Download XML)
 → Tally's own response per voucher → saved in Import History + Audit Log
```

- A file with **any error** can't be posted, and its XML can't be downloaded.
- **Warnings** (for example "computed tax amount" or "possible duplicate") don't block posting. Read them in the preview.
- "Success" is decided only from Tally's `CREATED/ALTERED/ERRORS/LINEERROR` response, never from the HTTP status.
- Vouchers are sent to Tally **one at a time**, so you get an exact status for each voucher. If Tally goes offline part-way, the remaining vouchers are marked *Not attempted*.
- Vouchers that Tally confirmed are remembered. Uploading the same invoice again is flagged as a duplicate error.

### Missing ledgers

If validation reports *Ledger "…" does not exist in Tally master data*, click **Create missing ledgers in Tally** on the validation screen. You can also open **Tally → Create Ledgers** for manual entry.

The form is pre-filled with every missing ledger and a suggested group:

| Used as | Suggested group |
|---|---|
| Customer | Sundry Debtors, with GSTIN, state and bill-wise from the Excel |
| Supplier | Sundry Creditors, with GSTIN, state and bill-wise from the Excel |
| Sales ledger | Sales Accounts |
| Purchase ledger | Purchase Accounts |
| Output/Input GST ledgers | Duties & Taxes, with the Central, State or Integrated Tax / Cess duty head |
| Round Off | Indirect Expenses |

Check the group for each ledger, then click **Review & Create in Tally** and confirm. Each ledger gets Tally's own result. The ledger list is re-synced, and **Re-validate** checks the same file again without re-uploading. Nothing is created without your confirmation, and every attempt is written to the Audit Log.

If the ledger already exists in Tally under a different name, correct the name in Excel instead. For GST and round-off ledgers, set the name in **Settings**.

## 5. Demo mode

Demo mode is on by default. It shows the banner **"DEMO MODE — No entry posted to Tally"** and replaces Tally with a simulator that has a demo company, demo masters, and realistic accept/reject behaviour (unknown ledger → error). Each voucher page has **Download filled sample** so you can try the full flow in under a minute. Demo masters are cached separately and never mix with a real company's masters. Demo postings are not counted for duplicate detection.

## 6. Accounting rules implemented

| Voucher | Entry |
|---|---|
| Sales | Customer Dr (invoice total) / Sales ledger Cr (taxable) / Output CGST, SGST or IGST, Cess Cr / Round Off Dr or Cr |
| Purchase | Purchase/Expense Dr (taxable) / Input CGST, SGST or IGST, Cess Dr / Round Off / Supplier Cr (invoice total) |
| Journal | As entered. Each row is Debit **or** Credit. Total Dr must equal total Cr. |
| Bank Receipt | Bank Dr / Party Cr (bill-wise *Agst Ref* when Reference Number is given, else on account) |
| Bank Payment | Party/Expense Dr / Bank Cr |

GST validation:
- GSTIN format, checksum, and state code against the state column.
- Intra-state (company state or supplier state equals place of supply) must use CGST+SGST. Inter-state must use IGST.
- CGST rate must equal SGST rate. Rates must come from the notified set.
- Tax amount must equal taxable × rate, within the tolerance set in Settings.
- Taxable value must equal qty × rate − discount.
- Invoice total must equal taxable + taxes + round off. The error message suggests the round-off that makes it balance.
- Blank tax amounts, taxable value or invoice total are computed and shown as warnings.
- **ITC Ineligible** lines add their GST to the purchase/expense ledger instead of input tax.
- **Reverse charge**: the tax columns must be blank. RCM liability is booked separately in Phase 1.

Stock items: if *Item/Description* matches a synced Tally stock item and Quantity is filled, the line is posted in item-invoice mode (inventory with quantity, unit and rate). Otherwise it is an accounting line.

Excel layout: one row per invoice line. Rows with the same invoice number (for purchases, the same supplier and invoice number) form one voucher. Invoice-level columns can be left blank on continuation rows. If they're filled, they must match the first row.

## 7. Tests

```bash
pytest -q
```

52 tests cover the accounting engine, GST checks, Excel parsing, templates, XML generation, Tally response parsing, the connection-failure path, the duplicate guard, and the full upload → preview → post → history flow through the API.

## 8. Samples

- `templates/*.xlsx`: blank templates. The app's **Download template** button is better, because it adds dropdowns from your synced masters.
- `samples/sample_*.xlsx`: filled examples matching the demo masters.
- `samples/sample_*.xml`: the Tally import XML produced from those samples.

Regenerate with `python -m scripts.generate_samples`.

## 9. Where things are stored

`DATA_DIR` defaults to `./data`:

| Path | Contents |
|---|---|
| `data/brmco_local.db` | SQLite: settings, master cache, batches, history, posted vouchers, audit log |
| `data/logs/app.log`, `errors.log` | Rotating logs (secrets redacted) |
| `data/xml/` | Every XML generated or posted |
| `data/uploads/` | Copy of every uploaded Excel |

Back up the `data` folder. Tally remains the accounting system of record. SQLite never replaces it.

## 10. Security

- No AI keys, MongoDB credentials or other provider secrets are stored in this project.
- The Server Host URL is configurable. A warning appears if a non-local server doesn't use HTTPS.
- The Local Host talks only to local Tally and to the BRMCo Server Host.
