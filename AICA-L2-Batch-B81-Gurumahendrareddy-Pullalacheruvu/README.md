# Cash Runway

**Cash command for founders and CFOs.**  ·  v1.8 — see [CHANGELOG.md](CHANGELOG.md)

Startups do not fail because they are unprofitable. They fail because they run
out of cash while the P&L still looks fine. Cash Runway is a twelve-screen tool
that answers one question per screen, built so a CFO can defend every number in
it in front of a board.

Built as the capstone for the ICAI **AICA (AI for Chartered Accountants) Level 2**
certification.

---

## What makes it different from a dashboard

Four rules run through the whole application, and they are the reason it is
usable rather than merely informative:

1. **One question per tab.** If the question cannot be said in a sentence, it
   is not a tab. Every screen header states its question.
2. **No number without its basis.** Every figure carries how it was worked out
   and the date it is as at. "Burn ₹ 62 L" is meaningless; "Net burn, 3-month
   average, normalised, as on 31-Aug-26" is usable.
3. **Every number is traceable.** Click any figure and the drawer shows the
   ledger entries, invoices or balances behind it. A figure you cannot trace is
   a figure you cannot quote.
4. **Colour means one thing only.** Red = act this week · Amber = watch ·
   Green = within tolerance · Grey = data incomplete, don't rely on it. Never
   decorative, and never carried by hue alone — every status has a word beside it.

The application is also honest about its own limits. When books and bank
disagree, a banner appears and every headline number carries a grey dot. When
confidence is low, the commentary **suppresses itself** and shows only the
data gaps — the CFO's instruction was that silence beats confident narration on
bad data.

---

## The twelve screens

| # | Screen | The question it answers |
|---|---|---|
| 1 | Today | Am I fine, and what needs me this week? |
| 2 | Runway & Burn | How fast am I spending, on what, and how long does that leave me? |
| 3 | Liquidity | Is my cash actually available, and is my position structurally healthy? |
| 4 | Money Coming In | What's owed to me, will it actually arrive, and how exposed am I? |
| 5 | Money Going Out | What must I pay, what can wait, and what have I already committed to? |
| 6 | Cash Calendar | Which specific week do I have a problem in? |
| 7 | Plan vs Actual | Are we tracking to what we told ourselves and the board? |
| 8 | Scenarios | What happens if, and which lever should I pull? |
| 9 | Capital & Debt | What do I owe lenders, what can I draw, am I about to breach something? |
| 10 | Board Pack | Can I produce the cash story for the board in ten minutes? |
| 11 | Alerts | What has the tool told me, and did anyone act on it? |
| 12 | Setup | Sources, plans, alert rules, people and definitions. |

Full specification: [`docs/SPEC.md`](docs/SPEC.md).

---

## First run

The first thing the application asks is which data to load, because the two
people who open it want opposite things:

- **Load the demonstration company** — eighteen months of Northwind Robotics,
  every screen populated, nothing to type.
- **Set up my company** — an empty book, then bring figures in from Tally, from
  a workbook, or by hand.

Set-up is staged rather than a single long form:

| Stage | What you enter | What it buys you |
|---|---|---|
| 1 | Bank balances · three months of receipts and payments | Cash available, net burn, runway, cash-out date |
| 2 | Open invoices · open bills · statutory dues | Ageing, DSO, concentration, the 13-week calendar, the statutory gap |
| 3 | Committed but not billed | Spend already promised that sits in no ledger |

A screen without its data says what it needs. It never shows a confident zero —
"₹ 0 receivable" and "no invoices entered yet" look identical on a card and
mean opposite things.

### The set-up workbook

Setup › Import data gives you two files built from the same schema, so they
cannot drift apart:

- **Blank template** — one sheet per thing the tool needs, with dropdowns on
  every choice column and the required columns marked.
- **Worked example** — the same workbook filled in with Northwind's figures.

Upload a filled-in file and it is read and checked before anything is saved.
You get a row-by-row report — every rejected row with its row number and a
sentence saying what is wrong — and nothing is written until you accept it.
Typed-in entries go through exactly the same validation, so the form cannot
quietly accept what the upload would have rejected.

---

## Running it

**You need Python 3.12, 3.13 or 3.14. Nothing else.**

