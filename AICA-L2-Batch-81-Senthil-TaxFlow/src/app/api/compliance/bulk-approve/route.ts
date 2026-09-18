import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

const ALLOWED_FROM = ["DRAFT", "PENDING_ADMIN_APPROVAL"]

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId, activeRole } = getActiveContextFromRequest(request)
    const orgRoles = session.user.orgs.find((o) => o.id === orgId)?.roles || []
    const isAdmin = activeRole === "ADMINISTRATOR" || orgRoles.includes("ADMINISTRATOR")
    if (!isAdmin) {
      return NextResponse.json({ error: "Only administrators can bulk approve compliances" }, { status: 403 })
    }
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }

    const body = await request.json()
    const { ids, reviewerId, comments } = body as {
      ids?: string[]
      reviewerId?: string
      comments?: string
    }

    if (!ids || !Array.isArray(ids) || ids.length === 0) {
      return NextResponse.json({ error: "ids array is required" }, { status: 400 })
    }

    const { data: schedules, error: fetchError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*, assignments:compliance_assignments(preparerId)")
      .eq("orgId", orgId)
      .in("id", ids)

    if (fetchError) throw fetchError

    if (reviewerId && orgId) {
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

    const toStatus = reviewerId ? "PENDING_REVIEW" : "PENDING_PREPARATION"
    const action = reviewerId ? "SENT_TO_REVIEWER" : "ADMIN_APPROVED"

    let approved = 0
    let skipped = 0
    const errors: string[] = []

    for (const schedule of schedules || []) {
      if (schedule.source === "TEMPLATE") {
        skipped++
        errors.push(`Compliance ${schedule.complianceId} is template-sourced and cannot be approved directly`)
        continue
      }
      if (!ALLOWED_FROM.includes(schedule.status)) {
        skipped++
        errors.push(`Compliance ${schedule.complianceId} is not in DRAFT or PENDING_ADMIN_APPROVAL`)
        continue
      }

      const updateData: Record<string, unknown> = {
        status: toStatus,
        updatedAt: now(),
      }
      if (reviewerId) {
        updateData.reviewerId = reviewerId
        updateData.adminComments = comments || null
      }

      const { error: updateError } = await supabaseAdmin
        .from("compliance_schedules")
        .update(updateData)
        .eq("id", schedule.id)

      if (updateError) {
        skipped++
        errors.push(`Update failed for ${schedule.complianceId}: ${updateError.message}`)
        continue
      }

      await supabaseAdmin.from("activities").insert({
        id: newId(),
        complianceId: schedule.id,
        userId: session.user.id,
        action,
        fromStatus: schedule.status,
        toStatus,
        comments: comments || undefined,
      })

      await supabaseAdmin.from("audit_trails").insert({
        id: newId(),
        userId: session.user.id,
        action: reviewerId ? "SEND_TO_REVIEWER" : "ADMIN_APPROVE",
        entity: "ComplianceSchedule",
        entityId: schedule.id,
        oldValue: schedule.status,
        newValue: toStatus,
        comments: comments || undefined,
      })

      if (!reviewerId && schedule.assignments?.length > 0) {
        const notifications = schedule.assignments.map((a: { preparerId: string }) => ({
          id: newId(),
          userId: a.preparerId,
          title: "Compliance Ready for Preparation",
          message: `Compliance ${schedule.complianceId} has been approved by admin and is ready for preparation`,
          type: "APPROVAL",
          link: `/compliance/${schedule.id}`,
        }))
        await supabaseAdmin.from("notifications").insert(notifications)
      }

      approved++
    }

    return NextResponse.json({
      data: {
        approved,
        skipped,
        total: ids.length,
        errors: errors.length > 0 ? errors : undefined,
      },
    })
  } catch (error) {
    console.error("POST /api/compliance/bulk-approve error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
