import { updateAuthSession } from "@/lib/supabase/auth-middleware"
import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export async function middleware(request: NextRequest) {
  if (process.env.NODE_ENV === "development") {
    return NextResponse.next()
  }

  const response = await updateAuthSession(request)
  const { pathname } = request.nextUrl

  // Match any Supabase project auth cookie, including chunked (.0, .1) cookies
  const hasSession = request.cookies
    .getAll()
    .some((c) => /^sb-.*-auth-token(\.\d+)?$/.test(c.name))
  const isLoginPage = pathname === "/login"

  if (isLoginPage) {
    if (hasSession) {
      return NextResponse.redirect(new URL("/dashboard", request.url))
    }
    return response
  }

  if (!hasSession) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  return response
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|uploads).*)"],
}
