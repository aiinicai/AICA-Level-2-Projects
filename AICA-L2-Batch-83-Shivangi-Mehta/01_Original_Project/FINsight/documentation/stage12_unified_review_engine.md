# Stage 12 — Unified Review Engine: Completion Report

Status: **complete, awaiting your review and approval.** Per your closing
instruction, FinSight does not proceed to Stage 13 or any later stage
(Query & Working Papers, Final UX, LAN mode, EXE packaging, or anything
else) until you approve this report.

This report covers all 15 items your instruction required, plus actual
test results.

---

## 1. Architecture

Stage 12 adds a **thin orchestration layer** above the three already-
approved, already-implemented engines — exactly the shape your
instruction specified:

```
FinSight
    |
Review Orchestrator (app/services/unified_review_service.py)
    |
    +-- Accounting Review Engine (unchanged, Stage 8)
    +-- Audit Review Engine      (unchanged, Stage 9)
    +-- Tax Review Engine        (unchanged, Stage 10)
    |
Unified Findings Centre (app/api/review_bp.py + frontend/templates/review/)
    |
Query / Working Paper Centre (existing QueryRecord data, Stage 14 UI not yet built)
    |
Reports (Stage 14+, not yet built)
```

The orchestrator does not call any rule module, any
`rule_runner_service.run_*` function, or construct any `ExceptionRecord`/
`QueryRecord` directly. It calls exactly four kinds of things, all
pre-existing:

- Each engine's own `preview_*_review(engagement_id)` / `run_*_review(engagement_id)`.
- Each engine's own precondition exception classes (caught, never re-thrown as something else).
- `upload_service.list_uploads()` (for the new readiness gate — see section 5).
- Each engine's own `get_last_review_results()` / rule-lookup helpers (for finding normalization — see section 9).

Two genuinely new pieces of logic exist, and only two — both
orchestration behavior, not rule content:

1. **The readiness gate** (`check_review_readiness()`) — new, because
   nothing in the codebase enforced "the whole engagement's data
   mapping and validation must be complete" before today. Each
   individual engine screen still behaves exactly as before (a live
   preview against whatever validated data currently exists, however
   partial); only the new unified "Run Review" workflow refuses to
   execute at all until every uploaded file for the engagement is
   VALIDATED.
2. **Finding normalization** (`NormalizedFinding` / `get_unified_findings()`)
   — a read-only presentation layer over the three engines' own
   `get_last_review_results()`, for the Unified Findings Centre.

## 2. Files changed

**New files:**

- `app/services/unified_review_service.py` — the orchestrator (readiness gate, preview/run dispatch with per-module error isolation, finding normalization, dashboard summary).
- `app/api/review_bp.py` — three routes: `/review/` (Configuration + Run + Result Summary), `/review/findings` (Findings Centre), `/review/findings/<module>/<finding_id>` (Finding Detail).
- `frontend/templates/review/configure.html`
- `frontend/templates/review/findings.html`
- `frontend/templates/review/finding_detail.html`
- `tests/unit/test_unified_review_service.py` (26 tests)
- `tests/test_review_http.py` (16 tests)
- `documentation/stage12_unified_review_engine.md` (this report)

**Modified files:**

- `app/__init__.py` — registered `review_bp` alongside the other blueprints.
- `frontend/templates/base.html` — added two sidebar links ("Run Review", "Findings Centre") under the existing "Review" nav group, above the three unchanged engine links.
- `documentation/architecture.md` — Stage 12 addendum appended.

**Files deliberately NOT touched:** every file under `app/rules/accounting/`,
`app/rules/audit/`, `app/rules/tax/`, `app/rules/sebi/`; `app/services/
accounting_review_service.py`, `app/services/audit_review_service.py`,
`app/services/tax_review_service.py`, `app/services/rule_runner_service.py`,
`app/services/dataset_service.py`; `app/api/accounting_bp.py`, `app/api/
audit_bp.py`, `app/api/tax_bp.py`, `app/api/sebi_bp.py`; every model file;
every existing template outside `frontend/templates/review/`.

## 3. Services reused (never duplicated)

`accounting_review_service.preview_accounting_review()` /
`.run_accounting_review()` / `.get_last_review_results()`;
`audit_review_service.preview_audit_review()` / `.run_audit_review()` /
`.get_last_review_results()` / `.get_audit_rules_by_id()`;
`tax_review_service.preview_tax_review()` / `.run_tax_review()` /
`.get_last_review_results()` / `.get_tax_rules_by_id()`;
`rule_runner_service.get_standards_by_id()` / `.list_all_accounting_rules()`;
`upload_service.list_uploads()`; `engagement_service.get_engagement()` /
`.get_current_engagement()`. Every re-run/reviewer-preservation decision
(what's cleared, what's preserved, what counts as a duplicate) is made
entirely inside each engine's own `run_*_review()` — the orchestrator
never inspects or second-guesses it.

