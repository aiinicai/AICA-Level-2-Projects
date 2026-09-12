import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

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
    const { roles } = body

    if (!roles || !Array.isArray(roles) || roles.length === 0) {
      return NextResponse.json({ error: "roles are required" }, { status: 400 })
    }

    const { data: existing } = await supabaseAdmin
      .from("organization_members")
      .select("id")
      .eq("id", id)
      .maybeSingle()

    if (!existing) {
      return NextResponse.json({ error: "Member not found" }, { status: 404 })
    }

    const { data, error } = await supabaseAdmin
      .from("organization_members")
      .update({ roles })
      .eq("id", id)
      .select("*, user:users!userId(id, email, username, name, image, isActive)")
      .single()

    if (error) {
      // Fallback if relation syntax fails
      const { data: fallbackData, error: fallbackError } = await supabaseAdmin
        .from("organization_members")
        .update({ roles })
        .eq("id", id)
        .select("*")
        .single()

      if (fallbackError) throw fallbackError

      const { data: user } = await supabaseAdmin
        .from("users")
        .select("id, email, username, name, image, isActive")
        .eq("id", fallbackData.userId)
        .maybeSingle()

      return NextResponse.json({
        data: {
          id: fallbackData.id,
          userId: user?.id || fallbackData.userId,
          name: user?.name || null,
          email: user?.email || "",
          username: user?.username || "",
          image: user?.image || null,
          isActive: user?.isActive ?? true,
          roles: fallbackData.roles,
        },
      })
    }

    return NextResponse.json({
      data: {
        id: data.id,
        userId: data.user?.id,
        name: data.user?.name,
        email: data.user?.email,
        username: data.user?.username,
        image: data.user?.image,
        isActive: data.user?.isActive,
        roles: data.roles,
      },
    })
  } catch (error) {
    console.error("PUT /api/employees/[id] error:", error)
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

    const { data: existing } = await supabaseAdmin
      .from("organization_members")
      .select("id")
      .eq("id", id)
      .maybeSingle()

    if (!existing) {
      return NextResponse.json({ error: "Member not found" }, { status: 404 })
    }

    const { error } = await supabaseAdmin
      .from("organization_members")
      .delete()
      .eq("id", id)

    if (error) throw error

    return NextResponse.json({ data: { message: "Member removed successfully" } })
  } catch (error) {
    console.error("DELETE /api/employees/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
