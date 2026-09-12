import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import {
  buildApprovalRecords,
  normalizeApprovalFlow,
  requiresApprover,
  requiresReviewer,
} from "@/lib/approval-flow"
import { NextResponse } from "next/server"

const VALID_FREQUENCIES = new Set(["WEEKLY", "MONTHLY", "BI_MONTHLY", "QUARTERLY", "HALF_YEARLY", "ANNUAL", "AD_HOC"])
const VALID_TAX_TYPES = new Set(["VAT", "GST", "SALES_TAX", "WHT", "CORPORATE_TAX", "STATUTORY"])
const VALID_PRIORITIES = new Set(["NORMAL", "HIGH", "CRITICAL"])

function normalize(value: unknown): string {
  return String(value || "").trim().toUpperCase()
}

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }

    const { items } = await request.json()
    if (!items || !Array.isArray(items) || items.length === 0) {
      return NextResponse.json({ error: "Items array is required" }, { status: 400 })
    }

    const [{ data: entities }, { data: countries }, { data: members }] = await Promise.all([
      supabaseAdmin
        .from("legal_entities")
        .select("id, entityNumber, entityName, countryId, approvalFlow")
        .eq("orgId", orgId),
      supabaseAdmin.from("countries").select("id, name, code"),
      supabaseAdmin
        .from("organization_members")
        .select("userId, user:users!userId(email)"),
    ])

    const entityMap = new Map<string, { id: string; countryId: string | null; approvalFlow: string }>()
    for (const e of entities || []) {
      const key = String(e.entityNumber || "").trim().toLowerCase()
      if (key) entityMap.set(key, { id: e.id, countryId: e.countryId, approvalFlow: e.approvalFlow || "ONE_LEVEL" })
    }

    const userByEmail = new Map<string, string>()
    for (const m of members || []) {
      const email = String((m.user as { email?: string } | null)?.email || "").trim().toLowerCase()
      if (email) userByEmail.set(email, m.userId)
    }

    const countryMap = new Map<string, string>()
    for (const c of countries || []) {
      if (c.code) countryMap.set(String(c.code).trim().toLowerCase(), c.id)
      if (c.name) countryMap.set(String(c.name).trim().toLowerCase(), c.id)
    }

    let inserted = 0
    let skipped = 0
    const errors: string[] = []

    for (const item of items) {
      const { entityNumber, country, taxType, taxPeriod, dueDate, frequency, priority, notes, reviewer, approver } = item
      const rowLabel = entityNumber || "unknown"

      if (!entityNumber || !taxType || !taxPeriod || !dueDate) {
        skipped++
        errors.push(`Missing required fields for ${rowLabel}`)
        continue
      }

      const taxTypeCode = normalize(taxType)
      if (!VALID_TAX_TYPES.has(taxTypeCode)) {
        skipped++
        errors.push(`Invalid taxType "${taxType}" for ${rowLabel}`)
        continue
      }

      const frequencyCode = frequency ? normalize(frequency) : "AD_HOC"
      if (!VALID_FREQUENCIES.has(frequencyCode)) {
        skipped++
        errors.push(`Invalid frequency "${frequency}" for ${rowLabel}`)
        continue
      }

      const priorityCode = priority ? normalize(priority) : "NORMAL"
      if (!VALID_PRIORITIES.has(priorityCode)) {
        skipped++
        errors.push(`Invalid priority "${priority}" for ${rowLabel}`)
        continue
      }

      const due = new Date(dueDate)
      if (isNaN(due.getTime())) {
        skipped++
        errors.push(`Invalid dueDate "${dueDate}" for ${rowLabel}`)
        continue
      }

      const entity = entityMap.get(String(entityNumber).trim().toLowerCase())
      if (!entity) {
        skipped++
        errors.push(`Entity "${entityNumber}" not found`)
        continue
      }

      let countryId = entity.countryId
      if (country) {
        const matched = countryMap.get(String(country).trim().toLowerCase())
        if (matched) countryId = matched
      }

      const reviewerId = reviewer ? userByEmail.get(String(reviewer).trim().toLowerCase()) : undefined
      const approverId = approver ? userByEmail.get(String(approver).trim().toLowerCase()) : undefined
      const flow = normalizeApprovalFlow(entity.approvalFlow)

      if (requiresApprover(flow) && (!reviewerId || !approverId)) {
        skipped++
        errors.push(`Reviewer and approver are required for ${rowLabel} (two-level approval)`)
        continue
      }
      if (requiresReviewer(flow) && !reviewerId) {
        skipped++
        errors.push(`Reviewer is required for ${rowLabel} (one-level approval)`)
        continue
      }

      const { data: existing } = await supabaseAdmin
        .from("compliance_schedules")
        .select("id")
        .eq("orgId", orgId)
        .eq("entityId", entity.id)
        .eq("taxType", taxTypeCode)
        .eq("taxPeriod", taxPeriod)
        .eq("dueDate", due.toISOString())
        .maybeSingle()

      if (existing) {
        skipped++
        errors.push(`Duplicate compliance for ${rowLabel} (${taxTypeCode}, ${taxPeriod})`)
        continue
      }

      const digits = Math.floor(10000 + Math.random() * 90000)
      const complianceId = `TAX-${digits}`
      const scheduleId = newId()

      const { error: insertError } = await supabaseAdmin.from("compliance_schedules").insert({
        id: scheduleId,
        orgId,
        complianceId,
        entityId: entity.id,
        countryId,
        taxType: taxTypeCode,
        taxPeriod,
        frequency: frequencyCode,
        dueDate: due.toISOString(),
        priority: priorityCode,
        status: "DRAFT",
        source: "IMPORT",
        isRecurring: false,
        notes: notes || null,
        updatedAt: now(),
        createdById: session.user.id,
      })

      if (insertError) {
        skipped++
        errors.push(`Insert failed for ${rowLabel}: ${insertError.message}`)
        continue
      }

      const { error: linkError } = await supabaseAdmin.from("compliance_entities").insert({
        id: newId(),
        complianceId: scheduleId,
        entityId: entity.id,
      })

      if (linkError) {
        skipped++
        errors.push(`Link failed for ${rowLabel}: ${linkError.message}`)
        continue
      }

      const approvalRecords = buildApprovalRecords(flow, reviewerId, approverId)

      if (approvalRecords.length > 0) {
        const { error: approvalError } = await supabaseAdmin.from("compliance_approvals").insert(
          approvalRecords.map((record) => ({
            id: newId(),
            complianceId: scheduleId,
            approverId: record.approverId,
            step: record.step,
            status: "PENDING_APPROVAL",
            updatedAt: now(),
          }))
        )

        if (approvalError) {
          skipped++
          errors.push(`Approval setup failed for ${rowLabel}: ${approvalError.message}`)
          continue
        }
      }

      inserted++
    }

    return NextResponse.json({
      data: {
        inserted,
        skipped,
        total: items.length,
        errors: errors.length > 0 ? errors : undefined,
      },
    })
  } catch (error) {
    console.error("POST /api/compliance/import error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
