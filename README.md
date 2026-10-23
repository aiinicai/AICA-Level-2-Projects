# GURU – GST Returns Downloader & Compliance Dashboard (v2)

## Why version 1 did not work

I checked each problem on the live GST portal in a logged-in session (October 2026):

| Problem in v1 | What the portal actually does | Fix in v2 |
|---|---|---|
| The app waited for the captcha as soon as the page opened | The captcha appears **only after the username is typed** and focus leaves the box | v2 types the username key by key and presses Tab, then shows the captcha |
| The captcha was pasted into the box | The captcha box **blocks paste** and accepts digits only | v2 types it key by key |
| The app opened pages by typing their URL | The portal shows **"Access Denied"** when a page is opened without coming from a link | v2 moves between pages from inside the page, the same way a link click does |
| The app clicked DOWNLOAD and waited for a file | The GSTR-3B PDF, GSTR-1 PDF and GSTR-2B Excel are **built inside the browser** from JSON data | v2 reads that same JSON and builds Excel with **pandas** |
| The certificate download was never saved | The REG-06 "download" **opens in a viewer tab** | v2 fetches the PDF directly and saves it |
| The GSTR-2B page could not be reached | The GSTR-2B site opens **only through the Returns Dashboard tile** | v2 selects the period and clicks the tile |

## Install (one time)

1. Install **Python 3.10+** from python.org. Tick **"Add python.exe to PATH"**.
2. Unzip this folder, for example to `D:\Tools\GST_Downloader`.
3. Double-click **setup.bat**. It installs pandas, openpyxl, Playwright and the browser engine.
4. Double-click **run.bat**.

## Use

1. Enter the username and password, then click **1. Open portal & show captcha**. A browser window opens and the captcha appears in the app.
2. Type the captcha digits and press **Enter**. If the portal asks for an OTP, enter it in the browser, then click **I have logged in in the browser (continue)**.
3. **Select one or more financial years** (Ctrl/Shift-click for several), the months, and items, then click **START**.

## What you get

```
<Save folder>\<GSTIN>\<FY>\
   <GSTIN>_Compliance_<FY>.xlsx   Summary | Return status | Month grid | Reconciliation
   <GSTIN>_GSTR3B_<FY>.xlsx       Monthly summary | Table-wise detail (3.1, 3.2, 4A-4D, 5.1, payment)
   <GSTIN>_GSTR1_<FY>.xlsx        Monthly totals | Section x month | All sections
   <GSTIN>_GSTR2B_<FY>.xlsx       ITC by month | B2B invoices | CDNR | ... | Supplier-wise | ITC summary
   <GSTIN>_GSTR9_<FY>.xlsx        (if ticked)
   PDF\  GSTR1\  GSTR2A\           (optional items)
   json\                           raw portal data, kept for audit
<Save folder>\<GSTIN>\Registration\<GSTIN>_GSTREG-06_....pdf
```

**Dashboard**
* Due dates and Filed / Not filed status come from the portal's Returns Dashboard.
* ARN and filing date come from View e-Filed Returns.
* The dashboard shows days late, an estimated late fee and a compliance score.
* The late-fee cap uses the aggregate turnover read from the portal.

**Reconciliation**
* GSTR-1 vs GSTR-3B: outward taxable value and output tax.
* GSTR-2B vs GSTR-3B: ITC, flagged where 3B ITC is more than 2B.

**GSTR-2A and GSTR-1 full JSON.** The portal prepares these files in the background, which can take up to 20 minutes. The first run requests them. Run again later with the same ticks to collect the files.

## Notes

* The captcha and any OTP are always entered by you. The app does not read or solve them.
* The password stays in memory only for the login and is never saved.
* All portal addresses are in `portal_config.py`, so if GSTN changes something only that file needs editing.
* The late-fee estimate excludes interest u/s 50, and notified extensions of due dates are only reflected if the portal shows them.


## The HTML dashboard

After every run (and from the **Open HTML dashboard** button on the dashboard tab),
the app writes `<GSTIN>_Dashboard_<FY>.html` next to the Excel files. It is one
self-contained page - KPI cards, a filing-status donut, GSTR-1 vs 3B and 2B vs 3B
bar charts, the return-wise table, the month grid, reconciliation flags and the
top suppliers. It has **no link to the portal and no internet use**, so it opens
instantly and can be emailed or shared as a single file. Rebuild it any time from
a saved folder with:

    python dashboard.py "C:\path\to\GST_Downloads\<GSTIN>\<FY>"

