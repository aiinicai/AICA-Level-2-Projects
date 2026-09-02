# Stage 18 — UX/Workflow Redesign, Phase 2 Report

## Context

Phase 1 (previous report, `Stage18_UX_Redesign_Phase1_Report.md`) covered the cosmetic, no-schema-change,
no-behavior-change items: dashboard chart colors, the single Overall Materiality box, friendlier
insufficient-data messaging, and the Reports tab's deferred-module wording.

Phase 2 covers the higher-risk items that were deliberately held back pending the user's answers to a
simple-language clarifying round: automatic AS/Ind-AS detection (a schema change), the tabular Yes/No
Applicability Matrix wired to the review engine, the automatic Upload → Map → Validate pipeline ending in
one "Looks Good — Confirm & Continue" click, removal of the standalone Mapping/Data Quality/Run Review nav
tabs, auto-navigation to the Findings Centre after a review run, and the tabular Query & Working Papers
screen with an Excel download.

Two things were flagged and resolved before implementation, per the standing "flag before implementing"
rule:

1. **Mapping auto-confirmation.** The user's first-round answer was "fully automatic, zero human step." On
   the simple-language re-ask, the user revised this to **"add one quick 'Looks good?' click"** — this is
   what got built. The existing Blueprint Section 8 safeguard ("never auto-apply a mapping without human
   confirmation") is fully preserved: nothing is written to the database until that one click is submitted.
2. **Query table Account Name / Date columns.** The user's first-round answer was "build the transaction-
   linking first." Investigating `dataset_service.py` before implementing surfaced that FinSight does not
   persist parsed transaction rows anywhere — data is re-derived live from uploaded file bytes on every
   rule-engine run — so "linking" a query back to one ledger row would mean adding a new persistence layer
   touched by roughly 40 rule files. This was not disclosed by the original simplified question, so it was
   re-asked with the full tradeoff. The user's corrected answer: **"leave blank for now, ship everything
   else sooner."** Account Name and Date are blank in both the on-screen table and the Excel export,
   clearly labeled as such, with a note that a reviewer can fill them in by hand. No architecture change was
   made.

## What was implemented and verified this stage

### 1. Automatic AS / Ind-AS detection (schema change — disclosed)

- **New field:** `EntityProfile.ind_as_mandated` (nullable Boolean) — the sole new column. Migration
  `database/migrations/versions/0004_entity_profiles_ind_as_mandated.py` adds it; like every hand-authored
  migration in this sandbox, it is disclosed as **not execution-verified via real Alembic** (Alembic remains
  uninstallable here) — only the SQLAlchemy model change itself was exercised, via
  `Base.metadata.create_all()` in the test suite.
- **The Entity Profile screen** now asks a plain Yes/No question — "Is this company required to follow
  Ind AS?" — instead of a manual Accounting Standard dropdown. A secondary "Override manually" dropdown
  remains for the rare case a professional needs to set the framework directly.
- **Backward compatible by design:** if `accounting_framework` is posted directly (every pre-existing
  caller/test does this), the Yes/No answer is not required and does not override it. This meant zero
  existing tests needed rewriting for this piece.

### 2. Applicability Matrix — tabular Yes/No, wired to the review engine

- Redesigned from the previous 6-area detailed screen (System Suggestion / Entity Profile Input /
  Professional Confirmation, one row each) to a single-row table: Sr No, Client Name, Accounting
  Standard/Ind AS (read-only, auto-detected), and three Yes/No questions — Audit Review, Income Tax Review,
  Tax Audit Review. Listed-entity/SEBI review remains out of V1 scope, unchanged.
- **New:** `engagement_service.get_enabled_review_modules()` reads these Yes/No answers to decide which of
  ACCOUNTING/AUDIT/TAX the one-click "Run Review" action runs. Before this stage, the Applicability Matrix
  was recorded but had no functional effect on which modules ran — it now does, but only for the *new*
  one-click path (see below); the original checkbox-based Run Review is untouched.
- No schema change beyond what Applicability already had (`user_confirmed_status` — same field, same
  values, just a simpler UI over it).

### 3. Upload automation — automatic Detect Structure / Map / Validate, one-click Confirm

- **New module** `app/services/auto_pipeline_service.py` computes, for every file still sitting at
  `UPLOADED`, the same structure detection, column-mapping suggestions, file-type-mismatch warning, and
  Data Quality preview the existing (still fully functional, unremoved) Mapping/Data Quality screens
  already compute — live, on every GET, nothing persisted.
- A new "Ready to Confirm" panel on the Upload screen shows this preview per file. One button — **"Looks
  Good — Confirm & Continue"** — persists the suggested mappings and runs+saves Data Quality for every
  eligible file in one click, via the exact same `mapping_service.confirm_mappings()` and
  `validation_service` functions the manual screens already use (so this can never disagree with what a
  professional would see by opening those screens directly).
- **Multi-sheet Excel:** the manual Mapping screen stops and asks a human to pick a sheet when a workbook
  has more than one. The automatic pipeline can't stop and ask, so it always picks the first/leftmost sheet
  and says so on screen ("chosen automatically — this workbook has more than one"). This is disclosed as the
  one new judgment call the automatic path makes that the manual screens don't.
- **Zero-match fallback:** if not one column can be auto-matched, the file is reported as "couldn't
  auto-match any columns," excluded from the Confirm & Continue action, and a "Review manually" link to the
  existing Mapping screen is offered instead. Nothing is ever force-mapped.
- **Once every uploaded file is VALIDATED**, a "Run Review" button appears on the Upload screen itself and
  posts to the review engine with a `run_source=upload_quick_action` marker.

### 4. One-click Run Review, auto-navigation to Findings Centre

- `app/api/review_bp.py` gained a second, additive POST path (dual-path design, same pattern already used
  in `upload_bp.py` for multi-file uploads): the new path reads no `modules` checkbox list at all — it uses
  `get_enabled_review_modules()` — and redirects straight to the Findings Centre on success. The **original**
  checkbox-based POST path (used by every pre-existing caller/test) is byte-for-byte unchanged: same module
  selection, same inline Result Summary render, no redirect.
- The standalone "Run Review" sidebar link was removed (the Upload screen's button is now the entry point);
  the `/review/` route itself, GET and the original POST, is untouched and still fully works.

### 5. Sidebar cleanup — Mapping and Data Quality folded into Upload

- Removed the "Mapping" and "Data Quality" sidebar sub-links, per the original request. Both routes
  (`/data/mapping/`, `/data/quality/`) remain fully functional and reachable — from the Upload screen's
  "Review manually" link on a per-file basis, or by direct navigation — only the sidebar shortcuts are gone.

### 6. Query & Working Papers — tabular screen + Excel export

- The Query Centre table (`/queries/`) now shows: Sr No, Account Name (blank — see above), Date (blank —
  see above), Amount, Observation, and two directly-editable columns — **Additional Note**
  (`QueryResponse.reviewer_comments`) and **Client Remark** (`QueryResponse.management_response`). Both
  already existed on the approved schema and were already wired through `update_working_paper()` — no new
  columns were needed for this piece.
  - Filters (module/status/risk/rule/search) and the summary panel were kept — the user did not ask to
    remove them, and they remain useful on a screen that can otherwise grow long.
  - A new inline-edit route, `POST /queries/<exception_id>/update-remarks`, saves just these two fields from
    the row without needing a visit to the full Working Paper screen — writing through the exact same
    `query_service.update_working_paper()` function (and therefore the exact same audit-log entries) the
    full screen already uses. The full Working Paper screen is untouched and still the place for status
    changes, evidence, and assignment.
- **New:** `GET /queries/export.xlsx` — a one-click Excel download of the same table, built with `openpyxl`
  (already an approved dependency) via `query_service.export_working_papers_workbook()`. Verified to produce
  a real, loadable `.xlsx` with the expected header row and blank Account Name/Date cells.

## Honest caveats (disclosed, not hidden)

- **Migration 0004 was not execution-verified via real Alembic** — same sandbox limitation as every prior
  migration in this project (Alembic remains uninstallable here). Only the SQLAlchemy model change was
  exercised, via `Base.metadata.create_all()` in the test suite.
- **Account Name and Date are blank** in the Query table and its Excel export, by the user's own final,
  fully-informed choice — not a bug, and not silently done. See "Query table Account Name / Date columns"
  above.
- This sandbox is Linux with no PyInstaller and no network access to install it — a real `.exe` still cannot
  be built or run-tested here. Everything above was implemented and tested through the real Flask app; the
  next step toward the requested `.exe` is preparing an updated source package plus the existing Windows
  Build Runbook, exactly as done for v1/v2/v3.

## Verification

- Targeted regression after each change: `tests/test_review_http.py`, `tests/unit/
  test_unified_review_service.py`, `tests/test_dashboard.py` (51 passed) after the review_bp.py dual-path
  change; `tests/test_upload_http.py`, `tests/test_mapping_http.py`, `tests/test_validation_http.py`,
  `tests/test_review_http.py` (50 passed) after the Upload-screen wiring; `tests/test_query_working_papers_http.py`,
  `tests/unit/test_query_service.py` (22 passed, including 6 new Stage 18 tests) after the Query table
  redesign.
- **16 new tests written this stage**, covering behavior the existing suite had no coverage for: the
  auto-pipeline preview and Confirm & Continue flow (including the zero-match fallback and multi-sheet
  auto-pick), the one-click Run Review action and its redirect to Findings Centre (with the legacy checkbox
  path independently re-verified as unaffected), AS/Ind-AS auto-detection end-to-end via HTTP, the Query
  table's inline remarks edit, and the Excel export's actual file contents (loaded back with `openpyxl` and
  checked, not just asserted on status code).
- **Full suite: 724 passed, 3 skipped, 0 failed** (`--ignore=tests/unit/test_models.py
  --ignore=tests/unit/test_migration.py` — the same two pre-existing sandbox-only import gaps disclosed in
  every prior stage's report, confirmed unrelated to this stage's changes). 707 passed at the last approved
  baseline; 708 after Phase 1's test rewrites (+1: 4 old applicability tests replaced by 5 new ones); 724
  now (+16 new Stage 18 tests) — the count is fully accounted for.
- **Manual end-to-end smoke test** run through the real Flask app (not just the automated suite), covering
  the full journey the user asked to see working before delivery: create engagement → Entity Profile via the
  new Yes/No question → Applicability Matrix (all Yes) → select engagement → upload a Trial Balance CSV and
  a General Ledger XLSX → "Ready to Confirm" preview shown → "Looks Good — Confirm & Continue" → both files
  VALIDATED → "Run Review" button appears → one click → redirected to Findings Centre → Dashboard,
  Accounting, Audit, Tax, Reports, Query Centre (with its Excel download), and Settings all loaded
  successfully (HTTP 200) with the new engagement's data. Every step passed.

## What's next

The remaining step toward the user's requested `.exe`: prepare an updated source package (v4, incorporating
both Phase 1 and Phase 2 of this redesign) alongside the existing Windows Build Runbook, so the user or a
Windows-equipped colleague can build and run the actual executable — the one thing that genuinely cannot be
done inside this Linux sandbox.
