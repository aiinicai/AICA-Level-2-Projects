# Cash Flow Forecast: user manual

For the finance team: Preparers, Approvers, Viewers and the Admin. Installation and servers are in the
[README](../README.md).

---

## 1. What the app does

It replaces the daily Excel cash-flow review. Each day you upload the ERP and bank files. The app
places every collection and payment in a **10-day lot** (1–10, 11–20, 21–month end) for the next
2 or 3 months and shows:

- opening cash, inflows, outflows and closing balance per lot, **as per ERP**;
- the funding position with the bank facility, and any **funding gap**;
- the effect of **cheques you hold**, the **net funding position after holds**, and whether the holds
  are sufficient.

You can hold a cheque, defer or re-date an item, reduce or exclude it, and export the result to Excel.
Every change is kept, survives the next day's upload, and is recorded in the audit log.

## 2. Signing in

Open the link the Admin gave you (on the server PC: the **Cash Flow Forecast** shortcut starts the app without
a window and opens it; **Stop Cash Flow Forecast** stops it). The **Demo** shortcut opens a copy with synthetic
data and shows its sign-in details on the sign-in page. At your first sign-in you
choose your own password: at least 10 characters, letters with numbers or symbols, not your user name.

- **Change password**: top bar, next to your name.
- **Forgotten password**: ask the Admin (Admin → Users → Reset password). You get a temporary password and
  choose a new one at sign-in.
- Five wrong attempts lock the account for 15 minutes (the Admin can unlock it sooner).

### Who can do what

| | See and export | Upload and change | Approve changes | Audit log | Users and settings |
|---|---|---|---|---|---|
| **Admin** | ✓ | ✓ | ✓ (not own) | ✓ | ✓ |
| **Preparer** | ✓ | ✓ | – | – | – |
| **Approver** | ✓ | – | ✓ (not own) | ✓ | – |
| **Viewer** | ✓ | – | – | – | – |

The Approver role exists only when the Admin switches approval on (section 9).

## 3. The daily routine (Preparer)

1. **Uploads** → choose what the file contains → choose the file → Upload. In this order:
   1. Category list (only when it changes)
   2. Bank balances (or type them in **Balances & facility**) and bank facility
   3. ERP receivables (customer collections)
   4. ERP PDC register (vendor post-dated cheques)
   5. ERP payment plan, bill discount / LC, additional collections, other & recurring items
2. Read the upload report. A file with errors is **rejected as a whole** and yesterday's data stays in use;
   the report lists each row and what is wrong. Fix the file and upload it again.
3. **Exceptions** (the menu shows how many are open): a header or category the app does not know. Map it to an
   existing category, add it as a new category, or leave the rows out. Tick "remember" so the same spelling is
   mapped automatically next time. When the last exception of a file is resolved, the file becomes current.
4. **Lot grid**: review the forecast (section 4). Check the *Bank position and ERP tie-out* panel: the ERP bank
   total should equal yesterday's forecast plus today's movements; a variance is shown if not.
5. **PDC list / Hold register**: hold or release cheques as agreed (section 5).
6. **Export to Excel** for the CFO pack (section 8). Optionally **Save snapshot** (the app also saves one a day).

Upload templates for manual files are on the Uploads page; the column layouts are in
[input_formats.md](input_formats.md). Amounts are positive, in OMR with up to 3 decimals; use `.` for decimals.

## 4. Reading the lot grid

Columns: one per lot, a **month total** after each month (a `*` marks a part month), and the **horizon total**.
The lot holding today's date is **CURRENT**. Click any figure to see the items behind it.

| Block | Rows | Notes |
|---|---|---|
| A | Opening bank balance | Current lot: ERP bank total. Later lots: previous lot's closing. |
| B | Cash inflows by category | Collections, additional collections… |
| C | Cash outflows by category | Vendor PDCs, payment plan, salaries, other… |
| D, E | Net cash flow, **closing balance (as per ERP items)** | |
| F | Bank facility, funding position before holds, funding gap | Gap = negative funding position. |
| G | **Cheque holds** | PDCs put on hold (+), held PDCs re-presented (–), net and cumulative effect, closing after holds, **NET FUNDING POSITION AFTER HOLDS**, shortfall after holds. |
| | **Are the holds sufficient?** | *No gap* (green) · *Covered by holds* (amber: there was a gap and the holds close it) · *NOT sufficient* (red: still a gap after holds). |
| H | Memo, not in totals | Risk-adjusted collections left out, amounts deferred into the lot, holds not re-presented within the horizon. |

Rows B–F always show the ERP position; holds act only in block G, so you can see both.

Above the grid: **Scenario**, **Risk-adjusted collections** (include / exclude), **Collection dates** (due dates or
the advisory delay model), **Horizon** (1–12 months) and **As-of date**. These change the view only, never the data.
The key figures and the commentary under the grid summarise the lowest funding position, gaps and holds.

## 5. Holding a cheque

**PDC list** shows every vendor cheque by lot, with a running summary of the funding position before and after holds.

1. In the cheque's **Action** column choose **Hold cheque**.
2. Enter the **next honouring date** (or use a quick pick: +10 days, next lot, next month), or tick
   **Open-ended** if no date is agreed yet.
3. Optionally hold only part of the amount, and give a reason (e.g. *Await delivery note*).
4. **Hold cheque**. The grid and summaries update at once.

