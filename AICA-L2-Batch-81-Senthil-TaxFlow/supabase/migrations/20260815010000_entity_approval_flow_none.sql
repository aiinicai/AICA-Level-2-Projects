ALTER TABLE legal_entities ADD COLUMN IF NOT EXISTS "approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL';

ALTER TABLE legal_entities DROP CONSTRAINT IF EXISTS "legal_entities_approvalFlow_check";

ALTER TABLE legal_entities ADD CONSTRAINT "legal_entities_approvalFlow_check"
  CHECK ("approvalFlow" IN ('NONE', 'ONE_LEVEL', 'TWO_LEVEL'));
