# Capstone Project Report
## GURU – GST Returns Downloader, Pre-filing Check & Compliance Dashboard

**Author:** CA P. GuruMurthy Mogalapalli — Mogalapalli & Co., Chartered Accountants, Visakhapatnam
**Programme:** ICAI AICA Level 2 (Artificial Intelligence for Chartered Accountants)
**Tech stack:** Python 3.10+, Playwright (browser automation), pandas (data), openpyxl (Excel), Tkinter (desktop UI), self-contained HTML/SVG (dashboards)

---

## 1. Problem statement

A practising CA office handles GST compliance for many GSTINs across many years. The routine work is
manual and repetitive: logging in to the GST portal for each client, downloading GSTR-1, GSTR-3B,
GSTR-2B, GSTR-9 and the registration certificate for each period, tracking which returns are filed,
late or pending, watching for notices, and — most importantly — **catching mismatches before filing**
so the client does not receive a notice later. E-way bills live on a separate portal and are rarely
reconciled against the returns at all.

The project automates the data collection and, on top of it, builds an **analysis layer** that a
reviewer runs **before filing** to surface every likely error, plus a presentation layer (per-year,
multi-year and firm-wide dashboards) that makes the position readable at a glance.

## 2. Objectives

1. Securely pull a GSTIN's return data from the GST portal without storing credentials or defeating
   the portal's security (captcha and OTP stay with a human).
2. Produce clean, formatted Excel working papers for each return.
3. Run a **pre-filing check** that reconciles the returns among themselves and against e-way bills and
   lists every issue with its severity, amount at risk, statutory reference and recommended action.
4. Reconcile and analyse **e-way bills** (customer-wise, type-wise, status-wise) against GSTR-1.
5. Present everything as branded, shareable dashboards — per year, across years, and firm-wide.

## 3. Design principles (and why they matter for a CA)

* **Human-in-the-loop security.** The app never reads, solves or bypasses the captcha or OTP. It reads
  the portal's data only while the user is logged in, with the browser visible. This keeps the office
  within GSTN's terms of use and avoids the user-ID blocking risk that "background scraping" tools carry.
* **No credential storage.** The password is held in memory only for the login and is cleared after.
* **Offline analysis.** Every dashboard and the whole analysis layer run from files already saved on the
  PC — no internet, so they open instantly and can be e-mailed or printed to PDF.
* **Maintainability.** All portal URLs, selectors and API paths sit in one file (`portal_config.py`);
  when GSTN changes a screen, only that file is edited.

## 4. System architecture

```
                    ┌──────────────────────────────────────────────┐
  GST portal ──────▶│ portal.py  (Playwright worker, own thread)    │
  EWB portal        │  login (human captcha) → read portal JSON     │
                    └──────────────┬───────────────────────────────┘
                                   │ raw JSON saved to <GSTIN>/<FY>/json
                    ┌──────────────▼───────────────────────────────┐
  EWB export  ─────▶│ reports.py / compliance.py / ewaybill.py      │  pandas → Excel
  (xlsx/csv)        │ issues.py  (pre-filing checks & reconciliations)│
                    └──────────────┬───────────────────────────────┘
                                   │ frames
                    ┌──────────────▼───────────────────────────────┐
                    │ dashboard.py  → per-year / overview / portfolio│  self-contained HTML
                    └───────────────────────────────────────────────┘
  main.py  = Tkinter desktop UI      gst_console.py = single-file console build
```

| Module | Responsibility |
|---|---|
| `portal_config.py` | All portal URLs, element selectors and API paths (GST + e-way bill) |
| `portal.py` | Browser automation: login, read the portal's own data services, download notice PDFs |
| `reports.py` | Parse portal JSON into pandas tables; GSTR-1/3B/2B/9 frames; formatted Excel writer |
| `compliance.py` | Statutory due dates, filing-status classification, late fee, compliance score |
| `issues.py` | **Pre-filing check**: all reconciliations and risk rules → ranked issue list |
| `ewaybill.py` | Parse EWB export; customer/type/status analysis; reconcile with GSTR-1 |
| `dashboard.py` | Branded HTML dashboards (per-year, multi-year overview, firm portfolio) |
| `main.py` | Desktop application (login screen, downloads tab, dashboard tab) |
| `gst_console.py` | The same engine as one file that runs in Command Prompt |

## 5. Key design decision: why not the "2-minute, no-login" approach

Tools that pull everything in two minutes save the login session and then call the portal's internal,
undocumented endpoints in the background. That violates GSTN's terms, can get a client's user-ID
blocked, and breaks silently whenever GSTN changes a page. The supported route for true background
access is a **GST Suvidha Provider (GSP) API** (enabled once with an OTP). This project deliberately
takes the compliant path — read the portal's data while logged in, with the browser visible — and puts
its real value in the **analysis layer**, which is where mistakes are actually caught.

## 6. The pre-filing check (the analytical core)

Run before filing each period, it evaluates, with severity, amount at risk, section and action:

