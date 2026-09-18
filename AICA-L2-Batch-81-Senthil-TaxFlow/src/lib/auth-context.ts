import { cookies } from "next/headers"

export interface ActiveContext {
  orgId: string | null
  activeRole: string
}

export async function getActiveContext(): Promise<ActiveContext> {
  const cookieStore = await cookies()
  const orgId = cookieStore.get("active-org-id")?.value || null
  const activeRole = cookieStore.get("active-role")?.value || "PREPARER"
  return { orgId, activeRole }
}

export function getActiveContextFromRequest(request: Request): ActiveContext {
  const cookieHeader = request.headers.get("cookie") || ""
  const cookies = cookieHeader.split(";").reduce<Record<string, string>>((acc, c) => {
    const eqIdx = c.indexOf("=")
    if (eqIdx === -1) return acc
    const name = c.slice(0, eqIdx).trim()
    const value = decodeURIComponent(c.slice(eqIdx + 1).trim())
    acc[name] = value
    return acc
  }, {})
  const orgId = cookies["active-org-id"] || null
  const activeRole = cookies["active-role"] || "PREPARER"
  return { orgId, activeRole }
}
