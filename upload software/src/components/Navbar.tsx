import React from 'react';
import {
  Building2,
  FileSpreadsheet,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Plus,
  Settings,
  Calculator,
  Layers,
  Archive,
  Save,
  ShieldCheck,
  LogOut,
  User,
} from 'lucide-react';
import { EntityDetails, ReconciliationReport, AppUser } from '../types/accounting';

interface NavbarProps {
  entity: EntityDetails;
  reconciliation: ReconciliationReport;
  onOpenEntityModal: () => void;
  onSelectSampleEntity: (sampleId: string) => void;
  onExportExcel: () => void;
  onExportPDF: () => void;
  onExportPPT?: () => void;
  onOpenPptDeck?: () => void;
  onOpenAdjustments: () => void;
  onOpenAiAssistant?: () => void;
  isExportingExcel: boolean;
  currentUser?: AppUser | null;
  onOpenUserManagement?: () => void;
  onOpenEntityVault?: () => void;
  onSaveEntity?: () => void;
  onLogout?: () => void;
  pendingUsersCount?: number;
  savedEntitiesCount?: number;
  isSavingEntity?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  entity,
  reconciliation,
  onOpenEntityModal,
  onSelectSampleEntity,
  onExportExcel,
  onExportPDF,
  onExportPPT,
  onOpenPptDeck,
  onOpenAdjustments,
  onOpenAiAssistant,
  isExportingExcel,
  currentUser,
  onOpenUserManagement,
  onOpenEntityVault,
  onSaveEntity,
  onLogout,
  pendingUsersCount = 0,
  savedEntitiesCount = 0,
  isSavingEntity = false,
}) => {
  return (
    <header className="bg-[#141414] text-[#E4E3E0] border-b border-[#222222] sticky top-0 z-40" id="app-navbar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          
          {/* Logo & Entity Name */}
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-none bg-[#E4E3E0] text-[#141414] flex items-center justify-center font-mono font-bold text-sm border border-[#E4E3E0]">
              <FileSpreadsheet className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-sm tracking-tight text-white font-mono flex items-center gap-1.5">
                  ACCUSHEET<span className="text-[#A3A29E]">.PRO</span>
                  <span className="text-[9px] uppercase tracking-widest bg-white/10 text-[#E4E3E0] font-mono px-1.5 py-0.5 border border-white/20">
                    NON-CORP GAAP
                  </span>
                </span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-[#A3A29E]">
                <span className="font-medium truncate max-w-[170px] text-white font-serif">{entity.name}</span>
                <span className="text-[#5E5E5E]">•</span>
                <span className="font-mono text-[10.5px]">FY {entity.financialYear}</span>
                <button
                  onClick={onOpenEntityModal}
                  className="text-[#E4E3E0] hover:text-white inline-flex items-center text-[10.5px] underline ml-1 font-mono cursor-pointer"
                  title="Edit Entity Details & Master Settings"
                  id="btn-edit-entity"
                >
                  <Settings className="w-3 h-3 mr-0.5" /> [CONFIG]
                </button>
              </div>
            </div>
          </div>

          {/* Center Status Indicators & Quick Entity Switcher */}
          <div className="hidden xl:flex items-center space-x-3">
            {/* Sample Selector */}
            <div className="flex items-center space-x-1 bg-[#222222] px-2 py-1 border border-white/10 text-[11px]">
              <span className="text-[#8E8C85] font-mono text-[10px] uppercase">Entity:</span>
              <button
                onClick={() => onSelectSampleEntity('ent-apex')}
                className={`px-2 py-0.5 text-[10.5px] font-mono transition cursor-pointer ${
                  entity.id === 'ent-apex' ? 'bg-[#E4E3E0] text-[#141414] font-bold' : 'text-[#A3A29E] hover:text-white'
                }`}
                id="btn-sample-apex"
              >
                PROPRIETORSHIP
              </button>
              <button
                onClick={() => onSelectSampleEntity('ent-kothari')}
                className={`px-2 py-0.5 text-[10.5px] font-mono transition cursor-pointer ${
                  entity.id === 'ent-kothari' ? 'bg-[#E4E3E0] text-[#141414] font-bold' : 'text-[#A3A29E] hover:text-white'
                }`}
                id="btn-sample-partnership"
              >
                PARTNERSHIP
              </button>
            </div>

            {/* Reconciliation Balance Badge */}
            <div
              className={`flex items-center space-x-1.5 px-2.5 py-1 text-[11px] font-mono font-bold border ${
                reconciliation?.isBalanceSheetBalanced && reconciliation?.isTrialBalanceBalanced
                  ? 'bg-[#1b2a1e] text-[#4ade80] border-[#4ade80]/40'
                  : 'bg-[#2f1f14] text-[#fbbf24] border-[#fbbf24]/40'
              }`}
              id="badge-reconciliation-status"
            >
              {reconciliation?.isBalanceSheetBalanced && reconciliation?.isTrialBalanceBalanced ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#4ade80]" />
                  <span>AUDIT: BALANCED (0.00)</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="w-3.5 h-3.5 text-[#fbbf24]" />
                  <span>
                    DIFF: ₹{Math.abs(reconciliation?.balanceSheetDifference ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Action Buttons: Entity Vault, Admin Users, Save & Exports */}
          <div className="flex items-center space-x-2">
            {/* Save Entity Workspace Button */}
            {onSaveEntity && (
              <button
                onClick={onSaveEntity}
                disabled={isSavingEntity}
                className="inline-flex items-center px-2.5 py-1 bg-[#1a2e1d] hover:bg-[#233d27] text-[#4ade80] text-[11px] font-mono border border-[#4ade80]/40 transition cursor-pointer disabled:opacity-50"
                title="Save this entity's trial balance, adjustments, depreciation & notes to Audit Vault"
                id="btn-quick-save-entity"
              >
                <Save className="w-3 h-3 mr-1" />
                <span>{isSavingEntity ? 'SAVING...' : 'SAVE DATA'}</span>
              </button>
            )}

            {/* Entity Vault / Archive Button */}
            {onOpenEntityVault && (
              <button
                onClick={onOpenEntityVault}
                className="inline-flex items-center px-2.5 py-1 bg-[#1e293b] hover:bg-[#334155] text-[#93c5fd] text-[11px] font-mono border border-[#3b82f6]/40 transition cursor-pointer"
                title="View and Fetch Saved Entity Data for Review"
                id="btn-entity-vault"
              >
                <Archive className="w-3 h-3 mr-1" />
                <span>ENTITY VAULT ({savedEntitiesCount})</span>
              </button>
            )}

            {/* Admin User Management Button */}
            {currentUser?.role === 'ADMIN' && onOpenUserManagement && (
              <button
                onClick={onOpenUserManagement}
                className="relative inline-flex items-center px-2.5 py-1 bg-[#2a2415] hover:bg-[#3d321d] text-[#f59e0b] text-[11px] font-mono border border-[#f59e0b]/50 transition cursor-pointer"
                title="Admin Control: Approve User IDs and manage authorizations"
                id="btn-admin-user-management"
              >
                <ShieldCheck className="w-3.5 h-3.5 mr-1" />
                <span className="hidden sm:inline">USER CONTROL</span>
                <span className="sm:hidden">ADMIN</span>
                {pendingUsersCount > 0 && (
                  <span className="ml-1.5 px-1.5 py-0.2 bg-[#dc2626] text-white text-[9px] font-bold rounded-full animate-pulse">
                    {pendingUsersCount}
                  </span>
                )}
              </button>
            )}

            {/* Year End Adjustments */}
            <button
              onClick={onOpenAdjustments}
              className="hidden lg:inline-flex items-center px-2.5 py-1 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition cursor-pointer"
              title="Add Closing Stock or Depreciation Adjustments"
              id="btn-adjustments"
            >
              <Calculator className="w-3 h-3 mr-1 text-[#A3A29E]" />
              ADJUSTMENTS
            </button>

            {/* PDF Export */}
            <button
              onClick={onExportPDF}
              className="hidden sm:inline-flex items-center px-2.5 py-1 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition cursor-pointer"
              title="Download Print-Ready PDF Statements"
              id="btn-export-pdf"
            >
              <FileText className="w-3 h-3 mr-1 text-[#f87171]" />
              PDF
            </button>

            {/* Primary Excel Workbook Export */}
            <button
              onClick={onExportExcel}
              disabled={isExportingExcel}
              className="inline-flex items-center px-3 py-1 bg-[#E4E3E0] hover:bg-white text-[#141414] text-[11px] font-mono font-bold border border-[#141414] transition disabled:opacity-50 cursor-pointer"
              title="Generate & Download Full Multi-Sheet Formula-Driven Excel Working Paper (.xlsx)"
              id="btn-export-excel-primary"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 mr-1 text-[#166534]" />
              {isExportingExcel ? 'EXPORTING...' : 'EXPORT .XLSX'}
            </button>

            {/* User Profile & Logout */}
            {currentUser && onLogout && (
              <div className="flex items-center pl-1 border-l border-white/20">
                <div className="hidden md:flex flex-col items-end pr-2 text-right">
                  <span className="text-[11px] font-mono font-bold text-white leading-tight">
                    {currentUser.id}
                  </span>
                  <span className="text-[9px] font-mono text-[#8E8C85] leading-tight">
                    {currentUser.role}
                  </span>
                </div>
                <button
                  onClick={onLogout}
                  className="p-1.5 bg-[#222222] hover:bg-[#2e2e2e] text-[#8E8C85] hover:text-[#f87171] border border-white/20 transition cursor-pointer"
                  title={`Sign out (${currentUser.id})`}
                  id="btn-logout"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>

        </div>
      </div>
    </header>
  );
};
