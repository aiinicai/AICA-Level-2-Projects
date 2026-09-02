# Stage 14 — Final UX & Application Polish

Status: **Complete.** UI/UX-only refinement pass across every FinSight screen built in Stages 2-13. No rule logic, schema, migration, or business-logic behavior was modified — see section 9 for the one backend call site that was rewired (not redesigned) and why it did not require a separate STOP/approval round.

---

## 1. UX Audit

(Delivered to the user in full as a chat message before implementation began, per the Stage 14 instruction not to wait for separate approval of the audit unless a backend/database change was identified. Reproduced here for the permanent record.)

**Current strengths.** The design system already followed the intended direction closely: navy/white/light-grey shell, risk colors reserved strictly for risk levels, no gradients/cartoon graphics/decorative elements, a dependency-free SVG chart library (no CDN, offline-safe). Every screen already distinguished FinSight's automated output from professional judgment in its own copy. Empty states already existed on nearly every list/filter screen.

**Visual inconsistencies found.** Only a light color-token layer existed (navy/white/grey/risk four-color set); there was no named "slate secondary" or formal success/warning/critical/info token set. Warning/ok banners reused `--fs-risk-medium`/`--fs-risk-low` directly rather than a named functional token. No typography scale was named. No Quick-Actions-style button group existed anywhere. A module-run summary badge on the Unified Review screen was hard-coded green (`fs-badge-low`) even when findings were present.

**Navigation inconsistencies found.** `base.html` had both top-level "Exceptions"/"Queries" links AND Review-group "Findings Centre"/"Query & Working Papers" links pointing at the same destinations — the exact duplication flagged in the Stage 14 instruction.

**Terminology inconsistencies found.** `dashboard/index.html` carried two stale references from an earlier stage-numbering scheme: "Composite score from the Risk Engine (Stage 12)" (no Risk Engine was ever built) and "Query Centre (Stage 14)" (Query Centre is Stage 13).

**Poor/unclear user flows found.** The Upload → Map → Validate → Run Review path had no visible step indicator.

**Missing empty/loading/error states found.** Settings and Reports were still raw Stage-2 placeholders with generic copy. No loading/processing indicator existed anywhere — every workflow action is a synchronous POST with no in-flight feedback.

**Accessibility/readability found.** Focus states existed on form inputs but not on buttons/links. Risk badges already paired color with a text label (not color-only).

**Screens requiring refinement, in priority order:** (1) Dashboard — hard-coded to genuine zeros despite Stage 12/13 now producing real data; (2) sidebar navigation dedup; (3) Settings — real About/Privacy content; (4) global CSS tokens/typography; (5) empty-state copy alignment; (6) Reports placeholder polish; (7) terminology fixes.

**The one near-boundary judgment call, stated explicitly before implementation:** wiring `dashboard_bp.py` to the already-built, already-tested `unified_review_service.unified_dashboard_summary()`, `unified_review_service.check_review_readiness()`, and `query_service.query_summary()` was determined to be UI-layer wiring, not a backend/database architecture change — no schema change, no new service logic, no rule-logic change — so it proceeded without a separate STOP. The one thing deliberately *not* done was fabricating a numeric "Overall Risk Score" gauge, since no weighted risk-scoring algorithm exists anywhere in the codebase.

---

## 2. Screens Reviewed

All 23 templates were read in full during reconnaissance: `dashboard/index.html`, `engagement/index.html`, `engagement/new.html`, `engagement/profile.html`, `engagement/applicability.html`, `upload/index.html`, `mapping/index.html`, `mapping/detail.html`, `mapping/error.html`, `mapping/sheet_picker.html`, `validation/index.html`, `validation/detail.html`, `validation/not_mapped.html`, `review/configure.html`, `review/findings.html`, `review/finding_detail.html`, `queries/index.html`, `exceptions/working_paper.html`, `accounting/index.html`, `audit/index.html`, `tax/index.html`, `sebi/deferred.html`, `placeholder.html`, plus `base.html`, the full `design-system.css`, `charts.js`, `dashboard.js`, and the `settings_bp.py`/`reports_bp.py` blueprints (both bare placeholders before this stage).

