import React from 'react';
import { 
  LayoutDashboard, 
  Users, 
  FileSpreadsheet, 
  Calculator, 
  CheckCircle2, 
  FileText, 
  Mail, 
  History, 
  Settings, 
  LogOut,
  ShieldCheck,
  Building,
  Database
} from 'lucide-react';
import { User } from '../types';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  currentUser: User;
  onLogout: () => void;
  pendingConfirmationsCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  currentUser,
  onLogout,
  pendingConfirmationsCount,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'clients', label: 'Clients', icon: Users },
    { id: 'delivery-logs', label: 'Delivery Logs', icon: FileSpreadsheet },
    { id: 'billing', label: 'Billing', icon: Calculator },
    { 
      id: 'confirmations', 
      label: 'Confirmations', 
      icon: CheckCircle2,
      badge: pendingConfirmationsCount > 0 ? pendingConfirmationsCount : null
    },
    { id: 'invoices', label: 'Invoices', icon: FileText },
    { id: 'emails', label: 'Email Preview', icon: Mail },
    { id: 'audit', label: 'Audit Trail', icon: History },
    ...(currentUser.role === 'Admin'
      ? [{ id: 'database', label: 'Database Viewer', icon: Database }]
      : []),
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between shrink-0 select-none">
      {/* Brand Header */}
      <div>
        <div className="p-5 border-b border-slate-800/80 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <Calculator className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-tight">FinTech Billing</h1>
            <span className="text-[10px] font-mono text-blue-400 block -mt-0.5">Automation MVP</span>
          </div>
        </div>

        {/* Nav Links */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold transition ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-amber-500 text-slate-950">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* User Profile & Logout Bottom */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/40 space-y-3">
        <div className="flex items-center gap-3 px-1">
          <div className="w-8 h-8 rounded-full bg-blue-500/20 border border-blue-400/30 flex items-center justify-center text-blue-400 font-bold text-xs">
            {currentUser.name.charAt(0)}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-slate-200 truncate">{currentUser.name}</p>
            <p className="text-[10px] text-slate-500 flex items-center gap-1 font-mono">
              <ShieldCheck className="w-3 h-3 text-emerald-500" />
              <span>{currentUser.role} Role</span>
            </p>
          </div>
        </div>

        <button
          onClick={onLogout}
          className="w-full flex items-center justify-center gap-2 py-1.5 px-3 rounded-lg border border-slate-800 text-slate-400 hover:text-rose-400 hover:bg-rose-950/20 text-xs font-medium transition"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
