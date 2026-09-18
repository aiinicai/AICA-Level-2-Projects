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

    const { activeRole } = getActiveContextFromRequest(request)

    const { id } = await params
    const body = await request.json()
    const {
      paymentDate,
      paymentReference,
      paymentMethod,
      paymentNotes,
      confirmPayment,
    } = body

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*, assignments:compliance_assignments(*, preparer:users(id, name, email))")
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

    if (existing.status !== "APPROVED" && existing.status !== "FILED") {
      return NextResponse.json(
        { error: "Only approved or filed compliance can be marked as paid" },
        { status: 400 }
      )
    }

    if (existing.requiresPayment === false) {
      return NextResponse.json(
        { error: "This compliance does not require payment" },
        { status: 400 }
      )
    }

    const assignedPreparers = (existing.assignments || []).map(
      (a: { preparer: { id: string } }) => a.preparer?.id
    )
    const isAssignedPreparer = assignedPreparers.includes(session.user.id)
    if (!isAssignedPreparer && activeRole !== "ADMINISTRATOR" && activeRole !== "MANAGER") {
      return NextResponse.json(
        { error: "Only the assigned preparer, administrators, or managers can record payment" },
        { status: 403 }
      )
    }

    if (existing.paymentAmount == null) {
      return NextResponse.json(
        { error: "Payment amount has not been submitted for this compliance" },
        { status: 400 }
      )
    }

    if (confirmPayment !== true) {
      return NextResponse.json(
        { error: "Payment must be confirmed before marking paid" },
        { status: 400 }
      )
    }

    // If already filed, marking paid moves it to CLOSED; otherwise PAID
    const nextStatus = existing.filedAt ? "CLOSED" : "PAID"

    const updateData: Record<string, unknown> = {
      status: nextStatus,
      paidAt: now(),
      updatedAt: now(),
    }

    if (paymentDate) updateData.paymentDate = new Date(paymentDate).toISOString()
    if (paymentReference) updateData.paymentReference = paymentReference
    if (paymentMethod) updateData.paymentMethod = paymentMethod
    if (paymentNotes) updateData.paymentNotes = paymentNotes

    const { data, error: updateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update(updateData)
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
          stage: "PREPARER_PAYMENT",
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
        action: "MARKED_PAID",
        fromStatus: existing.status,
        toStatus: "PAID",
        comments: paymentNotes || undefined,
      })

    if (activityError) throw activityError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        id: newId(),
        userId: session.user.id,
        action: "MARK_PAID",
        entity: "ComplianceSchedule",
        entityId: id,
        oldValue: existing.status,
        newValue: "PAID",
      })

    if (auditError) throw auditError

    return NextResponse.json({ data })
  } catch (error) {
    console.error("POST /api/compliance/[id]/mark-paid error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
