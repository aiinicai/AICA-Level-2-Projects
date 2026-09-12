import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { newId } from "@/lib/db"
import { confirmationStageForStep } from "@/lib/payment"
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
    const { approverId, comments, confirmAmount } = body

    if (!approverId) {
      return NextResponse.json({ error: "approverId is required" }, { status: 400 })
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

    // Impersonation check: only the assigned approver or an organization admin can approve
    const userOrg = session.user.orgs.find((o) => o.id === existing.orgId)
    const isAdmin = userOrg?.roles?.includes("ADMINISTRATOR") || session.user.roles.includes("ADMINISTRATOR")
    const isSelfApprover = session.user.id === approverId
    if (!isSelfApprover && !isAdmin) {
      return NextResponse.json(
        { error: "Forbidden: You are not authorized to approve on behalf of this approver" },
        { status: 403 }
      )
    }

    if (existing.status !== "PENDING_APPROVAL") {
      return NextResponse.json(
        { error: "Compliance must be in PENDING_APPROVAL status to approve" },
        { status: 400 }
      )
    }

    const approvalRecord = existing.approvals.find((a: { approverId: string }) => a.approverId === approverId)
    if (!approvalRecord) {
      return NextResponse.json({ error: "Approver not assigned to this compliance" }, { status: 400 })
    }

    const recordStep = approvalRecord.step || 1
    if (recordStep > 1) {
      const previousSteps = (existing.approvals as Array<{ step: number; status: string }>).filter(
        (a) => (a.step || 1) < recordStep
      )
      if (previousSteps.some((a) => a.status !== "APPROVED")) {
        return NextResponse.json(
          { error: "Previous approval step must be completed first" },
          { status: 400 }
        )
      }
    }

    if (approvalRecord.status === "APPROVED") {
      return NextResponse.json({ error: "Already approved by this approver" }, { status: 400 })
    }

    if (existing.paymentAmount == null || !existing.filingType) {
      return NextResponse.json(
        { error: "Payment details are required before approval" },
        { status: 400 }
      )
    }

    if (confirmAmount !== true) {
      return NextResponse.json(
        { error: "Amount must be reconfirmed before approval" },
        { status: 400 }
      )
    }

    const confirmStage = confirmationStageForStep(recordStep)

    const { error: confirmError } = await supabaseAdmin
      .from("compliance_payment_confirmations")
      .upsert(
        {
          id: newId(),
          complianceId: id,
          stage: confirmStage,
          confirmedById: session.user.id,
          confirmedAt: new Date().toISOString(),
        },
        { onConflict: "complianceId,stage" }
      )

    if (confirmError) throw confirmError

    const { error: approvalUpdateError } = await supabaseAdmin
      .from("compliance_approvals")
      .update({
        status: "APPROVED",
        actionAt: new Date().toISOString(),
        comments: comments || null,
      })
      .eq("id", approvalRecord.id)

    if (approvalUpdateError) throw approvalUpdateError

    const { data: allApprovals, error: allApprovalsError } = await supabaseAdmin
      .from("compliance_approvals")
      .select("status")
      .eq("complianceId", id)

    if (allApprovalsError) throw allApprovalsError

    const allApproved = allApprovals.every((a: { status: string }) => a.status === "APPROVED")

    if (allApproved) {
      const { error: statusUpdateError } = await supabaseAdmin
        .from("compliance_schedules")
        .update({ status: "APPROVED" })
        .eq("id", id)

      if (statusUpdateError) throw statusUpdateError
    }

    const { error: activityError } = await supabaseAdmin
      .from("activities")
      .insert({
        id: newId(),
        complianceId: id,
        userId: session.user.id,
        action: "APPROVED",
        fromStatus: "PENDING_APPROVAL",
        toStatus: allApproved ? "APPROVED" : "PENDING_APPROVAL",
        comments: comments || undefined,
      })

    if (activityError) throw activityError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        id: newId(),
        userId: session.user.id,
        action: "APPROVE",
        entity: "ComplianceApproval",
        entityId: approvalRecord.id,
        oldValue: "PENDING_APPROVAL",
        newValue: "APPROVED",
        comments: comments || undefined,
      })

    if (auditError) throw auditError

    if (existing.assignments?.length > 0) {
      const notifications = existing.assignments.map((assignment: { preparerId: string }) => ({
        id: newId(),
        userId: assignment.preparerId,
        title: allApproved ? "Compliance Approved" : "Compliance Partially Approved",
        message: allApproved
          ? `Compliance ${existing.complianceId} has been fully approved`
          : `Compliance ${existing.complianceId} has been approved by ${session.user.name || "an approver"}`,
        type: "APPROVAL",
        link: `/compliance/${id}`,
      }))

      const { error: notifError } = await supabaseAdmin
        .from("notifications")
        .insert(notifications)

      if (notifError) throw notifError
    }

    if (!allApproved) {
      const nextStepApprovers = (existing.approvals as Array<{ step: number; approverId: string; status: string }>)
        .filter((a) => (a.step || 1) === recordStep + 1 && a.status === "PENDING_APPROVAL")
      if (nextStepApprovers.length > 0) {
        const nextNotifications = nextStepApprovers.map((a) => ({
          id: newId(),
          userId: a.approverId,
          title: "Compliance Ready for Approval",
          message: `Compliance ${existing.complianceId} has been reviewed and now awaits your approval`,
          type: "APPROVAL",
          link: `/compliance/${id}`,
        }))

        const { error: nextNotifError } = await supabaseAdmin
          .from("notifications")
          .insert(nextNotifications)
        if (nextNotifError) throw nextNotifError
      }
    }

    const { data, error: fetchError } = await supabaseAdmin
      .from("compliance_schedules")
      .select(complianceSelect)
      .eq("id", id)
      .single()

    if (fetchError) throw fetchError

    return NextResponse.json({ data })
  } catch (error) {
    console.error("POST /api/compliance/[id]/approve error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
