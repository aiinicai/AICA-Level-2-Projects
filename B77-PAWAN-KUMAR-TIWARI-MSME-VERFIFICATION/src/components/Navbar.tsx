import React from 'react';
import {
  LayoutDashboard,
  Building2,
  ShieldCheck,
  FileText,
  CreditCard,
  Calculator,
  Clock,
  FileSpreadsheet,
  Settings2,
  History,
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export const Navbar: React.FC = () => {
  const { activeTab, setActiveTab, metrics, exceptionAlerts } = useApp();

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'vendors', label: 'Vendor Master', icon: Building2, badge: metrics.totalVendors },
    {
      id: 'verification',
      label: 'MSME Verification',
      icon: ShieldCheck,
      badge: metrics.pendingVerificationCount > 0 ? metrics.pendingVerificationCount : undefined,
      badgeColor: 'bg-amber-100 text-amber-800 border-amber-200',
    },
    { id: 'invoices', label: 'Invoice Register', icon: FileText },
    { id: 'payments', label: 'Payment Register', icon: CreditCard },
    {
      id: 'calculator',
      label: 'Interest Calculator',
      icon: Calculator,
      badge: metrics.overdueInvoicesCount > 0 ? `${metrics.overdueInvoicesCount} Overdue` : undefined,
      badgeColor: 'bg-rose-100 text-rose-800 border-rose-200',
    },
    { id: 'ageing', label: 'Ageing', icon: Clock },
    { id: 'reports', label: 'Reports', icon: FileSpreadsheet },
    { id: 'masters', label: 'Masters', icon: Settings2 },
    { id: 'audit', label: 'Audit Trail', icon: History },
  ];

  return (
    <div className="bg-white border-b border-slate-200 shadow-xs sticky top-16 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center space-x-1 overflow-x-auto py-2.5 no-scrollbar">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
                  isActive
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-500'}`} />
                <span>{tab.label}</span>
                {tab.badge !== undefined && (
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full border ${
                      isActive
                        ? 'bg-emerald-500/30 text-emerald-200 border-emerald-400/40'
                        : tab.badgeColor || 'bg-slate-200 text-slate-700 border-slate-300'
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
