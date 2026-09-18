# Multi-Entity Group Filing — Design Spec

**Date:** 2026-08-01
**Status:** Approved
**Feature area:** Compliance create/edit, list tracker, recurring generation

## Problem

Selecting multiple entities on the compliance create form currently creates **one schedule per entity** (`POST /api/compliance` loops and inserts N rows). The compliance tracker then shows N lines even though the user is filing a **single group return** that covers all selected companies. The user wants:

1. Selecting multiple entities produces **one compliance** (one tracker line) covering all entities.
2. A way to choose which entity the group return is **filed from** (the "filing entity").
3. A **search box and country filter** inside the entity multi-select for large entity lists.
4. A **recurring end date** so a recurring schedule stops generating after a chosen date.
5. **Entity-level membership retained** so entity-level reports can be produced in the future.

## Decisions

- **Approach A (adopted):** One `compliance_schedules` row per group compliance. The schedule's primary `entityId` (nullable, "primary for backward compatibility" per existing migration) stores the **filing entity**; `compliance_entities` stores **every** included entity.
- **Filing entity** is selected by the user when >1 entity is chosen; it drives `entityId` and `countryId` on the schedule.
- **Entity-level retention** is the existing `compliance_entities` join table (membership only). No schema change required for this; future entity reports join `compliance_schedules -> compliance_entities -> legal_entities`.
- **Analytics attribution deferred:** reports, KPI dashboard, and search continue to attribute a group compliance to its primary/filing entity only. Revisited later.
- **Recurring end date:** when a future occurrence's due date is after `recurringEndDate`, the generate job **skips it silently**; `isRecurring` stays `true`.

## Data Model

- **New column:** `compliance_schedules.recurringEndDate TIMESTAMPTZ` (nullable). Added to `supabase-full-schema.sql`, `supabase-migration.sql`, and applied to the live DB via `ALTER TABLE`.
- `compliance_entities` (existing): `id`, `complianceId` (FK, CASCADE), `entityId` (FK), unique `(complianceId, entityId)`. This is the authoritative per-entity fact table. No change.

## Backend

### POST `/api/compliance`

- Normalize selected entities (existing `entityIds`/`entityId` handling).
- Resolve filing entity:
  - If `filingEntityId` provided and is in the selection → use it.
  - Else if exactly one entity selected → use it.
  - Else → `400` "Filing entity is required".
- Insert **one** `compliance_schedules` row:
  - `entityId` = filing entity, `countryId` = filing entity's country (looked up from `legal_entities`).
  - `recurringEndDate` from body (nullable).
- Insert **one `compliance_entities` row per selected entity** (batch insert).
- Insert assignment/approval/activity/audit rows as today (single schedule).
- Return `created[0]` (single object) instead of an array.

### PUT `/api/compliance/[id]`

- Accept `filingEntityId` and `recurringEndDate`.
- If `filingEntityId` provided: set `entityId` = filing entity and `countryId` = filing entity's country (lookup); else keep current `nextEntityIds[0]` behavior.
- Persist `recurringEndDate` (null clears it).
- Existing delete/re-insert of `compliance_entities` for all `entityIds` is unchanged (already multi-entity).

### POST `/api/compliance/generate` (recurring job)

- Read `recurringEndDate` from the schedule.
- Before creating the next occurrence, if `recurringEndDate` is set and `nextDueDate > recurringEndDate`, `continue` (skip). `isRecurring` flag is left unchanged.
- Existing behavior of copying all `compliance_entities` rows to regenerated occurrences is preserved.

## Frontend

### `src/components/multi-select.tsx`

- Extend `Option` to `{ value, label, country?: string }`.
- Add optional props: `searchable?: boolean`, `showCountryFilter?: boolean`.
- Render a text search input at the top of the dropdown that filters options by label text (and country).
- Render a country filter dropdown (distinct countries derived from options) when enabled.
- Default behavior for existing callers unchanged (no search/filter unless props set).

### Create form (`compliance/create/page.tsx`)

- Extend `Entity` interface with `country?: { name: string; code: string }`.
- Pass searchable + country-filter options to the entity `MultiSelect`.
- Add **Filing Entity** selector after the Entities multi-select:
  - Options = currently selected entities.
  - Exactly one selected → auto-locked to that entity.
  - None selected → disabled ("Select entities first").
  - Derived value resets the filing entity if it is deselected (mirrors `effectivePreparerId` pattern; no setState-in-effect).
- Add **Recurring End Date** date input, shown only when "Is Recurring" is checked.
- Submit `filingEntityId` and `recurringEndDate` in the POST body.
- Validation: filing entity required when ≥1 entity selected.

### Edit form (`compliance/[id]/edit/page.tsx`)

- Same Filing Entity selector, pre-filled from the schedule's primary `entityId` (fallback to first `entityId`).
- Recurring End Date input shown when recurring, pre-filled from the record.
- Submit `filingEntityId` and `recurringEndDate` in the PUT body.

### Detail page (`compliance/[id]/page.tsx`)

- Show "Recurring End Date" readout when set (small addition).

### Tracker (list)

- No code change needed: one schedule yields one row; entity names are already comma-joined from `compliance_entities`; Country column shows the filing entity's country.

## Non-Goals

- Multi-entity attribution in reports, KPI dashboard, and search (deferred).
- Per-entity value fields on `compliance_entities` (membership only).
- Backfill/migration of previously fanned-out duplicate schedules.

## Error Handling

- `400` "Filing entity is required" when multiple entities are selected without one.
- `recurringEndDate` before the current/next due date simply results in no further occurrences.

## Verification

- `npx tsc --noEmit` and scoped `npx eslint` must pass.
- DB-layer reproduction script confirms: selecting N entities creates exactly one schedule with N `compliance_entities` rows and the filing entity's country.
- Manual browser checks: create with 2+ entities → one tracker line with all names; filing entity drives country; recurring end date stops generation after the date.