---

## 3. UI Changes

- Dashboard rebuilt: Current Engagement panel (entity/FY/status/Review Readiness), real stat cards (Total Findings / High-Risk Items / Open Queries / Resolved Queries), Review Overview (per-module bar chart), Risk Distribution (donut, only risk levels that actually occur), Review Status (query status bar chart using the approved conclusion labels), and a Quick Actions panel (Upload Data / Run Review / Findings Centre / Query & Working Papers). No engagement → a single professional empty banner + a Quick Actions panel with "+ New Engagement", not a wall of zeros.
- A visible 6-step indicator (Upload → Detect Structure → Map Columns → Validate → Confirm → Run Review) added to Upload, Mapping (list + detail), Data Quality (list + detail), and the Run Review screen. No separate "Confirm" screen exists in the current architecture, so the Run Review screen itself represents both "Confirm" and "Run Review" depending on readiness — disclosed as a limitation in section 13.
- A loading-state label (`data-loading-text`) added to every primary workflow submit button (Upload, Validate & Save, Run Review, the three individual engine Run buttons, Save Working Paper) via a small dependency-free `forms.js` enhancement — see section 6.
- Settings rebuilt with real About (product/description/modules/version) and Privacy & Data Handling content, plus an honest cross-link to where Materiality is actually editable (Entity Profile) rather than implying a control exists on Settings that doesn't.
- Reports (and the shared `placeholder.html` it uses) rewritten from generic Stage-2 copy to an explicit, honest "not part of FinSight V1 — planned for a later stage" empty state.
- A module-run summary badge on the Unified Review screen (`review/configure.html`) that was hard-coded green regardless of finding count now turns amber when findings are present, matching every other findings badge in the app.
- Stale terminology in the old Dashboard template ("Risk Engine (Stage 12)", "Query Centre (Stage 14)") is gone — it no longer exists in the rebuilt template.

---

## 4. Design System Changes

Added to `design-system.css`, all additive (nothing removed or renamed):

- `--fs-slate` / `--fs-slate-light` — a formally named secondary color (previously only reachable indirectly via `--fs-text-muted`/`--fs-grey-border`).
- `--fs-success` / `--fs-warning` / `--fs-critical` / `--fs-info` — named status-communication tokens. These intentionally alias the exact same hex values as the existing risk tokens (`--fs-risk-low` etc.) rather than introducing a second palette; `--fs-info` is `--fs-accent` under its functional name.
- A named type scale: `--fs-text-2xl` / `-xl` / `-lg` / `-base` / `-sm` / `-xs`. `.fs-page-title` and `.fs-panel-title` (etc.) now reference these instead of a repeated hardcoded rem value.
- `.fs-btn:focus-visible` / `.fs-link:focus-visible` / `.fs-nav-item:focus-visible` / `.fs-nav-subitem:focus-visible` — a visible keyboard-focus outline that didn't exist before (buttons/links previously relied on browser default, which some browsers suppress on click).
- `.fs-quick-actions` — a restrained flex row for action buttons (Dashboard).
- `.fs-steps` / `.fs-step` / `.fs-step-index` / `.fs-step-done` / `.fs-step-current` — the new step indicator component (plain HTML/CSS, no JS, degrades to a readable list without CSS).
- `.fs-app-footer` / `.fs-about-block` — the shared privacy footer and the About/Settings definition-list layout.

No new CSS framework was introduced; everything above extends the existing token-based approach already in place since Stage 2/4.

---

## 5. Navigation Changes

