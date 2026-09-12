# Dual Due Dates (Filing + Payment), Actual Dates, and Delay Capture

**Date:** 2026-08-15

## Goal

Every compliance has two due dates: a **filing due date** and a **payment due date**. The compliance tracker shows both (labeled `F` and `P`). Closed/completed compliance must **not** show as overdue. The File and Mark Paid screens accept the **actual** date of filing / date of payment so that delays (filed late / paid late) are captured in reports and the dashboard even after completion.

Not every filing requires payment. The **form master** carries a `requiresPayment` flag; individual compliance schedules inherit it and **dynamically show or hide the payment section** (payment due date, submit payment details, mark-paid, payment cards) accordingly.

## Background

- `compliance_schedules.dueDate` is the filing due date.
- `compliance_schedules.paymentDate` is currently **overloaded**: template generation writes the payment *due* date into it (`src/lib/template-compliance.ts`, `src/app/api/templates/generate/route.ts`, `src/app/api/templates/[id]/generate/route.ts`), while `mark-paid` overwrites it with the *actual* payment date (`src/app/api/compliance/[id]/mark-paid/route.ts:92`).
- The tracker (`src/app/compliance/page.tsx:466-478`) and detail page (`src/app/compliance/[id]/page.tsx:729-730`) mark items overdue purely by calendar date, ignoring status — so a closed compliance shows `(Overdue)`.
- The dashboard overdue count (`src/app/api/kpi/dashboard/route.ts`) excludes FILED/APPROVED/CLOSED entirely, so late-but-completed items never appear anywhere.

## Section 1 — Data model

Four distinct dates per compliance:

| Field | Meaning | Source |
|---|---|---|
| `dueDate` | Filing due date (F) | existing; template or ad-hoc create/edit |
| `paymentDueDate` | Payment due date (P) — **NEW column** | templates write here; optional field on ad-hoc create/edit |
| `filedAt` | Actual date filed | file dialog date input (defaults to today) |
| `paymentDate` | Actual date paid | mark-paid dialog date input (existing, unchanged semantics) |
| `paidAt` | Timestamp of the mark-paid action | existing, unchanged |
| `requiresPayment` | Whether this filing needs payment — **NEW columns** on `form_master` and `compliance_schedules` | snapshot copied from the form at compliance creation (default `true` when no form) |

### 1.1 Schema

New migration `supabase/migrations/20260815020000_payment_due_date.sql`:

```sql
ALTER TABLE compliance_schedules
  ADD COLUMN IF NOT EXISTS "paymentDueDate" TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS "requiresPayment" BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE form_master
  ADD COLUMN IF NOT EXISTS "requiresPayment" BOOLEAN NOT NULL DEFAULT true;

-- Best-effort backfill: rows not yet marked paid hold a payment DUE date in paymentDate.
UPDATE compliance_schedules
SET "paymentDueDate" = "paymentDate"
WHERE "paidAt" IS NULL AND "paymentDate" IS NOT NULL AND "paymentDueDate" IS NULL;
```

Mirror both new columns in `supabase-full-schema.sql` (`compliance_schedules` and `form_master` CREATE TABLE).

### 1.2 Generation code writes paymentDueDate

- `src/lib/compliance-period.ts`: keep computing a `paymentDate` value in the generation result, but it is now the payment **due** date. Rename the returned field to `paymentDueDate` for clarity (update `GenerationResult` interface + the `.test.ts` expectations).
- `src/lib/template-compliance.ts` (`insertGeneratedCompliance`): write `paymentDueDate: generation.paymentDueDate.toISOString()` instead of `paymentDate`. Update `GeneratedComplianceInput.generation` shape.
- `src/app/api/templates/generate/route.ts` and `src/app/api/templates/[id]/generate/route.ts`: pass/write `paymentDueDate` (not `paymentDate`).

### 1.3 Ad-hoc create/edit accepts paymentDueDate + requiresPayment

