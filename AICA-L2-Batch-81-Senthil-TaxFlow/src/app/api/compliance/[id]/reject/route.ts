import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { newId } from "@/lib/db"
import { NextResponse } from "next/server"

const complianceSelect = `
  *,
  entity:legal_entities(id, entityName, entityNumber),
  country:countries(id, name, code),
  complianceType:compliance_types(id, name, taxType),
  form:form_master(id, formNumber, formName),
  assignments:compliance_assignments(*, preparer:users(id, name, email)),
  approvals:compliance_approvals(*, approver:users(id, name, email)),
  attachments:attachments(id, originalName, fileType, fileSize, version, createdAt),
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

    const { id } = await params
    const body = await request.json()
    const { approverId, comments } = body

    if (!approverId) {
      return NextResponse.json({ error: "approverId is required" }, { status: 400 })
    }

    if (!comments) {
      return NextResponse.json({ error: "comments are required for rejection" }, { status: 400 })
    }

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*, approvals:compliance_approvals(*), assignments:compliance_assignments(*, preparer:users(id, name, email))")
      .eq("id", id)
      .maybeSingle()

    if (existingError) throw existingError

    if (!existing) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }

    // IDOR check: verify user belongs to the compliance's organization
    const isMember = session.user.orgs.some((o) => o.id === existing.orgId)
    if (!isMember) {
      return NextResponse.json({ error: "Forbidden: Not a member of this organization" }, { status: 403 })
    }

    // Impersonation check: only the assigned approver or an organization admin can reject
    const userOrg = session.user.orgs.find((o) => o.id === existing.orgId)
    const isAdmin = userOrg?.roles?.includes("ADMINISTRATOR") || session.user.roles.includes("ADMINISTRATOR")
    const isSelfApprover = session.user.id === approverId
    if (!isSelfApprover && !isAdmin) {
      return NextResponse.json(
        { error: "Forbidden: You are not authorized to reject on behalf of this approver" },
        { status: 403 }
      )
    }

    if (existing.status !== "PENDING_APPROVAL") {
      return NextResponse.json(
        { error: "Compliance must be in PENDING_APPROVAL status to reject" },
        { status: 400 }
      )
    }

    const approvalRecord = existing.approvals.find((a: { approverId: string }) => a.approverId === approverId)
    if (!approvalRecord) {
      return NextResponse.json({ error: "Approver not assigned to this compliance" }, { status: 400 })
    }

    const { error: approvalUpdateError } = await supabaseAdmin
      .from("compliance_approvals")
      .update({
        status: "REJECTED",
        actionAt: new Date().toISOString(),
        comments,
      })
      .eq("id", approvalRecord.id)

    if (approvalUpdateError) throw approvalUpdateError

    const { error: scheduleUpdateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update({ status: "REJECTED" })
      .eq("id", id)

    if (scheduleUpdateError) throw scheduleUpdateError

    const { error: activityError } = await supabaseAdmin
      .from("activities")
      .insert({
        id: newId(),
        complianceId: id,
        userId: session.user.id,
        action: "REJECTED",
        fromStatus: "PENDING_APPROVAL",
        toStatus: "REJECTED",
        comments,
      })

    if (activityError) throw activityError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        id: newId(),
        userId: session.user.id,
        action: "REJECT",
        entity: "ComplianceApproval",
        entityId: approvalRecord.id,
        oldValue: "PENDING_APPROVAL",
        newValue: "REJECTED",
        comments,
      })

    if (auditError) throw auditError

    if (existing.assignments?.length > 0) {
      const notifications = existing.assignments.map((assignment: { preparerId: string }) => ({
        id: newId(),
        userId: assignment.preparerId,
        title: "Compliance Rejected",
        message: `Compliance ${existing.complianceId} has been rejected. Reason: ${comments}`,
        type: "REJECTION",
        link: `/compliance/${id}`,
      }))

      const { error: notifError } = await supabaseAdmin
        .from("notifications")
        .insert(notifications)

      if (notifError) throw notifError
    }

    const { data, error: fetchError } = await supabaseAdmin
      .from("compliance_schedules")
      .select(complianceSelect)
      .eq("id", id)
      .single()

    if (fetchError) throw fetchError

    return NextResponse.json({ data })
  } catch (error) {
    console.error("POST /api/compliance/[id]/reject error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
