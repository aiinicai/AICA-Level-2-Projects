import React from 'react';
import { Calendar, RefreshCw, Database, Mail, LogOut, ShieldCheck } from 'lucide-react';
import { User } from '../types';

interface HeaderProps {
  currentTab: string;
  currentUser: User;
  onRefresh: () => void;
  isRefreshing: boolean;
  onSelectTab?: (tab: string) => void;
  onLogout?: () => void;
  theme?: string;
  onThemeChange?: (theme: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  currentUser,
  onRefresh,
  isRefreshing,
  onSelectTab,
  onLogout,
  theme,
  onThemeChange,
}) => {
  const getTabTitle = (tab: string) => {
    switch (tab) {
      case 'dashboard':
        return 'Executive Billing Dashboard';
      case 'clients':
        return 'Enterprise Client Accounts';
      case 'delivery-logs':
        return 'Delivery Logs & Excel Upload';
      case 'billing':
        return 'Quarterly File Billing Calculation';
      case 'confirmations':
        return 'Client Confirmations';
      case 'invoices':
        return 'Generated Tax Invoices';
      case 'emails':
        return 'Email Preview & Outbox';
      case 'audit':
        return 'Compliance Audit Trail';
      case 'database':
        return 'Database Viewer & Schema Inspector';
      case 'settings':
        return 'System Configuration';
      default:
        return 'Billing System';
    }
  };

  return (
    <header className="h-14 bg-white border-b border-slate-200 px-6 sm:px-8 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        <h2 className="text-base font-bold text-slate-900">{getTabTitle(currentTab)}</h2>
        <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-600">
          Cycle: Q1 FY 2026-27
        </span>
      </div>

      <div className="flex items-center gap-3">
        {/* Environment Status Pills */}
        <div className="hidden lg:flex items-center gap-2 text-xs">
          {currentUser.role === 'Admin' && (
            <button
              onClick={() => onSelectTab && onSelectTab('database')}
              title="Click to open live Database Viewer"
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 font-medium text-[11px] transition cursor-pointer"
            >
              <Database className="w-3 h-3 text-emerald-600" />
              <span>SQLite Active (View DB)</span>
            </button>
          )}
          <button
            onClick={() => onSelectTab && onSelectTab('emails')}
            title="Click to view Email Outbox"
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 font-medium text-[11px] transition cursor-pointer"
          >
            <Mail className="w-3 h-3 text-blue-600" />
            <span>Demo Email Mode</span>
          </button>
        </div>

        {/* Theme Selector */}
        {onThemeChange && (
          <div className="flex items-center gap-1 border border-slate-200 rounded-lg p-1 bg-slate-50">
            <button
              onClick={() => onThemeChange('blue')}
              title="Blue Theme"
              className={`w-5 h-5 rounded-md cursor-pointer transition ${theme === 'blue' || !theme ? 'bg-blue-600 ring-2 ring-blue-300 ring-offset-1' : 'bg-blue-400 hover:bg-blue-500'}`}
            />
            <button
              onClick={() => onThemeChange('pink')}
              title="Pink Theme"
              className={`w-5 h-5 rounded-md cursor-pointer transition ${theme === 'pink' ? 'bg-pink-600 ring-2 ring-pink-300 ring-offset-1' : 'bg-pink-400 hover:bg-pink-500'}`}
            />
            <button
              onClick={() => onThemeChange('orange')}
              title="Orange Theme"
              className={`w-5 h-5 rounded-md cursor-pointer transition ${theme === 'orange' ? 'bg-orange-600 ring-2 ring-orange-300 ring-offset-1' : 'bg-orange-400 hover:bg-orange-500'}`}
            />
          </div>
        )}

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Refresh All System Data"
          className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-50 transition cursor-pointer"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-blue-600' : ''}`} />
        </button>

        {/* User Role Badge & Sign Out in Header */}
        <div className="flex items-center gap-2 pl-3 border-l border-slate-200">
          <div className="hidden sm:flex flex-col text-right">
            <span className="text-xs font-bold text-slate-800 leading-tight">{currentUser.name}</span>
            <span className="text-[10px] text-slate-500 font-mono flex items-center justify-end gap-1">
              <ShieldCheck className="w-3 h-3 text-blue-600" />
              <span>{currentUser.role}</span>
            </span>
          </div>

          {onLogout && (
            <button
              onClick={onLogout}
              title="Sign Out to Login Page"
              className="flex items-center gap-1.5 py-1 px-2.5 rounded-lg text-xs font-semibold text-rose-600 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
