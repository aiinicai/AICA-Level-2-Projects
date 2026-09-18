# Approval Flow Decoupling & 3-Tier Display Design

## Overview
Currently, the approval workflow (`NONE`, `ONE_LEVEL`, `TWO_LEVEL`) for compliance schedules and recurring templates is derived dynamically from entity master (`legal_entities.approvalFlow`) and form master (`form_master.approvalFlow`). 

This feature decouples the actual approval workflow execution from entity and form masters:
1. **Entity Master** and **Form Master** `approvalFlow` settings become **placeholders** (informational settings).
2. **Template Level** (for recurring templates) and **Compliance Level** (for ad-hoc / manual compliances) now have an explicit `approvalFlow` dropdown field selected during creation or editing. This selected flow drives the actual approval workflow execution (`NONE`, `ONE_LEVEL`, `TWO_LEVEL`).
3. **Template & Compliance Detail Views** display a 3-tier approval mechanism breakdown (Entity Master, Form Master, Active Flow) so users can easily spot any differences.

---

## 1. Schema & Data Model Changes

### Database Migration
Add `approvalFlow` column to `compliance_templates`:
- `approvalFlow TEXT NOT NULL DEFAULT 'ONE_LEVEL'`
- CHECK constraint: `approvalFlow IN ('NONE', 'ONE_LEVEL', 'TWO_LEVEL')`
- Migration file: `supabase/migrations/20260830000000_template_approval_flow.sql`

### Prisma Schema (`prisma/schema.prisma`)
Add `approvalFlow String @default("ONE_LEVEL")` to `ComplianceTemplate` model.

---

## 2. Defaulting & UI Logic on Creation/Edit Forms

Applies to:
- `/master/compliance-templates/create`
- `/master/compliance-templates/[id]/edit`
- `/compliance/create`
- `/compliance/ad-hoc/create`
- `/compliance/[id]/edit`

### Field Behavior:
- **Approval Flow Dropdown**: `NONE` ("None (no approval)"), `ONE_LEVEL` ("One-Level (Reviewer only)"), `TWO_LEVEL` ("Two-Level (Reviewer then Approver)").
- **Defaulting Logic**:
  - When selecting a Form, default `approvalFlow` to `form.approvalFlow`.
  - If no Form is selected, default `approvalFlow` to filing `entity.approvalFlow`.
  - The user can freely change the `approvalFlow` dropdown to any value (`NONE`, `ONE_LEVEL`, `TWO_LEVEL`).
- **Dynamic Input Validation**:
  - `NONE`: Reviewer and Approver inputs are hidden/cleared.
  - `ONE_LEVEL`: Reviewer is required. Approver input is hidden/cleared.
  - `TWO_LEVEL`: Reviewer and Approver are both required.

---

## 3. Backend Workflow Engine Changes

### API Endpoints
- `POST /api/compliance-templates` & `PUT /api/compliance-templates/[id]`:
  - Store `approvalFlow` on `compliance_templates`.
- `POST /api/compliance` & `PUT /api/compliance/[id]`:
  - Store `approvalFlow` on `compliance_schedules`.
- `src/lib/template-compliance.ts`:
  - When generating schedules from templates, copy `template.approvalFlow` directly to `compliance_schedules.approvalFlow`.
  - Build `compliance_approvals` records based on `template.approvalFlow`.

---

## 4. 3-Tier Approval Display in Detail Views

Applies to:
- Template Detail (`/master/compliance-templates/[id]`)
- Compliance Detail (`/compliance/[id]`)

### Approval Mechanism Card Component:
Renders a card or dedicated section showing:
1. **Entity Level Approval Flow** *(Placeholder)*: `entity.approvalFlow` (e.g., "One-Level")
2. **Form Level Approval Flow** *(Placeholder)*: `form.approvalFlow` (e.g., "Two-Level" or "N/A - No form")
3. **Active Approval Flow**: `template.approvalFlow` or `schedule.approvalFlow` (e.g., "None")

If the active flow differs from entity or form master flow, display a soft badge indicator explaining the divergence.

---

## 5. Verification Plan
1. Run `npx tsc --noEmit` to verify type safety.
2. Test creating recurring templates with custom approval flow choices.
3. Test creating ad-hoc compliances with custom approval flow choices.
4. Verify detail pages render entity, form, and active approval flows correctly.
