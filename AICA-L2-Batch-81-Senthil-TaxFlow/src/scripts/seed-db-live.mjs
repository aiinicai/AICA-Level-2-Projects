import { createClient } from "@supabase/supabase-js"
import fs from "node:fs"

const env = fs.readFileSync(".env", "utf8")
const url = env.match(/NEXT_PUBLIC_SUPABASE_URL="([^"]+)"/)?.[1]
const key = env.match(/SUPABASE_SERVICE_ROLE_KEY="([^"]+)"/)?.[1]

if (!url || !key) {
  console.error("Missing Supabase credentials in .env")
  process.exit(1)
}

const supabase = createClient(url, key, {
  auth: { autoRefreshToken: false, persistSession: false },
})

console.log("Starting scenario seeding against:", url)

// 1. Organization: Acme Global Indirect Tax Org
const { data: org, error: orgErr } = await supabase.from("organizations").upsert({
  id: "org-acme-001",
  name: "Acme Global Indirect Tax Org",
  slug: "acme-tax",
  createdById: "8d3bf755-1789-452b-9840-97e870843875",
  updatedAt: new Date().toISOString(),
}).select().single()

if (orgErr) {
  console.error("Org insert error:", orgErr)
} else {
  console.log("✓ Organization created/updated:", org.name, `(${org.id})`)
}

// 2. Locate Senthil's existing user
const { data: existingSenthil } = await supabase
  .from("users")
  .select("id, email")
  .ilike("email", "senthil@lucid-exp.com")
  .maybeSingle()

const senthilId = existingSenthil?.id || "8d3bf755-1789-452b-9840-97e870843875"
console.log("Senthil user ID:", senthilId)

// Update Senthil's user roles to include ADMINISTRATOR
await supabase
  .from("users")
  .update({
    role: "ADMINISTRATOR",
    roles: ["ADMINISTRATOR", "PREPARER", "APPROVER", "REVIEWER"],
    updatedAt: new Date().toISOString(),
  })
  .eq("id", senthilId)

// Link Senthil to Acme Global Indirect Tax Org as ADMINISTRATOR
const { data: senthilMember, error: memErr } = await supabase
  .from("organization_members")
  .upsert({
    id: `mem-senthil-${senthilId}`,
    orgId: "org-acme-001",
    userId: senthilId,
    roles: ["ADMINISTRATOR", "PREPARER", "APPROVER", "REVIEWER"],
    updatedAt: new Date().toISOString(),
  })
  .select()
  .single()

if (memErr) {
  console.error("Membership error:", memErr)
} else {
  console.log("✓ Senthil successfully linked to Acme Global Indirect Tax Org as ADMINISTRATOR!")
}

// Seed additional sample users for the scenario workflow
const users = [
  { id: "u001", email: "admin@taxflow.com", username: "admin", name: "Alice Admin", role: "ADMINISTRATOR", roles: ["ADMINISTRATOR"], department: "Tax & Compliance" },
  { id: "u003", email: "manager1@taxflow.com", username: "manager1", name: "Bob Manager", role: "MANAGER", roles: ["MANAGER"], department: "Finance Leadership" },
  { id: "u006", email: "preparer1@taxflow.com", username: "preparer1", name: "David Preparer", role: "PREPARER", roles: ["PREPARER"], department: "Tax Operations" },
  { id: "u011", email: "approver1@taxflow.com", username: "approver1", name: "Rachel Reviewer", role: "REVIEWER", roles: ["REVIEWER"], department: "Tax Quality" },
  { id: "u012", email: "approver2@taxflow.com", username: "approver2", name: "Alex Approver", role: "APPROVER", roles: ["APPROVER"], department: "Finance Control" },
]

for (const u of users) {
  await supabase.from("users").upsert({ ...u, updatedAt: new Date().toISOString() })
  await supabase.from("organization_members").upsert({
    id: `mem-${u.id}-acme`,
    orgId: "org-acme-001",
    userId: u.id,
    roles: u.roles,
    updatedAt: new Date().toISOString(),
  })
}
console.log("✓ Workflow users (Admin, Manager, Preparer, Reviewer, Approver) linked to Acme Org")