No internet connection is required. The Python packages are bundled in
`backend/vendor` as ready-built wheels, and the frontend is already built and
served by the backend — so there is nothing to download, no Node, no `npm
install`, and only one server to start.

### One command

```
run.bat           # Windows
./run.sh          # macOS / Linux
```

Then open **http://localhost:8000** and sign in.

On Windows the browser opens by itself. On macOS and Linux `run.sh` installs
from PyPI rather than the bundle, because the bundled wheels are Windows-only.

### Or step by step

```bash
cd backend
pip install --no-index --find-links vendor -r requirements.txt   # offline
python seed_db.py                                                # demo data
python -m uvicorn app.main:app --port 8000
```

`--no-index` tells pip never to contact PyPI. With internet access,
`pip install -r requirements.txt` works too.

### Signing in

| Account | Role | What it can do |
|---|---|---|
| `guru@northwindrobotics.in` | CFO | Everything except user administration; can approve plans |
| `meera@northwindrobotics.in` | Finance | Enter and edit data; cannot approve plans |
| `vikram@northwindrobotics.in` | Admin | Everything, including users |
| `rohan@northstarventures.in` | Board Read-Only | Sees every screen, changes nothing, and sees only what the CFO has published |

Password for all four: `cashrunway`

### Working on the frontend