## 4. New services created

Exactly one: `unified_review_service.py` (see section 1). No new rule
module, no new persistence service.

## 5. Database changes

**None.** No migration was created or is needed. This was evaluated
carefully per your explicit instruction (a "Review Execution Record"
requires a 5-point proposal and your approval before implementing, with
a strong preference for reusing existing tables):

- **Evaluation:** a persisted "Review Execution Record" would record
  which modules were run, when, and with what result. I checked
  `app/models/risk.py` (`RiskScore` — schema only, no execution-history
  shape) and `app/models/system.py` (`AuditLog` — a generic
  engagement-scoped action/detail log that could technically hold this,
  but would repurpose a table meant for FinSight's own meta-audit trail
  for a different purpose). Concluded: **no new schema is needed at
  all.** `UnifiedReviewSummary` (the run's own result — which modules
  ran, their status, findings recorded/preserved) is a plain in-memory
  object returned to the Result Summary screen for that one request; it
  does not need to persist across sessions, because the durable half of
  a review's outcome — the findings themselves — is already fully
  captured by each engine's own `ExceptionRecord` + `QueryRecord` rows,
  which is what the Findings Centre actually reads. If you want a
  persisted "review was run on this date, by these modules" history
  later, that is a genuine new capability (not something this
  instruction asked for) and I would raise it as its own proposal at
  that time.
- **Conclusion: no STOP was triggered**, because no schema change was
  ultimately needed.

## 6. API changes