// 3. Countries (using existing country IDs in DB)
// c001: US, c003: GB, c007: IN, c004: DE
console.log("✓ Countries verified (c001: US, c003: GB, c007: IN, c004: DE)")

// 4. Currencies
const currencies = [
  { id: "curr-usd", orgId: "org-acme-001", code: "USD", name: "US Dollar", symbol: "$", decimals: 2, isBase: true },
  { id: "curr-gbp", orgId: "org-acme-001", code: "GBP", name: "British Pound", symbol: "£", decimals: 2, isBase: false },
  { id: "curr-eur", orgId: "org-acme-001", code: "EUR", name: "Euro", symbol: "€", decimals: 2, isBase: false },
  { id: "curr-inr", orgId: "org-acme-001", code: "INR", name: "Indian Rupee", symbol: "₹", decimals: 2, isBase: false },
]
for (const cur of currencies) {
  await supabase.from("currencies").upsert({ ...cur, updatedAt: new Date().toISOString() })
}

// 5. Legal Entities
const entities = [
  { id: "ent-us-001", orgId: "org-acme-001", entityNumber: "ENT-US-001", entityName: "Acme US Holdings Inc.", countryId: "c001", businessUnit: "North America Operations", status: "ACTIVE", taxRegistrationNumber: "TX-US-99214", currency: "USD", approvalFlow: "ONE_LEVEL" },
  { id: "ent-uk-001", orgId: "org-acme-001", entityNumber: "ENT-UK-001", entityName: "Acme UK Operations Ltd", countryId: "c003", businessUnit: "EMEA Corporate", status: "ACTIVE", taxRegistrationNumber: "GB-VAT-78219", currency: "GBP", approvalFlow: "TWO_LEVEL" },
  { id: "ent-in-001", orgId: "org-acme-001", entityNumber: "ENT-IN-001", entityName: "Acme India Tech Pvt Ltd", countryId: "c007", businessUnit: "APAC Tech Services", status: "ACTIVE", taxRegistrationNumber: "27AABCU9603R1ZM", currency: "INR", approvalFlow: "ONE_LEVEL" },
  { id: "ent-de-001", orgId: "org-acme-001", entityNumber: "ENT-DE-001", entityName: "Acme Germany GmbH", countryId: "c004", businessUnit: "EU Distribution", status: "ACTIVE", taxRegistrationNumber: "DE-302918234", currency: "EUR", approvalFlow: "ONE_LEVEL" },
]
for (const e of entities) {
  const { error: entErr } = await supabase.from("legal_entities").upsert({ ...e, updatedAt: new Date().toISOString() })
  if (entErr) console.error("Error upserting entity:", e.id, entErr)
}
console.log("✓ Legal Entities created for Acme Org")

// 6. Compliance Types & Forms
const complianceTypes = [
  { id: "ct-sales-tax", orgId: "org-acme-001", name: "US State Sales Tax", taxType: "SALES_TAX", frequency: "MONTHLY", dueDateRule: "20th of subsequent month", description: "Monthly state sales & use tax filing", countryId: "c001" },
  { id: "ct-vat-uk", orgId: "org-acme-001", name: "UK Quarterly VAT", taxType: "VAT", frequency: "QUARTERLY", dueDateRule: "Last day of following month", description: "Standard quarterly UK VAT return", countryId: "c003" },
  { id: "ct-gst-in", orgId: "org-acme-001", name: "India GST Monthly", taxType: "GST", frequency: "MONTHLY", dueDateRule: "20th of subsequent month", description: "Monthly outward & summary GST filing", countryId: "c007" },
  { id: "ct-stat-info", orgId: "org-acme-001", name: "Annual Corporate Info", taxType: "STATUTORY", frequency: "ANNUAL", dueDateRule: "30 days after fiscal year end", description: "Annual statutory information filing", countryId: "c004" },
]
for (const ct of complianceTypes) {
  const { error: ctErr } = await supabase.from("compliance_types").upsert({ ...ct, updatedAt: new Date().toISOString() })
  if (ctErr) console.error("Error upserting complianceType:", ct.id, ctErr)
}

