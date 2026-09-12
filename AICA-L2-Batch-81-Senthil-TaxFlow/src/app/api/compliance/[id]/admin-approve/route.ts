import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

const complianceSelect = `
  *,
  entity:legal_entities(id, entityName, entityNumber),
  country:countries(id, name, code),
  complianceType:compliance_types(id, name, taxType),
  form:form_master(id, formNumber, formName),
  assignments:compliance_assignments(*, preparer:users(id, name, email)),
  approvals:compliance_approvals(*, approver:users(id, name, email)),
  attachments(id, originalName, fileType, fileSize, version, createdAt),
  comments:comments(*, user:users(id, name)),
  activities:activities(*, user:users(id, name))
`

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
    const orgRoles = session.user.orgs.find((o) => o.id === orgId)?.roles || []
    const isAdmin = activeRole === "ADMINISTRATOR" || orgRoles.includes("ADMINISTRATOR")
    if (!isAdmin) {
      return NextResponse.json({ error: "Only administrators can perform admin approval" }, { status: 403 })
    }

    const { id } = await params
    const body = await request.json()
    const { reviewerId, comments } = body

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*, assignments:compliance_assignments(*)")
      .eq("id", id)
      .maybeSingle()

    if (existingError) throw existingError

    if (!existing) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }

    if (existing.source === "TEMPLATE") {
      return NextResponse.json(
        { error: "Template-sourced compliances are approved through the template" },
        { status: 400 }
      )
    }

    const allowedFrom = ["DRAFT", "PENDING_ADMIN_APPROVAL"]
    if (!allowedFrom.includes(existing.status)) {
      return NextResponse.json(
        { error: "Compliance must be in DRAFT or PENDING_ADMIN_APPROVAL to be admin-approved" },
        { status: 400 }
      )
    }

    const updateData: Record<string, unknown> = {
      status: "PENDING_PREPARATION",
      updatedAt: now(),
    }

    const { data, error: updateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update(updateData)
      .eq("id", id)
      .select(complianceSelect)
      .single()

    if (updateError) throw updateError

    if (reviewerId && orgId) {
      const { data: member } = await supabaseAdmin
        .from("organization_members")
        .select("id")
        .eq("orgId", orgId)
        .eq("userId", reviewerId)
        .maybeSingle()

      if (!member) {
        await supabaseAdmin
          .from("organization_members")
          .insert({ id: newId(), orgId, userId: reviewerId, roles: ["APPROVER"], updatedAt: now() })
      }
    }

    const { error: activityError } = await supabaseAdmin
      .from("activities")
      .insert({
        id: newId(),
        complianceId: id,
        userId: session.user.id,
        action: "ADMIN_APPROVED",
        fromStatus: existing.status,
        toStatus: "PENDING_PREPARATION",
        comments: comments || undefined,
      })

    if (activityError) throw activityError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        id: newId(),
        userId: session.user.id,
        action: "ADMIN_APPROVE",
        entity: "ComplianceSchedule",
        entityId: id,
        oldValue: existing.status,
        newValue: "PENDING_PREPARATION",
        comments: comments || undefined,
      })

    if (auditError) throw auditError

    // Notify preparer
    if (existing.assignments?.length > 0) {
      const notifications = existing.assignments.map((assignment: { preparerId: string }) => ({
        id: newId(),
        userId: assignment.preparerId,
        title: "Compliance Ready for Preparation",
        message: `Compliance ${existing.complianceId} has been approved by admin and is ready for preparation`,
        type: "APPROVAL",
        link: `/compliance/${id}`,
      }))

      await supabaseAdmin.from("notifications").insert(notifications)
    }

    return NextResponse.json({ data })
  } catch (error) {
    console.error("POST /api/compliance/[id]/admin-approve error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
