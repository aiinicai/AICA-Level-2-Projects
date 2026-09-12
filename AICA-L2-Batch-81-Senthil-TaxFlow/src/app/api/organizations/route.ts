import { cookies } from "next/headers"
import { createServerClient } from "@supabase/ssr"
import { supabaseAdmin } from "@/lib/supabase"
import { NextResponse } from "next/server"

const AUTH_URL = "https://osupitxzfdcetyvcunqi.supabase.co"
const AUTH_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9zdXBpdHh6ZmRjZXR5dmN1bnFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0OTgxNzMsImV4cCI6MjA4OTA3NDE3M30.BImUTZxauMPAbK2UXGKcrGLM9E3RaPSxY6teXBHsjxI"

async function getSession() {
  const cookieStore = await cookies()
  const supabaseUrl = process.env.NEXT_PUBLIC_LUCIDSHARE_SUPABASE_URL || AUTH_URL
  const supabaseAnonKey = process.env.NEXT_PUBLIC_LUCIDSHARE_SUPABASE_ANON_KEY || AUTH_ANON_KEY

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll()
      },
      setAll() {},
    },
  })

  const { data: { user: authUser }, error } = await supabase.auth.getUser()
  if (error || !authUser || !authUser.email) return null

  const email = authUser.email

  const { data: existingUser } = await supabaseAdmin
    .from("users")
    .select("*")
    .eq("email", email)
    .maybeSingle()

  if (existingUser) {
    const { data: orgMemberships } = await supabaseAdmin
      .from("organization_members")
      .select("org:organizations(id, name, slug), roles")
      .eq("userId", existingUser.id)

    const orgs = ((orgMemberships || []) as unknown as {
      org: { id: string; name: string; slug: string | null } | null
      roles: string[] | null
    }[])
      .flatMap((m) => {
        if (!m.org) return []
        return [{
          id: m.org.id,
          name: m.org.name,
          slug: m.org.slug,
          roles: m.roles || [],
        }]
      })

    return {
      user: {
        id: existingUser.id,
        email: existingUser.email,
        name: existingUser.name,
        username: existingUser.username,
        role: existingUser.role || "PREPARER",
        roles: existingUser.roles || [existingUser.role || "PREPARER"],
        image: existingUser.image,
        employeeId: existingUser.employeeId,
        department: existingUser.department,
        orgs,
      },
    }
  }

  const displayName = authUser.user_metadata?.name || email.split("@")[0]
  const username = email.split("@")[0]

  const { data: newUser } = await supabaseAdmin
    .from("users")
    .insert({
      id: crypto.randomUUID(),
      email,
      username,
      password: "",
      name: displayName,
      role: "PREPARER",
      roles: ["PREPARER"],
      isActive: true,
      updatedAt: new Date().toISOString(),
    })
    .select()
    .single()

  if (!newUser) return null

  return {
    user: {
      id: newUser.id,
      email: newUser.email,
      name: newUser.name,
      username: newUser.username,
      role: newUser.role || "PREPARER",
      roles: newUser.roles || ["PREPARER"],
      image: newUser.image,
      employeeId: newUser.employeeId,
      department: newUser.department,
      orgs: [],
    },
  }
}

export async function GET() {
  try {
    const session = await getSession()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    return NextResponse.json({ data: session.user.orgs })
  } catch (error) {
    console.error("GET /api/organizations error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    const session = await getSession()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const body = await request.json()
    const { name } = body

    if (!name) {
      return NextResponse.json({ error: "Organization name is required" }, { status: 400 })
    }

    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")

    if (!slug) {
      return NextResponse.json({ error: "Invalid organization name" }, { status: 400 })
    }

    const { data: existing } = await supabaseAdmin
      .from("organizations")
      .select("id, name, slug, createdById")
      .eq("slug", slug)
      .maybeSingle()

    if (existing) {
      // Check whether the current user is already a member
      const { data: membership } = await supabaseAdmin
        .from("organization_members")
        .select("id")
        .eq("orgId", existing.id)
        .eq("userId", session.user.id)
        .maybeSingle()

      if (membership) {
        return NextResponse.json({ error: "You are already a member of this organization" }, { status: 400 })
      }

      // Self-heal: the org was created by this user but the membership insert
      // previously failed (orphaned org). Re-link the creator as admin.
      if (existing.createdById === session.user.id) {
        const healNow = new Date().toISOString()
        const { error: healError } = await supabaseAdmin
          .from("organization_members")
          .insert({
            id: crypto.randomUUID(),
            orgId: existing.id,
            userId: session.user.id,
            roles: ["ADMINISTRATOR"],
            updatedAt: healNow,
          })
        if (healError) {
          return NextResponse.json({ error: `Member insert failed: ${healError.message}${healError.code ? ` (${healError.code})` : ""}` }, { status: 500 })
        }
        return NextResponse.json({ data: { id: existing.id, name: existing.name, slug: existing.slug, roles: ["ADMINISTRATOR"] } }, { status: 201 })
      }

      return NextResponse.json({ error: "An organization with this name already exists" }, { status: 400 })
    }

    const now = new Date().toISOString()
    const { data: org, error: orgError } = await supabaseAdmin
      .from("organizations")
      .insert({
        id: crypto.randomUUID(),
        name,
        slug,
        createdById: session.user.id,
        updatedAt: now,
      })
      .select()
      .single()

    if (orgError) {
      return NextResponse.json({ error: `Org insert failed: ${orgError.message}${orgError.code ? ` (${orgError.code})` : ""}` }, { status: 500 })
    }

    const { error: memberError } = await supabaseAdmin
      .from("organization_members")
      .insert({
        id: crypto.randomUUID(),
        orgId: org.id,
        userId: session.user.id,
        roles: ["ADMINISTRATOR"],
        updatedAt: now,
      })
    if (memberError) {
      // Roll back the org so it doesn't become an invisible orphan
      await supabaseAdmin.from("organizations").delete().eq("id", org.id)
      return NextResponse.json({ error: `Member insert failed: ${memberError.message}${memberError.code ? ` (${memberError.code})` : ""}` }, { status: 500 })
    }

    return NextResponse.json({ data: { id: org.id, name: org.name, slug: org.slug, roles: ["ADMINISTRATOR"] } }, { status: 201 })
  } catch (error) {
    console.error("POST /api/organizations error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
