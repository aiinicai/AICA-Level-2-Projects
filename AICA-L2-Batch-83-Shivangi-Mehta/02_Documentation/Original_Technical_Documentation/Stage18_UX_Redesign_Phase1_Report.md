# Stage 18 — UX/Workflow Redesign, Phase 1 Report

## Context

The user requested a large, multi-part redesign in one message: dashboard colors, automatic AS/Ind-AS
detection (schema change), a simplified materiality box, a tabular Yes/No applicability matrix wired to
gate which review modules run, a fully-automatic Upload → Detect Structure → Map Columns → Validate →
Confirm pipeline (removing the human mapping-confirmation step), removal of the standalone Mapping/Data
Quality/Run Review nav tabs, auto-navigation to Findings Centre after a review run, a tabular Query &
Working Papers drafting screen with an Excel download, friendlier "insufficient data" messaging, and
SEBI-style "future module" wording on the Reports tab — delivered as a Windows `.exe` the user could hand to
juniors, tested end-to-end before delivery.

Two things were flagged back to the user before any implementation:
1. This sandbox is Linux with no PyInstaller and no network access to install it — a real `.exe` cannot be
   built or run-tested here (same constraint as every prior stage). Agreed approach: implement and test here
   via the real Flask app + automated suite, then prepare an updated source package + the existing Windows
   Build Runbook for the user (or a Windows-equipped junior) to build the actual EXE, exactly as done for
   v1/v2/v3.
2. The scope mixes cosmetic items with a schema change (AS/Ind-AS auto-detection) and a change that reverses
   a documented safeguard (Blueprint Section 8's "never auto-apply a mapping without human confirmation").
   The user was asked to choose; they asked for reasonable assumptions on sequencing/EXE, said they will
   specify the exact AS/Ind-AS detection rule themselves (schema change held, not guessed), and explicitly
   approved "fully automatic, zero human step" for Mapping/Validate/Confirm.

Given the size and the number of judgment calls the higher-risk items require, the work was split into
**Phase 1** (this stage — cosmetic/low-risk, no schema change, no behavior change to the review engine or
audit trail) and a proposed **Phase 2** (the upload-automation/applicability/review-engine rewiring —
requires the user's sign-off on specific design decisions before implementation).

## Phase 1 — implemented and verified this stage

1. **Dashboard chart colors** — "Review Overview" (previously a flat single teal color for every bar) and
   "Risk Distribution" (previously vivid red/orange/yellow/green) now use a new, dedicated, muted
   professional palette (`--fs-chart-*` tokens in `frontend/static/css/design-system.css`, wired in
   `frontend/static/js/dashboard.js`). Deliberately kept separate from the existing `--fs-risk-*` badge
   tokens so nothing else in the app (Findings Centre badges, Query table risk badges, etc.) changed color —
   scoped exactly to the two charts the user named.
2. **Materiality** — `frontend/templates/engagement/profile.html` now shows only the Overall Materiality
   box. Performance Materiality and Clearly Trivial Threshold were removed from the screen only; both
   columns are untouched on `EntityProfile` (no schema change) — they were already optional and unused by
   any rule (only `overall_materiality` is read, via `shared_detectors.resolve_materiality_threshold_paise()`).
3. **Accounting/Audit/Tax "insufficient data" messaging** — each rule's `insufficient_data_reason` (already
   file-specific, e.g. "No validated Fixed Asset Register data is available for this engagement.") now
   renders as a styled callout banner with an "Upload the missing data to complete this check →" link to the
   Upload screen, instead of a plain muted line buried inside a collapsed rule row.
4. **Reports tab** — now shows SEBI-deferred-style wording naming the Auditor's Report, CARO (where
   applicable), and Tax Audit Report as a future FinSight module under process, instead of the generic
   placeholder. In the process, corrected a pre-existing inaccurate docstring in `app/api/reports_bp.py`
   that falsely claimed PDF/Excel report generation was "implemented in Stage 15" — it never was; flagged
   for the record, not something this stage introduced.

## Verification

- `tests/test_dashboard.py`, `tests/test_engagement_http.py`, `tests/test_stage14_ux_polish_http.py`,
  `tests/test_accounting_http.py`, `tests/test_audit_http.py`, `tests/test_tax_http.py`,
  `tests/unit/test_engagement_validation.py`, `tests/unit/test_engagement_service.py` (everything touching
  these four changes): **81 passed, 0 failed**.
- Full suite: **707 passed, 3 skipped, 0 failed** — identical to the approved v3 baseline, confirming no
  regression from Phase 1.
- Environment note (unrelated to this stage's changes): `tests/unit/test_models.py` and
  `tests/unit/test_migration.py` fail in this sandbox with `ModuleNotFoundError` for `sqlalchemy.exc` /
  `alembic` respectively — the same "SQLAlchemy/Alembic remain uninstallable in this sandbox" limitation
  documented since Stage 1, now surfacing on two test files that weren't part of the standard regression
  invocation before. Neither file was touched this stage; both fail identically with none of this stage's
  edits applied. Excluded from the 707/3/0 count above, exactly as they must have been excluded from every
  prior baseline in this sandbox.

## Phase 2 — proposed, not yet implemented (needs the user's sign-off on judgment calls)

Upload automation (auto Detect Structure → Map Columns → Validate → Confirm, no human step), removal of the
Mapping/Data Quality/Run Review nav tabs, a tabular Yes/No Applicability Matrix wired to actually gate which
review modules run, auto-redirect to Findings Centre after Run Review, and a tabular Query & Working Papers
screen with an Excel download. Recon complete (structure_detector.py, column_mapper.py, mapping_service.py,
validation_service.py, unified_review_service.py, review_bp.py, queries_bp.py, exceptions/transactions
models all read in full). Key judgment calls that need explicit approval before coding, since they affect
audit-trail integrity and aren't spelled out in the user's request:
- Which Applicability task maps to which review module — proposed: "Audit Review" → AUDIT module gate,
  "Income Tax Review" OR "Tax Audit Review" (either Yes) → TAX module gate (FinSight's single TAX module
  covers both rule categories today), ACCOUNTING always runs (not a user-selectable task in the user's own
  matrix spec).
- Multi-sheet Excel files: auto-pick the first sheet (no human sheet-picker anymore).
- `DataMapping.is_user_confirmed` will be set `True` by the automatic pipeline with no human review — this
  repurposes a field whose entire existing meaning (per its own code comment) was "a human confirmed this."
  No schema change, but a real semantic change to what "confirmed" records from now on.
- The Query table's "Account Name" and "Date" columns will show blank/dash today: no rule module currently
  populates `ExceptionRecord.related_transaction_id`, so the `QueryRecord → ExceptionRecord → Transaction`
  join has nothing to return yet. "Amount" (on `ExceptionRecord` directly) will populate correctly.

Not started: AS/Ind-AS auto-detection (holding for the user's exact statutory rule/fields — schema change).
