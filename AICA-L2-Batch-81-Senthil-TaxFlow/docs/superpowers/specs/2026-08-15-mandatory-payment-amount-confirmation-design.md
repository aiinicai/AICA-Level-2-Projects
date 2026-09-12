# Mandatory Payment Amount + Confirmation Checkmarks — Design Spec

Date: 2026-08-15

## Problem

Compliance amounts are only captured by admin/manager at the Mark Paid stage, after
approval/filing. There is no record of the payment amount, filing type, or currency at
submission time, and no per-actor confirmation that the amount is correct or that the
same amount was actually paid.

## Goals

1. The preparer **must** enter the payment amount when submitting a compliance for approval.
2. Capture a **filing type**: actual payment, NIL return, or refund return.
3. Refund returns carry a **refund type**: claimed from tax authority, or carried forward.
4. Currency defaults to the (filing) entity's currency; preparer may change it.
5. Reviewer and/or approver must click a **checkmark** next to the payment amount to
   reconfirm it before sending the compliance to the next step.
6. The preparer must click a **checkmark** at the payment screen to confirm the same
   amount has been paid before the compliance is marked PAID.
7. The amount and filing type are visible on **all screens** (detail at every status,
   list, reports, exports).

## Decisions

- **Approach:** fields on `compliance_schedules` (reusing `paymentAmount`) + a new
  `compliance_payment_confirmations` table for the who/when checkmark events.
- **Amount is a single field** whose meaning is given by `filingType`:
  - `PAYMENT` → tax paid
  - `NIL_RETURN` → forced to `0` (backend forces 0; non-zero rejected)
  - `REFUND_RETURN` → refund amount
- **Only the preparer edits the amount.** Reviewer/approver reconfirm or reject.
- **Preparer drives PAID.** The preparer confirms actual payment at the payment screen;
  admin/manager remains a fallback when no preparer is assigned.
- Admin **file/close** actions add no new confirmation step.
- For **group filings**, the filing entity governs: currency defaults to the filing
  entity's currency (consistent with how approval flow already resolves).

## Data Model

### `compliance_schedules` — new columns

| Column | Type | Notes |
|---|---|---|
| `filingType` | TEXT NOT NULL DEFAULT 'PAYMENT' | `PAYMENT` \| `NIL_RETURN` \| `REFUND_RETURN` |
| `refundType` | TEXT NULL | `CLAIMED` \| `CARRIED_FORWARD`; only for `REFUND_RETURN` |
| `paymentCurrency` | TEXT NULL | Defaults to filing entity's `legal_entities.currency` |

Reused existing columns: `paymentAmount` (the single amount), `paymentDate`,
`paymentReference`, `paymentMethod`, `paymentNotes`, `paidAt`, `filedAt`.
`refundAmount` / `refundReference` become unused for new records.

### New table `compliance_payment_confirmations`

```
id            TEXT PRIMARY KEY
complianceId  TEXT NOT NULL REFERENCES compliance_schedules(id)
stage         TEXT NOT NULL   -- PREPARER_SUBMIT | REVIEWER | APPROVER | PREPARER_PAYMENT
confirmedById TEXT NOT NULL REFERENCES users(id)
confirmedAt   TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
UNIQUE(complianceId, stage)
```

Index on `complianceId`.

## Workflow & Gating

1. **Submit (preparer, PENDING_PREPARATION/PREPARED):**
   - Filing type, amount, and currency are **required**.
   - NIL_RETURN: amount input shown but locked/auto-set to `0`.
   - REFUND_RETURN: refund type select appears (`CLAIMED` / `CARRIED_FORWARD`).
   - Currency defaults to filing entity's currency; preparer may change it.
   - On submit: writes `filingType`/`refundType`/`paymentCurrency`/`paymentAmount`,
     inserts a `PREPARER_SUBMIT` confirmation, transitions to `PENDING_APPROVAL`.
   - Backend returns 400 when filing type, amount, or currency is missing, when
     NIL_RETURN amount is non-zero, or when REFUND_RETURN lacks a refund type.
2. **Reviewer approve (step 1):** approve dialog shows amount/type/currency read-only
   plus a required "I reconfirm this amount" checkbox. Approve disabled until checked.
   Backend requires the confirmation flag and inserts a `REVIEWER` confirmation.
3. **Approver approve (step 2):** same pattern → `APPROVER` confirmation.
4. **Payment step (preparer, status APPROVED or FILED):**
   - Mark Paid is performed by the assigned preparer.
   - Payment screen shows the locked submitted amount; preparer enters payment
     date/reference/method and checks "I confirm the same amount has been paid".
   - Inserts a `PREPARER_PAYMENT` confirmation → status `PAID`.
   - Admin/manager fallback when no preparer is assigned.
5. **File / Close (admin/manager):** unchanged; amount remains visible.

## UI

- **Submit dialog:** filing type select, amount input (locked to 0 for NIL), currency
  select (defaulted), refund type select (when REFUND_RETURN).
- **Approve dialogs (reviewer/approver):** read-only payment summary + confirmation
  checkbox gating the Approve button.
- **Payment dialog (preparer):** locked amount, payment date/reference/method fields,
  confirmation checkbox gating Mark Paid.
- **Detail page:** a Payment/Amount card visible **at every status** once an amount
  exists. Shows filing type badge, refund type, amount + currency, and the confirmation
  trail (each stage: who + when). The existing PAID-only card is replaced by this
  always-on card.
- **List page:** add Payment Amount, Filing Type, Currency columns.
- **Reports/exports:** add amount, filing type, refund type, currency to the register
  and Excel/CSV/PDF outputs.

## Backend Enforcement

- `src/app/api/compliance/[id]/submit/route.ts`: validate filing type / amount /
  currency (+ refund type), write fields, insert `PREPARER_SUBMIT`.
- `src/app/api/compliance/[id]/approve/route.ts`: require confirmation flag, insert
  `REVIEWER` / `APPROVER` confirmation based on the current step.
- `src/app/api/compliance/[id]/mark-paid/route.ts`: rework to preparer, locked amount,
  `PREPARER_PAYMENT` confirmation.
- All `complianceSelect` / `listSelect` query strings add the
  `compliance_payment_confirmations` relation.

## Migration & Backfill

Single migration:
1. `ALTER TABLE compliance_schedules ADD COLUMN IF NOT EXISTS filingType TEXT NOT NULL DEFAULT 'PAYMENT'`,
   `ADD COLUMN IF NOT EXISTS refundType TEXT`,
   `ADD COLUMN IF NOT EXISTS paymentCurrency TEXT`.
2. `CREATE TABLE compliance_payment_confirmations (...)`, unique constraint, index.
3. Backfill `paymentCurrency` from the filing entity's currency for existing rows where
   null.
4. Existing PAID/paid rows get `filingType = 'PAYMENT'` (already the default).

Also update `supabase-full-schema.sql` to match.

## Out of Scope

- Changing file/close confirmation requirements.
- Editable amounts after submission (preparer edits via reject/resubmit only).
- New compliance statuses.
