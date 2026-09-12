# Entity-Driven Approval Flow with "No Approval" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `NONE` (no approval) option to the entity-level approval flow and make the Reviewer/Approver dropdowns on template create/edit, ad-hoc create, and import react dynamically to the effective filing entity's flow, auto-approving compliances that have no approval steps.

**Architecture:** The entity's `legal_entities.approvalFlow` is the single source of truth. A pure helper (`src/lib/approval-flow.ts`) centralizes flow normalization, required-role checks, and approval-record building. Every form resolves the flow from the effective filing entity (`filingEntityId || single selected entity`). The submit route auto-approves when a compliance has zero approval records.

**Tech Stack:** Next.js 16 App Router, Supabase (supabaseAdmin), TypeScript strict, Tailwind + shadcn/ui, Vitest.

## Global Constraints

- Approval flow values are the strings `'NONE' | 'ONE_LEVEL' | 'TWO_LEVEL'` (TEXT column, not a PG enum).
- Default flow for existing/new entities stays `'ONE_LEVEL'`.
- 1-level approval = Reviewer only (step 1). 2-level = Reviewer (step 1) then Approver (step 2). `NONE` = no approval records.
- The entity's flow always wins; templates never store or override approval flow.
- The effective filing entity is `filingEntityId`, else the single selected entity, else none.
- Test command: `npm test` (vitest run). Typecheck: `npx tsc --noEmit`. Lint: `npm run lint`.
- No new dependencies. Follow existing patterns: `supabaseAdmin`, `newId`/`now` from `@/lib/db`, shadcn/ui `Select`, `useToast`.
- Do not add code comments.

---

### Task 1: Approval-flow helper library (TDD)

**Files:**
- Create: `src/lib/approval-flow.ts`
- Create: `src/lib/approval-flow.test.ts`

**Interfaces:**
- Produces (used by every later task):
  - `export type ApprovalFlow = "NONE" | "ONE_LEVEL" | "TWO_LEVEL"`
  - `export interface ApprovalRecord { approverId: string; step: number }`
  - `export const APPROVAL_FLOWS: ApprovalFlow[]`
  - `export const APPROVAL_FLOW_OPTIONS: Array<{ value: ApprovalFlow; label: string }>`
  - `normalizeApprovalFlow(value?: string | null): ApprovalFlow`
  - `requiresReviewer(flow: ApprovalFlow): boolean`
  - `requiresApprover(flow: ApprovalFlow): boolean`
  - `buildApprovalRecords(flow: ApprovalFlow, reviewerId?: string | null, approverId?: string | null): ApprovalRecord[]`

- [ ] **Step 1: Write the failing test**

Create `src/lib/approval-flow.test.ts`:

```ts
import { describe, it, expect } from "vitest"
import {
  normalizeApprovalFlow,
  requiresReviewer,
  requiresApprover,
  buildApprovalRecords,
} from "./approval-flow"

describe("normalizeApprovalFlow", () => {
  it("passes through valid flows", () => {
    expect(normalizeApprovalFlow("NONE")).toBe("NONE")
    expect(normalizeApprovalFlow("ONE_LEVEL")).toBe("ONE_LEVEL")
    expect(normalizeApprovalFlow("TWO_LEVEL")).toBe("TWO_LEVEL")
  })

  it("defaults missing or unknown values to ONE_LEVEL", () => {
    expect(normalizeApprovalFlow(undefined)).toBe("ONE_LEVEL")
    expect(normalizeApprovalFlow(null)).toBe("ONE_LEVEL")
    expect(normalizeApprovalFlow("")).toBe("ONE_LEVEL")
    expect(normalizeApprovalFlow("THREE_LEVEL")).toBe("ONE_LEVEL")
  })
})

describe("requiresReviewer", () => {
  it("requires a reviewer for one- and two-level approval only", () => {
    expect(requiresReviewer("NONE")).toBe(false)
    expect(requiresReviewer("ONE_LEVEL")).toBe(true)
    expect(requiresReviewer("TWO_LEVEL")).toBe(true)
  })
})

describe("requiresApprover", () => {
  it("requires an approver only for two-level approval", () => {
    expect(requiresApprover("NONE")).toBe(false)
    expect(requiresApprover("ONE_LEVEL")).toBe(false)
    expect(requiresApprover("TWO_LEVEL")).toBe(true)
  })
})

describe("buildApprovalRecords", () => {
  it("builds no records for NONE", () => {
    expect(buildApprovalRecords("NONE", "u1", "u2")).toEqual([])
  })

  it("builds a step-1 reviewer record for ONE_LEVEL", () => {
    expect(buildApprovalRecords("ONE_LEVEL", "u1", "u2")).toEqual([
      { approverId: "u1", step: 1 },
    ])
  })

  it("builds reviewer then approver records for TWO_LEVEL", () => {
    expect(buildApprovalRecords("TWO_LEVEL", "u1", "u2")).toEqual([
      { approverId: "u1", step: 1 },
      { approverId: "u2", step: 2 },
    ])
  })

  it("omits records when a required assignee is missing", () => {
    expect(buildApprovalRecords("ONE_LEVEL", "", "u2")).toEqual([])
    expect(buildApprovalRecords("ONE_LEVEL", null, "u2")).toEqual([])
    expect(buildApprovalRecords("TWO_LEVEL", "u1", "")).toEqual([{ approverId: "u1", step: 1 }])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- src/lib/approval-flow.test.ts`
