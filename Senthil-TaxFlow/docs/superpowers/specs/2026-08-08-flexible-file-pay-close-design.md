# Flexible File/Pay Ordering + Close

**Date:** 2026-08-08

## Goal

After a compliance is approved, allow the admin/manager to do the filing and payment steps in either order:

```
APPROVED -> { FILED | PAID } -> { PAID | FILED } -> CLOSED
```

Close is only available once both filing and payment are recorded.

## Background

- `ComplianceStatus` enum already includes `CLOSED` (`supabase-full-schema.sql`), and `getStatusColor` (`src/lib/utils.ts`) plus the tracker/calendar/reports filters already map it.
- Today `file` accepts only `APPROVED` -> `FILED`, and `mark-paid` accepts only `FILED` -> `PAID`. There is no `close` route or button.
- No schema changes required.

## Changes

### 1. `src/app/api/compliance/[id]/file/route.ts`

Relax the guard:

- Accept `APPROVED` **or** `PAID` -> set `status = FILED`, `filedAt = now()`.
- Error message: "Only approved or paid compliance can be filed".

### 2. `src/app/api/compliance/[id]/mark-paid/route.ts`

Relax the guard:

- Accept `APPROVED` **or** `FILED` -> set `status = PAID`, `paidAt = now()`.
- Update error message text.
- Keep the existing ADMINISTRATOR/MANAGER-only check.

### 3. New `src/app/api/compliance/[id]/close/route.ts`

- Only ADMINISTRATOR/MANAGER (mirror `mark-paid`).
- Guard: `status` is `FILED` or `PAID` **and** both `filedAt` and `paidAt` are set; otherwise 400 "Only compliance that is filed and paid can be closed".
- Update `status = CLOSED`, `updatedAt = now()`; return the enriched row.
- Insert one `activities` row (`CLOSED`, fromStatus -> CLOSED) and one `audit_trails` row (`CLOSE`).

### 4. `src/app/compliance/[id]/page.tsx`

- Add `"close"` to the action-type union (line 243).
- Action buttons (admin/manager only):
  - `APPROVED`: show **File** and **Mark Paid**.
  - `PAID` without `filedAt`: show **File**.
  - `FILED` without `paidAt`: show **Mark Paid**.
  - `FILED` with `paidAt` **or** `PAID` with `filedAt`: show **Close**.
- Add `"close"` cases to `getActionLabel`, `getActionDescription`, `getActionApiEndpoint`.
- Reuse the existing optional-comment confirmation dialog (no new fields).

## Out of Scope

- No `closedAt` column (activity/audit trail records the close).
- No second-level review (`REVIEWED`) changes.

## Verification

- `npx tsc --noEmit`
- `npx eslint` on changed files
- `npx vitest run`
- Manual: approve -> file -> pay -> close, and approve -> pay -> file -> close.
