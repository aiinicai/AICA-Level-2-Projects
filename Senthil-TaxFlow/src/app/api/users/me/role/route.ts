import { cookies } from "next/headers"
import { createServerClient } from "@supabase/ssr"
import { supabaseAdmin } from "@/lib/supabase"
import { NextResponse } from "next/server"

const AUTH_URL = "https://osupitxzfdcetyvcunqi.supabase.co"
const AUTH_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9zdXBpdHh6ZmRjZXR5dmN1bnFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0OTgxNzMsImV4cCI6MjA4OTA3NDE3M30.BImUTZxauMPAbK2UXGKcrGLM9E3RaPSxY6teXBHsjxI"

const ALLOWED_ROLES = ["ADMINISTRATOR", "PREPARER", "REVIEWER", "APPROVER"] as const
type AllowedRole = typeof ALLOWED_ROLES[number]

export async function PUT(request: Request) {
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

    const { data: { user: authUser }, error: authError } = await supabase.auth.getUser()
    if (authError || !authUser || !authUser.email) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const email = authUser.email

    const { data: existingUser } = await supabaseAdmin
      .from("users")
      .select("id, email, name, username, role, roles, image, employeeId, department")
      .eq("email", email)
      .maybeSingle()

    let userId: string
    if (existingUser) {
      userId = existingUser.id
    } else {
      const displayName = authUser.user_metadata?.name || email.split("@")[0]
      const username = email.split("@")[0]

      const { data: newUser, error: createError } = await supabaseAdmin
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
        .select("id, email, name, username, role, roles, image, employeeId, department")
        .single()

      if (createError || !newUser) {
        const msg = createError ? `DB error: ${createError.message}${createError.code ? ` (${createError.code})` : ""}${createError.details ? ` - ${createError.details}` : ""}` : "Insert returned no data"
        return NextResponse.json(
          { error: msg },
          { status: 500 }
        )
      }
      userId = newUser.id
    }

    const body = await request.json()
    const { role } = body

    if (!role || typeof role !== "string") {
      return NextResponse.json(
        { error: "Role is required and must be a string" },
        { status: 400 }
      )
    }

    if (!ALLOWED_ROLES.includes(role as AllowedRole)) {
      return NextResponse.json(
        { error: `Invalid role. Must be one of: ${ALLOWED_ROLES.join(", ")}` },
        { status: 400 }
      )
    }

    const { data: updatedUser, error: updateError } = await supabaseAdmin
      .from("users")
      .update({ role, roles: [role] })
      .eq("id", userId)
      .select()
      .single()

    if (updateError) throw updateError

    if (!updatedUser) {
      return NextResponse.json({ error: "User not found" }, { status: 404 })
    }

    const responseUser = {
      id: updatedUser.id,
      email: updatedUser.email,
      name: updatedUser.name,
      username: updatedUser.username,
      role: updatedUser.role,
      roles: updatedUser.roles,
      image: updatedUser.image,
      employeeId: updatedUser.employeeId,
      department: updatedUser.department,
    }

    const res = NextResponse.json({ data: { user: responseUser } })
    res.headers.set(
      "Set-Cookie",
      `active-role=${encodeURIComponent(role)}; Path=/; SameSite=Lax; Secure`
    )
    return res
  } catch (error) {
    console.error("PUT /api/users/me/role error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
