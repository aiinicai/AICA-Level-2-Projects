-- ============================================================================
-- TaxFlow: Complete Scenario-Based Test Dataset (1 of Each Scenario)
-- ============================================================================
-- This script provisions:
-- 1. Organization & Memberships (1 org, 5 users with 1 of each distinct role)
-- 2. Master Data (4 countries, 4 entities, 4 currencies, exchange rates, 4 forms)
-- 3. Recurring Templates (1 active approved monthly template, 1 draft template)
-- 4. Obligations (13 items, exactly 1 of each distinct lifecycle & functional scenario)
-- 5. Supporting records: assignments, multi-level approvals, payment confirmations,
--    activities timeline, and comments.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Organization
-- ----------------------------------------------------------------------------
INSERT INTO "organizations" ("id", "name", "slug", "createdById", "createdAt", "updatedAt")
VALUES (
  'org-acme-001',
  'Acme Global Indirect Tax Org',
  'acme-tax',
  'usr-admin-001',
  NOW(),
  NOW()
)
ON CONFLICT ("id") DO UPDATE SET "name" = EXCLUDED."name", "slug" = EXCLUDED."slug", "updatedAt" = NOW();

-- ----------------------------------------------------------------------------
-- 2. Users (1 of each role)
-- ----------------------------------------------------------------------------
-- Password hash corresponds to 'password123'
INSERT INTO "users" ("id", "email", "username", "password", "name", "role", "roles", "department", "employeeId", "isActive", "createdAt", "updatedAt")
VALUES
  ('usr-senthil-001',  'senthil@lucid-exp.com', 'senthil',  '$2a$10$vI8qei86EeTm9lInBWpDGHjVi/af1VXMs87N918Ww', 'Senthil',        'ADMINISTRATOR', '{ADMINISTRATOR}', 'Executive Leadership', 'EMP-000', true, NOW(), NOW()),
  ('usr-admin-001',    'admin@taxflow.com',    'admin',    '$2a$10$vI8qei86EeTm9lInBWpDGHjVi/af1VXMs87N918Ww', 'Alice Admin',    'ADMINISTRATOR', '{ADMINISTRATOR}', 'Tax & Compliance', 'EMP-001', true, NOW(), NOW()),
  ('usr-manager-001',  'manager@taxflow.com',  'manager',  '$2a$10$vI8qei86EeTm9lInBWpDGHjVi/af1VXMs87N918Ww', 'Bob Manager',   'MANAGER',       '{MANAGER}',       'Finance Leadership', 'EMP-002', true, NOW(), NOW()),
  ('usr-preparer-001', 'preparer@taxflow.com', 'preparer', '$2a$10$vI8qei86EeTm9lInBWpDGHjVi/af1VXMs87N918Ww', 'David Preparer', 'PREPARER',      '{PREPARER}',      'Tax Operations',   'EMP-003', true, NOW(), NOW()),
  ('usr-reviewer-001', 'reviewer@taxflow.com', 'reviewer', '$2a$10$vI8qei86EeTm9lInBWpDGHjVi/af1VXMs87N918Ww', 'Rachel Reviewer', 'REVIEWER',     '{REVIEWER}',      'Tax Quality',      'EMP-004', true, NOW(), NOW()),
  ('usr-approver-001', 'approver@taxflow.com', 'approver', '$2a$10$vI8qei86EeTm9lInBWpDGHjVi/af1VXMs87N918Ww', 'Alex Approver',  'APPROVER',      '{APPROVER}',      'Finance Control',  'EMP-005', true, NOW(), NOW())
ON CONFLICT ("id") DO UPDATE SET
  "name" = EXCLUDED."name",
  "role" = EXCLUDED."role",
  "roles" = EXCLUDED."roles",
  "updatedAt" = NOW();

-- Ensure if senthil already exists under another ID (e.g. from LucidShare SSO auto-provisioning), update role
UPDATE "users"
SET "role" = 'ADMINISTRATOR', "roles" = '{ADMINISTRATOR}', "updatedAt" = NOW()
WHERE LOWER("email") = 'senthil@lucid-exp.com';

-- ----------------------------------------------------------------------------
-- 3. Organization Memberships
-- ----------------------------------------------------------------------------
INSERT INTO "organization_members" ("id", "orgId", "userId", "roles", "createdAt", "updatedAt")
VALUES
  ('mem-senthil-001',  'org-acme-001', 'usr-senthil-001',  '{ADMINISTRATOR}', NOW(), NOW()),
  ('mem-001',          'org-acme-001', 'usr-admin-001',    '{ADMINISTRATOR}', NOW(), NOW()),
  ('mem-002',          'org-acme-001', 'usr-manager-001',  '{MANAGER}',       NOW(), NOW()),
  ('mem-003',          'org-acme-001', 'usr-preparer-001', '{PREPARER}',      NOW(), NOW()),
  ('mem-004',          'org-acme-001', 'usr-reviewer-001', '{REVIEWER}',      NOW(), NOW()),
  ('mem-005',          'org-acme-001', 'usr-approver-001', '{APPROVER}',      NOW(), NOW())
ON CONFLICT ("orgId", "userId") DO UPDATE SET "roles" = EXCLUDED."roles", "updatedAt" = NOW();

-- Also link any existing user with email senthil@lucid-exp.com to org-acme-001 as ADMINISTRATOR
INSERT INTO "organization_members" ("id", "orgId", "userId", "roles", "createdAt", "updatedAt")
SELECT 'mem-senthil-auto-' || substr(md5(random()::text), 1, 8), 'org-acme-001', u."id", '{ADMINISTRATOR}', NOW(), NOW()
FROM "users" u
WHERE LOWER(u."email") = 'senthil@lucid-exp.com' AND u."id" != 'usr-senthil-001'
ON CONFLICT ("orgId", "userId") DO UPDATE SET "roles" = '{ADMINISTRATOR}', "updatedAt" = NOW();

