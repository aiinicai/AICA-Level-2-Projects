import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const body = await request.json()
    const { complianceId, content } = body

    if (!complianceId || !content) {
      return NextResponse.json(
        { error: "complianceId and content are required" },
        { status: 400 }
      )
    }

    const { data: compliance, error: complianceError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id")
      .eq("id", complianceId)
      .maybeSingle()
    if (complianceError) throw complianceError
    if (!compliance) {
      return NextResponse.json({ error: "Compliance not found" }, { status: 404 })
    }

    const { data, error } = await supabaseAdmin
      .from("comments")
      .insert({
        complianceId,
        userId: session.user.id,
        content,
      })
      .select("*, user:users!userId(id, name, email, image)")
      .single()
    if (error) throw error

    const { error: activityError } = await supabaseAdmin
      .from("activities")
      .insert({
        complianceId,
        userId: session.user.id,
        action: "COMMENTED",
        comments: content.slice(0, 100),
      })
    if (activityError) throw activityError

    const { error: auditError } = await supabaseAdmin
      .from("audit_trails")
      .insert({
        userId: session.user.id,
        action: "COMMENT",
        entity: "ComplianceSchedule",
        entityId: complianceId,
        comments: content.slice(0, 200),
      })
    if (auditError) throw auditError

    return NextResponse.json({ data }, { status: 201 })
  } catch (error) {
    console.error("POST /api/comments error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
