import React, { useState } from 'react';
import {
  Wrench,
  RotateCcw,
  CheckCircle2,
  Users,
  Building2,
  BookOpen,
  Hash,
  ShieldAlert,
  AlertTriangle,
} from 'lucide-react';
import { generateSeedData } from '../../data/seedEngine';
import { CHART_OF_ACCOUNTS } from '../../data/chartOfAccounts';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { USERS } from '../../data/users';
import { getAllCurrentSequences } from '../../core/sequences';
import { ConfirmDialog } from '../../components/ConfirmDialog';

interface AdministrationPageProps {
  onNavigate: (route: string) => void;
  initialTab?: string;
}

export const AdministrationPage: React.FC<AdministrationPageProps> = ({
  onNavigate,
  initialTab = 'coa',
}) => {
  const [activeTab, setActiveTab] = useState(initialTab === 'reset' ? 'reset' : 'coa');
  const [isResetConfirmOpen, setIsResetConfirmOpen] = useState(false);
  const [resetSuccess, setResetSuccess] = useState(false);

  const sequences = getAllCurrentSequences();

  const handleResetDemoData = () => {
    generateSeedData();
    setIsResetConfirmOpen(false);
    setResetSuccess(true);
    setTimeout(() => {
      window.location.reload();
    }, 1000);
  };

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50 select-none">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <Wrench className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">System Administration & Masters</h1>
            <p className="text-xs text-gray-500">
              Manage enterprise charts, organizational segments, approval limits, and demo database state.
            </p>
          </div>
        </div>

        <button
          onClick={() => setIsResetConfirmOpen(true)}
          className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-2 transition-colors cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Demo Data</span>
        </button>
      </div>

      {resetSuccess && (
        <div className="mb-5 p-4 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>Demo data successfully re-seeded with 2026 PRNG determinism. Reloading ERP workspace...</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-gray-200 mb-5">
        <button
          onClick={() => setActiveTab('coa')}
          className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
            activeTab === 'coa'
              ? 'border-[#5B2C83] text-[#5B2C83]'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Chart of Accounts (60+ IFRS Accounts)
        </button>
        <button
          onClick={() => setActiveTab('bu')}
          className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
            activeTab === 'bu'
              ? 'border-[#5B2C83] text-[#5B2C83]'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Business Units (15 Balancing Segments)
        </button>
        <button
          onClick={() => setActiveTab('users')}
          className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
            activeTab === 'users'
              ? 'border-[#5B2C83] text-[#5B2C83]'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Users & Approval Limits (Maker/Checker)
        </button>
        <button
          onClick={() => setActiveTab('sequences')}
          className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
            activeTab === 'sequences'
              ? 'border-[#5B2C83] text-[#5B2C83]'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Document Sequences
        </button>
        <button
          onClick={() => setActiveTab('reset')}
          className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
            activeTab === 'reset'
              ? 'border-rose-600 text-rose-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Reset Demo State
        </button>
      </div>

      {/* Tab Panels */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs p-6 overflow-hidden">
        {/* COA TAB */}
        {activeTab === 'coa' && (
          <div>
            <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-3">
              IFRS Chart of Accounts & Control Account Constraints
            </h2>
            <div className="overflow-x-auto max-h-[600px]">
              <table className="w-full text-xs text-left border-collapse">
                <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold sticky top-0 border-b border-plum-200">
                  <tr>
                    <th className="py-2.5 px-3 w-20">Code</th>
                    <th className="py-2.5 px-3">Account Name</th>
                    <th className="py-2.5 px-3 w-24">Type</th>
                    <th className="py-2.5 px-3 w-24">Balance</th>
                    <th className="py-2.5 px-3">IFRS Line</th>
                    <th className="py-2.5 px-3 w-36 text-center">Control Account?</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {CHART_OF_ACCOUNTS.map((a) => (
                    <tr key={a.code} className="hover:bg-plum-50/20">
                      <td className="py-2 px-3 font-mono font-bold text-[#5B2C83]">{a.code}</td>
                      <td className="py-2 px-3 font-medium text-gray-900">{a.name}</td>
                      <td className="py-2 px-3">{a.type}</td>
                      <td className="py-2 px-3">{a.normalBalance}</td>
                      <td className="py-2 px-3 text-gray-600">{a.ifrsLine}</td>
                      <td className="py-2 px-3 text-center">
                        {a.isControlAccount ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900">
                            Blocked from Manual JV
                          </span>
                        ) : (
                          <span className="text-gray-400 text-[10px]">Manual Allowed</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* BUSINESS UNITS TAB */}
        {activeTab === 'bu' && (
          <div>
            <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-3">
              15 Balancing Segments (Hospitals, Clinics, Pharmacies)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {BUSINESS_UNITS.map((bu) => (
                <div key={bu.code} className="p-3.5 rounded-lg border border-gray-200 bg-gray-50/50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono font-bold text-sm text-[#5B2C83]">{bu.code}</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-plum-100 text-[#5B2C83]">
                      {bu.type}
                    </span>
                  </div>
                  <h3 className="font-bold text-xs text-gray-900">{bu.name}</h3>
                  <div className="mt-2 text-[11px] text-gray-500 space-y-0.5">
                    <div>Emirate: <strong className="text-gray-700">{bu.emirate}</strong></div>
                    <div>VAT TRN: <span className="font-mono text-gray-700">{bu.vatTrn}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* USERS TAB */}
        {activeTab === 'users' && (
          <div>
            <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-3">
              Users & Segregation of Duties Approval Limits
            </h2>
            <div className="divide-y divide-gray-100">
              {USERS.map((u) => (
                <div key={u.userId} className="py-3 flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-xs text-gray-900">{u.name}</h3>
                    <p className="text-[11px] text-gray-500">
                      User ID: <span className="font-mono font-medium text-gray-800">{u.userId}</span> &bull; Role: {u.role}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-plum-100 text-[#5B2C83]">
                      {u.approvalLimitAED ? `Limit: AED ${u.approvalLimitAED.toLocaleString()}` : u.approvalLimitAED === null ? 'Unlimited Limit' : 'Maker Only (No Approval)'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SEQUENCES TAB */}
        {activeTab === 'sequences' && (
          <div>
            <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-3">
              Active Gapless Document Sequences
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {sequences.map((s, idx) => (
                <div key={idx} className="p-3 rounded-lg border border-gray-200 bg-gray-50">
                  <div className="font-mono font-bold text-xs text-[#5B2C83]">{s.prefix} ({s.year})</div>
                  <div className="text-lg font-bold text-gray-900 mt-1">{s.current}</div>
                  <span className="text-[10px] text-gray-400">Current atomic counter</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* RESET TAB */}
        {activeTab === 'reset' && (
          <div className="max-w-xl mx-auto py-8 text-center">
            <div className="w-12 h-12 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mx-auto mb-3">
              <RotateCcw className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-gray-900">Reset Demo Data to Initial State</h2>
            <p className="text-xs text-gray-600 mt-2 leading-relaxed">
              This action will reset IndexedDB and deterministically re-seed opening balances, masters, and 100s of transactions across all 15 business units using the PRNG engine (seed 2026).
            </p>
            <div className="mt-6">
              <button
                onClick={() => setIsResetConfirmOpen(true)}
                className="px-6 py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg shadow-sm transition-colors cursor-pointer"
              >
                Reset Everything & Re-Seed
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Confirm Reset Dialog */}
      {isResetConfirmOpen && (
        <ConfirmDialog
          isOpen={isResetConfirmOpen}
          onClose={() => setIsResetConfirmOpen(false)}
          onConfirm={handleResetDemoData}
          title="Confirm Reset Demo Data"
          message="Are you sure you want to completely re-seed the ERP database? All local test modifications will be reset to the standard Meridian Healthcare Group demo baseline."
          type="danger"
          confirmLabel="Yes, Reset Database"
        />
      )}
    </div>
  );
};
