import { useEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { useAuth } from '@/components/auth-provider'
import { FIRM_INITIALS } from '@/lib/constants'

export function FullPageLoader() {
  return (
    <div className="bg-background flex min-h-screen flex-col items-center justify-center gap-4">
      <div className="bg-primary text-primary-foreground grid size-12 place-items-center rounded-lg text-sm font-semibold">
        {FIRM_INITIALS}
      </div>
      <Loader2 className="text-muted-foreground size-5 animate-spin" />
    </div>
  )
}

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { session, loading } = useAuth()
  const location = useLocation()

  if (loading) return <FullPageLoader />
  if (!session) return <Navigate to="/auth" state={{ from: location.pathname }} replace />
  return <>{children}</>
}

export function AdminRoute({ children }: { children: React.ReactNode }) {
  const { session, isAdmin, loading } = useAuth()
  const location = useLocation()
  const denied = !loading && Boolean(session) && !isAdmin

  useEffect(() => {
    if (denied) toast.error('Administrator access required')
  }, [denied])

  if (loading) return <FullPageLoader />
  if (!session) return <Navigate to="/auth" state={{ from: location.pathname }} replace />
  if (!isAdmin) return <Navigate to="/my-tasks" replace />
  return <>{children}</>
}

/** Sends admins to the dashboard and everyone else to their own task list. */
export function HomeRedirect() {
  const { isAdmin, loading } = useAuth()
  if (loading) return <FullPageLoader />
  return <Navigate to={isAdmin ? '/dashboard' : '/my-tasks'} replace />
}