- `POST /api/compliance` (`src/app/api/compliance/route.ts`): accept `paymentDueDate` in body; persist `paymentDueDate: paymentDueDate ? new Date(paymentDueDate).toISOString() : null`. Accept `requiresPayment`; if not provided, derive it from the linked form (`form_master.requiresPayment` by `formId`, default `true`).
- `PUT /api/compliance/[id]` (`src/app/api/compliance/[id]/route.ts`): accept `paymentDueDate` (persist ISO string or null) and `requiresPayment` (boolean). When `requiresPayment` flips to `false`, clear `paymentDueDate`/`paymentDate`.
- `src/app/compliance/create/page.tsx` and `src/app/compliance/[id]/edit/page.tsx`: add optional **Payment Due Date** date input next to **Due Date**; include `paymentDueDate` and `requiresPayment` in POST/PUT payloads; prefill on edit. The Payment Due Date field renders only when `requiresPayment` is `true` (derived from the selected form; default `true` with no form). The `Form` interface gains `requiresPayment`.

### 1.4 Template generation propagates requiresPayment

- `src/lib/template-compliance.ts` (`insertGeneratedCompliance`): fetch `form_master.requiresPayment` for `template.formId` (default `true` when no form) and write it to the generated schedule. Template-generated schedules never receive a `paymentDate` (only `paymentDueDate`).

## Section 2 — Tracker F/P columns + overdue fix

### 2.1 `src/app/compliance/page.tsx`

Replace the single `Due Date` column with two columns:

- **F Due** — filing due date; small `F` badge; tooltip "Filing Due Date".
- **P Due** — payment due date; small `P` badge; tooltip "Payment Due Date"; `—` when absent.

Add `paymentDueDate`, `filedAt`, `paidAt`, `paymentDate`, `requiresPayment` to the `ComplianceItem` interface.

- **P Due** shows `—` when `requiresPayment` is `false` (muted, tooltip "Payment not required").

Overdue (action-based) rules:

- **F cell**: red + `(Overdue)` only when `!filedAt && daysUntil(dueDate) < 0`. Orange "X days left" only when `!filedAt`.
- **P cell**: only evaluated when `requiresPayment` is `true`. Red + `(Overdue)` only when `paymentDueDate` is set, `daysUntil(paymentDueDate) < 0`, and `!paidAt && !paymentDate`. Orange hint only while not paid.
- Filed/paid cells render the due date in normal color. **Closed/completed items never show Overdue.**

### 2.2 `src/app/compliance/[id]/page.tsx`

- Compute per-date overdue flags: filing overdue = `!data.filedAt && daysUntil(data.dueDate) < 0`; payment overdue = `requiresPayment && paymentDueDate set && daysUntil(paymentDueDate) < 0 && not paid`.
- "Compliance Info" card and "Details" tab show both **Filing Due** and **Payment Due** with the per-date flags. **Payment Due** is hidden when `requiresPayment` is `false`.
- Payment Details card (rendered only when `requiresPayment` is `true`) shows **Date Filed** (`filedAt`) and **Date of Payment** (`paymentDate`).
- Action buttons: **Mark Paid** is shown only when `requiresPayment` is `true`. **Close** is available after filing for both cases (see 3.3).

## Section 3 — File & payment screens (actual dates)

### 3.1 File dialog + route

- `src/app/compliance/[id]/page.tsx`: add **Date of Filing** date input to the `file` dialog, defaulting to today. Send as `filedDate` in the action body.
- `src/app/api/compliance/[id]/file/route.ts`: accept optional `filedDate`; set `filedAt = filedDate ? new Date(filedDate).toISOString() : now()`. Keep existing status guards.

### 3.2 Mark Paid dialog + route

- Relabel the existing **Payment Date** input to **Date of Payment**, default to today.
- `src/app/api/compliance/[id]/mark-paid/route.ts`: unchanged semantics — writes the actual date to `paymentDate`. It must not touch `paymentDueDate`. Guard: reject with 400 when `requiresPayment` is `false`.

### 3.3 Payment section visibility (requiresPayment = false)

- **Submit/Resubmit dialog** (`[id]/page.tsx`): hide the **"Payment Details (required)"** section entirely when `requiresPayment` is `false`; do not send payment fields.
- **Submit/Resubmit routes** (`submit`, `resubmit`, `submit-to-admin`): when `requiresPayment` is `false`, skip `validatePaymentSubmission` and persist `filingType: "NIL_RETURN"`, `paymentAmount: 0`, `paymentCurrency: null` (keeps the schema consistent; no payment data is collected).
- **Close route** (`src/app/api/compliance/[id]/close/route.ts`): guard becomes — `requiresPayment = true` → status `FILED`/`PAID` **and** both `filedAt` and `paidAt` set; `requiresPayment = false` → status `FILED`/`PAID` **and** `filedAt` set (paid not required).
- **Mark Paid** action is hidden when `requiresPayment` is `false` (a payment-only compliance flow never enters the payment step).

