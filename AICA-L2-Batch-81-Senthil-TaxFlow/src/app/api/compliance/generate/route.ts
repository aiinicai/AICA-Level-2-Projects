import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { newId, now } from "@/lib/db"
import { calculateNextDueDate, advanceTaxPeriod } from "@/lib/recurrence-date"
import { NextResponse } from "next/server"

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const body = await request.json()
    const { lookAheadDays } = body
    const days = lookAheadDays || 30

    const currentTime = new Date()
    const ahead = new Date()
    ahead.setDate(ahead.getDate() + days)

    const { data: recurringSchedules, error: fetchError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("*, entities:compliance_entities(*), assignments:compliance_assignments(*), approvals:compliance_approvals(*)")
      .eq("isRecurring", true)
      .lte("dueDate", ahead.toISOString())
      .in("status", ["FILED", "CLOSED", "APPROVED"])

    if (fetchError) throw fetchError

    let generated = 0

    for (const schedule of recurringSchedules || []) {
      const nextDueDate = calculateNextDueDate(new Date(schedule.dueDate), schedule.frequency)
      if (!nextDueDate || nextDueDate <= currentTime) continue
      if (schedule.recurringEndDate && nextDueDate > new Date(schedule.recurringEndDate)) continue

      const nextTaxPeriod = advanceTaxPeriod(schedule.taxPeriod, schedule.frequency) || schedule.taxPeriod

      const { data: existingNext } = await supabaseAdmin
        .from("compliance_schedules")
        .select("id")
        .eq("entityId", schedule.entityId)
        .eq("taxType", schedule.taxType)
        .eq("taxPeriod", nextTaxPeriod)
        .eq("dueDate", nextDueDate.toISOString())
        .maybeSingle()

      if (existingNext) continue

      const digits = Math.floor(10000 + Math.random() * 90000)
      const complianceId = `TAX-${digits}`

      const { data: newSchedule, error: createError } = await supabaseAdmin
        .from("compliance_schedules")
        .insert({
          id: newId(),
          orgId: schedule.orgId,
          complianceId,
          entityId: schedule.entityId,
          countryId: schedule.countryId,
          taxType: schedule.taxType,
          complianceTypeId: schedule.complianceTypeId ?? null,
          formId: schedule.formId,
          taxPeriod: nextTaxPeriod,
          frequency: schedule.frequency,
          dueDate: nextDueDate.toISOString(),
          priority: schedule.priority,
          status: "PENDING_PREPARATION",
          source: schedule.source || "MANUAL",
          isRecurring: schedule.isRecurring,
          notes: schedule.notes,
          updatedAt: now(),
        })
        .select("id")
        .single()

      if (createError) throw createError

      if (schedule.entities?.length > 0) {
        const { error: entityLinkError } = await supabaseAdmin
          .from("compliance_entities")
          .insert(
            schedule.entities.map((e: { entityId: string }) => ({
              id: newId(),
              complianceId: newSchedule.id,
              entityId: e.entityId,
            }))
          )

        if (entityLinkError) throw entityLinkError
      }

      if (schedule.assignments?.length > 0) {
        const { error: assignError } = await supabaseAdmin
          .from("compliance_assignments")
          .insert(
            schedule.assignments.map((a: { preparerId: string }) => ({
              id: newId(),
              complianceId: newSchedule.id,
              preparerId: a.preparerId,
              updatedAt: now(),
            }))
          )

        if (assignError) throw assignError
      }

      if (schedule.approvals?.length > 0) {
        const { error: approvalError } = await supabaseAdmin
          .from("compliance_approvals")
          .insert(
            schedule.approvals.map((a: { approverId: string; step?: number }) => ({
              id: newId(),
              complianceId: newSchedule.id,
              approverId: a.approverId,
              step: a.step || 1,
              status: "PENDING_APPROVAL",
              updatedAt: now(),
            }))
          )

        if (approvalError) throw approvalError
      }

      const { error: activityError } = await supabaseAdmin
        .from("activities")
        .insert({
          id: newId(),
          complianceId: schedule.id,
          userId: session.user.id,
          action: "RECURRING_GENERATED",
          comments: `Generated next recurring compliance due ${nextDueDate.toISOString().split("T")[0]}`,
        })

      if (activityError) throw activityError

      generated++
    }

    return NextResponse.json({ data: { generated, message: `${generated} recurring compliance(s) generated` } })
  } catch (error) {
    console.error("POST /api/compliance/generate error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
