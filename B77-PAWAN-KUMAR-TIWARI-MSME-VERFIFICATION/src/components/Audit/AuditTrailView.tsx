import React, { useState } from 'react';
import {
  History,
  Search,
  Download,
  Filter,
  ShieldCheck,
  Clock,
  UserCheck,
  FileSpreadsheet,
  Layers,
  ChevronRight,
  Eye,
  X,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { AuditLogEntry } from '../../types';
import { formatDate } from '../../utils/formatters';
import { exportTableToExcel } from '../../utils/excelService';

export const AuditTrailView: React.FC = () => {
  const { auditLogs } = useApp();

  const [searchTerm, setSearchTerm] = useState('');
  const [actionFilter, setActionFilter] = useState('ALL');
  const [entityFilter, setEntityFilter] = useState('ALL');
  const [selectedEntry, setSelectedEntry] = useState<AuditLogEntry | null>(null);

  const filteredLogs = auditLogs.filter((log) => {
    const matchesSearch =
      log.details.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.userName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (log.entityName || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.action.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesAction = actionFilter === 'ALL' || log.action === actionFilter;
    const matchesEntity = entityFilter === 'ALL' || log.entityType === entityFilter;

    return matchesSearch && matchesAction && matchesEntity;
  });

  const handleExportExcel = () => {
    const exportData = filteredLogs.map((log) => ({
      'Timestamp': formatDate(log.timestamp),
      'User Name': log.userName,
      'User Role': log.userRole,
      'Action': log.action,
      'Entity Type': log.entityType,
      'Entity Ref': log.entityName || log.entityId || '—',
      'Details': log.details,
      'IP Address': log.ipAddress || '127.0.0.1',
    }));
    exportTableToExcel(exportData, 'MSME_Audit_Trail_Log', 'Audit Trail');
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Statutory Audit Trail & Compliance Log</h2>
          <p className="text-xs text-slate-500">
            Immutable log of vendor verifications, manual due date overrides, invoice alterations and master rate updates
          </p>
        </div>

        <button
          onClick={handleExportExcel}
          className="px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
          Export Audit Trail
        </button>
      </div>

      {/* Filter and Search */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search details, user, entity, action..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:bg-white focus:border-emerald-500"
          />
        </div>

        <div className="flex items-center gap-2.5 w-full md:w-auto overflow-x-auto">
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-400 font-semibold shrink-0">Action:</span>
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700"
            >
              <option value="ALL">All Actions</option>
              <option value="VERIFY">VERIFY</option>
              <option value="CREATE">CREATE</option>
              <option value="UPDATE">UPDATE</option>
              <option value="OVERRIDE">OVERRIDE</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-400 font-semibold shrink-0">Entity:</span>
            <select
              value={entityFilter}
              onChange={(e) => setEntityFilter(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700"
            >
              <option value="ALL">All Entities</option>
              <option value="VENDOR">VENDOR</option>
              <option value="INVOICE">INVOICE</option>
              <option value="PAYMENT">PAYMENT</option>
              <option value="RATE_MASTER">RATE_MASTER</option>
              <option value="STATUTORY_RULES">STATUTORY_RULES</option>
            </select>
          </div>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase text-[10px] font-bold tracking-wider">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">User & Role</th>
                <th className="px-4 py-3">Action Type</th>
                <th className="px-4 py-3">Entity Reference</th>
                <th className="px-4 py-3">Activity Description</th>
                <th className="px-4 py-3 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                    No audit records match the current filter.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-4 py-3 text-slate-600 font-mono text-[11px] whitespace-nowrap">
                      {formatDate(log.timestamp)}
                    </td>

                    <td className="px-4 py-3">
                      <div className="font-bold text-slate-900">{log.userName.split(' ')[0]}</div>
                      <div className="text-[10px] text-slate-400 font-semibold">{log.userRole}</div>
                    </td>

                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-extrabold inline-block ${
                          log.action === 'VERIFY'
                            ? 'bg-emerald-100 text-emerald-800'
                            : log.action === 'OVERRIDE'
                            ? 'bg-purple-100 text-purple-800'
                            : log.action === 'CREATE'
                            ? 'bg-blue-100 text-blue-800'
                            : log.action === 'UPDATE'
                            ? 'bg-teal-100 text-teal-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}
                      >
                        {log.action}
                      </span>
                    </td>

                    <td className="px-4 py-3 font-semibold text-slate-800">
                      <div>{log.entityName || log.entityId}</div>
                      <div className="text-[10px] text-slate-400">{log.entityType}</div>
                    </td>

                    <td className="px-4 py-3 text-slate-700 max-w-md">
                      <p className="line-clamp-2">{log.details}</p>
                    </td>

                    <td className="px-4 py-3 text-right">
                      {(log.oldValue || log.newValue) && (
                        <button
                          onClick={() => setSelectedEntry(log)}
                          className="px-2.5 py-1 bg-white border border-slate-300 hover:bg-slate-100 rounded text-slate-700 font-semibold text-[11px] cursor-pointer"
                        >
                          Diff
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Log Diff Modal */}
      {selectedEntry && (
        <AuditDiffModal entry={selectedEntry} onClose={() => setSelectedEntry(null)} />
      )}
    </div>
  );
};

/* --- Audit Diff Modal --- */
const AuditDiffModal: React.FC<{ entry: AuditLogEntry; onClose: () => void }> = ({ entry, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden animate-in fade-in zoom-in-95 max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div>
            <h3 className="font-bold text-slate-800 text-sm">Audit Trail Change Snapshot</h3>
            <p className="text-xs text-slate-500">
              {entry.action} on {entry.entityType} ({entry.entityName || entry.entityId})
            </p>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto flex-1 text-xs">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div>
              <span className="text-slate-400 block">User:</span>
              <strong className="text-slate-800">{entry.userName}</strong>
            </div>
            <div>
              <span className="text-slate-400 block">Role:</span>
              <strong className="text-slate-800">{entry.userRole}</strong>
            </div>
            <div>
              <span className="text-slate-400 block">Timestamp:</span>
              <strong className="text-slate-800 font-mono">{formatDate(entry.timestamp)}</strong>
            </div>
            <div>
              <span className="text-slate-400 block">IP:</span>
              <strong className="text-slate-800 font-mono">{entry.ipAddress || '127.0.0.1'}</strong>
            </div>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Audit Description:</label>
            <p className="text-slate-800 bg-slate-50 p-2.5 rounded border border-slate-200">
              {entry.details}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div>
              <span className="font-bold text-slate-600 block mb-1 text-rose-700">Previous State / Old Value:</span>
              <pre className="bg-rose-50/50 border border-rose-200 rounded-lg p-3 text-[11px] font-mono text-slate-800 overflow-x-auto max-h-60">
                {entry.oldValue ? JSON.stringify(entry.oldValue, null, 2) : 'None (Created)'}
              </pre>
            </div>

            <div>
              <span className="font-bold text-slate-600 block mb-1 text-emerald-700">Committed State / New Value:</span>
              <pre className="bg-emerald-50/50 border border-emerald-200 rounded-lg p-3 text-[11px] font-mono text-slate-800 overflow-x-auto max-h-60">
                {entry.newValue ? JSON.stringify(entry.newValue, null, 2) : 'None (Deleted)'}
              </pre>
            </div>
          </div>
        </div>

        <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 flex justify-end">
          <button onClick={onClose} className="px-5 py-1.5 bg-slate-800 text-white font-bold rounded-lg text-xs">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
