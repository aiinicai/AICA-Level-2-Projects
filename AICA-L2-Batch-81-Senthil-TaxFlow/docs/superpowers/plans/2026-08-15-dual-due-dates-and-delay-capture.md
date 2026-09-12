# Dual Due Dates (Filing + Payment), Actual Dates, Delay Capture & requiresPayment

**Date:** 2026-08-15

## Summary

1. New `paymentDueDate` column (payment **due** date, "P"). `paymentDate` keeps meaning the **actual** payment date (set by mark-paid).
2. `filedAt` becomes the **actual** filing date (user inputs it in the File dialog; defaults to today).
3. Tracker shows **F Due** and **P Due** columns. Overdue becomes **action-based**: F overdue only when not yet filed; P overdue only when not yet paid. Closed/completed items never show overdue.
4. New `requiresPayment` flag on `form_master` and a snapshot on `compliance_schedules`. Non-payment compliance dynamically hides the payment section everywhere.
5. Dashboard gets **Filed Late** / **Paid Late** cards; reports get delay columns.

## Verification commands (run after each task)

```powershell
npx tsc --noEmit
npx eslint <changed files>
npx vitest run
```

## Task 1 — Schema migration

**Files:**
- `supabase/migrations/20260815020000_payment_due_date.sql` (new)
- `supabase-full-schema.sql`

Create the migration:

```sql
-- Dual due dates + form-level payment requirement
ALTER TABLE compliance_schedules
  ADD COLUMN IF NOT EXISTS "paymentDueDate" TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS "requiresPayment" BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE form_master
  ADD COLUMN IF NOT EXISTS "requiresPayment" BOOLEAN NOT NULL DEFAULT true;

-- Best-effort backfill: rows never marked paid hold a payment DUE date in paymentDate.
UPDATE compliance_schedules
SET "paymentDueDate" = "paymentDate"
WHERE "paidAt" IS NULL AND "paymentDate" IS NOT NULL AND "paymentDueDate" IS NULL;
```

Mirror both new columns in `supabase-full-schema.sql`:
- `compliance_schedules` CREATE TABLE: add `"paymentDueDate" TIMESTAMPTZ,` after `"paymentDate"` and `"requiresPayment" BOOLEAN NOT NULL DEFAULT true,` (keep the comma structure valid — it is currently the last column before the PK constraint; place `requiresPayment` before the closing `)` or reorder carefully).
- `form_master` CREATE TABLE: add `"requiresPayment" BOOLEAN NOT NULL DEFAULT true,`.

Verify: `npx tsc --noEmit` (SQL is not compiled; just confirm nothing else references it yet).

Commit: `feat(schema): payment due date and requiresPayment columns`

## Task 2 — `compliance-period`: payment due date rename + test

The generation result field `paymentDate` is the payment **due** date. Rename it to `paymentDueDate` everywhere in this lib + its test.

**Files:**
- `src/lib/compliance-period.ts`
- `src/lib/compliance-period.test.ts`

In `src/lib/compliance-period.ts`:
- `GenerationResult`: rename `paymentDate?: Date` → `paymentDueDate?: Date` (line 141).
- In `computeGeneration`, rename the local `paymentDate` const (line 190) and the returned field (line 196) to `paymentDueDate`.

In `src/lib/compliance-period.test.ts`, update all `result.paymentDate` expectations to `result.paymentDueDate` (lines ~150, ~212, ~300).

Verify: `npx vitest run`

Commit: `refactor(period): rename generation paymentDate to paymentDueDate`

## Task 3 — Template generation writes `paymentDueDate` + `requiresPayment`

**Files:**
- `src/lib/template-compliance.ts`
- `src/app/api/templates/generate/route.ts`
- `src/app/api/templates/[id]/generate/route.ts`

In `src/lib/template-compliance.ts`:
- `GeneratedComplianceInput.generation` type: `{ periodStart; periodEnd; dueDate; paymentDate }` → `paymentDueDate` (line 34).
- In `insertGeneratedCompliance`, fetch the form's payment requirement before insert:

