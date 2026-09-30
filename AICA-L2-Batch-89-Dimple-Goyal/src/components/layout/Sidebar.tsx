import React from 'react';
import {
  LayoutDashboard,
  Users,
  FileText,
  Landmark,
  Scale,
  Clock,
  ShieldCheck,
  Receipt,
  AlertOctagon,
  BarChart3,
  FolderArchive,
  Settings,
  HelpCircle,
  CheckCircle2,
  Lock
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { hasTabAccess } from '../../utils/rbac';

export type ActiveTab =
  | 'dashboard'
  | 'customers'
  | 'invoices'
  | 'payments'
  | 'reconciliation'
  | 'ageing'
  | 'tds'
  | 'gst'
  | 'exceptions'
  | 'reports'
  | 'documents'
  | 'settings'
  | 'tests';

interface SidebarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  onCloseMobile
}) => {
  const { currentUser, suggestedMatches, exceptions, kpis } = useApp();

  const navItems: Array<{
    id: ActiveTab;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    badge?: number | string;
    badgeColor?: string;
  }> = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'customers', label: 'Customers', icon: Users },
    {
      id: 'invoices',
      label: 'Sales / Invoices',
      icon: FileText,
      badge: kpis.unmatchedInvoicesCount > 0 ? kpis.unmatchedInvoicesCount : undefined,
      badgeColor: 'bg-slate-200 text-slate-700'
    },
    {
      id: 'payments',
      label: 'Bank Payments',
      icon: Landmark,
      badge: kpis.unallocatedReceiptsCount > 0 ? `${kpis.unallocatedReceiptsCount} New` : undefined,
      badgeColor: 'bg-amber-100 text-amber-800'
    },
    {
      id: 'reconciliation',
      label: 'Reconciliation',
      icon: Scale,
      badge: suggestedMatches.length > 0 ? `${suggestedMatches.length} Match` : undefined,
      badgeColor: 'bg-emerald-100 text-emerald-800'
    },
    { id: 'ageing', label: 'Receivables Ageing', icon: Clock },
    {
      id: 'tds',
      label: 'TDS / 26AS',
      icon: ShieldCheck,
      badge: kpis.pendingTds > 0 ? 'Mismatch' : undefined,
      badgeColor: 'bg-rose-100 text-rose-800'
    },
    { id: 'gst', label: 'GST Reconciliation', icon: Receipt },
    {
      id: 'exceptions',
      label: 'Exceptions',
      icon: AlertOctagon,
      badge: exceptions.filter(e => e.status === 'Open').length || undefined,
      badgeColor: 'bg-rose-500 text-white'
    },
    { id: 'reports', label: 'Reports & Export', icon: BarChart3 },
    { id: 'documents', label: 'Documents', icon: FolderArchive },
    { id: 'settings', label: 'Settings', icon: Settings }
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col h-full border-r border-slate-800 shrink-0 select-none">
      {/* Platform Branding */}
      <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white flex items-center justify-center font-black text-base shadow-sm">
            ₹
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h2 className="font-bold text-white text-sm tracking-tight leading-tight">FinRecon India</h2>
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                FY 26-27
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Receivables & Audit Platform</p>
          </div>
        </div>
      </div>

      {/* Main Navigation Scroll Area */}
      <nav className="flex-1 px-3 py-3 space-y-1 overflow-y-auto">
        <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Core Modules
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          const isAllowed = hasTabAccess(currentUser.role, item.id);

          return (
            <button
              key={item.id}
              onClick={() => {
                setActiveTab(item.id);
                if (onCloseMobile) onCloseMobile();
              }}
              className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium rounded-lg transition-all ${
                isActive
                  ? 'bg-emerald-600 text-white shadow-xs font-semibold'
                  : isAllowed
                  ? 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/30'
              }`}
              title={!isAllowed ? `Restricted for role: ${currentUser.role}` : undefined}
            >
              <div className="flex items-center gap-2.5 truncate">
                <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : isAllowed ? 'text-slate-400' : 'text-slate-600'}`} />
                <span className="truncate">{item.label}</span>
              </div>
              <div className="flex items-center gap-1.5">
                {!isAllowed && (
                  <Lock className="w-3 h-3 text-slate-500 shrink-0" />
                )}
                {item.badge && isAllowed && (
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${item.badgeColor}`}>
                    {item.badge}
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </nav>

      {/* Bottom Actions: Tests & Version */}
      <div className="p-3 border-t border-slate-800/80 space-y-2 bg-slate-950/40">
        <button
          onClick={() => {
            setActiveTab('tests');
            if (onCloseMobile) onCloseMobile();
          }}
          className={`w-full flex items-center gap-2.5 px-3 py-2 text-xs rounded-lg transition-all ${
            activeTab === 'tests'
              ? 'bg-emerald-600 text-white font-semibold'
              : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
          }`}
        >
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Accounting Test Suite</span>
        </button>

        <div className="pt-2 px-2 flex items-center justify-between text-[11px] text-slate-400">
          <span>v1.2.0 • Indian SME</span>
          <span className="text-emerald-400 font-mono text-[10px]">26AS • GST Ready</span>
        </div>
      </div>
    </aside>
  );
};
