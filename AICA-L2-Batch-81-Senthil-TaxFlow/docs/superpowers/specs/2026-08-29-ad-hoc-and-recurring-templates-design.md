# Ad-hoc Compliance Page & Recurring Templates Rename — Design

Date: 2026-08-29

## Context

The Compliance Tracker (`/compliance`) currently exposes two creation paths:
a CSV import called **"Create Ad-hoc Compliance"** (a dropdown with Download
Template / Upload CSV hitting `/api/compliance/import`) and a **"Create
Recurring Template"** button pointing at `/master/compliance-templates/create`.

The product request is to:

1. Rename **Compliance Templates** to **Recurring Templates** across the UI.
2. Add a dedicated **Ad-hoc compliance page** where one-off compliances are
   uploaded and then tracked.
3. Rename the Compliance Tracker buttons to **"+ Add Ad-hoc Compliances"** and
   **"+ Add Recurring Templates"**.

## Scope

- Navigation and label changes (no URL changes; routes stay as-is).
- A new Ad-hoc Compliances page and one small API filter addition.
- No database/schema changes.

## Approach

Adopt **Approach A**: a dedicated `/compliance/ad-hoc` page plus renamed labels.
URLs are intentionally unchanged to avoid breaking existing links and entry
points.

## Definitions

- **Recurring Templates** = the existing compliance-templates feature
  (`/master/compliance-templates`, sidecar page being the create flow).
- **Ad-hoc Compliances** (page) = a list of **all non-recurring** compliance
  items (`compliance_schedules.isRecurring = false`). This covers items
  uploaded via CSV import (`source = IMPORT`) and manually created one-off
  items (`frequency = AD_HOC`, `isRecurring` unset).

## Design

### 1. Rename Compliance Templates → Recurring Templates

Labels only; routes unchanged.

| Location | Change |
| --- | --- |
| `src/components/layout/app-sidebar.tsx` | "Compliance Templates" → "Recurring Templates" (Compliance Home group). Icon stays `FileType`. |
| `src/app/master/page.tsx` | Remove the "Compliance Templates" overview card entirely. |
| `src/app/master/layout.tsx` | Remove the "Templates" nav tab. |
| `src/app/master/compliance-templates/page.tsx` | `CardTitle` → "Recurring Templates"; description → "Manage recurring template schedules and generate by month."; "Create Recurring Template" button → "+ Add Recurring Templates"; empty-state texts updated ("No recurring templates yet."). |
| `src/app/master/compliance-templates/create/page.tsx` | Heading → "Create Recurring Template". |
| `src/app/master/compliance-templates/[id]/page.tsx` | Heading fallback → "Recurring Template"; "Back to Compliance Templates" → "Back to Recurring Templates"; not-found copy updated. |
| `src/app/master/compliance-templates/[id]/edit/page.tsx` | Heading → "Edit Recurring Template"; "Back to …" updated. |

The master layout currently hides its header/tab bar on
`/master/compliance-templates*` and renders the list/detail pages bare under
`DashboardLayout`; removing the Master Data entry keeps that behavior.

### 2. New Ad-hoc Compliances page — `/compliance/ad-hoc`

- New sidebar item under **Compliance Home**: "Ad-hoc Compliances", between
  "Compliance Tracker" and "Recurring Templates". Icon: `ClipboardPlus`.
- **Page layout** (wraps `DashboardLayout title="Ad-hoc Compliances"`):
  - Header row: heading "Ad-hoc Compliances" with subtitle explaining these
    are one-off compliances uploaded for tracking.
  - `+ Add Ad-hoc Compliances` button (Admins + Preparers only) that opens the
    existing CSV flow: **Download Template** + **Upload CSV** →
    `/api/compliance/import`. Reuses the `DataImport` component with the same
    import columns already used by the tracker (`IMPORT_COLUMNS`).
  - Empty state with the same `+ Add Ad-hoc Compliances` button.
  - **Tracking table** of non-recurring items fetched from
    `GET /api/compliance?isRecurring=false`:
    - Same columns/status badges/filter controls as the Compliance Tracker
      (search, status, priority, country, entity) and pagination.
    - Row actions: View, Edit (admin/preparer), Delete (admin).
    - Bulk-approve for admins, matching tracker behavior.
- Data/roles: read for all authenticated roles; add/edit for Admins and
  Preparers only (same rules as the tracker).

### 3. API — `GET /api/compliance` filter

- Add support for an `isRecurring` query parameter. When `isRecurring=false`,
  filter `compliance_schedules.isRecurring = false`; when `isRecurring=true`,
  filter `isRecurring = true`. Absent = no filtering (current behavior).
- No table/column changes.

### 4. Compliance Tracker changes (`/compliance`)

- Replace the `DataImport` dropdown (labeled "Create Ad-hoc Compliance") with a
  plain button labeled **"+ Add Ad-hoc Compliances"** that navigates to
  `/compliance/ad-hoc`.
- Rename "Create Recurring Template" button → **"+ Add Recurring Templates"**
  (same destination `/master/compliance-templates/create`).
- Empty state: show both next-step buttons — "+ Add Recurring Templates"
  (navigates to `/master/compliance-templates/create`) and
  "+ Add Ad-hoc Compliances" (navigates to `/compliance/ad-hoc`).
- The tracker keeps listing all compliances (recurring and ad-hoc) as today.

## Out of Scope

- Renaming URLs (`/master/compliance-templates` stays).
- Changes to CSV import behavior or columns.
- Any recurring-generation logic.
- Notifications/email copy mentioning "template".

## Testing

- Manual: sidebar shows "Recurring Templates" + "Ad-hoc Compliances";
  Master Data no longer lists templates; tracker buttons navigate correctly.
- `GET /api/compliance?isRecurring=false` returns only non-recurring items;
  no filter returns everything.
- Ad-hoc page: upload CSV via the dialog, confirm items appear in the table.

## Rollout

Single commit set. No migrations, no env changes.