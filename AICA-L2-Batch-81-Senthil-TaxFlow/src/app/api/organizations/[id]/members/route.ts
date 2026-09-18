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
      .from("organization_members")
      .select("*, user:users(id, email, username, name, image, isActive)")
      .eq("orgId", id)
      .order("createdAt", { ascending: false })

    if (error) throw error

    return NextResponse.json({ data: data || [] })
  } catch (error) {
    console.error("GET /api/organizations/[id]/members error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function POST(
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
    const { userId, roles } = body

    if (!userId || !roles || !Array.isArray(roles) || roles.length === 0) {
      return NextResponse.json({ error: "userId and roles are required" }, { status: 400 })
    }

    // Check if user exists
    const { data: user } = await supabaseAdmin
      .from("users")
      .select("id, name, email")
      .eq("id", userId)
      .maybeSingle()

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 })
    }

    // Check if already a member
    const { data: existing } = await supabaseAdmin
      .from("organization_members")
      .select("id")
      .eq("orgId", id)
      .eq("userId", userId)
      .maybeSingle()

    if (existing) {
      return NextResponse.json({ error: "User is already a member of this organization" }, { status: 400 })
    }

    const { data, error } = await supabaseAdmin
      .from("organization_members")
      .insert({
        orgId: id,
        userId,
        roles,
        createdById: session.user.id,
      })
      .select("*, user:users(id, email, username, name, image, isActive)")
      .single()

    if (error) throw error

    return NextResponse.json({ data }, { status: 201 })
  } catch (error) {
    console.error("POST /api/organizations/[id]/members error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
