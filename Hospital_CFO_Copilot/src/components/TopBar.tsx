import React, { useState } from 'react';
import { Menu, Play, RefreshCw, FileSpreadsheet, ShieldCheck, Trash2, AlertTriangle, X } from 'lucide-react';
import { UserSession } from '../types';

interface TopBarProps {
  currentTab: string;
  onOpenMobileMenu: () => void;
  currentUser: UserSession | null;
  onRunControls?: () => void;
  onOpenManagementPack?: () => void;
  onClearWorkspace?: () => void;
  hasData?: boolean;
}

const TAB_TITLES: Record<string, { title: string; category: string }> = {
  dashboard: { title: 'Finance Control Tower', category: 'Overview' },
  'revenue-controls': { title: 'Billing & Revenue Controls', category: 'Revenue & Billing' },
  'department-clearance': { title: 'Departmental Billing Review', category: 'Revenue & Billing' },
  'tariff-intelligence': { title: 'Tariff & Rate Review', category: 'Revenue & Billing' },
  'receivables-collections': { title: 'Receivables & Collections', category: 'Receivables' },
  'financial-performance': { title: 'Financial Performance', category: 'Management' },
  'budget-vs-actual': { title: 'Budget vs Actual', category: 'Management' },
  'cfo-copilot': { title: 'CFO Copilot', category: 'Management' },
  'data-intelligence': { title: 'Data Import & Mapping', category: 'Governance' },
  'audit-evidence': { title: 'Audit Trail', category: 'Governance' },
  'control-settings': { title: 'Control Settings & Rules', category: 'Governance' },
};

export const TopBar: React.FC<TopBarProps> = ({
  currentTab,
  onOpenMobileMenu,
  currentUser,
  onRunControls,
  onOpenManagementPack,
  onClearWorkspace,
  hasData,
}) => {
  const [showResetModal, setShowResetModal] = useState(false);
  const currentInfo = TAB_TITLES[currentTab] || {
    title: 'Hospital CFO Copilot',
    category: 'Finance Workspace',
  };

  const isFinanceExecutive =
    currentUser?.role === 'CFO' || currentUser?.role === 'Finance/Billing Manager';

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center justify-between border-b border-slate-200/80 bg-white/95 px-4 sm:px-6 backdrop-blur-xs">
      <div className="flex items-center gap-3">
        {/* Mobile menu button */}
        <button
          onClick={onOpenMobileMenu}
          className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 lg:hidden cursor-pointer"
          aria-label="Open navigation"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Breadcrumb & Module Title */}
        <div>
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500 font-medium">
            <span>{currentInfo.category}</span>
            <span>/</span>
            <span className="text-slate-800 font-semibold">{currentInfo.title}</span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-2">
        {onOpenManagementPack && isFinanceExecutive && (
          <button
            onClick={onOpenManagementPack}
            className="hidden sm:inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-slate-900 shadow-2xs transition cursor-pointer"
          >
            <FileSpreadsheet className="h-3.5 w-3.5 text-teal-700" />
            <span>Management Pack</span>
          </button>
        )}

        {onRunControls && isFinanceExecutive && (
          <button
            onClick={onRunControls}
            className="inline-flex items-center gap-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 px-3 py-1.5 text-xs font-semibold text-white shadow-2xs transition active:scale-95 cursor-pointer"
            title="Re-run C01–C08 Financial Controls across all hospital records"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Re-run Controls</span>
          </button>
        )}

        {onClearWorkspace && hasData && isFinanceExecutive && (
          <button
            onClick={() => setShowResetModal(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50/60 hover:bg-rose-100 px-2.5 py-1.5 text-xs font-semibold text-rose-700 shadow-2xs transition active:scale-95 cursor-pointer"
            title="Delete all uploaded data and re-upload from scratch"
          >
            <Trash2 className="h-3.5 w-3.5 text-rose-600" />
            <span className="hidden md:inline">Reset Workspace</span>
          </button>
        )}
      </div>

      {/* Reset Workspace Confirmation Modal */}
      {showResetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl text-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2 text-rose-700 font-bold text-base">
                <AlertTriangle className="h-5 w-5" />
                <span>Delete Uploaded Data?</span>
              </div>
              <button
                onClick={() => setShowResetModal(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              This action will permanently remove all imported encounters, services, billings, claims, and collections from your active session and reset all controls to a clean state.
            </p>

            <div className="rounded-lg bg-amber-50 p-3 border border-amber-200 text-[11px] text-amber-900">
              <strong>Notice:</strong> You will be able to upload fresh hospital files from scratch immediately after this reset.
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setShowResetModal(false)}
                className="px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-lg transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onClearWorkspace?.();
                  setShowResetModal(false);
                }}
                className="px-4 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-xs transition cursor-pointer"
              >
                Yes, Delete Stored Data &amp; Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
