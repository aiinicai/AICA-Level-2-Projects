# Approval Flow Decoupling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple actual approval workflow execution from Entity and Form master placeholders, allowing explicit selection at recurring template and ad-hoc compliance creation time, and displaying a 3-tier approval mechanism breakdown on detail views.

**Architecture:** Add `approvalFlow` to `compliance_templates` model/table. Update creation/edit pages to include an Approval Flow dropdown (defaulted to form/entity flow). Update backend workflow generators to use the active flow directly. Add a 3-tier approval flow card to template and compliance detail views.

**Tech Stack:** Next.js (App Router), TypeScript, Prisma, Supabase/PostgreSQL, Tailwind CSS, Shadcn UI.

## Global Constraints
- TypeScript strict mode: `npx tsc --noEmit` must pass after every task.
- Linting: `npm run lint` must pass.
- Maintain existing codebase naming conventions and UI patterns.

---

### Task 1: Database Migration & Schema Update

**Files:**
- Modify: `prisma/schema.prisma`
- Create: `supabase/migrations/20260830000000_template_approval_flow.sql`

**Interfaces:**
- Produces: `ComplianceTemplate.approvalFlow` in Prisma model and PostgreSQL table.

- [ ] **Step 1: Update Prisma schema**

Add `approvalFlow String @default("ONE_LEVEL")` to `ComplianceTemplate` model in `prisma/schema.prisma`:
```prisma
model ComplianceTemplate {
  ...
  priority            Priority @default(NORMAL)
  approvalFlow        String   @default("ONE_LEVEL")
  isRecurring         Boolean  @default(true)
  ...
}
```

- [ ] **Step 2: Create SQL Migration file**

Create `supabase/migrations/20260830000000_template_approval_flow.sql`:
```sql
ALTER TABLE compliance_templates ADD COLUMN IF NOT EXISTS "approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL';

ALTER TABLE compliance_templates DROP CONSTRAINT IF EXISTS "compliance_templates_approvalFlow_check";

ALTER TABLE compliance_templates ADD CONSTRAINT "compliance_templates_approvalFlow_check"
  CHECK ("approvalFlow" IN ('NONE', 'ONE_LEVEL', 'TWO_LEVEL'));
```

- [ ] **Step 3: Validate schema and types**

Run: `npx tsc --noEmit`
Expected: PASS with 0 errors.

- [ ] **Step 4: Commit**

```bash
git add prisma/schema.prisma supabase/migrations/20260830000000_template_approval_flow.sql
git commit -m "feat(db): add approvalFlow column to compliance_templates"
```

---

### Task 2: Backend API and Lib Updates

**Files:**
- Modify: `src/app/api/compliance-templates/route.ts`
- Modify: `src/app/api/compliance-templates/[id]/route.ts`
- Modify: `src/app/api/compliance/route.ts`
- Modify: `src/app/api/compliance/[id]/route.ts`
- Modify: `src/lib/template-compliance.ts`

**Interfaces:**
- Consumes: `ComplianceTemplate.approvalFlow`
- Produces: API acceptance and schedule creation using active `approvalFlow`.

- [ ] **Step 1: Update Template POST API (`src/app/api/compliance-templates/route.ts`)**

Extract `approvalFlow` from body, default to `ONE_LEVEL` if empty, validate it against `APPROVAL_FLOWS`, and insert into `compliance_templates`.

- [ ] **Step 2: Update Template PUT API (`src/app/api/compliance-templates/[id]/route.ts`)**

Accept `approvalFlow` in body updates for existing templates.

- [ ] **Step 3: Update Compliance Schedule Generator (`src/lib/template-compliance.ts`)**

Change approvalFlow calculation in `generateComplianceFromTemplate`:
Use `template.approvalFlow` directly instead of computing from form and entity:
```ts
const activeFlow = normalizeApprovalFlow(template.approvalFlow || "ONE_LEVEL")
```
Set `approvalFlow: activeFlow` on `compliance_schedules` insert, and build approval records using `activeFlow`.

- [ ] **Step 4: Update Compliance Schedule POST API (`src/app/api/compliance/route.ts`)**

Accept `approvalFlow` from request body (or default to effective form/entity flow if missing), set `approvalFlow` on `compliance_schedules` insert, and build approval records using this active flow.

- [ ] **Step 5: Update Compliance Schedule PUT API (`src/app/api/compliance/[id]/route.ts`)**

Accept `approvalFlow` in body updates and update `compliance_schedules.approvalFlow`.