-- ----------------------------------------------------------------------------
-- 4. Countries
-- ----------------------------------------------------------------------------
INSERT INTO "countries" ("id", "name", "code", "region", "createdAt", "updatedAt")
VALUES
  ('ctry-us', 'United States', 'US', 'North America', NOW(), NOW()),
  ('ctry-gb', 'United Kingdom', 'GB', 'Europe',        NOW(), NOW()),
  ('ctry-in', 'India',          'IN', 'Asia',          NOW(), NOW()),
  ('ctry-de', 'Germany',        'DE', 'Europe',        NOW(), NOW())
ON CONFLICT ("id") DO UPDATE SET "name" = EXCLUDED."name", "code" = EXCLUDED."code";

-- ----------------------------------------------------------------------------
-- 5. Currencies & Exchange Rates
-- ----------------------------------------------------------------------------
INSERT INTO "currencies" ("id", "orgId", "code", "name", "symbol", "decimals", "isBase", "createdAt", "updatedAt")
VALUES
  ('curr-usd', 'org-acme-001', 'USD', 'US Dollar',     '$', 2, true,  NOW(), NOW()),
  ('curr-gbp', 'org-acme-001', 'GBP', 'British Pound', '£', 2, false, NOW(), NOW()),
  ('curr-eur', 'org-acme-001', 'EUR', 'Euro',          '€', 2, false, NOW(), NOW()),
  ('curr-inr', 'org-acme-001', 'INR', 'Indian Rupee',  '₹', 2, false, NOW(), NOW())
ON CONFLICT ("orgId", "code") DO UPDATE SET "name" = EXCLUDED."name", "symbol" = EXCLUDED."symbol";

INSERT INTO "exchange_rates" ("id", "fromCurrency", "toCurrency", "rate", "date", "createdAt", "updatedAt")
VALUES
  ('ex-gbp-usd', 'GBP', 'USD', 1.280000, CURRENT_DATE, NOW(), NOW()),
  ('ex-eur-usd', 'EUR', 'USD', 1.090000, CURRENT_DATE, NOW(), NOW()),
  ('ex-inr-usd', 'INR', 'USD', 0.012000, CURRENT_DATE, NOW(), NOW())
ON CONFLICT ("fromCurrency", "date") DO UPDATE SET "rate" = EXCLUDED."rate", "updatedAt" = NOW();

-- ----------------------------------------------------------------------------
-- 6. Legal Entities
-- ----------------------------------------------------------------------------
INSERT INTO "legal_entities" ("id", "orgId", "entityNumber", "entityName", "countryId", "businessUnit", "status", "taxRegistrationNumber", "currency", "approvalFlow", "createdAt", "updatedAt")
VALUES
  ('ent-us-001', 'org-acme-001', 'ENT-US-001', 'Acme US Holdings Inc.', 'ctry-us', 'North America Operations', 'ACTIVE', 'TX-US-99214', 'USD', 'ONE_LEVEL', NOW(), NOW()),
  ('ent-uk-001', 'org-acme-001', 'ENT-UK-001', 'Acme UK Operations Ltd', 'ctry-gb', 'EMEA Corporate',         'ACTIVE', 'GB-VAT-78219', 'GBP', 'TWO_LEVEL', NOW(), NOW()),
  ('ent-in-001', 'org-acme-001', 'ENT-IN-001', 'Acme India Tech Pvt Ltd', 'ctry-in', 'APAC Tech Services',     'ACTIVE', '27AABCU9603R1ZM', 'INR', 'ONE_LEVEL', NOW(), NOW()),
  ('ent-de-001', 'org-acme-001', 'ENT-DE-001', 'Acme Germany GmbH',     'ctry-de', 'EU Distribution',        'ACTIVE', 'DE-302918234', 'EUR', 'ONE_LEVEL', NOW(), NOW())
ON CONFLICT ("orgId", "entityNumber") DO UPDATE SET
  "entityName" = EXCLUDED."entityName",
  "currency" = EXCLUDED."currency",
  "approvalFlow" = EXCLUDED."approvalFlow",
  "updatedAt" = NOW();

-- ----------------------------------------------------------------------------
-- 7. Compliance Types
-- ----------------------------------------------------------------------------
INSERT INTO "compliance_types" ("id", "orgId", "name", "taxType", "frequency", "dueDateRule", "description", "defaultPreparationDays", "defaultApprovalDays", "countryId", "createdAt", "updatedAt")
VALUES
  ('ct-sales-tax', 'org-acme-001', 'US State Sales Tax',     'SALES_TAX', 'MONTHLY',   '20th of subsequent month', 'Monthly state sales & use tax filing', 5, 3, 'ctry-us', NOW(), NOW()),
  ('ct-vat-uk',    'org-acme-001', 'UK Quarterly VAT',       'VAT',       'QUARTERLY', 'Last day of following month', 'Standard quarterly UK VAT return', 10, 5, 'ctry-gb', NOW(), NOW()),
  ('ct-gst-in',    'org-acme-001', 'India GST Monthly',      'GST',       'MONTHLY',   '20th of subsequent month', 'Monthly outward & summary GST filing', 7, 3, 'ctry-in', NOW(), NOW()),
  ('ct-stat-info', 'org-acme-001', 'Annual Corporate Info',  'STATUTORY', 'ANNUAL',    '30 days after fiscal year end', 'Annual statutory information filing', 15, 5, 'ctry-de', NOW(), NOW())
ON CONFLICT ("orgId", "name") DO UPDATE SET "taxType" = EXCLUDED."taxType", "updatedAt" = NOW();

