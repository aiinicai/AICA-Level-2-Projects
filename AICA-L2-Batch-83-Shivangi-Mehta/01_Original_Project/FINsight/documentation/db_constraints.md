# FinSight — Database vs Service-Layer Constraint Decisions

Stage 3, review round 2, condition #2. This document records, for every
table, which rules are enforced by the SQLite schema itself and which
are left to the service layer (Stage 5+), and why — so the boundary is
a documented decision, not an accident of who got around to writing
which check first.

## Principle

A constraint goes in the **database** when violating it would corrupt
data in a way no later code could safely interpret (e.g., two "current"
profiles for one engagement, a dangling foreign key, a review status
value nothing in the app recognizes). A rule stays in the **service
layer** when it's about *when* something is required, not *whether the
data is structurally sound* — SQLite's limited conditional-constraint
support (no real `CHECK ... WHERE`-style conditional NOT NULL across
columns) makes it the wrong tool for anything context-dependent, and
over-constraining SQLite for a single-writer, offline desktop app adds
migration friction for little real benefit.

## Enums enforced at the service layer only (not DB CHECK constraints)

All of these are free-text `String` columns at the DB level; the
allowed-values comment lives next to each field in `app/models/*.py`.
Enforcing them as SQLite `CHECK` constraints was considered and rejected
for now: every one of these enums is still actively evolving as later
stages (5 through 16) are built, and a `CHECK` constraint means a schema
migration for every new status value — a worse failure mode (a rejected
insert with a cryptic constraint-name error) than a service-layer
validator giving a clear message. This can be revisited once the enums
are stable (e.g., after Stage 14).

| Table.column | Values |
|---|---|
| engagements.status | DRAFT / IN_PROGRESS / COMPLETED / ARCHIVED |
| entity_profiles.accounting_framework | AS / IND_AS |
| entity_profiles.tax_audit_status | APPLICABLE / NOT_APPLICABLE / REQUIRES_REVIEW |
| applicability.system_suggested_status | YES / NO / REVIEW_REQUIRED |
| applicability.user_confirmed_status | APPLICABLE / NOT_APPLICABLE / REQUIRES_FURTHER_REVIEW |
| uploaded_files.file_type | TB / GL / JE / SALES / PURCHASE / BANK / AR / AP / FIXED_ASSETS / GST / TDS / PRIOR_YEAR / OTHER |
| uploaded_files.upload_status | UPLOADED / MAPPED / VALIDATED / ERROR |
| *_rules.risk_level_default, exceptions.risk_level, queries.risk_level | LOW / MEDIUM / HIGH / CRITICAL |
| *_rules.verification_status | VERIFIED / SOURCE_VERIFICATION_REQUIRED |
| exceptions.module, queries.category | ACCOUNTING / AUDIT / TAX / SEBI |
| exceptions.status | OPEN / UNDER_REVIEW / QUERY_RAISED / RESPONSE_RECEIVED / RESOLVED / REVIEWED_NO_ISSUE / NOT_APPLICABLE / CLOSED |
| queries.status | OPEN / UNDER_REVIEW / QUERY_SENT / RESPONSE_RECEIVED / RESOLVED / CLOSED |
| transactions.dataset_type | TB / GL / JE / SALES / PURCHASE / BANK / AR / AP / FIXED_ASSETS / GST / TDS |
| transactions.payment_mode | CASH / CHEQUE / NEFT_RTGS / UPI / DD / OTHER / UNKNOWN |

## Conditional validation enforced at the service layer

These genuinely can't be expressed as static SQLite constraints because
they depend on the *value* of another column, not just presence:

- `exceptions.status_reason` — required when `status` is
  `REVIEWED_NO_ISSUE` or `NOT_APPLICABLE`, optional otherwise
  (`exception_service.py`, Stage 13).
- `applicability` module unlocking — a Review screen only fully unlocks
  once `user_confirmed_status` is set (Stage 5 UI logic, not a DB rule).
- Tax/SEBI rule execution gating — `rule_runner_service` (Stage 10+)
  must refuse to run any `tax_rules`/`sebi_rules` row where
  `verification_status != VERIFIED`. The new indexes on that column
  (below) make that check cheap; the refusal itself is application
  logic, since SQLite can't "refuse to SELECT."

## Structural constraints added to the database this round

