# Cash Runway — release log

Every pack sent to Guru, newest first. Each version is a complete, runnable
folder; there is no need to keep an older one except to compare.

Releases live in `releases/vN.N/`. To find the one you are running, open
`VERSION.txt` in the root of the folder.

---

## v1.8 — 09-Sep-2026

**Three things that had to be true before anyone could rely on this.**

- **The JWT signing key is no longer a literal in the source.** It was
  `"cash-runway-dev-secret-change-in-production"` — a published key, which
  means anyone who had seen the source could mint a valid token for any
  account, Admin included, without knowing a password. It is now generated
  once per installation into `backend/data/secret.key`, or taken from
  `CR_SECRET_KEY`. **Everyone signs in again after this upgrade**, because the
  key changed.
- **Sign-in now locks out.** Five wrong passwords for an account, or fifteen
  from one machine, and it refuses for fifteen minutes. The two thresholds
  differ on purpose: fumbling your own password should not lock every account
  for that machine, while a host working through the four addresses printed in
  the README should hit a wall. The failure message is identical whether or
  not the address exists, so the error cannot be used to confirm which
  accounts are real. Held in memory — no migration on an existing database, and
  a lockout does not survive a restart.
- **`python backup.py`.** Everything lives in one SQLite file. The copy uses
  SQLite's online backup API so it is safe while the app is running, then the
  backup is opened, integrity-checked and row-counted — and deleted if it
  fails, because a corrupt file that looks like a backup is worse than none.
  `--list`, `--verify` and `--restore` too; a restore saves the current
  database first. Fourteen kept.

**Also:** `run.bat` and `run.sh` now honour `CR_HOST`. The default is still
`127.0.0.1` — this machine only — but `CR_HOST=0.0.0.0` lets colleagues sign in
from their own devices over the office network. There is still no HTTPS, so
that is a trusted-network option and the README says so.

Not done, and named rather than left to be discovered: HTTPS, which needs a
certificate and a hostname; an SMS delivery webhook; and DLT registration.

## v1.7 — 09-Sep-2026

**Alerts move from WhatsApp to SMS, through Twilio.**

The WhatsApp path looked finished and could not have worked. Meta's Cloud API
accepts a free-form message only inside a **24-hour window that opens when the
recipient messages the business first**. An alert is business-initiated by
definition — it fires because runway crossed a threshold at 08:00, not because
anyone wrote in — so that window is always shut, and every alert would have
needed a template approved by Meta in advance. `config.py` already had a
`WA_TEMPLATE_NAME` setting; no code ever read it. Console mode and the tests
both passed regardless, which is the same failure shape as the Tally sign
convention and the missing `api.put`.

- **Twilio REST API**, behind the same channel interface — `console` and `n8n`
  are unchanged, and `CR_ALERT_CHANNEL` still picks between them.
- **The channel is now `sms` everywhere** — rules, delivery history, the
  pickers on Setup › Alert rules. A database written earlier says `whatsapp`;
  it is read as SMS regardless, and renamed once on the next start, so no rule
  loses its setting.
- **The SMS body is transliterated to GSM-7.** One character outside that
  alphabet — `₹`, an emoji, an em-dash — switches the whole message to UCS-2
  and cuts the segment from 160 characters to 70, so a four-line alert would
  have cost six segments instead of two. Email keeps the rupee sign and the
  deep link; SMS drops the link, which pointed at `localhost` and was useless
  on a phone.
- **The test result reports characters and segment count**, and says
  *accepted*, not *delivered* — Twilio taking a message is not a handset
  showing it, and without a status webhook the app cannot honestly claim more.

**What SMS does not escape, and the docs now say so:** sending to Indian
numbers on the domestic route needs DLT registration — entity, sender header
and every template approved in advance — and unregistered messages are dropped
at the network with no error returned. Twilio's international route reaches
Indian handsets unbranded and without it, which is what a demonstration runs
on. The code is production-shaped; the account is not production-registered.

New: `docs/SMS_SETUP.md` — Twilio setup, the trial-account verified-number
restriction, the DLT position, the Twilio error codes worth recognising, and
how to demonstrate with no account at all.

