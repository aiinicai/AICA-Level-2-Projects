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
  form:form_master(id, formNumber, formName, requiresPayment),
  entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber, country:countries(name))),
  versions:compliance_template_versions(id, version, changedAt, changedById, changeReason, fieldDiffs, changedBy:users!compliance_template_versions_changedById_fkey(id, name)),
  createdBy:users!compliance_templates_createdById_fkey(id, name, email),
  reviewer:users!compliance_templates_reviewerId_fkey(id, name, email),
  preparer:users!compliance_templates_preparerId_fkey(id, name, email),
  approver:users!compliance_templates_approverId_fkey(id, name, email),
  complianceReviewer:users!compliance_templates_complianceReviewerId_fkey(id, name, email),
  generatedCompliances:compliance_schedules(id, complianceId, status, filingMonth, dueDate, createdAt)
`

function buildSnapshot(row: Record<string, unknown>) {
  const { id, orgId, createdAt, updatedAt, versions, entities, generatedCompliances, createdBy, reviewer, preparer, approver, complianceReviewer, country, form, complianceType, ...rest } = row as Record<string, unknown>
  void id; void orgId; void createdAt; void updatedAt; void versions; void entities; void generatedCompliances; void createdBy; void reviewer; void preparer; void approver; void complianceReviewer; void country; void form; void complianceType
  return rest
}

function computeDiffs(oldSnap: Record<string, unknown>, newSnap: Record<string, unknown>) {
  const diffs: Record<string, { old: unknown; new: unknown }> = {}
  const allKeys = new Set([...Object.keys(oldSnap), ...Object.keys(newSnap)])
  for (const key of allKeys) {
    if (JSON.stringify(oldSnap[key]) !== JSON.stringify(newSnap[key])) {
      diffs[key] = { old: oldSnap[key], new: newSnap[key] }
    }
  }
  return Object.keys(diffs).length > 0 ? diffs : null
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }

    const { id } = await params

    const { data, error } = await supabaseAdmin
      .from("compliance_templates")
      .select(templateSelect)
      .eq("id", id)
      .eq("orgId", orgId)
      .single()

    if (error || !data) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    if (data.versions) {
      (data.versions as Array<Record<string, unknown>>).sort(
        (a, b) => (b.version as number) - (a.version as number)
      )
    }

    return NextResponse.json({ data })
  } catch (error) {
    console.error("GET /api/templates/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function PUT(
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

    const { id } = await params
    const body = await request.json()

    const { data: existing, error: fetchError } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, entities:compliance_template_entities(*)")
      .eq("id", id)
      .single()

    if (fetchError || !existing || existing.orgId !== orgId) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    const isAdmin = activeRole === "ADMINISTRATOR"

    if (existing.status === "APPROVED" && !isAdmin) {
      return NextResponse.json(
        { error: "Only administrators can edit approved templates" },
        { status: 403 }
      )
    }

    const oldSnapshot = buildSnapshot(existing)

    const updates: Record<string, unknown> = { updatedAt: now(), isRecurring: true }
    const fields = [
      "taxType", "formId", "countryId", "frequency", "dueDaysAfterPeriodEnd",
      "priority", "notes", "preparerId", "approverId", "complianceReviewerId", "paymentDueDaysAfterPeriodEnd",
    ]
    for (const f of fields) {
      if (body[f] !== undefined) updates[f] = body[f] === "" ? null : body[f]
    }
    if (body.approvalFlow !== undefined) {
      updates.approvalFlow = normalizeApprovalFlow(body.approvalFlow as string | undefined)
    }
    if (body.recurringEndDate !== undefined) {
      updates.recurringEndDate = body.recurringEndDate ? new Date(body.recurringEndDate).toISOString() : null
    }
    if (body.periodEndDate !== undefined) {
      updates.periodEndDate = body.periodEndDate ? parseDate(body.periodEndDate).toISOString() : null
    }
    if (body.filingEntityId !== undefined) {
      const targetEntities = body.entityIds !== undefined
        ? Array.from(new Set(body.entityIds as string[]))
        : ((existing.entities || []) as Array<{ entityId: string }>).map((e) => e.entityId)
      if (body.filingEntityId && !targetEntities.includes(body.filingEntityId)) {
        return NextResponse.json(
          { error: "Filing entity must be one of the selected entities" },
          { status: 400 }
        )
      }
      updates.filingEntityId = body.filingEntityId || null
    }

    const { error: updateError } = await supabaseAdmin
      .from("compliance_templates")
      .update(updates)
      .eq("id", id)

    if (updateError) throw updateError

    if (body.entityIds !== undefined) {
      await supabaseAdmin.from("compliance_template_entities").delete().eq("templateId", id)
      const entities = Array.from(new Set(body.entityIds as string[]))
      if (entities.length > 0) {
        const { error: entityError } = await supabaseAdmin
          .from("compliance_template_entities")
          .insert(entities.map((eid: string) => ({
            id: newId(),
            templateId: id,
            entityId: eid,
          })))
        if (entityError) throw entityError
      }
    }

    if (existing.status === "APPROVED") {
      const { data: updated } = await supabaseAdmin
        .from("compliance_templates")
        .select("*")
        .eq("id", id)
        .single()

      const newSnapshot = buildSnapshot(updated || {})
      const diffs = computeDiffs(oldSnapshot, newSnapshot as Record<string, unknown>) || {}

      if (body.entityIds !== undefined) {
        const oldEntityIds = (existing.entities || []).map(
          (e: { entityId: string }) => e.entityId
        ).sort()
        const newEntityIds = Array.from(new Set(body.entityIds as string[])).sort()
        if (JSON.stringify(oldEntityIds) !== JSON.stringify(newEntityIds)) {
          diffs.entityIds = { old: oldEntityIds, new: newEntityIds }
        }
      }

      if (Object.keys(diffs).length > 0) {
        const newVersion = existing.version + 1
        await supabaseAdmin.from("compliance_templates").update({ version: newVersion, updatedAt: now() }).eq("id", id)

        await supabaseAdmin.from("compliance_template_versions").insert({
          id: newId(),
          templateId: id,
          version: newVersion,
          snapshot: newSnapshot,
          fieldDiffs: diffs,
          changeReason: body.changeReason || null,
          changedById: session.user.id,
        })

        await supabaseAdmin.from("audit_trails").insert({
          id: newId(),
          userId: session.user.id,
          action: "TEMPLATE_VERSION_CREATED",
          entity: "ComplianceTemplate",
          entityId: id,
          oldValue: JSON.stringify(oldSnapshot),
          newValue: JSON.stringify(newSnapshot),
          comments: `Version ${newVersion} created`,
        })
      }
    }

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "UPDATE",
      entity: "ComplianceTemplate",
      entityId: id,
      oldValue: JSON.stringify(oldSnapshot),
      newValue: JSON.stringify(updates),
    })

    const { data: full, error: refetchError } = await supabaseAdmin
      .from("compliance_templates")
      .select(templateSelect)
      .eq("id", id)
      .single()

    if (refetchError) throw refetchError

    return NextResponse.json({ data: full })
  } catch (error) {
    console.error("PUT /api/templates/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function DELETE(
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
      return NextResponse.json({ error: "Only administrators can delete templates" }, { status: 403 })
    }

    const { id } = await params

    const { data: existing } = await supabaseAdmin
      .from("compliance_templates")
      .select("id, templateNumber")
      .eq("id", id)
      .eq("orgId", orgId)
      .single()

    if (!existing) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    const { count } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id", { count: "exact", head: true })
      .eq("templateId", id)

    if ((count || 0) > 0) {
      return NextResponse.json(
        { error: "Cannot delete template with generated compliances. Deactivate it instead." },
        { status: 400 }
      )
    }

    await supabaseAdmin.from("compliance_template_versions").delete().eq("templateId", id)
    await supabaseAdmin.from("compliance_template_entities").delete().eq("templateId", id)
    await supabaseAdmin.from("compliance_templates").delete().eq("id", id)

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "DELETE",
      entity: "ComplianceTemplate",
      entityId: id,
      oldValue: JSON.stringify({ templateNumber: existing.templateNumber }),
    })

    return NextResponse.json({ data: { success: true } })
  } catch (error) {
    console.error("DELETE /api/templates/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
