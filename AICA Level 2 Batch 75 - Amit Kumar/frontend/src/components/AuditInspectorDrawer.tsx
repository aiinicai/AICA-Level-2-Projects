import React, { useState } from 'react';
import type { ValidationItem, FinancialStatements } from '../types';
import { ShieldCheck, ShieldAlert, AlertTriangle, ChevronUp, ChevronDown, CheckCircle2, XCircle } from 'lucide-react';

interface AuditInspectorDrawerProps {
  validations: ValidationItem[];
  financialStatements: FinancialStatements | null;
}

export const AuditInspectorDrawer: React.FC<AuditInspectorDrawerProps> = ({ validations, financialStatements }) => {
  const [isOpen, setIsOpen] = useState(false);

  const criticalCount = validations.filter(v => v.status === 'Critical').length;
  const warningCount = validations.filter(v => v.status === 'Warning').length;
  const passedCount = validations.filter(v => v.status === 'Passed').length;

  const isTallied = financialStatements?.is_tallied ?? true;
  const diff = financialStatements?.difference ?? 0;

  return (
    <div className="fixed bottom-0 right-0 left-64 z-40 transition-all duration-300">
      {/* Header bar of drawer */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className={`px-6 py-2.5 flex items-center justify-between cursor-pointer border-t shadow-lg ${
          criticalCount > 0 
            ? 'bg-red-900 text-white border-red-700' 
            : warningCount > 0 
            ? 'bg-amber-900 text-white border-amber-700' 
            : 'bg-[#1B365D] text-white border-slate-700'
        }`}
      >
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2 font-bold uppercase tracking-wider">
            {criticalCount > 0 ? (
              <ShieldAlert className="w-4 h-4 text-red-300 animate-pulse" />
            ) : warningCount > 0 ? (
              <AlertTriangle className="w-4 h-4 text-amber-300" />
            ) : (
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            )}
            <span>Live Audit Inspector</span>
          </div>

          <div className="h-4 w-px bg-white/20" />

          {/* Tally Pill */}
          <div className="flex items-center gap-1.5 font-mono font-bold">
            <span>Balance Sheet Tally:</span>
            {isTallied ? (
              <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded text-[11px] flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> TALLIED (Diff: ₹0.00)
              </span>
            ) : (
              <span className="bg-red-500/20 text-red-300 border border-red-500/40 px-2 py-0.5 rounded text-[11px] flex items-center gap-1">
                <XCircle className="w-3 h-3" /> OUT OF TALLY (Diff: ₹{diff.toFixed(2)} L)
              </span>
            )}
          </div>

          <div className="h-4 w-px bg-white/20" />

          {/* Status Counts */}
          <div className="flex items-center gap-2 font-bold text-[11px]">
            <span className="bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded">{passedCount} Passed</span>
            <span className="bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded">{warningCount} Warnings</span>
            {criticalCount > 0 && (
              <span className="bg-red-500/30 text-red-200 px-2 py-0.5 rounded animate-pulse">{criticalCount} Critical Exceptions</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-semibold">
          <span>{isOpen ? 'Collapse Panel' : 'Expand Inspector'}</span>
          {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
        </div>
      </div>

      {/* Expanded Content Panel */}
      {isOpen && (
        <div className="bg-slate-900 border-t border-slate-800 p-4 max-h-64 overflow-y-auto text-xs text-slate-300">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Left: Critical Exceptions & Warnings */}
            <div>
              <h4 className="font-bold text-white uppercase text-[11px] tracking-wider mb-2 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Mapping & Accounting Sanity Alerts
              </h4>
              <div className="space-y-1.5">
                {validations.filter(v => v.status !== 'Passed').length === 0 ? (
                  <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded text-emerald-300 text-xs">
                    All 27 Schedule III audit sanity checks passed cleanly with 0 exceptions!
                  </div>
                ) : (
                  validations.filter(v => v.status !== 'Passed').map(v => (
                    <div key={v.code} className={`p-2.5 rounded border ${
                      v.status === 'Critical' ? 'bg-red-950/50 border-red-800 text-red-200' : 'bg-amber-950/50 border-amber-800 text-amber-200'
                    }`}>
                      <div className="flex items-center justify-between font-bold">
                        <span>{v.code}: {v.check_name}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded uppercase ${
                          v.status === 'Critical' ? 'bg-red-600 text-white' : 'bg-amber-600 text-white'
                        }`}>{v.status}</span>
                      </div>
                      <p className="mt-1 text-[11px] opacity-90">{v.message}</p>
                      {v.details && <p className="mt-0.5 text-[10px] opacity-75 font-mono">{v.details}</p>}
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Right: Passed Audit Checks */}
            <div>
              <h4 className="font-bold text-white uppercase text-[11px] tracking-wider mb-2 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Verified Audit Compliance Checks
              </h4>
              <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                {validations.filter(v => v.status === 'Passed').map(v => (
                  <div key={v.code} className="p-1.5 bg-slate-800/60 border border-slate-700/60 rounded text-slate-300 flex items-center justify-between text-[11px]">
                    <span className="font-medium truncate">{v.code}: {v.check_name}</span>
                    <span className="text-emerald-400 font-bold text-[10px] uppercase shrink-0">Passed</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
