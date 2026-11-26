# Band Baaja Baraati — Wedding Planning, Costing & Customer Management (desktop edition)

Python desktop application (PySide6) for an Indian-wedding planning business in Oman: customers & weddings,
events and guest counts, venues/spaces, vendors with price history, **one central costing engine**,
quotations with immutable versions and PDF output, role-based access control, audit log.
Currency: **OMR, 3 decimals**, exact `Decimal` arithmetic everywhere (no floats).

## Run it

```
pip install -r requirements.txt
python -m weddingplanner          # or run_windows.bat / ./run.sh
```
First start asks you to create the **Super Administrator** (there is no default password). The Super Administrator then
creates the other users under *Administration → Users & permissions*.

Database: SQLite file in `~/.wedding_planner/` by default. For PostgreSQL set `WP_DATABASE_URL`
(see `.env.example`); the schema is created/upgraded automatically with Alembic on start-up
(`alembic upgrade head` also works from the command line). Money columns are native `NUMERIC(18,4)` on PostgreSQL.

## Scope of this first build

| Brief section | Status |
|---|---|
| 4 Roles & access control | **Done** — service-layer enforcement, per-user extra/revoked permissions (matrix below) |
| 5 Customers & weddings | **Done** — auto title "The Wedding Celebrations of [Bride] & [Groom]", multiple weddings per customer |
| 6 Events | **Done** — 10 seeded templates + admin-created types (no schema change); property vs. space; **double-booking prevention** (incl. events running past midnight) |
| 7 Guests | **Done** — 6 independent categories per event, auto total, mismatch validation, revising guests re-quantifies food/venue lines |
| 8 Venues | **Done** — property + spaces, capacities, effective-dated pricing (fixed / per person / per hour / per event / custom) |
| 9 Vendors | **Done** — vendor master, multiple services, append-only price history; changing a price never alters existing costing |
| 10 Food & beverage | **Costing formula done** (guest-category rates + counters); full menu/dietary catalogue **not yet** |
| 11 Decoration | Costed as lines / vendor services; theme list seeded; **package & component catalogue and AI preview not yet** |
| 12 Services | Flexible vendor-service catalogue (one generic table, no per-category tables) → feeds costing |
| 13 Accommodation | **Done** — rooms × nights × rate, extras as separate lines |
| 14 Gifts & invitations | Costable as lines; **catalogues / invitation templates not yet** |
| 15 Costing engine | **Done** — mark-up / gross margin / fixed, 4-level precedence, tax, overrides with approval, full audit |
| 16 Quotation & PDF | **Done** — event-wise table (Decoration / Food & Drinks / Other / Total), details, payment schedule, T&Cs, validity, version |
| 17 Versioning | **Done** — immutable snapshots + SHA-256 integrity check |
| 18 Change-request workflow, payments & expenses tracking | **Not yet** (your brief was cut off at section 18; please send the rest) |
| 2B / 3 Customer portal, Next.js/FastAPI | **Not built** — you chose a desktop-only app. Customers receive the PDF. The engine and services are UI-independent, so a web/mobile front end can be added later |

## Menus, decoration, customer window, payments and expenses (second build)

* **Menus & Decor** page (planner / admin): dishes, **menu packages including cocktail packages**, and decoration options by theme
  and colour scheme with photo galleries. A package's cost per guest is derived from its dishes; applying it to an event
  (Costing tab -> *+ Menu package*) creates ordinary cost lines that follow the guest numbers.
* **Margins**: the same rules as before apply to menus and decoration - Overview tab -> *Margin rules* (wedding / event / category),
  Costing tab -> *Item margin...*, Administration -> *Default margin*. Planners cannot see or change margins unless given the permission.
* **Customer window**: a user with the *Customer (portal)* role (Administration -> Users, linked to a customer) gets a separate,
  colourful window: wedding & events, quotation (selling prices only), venue photos, menus, decorations and "My requests".
  Choices are sent to the planner as requests; the planner approves them under *Customer requests*, which creates the cost lines.
* **Payments** (receipts against the issued quotation, with the VAT component) and **Expenses** (vendor payments planned / paid,
  budget vs actual, cash position and VAT in/out) are on the *Payments & expenses* tab of each wedding. Receipts and expenses are
  never edited - only voided with a reason.

## How pricing works (`weddingplanner/core/costing.py`)

* Mark-up: `selling = cost × (1 + m%)` — Gross margin: `selling = cost ÷ (1 − m%)` (m < 100) — Fixed: `selling = cost + amount`.
* Example: cost 1,000, mark-up 20 % → selling 1,200, profit 200, **gross margin 16.67 %** (mark-up on cost is 20 %). Both are displayed and labelled.
* Precedence (most specific wins, and the winning rule is shown on every line): **Item › Category › Event › Wedding › System default**.
* Rounding: each line is rounded half-up once to 3 dp (cost, selling, tax, final); event and wedding totals are sums of rounded lines, so every printed total re-adds exactly.
* Overrides: reason mandatory; Administrators apply instantly, Planners (if given `pricing.override_request`) create a pending request that an approver accepts. The calculated price is stored alongside and never overwritten; override history is in the internal quotation.
* Vendor/venue prices are *frozen onto the cost line* when selected. Tax rate is frozen per line too.

## What the customer can never see

The customer PDF is built **only** from the customer snapshot, which contains selling prices and nothing else (no cost, vendor, margin,
profit, override, internal notes). This is enforced three ways: the snapshot builder asserts that no forbidden key exists; the PDF
function never receives the internal snapshot; and tests scan the generated PDF text for secrets. Staff screens and service
results are redacted by permission (`costs.view`, `margins.view`) on the server side, not just hidden in the UI.

