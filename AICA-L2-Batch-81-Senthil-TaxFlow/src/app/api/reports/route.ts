import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { NextResponse } from "next/server"
import ExcelJS from "exceljs"
import { stringify } from "csv-stringify/sync"
import jsPDF from "jspdf"
import autoTable from "jspdf-autotable"
import { fetchExchangeRatesForDate } from "@/lib/exchange-rates"
import {
  formatDate,
  dayDiff,
  getFilingTimeliness,
  getPaymentTimeliness,
  getPaymentUrgency,
} from "@/lib/reports-utils"

const REPORT_TYPES = [
  "compliance-register",
  "pending-compliance",
  "overdue",
  "treasury-forecast",
  "statutory-audit-pack",
  "employee-productivity",
  "approval-tat",
  "preparation-tat",
  "country-compliance",
  "entity-compliance",
  "audit-trail",
  "rejected-compliance",
  "compliance-source",
  "monthly-summary",
  "quarterly-summary",
  "yearly-summary",
] as const

type ReportType = (typeof REPORT_TYPES)[number]
type ExportFormat = "excel" | "csv" | "pdf"

interface ReportColumn {
  header: string
  key: string
  width: number
  includeInPdf?: boolean
}

interface ReportDataset {
  title: string
  columns: ReportColumn[]
  rows: Record<string, unknown>[]
  landscape?: boolean
}

function getDateRangeFilter(filters: Record<string, string>) {
  const dateFrom = filters.dateFrom ? new Date(filters.dateFrom) : undefined
  const dateTo = filters.dateTo ? new Date(filters.dateTo) : undefined
  return { dateFrom, dateTo }
}

const complianceSelect = `
  *,
  entity:legal_entities(id, entityName, entityNumber, currency, taxRegistrationNumber),
  country:countries(id, name, code, region, currency),
  complianceType:compliance_types(id, name, taxType),
  form:form_master(id, formNumber, formName),
  assignments:compliance_assignments(*, preparer:users(id, name, email)),
  approvals:compliance_approvals(*, approver:users(id, name, email))
`

interface ComplianceBaseRow {
  id: string
  complianceId: string
  orgId: string
  entity: { id?: string; entityName: string; entityNumber: string | null; currency: string | null; taxRegistrationNumber?: string | null } | null
  country: { id?: string; name: string; code: string | null; region?: string | null; currency?: string | null } | null
  complianceType: { id?: string; name: string; taxType: string | null } | null
  form: { id?: string; formNumber: string; formName: string } | null
  taxPeriod: string | null
  frequency: string | null
  dueDate: string | null
  paymentDueDate: string | null
  requiresPayment: boolean | null
  filedAt: string | null
  paymentDate: string | null
  paymentAmount: number | string | null
  refundAmount: number | string | null
  paymentReference: string | null
  paymentMethod: string | null
  paymentNotes: string | null
  notes: string | null
  status: string | null
  priority: string | null
  submittedAt: string | null
  source: string | null
  filingType: string | null
  refundType: string | null
  createdAt?: string | null
  updatedAt?: string | null
  assignments: { preparer: { id: string; name: string; email?: string } }[] | null
  approvals: { approver: { id: string; name: string; email?: string }; step?: number; status?: string; updatedAt?: string }[] | null
}

interface ComputedExportFields {
  _currency?: string | null
  _paymentUSD?: number | null
  _refundUSD?: number | null
}

type ComplianceRow = ComplianceBaseRow & ComputedExportFields

const ratesCache = new Map<string, Record<string, number>>()

