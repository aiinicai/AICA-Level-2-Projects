import { Suspense, lazy, useEffect } from 'react'
import { Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/app-shell'
import { AdminRoute, FullPageLoader, HomeRedirect, ProtectedRoute } from '@/components/route-guards'
import AuthPage from '@/pages/auth'
import ResetPasswordPage from '@/pages/reset-password'
import NotFoundPage from '@/pages/not-found'

// Split per route. The dashboard alone pulls in Recharts, and an employee who
// only ever opens My Tasks should never download it.
const DashboardPage = lazy(() => import('@/pages/dashboard'))
const BoardPage = lazy(() => import('@/pages/board'))
const NeedHelpPage = lazy(() => import('@/pages/need-help'))
const ClientStatusPage = lazy(() => import('@/pages/client-status'))
const RecurringPage = lazy(() => import('@/pages/recurring'))
const EmployeesPage = lazy(() => import('@/pages/employees'))
const ClientsPage = lazy(() => import('@/pages/clients'))
const TaskMasterPage = lazy(() => import('@/pages/task-master'))
const TasksPage = lazy(() => import('@/pages/tasks'))
const TaskDetailPage = lazy(() => import('@/pages/task-detail'))
const MyTasksPage = lazy(() => import('@/pages/my-tasks'))
const ProfilePage = lazy(() => import('@/pages/profile'))

/** Everything inside the shell is already behind ProtectedRoute/AdminRoute. */
function Shell({ children }: { children: React.ReactNode }) {
  return (
    <AppShell>
      <Suspense fallback={<FullPageLoader />}>{children}</Suspense>
    </AppShell>
  )
}

export default function App() {
  // Warm the likely next screens during idle time, so first navigation after
  // sign-in does not wait on a chunk download.
  useEffect(() => {
    const warm = () => {
      void import('@/pages/dashboard')
      void import('@/pages/board')
      void import('@/pages/my-tasks')
      void import('@/pages/tasks')
    }
    if (typeof window.requestIdleCallback === 'function') {
      const id = window.requestIdleCallback(warm, { timeout: 4000 })
      return () => window.cancelIdleCallback(id)
    }
    const id = window.setTimeout(warm, 2500)
    return () => window.clearTimeout(id)
  }, [])

  return (
    <Routes>
      <Route path="/auth" element={<AuthPage />} />

      {/* Outside the guards: a recovery link creates a session that may do
          nothing except set a new password. */}
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <HomeRedirect />
          </ProtectedRoute>
        }
      />

      <Route
        path="/dashboard"
        element={
          <AdminRoute>
            <Shell>
              <DashboardPage />
            </Shell>
          </AdminRoute>
        }
      />
      {/* The board is for everyone: an employee sees only their own cards,
          because the view is security_invoker. */}
      <Route
        path="/board"
        element={
          <ProtectedRoute>
            <Shell>
              <BoardPage />
            </Shell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/need-help"
        element={
          <AdminRoute>
            <Shell>
              <NeedHelpPage />
            </Shell>
          </AdminRoute>
        }
      />
      <Route
        path="/client-status"
        element={
          <AdminRoute>
            <Shell>
              <ClientStatusPage />
            </Shell>
          </AdminRoute>
        }
      />
      <Route
        path="/client-status/:clientId"
        element={
          <AdminRoute>
            <Shell>
              <ClientStatusPage />
            </Shell>
          </AdminRoute>
        }
      />
      <Route
        path="/recurring"
        element={
          <AdminRoute>
            <Shell>
              <RecurringPage />
            </Shell>
          </AdminRoute>
        }
      />
      <Route
        path="/employees"
        element={
          <AdminRoute>
            <Shell>
              <EmployeesPage />
            </Shell>
          </AdminRoute>
        }
      />
      <Route
        path="/clients"
        element={
          <AdminRoute>
            <Shell>
              <ClientsPage />
            </Shell>
          </AdminRoute>
        }
      />
      <Route
        path="/task-master"
        element={
          <AdminRoute>
            <Shell>
              <TaskMasterPage />
            </Shell>
          </AdminRoute>
        }
      />
      <Route
        path="/tasks"
        element={
          <AdminRoute>
            <Shell>
              <TasksPage />
            </Shell>
          </AdminRoute>
        }
      />

      {/* Task detail is shared: RLS decides what an employee may open. */}
      <Route
        path="/tasks/:id"
        element={
          <ProtectedRoute>
            <Shell>
              <TaskDetailPage />
            </Shell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/my-tasks"
        element={
          <ProtectedRoute>
            <Shell>
              <MyTasksPage />
            </Shell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Shell>
              <ProfilePage />
            </Shell>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
