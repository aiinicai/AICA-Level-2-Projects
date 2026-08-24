import React, { useState } from 'react';
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
  RotateCcw,
  UserCheck,
  ChevronDown,
  X,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { UserRole } from '../types';

interface SidebarProps {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ mobileOpen, onCloseMobile }) => {
  const {
    activeTab,
    setActiveTab,
    metrics,
    currentUserRole,
    currentUserName,
    setCurrentUserRole,
    setCurrentUserName,
    resetToDemoData,
  } = useApp();

  const [showRoleDropdown, setShowRoleDropdown] = useState(false);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'vendors', label: 'Vendor Master', icon: Building2, badge: metrics.totalVendors },
    {
      id: 'verification',
      label: 'MSME Verification',
      icon: ShieldCheck,
      badge: metrics.pendingVerificationCount > 0 ? metrics.pendingVerificationCount : undefined,
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    },
    { id: 'invoices', label: 'Invoice Register', icon: FileText, badge: metrics.overdueInvoicesCount > 0 ? `${metrics.overdueInvoicesCount}` : undefined, badgeColor: 'bg-red-500/20 text-red-300 border-red-500/30' },
    { id: 'payments', label: 'Payment Register', icon: CreditCard },
    {
      id: 'calculator',
      label: 'Interest Calculator',
      icon: Calculator,
    },
    { id: 'ageing', label: 'Ageing Analysis', icon: Clock },
    { id: 'reports', label: 'Reports & Forms', icon: FileSpreadsheet },
    { id: 'masters', label: 'Statutory Masters', icon: Settings2 },
    { id: 'audit', label: 'Audit Trail', icon: History },
  ];

  const roles: { role: UserRole; name: string; desc: string }[] = [
    {
      role: 'Admin',
      name: 'Admin User',
      desc: 'System Administrator (Full Privileges)',
    },
    {
      role: 'Finance Manager',
      name: 'Rajesh Sharma',
      desc: 'Finance Manager (Approval & Verification)',
    },
    {
      role: 'Accounts User',
      name: 'Anjali Verma',
      desc: 'Accounts Officer (Invoices & Payments)',
    },
    {
      role: 'Management',
      name: 'CFO / Executive Director',
      desc: 'Executive Board (MIS & Statutory Exposure)',
    },
    {
      role: 'Auditor',
      name: 'Statutory Auditor',
      desc: 'KPMG / Audit Partner (Read-only Verification)',
    },
  ];

  const handleSelectRole = (r: (typeof roles)[0]) => {
    setCurrentUserRole(r.role);
    setCurrentUserName(r.name);
    setShowRoleDropdown(false);
  };

  const handleNavClick = (tabId: string) => {
    setActiveTab(tabId);
    if (onCloseMobile) {
      onCloseMobile();
    }
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/70 backdrop-blur-xs z-40 lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      <nav
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-[#0f172a] text-slate-300 flex flex-col shrink-0 transform transition-transform duration-200 ease-in-out lg:static lg:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="p-5 flex items-center justify-between border-b border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center text-white font-black text-xs shadow-md shadow-blue-500/20">
              MSME
            </div>
            <div>
              <span className="font-bold text-white tracking-tight text-base block leading-none">
                FinVerify Pro
              </span>
              <span className="text-[10px] text-blue-400 font-semibold tracking-wider uppercase block mt-1">
                Know • Calculate • Comply
              </span>
            </div>
          </div>
          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="lg:hidden p-1 text-slate-400 hover:text-white rounded"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Main Menu List */}
        <div className="flex-1 py-4 overflow-y-auto no-scrollbar">
          <div className="px-5 py-2 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
            Main Menu
          </div>
          <ul className="space-y-1 px-3 mt-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;

              return (
                <li key={item.id}>
                  <button
                    onClick={() => handleNavClick(item.id)}
                    className={`w-full px-3 py-2 rounded-md font-medium text-xs flex items-center justify-between transition-colors cursor-pointer text-left ${
                      isActive
                        ? 'bg-blue-600/10 text-blue-400 font-semibold shadow-xs'
                        : 'hover:bg-slate-800 text-slate-300 hover:text-white'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                          isActive ? 'bg-blue-400' : 'bg-slate-600'
                        }`}
                      />
                      <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
                      <span className="truncate">{item.label}</span>
                    </div>

                    {item.badge !== undefined && (
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full border ${
                          isActive
                            ? 'bg-blue-500/20 text-blue-300 border-blue-400/40'
                            : item.badgeColor || 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="px-5 pt-5 pb-2 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
            Statutory Standards
          </div>
          <div className="px-5 space-y-1.5 text-[11px] text-slate-400">
            <div className="flex items-center justify-between py-1 border-b border-slate-800/80">
              <span>Section 15 Limit</span>
              <strong className="text-slate-200">45 / 15 Days</strong>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-800/80">
              <span>Section 16 Rate</span>
              <strong className="text-emerald-400">3x RBI (Comp.)</strong>
            </div>
            <div className="flex items-center justify-between py-1">
              <span>Section 43B(h)</span>
              <strong className="text-rose-400">Micro & Small</strong>
            </div>
          </div>
        </div>

        {/* User Profile & Role Switcher */}
        <div className="p-3.5 border-t border-slate-700/50 bg-[#0b1222] relative">
          <div
            onClick={() => setShowRoleDropdown(!showRoleDropdown)}
            className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-800/80 cursor-pointer transition-colors"
          >
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-blue-600/30 border border-blue-500/40 flex items-center justify-center text-xs font-bold text-blue-300 shrink-0">
                {currentUserName.split(' ').map((n) => n[0]).slice(0, 2).join('')}
              </div>
              <div className="overflow-hidden text-left">
                <div className="text-xs font-semibold text-white truncate">
                  {currentUserName}
                </div>
                <div className="text-[10px] text-slate-400 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  <span>{currentUserRole}</span>
                </div>
              </div>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          </div>

          {/* Role Dropdown */}
          {showRoleDropdown && (
            <div className="absolute bottom-16 left-3 right-3 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl py-2 z-50 text-xs">
              <div className="px-3 py-1.5 border-b border-slate-800 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Switch Role (RBAC)
              </div>
              {roles.map((r) => (
                <button
                  key={r.role}
                  onClick={() => handleSelectRole(r)}
                  className={`w-full text-left px-3 py-2 hover:bg-slate-800 flex items-center justify-between text-xs transition-colors ${
                    currentUserRole === r.role ? 'bg-blue-600/20 text-blue-300 font-bold' : 'text-slate-300'
                  }`}
                >
                  <div>
                    <div className="font-semibold">{r.name}</div>
                    <div className="text-[10px] text-slate-400">{r.role}</div>
                  </div>
                  {currentUserRole === r.role && (
                    <span className="text-[10px] text-blue-400 font-bold">Active</span>
                  )}
                </button>
              ))}
              <div className="px-3 pt-2 mt-1 border-t border-slate-800 flex items-center justify-between">
                <button
                  onClick={() => {
                    resetToDemoData();
                    setShowRoleDropdown(false);
                  }}
                  className="text-[11px] font-medium text-rose-400 hover:text-rose-300 flex items-center gap-1 cursor-pointer"
                >
                  <RotateCcw className="w-3 h-3" /> Reset Demo
                </button>
              </div>
            </div>
          )}
        </div>
      </nav>
    </>
  );
};
