import { supabaseAdmin } from "@/lib/supabase"
import { newId, now } from "@/lib/db"
import {
  computeGeneration,
  parseDate,
  toDateOnlyString,
  type GenerationResult,
} from "@/lib/compliance-period"
import { buildApprovalRecords, normalizeApprovalFlow, type ApprovalFlow } from "@/lib/approval-flow"

export interface GeneratedComplianceInput {
  template: {
    id: string
    templateNumber?: string | null
    version?: number | null
    taxType?: string | null
    formId?: string | null
    countryId?: string | null
    filingEntityId?: string | null
    frequency?: string | null
    priority?: string | null
    isRecurring?: boolean | null
    recurringEndDate?: string | null
    notes?: string | null
    preparerId?: string | null
    approverId?: string | null
    complianceReviewerId?: string | null
    approvalFlow?: string | null
  }
  entityIds: string[]
  countryId: string
  orgId: string
  userId: string
  filingMonth: string
  generation: { periodStart: Date; periodEnd: Date; dueDate: Date; paymentDueDate: Date }
}

export async function insertGeneratedCompliance(
  input: GeneratedComplianceInput
): Promise<{ scheduleId: string; complianceId: string }> {
  const { template, entityIds, countryId, orgId, userId, filingMonth, generation } = input
  const digits = Math.floor(10000 + Math.random() * 90000)
  const complianceId = `TAX-${digits}`
  const scheduleId = newId()

  let requiresPayment = true
  if (template.formId) {
    const { data: formRow } = await supabaseAdmin
      .from("form_master")
      .select("requiresPayment")
      .eq("id", template.formId)
      .maybeSingle()
    requiresPayment = formRow?.requiresPayment ?? true
  }

  const activeFlow = normalizeApprovalFlow((template.approvalFlow as string) || "ONE_LEVEL")

  const { error: scheduleError } = await supabaseAdmin.from("compliance_schedules").insert({
    id: scheduleId,
    orgId,
    complianceId,
    entityId: template.filingEntityId || entityIds[0] || null,
    countryId,
    taxType: template.taxType,
    formId: template.formId || null,
    taxPeriod: `${toDateOnlyString(generation.periodStart)}–${toDateOnlyString(generation.periodEnd)}`,
    taxPeriodStart: generation.periodStart.toISOString(),
    taxPeriodEnd: generation.periodEnd.toISOString(),
    filingMonth,
    frequency: template.frequency,
    dueDate: generation.dueDate.toISOString(),
    paymentDueDate: requiresPayment ? generation.paymentDueDate.toISOString() : null,
    requiresPayment,
    priority: template.priority || "NORMAL",
    status: "PENDING_PREPARATION",
    source: "TEMPLATE",
    isRecurring: template.isRecurring ?? true,
    recurringEndDate: template.recurringEndDate || null,
    notes: template.notes || null,
    templateId: template.id,
    templateVersion: template.version ?? 0,
    approvalFlow: activeFlow,
    updatedAt: now(),
    createdById: userId,
  })
  if (scheduleError) throw scheduleError

  for (const entityId of entityIds) {
    const { error: linkError } = await supabaseAdmin.from("compliance_entities").insert({
      id: newId(),
      complianceId: scheduleId,
      entityId,
    })
    if (linkError) throw linkError
  }

  if (template.preparerId) {
    const { error: assignmentError } = await supabaseAdmin.from("compliance_assignments").insert({
      id: newId(),
      complianceId: scheduleId,
      preparerId: template.preparerId,
      updatedAt: now(),
    })
    if (assignmentError) throw assignmentError
  }

  const approvalRecords = buildApprovalRecords(
    activeFlow,
    template.complianceReviewerId,
    template.approverId
  )

  if (approvalRecords.length > 0) {
    const { error: approvalError } = await supabaseAdmin.from("compliance_approvals").insert(
      approvalRecords.map((record) => ({
        id: newId(),
        complianceId: scheduleId,
        approverId: record.approverId,
        step: record.step,
        status: "PENDING_APPROVAL",
        updatedAt: now(),
      }))
    )
    if (approvalError) throw approvalError
  }

  const { error: activityError } = await supabaseAdmin.from("activities").insert({
    id: newId(),
    complianceId: scheduleId,
    userId,
    action: "CREATED",
    toStatus: "PENDING_PREPARATION",
    comments: `Generated from template ${template.templateNumber} v${template.version} for ${filingMonth}`,
  })
  if (activityError) throw activityError

  return { scheduleId, complianceId }
}

