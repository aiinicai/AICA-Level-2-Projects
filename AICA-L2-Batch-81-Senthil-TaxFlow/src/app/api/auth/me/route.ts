import { cookies } from "next/headers"
import { createServerClient } from "@supabase/ssr"
import { supabaseAdmin } from "@/lib/supabase"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { NextResponse } from "next/server"

const AUTH_URL = "https://osupitxzfdcetyvcunqi.supabase.co"
const AUTH_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9zdXBpdHh6ZmRjZXR5dmN1bnFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0OTgxNzMsImV4cCI6MjA4OTA3NDE3M30.BImUTZxauMPAbK2UXGKcrGLM9E3RaPSxY6teXBHsjxI"

export async function GET(request: Request) {
  try {
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
    if (error || !authUser || !authUser.email) {
      return NextResponse.json({ user: null }, { status: 401 })
    }

    const email = authUser.email

    const { data: existingUser } = await supabaseAdmin
      .from("users")
      .select("id, email, name, username, role, roles, image, employeeId, department")
      .eq("email", email)
      .maybeSingle()

    const activeContext = getActiveContextFromRequest(request)
const noStore = { "Cache-Control": "no-store, max-age=0" }

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

      return NextResponse.json({
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
        activeContext,
      }, { headers: noStore })
    }

    return NextResponse.json({
      user: {
        id: authUser.id,
        email: authUser.email,
        name: authUser.user_metadata?.name || null,
        username: authUser.email.split("@")[0] || "",
        role: "PREPARER",
        roles: ["PREPARER"],
        image: authUser.user_metadata?.avatar_url || null,
        employeeId: null,
        department: null,
        orgs: [],
      },
      activeContext,
    }, { headers: noStore })
  } catch (error) {
    console.error("GET /api/auth/me error:", error)
    return NextResponse.json({ user: null }, { status: 500 })
  }
}
