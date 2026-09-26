# ProForma

Provisional, estimated and projected financial statements, CMA data and Schedule III
reporting for Indian entities — a decimal-safe engine with a React front end.

## Layout

```
packages/engine   the accounting core: pure functions, no framework, no DB
apps/api          Express + MongoDB — every piece of state lives here
apps/web          Vite + React UI
```

The engine is the source of truth. It runs unchanged in Node and in the browser,
so a figure on screen is the same figure the API persists and the same figure an
export carries.

The browser is a view, never a vault. Preferences and the model being typed into
are read from the API on boot and autosaved back as they change, so nothing at
all is held only in the tab — there is no localStorage. Close the laptop, open
the app somewhere else, and the same work is on screen.

## Running it

```bash
npm install
npm run dev          # builds the engine, then starts the API and the UI together
```

- UI — http://localhost:5173
- API — http://localhost:4000/api

Or separately: `npm run dev:api`, `npm run dev:web`.

## Serving it to other people

```bash
npm run serve        # builds everything, then serves the UI and the API together
```

One server, one port, one link. The API serves the built UI from its own origin,
so the browser asks for `/api` on whatever host it was loaded from — the same
build works on localhost, on a LAN address and behind a tunnel with nothing
rebuilt or reconfigured. Startup prints every address it can be opened on:

```
  Local    http://localhost:4000
  LAN (en0)   http://192.168.0.37:4000
```

`HOST` decides how far it reaches: `0.0.0.0` (the default) answers on every
interface, `127.0.0.1` keeps it to this machine. In development `npm run dev:web`
is on the network too, at `http://<lan-ip>:5173`.

### Over the internet

Put a password on it first — there are no accounts, and anyone who reaches the
port can read and change every entity and model:

```
AUTH_USER=cma
AUTH_PASS=a-long-random-string
```

Then pick a route in:

- **Tunnel (simplest).** `brew install cloudflared`, then `npm run tunnel` with
  the server already running. It prints an `https://…trycloudflare.com` address
  that works from anywhere, with TLS, and needs no router or firewall changes —
  which also makes it the only option that survives a dynamic home IP.
- **Port forwarding.** Forward an external port to this machine's `4000`. Needs a
  static IP or dynamic DNS, and the credentials travel in clear unless you put
  HTTPS in front.
- **Private network.** Tailscale or a VPN, if it should not be public at all.

Set `PUBLIC_URL` to whichever address you settle on and startup will print it
alongside the others. For a tunnel in *development* (`npm run dev:web`), Vite
refuses unknown hostnames, so pass `ALLOWED_HOSTS=<the-tunnel-host>` — the built
app served by the API has no such restriction.

### Database

Put a connection string in `apps/api/.env`:

```
MONGODB_URI=mongodb+srv://…
MONGODB_DB=proforma
PORT=4000
```

The API will not start without a reachable database, and there is no local
fallback: a fallback would mean an afternoon's work going somewhere other than
Atlas without anyone noticing. If the connection fails the usual cause is the
Atlas Network Access allowlist.

Four collections, one shape each:

| collection    | holds                                                        |
| ------------- | ------------------------------------------------------------ |
| `entities`    | the entity master — captured once, reused every year          |
| `models`      | filed models, keyed by entity and base year                   |
| `preferences` | display unit, decimals, theme, last view, last entity         |
| `drafts`      | the live working copy, autosaved as it is edited              |

A draft is the model on screen; filing it under an entity (**Master & Saved
Models → Save**) is still a deliberate act, so autosave never rewrites something
already filed. **Discard working draft** on the same screen clears the draft and
leaves filed models untouched.

An earlier build fell back to `apps/api/.data/workspace.json` when the database
was unreachable. To lift anything still only in that file into Mongo:

```bash
npm run migrate -w @proforma/api
```

It skips ids the database already holds and renames the file when it is done.

## Exporting a pack

**Export & Backup → Printable pack** builds the whole bound pack: cover, statements,
comparative notes, asset register, tax reconciliation, Schedule III disclosures,
CMA Forms I–VI, ratios and validation.

- **PDF** — print from the browser. The layout is A4 landscape with a running
  header, column headers repeated on every page, and rows kept off page breaks.
  Text stays selectable and searchable rather than being rasterised.
