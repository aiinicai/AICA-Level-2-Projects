-- TaxFlow - Full Database Schema + Seed Data
-- Run this in your Supabase SQL editor to restore the entire database

-- Drop existing tables (order matters for FK constraints)
DROP TABLE IF EXISTS "exchange_rates" CASCADE;
DROP TABLE IF EXISTS "activities" CASCADE;
DROP TABLE IF EXISTS "notifications" CASCADE;
DROP TABLE IF EXISTS "audit_trails" CASCADE;
DROP TABLE IF EXISTS "comments" CASCADE;
DROP TABLE IF EXISTS "attachments" CASCADE;
DROP TABLE IF EXISTS "compliance_approvals" CASCADE;
DROP TABLE IF EXISTS "compliance_assignments" CASCADE;
DROP TABLE IF EXISTS "compliance_entities" CASCADE;
DROP TABLE IF EXISTS "compliance_schedules" CASCADE;
DROP TABLE IF EXISTS "holidays" CASCADE;
DROP TABLE IF EXISTS "form_master" CASCADE;
DROP TABLE IF EXISTS "compliance_types" CASCADE;
DROP TABLE IF EXISTS "legal_entities" CASCADE;
DROP TABLE IF EXISTS "organization_members" CASCADE;
DROP TABLE IF EXISTS "organizations" CASCADE;
DROP TABLE IF EXISTS "users" CASCADE;
DROP TABLE IF EXISTS "countries" CASCADE;
DROP TABLE IF EXISTS "currencies" CASCADE;

DROP TYPE IF EXISTS "Role" CASCADE;
DROP TYPE IF EXISTS "ComplianceStatus" CASCADE;
DROP TYPE IF EXISTS "Priority" CASCADE;
DROP TYPE IF EXISTS "Frequency" CASCADE;
DROP TYPE IF EXISTS "TaxType" CASCADE;
DROP TYPE IF EXISTS "EntityStatus" CASCADE;

-- Enums
CREATE TYPE "Role" AS ENUM ('ADMINISTRATOR', 'MANAGER', 'PREPARER', 'APPROVER');
CREATE TYPE "ComplianceStatus" AS ENUM ('DRAFT','PENDING_ADMIN_APPROVAL','PENDING_REVIEW','PENDING_PREPARATION','PREPARED','PENDING_APPROVAL','REVIEWED','APPROVED','REJECTED','FILED','PAID','CLOSED');
CREATE TYPE "Priority" AS ENUM ('NORMAL','HIGH','CRITICAL');
CREATE TYPE "Frequency" AS ENUM ('WEEKLY','MONTHLY','BI_MONTHLY','QUARTERLY','HALF_YEARLY','ANNUAL','AD_HOC');
CREATE TYPE "TaxType" AS ENUM ('GST','VAT','SALES_TAX','WHT','CORPORATE_TAX','STATUTORY');
CREATE TYPE "EntityStatus" AS ENUM ('ACTIVE','INACTIVE','SUSPENDED');

-- Countries (no FKs, insert first)
CREATE TABLE "countries" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "region" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "countries_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "countries_name_key" ON "countries"("name");
CREATE UNIQUE INDEX IF NOT EXISTS "countries_code_key" ON "countries"("code");

