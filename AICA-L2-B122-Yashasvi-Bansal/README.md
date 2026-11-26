# 3CD Helper – Form 3CD Clause 44 and Clause 31 from Tally

**Capstone Project – AICA Level 2 (ICAI)**
**Submitted by:** CA Yashasvi Bansal, Yash Associates – AICA-L2-B122
**Live demo app:** https://clause44-3cd-helper.lovable.app  
**Demo login (for the examiner):** username `demo` · password `Demo@456789` (sign in with "Email or username")
**Video:** _link to be added_

---

## 1. The problem

Every tax audit needs two Form 3CD clauses that take hours of manual work:

- **Clause 44 – break-up of expenditure by GST status.** Every expense and capital addition has to be split into: exempt / non-GST, composition dealers, other registered parties, and unregistered parties. The auditor goes ledger by ledger and party by party, checks each GSTIN, and reconciles the total with the books.
- **Clause 31 – loans and deposits (sections 269SS / 269T).** Every loan or deposit taken and repaid has to be reported, with the mode of payment, the maximum balance, and whether it went through an account payee cheque or bank.

The data is already in Tally, but CAs still copy it into Excel by hand, check GSTINs on the GST portal one by one, and type the result into the utility. It is slow and mistakes are easy to miss.

## 2. The solution

3CD Helper is a web app (installable on desktop and mobile) for a CA firm and its team.

1. **Bring data from Tally in one click.** A small Chrome / Edge extension (the *Tally Connector*) reads the Day Book and masters straight from TallyPrime on the same computer, using Tally's XML interface (read-only). Tally XML, ZIP, Excel and CSV files can also be uploaded.
2. **Clause 44, done ledger-wise.** The app reads the Tally group tree, suggests which ledgers belong in Clause 44 (purchases, direct and indirect expenses, fixed-asset additions) and which to leave out (depreciation, salary, taxes, provisions, round-off …). Each party is placed in a GST column from its GST registration type and GSTIN, with a reconciliation to the books total.
3. **Party check on the GST portal.** Parties that need checking are listed in one place. One click opens the GST portal search with the GSTIN filled in, and the status and taxpayer type are read back into the app.
4. **Clause 31 from the running balance.** Loan ledgers are found from the group tree. Each entry is classed as loan taken, repaid, given or received back from the running balance; TDS and interest entries are kept out; the mode (cheque, RTGS, cash …) can be set per line, and items that need review are marked.
5. **Reports** in the Form 3CD layout, exported to Excel, and shareable on WhatsApp through a private 7-day link.
6. **Client data link.** The firm sends a link; the client brings the data from their own Tally and it reaches the firm's app – or the firm's own Google Drive (a script in the firm's Google account with access only to the files it creates). The app then finds the right client's and year's file in Drive and brings it in.
7. **Firm workspace.** Owner / partner / staff roles, clients and assessment years, review and "Final" locking, notes and an activity log.

**Result on the demo company** (fictional data, AY 2026-27): the full Day Book and masters (about 44 MB of Tally XML) were read in the browser; Clause 44 came to ₹1,13,29,518 across 116 ledger-party lines and reconciled to the books; 9 parties were flagged for checking.

## 3. How AI was used – from *using* AI to *building with* AI

The whole application was designed and built by a practising CA (CA Yashasvi Bansal) without a programming background, by working with AI tools:

| Stage | AI tool | What it did |
|---|---|---|
| Idea to first app | **Lovable** (AI app builder) | Turned plain-language prompts into the first working app, database and sign-in |
| Logic and features | **Claude** (Anthropic), as a coding agent connected to this GitHub repository | Wrote and tested the Tally XML reader, the Clause 44 and Clause 31 rules, the connector extension, the GST portal helper and the Google Drive script, from instructions given in Hindi |
| Review | Claude | Independent audits of the code for errors (16 issues found and fixed), and checks against real Tally exports |
| Domain rules | The CA | Clause 44 and 31 treatment, what to include or leave out, review points – given to the AI as instructions and checked on real books |

Prompts were written as a CA would explain the work to a junior: *what the clause needs, what the books look like, and what the report should show.* The AI wrote the code; the CA decided the rules and checked every result against Tally.

The finished app **does not need AI to run**: the rules are fixed and explainable, so the same books always give the same result, there is no per-use AI cost, and client data does not go to any AI service.

## 4. Technology

- **Front end:** React 19, TanStack Start, Tailwind CSS (TypeScript)
- **Database and sign-in:** Lovable Cloud (Supabase – PostgreSQL with row-level security per firm)
- **Tally link:** Chrome / Edge extension (Manifest V3) talking to TallyPrime's XML port (9000)
- **Google Drive:** Google Apps Script web app with the minimal `drive.file` scope
- **Files:** Excel / CSV / XML / ZIP read in the browser (a web worker), so large books do not slow the page

## 5. Folder contents

| Folder / file | What is inside |
|---|---|
| `3CD Helper - App Source Code/` | Full source code of the app (see `HOW-TO-RUN.md` inside) |
| `3CD Helper - App Source Code/src/lib/c44/` | Clause 44 rules (ledger choice, GST columns, reconciliation) |
| `3CD Helper - App Source Code/src/lib/c31/` | Clause 31 rules (running balance, loan kinds, TDS, review marks) |
| `3CD Helper - App Source Code/drizzle/migrations/` | Database tables and security rules (SQL) |
| `3cd-tally-connector/` | The Tally Connector Chrome / Edge extension (Load unpacked) |
| `Google Apps Script/` | The Google Drive script the firm installs, with set-up steps |
| `demo tally prime 5.0 data/100000/` | TallyPrime 5.0 data of the fictional demo company Aeron Medicare Pvt. Ltd. |

## 6. How to see it working

**Quickest – the live demo app:** open https://clause44-3cd-helper.lovable.app, type `demo` in "Email or username" and `Demo@456789` as the password. The demo firm already has the fictional company **Aeron Medicare Pvt. Ltd.** (AY 2026-27) with Clause 44 and Clause 31 prepared; open Clients → Aeron Medicare → AY 2026-27.

The video shows the full flow on a fictional company: bringing data from Tally, Clause 44, the GST portal check, Clause 31, the client link and Google Drive.

To try it with Tally: copy the folder `demo tally prime 5.0 data/100000` into TallyPrime 5's data folder and open the company **Aeron Medicare Pvt. Ltd.**; in TallyPrime set F1 → Settings → Connectivity → "TallyPrime acts as" = Both, port 9000. Install the Tally Connector (Chrome → `chrome://extensions` → Developer mode → Load unpacked → `3cd-tally-connector`), then in the app open a client's year and press **Bring data (all clauses)** → **Connect to Tally**.

To run the code yourself: see `3CD Helper - App Source Code/HOW-TO-RUN.md` (`npm install`, `npm run dev`; copy `.env.example` to `.env` with your own database values).

## 7. Data and privacy

- Each firm sees only its own data (database row-level security).
- The Tally Connector only reads from Tally and only works on this app's pages.
- The Google Drive script can reach only the files it creates; it cannot see or delete anything else in the firm's Drive.
- All data in this folder is fictional.

## 8. Declaration

I declare that this project is my original work, prepared for the AICA Level 2 Certificate Course of ICAI.