-- ----------------------------------------------------------------------------
-- 8. Form Masters
-- ----------------------------------------------------------------------------
INSERT INTO "form_master" ("id", "orgId", "formNumber", "formName", "complianceTypeId", "countryId", "taxType", "description", "approvalFlow", "requiresPayment", "createdAt", "updatedAt")
VALUES
  ('form-st100',  'org-acme-001', 'ST-100',    'Form ST-100 Sales Tax Return',       'ct-sales-tax', 'ctry-us', 'SALES_TAX', 'Standard State Sales Tax Return',         'ONE_LEVEL', true,  NOW(), NOW()),
  ('form-vat100', 'org-acme-001', 'VAT-100',   'Form VAT-100 Value Added Tax Return','ct-vat-uk',    'ctry-gb', 'VAT',       'UK Standard Quarterly VAT Return',         'TWO_LEVEL', true,  NOW(), NOW()),
  ('form-gstr3b', 'org-acme-001', 'GSTR-3B',   'Form GSTR-3B Summary GST Return',    'ct-gst-in',    'ctry-in', 'GST',       'India Monthly Summary GST Return',         'ONE_LEVEL', true,  NOW(), NOW()),
  ('form-stat01', 'org-acme-001', 'STAT-INFO', 'Form STAT-01 Annual Information Return', 'ct-stat-info', 'ctry-de', 'STATUTORY', 'Statutory Information Return (Non-Payment)', 'NONE',      false, NOW(), NOW())
ON CONFLICT ("orgId", "formNumber", "countryId") DO UPDATE SET
  "formName" = EXCLUDED."formName",
  "approvalFlow" = EXCLUDED."approvalFlow",
  "requiresPayment" = EXCLUDED."requiresPayment",
  "updatedAt" = NOW();

-- ----------------------------------------------------------------------------
-- 9. Recurring Compliance Templates (1 active approved, 1 draft)
-- ----------------------------------------------------------------------------
INSERT INTO "compliance_templates" (
  "id", "orgId", "templateNumber", "version", "status", "isActive",
  "taxType", "complianceTypeId", "formId", "countryId", "filingEntityId",
  "frequency", "dueDaysAfterPeriodEnd", "paymentDueDaysAfterPeriodEnd",
  "priority", "approvalFlow", "isRecurring", "notes",
  "preparerId", "approverId", "createdById", "createdAt", "updatedAt"
)
VALUES
  (
    'tmpl-001-active', 'org-acme-001', 'TPL-GST-IN-001', 1, 'APPROVED', true,
    'GST', 'ct-gst-in', 'form-gstr3b', 'ctry-in', 'ent-in-001',
    'MONTHLY', 20, 20,
    'HIGH', 'ONE_LEVEL', true, 'Standing recurring template for India monthly GSTR-3B obligations',
    'usr-preparer-001', 'usr-reviewer-001', 'usr-admin-001', NOW(), NOW()
  ),
  (
    'tmpl-002-draft', 'org-acme-001', 'TPL-VAT-GB-001', 0, 'DRAFT', false,
    'VAT', 'ct-vat-uk', 'form-vat100', 'ctry-gb', 'ent-uk-001',
    'QUARTERLY', 30, 30,
    'NORMAL', 'TWO_LEVEL', true, 'Draft recurring template for UK Quarterly VAT return',
    'usr-preparer-001', 'usr-approver-001', 'usr-admin-001', NOW(), NOW()
  )
ON CONFLICT ("id") DO UPDATE SET "status" = EXCLUDED."status", "updatedAt" = NOW();

INSERT INTO "compliance_template_entities" ("id", "templateId", "entityId", "createdAt")
VALUES
  ('te-001', 'tmpl-001-active', 'ent-in-001', NOW()),
  ('te-002', 'tmpl-002-draft',  'ent-uk-001', NOW())
ON CONFLICT ("templateId", "entityId") DO NOTHING;

-- ----------------------------------------------------------------------------
-- 10. Obligations Items (1 OF EACH DISTINCT SCENARIO)
-- ----------------------------------------------------------------------------

-- Clean existing scenario rows if re-running
DELETE FROM "compliance_schedules" WHERE "id" LIKE 'obl-scen-%';

-- Scenario 01: Ad-hoc / Manual item in initial DRAFT
INSERT INTO "compliance_schedules" (
  "id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "formId",
  "taxType", "taxPeriod", "taxPeriodStart", "taxPeriodEnd", "filingMonth", "frequency",
  "dueDate", "paymentDueDate", "requiresPayment", "priority", "status", "source",
  "isRecurring", "approvalFlow", "createdById", "notes", "createdAt", "updatedAt"
) VALUES (
  'obl-scen-01-draft', 'org-acme-001', 'OBL-SCEN-01', 'ent-us-001', 'ctry-us', 'ct-sales-tax', 'form-st100',
  'SALES_TAX', '2026-08-01–2026-08-31', '2026-08-01', '2026-08-31', '2026-09', 'MONTHLY',
  NOW() + INTERVAL '10 days', NOW() + INTERVAL '10 days', true, 'NORMAL', 'DRAFT', 'MANUAL',
  false, 'ONE_LEVEL', 'usr-preparer-001', 'Scenario 1: Ad-hoc obligation in initial DRAFT state awaiting submission to admin', NOW(), NOW()
);

-- Scenario 02: Pre-Preparation Gate: PENDING_ADMIN_APPROVAL
INSERT INTO "compliance_schedules" (
  "id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "formId",
  "taxType", "taxPeriod", "taxPeriodStart", "taxPeriodEnd", "filingMonth", "frequency",
  "dueDate", "paymentDueDate", "requiresPayment", "priority", "status", "source",
  "isRecurring", "approvalFlow", "createdById", "notes", "createdAt", "updatedAt"
) VALUES (
  'obl-scen-02-pending-admin', 'org-acme-001', 'OBL-SCEN-02', 'ent-us-001', 'ctry-us', 'ct-sales-tax', 'form-st100',
  'SALES_TAX', '2026-08-01–2026-08-31', '2026-08-01', '2026-08-31', '2026-09', 'MONTHLY',
  NOW() + INTERVAL '12 days', NOW() + INTERVAL '12 days', true, 'NORMAL', 'PENDING_ADMIN_APPROVAL', 'MANUAL',
  false, 'ONE_LEVEL', 'usr-preparer-001', 'Scenario 2: Manual item submitted to admin for pre-preparation gate approval', NOW() - INTERVAL '1 day', NOW()
);

