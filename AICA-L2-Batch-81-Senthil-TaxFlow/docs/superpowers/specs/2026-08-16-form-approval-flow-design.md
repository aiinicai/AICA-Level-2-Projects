# Form-Level Approval Flow — Design Spec

Date: 2026-08-16

## Problem

Approval flow is currently a per-entity master-data setting
(`legal_entities.approvalFlow`). A form master (`form_master`) has no approval flow of
its own. The user wants each form to carry an approval flow value so that:

1. The form's approval flow is compared against the flow of the entity a compliance was
   generated for.
2. If they differ, the compliance shows a **soft warning** (non-blocking, informational).
3. When they differ, the **form's approval flow takes precedence** over the entity's
   flow when building the compliance's approval chain.

## Goals

1. `form_master` gains a mandatory `approvalFlow` column (`NONE` / `ONE_LEVEL` /
   `TWO_LEVEL`).
2. The effective approval flow for a compliance resolves as **form flow → entity flow
   fallback** (form wins when a form is linked; entity flow applies when there is no
   form).
3. Reviewer/Approver dropdowns on template create/edit, compliance create/edit follow
   the effective flow (form's flow when a form is selected, otherwise the entity's).
4. The compliance detail page shows a soft (amber) warning below the filing entity in the
   entity card whenever the form's flow differs from the filing entity's flow.
5. The approval chain builders (template generation, manual create, compliance edit) use
   the effective flow.
6. Import route is unchanged — imports do not link a form, so they stay entity-driven.

## Decisions

- **Form flow is mandatory.** `form_master.approvalFlow` is `NOT NULL DEFAULT 'ONE_LEVEL'`.
  Existing forms backfill to `ONE_LEVEL` (matches the entity default and prior behavior).
  The Add/Edit Form dialog requires an explicit selection.
- **Form wins over entity.** When a compliance links a form, the form's flow determines
  the approval chain. The entity's flow is only a fallback when no form is linked.
- **Warning is display-only.** It is shown in the compliance detail page, below the
  **filing entity** in the entity card. It never blocks saving or submission.
- **Only the filing entity is compared.** The filing entity
  (`compliance_schedules.entityId`) is what drives approval, so the mismatch check is
  `form.approvalFlow` vs `filingEntity.approvalFlow`.
- Backward compatible for compliances without a form: they keep using the entity flow,
  exactly as today.

## Data Model

### Migration `20260816010000_form_approval_flow.sql`

Self-contained and idempotent:

```sql
ALTER TABLE form_master ADD COLUMN IF NOT EXISTS "approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL';

ALTER TABLE form_master DROP CONSTRAINT IF EXISTS "form_master_approvalFlow_check";

ALTER TABLE form_master ADD CONSTRAINT "form_master_approvalFlow_check"
  CHECK ("approvalFlow" IN ('NONE', 'ONE_LEVEL', 'TWO_LEVEL'));
```

Also update the `supabase-full-schema.sql` snapshot.

### Prisma

`FormMaster` gains `approvalFlow String @default("ONE_LEVEL")`.

## Changes by Area

### 1. Effective flow helper

New pure helper in `src/lib/approval-flow.ts`:

```ts
effectiveApprovalFlow(formFlow?: string | null, entityFlow?: string | null): ApprovalFlow
```

Returns `normalizeApprovalFlow(formFlow)` when `formFlow` is set, otherwise
`normalizeApprovalFlow(entityFlow)`.

### 2. Forms master UI + APIs

- **Forms page** (`master/forms/page.tsx`):
  - Add mandatory "Approval Flow" select (all three options) to the Add/Edit dialog.
  - Add to `FormMaster` interface, `emptyForm`, and edit loading.
  - Add an "Approval Flow" badge column to the table.
  - Add the column to `importColumns` (value `NONE` / `ONE_LEVEL` / `TWO_LEVEL`).
- **APIs**: `api/forms/route.ts` (GET select + POST body/validation),
  `api/forms/[id]/route.ts` (GET select + PUT body/validation),
  `api/forms/upload/route.ts` (column + validation) all carry `approvalFlow`.

### 3. Approval-chain builders use the effective flow

- **`lib/template-compliance.ts`** (`insertGeneratedCompliance`): when
  `template.formId` is set, fetch `form_master.approvalFlow`; effective flow =
  `effectiveApprovalFlow(formFlow, entityFlow)`; build records from it.
- **`api/compliance/route.ts`** (manual create): same — when `formId` is present, fetch
  the form's flow and use `effectiveApprovalFlow` for validation and records.
- **`api/compliance/[id]/route.ts`** (edit): same when rebuilding approval records.
- **`api/compliance/import/route.ts`**: no change.

### 4. Dropdowns follow the effective flow

- **Template create** (`master/compliance-templates/create/page.tsx`): `flow` =
  selected form's `approvalFlow` when a form is chosen, else the filing entity's flow.
- **Template edit** (`master/compliance-templates/[id]/edit/page.tsx`): same.
- **Ad-hoc create** (`compliance/create/page.tsx`): form is required → `flow` = selected
  form's `approvalFlow` (entity flow remains only until a form is picked).
- **Compliance edit** (`compliance/[id]/edit/page.tsx`): `flow` = selected form's
  `approvalFlow` when a form is chosen, else the filing entity's flow. Preserve the
  existing `existingApproverCount > 0` fallback so that a compliance which already has
  approval records keeps showing the reviewer/approver dropdowns even when the effective
  flow is `NONE`.
- The `Form` interfaces on these pages gain `approvalFlow?: string`.

### 5. Compliance detail soft warning

- **Detail API** (`api/compliance/[id]/route.ts`): add `approvalFlow` to the `form` and
  filing `entity` selects.
- **Detail page** (`compliance/[id]/page.tsx`): in the entity card, below the **filing
  entity** block (the entity entry whose id matches `data.entity?.id` — the filing entity
  is always present in the rendered list), when `form.approvalFlow` and the filing
  entity's `approvalFlow` differ, render a soft amber warning styled like
  `master/compliance-templates/[id]/edit/page.tsx:431`:
  *"Approval flow mismatch — Form is {formFlow}, entity master is {entityFlow}. The form's
  approval flow applies."*

## Testing

- Vitest unit test for `effectiveApprovalFlow`: form set → form wins; form `NONE` → still
  `NONE`; form null/undefined → falls back to entity flow; both null → `ONE_LEVEL`.
- Existing tests must continue to pass; `npx tsc --noEmit` must be clean; lint clean.

## Scope

Files touched: new migration, `supabase-full-schema.sql`, `prisma/schema.prisma`,
`src/lib/approval-flow.ts` (+ test), `master/forms/page.tsx`, 3 form APIs,
`lib/template-compliance.ts`, `api/compliance/route.ts`, `api/compliance/[id]/route.ts`,
template create + edit pages, compliance create + edit pages, compliance detail page.

No changes to: import route, submit/approve flows (they operate on existing approval
records, which are already built using the effective flow), dashboard/KPI queries.
