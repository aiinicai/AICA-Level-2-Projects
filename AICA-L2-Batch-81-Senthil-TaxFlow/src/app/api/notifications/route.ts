import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export async function GET() {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const [listResult, countResult] = await Promise.all([
      supabaseAdmin
        .from("notifications")
        .select("*")
        .eq("userId", session.user.id)
        .order("createdAt", { ascending: false }),
      supabaseAdmin
        .from("notifications")
        .select("*", { count: "exact", head: true })
        .eq("userId", session.user.id)
        .eq("read", false),
    ])
    if (listResult.error) throw listResult.error

    return NextResponse.json({
      data: listResult.data || [],
      unreadCount: countResult.count || 0,
    })
  } catch (error) {
    console.error("GET /api/notifications error:", error)
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

    if (body.all) {
      const { error } = await supabaseAdmin
        .from("notifications")
        .update({ read: true })
        .eq("userId", session.user.id)
        .eq("read", false)
      if (error) throw error
      return NextResponse.json({ data: { message: "All notifications marked as read" } })
    }

    if (body.ids?.length) {
      const { error } = await supabaseAdmin
        .from("notifications")
        .update({ read: true })
        .in("id", body.ids)
        .eq("userId", session.user.id)
      if (error) throw error
      return NextResponse.json({ data: { message: `${body.ids.length} notifications marked as read` } })
    }

    return NextResponse.json({ error: "ids or all required" }, { status: 400 })
  } catch (error) {
    console.error("POST /api/notifications error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