- **Excel** — one sheet per section plus a cover, with frozen headers, Indian
  digit grouping (`1,23,45,678.00`), print titles and fit-to-width already set.
  Figures are written as numbers, so a recipient can still calculate with them.

By default the notes are bound as **one** annexure, the register as **one** schedule
and the Schedule III disclosures as **one** — a single spreadsheet tab each, and a
pack that reads down the page instead of putting every note on its own sheet. Untick
*bind notes & schedules together* to go back to a section per note.

Tick the periods the pack is bound for. A renewal often wants two years of history and
one projected where a fresh proposal wants five; the selection applies to every
section at once, so the statements, the notes, the schedules and the CMA forms cannot
end up on different columns.

Verify a generated workbook actually opens:

```bash
npm run verify:xlsx -w @proforma/web -- /tmp/pack.xlsx
```

## Importing a trial balance

**Trial Balance & Mapping → Import file…** reads `.xlsx`, `.csv`, `.tsv` and plain
text, or you can drop a file onto the source box, or paste directly. The old binary
`.xls` format is refused with a message rather than parsed wrongly.

A **Tally export is recognised as one**, with no preparation: the company name, report
title and period above the table; the two-row header where Opening, Transactions and
Closing each span a Debit/Credit pair; `1,23,456.00 Cr` and bracketed negatives; group
lines that carry the total of the ledgers indented beneath them; and the Grand Total.
Group lines are dropped — keeping both them and their ledgers would double every
figure — and their names are carried onto the ledgers, which is what the mapping rules
want. Everything read is reported, including what was dropped and why.

### More than one unit

Add a unit and import a trial balance per branch. On consolidation the balances the
units hold against each other are **set off, not added**: the reciprocal current
accounts each pair keeps with the other, and the ledgers carrying goods between them.
Both are detected by name and listed with their amounts, and any of them can be
switched off or capped where only part of a ledger is internal.

The matched amount comes off the debit and the credit side together, so the
consolidated trial balance still tallies. What does not match is **not** absorbed — it
stands as a stated in-transit balance and is reported, because an unmatched inter-unit
account is a real difference for someone to reconcile.

### Merging ledgers

Tick two or more ledgers to present them as one line. Nothing is netted away and the
members are kept, so a merge can be undone exactly. The same grouping appears in
**Notes to Accounts**, where it can also be created and split apart — both write to the
same trial balance.

### Adjusting what was imported

A trial balance pulled before the accounts are closed is rarely final. Depreciation
for the year, the tax provision, interest accrued, the closing stock entry and any
reclassification are still to be passed — so **Adjustments** takes them as journal
entries rather than edits. Standard entries write both legs for you; the journal has
to balance before it is applied; and the mapping table shows what the file said, what
was passed over it, and what the statements read.

Nothing touches the imported figures, so every figure still traces back to the file.
An entry may name a ledger the trial balance does not carry — passing depreciation on
a trial balance that has none has to mean exactly that — and the ledger is created,
classified by the code on the entry.

### Binding a trial balance to a period

An import states a period, and the importer preselects it from the financial year in
the file. Once bound, **that period is actual**: its figures come from the ledgers, and
the growth, margin and working-capital assumptions are not applied to it — the cells
for that year go inert on the Assumptions screen. The projection continues from the
actual rather than from a keyed base-sales figure, and carries the deferred tax the
books actually show.

Where the **first** period is bound and the file carried an opening-balance column, the
Opening Balance Sheet screen is not used at all: the position at day one is read from
the file. Two statements of the same thing can only disagree, so the file wins.

Two worked examples open straight from a link: `?demo=tally` has its first period
stated by a Tally import, and `?demo=branches` has two units to consolidate. (The
import screen also has a **Load a two-unit example** button.)

## The proposal

A projection prepared for a bank exists to support a request. **Facilities & Working
Capital** states what that request is: the limits sanctioned today, the limits sought,
the margins the bank stipulates on each class of current asset, and the assessment
that runs from the projected balances to the maximum permissible bank finance on both
Tandon methods. The enhancement is the difference, and the pack says plainly whether
the ask is inside the norms.

