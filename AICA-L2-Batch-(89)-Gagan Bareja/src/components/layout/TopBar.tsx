import React from 'react';
import {
  Building2,
  Shield,
  History,
  Search,
  Bell,
  CheckCircle2,
  ChevronDown,
  UserCheck,
  FileSpreadsheet,
  Layers,
} from 'lucide-react';
import { SystemSettings, UserRole } from '../../types';

interface TopBarProps {
  settings: SystemSettings;
  activeGstin: string;
  onSelectGstin: (gstin: string) => void;
  activeRole: UserRole;
  onSelectRole: (role: UserRole) => void;
  onOpenAuditLog: () => void;
  onOpenUploadModal: () => void;
  totalAlertsCount: number;
}

export const TopBar: React.FC<TopBarProps> = ({
  settings,
  activeGstin,
  onSelectGstin,
  activeRole,
  onSelectRole,
  onOpenAuditLog,
  onOpenUploadModal,
  totalAlertsCount,
}) => {
  const currentBranch = settings.multiGstinList.find((g) => g.gstin === activeGstin) || settings.multiGstinList[0];

  const roleLabels: Record<UserRole, { label: string; badge: string }> = {
    CFO: { label: 'CFO / Finance Head', badge: 'Full Access' },
    ACCOUNTANT: { label: 'Accountant', badge: 'Maker / Queue' },
    AUDITOR: { label: 'Statutory Auditor', badge: 'Read-Only / Trail' },
    SALES_PROCUREMENT: { label: 'Sales / Procurement', badge: 'Doc Capture' },
  };

  return (
    <header
      id="top-context-bar"
      className="h-16 bg-slate-900/90 backdrop-blur border-b border-slate-800 flex items-center justify-between px-5 sticky top-0 z-20"
    >
      {/* Left: Entity & GSTIN Switcher */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300">
            <Building2 className="w-4 h-4 text-indigo-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-100 text-sm">{settings.companyName}</span>
              <span className="text-[10px] font-mono bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 border border-slate-700">
                {settings.cin}
              </span>
            </div>
            <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-400">
              <span>Financial Year: <strong className="text-slate-200">FY 2025-26</strong></span>
              <span>•</span>
              <span className="text-emerald-400 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Books Reconciled
              </span>
            </div>
          </div>
        </div>

        {/* GSTIN / Branch Selector */}
        <div className="relative group ml-2">
          <div className="flex items-center gap-1.5 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-xs hover:border-slate-700 cursor-pointer">
            <Layers className="w-3.5 h-3.5 text-indigo-400" />
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-400 font-mono leading-none">GSTIN / Branch</span>
              <span className="text-slate-200 font-medium font-mono text-[11px] leading-tight">
                {currentBranch.gstin} ({currentBranch.stateName})
              </span>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 ml-1" />
          </div>

          {/* Dropdown for multi-GSTIN */}
          <div className="absolute left-0 top-full mt-1.5 w-72 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-2 hidden group-hover:block z-50">
            <div className="text-[11px] font-semibold text-slate-400 px-2 py-1 uppercase tracking-wider">
              Operating Entities / Branches
            </div>
            {settings.multiGstinList.map((branch) => (
              <button
                key={branch.gstin}
                onClick={() => onSelectGstin(branch.gstin)}
                className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition-colors flex items-start justify-between ${
                  activeGstin === branch.gstin
                    ? 'bg-indigo-600/20 text-indigo-200 border border-indigo-500/30'
                    : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div>
                  <div className="font-medium text-slate-100">{branch.branchName}</div>
                  <div className="font-mono text-[10px] text-slate-400">{branch.gstin}</div>
                </div>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {branch.stateName}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Right: Actions, Role Selector & Audit Trail */}
      <div className="flex items-center gap-3">
        {/* Document Upload Button */}
        <button
          id="top-quick-upload-btn"
          onClick={onOpenUploadModal}
          className="flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white text-xs font-semibold px-3.5 py-2 rounded-lg shadow-sm shadow-indigo-900/40 border border-indigo-500/30 transition-all cursor-pointer"
        >
          <FileSpreadsheet className="w-3.5 h-3.5" />
          <span>Upload Bill / Invoice (OCR)</span>
        </button>

        {/* Audit Log Trigger */}
        <button
          id="top-audit-trail-btn"
          onClick={onOpenAuditLog}
          className="flex items-center gap-1.5 bg-slate-800/80 hover:bg-slate-700 text-slate-200 text-xs font-medium px-3 py-2 rounded-lg border border-slate-700 transition-colors cursor-pointer"
          title="Audit Trail & Immutability Log"
        >
          <History className="w-3.5 h-3.5 text-amber-400" />
          <span>Audit Log</span>
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
        </button>

        {/* Role Switcher (RBAC Showcase) */}
        <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800">
          <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
          <div className="flex flex-col text-left">
            <span className="text-[9px] uppercase tracking-wider text-slate-400 font-semibold">Active Role</span>
            <select
              id="role-switcher-select"
              value={activeRole}
              onChange={(e) => onSelectRole(e.target.value as UserRole)}
              className="bg-transparent text-slate-200 text-xs font-medium focus:outline-none cursor-pointer pr-1"
            >
              <option value="CFO" className="bg-slate-900 text-slate-100">CFO / Finance Head (Full)</option>
              <option value="ACCOUNTANT" className="bg-slate-900 text-slate-100">Accountant (Entry/Queue)</option>
              <option value="AUDITOR" className="bg-slate-900 text-slate-100">Auditor (Read-Only)</option>
              <option value="SALES_PROCUREMENT" className="bg-slate-900 text-slate-100">Sales/Procurement (Upload)</option>
            </select>
          </div>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-medium">
            {roleLabels[activeRole].badge}
          </span>
        </div>
      </div>
    </header>
  );
};
