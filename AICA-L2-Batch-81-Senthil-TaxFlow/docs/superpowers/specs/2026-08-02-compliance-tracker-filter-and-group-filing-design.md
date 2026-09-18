# Compliance Tracker: Group Filing, Templates Filter, and Workflow Refinements

Date: 2026-08-02

## Problem

1. A compliance template with multiple attached entities creates one compliance per entity in the Compliance Tracker. Group filings must produce exactly one compliance linking all entities.
2. The Compliance Tracker page has two duplicate buttons: "Add New Compliance Template" and "Create Template".
3. The Compliance Tracker only shows compliances. Users need to switch between a list of their templates and their compliances. Templates are editable; compliances are not editable by design.
4. Compliance workflow needs alignment with the target flow: Pending Preparation → Prepared → Pending Approval → Approved → (2nd-level Pending Review → Reviewed, only if a 2nd-level approver exists) → Filed/Paid (either order) → Closed.

## Confirmed Decisions

- **Template approval:** Keep both paths. Admin can approve a template directly to APPROVED, or send it to a reviewer first (Pending Review → reviewer approves → APPROVED). No change to template transitions.
- **Generated compliance start status:** Template-generated compliances start at `PENDING_PREPARATION` (not `DRAFT`).
- **Compliance workflow scope:** Align statuses only; keep existing transitions. Add (a) a "Mark as Prepared" step, (b) a 2nd-level review step after approval, (c) flexible payment/filing ordering, (d) a Close action.
- **Payment/filing order:** Both orderings allowed after approval — File→Paid or Paid→File, then Closed.
- **Permissions:** In the Compliance Tracker tabs, View and Edit actions are available to preparers and approvers as well as admins. When anyone other than an admin edits a template, the change must go to the admin for approval before the template is finalized.

## Change 1: Group-filing fix (one template → one compliance)

All three generation paths currently loop per entity and insert one `compliance_schedules` row each:

- `src/app/api/templates/[id]/generate/route.ts`
- `src/app/api/templates/generate/route.ts`
- `src/lib/template-compliance.ts` (`generateFirstCompliance`)

### New generation behavior

For a given template + filing month:

1. Dedup check on `compliance_schedules` by `templateId` + `filingMonth` (regardless of entity). If a compliance exists, skip the template.
2. Create exactly one `compliance_schedules` row:
   - `entityId` = first entity (filing entity)
   - `countryId` = that entity's country, falling back to `template.countryId`
   - `status` = `PENDING_PREPARATION`
   - `reviewerId` = `template.reviewerId` (copied so 2nd-level review works)
   - all other fields copied from the template as today
3. Insert one `compliance_entities` row per entity, linking the new schedule.
4. Insert assignments (`template.preparerId`), approvals (`template.approverId`), activity record as today.
5. `generated` result: one entry per template (not per entity).

### GET /api/compliance entityId filter

When `entityId` filter is present, match schedules where `entityId = <id>` OR the schedule has that entity in the `compliance_entities` junction:

```sql
.or(`entityId.eq.${entityId},id.in.(select complianceId from compliance_entities where entityId='${entityId}')`)
```

## Change 2: Remove "Add New Compliance Template" button

`src/app/compliance/page.tsx`:
- Remove the header button "Add New Compliance Template" (navigates to `/compliance/create`).
- Remove the empty-state button pointing to `/compliance/create`.
- Keep the "Create Template" button (navigates to `/master/compliance-templates/create`).

## Change 3: Templates/Compliances filter in Compliance Tracker

Add a `Tabs` control with two tabs: **Compliances** and **Templates**.

### Compliances tab

- Data: `GET /api/compliance`
- Columns: Compliance ID, Entity, Country, Tax Type, Tax Period, Due Date, Priority, Status, Preparer, Actions
- Actions: **View**, **Delete** (admin only). No Edit.
- Filters: search, status, priority, country, entity
- Status options: `PENDING_PREPARATION`, `PREPARED`, `PENDING_APPROVAL`, `APPROVED`, `PENDING_REVIEW`, `REVIEWED`, `REJECTED`, `FILED`, `PAID`, `CLOSED` (add `REVIEWED` and `CLOSED`)

### Templates tab

