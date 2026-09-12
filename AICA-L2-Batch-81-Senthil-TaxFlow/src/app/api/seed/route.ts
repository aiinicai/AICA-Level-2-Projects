import { supabaseAdmin } from "@/lib/supabase"
import bcrypt from "bcryptjs"
import { NextResponse } from "next/server"

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const force = searchParams.get("force") === "true"

    const { data: existingSchedules } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id")
      .limit(1)

    if (!force && existingSchedules && existingSchedules.length > 0) {
      return NextResponse.json({
        message: "Database already contains obligations test data. Pass ?force=true to reseed.",
        seeded: false,
      })
    }

    // 1. Organization
    await supabaseAdmin.from("organizations").upsert({
      id: "org-acme-001",
      name: "Acme Global Indirect Tax Org",
      slug: "acme-tax",
      createdById: "usr-admin-001",
      updatedAt: new Date().toISOString(),
    })

    // 2. Users (including Senthil as Administrator)
    const hashedPassword = bcrypt.hashSync("password123", 10)
    const users = [
      { id: "usr-senthil-001", email: "senthil@lucid-exp.com", username: "senthil", password: hashedPassword, name: "Senthil", role: "ADMINISTRATOR", roles: ["ADMINISTRATOR"], department: "Executive Leadership", employeeId: "EMP-000", isActive: true },
      { id: "usr-admin-001", email: "admin@taxflow.com", username: "admin", password: hashedPassword, name: "Alice Admin", role: "ADMINISTRATOR", roles: ["ADMINISTRATOR"], department: "Tax & Compliance", employeeId: "EMP-001", isActive: true },
      { id: "usr-manager-001", email: "manager@taxflow.com", username: "manager", password: hashedPassword, name: "Bob Manager", role: "MANAGER", roles: ["MANAGER"], department: "Finance Leadership", employeeId: "EMP-002", isActive: true },
      { id: "usr-preparer-001", email: "preparer@taxflow.com", username: "preparer", password: hashedPassword, name: "David Preparer", role: "PREPARER", roles: ["PREPARER"], department: "Tax Operations", employeeId: "EMP-003", isActive: true },
      { id: "usr-reviewer-001", email: "reviewer@taxflow.com", username: "reviewer", password: hashedPassword, name: "Rachel Reviewer", role: "REVIEWER", roles: ["REVIEWER"], department: "Tax Quality", employeeId: "EMP-004", isActive: true },
      { id: "usr-approver-001", email: "approver@taxflow.com", username: "approver", password: hashedPassword, name: "Alex Approver", role: "APPROVER", roles: ["APPROVER"], department: "Finance Control", employeeId: "EMP-005", isActive: true },
    ]

    for (const u of users) {
      await supabaseAdmin.from("users").upsert({
        ...u,
        updatedAt: new Date().toISOString(),
      })
    }

    // Also check if senthil was previously auto-provisioned with a different UUID
    const { data: existingSenthil } = await supabaseAdmin
      .from("users")
      .select("id")
      .ilike("email", "senthil@lucid-exp.com")
      .maybeSingle()

    if (existingSenthil?.id && existingSenthil.id !== "usr-senthil-001") {
      await supabaseAdmin
        .from("users")
        .update({ role: "ADMINISTRATOR", roles: ["ADMINISTRATOR"], updatedAt: new Date().toISOString() })
        .eq("id", existingSenthil.id)

      await supabaseAdmin.from("organization_members").upsert({
        id: `mem-senthil-${existingSenthil.id}`,
        orgId: "org-acme-001",
        userId: existingSenthil.id,
        roles: ["ADMINISTRATOR"],
        updatedAt: new Date().toISOString(),
      })
    }

    // 3. Organization Memberships
    const memberships = [
      { id: "mem-senthil-001", orgId: "org-acme-001", userId: "usr-senthil-001", roles: ["ADMINISTRATOR"] },
      { id: "mem-001", orgId: "org-acme-001", userId: "usr-admin-001", roles: ["ADMINISTRATOR"] },
      { id: "mem-002", orgId: "org-acme-001", userId: "usr-manager-001", roles: ["MANAGER"] },
      { id: "mem-003", orgId: "org-acme-001", userId: "usr-preparer-001", roles: ["PREPARER"] },
      { id: "mem-004", orgId: "org-acme-001", userId: "usr-reviewer-001", roles: ["REVIEWER"] },
      { id: "mem-005", orgId: "org-acme-001", userId: "usr-approver-001", roles: ["APPROVER"] },
    ]

    for (const m of memberships) {
      await supabaseAdmin.from("organization_members").upsert({
        ...m,
        updatedAt: new Date().toISOString(),
      })
    }

    // 4. Countries
    const countries = [
      { id: "ctry-us", name: "United States", code: "US", region: "North America" },
      { id: "ctry-gb", name: "United Kingdom", code: "GB", region: "Europe" },
      { id: "ctry-in", name: "India", code: "IN", region: "Asia" },
      { id: "ctry-de", name: "Germany", code: "DE", region: "Europe" },
    ]

    for (const c of countries) {
      await supabaseAdmin.from("countries").upsert({
        ...c,
        updatedAt: new Date().toISOString(),
      })
    }

    // 5. Currencies
    const currencies = [
      { id: "curr-usd", orgId: "org-acme-001", code: "USD", name: "US Dollar", symbol: "$", decimals: 2, isBase: true },
      { id: "curr-gbp", orgId: "org-acme-001", code: "GBP", name: "British Pound", symbol: "£", decimals: 2, isBase: false },
      { id: "curr-eur", orgId: "org-acme-001", code: "EUR", name: "Euro", symbol: "€", decimals: 2, isBase: false },
      { id: "curr-inr", orgId: "org-acme-001", code: "INR", name: "Indian Rupee", symbol: "₹", decimals: 2, isBase: false },
    ]

    for (const cur of currencies) {
      await supabaseAdmin.from("currencies").upsert({
        ...cur,
        updatedAt: new Date().toISOString(),
      })
    }

    // 6. Legal Entities
    const entities = [
      { id: "ent-us-001", orgId: "org-acme-001", entityNumber: "ENT-US-001", entityName: "Acme US Holdings Inc.", countryId: "ctry-us", businessUnit: "North America Operations", status: "ACTIVE", taxRegistrationNumber: "TX-US-99214", currency: "USD", approvalFlow: "ONE_LEVEL" },
      { id: "ent-uk-001", orgId: "org-acme-001", entityNumber: "ENT-UK-001", entityName: "Acme UK Operations Ltd", countryId: "ctry-gb", businessUnit: "EMEA Corporate", status: "ACTIVE", taxRegistrationNumber: "GB-VAT-78219", currency: "GBP", approvalFlow: "TWO_LEVEL" },
      { id: "ent-in-001", orgId: "org-acme-001", entityNumber: "ENT-IN-001", entityName: "Acme India Tech Pvt Ltd", countryId: "ctry-in", businessUnit: "APAC Tech Services", status: "ACTIVE", taxRegistrationNumber: "27AABCU9603R1ZM", currency: "INR", approvalFlow: "ONE_LEVEL" },
      { id: "ent-de-001", orgId: "org-acme-001", entityNumber: "ENT-DE-001", entityName: "Acme Germany GmbH", countryId: "ctry-de", businessUnit: "EU Distribution", status: "ACTIVE", taxRegistrationNumber: "DE-302918234", currency: "EUR", approvalFlow: "ONE_LEVEL" },
    ]

    for (const e of entities) {
      await supabaseAdmin.from("legal_entities").upsert({
        ...e,
        updatedAt: new Date().toISOString(),
      })
    }

    // 7. Compliance Types
    const complianceTypes = [
      { id: "ct-sales-tax", orgId: "org-acme-001", name: "US State Sales Tax", taxType: "SALES_TAX", frequency: "MONTHLY", dueDateRule: "20th of subsequent month", description: "Monthly state sales & use tax filing", defaultPreparationDays: 5, defaultApprovalDays: 3, countryId: "ctry-us" },
      { id: "ct-vat-uk", orgId: "org-acme-001", name: "UK Quarterly VAT", taxType: "VAT", frequency: "QUARTERLY", dueDateRule: "Last day of following month", description: "Standard quarterly UK VAT return", defaultPreparationDays: 10, defaultApprovalDays: 5, countryId: "ctry-gb" },
      { id: "ct-gst-in", orgId: "org-acme-001", name: "India GST Monthly", taxType: "GST", frequency: "MONTHLY", dueDateRule: "20th of subsequent month", description: "Monthly outward & summary GST filing", defaultPreparationDays: 7, defaultApprovalDays: 3, countryId: "ctry-in" },
      { id: "ct-stat-info", orgId: "org-acme-001", name: "Annual Corporate Info", taxType: "STATUTORY", frequency: "ANNUAL", dueDateRule: "30 days after fiscal year end", description: "Annual statutory information filing", defaultPreparationDays: 15, defaultApprovalDays: 5, countryId: "ctry-de" },
    ]

    for (const ct of complianceTypes) {
      await supabaseAdmin.from("compliance_types").upsert({
        ...ct,
        updatedAt: new Date().toISOString(),
      })
    }

    // 8. Form Master
    const forms = [
      { id: "form-st100", orgId: "org-acme-001", formNumber: "ST-100", formName: "Form ST-100 Sales Tax Return", complianceTypeId: "ct-sales-tax", countryId: "ctry-us", taxType: "SALES_TAX", description: "Standard State Sales Tax Return", approvalFlow: "ONE_LEVEL", requiresPayment: true },
      { id: "form-vat100", orgId: "org-acme-001", formNumber: "VAT-100", formName: "Form VAT-100 Value Added Tax Return", complianceTypeId: "ct-vat-uk", countryId: "ctry-gb", taxType: "VAT", description: "UK Standard Quarterly VAT Return", approvalFlow: "TWO_LEVEL", requiresPayment: true },
      { id: "form-gstr3b", orgId: "org-acme-001", formNumber: "GSTR-3B", formName: "Form GSTR-3B Summary GST Return", complianceTypeId: "ct-gst-in", countryId: "ctry-in", taxType: "GST", description: "India Monthly Summary GST Return", approvalFlow: "ONE_LEVEL", requiresPayment: true },
      { id: "form-stat01", orgId: "org-acme-001", formNumber: "STAT-INFO", formName: "Form STAT-01 Annual Information Return", complianceTypeId: "ct-stat-info", countryId: "ctry-de", taxType: "STATUTORY", description: "Statutory Information Return (Non-Payment)", approvalFlow: "NONE", requiresPayment: false },
    ]

    for (const f of forms) {
      await supabaseAdmin.from("form_master").upsert({
        ...f,
        updatedAt: new Date().toISOString(),
      })
    }

    // 9. Recurring Compliance Templates
    await supabaseAdmin.from("compliance_templates").upsert([
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
        countryId: "ctry-in",
        filingEntityId: "ent-in-001",
        frequency: "MONTHLY",
        dueDaysAfterPeriodEnd: 20,
        paymentDueDaysAfterPeriodEnd: 20,
        priority: "HIGH",
        approvalFlow: "ONE_LEVEL",
        isRecurring: true,
        notes: "Standing recurring template for India monthly GSTR-3B obligations",
        preparerId: "usr-preparer-001",
        approverId: "usr-reviewer-001",
        createdById: "usr-admin-001",
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
        countryId: "ctry-gb",
        filingEntityId: "ent-uk-001",
        frequency: "QUARTERLY",
        dueDaysAfterPeriodEnd: 30,
        paymentDueDaysAfterPeriodEnd: 30,
        priority: "NORMAL",
        approvalFlow: "TWO_LEVEL",
        isRecurring: true,
        notes: "Draft recurring template for UK Quarterly VAT return",
        preparerId: "usr-preparer-001",
        approverId: "usr-approver-001",
        createdById: "usr-admin-001",
        updatedAt: new Date().toISOString(),
      },
    ])

    await supabaseAdmin.from("compliance_template_entities").upsert([
      { id: "te-001", templateId: "tmpl-001-active", entityId: "ent-in-001" },
      { id: "te-002", templateId: "tmpl-002-draft", entityId: "ent-uk-001" },
    ])

    // 10. Obligations Items (1 OF EACH SCENARIO)
    const now = new Date()
    const d = (offsetDays: number) => new Date(now.getTime() + offsetDays * 86400000).toISOString()

    const obligations = [
      // Scenario 1: DRAFT
      {
        id: "obl-scen-01-draft",
        orgId: "org-acme-001",
        complianceId: "OBL-SCEN-01",
        entityId: "ent-us-001",
        countryId: "ctry-us",
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
        approvalFlow: "ONE_LEVEL",
        createdById: "usr-preparer-001",
        notes: "Scenario 1: Ad-hoc obligation in initial DRAFT state awaiting submission to admin",
        updatedAt: now.toISOString(),
      },
      // Scenario 2: PENDING_ADMIN_APPROVAL
      {
        id: "obl-scen-02-pending-admin",
        orgId: "org-acme-001",
        complianceId: "OBL-SCEN-02",
        entityId: "ent-us-001",
        countryId: "ctry-us",
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
        approvalFlow: "ONE_LEVEL",
        createdById: "usr-preparer-001",
        notes: "Scenario 2: Manual item submitted to admin for pre-preparation gate approval",
        updatedAt: now.toISOString(),
      },
      // Scenario 3: PENDING_REVIEW
      {
        id: "obl-scen-03-pending-review",
        orgId: "org-acme-001",
        complianceId: "OBL-SCEN-03",
        entityId: "ent-uk-001",
        countryId: "ctry-gb",
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
        approvalFlow: "TWO_LEVEL",
        reviewerId: "usr-reviewer-001",
        createdById: "usr-admin-001",
        notes: "Scenario 3: Admin sent manual obligation to Rachel Reviewer for pre-prep gate review",
        updatedAt: now.toISOString(),
      },
      // Scenario 4: PENDING_PREPARATION
      {
        id: "obl-scen-04-preparation",
        orgId: "org-acme-001",
        complianceId: "OBL-SCEN-04",
        entityId: "ent-in-001",
        countryId: "ctry-in",
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
        approvalFlow: "ONE_LEVEL",
        createdById: "usr-admin-001",
        notes: "Scenario 4: Sourced from recurring template; in PENDING_PREPARATION assigned to David Preparer",
        updatedAt: now.toISOString(),
      },
      // Scenario 5: Multi-Entity Group Filing in PENDING_APPROVAL (Step 1 Reviewer)
      {
        id: "obl-scen-05-group-step1",
        orgId: "org-acme-001",
        complianceId: "OBL-SCEN-05",
        entityId: "ent-us-001",
        countryId: "ctry-us",
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
        approvalFlow: "TWO_LEVEL",
        createdById: "usr-preparer-001",
        notes: "Scenario 5: Multi-entity group filing in PENDING_APPROVAL awaiting Step 1 Reviewer sign-off and amount reconfirmation",
        updatedAt: now.toISOString(),
      },
      // Scenario 6: Step 1 Approved, PENDING_APPROVAL at Step 2 (Approver)
      {
        id: "obl-scen-06-step2",
        orgId: "org-acme-001",
        complianceId: "OBL-SCEN-06",
        entityId: "ent-uk-001",
        countryId: "ctry-gb",
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
        approvalFlow: "TWO_LEVEL",
        createdById: "usr-preparer-001",
        notes: "Scenario 6: Two-level flow: Step 1 (Reviewer) Approved with amount reconfirmed; currently awaiting Step 2 (Alex Approver)",
        updatedAt: now.toISOString(),
      },
      // Scenario 7: Zero Approval Flow (NONE): Auto-APPROVED
      {
        id: "obl-scen-07-none-approved",
        orgId: "org-acme-001",
        complianceId: "OBL-SCEN-07",
        entityId: "ent-us-001",
        countryId: "ctry-us",
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
        approvalFlow: "NONE",
        createdById: "usr-preparer-001",
        notes: "Scenario 7: Zero approval flow (NONE): immediately APPROVED upon submission; ready for filing and payment",
        updatedAt: now.toISOString(),
      },
      // Scenario 8: REJECTED
      {
        id: "obl-scen-08-rejected",
        orgId: "org-acme-001",
        complianceId: "OBL-SCEN-08",
        entityId: "ent-in-001",
        countryId: "ctry-in",
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
        approvalFlow: "ONE_LEVEL",
        createdById: "usr-preparer-001",
        notes: "Scenario 8: Rejected by reviewer due to ITC discrepancy; awaiting preparer resubmission",
        updatedAt: now.toISOString(),
      },
      // Scenario 9: Return FILED (Payment Pending)
      {
        id: "obl-scen-09-filed-pending-pay",
        orgId: "org-acme-001",
        complianceId: "OBL-SCEN-09",
        entityId: "ent-us-001",
        countryId: "ctry-us",
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
        approvalFlow: "ONE_LEVEL",
        createdById: "usr-admin-001",
        notes: "Scenario 9: Return FILED with tax portal (filedAt recorded); payment remains pending before payment due date",
        updatedAt: now.toISOString(),
      },
      // Scenario 10: Liability PAID (Filing Pending)
      {
        id: "obl-scen-10-paid-pending-file",
        orgId: "org-acme-001",
        complianceId: "OBL-SCEN-10",
        entityId: "ent-uk-001",
        countryId: "ctry-gb",
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
        approvalFlow: "ONE_LEVEL",
        createdById: "usr-preparer-001",
        notes: "Scenario 10: Liability PAID via bank transfer; return filing is still pending (flexible pay-first ordering)",
        updatedAt: now.toISOString(),
      },
      // Scenario 11: Non-Payment / NIL Return — CLOSED
      {
        id: "obl-scen-11-nil-closed",
        orgId: "org-acme-001",
        complianceId: "OBL-SCEN-11",
        entityId: "ent-de-001",
        countryId: "ctry-de",
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
        approvalFlow: "NONE",
        createdById: "usr-admin-001",
        notes: "Scenario 11: Non-payment return (requiresPayment=false); filed as NIL Return and administratively CLOSED",
        updatedAt: now.toISOString(),
      },
      // Scenario 12: Refund Return — CLOSED
      {
        id: "obl-scen-12-refund-closed",
        orgId: "org-acme-001",
        complianceId: "OBL-SCEN-12",
        entityId: "ent-de-001",
        countryId: "ctry-de",
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
        approvalFlow: "ONE_LEVEL",
        createdById: "usr-preparer-001",
        notes: "Scenario 12: Refund return with €6,750 CLAIMED from tax authority; filed and administratively CLOSED",
        updatedAt: now.toISOString(),
      },
      // Scenario 13: Overdue Obligation (CRITICAL Priority)
      {
        id: "obl-scen-13-overdue-critical",
        orgId: "org-acme-001",
        complianceId: "OBL-SCEN-13",
        entityId: "ent-in-001",
        countryId: "ctry-in",
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
        approvalFlow: "ONE_LEVEL",
        createdById: "usr-preparer-001",
        notes: "Scenario 13: Past-due obligation (7 days overdue) displaying red Overdue warnings and critical priority badge",
        updatedAt: now.toISOString(),
      },
    ]

    for (const obl of obligations) {
      await supabaseAdmin.from("compliance_schedules").upsert(obl as any)
    }

    // 11. Multi-Entity links for Scenario 5
    await supabaseAdmin.from("compliance_entities").upsert([
      { id: "ce-scen-05-a", complianceId: "obl-scen-05-group-step1", entityId: "ent-us-001" },
      { id: "ce-scen-05-b", complianceId: "obl-scen-05-group-step1", entityId: "ent-de-001" },
    ])

    // 12. Assignments (David Preparer assigned)
    for (const obl of obligations) {
      await supabaseAdmin.from("compliance_assignments").upsert({
        id: `asg-${obl.id}`,
        complianceId: obl.id,
        preparerId: "usr-preparer-001",
        updatedAt: now.toISOString(),
      })
    }

    // 13. Approvals
    const approvals = [
      // Scenario 05: Two-level, Step 1 pending
      { id: "app-05-s1", complianceId: "obl-scen-05-group-step1", approverId: "usr-reviewer-001", step: 1, status: "PENDING_APPROVAL" },
      { id: "app-05-s2", complianceId: "obl-scen-05-group-step1", approverId: "usr-approver-001", step: 2, status: "PENDING_APPROVAL" },
      // Scenario 06: Two-level, Step 1 approved, Step 2 pending
      { id: "app-06-s1", complianceId: "obl-scen-06-step2", approverId: "usr-reviewer-001", step: 1, status: "APPROVED", comments: "Reconciliation verified against GL.", actionAt: d(-0.75) },
      { id: "app-06-s2", complianceId: "obl-scen-06-step2", approverId: "usr-approver-001", step: 2, status: "PENDING_APPROVAL" },
      // Scenario 08: Rejected
      { id: "app-08-s1", complianceId: "obl-scen-08-rejected", approverId: "usr-reviewer-001", step: 1, status: "REJECTED", comments: "Input tax credit discrepancy between Books and GSTR-2B; please reconcile and resubmit.", actionAt: d(-2) },
      // Scenario 09: Approved
      { id: "app-09-s1", complianceId: "obl-scen-09-filed-pending-pay", approverId: "usr-reviewer-001", step: 1, status: "APPROVED", comments: "Approved for filing.", actionAt: d(-3) },
      // Scenario 10: Approved
      { id: "app-10-s1", complianceId: "obl-scen-10-paid-pending-file", approverId: "usr-reviewer-001", step: 1, status: "APPROVED", comments: "Approved for wire transfer.", actionAt: d(-2) },
      // Scenario 12: Approved
      { id: "app-12-s1", complianceId: "obl-scen-12-refund-closed", approverId: "usr-reviewer-001", step: 1, status: "APPROVED", comments: "Refund verified against credit notes.", actionAt: d(-38) },
      // Scenario 13: Pending
      { id: "app-13-s1", complianceId: "obl-scen-13-overdue-critical", approverId: "usr-reviewer-001", step: 1, status: "PENDING_APPROVAL" },
    ]

    for (const a of approvals) {
      await supabaseAdmin.from("compliance_approvals").upsert({
        ...a,
        updatedAt: now.toISOString(),
      })
    }

    // 14. Payment Confirmations
    const confirmations = [
      { id: "conf-05-prep", complianceId: "obl-scen-05-group-step1", stage: "PREPARER_SUBMIT", confirmedById: "usr-preparer-001", confirmedAt: d(-0.25) },
      { id: "conf-06-prep", complianceId: "obl-scen-06-step2", stage: "PREPARER_SUBMIT", confirmedById: "usr-preparer-001", confirmedAt: d(-1) },
      { id: "conf-06-rev", complianceId: "obl-scen-06-step2", stage: "REVIEWER", confirmedById: "usr-reviewer-001", confirmedAt: d(-0.75) },
      { id: "conf-09-prep", complianceId: "obl-scen-09-filed-pending-pay", stage: "PREPARER_SUBMIT", confirmedById: "usr-preparer-001", confirmedAt: d(-4) },
      { id: "conf-09-rev", complianceId: "obl-scen-09-filed-pending-pay", stage: "REVIEWER", confirmedById: "usr-reviewer-001", confirmedAt: d(-3) },
      { id: "conf-10-prep", complianceId: "obl-scen-10-paid-pending-file", stage: "PREPARER_SUBMIT", confirmedById: "usr-preparer-001", confirmedAt: d(-3) },
      { id: "conf-10-rev", complianceId: "obl-scen-10-paid-pending-file", stage: "REVIEWER", confirmedById: "usr-reviewer-001", confirmedAt: d(-2) },
      { id: "conf-10-pay", complianceId: "obl-scen-10-paid-pending-file", stage: "PREPARER_PAYMENT", confirmedById: "usr-preparer-001", confirmedAt: d(-1) },
    ]

    for (const conf of confirmations) {
      await supabaseAdmin.from("compliance_payment_confirmations").upsert(conf)
    }

    return NextResponse.json({
      message: "Successfully seeded 1 of each scenario of obligations test data.",
      scenariosCount: obligations.length,
      organization: "Acme Global Indirect Tax Org (acme-tax)",
      usersCount: users.length,
      templatesCount: 2,
    })
  } catch (error) {
    console.error("GET /api/seed error:", error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
