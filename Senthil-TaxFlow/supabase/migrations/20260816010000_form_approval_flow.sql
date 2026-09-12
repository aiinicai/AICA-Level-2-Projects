ALTER TABLE form_master ADD COLUMN IF NOT EXISTS "approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL';

ALTER TABLE form_master DROP CONSTRAINT IF EXISTS "form_master_approvalFlow_check";

ALTER TABLE form_master ADD CONSTRAINT "form_master_approvalFlow_check"
  CHECK ("approvalFlow" IN ('NONE', 'ONE_LEVEL', 'TWO_LEVEL'));
