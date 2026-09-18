# Form-Level Approval Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a mandatory approval flow to the form master, make the form's flow take precedence over the entity's flow when building compliance approval chains, drive reviewer/approver dropdowns from the effective flow, and show a soft mismatch warning on the compliance detail page.

**Architecture:** `form_master` gains an `approvalFlow` column. A pure helper `effectiveApprovalFlow(formFlow, entityFlow)` resolves the flow as form-wins-with-entity-fallback. Compliance builders (template generation, manual create, compliance edit) use that helper; the four create/edit pages compute it in-memory for dropdown visibility; the compliance detail API exposes both flows and the detail page renders an amber warning below the filing entity when they differ.

**Tech Stack:** Next.js 16 (App Router), React 19, Supabase (admin client), Radix UI Select/Dialog, Tailwind, Prisma, Vitest.

## Global Constraints

- Approval flow values are exactly `NONE`, `ONE_LEVEL`, `TWO_LEVEL` (from `src/lib/approval-flow.ts`).
- The form's flow wins when a form is linked; the entity's flow is the fallback when there is no form.
- The warning is display-only and never blocks saving or submission.
- Only the filing entity (`compliance_schedules.entityId`) is compared.
- Import route (`api/compliance/import/route.ts`) is NOT modified — imports link no form.
- No new dependencies. Follow existing code style (no added comments).
- After each task: run `npx tsc --noEmit` and `npm run lint`; after Task 2 also `npm test`.
- Existing tests must keep passing.

---

### Task 1: Database migration, schema snapshot, Prisma model

**Files:**
- Create: `supabase/migrations/20260816010000_form_approval_flow.sql`
- Modify: `supabase-full-schema.sql:155-168` (form_master CREATE TABLE)
- Modify: `prisma/schema.prisma` (FormMaster model, near line 345)

**Interfaces:**
- Produces: DB column `form_master."approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL'` with a CHECK constraint — consumed by every later task.

- [ ] **Step 1: Create the migration**

Create `supabase/migrations/20260816010000_form_approval_flow.sql`:

```sql
ALTER TABLE form_master ADD COLUMN IF NOT EXISTS "approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL';

ALTER TABLE form_master DROP CONSTRAINT IF EXISTS "form_master_approvalFlow_check";

ALTER TABLE form_master ADD CONSTRAINT "form_master_approvalFlow_check"
  CHECK ("approvalFlow" IN ('NONE', 'ONE_LEVEL', 'TWO_LEVEL'));
```

- [ ] **Step 2: Update the full-schema snapshot**

In `supabase-full-schema.sql`, inside `CREATE TABLE "form_master"`, add the column after the `requiresPayment` line (line 164):

```sql
    "requiresPayment" BOOLEAN NOT NULL DEFAULT true,
    "approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL',
```

The seed `INSERT INTO "form_master"` (line 551) is untouched — new rows get the column default.

- [ ] **Step 3: Update the Prisma model**

In `prisma/schema.prisma`, add the field to `model FormMaster` right after `description`:

```prisma
  description      String?
  approvalFlow     String         @default("ONE_LEVEL")
  createdAt        DateTime       @default(now())
```

- [ ] **Step 4: Verify compile + lint**

Run: `npx tsc --noEmit`
Expected: clean.

