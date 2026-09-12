import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { computeGeneration, parseDate, type GenerationResult } from "@/lib/compliance-period"
import { insertGeneratedCompliance } from "@/lib/template-compliance"
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
      return NextResponse.json({ error: "Only administrators can generate compliances" }, { status: 403 })
    }

    const { id } = await params
    const body = await request.json()
    const { filingMonth } = body

    if (!filingMonth) {
      return NextResponse.json({ error: "filingMonth is required (e.g. 2026-08)" }, { status: 400 })
    }

    const { data: template, error: templateError } = await supabaseAdmin
      .from("compliance_templates")
      .select("*, entities:compliance_template_entities(entityId)")
      .eq("id", id)
      .eq("orgId", orgId)
      .single()

    if (templateError && templateError.code !== "PGRST116") throw templateError

    if (!template) {
      return NextResponse.json({ error: "Template not found" }, { status: 404 })
    }
    if (template.status !== "APPROVED") {
      return NextResponse.json({ error: "Only approved templates can generate compliances" }, { status: 400 })
    }
    if (!template.isActive) {
      return NextResponse.json({ error: "Template is inactive" }, { status: 400 })
    }

    if (template.recurringEndDate) {
      const [fYear, fMonth] = filingMonth.split("-").map(Number)
      const filingDate = new Date(fYear, fMonth - 1, 1)
      if (filingDate > parseDate(template.recurringEndDate)) {
        return NextResponse.json({ error: "Filing month exceeds recurring end date" }, { status: 400 })
      }
    }

    const templateEntities = (template.entities || []) as Array<{ entityId: string }>
    const entityIds = templateEntities.map((te) => te.entityId)

    const generated: Array<{ entityId: string | null; complianceId: string }> = []
    const futureNotGenerated: Array<{ entityId: string | null; reason: string }> = []
    const overlapSkipped: Array<{ entityId: string | null; reason: string }> = []
    const existingSkipped: Array<{ entityId: string | null; reason: string }> = []
    const errors: Array<{ entityId: string | null; error: string }> = []

    if (!entityIds.length) {
      return NextResponse.json({
        data: {
          generated,
          futureNotGenerated,
          overlapSkipped,
          existingSkipped,
          errors,
          summary: { created: 0, skipped: 0, futureNotGenerated: 0, overlapSkipped: 0, existingSkipped: 0, failed: 0 },
        },
      })
    }

    const { data: existingRows, error: existingError } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id, complianceId, entityId, taxPeriodStart, taxPeriodEnd, filingMonth")
      .eq("templateId", template.id)
    if (existingError) throw existingError

    const { data: entities, error: entitiesError } = await supabaseAdmin
      .from("legal_entities")
      .select("id, countryId")
      .in("id", entityIds)
    if (entitiesError && entitiesError.code !== "PGRST116") throw entitiesError

    const countryByEntity = new Map<string, string>()
    for (const e of (entities || []) as Array<{ id: string; countryId: string }>) {
      countryByEntity.set(e.id, e.countryId)
    }

    try {
      const rows = (existingRows || []) as Array<{
        id: string
        complianceId: string
        entityId: string | null
        taxPeriodStart: string | null
        taxPeriodEnd: string | null
        filingMonth: string | null
      }>

      const existingPeriods = rows.map((r) => ({ start: r.taxPeriodStart, end: r.taxPeriodEnd }))
      const existingFilingMonths = rows.map((r) => r.filingMonth)
      const latest = rows.reduce<Record<string, unknown> | null>((acc, r) => {
        if (!r.taxPeriodEnd) return acc
        if (!acc || parseDate(r.taxPeriodEnd) > parseDate(acc.taxPeriodEnd as string)) return r
        return acc
      }, null)

      const generation: GenerationResult = computeGeneration({
        frequency: template.frequency as string,
        periodEndDate: (template.periodEndDate as string | null | undefined) ?? null,
        dueDaysAfterPeriodEnd: template.dueDaysAfterPeriodEnd as number | undefined,
        paymentDueDaysAfterPeriodEnd: template.paymentDueDaysAfterPeriodEnd as number | undefined,
        filingMonth,
        latestComplianceEnd: (latest?.taxPeriodEnd as string | null) ?? null,
        existingPeriods,
        existingFilingMonths,
      })

      if (generation.bucket === "existing") {
        existingSkipped.push({
          entityId: null,
          reason: generation.reason || `Compliance already exists for ${filingMonth}`,
        })
        return NextResponse.json({
          data: {
            generated,
            futureNotGenerated,
            overlapSkipped,
            existingSkipped,
            errors,
            summary: {
              created: 0,
              skipped: 1,
              futureNotGenerated: 0,
              overlapSkipped: 0,
              existingSkipped: 1,
              failed: 0,
            },
          },
        })
      }

      if (generation.bucket === "overlap") {
        overlapSkipped.push({ entityId: null, reason: generation.reason || "Overlap" })
        return NextResponse.json({
          data: {
            generated,
            futureNotGenerated,
            overlapSkipped,
            existingSkipped,
            errors,
            summary: {
              created: 0,
              skipped: 1,
              futureNotGenerated: 0,
              overlapSkipped: 1,
              existingSkipped: 0,
              failed: 0,
            },
          },
        })
      }

      if (generation.bucket === "future") {
        futureNotGenerated.push({ entityId: null, reason: generation.reason || "Future period" })
        return NextResponse.json({
          data: {
            generated,
            futureNotGenerated,
            overlapSkipped,
            existingSkipped,
            errors,
            summary: {
              created: 0,
              skipped: 1,
              futureNotGenerated: 1,
              overlapSkipped: 0,
              existingSkipped: 0,
              failed: 0,
            },
          },
        })
      }

      if (!generation.periodStart || !generation.periodEnd || !generation.dueDate || !generation.paymentDueDate) {
        throw new Error("Generation result missing period or due dates")
      }

      const filingEntityId = (template.filingEntityId as string | null | undefined) || entityIds[0]
      const { complianceId } = await insertGeneratedCompliance({
        template: template as {
          id: string
          templateNumber?: string | null
          version?: number | null
          taxType?: string | null
          formId?: string | null
          countryId?: string | null
          filingEntityId?: string | null
          frequency?: string | null
          priority?: string | null
          isRecurring?: boolean | null
          recurringEndDate?: string | null
          notes?: string | null
          preparerId?: string | null
          approverId?: string | null
        },
        entityIds,
        countryId:
          countryByEntity.get(filingEntityId) ||
          countryByEntity.get(entityIds[0]) ||
          template.countryId ||
          "",
        orgId,
        userId: session.user.id,
        filingMonth,
        generation: {
          periodStart: generation.periodStart,
          periodEnd: generation.periodEnd,
          dueDate: generation.dueDate,
          paymentDueDate: generation.paymentDueDate,
        },
      })

      generated.push({ entityId: filingEntityId, complianceId })

      return NextResponse.json({
        data: {
          generated,
          futureNotGenerated,
          overlapSkipped,
          existingSkipped,
          errors,
          summary: {
            created: generated.length,
            skipped: futureNotGenerated.length + overlapSkipped.length + existingSkipped.length,
            futureNotGenerated: futureNotGenerated.length,
            overlapSkipped: overlapSkipped.length,
            existingSkipped: existingSkipped.length,
            failed: errors.length,
          },
        },
      })
    } catch (err) {
      errors.push({ entityId: entityIds[0] || null, error: err instanceof Error ? err.message : "Unknown error" })
      return NextResponse.json({
        data: {
          generated,
          futureNotGenerated,
          overlapSkipped,
          existingSkipped,
          errors,
          summary: { created: 0, skipped: 0, futureNotGenerated: 0, overlapSkipped: 0, existingSkipped: 0, failed: 1 },
        },
      })
    }
  } catch (error) {
    console.error("POST /api/templates/[id]/generate error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
