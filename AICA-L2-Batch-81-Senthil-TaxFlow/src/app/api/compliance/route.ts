import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import {
  APPROVAL_FLOWS,
  buildApprovalRecords,
  effectiveApprovalFlow,
  normalizeApprovalFlow,
  requiresApprover,
  requiresReviewer,
  type ApprovalFlow,
} from "@/lib/approval-flow"
import { NextResponse } from "next/server"

const complianceSelect = `
  *,
  entity:legal_entities(id, entityName, entityNumber),
  entities:compliance_entities(*, entity:legal_entities(id, entityName, entityNumber, country:countries(name))),
  country:countries(id, name, code),
  complianceType:compliance_types(id, name, taxType),
  form:form_master(id, formNumber, formName),
  assignments:compliance_assignments(*, preparer:users(id, name, email)),
  approvals:compliance_approvals(*, approver:users(id, name, email)),
  attachments:attachments(id, originalName, fileType, fileSize, version, createdAt),
  comments:comments(*, user:users(id, name)),
  activities:activities(*, user:users(id, name))
`

const listSelect = `
  *,
  entity:legal_entities(id, entityName, entityNumber),
  entities:compliance_entities(*, entity:legal_entities(id, entityName, entityNumber)),
  country:countries(id, name, code),
  complianceType:compliance_types(id, name, taxType),
  form:form_master(id, formNumber, formName),
  assignments:compliance_assignments(*, preparer:users(id, name, email))
`

function sortNestedRelations(item: Record<string, unknown>) {
  if (item.comments) {
    (item.comments as Array<Record<string, unknown>>).sort(
      (a, b) => new Date(b.createdAt as string).getTime() - new Date(a.createdAt as string).getTime()
    )
  }
  if (item.activities) {
    (item.activities as Array<Record<string, unknown>>).sort(
      (a, b) => new Date(b.createdAt as string).getTime() - new Date(a.createdAt as string).getTime()
    )
  }
  return item
}

async function ensureOrgMember(orgId: string, userId: string, roles: string[]) {
  if (!orgId || !userId) return
  const { data: existing } = await supabaseAdmin
    .from("organization_members")
    .select("id, roles")
    .eq("orgId", orgId)
    .eq("userId", userId)
    .maybeSingle()

  if (existing) {
    const merged = Array.from(new Set([...(existing.roles || []), ...roles]))
    if (merged.length === (existing.roles || []).length) return
    await supabaseAdmin
      .from("organization_members")
      .update({ roles: merged, updatedAt: now() })
      .eq("id", existing.id)
    return
  }

  await supabaseAdmin
    .from("organization_members")
    .insert({
      id: newId(),
      orgId,
      userId,
      roles,
      updatedAt: now(),
    })
}

