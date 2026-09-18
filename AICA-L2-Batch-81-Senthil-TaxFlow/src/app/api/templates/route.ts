import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { parseDate } from "@/lib/compliance-period"
import { normalizeApprovalFlow } from "@/lib/approval-flow"
import { NextResponse } from "next/server"

const templateSelect = `
  *,
  country:countries(id, name, code),
  complianceType:compliance_types(id, name, taxType),
  form:form_master(id, formNumber, formName),
  entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber, country:countries(name))),
  versions:compliance_template_versions(id, version, changedAt, changedById, changeReason),
  createdBy:users!compliance_templates_createdById_fkey(id, name, email),
  reviewer:users!compliance_templates_reviewerId_fkey(id, name, email),
  preparer:users!compliance_templates_preparerId_fkey(id, name, email),
  approver:users!compliance_templates_approverId_fkey(id, name, email),
  complianceReviewer:users!compliance_templates_complianceReviewerId_fkey(id, name, email)
`

const listSelect = `
  *,
  country:countries(id, name, code),
  form:form_master(id, formNumber, formName),
  entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber)),
  createdBy:users!compliance_templates_createdById_fkey(id, name, email)
`

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
    const taxType = searchParams.get("taxType") || ""
    const formId = searchParams.get("formId") || ""
    const frequency = searchParams.get("frequency") || ""
    const page = parseInt(searchParams.get("page") || "1", 10)
    const limit = parseInt(searchParams.get("limit") || "15", 10)
    const from = (page - 1) * limit
    const to = from + limit - 1

    let query = supabaseAdmin
      .from("compliance_templates")
      .select(listSelect, { count: "exact" })
      .eq("orgId", orgId)

    if (search) query = query.ilike("templateNumber", `%${search}%`)
    if (status && status !== "all") query = query.eq("status", status)
    if (countryId && countryId !== "all") query = query.eq("countryId", countryId)
    if (taxType && taxType !== "all") query = query.eq("taxType", taxType)
    if (formId && formId !== "all") query = query.eq("formId", formId)
    if (frequency && frequency !== "all") query = query.eq("frequency", frequency)
    if (entityId && entityId !== "all") {
      const { data: templateIds } = await supabaseAdmin
        .from("compliance_template_entities")
        .select("templateId")
        .eq("entityId", entityId)
      const ids = (templateIds || []).map((t: { templateId: string }) => t.templateId)
      if (ids.length > 0) {
        query = query.in("id", ids)
      } else {
        return NextResponse.json({ data: [], total: 0 })
      }
    }

    query = query.order("createdAt", { ascending: false }).range(from, to)

    const { data, error, count } = await query
    if (error) throw error

    return NextResponse.json({ data: data || [], total: count || 0 })
  } catch (error) {
    console.error("GET /api/templates error:", error)
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
      entityIds, taxType, formId, countryId, frequency, dueDaysAfterPeriodEnd,
      priority, recurringEndDate, notes,
      preparerId, approverId, complianceReviewerId, periodEndDate, paymentDueDaysAfterPeriodEnd, filingEntityId,
      approvalFlow: bodyApprovalFlow,
    } = body

    const entities = Array.isArray(entityIds) && entityIds.length > 0
      ? Array.from(new Set(entityIds)) : []

    if (entities.length === 0 || !taxType || !countryId || !frequency) {
      return NextResponse.json(
        { error: "entityIds, taxType, countryId, and frequency are required" },
        { status: 400 }
      )
    }

    if (filingEntityId && !entities.includes(filingEntityId)) {
      return NextResponse.json(
        { error: "Filing entity must be one of the selected entities" },
        { status: 400 }
      )
    }

    const templateId = newId()
    const approvalFlow = normalizeApprovalFlow(bodyApprovalFlow as string | undefined)

    const { error: createError } = await supabaseAdmin
      .from("compliance_templates")
      .insert({
        id: templateId,
        orgId,
        status: "PENDING_ADMIN_APPROVAL",
        submittedAt: now(),
        submittedById: session.user.id,
        version: 0,
        taxType,
        formId: formId || null,
        countryId,
        filingEntityId: filingEntityId || null,
        frequency,
        dueDaysAfterPeriodEnd: dueDaysAfterPeriodEnd ?? null,
        periodEndDate: periodEndDate ? parseDate(periodEndDate).toISOString() : null,
        paymentDueDaysAfterPeriodEnd: paymentDueDaysAfterPeriodEnd ?? null,
        priority: priority || "NORMAL",
        isRecurring: true,
        recurringEndDate: recurringEndDate ? new Date(recurringEndDate).toISOString() : null,
        notes: notes || null,
        preparerId: preparerId || null,
        approverId: approverId || null,
        complianceReviewerId: complianceReviewerId || null,
        approvalFlow,
        createdById: session.user.id,
        updatedAt: now(),
      })

    if (createError) throw createError

    if (entities.length > 0) {
      const { error: entityError } = await supabaseAdmin
        .from("compliance_template_entities")
        .insert(entities.map((eid: string) => ({
          id: newId(),
          templateId,
          entityId: eid,
        })))
      if (entityError) throw entityError
    }

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "CREATE",
      entity: "ComplianceTemplate",
      entityId: templateId,
      newValue: JSON.stringify({ taxType, countryId, frequency, entities }),
    })

    const { data: full, error: fetchError } = await supabaseAdmin
      .from("compliance_templates")
      .select(templateSelect)
      .eq("id", templateId)
      .single()

    if (fetchError) throw fetchError

    return NextResponse.json({ data: full }, { status: 201 })
  } catch (error) {
    console.error("POST /api/templates error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
