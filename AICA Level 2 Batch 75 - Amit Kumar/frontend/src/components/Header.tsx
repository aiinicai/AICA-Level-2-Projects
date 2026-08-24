import React, { useState, useEffect } from 'react';
import type { Client, User } from '../types';
import { Calendar, UserCheck, Sun, Moon, Sparkles, LogOut } from 'lucide-react';


interface HeaderProps {
  client: Client | null;
  clients: Client[];
  onSelectClient: (c: Client) => void;
  currentUser: User | null;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  client,
  clients,
  onSelectClient,
  currentUser,
  onLogout,
}) => {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    const savedTheme = localStorage.getItem('sw_theme') as 'light' | 'dark' | null;
    if (savedTheme) {
      setTheme(savedTheme);
      document.documentElement.setAttribute('data-theme', savedTheme);
    }
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(nextTheme);
    localStorage.setItem('sw_theme', nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
  };

  const getRoleBadgeStyle = (role?: string) => {
    switch (role) {
      case 'System Administrator':
        return 'bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border-rose-300 dark:border-rose-800';
      case 'Partner':
        return 'bg-purple-100 dark:bg-purple-950 text-purple-800 dark:text-purple-300 border-purple-300 dark:border-purple-800';
      case 'Director':
        return 'bg-indigo-100 dark:bg-indigo-950 text-indigo-800 dark:text-indigo-300 border-indigo-300 dark:border-indigo-800';
      case 'Manager':
        return 'bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300 border-blue-300 dark:border-blue-800';
      case 'Assistant Manager':
        return 'bg-cyan-100 dark:bg-cyan-950 text-cyan-800 dark:text-cyan-300 border-cyan-300 dark:border-cyan-800';
      case 'Executive':
        return 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800';
      case 'Article Assistant':
        return 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-800';
      default:
        return 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-300 border-slate-300 dark:border-slate-700';
    }
  };

  return (
    <header className="sw-header px-6 py-2.5 flex flex-wrap items-center justify-between sticky top-0 z-30 shadow-xs">
      {/* Left: FS BUILDER LITE Branding & Logo */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          {/* Logo removed */}
          
          <div className="border-l-2 border-slate-200 dark:border-slate-700 pl-3">
            <span className="text-xs font-black tracking-widest text-[#1B365D] dark:text-blue-400 uppercase block leading-none">
              FS BUILDER LITE
            </span>
            <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 tracking-wider block mt-0.5">
              
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-orange-50 dark:bg-orange-950/40 border border-orange-200 dark:border-orange-900/60 px-2.5 py-1 rounded-md ml-2">
          <span className="bg-orange-600 text-white text-[10px] font-black px-1.5 py-0.5 rounded uppercase tracking-wider flex items-center gap-1">
            <Sparkles className="w-3 h-3" /> FS BUILDER LITE
          </span>
          <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 font-mono">v0.2 | Schedule III Div I</span>
        </div>

        {clients.length > 0 && (
          <div className="flex items-center gap-2 border-l border-slate-200 dark:border-slate-700 pl-4">
            <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Client:</span>
            <select
              className="studio-input text-xs font-bold px-3 py-1.5 max-w-xs truncate"
              value={client?.id || ''}
              onChange={(e) => {
                const selected = clients.find(c => c.id === Number(e.target.value));
                if (selected) onSelectClient(selected);
              }}
            >
              {clients.map(c => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.entity_type})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Right: Active Client Metadata, User Badge & Theme Toggle */}
      <div className="flex items-center gap-3">
          {/* Logo removed */}
        {client && (
          <div className="hidden lg:flex items-center gap-2 text-xs">
            <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300">
              <Calendar className="w-3.5 h-3.5 text-orange-600" />
              <span>Period: <strong className="text-[#1B365D] dark:text-blue-400 font-bold">{client.reporting_period}</strong></span>
            </div>

            <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300">
              <UserCheck className="w-3.5 h-3.5 text-slate-600 dark:text-slate-400" />
              <span>Prep: <strong className="text-slate-900 dark:text-white font-bold">{client.prepared_by}</strong></span>
            </div>

            <div className="bg-[#1B365D] dark:bg-blue-900/60 text-white font-mono text-[11px] font-bold px-2.5 py-1 rounded border border-blue-800">
              {client.currency}
            </div>
          </div>
        )}

        {/* Enterprise Top Bar: User Name, Role & Logout */}
        {currentUser && (
          <div className="flex items-center gap-2.5 border-l border-slate-200 dark:border-slate-700 pl-3">
            <div className="flex items-center gap-2 bg-slate-50 dark:bg-slate-800/80 px-2.5 py-1 rounded-md border border-slate-200 dark:border-slate-700">
              <div className="w-7 h-7 rounded-full bg-[#1B365D] text-white flex items-center justify-center font-bold text-xs">
                {currentUser.name.charAt(0)}
              </div>
              <div className="flex flex-col text-left">
                <span className="text-xs font-bold text-slate-900 dark:text-white leading-tight flex items-center gap-1">
                  {currentUser.name}
                  <span className="text-[10px] text-slate-400 font-normal">({currentUser.employee_code})</span>
                </span>
                <span className={`text-[9px] font-black px-1.5 py-0.2 rounded border uppercase tracking-wide mt-0.5 inline-block w-fit ${getRoleBadgeStyle(currentUser.role)}`}>
                  {currentUser.role}
                </span>
              </div>
            </div>

            <button
              onClick={onLogout}
              title="Logout from FS Builder Lite"
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-bold text-rose-700 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 hover:bg-rose-100 dark:hover:bg-rose-900/60 transition-colors cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        )}

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
          className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-amber-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors cursor-pointer"
        >
          {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4 text-amber-400" />}
        </button>
      </div>
    </header>
  );
};

