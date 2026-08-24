import React, { useState } from 'react';
import { AlertTriangle, AlertCircle, CheckCircle2, X, ExternalLink, ShieldAlert, ArrowRight } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { formatINR, formatDate } from '../../utils/formatters';

interface ExceptionAlertsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ExceptionAlertsModal: React.FC<ExceptionAlertsModalProps> = ({ isOpen, onClose }) => {
  const { exceptionAlerts, setActiveTab } = useApp();
  const [filterSeverity, setFilterSeverity] = useState<'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL');

  if (!isOpen) return null;

  const filteredAlerts = exceptionAlerts.filter((a) => {
    if (filterSeverity === 'ALL') return true;
    return a.severity === filterSeverity;
  });

  const highCount = exceptionAlerts.filter((a) => a.severity === 'HIGH').length;
  const mediumCount = exceptionAlerts.filter((a) => a.severity === 'MEDIUM').length;

  const handleNavigate = (targetModule: string) => {
    onClose();
    if (targetModule === 'Vendor Master') setActiveTab('vendors');
    else if (targetModule === 'MSME Verification') setActiveTab('verification');
    else if (targetModule === 'Invoice Register') setActiveTab('invoices');
    else if (targetModule === 'Payment Register') setActiveTab('payments');
    else if (targetModule === 'Interest Calculator') setActiveTab('calculator');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-3xl overflow-hidden animate-in fade-in zoom-in-95 duration-150 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-900 text-white">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-rose-500/20 text-rose-300 rounded-lg border border-rose-500/30">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-white text-base">MSME Statutory Compliance & Exception Alerts</h3>
                <span className="px-2 py-0.5 bg-rose-500 text-white text-[10px] font-bold rounded-full">
                  {exceptionAlerts.length} Active
                </span>
              </div>
              <p className="text-xs text-slate-300">
                Automated risk flagging under MSMED Act 2006 (Sec 15/16) and Income Tax Act (Sec 43B(h))
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filter Pills */}
        <div className="px-6 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 text-xs">
            <button
              onClick={() => setFilterSeverity('ALL')}
              className={`px-3 py-1 rounded-md font-semibold transition-all ${
                filterSeverity === 'ALL'
                  ? 'bg-slate-800 text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
              }`}
            >
              All Alerts ({exceptionAlerts.length})
            </button>
            <button
              onClick={() => setFilterSeverity('HIGH')}
              className={`px-3 py-1 rounded-md font-semibold transition-all flex items-center gap-1.5 ${
                filterSeverity === 'HIGH'
                  ? 'bg-rose-600 text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-rose-700 hover:bg-rose-50'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-rose-500"></span>
              🔴 Overdue / High Risk ({highCount})
            </button>
            <button
              onClick={() => setFilterSeverity('MEDIUM')}
              className={`px-3 py-1 rounded-md font-semibold transition-all flex items-center gap-1.5 ${
                filterSeverity === 'MEDIUM'
                  ? 'bg-amber-600 text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-amber-700 hover:bg-amber-50'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-amber-500"></span>
              🟡 Attention Required ({mediumCount})
            </button>
          </div>

          <div className="text-[11px] text-slate-500 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
            <span>🟢 Compliant invoices excluded</span>
          </div>
        </div>

        {/* Alerts List */}
        <div className="p-6 overflow-y-auto space-y-3 flex-1">
          {filteredAlerts.length === 0 ? (
            <div className="py-12 text-center space-y-2">
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto" />
              <h4 className="font-bold text-slate-800 text-sm">No Pending Exceptions in this category</h4>
              <p className="text-xs text-slate-500">All vendor credentials, due dates, and tax criteria are compliant.</p>
            </div>
          ) : (
            filteredAlerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-4 rounded-xl border transition-all ${
                  alert.severity === 'HIGH'
                    ? 'bg-rose-50/40 border-rose-200 hover:border-rose-300'
                    : 'bg-amber-50/40 border-amber-200 hover:border-amber-300'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div
                      className={`p-2 rounded-lg shrink-0 mt-0.5 ${
                        alert.severity === 'HIGH'
                          ? 'bg-rose-100 text-rose-700'
                          : 'bg-amber-100 text-amber-700'
                      }`}
                    >
                      {alert.severity === 'HIGH' ? (
                        <ShieldAlert className="w-4 h-4" />
                      ) : (
                        <AlertTriangle className="w-4 h-4" />
                      )}
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span
                          className={`px-2 py-0.5 text-[10px] font-bold rounded-md uppercase tracking-wider ${
                            alert.severity === 'HIGH'
                              ? 'bg-rose-600 text-white'
                              : 'bg-amber-600 text-white'
                          }`}
                        >
                          {alert.severity === 'HIGH' ? '🔴 High Risk' : '🟡 Attention'}
                        </span>
                        <h4 className="font-bold text-slate-800 text-xs">{alert.title}</h4>
                        <span className="text-[11px] text-slate-400 font-mono">[{alert.targetModule}]</span>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">{alert.description}</p>
                      
                      <div className="pt-1 flex items-center gap-3 text-[11px]">
                        <span className="text-slate-500 font-medium">
                          Target Action: <strong className="text-slate-700">{alert.actionRequired}</strong>
                        </span>
                        {alert.amount && (
                          <span className="font-semibold text-rose-700">
                            Exposure: {formatINR(alert.amount)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleNavigate(alert.targetModule)}
                    className="shrink-0 px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-800 hover:text-white text-slate-700 text-xs font-semibold rounded-lg shadow-xs flex items-center gap-1.5 transition-all"
                  >
                    <span>Resolve</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
          <span>Automatic MSME engine check on every invoice & vendor change.</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
