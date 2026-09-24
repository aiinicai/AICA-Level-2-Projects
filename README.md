# Kashyap &amp; Co. — Assignment Profitability App

A small, self-contained web app that calculates the profitability of every
assignment (client engagement) and every Manager at Kashyap &amp; Co., a
Chartered Accountants' Risk Advisory practice — and lets you keep adding new
assignments, revenue, staff and cost as the year goes on.

It is seeded with the firm's actual Apr–Aug 2026 Billing and Prime Cost data
(from `Capstone_Project_Level_2_KV.xlsx`), and re-calculates profit live from
whatever is currently in the database, so new entries immediately flow
through to every report.

**No installation beyond Node.js is required.** The app has **zero external
dependencies** — no `npm install`, no build step, nothing to download except
Node itself.

---

## 1. Install Node.js (if you don't already have it)

Check whether you already have it:

```bash
node -v
```

If that prints a version number (v16 or later), skip to step 2.

If not, download the **LTS** installer for your operating system from
**https://nodejs.org** and run it (Next → Next → Finish). Then re-run
`node -v` to confirm it worked.

## 2. Run the app

From this folder:

```bash
node server.js
```

You should see:

```
=======================================================
 Kashyap & Co. - Assignment Profitability App
=======================================================
 Server running at: http://localhost:3000
 Press Ctrl+C to stop.
=======================================================
```

Open **http://localhost:3000** in your browser. That's it.

To stop the server, press `Ctrl+C` in that terminal.

Want a different port? `PORT=4000 node server.js`.

### Using npm instead

`package.json` also defines a script, so `npm start` does the same thing as
`node server.js` above (there is nothing to install first — `npm install`
would report "up to date" and do nothing, since there are no dependencies).

---

## 3. What you can do in the app

| Tab | What it's for |
|---|---|
| **Dashboard** | Firm-wide billing / cost / profit, a manager comparison chart, a cost-composition chart, and every assignment sorted into **Profitable**, **Non-profitable** and **In progress**. Click any assignment card for its full cost breakdown. |
| **Assignments** | The full list of assignments with computed billing, cost and profit. Add, edit or delete an assignment, filter by manager/status, and open the detail view (dedicated staff + every revenue line). |
| **Managers** | Roll-up per Manager (and for the Partner's cost pool) — billing, direct cost, pooled "many assignments" cost, allocated Partner-cost share, overhead, total cost, profit, margin. |
| **Staff & cost** | Every prime-cost entry. Add a new staff member's cost, tagging it as *dedicated* to one assignment, *many assignments* under a manager, or the *Partner-level* pool. Edit or delete existing entries. |
| **Billing & revenue** | Every billing / credit-note line. Add a new one against any assignment, edit or delete existing lines. |
| **Method** | A plain-English explanation of exactly how profit is calculated (mirrors §5 below). |

All changes are saved straight to `data/db.json` and every report
recalculates immediately — there is no "save" or "publish" step beyond
submitting the form.

---

## 4. Where your data lives

Everything is stored in one file: **`data/db.json`**. There is no external
database to install or configure.

- **Back it up** by copying that file — it's the entire app's data.
- **Reset to the original workbook data** by restoring a saved copy of
  `data/db.json`, or by re-running the importer (see §6).
- If you move the app to another folder/computer, just take the whole
  project folder (including `data/db.json`) with you.

---

## 5. How profitability is calculated

This mirrors the firm's specified allocation rules exactly (also shown in
the app's **Method** tab, and implemented in `lib/allocation.js`):

1. **Assignment billing** = sum of billing entries − sum of credit notes
   raised against that assignment.
2. **Dedicated staff cost** — a staff member working on a single assignment
   has their full prime cost charged straight to it.
3. **"Many assignments" cost** — a staff member shared across several
   assignments under **one** manager has their cost pooled at that
   manager's level, then spread across that manager's own assignments in
   proportion to each assignment's billing vs. the manager's total billing.
4. **Partner-level cost** — the Partner's own cost, and any staff who
   report directly to the Partner across many assignments, are first spread
   across the four Managers in proportion to each manager's billing vs.
   firm-wide billing, then — within each manager — spread across that
   manager's assignments in proportion to assignment billing (the same
   two-step waterfall as rule 3, just starting one level higher).
5. **Overhead** — 30% of an assignment's billing is added as overhead on
   top of the cost above (edit `data/db.json`'s `meta.overheadRate` to
   change this firm-wide, e.g. to `0.25` for 25%).
6. **Profit** = Billing − (direct + allocated "many" + allocated Partner +
   overhead). Manager and firm figures are simple totals of their
   assignments' figures — nothing is double-counted or left out.

**Dashboard buckets:** an assignment is **In progress** if it is explicitly
marked that way, or if it has no billing recorded yet (there's often cost
before there's revenue on a new engagement). Everything else is
**Profitable** or **Non-profitable** depending on the sign of its profit.
Change an assignment's status any time from the **Assignments** tab.

---

## 6. Re-importing from a fresh copy of the workbook (optional)

The app doesn't need Excel or Python to run day-to-day — this is only if you
want to rebuild `data/db.json` from scratch from a new export of the source
workbook (⚠️ this **overwrites** `data/db.json`, including any manual
entries you've made in the app, so back it up first):

```bash
pip install openpyxl pandas
python3 scripts/import_from_excel.py "/path/to/Capstone_Project_Level_2_KV.xlsx"
```

---

## 7. Checking everything still adds up

At any point — especially after re-importing from Excel or hand-editing
`data/db.json` — you can run:

```bash
node scripts/selftest.js
```

It reconciles billing, cost and profit across assignments/managers/firm,
checks every allocation sums back to its source, and flags any row with a
missing field or a dangling reference. It only reads the data, so it's safe
to run any time.

## 8. Project structure

```
kashyap-profitability-app/
├── server.js               Zero-dependency Node.js HTTP server (API + static files)
├── package.json
├── lib/
│   ├── allocation.js        The profitability allocation engine (pure functions)
│   └── db.js                 Small JSON-file-backed data store (load/save/CRUD)
├── data/
│   └── db.json                The database — all assignments, staff, revenue live here
├── public/                  The front end (no build step, no framework)
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── app.js             App logic: views, forms, API calls
│       └── charts.js           Small dependency-free SVG bar/donut chart helpers
├── scripts/
│   └── import_from_excel.py  One-time importer from the source workbook (optional)
└── README.md
```

## 9. Publishing to GitHub

```bash
cd kashyap-profitability-app
git init
git add .
git commit -m "Kashyap & Co. assignment profitability app"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

`data/db.json` is committed by default so a fresh clone works immediately.
If you'd rather keep the firm's cost/billing data out of a public repo,
add `data/db.json` to `.gitignore` before your first commit and instead
commit a redacted sample, or re-run the importer after cloning.

## 10. Troubleshooting

- **"Port 3000 is already in use"** — another program is using that port.
  Either close it, or run `PORT=4000 node server.js` and open
  `http://localhost:4000` instead.
- **Page loads but shows no data / "Could not reach the server"** — make
  sure the `node server.js` terminal is still running and hasn't shown an
  error; then refresh the browser tab.
- **Fonts look like a plain system font** — the page pulls Fraunces/Inter
  from Google Fonts for a nicer look. Without an internet connection it
  falls back to your system fonts automatically; nothing else in the app
  needs the internet.
- **`data/db.json` won't load / "Unexpected token" error on startup** — the
  file has been hand-edited into invalid JSON. Restore it from a backup, or
  re-run the importer (§6).
