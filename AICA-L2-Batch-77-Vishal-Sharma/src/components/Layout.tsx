import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import ecooLogo from '../assets/ecoo-logo.png'

export function Layout() {
  const { profile, signOut } = useAuth()

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
      isActive ? 'bg-bark-gradient text-white shadow-sm' : 'text-ink-soft hover:text-ink'
    }`

  return (
    <div className="min-h-full flex flex-col">
      <header className="border-b border-line bg-paper-raised print:hidden">
        <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center gap-6">
          <img src={ecooLogo} alt="Ecoo" className="h-10 w-auto shrink-0" />
          <nav className="flex items-center gap-1 flex-1">
            <div className="flex items-center gap-1 bg-paper border border-line rounded-lg p-1">
              {profile?.is_admin && (
                <NavLink to="/" end className={linkClass}>
                  Dashboard
                </NavLink>
              )}
              <NavLink to="/tasks" className={linkClass}>
                Tasks
              </NavLink>
              {profile?.is_admin && (
                <NavLink to="/admin/users" className={linkClass}>
                  Manage Users
                </NavLink>
              )}
            </div>
          </nav>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-ink-soft">{profile?.full_name || profile?.email}</span>
            {profile?.is_admin && (
              <span className="font-mono text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full bg-gold-bg text-gold-ink">
                Admin
              </span>
            )}
            <button
              onClick={signOut}
              className="text-ink-soft hover:text-ink underline underline-offset-2"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
