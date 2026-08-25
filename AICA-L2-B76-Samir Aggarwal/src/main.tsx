import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient } from '@tanstack/react-query'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AuthProvider } from '@/components/auth-provider'
import { isSupabaseConfigured, supabaseUrl } from '@/lib/supabase'
import ConfigNotice from '@/pages/config-notice'
import App from './App'
import './index.css'

// Open the TLS connection to Supabase before the first query needs it —
// saves a DNS + handshake round-trip on every cold start.
if (isSupabaseConfigured && supabaseUrl) {
  const link = document.createElement('link')
  link.rel = 'preconnect'
  link.href = supabaseUrl
  link.crossOrigin = 'anonymous'
  document.head.appendChild(link)
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 60_000,
      // Must outlive the persisted cache's maxAge, or restored entries are
      // garbage-collected immediately.
      gcTime: 24 * 60 * 60 * 1000,
    },
  },
})

// Last-known data is restored instantly from localStorage on startup, then
// refetched in the background — the app paints at once instead of showing
// skeletons while every table loads from zero. Cleared on sign-out.
const persister = createSyncStoragePersister({
  storage: typeof window === 'undefined' ? undefined : window.localStorage,
  key: 'asco-query-cache',
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {isSupabaseConfigured ? (
      <PersistQueryClientProvider
        client={queryClient}
        persistOptions={{
          persister,
          maxAge: 24 * 60 * 60 * 1000,
          buster: 'v1',
        }}
      >
        <BrowserRouter>
          <AuthProvider>
            <TooltipProvider delayDuration={200}>
              <App />
              <Toaster richColors closeButton position="top-right" />
            </TooltipProvider>
          </AuthProvider>
        </BrowserRouter>
      </PersistQueryClientProvider>
    ) : (
      <ConfigNotice />
    )}
  </StrictMode>,
)
