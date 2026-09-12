# Architecture

## The shape of the problem

A cash tool has three hard parts, and none of them is the dashboard:

1. **Only about 45% of what a CFO needs is in the accounting system.** Tally
   knows the ledger. It does not know which bank balance is lien-marked, what
   has been committed on a purchase order that hasn't been invoiced, what the
   covenant thresholds are, or how likely a given client is to pay.
2. **Numbers have to reconcile across screens.** A 13-week forecast that
   contradicts the runway figure destroys trust in both. This actually happened
   during the build — see "Reconciliation" below.
3. **The tool has to know when not to be trusted**, and say so.

Everything below follows from those three.

---

## Layers

```
  SOURCES                NORMALISATION            STORE
  ─────────              ─────────────            ─────
  Tally Prime  ────┐
  (XML over HTTP)  │
                   ├──▶  adapters/tally.py  ──▶  adapters/normalizer.py  ──▶  SQLite
  Zoho (roadmap)   │     extract                 classify + upsert            40 tables
  CSV   (roadmap) ─┘

  Manual registers ──────────────────────────────────────────────────────▶   (audited:
  (in-app, named person, recorded time)                                        source,
                                                                               created_by,
                                                                               updated_at)
```

```
  ENGINE                                         SURFACES
  ──────                                         ────────
  services/                                      routers/          → REST API + /docs
    common.py      Figure, Ctx, formatting        ├─ tabs.py        one call per screen
    cash.py        position, confidence           ├─ trace.py       drill-down
    burn.py        gross/net/normalised           ├─ registers.py   the manual layer
    runway.py      four scenarios, movement       ├─ scenarios.py
    liquidity.py   score + ratios                 ├─ alerts.py
    receivables.py ageing, weighted, DSO          └─ setup.py
    payables.py    obligations, statutory
    cashcalendar.py 13-week bottom-up            adapters/notifier.py
    variance.py    plan vs actual                  → SMS (Twilio)
    scenarios.py   levers + sensitivity            → n8n (same interface)
    people.py      headcount, hiring impact        → email
    capital.py     facilities, covenants
    boardpack.py   frozen snapshots              frontend/
    narrative.py   the AI commentary               React + Vite + Tailwind
    alertengine.py ten rules                       12 screens
```

---

## Why a common internal schema

The Tally adapter's only job is to turn Tally's XML into plain dictionaries.
The normaliser's only job is to classify those into the internal schema:
which Tally group is cash, which is statutory, which expense ledger belongs to
which of the nine burn categories.

Nothing downstream — not one service, not one screen — knows Tally exists.
Adding Zoho Books means writing `adapters/zoho.py` and extending the
normaliser's classification rules. It means changing no screen and no
calculation.

The normaliser also **reports what it could not classify**. An unmapped ledger
is a data-quality finding, and the sync result names it. Silently defaulting to
"Other" is how a burn breakdown quietly becomes wrong.

---

## Every figure carries its basis

`services/common.py` defines `Figure`: a value, its unit, its status, the
period it covers, the as-on date, a one-line description of how it was worked
out, and a `trace` descriptor.

```python
Figure(
    label="Net Burn / Month",
    value=5_404_312.0,
    unit="inr",
    basis="Net burn, 3-month average, normalised (one-off items excluded)",
    as_on=date(2026, 8, 31),
    status=Status.AMBER,
    sub_line="3-mth average · ↓ 44% vs prior 3 mths",
    trace=trace("burn_entries", entity_id=1, months=3, normalised=True),
)
```

The `trace` descriptor is **data, not a query**. The frontend hands it back to
`GET /api/trace` unchanged and the backend replays it. That is what keeps the
frontend from ever constructing a database query, and what makes "every number
is clickable" a property of the architecture rather than a promise per screen.

---

## Reconciliation

The first working version had the 13-week forecast ending below zero while the
runway figure said seven months. Both were computed correctly from their own
inputs; they disagreed because the forecast had no forward billing in it. Open
invoices run out after about six weeks, so the grid showed a company that stops
invoicing but keeps paying salaries.

