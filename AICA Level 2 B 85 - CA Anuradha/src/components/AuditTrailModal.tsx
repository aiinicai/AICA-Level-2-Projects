import React, { useState, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { formatIST } from '../utils/formatters';
import { History, Search, Filter, X, Shield, Clock, ArrowRight } from 'lucide-react';

interface AuditTrailModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AuditTrailModal: React.FC<AuditTrailModalProps> = ({ isOpen, onClose }) => {
  const { auditLogs } = useApp();
  const [search, setSearch] = useState('');
  const [filterAction, setFilterAction] = useState('ALL');

  const filteredLogs = useMemo(() => {
    return auditLogs.filter((log) => {
      if (filterAction !== 'ALL' && !log.action.toLowerCase().includes(filterAction.toLowerCase())) {
        return false;
      }
      if (search.trim() !== '') {
        const q = search.toLowerCase();
        const matchesUser = log.userName.toLowerCase().includes(q);
        const matchesDetails = log.details.toLowerCase().includes(q);
        const matchesAction = log.action.toLowerCase().includes(q);
        const matchesMonth = log.monthId.toLowerCase().includes(q);
        if (!matchesUser && !matchesDetails && !matchesAction && !matchesMonth) return false;
      }
      return true;
    });
  }, [auditLogs, filterAction, search]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-3xl w-full p-6 space-y-4 max-h-[85vh] flex flex-col">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-amber-50 rounded-lg text-amber-700">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Governance & Activity Audit Trail
              </h3>
              <p className="text-xs text-slate-500">
                Chronological log of all submissions, rate locks, edits, and executive approvals (IST).
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filter Bar */}
        <div className="flex items-center gap-3 text-xs">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search audit trail by user, action, or details..."
              className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            className="bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none"
          >
            <option value="ALL">All Event Types</option>
            <option value="Submitted">Submissions</option>
            <option value="Draft">Drafts</option>
            <option value="Rate">Exchange Rate</option>
            <option value="Decision">Approvals & Decisions</option>
            <option value="Opened">Cycle Events</option>
          </select>
        </div>

        {/* Audit Log Timeline */}
        <div className="overflow-y-auto space-y-3 flex-1 pr-1">
          {filteredLogs.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs">
              No matching audit entries found.
            </div>
          ) : (
            filteredLogs.map((log) => (
              <div
                key={log.id}
                className="p-3.5 bg-slate-50/80 border border-slate-200 rounded-xl space-y-1 text-xs hover:border-slate-300 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900">{log.action}</span>
                    {log.department && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                        {log.department}
                      </span>
                    )}
                    <span className="text-[10px] text-slate-400 font-mono">
                      Cycle: {log.monthId}
                    </span>
                  </div>

                  <span className="text-[11px] font-mono text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3 text-slate-400" />
                    {formatIST(log.timestamp)}
                  </span>
                </div>

                <p className="text-slate-700">
                  {log.details}
                </p>

                <div className="text-[11px] text-slate-400 pt-0.5 flex items-center gap-1.5">
                  <span>Logged by: <strong className="text-slate-600 font-medium">{log.userName}</strong> ({log.userRole})</span>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="pt-2 border-t border-slate-100 flex justify-end text-xs">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white font-semibold rounded-lg shadow-xs"
          >
            Close Audit Log
          </button>
        </div>

      </div>
    </div>
  );
};
