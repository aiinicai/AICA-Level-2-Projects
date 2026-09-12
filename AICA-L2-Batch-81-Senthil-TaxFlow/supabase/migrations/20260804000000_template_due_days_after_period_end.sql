-- Compliance templates: replace "due day of month" with "days available to file after period end"
ALTER TABLE compliance_templates
  ADD COLUMN IF NOT EXISTS "dueDaysAfterPeriodEnd" INTEGER;

-- Migrate existing templates: due date was previously the day-of-month in the filing month.
-- Interpret that value as days-after-period-end for the new model.
UPDATE compliance_templates
SET "dueDaysAfterPeriodEnd" = "dueDateDay"
WHERE "dueDateDay" IS NOT NULL AND "dueDaysAfterPeriodEnd" IS NULL;
