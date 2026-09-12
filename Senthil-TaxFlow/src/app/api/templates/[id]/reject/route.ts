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
    const { id } = await params
    const body = await request.json()

    if (!body.comments) {
      return NextResponse.json({ error: "Rejection reason is required" }, { status: 400 })
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

    const isAdmin = activeRole === "ADMINISTRATOR"
    const isReviewer = existing.reviewerId === session.user.id

    if (existing.status === "PENDING_ADMIN_APPROVAL" && !isAdmin) {
      return NextResponse.json({ error: "Only administrators can reject" }, { status: 403 })
    }
    if (existing.status === "PENDING_REVIEW" && !isReviewer && !isAdmin) {
      return NextResponse.json({ error: "Only the assigned reviewer can reject" }, { status: 403 })
    }

    const { error: updateError } = await supabaseAdmin
      .from("compliance_templates")
      .update({
        status: "REJECTED",
        rejectedAt: now(),
        rejectedById: session.user.id,
        updatedAt: now(),
      })
      .eq("id", id)

    if (updateError) throw updateError

    if (existing.createdById) {
      await supabaseAdmin.from("notifications").insert({
        id: newId(),
        userId: existing.createdById,
        title: "Template Rejected",
        message: `Your compliance template has been rejected: ${body.comments}`,
        type: "REJECTION",
        link: `/master/compliance-templates/${id}`,
      })
    }

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "TEMPLATE_REJECTED",
      entity: "ComplianceTemplate",
      entityId: id,
      comments: body.comments,
    })

    const { data: full } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, country:countries(id, name, code), form:form_master(id, formNumber, formName), entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber)), createdBy:users!compliance_templates_createdById_fkey(id, name, email)")
      .eq("id", id)
      .single()

    return NextResponse.json({ data: full })
  } catch (error) {
    console.error("POST /api/templates/[id]/reject error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
