import React from 'react';
import { ShieldCheck, AlertTriangle, Building2, UserCircle, Settings, Download, LogOut } from 'lucide-react';
import { NumberUnitMode } from '../utils/formatters';
import { UserRole, CompanyProfile } from '../types';

interface HeaderProps {
  currentRole: UserRole;
  userEmail?: string;
  onRoleChange: (role: UserRole) => void;
  unitMode: NumberUnitMode;
  onUnitModeChange: (mode: NumberUnitMode) => void;
  onOpenAdmin: () => void;
  onOpenInstallApp: () => void;
  onLogout?: () => void;
  activeCompany?: CompanyProfile | null;
}

export const Header: React.FC<HeaderProps> = ({
  currentRole,
  userEmail,
  onRoleChange,
  unitMode,
  onUnitModeChange,
  onOpenAdmin,
  onOpenInstallApp,
  onLogout,
  activeCompany,
}) => {
  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
      {/* Main Navbar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          {activeCompany?.logo_data ? (
            <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center shadow-md border border-slate-200 overflow-hidden p-1 relative">
              <img
                src={activeCompany.logo_data}
                alt={activeCompany.brand_name}
                className="w-full h-full object-contain"
              />
              <div className="absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full bg-[#a45139] border-2 border-white" />
            </div>
          ) : (
            <div className="w-10 h-10 rounded-xl bg-[#1b2632] text-white flex items-center justify-center shadow-md border border-[#2a3c4f] relative">
              <Building2 className="w-5 h-5 text-slate-200" />
              <div className="absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full bg-[#a45139] border-2 border-white" />
            </div>
          )}
          <div>
            <div className="flex items-center gap-2">
              <span className="font-black text-lg tracking-tight text-[#1b2632]">
                {activeCompany?.brand_name || 'GIA_Arthwise'}
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#faece7] text-[#a45139] border border-[#f5d7cf]">
                {activeCompany?.company_code ? `${activeCompany.company_code} Syndication` : 'Loan Facilitator & Syndication'}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              {activeCompany?.tagline || 'Credit Appraisal, 9-Year CMA Projections & Bank Submission Suite'}
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Currency Unit Toggle */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-medium">
            <button
              onClick={() => onUnitModeChange('standard')}
              className={`px-2.5 py-1 rounded-md transition-all ${
                unitMode === 'standard' ? 'bg-white shadow text-[#1b2632] font-semibold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              ₹ INR
            </button>
            <button
              onClick={() => onUnitModeChange('lakhs')}
              className={`px-2.5 py-1 rounded-md transition-all ${
                unitMode === 'lakhs' ? 'bg-white shadow text-[#1b2632] font-semibold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Lakhs (L)
            </button>
            <button
              onClick={() => onUnitModeChange('crores')}
              className={`px-2.5 py-1 rounded-md transition-all ${
                unitMode === 'crores' ? 'bg-white shadow text-[#1b2632] font-semibold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Crores (Cr)
            </button>
          </div>

          {/* Role Switcher */}
          <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
            <UserCircle className="w-4 h-4 text-slate-400" />
            <select
              value={currentRole}
              onChange={(e) => onRoleChange(e.target.value as UserRole)}
              className="text-xs font-medium bg-slate-50 border border-slate-200 rounded-md px-2 py-1.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#a45139]"
            >
              <option value="analyst">Role: Senior Analyst</option>
              <option value="reviewer">Role: Credit Reviewer</option>
              <option value="admin">Role: Administrator</option>
              <option value="client">Role: Borrower Client</option>
            </select>
          </div>

          {/* Install App Button */}
          <button
            onClick={onOpenInstallApp}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#faece7] hover:bg-[#f5d7cf] text-[#a45139] border border-[#f5d7cf] text-xs font-semibold transition-all shadow-2xs"
            title="Install as Desktop or Mobile App (PWA)"
          >
            <Download className="w-3.5 h-3.5 text-[#a45139]" />
            <span className="hidden sm:inline">Install App</span>
          </button>

          {/* Admin / Integrations Button */}
          {currentRole === 'admin' && (
            <button
              onClick={onOpenAdmin}
              className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-md transition-colors"
              title="Admin Settings & Audit Trail"
            >
              <Settings className="w-5 h-5" />
            </button>
          )}

          {/* Sign Out Button */}
          {onLogout && (
            <button
              onClick={onLogout}
              className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:text-rose-700 hover:bg-rose-50 rounded-lg transition-colors border border-transparent hover:border-rose-200"
              title="Sign Out to Login Screen"
            >
              <LogOut className="w-4 h-4 text-slate-500 hover:text-rose-600" />
              <span className="hidden md:inline">Sign Out</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