Only needed if you want to change the interface. Node 18+, then:

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, proxies /api to :8000
npm run build    # rebuilds frontend/dist, which the backend serves
```

---

## The demonstration data

The app ships with 18 months of ledger for **Northwind Robotics Pvt Ltd**, a
Bangalore industrial-IoT company that closed a ₹ 18 Cr Series A in Feb-2025.

Nothing in it is asserted. Bank balances are derived from the ledger; the
opening balance is back-solved so the closing position lands on target;
receivables, payables and statutory dues are real open items with real due
dates, so ageing, weighted collections and the 13-week calendar are all
computed rather than hard-coded.

As at 31-Aug-2026 the position is:

| | |
|---|---|
| Cash available | ₹ 4.17 Cr (₹ 45 L lien-marked, ₹ 2.50 Cr undrawn credit) |
| Net burn | ₹ 54.0 L / month, 3-month average, normalised |
| Runway | 7.7 months · cash-out 22-Apr-27 |
| Liquidity health | 52 — Tight |
| Receivables | ₹ 4.80 Cr · DSO 72 days · 42% overdue |
| Largest client | Bharat Metro Rail — 36% of receivables, ₹ 84 L 47 days late |
| Statutory, next 30 days | ₹ 33.05 L due, ₹ 26.55 L earmarked, **₹ 6.50 L gap** |
| Covenant status | Current ratio amber — 8.4% headroom, tested 30-Sep |

That is a company that needs this tool.

---

## Connecting your own data

### Tally Prime

**Setup › Tally** is a four-step wizard, and only the third step is interesting.

1. **Connect.** Tally must be running on the same machine or network with its
   HTTP endpoint enabled: **F1 › Advanced Configuration › Enable ODBC/HTTP =
   Yes**, port 9000. There is no API key — the trade-off is that the app has to
   reach Tally over the local network, which suits a local-first tool. When it
   cannot connect, the screen lists the five things to check, in order.
2. **Choose the company.** Tally can have several open. A connected-but-empty
   endpoint is a common cause of a sync that returns nothing without failing,
   so the screen names that case.
3. **Map the ledgers.** This is the step that decides whether the numbers are
   right. Every Tally company has its own chart of accounts, written by whoever
   was there at the time — "Sundry Debtors - BLR", "SD-Old", "Misc Exp 2". The
   app shows its guess for each ledger and a person confirms or corrects it.
   **A confirmed row is a decision and is never overwritten by a later sync**;
   a ledger created since the last review is flagged rather than absorbed.
4. **Schedule.** Daily is usually right.

   > Tally cannot push. There is no webhook. A daily sync means this
   > application polls Tally at the time you set, which only happens if it is
   > running then. If the machine was asleep, the sync did not happen — and the
   > banner says how old the data actually is rather than quietly catching up.

After sign-in, a banner reports the connection's state. A **failed sync is
louder than a successful one**, and a healthy connection shows no banner at
all: the dangerous state is not "sync failed", it is "sync failed four days ago
and the screen still shows numbers".

```bash
export CR_TALLY_HOST=localhost
export CR_TALLY_PORT=9000
```

Zoho Books, QuickBooks and a generic CSV importer are roadmap: because
everything downstream reads the common schema, adding one means writing an
adapter and touching no screen.

### Demonstrating the Tally connection

Two ways, in `backend/`:

```bash
python tally_export.py     # writes the five XML files into demo-tally/
python mock_tally.py       # a stand-in for Tally, on port 9000
```

`tally_export.py` produces Tally-importable XML covering **seventeen months** —
FY 2025-26 in full plus FY 2026-27 to 31-Aug-2026, so the tool has a prior year
to compare against. Five files: 50 ledgers, 374 cash vouchers and 101 sales
invoices with bill-by-bill references, with the vouchers and invoices split by
financial year. Create a company called *Northwind Robotics Pvt Ltd* with a
financial year from **1-Apr-2025**, then import masters, year one, change the
period with `Alt+F2`, and import year two. Masters first, because a voucher
naming a ledger Tally does not have is rejected; and the years separately
because Tally imports only into the period the company is open for, and
declines the rest as a count of exceptions rather than a sentence.
`docs/TALLY_IMPORT.md` has the steps and the paths.

Nothing in that data is asserted. Sales are billed, receipts settle those bills
oldest-first, and the receivables left on 31-Aug-2026 are whatever the
arithmetic leaves. Opening cash is back-solved so the closing position lands on
the figure every screen quotes. `python tally_export.py --check` prints the
trial balance and refuses to write the files if the books do not balance, no
payable has drifted onto the debit side, or any bank account went overdrawn
along the way.

|  | Collections | Net burn |
|---|---|---|
| FY 2025-26 | ₹ 94 L / month | ₹ 84 L / month |
| FY 2026-27 (to Aug) | ₹ 170 L / month | ₹ 56 L / month |

Step-by-step instructions, including what to do when Tally complains:
[`docs/TALLY_IMPORT.md`](docs/TALLY_IMPORT.md).

`mock_tally.py` answers the same four requests the connector makes, with the
same data, on the same port — so the connection can be demonstrated without a
Tally licence. It is a demonstration aid, and it prints every request it
serves. Do not run it alongside a real Tally instance; they cannot both hold
port 9000.

The chart of accounts in both deliberately includes two ledgers the classifier
cannot recognise, so the mapping screen has something real to do.

### What Tally cannot tell you

Roughly 55% of what a CFO needs is not in any accounting system: which bank
balances are lien-marked, what has been committed on a PO that hasn't been
invoiced, covenant thresholds, headcount and loaded cost, plan versions,
disputes, and how likely a given client is to actually pay.

All of that is maintained in-app, entered by a named person at a recorded time,
and listed together in **Setup › Manual Entries Register** — so it is always
obvious which figures depend on someone keeping them current.

### What the board sees

Real boards get a curated pack, so the board view is curated here too — by the
CFO or an Admin, in **Setup › Board visibility**. Eleven switches: client and
vendor names, individual salaries, bank account numbers, drill-downs, untabled
plans, covenant headroom, alert routing, the activity log, the manual register,
scenario levers.

One rule governs all of it, and it is a design decision rather than a setting:

> **Hide detail, never contradict.**

Every headline figure a board member sees is the same figure the CFO sees. What
can be withheld is the granularity behind it — and wherever something is
withheld, the board's screen says so. A board member who can see that a thing
was restricted is being governed; one who cannot is being misled, and would
never trust the tool again on finding out.

Concretely:

- Names become "Client A", allocated once and **stable everywhere** — the same
  company on Money Coming In, in the board pack and in an alert.
- The engine also *writes sentences*. "If Bharat Metro Rail Corporation paid 45
  days late…" is masked too, in prose as well as in fields; masking the
  structured columns while leaving the paragraphs intact would be worse than
  not masking at all, because it would look like the policy was working.
- A withheld screen returns a sentence explaining the decision, not a blank page.
- Masking sits in one place, at the edge, so an endpoint written next month is
  covered the day it is written. The engine underneath is untouched — which is
  what guarantees the figures cannot diverge.

The smoke test asserts both halves: that no counterparty name reaches the board
across nine screens, and that every headline figure is identical.

### SMS alerts

Alerts go out as SMS through Twilio.

```bash
export CR_TWILIO_ACCOUNT_SID=AC...
export CR_TWILIO_AUTH_TOKEN=...
export CR_TWILIO_FROM=+15551234567
```

Then Setup › Alert Rules › **Send a test message** to prove delivery before
relying on it. The result reports the character count and the number of SMS
segments the message costs.

**Why not WhatsApp.** The first build used Meta's Cloud API, and it could not
have worked: Meta accepts a free-form message only inside a 24-hour window
opened by the *recipient* messaging first, so a business-initiated alert —
which is every alert — would have needed a pre-approved template. SMS has no
such window.

**What SMS does not escape, in India.** Sending on the domestic route needs
DLT registration: the entity, a sender header and every message template
approved in advance, with unregistered messages dropped at the network and no
error returned. Twilio's international route reaches Indian handsets without
that, unbranded, and is what a demonstration runs on. The code is
production-shaped; the account is not production-registered.
`docs/SMS_SETUP.md` says so at length.

The message body is transliterated to the GSM-7 alphabet before sending — `₹`
becomes `Rs`, severity emoji are dropped. One character outside that alphabet
switches the whole SMS to UCS-2 and cuts the segment from 160 characters to
70, so a four-line alert would cost six segments instead of two. Email keeps
the rupee sign and the deep link, which SMS omits because it points at
`localhost`.

Routing through n8n instead is a one-line change — the sender sits behind an
interface:

```bash
export CR_ALERT_CHANNEL=n8n
export CR_N8N_WEBHOOK_URL=https://your-n8n/webhook/cash-runway
```

`CR_ALERT_CHANNEL=console` prints messages to the server log with their segment
count, which is what you want when demonstrating the app without a Twilio
account. Nothing is stubbed — the same code builds the same body; only the
transport changes.

### Letting other people sign in

The app is a normal web application — four roles, real sign-in, and the board
account is filtered server-side rather than just shown a different screen. But
it binds to this machine only by default, so nobody else can reach it. To let
colleagues in from their own laptops and phones:

```
set CR_HOST=0.0.0.0      REM Windows; export CR_HOST=0.0.0.0 elsewhere
run.bat
```

They open `http://<your-machine-ip>:8000`. **There is no HTTPS** — passwords
cross the network in clear text — so do this on a trusted office network and
not on public wi-fi. Putting it behind Caddy or nginx with a certificate is
the fix, and is not done.