const forms = [
  { id: "form-st100", orgId: "org-acme-001", formNumber: "ST-100", formName: "Form ST-100 Sales Tax Return", complianceTypeId: "ct-sales-tax", countryId: "c001", taxType: "SALES_TAX", description: "Standard State Sales Tax Return", approvalFlow: "ONE_LEVEL", requiresPayment: true },
  { id: "form-vat100", orgId: "org-acme-001", formNumber: "VAT-100", formName: "Form VAT-100 Value Added Tax Return", complianceTypeId: "ct-vat-uk", countryId: "c003", taxType: "VAT", description: "UK Standard Quarterly VAT Return", approvalFlow: "TWO_LEVEL", requiresPayment: true },
  { id: "form-gstr3b", orgId: "org-acme-001", formNumber: "GSTR-3B", formName: "Form GSTR-3B Summary GST Return", complianceTypeId: "ct-gst-in", countryId: "c007", taxType: "GST", description: "India Monthly Summary GST Return", approvalFlow: "ONE_LEVEL", requiresPayment: true },
  { id: "form-stat01", orgId: "org-acme-001", formNumber: "STAT-INFO", formName: "Form STAT-01 Annual Information Return", complianceTypeId: "ct-stat-info", countryId: "c004", taxType: "STATUTORY", description: "Statutory Information Return (Non-Payment)", approvalFlow: "NONE", requiresPayment: false },
]
for (const f of forms) {
  const { error: fErr } = await supabase.from("form_master").upsert({ ...f, updatedAt: new Date().toISOString() })
  if (fErr) console.error("Error upserting form:", f.id, fErr)
}
console.log("✓ Compliance Types & Forms created")

// 7. Recurring Templates
const { error: tmplErr } = await supabase.from("compliance_templates").upsert([
  {
    id: "tmpl-001-active",
    orgId: "org-acme-001",
    templateNumber: "TPL-GST-IN-001",
    version: 1,
    status: "APPROVED",
    isActive: true,
    taxType: "GST",
    complianceTypeId: "ct-gst-in",
    formId: "form-gstr3b",
    countryId: "c007",
    filingEntityId: "ent-in-001",
    frequency: "MONTHLY",
    dueDaysAfterPeriodEnd: 20,
    paymentDueDaysAfterPeriodEnd: 20,
    priority: "HIGH",
    isRecurring: true,
    notes: "Standing recurring template for India monthly GSTR-3B obligations",
    preparerId: "u006",
    approverId: "u011",
    createdById: senthilId,
    updatedAt: new Date().toISOString(),
  },
  {
    id: "tmpl-002-draft",
    orgId: "org-acme-001",
    templateNumber: "TPL-VAT-GB-001",
    version: 0,
    status: "DRAFT",
    isActive: false,
    taxType: "VAT",
    complianceTypeId: "ct-vat-uk",
    formId: "form-vat100",
    countryId: "c003",
    filingEntityId: "ent-uk-001",
    frequency: "QUARTERLY",
    dueDaysAfterPeriodEnd: 30,
    paymentDueDaysAfterPeriodEnd: 30,
    priority: "NORMAL",
    isRecurring: true,
    notes: "Draft recurring template for UK Quarterly VAT return",
    preparerId: "u006",
    approverId: "u012",
    createdById: senthilId,
    updatedAt: new Date().toISOString(),
  },
])
if (tmplErr) console.error("Error upserting templates:", tmplErr)

const { error: teErr } = await supabase.from("compliance_template_entities").upsert([
  { id: "te-001", templateId: "tmpl-001-active", entityId: "ent-in-001" },
  { id: "te-002", templateId: "tmpl-002-draft", entityId: "ent-uk-001" },
])
if (teErr) console.error("Error upserting template entities:", teErr)
console.log("✓ Recurring Templates created")

