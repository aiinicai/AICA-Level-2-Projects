# Ad-hoc Compliance Create Form

## Overview

Add a dedicated form page at `/compliance/ad-hoc/create` for creating individual ad-hoc compliances manually. This complements the existing CSV upload flow on the ad-hoc list page, giving users two ways to add ad-hoc compliances: one-by-one via the form, or in bulk via CSV import.

## Background

- The ad-hoc list page (`/compliance/ad-hoc`) currently only supports CSV import via the `DataImport` component.
- The recurring compliance template form (`/master/compliance-templates/create`) is the reference pattern for this new form.
- The backend endpoint `POST /api/compliance` already supports ad-hoc creation by accepting `isRecurring: false` and `frequency: "AD_HOC"`.
- No backend changes are required.

## Approach

New standalone page modeled after the recurring template create form. Remove recurrence-specific fields (frequency selector, recurring end date, period end date, days-after-period-end calculations) and replace with direct date pickers for due date and payment due date.

## Page Structure & Routing

### New Page

**File**: `src/app/compliance/ad-hoc/create/page.tsx`

A client component using `DashboardLayout` (same layout as the ad-hoc list page).

### Ad-hoc List Page Changes

**File**: `src/app/compliance/ad-hoc/page.tsx`

Add an "+ Add Individual" button next to the existing import button. Both visible to admin/preparer roles. The existing button (which triggers CSV import via `DataImport`) should be kept as-is or optionally relabeled to "+ Upload CSV" for clarity.

### Routing Flow

- `/compliance/ad-hoc` -- list page (existing)
- `/compliance/ad-hoc/create` -- new form page
- On successful submit -- redirect to `/compliance/ad-hoc` with success toast
- Cancel button -- redirect back to `/compliance/ad-hoc`

## Form Fields

| Field | Control | Required | Conditional | Notes |
|-------|---------|----------|-------------|-------|
| Tax Type | `<Select>` from `TAX_TYPE_OPTIONS` | Yes | No | Triggers form dropdown refresh |
| Form | `<Select>` from `/api/forms?taxType=` | No | Disabled until tax type chosen | Same as template form |
| Entities | `<MultiSelect>` | Yes (at least 1) | No | Same component as template form |
| Filing Entity | `<Select>` | Yes if >1 entity | Auto-locks to sole entity when only one selected | Same as template form |
| Country | `<Select>` | Yes | Auto-detected from first selected entity, overridable | Same as template form |
| Tax Period | `<Input>` (text) | Yes | No | e.g. "2026-03" or "Q1 2026" |
| Due Date | `<Input type="date">` | Yes | No | Direct date picker |
| Payment Due Date | `<Input type="date">` | No | Only shown if selected form `requiresPayment` | Direct date picker |
| Priority | `<Select>` NORMAL / HIGH / CRITICAL | No (defaults NORMAL) | No | Same as template form |
| Preparer | `<Select>` from `/api/users?role=PREPARER` | No (defaults to session user) | No | Same as template form |
| Reviewer | `<Select>` from `/api/users?role=REVIEWER` | Yes if flow requires | Shown when approval flow is ONE_LEVEL or TWO_LEVEL | Same as template form |
| Approver | `<Select>` from `/api/users?role=APPROVER` | Yes if flow requires | Shown when approval flow is TWO_LEVEL | Same as template form |
| Notes | `<Textarea>` | No | No | Same as template form |

### Hidden / Hardcoded Values (sent in payload, not shown in UI)

- `frequency: "AD_HOC"`
- `isRecurring: false`

### Approval Flow Logic

Same as template form: `normalizeApprovalFlow(formFlow || entityFlow)` determines which approval fields appear.

- `NONE` -- no reviewer or approver fields
- `ONE_LEVEL` -- reviewer field shown (required)
- `TWO_LEVEL` -- reviewer and approver fields shown (both required)

## Data Flow

### On Mount (parallel fetches)

- `GET /api/countries` -- countries list
- `GET /api/entities` -- entities list
- `GET /api/users?role=PREPARER` -- preparers
- `GET /api/users?role=REVIEWER` -- reviewers
- `GET /api/users?role=APPROVER` -- approvers

### On Tax Type Change

- `GET /api/forms?taxType=${taxType}` -- form options

### On Entity Selection

- Auto-detect country from first selected entity (user can override)
- Auto-set filing entity if only one entity selected

### Submit

`POST /api/compliance`

```typescript
{
  entityIds: string[],
  taxType: string,
  formId: string | undefined,
  countryId: string,
  filingEntityId: string | undefined,
  frequency: "AD_HOC",
  isRecurring: false,
  taxPeriod: string,
  dueDate: string,                    // "YYYY-MM-DD"
  paymentDueDate: string | undefined, // "YYYY-MM-DD"
  priority: string,                   // "NORMAL" | "HIGH" | "CRITICAL"
  notes: string | undefined,
  preparerId: string | undefined,
  reviewerId: string | undefined,     // if flow requires
  approverId: string | undefined,     // if flow requires
}
```

### Client-Side Validation

1. At least one entity, a tax type, a country, a tax period, and a due date are required
2. If multiple entities, filing entity is required
3. If approval flow requires reviewer -- reviewer is required
4. If approval flow requires approver -- approver is required

### Error Handling

- Show toast notification on submit failure
- If API returns field-level errors, display them inline

### Post-Submit

- Redirect to `/compliance/ad-hoc` with success toast

## UI Layout

Card-based layout matching the recurring template create form:

- **Header**: "Add Ad-hoc Compliance" title with back button to `/compliance/ad-hoc`
- **Card 1 -- Core Details**: Tax Type, Form, Entities, Filing Entity, Country, Tax Period, Due Date
- **Card 2 -- Payment & Priority**: Payment Due Date (conditional on form requiring payment), Priority
- **Card 3 -- Assignment & Approval**: Preparer, Reviewer (conditional), Approver (conditional)
- **Card 4 -- Notes**: Textarea
- **Footer buttons**: "Create Compliance" (primary), "Cancel" (outline)

### Loading State

Show `Skeleton` placeholders while reference data loads (same pattern as template edit form).

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `src/app/compliance/ad-hoc/create/page.tsx` | Create | New form page |
| `src/app/compliance/ad-hoc/page.tsx` | Modify | Add "+ Add Individual" button linking to create page |

## Shared Components Used

- `@/components/ui/button` (Button)
- `@/components/ui/input` (Input)
- `@/components/ui/label` (Label)
- `@/components/ui/textarea` (Textarea)
- `@/components/ui/select` (Select, SelectContent, SelectItem, SelectTrigger, SelectValue)
- `@/components/ui/card` (Card, CardContent, CardHeader, CardTitle)
- `@/components/ui/skeleton` (Skeleton)
- `@/components/ui/toast` (toast)
- `@/components/multi-select` (MultiSelect)
- `@/components/layout/dashboard-layout` (DashboardLayout)
- `@/components/layout/providers` (useAuth)
- `@/lib/tax-types` (TAX_TYPE_OPTIONS)
- `@/lib/approval-flow` (normalizeApprovalFlow, requiresApprover, requiresReviewer)

## No Backend Changes

The existing `POST /api/compliance` endpoint already handles all the fields this form sends. No API modifications needed.
