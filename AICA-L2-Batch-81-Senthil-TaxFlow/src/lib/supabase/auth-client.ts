"use client"

import { createBrowserClient } from "@supabase/ssr"

const AUTH_URL = "https://osupitxzfdcetyvcunqi.supabase.co"
const AUTH_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9zdXBpdHh6ZmRjZXR5dmN1bnFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0OTgxNzMsImV4cCI6MjA4OTA3NDE3M30.BImUTZxauMPAbK2UXGKcrGLM9E3RaPSxY6teXBHsjxI"

export function createAuthClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_LUCIDSHARE_SUPABASE_URL || AUTH_URL
  const supabaseAnonKey = process.env.NEXT_PUBLIC_LUCIDSHARE_SUPABASE_ANON_KEY || AUTH_ANON_KEY
  const host = typeof window !== "undefined" ? window.location.hostname : ""
  const isLucidExp = host.endsWith(".lucid-exp.com") || host === "lucid-exp.com"

  return createBrowserClient(supabaseUrl, supabaseAnonKey, {
    cookieOptions: {
      domain: isLucidExp ? ".lucid-exp.com" : undefined,
      path: "/",
      sameSite: "lax",
      secure: true,
    },
  })
}