-- Scenario 03: Pre-Preparation Gate: PENDING_REVIEW (Admin delegated to reviewer)
INSERT INTO "compliance_schedules" (
  "id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "formId",
  "taxType", "taxPeriod", "taxPeriodStart", "taxPeriodEnd", "filingMonth", "frequency",
  "dueDate", "paymentDueDate", "requiresPayment", "priority", "status", "source",
  "isRecurring", "approvalFlow", "reviewerId", "createdById", "notes", "createdAt", "updatedAt"
) VALUES (
  'obl-scen-03-pending-review', 'org-acme-001', 'OBL-SCEN-03', 'ent-uk-001', 'ctry-gb', 'ct-vat-uk', 'form-vat100',
  'VAT', '2026-06-01–2026-08-31', '2026-06-01', '2026-08-31', '2026-09', 'QUARTERLY',
  NOW() + INTERVAL '15 days', NOW() + INTERVAL '15 days', true, 'NORMAL', 'PENDING_REVIEW', 'MANUAL',
  false, 'TWO_LEVEL', 'usr-reviewer-001', 'usr-admin-001', 'Scenario 3: Admin sent manual obligation to Rachel Reviewer for pre-prep gate review', NOW() - INTERVAL '2 days', NOW()
);

-- Scenario 04: Template-Sourced in PENDING_PREPARATION (Active work)
INSERT INTO "compliance_schedules" (
  "id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "formId",
  "taxType", "taxPeriod", "taxPeriodStart", "taxPeriodEnd", "filingMonth", "frequency",
  "dueDate", "paymentDueDate", "requiresPayment", "priority", "status", "source",
  "templateId", "templateVersion", "isRecurring", "approvalFlow", "createdById", "notes", "createdAt", "updatedAt"
) VALUES (
  'obl-scen-04-preparation', 'org-acme-001', 'OBL-SCEN-04', 'ent-in-001', 'ctry-in', 'ct-gst-in', 'form-gstr3b',
  'GST', '2026-08-01–2026-08-31', '2026-08-01', '2026-08-31', '2026-09', 'MONTHLY',
  NOW() + INTERVAL '9 days', NOW() + INTERVAL '9 days', true, 'HIGH', 'PENDING_PREPARATION', 'TEMPLATE',
  'tmpl-001-active', 1, true, 'ONE_LEVEL', 'usr-admin-001', 'Scenario 4: Sourced from recurring template; in PENDING_PREPARATION assigned to David Preparer', NOW() - INTERVAL '3 days', NOW()
);

-- Scenario 05: Multi-Entity Group Filing in PENDING_APPROVAL (Step 1 Reviewer)
INSERT INTO "compliance_schedules" (
  "id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "formId",
  "taxType", "taxPeriod", "taxPeriodStart", "taxPeriodEnd", "filingMonth", "frequency",
  "dueDate", "paymentDueDate", "requiresPayment", "priority", "status", "source",
  "filingType", "paymentCurrency", "paymentAmount", "submittedAt",
  "isRecurring", "approvalFlow", "createdById", "notes", "createdAt", "updatedAt"
) VALUES (
  'obl-scen-05-group-step1', 'org-acme-001', 'OBL-SCEN-05', 'ent-us-001', 'ctry-us', 'ct-sales-tax', 'form-st100',
  'SALES_TAX', '2026-08-01–2026-08-31', '2026-08-01', '2026-08-31', '2026-09', 'MONTHLY',
  NOW() + INTERVAL '8 days', NOW() + INTERVAL '8 days', true, 'HIGH', 'PENDING_APPROVAL', 'MANUAL',
  'PAYMENT', 'USD', 25000.00, NOW() - INTERVAL '6 hours',
  false, 'TWO_LEVEL', 'usr-preparer-001', 'Scenario 5: Multi-entity group filing in PENDING_APPROVAL awaiting Step 1 Reviewer sign-off and amount reconfirmation', NOW() - INTERVAL '4 days', NOW()
);

-- Scenario 06: Two-Level Flow: Step 1 Approved, PENDING_APPROVAL at Step 2 (Approver)
INSERT INTO "compliance_schedules" (
  "id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "formId",
  "taxType", "taxPeriod", "taxPeriodStart", "taxPeriodEnd", "filingMonth", "frequency",
  "dueDate", "paymentDueDate", "requiresPayment", "priority", "status", "source",
  "filingType", "paymentCurrency", "paymentAmount", "submittedAt",
  "isRecurring", "approvalFlow", "createdById", "notes", "createdAt", "updatedAt"
) VALUES (
  'obl-scen-06-step2', 'org-acme-001', 'OBL-SCEN-06', 'ent-uk-001', 'ctry-gb', 'ct-vat-uk', 'form-vat100',
  'VAT', '2026-06-01–2026-08-31', '2026-06-01', '2026-08-31', '2026-09', 'QUARTERLY',
  NOW() + INTERVAL '14 days', NOW() + INTERVAL '14 days', true, 'HIGH', 'PENDING_APPROVAL', 'MANUAL',
  'PAYMENT', 'GBP', 12400.00, NOW() - INTERVAL '1 day',
  false, 'TWO_LEVEL', 'usr-preparer-001', 'Scenario 6: Two-level flow: Step 1 (Reviewer) Approved with amount reconfirmed; currently awaiting Step 2 (Alex Approver)', NOW() - INTERVAL '5 days', NOW()
);

-- Scenario 07: Flow NONE (Zero Approval): Auto-APPROVED on Submission
INSERT INTO "compliance_schedules" (
  "id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "formId",
  "taxType", "taxPeriod", "taxPeriodStart", "taxPeriodEnd", "filingMonth", "frequency",
  "dueDate", "paymentDueDate", "requiresPayment", "priority", "status", "source",
  "filingType", "paymentCurrency", "paymentAmount", "submittedAt",
  "isRecurring", "approvalFlow", "createdById", "notes", "createdAt", "updatedAt"
) VALUES (
  'obl-scen-07-none-approved', 'org-acme-001', 'OBL-SCEN-07', 'ent-us-001', 'ctry-us', 'ct-sales-tax', 'form-st100',
  'SALES_TAX', '2026-08-01–2026-08-31', '2026-08-01', '2026-08-31', '2026-09', 'MONTHLY',
  NOW() + INTERVAL '6 days', NOW() + INTERVAL '6 days', true, 'NORMAL', 'APPROVED', 'MANUAL',
  'PAYMENT', 'USD', 4800.00, NOW() - INTERVAL '4 hours',
  false, 'NONE', 'usr-preparer-001', 'Scenario 7: Zero approval flow (NONE): immediately APPROVED upon submission; ready for filing and payment', NOW() - INTERVAL '2 days', NOW()
);