- Data: `GET /api/templates`
- Columns: Template Number, Version, Status, Tax Type, Country, Frequency, Entities (count), Created By, Actions
- Actions:
  - **View** — all roles
  - **Edit** — admin, preparer, approver (any member)
  - **Delete** — admin only
  - **Generate for Month** — admin only
- Filters: search, status, country, entity, tax type, frequency

### Edit requires admin approval for non-admin changes

When a non-admin (preparer/approver) edits a template:
- If the template is **not** `APPROVED`: the edit is applied directly (it still proceeds through the normal admin/review approval workflow before being finalized).
- If the template is `APPROVED`: the edit is **not** applied directly. It is saved as a pending change request that an admin must approve (or reject) before the template is finalized.

Implementation — new table `template_change_requests`:

```sql
CREATE TABLE IF NOT EXISTS template_change_requests (
  id TEXT PRIMARY KEY,
  "templateId" TEXT NOT NULL REFERENCES compliance_templates(id) ON DELETE CASCADE,
  "orgId" TEXT NOT NULL REFERENCES organizations(id),
  "requestedById" TEXT NOT NULL REFERENCES users(id),
  snapshot JSONB NOT NULL,
  "fieldDiffs" JSONB,
  "changeReason" TEXT,
  status TEXT NOT NULL DEFAULT 'PENDING',   -- PENDING | APPROVED | REJECTED
  "reviewedById" TEXT REFERENCES users(id),
  "reviewedAt" TIMESTAMPTZ,
  "reviewComments" TEXT,
  "requestedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_change_requests_template ON template_change_requests("templateId");
CREATE INDEX idx_change_requests_status ON template_change_requests(status);
```

Behavior:
- `PUT /api/templates/[id]` — when caller is non-admin and `existing.status === "APPROVED"`, do NOT mutate the template. Compute snapshot + diffs from the submitted fields and insert a `template_change_requests` row (status `PENDING`). Notify org admins. Return a flag so the UI shows "Changes submitted for admin approval."
- Template detail page shows pending change requests (diff summary, requester, reason) with admin actions.
- `POST /api/templates/[id]/change-requests/[cid]/approve` (admin) — applies the stored snapshot to the template, bumps `version`, inserts a `compliance_template_versions` row, marks the request `APPROVED`.
- `POST /api/templates/[id]/change-requests/[cid]/reject` (admin) — marks the request `REJECTED`, discards the snapshot.

Note: The template list/detail pages under `/master/compliance-templates` already gate Edit behind the same rules. The tracker Templates tab reuses the same navigation (`/master/compliance-templates/[id]` and `/master/compliance-templates/[id]/edit`).

## Change 4: Make compliances non-editable

- `compliance/page.tsx`: remove the "Edit" dropdown item.
- `compliance/[id]/page.tsx`: remove the header Edit button.
- The edit route `/compliance/[id]/edit` remains in place but is unreachable from the UI.

## Change 5: Add "Mark as Prepared" step

### New route `POST /api/compliance/[id]/prepare`

- Auth required.
- Guard: status must be `PENDING_PREPARATION`.
- Guard: caller must be the assigned preparer or an admin/manager.
- Sets `status = PREPARED`; records activity (`PREPARED`, from `PENDING_PREPARATION`) and audit trail.

### Update `POST /api/compliance/[id]/submit`

- Require `PREPARED` only (remove `PENDING_PREPARATION` from allowed states).

### UI (`compliance/[id]/page.tsx`)

- `PENDING_PREPARATION` + preparer → "Mark as Prepared"
- `PREPARED` + preparer → "Submit for Approval"

## Change 6: 2nd-level review after approval

### New route `POST /api/compliance/[id]/request-second-review`

- Auth required; admin only.
- Body: `reviewerId` (required), `comments` (optional).
- Guard: status must be `APPROVED`.
- Sets `status = PENDING_REVIEW`, `reviewerId`, `adminComments`.
- Inserts notification to reviewer; activity + audit.

### New route `POST /api/compliance/[id]/approve-second-review`

- Auth required.
- Guard: status must be `PENDING_REVIEW`.
- Guard: caller must be the assigned reviewer (`reviewerId === session.user.id`).
- Sets `status = REVIEWED`, `reviewerActionAt`, `reviewerComments`.
- Activity + audit.

### Extend `POST /api/compliance/[id]/reject`

