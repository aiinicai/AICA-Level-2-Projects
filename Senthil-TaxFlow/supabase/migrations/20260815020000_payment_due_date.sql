-- Dual due dates (filing + payment) and form-level payment requirement
ALTER TABLE compliance_schedules
  ADD COLUMN IF NOT EXISTS "paymentDueDate" TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS "requiresPayment" BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE form_master
  ADD COLUMN IF NOT EXISTS "requiresPayment" BOOLEAN NOT NULL DEFAULT true;

-- Best-effort backfill: rows never marked paid hold a payment DUE date in paymentDate.
UPDATE compliance_schedules
SET "paymentDueDate" = "paymentDate"
WHERE "paidAt" IS NULL AND "paymentDate" IS NOT NULL AND "paymentDueDate" IS NULL;