```ts
let requiresPayment = true
if (template.formId) {
  const { data: formRow } = await supabaseAdmin
    .from("form_master")
    .select("requiresPayment")
    .eq("id", template.formId)
    .maybeSingle()
  requiresPayment = formRow?.requiresPayment ?? true
}
```

- Change the insert field `paymentDate: generation.paymentDate.toISOString()` (line 59) to:

```ts
paymentDueDate: requiresPayment ? generation.paymentDueDate.toISOString() : null,
requiresPayment,
```

(The `paymentDate` field is NOT set at insert — it remains null until mark-paid writes the actual date.)

In `templates/generate/route.ts` and `templates/[id]/generate/route.ts`: no field-level changes needed — they pass `generation` into `insertGeneratedCompliance`; the type rename flows through. Verify each route still compiles.

Verify: `npx tsc --noEmit`, `npx vitest run`

Commit: `feat(templates): write paymentDueDate and inherit requiresPayment from form`

## Task 4 — Form master: `requiresPayment` in APIs + page

**Files:**
- `src/app/api/forms/route.ts`
- `src/app/api/forms/[id]/route.ts`
- `src/app/api/forms/upload/route.ts`
- `src/app/master/forms/page.tsx`

### 4.1 `src/app/api/forms/route.ts`
- GET select (line 26): add `requiresPayment`.
- POST handler: destructure `requiresPayment`; add `if (requiresPayment !== undefined) insertData.requiresPayment = requiresPayment === true`.

### 4.2 `src/app/api/forms/[id]/route.ts`
- GET select (line 21): add `requiresPayment`.
- PUT handler: destructure `requiresPayment` from body; in the update block add `if (requiresPayment !== undefined) updateData.requiresPayment = requiresPayment === true`.

### 4.3 `src/app/api/forms/upload/route.ts`
- POST loop: accept `requiresPayment` from item; normalize `"yes"/"true"/"1"` → `true`, else `false`; default `true`. Set in insert and in the update branch. Add `requiresPayment` to the insert payload.

### 4.4 `src/app/master/forms/page.tsx`
- `importColumns`: add `{ key: "requiresPayment", label: "Requires Payment", description: "yes/no — whether this form's filing requires payment" }` (optional column).
- `emptyForm`: add `requiresPayment: true`.
- `FormMaster` interface: add `requiresPayment: boolean`.
- `handleOpenEdit`: populate `requiresPayment` from detail (default `true`).
- Dialog: add a switch/toggle (use `Switch` from `@/components/ui/switch`, used elsewhere in the app) labeled **Requires Payment** bound to `form.requiresPayment`.
- Table: add a `Payment Required` column rendering `<Badge>{form.requiresPayment ? "Yes" : "No"}</Badge>`.

Verify: `npx tsc --noEmit`, `npx eslint src/app/api/forms src/app/master/forms/page.tsx`

Commit: `feat(forms): requiresPayment flag on form master`

## Task 5 — Compliance create/edit: `paymentDueDate` + `requiresPayment`

**Files:**
- `src/app/api/compliance/route.ts`
- `src/app/api/compliance/[id]/route.ts`
- `src/app/compliance/create/page.tsx`
- `src/app/compliance/[id]/edit/page.tsx`

### 5.1 `src/app/api/compliance/route.ts` (POST)
- Destructure `paymentDueDate` and `requiresPayment: bodyRequiresPayment` from body.
- Before building the insert, resolve the payment requirement from the form when not provided:

```ts
let requiresPayment = bodyRequiresPayment === true || bodyRequiresPayment === false ? !!bodyRequiresPayment : true
if (bodyRequiresPayment === undefined && formId) {
  const { data: formRow } = await supabaseAdmin
    .from("form_master")
    .select("requiresPayment")
    .eq("id", formId)
    .maybeSingle()
  requiresPayment = formRow?.requiresPayment ?? true
}
```

