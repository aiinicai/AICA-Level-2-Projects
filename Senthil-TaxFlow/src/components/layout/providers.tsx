"use client"

import { createAuthClient } from "@/lib/supabase/auth-client"
import { TooltipProvider } from "@/components/ui/tooltip"
import { useRouter, usePathname } from "next/navigation"
import { createContext, useContext, useEffect, useState, useCallback } from "react"

interface OrgInfo {
  id: string
  name: string
  slug: string
  roles: string[]
}

interface AuthUser {
  id: string
  email: string
  name: string | null
  username: string
  role: string
  roles: string[]
  image: string | null
  employeeId: string | null
  department: string | null
  orgs: OrgInfo[]
}

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  refresh: () => Promise<void>
  activeOrgId: string | null
  activeRole: string
  setActiveContext: (orgId: string | null, role: string) => Promise<void>
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  refresh: async () => {},
  activeOrgId: null,
  activeRole: "PREPARER",
  setActiveContext: async () => {},
})

export const useAuth = () => useContext(AuthContext)

function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeOrgId, setActiveOrgId] = useState<string | null>(null)
  const [activeRole, setActiveRole] = useState<string>("PREPARER")

  const [authSupabase] = useState(() =>
    typeof window !== "undefined" ? createAuthClient() : null
  )

  const fetchUser = useCallback(async () => {
    try {
      const res = await fetch("/api/auth/me")
      if (res.ok) {
        const data = await res.json()
        setUser(data.user)
        if (data.activeContext) {
          setActiveOrgId(data.activeContext.orgId)
          setActiveRole(data.activeContext.activeRole)
        }
      } else {
        setUser(null)
      }
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // fetchUser awaits the API before any setState runs; acceptable fetch-on-mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching is async
    fetchUser()

    if (authSupabase) {
      const { data: { subscription } } = authSupabase.auth.onAuthStateChange(() => {
        fetchUser()
      })
      return () => subscription.unsubscribe()
    }
  }, [fetchUser, authSupabase])

  useEffect(() => {
    // Middleware skips auth checks in development, so route protection must
    // happen on the client: send unauthenticated users to /login (they would
    // otherwise see a blank page) and signed-in users away from /login.
    if (!loading && !user && pathname !== "/login") {
      router.replace("/login")
    } else if (!loading && user && pathname === "/login") {
      router.replace("/dashboard")
    }
  }, [loading, user, pathname, router])

  const setActiveContext = useCallback(async (orgId: string | null, role: string) => {
    await fetch("/api/auth/active-context", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ orgId, activeRole: role }),
    })
    setActiveOrgId(orgId)
    setActiveRole(role)
    // Refresh user data to reflect new context
    await fetchUser()
  }, [fetchUser])

  return (
    <AuthContext.Provider value={{ user, loading, refresh: fetchUser, activeOrgId, activeRole, setActiveContext }}>
      {children}
    </AuthContext.Provider>
  )
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <TooltipProvider delayDuration={0}>
        {children}
      </TooltipProvider>
    </AuthProvider>
  )
}
