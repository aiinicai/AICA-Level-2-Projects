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
      .from("notifications")
      .select("*")
      .eq("id", id)
      .maybeSingle()
    if (error) throw error

    if (!data) {
      return NextResponse.json({ error: "Notification not found" }, { status: 404 })
    }

    if (data.userId !== session.user.id) {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 })
    }

    return NextResponse.json({ data })
  } catch (error) {
    console.error("GET /api/notifications/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function PUT(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params

    const { data: existing, error: findError } = await supabaseAdmin
      .from("notifications")
      .select("*")
      .eq("id", id)
      .maybeSingle()
    if (findError) throw findError
    if (!existing) {
      return NextResponse.json({ error: "Notification not found" }, { status: 404 })
    }

    if (existing.userId !== session.user.id) {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 })
    }

    const { data, error } = await supabaseAdmin
      .from("notifications")
      .update({ read: true })
      .eq("id", id)
      .select()
      .single()
    if (error) throw error

    return NextResponse.json({ data })
  } catch (error) {
    console.error("PUT /api/notifications/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