-- Scenario 08: REJECTED Submission awaiting preparer resubmission
INSERT INTO "compliance_schedules" (
  "id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "formId",
  "taxType", "taxPeriod", "taxPeriodStart", "taxPeriodEnd", "filingMonth", "frequency",
  "dueDate", "paymentDueDate", "requiresPayment", "priority", "status", "source",
  "filingType", "paymentCurrency", "paymentAmount", "submittedAt",
  "isRecurring", "approvalFlow", "createdById", "notes", "createdAt", "updatedAt"
) VALUES (
  'obl-scen-08-rejected', 'org-acme-001', 'OBL-SCEN-08', 'ent-in-001', 'ctry-in', 'ct-gst-in', 'form-gstr3b',
  'GST', '2026-08-01–2026-08-31', '2026-08-01', '2026-08-31', '2026-09', 'MONTHLY',
  NOW() + INTERVAL '5 days', NOW() + INTERVAL '5 days', true, 'HIGH', 'REJECTED', 'MANUAL',
  'PAYMENT', 'INR', 180000.00, NOW() - INTERVAL '2 days',
  false, 'ONE_LEVEL', 'usr-preparer-001', 'Scenario 8: Rejected by reviewer due to ITC discrepancy; awaiting preparer resubmission', NOW() - INTERVAL '6 days', NOW()
);

-- Scenario 09: Return FILED (Payment Pending)
INSERT INTO "compliance_schedules" (
  "id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "formId",
  "taxType", "taxPeriod", "taxPeriodStart", "taxPeriodEnd", "filingMonth", "frequency",
  "dueDate", "paymentDueDate", "requiresPayment", "priority", "status", "source",
  "filingType", "paymentCurrency", "paymentAmount", "submittedAt", "filedAt",
  "isRecurring", "approvalFlow", "createdById", "notes", "createdAt", "updatedAt"
) VALUES (
  'obl-scen-09-filed-pending-pay', 'org-acme-001', 'OBL-SCEN-09', 'ent-us-001', 'ctry-us', 'ct-sales-tax', 'form-st100',
  'SALES_TAX', '2026-07-01–2026-07-31', '2026-07-01', '2026-07-31', '2026-08', 'MONTHLY',
  NOW() - INTERVAL '1 day', NOW() + INTERVAL '3 days', true, 'HIGH', 'FILED', 'TEMPLATE',
  'PAYMENT', 'USD', 9200.00, NOW() - INTERVAL '4 days', NOW() - INTERVAL '2 days',
  true, 'ONE_LEVEL', 'usr-admin-001', 'Scenario 9: Return FILED with tax portal (filedAt recorded); payment remains pending before payment due date', NOW() - INTERVAL '15 days', NOW()
);

-- Scenario 10: Liability PAID (Filing Pending) - Demonstrates flexible ordering
INSERT INTO "compliance_schedules" (
  "id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "formId",
  "taxType", "taxPeriod", "taxPeriodStart", "taxPeriodEnd", "filingMonth", "frequency",
  "dueDate", "paymentDueDate", "requiresPayment", "priority", "status", "source",
  "filingType", "paymentCurrency", "paymentAmount", "submittedAt",
  "paidAt", "paymentDate", "paymentReference", "paymentMethod", "paymentNotes",
  "isRecurring", "approvalFlow", "createdById", "notes", "createdAt", "updatedAt"
) VALUES (
  'obl-scen-10-paid-pending-file', 'org-acme-001', 'OBL-SCEN-10', 'ent-uk-001', 'ctry-gb', 'ct-vat-uk', 'form-vat100',
  'VAT', '2026-06-01–2026-08-31', '2026-06-01', '2026-08-31', '2026-09', 'QUARTERLY',
  NOW() + INTERVAL '4 days', NOW() + INTERVAL '4 days', true, 'NORMAL', 'PAID', 'MANUAL',
  'PAYMENT', 'GBP', 7500.00, NOW() - INTERVAL '3 days',
  NOW() - INTERVAL '1 day', CURRENT_DATE - INTERVAL '1 day', 'BANK-CHAPS-99214', 'WIRE_TRANSFER', 'Payment executed ahead of portal filing',
  false, 'ONE_LEVEL', 'usr-preparer-001', 'Scenario 10: Liability PAID via bank transfer; return filing is still pending (flexible pay-first ordering)', NOW() - INTERVAL '10 days', NOW()
);

-- Scenario 11: Non-Payment / NIL Return — Filed & administratively CLOSED
INSERT INTO "compliance_schedules" (
  "id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "formId",
  "taxType", "taxPeriod", "taxPeriodStart", "taxPeriodEnd", "filingMonth", "frequency",
  "dueDate", "paymentDueDate", "requiresPayment", "priority", "status", "source",
  "filingType", "paymentAmount", "submittedAt", "filedAt",
  "isRecurring", "approvalFlow", "createdById", "notes", "createdAt", "updatedAt"
) VALUES (
  'obl-scen-11-nil-closed', 'org-acme-001', 'OBL-SCEN-11', 'ent-de-001', 'ctry-de', 'ct-stat-info', 'form-stat01',
  'STATUTORY', '2025-01-01–2025-12-31', '2025-01-01', '2025-12-31', '2026-01', 'ANNUAL',
  NOW() - INTERVAL '20 days', null, false, 'NORMAL', 'CLOSED', 'TEMPLATE',
  'NIL_RETURN', 0.00, NOW() - INTERVAL '25 days', NOW() - INTERVAL '22 days',
  true, 'NONE', 'usr-admin-001', 'Scenario 11: Non-payment return (requiresPayment=false); filed as NIL Return and administratively CLOSED', NOW() - INTERVAL '40 days', NOW()
);

