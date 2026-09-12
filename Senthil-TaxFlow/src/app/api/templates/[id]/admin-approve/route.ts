import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { generateTemplateNumber } from "@/lib/template-number"
import { generateFirstCompliance } from "@/lib/template-compliance"
import { NextResponse } from "next/server"

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId, activeRole } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }
    if (activeRole !== "ADMINISTRATOR") {
      return NextResponse.json({ error: "Only administrators can approve templates" }, { status: 403 })
    }

    const { id } = await params
    const body = await request.json().catch(() => ({}))

    const { data: existing, error: fetchError } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, entities:compliance_template_entities(entityId), country:countries(code)")
      .eq("id", id)
      .eq("orgId", orgId)
      .single()

    if (fetchError || !existing) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    if (!["DRAFT", "PENDING_ADMIN_APPROVAL"].includes(existing.status)) {
      return NextResponse.json({ error: "Template cannot be approved in its current state" }, { status: 400 })
    }

    if (body.reviewerId) {
      const { error: updateError } = await supabaseAdmin
        .from("compliance_templates")
        .update({
          reviewerId: body.reviewerId,
          updatedAt: now(),
        })
        .eq("id", id)
      if (updateError) throw updateError
    }

    const countryCode = (existing.country as { code: string })?.code || "XX"
    const templateNumber = existing.templateNumber || await generateTemplateNumber(existing.taxType || "TAX", countryCode, orgId)

    const { error: updateError } = await supabaseAdmin
      .from("compliance_templates")
      .update({
        status: "APPROVED",
        templateNumber,
        version: 1,
        approvedAt: now(),
        approvedById: session.user.id,
        adminApprovedAt: now(),
        adminApprovedById: session.user.id,
        adminComments: body.comments || null,
        updatedAt: now(),
      })
      .eq("id", id)

    if (updateError) throw updateError

    const { data: approved } = await supabaseAdmin
      .from("compliance_templates")
      .select("*")
      .eq("id", id)
      .single()

    const snapshot = {
      taxType: approved.taxType, formId: approved.formId, countryId: approved.countryId,
      frequency: approved.frequency, dueDaysAfterPeriodEnd: approved.dueDaysAfterPeriodEnd, priority: approved.priority,
      isRecurring: approved.isRecurring, recurringEndDate: approved.recurringEndDate,
      notes: approved.notes, preparerId: approved.preparerId, approverId: approved.approverId,
      complianceReviewerId: approved.complianceReviewerId,
      entityIds: (existing.entities || []).map((e: { entityId: string }) => e.entityId),
    }

    await supabaseAdmin.from("compliance_template_versions").insert({
      id: newId(),
      templateId: id,
      version: 1,
      snapshot,
      changeReason: "Initial approval",
      changedById: session.user.id,
    })

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "TEMPLATE_APPROVED",
      entity: "ComplianceTemplate",
      entityId: id,
      newValue: JSON.stringify({ templateNumber, version: 1 }),
      comments: body.comments || "Template approved",
    })

    const currentDate = new Date()
    const filingMonth = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, "0")}`

    const generationResult = await generateFirstCompliance(
      { ...approved, templateNumber, version: 1 },
      existing.entities || [],
      orgId,
      session.user.id,
      filingMonth
    )

    const { data: full } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, country:countries(id, name, code), form:form_master(id, formNumber, formName), entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber)), versions:compliance_template_versions(id, version, changedAt, changeReason), createdBy:users!compliance_templates_createdById_fkey(id, name, email)")
      .eq("id", id)
      .single()

    return NextResponse.json({ data: full, generation: generationResult })
  } catch (error) {
    console.error("POST /api/templates/[id]/admin-approve error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
