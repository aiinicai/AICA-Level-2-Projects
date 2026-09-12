-- Per-entity approval flow: a "reviewer" level sits between preparer and approver.
--   ONE_LEVEL: only the reviewer approves (no approver step).
--   TWO_LEVEL: reviewer approves first, then it flows to the approver.
ALTER TABLE legal_entities ADD COLUMN IF NOT EXISTS "approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL';

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'legal_entities_approvalFlow_check'
  ) THEN
    ALTER TABLE legal_entities ADD CONSTRAINT "legal_entities_approvalFlow_check"
      CHECK ("approvalFlow" IN ('ONE_LEVEL', 'TWO_LEVEL'));
  END IF;
END $$;

-- Step on compliance approvals: 1 = reviewer, 2 = approver. Existing records default to step 1,
-- preserving the legacy "all assigned approvers must approve" behavior.
ALTER TABLE compliance_approvals ADD COLUMN IF NOT EXISTS "step" INTEGER NOT NULL DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_compliance_approvals_compliance_step
  ON compliance_approvals("complianceId", "step");

-- Reviewer assigned to compliances generated from a template (distinct from the template's own
-- lifecycle reviewer column). Used with approverId to build the generated approval chain.
ALTER TABLE compliance_templates ADD COLUMN IF NOT EXISTS "complianceReviewerId" TEXT REFERENCES users(id);