## Section 4 — Reports & dashboard delay capture

### 4.1 Dashboard (`src/app/api/kpi/dashboard/route.ts` + `src/app/dashboard/page.tsx`)

Manager/admin payload additions:

- `filedLate`: count where `filedAt > dueDate` (including FILED/CLOSED).
- `paidLate`: count where `requiresPayment` is `true` **and** `paymentDate > paymentDueDate` and `paymentDueDate` not null.
- Add **Filed Late** and **Paid Late** cards next to **Overdue**.

Preparer payload: switch the **Overdue** count to action-based — `dueDate < now` and `filedAt IS NULL` (plus existing preparer scoping), instead of `status not in (FILED, APPROVED, CLOSED)`.

### 4.2 Reports (`src/app/api/reports/route.ts`)

Add columns to the compliance-register exports (excel/csv/pdf):

- `Filing Due Date` (`dueDate`), `Payment Due Date` (`paymentDueDate`)
- `Requires Payment` (`Yes`/`No`)
- `Filing Date` (`filedAt`), `Filing Delay (days)` = `max(0, filedAt − dueDate)` in whole days, blank when not filed
- `Payment Date` (`paymentDate`), `Payment Delay (days)` = `max(0, paymentDate − paymentDueDate)` in whole days; blank when no payment due date; `N/A` for all payment columns when `requiresPayment` is `false`

## Section 5 — Form master "requires payment" flag

### 5.1 Form master CRUD + API

- `src/app/api/forms/route.ts` (GET): include `requiresPayment` in the select and response.
- `src/app/api/forms/route.ts` (POST) and `src/app/api/forms/[id]/route.ts` (PUT): accept and persist `requiresPayment` (boolean, default `true`).
- `src/app/api/forms/upload/route.ts`: accept optional `requiresPayment` import column ("yes"/"true"/"no"/"false"); default `true`.
- `src/app/master/forms/page.tsx`: add a **Requires Payment** toggle to the create/edit dialog and a **Payment Required** column/badge in the table. Add `requiresPayment` to `importColumns` (optional).

### 5.2 Templates

- `src/app/master/compliance-templates/create/page.tsx` and `[id]/edit/page.tsx`: hide the **Payment Due Days** field when the selected form's `requiresPayment` is `false` (forms list already fetched; add `requiresPayment` to the form options type). Clear `paymentDueDaysAfterPeriodEnd` in the payload in that case.
- `src/app/master/compliance-templates/[id]/page.tsx` (detail): when the form requires no payment, show "No payment required" instead of the payment due days line.

## Out of Scope

- Calendar page: already treats FILED/PAID/CLOSED as completed; no changes.
- Approver dashboard: no due-date-based metrics; no changes.
- No `closedAt` column or status flow changes.
- No editing of `filedAt`/`paymentDate` after the fact (set at action time).
- No changes to the compliance CSV import flow (`api/compliance/import/route.ts`) — imported schedules default `requiresPayment = true`.

## Verification

- `npx tsc --noEmit`
- `npx eslint` on changed files
- `npx vitest run` (covers `compliance-period.test.ts` updates)
- Manual:
  - Template generation sets both F and P due dates; tracker shows both.
  - Ad-hoc create/edit accepts a payment due date; tracker shows P.
  - File with a back-dated filing date; filed-late item appears in dashboard "Filed Late" and report delay column; tracker no longer shows it overdue.
  - Mark Paid with a back-dated payment date; paid-late item appears in dashboard "Paid Late"; tracker no longer shows P overdue.
  - A CLOSED compliance shows no overdue anywhere.
  - A form marked "Requires Payment = No": new/generated compliance shows no Payment Due (P `—`), no "Payment Details" in submit dialog, no Mark Paid button, and closes right after filing. Its report row shows `Requires Payment = No` and `N/A` payment columns.
