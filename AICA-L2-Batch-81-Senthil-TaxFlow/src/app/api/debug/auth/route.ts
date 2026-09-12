import { cookies, headers } from "next/headers"
import { NextResponse } from "next/server"
import { createServerClient } from "@supabase/ssr"
import { supabaseAdmin } from "@/lib/supabase"

const AUTH_URL = "https://osupitxzfdcetyvcunqi.supabase.co"
const AUTH_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9zdXBpdHh6ZmRjZXR5dmN1bnFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0OTgxNzMsImV4cCI6MjA4OTA3NDE3M30.BImUTZxauMPAbK2UXGKcrGLM9E3RaPSxY6teXBHsjxI"

export async function GET() {
  const cookieStore = await cookies()
  const headersList = await headers()
  const allCookies = cookieStore.getAll()

  const supabaseCookie = allCookies.find(c => c.name.includes("sb-"))

  const supabaseUrl = process.env.NEXT_PUBLIC_LUCIDSHARE_SUPABASE_URL || AUTH_URL
  const supabaseAnonKey = process.env.NEXT_PUBLIC_LUCIDSHARE_SUPABASE_ANON_KEY || AUTH_ANON_KEY

  let getUserResult: { user: string | null; hasUser: boolean } | null = null
  let getUserError: string | null = null
  const client = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll()
      },
      setAll() {},
    },
  })
  let authEmail: string | null = null
  try {
    const result = await client.auth.getUser()
    authEmail = result.data.user?.email || null
    getUserResult = { user: authEmail, hasUser: !!result.data.user }
    getUserError = result.error?.message || null
  } catch (e) {
    getUserError = "exception: " + (e instanceof Error ? e.message : String(e))
  }

  // Data-layer diagnostics: replicate what /api/auth/me does
  let appUser: {
    id: string
    email: string | null
    name: string | null
    username: string | null
    role: string | null
    roles: string[] | null
  } | null = null
  let appUserError: string | null = null
  let memberships: {
    orgId: string
    roles: string[] | null
    org: { id: string; name: string; slug: string | null } | null
  }[] | null = null
  let membershipsError: string | null = null

  if (authEmail) {
    const userRes = await supabaseAdmin
      .from("users")
      .select("id, email, name, username, role, roles")
      .eq("email", authEmail)
      .maybeSingle()
    appUser = userRes.data
    appUserError = userRes.error?.message || null

    if (userRes.data?.id) {
      const memRes = await supabaseAdmin
        .from("organization_members")
        .select("orgId, roles, org:organizations(id, name, slug)")
        .eq("userId", userRes.data.id)
      memberships = (memRes.data as unknown as {
      orgId: string
      roles: string[] | null
      org: { id: string; name: string; slug: string | null } | null
    }[] | null)
      membershipsError = memRes.error?.message || null
    }
  }

  return NextResponse.json({
    host: headersList.get("host"),
    cookieCount: allCookies.length,
    hasSupabaseCookie: !!supabaseCookie,
    supabaseCookieName: supabaseCookie?.name || null,
    getUserResult,
    getUserError,
    authEmail,
    appUser,
    appUserError,
    memberships,
    membershipsError,
    supabaseUrl: supabaseUrl.substring(0, 30) + "...",
    nodeEnv: process.env.NODE_ENV,
  })
}
