# PROJECT STATE — Cash Runway

> **Read this file first in any new session.** It is the single source of truth for
> what is done, what is next, and every decision already locked. If a session ends
> mid-phase, resume from "NEXT ACTION" below.

**Project:** Cash Runway — CFO cash-command tool
**Owner:** Guru (CA, Reward360, Bangalore)
**Purpose:** ICAI AICA Level 2 capstone. Submission = ZIP (code + sample data + video walkthrough), fork + PR to `github.com/aiinicai/AICA-Level-2-Projects`.
**Deadline:** ~12-Sep-2026 (8 days from 04-Sep-2026)
**Owner availability:** ~2–3 hrs/day, for review/verification — Claude writes the code.

---

## Locked decisions

| # | Decision | Value | Locked on |
|---|---|---|---|
| 1 | App name | **Cash Runway** (renamed from "Finance Health Command Center") | 04-Sep |
| 2 | Stack | React + Vite + Tailwind (frontend) · FastAPI + SQLAlchemy + SQLite (backend) | 04-Sep |
| 3 | Auth | Simple login gate: JWT + bcrypt, roles Admin / CFO / Finance / Board Read-Only | 04-Sep |
| 4 | Deployment | Local-first (localhost), backend also exposed as a documented REST API | 04-Sep |
| 5 | Accounting connector | **Tally** primary/live (XML-over-HTTP, port 9000). Zoho + others = roadmap only, not built. | 04-Sep |
| 6 | Non-Tally data | **Manual in-app registers (audit-logged) + downloadable Excel upload templates** — both | 04-Sep |
| 7 | Scope | **All 12 tabs fully built** | 04-Sep |
| 8 | Demo data | **Seeded 18-month startup dataset (Northwind Robotics Pvt Ltd) + working live Tally connector.** Video runs on seeded data. | 04-Sep |
| 9 | SMS | **Twilio REST API from Python**, behind a channel interface so n8n can be swapped in. Was Meta WhatsApp until 09-Sep — the Cloud API refuses business-initiated messages outside a 24-hour recipient-opened window, so every alert would have needed a pre-approved template | 09-Sep |
| 10 | Spec | `docs/SPEC.md` is the contract — 12 tabs, verbatim from the CFO layout document | 04-Sep |

---

## Build phases

| Phase | Description | Status |
|---|---|---|
| P0 | Scaffold + spec/state files | ✅ done |
| P1 | Data model + seeded dataset | ✅ done |
| P2 | Calculation engine | ✅ done |
| P3 | Auth + API routes (all 12 tabs) | ✅ done |
| P4 | Tally adapter + normalizer | ✅ done |
| P5 | Alert engine + SMS | ✅ done |
| P6 | Frontend shell + design system | ✅ done |
| P7 | Tabs 1–3 (Today, Runway & Burn, Liquidity) | ✅ done |
| P8 | Tabs 4–6 (Money In, Money Out, Cash Calendar) | ✅ done |
| P9 | Tabs 7–9 (Plan vs Actual, Scenarios, Capital & Debt) | ✅ done |
| P10 | Tabs 10–12 (Board Pack, Alerts, Setup) | ✅ done |
| P11 | Verification, docs, submission package | ◐ code verified; ZIP + PR still to do |
| P12 | Onboarding, Tally wizard, board visibility, demo Tally data | ✅ done |

---

## NEXT ACTION

> **The application is complete and verified.** All 12 tabs are built, the API
> smoke test passes 0 failures, and every screen has been driven with a real
> browser and read back as a screenshot.
>
> What is left is submission mechanics, not build work:
> 1. Guru reviews the running app and gives feedback.
> 2. Record the video walkthrough — script at `docs/VIDEO_SCRIPT.md`.
> 3. Zip and raise the PR against `github.com/aiinicai/AICA-Level-2-Projects`.
>
> To run it: `run.bat` (or `./run.sh`), then http://localhost:8000,
> sign in as `guru@northwindrobotics.in` / `cashrunway`.
> Python only — no Node, no internet needed.

