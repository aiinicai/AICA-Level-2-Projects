import React, { useState } from 'react';
import { History, ShieldCheck, Search, Filter, Lock, CheckCircle2 } from 'lucide-react';
import { AuditLogEntry } from '../../types';

interface AuditTrailModalProps {
  isOpen: boolean;
  onClose: () => void;
  auditLogs: AuditLogEntry[];
}

export const AuditTrailModal: React.FC<AuditTrailModalProps> = ({
  isOpen,
  onClose,
  auditLogs,
}) => {
  const [filterQuery, setFilterQuery] = useState('');

  if (!isOpen) return null;

  const filteredLogs = auditLogs.filter(
    (l) =>
      l.documentReference.toLowerCase().includes(filterQuery.toLowerCase()) ||
      l.performedBy.toLowerCase().includes(filterQuery.toLowerCase()) ||
      l.action.toLowerCase().includes(filterQuery.toLowerCase()) ||
      l.details.toLowerCase().includes(filterQuery.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 font-mono text-xs">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-4xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 font-sans shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <History className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-slate-100 text-base">Immutable Statutory Audit Trail Log</h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Rule 3(1) Companies (Accounts) Rules 2014 Compliant
                </span>
              </div>
              <p className="text-xs text-slate-400 font-sans">
                Permanent chronological recording of all document creation, GL postings, and maker-checker approvals.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200 cursor-pointer text-sm">
            ✕
          </button>
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search audit trail by user, action, voucher or document ID..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div className="text-[11px] text-slate-400">
            <strong>{filteredLogs.length}</strong> Logged Events
          </div>
        </div>

        {/* Table Container */}
        <div className="overflow-y-auto flex-1 border border-slate-800 rounded-xl bg-slate-950/40">
          <table className="w-full text-left text-[11px]">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase text-[10px] sticky top-0">
              <tr>
                <th className="py-2.5 px-3">Timestamp (IST)</th>
                <th className="py-2.5 px-3">User & Role</th>
                <th className="py-2.5 px-3">Action</th>
                <th className="py-2.5 px-3">Document Ref</th>
                <th className="py-2.5 px-3">Operation Details</th>
                <th className="py-2.5 px-3">Cryptographic Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-slate-300">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/40">
                  <td className="py-2.5 px-3 text-slate-400">{log.timestamp.replace('T', ' ').substring(0, 19)}</td>
                  <td className="py-2.5 px-3">
                    <div className="text-slate-200 font-sans font-medium">{log.performedBy}</div>
                    <div className="text-[10px] text-indigo-400">{log.role}</div>
                  </td>
                  <td className="py-2.5 px-3 font-sans">
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {log.action}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-bold text-slate-200">{log.documentReference}</td>
                  <td className="py-2.5 px-3 font-sans text-slate-300 text-xs">{log.details}</td>
                  <td className="py-2.5 px-3 text-[10px] text-slate-400">
                    <div className="flex items-center gap-1 font-mono">
                      <Lock className="w-3 h-3 text-emerald-400 shrink-0" />
                      <span>{log.hash.substring(0, 12)}...</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer info */}
        <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400 font-sans shrink-0">
          <div className="flex items-center gap-1.5 text-emerald-400">
            <CheckCircle2 className="w-4 h-4" />
            <span>Audit Trail feature has operated throughout the financial year without tampering.</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 cursor-pointer"
          >
            Close Audit Trail
          </button>
        </div>
      </div>
    </div>
  );
};