- Allow `PENDING_REVIEW` → `REJECTED` (currently only `PENDING_APPROVAL`).
- Caller must be the assigned reviewer (or admin) when rejecting from `PENDING_REVIEW`.
- Notify preparer.

### UI (`compliance/[id]/page.tsx`)

- `APPROVED` + `reviewerId` present + admin → "Send for 2nd-Level Review"
- `PENDING_REVIEW` + reviewer → "Approve" (→ REVIEWED) and "Reject"
- `REVIEWED` → "File" and "Mark Paid"

## Change 7: Flexible payment/filing ordering

### Update `POST /api/compliance/[id]/file`

- Allow from `APPROVED`, `REVIEWED`, or `PAID` (PAID → FILED ordering).
- Guard otherwise unchanged.

### Update `POST /api/compliance/[id]/mark-paid`

- Allow from `FILED`, `APPROVED`, or `REVIEWED`.
- Guard otherwise unchanged.

### New route `POST /api/compliance/[id]/close`

- Auth required; admin or manager only.
- Guard: status must be `FILED` or `PAID`.
- Sets `status = CLOSED`; records activity + audit.

### UI (`compliance/[id]/page.tsx`)

- `APPROVED` or `REVIEWED` → "File" + "Mark Paid"
- `FILED` → "Mark Paid" + "Close"
- `PAID` → "File" + "Close"

## Change 8: Status/type updates

- `src/types/index.ts`: add `REVIEWED` to `ComplianceStatus`.
- `compliance/page.tsx` `STATUS_OPTIONS`: add `REVIEWED` and `CLOSED`.
- `src/lib/utils.ts`: ensure `getStatusColor` maps `REVIEWED` and `CLOSED`.

## Change 9: Database migration

New migration file in `supabase/migrations/`:
- `ALTER TYPE "ComplianceStatus" ADD VALUE IF NOT EXISTS 'REVIEWED';` (guarded in a DO block)
- Create `template_change_requests` table + indexes.

Also update the reference schema files (`prisma/schema.prisma`, `supabase-full-schema.sql`, `supabase-migration.sql`) so the `REVIEWED` enum value and the new table are present for future regenerations.

## Out of Scope

- Removing the `/compliance/create` page (still reachable for one-off manual creation).
- Changing template workflow transitions (kept as-is per decision).
- Dashboard KPIs / reports / calendar that consume `compliance_schedules` (they may show group filings; no changes here).

## File Summary

| Area | Files |
|---|---|
| Group filing | `src/app/api/templates/[id]/generate/route.ts`, `src/app/api/templates/generate/route.ts`, `src/lib/template-compliance.ts`, `src/app/api/compliance/route.ts` |
| Tracker filter + button removal + non-editable | `src/app/compliance/page.tsx` |
| Prepared step | `src/app/api/compliance/[id]/prepare/route.ts` (new), `src/app/api/compliance/[id]/submit/route.ts`, `src/app/compliance/[id]/page.tsx` |
| 2nd-level review | `src/app/api/compliance/[id]/request-second-review/route.ts` (new), `src/app/api/compliance/[id]/approve-second-review/route.ts` (new), `src/app/api/compliance/[id]/reject/route.ts`, `src/app/compliance/[id]/page.tsx` |
| Payment/filing + close | `src/app/api/compliance/[id]/file/route.ts`, `src/app/api/compliance/[id]/mark-paid/route.ts`, `src/app/api/compliance/[id]/close/route.ts` (new), `src/app/compliance/[id]/page.tsx` |
| Template edit w/ admin approval | `template_change_requests` migration, `src/app/api/templates/[id]/route.ts` (PUT), new `src/app/api/templates/[id]/change-requests/[cid]/approve/route.ts`, new `.../reject/route.ts`, template edit page + detail page |
| Types/status | `src/types/index.ts`, `src/lib/utils.ts`, prisma/schema.prisma, supabase-full-schema.sql, supabase-migration.sql |

## Permissions Matrix (Compliance Tracker tabs)

| Action | Compliances tab | Templates tab |
|---|---|---|
| View | All roles | All roles |
| Edit | Never (by design) | Admin + Preparer + Approver (non-admin edits route to admin approval) |
| Delete | Admin only | Admin only |
| Generate for Month | — | Admin only |
