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
    const body = await request.json().catch(() => ({}))
    const filedDate = typeof body?.filedDate === "string" && body.filedDate ? new Date(body.filedDate).toISOString() : null

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id, status, complianceId, orgId, paidAt, requiresPayment")
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

    if (existing.status !== "APPROVED" && existing.status !== "PAID") {
      return NextResponse.json(
        { error: "Only approved or paid compliance can be filed" },
        { status: 400 }
      )
    }

    // If already paid or payment is not required, filing moves it to CLOSED; otherwise FILED
    const nextStatus = existing.paidAt || !existing.requiresPayment ? "CLOSED" : "FILED"

    const { data, error: updateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update({
        status: nextStatus,
        filedAt: filedDate || new Date().toISOString(),
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
        action: "FILED",
        fromStatus: existing.status,
        toStatus: "FILED",
        comments: "Compliance has been filed",
      })

    if (activityError) throw activityError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        id: newId(),
        userId: session.user.id,
        action: "FILE",
        entity: "ComplianceSchedule",
        entityId: id,
        oldValue: existing.status,
        newValue: "FILED",
      })

    if (auditError) throw auditError

    return NextResponse.json({ data })
  } catch (error) {
    console.error("POST /api/compliance/[id]/file error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
