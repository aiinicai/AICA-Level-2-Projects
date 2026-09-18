import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { now } from "@/lib/db"
import { APPROVAL_FLOWS, type ApprovalFlow } from "@/lib/approval-flow"
import { NextResponse } from "next/server"

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params

    const { data, error } = await supabaseAdmin
      .from("form_master")
      .select("id, formNumber, formName, taxType, description, requiresPayment, approvalFlow, complianceTypeId, complianceType:compliance_types(id, name, taxType)")
      .eq("id", id)
      .maybeSingle()

    if (error) throw error

    if (!data) {
      return NextResponse.json({ error: "Form not found" }, { status: 404 })
    }

    return NextResponse.json({ data })
  } catch (error) {
    console.error("GET /api/forms/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId } = getActiveContextFromRequest(request)

    const { id } = await params
    const body = await request.json()
    const { formNumber, formName, taxType, description, complianceTypeId, countryId, requiresPayment, approvalFlow } = body

    if (approvalFlow !== undefined && !APPROVAL_FLOWS.includes(approvalFlow as ApprovalFlow)) {
      return NextResponse.json({ error: "approvalFlow must be NONE, ONE_LEVEL, or TWO_LEVEL" }, { status: 400 })
    }

    const { data: existing, error: fetchError } = await supabaseAdmin
      .from("form_master")
      .select("*")
      .eq("id", id)
      .maybeSingle()

    if (fetchError) throw fetchError

    if (!existing) {
      return NextResponse.json({ error: "Form not found" }, { status: 404 })
    }

    const effectiveFormNumber = formNumber ?? existing.formNumber
    const effectiveCountryId = countryId !== undefined ? (countryId || null) : existing.countryId

    if (orgId) {
      const conflictQuery = effectiveCountryId === null
        ? supabaseAdmin.from("form_master").select("id").is("countryId", null)
        : supabaseAdmin.from("form_master").select("id").eq("countryId", effectiveCountryId)

      const { data: conflict } = await conflictQuery
        .eq("orgId", orgId)
        .eq("formNumber", effectiveFormNumber)
        .neq("id", id)
        .maybeSingle()

      if (conflict) {
        return NextResponse.json({ error: "Form with this number already exists in this organization for this country" }, { status: 400 })
      }
    }

    const updateData: Record<string, unknown> = { updatedAt: now() }
    if (formNumber !== undefined) updateData.formNumber = formNumber
    if (formName !== undefined) updateData.formName = formName
    if (taxType !== undefined) updateData.taxType = taxType || null
    if (complianceTypeId !== undefined) updateData.complianceTypeId = complianceTypeId || null
    if (countryId !== undefined) updateData.countryId = countryId || null
    if (description !== undefined) updateData.description = description
    if (requiresPayment !== undefined) updateData.requiresPayment = requiresPayment === true
    if (approvalFlow !== undefined) updateData.approvalFlow = approvalFlow

    const { data, error } = await supabaseAdmin
      .from("form_master")
      .update(updateData)
      .eq("id", id)
      .select("id, formNumber, formName, taxType, description, requiresPayment, approvalFlow, complianceTypeId, complianceType:compliance_types(id, name, taxType)")
      .single()

    if (error) throw error

    return NextResponse.json({ data })
  } catch (error) {
    console.error("PUT /api/forms/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params

    const { data: existing, error: fetchError } = await supabaseAdmin
      .from("form_master")
      .select("id")
      .eq("id", id)
      .maybeSingle()

    if (fetchError) throw fetchError

    if (!existing) {
      return NextResponse.json({ error: "Form not found" }, { status: 404 })
    }

    const { error } = await supabaseAdmin
      .from("form_master")
      .delete()
      .eq("id", id)

    if (error) throw error

    return NextResponse.json({ data: { message: "Form deleted successfully" } })
  } catch (error) {
    console.error("DELETE /api/forms/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