Expected: FAIL — module `./approval-flow` not found.

- [ ] **Step 3: Write the implementation**

Create `src/lib/approval-flow.ts`:

```ts
export type ApprovalFlow = "NONE" | "ONE_LEVEL" | "TWO_LEVEL"

export interface ApprovalRecord {
  approverId: string
  step: number
}

export const APPROVAL_FLOWS: ApprovalFlow[] = ["NONE", "ONE_LEVEL", "TWO_LEVEL"]

export const APPROVAL_FLOW_OPTIONS: Array<{ value: ApprovalFlow; label: string }> = [
  { value: "NONE", label: "None (no approval)" },
  { value: "ONE_LEVEL", label: "One-Level (Reviewer only)" },
  { value: "TWO_LEVEL", label: "Two-Level (Reviewer then Approver)" },
]

export function normalizeApprovalFlow(value?: string | null): ApprovalFlow {
  return APPROVAL_FLOWS.includes(value as ApprovalFlow) ? (value as ApprovalFlow) : "ONE_LEVEL"
}

export function requiresReviewer(flow: ApprovalFlow): boolean {
  return flow === "ONE_LEVEL" || flow === "TWO_LEVEL"
}

export function requiresApprover(flow: ApprovalFlow): boolean {
  return flow === "TWO_LEVEL"
}

export function buildApprovalRecords(
  flow: ApprovalFlow,
  reviewerId?: string | null,
  approverId?: string | null
): ApprovalRecord[] {
  const records: ApprovalRecord[] = []
  if (requiresReviewer(flow) && reviewerId) {
    records.push({ approverId: reviewerId, step: 1 })
  }
  if (requiresApprover(flow) && approverId) {
    records.push({ approverId, step: 2 })
  }
  return records
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- src/lib/approval-flow.test.ts`
Expected: PASS (10 tests). Then run `npm test` to confirm the full suite still passes.

- [ ] **Step 5: Commit**

```bash
git add src/lib/approval-flow.ts src/lib/approval-flow.test.ts
git commit -m "feat: add approval flow helper library"
```

---

### Task 2: Migration allowing NONE + schema snapshot

**Files:**
- Create: `supabase/migrations/20260815010000_entity_approval_flow_none.sql`
- Modify: `supabase-full-schema.sql:118-132`

**Interfaces:**
- Consumes: none.
- Produces: `legal_entities.approvalFlow` constraint accepting `'NONE' | 'ONE_LEVEL' | 'TWO_LEVEL'`.

- [ ] **Step 1: Write the migration**

Create `supabase/migrations/20260815010000_entity_approval_flow_none.sql`:

```sql
ALTER TABLE legal_entities ADD COLUMN IF NOT EXISTS "approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL';

ALTER TABLE legal_entities DROP CONSTRAINT IF EXISTS "legal_entities_approvalFlow_check";

ALTER TABLE legal_entities ADD CONSTRAINT "legal_entities_approvalFlow_check"
  CHECK ("approvalFlow" IN ('NONE', 'ONE_LEVEL', 'TWO_LEVEL'));
```

The migration is idempotent and safe even if `20260814010000_entity_approval_flow.sql` was never applied.

- [ ] **Step 2: Update the schema snapshot**

In `supabase-full-schema.sql`, the `CREATE TABLE "legal_entities"` block currently has:

```
    "currency" TEXT NOT NULL DEFAULT 'USD',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
```

Change it to add the column between currency and createdAt:

```
    "currency" TEXT NOT NULL DEFAULT 'USD',
    "approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
```

Immediately after the line `CREATE UNIQUE INDEX IF NOT EXISTS "legal_entities_orgId_entityNumber_key" ON "legal_entities"("orgId", "entityNumber");`, add:

```sql
ALTER TABLE "legal_entities" ADD CONSTRAINT "legal_entities_approvalFlow_check" CHECK ("approvalFlow" IN ('NONE', 'ONE_LEVEL', 'TWO_LEVEL'));
```

- [ ] **Step 3: Verify**

