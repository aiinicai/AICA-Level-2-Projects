# Bank Guarantee Lifecycle Monitoring System

An internal financial control over bank guarantees held by a company — automated
expiry tracking, three-tier escalation to vendors, an immutable evidence log, and
a management dashboard.

Built as the operating control through which the safeguarding-of-assets limb of
**Section 134(5)(e) of the Companies Act, 2013** is discharged in respect of bank
guarantees.

---

## The problem

A bank guarantee is a contingent claim enforceable only inside a defined window.
It extinguishes automatically on expiry.

A guarantee allowed to lapse without extension or invocation is a control failure
that leaves no trace: no entry is passed, no balance moves, no reconciliation
breaks. The loss surfaces only when recovery is attempted and found impossible.
A register maintained by hand depends on an individual remembering — which is not
a control that can be evidenced to an auditor.

## What the system does

| Stage | Behaviour |
|---|---|
| **Capture** | Operator keys the IFS code; issuing bank and branch are derived by lookup against the RBI NEFT participant list. Chronological rules are enforced at the point of entry. |
| **Validate** | Six gates run at every execution — populated row, live status, readable expiry, BG date ≥ contract date, expiry > BG date, not already lapsed. |
| **Escalate** | Notices at 30 days (polite), 20 days (firm) and 10 days (assertive, carrying the invocation clause). |
| **Suppress** | A compound key `BG-[number]-[expiry]-[tier]` is matched against the log. No tier is ever despatched twice, and a sent notice closes off all softer tiers. |
| **Evidence** | Every outcome — sent, failed with reason, skipped, invalid — is appended to `BG_Email_Log` and never edited. |
| **Report** | An eight-panel dashboard: ageing, value falling due by month, watch list, bank and vendor concentration, dispatch outcomes, data quality exceptions. |

Two design rules are worth stating explicitly:

- **Escalation runs one way only.** The most urgent due tier is tested first. Once
  despatched, no softer notice can follow it. (An earlier version could send the
  firm 20-day notice and then the polite 30-day advisory the next day, which a
  vendor could reasonably read as a withdrawal of the warning.)
- **Holiday rollback is always backward.** A target date falling on a weekend or a
  listed holiday is stepped back to the preceding business day, one day at a time,
  so the recipient never receives less than the stated notice period.

---

## Repository layout

```
├── src/
│   ├── bg_monitor.py        monitoring engine — validation, tiers, despatch, logging
│   ├── bg_monitor_exe.py    engine variant used when building the executables
│   ├── bg_gui.py            desktop application (Tkinter)
│   └── bg_dashboard.py      management dashboard generator
├── apps_script/
│   └── validation.gs        cell-level validation retained inside Google Sheets
├── docs/
│   ├── SOP_User_Manual_V3.pdf      26-page SOP, IFC framing, audit checklist
│   └── Presentation_15_Slides.pdf  15-slide overview
├── samples/
│   ├── sample_register.csv         fabricated register — no real vendor data
│   └── sample_dashboard.html       dashboard generated from that sample
├── requirements.txt
└── .gitignore
```

## Register structure

Column positions are fixed; the engine addresses them by header text and by
position.

| Col | Field | Entry |
|---|---|---|
| A | Sl. No. | keyed |
| B | Vendor Name | keyed |
| C | Recipient Email | keyed |
| D | Contract Number | keyed |
| E | Contract Date | keyed |
| F | Purpose of BG | dropdown |
| G | BG Number | keyed |
| H | BG Date | keyed — must be ≥ column E |
| I | Issuing Bank | **derived** from the IFSC master |
| J | IFS Code | keyed — the only bank field typed |
| K | Branch Details | **derived** from the IFSC master |
| L | BG Amount (INR) | keyed |
| M | Date of Expiry | keyed — must be > column H |
| N | Status | dropdown |

Supporting tabs: `Config` (mode and routing), `Holidays`, `BG_Email_Log`,
and `IFSC-1` / `IFSC-2` holding the NEFT participant list published by the
Reserve Bank of India at <https://www.rbi.org.in/scripts/neft.aspx>.

---

## Setup

```bash
pip install -r requirements.txt
```

1. Create a Google Cloud project and enable the **Google Sheets API** and
   **Google Drive API**.
2. Create a service account, issue a JSON key, and save it beside the scripts as
   `key.json`.