---

## Decisions locked in P12 (06-Sep)

| # | Decision | Why |
|---|---|---|
| 11 | **Demo data is a choice, not a default.** First run offers "load the demonstration company" or "set up my company". Sign-in accounts are bootstrapped either way. | The reviewer and the deployer want opposite things; guessing wastes the first two minutes of one of them. Also fixes the empty-database class of fault permanently. |
| 12 | **Onboarding is staged, not one long form.** Stage 1 = bank balances + 3 months of movement ⇒ a defensible runway number. | A forty-field form does not get finished. Getting to a real number in ten minutes is what makes someone come back. |
| 13 | **One schema drives the blank template, the worked example and the validator.** | A sample file that has drifted from the template it illustrates is worse than no sample. |
| 14 | **Ledger mapping is a person's decision, stored.** A confirmed row is never overwritten by a later sync; a new ledger is flagged, not absorbed. | Connecting to Tally is the easy half. A connector that guesses and moves on is how the numbers quietly go wrong. |
| 15 | **Daily sync is a poll, and says so.** Tally cannot push. | Promising freshness the architecture cannot keep is the kind of lie that only surfaces during a board meeting. |
| 16 | **Board visibility: hide detail, never contradict.** Masking at the edge, in one place; free text scrubbed as well as fields; withheld screens explain themselves. | If the board's runway and the CFO's runway disagree, the tool has destroyed the only thing it is for. Silent omission reads as concealment. |

## Session log

| Date | What happened |
|---|---|
| 04-Sep-26 | Spec received (12 tabs), 4 scope decisions locked, project scaffolded, SPEC.md written. |
| 04-Sep-26 | P1 done — 40 tables, 18-month seeded dataset (783 ledger entries, 132 receipts). |
| 04-Sep-26 | P2 done — 14 service modules, all 12 tabs' calculations. Three reconciliation defects found and fixed: forecast double-counted the as-on payroll; the 13-week grid had no forward billing so it contradicted runway; runway movement used total cash where the headline used unrestricted. |
| 04-Sep-26 | P3–P5 done — 66 API routes, Tally adapter + normaliser, alert engine with 10 rules and SMS delivery. Smoke test: 0 failures. |
| 05-Sep-26 | P6–P10 done — all 12 screens built. Chart palette validated with the dataviz validator (status colours CVD-separated; single-hue navy for data marks; teal/violet diverging poles for waterfalls so neither can be mistaken for a status). |
| 05-Sep-26 | Browser verification across all 12 screens and every sub-tab. Four defects found and fixed that the build had not caught: the seeded plan was at the company's old scale so every line-item variance read 150–750%; the plan-vs-actual bridge started from the opening balance so the deltas were invisible; the top-client-delay lever moved the forecast but not the runway, so the sensitivity ranking said collection speed was worth zero days; and sub-lakh amounts dropped to raw rupees mid-column. |
| 05-Sep-26 | README, architecture note, video script and one-command run scripts written. |
| 05-Sep-26 | Guru's machine (Python 3.14) could not install: exact version pins meant no prebuilt wheel existed, so pip tried to compile pydantic-core from Rust and demanded a C++ linker. Switched to version floors and dropped python-jose (unmaintained, pulled in Rust) for PyJWT. |
| 05-Sep-26 | His machine then failed DNS resolution for pypi.org entirely — corporate network. Made the whole application offline: bundled Windows wheels for Python 3.12/3.13/3.14 in `backend/vendor` (17 MB), pre-built the frontend and had FastAPI serve it, and removed the remote web-font import. Node is no longer needed at all; one server on :8000. Verified with every external request blocked at the browser: 12/12 screens render, 0 external requests attempted, 0 page errors. |
| 05-Sep-26 | Sign-in failed on Guru's machine. Two bugs: `run.bat` skipped seeding whenever `cashrunway.db` *existed*, but an earlier run had already created an empty one — so the app ran against a database with no accounts; and `api.js` turned every 401 into "session expired", including the login endpoint's "Email or password is incorrect", which pointed at the wrong fault. Fixed both: the run scripts now test for accounts rather than for the file, `app/main.py` seeds automatically when it finds no accounts (so this cannot recur however the database got there), the login 401 shows the server's own sentence, and `backend/doctor.py` diagnoses a broken install in one command. Reproduced the exact failure and confirmed the fix end-to-end in a browser. |
| 06-Sep-26 | P12 — four things Guru asked for after reviewing the running app. (1) First-run choice + staged onboarding + a set-up workbook whose blank template, worked example and validator all come from one schema; row-level rejection reporting, and the typed-in path validated by the same rules. (2) Tally wizard: connect → choose company → **map the ledgers** → schedule, with confirmed mappings surviving later syncs, plus a post-login sync-status banner where a failure is louder than a success. (3) Board visibility — eleven switches under "hide detail, never contradict". (4) Tally-importable XML for the demo company and a mock Tally endpoint, so the connector can be demonstrated without a licence. |
| 06-Sep-26 | Board masking leaked in an unexpected place: the engine *writes sentences* ("If Bharat Metro Rail Corporation paid 45 days late…"), and masking the structured fields left every one of those intact across Today, Money In, Alerts and the narrative. Found by driving the board account in a browser, not by the field-level test that passed. Fixed with a text scrubber that also derives the short forms prose actually uses ("Bharat Metro"), and the smoke test now asserts no name reaches the board across nine screens **and** that every headline figure is identical. |
| 05-Sep-26 | Re-ran the full smoke test against the bundled package versions (FastAPI 0.141, Starlette 1.6, pydantic 2.13.5, SQLAlchemy 2.0.52, bcrypt 5.0) rather than the older ones it was written against: 0 failures. |

