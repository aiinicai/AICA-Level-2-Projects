import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
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

    let query = supabaseAdmin
      .from("currencies")
      .select("*", { count: "exact", head: false })
      .eq("orgId", orgId)

    if (search) {
      const pattern = `*${search}*`
      query = query.or(`code.ilike.${pattern},name.ilike.${pattern}`)
    }

    query = query.order("code", { ascending: true })

    const { data, count, error } = await query

    if (error) throw error

    return NextResponse.json({ data: data || [], total: count ?? 0 })
  } catch (error) {
    console.error("GET /api/currencies error:", error)
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
    const { code, name, symbol, decimals, isBase } = body

    if (!code || !name) {
      return NextResponse.json({ error: "Code and name are required" }, { status: 400 })
    }

    const { data: existing } = await supabaseAdmin
      .from("currencies")
      .select("id")
      .eq("orgId", orgId)
      .eq("code", code.toUpperCase())
      .maybeSingle()

    if (existing) {
      return NextResponse.json({ error: "Currency with this code already exists in this organization" }, { status: 400 })
    }

    const { data, error } = await supabaseAdmin
      .from("currencies")
      .insert({
        id: newId(),
        orgId,
        code: code.toUpperCase(),
        name,
        symbol: symbol || null,
        decimals: decimals ?? 2,
        isBase: isBase ?? false,
        updatedAt: now(),
      })
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ data }, { status: 201 })
  } catch (error) {
    console.error("POST /api/currencies error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
