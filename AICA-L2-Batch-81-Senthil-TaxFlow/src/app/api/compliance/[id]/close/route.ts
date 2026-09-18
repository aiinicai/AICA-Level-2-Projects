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
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { activeRole } = getActiveContextFromRequest(_request)
    if (activeRole !== "ADMINISTRATOR" && activeRole !== "MANAGER") {
      return NextResponse.json({ error: "Only administrators or managers can close compliance" }, { status: 403 })
    }

    const { id } = await params

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id, status, complianceId, filedAt, paidAt, requiresPayment")
      .eq("id", id)
      .maybeSingle()

    if (existingError) throw existingError

    if (!existing) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }

    const requiresPayment = existing.requiresPayment !== false
    if (
      !["FILED", "PAID"].includes(existing.status) ||
      !existing.filedAt ||
      (requiresPayment && !existing.paidAt)
    ) {
      return NextResponse.json(
        { error: requiresPayment ? "Only compliance that is filed and paid can be closed" : "Only compliance that is filed can be closed" },
        { status: 400 }
      )
    }

    const { data, error: updateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update({ status: "CLOSED", updatedAt: now() })
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
        action: "CLOSED",
        fromStatus: existing.status,
        toStatus: "CLOSED",
        comments: "Compliance closed",
      })

    if (activityError) throw activityError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        id: newId(),
        userId: session.user.id,
        action: "CLOSE",
        entity: "ComplianceSchedule",
        entityId: id,
        oldValue: existing.status,
        newValue: "CLOSED",
      })

    if (auditError) throw auditError

    return NextResponse.json({ data })
  } catch (error) {
    console.error("POST /api/compliance/[id]/close error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