-- Currencies (separate master)
CREATE TABLE "currencies" (
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

-- Users (FK to country)
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "username" TEXT NOT NULL,
    "password" TEXT NOT NULL,
    "name" TEXT,
    "role" TEXT NOT NULL DEFAULT 'PREPARER',
    "roles" TEXT[] DEFAULT '{PREPARER}',
    "department" TEXT,
    "image" TEXT,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "employeeId" TEXT,
    "managerId" TEXT,
    "countryId" TEXT,
    "emailVerified" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "users_email_key" ON "users"("email");
CREATE UNIQUE INDEX IF NOT EXISTS "users_username_key" ON "users"("username");
CREATE UNIQUE INDEX IF NOT EXISTS "users_employeeId_key" ON "users"("employeeId");

-- Organizations
CREATE TABLE "organizations" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "createdById" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "organizations_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "organizations_slug_key" ON "organizations"("slug");

-- Organization members
CREATE TABLE "organization_members" (
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

-- Legal entities
CREATE TABLE "legal_entities" (
    "id" TEXT NOT NULL,
    "orgId" TEXT,
    "entityNumber" TEXT NOT NULL,
    "entityName" TEXT NOT NULL,
    "countryId" TEXT NOT NULL,
    "businessUnit" TEXT,
    "status" "EntityStatus" NOT NULL DEFAULT 'ACTIVE',
    "taxRegistrationNumber" TEXT,
    "currency" TEXT NOT NULL DEFAULT 'USD',
    "approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "legal_entities_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "legal_entities_orgId_entityNumber_key" ON "legal_entities"("orgId", "entityNumber");
ALTER TABLE "legal_entities" ADD CONSTRAINT "legal_entities_approvalFlow_check" CHECK ("approvalFlow" IN ('NONE', 'ONE_LEVEL', 'TWO_LEVEL'));

-- Compliance types
CREATE TABLE "compliance_types" (
    "id" TEXT NOT NULL,
    "orgId" TEXT,
    "name" TEXT NOT NULL,
    "taxType" "TaxType",
    "frequency" "Frequency",
    "dueDateRule" TEXT,
    "description" TEXT,
    "defaultPreparationDays" INTEGER NOT NULL DEFAULT 5,
    "defaultApprovalDays" INTEGER NOT NULL DEFAULT 3,
    "countryId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "compliance_types_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "compliance_types_orgId_name_key" ON "compliance_types"("orgId", "name");

-- Form master
CREATE TABLE "form_master" (
    "id" TEXT NOT NULL,
    "orgId" TEXT,
    "formNumber" TEXT NOT NULL,
    "formName" TEXT NOT NULL,
    "complianceTypeId" TEXT,
    "countryId" TEXT,
    "taxType" "TaxType",
    "description" TEXT,
    "requiresPayment" BOOLEAN NOT NULL DEFAULT true,
    "approvalFlow" TEXT NOT NULL DEFAULT 'ONE_LEVEL',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "form_master_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "form_master_orgId_formNumber_countryId_key" ON "form_master"("orgId", "formNumber", "countryId");
ALTER TABLE "form_master" ADD CONSTRAINT "form_master_approvalFlow_check" CHECK ("approvalFlow" IN ('NONE', 'ONE_LEVEL', 'TWO_LEVEL'));

-- Form-countries junction (multi-country support)
CREATE TABLE IF NOT EXISTS "form_countries" (
    "id" TEXT NOT NULL,
    "formId" TEXT NOT NULL,
    "countryId" TEXT NOT NULL,
    CONSTRAINT "form_countries_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "form_countries_formId_idx" ON "form_countries"("formId");
CREATE INDEX IF NOT EXISTS "form_countries_countryId_idx" ON "form_countries"("countryId");

-- Compliance schedules
CREATE TABLE "compliance_schedules" (
    "id" TEXT NOT NULL,
    "orgId" TEXT,
    "complianceId" TEXT NOT NULL,
    "entityId" TEXT,
    "countryId" TEXT NOT NULL,
    "complianceTypeId" TEXT,
    "taxType" "TaxType",
    "formId" TEXT,
    "taxPeriod" TEXT NOT NULL,
    "taxPeriodStart" TIMESTAMP(3),
    "taxPeriodEnd" TIMESTAMP(3),
    "filingMonth" TEXT,
    "frequency" "Frequency" NOT NULL,
    "dueDate" TIMESTAMP(3) NOT NULL,
    "priority" "Priority" NOT NULL DEFAULT 'NORMAL',
    "status" "ComplianceStatus" NOT NULL DEFAULT 'DRAFT',
    "isRecurring" BOOLEAN NOT NULL DEFAULT true,
    "recurringEndDate" TIMESTAMPTZ,
    "notes" TEXT,
    "submittedAt" TIMESTAMP(3),
    "filedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "createdById" TEXT,
    "reviewerId" TEXT,
    "reviewerActionAt" TIMESTAMP(3),
    "reviewerComments" TEXT,
    "adminActionAt" TIMESTAMP(3),
    "adminComments" TEXT,
    "paidAt" TIMESTAMP(3),
    "paymentDate" TIMESTAMP(3),
    "paymentDueDate" TIMESTAMPTZ,
    "paymentAmount" DECIMAL(18,2),
    "paymentReference" TEXT,
    "paymentMethod" TEXT,
    "refundAmount" DECIMAL(18,2),
    "refundReference" TEXT,
    "paymentNotes" TEXT,
    "filingType" TEXT NOT NULL DEFAULT 'PAYMENT',
    "refundType" TEXT,
    "paymentCurrency" TEXT,
    "requiresPayment" BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT "compliance_schedules_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "compliance_schedules_complianceId_key" ON "compliance_schedules"("complianceId");

-- Who/when each actor reconfirmed the payment amount:
--   PREPARER_SUBMIT  - preparer entered the amount when submitting for approval.
--   REVIEWER         - reviewer reconfirmed the amount before approving (step 1).
--   APPROVER         - approver reconfirmed the amount before approving (step 2).
--   PREPARER_PAYMENT - preparer confirmed the same amount was actually paid.
CREATE TABLE "compliance_payment_confirmations" (
    "id" TEXT NOT NULL,
    "complianceId" TEXT NOT NULL,
    "stage" TEXT NOT NULL,
    "confirmedById" TEXT NOT NULL,
    "confirmedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "compliance_payment_confirmations_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "compliance_payment_confirmations_complianceId_stage_key" UNIQUE ("complianceId", "stage")
);
CREATE INDEX IF NOT EXISTS "compliance_payment_confirmations_complianceId_idx" ON "compliance_payment_confirmations"("complianceId");

-- Compliance schedule <-> entity join (group returns)
CREATE TABLE "compliance_entities" (
    "id" TEXT NOT NULL,
    "complianceId" TEXT NOT NULL,
    "entityId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "compliance_entities_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "compliance_entities_complianceId_entityId_key" ON "compliance_entities"("complianceId", "entityId");
CREATE INDEX IF NOT EXISTS "compliance_entities_entityId_idx" ON "compliance_entities"("entityId");

-- Compliance assignments
CREATE TABLE "compliance_assignments" (
    "id" TEXT NOT NULL,
    "complianceId" TEXT NOT NULL,
    "preparerId" TEXT NOT NULL,
    "startedAt" TIMESTAMP(3),
    "completedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "compliance_assignments_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "compliance_assignments_complianceId_preparerId_key" ON "compliance_assignments"("complianceId", "preparerId");

-- Compliance approvals
CREATE TABLE "compliance_approvals" (
    "id" TEXT NOT NULL,
    "complianceId" TEXT NOT NULL,
    "approverId" TEXT NOT NULL,
    "status" "ComplianceStatus" NOT NULL DEFAULT 'PENDING_APPROVAL',
    "comments" TEXT,
    "actionAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "compliance_approvals_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "compliance_approvals_complianceId_approverId_key" ON "compliance_approvals"("complianceId", "approverId");

-- Template change requests: non-admin edits to approved templates await admin approval
CREATE TABLE "template_change_requests" (
    "id" TEXT NOT NULL,
    "templateId" TEXT NOT NULL,
    "orgId" TEXT NOT NULL,
    "requestedById" TEXT NOT NULL,
    "snapshot" JSONB NOT NULL,
    "fieldDiffs" JSONB,
    "changeReason" TEXT,
    "status" TEXT NOT NULL DEFAULT 'PENDING',
    "reviewedById" TEXT,
    "reviewedAt" TIMESTAMP(3),
    "reviewComments" TEXT,
    "requestedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "template_change_requests_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "template_change_requests_templateId_fkey" FOREIGN KEY ("templateId") REFERENCES "compliance_templates"("id") ON DELETE CASCADE,
    CONSTRAINT "template_change_requests_orgId_fkey" FOREIGN KEY ("orgId") REFERENCES "organizations"("id"),
    CONSTRAINT "template_change_requests_requestedById_fkey" FOREIGN KEY ("requestedById") REFERENCES "users"("id"),
    CONSTRAINT "template_change_requests_reviewedById_fkey" FOREIGN KEY ("reviewedById") REFERENCES "users"("id")
);
CREATE INDEX IF NOT EXISTS "idx_change_requests_template" ON "template_change_requests"("templateId");
CREATE INDEX IF NOT EXISTS "idx_change_requests_status" ON "template_change_requests"("status");

-- Attachments
CREATE TABLE "attachments" (
    "id" TEXT NOT NULL,
    "complianceId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "fileName" TEXT NOT NULL,
    "originalName" TEXT NOT NULL,
    "fileType" TEXT NOT NULL,
    "fileSize" INTEGER NOT NULL,
    "filePath" TEXT NOT NULL,
    "version" INTEGER NOT NULL DEFAULT 1,
    "stage" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "attachments_pkey" PRIMARY KEY ("id")
);

-- Comments
CREATE TABLE "comments" (
    "id" TEXT NOT NULL,
    "complianceId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "comments_pkey" PRIMARY KEY ("id")
);

-- Audit trails
CREATE TABLE "audit_trails" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "entity" TEXT,
    "entityId" TEXT,
    "oldValue" TEXT,
    "newValue" TEXT,
    "ipAddress" TEXT,
    "comments" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "audit_trails_pkey" PRIMARY KEY ("id")
);

-- Notifications
CREATE TABLE "notifications" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "message" TEXT NOT NULL,
    "type" TEXT NOT NULL DEFAULT 'INFO',
    "read" BOOLEAN NOT NULL DEFAULT false,
    "link" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "notifications_pkey" PRIMARY KEY ("id")
);

-- Holidays
CREATE TABLE "holidays" (
    "id" TEXT NOT NULL,
    "countryId" TEXT NOT NULL,
    "date" TIMESTAMP(3) NOT NULL,
    "name" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "holidays_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "holidays_countryId_date_key" ON "holidays"("countryId", "date");

-- Exchange rates
CREATE TABLE "exchange_rates" (
    "id" TEXT NOT NULL,
    "fromCurrency" TEXT NOT NULL,
    "toCurrency" TEXT NOT NULL DEFAULT 'USD',
    "rate" DECIMAL(18,6) NOT NULL,
    "date" DATE NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "exchange_rates_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "exchange_rates_fromCurrency_date_key" ON "exchange_rates"("fromCurrency", "date");

-- Activities
CREATE TABLE "activities" (
    "id" TEXT NOT NULL,
    "complianceId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "fromStatus" "ComplianceStatus",
    "toStatus" "ComplianceStatus",
    "comments" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "activities_pkey" PRIMARY KEY ("id")
);

-- Foreign keys
ALTER TABLE "users" ADD CONSTRAINT "users_countryId_fkey" FOREIGN KEY ("countryId") REFERENCES "countries"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "currencies" ADD CONSTRAINT "currencies_orgId_fkey" FOREIGN KEY ("orgId") REFERENCES "organizations"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "users" ADD CONSTRAINT "users_managerId_fkey" FOREIGN KEY ("managerId") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE "organizations" ADD CONSTRAINT "organizations_createdById_fkey" FOREIGN KEY ("createdById") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "organization_members" ADD CONSTRAINT "organization_members_orgId_fkey" FOREIGN KEY ("orgId") REFERENCES "organizations"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "organization_members" ADD CONSTRAINT "organization_members_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "organization_members" ADD CONSTRAINT "organization_members_createdById_fkey" FOREIGN KEY ("createdById") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE "legal_entities" ADD CONSTRAINT "legal_entities_orgId_fkey" FOREIGN KEY ("orgId") REFERENCES "organizations"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "legal_entities" ADD CONSTRAINT "legal_entities_countryId_fkey" FOREIGN KEY ("countryId") REFERENCES "countries"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "compliance_types" ADD CONSTRAINT "compliance_types_orgId_fkey" FOREIGN KEY ("orgId") REFERENCES "organizations"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "compliance_types" ADD CONSTRAINT "compliance_types_countryId_fkey" FOREIGN KEY ("countryId") REFERENCES "countries"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "form_master" ADD CONSTRAINT "form_master_orgId_fkey" FOREIGN KEY ("orgId") REFERENCES "organizations"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "form_master" ADD CONSTRAINT "form_master_complianceTypeId_fkey" FOREIGN KEY ("complianceTypeId") REFERENCES "compliance_types"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "form_master" ADD CONSTRAINT "form_master_countryId_fkey" FOREIGN KEY ("countryId") REFERENCES "countries"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "form_countries" ADD CONSTRAINT "form_countries_formId_fkey" FOREIGN KEY ("formId") REFERENCES "form_master"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "form_countries" ADD CONSTRAINT "form_countries_countryId_fkey" FOREIGN KEY ("countryId") REFERENCES "countries"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_orgId_fkey" FOREIGN KEY ("orgId") REFERENCES "organizations"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_entityId_fkey" FOREIGN KEY ("entityId") REFERENCES "legal_entities"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_countryId_fkey" FOREIGN KEY ("countryId") REFERENCES "countries"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_complianceTypeId_fkey" FOREIGN KEY ("complianceTypeId") REFERENCES "compliance_types"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_formId_fkey" FOREIGN KEY ("formId") REFERENCES "form_master"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_createdById_fkey" FOREIGN KEY ("createdById") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "compliance_schedules" ADD CONSTRAINT "compliance_schedules_reviewerId_fkey" FOREIGN KEY ("reviewerId") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE "compliance_assignments" ADD CONSTRAINT "compliance_assignments_complianceId_fkey" FOREIGN KEY ("complianceId") REFERENCES "compliance_schedules"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "compliance_assignments" ADD CONSTRAINT "compliance_assignments_preparerId_fkey" FOREIGN KEY ("preparerId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "compliance_entities" ADD CONSTRAINT "compliance_entities_complianceId_fkey" FOREIGN KEY ("complianceId") REFERENCES "compliance_schedules"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "compliance_entities" ADD CONSTRAINT "compliance_entities_entityId_fkey" FOREIGN KEY ("entityId") REFERENCES "legal_entities"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "compliance_approvals" ADD CONSTRAINT "compliance_approvals_complianceId_fkey" FOREIGN KEY ("complianceId") REFERENCES "compliance_schedules"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "compliance_approvals" ADD CONSTRAINT "compliance_approvals_approverId_fkey" FOREIGN KEY ("approverId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "attachments" ADD CONSTRAINT "attachments_complianceId_fkey" FOREIGN KEY ("complianceId") REFERENCES "compliance_schedules"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "attachments" ADD CONSTRAINT "attachments_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "comments" ADD CONSTRAINT "comments_complianceId_fkey" FOREIGN KEY ("complianceId") REFERENCES "compliance_schedules"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "comments" ADD CONSTRAINT "comments_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "audit_trails" ADD CONSTRAINT "audit_trails_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "notifications" ADD CONSTRAINT "notifications_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "holidays" ADD CONSTRAINT "holidays_countryId_fkey" FOREIGN KEY ("countryId") REFERENCES "countries"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "activities" ADD CONSTRAINT "activities_complianceId_fkey" FOREIGN KEY ("complianceId") REFERENCES "compliance_schedules"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "activities" ADD CONSTRAINT "activities_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- =============================
-- SEED DATA
-- =============================

-- Countries
INSERT INTO "countries" ("id", "name", "code", "region", "timeZone", "workingDays", "currency", "createdAt", "updatedAt") VALUES
('c001', 'United States', 'US', 'North America', 'America/New_York', 5, 'USD', NOW(), NOW()),
('c002', 'Canada', 'CA', 'North America', 'America/Toronto', 5, 'CAD', NOW(), NOW()),
('c003', 'United Kingdom', 'GB', 'Europe', 'Europe/London', 5, 'GBP', NOW(), NOW()),
('c004', 'Germany', 'DE', 'Europe', 'Europe/Berlin', 5, 'EUR', NOW(), NOW()),
('c005', 'France', 'FR', 'Europe', 'Europe/Paris', 5, 'EUR', NOW(), NOW()),
('c006', 'Australia', 'AU', 'Oceania', 'Australia/Sydney', 5, 'AUD', NOW(), NOW()),
('c007', 'India', 'IN', 'Asia', 'Asia/Kolkata', 6, 'INR', NOW(), NOW()),
('c008', 'Singapore', 'SG', 'Asia', 'Asia/Singapore', 5, 'SGD', NOW(), NOW()),
('c009', 'United Arab Emirates', 'AE', 'Middle East', 'Asia/Dubai', 5, 'AED', NOW(), NOW()),
('c010', 'Brazil', 'BR', 'South America', 'America/Sao_Paulo', 5, 'BRL', NOW(), NOW());

-- Users (passwords: password123 / admin / admin123 via bcrypt)
INSERT INTO "users" ("id", "email", "username", "password", "name", "role", "roles", "department", "employeeId", "isActive", "countryId", "createdAt", "updatedAt") VALUES
('u001', 'admin@taxflow.com', 'admin', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Admin User', 'ADMINISTRATOR', '{ADMINISTRATOR}', 'Administration', 'EMP-001', true, 'c001', NOW(), NOW()),
('u002', 'superadmin@taxflow.com', 'superadmin', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Super Admin', 'ADMINISTRATOR', '{ADMINISTRATOR}', 'Administration', 'EMP-002', true, 'c001', NOW(), NOW()),
('u003', 'manager1@taxflow.com', 'manager1', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Alice Johnson', 'MANAGER', '{MANAGER}', 'Tax', 'EMP-003', true, 'c001', NOW(), NOW()),
('u004', 'manager2@taxflow.com', 'manager2', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Bob Williams', 'MANAGER', '{MANAGER}', 'Finance', 'EMP-004', true, 'c003', NOW(), NOW()),
('u005', 'manager3@taxflow.com', 'manager3', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Carol Davis', 'MANAGER', '{MANAGER}', 'Accounting', 'EMP-005', true, 'c008', NOW(), NOW()),
('u006', 'preparer1@taxflow.com', 'preparer1', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'David Brown', 'PREPARER', '{PREPARER}', 'Tax', 'EMP-006', true, 'c001', NOW(), NOW()),
('u007', 'preparer2@taxflow.com', 'preparer2', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Eva Martinez', 'PREPARER', '{PREPARER}', 'Tax', 'EMP-007', true, 'c002', NOW(), NOW()),
('u008', 'preparer3@taxflow.com', 'preparer3', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Frank Lee', 'PREPARER', '{PREPARER}', 'Finance', 'EMP-008', true, 'c004', NOW(), NOW()),
('u009', 'preparer4@taxflow.com', 'preparer4', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Grace Kim', 'PREPARER', '{PREPARER}', 'Accounting', 'EMP-009', true, 'c007', NOW(), NOW()),
('u010', 'preparer5@taxflow.com', 'preparer5', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Henry Chen', 'PREPARER', '{PREPARER}', 'Tax', 'EMP-010', true, 'c006', NOW(), NOW()),
('u011', 'approver1@taxflow.com', 'approver1', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Irene Patel', 'APPROVER', '{APPROVER}', 'Tax', 'EMP-011', true, 'c001', NOW(), NOW()),
('u012', 'approver2@taxflow.com', 'approver2', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Jack Thompson', 'APPROVER', '{APPROVER}', 'Finance', 'EMP-012', true, 'c003', NOW(), NOW()),
('u013', 'approver3@taxflow.com', 'approver3', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Katherine White', 'APPROVER', '{APPROVER}', 'Legal', 'EMP-013', true, 'c005', NOW(), NOW()),
('u014', 'approver4@taxflow.com', 'approver4', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Liam O''Brien', 'APPROVER', '{APPROVER}', 'Accounting', 'EMP-014', true, 'c009', NOW(), NOW()),
('u015', 'approver5@taxflow.com', 'approver5', '$2a$10$rS5P5E5E5E5E5E5E5E5E5O5E5E5E5E5E5E5E5E5E5E5E5E5E5', 'Mia Garcia', 'APPROVER', '{APPROVER}', 'Tax', 'EMP-015', true, 'c010', NOW(), NOW());

-- Set manager relationships
UPDATE "users" SET "managerId" = 'u003' WHERE "id" IN ('u006', 'u007', 'u010', 'u011', 'u013', 'u015');
UPDATE "users" SET "managerId" = 'u004' WHERE "id" IN ('u008', 'u012');
UPDATE "users" SET "managerId" = 'u005' WHERE "id" IN ('u009', 'u014');

-- Organization
INSERT INTO "organizations" ("id", "name", "slug", "createdById", "createdAt", "updatedAt") VALUES
('org001', 'TaxFlow Inc', 'taxflow', 'u001', NOW(), NOW());

-- Organization members
INSERT INTO "organization_members" ("id", "orgId", "userId", "roles", "createdById", "createdAt", "updatedAt") VALUES
('om001', 'org001', 'u001', '{ADMINISTRATOR}', 'u001', NOW(), NOW()),
('om002', 'org001', 'u002', '{ADMINISTRATOR}', 'u001', NOW(), NOW()),
('om003', 'org001', 'u003', '{MANAGER}', 'u001', NOW(), NOW()),
('om004', 'org001', 'u004', '{MANAGER}', 'u001', NOW(), NOW()),
('om005', 'org001', 'u005', '{MANAGER}', 'u001', NOW(), NOW()),
('om006', 'org001', 'u006', '{PREPARER}', 'u001', NOW(), NOW()),
('om007', 'org001', 'u007', '{PREPARER}', 'u001', NOW(), NOW()),
('om008', 'org001', 'u008', '{PREPARER}', 'u001', NOW(), NOW()),
('om009', 'org001', 'u009', '{PREPARER}', 'u001', NOW(), NOW()),
('om010', 'org001', 'u010', '{PREPARER}', 'u001', NOW(), NOW()),
('om011', 'org001', 'u011', '{APPROVER}', 'u001', NOW(), NOW()),
('om012', 'org001', 'u012', '{APPROVER}', 'u001', NOW(), NOW()),
('om013', 'org001', 'u013', '{APPROVER}', 'u001', NOW(), NOW()),
('om014', 'org001', 'u014', '{APPROVER}', 'u001', NOW(), NOW()),
('om015', 'org001', 'u015', '{APPROVER}', 'u001', NOW(), NOW());

-- Legal entities
INSERT INTO "legal_entities" ("id", "orgId", "entityNumber", "entityName", "countryId", "businessUnit", "status", "taxRegistrationNumber", "currency", "createdAt", "updatedAt") VALUES
('le001', 'org001', 'ENT-001', 'Acme Corp US', 'c001', 'Headquarters', 'ACTIVE', 'TX-US-001', 'USD', NOW(), NOW()),
('le002', 'org001', 'ENT-002', 'Acme Corp Canada', 'c002', 'North America', 'ACTIVE', 'TX-CA-001', 'CAD', NOW(), NOW()),
('le003', 'org001', 'ENT-003', 'TechSolutions GmbH', 'c004', 'Europe', 'ACTIVE', 'TX-DE-001', 'EUR', NOW(), NOW()),
('le004', 'org001', 'ENT-004', 'TechSolutions France SAS', 'c005', 'Europe', 'ACTIVE', 'TX-FR-001', 'EUR', NOW(), NOW()),
('le005', 'org001', 'ENT-005', 'GlobalTrade UK Ltd', 'c003', 'Europe', 'ACTIVE', 'TX-GB-001', 'GBP', NOW(), NOW()),
('le006', 'org001', 'ENT-006', 'DownUnder Operations Pty', 'c006', 'APAC', 'ACTIVE', 'TX-AU-001', 'AUD', NOW(), NOW()),
('le007', 'org001', 'ENT-007', 'India Operations Pvt Ltd', 'c007', 'APAC', 'ACTIVE', 'TX-IN-001', 'INR', NOW(), NOW()),
('le008', 'org001', 'ENT-008', 'Singapore Hub Pte Ltd', 'c008', 'APAC', 'ACTIVE', 'TX-SG-001', 'SGD', NOW(), NOW()),
('le009', 'org001', 'ENT-009', 'Middle East FZE', 'c009', 'Middle East', 'ACTIVE', 'TX-AE-001', 'AED', NOW(), NOW()),
('le010', 'org001', 'ENT-010', 'Brazil Subsidiary Ltda', 'c010', 'South America', 'ACTIVE', 'TX-BR-001', 'BRL', NOW(), NOW()),
('le011', 'org001', 'ENT-011', 'Acme Corp Europe BV', 'c004', 'Europe', 'ACTIVE', 'TX-DE-002', 'EUR', NOW(), NOW()),
('le012', 'org001', 'ENT-012', 'TechSolutions UK Ltd', 'c003', 'Europe', 'ACTIVE', 'TX-GB-002', 'GBP', NOW(), NOW()),
('le013', 'org001', 'ENT-013', 'GlobalTrade Australia', 'c006', 'APAC', 'INACTIVE', 'TX-AU-002', 'AUD', NOW(), NOW()),
('le014', 'org001', 'ENT-014', 'InnovateTech India', 'c007', 'APAC', 'ACTIVE', 'TX-IN-002', 'INR', NOW(), NOW()),
('le015', 'org001', 'ENT-015', 'Desert Innovations DMCC', 'c009', 'Middle East', 'SUSPENDED', 'TX-AE-002', 'AED', NOW(), NOW()),
('le016', 'org001', 'ENT-016', 'SambaTech Brazil', 'c010', 'South America', 'ACTIVE', 'TX-BR-002', 'BRL', NOW(), NOW()),
('le017', 'org001', 'ENT-017', 'Maple Leaf Corp', 'c002', 'North America', 'ACTIVE', 'TX-CA-002', 'CAD', NOW(), NOW()),
('le018', 'org001', 'ENT-018', 'Liberté Enterprises', 'c005', 'Europe', 'ACTIVE', 'TX-FR-002', 'EUR', NOW(), NOW()),
('le019', 'org001', 'ENT-019', 'Lion City Holdings', 'c008', 'APAC', 'ACTIVE', 'TX-SG-002', 'SGD', NOW(), NOW()),
('le020', 'org001', 'ENT-020', 'Acme Corp APAC', 'c008', 'APAC', 'ACTIVE', 'TX-SG-003', 'SGD', NOW(), NOW());

-- Compliance types
INSERT INTO "compliance_types" ("id", "orgId", "name", "taxType", "frequency", "dueDateRule", "description", "defaultPreparationDays", "defaultApprovalDays", "countryId", "createdAt", "updatedAt") VALUES
('ct001', 'org001', 'GST Return Monthly', 'GST', 'MONTHLY', '20th of following month', 'Monthly GST return filing', 10, 5, 'c007', NOW(), NOW()),
('ct002', 'org001', 'VAT Return Quarterly', 'VAT', 'QUARTERLY', 'Last day of month following quarter', 'Quarterly VAT return', 15, 5, 'c003', NOW(), NOW()),
('ct003', 'org001', 'Sales Tax Monthly', 'SALES_TAX', 'MONTHLY', '20th of following month', 'Monthly sales tax filing', 10, 3, 'c001', NOW(), NOW()),
('ct004', 'org001', 'WHT Monthly', 'WHT', 'MONTHLY', '15th of following month', 'Monthly withholding tax', 8, 3, 'c008', NOW(), NOW()),
('ct005', 'org001', 'Corporate Tax Annual', 'CORPORATE_TAX', 'ANNUAL', '30th June following year', 'Annual corporate tax return', 60, 20, 'c004', NOW(), NOW()),
('ct006', 'org001', 'VAT Return Monthly', 'VAT', 'MONTHLY', '25th of following month', 'Monthly VAT return filing (Germany)', 10, 5, 'c004', NOW(), NOW()),
('ct007', 'org001', 'GST Return Quarterly', 'GST', 'QUARTERLY', '28th of month following quarter', 'Quarterly GST return', 15, 5, 'c006', NOW(), NOW()),
('ct008', 'org001', 'Statutory Filing Annual', 'STATUTORY', 'ANNUAL', '31st December', 'Annual statutory filing', 45, 15, 'c009', NOW(), NOW()),
('ct009', 'org001', 'Sales Tax Quarterly', 'SALES_TAX', 'QUARTERLY', 'Last day of month following quarter', 'Quarterly sales tax filing', 15, 5, 'c002', NOW(), NOW()),
('ct010', 'org001', 'WHT Quarterly', 'WHT', 'QUARTERLY', 'End of month following quarter', 'Quarterly withholding tax', 12, 5, 'c005', NOW(), NOW());

-- Forms
INSERT INTO "form_master" ("id", "orgId", "formNumber", "formName", "complianceTypeId", "countryId", "description", "createdAt", "updatedAt") VALUES
('f001', 'org001', 'GSTR-1', 'GSTR-1 Monthly Return', 'ct001', 'c007', 'Outward supply details', NOW(), NOW()),
('f002', 'org001', 'GSTR-3B', 'GSTR-3B Monthly Summary', 'ct001', 'c007', 'Monthly summary return', NOW(), NOW()),
('f003', 'org001', 'VAT-100', 'VAT Return (Quarterly)', 'ct002', 'c003', 'Quarterly VAT return form', NOW(), NOW()),
('f004', 'org001', 'ST-3', 'Sales Tax Monthly Return', 'ct003', 'c001', 'Monthly sales tax form', NOW(), NOW()),
('f005', 'org001', 'WHT-M01', 'WHT Monthly Statement', 'ct004', 'c008', 'Monthly WHT statement', NOW(), NOW()),
('f006', 'org001', 'CT-600', 'Corporate Tax Return', 'ct005', 'c004', 'Annual corporate tax return form', NOW(), NOW()),
('f007', 'org001', 'USt-VA', 'Voranmeldung', 'ct006', 'c004', 'Monthly VAT pre-registration', NOW(), NOW()),
('f008', 'org001', 'GST-Q01', 'BAS Quarterly', 'ct007', 'c006', 'Business activity statement', NOW(), NOW()),
('f009', 'org001', 'SF-01', 'Statutory Filing Form', 'ct008', 'c009', 'Annual statutory form', NOW(), NOW()),
('f010', 'org001', 'ST-Q01', 'Sales Tax Quarterly Return', 'ct009', 'c002', 'Quarterly sales tax return', NOW(), NOW()),
('f011', 'org001', 'WHT-Q01', 'WHT Quarterly Statement', 'ct010', 'c005', 'Quarterly WHT statement', NOW(), NOW()),
('f012', 'org001', 'VAT-200', 'VAT Return (Monthly DE)', 'ct006', 'c004', 'Monthly VAT return', NOW(), NOW());

-- Compliance schedules
INSERT INTO "compliance_schedules" ("id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "taxPeriod", "frequency", "dueDate", "priority", "status", "isRecurring", "notes", "submittedAt", "filedAt", "createdAt", "updatedAt") VALUES
('cs001', 'org001', 'TAX-00001', 'le001', 'c001', 'ct003', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '19 days', 'NORMAL', 'FILED', true, 'Filed on time', NOW() - INTERVAL '8 days', NOW() - INTERVAL '7 days', NOW(), NOW()),
('cs002', 'org001', 'TAX-00002', 'le002', 'c002', 'ct002', 'Q' || (EXTRACT(quarter FROM NOW())::int) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW() + INTERVAL '1 month'), 'HIGH', 'APPROVED', true, 'Approved by manager', NOW() - INTERVAL '16 days', NULL, NOW(), NOW()),
('cs003', 'org001', 'TAX-00003', 'le003', 'c004', 'ct005', 'FY ' || (EXTRACT(year FROM NOW()) - 1) || '-' || EXTRACT(year FROM NOW()), 'ANNUAL', DATE_TRUNC('year', NOW()) + INTERVAL '5 months 29 days', 'CRITICAL', 'PENDING_PREPARATION', true, 'Requires Q4 financial statements', NULL, NULL, NOW(), NOW()),
('cs004', 'org001', 'TAX-00004', 'le004', 'c005', 'ct006', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '24 days', 'NORMAL', 'PENDING_APPROVAL', true, 'Ready for review', NOW() - INTERVAL '4 days', NULL, NOW(), NOW()),
('cs005', 'org001', 'TAX-00005', 'le005', 'c003', 'ct001', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '19 days', 'HIGH', 'PREPARED', true, 'Draft prepared', NULL, NULL, NOW(), NOW()),
('cs006', 'org001', 'TAX-00006', 'le006', 'c006', 'ct007', 'Q' || (EXTRACT(quarter FROM NOW())::int) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW() + INTERVAL '3 months') - INTERVAL '2 days', 'NORMAL', 'DRAFT', true, 'Not started', NULL, NULL, NOW(), NOW()),
('cs007', 'org001', 'TAX-00007', 'le007', 'c007', 'ct001', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '19 days', 'CRITICAL', 'REJECTED', true, 'Rejected due to data discrepancies', NOW() - INTERVAL '11 days', NULL, NOW(), NOW()),
('cs008', 'org001', 'TAX-00008', 'le008', 'c008', 'ct004', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '14 days', 'NORMAL', 'FILED', true, 'Filed early', NOW() - INTERVAL '16 days', NOW() - INTERVAL '14 days', NOW(), NOW()),
('cs009', 'org001', 'TAX-00009', 'le009', 'c009', 'ct008', 'FY ' || (EXTRACT(year FROM NOW()) - 1) || '-' || EXTRACT(year FROM NOW()), 'ANNUAL', DATE_TRUNC('year', NOW()) + INTERVAL '11 months 30 days', 'HIGH', 'PENDING_PREPARATION', true, 'Annual audit required', NULL, NULL, NOW(), NOW()),
('cs010', 'org001', 'TAX-00010', 'le010', 'c010', 'ct010', 'Q' || (EXTRACT(quarter FROM NOW())::int) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW() + INTERVAL '2 months') - INTERVAL '1 day', 'NORMAL', 'DRAFT', true, 'Awaiting data', NULL, NULL, NOW(), NOW()),
('cs011', 'org001', 'TAX-00011', 'le001', 'c001', 'ct006', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '24 days', 'HIGH', 'PENDING_APPROVAL', true, 'Under review', NOW() - INTERVAL '5 days', NULL, NOW(), NOW()),
('cs012', 'org001', 'TAX-00012', 'le003', 'c004', 'ct006', TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW() - INTERVAL '1 month') + INTERVAL '24 days', 'NORMAL', 'FILED', true, 'Previous month', NOW() - INTERVAL '36 days', NOW() - INTERVAL '33 days', NOW(), NOW()),
('cs013', 'org001', 'TAX-00013', 'le005', 'c003', 'ct003', TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW() - INTERVAL '1 month') + INTERVAL '19 days', 'NORMAL', 'FILED', true, 'Filed last month', NOW() - INTERVAL '48 days', NOW() - INTERVAL '47 days', NOW(), NOW()),
('cs014', 'org001', 'TAX-00014', 'le007', 'c007', 'ct003', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '19 days', 'HIGH', 'PREPARED', true, 'Data ready for review', NULL, NULL, NOW(), NOW()),
('cs015', 'org001', 'TAX-00015', 'le011', 'c004', 'ct005', 'FY ' || (EXTRACT(year FROM NOW()) - 1) || '-' || EXTRACT(year FROM NOW()), 'ANNUAL', DATE_TRUNC('year', NOW()) + INTERVAL '5 months 29 days', 'CRITICAL', 'PENDING_APPROVAL', true, 'Awaiting approval from CFO', NOW() - INTERVAL '21 days', NULL, NOW(), NOW()),
('cs016', 'org001', 'TAX-00016', 'le012', 'c003', 'ct002', 'Q' || (EXTRACT(quarter FROM NOW())::int) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW() + INTERVAL '1 month'), 'NORMAL', 'DRAFT', true, 'Quarterly draft', NULL, NULL, NOW(), NOW()),
('cs017', 'org001', 'TAX-00017', 'le013', 'c006', 'ct002', 'Q' || GREATEST(EXTRACT(quarter FROM NOW())::int - 1, 1) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW() - INTERVAL '1 month'), 'NORMAL', 'APPROVED', true, 'Previous quarter approved', NOW() - INTERVAL '21 days', NULL, NOW(), NOW()),
('cs018', 'org001', 'TAX-00018', 'le014', 'c007', 'ct001', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '19 days', 'HIGH', 'PENDING_PREPARATION', true, 'Urgent preparation needed', NULL, NULL, NOW(), NOW()),
('cs019', 'org001', 'TAX-00019', 'le015', 'c009', 'ct004', TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW() - INTERVAL '1 month') + INTERVAL '14 days', 'NORMAL', 'CLOSED', true, 'Closed after review', NOW() - INTERVAL '50 days', NOW() - INTERVAL '46 days', NOW(), NOW()),
('cs020', 'org001', 'TAX-00020', 'le016', 'c010', 'ct009', 'Q' || (EXTRACT(quarter FROM NOW())::int) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW() + INTERVAL '2 months') - INTERVAL '1 day', 'NORMAL', 'DRAFT', true, 'New quarter', NULL, NULL, NOW(), NOW()),
('cs021', 'org001', 'TAX-00021', 'le017', 'c002', 'ct002', 'Q' || GREATEST(EXTRACT(quarter FROM NOW())::int - 1, 1) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW() - INTERVAL '1 month'), 'HIGH', 'APPROVED', true, 'Approved by regional manager', NOW() - INTERVAL '27 days', NULL, NOW(), NOW()),
('cs022', 'org001', 'TAX-00022', 'le018', 'c005', 'ct010', 'Q' || (EXTRACT(quarter FROM NOW())::int) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW() + INTERVAL '2 months') - INTERVAL '1 day', 'NORMAL', 'PENDING_PREPARATION', true, 'Data gathering in progress', NULL, NULL, NOW(), NOW()),
('cs023', 'org001', 'TAX-00023', 'le019', 'c008', 'ct004', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '14 days', 'HIGH', 'PENDING_APPROVAL', true, 'Expedite approval please', NOW() - INTERVAL '14 days', NULL, NOW(), NOW()),
('cs024', 'org001', 'TAX-00024', 'le020', 'c008', 'ct001', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '19 days', 'NORMAL', 'FILED', true, 'Filed ahead of deadline', NOW() - INTERVAL '10 days', NOW() - INTERVAL '8 days', NOW(), NOW()),
('cs025', 'org001', 'TAX-00025', 'le001', 'c001', 'ct004', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '14 days', 'HIGH', 'PREPARED', true, 'Ready for review', NULL, NULL, NOW(), NOW()),
('cs026', 'org001', 'TAX-00026', 'le004', 'c005', 'ct006', TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW() - INTERVAL '1 month') + INTERVAL '24 days', 'NORMAL', 'FILED', true, 'Filed last month', NOW() - INTERVAL '52 days', NOW() - INTERVAL '50 days', NOW(), NOW()),
('cs027', 'org001', 'TAX-00027', 'le006', 'c006', 'ct007', 'Q' || GREATEST(EXTRACT(quarter FROM NOW())::int - 1, 1) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW()) - INTERVAL '1 day', 'NORMAL', 'REJECTED', true, 'Rejected - incorrect amounts', NOW() - INTERVAL '40 days', NULL, NOW(), NOW()),
('cs028', 'org001', 'TAX-00028', 'le008', 'c008', 'ct003', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '19 days', 'NORMAL', 'DRAFT', true, 'Initial draft', NULL, NULL, NOW(), NOW()),
('cs029', 'org001', 'TAX-00029', 'le010', 'c010', 'ct008', 'FY ' || (EXTRACT(year FROM NOW()) - 1) || '-' || EXTRACT(year FROM NOW()), 'ANNUAL', DATE_TRUNC('year', NOW()) + INTERVAL '11 months 30 days', 'HIGH', 'DRAFT', true, 'With legal team', NULL, NULL, NOW(), NOW()),
('cs030', 'org001', 'TAX-00030', 'le011', 'c004', 'ct006', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '24 days', 'NORMAL', 'PENDING_PREPARATION', true, 'To be started', NULL, NULL, NOW(), NOW()),
('cs031', 'org001', 'TAX-00031', 'le012', 'c003', 'ct009', 'Q' || (EXTRACT(quarter FROM NOW())::int) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW() + INTERVAL '2 months') - INTERVAL '1 day', 'HIGH', 'PREPARED', true, 'Draft complete', NULL, NULL, NOW(), NOW()),
('cs032', 'org001', 'TAX-00032', 'le014', 'c007', 'ct005', 'FY ' || (EXTRACT(year FROM NOW()) - 1) || '-' || EXTRACT(year FROM NOW()), 'ANNUAL', DATE_TRUNC('year', NOW()) + INTERVAL '5 months 29 days', 'CRITICAL', 'PENDING_APPROVAL', true, 'CFO review pending', NOW() - INTERVAL '18 days', NULL, NOW(), NOW()),
('cs033', 'org001', 'TAX-00033', 'le015', 'c009', 'ct010', 'Q' || GREATEST(EXTRACT(quarter FROM NOW())::int - 1, 1) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW()) - INTERVAL '1 day', 'NORMAL', 'APPROVED', true, 'Approved last quarter', NOW() - INTERVAL '50 days', NULL, NOW(), NOW()),
('cs034', 'org001', 'TAX-00034', 'le017', 'c002', 'ct001', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '19 days', 'NORMAL', 'DRAFT', true, 'Monthly recurring', NULL, NULL, NOW(), NOW()),
('cs035', 'org001', 'TAX-00035', 'le019', 'c008', 'ct003', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '19 days', 'HIGH', 'PENDING_APPROVAL', true, 'Needs urgent sign off', NOW() - INTERVAL '9 days', NULL, NOW(), NOW()),
('cs036', 'org001', 'TAX-00036', 'le020', 'c008', 'ct004', TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW() - INTERVAL '1 month') + INTERVAL '14 days', 'NORMAL', 'FILED', true, 'Filed', NOW() - INTERVAL '48 days', NOW() - INTERVAL '46 days', NOW(), NOW()),
('cs037', 'org001', 'TAX-00037', 'le001', 'c001', 'ct001', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '19 days', 'CRITICAL', 'PREPARED', true, 'High priority filing', NULL, NULL, NOW(), NOW()),
('cs038', 'org001', 'TAX-00038', 'le003', 'c004', 'ct003', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '19 days', 'NORMAL', 'PENDING_PREPARATION', true, 'Preparation not started', NULL, NULL, NOW(), NOW()),
('cs039', 'org001', 'TAX-00039', 'le005', 'c003', 'ct001', TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW() - INTERVAL '1 month') + INTERVAL '19 days', 'NORMAL', 'FILED', true, 'Previous month', NOW() - INTERVAL '43 days', NOW() - INTERVAL '41 days', NOW(), NOW()),
('cs040', 'org001', 'TAX-00040', 'le007', 'c007', 'ct007', 'Q' || GREATEST(EXTRACT(quarter FROM NOW())::int - 1, 1) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW()) - INTERVAL '1 day', 'HIGH', 'CLOSED', true, 'Closed successfully', NOW() - INTERVAL '40 days', NOW() - INTERVAL '37 days', NOW(), NOW()),
('cs041', 'org001', 'TAX-00041', 'le009', 'c009', 'ct009', 'Q' || (EXTRACT(quarter FROM NOW())::int) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW() + INTERVAL '2 months') - INTERVAL '1 day', 'NORMAL', 'DRAFT', true, 'New quarter starting', NULL, NULL, NOW(), NOW()),
('cs042', 'org001', 'TAX-00042', 'le011', 'c004', 'ct002', 'Q' || (EXTRACT(quarter FROM NOW())::int) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW() + INTERVAL '1 month'), 'HIGH', 'PENDING_PREPARATION', true, 'Data collection in progress', NULL, NULL, NOW(), NOW()),
('cs043', 'org001', 'TAX-00043', 'le013', 'c006', 'ct005', 'FY ' || (EXTRACT(year FROM NOW()) - 1) || '-' || EXTRACT(year FROM NOW()), 'ANNUAL', DATE_TRUNC('year', NOW()) + INTERVAL '5 months 29 days', 'CRITICAL', 'REJECTED', true, 'Rejected need revised figures', NOW() - INTERVAL '23 days', NULL, NOW(), NOW()),
('cs044', 'org001', 'TAX-00044', 'le016', 'c010', 'ct001', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '19 days', 'NORMAL', 'PENDING_APPROVAL', true, 'Awaiting review', NOW() - INTERVAL '7 days', NULL, NOW(), NOW()),
('cs045', 'org001', 'TAX-00045', 'le018', 'c005', 'ct006', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '24 days', 'HIGH', 'PREPARED', true, 'Prepared awaiting approval', NULL, NULL, NOW(), NOW()),
('cs046', 'org001', 'TAX-00046', 'le002', 'c002', 'ct009', 'Q' || GREATEST(EXTRACT(quarter FROM NOW())::int - 1, 1) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW()) - INTERVAL '1 day', 'NORMAL', 'FILED', true, 'Filed on time', NOW() - INTERVAL '60 days', NOW() - INTERVAL '57 days', NOW(), NOW()),
('cs047', 'org001', 'TAX-00047', 'le004', 'c005', 'ct010', 'Q' || GREATEST(EXTRACT(quarter FROM NOW())::int - 1, 1) || ' ' || EXTRACT(year FROM NOW()), 'QUARTERLY', DATE_TRUNC('month', NOW()) - INTERVAL '1 day', 'NORMAL', 'APPROVED', true, 'Approved', NOW() - INTERVAL '43 days', NULL, NOW(), NOW()),
('cs048', 'org001', 'TAX-00048', 'le006', 'c006', 'ct004', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '14 days', 'NORMAL', 'DRAFT', true, 'Not yet started', NULL, NULL, NOW(), NOW()),
('cs049', 'org001', 'TAX-00049', 'le008', 'c008', 'ct006', TO_CHAR(NOW(), 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW()) + INTERVAL '24 days', 'NORMAL', 'DRAFT', true, 'Initial entry', NULL, NULL, NOW(), NOW()),
('cs050', 'org001', 'TAX-00050', 'le010', 'c010', 'ct001', TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM'), 'MONTHLY', DATE_TRUNC('month', NOW() - INTERVAL '1 month') + INTERVAL '19 days', 'HIGH', 'APPROVED', true, 'Approved last month', NOW() - INTERVAL '40 days', NULL, NOW(), NOW());

-- Compliance assignments
INSERT INTO "compliance_assignments" ("id", "complianceId", "preparerId", "startedAt", "completedAt", "createdAt", "updatedAt") VALUES
('ca001', 'cs001', 'u006', NOW() - INTERVAL '15 days', NOW() - INTERVAL '8 days', NOW(), NOW()),
('ca002', 'cs002', 'u007', NOW() - INTERVAL '20 days', NOW() - INTERVAL '16 days', NOW(), NOW()),
('ca003', 'cs003', 'u008', NOW() - INTERVAL '14 days', NULL, NOW(), NOW()),
('ca004', 'cs004', 'u009', NOW() - INTERVAL '10 days', NOW() - INTERVAL '4 days', NOW(), NOW()),
('ca005', 'cs005', 'u010', NOW() - INTERVAL '7 days', NULL, NOW(), NOW()),
('ca006', 'cs007', 'u006', NOW() - INTERVAL '18 days', NOW() - INTERVAL '11 days', NOW(), NOW()),
('ca007', 'cs008', 'u007', NOW() - INTERVAL '20 days', NOW() - INTERVAL '16 days', NOW(), NOW()),
('ca008', 'cs009', 'u008', NOW() - INTERVAL '10 days', NULL, NOW(), NOW()),
('ca009', 'cs011', 'u009', NOW() - INTERVAL '12 days', NOW() - INTERVAL '5 days', NOW(), NOW()),
('ca010', 'cs012', 'u010', NOW() - INTERVAL '40 days', NOW() - INTERVAL '36 days', NOW(), NOW()),
('ca011', 'cs013', 'u006', NOW() - INTERVAL '55 days', NOW() - INTERVAL '48 days', NOW(), NOW()),
('ca012', 'cs014', 'u007', NOW() - INTERVAL '5 days', NULL, NOW(), NOW()),
('ca013', 'cs015', 'u008', NOW() - INTERVAL '28 days', NOW() - INTERVAL '21 days', NOW(), NOW()),
('ca014', 'cs017', 'u009', NOW() - INTERVAL '28 days', NOW() - INTERVAL '21 days', NOW(), NOW()),
('ca015', 'cs018', 'u010', NOW() - INTERVAL '3 days', NULL, NOW(), NOW()),
('ca016', 'cs019', 'u006', NOW() - INTERVAL '55 days', NOW() - INTERVAL '50 days', NOW(), NOW()),
('ca017', 'cs021', 'u007', NOW() - INTERVAL '35 days', NOW() - INTERVAL '27 days', NOW(), NOW()),
('ca018', 'cs022', 'u008', NOW() - INTERVAL '7 days', NULL, NOW(), NOW()),
('ca019', 'cs023', 'u009', NOW() - INTERVAL '18 days', NOW() - INTERVAL '14 days', NOW(), NOW()),
('ca020', 'cs024', 'u010', NOW() - INTERVAL '15 days', NOW() - INTERVAL '10 days', NOW(), NOW()),
('ca021', 'cs025', 'u006', NOW() - INTERVAL '6 days', NULL, NOW(), NOW()),
('ca022', 'cs026', 'u007', NOW() - INTERVAL '58 days', NOW() - INTERVAL '52 days', NOW(), NOW()),
('ca023', 'cs027', 'u008', NOW() - INTERVAL '47 days', NOW() - INTERVAL '40 days', NOW(), NOW()),
('ca024', 'cs030', 'u009', NOW() - INTERVAL '2 days', NULL, NOW(), NOW()),
('ca025', 'cs031', 'u010', NOW() - INTERVAL '5 days', NULL, NOW(), NOW()),
('ca026', 'cs032', 'u006', NOW() - INTERVAL '25 days', NOW() - INTERVAL '18 days', NOW(), NOW()),
('ca027', 'cs033', 'u007', NOW() - INTERVAL '57 days', NOW() - INTERVAL '50 days', NOW(), NOW()),
('ca028', 'cs035', 'u008', NOW() - INTERVAL '14 days', NOW() - INTERVAL '9 days', NOW(), NOW()),
('ca029', 'cs036', 'u009', NOW() - INTERVAL '55 days', NOW() - INTERVAL '48 days', NOW(), NOW()),
('ca030', 'cs037', 'u010', NOW() - INTERVAL '4 days', NULL, NOW(), NOW()),
('ca031', 'cs038', 'u006', NOW() - INTERVAL '1 day', NULL, NOW(), NOW()),
('ca032', 'cs039', 'u007', NOW() - INTERVAL '50 days', NOW() - INTERVAL '43 days', NOW(), NOW()),
('ca033', 'cs040', 'u008', NOW() - INTERVAL '47 days', NOW() - INTERVAL '40 days', NOW(), NOW()),
('ca034', 'cs042', 'u009', NOW() - INTERVAL '6 days', NULL, NOW(), NOW()),
('ca035', 'cs043', 'u010', NOW() - INTERVAL '30 days', NOW() - INTERVAL '23 days', NOW(), NOW()),
('ca036', 'cs044', 'u006', NOW() - INTERVAL '12 days', NOW() - INTERVAL '7 days', NOW(), NOW()),
('ca037', 'cs045', 'u007', NOW() - INTERVAL '3 days', NULL, NOW(), NOW()),
('ca038', 'cs046', 'u008', NOW() - INTERVAL '67 days', NOW() - INTERVAL '60 days', NOW(), NOW()),
('ca039', 'cs047', 'u009', NOW() - INTERVAL '50 days', NOW() - INTERVAL '43 days', NOW(), NOW()),
('ca040', 'cs050', 'u010', NOW() - INTERVAL '47 days', NOW() - INTERVAL '40 days', NOW(), NOW());

-- Compliance approvals
INSERT INTO "compliance_approvals" ("id", "complianceId", "approverId", "status", "comments", "actionAt", "createdAt", "updatedAt") VALUES
('cap001', 'cs001', 'u011', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '9 days', NOW(), NOW()),
('cap002', 'cs002', 'u012', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '18 days', NOW(), NOW()),
('cap003', 'cs004', 'u013', 'PENDING_APPROVAL', NULL, NULL, NOW(), NOW()),
('cap004', 'cs007', 'u014', 'REJECTED', 'Please revise and resubmit with corrected figures', NOW() - INTERVAL '13 days', NOW(), NOW()),
('cap005', 'cs008', 'u015', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '17 days', NOW(), NOW()),
('cap006', 'cs011', 'u011', 'PENDING_APPROVAL', NULL, NULL, NOW(), NOW()),
('cap007', 'cs012', 'u012', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '37 days', NOW(), NOW()),
('cap008', 'cs013', 'u013', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '50 days', NOW(), NOW()),
('cap009', 'cs015', 'u014', 'PENDING_APPROVAL', NULL, NULL, NOW(), NOW()),
('cap010', 'cs017', 'u015', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '23 days', NOW(), NOW()),
('cap011', 'cs019', 'u011', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '52 days', NOW(), NOW()),
('cap012', 'cs021', 'u012', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '29 days', NOW(), NOW()),
('cap013', 'cs023', 'u013', 'PENDING_APPROVAL', NULL, NULL, NOW(), NOW()),
('cap014', 'cs024', 'u014', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '12 days', NOW(), NOW()),
('cap015', 'cs026', 'u015', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '53 days', NOW(), NOW()),
('cap016', 'cs027', 'u011', 'REJECTED', 'Please revise and resubmit with corrected figures', NOW() - INTERVAL '42 days', NOW(), NOW()),
('cap017', 'cs032', 'u012', 'PENDING_APPROVAL', NULL, NULL, NOW(), NOW()),
('cap018', 'cs033', 'u013', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '52 days', NOW(), NOW()),
('cap019', 'cs035', 'u014', 'PENDING_APPROVAL', NULL, NULL, NOW(), NOW()),
('cap020', 'cs036', 'u015', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '50 days', NOW(), NOW()),
('cap021', 'cs039', 'u011', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '45 days', NOW(), NOW()),
('cap022', 'cs040', 'u012', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '42 days', NOW(), NOW()),
('cap023', 'cs043', 'u013', 'REJECTED', 'Please revise and resubmit with corrected figures', NOW() - INTERVAL '25 days', NOW(), NOW()),
('cap024', 'cs044', 'u014', 'PENDING_APPROVAL', NULL, NULL, NOW(), NOW()),
('cap025', 'cs046', 'u015', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '62 days', NOW(), NOW()),
('cap026', 'cs047', 'u011', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '45 days', NOW(), NOW()),
('cap027', 'cs050', 'u012', 'APPROVED', 'Approved - all checks passed', NOW() - INTERVAL '42 days', NOW(), NOW());

-- Comments
INSERT INTO "comments" ("id", "complianceId", "userId", "content", "createdAt") VALUES
('cm001', 'cs001', 'u006', 'All documentation is in order.', NOW() - INTERVAL '10 days'),
('cm002', 'cs002', 'u012', 'Tax calculations verified and correct.', NOW() - INTERVAL '19 days'),
('cm003', 'cs007', 'u014', 'Need additional information from the finance team.', NOW() - INTERVAL '14 days'),
('cm004', 'cs008', 'u007', 'Please review the attached supporting documents.', NOW() - INTERVAL '18 days'),
('cm005', 'cs012', 'u010', 'Updated with latest quarter data.', NOW() - INTERVAL '38 days'),
('cm006', 'cs013', 'u006', 'All documentation is in order.', NOW() - INTERVAL '51 days'),
('cm007', 'cs017', 'u015', 'Tax calculations verified and correct.', NOW() - INTERVAL '24 days'),
('cm008', 'cs019', 'u006', 'Please review the attached supporting documents.', NOW() - INTERVAL '53 days'),
('cm009', 'cs021', 'u007', 'All documentation is in order.', NOW() - INTERVAL '30 days'),
('cm010', 'cs024', 'u010', 'Updated with latest quarter data.', NOW() - INTERVAL '13 days'),
('cm011', 'cs026', 'u007', 'All documentation is in order.', NOW() - INTERVAL '54 days'),
('cm012', 'cs027', 'u011', 'Need additional information from the finance team.', NOW() - INTERVAL '43 days'),
('cm013', 'cs033', 'u013', 'Tax calculations verified and correct.', NOW() - INTERVAL '53 days'),
('cm014', 'cs036', 'u009', 'All documentation is in order.', NOW() - INTERVAL '51 days'),
('cm015', 'cs039', 'u007', 'Please review the attached supporting documents.', NOW() - INTERVAL '46 days'),
('cm016', 'cs040', 'u008', 'Tax calculations verified and correct.', NOW() - INTERVAL '43 days'),
('cm017', 'cs043', 'u013', 'Need additional information from the finance team.', NOW() - INTERVAL '26 days'),
('cm018', 'cs046', 'u008', 'All documentation is in order.', NOW() - INTERVAL '63 days'),
('cm019', 'cs047', 'u009', 'Updated with latest quarter data.', NOW() - INTERVAL '46 days'),
('cm020', 'cs050', 'u012', 'Please review the attached supporting documents.', NOW() - INTERVAL '43 days');

-- Activities
INSERT INTO "activities" ("id", "complianceId", "userId", "action", "fromStatus", "toStatus", "createdAt") VALUES
('act001', 'cs001', 'u006', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '15 days'),
('act002', 'cs001', 'u006', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '9 days'),
('act003', 'cs002', 'u007', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '20 days'),
('act004', 'cs002', 'u007', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '17 days'),
('act005', 'cs003', 'u008', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '14 days'),
('act006', 'cs004', 'u009', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '10 days'),
('act007', 'cs004', 'u009', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '5 days'),
('act008', 'cs005', 'u010', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '7 days'),
('act009', 'cs007', 'u006', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '18 days'),
('act010', 'cs007', 'u006', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '12 days'),
('act011', 'cs008', 'u007', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '20 days'),
('act012', 'cs008', 'u007', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '17 days'),
('act013', 'cs009', 'u008', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '10 days'),
('act014', 'cs011', 'u009', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '12 days'),
('act015', 'cs011', 'u009', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '6 days'),
('act016', 'cs012', 'u010', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '40 days'),
('act017', 'cs012', 'u010', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '37 days'),
('act018', 'cs013', 'u006', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '55 days'),
('act019', 'cs013', 'u006', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '49 days'),
('act020', 'cs014', 'u007', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '5 days'),
('act021', 'cs015', 'u008', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '28 days'),
('act022', 'cs015', 'u008', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '22 days'),
('act023', 'cs017', 'u009', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '28 days'),
('act024', 'cs017', 'u009', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '22 days'),
('act025', 'cs018', 'u010', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '3 days'),
('act026', 'cs019', 'u006', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '55 days'),
('act027', 'cs019', 'u006', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '51 days'),
('act028', 'cs021', 'u007', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '35 days'),
('act029', 'cs021', 'u007', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '28 days'),
('act030', 'cs022', 'u008', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '7 days'),
('act031', 'cs023', 'u009', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '18 days'),
('act032', 'cs023', 'u009', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '15 days'),
('act033', 'cs024', 'u010', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '15 days'),
('act034', 'cs024', 'u010', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '11 days'),
('act035', 'cs025', 'u006', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '6 days'),
('act036', 'cs026', 'u007', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '58 days'),
('act037', 'cs026', 'u007', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '53 days'),
('act038', 'cs027', 'u008', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '47 days'),
('act039', 'cs027', 'u008', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '41 days'),
('act040', 'cs030', 'u009', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '2 days'),
('act041', 'cs031', 'u010', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '5 days'),
('act042', 'cs032', 'u006', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '25 days'),
('act043', 'cs032', 'u006', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '19 days'),
('act044', 'cs033', 'u007', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '57 days'),
('act045', 'cs033', 'u007', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '51 days'),
('act046', 'cs035', 'u008', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '14 days'),
('act047', 'cs035', 'u008', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '10 days'),
('act048', 'cs036', 'u009', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '55 days'),
('act049', 'cs036', 'u009', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '49 days'),
('act050', 'cs037', 'u010', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '4 days'),
('act051', 'cs038', 'u006', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '1 day'),
('act052', 'cs039', 'u007', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '50 days'),
('act053', 'cs039', 'u007', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '44 days'),
('act054', 'cs040', 'u008', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '47 days'),
('act055', 'cs040', 'u008', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '41 days'),
('act056', 'cs042', 'u009', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '6 days'),
('act057', 'cs043', 'u010', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '30 days'),
('act058', 'cs043', 'u010', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '24 days'),
('act059', 'cs044', 'u006', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '12 days'),
('act060', 'cs044', 'u006', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '8 days'),
('act061', 'cs045', 'u007', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '3 days'),
('act062', 'cs046', 'u008', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '67 days'),
('act063', 'cs046', 'u008', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '61 days'),
('act064', 'cs047', 'u009', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '50 days'),
('act065', 'cs047', 'u009', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '44 days'),
('act066', 'cs050', 'u010', 'ASSIGNED', 'DRAFT', 'PENDING_PREPARATION', NOW() - INTERVAL '47 days'),
('act067', 'cs050', 'u010', 'COMPLETED_PREPARATION', 'PENDING_PREPARATION', 'PREPARED', NOW() - INTERVAL '41 days'),
-- Approval actions
('act068', 'cs001', 'u011', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '9 days'),
('act069', 'cs002', 'u012', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '18 days'),
('act070', 'cs007', 'u014', 'REJECTED', 'PENDING_APPROVAL', 'REJECTED', NOW() - INTERVAL '13 days'),
('act071', 'cs008', 'u015', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '17 days'),
('act072', 'cs012', 'u012', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '37 days'),
('act073', 'cs013', 'u013', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '50 days'),
('act074', 'cs017', 'u015', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '23 days'),
('act075', 'cs019', 'u011', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '52 days'),
('act076', 'cs021', 'u012', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '29 days'),
('act077', 'cs024', 'u014', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '12 days'),
('act078', 'cs026', 'u015', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '53 days'),
('act079', 'cs027', 'u011', 'REJECTED', 'PENDING_APPROVAL', 'REJECTED', NOW() - INTERVAL '42 days'),
('act080', 'cs033', 'u013', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '52 days'),
('act081', 'cs036', 'u015', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '50 days'),
('act082', 'cs039', 'u011', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '45 days'),
('act083', 'cs040', 'u012', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '42 days'),
('act084', 'cs043', 'u013', 'REJECTED', 'PENDING_APPROVAL', 'REJECTED', NOW() - INTERVAL '25 days'),
('act085', 'cs046', 'u015', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '62 days'),
('act086', 'cs047', 'u011', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '45 days'),
('act087', 'cs050', 'u012', 'APPROVED', 'PENDING_APPROVAL', 'APPROVED', NOW() - INTERVAL '42 days'),
-- Comment activities
('act088', 'cs001', 'u011', 'COMMENTED', 'FILED', 'FILED', NOW() - INTERVAL '10 days'),
('act089', 'cs002', 'u012', 'COMMENTED', 'APPROVED', 'APPROVED', NOW() - INTERVAL '19 days'),
('act090', 'cs007', 'u014', 'COMMENTED', 'REJECTED', 'REJECTED', NOW() - INTERVAL '14 days'),
('act091', 'cs008', 'u007', 'COMMENTED', 'FILED', 'FILED', NOW() - INTERVAL '18 days'),
('act092', 'cs012', 'u010', 'COMMENTED', 'FILED', 'FILED', NOW() - INTERVAL '38 days'),
('act093', 'cs013', 'u006', 'COMMENTED', 'FILED', 'FILED', NOW() - INTERVAL '51 days'),
('act094', 'cs017', 'u015', 'COMMENTED', 'APPROVED', 'APPROVED', NOW() - INTERVAL '24 days'),
('act095', 'cs019', 'u006', 'COMMENTED', 'CLOSED', 'CLOSED', NOW() - INTERVAL '53 days'),
('act096', 'cs021', 'u007', 'COMMENTED', 'APPROVED', 'APPROVED', NOW() - INTERVAL '30 days'),
('act097', 'cs024', 'u010', 'COMMENTED', 'FILED', 'FILED', NOW() - INTERVAL '13 days'),
('act098', 'cs026', 'u007', 'COMMENTED', 'FILED', 'FILED', NOW() - INTERVAL '54 days'),
('act099', 'cs027', 'u011', 'COMMENTED', 'REJECTED', 'REJECTED', NOW() - INTERVAL '43 days'),
('act100', 'cs033', 'u013', 'COMMENTED', 'APPROVED', 'APPROVED', NOW() - INTERVAL '53 days'),
('act101', 'cs036', 'u009', 'COMMENTED', 'FILED', 'FILED', NOW() - INTERVAL '51 days'),
('act102', 'cs039', 'u007', 'COMMENTED', 'FILED', 'FILED', NOW() - INTERVAL '46 days'),
('act103', 'cs040', 'u008', 'COMMENTED', 'CLOSED', 'CLOSED', NOW() - INTERVAL '43 days'),
('act104', 'cs043', 'u013', 'COMMENTED', 'REJECTED', 'REJECTED', NOW() - INTERVAL '26 days'),
('act105', 'cs046', 'u008', 'COMMENTED', 'FILED', 'FILED', NOW() - INTERVAL '63 days'),
('act106', 'cs047', 'u009', 'COMMENTED', 'APPROVED', 'APPROVED', NOW() - INTERVAL '46 days'),
('act107', 'cs050', 'u012', 'COMMENTED', 'APPROVED', 'APPROVED', NOW() - INTERVAL '43 days');

-- Notifications
INSERT INTO "notifications" ("id", "userId", "title", "message", "type", "link", "createdAt") VALUES
('n001', 'u006', 'Compliance TAX-00001 Update', 'Compliance TAX-00001 is now in FILED status.', 'SUCCESS', '/compliance/TAX-00001', NOW() - INTERVAL '7 days'),
('n002', 'u007', 'Compliance TAX-00002 Update', 'Compliance TAX-00002 is now in APPROVED status.', 'INFO', '/compliance/TAX-00002', NOW() - INTERVAL '16 days'),
('n003', 'u008', 'Compliance TAX-00003 Update', 'Compliance TAX-00003 is now in PENDING_PREPARATION status.', 'WARNING', '/compliance/TAX-00003', NOW()),
('n004', 'u009', 'Compliance TAX-00004 Update', 'Compliance TAX-00004 is now in PENDING_APPROVAL status.', 'INFO', '/compliance/TAX-00004', NOW() - INTERVAL '4 days'),
('n005', 'u010', 'Compliance TAX-00005 Update', 'Compliance TAX-00005 is now in PREPARED status.', 'INFO', '/compliance/TAX-00005', NOW()),
('n006', 'u006', 'Compliance TAX-00007 Update', 'Compliance TAX-00007 is now in REJECTED status.', 'WARNING', '/compliance/TAX-00007', NOW() - INTERVAL '11 days'),
('n007', 'u007', 'Compliance TAX-00008 Update', 'Compliance TAX-00008 is now in FILED status.', 'SUCCESS', '/compliance/TAX-00008', NOW() - INTERVAL '12 days'),
('n008', 'u008', 'Compliance TAX-00009 Update', 'Compliance TAX-00009 is now in PENDING_PREPARATION status.', 'INFO', '/compliance/TAX-00009', NOW()),
('n009', 'u009', 'Compliance TAX-00011 Update', 'Compliance TAX-00011 is now in PENDING_APPROVAL status.', 'INFO', '/compliance/TAX-00011', NOW() - INTERVAL '5 days'),
('n010', 'u010', 'Compliance TAX-00012 Update', 'Compliance TAX-00012 is now in FILED status.', 'SUCCESS', '/compliance/TAX-00012', NOW() - INTERVAL '33 days'),
('n011', 'u006', 'Compliance TAX-00013 Update', 'Compliance TAX-00013 is now in FILED status.', 'SUCCESS', '/compliance/TAX-00013', NOW() - INTERVAL '47 days'),
('n012', 'u007', 'Compliance TAX-00014 Update', 'Compliance TAX-00014 is now in PREPARED status.', 'INFO', '/compliance/TAX-00014', NOW()),
('n013', 'u008', 'Compliance TAX-00015 Update', 'Compliance TAX-00015 is now in PENDING_APPROVAL status.', 'WARNING', '/compliance/TAX-00015', NOW() - INTERVAL '21 days'),
('n014', 'u009', 'Compliance TAX-00017 Update', 'Compliance TAX-00017 is now in APPROVED status.', 'INFO', '/compliance/TAX-00017', NOW() - INTERVAL '21 days'),
('n015', 'u010', 'Compliance TAX-00018 Update', 'Compliance TAX-00018 is now in PENDING_PREPARATION status.', 'INFO', '/compliance/TAX-00018', NOW()),
('n016', 'u006', 'Compliance TAX-00019 Update', 'Compliance TAX-00019 is now in CLOSED status.', 'SUCCESS', '/compliance/TAX-00019', NOW() - INTERVAL '46 days'),
('n017', 'u007', 'Compliance TAX-00021 Update', 'Compliance TAX-00021 is now in APPROVED status.', 'INFO', '/compliance/TAX-00021', NOW() - INTERVAL '27 days'),
('n018', 'u008', 'Compliance TAX-00022 Update', 'Compliance TAX-00022 is now in PENDING_PREPARATION status.', 'INFO', '/compliance/TAX-00022', NOW()),
('n019', 'u009', 'Compliance TAX-00023 Update', 'Compliance TAX-00023 is now in PENDING_APPROVAL status.', 'INFO', '/compliance/TAX-00023', NOW() - INTERVAL '14 days'),
('n020', 'u010', 'Compliance TAX-00024 Update', 'Compliance TAX-00024 is now in FILED status.', 'SUCCESS', '/compliance/TAX-00024', NOW() - INTERVAL '8 days'),
('n021', 'u006', 'Compliance TAX-00025 Update', 'Compliance TAX-00025 is now in PREPARED status.', 'INFO', '/compliance/TAX-00025', NOW()),
('n022', 'u007', 'Compliance TAX-00026 Update', 'Compliance TAX-00026 is now in FILED status.', 'SUCCESS', '/compliance/TAX-00026', NOW() - INTERVAL '50 days'),
('n023', 'u008', 'Compliance TAX-00027 Update', 'Compliance TAX-00027 is now in REJECTED status.', 'INFO', '/compliance/TAX-00027', NOW() - INTERVAL '40 days'),
('n024', 'u009', 'Compliance TAX-00030 Update', 'Compliance TAX-00030 is now in PENDING_PREPARATION status.', 'INFO', '/compliance/TAX-00030', NOW()),
('n025', 'u010', 'Compliance TAX-00032 Update', 'Compliance TAX-00032 is now in PENDING_APPROVAL status.', 'WARNING', '/compliance/TAX-00032', NOW() - INTERVAL '18 days'),
('n026', 'u006', 'Compliance TAX-00033 Update', 'Compliance TAX-00033 is now in APPROVED status.', 'INFO', '/compliance/TAX-00033', NOW() - INTERVAL '50 days'),
('n027', 'u007', 'Compliance TAX-00035 Update', 'Compliance TAX-00035 is now in PENDING_APPROVAL status.', 'INFO', '/compliance/TAX-00035', NOW() - INTERVAL '9 days'),
('n028', 'u008', 'Compliance TAX-00036 Update', 'Compliance TAX-00036 is now in FILED status.', 'SUCCESS', '/compliance/TAX-00036', NOW() - INTERVAL '46 days'),
('n029', 'u009', 'Compliance TAX-00037 Update', 'Compliance TAX-00037 is now in PREPARED status.', 'WARNING', '/compliance/TAX-00037', NOW()),
('n030', 'u006', 'Compliance TAX-00038 Update', 'Compliance TAX-00038 is now in PENDING_PREPARATION status.', 'INFO', '/compliance/TAX-00038', NOW()),
('n031', 'u007', 'Compliance TAX-00039 Update', 'Compliance TAX-00039 is now in FILED status.', 'SUCCESS', '/compliance/TAX-00039', NOW() - INTERVAL '41 days'),
('n032', 'u008', 'Compliance TAX-00040 Update', 'Compliance TAX-00040 is now in CLOSED status.', 'SUCCESS', '/compliance/TAX-00040', NOW() - INTERVAL '37 days'),
('n033', 'u009', 'Compliance TAX-00042 Update', 'Compliance TAX-00042 is now in PENDING_PREPARATION status.', 'INFO', '/compliance/TAX-00042', NOW()),
('n034', 'u010', 'Compliance TAX-00043 Update', 'Compliance TAX-00043 is now in REJECTED status.', 'WARNING', '/compliance/TAX-00043', NOW() - INTERVAL '23 days'),
('n035', 'u006', 'Compliance TAX-00044 Update', 'Compliance TAX-00044 is now in PENDING_APPROVAL status.', 'INFO', '/compliance/TAX-00044', NOW() - INTERVAL '7 days'),
('n036', 'u007', 'Compliance TAX-00045 Update', 'Compliance TAX-00045 is now in PREPARED status.', 'INFO', '/compliance/TAX-00045', NOW()),
('n037', 'u008', 'Compliance TAX-00046 Update', 'Compliance TAX-00046 is now in FILED status.', 'SUCCESS', '/compliance/TAX-00046', NOW() - INTERVAL '57 days'),
('n038', 'u009', 'Compliance TAX-00047 Update', 'Compliance TAX-00047 is now in APPROVED status.', 'INFO', '/compliance/TAX-00047', NOW() - INTERVAL '43 days'),
('n039', 'u010', 'Compliance TAX-00050 Update', 'Compliance TAX-00050 is now in APPROVED status.', 'INFO', '/compliance/TAX-00050', NOW() - INTERVAL '40 days');

-- Exchange rates (as on current month / latest available)
INSERT INTO "exchange_rates" ("id", "fromCurrency", "toCurrency", "rate", "date", "createdAt", "updatedAt") VALUES
('er001', 'INR', 'USD', 83.500000, (TO_CHAR(NOW(), 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er002', 'GBP', 'USD', 0.780000, (TO_CHAR(NOW(), 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er003', 'EUR', 'USD', 0.920000, (TO_CHAR(NOW(), 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er004', 'CAD', 'USD', 1.370000, (TO_CHAR(NOW(), 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er005', 'AUD', 'USD', 1.520000, (TO_CHAR(NOW(), 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er006', 'SGD', 'USD', 1.340000, (TO_CHAR(NOW(), 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er007', 'AED', 'USD', 3.670000, (TO_CHAR(NOW(), 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er008', 'BRL', 'USD', 5.450000, (TO_CHAR(NOW(), 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er009', 'INR', 'USD', 83.200000, (TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er010', 'EUR', 'USD', 0.910000, (TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er011', 'GBP', 'USD', 0.770000, (TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er012', 'CAD', 'USD', 1.360000, (TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er013', 'INR', 'USD', 82.950000, (TO_CHAR(NOW() - INTERVAL '2 months', 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er014', 'EUR', 'USD', 0.900000, (TO_CHAR(NOW() - INTERVAL '2 months', 'YYYY-MM') || '-15')::date, NOW(), NOW()),
('er015', 'GBP', 'USD', 0.760000, (TO_CHAR(NOW() - INTERVAL '2 months', 'YYYY-MM') || '-15')::date, NOW(), NOW());
