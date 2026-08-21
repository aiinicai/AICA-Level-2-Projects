# Schema

Three layers plus child entities (§5). SQLAlchemy 2.x declarative, typed.
Identical models on SQLite and PostgreSQL.

## Layer 1 — masters

| Table | Notes |
|---|---|
| `firm` | One row. Document defaults live here so a firm can restyle output without a code change. |
| `partner` | `membership_no` unique. |
| `user` | Argon2id hash. Role: staff / manager / partner / admin. |
| `client` | **Immutable identity.** `client_code`, `cin`. Never versioned. |
| `client_profile` | **SCD Type 2.** Everything that can change. Partial unique index: one `is_current` row per client. |
| `director`, `kmp` | Effective-dated. Directors are never free text. |
| `banker` | Effective-dated. |

The split between `client` and `client_profile` is the important one. A CIN
never changes; a registered address does, and a document signed before the
move must keep printing the old one.

## Layer 2 — engagement

| Table | Notes |
|---|---|
| `engagement` | Unique on (client, `fy_code`). `profile_id` pins the profile version in force. `rolled_from` self-FK. |
| `field_catalog` | **Generated from the YAML at seed time.** Never hand-maintained. |
| `engagement_response` | EAV, PK (`engagement_id`, `field_key`). Typed columns: `value_text` / `value_num` / `value_date`. |
| `litigation`, `statutory_due`, `ifc_deficiency`, `board_meeting`, `director_change` | Child records for repeating blocks. |

**Why EAV.** The questionnaire changes with every amendment. Fixed columns
would force a migration each year, and a migration is exactly what a manager
adding a clause cannot perform. The cost is that consistency checks live in
application code rather than in constraints — which is why
`app/core/consistency.py` exists and is tested.

**Values are typed, never formatted.** `Decimal("4260000")` is stored;
`"42,60,000"` is produced at render time by `app/core/formatting.py`. The
prototype stored the FY end date as free text and interpolated it verbatim
into 34 sentences.

## Layer 3 — workflow and issuance

| Table | Notes |
|---|---|
| `review_comment` | Threaded via `parent_id`. Resolved comments are marked, never deleted. |
| `document_instance` | **Immutable.** `payload_json` freezes every input; `content_sha256` makes a reprint checkable. Unique on (engagement, doc_type, version). |
| `udin_register` | UDIN as PK, with revocation fields. |
| `audit_log` | Append-only. No ORM helper and no route deletes a row — the absence is the feature. |

## Migrations

`alembic/versions/0001_baseline.py` is deliberately empty: it establishes the
chain. `0002_phase4_schema.py` creates all twenty-one tables. Both directions
have been exercised — `upgrade head` then `downgrade base` runs clean.

SQLite cannot `ALTER` most things in place, so `env.py` sets
`render_as_batch` for SQLite only. The same migration therefore works on
PostgreSQL without a second version.

## Foreign keys

SQLite does not enforce foreign keys unless asked. `app/db.py` sets
`PRAGMA foreign_keys=ON` on every connection, detected from the connecting
driver rather than from a module-level engine — tests and scripts build their
own engines and need the pragma just as much.
