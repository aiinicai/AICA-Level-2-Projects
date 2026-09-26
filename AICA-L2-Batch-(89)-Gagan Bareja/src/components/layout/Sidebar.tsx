import React from 'react';
import {
  LayoutDashboard,
  TrendingUp,
  Receipt,
  Package,
  ShoppingCart,
  BookOpen,
  ShieldCheck,
  Calculator,
  Settings,
  PlugZap,
  ChevronRight,
  AlertCircle,
  FileCheck2,
} from 'lucide-react';

export type MainNavSection =
  | 'dashboard'
  | 'analytics'
  | 'sales'
  | 'stock'
  | 'procurement'
  | 'catalogue'
  | 'compliance'
  | 'accounting'
  | 'settings'
  | 'integrations';

interface SidebarProps {
  currentSection: MainNavSection;
  onSelectSection: (section: MainNavSection) => void;
  reviewQueueCount: number;
  unmatchedBankCount: number;
}

interface NavItemConfig {
  id: MainNavSection;
  label: string;
  icon: React.ElementType;
  badge?: number | string;
  badgeColor?: string;
  description: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentSection,
  onSelectSection,
  reviewQueueCount,
  unmatchedBankCount,
}) => {
  const navItems: NavItemConfig[] = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: LayoutDashboard,
      description: 'CFO Overview & KPI tiles',
    },
    {
      id: 'analytics',
      label: 'Analytics',
      icon: TrendingUp,
      description: 'Sales, Stock & Customer DSO',
    },
    {
      id: 'sales',
      label: 'Sales',
      icon: Receipt,
      badge: reviewQueueCount > 0 ? reviewQueueCount : undefined,
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
      description: 'Invoices & Debtors Ledger',
    },
    {
      id: 'stock',
      label: 'Stock',
      icon: Package,
      description: 'Perpetual Ledger & Valuation',
    },
    {
      id: 'procurement',
      label: 'Procurement',
      icon: ShoppingCart,
      description: 'Vendor Bills & 3-Way Match',
    },
    {
      id: 'catalogue',
      label: 'Catalogue',
      icon: BookOpen,
      description: 'SKU Masters & HSN Tax Rates',
    },
    {
      id: 'compliance',
      label: 'Compliance',
      icon: ShieldCheck,
      badge: 'GST/Ageing',
      badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
      description: 'GST Returns & Schedule III',
    },
    {
      id: 'accounting',
      label: 'Accounting',
      icon: Calculator,
      badge: unmatchedBankCount > 0 ? 'Bank' : undefined,
      badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
      description: 'BS, P&L, Ledgers & Payroll',
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: Settings,
      description: 'RBAC, Multi-GSTIN & Policies',
    },
    {
      id: 'integrations',
      label: 'Integrations',
      icon: PlugZap,
      description: 'Bank AA, GSP & Document OCR',
    },
  ];

  return (
    <aside
      id="main-sidebar"
      className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 h-screen sticky top-0 z-30 select-none"
    >
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800/80 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-emerald-400 p-0.5 shadow-lg shadow-indigo-900/30 flex items-center justify-center">
          <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
            <span className="font-mono font-bold text-indigo-400 text-lg">₹</span>
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <h1 className="font-bold text-slate-100 text-sm tracking-tight truncate">Apex Synthetics</h1>
            <span className="text-[10px] font-semibold tracking-wider uppercase px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              IND
            </span>
          </div>
          <p className="text-xs text-slate-400 truncate">CFO Platform • CA 2013</p>
        </div>
      </div>

      {/* Navigation List */}
      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1 scrollbar-thin scrollbar-thumb-slate-800">
        <div className="px-2 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Financial Modules
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentSection === item.id;
          return (
            <button
              key={item.id}
              id={`nav-btn-${item.id}`}
              onClick={() => onSelectSection(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-sm font-medium transition-all group relative ${
                isActive
                  ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Icon
                className={`w-4 h-4 shrink-0 transition-colors ${
                  isActive ? 'text-indigo-400' : 'text-slate-400 group-hover:text-slate-300'
                }`}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className={`truncate ${isActive ? 'font-semibold text-white' : ''}`}>
                    {item.label}
                  </span>
                  {item.badge && (
                    <span
                      className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full border ${
                        item.badgeColor || 'bg-slate-800 text-slate-300 border-slate-700'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 truncate font-normal leading-tight mt-0.5">
                  {item.description}
                </p>
              </div>
              {isActive && (
                <ChevronRight className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              )}
            </button>
          );
        })}
      </div>

      {/* Footer System Status */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/50">
        <div className="bg-slate-900/90 rounded-lg p-2.5 border border-slate-800">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Ledger State
            </span>
            <span className="text-[11px] font-mono text-emerald-400 font-medium">Immutable</span>
          </div>
          <div className="mt-1.5 text-[11px] text-slate-400 flex items-center justify-between">
            <span>Companies Act 2013</span>
            <span className="text-slate-300 font-medium">Sched. III</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