Run: `npx tsc --noEmit`
Expected: PASS (no type changes yet).

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/20260815010000_entity_approval_flow_none.sql supabase-full-schema.sql
git commit -m "feat: allow NONE approval flow on legal entities"
```

---

### Task 3: Entity APIs accept NONE

**Files:**
- Modify: `src/app/api/entities/route.ts:71-74`
- Modify: `src/app/api/entities/[id]/route.ts:53-55`
- Modify: `src/app/api/entities/upload/route.ts:37-42`

**Interfaces:**
- Consumes: `APPROVAL_FLOWS`, `normalizeApprovalFlow`, `ApprovalFlow` from `@/lib/approval-flow`.
- Produces: entity create/update/upload accept `approvalFlow` values `NONE | ONE_LEVEL | TWO_LEVEL`.

- [ ] **Step 1: Update POST /api/entities**

In `src/app/api/entities/route.ts`, add the import after the existing imports:

```ts
import { APPROVAL_FLOWS, normalizeApprovalFlow, type ApprovalFlow } from "@/lib/approval-flow"
```

Replace lines 71-74:

```ts
    const flow = approvalFlow || "ONE_LEVEL"
    if (!["ONE_LEVEL", "TWO_LEVEL"].includes(flow)) {
      return NextResponse.json({ error: "approvalFlow must be ONE_LEVEL or TWO_LEVEL" }, { status: 400 })
    }
```

with:

```ts
    if (approvalFlow !== undefined && !APPROVAL_FLOWS.includes(approvalFlow as ApprovalFlow)) {
      return NextResponse.json({ error: "approvalFlow must be NONE, ONE_LEVEL, or TWO_LEVEL" }, { status: 400 })
    }
    const flow = normalizeApprovalFlow(approvalFlow)
```

- [ ] **Step 2: Update PUT /api/entities/[id]**

In `src/app/api/entities/[id]/route.ts`, add the same import (plus `normalizeApprovalFlow` is not needed here unless desired; only `APPROVAL_FLOWS` and `ApprovalFlow`).

Replace lines 53-55:

```ts
    if (approvalFlow !== undefined && !["ONE_LEVEL", "TWO_LEVEL"].includes(approvalFlow)) {
      return NextResponse.json({ error: "approvalFlow must be ONE_LEVEL or TWO_LEVEL" }, { status: 400 })
    }
```

with:

```ts
    if (approvalFlow !== undefined && !APPROVAL_FLOWS.includes(approvalFlow as ApprovalFlow)) {
      return NextResponse.json({ error: "approvalFlow must be NONE, ONE_LEVEL, or TWO_LEVEL" }, { status: 400 })
    }
```

- [ ] **Step 3: Update POST /api/entities/upload**

In `src/app/api/entities/upload/route.ts`, add the import:

```ts
import { APPROVAL_FLOWS, normalizeApprovalFlow, type ApprovalFlow } from "@/lib/approval-flow"
```

Replace lines 37-42:

```ts
      const flow = approvalFlow || "ONE_LEVEL"
      if (!["ONE_LEVEL", "TWO_LEVEL"].includes(flow)) {
        skipped++
        errors.push(`Invalid approvalFlow for ${entityNumber}; must be ONE_LEVEL or TWO_LEVEL`)
        continue
      }
```

with:

```ts
      if (approvalFlow !== undefined && !APPROVAL_FLOWS.includes(approvalFlow as ApprovalFlow)) {
        skipped++
        errors.push(`Invalid approvalFlow for ${entityNumber}; must be NONE, ONE_LEVEL, or TWO_LEVEL`)
        continue
      }
      const flow = normalizeApprovalFlow(approvalFlow)
```

The rest of the upload route (update/insert using `flow`) is unchanged.

- [ ] **Step 4: Verify**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/app/api/entities/route.ts "src/app/api/entities/[id]/route.ts" src/app/api/entities/upload/route.ts
git commit -m "feat: accept NONE approval flow in entity APIs"
```

---

### Task 4: Entities page — NONE option, badge, import description

**Files:**
- Modify: `src/app/master/entities/page.tsx:208` (import column description)
- Modify: `src/app/master/entities/page.tsx:273-275` (badge)
- Modify: `src/app/master/entities/page.tsx:373-376` (form select options)

**Interfaces:**
- Consumes: none (labels are inline).
- Produces: user-facing ability to set an entity to "None (no approval)".

- [ ] **Step 1: Update the import column description**

At line 208, change:

```tsx
                { key: "approvalFlow", label: "Approval Flow", description: "ONE_LEVEL / TWO_LEVEL" },
```

to:

```tsx
                { key: "approvalFlow", label: "Approval Flow", description: "NONE / ONE_LEVEL / TWO_LEVEL" },
```

- [ ] **Step 2: Update the table badge**

At lines 273-275, change:

```tsx
                        <Badge variant={item.approvalFlow === "TWO_LEVEL" ? "default" : "secondary"}>
                          {item.approvalFlow === "TWO_LEVEL" ? "Two-Level" : "One-Level"}
                        </Badge>
```

to:

```tsx
                        <Badge variant={item.approvalFlow === "TWO_LEVEL" ? "default" : item.approvalFlow === "NONE" ? "outline" : "secondary"}>
                          {item.approvalFlow === "TWO_LEVEL" ? "Two-Level" : item.approvalFlow === "NONE" ? "None" : "One-Level"}
                        </Badge>
```

- [ ] **Step 3: Add the NONE option to the form select**

