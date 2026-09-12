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
      return NextResponse.json({ error: "Only administrators can activate/deactivate templates" }, { status: 403 })
    }

    const { id } = await params
    const body = await request.json()

    const isActive = body.isActive ?? true

    const { data: existing } = await supabaseAdmin
      .from("compliance_templates")
      .select("id")
      .eq("id", id)
      .eq("orgId", orgId)
      .single()

    if (!existing) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }

    const { error } = await supabaseAdmin
      .from("compliance_templates")
      .update({ isActive, updatedAt: now() })
      .eq("id", id)

    if (error) throw error

    await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: isActive ? "TEMPLATE_ACTIVATED" : "TEMPLATE_DEACTIVATED",
      entity: "ComplianceTemplate",
      entityId: id,
    })

    return NextResponse.json({ data: { success: true, isActive } })
  } catch (error) {
    console.error("POST /api/templates/[id]/activate error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
