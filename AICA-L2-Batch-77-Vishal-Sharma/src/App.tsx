import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthProvider'
import { DirectoryProvider } from './lib/DirectoryProvider'
import { Layout } from './components/Layout'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { TaskListPage } from './pages/TaskListPage'
import { NewTaskPage } from './pages/NewTaskPage'
import { TaskDetailPage } from './pages/TaskDetailPage'
import { AdminUsersPage } from './pages/AdminUsersPage'
import { DrilldownPage } from './pages/DrilldownPage'
import { RevisionRequestsPage } from './pages/RevisionRequestsPage'
import { Loading } from './components/Loading'

function App() {
  const { session, profile, loading, signOut } = useAuth()

  if (loading) {
    return (
      <div className="min-h-full flex items-center justify-center">
        <Loading />
      </div>
    )
  }

  if (!session) return <LoginPage />

  if (!profile) {
    return (
      <div className="min-h-full flex items-center justify-center px-6">
        <p className="text-ink-soft text-center max-w-sm">
          Your account isn't set up yet. Ask an Admin to add you, then sign in again.
        </p>
      </div>
    )
  }

  if (!profile.is_admin && !profile.is_approved) {
    return (
      <div className="min-h-full flex items-center justify-center px-6">
        <div className="text-center max-w-sm flex flex-col items-center gap-3">
          <p className="font-serif text-xl font-semibold text-ink">Waiting for approval</p>
          <p className="text-ink-soft text-sm">
            Your account has been created, but an Admin still needs to approve it before you can use Ecoo
            Delegation. Check back soon, or ask your Admin directly.
          </p>
          <button onClick={signOut} className="text-sm text-ink-soft hover:text-ink underline underline-offset-2">
            Sign out
          </button>
        </div>
      </div>
    )
  }

  // The Dashboard (due-bucket report) is an Admin-only view — a plain User's
  // home is the Task List instead.
  const homePath = profile.is_admin ? '/' : '/tasks'

  return (
    <DirectoryProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={profile.is_admin ? <DashboardPage /> : <Navigate to="/tasks" replace />} />
          {profile.is_admin && <Route path="/dashboard/drilldown" element={<DrilldownPage />} />}
          {profile.is_admin && <Route path="/revisions" element={<RevisionRequestsPage />} />}
          <Route path="/tasks" element={<TaskListPage />} />
          <Route path="/tasks/new" element={<NewTaskPage />} />
          <Route path="/tasks/:id" element={<TaskDetailPage />} />
          {profile.is_admin && <Route path="/admin/users" element={<AdminUsersPage />} />}
          <Route path="*" element={<Navigate to={homePath} replace />} />
        </Route>
      </Routes>
    </DirectoryProvider>
  )
}

export default App
