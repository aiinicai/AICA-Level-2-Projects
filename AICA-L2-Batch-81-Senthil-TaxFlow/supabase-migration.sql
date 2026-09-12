-- Migration: Add multi-org support
-- This is additive: skips types/tables/indexes/constraints that already exist.

-- Types (skip if already exist)
DO $$ BEGIN CREATE TYPE "Role" AS ENUM ('ADMINISTRATOR', 'MANAGER', 'PREPARER', 'APPROVER'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE "ComplianceStatus" AS ENUM ('DRAFT','PENDING_PREPARATION','PREPARED','PENDING_APPROVAL','APPROVED','REJECTED','FILED','CLOSED'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE "Priority" AS ENUM ('NORMAL','HIGH','CRITICAL'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE "Frequency" AS ENUM ('WEEKLY','MONTHLY','BI_MONTHLY','QUARTERLY','HALF_YEARLY','ANNUAL','AD_HOC'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE "TaxType" AS ENUM ('GST','VAT','SALES_TAX','WHT','CORPORATE_TAX','STATUTORY'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE "EntityStatus" AS ENUM ('ACTIVE','INACTIVE','SUSPENDED'); EXCEPTION WHEN duplicate_object THEN null; END $$;

-- New tables
CREATE TABLE IF NOT EXISTS "organizations" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "createdById" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "organizations_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "organizations_slug_key" ON "organizations"("slug");

CREATE TABLE IF NOT EXISTS "organization_members" (
    "id" TEXT NOT NULL,
    "orgId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "roles" TEXT[] DEFAULT '{PREPARER}',
    "createdById" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "organization_members_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "organization_members_orgId_userId_key" ON "organization_members"("orgId", "userId");

-- Existing users table: add roles array column
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "roles" TEXT[] DEFAULT '{PREPARER}';

-- Existing master-data tables: add orgId column
ALTER TABLE "legal_entities" ADD COLUMN IF NOT EXISTS "orgId" TEXT;
ALTER TABLE "compliance_types" ADD COLUMN IF NOT EXISTS "orgId" TEXT;
ALTER TABLE "form_master" ADD COLUMN IF NOT EXISTS "orgId" TEXT;
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "orgId" TEXT;

-- Drop old unique constraints that conflict with new org-scoped ones
ALTER TABLE "legal_entities" DROP CONSTRAINT IF EXISTS "legal_entities_entityNumber_key";
ALTER TABLE "compliance_types" DROP CONSTRAINT IF EXISTS "compliance_types_name_key";
ALTER TABLE "form_master" DROP CONSTRAINT IF EXISTS "form_master_formNumber_countryId_key";

-- Create new org-scoped unique indexes (skip if exist)
CREATE UNIQUE INDEX IF NOT EXISTS "legal_entities_orgId_entityNumber_key" ON "legal_entities"("orgId", "entityNumber");
CREATE UNIQUE INDEX IF NOT EXISTS "compliance_types_orgId_name_key" ON "compliance_types"("orgId", "name");
CREATE UNIQUE INDEX IF NOT EXISTS "form_master_orgId_formNumber_countryId_key" ON "form_master"("orgId", "formNumber", "countryId");

-- Foreign keys (skip if already exist)
DO $$ BEGIN
  ALTER TABLE "organizations" ADD CONSTRAINT "organizations_createdById_fkey" FOREIGN KEY ("createdById") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "organization_members" ADD CONSTRAINT "organization_members_orgId_fkey" FOREIGN KEY ("orgId") REFERENCES "organizations"("id") ON DELETE CASCADE ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "organization_members" ADD CONSTRAINT "organization_members_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "organization_members" ADD CONSTRAINT "organization_members_createdById_fkey" FOREIGN KEY ("createdById") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "legal_entities" ADD CONSTRAINT "legal_entities_orgId_fkey" FOREIGN KEY ("orgId") REFERENCES "organizations"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "legal_entities" ADD CONSTRAINT "legal_entities_countryId_fkey" FOREIGN KEY ("countryId") REFERENCES "countries"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "compliance_types" ADD CONSTRAINT "compliance_types_orgId_fkey" FOREIGN KEY ("orgId") REFERENCES "organizations"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "compliance_types" ADD CONSTRAINT "compliance_types_countryId_fkey" FOREIGN KEY ("countryId") REFERENCES "countries"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "form_master" ADD CONSTRAINT "form_master_orgId_fkey" FOREIGN KEY ("orgId") REFERENCES "organizations"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "form_master" ADD CONSTRAINT "form_master_complianceTypeId_fkey" FOREIGN KEY ("complianceTypeId") REFERENCES "compliance_types"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "form_master" ADD CONSTRAINT "form_master_countryId_fkey" FOREIGN KEY ("countryId") REFERENCES "countries"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_orgId_fkey" FOREIGN KEY ("orgId") REFERENCES "organizations"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_entityId_fkey" FOREIGN KEY ("entityId") REFERENCES "legal_entities"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_countryId_fkey" FOREIGN KEY ("countryId") REFERENCES "countries"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_complianceTypeId_fkey" FOREIGN KEY ("complianceTypeId") REFERENCES "compliance_types"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_formId_fkey" FOREIGN KEY ("formId") REFERENCES "form_master"("id") ON DELETE SET NULL ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "compliance_assignments" ADD CONSTRAINT "compliance_assignments_complianceId_fkey" FOREIGN KEY ("complianceId") REFERENCES "compliance_schedules"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "compliance_assignments" ADD CONSTRAINT "compliance_assignments_preparerId_fkey" FOREIGN KEY ("preparerId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "compliance_approvals" ADD CONSTRAINT "compliance_approvals_complianceId_fkey" FOREIGN KEY ("complianceId") REFERENCES "compliance_schedules"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "compliance_approvals" ADD CONSTRAINT "compliance_approvals_approverId_fkey" FOREIGN KEY ("approverId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "attachments" ADD CONSTRAINT "attachments_complianceId_fkey" FOREIGN KEY ("complianceId") REFERENCES "compliance_schedules"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "attachments" ADD CONSTRAINT "attachments_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "comments" ADD CONSTRAINT "comments_complianceId_fkey" FOREIGN KEY ("complianceId") REFERENCES "compliance_schedules"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "comments" ADD CONSTRAINT "comments_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "audit_trails" ADD CONSTRAINT "audit_trails_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "notifications" ADD CONSTRAINT "notifications_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "activities" ADD CONSTRAINT "activities_complianceId_fkey" FOREIGN KEY ("complianceId") REFERENCES "compliance_schedules"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "activities" ADD CONSTRAINT "activities_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
  EXCEPTION WHEN duplicate_object THEN null; END $$;

-- Forms: replace complianceTypeId with direct taxType
ALTER TABLE "form_master" ADD COLUMN IF NOT EXISTS "taxType" "TaxType";
ALTER TABLE "form_master" ALTER COLUMN "complianceTypeId" DROP NOT NULL;
ALTER TABLE "form_master" ALTER COLUMN "countryId" DROP NOT NULL;

-- Forms: multi-country support
CREATE TABLE IF NOT EXISTS "form_countries" (
    "id" TEXT NOT NULL,
    "formId" TEXT NOT NULL,
    "countryId" TEXT NOT NULL,
    CONSTRAINT "form_countries_pkey" PRIMARY KEY ("id")
);
DO $$ BEGIN
  ALTER TABLE "form_countries" ADD CONSTRAINT "form_countries_formId_fkey" FOREIGN KEY ("formId") REFERENCES "form_master"("id") ON DELETE CASCADE ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "form_countries" ADD CONSTRAINT "form_countries_countryId_fkey" FOREIGN KEY ("countryId") REFERENCES "countries"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- Compliance schedules: add tax period start/end and filing month columns
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "taxPeriodStart" TIMESTAMP(3);
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "taxPeriodEnd" TIMESTAMP(3);
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "filingMonth" TEXT;

-- Workflow: new statuses, reviewer, creator, payment/refund tracking
DO $$ BEGIN
  ALTER TYPE "ComplianceStatus" ADD VALUE IF NOT EXISTS 'PENDING_ADMIN_APPROVAL';
  EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TYPE "ComplianceStatus" ADD VALUE IF NOT EXISTS 'PENDING_REVIEW';
  EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TYPE "ComplianceStatus" ADD VALUE IF NOT EXISTS 'PAID';
  EXCEPTION WHEN duplicate_object THEN null; END $$;

ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "createdById" TEXT;
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "reviewerId" TEXT;
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "reviewerActionAt" TIMESTAMP(3);
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "reviewerComments" TEXT;
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "adminActionAt" TIMESTAMP(3);
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "adminComments" TEXT;
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "paidAt" TIMESTAMP(3);
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "paymentDate" TIMESTAMP(3);
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "paymentAmount" DECIMAL(18,2);
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "paymentReference" TEXT;
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "paymentMethod" TEXT;
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "refundAmount" DECIMAL(18,2);
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "refundReference" TEXT;
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "paymentNotes" TEXT;

-- Attachments: track the workflow stage at which the file was uploaded
ALTER TABLE "attachments" ADD COLUMN IF NOT EXISTS "stage" TEXT;

-- Foreign keys for reviewer/creator
DO $$ BEGIN
  ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_createdById_fkey" FOREIGN KEY ("createdById") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;
  EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_reviewerId_fkey" FOREIGN KEY ("reviewerId") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;
  EXCEPTION WHEN duplicate_object THEN null; END $$;

-- Group returns: a compliance schedule can span multiple entities
-- entityId becomes the primary (first) entity for backward compatibility
ALTER TABLE "compliance_schedules" ALTER COLUMN "entityId" DROP NOT NULL;

CREATE TABLE IF NOT EXISTS "compliance_entities" (
    "id" TEXT NOT NULL,
    "complianceId" TEXT NOT NULL,
    "entityId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "compliance_entities_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "compliance_entities_complianceId_entityId_key" ON "compliance_entities"("complianceId", "entityId");
CREATE INDEX IF NOT EXISTS "compliance_entities_entityId_idx" ON "compliance_entities"("entityId");

DO $$ BEGIN
  ALTER TABLE "compliance_entities" ADD CONSTRAINT "compliance_entities_complianceId_fkey" FOREIGN KEY ("complianceId") REFERENCES "compliance_schedules"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN
  ALTER TABLE "compliance_entities" ADD CONSTRAINT "compliance_entities_entityId_fkey" FOREIGN KEY ("entityId") REFERENCES "legal_entities"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
  EXCEPTION WHEN duplicate_object THEN null; END $$;

-- Compliance types: only name is required; taxType/frequency/country are optional
ALTER TABLE "compliance_types" ALTER COLUMN "taxType" DROP NOT NULL;
ALTER TABLE "compliance_types" ALTER COLUMN "frequency" DROP NOT NULL;
ALTER TABLE "compliance_types" ALTER COLUMN "countryId" DROP NOT NULL;

-- Currencies: separate master, decoupled from countries
CREATE TABLE IF NOT EXISTS "currencies" (
    "id" TEXT NOT NULL,
    "orgId" TEXT,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "symbol" TEXT,
    "decimals" INTEGER NOT NULL DEFAULT 2,
    "isBase" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "currencies_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "currencies_orgId_code_key" ON "currencies"("orgId", "code");
DO $$ BEGIN
  ALTER TABLE "currencies" ADD CONSTRAINT "currencies_orgId_fkey" FOREIGN KEY ("orgId") REFERENCES "organizations"("id") ON DELETE CASCADE ON UPDATE CASCADE;
  EXCEPTION WHEN duplicate_object THEN null; END $$;

-- Countries: remove time zone, working days, and embedded currency
ALTER TABLE "countries" DROP COLUMN IF EXISTS "timeZone";
ALTER TABLE "countries" DROP COLUMN IF EXISTS "workingDays";
ALTER TABLE "countries" DROP COLUMN IF EXISTS "currency";

-- Compliance schedules: use tax type instead of compliance type as the primary classification
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "taxType" "TaxType";
ALTER TABLE "compliance_schedules" ALTER COLUMN "complianceTypeId" DROP NOT NULL;

-- Multi-entity group filing: optional date after which recurring generation stops
ALTER TABLE "compliance_schedules" ADD COLUMN IF NOT EXISTS "recurringEndDate" TIMESTAMPTZ;

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