At lines 373-376, change:

```tsx
                  <SelectContent>
                    <SelectItem value="ONE_LEVEL">One-Level (Reviewer only)</SelectItem>
                    <SelectItem value="TWO_LEVEL">Two-Level (Reviewer then Approver)</SelectItem>
                  </SelectContent>
```

to:

```tsx
                  <SelectContent>
                    <SelectItem value="NONE">None (no approval)</SelectItem>
                    <SelectItem value="ONE_LEVEL">One-Level (Reviewer only)</SelectItem>
                    <SelectItem value="TWO_LEVEL">Two-Level (Reviewer then Approver)</SelectItem>
                  </SelectContent>
```

- [ ] **Step 4: Verify**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/app/master/entities/page.tsx
git commit -m "feat: add no-approval option to entity master data"
```

---

### Task 5: Approval-chain builders respect NONE

**Files:**
- Modify: `src/lib/template-compliance.ts:91-122`
- Modify: `src/app/api/compliance/route.ts:229-237,291-294`
- Modify: `src/app/api/compliance/import/route.ts:118-132,191-211`
- Modify: `src/app/api/compliance/[id]/route.ts:285-309`

**Interfaces:**
- Consumes: `normalizeApprovalFlow`, `requiresReviewer`, `requiresApprover`, `buildApprovalRecords`, `ApprovalFlow` from `@/lib/approval-flow` (Task 1).
- Produces: manual creation, import, template generation, and compliance edit all create approval records per the resolved entity flow (zero records for `NONE`).

- [ ] **Step 1: Update `insertGeneratedCompliance`**

In `src/lib/template-compliance.ts`, add the import after the existing `@/lib/compliance-period` import:

```ts
import { buildApprovalRecords, normalizeApprovalFlow, type ApprovalFlow } from "@/lib/approval-flow"
```

Replace the block at lines 91-122:

```ts
  const filingEntityId = template.filingEntityId || entityIds[0] || null
  let approvalFlow = "ONE_LEVEL"
  if (filingEntityId) {
    const { data: entity } = await supabaseAdmin
      .from("legal_entities")
      .select("approvalFlow")
      .eq("id", filingEntityId)
      .maybeSingle()
    approvalFlow = (entity?.approvalFlow as string) || "ONE_LEVEL"
  }

  const approvalRecords: Array<{ approverId: string; step: number }> = []
  if (template.complianceReviewerId) {
    approvalRecords.push({ approverId: template.complianceReviewerId, step: 1 })
  }
  if (approvalFlow === "TWO_LEVEL" && template.approverId) {
    approvalRecords.push({ approverId: template.approverId, step: 2 })
  }

  if (approvalRecords.length > 0) {
    const { error: approvalError } = await supabaseAdmin.from("compliance_approvals").insert(
      approvalRecords.map((record) => ({
        id: newId(),
        complianceId: scheduleId,
        approverId: record.approverId,
        step: record.step,
        status: "PENDING_APPROVAL",
        updatedAt: now(),
      }))
    )
    if (approvalError) throw approvalError
  }
```

with:

```ts
  const filingEntityId = template.filingEntityId || entityIds[0] || null
  let approvalFlow: ApprovalFlow = "ONE_LEVEL"
  if (filingEntityId) {
    const { data: entity } = await supabaseAdmin
      .from("legal_entities")
      .select("approvalFlow")
      .eq("id", filingEntityId)
      .maybeSingle()
    approvalFlow = normalizeApprovalFlow(entity?.approvalFlow as string | undefined)
  }

  const approvalRecords = buildApprovalRecords(
    approvalFlow,
    template.complianceReviewerId,
    template.approverId
  )

  if (approvalRecords.length > 0) {
    const { error: approvalError } = await supabaseAdmin.from("compliance_approvals").insert(
      approvalRecords.map((record) => ({
        id: newId(),
        complianceId: scheduleId,
        approverId: record.approverId,
        step: record.step,
        status: "PENDING_APPROVAL",
        updatedAt: now(),
      }))
    )
    if (approvalError) throw approvalError
  }
```

- [ ] **Step 2: Update manual create POST /api/compliance**

In `src/app/api/compliance/route.ts`, add the import:

```ts
import {
  buildApprovalRecords,
  normalizeApprovalFlow,
  requiresApprover,
  requiresReviewer,
} from "@/lib/approval-flow"
```

Replace lines 229-237:

```ts
    const reviewerId = bodyReviewerId || ""
    const approverId = bodyApproverId || ""

    if (!reviewerId) {
      return NextResponse.json({ error: "reviewerId is required" }, { status: 400 })
    }
    if (approvalFlow === "TWO_LEVEL" && !approverId) {
      return NextResponse.json({ error: "approverId is required for two-level approval" }, { status: 400 })
    }
