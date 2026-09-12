import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { APPROVAL_FLOWS, normalizeApprovalFlow, type ApprovalFlow } from "@/lib/approval-flow"
import { NextResponse } from "next/server"

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

    let inserted = 0
    let skipped = 0
    const errors: string[] = []

    for (const item of items) {
      const { entityNumber, entityName, countryId, status, taxRegistrationNumber, currency, approvalFlow } = item

      if (!entityNumber || !entityName || !countryId) {
        skipped++
        errors.push(`Missing required fields for ${entityNumber || "unknown"}`)
        continue
      }

      if (approvalFlow !== undefined && !APPROVAL_FLOWS.includes(approvalFlow as ApprovalFlow)) {
        skipped++
        errors.push(`Invalid approvalFlow for ${entityNumber}; must be NONE, ONE_LEVEL, or TWO_LEVEL`)
        continue
      }
      const flow = normalizeApprovalFlow(approvalFlow)

      const { data: existing } = await supabaseAdmin
        .from("legal_entities")
        .select("id")
        .eq("orgId", orgId)
        .eq("entityNumber", entityNumber)
        .maybeSingle()

      if (existing) {
        const { error: updateError } = await supabaseAdmin
          .from("legal_entities")
          .update({
            entityName,
            countryId,
            status: status || "ACTIVE",
            taxRegistrationNumber,
            currency: currency || "USD",
            approvalFlow: flow,
            updatedAt: now(),
          })
          .eq("id", existing.id)

        if (updateError) {
          errors.push(`Update failed for ${entityNumber}: ${updateError.message}`)
        } else {
          inserted++
        }
      } else {
        const { error: insertError } = await supabaseAdmin
          .from("legal_entities")
          .insert({
            id: newId(),
            orgId,
            entityNumber,
            entityName,
            countryId,
            status: status || "ACTIVE",
            taxRegistrationNumber,
            currency: currency || "USD",
            approvalFlow: flow,
            updatedAt: now(),
          })

        if (insertError) {
          errors.push(`Insert failed for ${entityNumber}: ${insertError.message}`)
        } else {
          inserted++
        }
      }
    }

    return NextResponse.json({
      data: { inserted, skipped, total: items.length, errors: errors.length > 0 ? errors : undefined },
    })
  } catch (error) {
    console.error("POST /api/entities/upload error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
