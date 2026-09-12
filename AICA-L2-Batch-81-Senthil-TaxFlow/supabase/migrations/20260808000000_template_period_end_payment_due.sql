-- Compliance templates: period end date anchor for the first compliance and payment due offset
ALTER TABLE compliance_templates
  ADD COLUMN IF NOT EXISTS "periodEndDate" TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS "paymentDueDaysAfterPeriodEnd" INTEGER,
  ADD COLUMN IF NOT EXISTS "filingEntityId" TEXT REFERENCES legal_entities(id);

-- Compliance schedules: optional payment due date alongside the filing due date
ALTER TABLE compliance_schedules
  ADD COLUMN IF NOT EXISTS "paymentDate" TIMESTAMPTZ;
