import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string; memberId: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { memberId } = await params
    const body = await request.json()
    const { roles } = body

    if (!roles || !Array.isArray(roles) || roles.length === 0) {
      return NextResponse.json({ error: "roles are required" }, { status: 400 })
    }

    const { data, error } = await supabaseAdmin
      .from("organization_members")
      .update({ roles })
      .eq("id", memberId)
      .select("*, user:users(id, email, username, name, image, isActive)")
      .single()

    if (error) throw error

    return NextResponse.json({ data })
  } catch (error) {
    console.error("PUT /api/organizations/[id]/members/[memberId] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string; memberId: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { memberId } = await params

    const { error } = await supabaseAdmin
      .from("organization_members")
      .delete()
      .eq("id", memberId)

    if (error) throw error

    return NextResponse.json({ data: { message: "Member removed successfully" } })
  } catch (error) {
    console.error("DELETE /api/organizations/[id]/members/[memberId] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