Three new routes, all under the new `review_bp` blueprint (`GET/POST
/review/`, `GET /review/findings`, `GET /review/findings/<module>/
<finding_id>`). No existing route's behavior changed — `/review/
accounting/`, `/review/audit/`, `/review/tax/` all still work exactly as
before (verified by `test_individual_engine_screens_still_work_directly`).

## 7. UI changes

Two new sidebar links ("Run Review", "Findings Centre") in the existing
"Review" nav group, above the unchanged Accounting/Audit/Tax links —
professionals are not required to visit the three engines separately,
but can still do so directly if they choose. Three new screens (Review
Configuration/Run/Result Summary; Unified Findings Centre with filters;
Finding Detail), built entirely from the existing design system classes
(`fs-panel`, `fs-table`, `fs-badge`, `fs-empty-banner`, `fs-form-actions`,
`fs-checkbox-field`) — no new CSS was added.

## 8. Finding normalization approach

`NormalizedFinding` is a common envelope (`module`, `finding_id`,
`rule_id`, `title`, `risk_level`, `status`, `trigger_condition`,
`explanation`, `reference`, `suggested_query`, `suggested_evidence`,
`data_sources`, `related_transaction_id`) plus a `module_fields` dict
that preserves everything module-specific without forcing shared
terminology:

- **Accounting:** `framework`, `standard_code`, `suggested_action`.
- **Audit:** `audit_area`, `assertions`, `suggested_audit_procedure`.
- **Tax:** `legislative_act`, `applicable_from_ay`, `suggested_action`.

`title` is populated from each rule's existing `topic` field (already
present on every rule catalogue row) — never invented text. No approved
wording (labels, explanations, trigger text) is altered anywhere in this
layer; `explanation`/`trigger_condition` are read verbatim from the
already-persisted `ExceptionRecord`.

**Two disclosed, honest gaps, not silently worked around:**

- `suggested_evidence` is only genuinely populated for **Audit**
  findings — that's the only one of the three rule catalogues with a
  `suggested_evidence` column (Stage 9 Decision A). Accounting and Tax
  findings show it as empty (`—`) rather than substituting a different
  field under the same label.
- **Limitation** — none of the three approved rule catalogues
  (`AccountingRule`, `AuditRule`, `TaxRule`) carries a dedicated
  "limitation" text column (only the unused `SebiRule` model has one).
  The Finding Detail page says so plainly rather than inventing content
  or repurposing an unrelated field to fill the slot.

## 9. Query integration approach

Each engine already creates exactly one `QueryRecord` linked to its
`ExceptionRecord` at persist time (Stage 8/9/10, unchanged). The Unified
Findings Centre reads that existing `QueryRecord.question_text` as
`suggested_query` — it never creates a second query merely to power the
unified display, and re-running never duplicates it
(`test_queries_are_linked_once_per_finding_even_after_repeated_runs`).
There is no separate Query Centre screen yet (`queries_bp.py` is still
the Stage-14 placeholder) — the Unified Findings Centre links to the
same underlying query data each individual engine's own "Persisted
Exceptions" table already shows, it does not build a new query
management UI.

## 10. Error handling / error isolation

`_execute()` in `unified_review_service.py` runs each selected module
inside its own `try/except`:

- A module's own documented precondition (e.g. `AccountingFrameworkNotSetError`,
  `ActEraNotSupportedError`) is caught and reported as **BLOCKED**, distinct
  from a genuine failure.
- Any other exception is caught and reported as **FAILED**, and does
  not stop the loop — the remaining selected modules still run, and any
  module that already completed keeps its result.
- `UnifiedReviewSummary.any_failed` / `.any_blocked` / `.all_completed`
  give the Result Summary screen an honest, per-module picture — there
  is no single "success" flag that could be true while a module actually
  failed. Verified directly by
  `test_one_module_failing_unexpectedly_does_not_prevent_the_others_from_running`
  (a simulated Audit failure via monkeypatch; Accounting and Tax still
  complete and persist).

## 11. Re-run behaviour

Entirely delegated. `run_unified_review()` calls each engine's own
`run_*_review()`, which independently runs its own established
`_clear_stale_automated_exceptions()` / `_preserved_finding_keys()`
logic (Stage 8/9/10, unchanged). The orchestrator adds no re-run logic
of its own — verified by `test_rerunning_with_unchanged_data_does_not_pile_up_duplicates`
and `test_reviewer_touched_finding_is_preserved_across_a_unified_rerun`.

## 12. Privacy / offline confirmation

No network call of any kind was added. `unified_review_service.py` and
`review_bp.py` import only from `app.services.*` and standard library —
no `requests`/`httpx`/`urllib` usage, no OpenAI/Claude/Gemini/Perplexity
SDK, no cloud database or storage client, no telemetry. AI was not used
or required anywhere in Stage 12, consistent with your instruction.

## 13. Test cases

21 required test areas, all covered (26 unit tests in
`tests/unit/test_unified_review_service.py`, 16 HTTP tests in
`tests/test_review_http.py`, 42 total):

| # | Requirement | Test(s) |
|---|---|---|
| 1 | Accounting-only review | `test_accounting_only_review_runs_only_accounting` |
| 2 | Audit-only review | `test_audit_only_review_runs_only_audit` |
| 3 | Tax-only review | `test_tax_only_review_runs_only_tax` |
| 4 | All-three review | `test_all_three_modules_run_together_and_all_default_selected` |
| 5 | Blocked before validation | `test_review_blocked_when_no_files_uploaded_at_all`, `test_review_blocked_with_exact_required_message_before_any_upload` |
| 6 | Blocked before mapping/validation complete | `test_review_blocked_when_a_file_is_uploaded_but_not_yet_validated`, `test_review_blocked_shows_upload_status_table_when_a_file_is_not_yet_validated`, `test_post_run_review_refuses_to_run_when_not_ready` |
| 7 | Accounting framework filtering reused correctly | `test_accounting_framework_selection_is_reused_from_the_existing_engine` |
| 8 | Tax FY/AY applicability reused correctly | `test_tax_act_era_precondition_is_reused_and_reported_as_blocked_not_failed`, `test_tax_act_era_precondition_reported_per_module_when_data_is_ready` |
| 9 | Preview doesn't persist | `test_preview_does_not_persist_anything` |
| 10 | Run persists | `test_run_persists_across_all_three_modules`, `test_running_all_three_modules_persists_and_shows_result_summary` |
| 11 | Re-run doesn't create inappropriate duplicates | `test_rerunning_with_unchanged_data_does_not_pile_up_duplicates`, `test_rerun_via_http_does_not_duplicate` |
| 12 | Reviewer-modified findings preserved | `test_reviewer_touched_finding_is_preserved_across_a_unified_rerun` |
| 13 | One module failure doesn't destroy others | `test_one_module_failing_unexpectedly_does_not_prevent_the_others_from_running` |
| 14 | Unified finding displays correct module | `test_unified_finding_displays_the_correct_module_and_title` |
| 15 | Module-specific fields remain available | `test_module_specific_fields_are_preserved_not_flattened_away`, `test_finding_detail_page_shows_tax_specific_fields` |
| 16 | Insufficient Data remains distinct | `test_insufficient_data_outcome_is_never_persisted_as_a_finding` |
| 17 | Queries not duplicated unnecessarily | `test_queries_are_linked_once_per_finding_even_after_repeated_runs` |
| 18 | No SEBI execution occurs | `test_sebi_is_never_a_selectable_module`, `test_posting_only_sebi_runs_nothing_and_is_reported_as_no_modules_selected`, `test_finding_detail_page_404s_for_sebi_module`, `test_configuration_screen_defaults_all_three_modules_checked_and_has_no_sebi_option` |
| 19 | Existing Stage 1–11 tests continue to pass | full-suite run, see section 14 |
| — | Findings Centre filters | `test_findings_centre_module_filter_narrows_results` |
| — | Finding Detail traceability / 404 handling | `test_finding_detail_page_shows_tax_specific_fields`, `test_finding_detail_page_404s_for_unknown_finding` |

## 14. Actual test results

Run inside the sandbox test environment
(`PYTHONPATH=/tmp/shim_site /tmp/testenv/bin/python -m pytest`), exactly
as every prior stage's results in this project were reported.

**New Stage 12 tests:**
```
tests/unit/test_unified_review_service.py — 26 passed
tests/test_review_http.py — 16 passed
```

**Full project suite** (`pytest tests/ --ignore=tests/unit/test_models.py`):
```
512 passed, 2 failed, 71 warnings
```

The 2 failures are `tests/unit/test_migration.py::test_alembic_upgrade_head_matches_base_metadata`
and `::test_downgrade_reverses_cleanly` — both `ModuleNotFoundError: No
module named 'alembic'`, the same pre-existing, environment-only gap
disclosed at the end of every prior stage (the sandbox has no network
access to install `alembic`; unrelated to any Stage 12 change).
`tests/unit/test_models.py` still fails to collect for the same
pre-existing reason disclosed previously (`ModuleNotFoundError:
No module named 'sqlalchemy.exc'` — the sandbox's ORM shim provides
only a partial `sqlalchemy` stand-in), also unrelated.

Baseline reconciliation: Stage 11's end-of-stage baseline was 470
passed / 2 failed (alembic) / 1 collection error (test_models.py).
Stage 12 adds 42 new tests (26 + 16) and changes nothing else:
470 + 42 = **512 passed** — exactly matches. No existing test was
modified, skipped, or deleted to reach this number.

I am not claiming the alembic or test_models.py issues are resolved,
and I am not claiming "all tests passed" — both remain open,
pre-existing, sandbox-only environment gaps, exactly as disclosed at
the end of Stage 10 and Stage 11.

## 15. Decisions requiring your approval

None of these required a STOP under your schema-change rule (no schema
was touched), but they are design choices I made and want to surface
explicitly rather than leave implicit:

1. **Readiness gate scope: whole-engagement, not per-file.** A Unified
   Review is blocked if *any* uploaded file for the engagement isn't
   VALIDATED yet — not just the ones a selected module would actually
   read. I judged "the data mapping and validation are completed" to
   describe the engagement's data preparation as a whole. An
   alternative reading (block only on files relevant to the selected
   modules) is possible; I can change this if you'd prefer it.
2. **The readiness gate also applies to the live preview, not just Run.**
   Showing a "preview" built from admittedly-incomplete data on the one
   screen whose purpose is a trustworthy Run Review action seemed more
   confusing than helpful, so GET (preview) is blocked the same as POST
   (run) until the engagement is ready. Individual engine screens
   (`/review/accounting/`, etc.) are unaffected and still preview
   against partial data exactly as before.
3. **The Review Configuration form (module checkboxes) is hidden while
   blocked**, showing only the blocked banner and a per-file upload
   status table instead. I judged offering module selection before
   there's any data to review as premature; happy to show it disabled
   instead if you'd prefer.
4. **Findings Centre is read/filter/detail only** — it does not add
   status-editing (changing a finding's status, adding reviewer notes)
   to this screen. That capability is `exceptions_bp.py`'s job (still a
   Stage 13 placeholder in this codebase); building it into Stage 12's
   Findings Centre would have meant either duplicating exception-status
   logic here or building Stage 13 early, neither of which your
   instruction asked for.
5. **`related_transaction_id` grouping is real but currently empty.**
   As flagged during reconnaissance: no rule module in any of the three
   engines currently sets `ExceptionDraft.related_transaction_id` (the
   `Transaction` table itself is schema-only, never populated —
   `dataset_service.py`'s own docstring says so). I implemented
   `group_findings_by_transaction()` keyed strictly on that field, so it
   activates automatically the moment a future rule populates it, but I
   deliberately did **not** build a fallback proxy grouping (e.g. "these
   findings share a source file") — a shared file is not the same as a
   shared transaction, and displaying it as if it were would
   misrepresent the review. Today, this grouping is always empty. This
   is disclosed, not hidden.
6. **"Suggested Evidence" and "Limitation" are honestly blank where the
   underlying rule catalogue has no such column** (section 8 above) —
   rather than substituting a different, similarly-named field to avoid
   an empty cell.