```

with:

```ts
    const reviewerId = bodyReviewerId || ""
    const approverId = bodyApproverId || ""
    const flow = normalizeApprovalFlow(approvalFlow)

    if (requiresReviewer(flow) && !reviewerId) {
      return NextResponse.json({ error: "reviewerId is required for this approval flow" }, { status: 400 })
    }
    if (requiresApprover(flow) && !approverId) {
      return NextResponse.json({ error: "approverId is required for two-level approval" }, { status: 400 })
    }
```

Replace lines 291-294:

```ts
    const approvalRecords = [
      { approverId: reviewerId, step: 1 },
      ...(approvalFlow === "TWO_LEVEL" ? [{ approverId: approverId, step: 2 }] : []),
    ]
```

with:

```ts
    const approvalRecords = buildApprovalRecords(flow, reviewerId, approverId)
```

- [ ] **Step 3: Update POST /api/compliance/import**

In `src/app/api/compliance/import/route.ts`, add the import:

```ts
import {
  buildApprovalRecords,
  normalizeApprovalFlow,
  requiresApprover,
  requiresReviewer,
} from "@/lib/approval-flow"
```

Replace lines 118-132:

```ts
      const flow = entity.approvalFlow

      if (flow === "TWO_LEVEL") {
        if (!reviewerId || !approverId) {
          skipped++
          errors.push(`Reviewer and approver are required for ${rowLabel} (two-level approval)`)
          continue
        }
      } else {
        if (!reviewerId) {
          skipped++
          errors.push(`Reviewer is required for ${rowLabel} (one-level approval)`)
          continue
        }
      }
```

with:

```ts
      const flow = normalizeApprovalFlow(entity.approvalFlow)

      if (requiresApprover(flow) && (!reviewerId || !approverId)) {
        skipped++
        errors.push(`Reviewer and approver are required for ${rowLabel} (two-level approval)`)
        continue
      }
      if (requiresReviewer(flow) && !reviewerId) {
        skipped++
        errors.push(`Reviewer is required for ${rowLabel} (one-level approval)`)
        continue
      }
```

Replace lines 191-211:

```ts
      const approvalRecords: Array<{ approverId: string; step: number }> = [{ approverId: reviewerId as string, step: 1 }]
      if (flow === "TWO_LEVEL") {
        approvalRecords.push({ approverId: approverId as string, step: 2 })
      }

      const { error: approvalError } = await supabaseAdmin.from("compliance_approvals").insert(
        approvalRecords.map((record) => ({
          id: newId(),
          complianceId: scheduleId,
          approverId: record.approverId,
          step: record.step,
          status: "PENDING_APPROVAL",
          updatedAt: now(),
        }))
      )

      if (approvalError) {
        skipped++
        errors.push(`Approval setup failed for ${rowLabel}: ${approvalError.message}`)
        continue
      }
```

with:

```ts
      const approvalRecords = buildApprovalRecords(flow, reviewerId, approverId)

      if (approvalRecords.length > 0) {
        const { error: approvalError } = await supabaseAdmin.from("compliance_approvals").insert(
          approvalRecords.map((record) => ({
            id: newId(),
            complianceId: scheduleId,
            approverId: record.approverId,
            step: record.step,
            status: "PENDING_APPROVAL",
            updatedAt: now(),
          }))
        )

        if (approvalError) {
          skipped++
          errors.push(`Approval setup failed for ${rowLabel}: ${approvalError.message}`)
          continue
        }
      }
```

- [ ] **Step 4: Update compliance edit PUT /api/compliance/[id]**

In `src/app/api/compliance/[id]/route.ts`, add the import:

```ts
import { buildApprovalRecords, normalizeApprovalFlow } from "@/lib/approval-flow"
```

Replace lines 285-309:

```ts
      const approvalRecords: Array<{ approverId: string; step: number }> = [{ approverId: reviewerId, step: 1 }]
      if (approvalFlow === "TWO_LEVEL" && approverId) {
        approvalRecords.push({ approverId: approverId, step: 2 })
      }

      const { error: createApprovalError } = await supabaseAdmin
        .from("compliance_approvals")
        .insert(
          approvalRecords.map((record) => ({
            id: newId(),
            complianceId: id,
            approverId: record.approverId,
            step: record.step,
            status: "PENDING_APPROVAL",
            updatedAt: now(),
          }))
        )

      if (createApprovalError) throw createApprovalError

      if (orgId) {
        for (const record of approvalRecords) {
          await ensureOrgMember(orgId, record.approverId, record.step === 1 ? ["REVIEWER"] : ["APPROVER"])
        }
      }
```

with:

```ts
      const flow = normalizeApprovalFlow(approvalFlow)
      const approvalRecords = buildApprovalRecords(flow, reviewerId, approverId)

      if (approvalRecords.length > 0) {
        const { error: createApprovalError } = await supabaseAdmin
          .from("compliance_approvals")
          .insert(
            approvalRecords.map((record) => ({
              id: newId(),
              complianceId: id,
              approverId: record.approverId,
              step: record.step,
              status: "PENDING_APPROVAL",
              updatedAt: now(),
            }))
          )

        if (createApprovalError) throw createApprovalError

        if (orgId) {
          for (const record of approvalRecords) {
            await ensureOrgMember(orgId, record.approverId, record.step === 1 ? ["REVIEWER"] : ["APPROVER"])
          }
        }
      }
