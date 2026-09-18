import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
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
      .from("legal_entities")
      .select("*, country:countries(*)")
      .eq("id", id)
      .maybeSingle()

    if (error) throw error

    if (!data) {
      return NextResponse.json({ error: "Entity not found" }, { status: 404 })
    }

    return NextResponse.json({ data })
  } catch (error) {
    console.error("GET /api/entities/[id] error:", error)
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
    const { entityNumber, entityName, countryId, status, taxRegistrationNumber, currency, approvalFlow } = body

    if (approvalFlow !== undefined && !APPROVAL_FLOWS.includes(approvalFlow as ApprovalFlow)) {
      return NextResponse.json({ error: "approvalFlow must be NONE, ONE_LEVEL, or TWO_LEVEL" }, { status: 400 })
    }

    const { data: existing, error: fetchError } = await supabaseAdmin
      .from("legal_entities")
      .select("*")
      .eq("id", id)
      .maybeSingle()

    if (fetchError) throw fetchError

    if (!existing) {
      return NextResponse.json({ error: "Entity not found" }, { status: 404 })
    }

    if (entityNumber && entityNumber !== existing.entityNumber && orgId) {
      const { data: conflict } = await supabaseAdmin
        .from("legal_entities")
        .select("id")
        .eq("orgId", orgId)
        .eq("entityNumber", entityNumber)
        .neq("id", id)
        .maybeSingle()

      if (conflict) {
        return NextResponse.json({ error: "Entity with this number already exists in this organization" }, { status: 400 })
      }
    }

    const { data, error } = await supabaseAdmin
      .from("legal_entities")
      .update({
        ...(entityNumber !== undefined && { entityNumber }),
        ...(entityName !== undefined && { entityName }),
        ...(countryId !== undefined && { countryId }),
        ...(status !== undefined && { status }),
        ...(taxRegistrationNumber !== undefined && { taxRegistrationNumber }),
        ...(currency !== undefined && { currency }),
        ...(approvalFlow !== undefined && { approvalFlow }),
      })
      .eq("id", id)
      .select("*, country:countries(*)")
      .single()

    if (error) throw error

    return NextResponse.json({ data })
  } catch (error) {
    console.error("PUT /api/entities/[id] error:", error)
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
      .from("legal_entities")
      .select("id")
      .eq("id", id)
      .maybeSingle()

    if (fetchError) throw fetchError

    if (!existing) {
      return NextResponse.json({ error: "Entity not found" }, { status: 404 })
    }

    const { error } = await supabaseAdmin
      .from("legal_entities")
      .delete()
      .eq("id", id)

    if (error) throw error

    return NextResponse.json({ data: { message: "Entity deleted successfully" } })
  } catch (error) {
    console.error("DELETE /api/entities/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
