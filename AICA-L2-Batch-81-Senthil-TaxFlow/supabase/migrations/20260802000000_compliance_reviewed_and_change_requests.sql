-- Compliance workflow: add REVIEWED status (2nd-level review completed)
DO $$ BEGIN
  ALTER TYPE "ComplianceStatus" ADD VALUE IF NOT EXISTS 'REVIEWED';
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- Template change requests: non-admin edits to approved templates await admin approval
CREATE TABLE IF NOT EXISTS template_change_requests (
  id TEXT PRIMARY KEY,
  "templateId" TEXT NOT NULL REFERENCES compliance_templates(id) ON DELETE CASCADE,
  "orgId" TEXT NOT NULL REFERENCES organizations(id),
  "requestedById" TEXT NOT NULL,
  snapshot JSONB NOT NULL,
  "fieldDiffs" JSONB,
  "changeReason" TEXT,
  status TEXT NOT NULL DEFAULT 'PENDING',
  "reviewedById" TEXT,
  "reviewedAt" TIMESTAMPTZ,
  "reviewComments" TEXT,
  "requestedAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT template_change_requests_requestedById_fkey FOREIGN KEY ("requestedById") REFERENCES users(id),
  CONSTRAINT template_change_requests_reviewedById_fkey FOREIGN KEY ("reviewedById") REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_change_requests_template ON template_change_requests("templateId");
CREATE INDEX IF NOT EXISTS idx_change_requests_status ON template_change_requests(status);