```

The existing `delete` of `compliance_approvals` (lines 278-283) still runs before this block; when the flow is `NONE` the delete leaves the compliance with no approvals and the insert is skipped.

- [ ] **Step 5: Verify**

Run: `npm test` (full suite) and `npx tsc --noEmit`
Expected: All tests pass, typecheck clean.

- [ ] **Step 6: Commit**

```bash
git add src/lib/template-compliance.ts src/app/api/compliance/route.ts src/app/api/compliance/import/route.ts "src/app/api/compliance/[id]/route.ts"
git commit -m "feat: respect NONE approval flow when building approval chains"
```

---

### Task 6: Submit auto-approves when there are no approval steps

**Files:**
- Modify: `src/app/api/compliance/[id]/submit/route.ts:81-157`

**Interfaces:**
- Consumes: none new (uses `existing.approvals` already fetched at line 34).
- Produces: submitting a compliance with zero approval records transitions it to `APPROVED` instead of `PENDING_APPROVAL`.

- [ ] **Step 1: Compute the target status**

In `src/app/api/compliance/[id]/submit/route.ts`, after the `existing` null-check (after line 49), add:

```ts
    const hasApprovalSteps = (existing.approvals || []).length > 0
    const nextStatus = hasApprovalSteps ? "PENDING_APPROVAL" : "APPROVED"
```

- [ ] **Step 2: Use the target status in the update**

Change the update at lines 81-93 so `status: nextStatus` instead of `status: "PENDING_APPROVAL"`:

```ts
      .update({
        status: nextStatus,
        submittedAt: new Date().toISOString(),
        filingType,
        refundType: resolvedRefundType,
        paymentCurrency: currency,
        paymentAmount: amount,
      })
```

- [ ] **Step 3: Update the activity message**

At lines 112-122, change the activity insert to use `nextStatus` and a flow-specific comment:

```ts
        fromStatus: existing.status,
        toStatus: nextStatus,
        comments: hasApprovalSteps
          ? "Compliance submitted for approval"
          : "Compliance submitted and auto-approved (no approval required)",
```

- [ ] **Step 4: Update the audit entry**

At line 135, change `newValue: "PENDING_APPROVAL"` to:

```ts
        newValue: nextStatus,