### Sign-in security

The JWT signing key is **generated once per installation** and kept in
`backend/data/secret.key`. It is never a literal in the source: a shipped
default is a published key, and anyone holding the source could otherwise mint
a valid token for any account. Set `CR_SECRET_KEY` to override it. Deleting
the file signs everybody out.

Five wrong passwords for one account, or fifteen from one machine, and sign-in
is refused for fifteen minutes — `CR_LOGIN_MAX_ATTEMPTS` and
`CR_LOGIN_LOCKOUT_MINUTES` change that. The counter lives in memory, so it
does not survive a restart; an attacker on the far side of the API cannot
cause one.

### Backups

```bash
cd backend
python backup.py                    # take one now
python backup.py --list             # what exists
python backup.py --verify FILE      # check one, change nothing
python backup.py --restore FILE     # put one back
```

Everything lives in one SQLite file, so this matters more than it looks. The
copy is taken with SQLite's online backup API, which is safe while the app is
running — a plain file copy is not, because it can catch the database
mid-write.

Every backup is then **opened, integrity-checked and row-counted**, and one
that fails is deleted rather than kept: a corrupt file that looks like a
backup is worse than no backup. A restore saves the current database first,
because restoring the wrong file is a mistake people make once. Fourteen are
kept.

### The "Reading of the Position" commentary

**As shipped, this is a deterministic narrator — not a language model.**
`_rule_narrative()` in `app/services/narrative.py` assembles four to six
sentences from figures that are already computed and already formatted, using
ordinary conditional logic. Same inputs, same sentence, every time. Nothing is
sent anywhere, there is no API cost, and a number cannot be invented because
the narrator never produces one — it only places figures the services worked
out.