-- Scenario 12: Refund Return — Claimed & CLOSED
INSERT INTO "compliance_schedules" (
  "id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "formId",
  "taxType", "taxPeriod", "taxPeriodStart", "taxPeriodEnd", "filingMonth", "frequency",
  "dueDate", "paymentDueDate", "requiresPayment", "priority", "status", "source",
  "filingType", "refundType", "paymentCurrency", "paymentAmount", "refundAmount", "submittedAt", "filedAt",
  "isRecurring", "approvalFlow", "createdById", "notes", "createdAt", "updatedAt"
) VALUES (
  'obl-scen-12-refund-closed', 'org-acme-001', 'OBL-SCEN-12', 'ent-de-001', 'ctry-de', 'ct-vat-uk', 'form-vat100',
  'VAT', '2026-04-01–2026-06-30', '2026-04-01', '2026-06-30', '2026-07', 'QUARTERLY',
  NOW() - INTERVAL '35 days', NOW() - INTERVAL '35 days', true, 'NORMAL', 'CLOSED', 'MANUAL',
  'REFUND_RETURN', 'CLAIMED', 'EUR', 6750.00, 6750.00, NOW() - INTERVAL '40 days', NOW() - INTERVAL '36 days',
  false, 'ONE_LEVEL', 'usr-preparer-001', 'Scenario 12: Refund return with €6,750 CLAIMED from tax authority; filed and administratively CLOSED', NOW() - INTERVAL '50 days', NOW()
);

-- Scenario 13: Overdue Obligation (CRITICAL Priority)
INSERT INTO "compliance_schedules" (
  "id", "orgId", "complianceId", "entityId", "countryId", "complianceTypeId", "formId",
  "taxType", "taxPeriod", "taxPeriodStart", "taxPeriodEnd", "filingMonth", "frequency",
  "dueDate", "paymentDueDate", "requiresPayment", "priority", "status", "source",
  "isRecurring", "approvalFlow", "createdById", "notes", "createdAt", "updatedAt"
) VALUES (
  'obl-scen-13-overdue-critical', 'org-acme-001', 'OBL-SCEN-13', 'ent-in-001', 'ctry-in', 'ct-gst-in', 'form-gstr3b',
  'GST', '2026-07-01–2026-07-31', '2026-07-01', '2026-07-31', '2026-08', 'MONTHLY',
  NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days', true, 'CRITICAL', 'PENDING_PREPARATION', 'MANUAL',
  false, 'ONE_LEVEL', 'usr-preparer-001', 'Scenario 13: Past-due obligation (7 days overdue) displaying red Overdue warnings and critical priority badge', NOW() - INTERVAL '25 days', NOW()
);

-- ----------------------------------------------------------------------------
-- 11. Multi-Entity Group Filing Links (Scenario 05 links both US & DE entities)
-- ----------------------------------------------------------------------------
INSERT INTO "compliance_entities" ("id", "complianceId", "entityId", "createdAt")
VALUES
  ('ce-scen-05-a', 'obl-scen-05-group-step1', 'ent-us-001', NOW()),
  ('ce-scen-05-b', 'obl-scen-05-group-step1', 'ent-de-001', NOW())
ON CONFLICT ("complianceId", "entityId") DO NOTHING;

-- ----------------------------------------------------------------------------
-- 12. Assignments (Link David Preparer to obligations)
-- ----------------------------------------------------------------------------
INSERT INTO "compliance_assignments" ("id", "complianceId", "preparerId", "startedAt", "completedAt", "createdAt", "updatedAt")
VALUES
  ('asg-01', 'obl-scen-01-draft',            'usr-preparer-001', null, null, NOW(), NOW()),
  ('asg-02', 'obl-scen-02-pending-admin',    'usr-preparer-001', null, null, NOW(), NOW()),
  ('asg-03', 'obl-scen-03-pending-review',   'usr-preparer-001', null, null, NOW(), NOW()),
  ('asg-04', 'obl-scen-04-preparation',      'usr-preparer-001', NOW() - INTERVAL '2 days', null, NOW(), NOW()),
  ('asg-05', 'obl-scen-05-group-step1',      'usr-preparer-001', NOW() - INTERVAL '3 days', NOW() - INTERVAL '6 hours', NOW(), NOW()),
  ('asg-06', 'obl-scen-06-step2',            'usr-preparer-001', NOW() - INTERVAL '4 days', NOW() - INTERVAL '1 day', NOW(), NOW()),
  ('asg-07', 'obl-scen-07-none-approved',    'usr-preparer-001', NOW() - INTERVAL '1 day',  NOW() - INTERVAL '4 hours', NOW(), NOW()),
  ('asg-08', 'obl-scen-08-rejected',         'usr-preparer-001', NOW() - INTERVAL '5 days', NOW() - INTERVAL '3 days', NOW(), NOW()),
  ('asg-09', 'obl-scen-09-filed-pending-pay','usr-preparer-001', NOW() - INTERVAL '10 days', NOW() - INTERVAL '4 days', NOW(), NOW()),
  ('asg-10', 'obl-scen-10-paid-pending-file','usr-preparer-001', NOW() - INTERVAL '8 days', NOW() - INTERVAL '3 days', NOW(), NOW()),
  ('asg-11', 'obl-scen-11-nil-closed',       'usr-preparer-001', NOW() - INTERVAL '30 days', NOW() - INTERVAL '25 days', NOW(), NOW()),
  ('asg-12', 'obl-scen-12-refund-closed',    'usr-preparer-001', NOW() - INTERVAL '45 days', NOW() - INTERVAL '40 days', NOW(), NOW()),
  ('asg-13', 'obl-scen-13-overdue-critical', 'usr-preparer-001', NOW() - INTERVAL '20 days', null, NOW(), NOW())
ON CONFLICT ("complianceId", "preparerId") DO NOTHING;

