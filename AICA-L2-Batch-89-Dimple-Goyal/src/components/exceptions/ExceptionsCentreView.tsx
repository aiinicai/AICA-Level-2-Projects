import React, { useState, useMemo } from 'react';
import {
  AlertOctagon,
  Download,
  CheckCircle2,
  Clock,
  User,
  Filter,
  ArrowRight,
  MessageSquare,
  AlertTriangle
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { ExceptionItem } from '../../types';
import { formatINR, formatDate } from '../../utils/formatters';
import { exportToCSV, exportToExcel } from '../../utils/excelEngine';

export const ExceptionsCentreView: React.FC = () => {
  const { exceptions, resolveException, currentUser } = useApp();
  const [categoryFilter, setCategoryFilter] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string>('Open');
  const [priorityFilter, setPriorityFilter] = useState<string>('All');

  const canEdit = currentUser.role !== 'Viewer';

  const filteredExceptions = useMemo(() => {
    return exceptions.filter(e => {
      const matchCat = categoryFilter === 'All' || e.category === categoryFilter;
      const matchStat = statusFilter === 'All' || e.status === statusFilter;
      const matchPri = priorityFilter === 'All' || e.priority === priorityFilter;
      return matchCat && matchStat && matchPri;
    });
  }, [exceptions, categoryFilter, statusFilter, priorityFilter]);

  const handleExport = (type: 'csv' | 'excel') => {
    const exportData = filteredExceptions.map(e => ({
      'Category': e.category,
      'Customer': e.customerName || 'N/A',
      'Invoice No': e.invoiceNumber || 'N/A',
      'Amount': e.amount,
      'Priority': e.priority,
      'Assigned To': e.assignedTo,
      'Status': e.status,
      'Remarks / Cause': e.remarks,
      'Created Date': e.createdAt
    }));

    if (type === 'csv') exportToCSV(exportData, 'Exceptions_FinRecon');
    else exportToExcel(exportData, 'Exceptions_FinRecon', 'Exceptions');
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Exceptions & Discrepancies Centre</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Audit triage for short payments, excess payments, unmatched receipts, and TDS/GST divergences.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport('excel')}
            className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors flex items-center gap-1.5"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Export Exceptions</span>
          </button>
        </div>
      </div>

      {/* Filter and Category Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 text-xs">
        <div className="flex items-center gap-2">
          <label className="font-semibold text-slate-700">Category:</label>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="p-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-700"
          >
            <option value="All">All Categories</option>
            <option value="Short Payment">Short Payment</option>
            <option value="Unmatched Receipt">Unmatched Receipt</option>
            <option value="TDS Mismatch">TDS Mismatch</option>
            <option value="GST Mismatch">GST Mismatch</option>
            <option value="Overdue Invoice">Overdue Invoice</option>
          </select>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <label className="font-semibold text-slate-700">Status:</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="p-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-700"
            >
              <option value="All">All Statuses</option>
              <option value="Open">Open Only</option>
              <option value="In Progress">In Progress</option>
              <option value="Resolved">Resolved</option>
            </select>
          </div>

          <div className="flex items-center gap-1">
            <label className="font-semibold text-slate-700">Priority:</label>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="p-1.5 rounded-lg border border-slate-200 bg-slate-50 text-slate-700"
            >
              <option value="All">All Priorities</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </div>
        </div>
      </div>

      {/* Exceptions Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500 tracking-wider">
              <tr>
                <th className="p-3.5">Category & Priority</th>
                <th className="p-3.5">Entity / Customer</th>
                <th className="p-3.5">Invoice / Reference</th>
                <th className="p-3.5 text-right">Variance Amount</th>
                <th className="p-3.5">Assigned To</th>
                <th className="p-3.5">Remarks / Root Cause</th>
                <th className="p-3.5 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredExceptions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-400">
                    No open exceptions matching current filters!
                  </td>
                </tr>
              ) : (
                filteredExceptions.map((exc) => (
                  <tr key={exc.id} className="hover:bg-slate-50">
                    <td className="p-3.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900">{exc.category}</span>
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                            exc.priority === 'High'
                              ? 'bg-rose-100 text-rose-800'
                              : exc.priority === 'Medium'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {exc.priority}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-400 block mt-0.5">{formatDate(exc.createdAt)}</span>
                    </td>

                    <td className="p-3.5">
                      <span className="font-semibold text-slate-800 block truncate max-w-xs">
                        {exc.customerName || 'Direct Bank Entry'}
                      </span>
                    </td>

                    <td className="p-3.5 font-mono text-slate-600">
                      {exc.invoiceNumber || 'N/A'}
                    </td>

                    <td className="p-3.5 text-right font-mono font-bold text-slate-900">
                      {formatINR(exc.amount, false)}
                    </td>

                    <td className="p-3.5 text-slate-700">
                      <span className="flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        <span>{exc.assignedTo}</span>
                      </span>
                    </td>

                    <td className="p-3.5 max-w-xs text-slate-600">
                      <p className="truncate">{exc.remarks}</p>
                    </td>

                    <td className="p-3.5 text-center">
                      {exc.status === 'Open' && canEdit ? (
                        <button
                          onClick={() => {
                            const res = prompt('Enter resolution remarks:');
                            if (res) resolveException(exc.id, res);
                          }}
                          className="px-2.5 py-1 text-xs font-bold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 rounded-lg transition-colors flex items-center gap-1 mx-auto"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Resolve</span>
                        </button>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                          {exc.status}
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