- Add to the insert payload:
  - `paymentDueDate: paymentDueDate && requiresPayment ? new Date(paymentDueDate).toISOString() : null`
  - `requiresPayment`

### 5.2 `src/app/api/compliance/[id]/route.ts` (PUT)
- Destructure `paymentDueDate`, `requiresPayment` from body.
- In `updateData` block add:

```ts
if (paymentDueDate !== undefined && requiresPayment !== false) {
  updateData.paymentDueDate = paymentDueDate ? new Date(paymentDueDate).toISOString() : null
}
if (requiresPayment !== undefined) {
  updateData.requiresPayment = requiresPayment === true
  if (!requiresPayment) updateData.paymentDueDate = null
}
```

### 5.3 `src/app/compliance/create/page.tsx`
- `Form` interface: add `requiresPayment?: boolean`.
- Add state `const [paymentDueDate, setPaymentDueDate] = useState("")` and `const [requiresPayment, setRequiresPayment] = useState(true)`.
- When a form is selected (`setFormId` handler), set `setRequiresPayment(selectedForm?.requiresPayment ?? true)`.
- Add **Payment Due Date** `<Input type="date">` next to **Due Date** (line ~489), rendered only when `requiresPayment`.
- Include in `handleSubmit` body: `paymentDueDate, requiresPayment` (line ~264).

### 5.4 `src/app/compliance/[id]/edit/page.tsx`
- Same additions; prefill from `d.paymentDueDate` (use the existing `toDateInputValue` helper used for dueDate) and `d.requiresPayment` (default `true`) in the load effect (line ~257).
- Include `paymentDueDate, requiresPayment` in the PUT payload (line ~315).

Verify: `npx tsc --noEmit`, `npx eslint` on the four files

Commit: `feat(compliance): payment due date and requiresPayment on create/edit`

## Task 6 — File route accepts the actual filing date

**Files:**
- `src/app/api/compliance/[id]/file/route.ts`
- `src/app/compliance/[id]/page.tsx`

### 6.1 Route
- `const { filedDate } = await request.json()` (the route currently ignores the body).
- In the update: `filedAt: filedDate ? new Date(filedDate).toISOString() : now()` (currently `filedAt: now()`).