-- ----------------------------------------------------------------------------
-- 13. Multi-Level Approvals (1-level & 2-level steps)
-- ----------------------------------------------------------------------------
INSERT INTO "compliance_approvals" ("id", "complianceId", "approverId", "step", "status", "comments", "actionAt", "createdAt", "updatedAt")
VALUES
  -- Scenario 05 (Two-Level: Step 1 Pending Reviewer, Step 2 Pending Approver)
  ('app-05-s1', 'obl-scen-05-group-step1', 'usr-reviewer-001', 1, 'PENDING_APPROVAL', null, null, NOW(), NOW()),
  ('app-05-s2', 'obl-scen-05-group-step1', 'usr-approver-001', 2, 'PENDING_APPROVAL', null, null, NOW(), NOW()),

  -- Scenario 06 (Two-Level: Step 1 Approved by Reviewer, Step 2 Pending Approver)
  ('app-06-s1', 'obl-scen-06-step2', 'usr-reviewer-001', 1, 'APPROVED', 'Figures verified against GL report and bank balances.', NOW() - INTERVAL '18 hours', NOW(), NOW()),
  ('app-06-s2', 'obl-scen-06-step2', 'usr-approver-001', 2, 'PENDING_APPROVAL', null, null, NOW(), NOW()),

  -- Scenario 08 (One-Level: Rejected by Reviewer)
  ('app-08-s1', 'obl-scen-08-rejected', 'usr-reviewer-001', 1, 'REJECTED', 'Input tax credit discrepancy between Books and GSTR-2B; please reconcile and resubmit.', NOW() - INTERVAL '2 days', NOW(), NOW()),

  -- Scenario 09 (One-Level: Approved)
  ('app-09-s1', 'obl-scen-09-filed-pending-pay', 'usr-reviewer-001', 1, 'APPROVED', 'Approved for filing.', NOW() - INTERVAL '3 days', NOW(), NOW()),

  -- Scenario 10 (One-Level: Approved)
  ('app-10-s1', 'obl-scen-10-paid-pending-file', 'usr-reviewer-001', 1, 'APPROVED', 'Approved for wire transfer.', NOW() - INTERVAL '2 days', NOW(), NOW()),

  -- Scenario 12 (One-Level: Approved)
  ('app-12-s1', 'obl-scen-12-refund-closed', 'usr-reviewer-001', 1, 'APPROVED', 'Refund verified against credit notes.', NOW() - INTERVAL '38 days', NOW(), NOW()),

  -- Scenario 13 (One-Level: Pending)
  ('app-13-s1', 'obl-scen-13-overdue-critical', 'usr-reviewer-001', 1, 'PENDING_APPROVAL', null, null, NOW(), NOW())
ON CONFLICT ("complianceId", "approverId") DO UPDATE SET
  "status" = EXCLUDED."status",
  "comments" = EXCLUDED."comments",
  "actionAt" = EXCLUDED."actionAt",
  "updatedAt" = NOW();

-- ----------------------------------------------------------------------------
-- 14. Mandatory Payment Confirmations
-- ----------------------------------------------------------------------------
INSERT INTO "compliance_payment_confirmations" ("id", "complianceId", "stage", "confirmedById", "confirmedAt")
VALUES
  -- Scenario 05: Preparer confirmed on submit
  ('conf-05-prep', 'obl-scen-05-group-step1', 'PREPARER_SUBMIT', 'usr-preparer-001', NOW() - INTERVAL '6 hours'),

  -- Scenario 06: Preparer confirmed + Reviewer reconfirmed
  ('conf-06-prep', 'obl-scen-06-step2', 'PREPARER_SUBMIT', 'usr-preparer-001', NOW() - INTERVAL '1 day'),
  ('conf-06-rev',  'obl-scen-06-step2', 'REVIEWER',        'usr-reviewer-001', NOW() - INTERVAL '18 hours'),

  -- Scenario 09: Preparer confirmed + Reviewer confirmed
  ('conf-09-prep', 'obl-scen-09-filed-pending-pay', 'PREPARER_SUBMIT', 'usr-preparer-001', NOW() - INTERVAL '4 days'),
  ('conf-09-rev',  'obl-scen-09-filed-pending-pay', 'REVIEWER',        'usr-reviewer-001', NOW() - INTERVAL '3 days'),

  -- Scenario 10: Preparer confirmed + Reviewer confirmed + Payment confirmed
  ('conf-10-prep', 'obl-scen-10-paid-pending-file', 'PREPARER_SUBMIT',  'usr-preparer-001', NOW() - INTERVAL '3 days'),
  ('conf-10-rev',  'obl-scen-10-paid-pending-file', 'REVIEWER',         'usr-reviewer-001', NOW() - INTERVAL '2 days'),
  ('conf-10-pay',  'obl-scen-10-paid-pending-file', 'PREPARER_PAYMENT', 'usr-preparer-001', NOW() - INTERVAL '1 day')
ON CONFLICT ("complianceId", "stage") DO NOTHING;

