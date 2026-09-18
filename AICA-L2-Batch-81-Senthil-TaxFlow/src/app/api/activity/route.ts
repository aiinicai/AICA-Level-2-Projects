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
    const limit = Math.min(parseInt(searchParams.get("limit") || "10", 10), 50)

    const { data, error } = await supabaseAdmin
      .from("activities")
      .select("*, compliance:compliance_schedules!complianceId(id, complianceId), user:users!userId(id, name, email)")
      .order("createdAt", { ascending: false })
      .limit(limit)
    if (error) throw error

    return NextResponse.json({ data: data || [] })
  } catch (error) {
    console.error("GET /api/activity error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