## v1.6 — 06-Sep-2026

**Three "Save" buttons that never saved.**

The browser-side API client had `get`, `post`, `patch`, `del` and `form` — but
no `put`. Three screens called `api.put`, so each failed at the moment of
saving with `put is not a function`: the work was done, the server never heard
about it, and the message said nothing a user could act on.

- **Setup › Tally › Map the ledgers** — Confirm all.
- **Setup › Tally › Schedule** — Save the schedule.
- **Setup › Board visibility** — saving the policy.

All three backend endpoints were correct and always had been; nothing but the
client was wrong. Board visibility is the one that matters most — the switches
appeared to work, and the policy was never stored.

This survived because the smoke test drives the API directly, where `PUT`
works. Nothing exercised the button that calls it. A test that talks to the
server cannot catch a client that never reaches the server.

## v1.5 — 06-Sep-2026

**The Tally import: "Voucher Date is missing".**

Three separate faults in the generated XML, any one of which produces that
message. The figures were never wrong — the trial balance checks clean, no
voucher is unbalanced, no bill allocation disagrees with its party line — so
this was a dialect problem, not a data problem.

- **`EFFECTIVEDATE` removed.** Tally honours it only when *Use effective dates
  for vouchers* is switched on under F11. In a default company the tag is read,
  the feature is off, and the voucher can be left with no usable date. A cash
  voucher needs `DATE` and nothing else.
- **The files are now plain ASCII and declare their encoding.** Every narration
  carried a typographic dash. Tally's reader is not a conforming XML parser:
  given no encoding declaration it takes the bytes as ANSI, so a multi-byte
  character lands mid-narration as three stray bytes — and a parser that loses
  its place there reports the failure against whatever tag it expected next.
  371 of the 374 vouchers had one.
- **The vouchers are split by financial year.** Tally imports into the period
  the company is currently open for, which for a new company is one year wide.
  One file spanning two years asks it to accept vouchers it is not open for.
  Now: import year one, `Alt+F2` to change the period, import year two. If year
  one lands clean and year two does not, the period is the problem and nothing
  else is.

Two smaller things found while looking:

- `PARTYLEDGERNAME` is no longer written on a Contra. A transfer between the
  company's own accounts has no party, and naming a bank ledger there is not
  what the field means.
- The MSME incentive receipt named a counterparty the company has no ledger
  for. The field is now written only when the party is a ledger the voucher
  actually posts to.

`docs/TALLY_IMPORT.md` rewritten for the five-file order, with the period
change as its own step and this exception at the top of the troubleshooting
table. **Import into a fresh company** — the exception vouchers from the
earlier attempt are still in the old one.

## v1.4 — 06-Sep-2026

**Two financial years of Tally data, so the tool has something to compare.**

- The demonstration Tally company now covers **17 months** — FY 2025-26 in
  full plus FY 2026-27 to 31-Aug-2026. Three files: 50 ledgers, 374 cash
  vouchers, 101 sales invoices with bill-by-bill references. Sync the full
  range and Runway & Burn shows collections up ~80% year on year and burn
  down by a third, with the months behind it.
- The data is generated, not written out by hand: sales are billed, receipts
  settle them oldest-first, and the ₹ 3.70 Cr of receivables left at the end
  is what the arithmetic leaves. Opening cash is back-solved so the closing
  position lands on ₹ 4.62 Cr, the figure every screen quotes.
- `python tally_export.py --check` prints the trial balance and **refuses to
  write the files** unless the books balance to zero, every voucher balances,
  no payable has drifted onto the debit side, and no bank account went
  overdrawn at any point in the seventeen months.
- Payroll is now posted properly — gross to the P&L, net to the bank, PF and
  TDS withheld and settled separately — and sales carry output GST. Without
  that, the payables sat in debit and the trial balance was nonsense to
  anyone who opened it.
- Added the transfers a company actually makes between its own accounts.
  Without them two of the three bank accounts finished deeply overdrawn.

**Two connector bugs found while building it, both of which would only ever
have shown against real Tally:**

