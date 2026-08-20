import React from 'react';
import { History, ShieldCheck, FileText, CheckCircle2, Clock } from 'lucide-react';
import { RegulatoryUpdate, ClientAdvisory } from '../types';

interface HistoryViewProps {
  updates: RegulatoryUpdate[];
  advisories: ClientAdvisory[];
}

export const HistoryView: React.FC<HistoryViewProps> = ({ updates, advisories }) => {
  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-blue-600 mb-1">
            <History className="w-4 h-4" />
            <span>MODULE 10 — CA AUDIT TRAIL & LOGS</span>
          </div>
          <h1 className="text-xl font-bold text-slate-900">Audit Trail & Activity Log</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Preserves complete historical evidence of raw inputs, Gemini AI extraction timestamps, and CA approval decisions
          </p>
        </div>
      </div>

      {/* History Timeline Cards */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
        <h2 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
          <Clock className="w-4 h-4 text-blue-600" />
          <span>Audit Trail Records</span>
        </h2>

        <div className="space-y-3 text-xs">
          {updates.map((upd, idx) => (
            <div key={upd.id} className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5">
              <div className="flex items-center justify-between text-[11px] text-slate-500">
                <span className="font-mono text-slate-600">
                  {new Date(upd.createdAt).toLocaleString()} • ID: {upd.id}
                </span>
                <span className="px-2 py-0.5 bg-blue-100 text-blue-800 font-bold rounded-md">
                  Source: {upd.sourceType}
                </span>
              </div>

              <div className="font-bold text-slate-900">{upd.title}</div>
              <p className="text-slate-600 text-[11px]">{upd.keyDevelopment}</p>

              <div className="flex items-center space-x-4 pt-1 text-[11px] text-slate-500">
                <span>Category: {upd.category}</span>
                <span>Issuing Authority: {upd.issuingAuthority}</span>
                <span className="font-semibold text-emerald-700">Verification: {upd.verificationStatus}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
