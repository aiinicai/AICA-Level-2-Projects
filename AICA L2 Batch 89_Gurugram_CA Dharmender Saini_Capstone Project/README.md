# Debtors & Creditors MIS – Outstanding Reconciliation

A single-file, offline **Receivables & Payables MIS** for Indian businesses, with a read-only **TallyPrime bridge**.
Open one HTML file in Chrome or Edge – no installation, server or internet connection is needed.

> Developed by **CA Dharmender Saini**, Gurugram-122001 · Mobile No. +91-8800116810 · Email id ca.dharmendersaini@yahoo.com

---

## Contents of this folder

| File | What it is |
|---|---|
| `debtors-creditors-mis-outstanding-reconciliation.html` | The MIS application (everything in one file) |
| `tally_bridge-full-outstanding-reconciliation.py` | TallyPrime bridge – Python source (standard library only) |
| `bridge_config.json` | Bridge settings: Tally address, port, pairing token (blank – a new token is created on first run) |
| `tally_bridge.spec` | PyInstaller recipe to build a ready-to-run `tally_bridge.exe` (no Python needed on the Tally computer) |
| `README.md` | This file |

---

## Quick start

1. Open `debtors-creditors-mis-outstanding-reconciliation.html` in **Google Chrome** or **Microsoft Edge**.
2. On first open, **Create your first company** (name, admin, financial year, GSTIN, state …).
3. Add data with **Data import** (Excel / CSV templates or your own workbooks) or **Tally Sync**.
4. Use the dashboard and reports; export or share any report as Excel, Word, PDF or HTML.

---

## Features

### Companies (multi-company)
- **Admin → Company master** and the sidebar **Switch / add company** button: add, open, edit and delete companies.
- Each company keeps its **own** customers, vendors, bills, receipts, cheques, users, settings, Tally link and audit trail.
- Adding or deleting a company needs the Admin user; other users are offered to switch to the Admin first.
- Deleting asks you to type the company name and cannot be undone – take a backup first.

### Company / Admin Master (Settings)
- Company, legal name, admin, address (State from a dropdown of all states / UTs), GSTIN, PAN, CIN, contact, logo.
- **Financial Year** from a dropdown; default as-on date, credit periods, currency, ageing basis, key vendor,
  large-bill threshold, legacy cut-off, **Debtor Segment 1 (Business Unit)**, report footer, authorised signatory.
- Typing a GSTIN fills in the State; a mismatch between GSTIN state code and State is warned.
- Excel template to fill and import the whole master in one go.

### Dashboard
- **Debtors / Creditors** views with KPIs, segment summary, collection summary, top 15, ageing, PDC and charts.
- **Debtor Segment: All | [Customer ▾] | Others** – pick any customer to see its own dashboard; *Others* shows every other customer.
- **Vendor** dropdown on the Creditors view.
- **Management Summary** export bar: format + **Download / WhatsApp / Email**.

### Report pages
Debtors (receivable), Creditors (payable), Bill-wise outstanding, Ageing analysis, Collections & payments,
PDC / cheques, Customer & vendor ledger and Reports each have an **export bar** under the heading:

`[Report] – export as [Excel ▾]   [Download]  [WhatsApp]  [Email]`

Exports contain exactly what the page shows (side, status, filters, selected customer / vendor).

### Report formats
| Format | Output |
|---|---|
| **Excel (.xlsx)** | Coloured header, zebra rows, Indian lakh / crore numbers, negatives in red, frozen header + filters, A4 print setup and **live formulas**: `SUBTOTAL` totals, balance columns such as `=Amount-Received-CN`, and % columns such as `=B8/B$14*100` |
| **Word (.docx)** | Company header and logo, coloured tables with repeating header row, landscape for wide reports, page X of Y |
| **PDF (.pdf)** | Print-ready with company header, zebra rows, negatives in red, page numbers |
| **HTML (.html)** | One web page for any browser or phone, with a Print / Save as PDF button |
| CSV / Print | Plain data / direct printing |