The cheque stays in the Vendor PDCs row (as per ERP). Block G takes it out of its lot and puts it back in the lot of
the honouring date, so the funding position after holds rises from the cheque's lot up to the honouring lot.
An open-ended hold raises every later lot.

Warnings shown on the cheque: amount larger than the cheque, honouring date not after the cheque date, date
already passed, date after the horizon, cheque older than the validity period (confirm with the bank), or
"honouring lot is in a gap — the problem has only moved".

- **Extend / change hold**: same menu; the history keeps every version and counts extensions.
- **Release hold**: the cheque is honoured on its own date again.
- **Hold register**: all cheques on hold, with days held, times extended, who held them, and the history.

## 6. Other changes to an item

Available from the item's Action menu (PDC list, or the drill-down from a grid figure):

| Action | Effect |
|---|---|
| Defer to lot | Moves the item to a later lot. Nothing is lost: the amount leaves one lot and arrives in the other. |
| Re-date | Gives the item a new date (and so a new lot). |
| Reduce amount | Uses a smaller amount (e.g. part payment). |
| Exclude | Leaves the item out of the forecast; it stays stored as imported. |
| Flag risk-adjusted | (Collections) left out when *Risk-adjusted collections* is excluded. |
| Flag bill discounted | (Collections) already financed by the bank; not counted again. |
| Back to as imported | Revokes every change on the item. |

Changes are keyed by the ERP reference (invoice, voucher + cheque number), so **they survive the next day's
upload**. If an item disappears from the ERP file (e.g. the cheque cleared), its changes simply stop applying.

## 7. Scenarios and snapshots

- **Scenarios** lists every scenario side by side with its key figures. The Admin creates them (e.g. *Stress*:
  risk-adjusted collections excluded, delay model on). The default scenario is used for snapshots.
- **Save snapshot** stores the day's figures. Past lots are then shown as locked *ACTUAL* columns (if the Admin
  sets the grid to start at the beginning of the month) and feed the next day's tie-out.

## 8. Export to Excel

**Lot grid → Export to Excel** exports exactly what is on screen (scenario, toggles, horizon, as-of date).

The workbook has the sheets *Forecast* (the grid), *Items*, *Holds*, *Bank* and *About*. Every figure on *Forecast*
is a **live formula** (`SUMIFS` over Items and Holds), so if you change an amount on *Items* the forecast updates.

Before the file is released, the app has LibreOffice recalculate every formula and compares each cell with the
screen. If even one cell differs, the export is **blocked** and the differing cells are listed. Only checked files
can be downloaded. **Exports** in the menu lists every export with its check result.

## 9. Approvals (when switched on)

The Admin can switch on approval (Admin → Settings → `approver_enabled`) and give someone the Approver role.

- A Preparer's hold, deferral, re-date, reduction, exclusion or flag is then a **request**: it shows
  "⏳ Waiting for approval" and the forecast does **not** use it yet. Any change approved earlier stays in force.
- **Approvals** (menu, with a count) lists the requests and, for each, the **lowest funding position after holds
  now and if approved**.
- The Approver (or Admin) clicks **Approve**, or **Reject** with a comment. **Nobody can approve their own change.**
- The person who asked (or the Admin) can **Withdraw** a request. A newer request for the same item replaces the
  older one.
- **Release hold** and **Back to as imported** apply at once, because they return the item to the ERP figures.

## 10. For the Admin

- **Admin → Users**: add users (a temporary password is shown **once**; give it in person), change name, role or
  active flag, **Reset password**, **Unlock**. The last active Admin cannot be removed.
- **Admin → Categories**: rows of the report (name, direction, summary group, order). A category in use cannot change
  direction; deactivate it instead.
- **Admin → Settings**: lot scheme and length, **lot anchor date** (see below), horizon months, month totals, grid start, funding alert threshold,
  default hold days, cheque validity, approval. Every change is audited.
  - **Lot anchor date** (blank = lots start on the 1st). With `month_thirds`, the *day* of the date starts every
    period: day 5 gives periods 5 Nov–4 Dec split into 5–14, 15–24 and 25 Nov–4 Dec, and the period totals and
    headings follow it (day 1–28 only, so every month has it). With `fixed_days`, lots repeat every lot length from
    that exact date, across month ends.
- **Admin → Backups**: encrypted backups (one a day automatically), *Back up now*, download. Restore is done on the
  server with `restore_backup.bat` (see README).
- **Audit log** (Admin and Approver): every sign-in, upload, change, approval, export, setting and backup. Filter by
  user, type, item (e.g. a cheque number) and dates; download as CSV. Nobody can edit or delete it.

## 11. Questions

**The grid did not change after my hold.** Approval may be on: the hold is waiting (section 9).

**An upload was rejected.** Nothing changed; yesterday's data is still in use. The report lists each row and the reason.

**The opening balance looks wrong.** Check *Balances & facility*: one balance per account for the as-of date; other
currencies need a manual rate to OMR.

**Export blocked.** "Could not run": LibreOffice is missing on the server (ask the Admin). "N differences": report it
to the Admin with the export number; the app refused to release a workbook that disagrees with the screen.

**Times look wrong.** Times are shown in Oman time (UTC+4).

---
*All data in this repository and the demo is synthetic.*