The top-level "Exceptions" and "Queries" sidebar links were removed from `base.html`. The Review-group "Findings Centre" and "Query & Working Papers" links — which pointed at the exact same two destinations — are now the sole sidebar entry points, matching the Stage 14 preferred navigation structure (Dashboard / Engagement / Data / Review[Run Review, Findings Centre, Query & Working Papers, Accounting, Audit, Tax] / Reports / Settings). The underlying `/exceptions/` and `/queries/` Flask routes were **not** removed or renamed — both still resolve to 200 (Finding Detail's "Open Working Paper" link and the Query Centre table's "Open Working Paper" links both still target `/exceptions/<id>/` directly). The SEBI nav item remains exactly as before: a non-clickable, visibly disabled label, never a link.

---

## 6. Empty / Error / Loading States

- **Empty states**: Dashboard (no engagement) now shows one professional banner + Quick Actions rather than a zero-filled stat grid. Engagements list already said "No engagements yet" and was left as-is (already matched). Settings and Reports moved from a generic Stage-2 placeholder sentence to specific, honest "not part of FinSight V1" copy.
- **Error states**: no change was needed to error-message wording — a review of every `errors.*`/`fs-field-error` path (Entity Name/Financial Year validation, Entity Profile validation, upload validation, mapping validation) confirmed all existing messages are already CA-appropriate plain English (e.g. "Entity Name is required", never a raw exception name or stack trace); confirmed by `test_new_engagement_validation_error_is_understandable_not_a_stack_trace`.
- **Loading states**: `frontend/static/js/forms.js` (new) relabels a submit button to a `data-loading-text` value and disables it on submit — "Uploading...", "Validating financial data...", "Running FINsight Review...", "Running Accounting/Audit/Tax Review...", "Saving...". This is a plain synchronous-POST app (no fetch/AJAX anywhere), so the only moment a user could wonder whether the app is frozen is between clicking Submit and the next page load; the script only acknowledges the click and prevents a double-submit — it does not intercept or fake the actual page transition.

---

## 7. Accessibility Improvements

- Visible `:focus-visible` outlines added to buttons, links, and nav items (previously only form inputs had one).
- The step indicator uses `aria-label="Data preparation progress"` and plain text (not color-only) to communicate progress, with a checkmark glyph for completed steps in addition to color.
- No large accessibility framework was introduced, per the explicit instruction — this is incremental, targeted improvement only.

---

## 8. Files Changed

**New files:**
- `frontend/static/js/forms.js`
- `frontend/templates/partials/step_indicator.html`
- `frontend/templates/settings/index.html`
- `tests/test_stage14_ux_polish_http.py`

**Modified files:**
- `frontend/static/css/design-system.css` (tokens, focus states, steps, quick actions, footer, about block)
- `frontend/templates/base.html` (nav dedup, privacy footer, forms.js include)
- `frontend/templates/dashboard/index.html` (rebuilt)
- `frontend/static/js/dashboard.js` (rewired to the new payload shape; gauge/coverage calls removed)
- `app/api/dashboard_bp.py` (rewired to real Stage 12/13 data — see section 9)
- `app/api/settings_bp.py` (rewritten; added `APP_VERSION`)
- `frontend/templates/placeholder.html` (copy rewritten; still used only by Reports)
- `frontend/templates/upload/index.html` (step indicator, loading-state button)
- `frontend/templates/mapping/index.html` (step indicator)
- `frontend/templates/mapping/detail.html` (step indicator)
- `frontend/templates/validation/index.html` (step indicator)
- `frontend/templates/validation/detail.html` (step indicator, loading-state button)
- `frontend/templates/review/configure.html` (step indicator, loading-state button, module-badge color fix)
- `frontend/templates/accounting/index.html` (loading-state button)
- `frontend/templates/audit/index.html` (loading-state button)
- `frontend/templates/tax/index.html` (loading-state button)
- `frontend/templates/exceptions/working_paper.html` (loading-state button)
- `tests/test_dashboard.py` (rewritten — see section 9/11)
- `documentation/architecture.md` (Stage 14 addendum appended)

No file under `app/rules/`, `app/models/`, or `database/migrations/` was touched.

