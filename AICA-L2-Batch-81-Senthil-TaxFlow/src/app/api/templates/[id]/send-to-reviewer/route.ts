import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

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
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }
    if (activeRole !== "ADMINISTRATOR") {
      return NextResponse.json({ error: "Only administrators can send templates for review" }, { status: 403 })
    }

    const { id } = await params
    const body = await request.json()

    if (!body.reviewerId) {
      return NextResponse.json({ error: "reviewerId is required" }, { status: 400 })
    }

    const { data: existing } = await supabaseAdmin
      .from("compliance_templates")
      .select("*")
      .eq("id", id)
      .eq("orgId", orgId)
      .single()

    if (!existing) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    if (!["DRAFT", "PENDING_ADMIN_APPROVAL"].includes(existing.status)) {
      return NextResponse.json({ error: "Template cannot be sent for review in its current state" }, { status: 400 })
    }

    const { error: updateError } = await supabaseAdmin
      .from("compliance_templates")
      .update({
        status: "PENDING_REVIEW",
        reviewerId: body.reviewerId,
        adminComments: body.comments || null,
        updatedAt: now(),
      })
      .eq("id", id)

    if (updateError) throw updateError

    await supabaseAdmin.from("notifications").insert({
      id: newId(),
      userId: body.reviewerId,
      title: "Template Review Requested",
      message: `You have been assigned to review a compliance template`,
      type: "REVIEW",
      link: `/master/compliance-templates/${id}`,
    })

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "TEMPLATE_SENT_TO_REVIEWER",
      entity: "ComplianceTemplate",
      entityId: id,
      newValue: JSON.stringify({ reviewerId: body.reviewerId }),
    })

    const { data: full } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, country:countries(id, name, code), form:form_master(id, formNumber, formName), entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber)), createdBy:users!compliance_templates_createdById_fkey(id, name, email), reviewer:users!compliance_templates_reviewerId_fkey(id, name, email)")
      .eq("id", id)
      .single()

    return NextResponse.json({ data: full })
  } catch (error) {
    console.error("POST /api/templates/[id]/send-to-reviewer error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