### Sharing over WhatsApp and e-mail
- The message is drafted automatically: company, report, as-on date, key figures, filters, your name and contact.
- **WhatsApp**
  - *Share with attachment* – sends the file through the device share window (pick WhatsApp).
    Chrome / Edge allow only **PDF, HTML, CSV and images** there, so for Excel / Word a **PDF copy** of the same
    report is prepared automatically (*Share PDF copy with attachment*).
  - *Open WhatsApp chat / WhatsApp Web* – downloads the actual file, copies the message and opens the chat;
    attach the file with 📎 → Document.
  - On Windows, WhatsApp appears in the share window only when the **WhatsApp desktop app** (Microsoft Store) is installed.
- **Email**
  - *Open draft with attachment* – downloads an `.eml` draft; open it and Outlook / Windows Mail shows the message
    with the report already attached – check and press Send.
  - Gmail, Outlook web and the default mail app are also offered (the file is downloaded for you to attach).
- Every share is recorded in the audit trail.

### Importing data
- **Import Master Data / Import Raw Data** – Master Import Template, your Summary / Cosmetics workbooks, or any single sheet (column mapping).
- **Import from template** (Import / export templates page and Data import page) – upload a filled Master Import
  Template or Summary / Cosmetics layout and choose:
  - **Incremental import** – only new records are added: new customers / vendors, new bills with their own receipts,
    notes and PDCs, and targets that are still blank. Existing customers, vendors, bills and settings are never
    changed, replaced or deleted; bills already in the application are listed as skipped.
  - **Full import** – the file replaces the existing data (all debtors & creditors for a Master template; that side's
    data for a Summary / Cosmetics layout). Admin / Finance Manager only.
  - A check screen comes first either way, and **Undo this import** removes an incremental import.
- Every import is checked before saving and recorded with a batch number in the audit trail.

### Saving
- **Save** button and **Auto-save** switch in the top bar (Ctrl + S also saves).
- With auto-save off, the Save button turns amber on unsaved changes; closing the tab or switching company warns first.
- Data is stored in this browser (IndexedDB). It is **not** inside the HTML file – use **Settings → Data → Backup Data**
  to keep a `.json` copy and **Restore Data** to load it on another computer. A backup holds the open company only.

### Users, roles and rules
- Roles: Admin, Finance Manager, Accounts Executive, Management / Viewer.
- **Settings → Users & roles**: the permission rules can be edited per company (Save rules / Reset to default).
  "Dashboard and reports" is always on and Admin always keeps "Settings and users".

---

## TallyPrime bridge (read-only)

```
TallyPrime (XML over HTTP)  ←  Tally bridge (127.0.0.1:9901)  ←  MIS HTML file
```

- Reads from TallyPrime only – it never creates, alters or deletes anything in Tally.
- Listens on this computer only; the app must present the pairing token shown by the bridge.

**One-time setup**
1. TallyPrime: F1 (Help) → Settings → Connectivity → *TallyPrime acts as* = **Server** (or Both), port **9000**.
2. Run `py tally_bridge-full-outstanding-reconciliation.py` (Python 3.8+, standard library only).
   Optional: build a Windows program with `pip install pyinstaller` then `pyinstaller tally_bridge.spec` and run `dist/tally_bridge.exe`.
3. In the MIS: **Tally Sync → Connection** – paste the pairing token, click *Save & test*.

**Every sync**: open TallyPrime with the company loaded, start the bridge, then **Tally Sync → Sync**
(choose company, data types and period → Preview → Sync Selected Data).

Options: `--tally http://localhost:9000`, `--port 9901`, `--new-token`. Settings live in `bridge_config.json`.

---

## Troubleshooting

| Message | What to do |
|---|---|
| "TallyPrime is not reachable" | Open TallyPrime, load the company, enable the HTTP server / port |
| "Wrong or missing pairing token" | Copy the token from the bridge window again |
| "Bridge not reachable" | Start the bridge; use the downloaded HTML file on the same computer |
| "Your browser cannot put Excel files into the device share window" | Use *Share PDF copy* or *Open WhatsApp chat* (browser limitation) |
| Add / Delete company not allowed | Sign in as the Admin user (the app offers to switch) |
| Data missing on another computer | Data stays in the browser where it was entered – use Backup / Restore |

---

## Requirements
- Windows 10 / 11, Google Chrome or Microsoft Edge (current version).
- TallyPrime (for Tally Sync only). Microsoft Excel / Word to open exported `.xlsx` / `.docx` files.

---

Developed by **CA Dharmender Saini**, Gurugram-122001 · Mobile No. +91-8800116810 · Email id ca.dharmendersaini@yahoo.com