---

## Open items / assumptions to confirm

- **Twilio account** — trial account sends only to verified numbers; Indian domestic-route delivery needs DLT registration (entity, header, template). See docs/SMS_SETUP.md.
- **Minimum cash floor** assumed ₹ 2.00 Cr (one payroll + statutory + buffer). Editable in Setup.
- **Fundraise lead time** assumed 6 months. Editable in Setup.
- **Company scale in the demo data** — Northwind bills ~₹ 1.9 Cr/month. This was
  chosen so the ₹ 22 L GST liability in the spec is arithmetically consistent with
  the revenue line (people-heavy company ⇒ thin input credit ⇒ large net GST).
  At a smaller scale the GST figure could not be made to tie.
- **DSCR / interest cover** come out negative — correct for a company burning cash.
  They are reported (lenders ask) but the covenants that actually bind are the
  liquidity and runway ones. Flagged on screen as "Not covenanted — negative while
  burning".
- Singapore entity carries a light dataset so the entity dropdown is not a dead end.

## Verified figures in the seeded dataset (as at 31-Aug-26)

| Figure | Value |
|---|---|
| Cash available | ₹ 4.17 Cr (₹ 45 L restricted, ₹ 2.50 Cr undrawn) |
| Net burn, 3-mth avg normalised | ₹ 54.0 L |
| Runway | 7.7 months · cash-out 22-Apr-27 |
| Liquidity health | 56 — Tight |
| Receivables | ₹ 3.81 Cr · DSO 59 · 27% overdue |
| Largest client | Bharat Metro Rail — 38% of AR, ₹ 84 L 47 days late |
| Statutory 30-day | ₹ 33.05 L due, ₹ 26.55 L earmarked, gap ₹ 6.50 L |
| 13-week low | ₹ 2.13 Cr in w/c 16-Nov-26 (floor ₹ 2.00 Cr) |
| Covenant status | Current ratio amber, 8.4% headroom |
