import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { NextResponse } from "next/server"

export async function GET(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    let { orgId } = getActiveContextFromRequest(request)
    if (!orgId) {
      // Fallback to first user organization if active-org-id cookie isn't set
      orgId = session.user.orgs[0]?.id || null
    }

    if (!orgId) {
      return NextResponse.json({ data: [] })
    }

    const { searchParams } = new URL(request.url)
    const search = searchParams.get("search") || ""

    let userIds: string[] | undefined

    if (search) {
      const { data: matchedUsers } = await supabaseAdmin
        .from("users")
        .select("id")
        .or(`name.ilike.%${search}%,email.ilike.%${search}%,username.ilike.%${search}%`)
      userIds = matchedUsers?.map((u: { id: string }) => u.id) || []
    }

    let listQuery = supabaseAdmin
      .from("organization_members")
      .select("*, user:users!userId(id, email, username, name, image, isActive)")
      .eq("orgId", orgId)

    if (userIds !== undefined) {
      listQuery = listQuery.in("userId", userIds.length > 0 ? userIds : [""])
    }

    listQuery = listQuery.order("createdAt", { ascending: false })

    const { data, error } = await listQuery

    if (error) {
      console.error("GET /api/employees query error:", error)
      // Fallback: query organization_members and users separately if PostgREST relation cache fails
      const { data: rawMembers, error: rawError } = await supabaseAdmin
        .from("organization_members")
        .select("*")
        .eq("orgId", orgId)
        .order("createdAt", { ascending: false })

      if (rawError) throw rawError

      const memberUserIds = (rawMembers || []).map((m: { userId: string }) => m.userId).filter(Boolean)
      let usersMap = new Map<string, { id: string; name: string | null; email: string; username: string; image: string | null; isActive: boolean }>()

      if (memberUserIds.length > 0) {
        const { data: usersList } = await supabaseAdmin
          .from("users")
          .select("id, name, email, username, image, isActive")
          .in("id", memberUserIds)

        for (const u of usersList || []) {
          usersMap.set(u.id, u)
        }
      }

      let transformed = (rawMembers || []).map((m: { id: string; userId: string; roles: string[]; createdAt: string }) => {
        const u = usersMap.get(m.userId)
        return {
          id: m.id,
          userId: m.userId,
          name: u?.name || null,
          email: u?.email || "",
          username: u?.username || "",
          image: u?.image || null,
          isActive: u?.isActive ?? true,
          roles: m.roles,
          createdAt: m.createdAt,
        }
      })

      if (search) {
        const q = search.toLowerCase()
        transformed = transformed.filter(
          (t) =>
            (t.name || "").toLowerCase().includes(q) ||
            t.email.toLowerCase().includes(q) ||
            t.username.toLowerCase().includes(q)
        )
      }

      return NextResponse.json({ data: transformed })
    }

    const transformed = (data || []).map((m: { id: string; user?: { id: string; name: string; email: string; username: string; image: string | null; isActive: boolean }; roles: string[]; createdAt: string }) => ({
      id: m.id,
      userId: m.user?.id,
      name: m.user?.name,
      email: m.user?.email,
      username: m.user?.username,
      image: m.user?.image,
      isActive: m.user?.isActive,
      roles: m.roles,
      createdAt: m.createdAt,
    }))

    return NextResponse.json({ data: transformed })
  } catch (error) {
    console.error("GET /api/employees error:", error)
    return NextResponse.json({ error: error instanceof Error ? error.message : "Internal server error" }, { status: 500 })
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
    const { userId, roles } = body

    if (!userId || !roles || !Array.isArray(roles) || roles.length === 0) {
      return NextResponse.json({ error: "userId and roles are required" }, { status: 400 })
    }

    const { data: user } = await supabaseAdmin
      .from("users")
      .select("id, name, email")
      .eq("id", userId)
      .maybeSingle()

    if (!user) {
      return NextResponse.json({ error: "User not found" }, { status: 404 })
    }

    const { data: existing } = await supabaseAdmin
      .from("organization_members")
      .select("id")
      .eq("orgId", orgId)
      .eq("userId", userId)
      .maybeSingle()

    if (existing) {
      return NextResponse.json({ error: "User is already a member of this organization" }, { status: 400 })
    }

    const { data, error } = await supabaseAdmin
      .from("organization_members")
      .insert({
        orgId,
        userId,
        roles,
        createdById: session.user.id,
      })
      .select("*, user:users!userId(id, email, username, name, image, isActive)")
      .single()

    if (error) {
      // Fallback if relation syntax fails
      const { data: fallbackData, error: fallbackError } = await supabaseAdmin
        .from("organization_members")
        .insert({
          orgId,
          userId,
          roles,
          createdById: session.user.id,
        })
        .select("*")
        .single()

      if (fallbackError) throw fallbackError

      return NextResponse.json({
        data: {
          id: fallbackData.id,
          userId: user.id,
          name: user.name,
          email: user.email,
          username: (user as { username?: string }).username || "",
          image: null,
          isActive: true,
          roles: fallbackData.roles,
          createdAt: fallbackData.createdAt,
        },
      }, { status: 201 })
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
        createdAt: data.createdAt,
      },
    }, { status: 201 })
  } catch (error) {
    console.error("POST /api/employees error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
