import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { newId } from "@/lib/db"
import { validatePaymentSubmission } from "@/lib/payment"
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

interface ApprovalStep {
  id: string
  step?: number
  approverId: string
}

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

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*, assignments:compliance_assignments(*, preparer:users(id, name, email)), approvals:compliance_approvals(*, approver:users(id, name, email))")
      .eq("id", id)
      .maybeSingle()

    if (existingError) throw existingError

    if (!existing) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }

    if (existing.status !== "PREPARED" && existing.status !== "PENDING_PREPARATION") {
      return NextResponse.json(
        { error: "Only compliance in PENDING_PREPARATION or PREPARED status can be submitted" },
        { status: 400 }
      )
    }

    const hasApprovalSteps = (existing.approvals || []).length > 0
    const nextStatus = hasApprovalSteps ? "PENDING_APPROVAL" : "APPROVED"

    const body = await request.json()
    const { filingType: rawFilingType, refundType, paymentCurrency, paymentAmount } = body || {}

    const requiresPayment = existing.requiresPayment !== false

    if (!requiresPayment) {
      const { data, error: updateError } = await supabaseAdmin
        .from("compliance_schedules")
        .update({
          status: nextStatus,
          submittedAt: new Date().toISOString(),
          filingType: "NIL_RETURN",
          refundType: null,
          paymentCurrency: null,
          paymentAmount: 0,
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
          action: "SUBMITTED",
          fromStatus: existing.status,
          toStatus: nextStatus,
          comments: hasApprovalSteps
            ? "Compliance submitted for approval"
            : "Compliance submitted and auto-approved (no approval required)",
        })

      if (activityError) throw activityError

      const { error: auditError } = await supabaseAdmin
        .from("audit_trails")
        .insert({
          id: newId(),
          userId: session.user.id,
          action: "SUBMIT",
          entity: "ComplianceSchedule",
          entityId: id,
          oldValue: existing.status,
          newValue: nextStatus,
        })

      if (auditError) throw auditError

      const stepOneApprovals = (existing.approvals || []).filter((a: ApprovalStep) => (a.step || 1) === 1)

      if (hasApprovalSteps && stepOneApprovals.length > 0) {
        const notifications = stepOneApprovals.map((approval: ApprovalStep) => ({
          id: newId(),
          userId: approval.approverId,
          title: "Compliance Pending Review",
          message: `Compliance ${existing.complianceId} has been submitted and awaits your review`,
          type: "APPROVAL",
          link: `/compliance/${id}`,
        }))

        const { error: notifError } = await supabaseAdmin
          .from("notifications")
          .insert(notifications)

        if (notifError) throw notifError
      }

      return NextResponse.json({ data })
    }

    const filingType = (rawFilingType as string) || "PAYMENT"

    let defaultCurrency = "USD"
    if (existing.entityId) {
      const { data: filingEntity } = await supabaseAdmin
        .from("legal_entities")
        .select("currency")
        .eq("id", existing.entityId)
        .maybeSingle()
      if (filingEntity?.currency) defaultCurrency = filingEntity.currency
    }

    const currency = (paymentCurrency as string) || defaultCurrency
    const amount = filingType === "NIL_RETURN" ? 0 : Number(paymentAmount)
    const errors = validatePaymentSubmission({
      filingType,
      amount,
      currency,
      refundType: filingType === "REFUND_RETURN" ? (refundType as string) || null : null,
    })

    if (errors.length > 0) {
      return NextResponse.json({ error: errors.join(". ") }, { status: 400 })
    }

    const resolvedRefundType = filingType === "REFUND_RETURN" ? refundType : null
    
    const { data, error: updateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update({
        status: nextStatus,
        submittedAt: new Date().toISOString(),
        filingType,
        refundType: resolvedRefundType,
        paymentCurrency: currency,
        paymentAmount: amount,
      })
      .eq("id", id)
      .select(complianceSelect)
      .single()

    if (updateError) throw updateError

    const { error: confirmError } = await supabaseAdmin
      .from("compliance_payment_confirmations")
      .upsert(
        {
          id: newId(),
          complianceId: id,
          stage: "PREPARER_SUBMIT",
          confirmedById: session.user.id,
          confirmedAt: new Date().toISOString(),
        },
        { onConflict: "complianceId,stage" }
      )

    if (confirmError) throw confirmError

    const { error: activityError } = await supabaseAdmin
      .from("activities")
      .insert({
        id: newId(),
        complianceId: id,
        userId: session.user.id,
        action: "SUBMITTED",
        fromStatus: existing.status,
        toStatus: nextStatus,
        comments: hasApprovalSteps
          ? "Compliance submitted for approval"
          : "Compliance submitted and auto-approved (no approval required)",
      })

    if (activityError) throw activityError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        id: newId(),
        userId: session.user.id,
        action: "SUBMIT",
        entity: "ComplianceSchedule",
        entityId: id,
        oldValue: existing.status,
        newValue: nextStatus,
      })

    if (auditError) throw auditError

    const stepOneApprovals = (existing.approvals || []).filter((a: ApprovalStep) => (a.step || 1) === 1)

    if (hasApprovalSteps && stepOneApprovals.length > 0) {
      const notifications = stepOneApprovals.map((approval: ApprovalStep) => ({
        id: newId(),
        userId: approval.approverId,
        title: "Compliance Pending Review",
        message: `Compliance ${existing.complianceId} has been submitted and awaits your review`,
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
    console.error("POST /api/compliance/[id]/submit error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
