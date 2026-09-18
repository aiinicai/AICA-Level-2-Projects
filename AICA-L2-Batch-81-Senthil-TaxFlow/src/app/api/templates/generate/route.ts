import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId } from "@/lib/db"
import { computeGeneration, parseDate, type GenerationResult } from "@/lib/compliance-period"
import { insertGeneratedCompliance } from "@/lib/template-compliance"
import { NextResponse } from "next/server"

export async function POST(request: Request) {
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

    const body = await request.json()
    const { filingMonth, filters } = body

    if (!filingMonth) {
      return NextResponse.json({ error: "filingMonth is required (e.g. 2026-08)" }, { status: 400 })
    }

    let query = supabaseAdmin
      .from("compliance_templates")
      .select("*, entities:compliance_template_entities(entityId), country:countries(code)")
      .eq("orgId", orgId)
      .eq("status", "APPROVED")
      .eq("isActive", true)

    if (filters?.countryIds?.length > 0) {
      query = query.in("countryId", filters.countryIds)
    }
    if (filters?.taxTypes?.length > 0) {
      query = query.in("taxType", filters.taxTypes)
    }
    if (filters?.formIds?.length > 0) {
      query = query.in("formId", filters.formIds)
    }

    const { data: templates, error: fetchError } = await query
    if (fetchError) throw fetchError

    let filteredTemplates = templates || []

    if (filters?.entityIds?.length > 0) {
      filteredTemplates = filteredTemplates.filter((t: Record<string, unknown>) =>
        (t.entities as Array<{ entityId: string }>)?.some((e) =>
          filters.entityIds.includes(e.entityId)
        )
      )
    }

    const generated: Array<{ templateId: string; templateNumber: string; entityId: string; complianceId: string }> = []
    const futureNotGenerated: Array<{ templateId: string; templateNumber: string; reason: string }> = []
    const overlapSkipped: Array<{ templateId: string; templateNumber: string; reason: string }> = []
    const existingSkipped: Array<{ templateId: string; templateNumber: string; reason: string }> = []
    const errors: Array<{ templateId: string; error: string }> = []

    const templateIds = filteredTemplates.map((t: { id: string }) => t.id)

    const { data: existingRows } = await supabaseAdmin
      .from("compliance_schedules")
      .select("id, complianceId, templateId, taxPeriodStart, taxPeriodEnd, filingMonth")
      .in("templateId", templateIds.length ? templateIds : ["__none__"])

    const existingByTemplate = new Map<string, Array<Record<string, unknown>>>()
    for (const row of (existingRows || []) as Array<Record<string, unknown>>) {
      const key = row.templateId as string
      const list = existingByTemplate.get(key) || []
      list.push(row)
      existingByTemplate.set(key, list)
    }

    const allEntityIds = Array.from(
      new Set(
        filteredTemplates.flatMap((t: Record<string, unknown>) =>
          ((t.entities as Array<{ entityId: string }>) || []).map((e) => e.entityId)
        )
      )
    )

    const { data: entityRows } = await supabaseAdmin
      .from("legal_entities")
      .select("id, countryId")
      .in("id", allEntityIds.length ? allEntityIds : ["__none__"])

    const countryByEntity = new Map<string, string>()
    for (const e of (entityRows || []) as Array<{ id: string; countryId: string }>) {
      countryByEntity.set(e.id, e.countryId)
    }

    const [fYear, fMonth] = filingMonth.split("-").map(Number)

    for (const template of filteredTemplates) {
      try {
        if (template.recurringEndDate) {
          const endDate = parseDate(template.recurringEndDate)
          const filingDate = new Date(fYear, fMonth - 1, 1)
          if (filingDate > endDate) {
            futureNotGenerated.push({
              templateId: template.id,
              templateNumber: template.templateNumber || "N/A",
              reason: "Filing month exceeds recurring end date",
            })
            continue
          }
        }

        const templateEntities = (template.entities || []) as Array<{ entityId: string }>
        const entityIds = templateEntities.map((te) => te.entityId)
        if (!entityIds.length) {
          futureNotGenerated.push({
            templateId: template.id,
            templateNumber: template.templateNumber || "N/A",
            reason: "Template has no entities",
          })
          continue
        }

        const rows = existingByTemplate.get(template.id) || []
        const existingPeriods = rows.map((r) => ({
          start: r.taxPeriodStart as string | null,
          end: r.taxPeriodEnd as string | null,
        }))
        const existingFilingMonths = rows.map((r) => r.filingMonth as string | null)
        const latest = rows.reduce<Record<string, unknown> | null>((acc, r) => {
          if (!r.taxPeriodEnd) return acc
          if (!acc || parseDate(r.taxPeriodEnd as string) > parseDate(acc.taxPeriodEnd as string)) return r
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
            templateId: template.id,
            templateNumber: template.templateNumber || "N/A",
            reason: generation.reason || `Compliance already exists for ${filingMonth}`,
          })
          continue
        }

        if (generation.bucket === "overlap") {
          overlapSkipped.push({
            templateId: template.id,
            templateNumber: template.templateNumber || "N/A",
            reason: generation.reason || "Overlap",
          })
          continue
        }

        if (generation.bucket === "future") {
          futureNotGenerated.push({
            templateId: template.id,
            templateNumber: template.templateNumber || "N/A",
            reason: generation.reason || "Future period",
          })
          continue
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

        generated.push({
          templateId: template.id,
          templateNumber: template.templateNumber || "N/A",
          entityId: filingEntityId,
          complianceId,
        })
      } catch (err) {
        errors.push({
          templateId: template.id,
          error: err instanceof Error ? err.message : "Unknown error",
        })
      }
    }

    const { error: auditError } = await supabaseAdmin.from("audit_trails").insert({
      id: newId(),
      userId: session.user.id,
      action: "BULK_GENERATE_COMPLIANCES",
      entity: "ComplianceTemplate",
      newValue: JSON.stringify({
        filingMonth,
        filters,
        generated: generated.length,
        futureNotGenerated: futureNotGenerated.length,
        overlapSkipped: overlapSkipped.length,
        existingSkipped: existingSkipped.length,
        errors: errors.length,
      }),
    })
    if (auditError) throw auditError

    return NextResponse.json({
      data: {
        generated,
        futureNotGenerated,
        overlapSkipped,
        existingSkipped,
        errors,
        summary: {
          total:
            generated.length +
            futureNotGenerated.length +
            overlapSkipped.length +
            existingSkipped.length +
            errors.length,
          created: generated.length,
          skipped: futureNotGenerated.length + overlapSkipped.length + existingSkipped.length,
          futureNotGenerated: futureNotGenerated.length,
          overlapSkipped: overlapSkipped.length,
          existingSkipped: existingSkipped.length,
          failed: errors.length,
        },
      },
    })
  } catch (error) {
    console.error("POST /api/templates/generate error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
