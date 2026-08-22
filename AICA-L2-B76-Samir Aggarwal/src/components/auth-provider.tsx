import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { Session } from '@supabase/supabase-js'
import { useQueryClient } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import type { Profile } from '@/types/db'

interface AuthState {
  session: Session | null
  profile: Profile | null
  isAdmin: boolean
  /** True until BOTH the session and the role have been resolved. */
  loading: boolean
  signOut: () => Promise<void>
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthState | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [isAdmin, setIsAdmin] = useState(false)
  const [loading, setLoading] = useState(true)

  // Which user's profile and role are already loaded. Supabase fires
  // SIGNED_IN / TOKEN_REFRESHED every time the tab regains focus, for the SAME
  // user — treating those as a fresh sign-in flipped `loading`, which unmounts
  // the entire page and destroys any open dialog and half-typed form.
  const loadedUserRef = useRef<string | null>(null)

  const loadUserData = useCallback(async (userId: string) => {
    const [profileRes, roleRes] = await Promise.all([
      supabase.from('profiles').select('*').eq('id', userId).maybeSingle(),
      supabase.from('user_roles').select('role').eq('user_id', userId).eq('role', 'admin').maybeSingle(),
    ])
    setProfile((profileRes.data as Profile | null) ?? null)
    setIsAdmin(Boolean(roleRes.data))
    setLoading(false)
  }, [])

  useEffect(() => {
    let active = true

    // Register the listener FIRST, then read the existing session. Doing it the
    // other way round drops the event that fires between the two calls.
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      if (!active) return
      setSession(nextSession)

      if (!nextSession?.user) {
        loadedUserRef.current = null
        setProfile(null)
        setIsAdmin(false)
        setLoading(false)
        return
      }

      // Same user already loaded: this is a token refresh or an Alt+Tab focus
      // revalidation, not a sign-in. Update the session silently and leave the
      // page exactly as it is.
      if (nextSession.user.id === loadedUserRef.current) return

      loadedUserRef.current = nextSession.user.id
      // Never call Supabase synchronously inside this callback — it deadlocks
      // the auth client. Defer to the next tick.
      setLoading(true)
      setTimeout(() => {
        if (active) void loadUserData(nextSession.user.id)
      }, 0)
    })

    void supabase.auth.getSession().then(({ data }) => {
      if (!active) return
      setSession(data.session)
      if (data.session?.user) {
        if (data.session.user.id !== loadedUserRef.current) {
          loadedUserRef.current = data.session.user.id
          void loadUserData(data.session.user.id)
        }
      } else {
        setLoading(false)
      }
    })

    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [loadUserData])

  const queryClient = useQueryClient()

  const signOut = useCallback(async () => {
    await supabase.auth.signOut()
    setProfile(null)
    setIsAdmin(false)
    // The query cache is persisted to localStorage for fast startup; a
    // signed-out machine must not keep the firm's data around.
    queryClient.clear()
    try {
      window.localStorage.removeItem('asco-query-cache')
    } catch {
      /* storage unavailable — nothing to clear */
    }
  }, [queryClient])

  const refreshProfile = useCallback(async () => {
    if (session?.user) await loadUserData(session.user.id)
  }, [session, loadUserData])

  const value = useMemo<AuthState>(
    () => ({ session, profile, isAdmin, loading, signOut, refreshProfile }),
    [session, profile, isAdmin, loading, signOut, refreshProfile],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
