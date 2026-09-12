import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { APPROVAL_FLOWS, type ApprovalFlow } from "@/lib/approval-flow"
import { NextResponse } from "next/server"

export async function GET(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }

    const { searchParams } = new URL(request.url)
    const search = searchParams.get("search") || ""
    const complianceTypeId = searchParams.get("complianceTypeId") || ""
    const taxType = searchParams.get("taxType") || ""

    let query = supabaseAdmin
      .from("form_master")
      .select("id, formNumber, formName, taxType, description, requiresPayment, approvalFlow, complianceTypeId, complianceType:compliance_types(id, name, taxType)")
      .eq("orgId", orgId)

    if (complianceTypeId) {
      query = query.eq("complianceTypeId", complianceTypeId)
    }

    if (taxType) {
      query = query.eq("taxType", taxType)
    }

    if (search) {
      const pattern = `*${search}*`
      query = query.or(
        `formNumber.ilike.${pattern},formName.ilike.${pattern},description.ilike.${pattern}`
      )
    }

    query = query.order("formName", { ascending: true })

    const { data, error } = await query

    if (error) throw error

    return NextResponse.json({ data: data || [] })
  } catch (error) {
    console.error("GET /api/forms error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
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

    const body = await request.json()
    const { formNumber, formName, taxType, description, complianceTypeId, countryId, requiresPayment, approvalFlow } = body

    if (!formNumber || !formName) {
      return NextResponse.json({ error: "formNumber and formName are required" }, { status: 400 })
    }

    if (approvalFlow !== undefined && !APPROVAL_FLOWS.includes(approvalFlow as ApprovalFlow)) {
      return NextResponse.json({ error: "approvalFlow must be NONE, ONE_LEVEL, or TWO_LEVEL" }, { status: 400 })
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
      return NextResponse.json({ error: "Form with this number already exists in this organization for this country" }, { status: 400 })
    }

    const id = newId()

    const { data, error } = await supabaseAdmin
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
        requiresPayment: requiresPayment === undefined ? true : requiresPayment === true,
        approvalFlow: approvalFlow || "ONE_LEVEL",
        updatedAt: now(),
      })
      .select("id, formNumber, formName, taxType, description, requiresPayment, approvalFlow, complianceTypeId, complianceType:compliance_types(id, name, taxType)")
      .single()

    if (error) throw error

    return NextResponse.json({ data }, { status: 201 })
  } catch (error) {
    console.error("POST /api/forms error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