The rate on a cash-credit facility is what prices working-capital borrowing throughout
the model, so an overdraft costs what it actually costs and shows up in interest cover.

**Borrowings** models the drawing. A term loan amortises to a schedule; a cash credit
or overdraft revolves inside a limit and is entered by how much of it is expected to
be drawn; a dropline overdraft does both. Any of them can have been taken before the
window opened — enter the date it was drawn and the schedule picks it up wherever it
has got to. A rate and an instalment imply each other, so only one is needed; state
both and the difference is reported rather than silently resolved.

## Squaring the balance sheet

Assets less every other claim leaves one figure, and there are only two places it can
go. **Assumptions → Funding policy** decides which, and the balance sheet screen shows
the working:

- **Bank borrowing takes the strain** — the borrowing is the funding need and cash
  sits at the stated minimum.
- **Cash is the residual** — borrowing is held flat and any shortfall is reported as a
  funding gap.
- **State the borrowing** — the suggestion is offered, year by year, and can be
  overridden. Cash is whatever that leaves, including negative, which is raised as a
  critical issue rather than absorbed.
- **Hold a current ratio** — state the ratio and the borrowing follows from it.

Whichever is chosen, the funding need is still computed and shown beside what was
taken, so an override is a choice made against a stated alternative. The difference
goes to cash and nowhere else, and the resulting current ratio is printed under it.

Two things the last option will tell you rather than fake. Cash and borrowing both
rise one-for-one with a drawing, so **borrowing moves the current ratio towards 1** —
it can never raise it above what the business already carries. And the range is
bounded below by cash reaching nil. Ask for a ratio outside that range and the pack
says so, quotes the ratio the business actually supports at its own funding need, and
notes that only the working-capital cycle can do better.

## Where a period's figures come from

Each period on the **Periods** screen carries a source:

- **Projected** from the drivers.
- **Imported** — a trial balance bound to it.
- **Keyed in** — accounts that are already finalised, entered against the same chart
  of accounts, note by note. A keyed balance sheet is post-closing, so the profit is
  already in reserves and nothing is transferred.

Imported and keyed periods are both *actual*: the assumptions are not applied to them,
and the projection continues from them. Where the first period is actual and nothing
states the position at the start of it, the opening balance sheet is not required —
and not invented: the movements two balance sheets would have forced (capital
expenditure, the owners' account, borrowings, the cash flow) are shown as a dash
rather than derived from nothing.

## Policies and narrative

**Policies & Narrative** carries a library of significant accounting policies — the
standard wording for each of the choices an entity actually makes — which can be
chosen between, reworded, dropped or added to. The narrative that explains a
particular balance is not standard, so for that the screen composes a brief: the
entity, the framework, the figures and the choices already made, as text to hand to
whichever assistant you use.

Nothing is sent anywhere. The brief is text to copy and what comes back is text to
paste, read before it goes near the accounts. A pasted reply can be split into the
notes it names, and every note stays editable afterwards.

## Verifying

```bash
npm test             # 408 engine tests
npm run typecheck    # engine, api and web
npm run build        # engine + api + web
npm run report -- --far --schedules   # the whole pack, printed to the terminal
```

The terminal report takes the same flags as the UI's tabs: `--types`, `--type company`,
`--nbfc`, `--far`, `--schedules`, `--rollover`, `--tb --notes`, `--json`.

## What the engine guarantees

- **No binary floating point on money.** Every calculation goes through `decimal.js`
  at 34 significant digits.
- **No hidden balancing plugs.** Once everything else is fixed there is one figure
  left to place, and it can only go to short-term borrowing or to cash. Capital,
  loans and profit are never quietly adjusted to make a balance sheet close.
- **Presentation is separate from measurement.** Eight report templates (NCE,
  Schedule III Divisions I, II and III) read the same normalized balances, so
  switching framework changes labels and grouping, never a figure.
- **Two depreciation bases.** Schedule II in the books, section 32 blocks for tax —
  and deferred tax measured on the difference between them.
- **Disclosures are computed.** Receivable and payable ageing derive from the
  collection and payment periods, so they reconcile to the balance sheet by
  construction and move when the assumptions move.
