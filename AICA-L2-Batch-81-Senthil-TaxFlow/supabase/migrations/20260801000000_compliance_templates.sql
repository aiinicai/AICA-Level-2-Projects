-- Compliance Templates
CREATE TABLE IF NOT EXISTS compliance_templates (
  id TEXT PRIMARY KEY,
  "orgId" TEXT NOT NULL REFERENCES organizations(id),
  "templateNumber" TEXT UNIQUE,
  version INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'DRAFT',
  "isActive" BOOLEAN NOT NULL DEFAULT true,

  "taxType" TEXT,
  "complianceTypeId" TEXT REFERENCES compliance_types(id),
  "formId" TEXT REFERENCES form_master(id),
  "countryId" TEXT NOT NULL REFERENCES countries(id),
  frequency TEXT NOT NULL,
  "dueDateDay" INTEGER,
  priority TEXT NOT NULL DEFAULT 'NORMAL',
  "isRecurring" BOOLEAN NOT NULL DEFAULT true,
  "recurringEndDate" TIMESTAMPTZ,
  notes TEXT,

  "preparerId" TEXT REFERENCES users(id),
  "approverId" TEXT REFERENCES users(id),

  "submittedAt" TIMESTAMPTZ,
  "submittedById" TEXT REFERENCES users(id),
  "adminApprovedAt" TIMESTAMPTZ,
  "adminApprovedById" TEXT REFERENCES users(id),
  "reviewerId" TEXT REFERENCES users(id),
  "reviewerActionAt" TIMESTAMPTZ,
  "reviewerComments" TEXT,
  "adminComments" TEXT,
  "approvedAt" TIMESTAMPTZ,
  "approvedById" TEXT REFERENCES users(id),
  "rejectedAt" TIMESTAMPTZ,
  "rejectedById" TEXT REFERENCES users(id),

  "createdById" TEXT NOT NULL REFERENCES users(id),
  "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_templates_org ON compliance_templates("orgId");
CREATE INDEX idx_templates_status ON compliance_templates(status);
CREATE INDEX idx_templates_country ON compliance_templates("countryId");
CREATE INDEX idx_templates_tax_type ON compliance_templates("taxType");

-- Template ↔ Entity junction
CREATE TABLE IF NOT EXISTS compliance_template_entities (
  id TEXT PRIMARY KEY,
  "templateId" TEXT NOT NULL REFERENCES compliance_templates(id) ON DELETE CASCADE,
  "entityId" TEXT NOT NULL REFERENCES legal_entities(id),
  "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE("templateId", "entityId")
);

-- Template version history
CREATE TABLE IF NOT EXISTS compliance_template_versions (
  id TEXT PRIMARY KEY,
  "templateId" TEXT NOT NULL REFERENCES compliance_templates(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  snapshot JSONB NOT NULL,
  "fieldDiffs" JSONB,
  "changeReason" TEXT,
  "changedById" TEXT NOT NULL REFERENCES users(id),
  "changedAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE("templateId", version)
);

-- Link compliance_schedules back to template
ALTER TABLE compliance_schedules
  ADD COLUMN IF NOT EXISTS "templateId" TEXT REFERENCES compliance_templates(id),
  ADD COLUMN IF NOT EXISTS "templateVersion" INTEGER;

CREATE INDEX idx_schedules_template ON compliance_schedules("templateId");