Run: `npm run lint`
Expected: no new errors (pre-existing warnings are acceptable if they were there before).

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/20260816010000_form_approval_flow.sql supabase-full-schema.sql prisma/schema.prisma
git commit -m "feat(schema): approvalFlow column on form_master"
```

---

### Task 2: `effectiveApprovalFlow` helper + unit tests

**Files:**
- Modify: `src/lib/approval-flow.ts`
- Test: `src/lib/approval-flow.test.ts`

**Interfaces:**
- Produces: `export function effectiveApprovalFlow(formFlow?: string | null, entityFlow?: string | null): ApprovalFlow` — returns `normalizeApprovalFlow(formFlow)` when `formFlow` is a valid flow, else `normalizeApprovalFlow(entityFlow)`.

- [ ] **Step 1: Write the failing tests**

Append to `src/lib/approval-flow.test.ts` and add `effectiveApprovalFlow` to the import at the top:

```ts
describe("effectiveApprovalFlow", () => {
  it("uses the form flow when set", () => {
    expect(effectiveApprovalFlow("TWO_LEVEL", "NONE")).toBe("TWO_LEVEL")
    expect(effectiveApprovalFlow("NONE", "TWO_LEVEL")).toBe("NONE")
    expect(effectiveApprovalFlow("ONE_LEVEL", "ONE_LEVEL")).toBe("ONE_LEVEL")
  })

  it("falls back to the entity flow when the form flow is unset", () => {
    expect(effectiveApprovalFlow(undefined, "TWO_LEVEL")).toBe("TWO_LEVEL")
    expect(effectiveApprovalFlow(null, "NONE")).toBe("NONE")
    expect(effectiveApprovalFlow("", "ONE_LEVEL")).toBe("ONE_LEVEL")
  })

  it("defaults to ONE_LEVEL when neither is set", () => {
    expect(effectiveApprovalFlow(undefined, undefined)).toBe("ONE_LEVEL")
    expect(effectiveApprovalFlow(null, null)).toBe("ONE_LEVEL")
  })

  it("ignores an invalid form flow value", () => {
    expect(effectiveApprovalFlow("THREE_LEVEL", "NONE")).toBe("NONE")
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npx vitest run src/lib/approval-flow.test.ts`
Expected: FAIL — `effectiveApprovalFlow is not a function`.

- [ ] **Step 3: Implement the helper**

Add to `src/lib/approval-flow.ts`:

```ts
export function effectiveApprovalFlow(
  formFlow?: string | null,
  entityFlow?: string | null
): ApprovalFlow {
  if (formFlow && APPROVAL_FLOWS.includes(formFlow as ApprovalFlow)) {
    return formFlow as ApprovalFlow
  }
  return normalizeApprovalFlow(entityFlow)
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npx vitest run src/lib/approval-flow.test.ts`
Expected: PASS (all suites).

- [ ] **Step 5: Verify compile + lint**

Run: `npx tsc --noEmit`; Expected: clean.
Run: `npm run lint`; Expected: no new errors.

- [ ] **Step 6: Commit**

```bash
git add src/lib/approval-flow.ts src/lib/approval-flow.test.ts
git commit -m "feat(approval-flow): effectiveApprovalFlow helper"
```

---

### Task 3: Forms APIs carry `approvalFlow`

**Files:**
- Modify: `src/app/api/forms/route.ts`
- Modify: `src/app/api/forms/[id]/route.ts`
- Modify: `src/app/api/forms/upload/route.ts`

**Interfaces:**
- Consumes: `APPROVAL_FLOWS`, `ApprovalFlow` from `@/lib/approval-flow` (Task 2 already shipped `APPROVAL_FLOWS`; it exists at `src/lib/approval-flow.ts:8`).
- Produces: `GET /api/forms`, `POST /api/forms`, `GET/PUT /api/forms/[id]`, `POST /api/forms/upload` all accept/return `approvalFlow: "NONE" | "ONE_LEVEL" | "TWO_LEVEL"`.

- [ ] **Step 1: Update `api/forms/route.ts`**

1. Import the flow constants:

```ts
import { APPROVAL_FLOWS, type ApprovalFlow } from "@/lib/approval-flow"
```

2. GET (line 26) — add `approvalFlow` to the select:

```ts
      .select("id, formNumber, formName, taxType, description, requiresPayment, approvalFlow, complianceTypeId, complianceType:compliance_types(id, name, taxType)")
```

3. POST — add `approvalFlow` to the destructure (line 70) and validate before the insert (after the existing `if (!formNumber || !formName)` block):

```ts
    const { formNumber, formName, taxType, description, complianceTypeId, requiresPayment, approvalFlow } = body
```

```ts
    if (approvalFlow !== undefined && !APPROVAL_FLOWS.includes(approvalFlow as ApprovalFlow)) {
      return NextResponse.json({ error: "approvalFlow must be NONE, ONE_LEVEL, or TWO_LEVEL" }, { status: 400 })
    }
```

4. POST — include it in the insert (line 99) and in the `.select(...)` (line 102):

```ts
        requiresPayment: requiresPayment === undefined ? true : requiresPayment === true,
        approvalFlow: approvalFlow || "ONE_LEVEL",
```

```ts
      .select("id, formNumber, formName, taxType, description, requiresPayment, approvalFlow, complianceTypeId, complianceType:compliance_types(id, name, taxType)")
```

- [ ] **Step 2: Update `api/forms/[id]/route.ts`**

1. Import the flow constants:

```ts
import { APPROVAL_FLOWS, type ApprovalFlow } from "@/lib/approval-flow"
```

2. GET (line 21) and PUT `.select(...)` (line 94) — add `approvalFlow`:

```ts
      .select("id, formNumber, formName, taxType, description, requiresPayment, approvalFlow, complianceTypeId, complianceType:compliance_types(id, name, taxType)")
```

3. PUT — add `approvalFlow` to the destructure (line 52), validate, and add to `updateData`:

```ts
    const { formNumber, formName, taxType, description, complianceTypeId, requiresPayment, approvalFlow } = body
```

```ts
    if (approvalFlow !== undefined && !APPROVAL_FLOWS.includes(approvalFlow as ApprovalFlow)) {
      return NextResponse.json({ error: "approvalFlow must be NONE, ONE_LEVEL, or TWO_LEVEL" }, { status: 400 })
    }
```

```ts
    if (approvalFlow !== undefined) updateData.approvalFlow = approvalFlow
```

- [ ] **Step 3: Update `api/forms/upload/route.ts`**

1. Import the flow constants:

```ts
import { APPROVAL_FLOWS, type ApprovalFlow } from "@/lib/approval-flow"
```

2. In the loop (line 29), destructure `approvalFlow` and normalize/validate it (insert right after the `requiresPayment` destructure):

```ts
      const { formNumber, formName, taxType, description, complianceTypeId, requiresPayment, approvalFlow } = item
      const normalizedApprovalFlow = approvalFlow ? String(approvalFlow).trim().toUpperCase() : "ONE_LEVEL"
```

```ts
      if (!APPROVAL_FLOWS.includes(normalizedApprovalFlow as ApprovalFlow)) {
        skipped++
        errors.push(`Invalid approvalFlow for ${formNumber || "unknown"}; must be NONE, ONE_LEVEL, or TWO_LEVEL`)
        continue
      }
```

3. Add to the update branch (after `if (requiresPayment !== undefined) updateData.requiresPayment = ...`):

```ts
        if (approvalFlow !== undefined) updateData.approvalFlow = normalizedApprovalFlow
```

4. Add to the insert branch (after `requiresPayment: normalizedRequiresPayment,`):

```ts
            approvalFlow: normalizedApprovalFlow,
```

- [ ] **Step 4: Verify compile + lint**

Run: `npx tsc --noEmit`; Expected: clean.
Run: `npm run lint`; Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add src/app/api/forms/route.ts "src/app/api/forms/[id]/route.ts" src/app/api/forms/upload/route.ts
git commit -m "feat(forms): approvalFlow in forms APIs"
```

---

### Task 4: Forms master page UI

**Files:**
- Modify: `src/app/master/forms/page.tsx`

**Interfaces:**
- Consumes: `APPROVAL_FLOW_OPTIONS` from `@/lib/approval-flow`; `approvalFlow` from the Task 3 APIs.
- Produces: Add/Edit dialog has a mandatory Approval Flow select; table shows an Approval Flow badge column; import columns include Approval Flow.

- [ ] **Step 1: Add the import**

```ts
import { APPROVAL_FLOW_OPTIONS } from "@/lib/approval-flow"
```

- [ ] **Step 2: Add the column to `importColumns`**

Add after the `requiresPayment` entry (line 38):

```ts
  { key: "approvalFlow", label: "Approval Flow", description: "NONE / ONE_LEVEL / TWO_LEVEL" },
```

- [ ] **Step 3: Extend the interface and initial state**

Add to `interface FormMaster` (after `requiresPayment`):

```ts
  approvalFlow: string
```

Add to `emptyForm`:

```ts
  approvalFlow: "ONE_LEVEL",
```

- [ ] **Step 4: Populate `approvalFlow` when editing**

In `handleOpenEdit`, every one of the three `setForm({...})` blocks (the `res.ok` branch, the `else` branch, and the `catch` branch) gains the field. For each, add after the `requiresPayment` line:

```ts
          approvalFlow: detail.approvalFlow || "ONE_LEVEL",
```

and in the two fallback blocks:

```ts
          approvalFlow: item.approvalFlow || "ONE_LEVEL",
```

- [ ] **Step 5: Add the table column**

Add a `<TableHead>Approval Flow</TableHead>` between "Payment Required" and "Description" in the table header (around line 247), and add a cell in each row after the payment badge cell:

```tsx
                      <TableCell>
                        <Badge variant={item.approvalFlow === "TWO_LEVEL" ? "default" : item.approvalFlow === "NONE" ? "outline" : "secondary"}>
                          {item.approvalFlow === "TWO_LEVEL" ? "Two-Level" : item.approvalFlow === "NONE" ? "None" : "One-Level"}
                        </Badge>
                      </TableCell>
```

- [ ] **Step 6: Add the Approval Flow select to the dialog**

Add a new `grid grid-cols-2 gap-4` row after the Tax Type/Description row (after line 352). Put the select in the first cell and move nothing else:

```tsx
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="approvalFlow">Approval Flow *</Label>
                  <Select value={form.approvalFlow} onValueChange={(v) => setForm({ ...form, approvalFlow: v })}>
                    <SelectTrigger id="approvalFlow">
                      <SelectValue placeholder="Select approval flow" />
                    </SelectTrigger>
                    <SelectContent>
                      {APPROVAL_FLOW_OPTIONS.map((f) => (
                        <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-[var(--color-muted-foreground)]">
                    Compared against the entity master on each compliance. The form&apos;s flow applies.
                  </p>
                </div>
              </div>
```

- [ ] **Step 7: Verify compile + lint**

Run: `npx tsc --noEmit`; Expected: clean.
Run: `npm run lint`; Expected: no new errors.

- [ ] **Step 8: Commit**

```bash
git add src/app/master/forms/page.tsx
git commit -m "feat(forms): approval flow field in form master UI"
```

---

### Task 5: Compliance builders resolve the effective flow

**Files:**
- Modify: `src/lib/template-compliance.ts`
- Modify: `src/app/api/compliance/route.ts`
- Modify: `src/app/api/compliance/[id]/route.ts`

**Interfaces:**
- Consumes: `effectiveApprovalFlow`, `normalizeApprovalFlow`, `buildApprovalRecords`, `type ApprovalFlow` from `@/lib/approval-flow`.
- Produces: Generated, manually-created, and edited compliances build their `compliance_approvals` rows from the effective flow (form flow when a form is linked, else entity flow).

- [ ] **Step 1: Update `lib/template-compliance.ts`**

1. Update the import (line 9):

```ts
import { buildApprovalRecords, effectiveApprovalFlow, normalizeApprovalFlow, type ApprovalFlow } from "@/lib/approval-flow"
```

2. Replace the requiresPayment fetch (lines 45-53) so it also captures the form's flow:

```ts
  let requiresPayment = true
  let formFlow: ApprovalFlow | undefined
  if (template.formId) {
    const { data: formRow } = await supabaseAdmin
      .from("form_master")
      .select("requiresPayment, approvalFlow")
      .eq("id", template.formId)
      .maybeSingle()
    requiresPayment = formRow?.requiresPayment ?? true
    if (formRow?.approvalFlow) {
      formFlow = normalizeApprovalFlow(formRow.approvalFlow as string)
    }
  }
```

3. Replace the entity-flow block (lines 103-112) to compute the effective flow:

```ts
  const filingEntityId = template.filingEntityId || entityIds[0] || null
  let entityFlow: ApprovalFlow = "ONE_LEVEL"
  if (filingEntityId) {
    const { data: entity } = await supabaseAdmin
      .from("legal_entities")
      .select("approvalFlow")
      .eq("id", filingEntityId)
      .maybeSingle()
    entityFlow = normalizeApprovalFlow(entity?.approvalFlow as string | undefined)
  }

  const approvalFlow = effectiveApprovalFlow(formFlow, entityFlow)
```

`buildApprovalRecords(approvalFlow, ...)` (line 114) then uses the effective flow unchanged.

- [ ] **Step 2: Update `api/compliance/route.ts` (manual create)**

1. Add `effectiveApprovalFlow` to the import (lines 5-10):

```ts
import {
  buildApprovalRecords,
  effectiveApprovalFlow,
  normalizeApprovalFlow,
  requiresApprover,
  requiresReviewer,
} from "@/lib/approval-flow"
```

2. Replace the `const approvalFlow = ...` + `const flow = ...` block (lines 235-239) so the form's flow wins when a form is selected, and move the `requiresPayment` form fetch up here to reuse it:

```ts
    let flow = normalizeApprovalFlow(filingEntity?.approvalFlow || "ONE_LEVEL")
    let requiresPayment =
      bodyRequiresPayment === true || bodyRequiresPayment === false ? !!bodyRequiresPayment : true
    if (formId) {
      const { data: formRow } = await supabaseAdmin
        .from("form_master")
        .select("requiresPayment, approvalFlow")
        .eq("id", formId)
        .maybeSingle()
      if (bodyRequiresPayment === undefined) requiresPayment = formRow?.requiresPayment ?? true
      flow = effectiveApprovalFlow(formRow?.approvalFlow as string | undefined, flow)
    }
```

3. Delete the now-duplicated requiresPayment fetch block (lines 248-257).

The reviewer/approver validation (lines 241-246) and `buildApprovalRecords(flow, ...)` (line 313) then use the effective flow unchanged.

- [ ] **Step 3: Update `api/compliance/[id]/route.ts` (edit)**

1. Update the import (line 5):

```ts
import { buildApprovalRecords, effectiveApprovalFlow, normalizeApprovalFlow, type ApprovalFlow } from "@/lib/approval-flow"
```

2. Replace the approval-rebuild block (lines 276-296) with one that resolves the effective flow from the form (body `formId` if provided, else `existing.formId`) over the filing entity:

```ts
    if (reviewerId !== undefined) {
      let entityFlow: ApprovalFlow = "ONE_LEVEL"
      const flowEntityId = filingEntityId ?? existing.entityId
      if (flowEntityId) {
        const { data: entity } = await supabaseAdmin
          .from("legal_entities")
          .select("approvalFlow")
          .eq("id", flowEntityId)
          .maybeSingle()
        entityFlow = normalizeApprovalFlow((entity?.approvalFlow as string) || undefined)
      }

      const effectiveFormId = formId !== undefined ? formId || null : (existing.formId as string | null) || null
      let formFlow: ApprovalFlow | undefined
      if (effectiveFormId) {
        const { data: formRow } = await supabaseAdmin
          .from("form_master")
          .select("approvalFlow")
          .eq("id", effectiveFormId)
          .maybeSingle()
        if (formRow?.approvalFlow) {
          formFlow = normalizeApprovalFlow(formRow.approvalFlow as string)
        }
      }

      const flow = effectiveApprovalFlow(formFlow, entityFlow)

      const { error: deleteApprovalError } = await supabaseAdmin
        .from("compliance_approvals")
        .delete()
        .eq("complianceId", id)

      if (deleteApprovalError) throw deleteApprovalError

      const approvalRecords = buildApprovalRecords(flow, reviewerId, approverId)
```

The remainder of that block (record insert + `ensureOrgMember`) stays as-is.

- [ ] **Step 4: Verify compile + lint**

Run: `npx tsc --noEmit`; Expected: clean.
Run: `npm run lint`; Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add src/lib/template-compliance.ts src/app/api/compliance/route.ts "src/app/api/compliance/[id]/route.ts"
git commit -m "feat(compliance): effective approval flow wins for builders"
```

---

### Task 6: Template pages drive dropdowns from the form's flow

**Files:**
- Modify: `src/app/master/compliance-templates/create/page.tsx`
- Modify: `src/app/master/compliance-templates/[id]/edit/page.tsx`

**Interfaces:**
- Consumes: `approvalFlow` on `Form` objects returned by `GET /api/forms?taxType=...` (Task 3); existing `selectedEntityFlow`/`flow` variables.
- Produces: `flow` resolves to the selected form's `approvalFlow` when a form is chosen, else the filing entity's flow.

- [ ] **Step 1: Update the template create page**

In `src/app/master/compliance-templates/create/page.tsx`:

1. Add `approvalFlow?: string` to the `Form` interface (lines 43-48).

2. After the `selectedEntityFlow` memo (lines 151-154), add a `selectedFormFlow` memo:

```ts
  const selectedFormFlow = useMemo(() => {
    if (!formId) return ""
    return forms.find((f) => f.id === formId)?.approvalFlow || ""
  }, [forms, formId])
```

3. Change the `flow` derivation (line 156):

```ts
  const flow = normalizeApprovalFlow(selectedFormFlow || selectedEntityFlow)
```

- [ ] **Step 2: Update the template edit page**

In `src/app/master/compliance-templates/[id]/edit/page.tsx`:

1. Add `approvalFlow?: string` to the `Form` interface.

2. After the `selectedEntityFlow` memo (lines 196-199), add a `selectedFormFlow` memo:

```ts
  const selectedFormFlow = useMemo(() => {
    if (!formId) return ""
    return forms.find((f) => f.id === formId)?.approvalFlow || ""
  }, [forms, formId])
```

3. Change the `flow` derivation (line 201):

```ts
  const flow = normalizeApprovalFlow(selectedFormFlow || selectedEntityFlow)
```

- [ ] **Step 3: Verify compile + lint**

Run: `npx tsc --noEmit`; Expected: clean.
Run: `npm run lint`; Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
git add src/app/master/compliance-templates/create/page.tsx "src/app/master/compliance-templates/[id]/edit/page.tsx"
git commit -m "feat(templates): dropdowns follow form approval flow"
```

---

### Task 7: Compliance pages drive dropdowns from the form's flow

**Files:**
- Modify: `src/app/compliance/create/page.tsx`
- Modify: `src/app/compliance/[id]/edit/page.tsx`

**Interfaces:**
- Consumes: `approvalFlow` on `Form` objects from `GET /api/forms?taxType=...`; existing `selectedEntityFlow`/`flow` variables.
- Produces: create/edit pages resolve the effective flow the same way the builders do (form flow wins).

- [ ] **Step 1: Update the compliance create page**

In `src/app/compliance/create/page.tsx`:

1. Add `approvalFlow?: string` to the `Form` interface (lines 49-54).

2. After the `selectedEntityFlow` memo (lines 171-174), add a `selectedFormFlow` memo:

```ts
  const selectedFormFlow = useMemo(() => {
    if (!formId) return ""
    return forms.find((f) => f.id === formId)?.approvalFlow || ""
  }, [forms, formId])
```

3. Change the `flow` derivation (line 176):

```ts
  const flow = normalizeApprovalFlow(selectedFormFlow || selectedEntityFlow)
```

- [ ] **Step 2: Update the compliance edit page**

In `src/app/compliance/[id]/edit/page.tsx`:

1. Add the import (after the `TAX_TYPE_OPTIONS` import, line 40):

```ts
import { normalizeApprovalFlow } from "@/lib/approval-flow"
```

2. Add `approvalFlow?: string` to the `Form` interface (lines 56-61).

3. After the `selectedEntityFlow` memo (lines 226-230), add a `selectedFormFlow` memo and a raw effective-flow value:

```ts
  const selectedFormFlow = useMemo(() => {
    if (!formId) return ""
    return forms.find((f) => f.id === formId)?.approvalFlow || ""
  }, [forms, formId])

  const rawFlow = selectedFormFlow || selectedEntityFlow
```

4. Change the approver-dropdown condition (line 663) from:

```tsx
              {(selectedEntityFlow === "TWO_LEVEL" || (!selectedEntityFlow && existingApproverCount > 0)) && (
```

to:

```tsx
              {(rawFlow === "TWO_LEVEL" || (!rawFlow && existingApproverCount > 0)) && (
```

The reviewer dropdown stays as-is (unconditional on this page — pre-existing behavior).

- [ ] **Step 3: Verify compile + lint**

Run: `npx tsc --noEmit`; Expected: clean.
Run: `npm run lint`; Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
git add src/app/compliance/create/page.tsx "src/app/compliance/[id]/edit/page.tsx"
git commit -m "feat(compliance): dropdowns follow form approval flow"
```

---

### Task 8: Compliance detail soft warning

**Files:**
- Modify: `src/app/api/compliance/[id]/route.ts`
- Modify: `src/app/compliance/[id]/page.tsx`

**Interfaces:**
- Consumes: `approvalFlow` on the compliance's `form` and filing `entity` (exposed by the Task 8 API change); `APPROVAL_FLOW_OPTIONS` from `@/lib/approval-flow`; `AlertTriangle` already imported in the detail page (line 9).
- Produces: amber warning below the filing entity in the entity card when `form.approvalFlow !== filingEntity.approvalFlow`.

- [ ] **Step 1: Expose both flows in the detail API**

In `src/app/api/compliance/[id]/route.ts`, update the `complianceSelect` (lines 8-21) — add `approvalFlow` to the form, the filing entity, and each compliance entity:

```ts
const complianceSelect = `
  *,
  entity:legal_entities(id, entityName, entityNumber, currency, approvalFlow),
  entities:compliance_entities(*, entity:legal_entities(id, entityName, entityNumber, currency, country:countries(name), approvalFlow)),
  country:countries(id, name, code),
  complianceType:compliance_types(id, name, taxType),
  form:form_master(id, formNumber, formName, approvalFlow),
  assignments:compliance_assignments(*, preparer:users(id, name, email)),
  approvals:compliance_approvals(*, approver:users(id, name, email)),
  confirmations:compliance_payment_confirmations(*, confirmedBy:users(id, name)),
  attachments:attachments(id, originalName, fileType, fileSize, version, createdAt),
  comments:comments(*, user:users(id, name)),
  activities:activities(*, user:users(id, name))
`
```

- [ ] **Step 2: Update the detail page types**

In `src/app/compliance/[id]/page.tsx`:

1. Add the import:

```ts
import { APPROVAL_FLOW_OPTIONS } from "@/lib/approval-flow"
```

2. Update `ComplianceDetail` (lines 137-193):

```ts
  entity: { id: string; entityName: string; entityNumber: string; currency?: string | null; approvalFlow?: string | null; country?: { name: string } } | null
  entities: { id: string; entityId: string; entity: { id: string; entityName: string; entityNumber: string; currency?: string | null; approvalFlow?: string | null; country?: { name: string } } }[]
```

```ts
  form: { id: string; formNumber: string; formName: string; approvalFlow?: string | null } | null
```

3. Add a label helper (near the other helpers, e.g. after `formatFileSize`):

```ts
function approvalFlowLabel(value: string | null | undefined): string {
  return APPROVAL_FLOW_OPTIONS.find((o) => o.value === value)?.label || value || ""
}
```

- [ ] **Step 3: Render the warning below the filing entity**

Replace the entity card map body (lines 793-806) so that the matching filing-entity entry shows the warning. Replace:

```tsx
              ).map((en) => (
                <div key={en.id}>
                  <p className="font-medium">{en.entity?.entityName}</p>
                  <p className="text-xs text-[var(--color-muted-foreground)]">
                    {en.entity?.entityNumber}
                  </p>
                  {en.entity?.country && (
                    <p className="text-xs text-[var(--color-muted-foreground)]">
                      <Globe className="h-3 w-3 inline mr-1" />
                      {en.entity.country.name}
                    </p>
                  )}
                </div>
              ))}
```

with:

```tsx
              ).map((en) => {
                const isFilingEntity = en.entityId === data.entity?.id || en.id === data.entity?.id
                const mismatch =
                  isFilingEntity &&
                  !!data.form?.approvalFlow &&
                  !!en.entity?.approvalFlow &&
                  data.form.approvalFlow !== en.entity.approvalFlow
                return (
                  <div key={en.id}>
                    <p className="font-medium">{en.entity?.entityName}</p>
                    <p className="text-xs text-[var(--color-muted-foreground)]">
                      {en.entity?.entityNumber}
                    </p>
                    {en.entity?.country && (
                      <p className="text-xs text-[var(--color-muted-foreground)]">
                        <Globe className="h-3 w-3 inline mr-1" />
                        {en.entity.country.name}
                      </p>
                    )}
                    {mismatch && (
                      <div className="flex items-start gap-2 mt-2 rounded-md border border-amber-300 bg-amber-50 dark:bg-amber-950/40 p-2 text-xs text-amber-800 dark:text-amber-200">
                        <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                        <span>
                          Approval flow mismatch — Form is {approvalFlowLabel(data.form?.approvalFlow)}, entity master is{" "}
                          {approvalFlowLabel(en.entity?.approvalFlow)}. The form&apos;s approval flow applies.
                        </span>
                      </div>
                    )}
                  </div>
                )
              })}
```

- [ ] **Step 4: Verify compile + lint**

Run: `npx tsc --noEmit`; Expected: clean.
Run: `npm run lint`; Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add "src/app/api/compliance/[id]/route.ts" "src/app/compliance/[id]/page.tsx"
git commit -m "feat(compliance): soft approval flow mismatch warning on detail"
```

---

### Task 9: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `npm test`
Expected: all tests pass (existing + new `effectiveApprovalFlow` suite).

- [ ] **Step 2: Compile + lint**

Run: `npx tsc --noEmit`; Expected: clean.
Run: `npm run lint`; Expected: no new errors.

- [ ] **Step 3: Manual smoke test (dev server)**

Run: `npm run dev`, then verify:
1. Apply the migration to the local database (e.g. via `npx prisma db push` or the Supabase migration tooling used in this repo).
2. **Forms master**: open `/master/forms` → Add Form → Approval Flow select is present and mandatory; create a form with `TWO_LEVEL`; the table shows the "Two-Level" badge. Edit shows the saved value.
3. **Template create** (`/master/compliance-templates/create`): select a tax type + a form whose flow is `TWO_LEVEL` and an entity whose flow is `NONE` — the Approver dropdown appears (form flow wins).
4. **Compliance create** (`/compliance/create`): same — dropdowns follow the form's flow.
5. **Compliance detail**: open a compliance that links a form whose flow differs from its filing entity's flow — the amber "Approval flow mismatch" warning appears below the filing entity. A compliance whose form flow matches its entity flow shows no warning.
6. Generate a compliance from a template whose form flow is `TWO_LEVEL` against a `NONE` entity — `compliance_approvals` contains reviewer (step 1) + approver (step 2) records (form wins).

- [ ] **Step 4: Commit any follow-up fixes** (only if smoke test surfaced issues)

```bash
git add -A
git commit -m "fix: form approval flow follow-ups"
```
