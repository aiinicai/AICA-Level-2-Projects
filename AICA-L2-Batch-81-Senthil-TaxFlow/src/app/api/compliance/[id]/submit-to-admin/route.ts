import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
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

    const { id } = await params

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*, assignments:compliance_assignments(*)")
      .eq("id", id)
      .maybeSingle()

    if (existingError) throw existingError

    if (!existing) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }

    if (existing.status !== "DRAFT") {
      return NextResponse.json(
        { error: "Only DRAFT compliance can be submitted to admin" },
        { status: 400 }
      )
    }

    const { data, error: updateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update({ status: "PENDING_ADMIN_APPROVAL", updatedAt: now() })
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
        action: "SUBMITTED_TO_ADMIN",
        fromStatus: "DRAFT",
        toStatus: "PENDING_ADMIN_APPROVAL",
        comments: "Compliance submitted to admin for approval",
      })

    if (activityError) throw activityError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        id: newId(),
        userId: session.user.id,
        action: "SUBMIT_TO_ADMIN",
        entity: "ComplianceSchedule",
        entityId: id,
        oldValue: "DRAFT",
        newValue: "PENDING_ADMIN_APPROVAL",
      })

    if (auditError) throw auditError

    // Notify org admins
    const { data: admins } = await supabaseAdmin
      .from("organization_members")
      .select("userId")
      .eq("orgId", existing.orgId)
      .contains("roles", ["ADMINISTRATOR"])

    if (admins && admins.length > 0) {
      const notifications = admins
        .filter((a: { userId: string }) => a.userId !== session.user.id)
        .map((a: { userId: string }) => ({
          id: newId(),
          userId: a.userId,
          title: "Compliance Awaiting Admin Approval",
          message: `Compliance ${existing.complianceId} has been submitted for admin approval`,
          type: "APPROVAL",
          link: `/compliance/${id}`,
        }))

      if (notifications.length > 0) {
        await supabaseAdmin.from("notifications").insert(notifications)
      }
    }

    return NextResponse.json({ data })
  } catch (error) {
    console.error("POST /api/compliance/[id]/submit-to-admin error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