3. Share the spreadsheet with the service account address, granting Editor rights.
4. Set `SPREADSHEET_ID` in `src/bg_monitor.py` to the identifier in the sheet's
   web address (the portion between `/d/` and `/edit`).
5. Set `SENDER_EMAIL` to the authorised despatch address.
6. Enable two-step verification on that account and generate a 16-character app
   password. Supply it through the `BG_GMAIL_APP_PASSWORD` environment variable —
   never hard-code it.

Full installation and authorisation steps are at section 10 of the manual.

## Running

```bash
python src/bg_monitor.py --preview    # lists what is due; sends nothing, logs nothing
python src/bg_monitor.py --test       # routes everything to the administrator
python src/bg_monitor.py              # live run, per SYSTEM_MODE in the Config tab
python src/bg_dashboard.py            # builds and opens the dashboard
python src/bg_gui.py                  # desktop application
```

**Preview before every live run.** The 10-day notice states that the guarantee
will be invoked without further reference to the vendor. A mistyped expiry date
therefore does not produce a harmless early reminder — it produces a legal warning
to a counterparty whose guarantee is in order.

### Scheduling

A single daily run is sufficient; escalation intervals are measured in whole days
and duplicate suppression makes additional runs inert. Schedule it through Windows
Task Scheduler with *run as soon as possible after a missed start* enabled. The
dashboard reports the last engine run, so a prolonged outage is visible rather
than silent.

### Building executables

```bash
pip install pyinstaller
python -m PyInstaller --onefile --name BG_Monitor src/bg_monitor_exe.py
python -m PyInstaller --onefile --windowed --name BG_Monitor_App src/bg_gui.py
```

---

## Security

Two credentials are used, each narrowly scoped. Neither is any individual's
account password.

| Credential | Grants | Where it lives |
|---|---|---|
| `key.json` | Read/write on spreadsheets explicitly shared with the service account, and nothing else | Application folder on the nominated workstation only |
| Gmail app password | Sending mail through the SMTP gateway | Environment variable, or typed into the application at time of use |

**Neither is in this repository, and `.gitignore` is configured to keep it that
way.** Launcher `.bat` files are excluded for the same reason — they carry the app
password in plain text. If a credential is ever committed, deleting the file is
not sufficient: it remains in the commit history and the key must be revoked and
reissued.

Keep the application folder outside OneDrive or any synchronised location.

## A known trade-off

The engine previously ran on Google's servers via Apps Script and executed whether
or not any workstation was powered on. It now runs locally, which brings the
control inside the organisation's own environment and removes dependence on a
personal account's trigger quota — but the workstation must be on at the scheduled
hour. The compensating controls are the missed-start retry and the last-run
timestamp displayed on the dashboard.

## Sample data

Everything in `samples/` is fabricated. Vendor names, guarantee numbers, amounts
and IFS codes are invented, and all addresses use the reserved `.example` domain.
The sample deliberately includes three defective rows so the data quality panel
demonstrates each exception type: an unresolved IFSC lookup, a missing vendor
address, and a blank expiry date.

## Documentation

- **`docs/SOP_User_Manual_V3.pdf`** — statutory mandate, register blueprint,
  validation and escalation design, configuration, access control, installation,
  operation, dashboard interpretation, a ten-test IFC audit checklist,
  troubleshooting, and three annexures.
- **`docs/Presentation_15_Slides.pdf`** — 15-slide overview for an audit committee
  or board presentation.

## Demonstration and live register

**Demonstration spreadsheet:**
https://docs.google.com/spreadsheets/d/11TRCIeCotBI5Z83lsWcSFTrNisl0xq9ZUqTBs3cPdek/edit?usp=drive_link

A read-only copy of the register showing the tab structure, the derived bank and
branch columns, and the log format. Access is view-only; the live register is not
published.

**Walkthrough video:**
https://drive.google.com/file/d/1mOcQ8o9sHoxPoKcn0svajEfCuaUC8mG-/view?usp=drive_link

A recorded demonstration of the preview run, a test despatch, and the dashboard.

## Status

Version 3.0. The Apps Script engine of version 2.4 has been retired; only the
cell-level validation function remains inside the spreadsheet. No time-based
trigger may be active on that project while the Python scheduled task is running,
or vendors receive every notice twice.

---

*This system handles counterparty commercial data and despatches correspondence
carrying legal consequences. Read section 12 of the manual before operating it
against a live register.*