### 6.2 Detail page (File dialog)
- In `handleAction`, when `action === "file"`, add `body.filedDate = filedDate` (new state `filedDate`, default today's `YYYY-MM-DD`).
- In the dialog body for `actionDialog?.type === "file"`, add a **Date of Filing** `<Input type="date">` bound to `filedDate`.
- Reset `filedDate` in `resetPaymentForm` (rename usage or add a separate reset).

Verify: `npx tsc --noEmit`, `npx eslint` on both files

Commit: `feat(compliance): allow back-dated filing date in file action`

## Task 7 — Submit / mark-paid / close route behavior for `requiresPayment`

**Files:**
- `src/app/api/compliance/[id]/submit/route.ts`
- `src/app/api/compliance/[id]/mark-paid/route.ts`
- `src/app/api/compliance/[id]/close/route.ts`

### 7.1 `submit/route.ts`
- Fetch `requiresPayment` (it is included via `*`).
- When `existing.requiresPayment === false`:

```ts
const isPaymentRequired = existing.requiresPayment !== false
```

Skip `validatePaymentSubmission` when not required, and force `filingType = "NIL_RETURN"`, `paymentAmount = 0`, `paymentCurrency = null` (do not store the body's payment values):

```ts
const filingType = isPaymentRequired ? (rawFilingType as string) || "PAYMENT" : "NIL_RETURN"
...
const errors = isPaymentRequired
  ? validatePaymentSubmission({ filingType, amount, currency, refundType: ... })
  : []
```

When `!isPaymentRequired`, set `paymentCurrency: null` in the update instead of the resolved currency.

### 7.2 `mark-paid/route.ts`
- After the status guard, add:

```ts
if (existing.requiresPayment === false) {
  return NextResponse.json(
    { error: "This compliance does not require payment" },
    { status: 400 }
  )
}
```

### 7.3 `close/route.ts`
- Fetch `requiresPayment` in the select (line 39: `id, status, complianceId, filedAt, paidAt, requiresPayment`).
- Relax the guard:

```ts
const needsPaid = existing.requiresPayment !== false
if (
  !["FILED", "PAID"].includes(existing.status) ||
  !existing.filedAt ||
  (needsPaid && !existing.paidAt)
) {
  return NextResponse.json(
    { error: needsPaid ? "Only compliance that is filed and paid can be closed" : "Only compliance that is filed can be closed" },
    { status: 400 }
  )
}
```

Verify: `npx tsc --noEmit`, `npx eslint` on the three routes

Commit: `feat(compliance): non-payment submit/mark-paid/close behavior`

## Task 8 — Compliance detail page (F/P due dates + payment section visibility)

**Files:**
- `src/app/compliance/[id]/page.tsx`

### 8.1 Overdue flags
Replace lines 729–730:

```ts
const dueDays = daysUntil(new Date(data.dueDate))
const isOverdue = !data.filedAt && dueDays < 0

const requiresPayment = data.requiresPayment !== false
const paymentDueDays = data.paymentDueDate ? daysUntil(new Date(data.paymentDueDate)) : null
const paymentOverdue = requiresPayment && !data.paidAt && !data.paymentDate && paymentDueDays !== null && paymentDueDays < 0
```

- "Compliance Info" card (lines 809–821): update the Due line to **Filing Due** + filing overdue/days-left using `isOverdue`/`dueDays`; add a second line **Payment Due** only when `requiresPayment`, using `paymentOverdue`/`paymentDueDays`.
- Details tab due row (line ~951): same treatment (use `isOverdue`).
- Payment Details card (line ~1035): wrap with `requiresPayment &&` (plus existing `(data.paymentAmount != null || data.refundAmount != null)` condition if any) so it is hidden for non-payment filings.

### 8.2 Action buttons
- `APPROVED` block (lines 593–604): push **Mark Paid** only when `requiresPayment`:

```ts
{requiresPayment && (
  <Button key="markPaid" variant="outline" ...>Mark Paid</Button>
)}
```

- `FILED` block (lines 615–622): same guard for the **Mark Paid** button.
- Close button block (lines 624–634): condition becomes:

```ts
if (isAdminOrManager() && data.filedAt && (requiresPayment ? data.paidAt : true) && (status === "FILED" || status === "PAID")) {
```

### 8.3 Submit/Resubmit dialog
- Wrap the "Payment Details (required)" block (lines 1413–1536) with `requiresPayment && (...)`.
- In `handleAction`, when `action === "submit" || action === "resubmit"`, only include payment fields when `requiresPayment`; otherwise skip them entirely.

### 8.4 File dialog
- See Task 6.2 (add the Date of Filing input in this same file).

Verify: `npx tsc --noEmit`, `npx eslint src/app/compliance/[id]/page.tsx`

Commit: `feat(compliance): detail page F/P due dates and payment section visibility`

## Task 9 — Tracker F/P columns + action-based overdue

**Files:**
- `src/app/compliance/page.tsx`

### 9.1 Interface
Add to `ComplianceItem` (line 80): `paymentDueDate: string | null`, `filedAt: string | null`, `paidAt: string | null`, `paymentDate: string | null`, `requiresPayment: boolean`.

### 9.2 Helpers
Replace `getDueDateColor(dueDate: string)` (line 277) with action-based helpers:

```ts
function getDueColor(days: number, done: boolean) {
  if (done) return ""
  if (days < 0) return "text-red-600 font-medium"
  if (days <= 3) return "text-orange-600 font-medium"
  return ""
}
```

### 9.3 Table header
Replace `<TableHead>Due Date</TableHead>` (line 435) with two heads:

```tsx
<TableHead>F Due</TableHead>
<TableHead>P Due</TableHead>
```

### 9.4 Table cell
Replace the Due Date cell (lines 466–479) with:

```tsx
<TableCell className={getDueColor(daysUntil(new Date(item.dueDate)), !!item.filedAt)}>
  <span className="mr-1 text-[10px] font-semibold text-[var(--color-muted-foreground)]" title="Filing Due Date">F</span>
  {formatDate(item.dueDate)}
  {!item.filedAt && daysUntil(new Date(item.dueDate)) < 0 && (
    <span className="ml-1 text-xs text-red-500">(Overdue)</span>
  )}
  {!item.filedAt && daysUntil(new Date(item.dueDate)) >= 0 && daysUntil(new Date(item.dueDate)) <= 3 && (
    <span className="ml-1 text-xs text-orange-500">({daysUntil(new Date(item.dueDate))}d left)</span>
  )}
</TableCell>
<TableCell className={item.requiresPayment === false ? "" : getDueColor(daysUntil(new Date(item.paymentDueDate!)), !!(item.paidAt || item.paymentDate))}>
  {item.requiresPayment === false ? (
    <span className="text-[var(--color-muted-foreground)]" title="Payment not required">—</span>
  ) : item.paymentDueDate ? (
    <>
      <span className="mr-1 text-[10px] font-semibold text-[var(--color-muted-foreground)]" title="Payment Due Date">P</span>
      {formatDate(item.paymentDueDate)}
      {!(item.paidAt || item.paymentDate) && daysUntil(new Date(item.paymentDueDate)) < 0 && (
        <span className="ml-1 text-xs text-red-500">(Overdue)</span>
      )}
      {!(item.paidAt || item.paymentDate) && daysUntil(new Date(item.paymentDueDate)) >= 0 && daysUntil(new Date(item.paymentDueDate)) <= 3 && (
        <span className="ml-1 text-xs text-orange-500">({daysUntil(new Date(item.paymentDueDate))}d left)</span>
      )}
    </>
  ) : (
    "—"
  )}
</TableCell>
```

`item.paymentDueDate!` is only dereferenced when `requiresPayment !== false`; guard with the conditional to avoid `new Date(null)`.

Verify: `npx tsc --noEmit`, `npx eslint src/app/compliance/page.tsx`

Commit: `feat(tracker): F/P due date columns with action-based overdue`

## Task 10 — Dashboard: Filed Late / Paid Late cards + action-based preparer overdue

**Files:**
- `src/app/api/kpi/dashboard/route.ts`
- `src/app/dashboard/page.tsx`

### 10.1 Preparer overdue (action-based)
In the PREPARER branch, the overdue query (lines 97–105) changes from `lt("dueDate", now) + not status in (FILED,APPROVED,CLOSED)` to:

```ts
q = q.lt("dueDate", now.toISOString())
q = q.is("filedAt", null)
```

(Keep the existing `id in prepIds` scoping.)

### 10.2 Manager/admin: filedLate / paidLate
After the existing `overdue` count (line ~287), add two counts (still `eq("orgId", orgId)`):

```ts
const { count: filedLate } = await supabaseAdmin
  .from("compliance_schedules")
  .select("*", { count: "exact", head: true })
  .eq("orgId", orgId)
  .not("filedAt", "is", null)
  .gt("filedAt", "dueDate")

const { count: paidLate } = await supabaseAdmin
  .from("compliance_schedules")
  .select("*", { count: "exact", head: true })
  .eq("orgId", orgId)
  .eq("requiresPayment", true)
  .not("paymentDate", "is", null)
  .not("paymentDueDate", "is", null)
  .gt("paymentDate", "paymentDueDate")
```

(Column-vs-column comparison in PostgREST/Supabase: use the `gt(a,b)` style syntax `gt=paymentDate>paymentDueDate` via `.filter("paymentDate,gt,paymentDueDate")` if `.gt()` with a column name is unsupported — verify at runtime and use `.filter()` accordingly.)

Add `filedLate: filedLate || 0, paidLate: paidLate || 0` to the manager payload (line ~471).

### 10.3 Dashboard page cards
In `transformApiResponse` manager branch (the non-preparer/approver fallback), add two cards after the **Overdue** card:

```ts
{ title: "Filed Late", value: rawData.filedLate ?? 0, icon: "AlertTriangle", color: "orange" },
{ title: "Paid Late", value: rawData.paidLate ?? 0, icon: "AlertTriangle", color: "red" },
```

Verify: `npx tsc --noEmit`, `npx eslint src/app/api/kpi/dashboard/route.ts src/app/dashboard/page.tsx`

Commit: `feat(dashboard): filed/paid late cards and action-based overdue`

## Task 11 — Reports: delay columns

**Files:**
- `src/app/api/reports/route.ts`

Add columns to all three register exports (excel/csv/pdf). Compute per row:

```ts
function dayDiff(value: string | null, due: string | null): string {
  if (!value || !due) return ""
  const ms = new Date(value).getTime() - new Date(due).getTime()
  if (ms <= 0) return ""
  return String(Math.floor(ms / 86400000))
}
```

Add to the row objects (excel addRow lines 191–214, csv records lines 239–262, and the pdf row map):

```ts
paymentDueDate: row.requiresPayment === false ? "N/A" : formatDate(row.paymentDueDate),
requiresPayment: row.requiresPayment === false ? "No" : "Yes",
filingDate: row.filedAt ? formatDate(row.filedAt) : "",
filingDelay: dayDiff(row.filedAt, row.dueDate),
paymentDate: row.requiresPayment === false ? "N/A" : row.paymentDate ? formatDate(row.paymentDate) : "",
paymentDelay: row.requiresPayment === false ? "N/A" : dayDiff(row.paymentDate, row.paymentDueDate),
```

Add matching headers to the excel `columns` array (after `Due Date`, line 179) and to the PDF `autoTable` head/body and CSV `stringify` records (CSV derives headers from record keys, so just add the keys above).

Verify: `npx tsc --noEmit`, `npx eslint src/app/api/reports/route.ts`

Commit: `feat(reports): filing/payment due, actual and delay columns`

## Task 12 — Template pages hide Payment Due Days for no-payment forms

**Files:**
- `src/app/master/compliance-templates/create/page.tsx`
- `src/app/master/compliance-templates/[id]/edit/page.tsx`
- `src/app/master/compliance-templates/[id]/page.tsx`

The forms fetch (`/api/forms`) now returns `requiresPayment` (Task 4). Add it to the form option type.

- **create/edit**: track the selected form's `requiresPayment`. Wrap the **Payment Due Days** input (create line ~487, edit line ~777 region) with `selectedFormRequiresPayment && (...)` — when the selected form requires no payment, do not render the field and set `paymentDueDaysAfterPeriodEnd = ""` (and send `undefined`/`null` in the payload).
- **detail** (`[id]/page.tsx`): when the linked form's `requiresPayment` is false, render "No payment required" instead of the "Payment due: N day(s) after period end" line (line ~598–600) and show "—" in the Payment Due Days info row (line ~777–779).

Verify: `npx tsc --noEmit`, `npx eslint` on the three files

Commit: `feat(templates): hide payment due days for no-payment forms`

## Final verification

```powershell
npx tsc --noEmit
npx vitest run
npx eslint .  # repo-wide; fix any new findings
```

Manual smoke test checklist:
- Create a form with **Requires Payment = No**; create a compliance from it → Payment Due field hidden, tracker P shows `—`, submit dialog has no payment section, no Mark Paid button, Close available after File.
- Create/edit a payment-required compliance with a **Payment Due Date** → tracker shows `P` with the date; overdue only after the date while unpaid.
- File with a back-dated date → tracker F no longer shows Overdue; dashboard **Filed Late** increments; report shows `Filing Date` + `Filing Delay`.
- Mark Paid with a back-dated date → tracker P no longer shows Overdue; dashboard **Paid Late** increments.
- A CLOSED compliance shows no overdue anywhere.
