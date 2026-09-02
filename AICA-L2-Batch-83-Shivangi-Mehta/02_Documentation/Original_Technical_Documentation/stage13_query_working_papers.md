# Stage 13 — Query & Working Papers Centre: Completion Report

Status: **complete, awaiting your review and approval.** Per your closing
instruction, FinSight does not proceed to Stage 14 (or Stage 15/16/17/18/19)
until you approve this report.

---

## 1. Files changed

**New files:**

- `database/migrations/versions/0003_query_reviewer_editing_and_evidence.py` — the approved migration.
- `app/services/query_service.py` — all Stage 13 logic (Working Paper assembly, reviewer actions, audit logging, Query Centre listing/filtering/summary).
- `frontend/templates/queries/index.html` — the Query Centre.
- `frontend/templates/exceptions/working_paper.html` — the Working Paper screen.
- `tests/unit/test_query_service.py` (27 tests)
- `tests/test_query_working_papers_http.py` (16 tests)
- `documentation/stage13_query_working_papers.md` (this report)

**Modified files:**

- `app/models/queries.py` — added the three approved nullable columns (`QueryRecord.reviewer_query_text`; `QueryResponse.evidence_description`, `.evidence_reference`).
- `app/api/exceptions_bp.py` — real routes: `/exceptions/` (renders the Query Centre directly — see section 11's note on why this isn't a redirect) and `/exceptions/<id>/` (the real Working Paper, GET + POST).
- `app/api/queries_bp.py` — real route: `/queries/` (the Query Centre, GET with filters).
- `frontend/templates/base.html` — added one sidebar link ("Query & Working Papers") under the existing Review nav group.
- `frontend/templates/review/finding_detail.html` — added an "Open Working Paper" link (Stage 12/13 integration, per your section 16).
- `database/seed/_sandbox_migration_harness.py` — extended to load and run `0003` after `0001`/`0002` (upgrade and downgrade), same pattern Stage 9 used to add `0002`.

**Files deliberately NOT touched:** every file under `app/rules/accounting/`, `app/rules/audit/`, `app/rules/tax/`, `app/rules/sebi/`; `app/services/accounting_review_service.py`, `app/services/audit_review_service.py`, `app/services/tax_review_service.py`, `app/services/unified_review_service.py`, `app/services/rule_runner_service.py`; `app/models/exceptions.py` (no change — `ExceptionRecord` already had every field Stage 13 needed); every Stage 8/9/10/12 template.

## 2. Migration details

`0003_query_reviewer_editing_and_evidence.py`, hand-authored in the exact style of `0001`/`0002` (the sandbox still cannot install Alembic — same disclosed, pre-existing environment gap as every prior stage). Adds three nullable columns, purely additive:

```
op.add_column("queries", sa.Column("reviewer_query_text", sa.String, nullable=True))
op.add_column("query_responses", sa.Column("evidence_description", sa.String, nullable=True))
op.add_column("query_responses", sa.Column("evidence_reference", sa.String, nullable=True))
```

Verified against a real, on-disk SQLite database via
`database/seed/_sandbox_migration_harness.py` (extended this stage —
see actual output in section 10). No table was created or dropped, no
foreign key was added, no existing column's type or nullability
changed, no data migrated or transformed.

## 3. Database schema after migration

`queries` (13 → 14 columns): `query_id`, `engagement_id`, `exception_id`,
`category`, `area`, `observation`, `question_text`, `required_document`,
`reference`, `risk_level`, `status`, `is_ai_drafted`, `created_at`,
**`reviewer_query_text` (new)**.

`query_responses` (5 → 7 columns): `response_id`, `query_id`,
`management_response`, `reviewer_comments`, `resolution`,
`responded_at`, **`evidence_description` (new)**, **`evidence_reference` (new)**.

Every other table is unchanged. Total table count remains 24.

## 4. Query Centre

`GET /queries/` — lists every `QueryRecord` for the current engagement
joined with its `ExceptionRecord` and latest `QueryResponse`
(`app/services/query_service.list_queries()`). Per query: Query ID,
Finding ID, Module, Rule ID, effective query text (reviewer-edited if
present, else the original), Finding Status (with its reviewer-facing
conclusion label), Query Status (shown separately — see section 6),
Risk, Created date, a derived Last Updated date, and a link to the
Working Paper. Filters: Module, Finding Status, Risk, Rule ID, and a
free-text Search across Query ID / Finding ID / Rule ID / query text.
A summary panel (Total + per-module + per-status counts) is computed
live from `query_summary()` — nothing hard-coded.

## 5. Working Paper workflow

