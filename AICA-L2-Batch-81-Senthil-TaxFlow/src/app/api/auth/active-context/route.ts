import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const body = await request.json()
    const { orgId, activeRole } = body

    const response = NextResponse.json({ success: true })

    if (orgId) {
      response.cookies.set("active-org-id", orgId, {
        path: "/",
        sameSite: "lax",
        secure: true,
        maxAge: 60 * 60 * 24 * 30,
      })
    } else {
      response.cookies.delete("active-org-id")
    }

    if (activeRole) {
      response.cookies.set("active-role", activeRole, {
        path: "/",
        sameSite: "lax",
        secure: true,
        maxAge: 60 * 60 * 24 * 30,
      })
    }

    return response
  } catch (error) {
    console.error("POST /api/auth/active-context error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
