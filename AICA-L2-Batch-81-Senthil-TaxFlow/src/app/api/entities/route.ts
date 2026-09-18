import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { APPROVAL_FLOWS, normalizeApprovalFlow, type ApprovalFlow } from "@/lib/approval-flow"
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
    const countryId = searchParams.get("countryId") || ""

    let query = supabaseAdmin
      .from("legal_entities")
      .select("*, country:countries(*)", { count: "exact", head: false })
      .eq("orgId", orgId)

    if (countryId) {
      query = query.eq("countryId", countryId)
    }

    if (search) {
      const pattern = `*${search}*`
      query = query.or(
        `entityNumber.ilike.${pattern},entityName.ilike.${pattern},taxRegistrationNumber.ilike.${pattern}`
      )
    }

    query = query.order("entityName", { ascending: true })

    const { data, count, error } = await query

    if (error) throw error

    return NextResponse.json({ data: data || [], total: count ?? 0 })
  } catch (error) {
    console.error("GET /api/entities error:", error)
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
    const { entityNumber, entityName, countryId, status, taxRegistrationNumber, currency, approvalFlow } = body

    if (!entityNumber || !entityName || !countryId) {
      return NextResponse.json({ error: "entityNumber, entityName, and countryId are required" }, { status: 400 })
    }

    if (approvalFlow !== undefined && !APPROVAL_FLOWS.includes(approvalFlow as ApprovalFlow)) {
      return NextResponse.json({ error: "approvalFlow must be NONE, ONE_LEVEL, or TWO_LEVEL" }, { status: 400 })
    }
    const flow = normalizeApprovalFlow(approvalFlow)

    const { data: existing, error: existingError } = await supabaseAdmin
      .from("legal_entities")
      .select("id")
      .eq("orgId", orgId)
      .eq("entityNumber", entityNumber)
      .maybeSingle()

    if (existingError) throw existingError

    if (existing) {
      return NextResponse.json({ error: "Entity with this number already exists in this organization" }, { status: 400 })
    }

    const { data, error } = await supabaseAdmin
      .from("legal_entities")
      .insert({
        id: newId(),
        orgId,
        entityNumber,
        entityName,
        countryId,
        status: status ?? "ACTIVE",
        taxRegistrationNumber,
        currency: currency ?? "USD",
        approvalFlow: flow,
        updatedAt: now(),
      })
      .select("*, country:countries(*)")
      .single()

    if (error) throw error

    return NextResponse.json({ data }, { status: 201 })
  } catch (error) {
    console.error("POST /api/entities error:", error)
    return NextResponse.json({ error: `Internal server error: ${(error as Error).message}` }, { status: 500 })
  }
}