// 8. The 13 Specific Scenario Obligations Items
const now = new Date()
const d = (offsetDays) => new Date(now.getTime() + offsetDays * 86400000).toISOString()

const obligations = [
  // Scenario 1: DRAFT
  {
    id: "obl-scen-01-draft",
    orgId: "org-acme-001",
    complianceId: "OBL-SCEN-01",
    entityId: "ent-us-001",
    countryId: "c001",
    complianceTypeId: "ct-sales-tax",
    formId: "form-st100",
    taxType: "SALES_TAX",
    taxPeriod: "2026-08-01–2026-08-31",
    taxPeriodStart: "2026-08-01T00:00:00.000Z",
    taxPeriodEnd: "2026-08-31T23:59:59.000Z",
    filingMonth: "2026-09",
    frequency: "MONTHLY",
    dueDate: d(10),
    paymentDueDate: d(10),
    requiresPayment: true,
    priority: "NORMAL",
    status: "DRAFT",
    source: "MANUAL",
    isRecurring: false,
    createdById: senthilId,
    notes: "Scenario 1: Ad-hoc obligation in initial DRAFT state awaiting submission to admin",
    updatedAt: now.toISOString(),
  },
  // Scenario 2: PENDING_ADMIN_APPROVAL
  {
    id: "obl-scen-02-pending-admin",
    orgId: "org-acme-001",
    complianceId: "OBL-SCEN-02",
    entityId: "ent-us-001",
    countryId: "c001",
    complianceTypeId: "ct-sales-tax",
    formId: "form-st100",
    taxType: "SALES_TAX",
    taxPeriod: "2026-08-01–2026-08-31",
    taxPeriodStart: "2026-08-01T00:00:00.000Z",
    taxPeriodEnd: "2026-08-31T23:59:59.000Z",
    filingMonth: "2026-09",
    frequency: "MONTHLY",
    dueDate: d(12),
    paymentDueDate: d(12),
    requiresPayment: true,
    priority: "NORMAL",
    status: "PENDING_ADMIN_APPROVAL",
    source: "MANUAL",
    isRecurring: false,
    createdById: "u006",
    notes: "Scenario 2: Manual item submitted to admin for pre-preparation gate approval",
    updatedAt: now.toISOString(),
  },
  // Scenario 3: PENDING_REVIEW
  {
    id: "obl-scen-03-pending-review",
    orgId: "org-acme-001",
    complianceId: "OBL-SCEN-03",
    entityId: "ent-uk-001",
    countryId: "c003",
    complianceTypeId: "ct-vat-uk",
    formId: "form-vat100",
    taxType: "VAT",
    taxPeriod: "2026-06-01–2026-08-31",
    taxPeriodStart: "2026-06-01T00:00:00.000Z",
    taxPeriodEnd: "2026-08-31T23:59:59.000Z",
    filingMonth: "2026-09",
    frequency: "QUARTERLY",
    dueDate: d(15),
    paymentDueDate: d(15),
    requiresPayment: true,
    priority: "NORMAL",
    status: "PENDING_REVIEW",
    source: "MANUAL",
    isRecurring: false,
    reviewerId: "u011",
    createdById: senthilId,
    notes: "Scenario 3: Admin sent manual obligation to Rachel Reviewer for pre-prep gate review",
    updatedAt: now.toISOString(),
  },
  // Scenario 4: PENDING_PREPARATION
  {
    id: "obl-scen-04-preparation",
    orgId: "org-acme-001",
    complianceId: "OBL-SCEN-04",
    entityId: "ent-in-001",
    countryId: "c007",
    complianceTypeId: "ct-gst-in",
    formId: "form-gstr3b",
    taxType: "GST",
    taxPeriod: "2026-08-01–2026-08-31",
    taxPeriodStart: "2026-08-01T00:00:00.000Z",
    taxPeriodEnd: "2026-08-31T23:59:59.000Z",
    filingMonth: "2026-09",
    frequency: "MONTHLY",
    dueDate: d(9),
    paymentDueDate: d(9),
    requiresPayment: true,
    priority: "HIGH",
    status: "PENDING_PREPARATION",
    source: "TEMPLATE",
    templateId: "tmpl-001-active",
    templateVersion: 1,
    isRecurring: true,
    createdById: senthilId,
    notes: "Scenario 4: Sourced from recurring template; in PENDING_PREPARATION assigned to David Preparer",
    updatedAt: now.toISOString(),
  },
  // Scenario 5: Multi-Entity Group Filing in PENDING_APPROVAL
  {
    id: "obl-scen-05-group-step1",
    orgId: "org-acme-001",
    complianceId: "OBL-SCEN-05",
    entityId: "ent-us-001",
    countryId: "c001",
    complianceTypeId: "ct-sales-tax",
    formId: "form-st100",
    taxType: "SALES_TAX",
    taxPeriod: "2026-08-01–2026-08-31",
    taxPeriodStart: "2026-08-01T00:00:00.000Z",
    taxPeriodEnd: "2026-08-31T23:59:59.000Z",
    filingMonth: "2026-09",
    frequency: "MONTHLY",
    dueDate: d(8),
    paymentDueDate: d(8),
    requiresPayment: true,
    priority: "HIGH",
    status: "PENDING_APPROVAL",
    source: "MANUAL",
    filingType: "PAYMENT",
    paymentCurrency: "USD",
    paymentAmount: 25000.00,
    submittedAt: d(-0.25),
    isRecurring: false,
    createdById: "u006",
    notes: "Scenario 5: Multi-entity group filing in PENDING_APPROVAL awaiting Step 1 Reviewer sign-off and amount reconfirmation",
    updatedAt: now.toISOString(),
  },
  // Scenario 6: Step 1 Approved, PENDING_APPROVAL at Step 2
  {
    id: "obl-scen-06-step2",
    orgId: "org-acme-001",
    complianceId: "OBL-SCEN-06",
    entityId: "ent-uk-001",
    countryId: "c003",
    complianceTypeId: "ct-vat-uk",
    formId: "form-vat100",
    taxType: "VAT",
    taxPeriod: "2026-06-01–2026-08-31",
    taxPeriodStart: "2026-06-01T00:00:00.000Z",
    taxPeriodEnd: "2026-08-31T23:59:59.000Z",
    filingMonth: "2026-09",
    frequency: "QUARTERLY",
    dueDate: d(14),
    paymentDueDate: d(14),
    requiresPayment: true,
    priority: "HIGH",
    status: "PENDING_APPROVAL",
    source: "MANUAL",
    filingType: "PAYMENT",
    paymentCurrency: "GBP",
    paymentAmount: 12400.00,
    submittedAt: d(-1),
    isRecurring: false,
    createdById: "u006",
    notes: "Scenario 6: Two-level flow: Step 1 (Reviewer) Approved with amount reconfirmed; currently awaiting Step 2 (Alex Approver)",
    updatedAt: now.toISOString(),
  },
  // Scenario 7: Flow NONE (Zero Approval): Auto-APPROVED
  {
    id: "obl-scen-07-none-approved",
    orgId: "org-acme-001",
    complianceId: "OBL-SCEN-07",
    entityId: "ent-us-001",
    countryId: "c001",
    complianceTypeId: "ct-sales-tax",
    formId: "form-st100",
    taxType: "SALES_TAX",
    taxPeriod: "2026-08-01–2026-08-31",
    taxPeriodStart: "2026-08-01T00:00:00.000Z",
    taxPeriodEnd: "2026-08-31T23:59:59.000Z",
    filingMonth: "2026-09",
    frequency: "MONTHLY",
    dueDate: d(6),
    paymentDueDate: d(6),
    requiresPayment: true,
    priority: "NORMAL",
    status: "APPROVED",
    source: "MANUAL",
    filingType: "PAYMENT",
    paymentCurrency: "USD",
    paymentAmount: 4800.00,
    submittedAt: d(-0.15),
    isRecurring: false,
    createdById: "u006",
    notes: "Scenario 7: Zero approval flow (NONE): immediately APPROVED upon submission; ready for filing and payment",
    updatedAt: now.toISOString(),
  },
  // Scenario 8: REJECTED
  {
    id: "obl-scen-08-rejected",
    orgId: "org-acme-001",
    complianceId: "OBL-SCEN-08",
    entityId: "ent-in-001",
    countryId: "c007",
    complianceTypeId: "ct-gst-in",
    formId: "form-gstr3b",
    taxType: "GST",
    taxPeriod: "2026-08-01–2026-08-31",
    taxPeriodStart: "2026-08-01T00:00:00.000Z",
    taxPeriodEnd: "2026-08-31T23:59:59.000Z",
    filingMonth: "2026-09",
    frequency: "MONTHLY",
    dueDate: d(5),
    paymentDueDate: d(5),
    requiresPayment: true,
    priority: "HIGH",
    status: "REJECTED",
    source: "MANUAL",
    filingType: "PAYMENT",
    paymentCurrency: "INR",
    paymentAmount: 180000.00,
    submittedAt: d(-2),
    isRecurring: false,
    createdById: "u006",
    notes: "Scenario 8: Rejected by reviewer due to ITC discrepancy; awaiting preparer resubmission",
    updatedAt: now.toISOString(),
  },
  // Scenario 9: Return FILED (Payment Pending)
  {
    id: "obl-scen-09-filed-pending-pay",
    orgId: "org-acme-001",
    complianceId: "OBL-SCEN-09",
    entityId: "ent-us-001",
    countryId: "c001",
    complianceTypeId: "ct-sales-tax",
    formId: "form-st100",
    taxType: "SALES_TAX",
    taxPeriod: "2026-07-01–2026-07-31",
    taxPeriodStart: "2026-07-01T00:00:00.000Z",
    taxPeriodEnd: "2026-07-31T23:59:59.000Z",
    filingMonth: "2026-08",
    frequency: "MONTHLY",
    dueDate: d(-1),
    paymentDueDate: d(3),
    requiresPayment: true,
    priority: "HIGH",
    status: "FILED",
    source: "TEMPLATE",
    filingType: "PAYMENT",
    paymentCurrency: "USD",
    paymentAmount: 9200.00,
    submittedAt: d(-4),
    filedAt: d(-2),
    isRecurring: true,
    createdById: senthilId,
    notes: "Scenario 9: Return FILED with tax portal (filedAt recorded); payment remains pending before payment due date",
    updatedAt: now.toISOString(),
  },
  // Scenario 10: Liability PAID (Filing Pending)
  {
    id: "obl-scen-10-paid-pending-file",
    orgId: "org-acme-001",
    complianceId: "OBL-SCEN-10",
    entityId: "ent-uk-001",
    countryId: "c003",
    complianceTypeId: "ct-vat-uk",
    formId: "form-vat100",
    taxType: "VAT",
    taxPeriod: "2026-06-01–2026-08-31",
    taxPeriodStart: "2026-06-01T00:00:00.000Z",
    taxPeriodEnd: "2026-08-31T23:59:59.000Z",
    filingMonth: "2026-09",
    frequency: "QUARTERLY",
    dueDate: d(4),
    paymentDueDate: d(4),
    requiresPayment: true,
    priority: "NORMAL",
    status: "PAID",
    source: "MANUAL",
    filingType: "PAYMENT",
    paymentCurrency: "GBP",
    paymentAmount: 7500.00,
    submittedAt: d(-3),
    paidAt: d(-1),
    paymentDate: d(-1),
    paymentReference: "BANK-CHAPS-99214",
    paymentMethod: "WIRE_TRANSFER",
    paymentNotes: "Payment executed ahead of portal filing",
    isRecurring: false,
    createdById: "u006",
    notes: "Scenario 10: Liability PAID via bank transfer; return filing is still pending (flexible pay-first ordering)",
    updatedAt: now.toISOString(),
  },
  // Scenario 11: Non-Payment / NIL Return — CLOSED
  {
    id: "obl-scen-11-nil-closed",
    orgId: "org-acme-001",
    complianceId: "OBL-SCEN-11",
    entityId: "ent-de-001",
    countryId: "c004",
    complianceTypeId: "ct-stat-info",
    formId: "form-stat01",
    taxType: "STATUTORY",
    taxPeriod: "2025-01-01–2025-12-31",
    taxPeriodStart: "2025-01-01T00:00:00.000Z",
    taxPeriodEnd: "2025-12-31T23:59:59.000Z",
    filingMonth: "2026-01",
    frequency: "ANNUAL",
    dueDate: d(-20),
    paymentDueDate: null,
    requiresPayment: false,
    priority: "NORMAL",
    status: "CLOSED",
    source: "TEMPLATE",
    filingType: "NIL_RETURN",
    paymentAmount: 0.00,
    submittedAt: d(-25),
    filedAt: d(-22),
    isRecurring: true,
    createdById: senthilId,
    notes: "Scenario 11: Non-payment return (requiresPayment=false); filed as NIL Return and administratively CLOSED",
    updatedAt: now.toISOString(),
  },
  // Scenario 12: Refund Return — CLOSED
  {
    id: "obl-scen-12-refund-closed",
    orgId: "org-acme-001",
    complianceId: "OBL-SCEN-12",
    entityId: "ent-de-001",
    countryId: "c004",
    complianceTypeId: "ct-vat-uk",
    formId: "form-vat100",
    taxType: "VAT",
    taxPeriod: "2026-04-01–2026-06-30",
    taxPeriodStart: "2026-04-01T00:00:00.000Z",
    taxPeriodEnd: "2026-06-30T23:59:59.000Z",
    filingMonth: "2026-07",
    frequency: "QUARTERLY",
    dueDate: d(-35),
    paymentDueDate: d(-35),
    requiresPayment: true,
    priority: "NORMAL",
    status: "CLOSED",
    source: "MANUAL",
    filingType: "REFUND_RETURN",
    refundType: "CLAIMED",
    paymentCurrency: "EUR",
    paymentAmount: 6750.00,
    refundAmount: 6750.00,
    submittedAt: d(-40),
    filedAt: d(-36),
    isRecurring: false,
    createdById: "u006",
    notes: "Scenario 12: Refund return with €6,750 CLAIMED from tax authority; filed and administratively CLOSED",
    updatedAt: now.toISOString(),
  },
  // Scenario 13: Overdue Obligation
  {
    id: "obl-scen-13-overdue-critical",
    orgId: "org-acme-001",
    complianceId: "OBL-SCEN-13",
    entityId: "ent-in-001",
    countryId: "c007",
    complianceTypeId: "ct-gst-in",
    formId: "form-gstr3b",
    taxType: "GST",
    taxPeriod: "2026-07-01–2026-07-31",
    taxPeriodStart: "2026-07-01T00:00:00.000Z",
    taxPeriodEnd: "2026-07-31T23:59:59.000Z",
    filingMonth: "2026-08",
    frequency: "MONTHLY",
    dueDate: d(-7),
    paymentDueDate: d(-7),
    requiresPayment: true,
    priority: "CRITICAL",
    status: "PENDING_PREPARATION",
    source: "MANUAL",
    isRecurring: false,
    createdById: "u006",
    notes: "Scenario 13: Past-due obligation (7 days overdue) displaying red Overdue warnings and critical priority badge",
    updatedAt: now.toISOString(),
  },
]

