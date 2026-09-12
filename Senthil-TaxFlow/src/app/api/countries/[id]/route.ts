import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
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
      .from("countries")
      .select("*")
      .eq("id", id)
      .maybeSingle()

    if (error) throw error

    if (!data) {
      return NextResponse.json({ error: "Country not found" }, { status: 404 })
    }

    return NextResponse.json({ data })
  } catch (error) {
    console.error("GET /api/countries/[id] error:", error)
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

    const { id } = await params
    const body = await request.json()
    const { name, code, region } = body

    const { data: existing, error: fetchError } = await supabaseAdmin
      .from("countries")
      .select("*")
      .eq("id", id)
      .maybeSingle()

    if (fetchError) throw fetchError

    if (!existing) {
      return NextResponse.json({ error: "Country not found" }, { status: 404 })
    }

    if (name && name !== existing.name) {
      const { data: conflict } = await supabaseAdmin
        .from("countries")
        .select("id")
        .eq("name", name)
        .maybeSingle()

      if (conflict) {
        return NextResponse.json({ error: "Country with this name already exists" }, { status: 400 })
      }
    }

    if (code && code.toUpperCase() !== existing.code) {
      const { data: conflict } = await supabaseAdmin
        .from("countries")
        .select("id")
        .eq("code", code.toUpperCase())
        .maybeSingle()

      if (conflict) {
        return NextResponse.json({ error: "Country with this code already exists" }, { status: 400 })
      }
    }

    const { data, error } = await supabaseAdmin
      .from("countries")
      .update({
        ...(name !== undefined && { name }),
        ...(code !== undefined && { code: code.toUpperCase() }),
        ...(region !== undefined && { region }),
      })
      .eq("id", id)
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ data })
  } catch (error) {
    console.error("PUT /api/countries/[id] error:", error)
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
      .from("countries")
      .select("id")
      .eq("id", id)
      .maybeSingle()

    if (fetchError) throw fetchError

    if (!existing) {
      return NextResponse.json({ error: "Country not found" }, { status: 404 })
    }

    const { error } = await supabaseAdmin
      .from("countries")
      .delete()
      .eq("id", id)

    if (error) throw error

    return NextResponse.json({ data: { message: "Country deleted successfully" } })
  } catch (error) {
    console.error("DELETE /api/countries/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
