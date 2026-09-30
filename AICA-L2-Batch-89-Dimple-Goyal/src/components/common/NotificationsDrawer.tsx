import React from 'react';
import { X, AlertTriangle, AlertCircle, Clock, ShieldAlert, ArrowRight } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { formatINR } from '../../utils/formatters';
import { ActiveTab } from '../layout/Sidebar';

interface NotificationsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (tab: ActiveTab) => void;
}

export const NotificationsDrawer: React.FC<NotificationsDrawerProps> = ({
  isOpen,
  onClose,
  onNavigate
}) => {
  const { kpis, exceptions, bankTransactions, invoices } = useApp();

  if (!isOpen) return null;

  const overdueInvoices = invoices.filter(i => i.status === 'Overdue');
  const unallocatedReceipts = bankTransactions.filter(t => t.isCredit && t.unallocatedAmount > 0);

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-xs" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 max-w-md w-full bg-white shadow-2xl border-l border-slate-200 flex flex-col z-50 animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
          <div>
            <h3 className="font-bold text-slate-900 text-sm">Actionable Notifications</h3>
            <p className="text-xs text-slate-500">Live receivables & reconciliation alerts</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* List of Alerts */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 text-xs">
          {/* Overdue Invoices Alert */}
          {overdueInvoices.length > 0 && (
            <div className="p-3 rounded-lg border border-rose-200 bg-rose-50/40">
              <div className="flex items-start gap-2.5">
                <Clock className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-bold text-rose-900">
                    {overdueInvoices.length} invoices are overdue ({formatINR(kpis.totalOverdue)})
                  </p>
                  <p className="text-rose-700 text-[11px] mt-0.5">
                    Critical aging: {formatINR(kpis.overdue90Plus)} overdue by more than 90 days.
                  </p>
                  <button
                    onClick={() => {
                      onNavigate('ageing');
                      onClose();
                    }}
                    className="mt-2 text-xs font-semibold text-rose-800 hover:text-rose-950 flex items-center gap-1"
                  >
                    <span>View Ageing Breakdown</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Unallocated Receipts Alert */}
          {unallocatedReceipts.length > 0 && (
            <div className="p-3 rounded-lg border border-amber-200 bg-amber-50/40">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-bold text-amber-900">
                    {formatINR(kpis.unallocatedReceiptsAmount)} unallocated bank receipts
                  </p>
                  <p className="text-amber-700 text-[11px] mt-0.5">
                    {kpis.unallocatedReceiptsCount} credit deposits received in bank require customer invoice allocation.
                  </p>
                  <button
                    onClick={() => {
                      onNavigate('reconciliation');
                      onClose();
                    }}
                    className="mt-2 text-xs font-semibold text-amber-800 hover:text-amber-950 flex items-center gap-1"
                  >
                    <span>Run Reconciliation Match</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TDS Discrepancy Alert */}
          {kpis.mismatchTds > 0 && (
            <div className="p-3 rounded-lg border border-purple-200 bg-purple-50/40">
              <div className="flex items-start gap-2.5">
                <ShieldAlert className="w-4 h-4 text-purple-600 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-bold text-purple-900">
                    {formatINR(kpis.mismatchTds)} TDS Mismatches in Form 26AS
                  </p>
                  <p className="text-purple-700 text-[11px] mt-0.5">
                    TDS deducted or deposited under incorrect rates or missing in 26AS/AIS portal statement.
                  </p>
                  <button
                    onClick={() => {
                      onNavigate('tds');
                      onClose();
                    }}
                    className="mt-2 text-xs font-semibold text-purple-800 hover:text-purple-950 flex items-center gap-1"
                  >
                    <span>Resolve TDS Mismatches</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Active Exceptions List */}
          <div className="pt-2">
            <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
              Exceptions Requiring Attention ({exceptions.filter(e => e.status === 'Open').length})
            </h4>
            <div className="space-y-2">
              {exceptions.filter(e => e.status === 'Open').map(exc => (
                <div key={exc.id} className="p-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">{exc.category}</span>
                    <span className="font-mono font-bold text-slate-800">{formatINR(exc.amount)}</span>
                  </div>
                  <p className="text-[11px] text-slate-600 mt-1">{exc.remarks}</p>
                  <div className="flex items-center justify-between text-[10px] text-slate-400 mt-2">
                    <span>Assigned: {exc.assignedTo}</span>
                    <span className="font-bold text-rose-600 uppercase">{exc.priority} Priority</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-slate-200 bg-slate-50 text-center">
          <button
            onClick={() => {
              onNavigate('exceptions');
              onClose();
            }}
            className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition-colors shadow-xs"
          >
            Open Exceptions Centre
          </button>
        </div>
      </div>
    </div>
  );
};
