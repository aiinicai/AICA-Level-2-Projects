import React from 'react';
import {
  LayoutDashboard,
  FileText,
  Files,
  Users,
  TrendingUp,
  Sliders,
  HelpCircle,
  ShieldCheck,
  Building2,
  HardDrive,
  UserCheck,
  Package,
  CreditCard,
  UserPlus,
  LogOut
} from 'lucide-react';
import { ModuleId, CompanyProfile, User, UserRole } from '../../types';

interface SidebarProps {
  activeModule: ModuleId;
  onSelectModule: (module: ModuleId) => void;
  onOpenBackupModal: () => void;
  onOpenGuideModal: () => void;
  onOpenAuthModal?: () => void;
  onLogout?: () => void;
  companyProfile: CompanyProfile;
  isOnline: boolean;
  currentUser: User;
  users: User[];
  onSwitchUser: (user: User) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeModule,
  onSelectModule,
  onOpenBackupModal,
  onOpenGuideModal,
  onOpenAuthModal,
  onLogout,
  companyProfile,
  isOnline,
  currentUser,
  users,
  onSwitchUser,
}) => {
  const isClientPortal = currentUser.role === 'client_portal';

  // Define navigation items mapped to exact role matrix
  const allNavItems: {
    id: ModuleId;
    label: string;
    subLabel: string;
    icon: React.ReactNode;
    badge?: string;
    roles: UserRole[];
  }[] = [
    {
      id: 'dashboard',
      label: 'Home Dashboard',
      subLabel: 'Market Snapshot & Demand Gaps',
      icon: <LayoutDashboard className="w-5 h-5" />,
      roles: ['admin', 'finance', 'operations', 'procurement'],
    },
    {
      id: 'vouchers',
      label: isClientPortal
        ? 'My Invoices & Orders'
        : currentUser.role === 'procurement'
        ? 'Purchase Orders (PO)'
        : 'Vouchers & Invoicing',
      subLabel: isClientPortal
        ? 'Tax Invoices & Proformas'
        : currentUser.role === 'procurement'
        ? 'Vendor Purchase Orders'
        : 'PO, LPO, Proforma, Invoices',
      icon: <FileText className="w-5 h-5" />,
      roles: ['admin', 'finance', 'operations', 'procurement', 'client_portal'],
    },
    {
      id: 'pdf-toolkit',
      label: 'PDF Toolkit',
      subLabel: 'Merge, Split, Watermark, Sign',
      icon: <Files className="w-5 h-5" />,
      roles: ['admin', 'finance', 'operations', 'procurement', 'client_portal'],
    },
    {
      id: 'clientele',
      label: 'Clientele (CRM)',
      subLabel: 'Directory, KYC & Repeat Cadence',
      icon: <Users className="w-5 h-5" />,
      roles: ['admin', 'finance', 'operations'],
    },
    {
      id: 'products',
      label: 'Manage Products',
      subLabel: 'Item Master, Pricing & VAT Rules',
      icon: <Package className="w-5 h-5" />,
      roles: ['admin'],
    },
    {
      id: 'payment-trends',
      label: 'Payment Trends',
      subLabel: 'Days-to-Pay & Overdue Analysis',
      icon: <CreditCard className="w-5 h-5" />,
      roles: ['admin', 'finance'],
    },
    {
      id: 'intelligence',
      label: 'Global Intelligence',
      subLabel: 'USD/TZS, Crude, Dar Logistics',
      icon: <TrendingUp className="w-5 h-5" />,
      badge: 'Live',
      roles: ['admin', 'finance', 'operations', 'procurement'],
    },
    {
      id: 'signups',
      label: 'Pending Sign-ups',
      subLabel: 'Review & Approve Staff/Clients',
      icon: <UserCheck className="w-5 h-5" />,
      roles: ['admin'],
    },
    {
      id: 'branding',
      label: 'Company & Branding',
      subLabel: 'Logos, Seals, Theme, Bank Info',
      icon: <Sliders className="w-5 h-5" />,
      roles: ['admin'],
    },
  ];

  const visibleNavItems = allNavItems.filter((item) => item.roles.includes(currentUser.role));

  const getRoleBadgeStyle = (role: UserRole) => {
    switch (role) {
      case 'admin':
        return 'bg-purple-900/80 text-purple-200 border border-purple-700';
      case 'finance':
        return 'bg-amber-900/80 text-amber-200 border border-amber-700';
      case 'operations':
        return 'bg-blue-900/80 text-blue-200 border border-blue-700';
      case 'procurement':
        return 'bg-cyan-900/80 text-cyan-200 border border-cyan-700';
      case 'client_portal':
        return 'bg-emerald-900/80 text-emerald-200 border border-emerald-700';
      default:
        return 'bg-slate-800 text-slate-300 border border-slate-700';
    }
  };

  return (
    <aside
      id="desktop-sidebar"
      className="w-72 bg-slate-900 text-slate-100 flex flex-col justify-between border-r border-slate-800 select-none shrink-0 h-screen"
    >
      {/* App Header & Branding */}
      <div className="overflow-y-auto">
        <div className="p-4 border-b border-slate-800/80 bg-slate-950/40">
          <div className="flex items-center space-x-3">
            {companyProfile.logoUrl ? (
              <img
                src={companyProfile.logoUrl}
                alt="Company Logo"
                className="w-10 h-10 object-contain rounded bg-white/10 p-1 border border-white/10"
              />
            ) : (
              <div className="w-10 h-10 rounded-lg bg-blue-700 flex items-center justify-center text-white font-bold shadow-xs">
                <Building2 className="w-5 h-5" />
              </div>
            )}
            <div className="overflow-hidden flex-1">
              <h1 className="font-bold text-sm leading-tight text-white truncate" title={companyProfile.name}>
                {companyProfile.name}
              </h1>
              <p className="text-[11px] text-slate-400 font-mono tracking-tight">Code: <span className="text-blue-400 font-bold">{companyProfile.companyCode || 'KILI-7890'}</span></p>
            </div>
          </div>

          {/* User Profile & Role Switcher */}
          <div className="mt-3 p-2 bg-slate-800/90 rounded-lg border border-slate-700 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                Active Session
              </span>
              <span
                className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${getRoleBadgeStyle(currentUser.role)}`}
              >
                {currentUser.role === 'client_portal' ? 'Client' : currentUser.role}
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center font-bold text-xs text-white">
                {currentUser.name.slice(0, 2).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <select
                  value={currentUser.id}
                  onChange={(e) => {
                    const found = users.find((u) => u.id === e.target.value);
                    if (found) onSwitchUser(found);
                  }}
                  className="w-full bg-slate-900 border border-slate-700 text-xs font-semibold text-white rounded px-2 py-1 truncate focus:outline-none focus:border-blue-500"
                >
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name} ({u.role})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex items-center gap-1.5 mt-2">
              {onOpenAuthModal && (
                <button
                  onClick={onOpenAuthModal}
                  className="flex-1 flex items-center justify-center space-x-1 py-1 text-[10px] font-semibold text-blue-400 hover:text-blue-300 hover:bg-slate-700/50 rounded transition border border-slate-700/60"
                >
                  <UserPlus className="w-3 h-3" />
                  <span>Switch Tenant</span>
                </button>
              )}
              {onLogout && (
                <button
                  onClick={onLogout}
                  title="Sign out of current tenant"
                  className="flex items-center justify-center space-x-1 py-1 px-2 text-[10px] font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-950/50 rounded transition border border-slate-700/60"
                >
                  <LogOut className="w-3 h-3" />
                  <span>Log Out</span>
                </button>
              )}
            </div>
          </div>

          <div className="mt-2.5 flex items-center justify-between px-2.5 py-1.5 rounded-md bg-slate-800/60 border border-slate-700/50 text-[11px]">
            <div className="flex items-center space-x-1.5">
              <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400' : 'bg-amber-400'}`} />
              <span className="text-slate-300 font-medium">{isOnline ? 'Cloud Synced' : 'Cached Mode'}</span>
            </div>
            <span className="text-slate-400 text-[10px] uppercase font-mono">Multi-Tenant DB</span>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="p-3 space-y-1.5">
          <div className="px-3 py-1 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
            {isClientPortal ? 'Client Portal' : 'Core Modules'}
          </div>
          {visibleNavItems.map((item) => {
            const isActive = activeModule === item.id;
            return (
              <button
                key={item.id}
                id={`nav-btn-${item.id}`}
                onClick={() => onSelectModule(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-left transition-all duration-150 group ${
                  isActive
                    ? 'bg-blue-900 text-white font-semibold shadow-xs'
                    : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                }`}
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <span className={`${isActive ? 'text-white' : 'text-slate-400 group-hover:text-blue-300'}`}>
                    {item.icon}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold leading-snug truncate">{item.label}</p>
                    <p className={`text-[10px] leading-none truncate ${isActive ? 'text-blue-200' : 'text-slate-400'}`}>
                      {item.subLabel}
                    </p>
                  </div>
                </div>
                {item.badge && (
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold shrink-0 ${
                      isActive ? 'bg-blue-800 text-white' : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Sidebar Footer & Utilities */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/30 space-y-1 shrink-0">
        {!isClientPortal && (
          <button
            id="nav-btn-backup"
            onClick={onOpenBackupModal}
            className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition"
          >
            <HardDrive className="w-4 h-4 text-slate-400" />
            <span>Backup / Export Tenant DB</span>
          </button>
        )}

        <button
          id="nav-btn-guide"
          onClick={onOpenGuideModal}
          className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition"
        >
          <HelpCircle className="w-4 h-4 text-slate-400" />
          <span>Getting Started Guides</span>
        </button>

        <div className="pt-2 px-3 flex items-center justify-between text-[10px] text-slate-400 border-t border-slate-800/50">
          <span className="font-mono">SaaS Cloud v3.0</span>
          <span className="flex items-center space-x-1">
            <ShieldCheck className="w-3 h-3 text-blue-400" />
            <span>TRA Certified</span>
          </span>
        </div>
      </div>
    </aside>
  );
};
