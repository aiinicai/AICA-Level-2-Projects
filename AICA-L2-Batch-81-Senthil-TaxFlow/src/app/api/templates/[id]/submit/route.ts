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

    const { orgId } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }

    const { id } = await params
    const body = await request.json().catch(() => ({}))

    const { data: existing, error: fetchError } = await supabaseAdmin
      .from("compliance_templates")
      .select("*")
      .eq("id", id)
      .eq("orgId", orgId)
      .single()

    if (fetchError || !existing) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    if (existing.status !== "DRAFT") {
      return NextResponse.json({ error: "Only draft templates can be submitted" }, { status: 400 })
    }

    const { error: updateError } = await supabaseAdmin
      .from("compliance_templates")
      .update({
        status: "PENDING_ADMIN_APPROVAL",
        submittedAt: now(),
        submittedById: session.user.id,
        updatedAt: now(),
      })
      .eq("id", id)

    if (updateError) throw updateError

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "TEMPLATE_SUBMITTED",
      entity: "ComplianceTemplate",
      entityId: id,
      comments: body.comments || "Template submitted for admin approval",
    })

    const { data: full } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, country:countries(id, name, code), form:form_master(id, formNumber, formName), entities:compliance_template_entities(*, entity:legal_entities(id, entityName, entityNumber)), createdBy:users!compliance_templates_createdById_fkey(id, name, email)")
      .eq("id", id)
      .single()

    return NextResponse.json({ data: full })
  } catch (error) {
    console.error("POST /api/templates/[id]/submit error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