| Table | Constraint | Why it's structural, not a business rule |
|---|---|---|
| `entity_profiles` | `UNIQUE(engagement_id)` | Blueprint D.2 says "one profile per engagement" as a fact about the data model, not a workflow preference — a second row would silently corrupt the applicability engine's single source of truth. |
| `applicability` | `UNIQUE(engagement_id, area)` | Two rows for the same (engagement, area) makes "which is current" undefined — this is a shape problem, not a timing problem. |
| `uploaded_files` | `UNIQUE(engagement_id, checksum)` | Directly implements the field's documented purpose ("duplicate-upload detection", Blueprint D.4). Scoped per engagement — the same file re-uploaded to a *different* engagement isn't a duplicate. NULL checksums never collide under SQLite's NULL-distinct UNIQUE semantics, so this is safe before a checksum is computed. |
| `data_mappings` | `UNIQUE(file_id, source_column)` | A source column mapping to two different target fields simultaneously is not a valid state for any downstream rule to read. |
| `standards` | `UNIQUE(code)` | Two rows both claiming to be "SA 240" is a data-entry error, not two legitimate standards. |
| `audit_assertions` | `UNIQUE(code)` | Already approved in Blueprint Section 2.2 — a closed, fixed vocabulary. |
| `knowledge_base_versions` | `UNIQUE(version_label)` | Two rows both labeled "2026.1" defeats the version label's entire purpose. |
| `audit_rule_assertions` | composite `PRIMARY KEY(rule_id, assertion_id)` | Already approved (Blueprint Section 2.3) — prevents the same assertion being linked to the same rule twice. |
| All FK columns | `FOREIGN KEY ... REFERENCES ...`, enforced via `PRAGMA foreign_keys=ON` at connection time | SQLite does not enforce FKs by default even when declared — this must be turned on per-connection (done in `app/extensions.py`'s engine setup and in every test fixture) or the constraints below are decorative only. |

## Indexes added (performance, not correctness)

Every index below targets a column combination that a named screen in
the approved UI filters or joins by (Blueprint Section E / Section 18 /
Section 19), not a speculative "might be useful later" index:

`uploaded_files(engagement_id)`, `transactions(engagement_id,
dataset_type)`, `fixed_assets(engagement_id)`, `gst_line_items
(engagement_id)`, `gst_line_items(engagement_id, invoice_number)`
(the TAX-GST-009 reconciliation join key), `tds_line_items
(engagement_id)`, `exceptions(engagement_id, status)`, `exceptions
(engagement_id, module)` (the Exception Centre's filter list),
`queries(engagement_id, status)`, `documents(related_exception_id)`,
`documents(related_query_id)`, `audit_log(engagement_id)`,
`tax_rules(verification_status)`, `sebi_rules(verification_status)`
(so rule_runner_service's gating check, above, is cheap).

Deliberately NOT indexed: low-cardinality or rarely-filtered columns
(e.g. `is_active` alone, `risk_level` alone) — SQLite's query planner
gets little benefit from indexing a column with only 3-4 distinct
values on a table this size, and every index is write overhead. This is
the "without over-engineering SQLite" half of condition #2.

## Left nullable/unconstrained — flagged as open decisions, not resolved here

- **`exceptions.rule_id`** — kept nullable. Making it `NOT NULL` would
  structurally forbid ever supporting a manually-created exception with
  no automated rule behind it. Nothing in the approved blueprint rules
  this in or out as a future feature, so this is flagged for your
  decision rather than settled unilaterally in a constraints pass.
- **`transactions.debit_amount` / `credit_amount`** — kept nullable,
  deliberately not "at least one must be non-null." Some real-world GL
  exports populate only one side per row or use a single signed amount;
  a DB constraint here risks rejecting valid client data during
  ingestion (Stage 6/7 territory, not Stage 3's to decide).
- **`entity_profiles.turnover` / materiality fields** — kept nullable.
  Required-at-a-point-in-time is a workflow question (Stage 5: does the
  engagement wizard block "Save" without them?), not a structural one —
  the applicability engine is designed to treat missing turnover as a
  `REVIEW_REQUIRED` signal, not a crash.

## Document <-> Exception/Query relationship (condition #3)

See the dedicated section in the Stage 3 round-2 response for the full
before/after — summarized here for completeness: `exceptions
.supporting_file_id` (a FK to `documents`, allowing at most one document
per exception) was removed. `documents.related_exception_id` and
`documents.related_query_id` (both nullable FKs, already present) are
now the sole ownership direction, giving the intended
one-exception-to-many-documents relationship for free — many `documents`
rows can share one `related_exception_id`. This also happened to resolve
a genuine circular foreign-key dependency between `exceptions` and
`documents` that existed under the old design (each referenced the
other), which was forcing an awkward creation order; the corrected
dependency graph is now a clean DAG: `transactions -> exceptions ->
queries -> documents`.