- **Sign convention.** Inside `ALLLEDGERENTRIES.LIST` a negative amount is a
  debit; the adapter read it as a credit. Against real Tally every receipt
  would have been recorded as a payment — burn reading as income, every
  screen confidently upside down. Ledger balances had the same fault, which
  turned bank balances negative. Both now flip once, at the adapter boundary,
  and the mock endpoint emits Tally's convention rather than the intuitive
  one so this cannot pass a test and then fail in the one place that matters.
- **No bank accounts after a sync.** The connector created the chart of
  accounts but never a bank-account record, so a Tally-connected company had
  burn but no cash and runway came out as zero. Cash and bank ledgers now
  become bank accounts on sync. What Tally cannot say is which balances are
  restricted — that stays a manual entry, and the tool says so.

`docs/TALLY_IMPORT.md` updated: 1-Apr-2025 financial year, three files, and
the trial-balance figures to check against after importing.

## v1.3 — 06-Sep-2026

**Fixes the first-run screen, which v1.2 shipped unreachable.**

- `run.bat` and `run.sh` no longer load the demonstration dataset before
  starting the server. That was the fault: the application creates its sign-in
  accounts on first start and then *asks* which data to load, but the run
  scripts answered the question first, so the first-run screen never appeared.
  The run scripts are now two steps rather than three.
- **Setup › Import data › Start again** clears every figure and returns to the
  first-run screen, keeping sign-in accounts, definitions and alert rules.
  Confirmed by typing the phrase. This is what makes the set-up story
  demonstrable more than once — useful when recording.
- Silenced a SQLAlchemy warning printed when the demonstration company is
  loaded from inside the running application.

**Note if you are upgrading rather than replacing the folder:** an existing
`backend\data\cashrunway.db` still holds whatever was loaded into it. Delete it,
or use Start again, to see the first-run screen.

## v1.2 — 06-Sep-2026

The four items from the review.

- **First-run choice and staged onboarding.** Two doors on first sign-in.
  Set-up staged so stage 1 — bank balances plus three months of movement —
  produces a defensible runway number on its own. Screens without their data
  say what they need rather than showing a confident zero.
- **The set-up workbook.** Blank template, worked example and validator all
  generated from one schema. Row-by-row rejection report with row numbers and
  reasons; nothing written until the report is accepted. Typed-in entries
  validated by the same rules.
- **Tally wizard.** Connect → choose company → map the ledgers → schedule.
  Confirmed ledger mappings survive later syncs; new ledgers are flagged, not
  absorbed. Post-login sync banner where a failure is louder than a success,
  and a healthy connection shows nothing at all. States plainly that Tally
  cannot push.
- **Board visibility.** Eleven switches under one rule — hide detail, never
  contradict. Stable pseudonyms across every screen and pack. Withheld screens
  explain themselves.
- **Demonstration Tally data.** `demo-tally/` holds importable XML (49 ledgers,
  60 vouchers) and both workbooks; `mock_tally.py` stands in for Tally on port
  9000 so the connector can be shown without a licence.
- Fixed a masking leak found only by driving the board account in a browser:
  the engine writes sentences carrying counterparty names, and field-level
  masking left every one of them intact. Smoke test now asserts no name reaches
  the board across nine screens, and that every headline figure is identical to
  the CFO's.

## v1.1 — 05-Sep-2026

- Sign-in failed against an empty database. `run.bat` skipped seeding whenever
  the database file existed, but an earlier run had already created an empty
  one. Run scripts now test for accounts rather than for the file, and the
  application seeds itself if it finds none.
- A wrong password said "session expired". It now says "Email or password is
  incorrect"; a genuinely expired session still says so.
- Added `backend/doctor.py`, which diagnoses a broken install in one command.

## v1.0 — 05-Sep-2026

First complete build. Twelve screens, 89 API endpoints, 40 tables, an 18-month
seeded dataset, Tally adapter, alert engine with WhatsApp delivery, and the
offline bundle — Windows wheels for Python 3.12–3.14 and a pre-built frontend,
so it runs with no internet and no Node.