- [ ] **Step 6: Validate types**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/app/api/compliance-templates/route.ts src/app/api/compliance-templates/[id]/route.ts src/app/api/compliance/route.ts src/app/api/compliance/[id]/route.ts src/lib/template-compliance.ts
git commit -m "feat(api): support approvalFlow in template and schedule backend APIs"
```

---

### Task 3: Template Creation & Edit UI Update

**Files:**
- Modify: `src/app/master/compliance-templates/create/page.tsx`
- Modify: `src/app/master/compliance-templates/[id]/edit/page.tsx`

**Interfaces:**
- Consumes: `APPROVAL_FLOW_OPTIONS` from `@/lib/approval-flow`
- Produces: Interactive Approval Flow dropdown and submission payload with `approvalFlow`.

- [ ] **Step 1: Update Template Create Form (`src/app/master/compliance-templates/create/page.tsx`)**

1. Add `approvalFlow` state (`"ONE_LEVEL"` default).
2. Auto-set `approvalFlow` when form or filing entity changes:
```ts
useEffect(() => {
  if (selectedFormFlow) {
    setApprovalFlow(normalizeApprovalFlow(selectedFormFlow))
  } else if (selectedEntityFlow) {
    setApprovalFlow(normalizeApprovalFlow(selectedEntityFlow))
  }
}, [selectedFormFlow, selectedEntityFlow])
```
3. Add Approval Flow Select dropdown UI element under Assignments section.
4. Update dynamic validation:
   - If `approvalFlow === "NONE"`, hide/clear reviewer and approver fields.
   - If `approvalFlow === "ONE_LEVEL"`, require reviewer, hide/clear approver field.
   - If `approvalFlow === "TWO_LEVEL"`, require both reviewer and approver fields.
5. Include `approvalFlow` in POST request body.

- [ ] **Step 2: Update Template Edit Form (`src/app/master/compliance-templates/[id]/edit/page.tsx`)**

1. Load `template.approvalFlow` into state.
2. Render Approval Flow Select dropdown UI element.
3. Update dynamic validation and submit payload.

- [ ] **Step 3: Validate types**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/app/master/compliance-templates/create/page.tsx src/app/master/compliance-templates/[id]/edit/page.tsx
git commit -m "feat(ui): add approval flow selector to template create and edit forms"
```

---

### Task 4: Ad-hoc & Compliance Creation/Edit UI Update

**Files:**
- Modify: `src/app/compliance/create/page.tsx`
- Modify: `src/app/compliance/ad-hoc/create/page.tsx`
- Modify: `src/app/compliance/[id]/edit/page.tsx`

- [ ] **Step 1: Update General Create Form (`src/app/compliance/create/page.tsx`)**
Add `approvalFlow` state, auto-defaulting from selected form/entity, dropdown UI component, dynamic reviewer/approver validation, and payload submission.

- [ ] **Step 2: Update Ad-hoc Create Form (`src/app/compliance/ad-hoc/create/page.tsx`)**
Add `approvalFlow` state, auto-defaulting from selected form/entity, dropdown UI component, dynamic reviewer/approver validation, and payload submission.

- [ ] **Step 3: Update Compliance Edit Form (`src/app/compliance/[id]/edit/page.tsx`)**
Load `data.approvalFlow` into state, render dropdown UI, update submit payload.

- [ ] **Step 4: Validate types**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/app/compliance/create/page.tsx src/app/compliance/ad-hoc/create/page.tsx src/app/compliance/[id]/edit/page.tsx
git commit -m "feat(ui): add approval flow selector to compliance create and edit forms"
```

---

### Task 5: 3-Tier Approval Mechanism Display in Detail Views

**Files:**
- Modify: `src/app/master/compliance-templates/[id]/page.tsx`
- Modify: `src/app/compliance/[id]/page.tsx`

**Interfaces:**
- Consumes: Entity flow, Form flow, and active Template/Schedule flow.
- Produces: 3-tier Approval Mechanism breakdown UI card with mismatch indicators.

- [ ] **Step 1: Update Template Detail View (`src/app/master/compliance-templates/[id]/page.tsx`)**

Render a dedicated "Approval Flow Mechanism" card showing:
- **Entity Master Flow (Placeholder)**: `entity.approvalFlow`
- **Form Master Flow (Placeholder)**: `form.approvalFlow` (or "N/A - No form selected")
- **Active Template Flow**: `template.approvalFlow`
If active flow differs from entity or form master flow, render an informational badge indicator.

- [ ] **Step 2: Update Compliance Schedule Detail View (`src/app/compliance/[id]/page.tsx`)**

Render a dedicated "Approval Flow Mechanism" card showing:
- **Entity Master Flow (Placeholder)**: `entity.approvalFlow`
- **Form Master Flow (Placeholder)**: `form.approvalFlow` (or "N/A - No form selected")
- **Active Compliance Flow**: `data.approvalFlow`
If active flow differs from entity or form master flow, render an informational badge indicator.

- [ ] **Step 3: Validate types and build**

Run: `npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/app/master/compliance-templates/[id]/page.tsx src/app/compliance/[id]/page.tsx
git commit -m "feat(ui): add 3-tier approval mechanism card to template and compliance detail views"
```