---

## 9. Backend Changes (if any)

One call site was rewired; no new business logic, schema, or migration was introduced.

`app/api/dashboard_bp.py`'s `_dashboard_data()` previously returned hard-coded zeros for every figure (a genuine limitation documented in its own docstring since Stage 4, because no rule/exception/query module existed yet at the time). It now calls three already-existing, already-tested functions:

- `unified_review_service.unified_dashboard_summary(engagement_id)` — total findings, per-module counts, per-risk-level counts (built in Stage 12).
- `unified_review_service.check_review_readiness(engagement_id)` — the same readiness gate the Unified Review screen already uses (built in Stage 12).
- `query_service.query_summary(engagement_id)` — total queries, by-status, by-module (built in Stage 13).

No function in `query_service.py` or `unified_review_service.py` was modified. A local, private grouping tuple (`_RESOLVED_QUERY_STATUSES`) was added inside `dashboard_bp.py` itself — mirroring `query_service`'s own internal terminal-status grouping — to split the Dashboard's "Open Queries" vs. "Resolved Queries" stat cards; this is a display-only grouping over the already-public `STATUS_VALUES` vocabulary, not a new status value, and does not touch `query_service.py`.

This was flagged explicitly in the UX audit (section 1) before implementation, per the instruction to stop and report first if a backend/database change seemed necessary. The determination — no schema change, no new service logic — meant implementation proceeded without a separate approval round.