For a finance tool that is the safer default, and it is what every screenshot
and recording of this application shows. The API response says which path
produced the text, in a `source` field reading `"rules"`.

An optional model-written path exists behind the same interface: set
`ANTHROPIC_API_KEY`, install the `anthropic` SDK, and `_ai_narrative()` is
tried first with the deterministic narrator as the fallback. **Neither the key
nor the SDK is part of this build** — `anthropic` is deliberately absent from
`requirements.txt`, so the application runs offline with no external
dependency. Switching it on is a decision someone has to make, not a default.

Either way the same rule applies: the narrator is handed formatted facts and
never asked to compute anything.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Without a key, a deterministic narrator writes the same shape of paragraph from
the same facts. **The screen never shows an error and never shows nothing.**

---

## Architecture

```
                     ┌──────────────────────────────┐
   Tally Prime  ────▶│  Adapter  →  Normaliser      │
   (XML/HTTP)        │  (app/adapters/)             │
   Zoho (roadmap)───▶│  one common internal schema  │
   CSV   (roadmap)───▶└──────────────┬───────────────┘
                                     ▼
   Manual registers ─────▶  ┌─────────────────┐
   (in-app, audited)        │  SQLite          │  40 tables
                            └────────┬─────────┘
                                     ▼
                     ┌──────────────────────────────┐
                     │  Calculation engine          │  14 modules
                     │  burn · runway · liquidity   │
                     │  AR · AP · 13-week calendar  │
                     │  variance · scenarios        │
                     └───┬──────────┬───────────┬───┘
                         ▼          ▼           ▼
                   Alert engine  AI narrator  REST API
                         │                       │
                  SMS / email            React + Vite + Tailwind
                  (Meta Cloud API)          12 screens
```

Every figure the API returns travels with a `basis` string, an `as_on` date and
— where it is clickable — a `trace` descriptor that `/api/trace` replays to show
the underlying entries. The frontend never builds a query.

The API is documented and usable on its own at `/docs`, so the engine can be
driven from a script or another system, not only from this app's frontend.

More detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Layout

```
cash-runway/
├── README.md
├── PROJECT_STATE.md          build log and every locked decision
├── run.sh / run.bat
├── docs/
│   ├── SPEC.md               the CFO's specification — the contract
│   ├── ARCHITECTURE.md
│   └── VIDEO_SCRIPT.md       walkthrough script
├── demo-tally/               Tally-importable XML for the demo company
├── backend/
│   ├── seed_db.py            loads the demonstration dataset
│   ├── doctor.py             diagnoses a broken install in one command
│   ├── tally_export.py       writes the Tally import XML
│   ├── mock_tally.py         a stand-in for Tally, for demonstrating
│   ├── smoke_test.py         end-to-end API test
│   ├── vendor/               bundled wheels — installs with no internet
│   └── app/
│       ├── models/           40 tables across 8 modules
│       ├── services/         the calculation engine
│       ├── adapters/         Tally, normaliser, notifier
│       ├── routers/          REST API
│       └── seed/             18-month dataset generator
└── frontend/
    ├── dist/                 pre-built; the backend serves this
    └── src/
        ├── lib/              formatting, API client, app state
        ├── components/       shell, figures, charts, primitives
        └── pages/            the twelve screens
```

---

## Testing

```bash
cd backend
python smoke_test.py
```

Signs in, exercises every read endpoint, every drill-down kind, the scenario
engine, the alert engine, a write with its activity-log entry, board-pack
generation and read-back, and checks that the Board Read-Only role is refused
on writes and allowed on reads.

---

## Deliberate omissions

Named by the CFO in the specification, and worth stating because they were
choices rather than gaps:

- **No P&L or balance sheet.** Those live in the accounting system; duplicating
  them invites reconciliation arguments. This tool is about cash.
- **No transaction browser.** Entries are reached by drilling from a number,
  never as a destination of their own.
- **No customisable widget dashboard.** If everyone arranges their own screen,
  no two people in a meeting are looking at the same thing.
- **No mobile version of the full tool.** On a phone, the alert and the five
  numbers from Today. Nothing else.