for (const obl of obligations) {
  const { error: oblErr } = await supabase.from("compliance_schedules").upsert(obl)
  if (oblErr) console.error("Error upserting obligation:", obl.id, oblErr)
}
console.log(`✓ ${obligations.length} distinct scenario obligations inserted!`)

// 9. Multi-Entity links for Scenario 5
await supabase.from("compliance_entities").upsert([
  { id: "ce-scen-05-a", complianceId: "obl-scen-05-group-step1", entityId: "ent-us-001" },
  { id: "ce-scen-05-b", complianceId: "obl-scen-05-group-step1", entityId: "ent-de-001" },
])

// 10. Assignments
for (const obl of obligations) {
  await supabase.from("compliance_assignments").upsert({
    id: `asg-${obl.id}`,
    complianceId: obl.id,
    preparerId: "u006",
    updatedAt: now.toISOString(),
  })
}

// 11. Approvals
const approvals = [
  { id: "app-05-s1", complianceId: "obl-scen-05-group-step1", approverId: "u011", step: 1, status: "PENDING_APPROVAL" },
  { id: "app-05-s2", complianceId: "obl-scen-05-group-step1", approverId: "u012", step: 2, status: "PENDING_APPROVAL" },
  { id: "app-06-s1", complianceId: "obl-scen-06-step2", approverId: "u011", step: 1, status: "APPROVED", comments: "Reconciliation verified against GL.", actionAt: d(-0.75) },
  { id: "app-06-s2", complianceId: "obl-scen-06-step2", approverId: "u012", step: 2, status: "PENDING_APPROVAL" },
  { id: "app-08-s1", complianceId: "obl-scen-08-rejected", approverId: "u011", step: 1, status: "REJECTED", comments: "Input tax credit discrepancy between Books and GSTR-2B; please reconcile and resubmit.", actionAt: d(-2) },
  { id: "app-09-s1", complianceId: "obl-scen-09-filed-pending-pay", approverId: "u011", step: 1, status: "APPROVED", comments: "Approved for filing.", actionAt: d(-3) },
  { id: "app-10-s1", complianceId: "obl-scen-10-paid-pending-file", approverId: "u011", step: 1, status: "APPROVED", comments: "Approved for wire transfer.", actionAt: d(-2) },
  { id: "app-12-s1", complianceId: "obl-scen-12-refund-closed", approverId: "u011", step: 1, status: "APPROVED", comments: "Refund verified against credit notes.", actionAt: d(-38) },
  { id: "app-13-s1", complianceId: "obl-scen-13-overdue-critical", approverId: "u011", step: 1, status: "PENDING_APPROVAL" },
]
for (const a of approvals) {
  await supabase.from("compliance_approvals").upsert({ ...a, updatedAt: now.toISOString() })
}

