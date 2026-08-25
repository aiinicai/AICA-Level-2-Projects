import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import GenerationWizardPage from './pages/GenerationWizardPage';
import TemplateManagerPage from './pages/TemplateManagerPage';
import MappingPage from './pages/MappingPage';
import ClientsPage from './pages/ClientsPage';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';
import UnlockModal from './components/UnlockModal';

export default function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>(
    (localStorage.getItem('theme') as 'light' | 'dark') || 'light',
  );
  const [unlockOpen, setUnlockOpen] = useState(false);
  const [isTemplateAdmin, setIsTemplateAdmin] = useState(!!sessionStorage.getItem('templateAdminToken'));

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('theme', theme);
  }, [theme]);

  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <header className="h-14 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex items-center px-4 gap-6 shrink-0">
          <div className="font-semibold text-brand-600 dark:text-brand-100 text-lg">CA Docs</div>
          <nav className="flex gap-1 text-sm">
            <NavTab to="/">Generate Documents</NavTab>
            <NavTab to="/clients">Manage Clients</NavTab>
            <NavTab to="/history">Generation History</NavTab>
            {isTemplateAdmin && <NavTab to="/manage-formats">Manage Formats</NavTab>}
            {isTemplateAdmin && <NavTab to="/mapping">Placeholder Mapping</NavTab>}
            {isTemplateAdmin && <NavTab to="/settings">Settings</NavTab>}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <button
              aria-label="Toggle theme"
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
              className="text-sm px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
              title="Toggle light/dark theme"
            >
              {theme === 'light' ? '🌙' : '☀️'}
            </button>
            <button
              onClick={() => (isTemplateAdmin ? undefined : setUnlockOpen(true))}
              className="text-sm px-3 py-1.5 rounded-md border border-brand-500 text-brand-600 dark:text-brand-100 hover:bg-brand-50 dark:hover:bg-gray-700"
            >
              {isTemplateAdmin ? '🔓 Manage Formats' : '🔒 Manage Formats'}
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<GenerationWizardPage />} />
            <Route
              path="/manage-formats"
              element={<TemplateManagerPage isAdmin={isTemplateAdmin} onNeedUnlock={() => setUnlockOpen(true)} />}
            />
            <Route path="/clients" element={<ClientsPage isAdmin={isTemplateAdmin} />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route
              path="/mapping"
              element={<MappingPage isAdmin={isTemplateAdmin} onNeedUnlock={() => setUnlockOpen(true)} />}
            />
          </Routes>
        </main>

        {unlockOpen && (
          <UnlockModal
            onClose={() => setUnlockOpen(false)}
            onUnlocked={() => {
              setIsTemplateAdmin(true);
              setUnlockOpen(false);
              window.location.href = '/manage-formats';
            }}
          />
        )}
      </div>
    </BrowserRouter>
  );
}

function NavTab({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `px-3 py-1.5 rounded-md ${
          isActive
            ? 'bg-brand-50 dark:bg-gray-700 text-brand-700 dark:text-white font-medium'
            : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
        }`
      }
    >
      {children}
    </NavLink>
  );
}
