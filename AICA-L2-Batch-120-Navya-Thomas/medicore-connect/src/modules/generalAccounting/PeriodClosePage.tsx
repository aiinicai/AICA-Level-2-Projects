import React, { useState } from 'react';
import {
  Calendar,
  Lock,
  Unlock,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldCheck,
  Building2,
  FileSpreadsheet,
  Receipt,
  Landmark,
  ArrowLeftRight,
} from 'lucide-react';
import { getFiscalPeriods, setPeriodStatus } from '../../core/periods';
import { getDb } from '../../core/storage';
import { getActiveUser } from '../../core/auth';
import { FiscalPeriod } from '../../core/types';

interface PeriodClosePageProps {
  onNavigate: (route: string) => void;
}

export const PeriodClosePage: React.FC<PeriodClosePageProps> = ({ onNavigate }) => {
  const [periods, setPeriods] = useState(getFiscalPeriods());
  const [selectedPeriod, setSelectedPeriod] = useState<string>('Oct-26');
  const [msg, setMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const db = getDb();
  const currentUser = getActiveUser();
  const isCFO = currentUser.role === 'CFO';

  const currentPeriodObj = periods.find((p) => p.name === selectedPeriod);

  // Module Checklist for the selected period
  const unapprovedAP = db.apInvoices.filter((i) => i.status === 'Pending Approval').length;
  const heldAP = db.apInvoices.filter((i) => i.holds?.length > 0).length;
  const unapprovedAR = db.arTransactions.filter((i) => i.status === 'Pending Approval').length;
  const unpostedCash = db.cashVouchers.filter((v) => v.status === 'Pending Approval').length;
  const unreconciledBank = db.bankStatements.reduce(
    (acc, s) => acc + s.lines.filter((l) => !l.isReconciled).length,
    0
  );
  const depreciationRun = db.depreciationRuns.find((r) => r.period === selectedPeriod && r.status === 'Posted');
  const pendingIC = db.icTransactions.filter((i) => i.status === 'Pending Approval').length;

  const checklist = [
    {
      module: 'Payables (AP)',
      icon: FileSpreadsheet,
      task: 'All AP invoices approved and accounted to GL',
      status: unapprovedAP === 0 ? 'COMPLETED' : 'WARNING',
      details: `${unapprovedAP} invoice(s) pending approval, ${heldAP} on hold`,
      link: '#/payables/invoices',
    },
    {
      module: 'Receivables (AR)',
      icon: Receipt,
      task: 'All billing claims and receipts posted',
      status: unapprovedAR === 0 ? 'COMPLETED' : 'WARNING',
      details: `${unapprovedAR} AR transaction(s) pending approval`,
      link: '#/receivables/billing',
    },
    {
      module: 'Fixed Assets',
      icon: Building2,
      task: `Fixed Asset Depreciation run for ${selectedPeriod}`,
      status: depreciationRun ? 'COMPLETED' : 'PENDING',
      details: depreciationRun ? `Posted on ${depreciationRun.runDate}` : 'Depreciation run pending for this period',
      link: '#/fixed-assets/depreciation',
    },
    {
      module: 'Cash Management',
      icon: Landmark,
      task: 'Bank statements reconciled against subledgers',
      status: unreconciledBank === 0 ? 'COMPLETED' : 'WARNING',
      details: `${unreconciledBank} bank statement line(s) unmatched`,
      link: '#/cash/bank-reconciliation',
    },
    {
      module: 'Intercompany',
      icon: ArrowLeftRight,
      task: 'Intercompany accounts balanced across group',
      status: pendingIC === 0 ? 'COMPLETED' : 'WARNING',
      details: pendingIC === 0 ? 'Net elimination variance: 0.00 AED' : `${pendingIC} transaction(s) pending acceptance`,
      link: '#/intercompany/reconciliation',
    },
  ];

  const handleToggleStatus = (targetPeriod: string, nextStatus: 'Open' | 'Closed') => {
    if (!isCFO) {
      setMsg({
        text: 'Access Denied: Only the Chief Financial Officer (Daniel Reed) has authority to close or open fiscal periods.',
        type: 'error',
      });
      return;
    }

    setPeriodStatus(targetPeriod, nextStatus);
    setPeriods(getFiscalPeriods());
    setMsg({
      text: `Fiscal Period ${targetPeriod} has been successfully updated to status: ${nextStatus}.`,
      type: 'success',
    });
  };

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <Calendar className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">Fiscal Period Close & Controls</h1>
            <p className="text-xs text-gray-500">
              Manage 2026 calendar periods, module closing checklists, and CFO authorization controls.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500">Current User:</span>
          <span className="text-xs font-semibold px-2.5 py-1 rounded bg-plum-100 text-[#5B2C83]">
            {currentUser.name} ({currentUser.role})
          </span>
        </div>
      </div>

      {msg && (
        <div
          className={`mb-5 p-3.5 rounded-lg text-xs flex items-center justify-between border ${
            msg.type === 'success'
              ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
              : 'bg-rose-50 border-rose-300 text-rose-800'
          }`}
        >
          <span>{msg.text}</span>
          <button onClick={() => setMsg(null)} className="font-bold ml-2">
            &times;
          </button>
        </div>
      )}

      {/* 2026 Fiscal Periods Calendar Strip */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs p-5 mb-6">
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-gray-100">
          <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
            2026 Fiscal Calendar Overview
          </h2>
          <span className="text-xs text-gray-500">Calendar Year Basis &bull; Currency AED</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2">
          {periods.map((p) => {
            const isSelected = selectedPeriod === p.name;
            const isOpen = p.status === 'Open';
            const isClosed = p.status === 'Closed';

            return (
              <div
                key={p.name}
                onClick={() => setSelectedPeriod(p.name)}
                className={`p-3 rounded-lg border text-center cursor-pointer transition-all ${
                  isSelected
                    ? 'ring-2 ring-[#5B2C83] bg-plum-50 border-[#5B2C83]'
                    : 'bg-white border-gray-200 hover:border-plum-200'
                }`}
              >
                <div className="font-bold text-xs text-gray-900">{p.name}</div>
                <div className="my-1.5 flex justify-center">
                  {isOpen ? (
                    <span className="inline-flex items-center text-[10px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded-full">
                      <Unlock className="w-2.5 h-2.5 mr-0.5" />
                      Open
                    </span>
                  ) : isClosed ? (
                    <span className="inline-flex items-center text-[10px] font-bold text-gray-600 bg-gray-100 px-1.5 py-0.5 rounded-full">
                      <Lock className="w-2.5 h-2.5 mr-0.5" />
                      Closed
                    </span>
                  ) : (
                    <span className="inline-flex items-center text-[10px] font-bold text-plum-600 bg-plum-50 px-1.5 py-0.5 rounded-full">
                      <Clock className="w-2.5 h-2.5 mr-0.5" />
                      Future
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Selected Period Detail & Module Checklist */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Period Status Card (4 cols) */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-gray-200 shadow-xs p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
              <span className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                Period Status Controls
              </span>
              <span className="font-mono font-bold text-lg text-[#5B2C83]">{selectedPeriod}</span>
            </div>

            <div className="space-y-3 text-xs mb-6">
              <div className="flex justify-between py-1 border-b border-gray-50">
                <span className="text-gray-500">Period Name:</span>
                <span className="font-bold text-gray-900">{currentPeriodObj?.name}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-50">
                <span className="text-gray-500">Start Date:</span>
                <span className="font-medium text-gray-800">{currentPeriodObj?.startDate}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-50">
                <span className="text-gray-500">End Date:</span>
                <span className="font-medium text-gray-800">{currentPeriodObj?.endDate}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-50">
                <span className="text-gray-500">Current Status:</span>
                <span
                  className={`font-bold ${
                    currentPeriodObj?.status === 'Open'
                      ? 'text-emerald-700'
                      : currentPeriodObj?.status === 'Closed'
                      ? 'text-gray-600'
                      : 'text-plum-600'
                  }`}
                >
                  {currentPeriodObj?.status}
                </span>
              </div>
            </div>

            <p className="text-[11px] text-gray-500 leading-relaxed mb-4">
              Posting journals and subledger transactions to <strong>Closed</strong> or <strong>Future</strong> periods is strictly blocked by the posting engine. Only open periods allow transactional entries.
            </p>
          </div>

          {/* Action buttons */}
          <div className="pt-4 border-t border-gray-100 space-y-2">
            {currentPeriodObj?.status === 'Open' ? (
              <button
                onClick={() => handleToggleStatus(selectedPeriod, 'Closed')}
                className="w-full py-2.5 px-3 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white font-semibold text-xs rounded-lg shadow-xs flex items-center justify-center space-x-1.5 transition-colors cursor-pointer"
              >
                <Lock className="w-3.5 h-3.5 text-amber-300" />
                <span>Close Period {selectedPeriod}</span>
              </button>
            ) : (
              <button
                onClick={() => handleToggleStatus(selectedPeriod, 'Open')}
                className="w-full py-2.5 px-3 bg-emerald-700 hover:bg-emerald-800 text-white font-semibold text-xs rounded-lg shadow-xs flex items-center justify-center space-x-1.5 transition-colors cursor-pointer"
              >
                <Unlock className="w-3.5 h-3.5 text-white" />
                <span>Re-open Period {selectedPeriod}</span>
              </button>
            )}
            {!isCFO && (
              <p className="text-[10px] text-amber-700 text-center">
                Note: Switch user to Daniel Reed (CFO) to change period status.
              </p>
            )}
          </div>
        </div>

        {/* Right: Close Checklist (8 cols) */}
        <div className="lg:col-span-8 bg-white rounded-xl border border-gray-200 shadow-xs p-5">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
            <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-[#5B2C83]" />
              <span>Pre-Closing Module Verification Checklist</span>
            </h2>
            <span className="text-[11px] text-gray-400">Section 6.4 Specification</span>
          </div>

          <div className="space-y-3">
            {checklist.map((item, idx) => {
              const IconComp = item.icon;
              const isDone = item.status === 'COMPLETED';

              return (
                <div
                  key={idx}
                  className="p-3 rounded-lg border border-gray-200 hover:border-plum-200 bg-gray-50/50 flex items-center justify-between transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <div className="p-2 rounded bg-white border border-gray-200 text-[#5B2C83]">
                      <IconComp className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-gray-900">{item.task}</span>
                        <span className="text-[10px] text-gray-500">({item.module})</span>
                      </div>
                      <p className="text-[11px] text-gray-500 mt-0.5">{item.details}</p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    {isDone ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                        <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" />
                        Ready
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                        <AlertTriangle className="w-3 h-3 mr-1 text-amber-600" />
                        Action Req.
                      </span>
                    )}
                    <button
                      onClick={() => onNavigate(item.link)}
                      className="text-xs text-[#5B2C83] hover:underline font-semibold"
                    >
                      Review &rarr;
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
