-- Mandatory payment amount + confirmation checkmarks for compliances.
-- Filing type: PAYMENT (tax paid), NIL_RETURN (amount forced to 0), REFUND_RETURN (refund amount).
-- Refund returns carry a refund type: CLAIMED (from tax authority) or CARRIED_FORWARD.
-- Currency defaults to the filing entity's currency; preparer may change it.
ALTER TABLE compliance_schedules ADD COLUMN IF NOT EXISTS "filingType" TEXT NOT NULL DEFAULT 'PAYMENT';
ALTER TABLE compliance_schedules ADD COLUMN IF NOT EXISTS "refundType" TEXT;
ALTER TABLE compliance_schedules ADD COLUMN IF NOT EXISTS "paymentCurrency" TEXT;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'compliance_schedules_filingType_check'
  ) THEN
    ALTER TABLE compliance_schedules ADD CONSTRAINT "compliance_schedules_filingType_check"
      CHECK ("filingType" IN ('PAYMENT', 'NIL_RETURN', 'REFUND_RETURN'));
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'compliance_schedules_refundType_check'
  ) THEN
    ALTER TABLE compliance_schedules ADD CONSTRAINT "compliance_schedules_refundType_check"
      CHECK ("refundType" IN ('CLAIMED', 'CARRIED_FORWARD'));
  END IF;
END $$;

-- Who/when each actor reconfirmed the payment amount:
--   PREPARER_SUBMIT  - preparer entered the amount when submitting for approval.
--   REVIEWER         - reviewer reconfirmed the amount before approving (step 1).
--   APPROVER         - approver reconfirmed the amount before approving (step 2).
--   PREPARER_PAYMENT - preparer confirmed the same amount was actually paid.
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

-- Backfill currency from the filing entity's currency for existing records.
UPDATE "compliance_schedules" s
SET "paymentCurrency" = e."currency"
FROM "legal_entities" e
WHERE s."entityId" = e."id" AND s."paymentCurrency" IS NULL;