1. **Filing discipline** — not filed / filed late; late fee; estimated interest u/s 50 on late 3B.
2. **GSTR-1 vs GSTR-3B** — output tax and taxable value, per month and cumulative (the common Table 9 gap).
3. **GSTR-2B vs GSTR-3B** — excess ITC claimed over 2B (Sec 16(2)(aa) / Rule 36(4)); unclaimed ITC (Sec 16(4)).
4. **Anomalies** — nil 3B while 2B has ITC; RCM liability (3.1(d)) vs RCM ITC (4A(3)).
5. **Turnover** — GSTR-1 turnover vs portal aggregate turnover.
6. **GSTR-9 Table 9** — payable vs paid differences.
7. **E-way bills vs GSTR-1** — EWB > GSTR-1 (possible unreported sales), GSTR-1 > EWB, EWB with nil GSTR-1.

Each firing produces `<GSTIN>_Issues_<FY>.xlsx` and a colour-coded section on the dashboard, and the
counts roll up into the multi-year overview and the firm portfolio.

## 7. E-way bill module

Reads the EWB portal's "EWB generated by me" data, normalises the varying column headers, drops
cancelled bills from the active totals, and produces: a **month-wise reconciliation with GSTR-1**
(flagged), and analysis **by customer, document type, supply type, transaction type, status, HSN and
transporter**. The month-wise outward value also feeds the pre-filing check above.

**Automated complete download.** The portal's detailed Outward Supplies report is hard-capped at a
**5-day range per query** (verified live: *"Date Range shouldn't be more than 5 Days..!"*), so a full
year is ~73 manual downloads per client. The app automates this: after the user logs in to the EWB
portal (captcha/OTP by hand), it walks the requested period in 5-day windows, sets the **Subuser =
ALL** filter, clicks the report's **Export To Excel** on each window, saves every chunk into
`<GSTIN>\ewb\`, and combines them **de-duplicated on EWB number**. Portal mechanics were mapped in a
live logged-in session: the report page rejects direct-URL navigation (referer rule) so it is reached
as a menu click does; the export is sometimes an HTML table saved as `.xls`, which the reader handles
alongside real spreadsheets; and a faster whole-month download route exists but is served only
8 AM-12 PM IST, so the any-time 5-day loop is used. The download path (multi-window combine, dedupe,
HTML-`.xls` parsing, cancelled-bill exclusion) was unit-tested end-to-end.

**Party-wise reconciliation with GSTR-1 B2B.** Beyond the month-wise total check, the tool reconciles
**each counterparty (recipient GSTIN)**: total e-way bill outward value to a party against that GSTIN's
value reported in **GSTR-1 B2B** (netting B2B invoices, b2b amendments and credit/debit notes from the
GSTR-1 JSON). A full outer join surfaces GSTINs present on only one side, and each party is flagged
*EWB > GSTR-1*, *GSTR-1 > EWB*, *In EWB not in GSTR-1*, *In GSTR-1 no EWB*, or *OK* (within 5% /
Rs 10,000). It is written as the "EWB vs GSTR-1 (party)" sheet and a dashboard table with a summary
line. Because EWB *assessable* value is compared with GSTR-1 *taxable* value, timing and document-type
differences are expected and are called out as caveats. The netting and flag logic were unit-tested.

## 8. Testing

Because the live portal cannot be scripted against safely, a **mock portal** (a local multi-origin HTTP
server replicating the GST login captcha flow, the "Access Denied" referer rule, the returns-dashboard
tiles, the GSTR-2B site and the notices API) was built, and the whole application was run end-to-end
against it: multi-year download, notices, per-year and overview and firm-portfolio dashboards, the
issues engine and the e-way bill analysis. The analysis modules (`compliance`, `issues`, `ewaybill`,
`reports`) were unit-tested on data shaped exactly like the live portal's responses (the live response
structures were confirmed from a logged-in session). The dashboards were rendered headless and visually
inspected.

## 9. Limitations

* Late fee and interest are **estimates**; notified due-date extensions are reflected only where the
  portal shows them.
* System-generated u/s 46 notices (GSTR-3A) are listed but viewable only on the portal; orders and any
  document with a docId are saved as PDFs.
* E-way bill data is pulled automatically across the portal's 5-day report windows and combined; the
  faster whole-month download route is used only when the portal serves it (8 AM-12 PM IST).
* GSTR-2A and the full GSTR-1 JSON are prepared by the portal in the background (up to 20 minutes).

## 10. Future scope

Ledger balances (cash/credit) on the dashboard; a notice-deadline calendar with reminders; a one-click
`.exe` (no Python install); encrypted saved client logins; a GSP-API data layer for unattended refresh;
and e-mail alerts on new notices or new high-severity issues.

## 11. Outcome

A practising CA office can, for one client or across the whole firm, pull a year (or several) of GST
data in a couple of minutes of attended time, get formatted working papers, and — the point of the
project — run a **pre-filing check that catches the mismatches that otherwise become notices**, all
presented in branded dashboards that are ready to share.

*Mogalapalli & Co., Chartered Accountants — Visakhapatnam.*
