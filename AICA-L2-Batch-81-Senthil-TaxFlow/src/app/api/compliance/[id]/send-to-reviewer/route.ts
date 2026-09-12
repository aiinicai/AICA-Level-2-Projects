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
    if (activeRole !== "ADMINISTRATOR") {
      return NextResponse.json({ error: "Only administrators can send for review" }, { status: 403 })
    }

    const { id } = await params
    const body = await request.json()
    const { reviewerId, comments } = body

    if (!reviewerId) {
      return NextResponse.json({ error: "reviewerId is required" }, { status: 400 })
    }

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*")
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
        { error: "Compliance must be in DRAFT or PENDING_ADMIN_APPROVAL to send for review" },
        { status: 400 }
      )
    }

    const { data, error: updateError } = await supabaseAdmin
      .from("compliance_schedules")
      .update({
        status: "PENDING_REVIEW",
        reviewerId,
        adminComments: comments || null,
        updatedAt: now(),
      })
      .eq("id", id)
      .select(complianceSelect)
      .single()

    if (updateError) throw updateError

    if (orgId) {
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
        action: "SENT_TO_REVIEWER",
        fromStatus: existing.status,
        toStatus: "PENDING_REVIEW",
        comments: comments || undefined,
      })

    if (activityError) throw activityError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        id: newId(),
        userId: session.user.id,
        action: "SEND_TO_REVIEWER",
        entity: "ComplianceSchedule",
        entityId: id,
        oldValue: existing.status,
        newValue: "PENDING_REVIEW",
        comments: comments || undefined,
      })

    if (auditError) throw auditError

    await supabaseAdmin.from("notifications").insert({
      id: newId(),
      userId: reviewerId,
      title: "Compliance Sent for Your Review",
      message: `Compliance ${existing.complianceId} has been sent to you for review`,
      type: "APPROVAL",
      link: `/compliance/${id}`,
    })

    return NextResponse.json({ data })
  } catch (error) {
    console.error("POST /api/compliance/[id]/send-to-reviewer error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
