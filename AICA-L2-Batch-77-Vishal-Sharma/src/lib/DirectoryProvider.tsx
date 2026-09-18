import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { fetchClients, fetchProfiles } from './queries'
import type { Client, Profile } from '../types/database'
import { useAuth } from '../auth/AuthProvider'

interface DirectoryState {
  profiles: Profile[]
  clients: Client[]
  profileName: (id: string | null | undefined) => string
  clientName: (id: string | null | undefined) => string
  reloadClients: () => Promise<void>
  loading: boolean
}

const DirectoryContext = createContext<DirectoryState | undefined>(undefined)

/** Loads the small, whole-company directory (profiles + clients) once per
 * session — fine at this scale (~18 people, under 100 clients) and lets
 * every screen resolve ids to names without repeating joins everywhere. */
export function DirectoryProvider({ children }: { children: ReactNode }) {
  const { profile } = useAuth()
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [clients, setClients] = useState<Client[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    const [p, c] = await Promise.all([fetchProfiles(), fetchClients()])
    setProfiles(p)
    setClients(c)
    setLoading(false)
  }

  useEffect(() => {
    if (profile) load()
  }, [profile?.id])

  const profileName = (id: string | null | undefined) =>
    profiles.find((p) => p.id === id)?.full_name || profiles.find((p) => p.id === id)?.email || '—'

  const clientName = (id: string | null | undefined) => clients.find((c) => c.id === id)?.name || '—'

  return (
    <DirectoryContext.Provider
      value={{ profiles, clients, profileName, clientName, reloadClients: load, loading }}
    >
      {children}
    </DirectoryContext.Provider>
  )
}

export function useDirectory() {
  const ctx = useContext(DirectoryContext)
  if (!ctx) throw new Error('useDirectory must be used within a DirectoryProvider')
  return ctx
}
