import React, { useState } from 'react';
import {
  History,
  Search,
  Calendar,
  Filter,
  RefreshCw,
  Activity,
  ShieldCheck,
  FileCheck,
  Mail,
  CheckCircle2,
  FileSpreadsheet,
  Download
} from 'lucide-react';
import { AuditLogItem } from '../types';
import { systemService } from '../lib/services/systemService';

interface AuditTrailScreenProps {
  logs: AuditLogItem[];
  loading: boolean;
  onRefresh: () => void;
}

export const AuditTrailScreen: React.FC<AuditTrailScreenProps> = ({
  logs,
  loading,
  onRefresh,
}) => {
  const [clientFilter, setClientFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('ALL');
  const [dateFilter, setDateFilter] = useState('');

  const getActionIcon = (action: string) => {
    if (action.includes('DELIVERY')) return FileSpreadsheet;
    if (action.includes('BILLING')) return Activity;
    if (action.includes('CONFIRMATION')) return CheckCircle2;
    if (action.includes('EMAIL')) return Mail;
    if (action.includes('INVOICE')) return FileCheck;
    return ShieldCheck;
  };

  const getActionBadgeColor = (action: string) => {
    if (action.includes('REJECTED')) return 'bg-rose-50 text-rose-700 border-rose-200';
    if (action.includes('INVOICE')) return 'bg-purple-50 text-purple-700 border-purple-200';
    if (action.includes('CONFIRMATION')) return 'bg-teal-50 text-teal-700 border-teal-200';
    if (action.includes('EMAIL')) return 'bg-blue-50 text-blue-700 border-blue-200';
    if (action.includes('DELIVERY')) return 'bg-indigo-50 text-indigo-700 border-indigo-200';
    return 'bg-slate-50 text-slate-700 border-slate-200';
  };

  const filteredLogs = logs.filter((log) => {
    const matchesClient =
      !clientFilter ||
      log.description.toLowerCase().includes(clientFilter.toLowerCase()) ||
      log.entityId.toLowerCase().includes(clientFilter.toLowerCase());

    const matchesAction = actionFilter === 'ALL' || log.action === actionFilter;

    const matchesDate = !dateFilter || log.createdAt.startsWith(dateFilter);

    return matchesClient && matchesAction && matchesDate;
  });

  const handleDownloadExcel = () => {
    if (filteredLogs.length === 0) return;
    systemService.downloadAuditTrailExcel(filteredLogs);
    onRefresh();
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Audit Trail &amp; Compliance</h1>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
              Immutable
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Chronological audit records of all lifecycle activities from log ingestion to invoice dispatch.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadExcel}
            disabled={filteredLogs.length === 0}
            title="Download the currently filtered audit records as an Excel (.xlsx) report"
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4" />
            <span>Download Excel</span>
          </button>
          <button
            onClick={onRefresh}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold shadow-xs transition"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh Logs</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Client filter */}
          <div className="relative w-64">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Filter by client..."
              value={clientFilter}
              onChange={(e) => setClientFilter(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Action filter */}
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="py-2 px-3 border border-slate-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-blue-500 font-medium"
          >
            <option value="ALL">All Actions</option>
            <option value="DELIVERY_LOG_UPLOADED">Delivery Log Uploaded</option>
            <option value="DELIVERY_LOG_IMPORTED">Delivery Log Imported</option>
            <option value="BILLING_CALCULATED">Billing Calculated</option>
            <option value="CONFIRMATION_EMAIL_SENT">Confirmation Email Sent</option>
            <option value="CLIENT_CONFIRMATION_RECEIVED">Client Confirmation Received</option>
            <option value="INVOICE_GENERATED">Invoice Generated</option>
            <option value="INVOICE_EMAIL_SENT">Invoice Email Sent</option>
            <option value="CLIENT_CONFIRMATION_REJECTED">Confirmation Rejected</option>
          </select>

          {/* Date filter */}
          <div className="flex items-center gap-1.5 text-xs text-slate-600 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-lg">
            <Calendar className="w-4 h-4 text-slate-400" />
            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="bg-transparent border-0 text-xs text-slate-700 focus:ring-0 p-0"
            />
            {dateFilter && (
              <button
                onClick={() => setDateFilter('')}
                className="text-slate-400 hover:text-slate-600 ml-1 text-xs"
              >
                ×
              </button>
            )}
          </div>
        </div>

        <div className="text-xs text-slate-500 font-medium">
          Showing <strong className="text-slate-900">{filteredLogs.length}</strong> of{' '}
          <strong className="text-slate-900">{logs.length}</strong> events
        </div>
      </div>

      {/* Chronological Timeline */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
        {loading ? (
          <div className="py-12 text-center text-slate-400 text-xs">Loading audit trail...</div>
        ) : filteredLogs.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            No audit records match the selected filters.
          </div>
        ) : (
          <div className="relative border-l border-slate-200 ml-4 space-y-6">
            {filteredLogs.map((log) => {
              const Icon = getActionIcon(log.action);
              const badgeColor = getActionBadgeColor(log.action);
              const dateObj = new Date(log.createdAt);

              return (
                <div key={log.id} className="relative pl-6 group">
                  {/* Timeline Node Dot */}
                  <div className="absolute -left-2.5 top-1.5 w-5 h-5 rounded-full bg-white border-2 border-blue-600 flex items-center justify-center group-hover:scale-110 transition shadow-xs">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                  </div>

                  <div className="bg-slate-50/60 hover:bg-slate-50 p-4 rounded-xl border border-slate-200/80 transition space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-bold border ${badgeColor}`}
                        >
                          <Icon className="w-3 h-3 mr-1" />
                          {log.action}
                        </span>
                        <span className="text-xs font-semibold text-slate-700">
                          {log.entity} : {log.entityId}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                        <span className="font-semibold text-slate-600">
                          {dateObj.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                        </span>
                        <span>{dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-800 leading-relaxed font-sans">
                      {log.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
