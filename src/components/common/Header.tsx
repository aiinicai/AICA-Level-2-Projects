import React from 'react';
import {
  FilePlus,
  UserPlus,
  Database,
  Wifi,
  WifiOff,
  Sparkles,
  Calendar,
  Layers,
  Lock,
  UserCheck,
  LogOut
} from 'lucide-react';
import { ModuleId, CompanyProfile, User } from '../../types';

interface HeaderProps {
  activeModule: ModuleId;
  companyProfile: CompanyProfile;
  isOnline: boolean;
  currentUser: User;
  onCreateVoucher: () => void;
  onCreateClient: () => void;
  onOpenBackupModal: () => void;
  onOpenAIAnalyst?: () => void;
  onLogout?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeModule,
  companyProfile,
  isOnline,
  currentUser,
  onCreateVoucher,
  onCreateClient,
  onOpenBackupModal,
  onOpenAIAnalyst,
  onLogout,
}) => {
  const isClientPortal = currentUser.role === 'client_portal';

  const moduleTitles: Record<ModuleId, { title: string; subtitle: string }> = {
    dashboard: {
      title: 'Operations Dashboard & Market Intelligence',
      subtitle: 'Real-time overview of demand-gap targets, repeat order cadence, and global trade indicators',
    },
    vouchers: {
      title: isClientPortal ? 'Client Document Portal' : 'Voucher & Invoicing System',
      subtitle: isClientPortal
        ? 'Access and download your finalized tax invoices, delivery notes, and proformas'
        : 'Tanzania Revenue Authority compliant Purchase Orders, Proformas, Invoices & Delivery Notes',
    },
    'pdf-toolkit': {
      title: 'Offline PDF Toolkit & Converter',
      subtitle: 'Vector merge, split, watermark, decrypt, Excel/Word converter & seal applicator',
    },
    clientele: {
      title: 'Clientele Management (CRM)',
      subtitle: 'Client directories, TIN validation, KYC documents, credit limits & repeat-order trend analytics',
    },
    intelligence: {
      title: 'Global Trade & Logistics Intelligence',
      subtitle: 'Live TZS/USD forex rates, Brent crude & Bitumen benchmarks, and Dar es Salaam Port corridor feeds',
    },
    branding: {
      title: 'Company Profile & Theme Settings',
      subtitle: 'Legal entity details, Bank accounts, Logo, Official Seal & Signature customization',
    },
    signups: {
      title: 'User Access & Sign-up Gatekeeper',
      subtitle: 'Administrator review and approval workflow for new staff and client portal accounts',
    },
    products: {
      title: 'Product Catalog & Pricing Management',
      subtitle: 'Configure inventory catalog items, unit metrics, TRA VAT taxation rules, and active status',
    },
    'payment-trends': {
      title: 'Client Payment Trends & Credit Risk Analytics',
      subtitle: 'Average Days-to-Pay tracking vs 21-day benchmark, overdue debt aging, and cash settlements',
    },
    guide: {
      title: 'Desktop User Manual',
      subtitle: 'Offline usage protocols, electron packaging, and architecture specifications',
    },
  };

  const currentInfo = moduleTitles[activeModule] || {
    title: 'Business Management Suite',
    subtitle: 'Offline-first Enterprise Platform',
  };

  const todayStr = new Date().toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  return (
    <header
      id="desktop-header"
      className="h-16 border-b border-slate-200 bg-white/95 backdrop-blur px-6 flex items-center justify-between shrink-0 z-10 select-none shadow-xs"
    >
      {/* Title & Subtitle */}
      <div className="flex items-center space-x-3">
        <div>
          <h2 className="text-base font-bold text-slate-800 tracking-tight flex items-center space-x-2">
            <span>{currentInfo.title}</span>
            {isClientPortal && (
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-bold rounded">
                Portal View
              </span>
            )}
          </h2>
          <p className="text-xs text-slate-500 hidden sm:block truncate max-w-xl">
            {currentInfo.subtitle}
          </p>
        </div>
      </div>

      {/* Quick Action Buttons & Status Indicators */}
      <div className="flex items-center space-x-3">
        {/* Date Display */}
        <div className="hidden lg:flex items-center space-x-1.5 px-3 py-1.5 bg-slate-100 rounded-md text-xs text-slate-600 font-medium border border-slate-200/60">
          <Calendar className="w-3.5 h-3.5 text-slate-400" />
          <span>{todayStr}</span>
        </div>

        {/* Global Action: New Document (Only internal users) */}
        {!isClientPortal && activeModule === 'vouchers' && (
          <button
            id="btn-quick-new-voucher"
            onClick={onCreateVoucher}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-blue-900 hover:bg-blue-800 active:bg-blue-950 text-white rounded-md text-xs font-bold shadow-xs transition"
          >
            <FilePlus className="w-3.5 h-3.5" />
            <span>Create Document</span>
          </button>
        )}

        {/* Global Action: New Client (Only internal users) */}
        {!isClientPortal && activeModule === 'clientele' && (
          <button
            id="btn-quick-new-client"
            onClick={onCreateClient}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-emerald-700 hover:bg-emerald-800 active:bg-emerald-900 text-white rounded-md text-xs font-bold shadow-xs transition"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>Add Client</span>
          </button>
        )}

        {/* AI Assistant Quick Trigger (Only internal users) */}
        {!isClientPortal && onOpenAIAnalyst && (
          <button
            id="btn-quick-ai-analyst"
            onClick={onOpenAIAnalyst}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-900 border border-blue-200 rounded-md text-xs font-bold transition"
          >
            <Sparkles className="w-3.5 h-3.5 text-blue-700" />
            <span className="hidden sm:inline">AI Market Analyst</span>
          </button>
        )}

        {/* Connectivity Pill */}
        <div
          title={isOnline ? 'Internet connection active' : 'Running offline with local database'}
          className={`flex items-center space-x-1 px-2.5 py-1 rounded-full text-[11px] font-medium border ${
            isOnline
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : 'bg-amber-50 text-amber-800 border-amber-200'
          }`}
        >
          {isOnline ? (
            <Wifi className="w-3 h-3 text-emerald-600" />
          ) : (
            <WifiOff className="w-3 h-3 text-amber-600" />
          )}
          <span className="hidden sm:inline font-mono">{isOnline ? 'Cloud' : 'Offline'}</span>
        </div>

        {/* Log Out Button */}
        {onLogout && (
          <button
            onClick={onLogout}
            title="Sign out of current tenant session"
            className="flex items-center space-x-1 px-2.5 py-1.5 bg-slate-100 hover:bg-rose-50 text-slate-600 hover:text-rose-600 border border-slate-200 hover:border-rose-200 rounded-md text-xs font-semibold transition"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Log Out</span>
          </button>
        )}
      </div>
    </header>
  );
};
