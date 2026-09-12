import { createAuthClient } from "@/lib/supabase/auth-server"
import { supabaseAdmin } from "@/lib/supabase"

export interface AuthUser {
  id: string
  email: string
  name: string | null
  username: string
  role: string
  roles: string[]
  image: string | null
  employeeId: string | null
  department: string | null
  orgs: { id: string; name: string; slug: string | null; roles: string[] }[]
}

export async function auth(): Promise<{ user: AuthUser } | null> {
  const supabase = await createAuthClient()
  if (!supabase) return null

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