async function getCachedRatesForDate(dateStr: string): Promise<Record<string, number>> {
  const d = new Date(dateStr)
  const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`
  if (ratesCache.has(key)) {
    return ratesCache.get(key)!
  }
  const rates = await fetchExchangeRatesForDate(dateStr)
  ratesCache.set(key, rates)
  return rates
}

async function fetchComplianceRegister(filters: Record<string, string>, orgId: string | null): Promise<ComplianceRow[]> {
  let query = supabaseAdmin
    .from("compliance_schedules")
    .select(complianceSelect)

  if (orgId) {
    query = query.eq("orgId", orgId)
  }

  if (filters.countryId && filters.countryId !== "all") query = query.eq("countryId", filters.countryId)
  if (filters.entityId && filters.entityId !== "all") query = query.eq("entityId", filters.entityId)
  if (filters.status && filters.status !== "all") query = query.eq("status", filters.status)
  if (filters.priority && filters.priority !== "all") query = query.eq("priority", filters.priority)
  if (filters.complianceTypeId && filters.complianceTypeId !== "all") query = query.eq("complianceTypeId", filters.complianceTypeId)
  if (filters.preparerId) query = query.eq("compliance_assignments.preparerId", filters.preparerId)

  const { dateFrom, dateTo } = getDateRangeFilter(filters)
  if (dateFrom) query = query.gte("dueDate", dateFrom.toISOString())
  if (dateTo) query = query.lte("dueDate", dateTo.toISOString())

  query = query.order("dueDate", { ascending: true })

  const { data, error } = await query
  if (error) throw error

  const rows = (data || []) as ComplianceRow[]

  for (const row of rows) {
    const currency = row.entity?.currency || row.country?.currency || "USD"
    row._currency = currency
    row._paymentUSD = null
    row._refundUSD = null

    const refDate = row.filedAt || row.submittedAt || row.dueDate || new Date().toISOString()

    if (currency !== "USD" && row.paymentAmount) {
      const rates = await getCachedRatesForDate(refDate)
      const rate = rates[currency]
      if (rate) {
        row._paymentUSD = Number(row.paymentAmount) / rate
      }
    } else if (currency === "USD") {
      row._paymentUSD = row.paymentAmount ? Number(row.paymentAmount) : null
    }

    if (currency !== "USD" && row.refundAmount) {
      const rates = await getCachedRatesForDate(refDate)
      const rate = rates[currency]
      if (rate) {
        row._refundUSD = Number(row.refundAmount) / rate
      }
    } else if (currency === "USD") {
      row._refundUSD = row.refundAmount ? Number(row.refundAmount) : null
    }
  }

  return rows
}

async function buildComplianceRegisterReport(
  type: "compliance-register" | "pending-compliance" | "overdue" | "rejected-compliance",
  filters: Record<string, string>,
  orgId: string | null
): Promise<ReportDataset> {
  const allRows = await fetchComplianceRegister(filters, orgId)

  let rows = allRows
  if (type === "pending-compliance") {
    rows = allRows.filter((r) => !["FILED", "PAID", "CLOSED", "REJECTED"].includes(r.status || ""))
  } else if (type === "overdue") {
    const today = new Date()
    rows = allRows.filter(
      (r) =>
        !["FILED", "PAID", "CLOSED"].includes(r.status || "") &&
        r.dueDate &&
        new Date(r.dueDate) < today
    )
  } else if (type === "rejected-compliance") {
    rows = allRows.filter((r) => r.status === "REJECTED")
  }

  const columns: ReportColumn[] = [
    { header: "Compliance ID", key: "complianceId", width: 18, includeInPdf: true },
    { header: "Entity", key: "entity", width: 24, includeInPdf: true },
    { header: "Entity Code", key: "entityCode", width: 14 },
    { header: "Tax Reg # (GSTIN/VAT/EIN)", key: "taxRegNo", width: 22 },
    { header: "Country", key: "country", width: 16, includeInPdf: true },
    { header: "Region", key: "region", width: 14 },
    { header: "Currency", key: "currency", width: 10 },
    { header: "Compliance Type", key: "complianceType", width: 18 },
    { header: "Tax Type", key: "taxType", width: 14 },
    { header: "Form", key: "form", width: 20, includeInPdf: true },
    { header: "Tax Period", key: "taxPeriod", width: 14, includeInPdf: true },
    { header: "Frequency", key: "frequency", width: 14 },
    { header: "Due Date", key: "dueDate", width: 14, includeInPdf: true },
    { header: "Filing Date", key: "filingDate", width: 14, includeInPdf: true },
    { header: "Filing Delay (days)", key: "filingDelay", width: 16 },
    { header: "Filing Timeliness", key: "filingTimeliness", width: 16, includeInPdf: true },
    { header: "Requires Payment", key: "requiresPayment", width: 16 },
    { header: "Payment Due Date", key: "paymentDueDate", width: 16 },
    { header: "Payment Date", key: "paymentDate", width: 14 },
    { header: "Payment Delay (days)", key: "paymentDelay", width: 18 },
    { header: "Payment Timeliness", key: "paymentTimeliness", width: 18 },
    { header: "Payment Ref / Challan", key: "paymentRef", width: 22 },
    { header: "Payment Method", key: "paymentMethod", width: 16 },
    { header: "Payment (Local)", key: "paymentLocal", width: 16, includeInPdf: true },
    { header: "Payment (USD)", key: "paymentUSD", width: 16, includeInPdf: true },
    { header: "Status", key: "status", width: 16, includeInPdf: true },
    { header: "Priority", key: "priority", width: 12 },
    { header: "Preparer", key: "preparer", width: 20, includeInPdf: true },
    { header: "Reviewer (Step 1)", key: "reviewer", width: 20 },
    { header: "Approver (Step 2)", key: "approver", width: 20 },
    { header: "Source", key: "source", width: 12 },
    { header: "Filing Type", key: "filingType", width: 14 },
    { header: "Refund Type", key: "refundType", width: 14 },
  ]

  const mappedRows = rows.map((row) => {
    const reviewer = row.approvals?.find((a) => a.step === 1)?.approver?.name || ""
    const approver =
      row.approvals?.find((a) => a.step === 2)?.approver?.name ||
      row.approvals?.filter((a) => a.step !== 1).map((a) => a.approver?.name).filter(Boolean).join(", ") ||
      ""
    const preparer = row.assignments?.map((a) => a.preparer.name).filter(Boolean).join(", ") || ""

    return {
      complianceId: row.complianceId,
      entity: row.entity?.entityName || "",
      entityCode: row.entity?.entityNumber || "",
      taxRegNo: row.entity?.taxRegistrationNumber || "",
      country: row.country?.name || "",
      region: row.country?.region || "",
      currency: row._currency || row.entity?.currency || "USD",
      complianceType: row.complianceType?.name || "",
      taxType: row.complianceType?.taxType || "",
      form: row.form ? `${row.form.formNumber} - ${row.form.formName}` : "",
      taxPeriod: row.taxPeriod || "",
      frequency: row.frequency || "",
      dueDate: formatDate(row.dueDate),
      filingDate: row.filedAt ? formatDate(row.filedAt) : "",
      filingDelay: dayDiff(row.filedAt, row.dueDate),
      filingTimeliness: getFilingTimeliness(row.filedAt, row.dueDate),
      requiresPayment: row.requiresPayment === false ? "No" : "Yes",
      paymentDueDate: row.requiresPayment === false ? "N/A" : formatDate(row.paymentDueDate),
      paymentDate: row.requiresPayment === false ? "N/A" : row.paymentDate ? formatDate(row.paymentDate) : "",
      paymentDelay: row.requiresPayment === false ? "N/A" : dayDiff(row.paymentDate, row.paymentDueDate),
      paymentTimeliness: getPaymentTimeliness(row.requiresPayment, row.paymentDate, row.paymentDueDate),
      paymentRef: row.paymentReference || "",
      paymentMethod: row.paymentMethod || "",
      paymentLocal: row.paymentAmount ? Number(row.paymentAmount) : "",
      paymentUSD: row._paymentUSD ? Number(row._paymentUSD.toFixed(2)) : "",
      status: row.status || "",
      priority: row.priority || "",
      preparer,
      reviewer,
      approver,
      source: row.source || "MANUAL",
      filingType: row.filingType || "PAYMENT",
      refundType: row.refundType || "",
    }
  })

  const titleMap: Record<string, string> = {
    "compliance-register": "Compliance Register",
    "pending-compliance": "Pending Compliance Obligations",
    overdue: "Overdue Compliance Report",
    "rejected-compliance": "Rejected Compliance Items",
  }

  return {
    title: titleMap[type] || type,
    columns,
    rows: mappedRows,
    landscape: true,
  }
}

async function buildTreasuryReport(filters: Record<string, string>, orgId: string | null): Promise<ReportDataset> {
  const allRows = await fetchComplianceRegister(filters, orgId)
  const rows = allRows.filter(
    (r) => r.requiresPayment !== false && !["PAID", "CLOSED"].includes(r.status || "")
  )

  rows.sort((a, b) => {
    const da = a.paymentDueDate || a.dueDate || "9999"
    const db = b.paymentDueDate || b.dueDate || "9999"
    return da.localeCompare(db)
  })

  const columns: ReportColumn[] = [
    { header: "Entity", key: "entity", width: 24, includeInPdf: true },
    { header: "Entity Code", key: "entityCode", width: 14 },
    { header: "Tax Reg #", key: "taxRegNo", width: 20, includeInPdf: true },
    { header: "Country", key: "country", width: 16, includeInPdf: true },
    { header: "Region", key: "region", width: 14 },
    { header: "Tax Type", key: "taxType", width: 14, includeInPdf: true },
    { header: "Form", key: "form", width: 20 },
    { header: "Tax Period", key: "taxPeriod", width: 14, includeInPdf: true },
    { header: "Payment Due Date", key: "paymentDueDate", width: 16, includeInPdf: true },
    { header: "Days Left", key: "daysLeft", width: 14, includeInPdf: true },
    { header: "Urgency", key: "urgency", width: 18, includeInPdf: true },
    { header: "Currency", key: "currency", width: 10, includeInPdf: true },
    { header: "Liability (Local)", key: "paymentLocal", width: 16, includeInPdf: true },
    { header: "Est. Outflow (USD)", key: "paymentUSD", width: 18, includeInPdf: true },
    { header: "Filing Status", key: "status", width: 16, includeInPdf: true },
    { header: "Preparer", key: "preparer", width: 20 },
    { header: "Approver", key: "approver", width: 20 },
  ]

  const mappedRows = rows.map((r) => {
    const urgencyInfo = getPaymentUrgency(r.paymentDueDate, r.dueDate)
    const preparer = r.assignments?.map((a) => a.preparer.name).filter(Boolean).join(", ") || ""
    const approver = r.approvals?.map((a) => a.approver.name).filter(Boolean).join(", ") || ""

    return {
      entity: r.entity?.entityName || "",
      entityCode: r.entity?.entityNumber || "",
      taxRegNo: r.entity?.taxRegistrationNumber || "",
      country: r.country?.name || "",
      region: r.country?.region || "",
      taxType: r.complianceType?.taxType || "",
      form: r.form ? `${r.form.formNumber} - ${r.form.formName}` : "",
      taxPeriod: r.taxPeriod || "",
      paymentDueDate: formatDate(r.paymentDueDate || r.dueDate),
      daysLeft: urgencyInfo.daysLeft,
      urgency: urgencyInfo.urgency,
      currency: r._currency || r.entity?.currency || "USD",
      paymentLocal: r.paymentAmount ? Number(r.paymentAmount) : "",
      paymentUSD: r._paymentUSD ? Number(r._paymentUSD.toFixed(2)) : "",
      status: r.status || "",
      preparer,
      approver,
    }
  })

  return {
    title: "Treasury Outflow Forecast",
    columns,
    rows: mappedRows,
    landscape: true,
  }
}

async function buildStatutoryAuditReport(filters: Record<string, string>, orgId: string | null): Promise<ReportDataset> {
  const allRows = await fetchComplianceRegister(filters, orgId)
  const rows = allRows.filter((r) => ["FILED", "PAID", "CLOSED"].includes(r.status || ""))

  rows.sort((a, b) => {
    const da = a.filedAt || a.dueDate || ""
    const db = b.filedAt || b.dueDate || ""
    return db.localeCompare(da)
  })

  const columns: ReportColumn[] = [
    { header: "Compliance ID", key: "complianceId", width: 18, includeInPdf: true },
    { header: "Legal Entity", key: "entity", width: 24, includeInPdf: true },
    { header: "Entity Code", key: "entityCode", width: 14 },
    { header: "Tax Reg #", key: "taxRegNo", width: 20, includeInPdf: true },
    { header: "Country", key: "country", width: 16 },
    { header: "Form", key: "form", width: 20, includeInPdf: true },
    { header: "Tax Period", key: "taxPeriod", width: 14, includeInPdf: true },
    { header: "Due Date", key: "dueDate", width: 14, includeInPdf: true },
    { header: "Filing Date", key: "filingDate", width: 14, includeInPdf: true },
    { header: "Filing Delay", key: "filingDelay", width: 14 },
    { header: "Filing Timeliness", key: "filingTimeliness", width: 16, includeInPdf: true },
    { header: "Payment Date", key: "paymentDate", width: 14 },
    { header: "Payment Delay", key: "paymentDelay", width: 14 },
    { header: "Challan / Ref #", key: "paymentRef", width: 24, includeInPdf: true },
    { header: "Payment Mode", key: "paymentMethod", width: 16 },
    { header: "Currency", key: "currency", width: 10 },
    { header: "Tax Paid (Local)", key: "paymentLocal", width: 16, includeInPdf: true },
    { header: "Tax Paid (USD)", key: "paymentUSD", width: 16, includeInPdf: true },
    { header: "Preparer", key: "preparer", width: 18 },
    { header: "Reviewer (Step 1)", key: "reviewer", width: 18, includeInPdf: true },
    { header: "Approver (Step 2)", key: "approver", width: 18, includeInPdf: true },
    { header: "Audit Status", key: "auditStatus", width: 18, includeInPdf: true },
  ]

  const mappedRows = rows.map((r) => {
    const reviewer = r.approvals?.find((a) => a.step === 1)?.approver?.name || ""
    const approver =
      r.approvals?.find((a) => a.step === 2)?.approver?.name ||
      r.approvals?.filter((a) => a.step !== 1).map((a) => a.approver?.name).filter(Boolean).join(", ") ||
      ""
    const preparer = r.assignments?.map((a) => a.preparer.name).filter(Boolean).join(", ") || ""

    return {
      complianceId: r.complianceId,
      entity: r.entity?.entityName || "",
      entityCode: r.entity?.entityNumber || "",
      taxRegNo: r.entity?.taxRegistrationNumber || "",
      country: r.country?.name || "",
      form: r.form ? `${r.form.formNumber} - ${r.form.formName}` : "",
      taxPeriod: r.taxPeriod || "",
      dueDate: formatDate(r.dueDate),
      filingDate: formatDate(r.filedAt),
      filingDelay: dayDiff(r.filedAt, r.dueDate),
      filingTimeliness: getFilingTimeliness(r.filedAt, r.dueDate),
      paymentDate: r.paymentDate ? formatDate(r.paymentDate) : "—",
      paymentDelay: dayDiff(r.paymentDate, r.paymentDueDate),
      paymentRef: r.paymentReference || "—",
      paymentMethod: r.paymentMethod || "—",
      currency: r._currency || r.entity?.currency || "USD",
      paymentLocal: r.paymentAmount ? Number(r.paymentAmount) : "",
      paymentUSD: r._paymentUSD ? Number(r._paymentUSD.toFixed(2)) : "",
      preparer,
      reviewer,
      approver,
      auditStatus: "Filed & Verified",
    }
  })

  return {
    title: "Statutory Filing & Challan Pack",
    columns,
    rows: mappedRows,
    landscape: true,
  }
}

async function buildEmployeeProductivityReport(filters: Record<string, string>, orgId: string | null): Promise<ReportDataset> {
  const allRows = await fetchComplianceRegister(filters, orgId)
  const today = new Date()

  const empMap = new Map<
    string,
    {
      name: string
      email: string
      total: number
      completed: number
      pending: number
      overdue: number
      onTimeCompleted: number
      totalTaxUSD: number
    }
  >()

  for (const r of allRows) {
    const preparers = r.assignments?.map((a) => a.preparer).filter(Boolean) || []
    const isCompleted = ["FILED", "PAID", "CLOSED"].includes(r.status || "")
    const isOverdue = !isCompleted && r.dueDate && new Date(r.dueDate) < today
    const isOnTime = isCompleted && r.filedAt && r.dueDate && new Date(r.filedAt) <= new Date(r.dueDate)
    const taxUSD = r._paymentUSD || 0

    for (const prep of preparers) {
      if (!empMap.has(prep.id)) {
        empMap.set(prep.id, {
          name: prep.name || "Unknown",
          email: prep.email || "—",
          total: 0,
          completed: 0,
          pending: 0,
          overdue: 0,
          onTimeCompleted: 0,
          totalTaxUSD: 0,
        })
      }
      const entry = empMap.get(prep.id)!
      entry.total++
      if (isCompleted) entry.completed++
      else if (isOverdue) entry.overdue++
      else entry.pending++

      if (isOnTime) entry.onTimeCompleted++
      entry.totalTaxUSD += taxUSD
    }
  }

  const columns: ReportColumn[] = [
    { header: "Employee Name", key: "name", width: 24, includeInPdf: true },
    { header: "Email Address", key: "email", width: 26, includeInPdf: true },
    { header: "Total Assigned", key: "total", width: 16, includeInPdf: true },
    { header: "Completed", key: "completed", width: 14, includeInPdf: true },
    { header: "In Progress", key: "pending", width: 14, includeInPdf: true },
    { header: "Overdue", key: "overdue", width: 14, includeInPdf: true },
    { header: "On-Time Filings", key: "onTimeCompleted", width: 16, includeInPdf: true },
    { header: "On-Time Rate (%)", key: "rate", width: 18, includeInPdf: true },
    { header: "Tax Managed (USD)", key: "taxUSD", width: 20, includeInPdf: true },
  ]

  const mappedRows = Array.from(empMap.values())
    .map((e) => ({
      name: e.name,
      email: e.email,
      total: e.total,
      completed: e.completed,
      pending: e.pending,
      overdue: e.overdue,
      onTimeCompleted: e.onTimeCompleted,
      rate: e.completed > 0 ? `${((e.onTimeCompleted / e.completed) * 100).toFixed(1)}%` : e.total > 0 ? "0.0%" : "100.0%",
      taxUSD: Number(e.totalTaxUSD.toFixed(2)),
    }))
    .sort((a, b) => b.total - a.total)

  return {
    title: "Employee Productivity Report",
    columns,
    rows: mappedRows,
    landscape: false,
  }
}

async function buildApprovalTatReport(filters: Record<string, string>, orgId: string | null): Promise<ReportDataset> {
  const allRows = await fetchComplianceRegister(filters, orgId)
  const records: Record<string, unknown>[] = []

  for (const r of allRows) {
    if (!r.approvals || r.approvals.length === 0) continue

    for (const app of r.approvals) {
      const stepName = app.step === 1 ? "Reviewer (Step 1)" : app.step === 2 ? "Approver (Step 2)" : "Admin Approver"
      const submittedAt = r.submittedAt ? formatDate(r.submittedAt) : "—"
      const decisionDate = app.updatedAt ? formatDate(app.updatedAt) : r.updatedAt ? formatDate(r.updatedAt) : "—"

      let tatHours = "—"
      let tatDays = "—"
      if (r.submittedAt && (app.updatedAt || r.updatedAt)) {
        const ms = new Date(app.updatedAt || r.updatedAt || "").getTime() - new Date(r.submittedAt).getTime()
        if (ms >= 0) {
          tatHours = (ms / (1000 * 60 * 60)).toFixed(1)
          tatDays = (ms / (1000 * 60 * 60 * 24)).toFixed(1)
        }
      }

      const dueDate = formatDate(r.dueDate)
      const approvedOnTime =
        dueDate && (app.updatedAt || r.updatedAt)
          ? new Date(app.updatedAt || r.updatedAt || "") <= new Date(r.dueDate || "")
            ? "Yes"
            : "No"
          : "—"

      records.push({
        complianceId: r.complianceId,
        entity: r.entity?.entityName || "",
        form: r.form ? `${r.form.formNumber} - ${r.form.formName}` : "",
        taxPeriod: r.taxPeriod || "",
        approver: app.approver?.name || "Pending Assignee",
        step: stepName,
        submittedAt,
        decisionDate,
        tatHours,
        tatDays,
        dueDate,
        approvedOnTime,
        status: app.status || r.status || "",
      })
    }
  }

  const columns: ReportColumn[] = [
    { header: "Compliance ID", key: "complianceId", width: 18, includeInPdf: true },
    { header: "Entity", key: "entity", width: 22, includeInPdf: true },
    { header: "Form", key: "form", width: 20 },
    { header: "Tax Period", key: "taxPeriod", width: 14, includeInPdf: true },
    { header: "Sign-off User", key: "approver", width: 20, includeInPdf: true },
    { header: "Approval Step", key: "step", width: 18, includeInPdf: true },
    { header: "Submitted Date", key: "submittedAt", width: 16 },
    { header: "Decision Date", key: "decisionDate", width: 16, includeInPdf: true },
    { header: "TAT (Hours)", key: "tatHours", width: 14, includeInPdf: true },
    { header: "TAT (Days)", key: "tatDays", width: 14, includeInPdf: true },
    { header: "Due Date", key: "dueDate", width: 14 },
    { header: "Met Due Date?", key: "approvedOnTime", width: 16, includeInPdf: true },
    { header: "Decision Status", key: "status", width: 16, includeInPdf: true },
  ]

  return {
    title: "Approval Turnaround Time (TAT) Analysis",
    columns,
    rows: records,
    landscape: true,
  }
}

async function buildPreparationTatReport(filters: Record<string, string>, orgId: string | null): Promise<ReportDataset> {
  const allRows = await fetchComplianceRegister(filters, orgId)
  const rows = allRows.filter((r) => r.submittedAt || r.filedAt)

  const records = rows.map((r) => {
    const preparer = r.assignments?.map((a) => a.preparer.name).filter(Boolean).join(", ") || "Unassigned"
    const createdAt = formatDate(r.createdAt || r.dueDate)
    const submittedAt = formatDate(r.submittedAt || r.filedAt)

    let prepDays = "—"
    if (r.createdAt && (r.submittedAt || r.filedAt)) {
      const ms = new Date(r.submittedAt || r.filedAt || "").getTime() - new Date(r.createdAt).getTime()
      if (ms >= 0) {
        prepDays = (ms / (1000 * 60 * 60 * 24)).toFixed(1)
      }
    }

    const dueDate = formatDate(r.dueDate)
    const submittedOnTime =
      dueDate && (r.submittedAt || r.filedAt)
        ? new Date(r.submittedAt || r.filedAt || "") <= new Date(r.dueDate || "")
          ? "Yes"
          : "No"
        : "—"

    return {
      complianceId: r.complianceId,
      entity: r.entity?.entityName || "",
      form: r.form ? `${r.form.formNumber} - ${r.form.formName}` : "",
      taxPeriod: r.taxPeriod || "",
      preparer,
      createdAt,
      submittedAt,
      prepDays,
      dueDate,
      submittedOnTime,
      status: r.status || "",
    }
  })

  const columns: ReportColumn[] = [
    { header: "Compliance ID", key: "complianceId", width: 18, includeInPdf: true },
    { header: "Entity", key: "entity", width: 22, includeInPdf: true },
    { header: "Form", key: "form", width: 20 },
    { header: "Tax Period", key: "taxPeriod", width: 14, includeInPdf: true },
    { header: "Preparer", key: "preparer", width: 20, includeInPdf: true },
    { header: "Assignment Date", key: "createdAt", width: 16 },
    { header: "Submission Date", key: "submittedAt", width: 16, includeInPdf: true },
    { header: "Prep Time (Days)", key: "prepDays", width: 18, includeInPdf: true },
    { header: "Due Date", key: "dueDate", width: 14 },
    { header: "Submitted On-Time?", key: "submittedOnTime", width: 20, includeInPdf: true },
    { header: "Current Status", key: "status", width: 16, includeInPdf: true },
  ]

  return {
    title: "Preparation Turnaround Time (TAT) Analysis",
    columns,
    rows: records,
    landscape: true,
  }
}

async function buildCountryComplianceReport(filters: Record<string, string>, orgId: string | null): Promise<ReportDataset> {
  const allRows = await fetchComplianceRegister(filters, orgId)
  const today = new Date()

  const countryMap = new Map<
    string,
    {
      country: string
      code: string
      region: string
      total: number
      completed: number
      pending: number
      overdue: number
      onTimeCompleted: number
      taxUSD: number
    }
  >()

  for (const r of allRows) {
    const cName = r.country?.name || "Unknown"
    const cCode = r.country?.code || "—"
    const cRegion = r.country?.region || "—"

    if (!countryMap.has(cName)) {
      countryMap.set(cName, {
        country: cName,
        code: cCode,
        region: cRegion,
        total: 0,
        completed: 0,
        pending: 0,
        overdue: 0,
        onTimeCompleted: 0,
        taxUSD: 0,
      })
    }

    const entry = countryMap.get(cName)!
    entry.total++

    const isCompleted = ["FILED", "PAID", "CLOSED"].includes(r.status || "")
    const isOverdue = !isCompleted && r.dueDate && new Date(r.dueDate) < today
    const isOnTime = isCompleted && r.filedAt && r.dueDate && new Date(r.filedAt) <= new Date(r.dueDate)

    if (isCompleted) entry.completed++
    else if (isOverdue) entry.overdue++
    else entry.pending++

    if (isOnTime) entry.onTimeCompleted++
    entry.taxUSD += r._paymentUSD || 0
  }

  const columns: ReportColumn[] = [
    { header: "Country", key: "country", width: 22, includeInPdf: true },
    { header: "Code", key: "code", width: 10, includeInPdf: true },
    { header: "Region", key: "region", width: 16, includeInPdf: true },
    { header: "Total Schedules", key: "total", width: 16, includeInPdf: true },
    { header: "Completed", key: "completed", width: 14, includeInPdf: true },
    { header: "Pending", key: "pending", width: 14, includeInPdf: true },
    { header: "Overdue", key: "overdue", width: 14, includeInPdf: true },
    { header: "Compliance Rate (%)", key: "rate", width: 20, includeInPdf: true },
    { header: "Total Tax Settled (USD)", key: "taxUSD", width: 22, includeInPdf: true },
  ]

  const mappedRows = Array.from(countryMap.values())
    .map((c) => ({
      country: c.country,
      code: c.code,
      region: c.region,
      total: c.total,
      completed: c.completed,
      pending: c.pending,
      overdue: c.overdue,
      rate: c.total > 0 ? `${((c.completed / c.total) * 100).toFixed(1)}%` : "0.0%",
      taxUSD: Number(c.taxUSD.toFixed(2)),
    }))
    .sort((a, b) => b.total - a.total)

  return {
    title: "Country Compliance Distribution",
    columns,
    rows: mappedRows,
    landscape: false,
  }
}

async function buildEntityComplianceReport(filters: Record<string, string>, orgId: string | null): Promise<ReportDataset> {
  const allRows = await fetchComplianceRegister(filters, orgId)
  const today = new Date()

  const entityMap = new Map<
    string,
    {
      entity: string
      code: string
      taxRegNo: string
      country: string
      currency: string
      total: number
      completed: number
      pending: number
      overdue: number
      onTimeCompleted: number
      taxUSD: number
    }
  >()

  for (const r of allRows) {
    const eName = r.entity?.entityName || "Unknown"
    const eCode = r.entity?.entityNumber || "—"
    const taxRegNo = r.entity?.taxRegistrationNumber || "—"
    const country = r.country?.name || "—"
    const currency = r.entity?.currency || "USD"

    if (!entityMap.has(eName)) {
      entityMap.set(eName, {
        entity: eName,
        code: eCode,
        taxRegNo,
        country,
        currency,
        total: 0,
        completed: 0,
        pending: 0,
        overdue: 0,
        onTimeCompleted: 0,
        taxUSD: 0,
      })
    }

    const entry = entityMap.get(eName)!
    entry.total++

    const isCompleted = ["FILED", "PAID", "CLOSED"].includes(r.status || "")
    const isOverdue = !isCompleted && r.dueDate && new Date(r.dueDate) < today
    const isOnTime = isCompleted && r.filedAt && r.dueDate && new Date(r.filedAt) <= new Date(r.dueDate)

    if (isCompleted) entry.completed++
    else if (isOverdue) entry.overdue++
    else entry.pending++

    if (isOnTime) entry.onTimeCompleted++
    entry.taxUSD += r._paymentUSD || 0
  }

  const columns: ReportColumn[] = [
    { header: "Entity Name", key: "entity", width: 26, includeInPdf: true },
    { header: "Entity Code", key: "code", width: 14, includeInPdf: true },
    { header: "Tax Reg #", key: "taxRegNo", width: 22, includeInPdf: true },
    { header: "Country", key: "country", width: 18, includeInPdf: true },
    { header: "Currency", key: "currency", width: 10 },
    { header: "Total Schedules", key: "total", width: 16, includeInPdf: true },
    { header: "Completed", key: "completed", width: 14, includeInPdf: true },
    { header: "Pending", key: "pending", width: 14, includeInPdf: true },
    { header: "Overdue", key: "overdue", width: 14, includeInPdf: true },
    { header: "Compliance Rate (%)", key: "rate", width: 20, includeInPdf: true },
    { header: "Total Tax Settled (USD)", key: "taxUSD", width: 22, includeInPdf: true },
  ]

  const mappedRows = Array.from(entityMap.values())
    .map((e) => ({
      entity: e.entity,
      code: e.code,
      taxRegNo: e.taxRegNo,
      country: e.country,
      currency: e.currency,
      total: e.total,
      completed: e.completed,
      pending: e.pending,
      overdue: e.overdue,
      rate: e.total > 0 ? `${((e.completed / e.total) * 100).toFixed(1)}%` : "0.0%",
      taxUSD: Number(e.taxUSD.toFixed(2)),
    }))
    .sort((a, b) => b.total - a.total)

  return {
    title: "Legal Entity Compliance Report",
    columns,
    rows: mappedRows,
    landscape: true,
  }
}

async function buildPeriodicSummaryReport(
  type: "monthly-summary" | "quarterly-summary" | "yearly-summary",
  filters: Record<string, string>,
  orgId: string | null
): Promise<ReportDataset> {
  const allRows = await fetchComplianceRegister(filters, orgId)
  const today = new Date()

  const periodMap = new Map<
    string,
    {
      period: string
      total: number
      onTime: number
      delayed: number
      pending: number
      overdue: number
      taxUSD: number
    }
  >()

  for (const r of allRows) {
    const dStr = r.dueDate || r.filedAt || new Date().toISOString()
    const d = new Date(dStr)
    const year = d.getFullYear()
    const month = d.getMonth() + 1

    let periodKey: string
    if (type === "monthly-summary") {
      periodKey = `${year}-${String(month).padStart(2, "0")}`
    } else if (type === "quarterly-summary") {
      const q = Math.ceil(month / 3)
      periodKey = `${year}-Q${q}`
    } else {
      periodKey = `${year}`
    }

    if (!periodMap.has(periodKey)) {
      periodMap.set(periodKey, {
        period: periodKey,
        total: 0,
        onTime: 0,
        delayed: 0,
        pending: 0,
        overdue: 0,
        taxUSD: 0,
      })
    }

    const entry = periodMap.get(periodKey)!
    entry.total++

    const isCompleted = ["FILED", "PAID", "CLOSED"].includes(r.status || "")
    const isOverdue = !isCompleted && r.dueDate && new Date(r.dueDate) < today
    const isOnTime = isCompleted && r.filedAt && r.dueDate && new Date(r.filedAt) <= new Date(r.dueDate)

    if (isOnTime) {
      entry.onTime++
    } else if (isCompleted) {
      entry.delayed++
    } else if (isOverdue) {
      entry.overdue++
    } else {
      entry.pending++
    }

    entry.taxUSD += r._paymentUSD || 0
  }

  const columns: ReportColumn[] = [
    { header: "Period", key: "period", width: 16, includeInPdf: true },
    { header: "Total Due", key: "total", width: 14, includeInPdf: true },
    { header: "Completed On-Time", key: "onTime", width: 18, includeInPdf: true },
    { header: "Completed Delayed", key: "delayed", width: 18, includeInPdf: true },
    { header: "Currently Pending", key: "pending", width: 16, includeInPdf: true },
    { header: "Currently Overdue", key: "overdue", width: 16, includeInPdf: true },
    { header: "On-Time Rate (%)", key: "rate", width: 18, includeInPdf: true },
    { header: "Total Tax Settled (USD)", key: "taxUSD", width: 22, includeInPdf: true },
  ]

  const mappedRows = Array.from(periodMap.values())
    .map((p) => ({
      period: p.period,
      total: p.total,
      onTime: p.onTime,
      delayed: p.delayed,
      pending: p.pending,
      overdue: p.overdue,
      rate: p.total > 0 ? `${((p.onTime / p.total) * 100).toFixed(1)}%` : "0.0%",
      taxUSD: Number(p.taxUSD.toFixed(2)),
    }))
    .sort((a, b) => a.period.localeCompare(b.period))

  const titleMap = {
    "monthly-summary": "Monthly Compliance Executive Summary",
    "quarterly-summary": "Quarterly Compliance Executive Summary",
    "yearly-summary": "Annual Compliance Executive Summary",
  }

  return {
    title: titleMap[type],
    columns,
    rows: mappedRows,
    landscape: false,
  }
}

async function buildAuditTrailReport(filters: Record<string, string>, orgId: string | null): Promise<ReportDataset> {
  let query = supabaseAdmin
    .from("activities")
    .select(`
      id,
      action,
      fromStatus,
      toStatus,
      comments,
      createdAt,
      user:users!userId(name, email),
      compliance:compliance_schedules!complianceId(complianceId, orgId)
    `)
    .order("createdAt", { ascending: false })
    .limit(500)

  const { dateFrom, dateTo } = getDateRangeFilter(filters)
  if (dateFrom) query = query.gte("createdAt", dateFrom.toISOString())
  if (dateTo) query = query.lte("createdAt", dateTo.toISOString())

  const { data, error } = await query
  if (error) throw error

  interface ActivityRaw {
    id: string
    action: string
    fromStatus: string | null
    toStatus: string | null
    comments: string | null
    createdAt: string
    user: { name: string; email: string } | null
    compliance: { complianceId: string; orgId: string } | null
  }

  const rows = ((data || []) as unknown as ActivityRaw[]).filter((item) => {
    if (!orgId) return true
    return item.compliance?.orgId === orgId
  })

  const columns: ReportColumn[] = [
    { header: "Date / Time", key: "timestamp", width: 20, includeInPdf: true },
    { header: "Compliance ID", key: "complianceId", width: 18, includeInPdf: true },
    { header: "User", key: "userName", width: 20, includeInPdf: true },
    { header: "Email", key: "userEmail", width: 24 },
    { header: "Action", key: "action", width: 18, includeInPdf: true },
    { header: "From Status", key: "fromStatus", width: 18, includeInPdf: true },
    { header: "To Status", key: "toStatus", width: 18, includeInPdf: true },
    { header: "Comments / Remarks", key: "comments", width: 35, includeInPdf: true },
  ]

  const mappedRows = rows.map((r) => ({
    timestamp: r.createdAt ? new Date(r.createdAt).toLocaleString() : "",
    complianceId: r.compliance?.complianceId || "—",
    userName: r.user?.name || "System",
    userEmail: r.user?.email || "—",
    action: (r.action || "").replace(/_/g, " "),
    fromStatus: r.fromStatus || "—",
    toStatus: r.toStatus || "—",
    comments: r.comments || "",
  }))

  return {
    title: "Audit Trail & Activity Log",
    columns,
    rows: mappedRows,
    landscape: true,
  }
}

async function buildSourceReport(filters: Record<string, string>, orgId: string | null): Promise<ReportDataset> {
  let query = supabaseAdmin
    .from("compliance_schedules")
    .select("source, status")

  if (orgId) query = query.eq("orgId", orgId)
  if (filters.countryId && filters.countryId !== "all") query = query.eq("countryId", filters.countryId)
  if (filters.entityId && filters.entityId !== "all") query = query.eq("entityId", filters.entityId)
  if (filters.status && filters.status !== "all") query = query.eq("status", filters.status)

  const { dateFrom, dateTo } = getDateRangeFilter(filters)
  if (dateFrom) query = query.gte("dueDate", dateFrom.toISOString())
  if (dateTo) query = query.lte("dueDate", dateTo.toISOString())

  const { data, error } = await query
  if (error) throw error

  const counts = new Map<string, number>()
  for (const row of (data || []) as { source: string | null; status: string | null }[]) {
    const source = row.source || "MANUAL"
    const status = row.status || "UNKNOWN"
    const key = `${source}|${status}`
    counts.set(key, (counts.get(key) || 0) + 1)
  }

  const mappedRows = Array.from(counts.entries())
    .map(([key, count]) => {
      const [source, status] = key.split("|")
      return { source, status, count }
    })
    .sort((a, b) => a.source.localeCompare(b.source) || a.status.localeCompare(b.status))

  const columns: ReportColumn[] = [
    { header: "Source", key: "source", width: 20, includeInPdf: true },
    { header: "Status", key: "status", width: 25, includeInPdf: true },
    { header: "Count", key: "count", width: 12, includeInPdf: true },
  ]

  return {
    title: "Compliance Source Breakdown",
    columns,
    rows: mappedRows,
    landscape: false,
  }
}

async function getReportDataset(type: ReportType, filters: Record<string, string>, orgId: string | null): Promise<ReportDataset> {
  switch (type) {
    case "compliance-register":
    case "pending-compliance":
    case "overdue":
    case "rejected-compliance":
      return buildComplianceRegisterReport(type, filters, orgId)
    case "treasury-forecast":
      return buildTreasuryReport(filters, orgId)
    case "statutory-audit-pack":
      return buildStatutoryAuditReport(filters, orgId)
    case "employee-productivity":
      return buildEmployeeProductivityReport(filters, orgId)
    case "approval-tat":
      return buildApprovalTatReport(filters, orgId)
    case "preparation-tat":
      return buildPreparationTatReport(filters, orgId)
    case "country-compliance":
      return buildCountryComplianceReport(filters, orgId)
    case "entity-compliance":
      return buildEntityComplianceReport(filters, orgId)
    case "monthly-summary":
    case "quarterly-summary":
    case "yearly-summary":
      return buildPeriodicSummaryReport(type, filters, orgId)
    case "audit-trail":
      return buildAuditTrailReport(filters, orgId)
    case "compliance-source":
      return buildSourceReport(filters, orgId)
  }
}

async function generateExcel(dataset: ReportDataset): Promise<Buffer> {
  const workbook = new ExcelJS.Workbook()
  const sheet = workbook.addWorksheet(dataset.title.slice(0, 31))

  sheet.columns = dataset.columns.map((c) => ({
    header: c.header,
    key: c.key,
    width: c.width,
  }))

  dataset.rows.forEach((row) => sheet.addRow(row))

  const headerRow = sheet.getRow(1)
  headerRow.font = { bold: true, color: { argb: "FFFFFFFF" } }
  headerRow.fill = {
    type: "pattern",
    pattern: "solid",
    fgColor: { argb: "FF2563EB" },
  }
  headerRow.alignment = { vertical: "middle", horizontal: "left" }
  headerRow.height = 24

  const buf = await workbook.xlsx.writeBuffer()
  return Buffer.from(buf)
}

async function generateCSV(dataset: ReportDataset): Promise<string> {
  return stringify(dataset.rows, {
    header: true,
    columns: dataset.columns.map((c) => ({ key: c.key, header: c.header })),
  })
}

async function generatePDF(dataset: ReportDataset): Promise<Buffer> {
  const orientation = dataset.landscape ? "landscape" : "portrait"
  const doc = new jsPDF({ orientation })

  doc.setFontSize(15)
  doc.setTextColor(30, 41, 59)
  doc.text(dataset.title, 14, 15)

  doc.setFontSize(9)
  doc.setTextColor(100, 116, 139)
  doc.text(`Generated on: ${new Date().toLocaleString()} | Total Records: ${dataset.rows.length}`, 14, 21)

  const pdfCols = dataset.columns.some((c) => c.includeInPdf)
    ? dataset.columns.filter((c) => c.includeInPdf)
    : dataset.columns

  const head = [pdfCols.map((c) => c.header)]
  const body = dataset.rows.map((row) => pdfCols.map((c) => String(row[c.key] ?? "")))

  const fontSize = pdfCols.length > 12 ? 6 : pdfCols.length > 8 ? 7 : 8.5

  autoTable(doc, {
    head,
    body,
    startY: 26,
    styles: { fontSize, cellPadding: 2 },
    headStyles: { fillColor: [37, 99, 235], textColor: [255, 255, 255], fontStyle: "bold" },
    alternateRowStyles: { fillColor: [248, 250, 252] },
  })

  return Buffer.from(doc.output("arraybuffer"))
}

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId } = getActiveContextFromRequest(request)
    const targetOrgId = orgId || session.user.orgs?.[0]?.id || null

    const body = await request.json()
    const { type, format, filters = {} } = body as {
      type: ReportType
      format: ExportFormat
      filters: Record<string, string>
    }

    if (!REPORT_TYPES.includes(type)) {
      return NextResponse.json(
        { error: `Invalid report type. Must be one of: ${REPORT_TYPES.join(", ")}` },
        { status: 400 }
      )
    }

    if (!["excel", "csv", "pdf"].includes(format)) {
      return NextResponse.json(
        { error: "Invalid format. Must be excel, csv, or pdf" },
        { status: 400 }
      )
    }

    const dataset = await getReportDataset(type, filters, targetOrgId)

    let fileBuffer: Buffer
    let contentType: string
    let fileName: string

    switch (format) {
      case "excel":
        fileBuffer = await generateExcel(dataset)
        contentType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        fileName = `${type}-${Date.now()}.xlsx`
        break
      case "csv":
        fileBuffer = Buffer.from(await generateCSV(dataset))
        contentType = "text/csv"
        fileName = `${type}-${Date.now()}.csv`
        break
      case "pdf":
        fileBuffer = await generatePDF(dataset)
        contentType = "application/pdf"
        fileName = `${type}-${Date.now()}.pdf`
        break
    }

    return new NextResponse(new Uint8Array(fileBuffer), {
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": `attachment; filename="${fileName}"`,
        "Content-Length": String(fileBuffer.length),
      },
    })
  } catch (error) {
    console.error("POST /api/reports error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
