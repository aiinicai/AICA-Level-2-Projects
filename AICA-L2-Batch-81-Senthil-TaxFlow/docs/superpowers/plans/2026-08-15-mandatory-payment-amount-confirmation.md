# Mandatory Payment Amount + Confirmation Checkmarks — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** The preparer must enter a payment amount (with filing type, optional refund type, and a changeable currency defaulting to the filing entity's currency) when submitting a compliance for approval. Reviewer and approver must reconfirm the amount (checkmark) before approving; the preparer must confirm the same amount was paid before the compliance is marked PAID. The amount/type/currency show on the detail page at every status, in the list, and in reports/exports.

**Spec:** `docs/superpowers/specs/2026-08-15-mandatory-payment-amount-confirmation-design.md`

**Architecture:** New pure validation/logic in `src/lib/payment.ts` (unit-tested with Vitest). Confirmation checkmarks are stored as events in a new `compliance_payment_confirmations` table (stage, confirmedById, confirmedAt). Payment fields live on `compliance_schedules` (reusing existing `paymentAmount`). Route handlers enforce each gate; client dialogs collect the data.

**Tech Stack:** Next.js App Router (route handlers + client components), Supabase via `supabaseAdmin`, TypeScript strict, Tailwind + shadcn/ui, Vitest.

## Global Constraints

- **Read Next.js docs before coding.** This is a modified Next.js. Before touching any Next.js file, read the relevant guide under `node_modules/next/dist/docs/` (e.g. route handlers guide) and heed deprecation notices.
- **Do not add code comments** unless asked.
- **TDD for the pure lib** (`src/lib/payment.ts` + `src/lib/payment.test.ts`); route handlers follow existing patterns and are verified with `npx tsc --noEmit` + manual review.
- Run `npx tsc --noEmit`, `npm run test`, and scoped `npx eslint` after completing the work.
- Do NOT create a git commit for every task unless the plan says so; commit at milestones with repo-style messages (e.g. `feat: mandatory payment amount and confirmations`).

## Key Codebase Facts (read before editing)

- `compliance_schedules` already has: `paymentAmount`, `paymentDate`, `paymentReference`, `paymentMethod`, `paymentNotes`, `paidAt`, `filedAt`, `refundAmount`, `refundReference`. `refundAmount`/`refundReference` stay unused for new records.
- Filing entity is `compliance_schedules.entityId`; `legal_entities.currency` is the default payment currency. Group filings: the filing entity governs.
- Submission flow: `PENDING_PREPARATION`/`PREPARED` → (submit) → `PENDING_APPROVAL`. `src/app/api/compliance/[id]/submit/route.ts`.
- Approval flow: `compliance_approvals` rows have `step` (1 = reviewer, 2 = approver); `src/app/api/compliance/[id]/approve/route.ts`. Approve completes when all approval rows are APPROVED.
- Mark Paid: `src/app/api/compliance/[id]/mark-paid/route.ts` — today admin/manager only, status APPROVED or FILED → PAID.
- Detail page: `src/app/compliance/[id]/page.tsx`. `paymentForm` state at line ~250. Action dialogs (`actionDialog.type`) at line ~244: `"approve" | "reject" | "submit" | "resubmit" | "file" | "submitToAdmin" | "adminApprove" | "sendToReviewer" | "reviewerApprove" | "markPaid" | "close"`. Payment/Refund Details card only renders when `status === "PAID" || paidAt` (line ~981).
- List page: `src/app/compliance/page.tsx`; list API select (`listSelect` in `src/app/api/compliance/route.ts`) already selects `*` so new columns arrive free.
- Reports: `src/app/api/reports/route.ts` — register Excel columns at ~line 169, CSV ~line 225, PDF ~line 280.
- Types: `src/types/index.ts` has a `ComplianceStatus` union (this feature adds no statuses).

---

## Task 1 — Migration + schema snapshot

