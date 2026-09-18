import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { now } from "@/lib/db"
import { NextResponse } from "next/server"

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params

    const { data, error } = await supabaseAdmin
      .from("currencies")
      .select("*")
      .eq("id", id)
      .maybeSingle()

    if (error) throw error

    if (!data) {
      return NextResponse.json({ error: "Currency not found" }, { status: 404 })
    }

    return NextResponse.json({ data })
  } catch (error) {
    console.error("GET /api/currencies/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function PUT(request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId } = getActiveContextFromRequest(request)
    const { id } = await params
    const body = await request.json()
    const { code, name, symbol, decimals, isBase } = body

    const { data: existing, error: fetchError } = await supabaseAdmin
      .from("currencies")
      .select("*")
      .eq("id", id)
      .maybeSingle()

    if (fetchError) throw fetchError

    if (!existing) {
      return NextResponse.json({ error: "Currency not found" }, { status: 404 })
    }

    if (code && code.toUpperCase() !== existing.code && orgId) {
      const { data: conflict } = await supabaseAdmin
        .from("currencies")
        .select("id")
        .eq("orgId", orgId)
        .eq("code", code.toUpperCase())
        .neq("id", id)
        .maybeSingle()

      if (conflict) {
        return NextResponse.json({ error: "Currency with this code already exists in this organization" }, { status: 400 })
      }
    }

    const { data, error } = await supabaseAdmin
      .from("currencies")
      .update({
        ...(code !== undefined && { code: code.toUpperCase() }),
        ...(name !== undefined && { name }),
        ...(symbol !== undefined && { symbol: symbol || null }),
        ...(decimals !== undefined && { decimals }),
        ...(isBase !== undefined && { isBase }),
        updatedAt: now(),
      })
      .eq("id", id)
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ data })
  } catch (error) {
    console.error("PUT /api/currencies/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function DELETE(request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params

    const { error } = await supabaseAdmin
      .from("currencies")
      .delete()
      .eq("id", id)

    if (error) throw error

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error("DELETE /api/currencies/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