-- ----------------------------------------------------------------------------
-- 15. Activity Timeline Entries
-- ----------------------------------------------------------------------------
INSERT INTO "activities" ("id", "complianceId", "userId", "action", "fromStatus", "toStatus", "comments", "createdAt")
VALUES
  ('act-01', 'obl-scen-01-draft', 'usr-preparer-001', 'CREATED', null, 'DRAFT', 'Created manual sales tax obligation entry', NOW()),
  ('act-02', 'obl-scen-02-pending-admin', 'usr-preparer-001', 'SUBMITTED_TO_ADMIN', 'DRAFT', 'PENDING_ADMIN_APPROVAL', 'Submitted to admin for pre-preparation sign-off', NOW() - INTERVAL '1 day'),
  ('act-03', 'obl-scen-03-pending-review', 'usr-admin-001', 'SENT_TO_REVIEWER', 'PENDING_ADMIN_APPROVAL', 'PENDING_REVIEW', 'Delegated to Rachel Reviewer for gate review', NOW() - INTERVAL '2 days'),
  ('act-04', 'obl-scen-04-preparation', 'usr-admin-001', 'CREATED', null, 'PENDING_PREPARATION', 'Generated from recurring template TPL-GST-IN-001 v1', NOW() - INTERVAL '3 days'),
  ('act-05', 'obl-scen-05-group-step1', 'usr-preparer-001', 'SUBMITTED', 'PENDING_PREPARATION', 'PENDING_APPROVAL', 'Submitted multi-entity filing with $25,000 payment details', NOW() - INTERVAL '6 hours'),
  ('act-06', 'obl-scen-06-step2', 'usr-reviewer-001', 'STEP_APPROVED', 'PENDING_APPROVAL', 'PENDING_APPROVAL', 'Step 1 Reviewer sign-off completed; forwarded to Approver', NOW() - INTERVAL '18 hours'),
  ('act-07', 'obl-scen-07-none-approved', 'usr-preparer-001', 'SUBMITTED', 'PENDING_PREPARATION', 'APPROVED', 'Submitted and auto-approved (approval flow NONE)', NOW() - INTERVAL '4 hours'),
  ('act-08', 'obl-scen-08-rejected', 'usr-reviewer-001', 'REJECTED', 'PENDING_APPROVAL', 'REJECTED', 'Rejected due to ITC discrepancy with books', NOW() - INTERVAL '2 days'),
  ('act-09', 'obl-scen-09-filed-pending-pay', 'usr-admin-001', 'FILED', 'APPROVED', 'FILED', 'Filed successfully on tax portal; receipt saved', NOW() - INTERVAL '2 days'),
  ('act-10', 'obl-scen-10-paid-pending-file', 'usr-preparer-001', 'PAID', 'APPROVED', 'PAID', 'Payment of £7,500 executed via CHAPS wire transfer', NOW() - INTERVAL '1 day'),
  ('act-11', 'obl-scen-11-nil-closed', 'usr-admin-001', 'CLOSED', 'FILED', 'CLOSED', 'Form has requiresPayment=false; administratively closed', NOW() - INTERVAL '20 days'),
  ('act-12', 'obl-scen-12-refund-closed', 'usr-manager-001', 'CLOSED', 'FILED', 'CLOSED', 'Refund of €6,750 claimed; closed obligation', NOW() - INTERVAL '35 days'),
  ('act-13', 'obl-scen-13-overdue-critical', 'usr-preparer-001', 'CREATED', null, 'PENDING_PREPARATION', 'Obligation overdue by 7 days', NOW() - INTERVAL '20 days')
ON CONFLICT ("id") DO NOTHING;

-- ----------------------------------------------------------------------------
-- 16. Contextual Comments
-- ----------------------------------------------------------------------------
INSERT INTO "comments" ("id", "complianceId", "userId", "content", "createdAt")
VALUES
  ('cmt-01', 'obl-scen-05-group-step1', 'usr-preparer-001', 'Group return includes figures from both Acme US and Acme Germany operations.', NOW() - INTERVAL '5 hours'),
  ('cmt-02', 'obl-scen-06-step2', 'usr-reviewer-001', 'Reviewed reconciliation sheet. Output tax matches invoices 1001-1450.', NOW() - INTERVAL '18 hours'),
  ('cmt-03', 'obl-scen-08-rejected', 'usr-reviewer-001', 'Vendor invoice #9921 for INR 42,000 is missing from GSTR-2B. Please recheck before resubmitting.', NOW() - INTERVAL '2 days'),
  ('cmt-04', 'obl-scen-09-filed-pending-pay', 'usr-admin-001', 'Filing confirmation #US-ST-2026-9912 received. Treasury team please initiate wire.', NOW() - INTERVAL '2 days'),
  ('cmt-05', 'obl-scen-10-paid-pending-file', 'usr-preparer-001', 'Bank payment ref TXN-UK-882193 posted. Return filing portal opens tomorrow.', NOW() - INTERVAL '1 day')
ON CONFLICT ("id") DO NOTHING;

-- ----------------------------------------------------------------------------
-- 17. User Notifications
-- ----------------------------------------------------------------------------
INSERT INTO "notifications" ("id", "userId", "title", "message", "type", "link", "read", "createdAt")
VALUES
  ('notif-01', 'usr-admin-001',    'Compliance Awaiting Admin Approval', 'Compliance OBL-SCEN-02 has been submitted for pre-preparation approval.', 'WARNING', '/compliance/obl-scen-02-pending-admin', false, NOW() - INTERVAL '1 day'),
  ('notif-02', 'usr-reviewer-001', 'Compliance Sent for Your Review',   'Compliance OBL-SCEN-03 has been sent for your pre-preparation review.', 'INFO', '/compliance/obl-scen-03-pending-review', false, NOW() - INTERVAL '2 days'),
  ('notif-03', 'usr-reviewer-001', 'Compliance Pending Review (Step 1)','Compliance OBL-SCEN-05 requires your step 1 approval and amount confirmation.', 'APPROVAL', '/compliance/obl-scen-05-group-step1', false, NOW() - INTERVAL '6 hours'),
  ('notif-04', 'usr-approver-001', 'Compliance Ready for Approval',    'Compliance OBL-SCEN-06 has been reviewed by Rachel and awaits your final sign-off.', 'APPROVAL', '/compliance/obl-scen-06-step2', false, NOW() - INTERVAL '18 hours'),
  ('notif-05', 'usr-preparer-001', 'Compliance Ready for Resubmission', 'Compliance OBL-SCEN-08 was rejected by Rachel Reviewer. Reason: ITC discrepancy.', 'ERROR', '/compliance/obl-scen-08-rejected', false, NOW() - INTERVAL '2 days'),
  ('notif-06', 'usr-preparer-001', 'Urgent Overdue Obligation',         'Compliance OBL-SCEN-13 is 7 days overdue. Please expedite preparation.', 'ERROR', '/compliance/obl-scen-13-overdue-critical', false, NOW() - INTERVAL '1 hour')
ON CONFLICT ("id") DO NOTHING;