- [ ] Create `supabase/migrations/<timestamp>_payment_amount_confirmations.sql`:
  ```sql
  ALTER TABLE "compliance_schedules"
    ADD COLUMN IF NOT EXISTS "filingType" TEXT NOT NULL DEFAULT 'PAYMENT',
    ADD COLUMN IF NOT EXISTS "refundType" TEXT,
    ADD COLUMN IF NOT EXISTS "paymentCurrency" TEXT;

  CREATE TABLE IF NOT EXISTS "compliance_payment_confirmations" (
    "id" TEXT NOT NULL,
    "complianceId" TEXT NOT NULL REFERENCES "compliance_schedules"("id") ON DELETE CASCADE,
    "stage" TEXT NOT NULL,
    "confirmedById" TEXT NOT NULL REFERENCES "users"("id"),
    "confirmedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "compliance_payment_confirmations_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "compliance_payment_confirmations_complianceId_stage_key" UNIQUE ("complianceId", "stage")
  );
  CREATE INDEX IF NOT EXISTS "compliance_payment_confirmations_complianceId_idx"
    ON "compliance_payment_confirmations"("complianceId");
  ```
  Then a backfill: for rows where `paymentCurrency IS NULL`, set it from the filing entity's currency:
  ```sql
  UPDATE "compliance_schedules" s
  SET "paymentCurrency" = e."currency"
  FROM "legal_entities" e
  WHERE s."entityId" = e."id" AND s."paymentCurrency" IS NULL;
  ```
- [ ] Mirror the changes in `supabase-full-schema.sql` (add the 3 columns to `compliance_schedules`, add the table definition after `compliance_schedules`).
- [ ] Verify: file reads cleanly; schema snapshot matches migration shape.

## Task 2 — Pure lib `src/lib/payment.ts` + Vitest tests (TDD)

- [ ] Create `src/lib/payment.ts`:
  - `export const FILING_TYPES = ["PAYMENT", "NIL_RETURN", "REFUND_RETURN"] as const`
  - `export type FilingType = typeof FILING_TYPES[number]`
  - `export const REFUND_TYPES = ["CLAIMED", "CARRIED_FORWARD"] as const`
  - `export type RefundType = typeof REFUND_TYPES[number]`
  - `export const CONFIRMATION_STAGES = ["PREPARER_SUBMIT", "REVIEWER", "APPROVER", "PREPARER_PAYMENT"] as const`
  - `export type ConfirmationStage = typeof CONFIRMATION_STAGES[number]`
  - `export interface PaymentSubmission { filingType: string; amount: number; currency: string; refundType?: string | null }`
  - `export function validatePaymentSubmission(input: PaymentSubmission): string[]` returns error messages:
    - filing type must be one of FILING_TYPES
    - amount must be a finite number >= 0
    - `NIL_RETURN` forces amount to 0 → return error if amount !== 0 (message like "NIL return amount must be 0")
    - currency required (non-empty)
    - `REFUND_RETURN` requires `refundType` in REFUND_TYPES
    - `REFUND_RETURN` with non-refund refundType → error; refundType on non-refund filing → error (must be null)
  - `export function confirmationStageForStep(step: number): ConfirmationStage` → `step <= 1 ? "REVIEWER" : "APPROVER"`
  - `export const FILING_TYPE_LABELS: Record<string,string>`, `REFUND_TYPE_LABELS`, `CONFIRMATION_STAGE_LABELS` for UI text.
- [ ] Create `src/lib/payment.test.ts` covering: valid PAYMENT, valid NIL with 0, NIL with non-zero rejected, valid REFUND with CLAIMED and CARRIED_FORWARD, REFUND without refundType rejected, REFUND with bad refundType rejected, refundType on PAYMENT rejected, missing currency rejected, negative amount rejected, `confirmationStageForStep(1) === "REVIEWER"`, `confirmationStageForStep(2) === "APPROVER"`.
- [ ] Verify: `npm run test` (all pass, including the existing 33).

## Task 3 — Submit route: mandatory payment + PREPARER_SUBMIT confirmation

File: `src/app/api/compliance/[id]/submit/route.ts`

- [ ] Read the file fully first. Note it currently requires status `PENDING_PREPARATION` or `PREPARED` and transitions to `PENDING_APPROVAL`.
- [ ] Accept body: `{ filingType, refundType, paymentCurrency, paymentAmount }`.
- [ ] Resolve the default currency: select `currency` from `legal_entities` via `existing.entityId`; if `paymentCurrency` absent, use the entity currency (fallback `"USD"`).
- [ ] Validate with `validatePaymentSubmission`. If errors: `400` with joined message. If `filingType === "NIL_RETURN"`, store amount as `0` (force). Otherwise store the number.
- [ ] In the same update: set `filingType`, `refundType` (only for REFUND_RETURN else null), `paymentCurrency`, `paymentAmount`, and the existing status/`submittedAt` transition.
- [ ] Insert a `compliance_payment_confirmations` row: `{ id: newId(), complianceId: id, stage: "PREPARER_SUBMIT", confirmedById: session.user.id, confirmedAt: new Date().toISOString() }`. Use the existing `newId` import.
- [ ] If the compliance already has payment data (resubmit after rejection), the update overwrites it; no duplicate confirmation row because of the unique constraint — use `.upsert(..., { onConflict: "complianceId,stage" })` or delete+insert if the pattern in the codebase is `insert`. Prefer `.upsert`.
- [ ] Verify: `npx tsc --noEmit` clean.