export function findLatestCompliance(
  rows: Array<{ taxPeriodEnd: string | null }>
): (typeof rows)[number] | null {
  return rows.reduce<(typeof rows)[number] | null>((acc, row) => {
    if (!row.taxPeriodEnd) return acc
    if (!acc || parseDate(row.taxPeriodEnd) > parseDate(acc.taxPeriodEnd as string)) return row
    return acc
  }, null)
}

export async function generateFirstCompliance(
  template: Record<string, unknown>,
  entities: Array<{ entityId: string }>,
  orgId: string,
  userId: string,
  filingMonth: string
) {
  const results: Array<{ entityId: string | null; complianceId: string; status: string }> = []
  const skipped: Array<{ entityId: string | null; reason: string }> = []

  const entityIds = entities.map((e) => e.entityId)
  if (!entityIds.length) {
    return { generated: results, skipped }
  }

  const { data: existingRows } = await supabaseAdmin
    .from("compliance_schedules")
    .select("id, complianceId, taxPeriodStart, taxPeriodEnd, filingMonth")
    .eq("templateId", template.id as string)

  const rows = (existingRows || []) as Array<{
    id: string
    complianceId: string
    taxPeriodStart: string | null
    taxPeriodEnd: string | null
    filingMonth: string | null
  }>
  const existingPeriods = rows.map((r) => ({ start: r.taxPeriodStart, end: r.taxPeriodEnd }))
  const existingFilingMonths = rows.map((r) => r.filingMonth)
  const latest = findLatestCompliance(rows)

  const generation: GenerationResult = computeGeneration({
    frequency: template.frequency as string,
    periodEndDate: (template.periodEndDate as string | null | undefined) ?? null,
    dueDaysAfterPeriodEnd: template.dueDaysAfterPeriodEnd as number | undefined,
    paymentDueDaysAfterPeriodEnd: template.paymentDueDaysAfterPeriodEnd as number | undefined,
    filingMonth,
    latestComplianceEnd: latest?.taxPeriodEnd ?? null,
    existingPeriods,
    existingFilingMonths,
    forceFirstPeriod: true,
  })

  if (generation.bucket !== "generate" || !generation.periodStart || !generation.periodEnd || !generation.dueDate || !generation.paymentDueDate) {
    skipped.push({ entityId: entityIds[0] || null, reason: generation.reason || "Not generated" })
    return { generated: results, skipped }
  }

  const { data: entitiesData } = await supabaseAdmin
    .from("legal_entities")
    .select("id, countryId")
    .in("id", entityIds)
  const entityCountries = (entitiesData || []) as Array<{ id: string; countryId: string }>
  const filingEntityId = (template.filingEntityId as string | null | undefined) || entityIds[0] || ""
  const countryId =
    entityCountries.find((e) => e.id === filingEntityId)?.countryId ||
    entityCountries[0]?.countryId ||
    (template.countryId as string) ||
    ""

  const { complianceId } = await insertGeneratedCompliance({
    template: template as GeneratedComplianceInput["template"],
    entityIds,
    countryId,
    orgId,
    userId,
    filingMonth,
    generation: {
      periodStart: generation.periodStart,
      periodEnd: generation.periodEnd,
      dueDate: generation.dueDate,
      paymentDueDate: generation.paymentDueDate,
    },
  })

  results.push({ entityId: entityIds[0] || null, complianceId, status: "created" })
  return { generated: results, skipped }
}
