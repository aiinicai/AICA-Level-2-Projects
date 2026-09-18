# Entity-Driven Approval Flow with "No Approval" — Design Spec

Date: 2026-08-15

## Problem

Compliance template creation always shows the Reviewer and Approver dropdowns, and
there is no way to declare that a compliance requires **no approval**. Approval flow is
already a per-entity master-data setting (`legal_entities.approvalFlow` with
`ONE_LEVEL` / `TWO_LEVEL`), but the reviewer/approver fields on forms do not react to it,
and there is no "no approval" option.

## Goals

1. Entity master data supports **three** approval flows: `NONE` (no approval),
   `ONE_LEVEL` (reviewer only), `TWO_LEVEL` (reviewer then approver).
2. The entity's flow is the single source of truth — the dropdown the user sees lives on
   the **entity form**, not the template.
3. Reviewer/Approver dropdowns are **dynamic** on template create/edit, ad-hoc create,
   and import, shown/hidden based on the effective filing entity's flow.
4. Approval-chain builders (template generation, manual create, import) respect `NONE`
   and create no approval records.
5. Submitting a compliance with no approval records **auto-approves** it (skips
   `PENDING_APPROVAL`) so it can proceed to filing/payment/close.

## Decisions

- **Approach:** extend the existing entity-level `approvalFlow` with a `NONE` value. No
  new column on `compliance_templates`. All forms resolve the flow from the effective
  filing entity (`filingEntityId || single selected entity`) — the same resolution the
  ad-hoc create page already uses (`compliance/create/page.tsx`).
- **1-level means Reviewer only** (the single approver is the reviewer / step 1).
  `TWO_LEVEL` adds the approver at step 2. Confirmed with user.
- **Template never overrides the entity** — the entity's flow always wins for generated,
  manual, and imported compliances.
- **No-approval submit = auto-approve.** When a compliance has zero approval records, the
  submit route sets `APPROVED` directly instead of `PENDING_APPROVAL`.
- **Default for new entities stays `ONE_LEVEL`** so existing behavior is unchanged until
  an entity is explicitly set to `NONE`.
- Backward compatible: existing rows with `ONE_LEVEL` / `TWO_LEVEL` are untouched.

## Data Model

### Migration `20260815010000_entity_approval_flow_none.sql`

Self-contained and idempotent (safe even if `20260814010000_entity_approval_flow.sql`
was not applied):

```sql
ALTER TABLE legal_entities ADD COLUMN IF NOT EXISTS "approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL';

ALTER TABLE legal_entities DROP CONSTRAINT IF EXISTS "legal_entities_approvalFlow_check";

ALTER TABLE legal_entities ADD CONSTRAINT "legal_entities_approvalFlow_check"
  CHECK ("approvalFlow" IN ('NONE', 'ONE_LEVEL', 'TWO_LEVEL'));
```

Also update the `supabase-full-schema.sql` snapshot.

## Changes by Area

### 1. Entity master data

- **Entities page** (`master/entities/page.tsx`): Approval Flow select gains
  `NONE` → "None (no approval)"; table badge shows "None" for `NONE`; import column
  description updated from `ONE_LEVEL / TWO_LEVEL` to `NONE / ONE_LEVEL / TWO_LEVEL`.
- **APIs** (`api/entities/route.ts`, `api/entities/[id]/route.ts`,
  `api/entities/upload/route.ts`): validation accepts `NONE`.

### 2. Dynamic reviewer/approver dropdowns

Pattern copied from the ad-hoc create page (`compliance/create/page.tsx:167-170`):

| Entity flow | Reviewer dropdown | Approver dropdown |
|---|---|---|
| `NONE` | hidden | hidden |
| `ONE_LEVEL` | shown | hidden |
| `TWO_LEVEL` | shown | shown |

- **Template create** (`master/compliance-templates/create/page.tsx`): add `approvalFlow`
  to the `Entity` interface, compute `selectedEntityFlow` from the effective filing
  entity, conditionally render Reviewer/Approver, and validate accordingly
  (reviewer required for `ONE_LEVEL`/`TWO_LEVEL`; approver required for `TWO_LEVEL`;
  neither for `NONE`).
- **Template edit** (`master/compliance-templates/[id]/edit/page.tsx`): same dynamic
  behavior on save, plus when loading the existing template.
- **Ad-hoc create** (`compliance/create/page.tsx`): reviewer field becomes conditional
  (hidden for `NONE`) and the reviewer-required validation relaxes for `NONE`.

### 3. Approval-chain builders respect `NONE`

New pure helper `src/lib/approval-flow.ts`:

- `type ApprovalFlow = "NONE" | "ONE_LEVEL" | "TWO_LEVEL"`
- `normalizeApprovalFlow(value?: string | null): ApprovalFlow` (falls back to `ONE_LEVEL`)
- `requiresReviewer(flow): boolean` — `ONE_LEVEL` or `TWO_LEVEL`
- `requiresApprover(flow): boolean` — `TWO_LEVEL`
- `buildApprovalRecords(flow, reviewerId?, approverId?): Array<{ approverId, step }>`

Used by:

- `insertGeneratedCompliance` (`lib/template-compliance.ts`): build records via the
  helper; `NONE` yields no records.
- `api/compliance/route.ts` (manual create): skip records for `NONE`, relax the
  reviewer-required validation for `NONE`.
- `api/compliance/import/route.ts`: for `NONE`, no reviewer/approver required and no
  records created.

### 4. Submit auto-approve

`api/compliance/[id]/submit/route.ts`: compute `hasApprovalSteps = approvals.length > 0`.
- If `hasApprovalSteps` → current behavior (`PENDING_APPROVAL`, notify step-1 approvers).
- Else → update status to `APPROVED`, insert an activity entry
  ("APPROVED — no approval required"), skip approver notifications.

Mandatory payment validation still applies in both paths.

## Testing

- Vitest unit tests for `src/lib/approval-flow.ts`: normalization (null/undefined →
  `ONE_LEVEL`), `requiresReviewer` / `requiresApprover` for all three flows, and
  `buildApprovalRecords` for all three flows (including no-op for `NONE`).
- Existing tests must continue to pass; `npx tsc --noEmit` must be clean.

## Scope

Files touched: migration, `supabase-full-schema.sql`, `entities/page.tsx` + 3 entity
APIs, template create + edit pages, ad-hoc create page, `lib/template-compliance.ts`,
`api/compliance/route.ts`, `api/compliance/import/route.ts`,
`api/compliance/[id]/submit/route.ts`, new `lib/approval-flow.ts` (+ test).

No changes to: template detail display, compliance detail approval UI, dashboard/KPI
approval queries (they filter by `approverId`/`step`, unaffected by zero-record rows).