## Task 4 — Approve route: require amount reconfirmation + REVIEWER/APPROVER confirmation

File: `src/app/api/compliance/[id]/approve/route.ts`

- [ ] Read the file fully first. Understand step ordering (all prior steps approved) and the all-approvals-approved completion.
- [ ] Accept body field `confirmAmount: boolean` (defaults false).
- [ ] Require `existing.paymentAmount != null && existing.filingType` present; if missing → `400` ("Payment details are required before approval").
- [ ] Require `confirmAmount === true`; else `400` ("Amount must be reconfirmed before approval").
- [ ] Determine the stage from the current step via `confirmationStageForStep(step)` (`"REVIEWER"` for step 1, `"APPROVER"` for step 2).
- [ ] Insert the `compliance_payment_confirmations` row (upsert on `complianceId,stage`), `confirmedById: session.user.id`.
- [ ] Do not change the existing approval-record update logic.
- [ ] Verify: `npx tsc --noEmit` clean.

## Task 5 — Mark-paid route: preparer-driven + locked amount + PREPARER_PAYMENT confirmation

File: `src/app/api/compliance/[id]/mark-paid/route.ts`

- [ ] Read the file fully first. Today it requires `activeRole` ADMINISTRATOR/MANAGER.
- [ ] Allow the assigned preparer: extend the select to include `assignments:compliance_assignments(*, preparer:users(id, email))`. Access is allowed when the session user is the assigned preparer OR `activeRole` is ADMINISTRATOR/MANAGER. Otherwise `403`.
- [ ] Require `paymentAmount` already set on the record (locked from submission); if missing → `400`. Ignore any client-sent `paymentAmount` (never overwrite it).
- [ ] Accept `paymentDate`, `paymentReference`, `paymentMethod`, `paymentNotes` as today.
- [ ] Accept `confirmPayment: boolean`; require `true` else `400` ("Payment must be confirmed before marking paid").
- [ ] Insert `compliance_payment_confirmations` row stage `"PREPARER_PAYMENT"`, `confirmedById: session.user.id`.
- [ ] Keep the existing status → `PAID` transition and `paidAt`.
- [ ] Verify: `npx tsc --noEmit` clean.

## Task 6 — Compliance detail page UI (`src/app/compliance/[id]/page.tsx`)

- [ ] **Entity/currency selectors:** the API select for the detail (`complianceSelect` in `src/app/api/compliance/[id]/route.ts`) should include `currency` on the `entity` relation (e.g. `entity:legal_entities(id, entityName, entityNumber, currency)`).
- [ ] **paymentForm state:** add `filingType` (default `"PAYMENT"`), `refundType` (default `""`), `paymentCurrency` (default `""`), `confirmAmount` (bool), `confirmPayment` (bool). Reset in the same places the existing form is reset (the openDialog function resets it around line 252).
- [ ] **Submit / resubmit dialogs** (`actionDialog.type === "submit" || "resubmit"`): render a payment section:
  - Filing Type select (PAYMENT / NIL_RETURN / REFUND_RETURN).
  - Amount input (number). When `filingType === "NIL_RETURN"`, show amount fixed at `0` (input disabled, value "0").
  - Currency select, defaulted to `data.entity?.currency`; include the existing currency options source already used by the create/edit forms (fetch `/api/currencies` or reuse a static list — check how `src/app/master/entities/page.tsx` populates its currency select and reuse that pattern).
  - When `filingType === "REFUND_RETURN"`, show Refund Type select (CLAIMED / CARRIED_FORWARD).
  - Note: this section is separate from the markPaid section; it must not appear for other dialog types.
