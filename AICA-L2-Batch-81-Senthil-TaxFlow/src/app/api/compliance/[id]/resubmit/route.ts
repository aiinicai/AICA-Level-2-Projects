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
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*, approvals:compliance_approvals(*), assignments:compliance_assignments(*, preparer:users(id, name, email))")
      .eq("id", id)
      .maybeSingle()

    if (existingError) throw existingError

    if (!existing) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }

    if (existing.status !== "REJECTED") {
      return NextResponse.json(
        { error: "Only rejected compliance can be resubmitted" },
        { status: 400 }
      )
    }

    const approvalIds = existing.approvals.map((a: { id: string }) => a.id)

    if (approvalIds.length > 0) {
      const { error: approvalUpdateError } = await supabaseAdmin
        .from("compliance_approvals")
        .update({
          status: "PENDING_APPROVAL",
          actionAt: null,
          comments: null,
        })
        .in("id", approvalIds)

      if (approvalUpdateError) throw approvalUpdateError
    }

    const { data, error: updateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update({
        status: "PENDING_APPROVAL",
        submittedAt: new Date().toISOString(),
      })
      .eq("id", id)
      .select(complianceSelect)
      .single()

    if (updateError) throw updateError

    const { error: activityError } = await supabaseAdmin
      .from("activities")
      .insert({
        id: newId(),
        complianceId: id,
        userId: session.user.id,
        action: "RESUBMITTED",
        fromStatus: "REJECTED",
        toStatus: "PENDING_APPROVAL",
        comments: "Compliance resubmitted for approval",
      })

    if (activityError) throw activityError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        id: newId(),
        userId: session.user.id,
        action: "RESUBMIT",
        entity: "ComplianceSchedule",
        entityId: id,
        oldValue: "REJECTED",
        newValue: "PENDING_APPROVAL",
      })

    if (auditError) throw auditError

    if (existing.approvals?.length > 0) {
      const notifications = existing.approvals.map((approval: { approverId: string }) => ({
        id: newId(),
        userId: approval.approverId,
        title: "Compliance Resubmitted",
        message: `Compliance ${existing.complianceId} has been resubmitted for your approval`,
        type: "APPROVAL",
        link: `/compliance/${id}`,
      }))

      const { error: notifError } = await supabaseAdmin
        .from("notifications")
        .insert(notifications)

      if (notifError) throw notifError
    }

    return NextResponse.json({ data })
  } catch (error) {
    console.error("POST /api/compliance/[id]/resubmit error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
