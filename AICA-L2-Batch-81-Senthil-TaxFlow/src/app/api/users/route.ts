import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { NextResponse } from "next/server"

interface OrgMemberUserRow {
  userId: string
  roles: string[] | null
  user: {
    id: string
    name: string | null
    email: string | null
    username: string | null
    role: string | null
    image: string | null
    isActive: boolean | null
  } | null
}

interface MemberUserRow {
  id: string
  name: string | null
  email: string | null
  username: string | null
  role: string | null
  image: string | null
  isActive: boolean | null
  roles: string[]
}

export async function GET(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId } = getActiveContextFromRequest(request)

    const { searchParams } = new URL(request.url)
    const search = searchParams.get("search") || ""
    const role = searchParams.get("role") || ""
    const scope = searchParams.get("scope") || ""

    // Default: scope to active org members (used by compliance create/edit,
    // where assignees must be able to access the org).
    // scope=all: search across all users (used by employees page to add new members).
    if (scope !== "all") {
      if (!orgId) {
        return NextResponse.json({ data: [] })
      }

      const { data: members, error } = await supabaseAdmin
        .from("organization_members")
        .select("userId, roles, user:users!userId(id, name, email, username, role, image, isActive)")
        .eq("orgId", orgId)

      if (error) throw error

      let users: MemberUserRow[] = ((members || []) as unknown as OrgMemberUserRow[])
        .flatMap((m) => {
          if (!m.user) return []
          return [{ ...m.user, roles: m.roles || [] }]
        })

      if (role) {
        users = users.filter((u) =>
          (u.roles || []).includes(role) || u.role === role
        )
      }

      if (search) {
        const q = search.toLowerCase()
        users = users.filter((u) =>
          (u.name || "").toLowerCase().includes(q) ||
          (u.email || "").toLowerCase().includes(q) ||
          (u.username || "").toLowerCase().includes(q)
        )
      }

      users.sort((a, b) => (a.name || "").localeCompare(b.name || ""))
      users = users.slice(0, 50)

      return NextResponse.json({ data: users })
    }

    // scope=all: search across all users (admin/manager flow to add members)
    let query = supabaseAdmin
      .from("users")
      .select("id, name, email, username, role, image, isActive")

    if (role) {
      query = query.eq("role", role)
    }

    if (search) {
      query = query.or(`name.ilike.%${search}%,email.ilike.%${search}%,username.ilike.%${search}%`)
    }

    query = query.order("name", { ascending: true }).limit(50)

    const { data, error } = await query

    if (error) throw error

    return NextResponse.json({ data: data || [] })
  } catch (error) {
    console.error("GET /api/users error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