**Deliberately not built:** a numeric "Overall Risk Score" gauge. No weighted risk-scoring algorithm exists anywhere in FinSight (`app/models/risk.py`'s `RiskScore` model is unpopulated scaffold, never computed by anything). Wiring a gauge to a value that can only ever read 0 would itself be the kind of hard-coded figure Stage 14 explicitly prohibits, so it was removed from the Dashboard entirely and replaced with the real, already-computed Data Readiness indicator instead. This is disclosed here and in section 13, not hidden.

---

## 10. Tests

Re-ran, unmodified: the full Stage 8 (Accounting), Stage 9 (Audit), Stage 10 (Tax), Stage 12 (Unified Review), and Stage 13 (Query & Working Papers) suites, plus every other pre-existing HTTP/unit test — all pass unchanged except the two files noted below.

**Updated (with disclosure, per the standing methodology — behavior was deliberately, explicitly superseded by this stage's own instruction):**
- `tests/test_dashboard.py` — the old test asserted a hard-coded, always-zero payload shape (`risk_score`, `coverage`, a fixed 6-value query-status enum). This is exactly the behavior the Stage 14 instruction explicitly asked to change ("Use actual application data. Do NOT hard-code counts... show a professional empty state rather than zeros everywhere"). Rewritten to 9 tests covering: real empty state with no engagement (no fabricated JSON payload rendered at all), genuine zeros with an engagement but no review yet, real non-zero figures after a review run, the always-Accounting/Audit/Tax module set, and an explicit assertion that no fabricated risk-score gauge is rendered.

**New:**
- `tests/test_stage14_ux_polish_http.py` (17 tests) — nav dedup (no duplicate `/exceptions/`/`/queries/` links, Review-group links still present), SEBI still non-clickable, Settings/Reports real content, the privacy footer (present once, not repeated as a banner), the step indicator on Upload/Run Review, loading-state buttons, understandable validation error messages, empty-state copy, and full engagement/upload workflow screen loads.

All items from the user's explicit Stage 14 testing list are covered: Dashboard loads (`test_dashboard.py`), Navigation links work (`test_stage14_ux_polish_http.py`, `test_app_factory.py`), Engagement/Upload workflow screens load, Review screen loads, Findings Centre loads, Finding Detail loads, Query Centre loads, Working Paper loads (`test_review_http.py`, `test_query_working_papers_http.py`), Reports/Settings pages load, empty states render, validation error messages render, SEBI remains non-executable.

---

## 11. Actual Test Results

Run with the sandbox ORM shim (`PYTHONPATH=/tmp/shim_site`, `/tmp/testenv/bin/python -m pytest`):

```
576 passed, 71 warnings in 13.45s
```

(with `tests/unit/test_models.py` and `tests/unit/test_migration.py` excluded from that run — see the two pre-existing gaps below.)

**Two pre-existing, environment-only gaps** (unrelated to any Stage 14 change, present since before this stage and disclosed in every prior stage's report):
1. `tests/unit/test_models.py` fails to even collect: `ModuleNotFoundError: No module named 'sqlalchemy.exc'` (the sandbox's ORM shim doesn't provide a real `sqlalchemy.exc` submodule).
2. `tests/unit/test_migration.py`'s 2 tests fail: `ModuleNotFoundError: No module named 'alembic'` (Alembic cannot be installed in this sandbox).

Reconciliation: 555 (Stage 13 end) − 5 (`tests/test_dashboard.py`'s original 5 tests, replaced) + 9 (rewritten `test_dashboard.py`) + 17 (new `test_stage14_ux_polish_http.py`) = 576. Matches exactly.

---

## 12. Visual QA

Browser automation was available in this sandbox (Playwright + a pre-installed Chromium at `/opt/pw-browsers/chromium`), so a real visual QA pass was performed rather than only inspecting rendered HTML. A throwaway seeded instance (one synthetic engagement, one uploaded/validated/mapped file, one Tax MSME finding and its resulting query) was run locally and screenshotted at 1440px width across 13 screens: Dashboard (empty state and populated state), Engagements list, Upload, Mapping, Data Quality, Run Review, Findings Centre, Finding Detail, Query & Working Papers, Working Paper, Settings, and Reports.

Findings from the visual pass: layout, spacing, badge coloring, and the step indicator all render as intended; the sidebar shows no duplicate Exceptions/Queries links; SEBI renders visibly dimmed/non-clickable; the privacy footer appears once at the bottom of every screen. One real defect was caught and fixed during this pass: the Unified Review screen's per-module result badge was unconditionally green even when it reported findings — corrected to switch to amber when `finding_count > 0` (see section 3), re-verified with both a screenshot and `tests/test_review_http.py`/`tests/test_stage14_ux_polish_http.py`.

The throwaway seeded instance and its screenshots were local to this session and are not part of the delivered application; no synthetic data or scratch files from this pass were committed to the repository.

---

## 13. Remaining UX Limitations

Disclosed honestly, not hidden:

- **No dedicated "Confirm" screen.** The workflow's step 5 ("Confirm") has no screen of its own in the current architecture — the Run Review screen represents both "Confirm" and "Run Review" depending on data readiness. Building a genuine separate Confirm screen would be new UI surface beyond what Stage 14's polish-only mandate covers; flagged here as a candidate for a future stage rather than added silently.
- **No Overall Risk Score.** As detailed in section 9, no weighted risk-scoring algorithm exists in FinSight at all. The Dashboard shows real finding/risk-level/query counts but no single composite score. Building that algorithm is out of scope for a UI/UX-only stage.
- **Per-finding "Limitation" field.** Finding Detail's Limitation row (present since Stage 12) still shows a disclosed content gap — no rule catalogue in Accounting/Audit/Tax records a separate limitation string per finding today. Stage 14 did not rewrite any rule-generated content, per the explicit instruction to preserve it, so this gap remains and is still disclosed in the UI itself.
- **Settings has no editable controls yet.** The rebuilt Settings screen is informational only (About, Privacy, a cross-link to Entity Profile for materiality) — an app password, AI toggle, and LAN mode are explicitly later-stage features per the blueprint and were not added here.
- **No formal version-numbering scheme exists.** Settings shows "FinSight V1 (Development Build)" rather than a semantic version number, since no release-versioning process (VERSION file, packaging config) exists anywhere in the codebase. Stated honestly rather than inventing a number that would imply a release process that doesn't exist.
