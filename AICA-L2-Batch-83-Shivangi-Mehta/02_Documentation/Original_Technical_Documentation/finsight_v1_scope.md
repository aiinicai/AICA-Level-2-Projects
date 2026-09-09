# FinSight V1 Scope Statement

**Status: current and authoritative for the active build.** This document
records a deliberate, user-approved scope decision made after Stages 1–10
were complete and approved, and before Stage 11 (originally planned as the
SEBI Rule Catalogue) began. It supersedes any earlier document — the
Blueprint, the Stage 4/5 addenda, the original v0.2 SEBI placeholder
register — wherever those describe SEBI/Listed-Entity review as an active
or imminent V1 module.

---

## Product positioning

**FinSight**
Offline Financial Review & Compliance Assistant
Primary modules: **Accounting · Audit · Tax**

FinSight V1 is not described as a SEBI compliance tool, and does not claim
to provide complete legal, regulatory, or audit compliance assurance. Every
finding FinSight produces is worded through the shared non-definitive
vocabulary already built in `app/rules/wording.py` — Review Assistant
framing, never a conclusion: **Potential Issue · Review Required ·
Potential Risk · Suggested Query · Insufficient Data**.

---

## Why this decision was made

After reviewing the project scope following Stage 10's approval, the
decision was made **not** to implement SEBI / Listed Entity compliance in
FinSight V1. This is a deliberate scope decision to keep V1 focused,
reliable, offline-first, and practical for accounting, audit, and tax
review work — not a technical limitation, and not an indication that SEBI
review is unimportant. It is explicitly carried forward as **future
scope**, not abandoned.

---

## IN SCOPE (FinSight V1)

- Accounting Review
- Audit Review
- Tax / Tax Audit Review
- Data Upload
- Data Structure Detection
- Column Mapping
- Data Validation
- Findings
- Queries
- Working Papers
- Reports
- Local/offline processing
- Optional local-network access

## OUT OF SCOPE (FinSight V1)

- SEBI compliance
- Listed entity compliance
- LODR (Listing Obligations and Disclosure Requirements) compliance
- Listed-company corporate governance compliance

## FUTURE SCOPE

- SEBI / Listed Entity Review

---

## What this means concretely

- **No SEBI rules, rule tables, seed data, APIs, findings, queries, or
  compliance reports exist in V1.** No development effort was spent
  researching or coding SEBI regulations at this stage (the Stage 11 SEBI
  catalogue research that had begun was stopped before any rule content
  was written, precisely because of this scope decision).
- **The database is unchanged.** No migration was created or is needed.
  `EntityProfile.is_listed` and the `Applicability` table's `"SEBI/LODR"`
  area remain in the schema exactly as Stage 3/5 built them — they are not
  deleted, and they do not activate anything. `SebiRule` (Stage 3) and the
  `app/rules/sebi` package (an empty stub since Stage 2/3) also remain,
  unused, for the same reason.
- **The UI clearly communicates the scope**, rather than silently omitting
  it:
  - The Entity Profile screen's "Listed entity" checkbox carries a note
    that Listed Entity / SEBI Review is outside the current V1 scope, and
    that this selection does not trigger any SEBI analysis.
  - The Applicability Matrix screen no longer surfaces a confirmable
    SEBI/LODR row, and carries the same out-of-scope note.
  - The sidebar nav's SEBI item is now a single, static, non-clickable
    "Future Module" label — in every engagement state, not conditionally
    shown/hidden the way it was before this decision — never a working
    link, never a fake button.
  - `/review/sebi/` (kept registered rather than removed, so a typed-in
    URL doesn't 404) renders a clear "outside current scope" message
    instead of the old generic Stage-2 placeholder text.
  - The Dashboard's "Exceptions by Module" and coverage panels list
    exactly Accounting, Audit, Tax — never a SEBI row, in any state.
- **Accounting, Audit, and Tax are functionally unchanged.** No rule
  logic, rule IDs, thresholds, or approved source references in
  `app/rules/accounting/`, `app/rules/audit/`, or `app/rules/tax/` were
  touched by this scope change. See the Stage 11 Scope Change Report for
  the itemized file list and test results.

---

## Preserved extensibility for a future FinSight V2

Nothing that would make reactivating SEBI review harder in a future
version was removed:

- `app/services/applicability_engine.py` (the generic Entity-Profile ->
  system-suggestion -> professional-confirmation framework, including
  `compute_sebi_nav_state()` and the `"SEBI/LODR"` entry in `AREAS`) is
  completely unchanged — just not surfaced through the V1 UI.
- `app/api/dashboard_bp.py`'s `_sebi_row()` function (the applicability-
  driven dashboard-row logic) is intact and documented as deliberately
  unused in V1, ready to be wired back into `_dashboard_data()`.
- `app/api/sebi_bp.py` remains a registered Flask blueprint with a real
  route, so a V2 build can replace its single placeholder view with real
  SEBI review screens without any nav/registration wiring changes.
- The `EntityProfile.is_listed` field and the `Applicability` table's
  generic per-area row mechanism require no schema change to support a
  real SEBI module later — only new rule content and UI surfacing.

The active V1 engine flow is:

```
Validated Financial Data
        |
Accounting Review Engine
        |
Audit Review Engine
        |
Tax Review Engine
        |
Unified Findings
        |
Query / Working Paper Centre
        |
Reports
```

SEBI does not appear as an active step in this flow. See
`documentation/architecture.md`'s "Stage 11 Scope Change" addendum for the
full before/after detail and the file-by-file change list.
