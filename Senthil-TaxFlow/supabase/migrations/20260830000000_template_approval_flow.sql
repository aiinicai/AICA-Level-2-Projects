ALTER TABLE compliance_templates ADD COLUMN IF NOT EXISTS "approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL';

ALTER TABLE compliance_templates DROP CONSTRAINT IF EXISTS "compliance_templates_approvalFlow_check";

ALTER TABLE compliance_templates ADD CONSTRAINT "compliance_templates_approvalFlow_check"
  CHECK ("approvalFlow" IN ('NONE', 'ONE_LEVEL', 'TWO_LEVEL'));