Note: a user who may see both cost and selling price can derive margin. Planners get `costs.view` by default because they choose
vendor services; revoke it per user (*Revoked role permissions*) if a planner should not see costs.

## Roles (defaults — adjustable per user)

| Permission | Super Administrator | Administrator | Wedding Planner | Finance User |
|---|---|---|---|---|
| `users.manage` — Create users, assign roles and permissions | ✔ |  |  |  |
| `settings.manage` — System settings: tax codes and system default margin | ✔ |  |  |  |
| `audit.view` — View audit log | ✔ | ✔ |  |  |
| `event_types.manage` — Create / edit event types | ✔ | ✔ |  |  |
| `customers.view` — View customers and weddings | ✔ | ✔ | ✔ | ✔ |
| `customers.edit` — Create / edit customers and weddings | ✔ | ✔ | ✔ |  |
| `events.edit` — Create / edit wedding events and guest counts | ✔ | ✔ | ✔ |  |
| `venues.view` — View venues and spaces | ✔ | ✔ | ✔ | ✔ |
| `venues.edit` — Maintain venue master and venue prices | ✔ | ✔ | ✔ |  |
| `vendors.view` — View vendors | ✔ | ✔ | ✔ | ✔ |
| `vendors.edit` — Maintain vendor master and services | ✔ | ✔ | ✔ |  |
| `vendor_prices.view` — View vendor purchase prices (confidential) | ✔ | ✔ | ✔ | ✔ |
| `vendor_prices.edit` — Record vendor price changes | ✔ | ✔ | ✔ |  |
| `costs.view` — View internal costs on cost lines | ✔ | ✔ | ✔ | ✔ |
| `costs.edit` — Add / edit / cancel cost lines | ✔ | ✔ | ✔ |  |
| `margins.view` — View margins and gross profit | ✔ | ✔ |  | ✔ |
| `margins.configure` — Configure margin rules (item/category/event/wedding) | ✔ | ✔ |  |  |
| `pricing.override_request` — Request a selling-price override (needs approval) | ✔ | ✔ | ✔ |  |
| `pricing.override` — Override selling price (auto-approved, reason mandatory) | ✔ | ✔ |  |  |
| `pricing.override_approve` — Approve / reject override requests | ✔ | ✔ |  |  |
| `quotations.view` — View customer quotations | ✔ | ✔ | ✔ | ✔ |
| `quotations.issue` — Issue quotation versions | ✔ | ✔ | ✔ |  |
| `quotations.record_decision` — Record customer approval / rejection | ✔ | ✔ |  |  |
| `quotations.internal_view` — View internal quotation with costs and profitability | ✔ | ✔ |  | ✔ |
| `reports.profitability` — View profitability reports | ✔ | ✔ |  | ✔ |


## Integrity & security

* Passwords: scrypt, salted; strength rules; lock-out after 5 failures for 15 min; no default accounts; no secrets in code (`.env`).
* Issued quotations: ORM guard refuses updates/deletes of frozen columns; a SHA-256 checksum detects edits made directly in the database
  (button *Verify integrity*). Approval is recorded against one specific version; a superseded version cannot be approved.
* Audit log of logins, price changes, margin rules, overrides, quotations, user changes (Administration → Audit log).

## Oman notes — please confirm with your tax adviser

* Default tax code `VAT5` = 5 % standard-rate VAT under the VAT Law, Royal Decree 121/2020 (in force 16 April 2021). Zero-rated/exempt
  treatment of particular items, and hotel tourism levy (reported at 5 % of hotel occupancy) can be added as extra tax codes
  (*Administration → Tax codes*) or entered as `Taxes & Fees` lines. The application does not decide tax treatment for you.
* Customer data is personal data: Personal Data Protection Law, Royal Decree 6/2022 and its Executive Regulations (Ministerial Decision 34/2024).
  Keep the database/backups on company-controlled storage and limit user access (the role model supports this).

## Tests

```
pip install -r requirements-dev.txt
pytest                                   # 52 tests (engine, services/RBAC, PDF, headless GUI flow)
WP_TEST_DATABASE_URL=postgresql+psycopg2://user@localhost/db pytest   # same suite on PostgreSQL (WIPES the public schema)
```
Last run: 52 passed on SQLite and 52 passed on PostgreSQL 16.

## Layout
```
weddingplanner/core/costing.py      central engine (pure Decimal, no DB/UI)
weddingplanner/services/*           business rules + permission checks (what a future API/mobile app would call)
weddingplanner/db/                  models, exact-decimal type, session, Alembic runner
weddingplanner/migrations/          Alembic
weddingplanner/reports/pdf.py       customer & internal PDFs (ReportLab)
weddingplanner/ui/                  PySide6 screens
```

## Windows quick start
1. Install Python 3.11, 3.12 or 3.13 from python.org (tick "Add Python to PATH").
2. Unzip the folder, then **double-click `Band_Baaja_Baraati.py`** (or `run_windows.bat`).
   The first time it installs the needed packages by itself (needs internet, takes a few minutes), then opens the app.
3. If anything goes wrong a message box shows the reason and a log is saved to `.wedding_planner\startup_error.log` in your user folder.


## Sample data and venue photos

The `sample_data/` folder holds 15 CSV files (three venues, 15 sample vendors, three sample weddings) plus `TEST_GUIDE.md`
with expected totals and test scenarios.

1. Sign in as the Super Administrator -> **Administration -> Sample data -> Import sample data...**
2. Photos: run `python fetch_images.py` inside `sample_data` on your own computer (needs internet), then import again.
   You can also add any photo to a venue with **Venues -> Add image...**.

All prices in the sample files are placeholders. The importer is idempotent and uses the normal services, so every validation,
audit-log entry and costing rule applies. Tests: `tests/test_sample_import.py` re-derives the wedding totals independently.
