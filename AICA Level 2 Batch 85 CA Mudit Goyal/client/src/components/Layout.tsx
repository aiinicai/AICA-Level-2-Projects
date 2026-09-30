import React, { useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface NavItem {
  to: string;
  label: string;
  icon: string;
  adminOnly?: boolean;
}

const NAV: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: '▤' },
  { to: '/invoices', label: 'Invoices', icon: '₹' },
  { to: '/attendance', label: 'Attendance', icon: '◷' },
  { to: '/attendance/register', label: 'Register', icon: '☰', adminOnly: true },
  { to: '/staff', label: 'Staff', icon: '⛁', adminOnly: true },
  { to: '/settings', label: 'Settings', icon: '⚙' },
];

/**
 * The app shell: a sidebar on a desktop, a bottom bar on a phone.
 *
 * Both render from the same NAV list, so a page added here appears in the
 * right place on both without the two lists drifting apart.
 */
const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isAdmin, signOut } = useAuth();
  const navigate = useNavigate();
  const [updateReady, setUpdateReady] = useState(false);

  // The service worker fires this when a newer build has been downloaded.
  useEffect(() => {
    const onUpdate = () => setUpdateReady(true);
    window.addEventListener('sw-update-available', onUpdate);
    return () => window.removeEventListener('sw-update-available', onUpdate);
  }, []);

  const applyUpdate = () => {
    navigator.serviceWorker?.getRegistration().then((reg) => {
      reg?.waiting?.postMessage({ type: 'SKIP_WAITING' });
      window.location.reload();
    });
  };

  const items = NAV.filter((item) => !item.adminOnly || isAdmin);

  const handleSignOut = () => {
    signOut();
    navigate('/login', { replace: true });
  };

  const linkClass = (isActive: boolean, mobile: boolean) => {
    if (mobile) {
      return `flex-1 flex flex-col items-center gap-0.5 py-2 text-[11px] ${
        isActive ? 'text-brand-700 font-semibold' : 'text-gray-500'
      }`;
    }
    return `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition-colors ${
      isActive ? 'bg-brand-700 text-white font-medium' : 'text-brand-100 hover:bg-brand-600'
    }`;
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      {updateReady && (
        <div className="fixed top-0 inset-x-0 z-50 bg-brand-700 text-white text-sm px-4 py-2 flex items-center justify-between">
          <span>A new version is ready.</span>
          <button onClick={applyUpdate} className="underline font-medium">
            Refresh
          </button>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className="hidden md:flex md:w-60 md:flex-col bg-brand-800 text-white">
        <div className="px-5 py-6 border-b border-brand-700">
          <div className="text-lg font-semibold">MGSG Lite</div>
          <div className="text-xs text-brand-100 mt-0.5">Invoicing &amp; Attendance</div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {items.map((item) => (
            <NavLink key={item.to} to={item.to} end className={({ isActive }) => linkClass(isActive, false)}>
              <span aria-hidden className="w-5 text-center">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-brand-700 text-sm">
          <div className="font-medium truncate">{user?.staffName ?? user?.email}</div>
          <div className="text-xs text-brand-100">{user?.designation ?? user?.role}</div>
          <button onClick={handleSignOut} className="mt-3 text-xs underline text-brand-100 hover:text-white">
            Sign out
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="md:hidden bg-brand-800 text-white px-4 py-3 flex items-center justify-between">
        <div>
          <div className="font-semibold leading-tight">MGSG Lite</div>
          <div className="text-[11px] text-brand-100">{user?.staffName ?? user?.email}</div>
        </div>
        <button onClick={handleSignOut} className="text-xs underline text-brand-100">
          Sign out
        </button>
      </header>

      <main className="flex-1 min-w-0 pb-16 md:pb-0">
        <div className="max-w-6xl mx-auto p-4 md:p-6">{children}</div>
      </main>

      {/* Mobile bottom bar */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 flex z-40">
        {items.map((item) => (
          <NavLink key={item.to} to={item.to} end className={({ isActive }) => linkClass(isActive, true)}>
            <span aria-hidden className="text-base leading-none">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
};

export default Layout;