```

- [ ] **Step 5: Guard the approver notifications**

At line 142, change:

```ts
    if (stepOneApprovals.length > 0) {
```

to:

```ts
    if (hasApprovalSteps && stepOneApprovals.length > 0) {
```

- [ ] **Step 6: Verify**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add "src/app/api/compliance/[id]/submit/route.ts"
git commit -m "feat: auto-approve submissions with no approval steps"
```

---

### Task 7: Ad-hoc create page — dynamic reviewer field

**Files:**
- Modify: `src/app/compliance/create/page.tsx` (imports, validation at lines 226-249, reviewer select at lines 537-556)

**Interfaces:**
- Consumes: `normalizeApprovalFlow`, `requiresReviewer`, `requiresApprover` from `@/lib/approval-flow`.
- Produces: reviewer required/shown only for `ONE_LEVEL`/`TWO_LEVEL`; approver required/shown only for `TWO_LEVEL`.

- [ ] **Step 1: Add the import**

After the `TAX_TYPE_OPTIONS` import (line 38), add:

```ts
import { normalizeApprovalFlow, requiresApprover, requiresReviewer } from "@/lib/approval-flow"
```

- [ ] **Step 2: Compute the normalized flow**

The `selectedEntityFlow` memo already exists at lines 167-170. After it (before `effectivePreparerId`), add:

```ts
  const flow = normalizeApprovalFlow(selectedEntityFlow)
```

- [ ] **Step 3: Relax the validation**

Replace lines 234-249:

```ts
    if (!reviewerId) {
      toast({
        title: "Validation Error",
        description: "Please select a reviewer",
        variant: "destructive",
      })
      return
    }
    if (selectedEntityFlow === "TWO_LEVEL" && !approverId) {
      toast({
        title: "Validation Error",
        description: "Please select an approver for two-level approval",
        variant: "destructive",
      })
      return
    }
```

with:

```ts
    if (requiresReviewer(flow) && !reviewerId) {
      toast({
        title: "Validation Error",
        description: "Please select a reviewer",
        variant: "destructive",
      })
      return
    }
    if (requiresApprover(flow) && !approverId) {
      toast({
        title: "Validation Error",
        description: "Please select an approver for two-level approval",
        variant: "destructive",
      })
      return
    }
```

The existing `if (!selectedEntityFlow)` guard (lines 226-233) stays, so an entity must still be selected before submission.

- [ ] **Step 4: Hide the reviewer select for NONE**

Wrap the reviewer field (currently lines 537-556, the `<div className="space-y-2">` containing the Reviewer `Select`) so it only renders when a reviewer is required:

```tsx
              {requiresReviewer(flow) && (
                <div className="space-y-2">
                  <Label htmlFor="reviewer">
                    Reviewer <span className="text-red-500">*</span>
                  </Label>
                  <Select value={reviewerId} onValueChange={setReviewerId}>
                    <SelectTrigger id="reviewer">
                      <SelectValue placeholder="Select reviewer" />
                    </SelectTrigger>
                    <SelectContent>
                      {reviewerOptions.map((r) => (
                        <SelectItem key={r.id} value={r.id}>
                          {r.name} ({r.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {reviewerOptions.length === 0 && (
                    <p className="text-xs text-[var(--color-muted-foreground)]">No reviewers available</p>
                  )}
                </div>
              )}
```

The Approver field (lines 558-579) already renders conditionally on `selectedEntityFlow === "TWO_LEVEL"`; switch that condition to `requiresApprover(flow)` for consistency:

```tsx
              {requiresApprover(flow) && (
```

- [ ] **Step 5: Verify**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/app/compliance/create/page.tsx
git commit -m "feat: dynamic reviewer/approver fields on ad-hoc compliance create"
```

---

### Task 8: Template create page — dynamic reviewer/approver dropdowns

**Files:**
- Modify: `src/app/master/compliance-templates/create/page.tsx` (Entity interface at lines 34-39, flow computation near line 138, validation at lines 191-225, reviewer/approver fields at lines 488-524)

**Interfaces:**
- Consumes: `normalizeApprovalFlow`, `requiresReviewer`, `requiresApprover` from `@/lib/approval-flow`.
- Produces: template create shows Reviewer only for `ONE_LEVEL`/`TWO_LEVEL` and Approver only for `TWO_LEVEL`, based on the effective filing entity's flow.

- [ ] **Step 1: Add the import**

After the `TAX_TYPE_OPTIONS` import (line 26), add:

```ts
import { normalizeApprovalFlow, requiresApprover, requiresReviewer } from "@/lib/approval-flow"
```

- [ ] **Step 2: Add approvalFlow to the Entity interface**

At lines 34-39, add the field:

```ts
interface Entity {
  id: string
  entityName: string
  entityNumber: string
  approvalFlow?: string
  country?: { id: string; name: string; code: string } | null
}
```

- [ ] **Step 3: Compute the effective filing entity and flow**

After `const effectivePreparerId = ...` (line 138), add:

```ts
  const effectiveFilingEntityId =
    filingEntityId && entityIds.includes(filingEntityId)
      ? filingEntityId
      : entityIds.length === 1
        ? entityIds[0]
        : ""

  const selectedEntityFlow = useMemo(() => {
    if (!effectiveFilingEntityId) return ""
    return entities.find((e) => e.id === effectiveFilingEntityId)?.approvalFlow || ""
  }, [entities, effectiveFilingEntityId])

  const flow = normalizeApprovalFlow(selectedEntityFlow)
```

- [ ] **Step 4: Add flow-based validation**

In `handleSubmit`, after the filing-entity check (after line 208), add:

```ts
    if (requiresReviewer(flow) && !complianceReviewerId) {
      toast({
        title: "Validation Error",
        description: "Please select a reviewer",
        variant: "destructive",
      })
      return
    }
    if (requiresApprover(flow) && !approverId) {
      toast({
        title: "Validation Error",
        description: "Please select an approver for two-level approval",
        variant: "destructive",
      })
      return
    }
```

- [ ] **Step 5: Conditionally render the Reviewer and Approver fields**

Wrap the Reviewer field (lines 488-505) so it renders only when a reviewer is required:

```tsx
              {requiresReviewer(flow) && (
                <div className="space-y-2">
                  <Label htmlFor="complianceReviewer">Reviewer</Label>
                  <Select value={complianceReviewerId} onValueChange={setComplianceReviewerId}>
                    <SelectTrigger id="complianceReviewer">
                      <SelectValue placeholder="Select reviewer" />
                    </SelectTrigger>
                    <SelectContent>
                      {reviewerOptions.map((r) => (
                        <SelectItem key={r.id} value={r.id}>
                          {r.name} ({r.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-[var(--color-muted-foreground)]">
                    Reviewers step-1 approvals on generated compliances.
                  </p>
                </div>
              )}
```

Wrap the Approver field (lines 507-524) so it renders only for two-level approval:

```tsx
              {requiresApprover(flow) && (
                <div className="space-y-2">
                  <Label htmlFor="approver">Approver</Label>
                  <Select value={approverId} onValueChange={setApproverId}>
                    <SelectTrigger id="approver">
                      <SelectValue placeholder="Select approver" />
                    </SelectTrigger>
                    <SelectContent>
                      {approverOptions.map((a) => (
                        <SelectItem key={a.id} value={a.id}>
                          {a.name} ({a.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {approverOptions.length === 0 && (
                    <p className="text-xs text-[var(--color-muted-foreground)]">No approvers available</p>
                  )}
                </div>
              )}
```

- [ ] **Step 6: Verify**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/app/master/compliance-templates/create/page.tsx
git commit -m "feat: dynamic reviewer/approver dropdowns on template create"
```

---

### Task 9: Template edit page — dynamic reviewer/approver dropdowns

**Files:**
- Modify: `src/app/master/compliance-templates/[id]/edit/page.tsx` (Entity interface at lines 38-43, flow computation, validation in `handleSubmit` at lines 263-296, reviewer/approver fields at lines 618-654)

**Interfaces:**
- Consumes: `normalizeApprovalFlow`, `requiresReviewer`, `requiresApprover` from `@/lib/approval-flow`.
- Produces: template edit shows the same dynamic reviewer/approver behavior as create.

- [ ] **Step 1: Add the import**

After the `TAX_TYPE_OPTIONS` import (line 30), add:

```ts
import { normalizeApprovalFlow, requiresApprover, requiresReviewer } from "@/lib/approval-flow"
```

- [ ] **Step 2: Add approvalFlow to the Entity interface**

At lines 38-43, add the field:

```ts
interface Entity {
  id: string
  entityName: string
  entityNumber: string
  approvalFlow?: string
  country?: { id: string; name: string; code: string } | null
}
```

- [ ] **Step 3: Compute the effective filing entity and flow**

After the `reviewerOptions` memo (line 183), add:

```ts
  const effectiveFilingEntityId =
    filingEntityId && entityIds.includes(filingEntityId)
      ? filingEntityId
      : entityIds.length === 1
        ? entityIds[0]
        : ""

  const selectedEntityFlow = useMemo(() => {
    if (!effectiveFilingEntityId) return ""
    return entities.find((e) => e.id === effectiveFilingEntityId)?.approvalFlow || ""
  }, [entities, effectiveFilingEntityId])

  const flow = normalizeApprovalFlow(selectedEntityFlow)
```

- [ ] **Step 4: Add flow-based validation**

In `handleSubmit`, after the filing-entity check (after line 280), add:

```ts
    if (requiresReviewer(flow) && !complianceReviewerId) {
      toast({
        title: "Validation Error",
        description: "Please select a reviewer",
        variant: "destructive",
      })
      return
    }
    if (requiresApprover(flow) && !approverId) {
      toast({
        title: "Validation Error",
        description: "Please select an approver for two-level approval",
        variant: "destructive",
      })
      return
    }
```

- [ ] **Step 5: Conditionally render the Reviewer and Approver fields**

Wrap the Reviewer field (lines 618-635) so it renders only when a reviewer is required (preserving `disabled={readOnly}`):

```tsx
              {requiresReviewer(flow) && (
                <div className="space-y-2">
                  <Label htmlFor="complianceReviewer">Reviewer</Label>
                  <Select value={complianceReviewerId} onValueChange={setComplianceReviewerId} disabled={readOnly}>
                    <SelectTrigger id="complianceReviewer">
                      <SelectValue placeholder="Select reviewer" />
                    </SelectTrigger>
                    <SelectContent>
                      {reviewerOptions.map((r) => (
                        <SelectItem key={r.id} value={r.id}>
                          {r.name} ({r.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {reviewerOptions.length === 0 && (
                    <p className="text-xs text-[var(--color-muted-foreground)]">No reviewers available</p>
                  )}
                </div>
              )}
```

Wrap the Approver field (lines 637-654) so it renders only for two-level approval (preserving `disabled={readOnly}`):

```tsx
              {requiresApprover(flow) && (
                <div className="space-y-2">
                  <Label htmlFor="approver">Approver</Label>
                  <Select value={approverId} onValueChange={setApproverId} disabled={readOnly}>
                    <SelectTrigger id="approver">
                      <SelectValue placeholder="Select approver" />
                    </SelectTrigger>
                    <SelectContent>
                      {approverOptions.map((a) => (
                        <SelectItem key={a.id} value={a.id}>
                          {a.name} ({a.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {approverOptions.length === 0 && (
                    <p className="text-xs text-[var(--color-muted-foreground)]">No approvers available</p>
                  )}
                </div>
              )}
```

- [ ] **Step 6: Verify**

Run: `npx tsc --noEmit` and `npm test`
Expected: Typecheck clean, all tests pass.

- [ ] **Step 7: Commit**

```bash
git add "src/app/master/compliance-templates/[id]/edit/page.tsx"
git commit -m "feat: dynamic reviewer/approver dropdowns on template edit"
```

---

## Post-Implementation Verification

1. Run `npm test` — all tests pass (existing + new `approval-flow` tests).
2. Run `npx tsc --noEmit` — clean.
3. Run `npm run lint` — clean for changed files.
4. Manual check: set an entity to "None (no approval)" in master data; create a template for it — no Reviewer/Approver dropdowns appear. Create a template for a `TWO_LEVEL` entity — both appear. Submit a generated compliance for the `NONE` entity — it transitions straight to `APPROVED`.
