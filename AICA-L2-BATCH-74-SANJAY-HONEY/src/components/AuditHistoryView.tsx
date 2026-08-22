import React, { useState } from 'react';
import { History, ShieldCheck, Search, Filter, Clock, FileText, CheckCircle2 } from 'lucide-react';
import { AuditLogEntry } from '../types';

interface AuditHistoryViewProps {
  logs: AuditLogEntry[];
}

export const AuditHistoryView: React.FC<AuditHistoryViewProps> = ({ logs }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAction, setSelectedAction] = useState('All');

  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.targetTitle.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.performedBy.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesAction = selectedAction === 'All' || log.action === selectedAction;
    return matchesSearch && matchesAction;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-teal-600 mb-1">
            <History className="w-4 h-4" />
            <span>MODULE 10 — CA AUDIT TRAIL & HISTORY LOG</span>
          </div>
          <h1 className="text-xl font-bold text-slate-900">Immutable CA Regulatory Audit Trail</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Complete record of regulatory inflows, AI matching, CA edits, approvals and client dispatches.
          </p>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-xs flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search audit trail by event, CA name, client..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:bg-white focus:outline-none"
          />
        </div>

        <select
          value={selectedAction}
          onChange={(e) => setSelectedAction(e.target.value)}
          className="bg-slate-50 border border-slate-200 text-slate-700 px-3 py-1.5 rounded-lg text-xs font-bold"
        >
          <option value="All">All Actions</option>
          <option value="Regulatory Update Inflow">Regulatory Update Inflow</option>
          <option value="Fact Extraction & Verification">Fact Extraction & Verification</option>
          <option value="Client Match Evaluated">Client Match Evaluated</option>
          <option value="Advisory Drafted">Advisory Drafted</option>
          <option value="CA Advisory Approved">CA Advisory Approved</option>
          <option value="Advisory Edited">Advisory Edited</option>
        </select>
      </div>

      {/* Logs Table / List */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
        <div className="p-4 bg-slate-50 border-b border-slate-200 font-bold text-xs text-slate-700 flex items-center justify-between">
          <span>Audit Event Stream ({filteredLogs.length} Events Logged)</span>
          <span className="text-[10px] text-slate-400">CA Regulatory Compliance Protocol</span>
        </div>

        {filteredLogs.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-500">No audit events match search filters.</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredLogs.map((log) => (
              <div key={log.id} className="p-4 hover:bg-slate-50/80 transition-colors flex items-start space-x-3 text-xs">
                <div className="p-2 bg-teal-50 border border-teal-200 rounded-xl text-teal-800 shrink-0 mt-0.5">
                  <ShieldCheck className="w-4 h-4" />
                </div>

                <div className="flex-1 space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-slate-900">{log.action}</span>
                    <span className="text-[10px] text-slate-400 font-mono">{log.timestamp}</span>
                  </div>

                  <p className="text-slate-700 font-medium">{log.details}</p>

                  <div className="flex items-center space-x-3 text-[10px] text-slate-500 pt-1">
                    <span>
                      Performed By: <strong className="text-slate-700">{log.performedBy}</strong>
                    </span>
                    <span>•</span>
                    <span>
                      Target: <strong className="text-slate-700">{log.targetTitle}</strong>
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
