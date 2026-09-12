import { createServerClient } from "@supabase/ssr"
import { NextResponse } from "next/server"
import { getCookieDomain } from "@/lib/cookie-domain"

const AUTH_URL = "https://osupitxzfdcetyvcunqi.supabase.co"
const AUTH_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9zdXBpdHh6ZmRjZXR5dmN1bnFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0OTgxNzMsImV4cCI6MjA4OTA3NDE3M30.BImUTZxauMPAbK2UXGKcrGLM9E3RaPSxY6teXBHsjxI"

export async function POST(request: Request) {
  const supabaseUrl = process.env.NEXT_PUBLIC_LUCIDSHARE_SUPABASE_URL || AUTH_URL
  const supabaseAnonKey = process.env.NEXT_PUBLIC_LUCIDSHARE_SUPABASE_ANON_KEY || AUTH_ANON_KEY
  const host = request.headers.get("host") || ""
  const cookieDomain = getCookieDomain(host)

  const response = NextResponse.json({ success: true })

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        const cookieHeader = request.headers.get("cookie") || ""
        if (!cookieHeader) return []
        return cookieHeader.split(";").map((c) => {
          const eqIdx = c.indexOf("=")
          if (eqIdx === -1) return { name: c.trim(), value: "" }
          return {
            name: c.slice(0, eqIdx).trim(),
            value: decodeURIComponent(c.slice(eqIdx + 1).trim()),
          }
        })
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value, options }) => {
          response.cookies.set(name, value, {
            ...options,
            domain: cookieDomain,
            path: "/",
            sameSite: "lax",
            secure: true,
          })
        })
      },
    },
    cookieOptions: {
      domain: cookieDomain,
      path: "/",
      sameSite: "lax",
      secure: true,
    },
  })

  await supabase.auth.signOut()
  return response
}