The fix is in `cashcalendar.build_forecast`: for each month in the horizon, the
named open items are totalled and compared against the actual monthly run-rate,
and the shortfall is spread across that month's weeks. Named items dominate the
near weeks; the run-rate takes over as they thin out. The forecast's monthly net
therefore reconciles to net burn **by construction**, and every topped-up rupee
is marked estimated rather than contracted — so week confidence falls away
exactly where the certainty does.

Two related defects were found the same way and are worth recording:

- The forecast was re-forecasting the as-on month's payroll, which had already
  been paid, double-counting a month of people cost.
- `runway_movement` used total cash where the headline runway used unrestricted
  cash, so the waterfall and the number above it were computed on different
  numerators.

Reconciliation between screens is not a nice-to-have in a tool like this. It is
the thing that makes it usable at all.

---

## The AI agent's job

Exactly one thing: read a structured pack of already-computed,
already-formatted facts and write four to six sentences about them.

It never computes. It never receives a raw number it could restate wrongly —
every value in the prompt is pre-formatted text like `"₹ 54.04 L"`. And there
is a deterministic narrator behind it that produces the same shape of paragraph
from the same facts, so the screen works with no API key, no network, and no
error state.

When confidence is Low, the box suppresses itself and renders only the data
gaps. That was an explicit instruction: *"I'd rather have silence than
confident narration on bad data."*

---

## The alert engine

Ten rules, each a function of `(Ctx, AlertRule)` returning either `None` or a
description of the hit. Every rule calls the same services the screens call, so
an alert can never assert something a tab contradicts.

The delivery rules live in the engine, not the sender:

- **Cooldown** — a rule that has fired recently will not fire again.
- **Duplicate suppression** — no second alert while one for the same rule is open.
- **Quiet hours** — the alert is still *recorded*; only the message is held.
- **Escalation** — an unacknowledged alert past its window goes to the escalation contact.

`evaluate_rules()` returns what fired **and what was suppressed and why**, which
is what makes Tab 11's performance panel possible.

Delivery sits behind one interface with three implementations: Twilio SMS
Cloud API (the default), an n8n webhook, and console. Every attempt is recorded
in `alert_deliveries` whether it succeeded or not, because Tab 11 asks
"Delivered? Read?" and sometimes the honest answer is no.

---

## Roles

A simple login gate, deliberately — not commercial licensing. But roles matter:

| Role | Can |
|---|---|
| Admin | Everything, including user administration |
| CFO | Everything except users; can approve plans |
| Finance | Enter and edit; cannot approve plans |
| Board Read-Only | Read every screen, change nothing |

`require_write` and `require_approver` are FastAPI dependencies, so read-only
enforcement is structural rather than per-handler. Marking a plan board-approved
needs a **second, different** approver — the one action the CFO said is not a
solo click.

---

## Data model

40 tables. The parts worth calling out:

- **`Provenance` mixin** — `source`, `created_by`, `created_at`, `updated_by`,
  `updated_at` on every row a human can enter. This is what makes Setup's
  Manual Entries Register a query rather than a separate table.
- **`LedgerEntry.cash_amount`** — one signed column for the cash view, so burn,
  runway and the calendar all read the same field rather than each deriving
  cash from debits and credits their own way.
- **`is_one_off` + `classified_by`** — normalised burn is only trustworthy if
  you can see what was excluded and who excluded it.
- **`BoardPack.snapshot`** — the whole computed payload as JSON at generation
  time. A pack is never recomputed, so December's pack still says what it said
  in December.
- **`ForecastSnapshot`** — what was forecast for a week, stored when it was
  forecast, so Tab 6 can state its own accuracy without hindsight.

---

## Testing

`backend/smoke_test.py` runs against the real app through `TestClient`: signs
in, refuses an unauthenticated request, exercises every read endpoint, every
drill-down kind, the scenario engine, a dry-run of the alert engine, the plan
template download, a write plus its activity-log entry, board-pack generation
and read-back, and finally that Board Read-Only is refused on writes and served
on reads.

The frontend was verified by driving it with Playwright across all twelve
screens and every sub-tab, checking for console errors and reading the rendered
screenshots — which is how the reconciliation defects above were found. A build
that compiles says nothing about whether the screens are right.