## A note on "pull everything in 2 minutes without the API"

Tools that do this usually save the login session and then call the portal's
internal, unpublished addresses in the background. That goes against GSTN's terms,
can get a user ID blocked, handles client passwords in ways worth questioning, and
breaks without warning whenever GSTN changes a page. This app deliberately does not
work that way: it reads the portal's data only while you are logged in with the
browser visible, and the dashboard above is built entirely from files already on
your PC. For genuine background pulling, the supported route is a GST Suvidha
Provider (GSP) API, which your office enables once with an OTP.


## Multi-year and notices (v4)

* **Multiple years in one run.** Pick several financial years in the list (hold Ctrl or Shift). Each year is downloaded in turn and gets its own folder, Excel files and dashboard. In the console use a list or a range: `--fy 2023-24..2025-26` or `--fy 2024-25,2025-26`.
* **Notices & orders.** Tick *Notices & orders* to pull the notices and orders list (System u/s 46 defaulter notices, assessment/registration orders, LUT and adjudication case tasks). Each row is tagged **Pending** (unread, an open case, or an action due date still ahead) or **Seen**. Saved as `<GSTIN>_Notices.xlsx`. Notices are not year-specific, so they are fetched once per GSTIN and then shown per year and in the overview.
* **Multi-year overview.** After the run the app writes `<GSTIN>_Overview.html` at the GSTIN folder: KPI totals, compliance score / late fee / defaults by year, a year-by-year table, clickable links to each year's dashboard, and the full notices list. This is the page it opens for you.


## v5 - notice PDFs, firm portfolio, branding, dark mode, print