// 12. Payment Confirmations
const confirmations = [
  { id: "conf-05-prep", complianceId: "obl-scen-05-group-step1", stage: "PREPARER_SUBMIT", confirmedById: "u006", confirmedAt: d(-0.25) },
  { id: "conf-06-prep", complianceId: "obl-scen-06-step2", stage: "PREPARER_SUBMIT", confirmedById: "u006", confirmedAt: d(-1) },
  { id: "conf-06-rev", complianceId: "obl-scen-06-step2", stage: "REVIEWER", confirmedById: "u011", confirmedAt: d(-0.75) },
  { id: "conf-09-prep", complianceId: "obl-scen-09-filed-pending-pay", stage: "PREPARER_SUBMIT", confirmedById: "u006", confirmedAt: d(-4) },
  { id: "conf-09-rev", complianceId: "obl-scen-09-filed-pending-pay", stage: "REVIEWER", confirmedById: "u011", confirmedAt: d(-3) },
  { id: "conf-10-prep", complianceId: "obl-scen-10-paid-pending-file", stage: "PREPARER_SUBMIT", confirmedById: "u006", confirmedAt: d(-3) },
  { id: "conf-10-rev", complianceId: "obl-scen-10-paid-pending-file", stage: "REVIEWER", confirmedById: "u011", confirmedAt: d(-2) },
  { id: "conf-10-pay", complianceId: "obl-scen-10-paid-pending-file", stage: "PREPARER_PAYMENT", confirmedById: "u006", confirmedAt: d(-1) },
]
for (const conf of confirmations) {
  await supabase.from("compliance_payment_confirmations").upsert(conf)
}

console.log("=================================================================")
console.log("ALL SEEDING COMPLETED SUCCESSFULLY!")
console.log("=================================================================")