- [ ] **Submit body:** in `handleAction`, for `action === "submit"` (covers submit + resubmit), add `filingType`, `refundType`, `paymentCurrency`, `paymentAmount` from `paymentForm`. Disable the Submit button when `validatePaymentSubmission` returns errors for the current form values (compute inline).
- [ ] **Approve dialog:** when `actionDialog.type === "approve"`, render a read-only payment summary (filing type label, amount, currency) + a checkbox bound to `paymentForm.confirmAmount` labeled "I reconfirm this amount". Send `confirmAmount: paymentForm.confirmAmount` in the body for `action === "approve"`. Disable Approve until checked.
- [ ] **Mark Paid dialog:** replace the current editable Payment Amount input with a read-only display of the submitted amount/type/currency, keep the payment date/reference/method/notes fields, add checkbox bound to `paymentForm.confirmPayment` labeled "I confirm the same amount has been paid". Send `confirmPayment` in the `mark-paid` body (remove `paymentAmount` from that body). Disable the Mark Paid button until the checkbox is checked.
- [ ] **Always-on payment card:** replace the `{(data.status === "PAID" || data.paidAt) && (...)}` wrapper (line ~981) with a card that renders whenever `data.paymentAmount != null`:
  - Filing type badge (label via `FILING_TYPE_LABELS`), refund type when present, amount (formatted), currency.
  - Confirmation trail: a compact list built from `data.confirmations` (the new relation) showing each stage label + confirmed-by name + timestamp, with a small check icon. Empty state: "Not yet confirmed" for stages not yet reached.
  - Keep existing payment date/reference/method/notes display when present.
- [ ] **Data fetch:** add the confirmations relation to the detail page's `TemplateDetail`-like interface (`data.confirmations` type) and to `complianceSelect` in the detail route: `confirmations:compliance_payment_confirmations(*, confirmedBy:users(id, name))`.
- [ ] Verify: `npx tsc --noEmit` clean.

## Task 7 — Compliance list columns (`src/app/compliance/page.tsx`)

- [ ] Add `Payment Amount`, `Filing Type`, `Currency` columns to the table header and rows (format amount as currency with the row's `paymentCurrency`; filing type as a label/badge).
- [ ] The `listSelect` already selects `*` so `paymentAmount`, `filingType`, `paymentCurrency` are present on each item; update the item type interface accordingly.
- [ ] Verify: `npx tsc --noEmit` clean.

## Task 8 — Reports & exports (`src/app/api/reports/route.ts`)

- [ ] Register output columns for the compliance register:
  - Excel `sheet.columns` (~line 169): add `{ header: "Filing Type", key: "filingType", width: 15 }` and `{ header: "Refund Type", key: "refundType", width: 15 }`; include values in `addRow` (~line 191).
  - CSV `columns` (~line 225): add `filingType`, `refundType`; include values in the row mapping.
  - PDF header + body (~line 280): add the two columns and row values.
- [ ] Verify: `npx tsc --noEmit` clean.

## Task 9 — Full verification

- [ ] `npx tsc --noEmit` — clean (only pre-existing known patterns are acceptable if they existed before this work).
- [ ] `npm run test` — all tests pass (existing 33 + new payment tests).
- [ ] Scoped `npx eslint` on every touched file — no NEW errors beyond the pre-existing `react-hooks/set-state-in-effect` pattern in page effects.
- [ ] Manual smoke (if dev server available): create a compliance → submit with amount/type/currency → confirm reviewer/approver approvals → preparer marks paid → verify amount visible on list/detail/report screens.

## File Map

| File | Change |
|---|---|
| `supabase/migrations/<ts>_payment_amount_confirmations.sql` | new — columns + table + backfill |
| `supabase-full-schema.sql` | mirror schema changes |
| `src/lib/payment.ts` | new — types, labels, `validatePaymentSubmission`, `confirmationStageForStep` |
| `src/lib/payment.test.ts` | new — unit tests |
| `src/app/api/compliance/[id]/submit/route.ts` | mandatory payment + PREPARER_SUBMIT |
| `src/app/api/compliance/[id]/approve/route.ts` | require reconfirmation + REVIEWER/APPROVER |
| `src/app/api/compliance/[id]/mark-paid/route.ts` | preparer-driven + PREPARER_PAYMENT |
| `src/app/api/compliance/[id]/route.ts` | add `currency` on entity relation + `confirmations` relation |
| `src/app/compliance/[id]/page.tsx` | dialogs, payment card, confirmation trail |
| `src/app/compliance/page.tsx` | list columns |
| `src/app/api/reports/route.ts` | register export columns |