* **Notice & order PDFs.** Orders and any document with a docId are saved as PDFs in `<GSTIN>\Notices\`, and each notice row in the dashboard links straight to its file. System-generated u/s 46 defaulter notices (GSTR-3A) are listed and marked "on portal" (the portal only shows those through its own viewer, so there is no clean file to save).
* **Firm portfolio (all clients).** `Firm_Portfolio.html` at the top of your save folder: one page across every GSTIN you have downloaded - clients sorted by returns overdue then notices pending, a KPI strip, a "needs attention" chart, and a click-through to each client's multi-year dashboard. Also on the **Firm portfolio** button.
* **Firm branding** - the GURU mark and firm name on every page.
* **Dark / light toggle** and a **Save as PDF** button on every dashboard (uses the browser's print-to-PDF, so clients who don't open HTML still get a PDF).
* **Notice PDF links** inside the year and overview pages.
* **Run history.** Every run appends one audit line to `run_history.log` (time, GSTIN, years, items, result counts).

### Ideas still open (say the word and I'll add them)
Ledger balances (cash / credit) on the dashboard; notice-deadline calendar with reminders; one-click .exe build (no Python install); encrypted saved client logins; scheduled overnight refresh with email alerts (limited by the captcha, which always needs a person).


## v6 - pre-filing checks, reconciliations, e-way bills (capstone)

**Pre-filing check & risk analysis** (`<GSTIN>_Issues_<FY>.xlsx`, and a section on every dashboard).
Run it before filing each period to clear mismatches and avoid notices. Each issue carries a
severity (High / Medium / Low / Info), the amount at risk, the section it relates to and a
recommended action. It checks:

* Returns not filed / filed late, with late fee and an interest-u/s-50 estimate on late 3B.
* **GSTR-1 vs GSTR-3B** output tax and taxable value, per month and cumulative (Table 9 gap).
* **GSTR-2B vs GSTR-3B** ITC - excess ITC claimed over 2B (Sec 16(2)(aa) / Rule 36(4)) and
  unclaimed ITC still available (Sec 16(4)).
* Nil-return anomalies, RCM liability vs ITC, turnover vs portal AATO.
* **GSTR-9 Table 9** payable-vs-paid differences (when GSTR-9 is downloaded).
* **E-way bills vs GSTR-1** (see below).

**E-way bills.** In the app, "Open e-way bill portal" logs you in (you type the captcha), then
download "EWB generated by me" from Reports; or add the exported file with "Add export file(s)".
The app saves it under `<GSTIN>\ewb\` and builds `<GSTIN>_EWB_<FY>.xlsx` and a dashboard section:

* **Reconciliation with GSTR-1** by month, flagged (EWB > GSTR-1, GSTR-1 > EWB, EWB but no GSTR-1).
* Analysis **customer-wise**, by **document type**, **supply type**, **transaction type**,
  **status** (incl. cancelled), **HSN-wise**, **transporter-wise** and **month-wise**.
* Console: `--ewb "C:\path\ewb1.xlsx,C:\path\ewb2.xlsx"`.

The issue analysis and e-way bill reconciliation flow through to the multi-year **Overview**
(a combined "Pre-filing issues - all years" section) and the **Firm Portfolio** (an "Issues (High)"
column and a "needs attention" chart), so the partner sees firm-wide risk at a glance.


## v7 - automated COMPLETE e-way bill download (no more 5-day manual pulls)

The e-way bill portal's detailed "EWB generated by me" (Outward Supplies) report can only be
queried **5 days at a time** - its own message is *"Date Range shouldn't be more than 5 Days..!"*.
Pulling a full year by hand means ~73 separate downloads per client. v7 does it for you.

**How to use it**

1. In the E-way bills box, click **1. Open e-way bill portal**. A browser opens at the EWB login.
2. **Log in there yourself** - type the captcha (and OTP if asked). The app never reads or stores
   the captcha, OTP or password.
3. Back in the app, set **From** and **To** (dd/mm/yyyy) for the whole period you want, optionally
   tick **also inward**, and click **2. Download complete EWB records**.
4. The app walks the period in 5-day windows, sets the **Subuser = ALL** filter (so bills raised by
   every sub-user / API user are caught), clicks **Export To Excel** on each window, and saves every
   chunk into `<GSTIN>\ewb\`. Empty windows are skipped. Progress is shown live.
5. Click **START** as usual. All the chunks are combined and **de-duplicated on EWB number**
   automatically, then the EWB analysis and the GSTR-1 reconciliation run on the complete data.

**What was mapped on the live portal (so it actually works)**

* The report page can't be opened by typing its URL (it bounces to the main menu); the app reaches
  it the way a menu click does, so the referer check passes.
* Results render into a 28-column grid; the real **Export To Excel** button exports the *full* result
  set for the window (not just the first page of rows). NIC's export is sometimes an HTML table saved
  as `.xls`, so the reader handles that as well as real `.xlsx`/`.xls`/`.csv`.
* A faster **"Monthwise download EWBs"** route (a whole month in one file) also exists, but the portal
  only serves it **8 AM - 12 PM IST**; outside that window it redirects away. The 5-day loop is the
  reliable any-time path and is what the app uses.
* The automated complete-download loop runs in the **desktop app**. The single-file console build
  still takes e-way bill files you've already saved: `--ewb "file1.xls,file2.xls"` (they're combined
  and de-duplicated the same way).

Security is unchanged: captcha and OTP are always typed by you, the password is never saved, and the
app only reads the portal while you are logged in with the browser visible - no background scraping.
Remember to log out of the e-way bill browser when you're done.

### Party-wise e-way bill vs GSTR-1 B2B reconciliation

Besides the month-wise check, the app now reconciles **each counterparty (recipient GSTIN)**: the total
e-way bill value raised to a party versus what was reported for that same GSTIN in **GSTR-1 B2B**. The
GSTR-1 side nets B2B invoices, B2B amendments and credit/debit notes. Each party is flagged:

* **EWB > GSTR-1** - more moved on e-way bills than billed to that party (possible under-reporting).
* **GSTR-1 > EWB** - billed more than e-way bills show (e-way bill may be missing).
* **In EWB, not in GSTR-1** - bills to a GSTIN with nothing reported for it (a likely omission).
* **In GSTR-1, no EWB** - invoices filed for a party with no e-way bill at all.
* **OK** - within tolerance (5% or Rs 10,000).

It appears as the **"EWB vs GSTR-1 (party)"** sheet in `<GSTIN>_EWB_<FY>.xlsx` and a party-wise table
on the dashboard, with a one-line summary (parties, matches, mismatches, EWB-only, GSTR-1-only).

This needs GSTR-1's counterparty data, which isn't in the GSTR-1 *summary*. **Tick "GSTR-1 full JSON"**
in the item list and collect it (the portal prepares it in ~20 minutes, so run once to request and again
to pick it up); the party-wise reconciliation then builds automatically. Note it compares EWB *assessable*
value against GSTR-1 *taxable* value, so genuine timing and document-type differences (challans, exports,
non-invoice movements) can show up and should be read with that in mind.

*The single-file console build is regenerated with `python build_console.py`.*