`GET/POST /exceptions/<exception_id>/` — the single-screen structure
your instruction laid out: Engagement/Module/Finding/Rule/Risk header,
Why FinSight Flagged This, Applicable Reference, FinSight Suggested
Query (read-only), Reviewer Query (editable), Reviewer, Document/
Evidence Requested, Response, Evidence (description + reference),
Reviewer Notes, Reviewer Conclusion (status + required-reason
explanation), and an Audit Trail. One POST saves the whole form;
`query_service.update_working_paper()` applies each field-group as an
independent, individually-audited update (see section 8) — nothing is
saved atomically-or-not-at-all as a single blob, so the audit trail
reads as a real changelog, not one opaque "form saved" entry.

## 6. Status lifecycle

Two status fields, kept independent exactly as you approved:

- **`ExceptionRecord.status`** (8 values, unchanged from the approved
  model) is the one Stage 13 actually manages. Reviewer-facing
  "conclusion" labels are a pure display mapping, never a second stored
  value: `RESOLVED` → "Confirmed", `REVIEWED_NO_ISSUE` → "Cleared",
  `NOT_APPLICABLE` → "Not Applicable", `UNDER_REVIEW` → "Further Review
  Required" (`query_service.CONCLUSION_LABELS`). `status_reason` is now
  enforced as required for `REVIEWED_NO_ISSUE`/`NOT_APPLICABLE` —
  `StatusReasonRequiredError` blocks the save entirely (nothing is
  written) if it's blank, and the Working Paper screen shows the
  rejection instead of a silent no-op.
- **`QueryRecord.status`** is displayed (its own column in both the
  Query Centre and, implicitly, unaffected on the Working Paper) but
  never written by anything in Stage 13 — it stays `"OPEN"` on every
  row, exactly as every prior stage left it. The Query Centre labels
  this column "Query Status" and the finding's column "Finding Status"
  side by side, so the two are visually distinguishable rather than
  conflated.

## 7. Evidence workflow

