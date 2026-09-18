import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { APPROVAL_FLOWS, type ApprovalFlow } from "@/lib/approval-flow"
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
      const { formNumber, formName, taxType, description, complianceTypeId, countryId, requiresPayment, approvalFlow } = item
      const normalizedRequiresPayment =
        requiresPayment === undefined ? true : /^(yes|true|1)$/i.test(String(requiresPayment).trim())
      const normalizedApprovalFlow = approvalFlow ? String(approvalFlow).trim().toUpperCase() : "ONE_LEVEL"

      if (!APPROVAL_FLOWS.includes(normalizedApprovalFlow as ApprovalFlow)) {
        skipped++
        errors.push(`Invalid approvalFlow for ${formNumber || "unknown"}; must be NONE, ONE_LEVEL, or TWO_LEVEL`)
        continue
      }

      if (!formNumber || !formName) {
        skipped++
        errors.push(`Missing required fields for ${formNumber || "unknown"}`)
        continue
      }

      const effectiveCountryId = countryId || null

      const countryIdQuery = effectiveCountryId === null
        ? supabaseAdmin.from("form_master").select("id").is("countryId", null)
        : supabaseAdmin.from("form_master").select("id").eq("countryId", effectiveCountryId)

      const { data: existing } = await countryIdQuery
        .eq("orgId", orgId)
        .eq("formNumber", formNumber)
        .maybeSingle()

      if (existing) {
        const updateData: Record<string, unknown> = { updatedAt: now() }
        if (formName !== undefined) updateData.formName = formName
        if (taxType !== undefined) updateData.taxType = taxType || null
        if (complianceTypeId !== undefined) updateData.complianceTypeId = complianceTypeId || null
        if (description !== undefined) updateData.description = description
        if (requiresPayment !== undefined) updateData.requiresPayment = normalizedRequiresPayment
        if (approvalFlow !== undefined) updateData.approvalFlow = normalizedApprovalFlow

        const { error: updateError } = await supabaseAdmin
          .from("form_master")
          .update(updateData)
          .eq("id", existing.id)

        if (updateError) {
          errors.push(`Update failed for ${formNumber}: ${updateError.message}`)
        } else {
          inserted++
        }
      } else {
        const id = newId()
        const { error: insertError } = await supabaseAdmin
          .from("form_master")
          .insert({
            id,
            orgId,
            formNumber,
            formName,
            taxType: taxType || null,
            complianceTypeId: complianceTypeId || null,
            countryId: effectiveCountryId,
            description,
            requiresPayment: normalizedRequiresPayment,
            approvalFlow: normalizedApprovalFlow,
            updatedAt: now(),
          })

        if (insertError) {
          errors.push(`Insert failed for ${formNumber}: ${insertError.message}`)
        } else {
          inserted++
        }
      }
    }

    return NextResponse.json({
      data: { inserted, skipped, total: items.length, errors: errors.length > 0 ? errors : undefined },
    })
  } catch (error) {
    console.error("POST /api/forms/upload error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
