import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export async function GET(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const search = searchParams.get("search") || ""

    let query = supabaseAdmin
      .from("countries")
      .select("*", { count: "exact", head: false })

    if (search) {
      const pattern = `*${search}*`
      query = query.or(`name.ilike.${pattern},code.ilike.${pattern},region.ilike.${pattern}`)
    }

    query = query.order("name", { ascending: true })

    const { data, count, error } = await query

    if (error) throw error

    return NextResponse.json({ data: data || [], total: count ?? 0 })
  } catch (error) {
    console.error("GET /api/countries error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const body = await request.json()
    const { name, code, region } = body

    if (!name || !code) {
      return NextResponse.json({ error: "Name and code are required" }, { status: 400 })
    }

    const { data: existing } = await supabaseAdmin
      .from("countries")
      .select("id")
      .or(`name.eq.${name},code.eq.${code}`)
      .maybeSingle()

    if (existing) {
      return NextResponse.json({ error: "Country with this name or code already exists" }, { status: 400 })
    }

    const { data, error } = await supabaseAdmin
      .from("countries")
      .insert({
        name,
        code: code.toUpperCase(),
        region,
      })
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ data }, { status: 201 })
  } catch (error) {
    console.error("POST /api/countries error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