`QueryRecord.required_document` (existing, previously unused) is now
displayed as "Document / Evidence Requested." `QueryResponse.
evidence_description` and `.evidence_reference` (new) record what was
actually received and a plain local file name/path/reference number.
No document is uploaded, moved, stored, or managed by FinSight —
`evidence_reference` is free text the reviewer types in, exactly as
your instruction specified ("do NOT build a full document-management
system"). `reviewer_comments` and `resolution` were never used as
substitutes for these two fields, per your explicit instruction.

## 8. Audit trail approach

`AuditLog` (Stage 3 schema, unused anywhere in the codebase until this
stage) now records, per your minimum list: `QUERY_TEXT_EDITED`,
`RESPONSE_ADDED`/`RESPONSE_UPDATED`, `EVIDENCE_ADDED`/`EVIDENCE_UPDATED`,
`REVIEWER_NOTES_CHANGED`, `STATUS_CHANGED` (and `STATUS_REASON_CHANGED`
if only the reason is edited without a status change), `REVIEWER_ASSIGNED`.
Every entry uses `entity_affected = "exceptions.<exception_id>"` so a
working paper's full history is one query away
(`query_service.get_audit_trail()`), is scoped to `engagement_id`, and
stores an old/new value pair (plus, for `QUERY_TEXT_EDITED`, an explicit
`original_question_text_unchanged` field) in `detail_json`. A save that
doesn't actually change a field's value writes no audit entry — verified
by `test_audit_log_does_not_record_a_no_op_save`. No second audit-log
table or mechanism was created.

## 9. Re-run preservation

No new preservation logic was written for Stage 13 — none was needed.
Because a reviewer-touched exception's `status` is no longer `"OPEN"`
(or it has `reviewer_notes`/`status_reason` set), Stage 8/9/10's
existing `_clear_stale_automated_exceptions()` already leaves it alone
on the next review run, exactly as it was built to do since Stage 8.
`reviewer_query_text`, the response, and the evidence fields all live
on rows (`QueryRecord`/`QueryResponse`) that a preserved `ExceptionRecord`
keeps pointing at, so they survive automatically too. Verified end-to-end
by `test_rerunning_review_does_not_erase_reviewer_work`.

## 10. Privacy confirmation

No network call of any kind was added. `query_service.py` and the two
blueprint files import only from `app.services.*`, `app.models.*`, and
the standard library. No OpenAI/Claude/Gemini/Perplexity SDK, no cloud
database or storage client, no email API, no telemetry. Evidence
recording is a plain text field, never a file upload or transfer.

## 11. Tests and actual test results

24 required test areas from your instruction, all covered (27 unit
tests in `tests/unit/test_query_service.py`, 16 HTTP tests in
`tests/test_query_working_papers_http.py`, 43 total) plus the 14
additional schema-specific tests from your approval message:

| Your requirement | Test(s) |
|---|---|
| Query Centre loads existing queries | `test_query_centre_loads_existing_queries`, `test_query_centre_lists_query_after_a_review_run` |
| Query links to correct finding | `test_query_links_to_correct_finding` |
| Tax/Audit/Accounting query displayed correctly | `test_tax_query_displayed_correctly` (Audit/Accounting exercised identically in Stage 12's own suite; module-agnostic display code shared) |
| Filters / search work | `test_query_filters_work`, `test_query_search_works`, `test_query_centre_filters_by_module`, `test_query_centre_search_works` |
| Reviewer can open a working paper | `test_reviewer_can_open_a_working_paper`, `test_working_paper_shows_original_finding_and_suggested_query` |
| Reviewer can add notes / record response / evidence / conclusion / change status | `test_reviewer_can_add_notes`, `test_reviewer_can_record_response`, `test_reviewer_can_record_evidence_reference`, `test_reviewer_can_record_conclusion_and_change_status`, `test_working_paper_post_saves_reviewer_edits` |
| Original automated finding remains unchanged | `test_original_automated_finding_remains_unchanged`, `test_original_finding_remains_unchanged_after_full_workflow` |
| Reviewer-edited query preserved separately | `test_reviewer_edited_query_is_preserved_separately_from_original` |
| Existing QueryRecord not duplicated | `test_no_duplicate_query_record_is_created_by_working_paper_edits`, `test_evidence_upsert_does_not_create_a_second_response_row` |
| Re-running review doesn't erase reviewer work | `test_rerunning_review_does_not_erase_reviewer_work` |
| Working paper stays linked to original finding | `test_finding_detail_links_to_working_paper`, `test_working_paper_links_back_to_finding_detail` |
| Local evidence reference stays local | `test_reviewer_can_record_evidence_reference` (plain text field, no upload path exercised or possible) |
| No external API/cloud call introduced | confirmed by code inspection (section 10); no test can positively prove a network call's absence, so this is a design/import-level guarantee, not a runtime-tested one |
| Accounting/Audit/Tax rule logic unchanged | full existing Stage 8/9/10 suites re-run unchanged (section 12) |
| Stage 12 Unified Findings Centre continues to work | `test_stage12_findings_centre_continues_to_work` |
| SEBI remains unavailable | `test_sebi_has_no_working_paper_or_query_centre_route` |
| **Schema-specific (your approval message):** | |
| Original `question_text` unchanged after reviewer edits | `test_reviewer_edited_query_is_preserved_separately_from_original`, `test_working_paper_post_saves_reviewer_edits` |
| `reviewer_query_text` stores the edit | same |
| Existing queries with NULL `reviewer_query_text` continue to work | `test_existing_query_with_null_reviewer_query_text_continues_to_work` |
| Evidence description/reference can be saved | `test_reviewer_can_record_evidence_reference` |
| Existing `QueryResponse` rows with NULL evidence fields continue to work | `test_existing_query_response_with_null_evidence_fields_continues_to_work` |
| `REVIEWED_NO_ISSUE`/`NOT_APPLICABLE` cannot be saved without a reason | `test_reviewed_no_issue_cannot_be_saved_without_status_reason`, `test_not_applicable_cannot_be_saved_without_status_reason`, `test_reviewed_no_issue_without_reason_shows_error_and_does_not_save` |
| `RESOLVED` can be saved appropriately | `test_resolved_can_be_saved_without_special_handling` |
| `QueryRecord.status` / `ExceptionRecord.status` stay independent | `test_query_record_status_remains_independent_of_exception_status` |
| `AuditLog` records reviewer changes | `test_audit_log_records_reviewer_changes`, `test_audit_log_does_not_record_a_no_op_save`, `test_working_paper_shows_audit_trail_after_edits` |
| No duplicate `QueryRecord` when one already exists | `test_no_duplicate_query_record_is_created_by_working_paper_edits` |

**Actual results**, run inside the sandbox test environment exactly as
every prior stage's results in this project (`PYTHONPATH=/tmp/shim_site
/tmp/testenv/bin/python -m pytest`):

```
tests/unit/test_query_service.py — 27 passed
tests/test_query_working_papers_http.py — 16 passed
```

**Migration verification** (`database/seed/_sandbox_migration_harness.py`,
run with a plain system Python — the same substitute used for every
prior migration since Alembic can't be installed here):

```
Tables created by migration.upgrade(): 24
Column comparison across 24 tables: All tables' columns match exactly between migration and models.
'reviewer_query_text' present in queries table after 0003: True (must be True)
'evidence_description' present in query_responses table after 0003: True (must be True)
'evidence_reference' present in query_responses table after 0003: True (must be True)
Stage 13 columns removed after 0003 downgrade(): True (must be True)
HARNESS_VERIFICATION_PASSED
```

**Full project suite** (`pytest tests/ --ignore=tests/unit/test_models.py`):

```
555 passed, 2 failed, 71 warnings
```

The 2 failures are the same pre-existing, environment-only
`ModuleNotFoundError: No module named 'alembic'` in
`tests/unit/test_migration.py`, disclosed at the end of every prior
stage — unrelated to any Stage 13 change (the DDL itself was
independently verified via the harness above, not via this test).
`tests/unit/test_models.py` still fails to collect for the same
pre-existing `sqlalchemy.exc` shim gap, also unrelated — note that its
existing `QueryRecord(...)`/`QueryResponse(...)` constructions don't
pass the three new columns at all, which is exactly the "NULL by
default, nothing breaks" behavior this stage relies on.

Baseline reconciliation: Stage 12's end-of-stage baseline was 512
passed / 2 failed / 1 collection error. Stage 13 adds 43 new tests
(27 + 16): 512 + 43 = **555 passed** — exactly matches. **One
pre-existing test was intentionally changed, disclosed here rather than
silently**: `tests/test_app_factory.py::test_all_nav_pages_load` (Stage
2) asserts every nav path returns exactly 200. Making `/exceptions/`
redirect to `/queries/` would have turned that assertion into a 302 and
broken this pre-existing test; instead, `/exceptions/` now renders the
Query Centre's own view function directly (still 200, no duplicate
template, no redirect) — see section 4/5's routes. This test file
itself required no edit at all once that route decision was made; it
still passes unchanged.

I am not claiming the alembic or `test_models.py` issues are resolved —
both remain the same open, pre-existing, sandbox-only environment gaps
disclosed since Stage 3/8.

## 12. Regression check — Accounting/Audit/Tax/Stage 12 suites

Re-run unchanged as part of the full suite above: all of
`tests/unit/test_accounting_review_service.py`,
`tests/unit/test_audit_review_service.py`,
`tests/unit/test_tax_review_service.py`,
`tests/unit/test_unified_review_service.py`,
`tests/test_accounting_http.py`, `tests/test_audit_http.py`,
`tests/test_tax_http.py`, `tests/test_review_http.py` pass with zero
modifications — no rule, threshold, provision, SA reference, or
applicability logic was touched.

## 13. Limitations

- **`QueryRecord.status` stays permanently inert in V1.** Nothing
  transitions it — it will read `"OPEN"` forever unless a future stage
  is explicitly asked to activate it. This is intentional (your
  instruction), not an oversight, but worth restating plainly.
- **No document management.** `evidence_reference` is an unvalidated
  text field — FinSight never checks that the path exists, never opens
  it, never stores a copy. If the reviewer's local file moves or is
  renamed, the reference silently goes stale; nothing in this stage
  detects that.
- **No user/reviewer authentication exists yet.** "Reviewer"
  (`assigned_to`) and `AuditLog.performed_by` are free-text fields the
  reviewer types in themselves — there's no login system to derive a
  real identity from. `performed_by` is left `None` when the field is
  blank, which will be common for a single-reviewer local install.
- **"Last Updated" on the Query Centre is derived, not stored** — the
  latest of the query's `created_at`, its response's `responded_at`, and
  the exception's `resolved_at`. No `updated_at` column was added (not
  part of the approved schema proposal), so this is an honest
  approximation, not a tracked field.

## 14. Decisions requiring your review (none require the schema-STOP gate — already resolved — but worth surfacing)

1. **`/exceptions/` renders the Query Centre directly rather than
   redirecting** — see section 11's baseline-reconciliation note. Happy
   to change this if you'd rather it be a genuinely separate screen.
2. **One combined "Save Working Paper" submit**, not eight separate
   save buttons per capability listed in your section 7. The service
   layer still logs each changed field-group as its own audit entry
   internally (section 8), but the UI is one form. I judged this more
   professional/less cluttered; can be split into per-section saves if
   you'd prefer.
3. **`required_document` is currently read-only in the UI** (displayed,
   not editable) — no rule module populates it today (same situation as
   Stage 12's disclosed `related_transaction_id` gap), so there's
   nothing to show but "—" in practice yet. I didn't add editing for it
   since your instruction listed it as something to *reuse*, not
   extend; let me know if you'd like the reviewer able to set it
   directly from the Working Paper.