export async function GET(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }

    const { searchParams } = new URL(request.url)
    const search = searchParams.get("search") || ""
    const status = searchParams.get("status") || ""
    const countryId = searchParams.get("countryId") || ""
    const entityId = searchParams.get("entityId") || ""
    const complianceTypeId = searchParams.get("complianceTypeId") || ""
    const taxType = searchParams.get("taxType") || ""
    const priority = searchParams.get("priority") || ""
    const preparerId = searchParams.get("preparerId") || ""
    const approverId = searchParams.get("approverId") || ""
    const isRecurringParam = searchParams.get("isRecurring") || ""

    let query = supabaseAdmin
      .from("compliance_schedules")
      .select(listSelect, { count: "exact", head: false })
      .eq("orgId", orgId)

    if (search) {
      query = query.ilike("complianceId", `%${search}%`)
    }
    if (status && status !== "all") {
      query = query.eq("status", status)
    }
    if (countryId && countryId !== "all") {
      query = query.eq("countryId", countryId)
    }
    if (entityId && entityId !== "all") {
      query = query.eq("entityId", entityId)
    }
    if (complianceTypeId && complianceTypeId !== "all") {
      query = query.eq("complianceTypeId", complianceTypeId)
    }
    if (taxType && taxType !== "all") {
      query = query.eq("taxType", taxType)
    }
    if (priority && priority !== "all") {
      query = query.eq("priority", priority)
    }
    if (preparerId && preparerId !== "all") {
      query = query.eq("compliance_assignments.preparerId", preparerId)
    }
    if (approverId && approverId !== "all") {
      query = query.eq("compliance_approvals.approverId", approverId)
    }
    if (isRecurringParam !== "") {
      query = query.eq("isRecurring", isRecurringParam === "true")
    }

    query = query.order("dueDate", { ascending: true })

    const { data, error, count } = await query

    if (error) throw error

    const sortedData = (data || []).map(sortNestedRelations)

    return NextResponse.json({ data: sortedData, total: count || 0 })
  } catch (error) {
    console.error("GET /api/compliance error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }

    const body = await request.json()
    const {
      entityId,
      entityIds,
      taxType,
      formId,
      taxPeriod,
      taxPeriodStart,
      taxPeriodEnd,
      frequency,
      dueDate,
      paymentDueDate,
      priority,
      isRecurring,
      notes,
      preparerId: bodyPreparerId,
      reviewerId: bodyReviewerId,
      approverId: bodyApproverId,
      filingEntityId: bodyFilingEntityId,
      recurringEndDate,
      requiresPayment: bodyRequiresPayment,
      approvalFlow: bodyApprovalFlow,
    } = body

    const entities = Array.isArray(entityIds) && entityIds.length > 0
      ? Array.from(new Set(entityIds))
      : entityId
        ? [entityId]
        : []

    if (entities.length === 0 || !taxType || !frequency || !dueDate) {
      return NextResponse.json(
        { error: "At least one entityId, taxType, frequency, and dueDate are required" },
        { status: 400 }
      )
    }

    if (!taxPeriod && !taxPeriodStart) {
      return NextResponse.json(
        { error: "Either taxPeriod or taxPeriodStart/taxPeriodEnd is required" },
        { status: 400 }
      )
    }

    // The creator can tag any preparer (defaults to themselves if not provided).
    const preparerId = bodyPreparerId || session.user.id

    const { data: entityRows } = await supabaseAdmin
      .from("legal_entities")
      .select("id, countryId, approvalFlow")
      .in("id", entities)
    const countryByEntity = new Map((entityRows || []).map((e: { id: string; countryId: string }) => [e.id, e.countryId]))

    const filingEntityId =
      bodyFilingEntityId && entities.includes(bodyFilingEntityId)
        ? bodyFilingEntityId
        : entities.length === 1
          ? entities[0]
          : null

    if (!filingEntityId) {
      return NextResponse.json(
        { error: "Filing entity is required when multiple entities are selected" },
        { status: 400 }
      )
    }

    const filingEntity = (entityRows || []).find((e: { id: string }) => e.id === filingEntityId) as {
      id: string
      countryId: string
      approvalFlow: string
    } | undefined
    let requiresPayment =
      bodyRequiresPayment === true || bodyRequiresPayment === false ? !!bodyRequiresPayment : true
    let formFlow: ApprovalFlow | undefined
    if (formId) {
      const { data: formRow } = await supabaseAdmin
        .from("form_master")
        .select("requiresPayment, approvalFlow")
        .eq("id", formId)
        .maybeSingle()
      if (bodyRequiresPayment === undefined) requiresPayment = formRow?.requiresPayment ?? true
      if (formRow?.approvalFlow) {
        formFlow = normalizeApprovalFlow(formRow.approvalFlow as string)
      }
    }

    let flow: ApprovalFlow
    if (bodyApprovalFlow && APPROVAL_FLOWS.includes(bodyApprovalFlow as ApprovalFlow)) {
      flow = bodyApprovalFlow as ApprovalFlow
    } else {
      const entityFlow = normalizeApprovalFlow(filingEntity?.approvalFlow || "ONE_LEVEL")
      flow = effectiveApprovalFlow(formFlow, entityFlow)
    }

    const reviewerId = bodyReviewerId || ""
    const approverId = bodyApproverId || ""

    if (requiresReviewer(flow) && !reviewerId) {
      return NextResponse.json({ error: "reviewerId is required for this approval flow" }, { status: 400 })
    }
    if (requiresApprover(flow) && !approverId) {
      return NextResponse.json({ error: "approverId is required for two-level approval" }, { status: 400 })
    }

    const digits = Math.floor(10000 + Math.random() * 90000)
    const generatedComplianceId = `TAX-${digits}`

    const { data: schedule, error: createError } = await supabaseAdmin
      .from("compliance_schedules")
      .insert({
        id: newId(),
        orgId,
        complianceId: generatedComplianceId,
        entityId: filingEntityId,
        countryId: countryByEntity.get(filingEntityId) ?? null,
        taxType,
        complianceTypeId: null,
        formId: formId || null,
        taxPeriod: taxPeriod || (taxPeriodStart && taxPeriodEnd ? `${taxPeriodStart}–${taxPeriodEnd}` : ""),
        frequency,
        dueDate: new Date(dueDate).toISOString(),
        paymentDueDate: paymentDueDate && requiresPayment ? new Date(paymentDueDate).toISOString() : null,
        requiresPayment,
        priority: priority || "NORMAL",
        status: "DRAFT",
        source: "MANUAL",
        isRecurring: isRecurring ?? true,
        recurringEndDate: recurringEndDate ? new Date(recurringEndDate).toISOString() : null,
        notes: notes || null,
        updatedAt: now(),
      })
      .select("id, complianceId, status")
      .single()

    if (createError) throw createError

    const { error: entityLinkError } = await supabaseAdmin
      .from("compliance_entities")
      .insert(
        entities.map((entity) => ({
          id: newId(),
          complianceId: schedule.id,
          entityId: entity,
        }))
      )

    if (entityLinkError) throw entityLinkError

    if (preparerId) {
      const { error: assignError } = await supabaseAdmin
        .from("compliance_assignments")
        .insert({ id: newId(), complianceId: schedule.id, preparerId, updatedAt: now() })

      if (assignError) throw assignError

      await ensureOrgMember(orgId, preparerId, ["PREPARER"])
    }

    const approvalRecords = buildApprovalRecords(flow, reviewerId, approverId)

    if (approvalRecords.length > 0) {
      const { error: approvalError } = await supabaseAdmin
        .from("compliance_approvals")
        .insert(
          approvalRecords.map((record) => ({
            id: newId(),
            complianceId: schedule.id,
            approverId: record.approverId,
            step: record.step,
            status: "PENDING_APPROVAL",
            updatedAt: now(),
          }))
        )

      if (approvalError) throw approvalError

      for (const record of approvalRecords) {
        await ensureOrgMember(orgId, record.approverId, record.step === 1 ? ["REVIEWER"] : ["APPROVER"])
      }
    }

    const { data: fullData, error: fetchError } = await supabaseAdmin
      .from("compliance_schedules")
      .select(complianceSelect)
      .eq("id", schedule.id)
      .single()

    if (fetchError) throw fetchError

    const { error: activityError } = await supabaseAdmin
      .from("activities")
      .insert({
        id: newId(),
        complianceId: schedule.id,
        userId: session.user.id,
        action: "CREATED",
        toStatus: schedule.status,
        comments: `Compliance ${generatedComplianceId} created`,
      })

    if (activityError) throw activityError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        id: newId(),
        userId: session.user.id,
        action: "CREATE",
        entity: "ComplianceSchedule",
        entityId: schedule.id,
        newValue: JSON.stringify({ complianceId: generatedComplianceId, entityId: filingEntityId, taxType, taxPeriod, frequency, dueDate }),
      })

    if (auditError) throw auditError

    return NextResponse.json({ data: sortNestedRelations(fullData) }, { status: 201 })
  } catch (error) {
    console.error("POST /api/compliance error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
