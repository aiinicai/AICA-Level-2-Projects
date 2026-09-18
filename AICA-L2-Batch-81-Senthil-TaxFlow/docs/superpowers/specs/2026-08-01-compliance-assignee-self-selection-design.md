# Design: Compliance Assignee Self-Selection (Create + Edit)

**Date:** 2026-08-01
**Status:** Approved (Approach A)

## Problem

In the compliance schedule creation and edit forms, a user cannot reliably add
themselves as the preparer or approver:

- The Preparer field is a read-only auto-assignment for non-admin users and a
  role-filtered dropdown for admins.
- The Approvers field is a checkbox grid of `APPROVER`-role org members.
- Both user lists come from `/api/users?role=PREPARER` and
  `/api/users?role=APPROVER`, which filter strictly by role. An
  `ADMINISTRATOR`-role user is not in either list, so the admin cannot add
  themselves as preparer or approver on a compliance schedule they create.

## Goals

1. Any user creating/editing a compliance schedule can add themselves as the
   preparer (dropdown, defaulting to self).
2. Approvers are selected via a single-select dropdown instead of a checkbox grid.
3. An admin can add themselves both as preparer and approver on a compliance
   schedule.

## Approach: Client-side inclusion + dropdowns (Option A)

Contained changes in the create/edit pages and one line in the create API. No
changes to shared API semantics.

## Data Model

No schema changes. The existing `compliance_assignments` and
`compliance_approvals` tables already support the assigned users, and the
existing `ensureOrgMember` logic already adds assigned preparers/approvers
(including the admin) to the active organization with the appropriate role.

## Changes

### 1. `src/app/compliance/create/page.tsx`

- Fetch preparer and approver option lists as today (role-filtered org members).
- Build the option lists in the client so the **current user is always
  included** (merged with the fetched list, deduped by id, sorted by name).
- **Preparer field**: render a `Select` dropdown for all roles (previously
  read-only for non-admins). Options = preparer list (incl. current user).
  Default selection = `sessionUser.id`.
- **Approvers field**: replace the checkbox grid with a single-select `Select`
  dropdown. Options = approver list (incl. current user). State changes from
  `approverIds: string[]` to a single `approverId: string`.
- Submit payload: always send `preparerId`; send
  `approverIds: approverId ? [approverId] : []` so the existing API contract
  (array) is preserved.

### 2. `src/app/compliance/[id]/edit/page.tsx`

- Same dropdown changes and current-user inclusion.
- Prefill preparer from the existing assignment
  (`assignments[0].preparerId`).
- Prefill approver from the first existing approval
  (`approvals[0]?.approverId`).
- Submit payload: `preparerId` and
  `approverIds: approverId ? [approverId] : []`.
- **Known implication:** a schedule that already has multiple approvers will
  display only the first; saving will collapse it to that single approver.

### 3. `src/app/api/compliance/route.ts` (POST)

Change preparer resolution so a non-admin's chosen preparer is respected:

```ts
// before
const preparerId = isAdmin ? (bodyPreparerId || session.user.id) : session.user.id
// after
const preparerId = bodyPreparerId || session.user.id
```

The PUT route already handles a 1-element `approverIds` array; no change needed.

## Files Touched

- `src/app/compliance/create/page.tsx`
- `src/app/compliance/[id]/edit/page.tsx`
- `src/app/api/compliance/route.ts`

## Out of Scope

- Changing the shared `/api/users` endpoint semantics.
- Multi-approver support in the UI (single-select only).
- Notification or audit-log changes (existing flows already cover assignments).
