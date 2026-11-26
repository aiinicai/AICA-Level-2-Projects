import React, { useMemo, useState } from 'react';
import { Download, Edit3, Play, Search, X } from 'lucide-react';
import { formatDateRangeLabel, roundDays } from '../lib/dateUtils';
import { exportBalancesToExcel } from '../lib/leaveService';
import type {
  Employee,
  LeaveBalance,
  LeaveCategory,
  LeaveRequest,
} from '../types/leave';

interface BalanceLedgerViewProps {
  currentEmployee: Employee;
  year: number;
  categories: LeaveCategory[];
  myBalances: LeaveBalance[];
  myRequests: LeaveRequest[];
  allEmployees: Employee[];
  allBalances: LeaveBalance[];
  isAdmin: boolean;
  isManager: boolean;
  onCancelRequest: (requestId: string) => Promise<void>;
  onAdjustBalance: (balance: LeaveBalance, opening: number, accrued: number) => Promise<void>;
  onRunMonthlyAccrual: () => void;
}

const STATUS_STYLE: Record<string, string> = {
  approved: 'text-emerald-700 font-medium',
  pending: 'text-amber-700 font-medium',
  rejected: 'text-red-700 font-medium',
  cancelled: 'text-slate-500 font-medium',
};

export const BalanceLedgerView: React.FC<BalanceLedgerViewProps> = ({
  currentEmployee,
  year,
  categories,
  myBalances,
  myRequests,
  allEmployees,
  allBalances,
  isAdmin,
  isManager,
  onCancelRequest,
  onAdjustBalance,
  onRunMonthlyAccrual,
}) => {
  const [scopeTab, setScopeTab] = useState<'my' | 'org'>('my');
  const [searchTerm, setSearchTerm] = useState('');
  const [editingBalance, setEditingBalance] = useState<LeaveBalance | null>(null);
  const [editOpening, setEditOpening] = useState<string>('0');
  const [editAccrued, setEditAccrued] = useState<string>('0');
  const [savingEdit, setSavingEdit] = useState(false);

  const pendingByCat = useMemo(() => {
    const map = new Map<string, number>();
    for (const req of myRequests) {
      if (req.status === 'pending' && Number(req.startDate.slice(0, 4)) === year) {
        map.set(req.categoryId, roundDays((map.get(req.categoryId) || 0) + req.workingDays));
      }
    }
    return map;
  }, [myRequests, year]);

  const personalRows = useMemo(() => {
    return categories
      .filter((c) => c.active)
      .map((cat) => {
        const bal = myBalances.find((b) => b.year === year && b.categoryId === cat.id);
        const opening = bal ? bal.opening : cat.defaultOpening;
        const accrued = bal ? bal.accrued : 0;
        const availed = bal ? bal.availed : 0;
        const closing = bal ? bal.closing : cat.defaultOpening;
        const pending = pendingByCat.get(cat.id) || 0;
        return {
          category: cat,
          opening,
          accrued,
          availed,
          pending,
          closing,
        };
      });
  }, [categories, myBalances, pendingByCat, year]);

  const orgBalancesFiltered = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    return allBalances
      .filter((b) => b.year === year)
      .filter((b) => {
        if (!q) return true;
        return (
          b.employeeName.toLowerCase().includes(q) ||
          b.employeeEmail.toLowerCase().includes(q) ||
          b.categoryName.toLowerCase().includes(q)
        );
      })
      .sort(
        (a, b) =>
          a.employeeName.localeCompare(b.employeeName) ||
          a.categoryName.localeCompare(b.categoryName)
      );
  }, [allBalances, year, searchTerm]);

  const openEditModal = (bal: LeaveBalance) => {
    setEditingBalance(bal);
    setEditOpening(String(bal.opening));
    setEditAccrued(String(bal.accrued));
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingBalance) return;
    setSavingEdit(true);
    try {
      await onAdjustBalance(
        editingBalance,
        Number(editOpening) || 0,
        Number(editAccrued) || 0
      );
      setEditingBalance(null);
    } finally {
      setSavingEdit(false);
    }
  };

  return (
    <div className="space-y-6">
      {(isAdmin || isManager) && (
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="inline-flex items-center gap-1 p-1 bg-slate-100 border border-slate-200 rounded-lg">
            <button
              type="button"
              onClick={() => setScopeTab('my')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                scopeTab === 'my'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              My Balance Ledger
            </button>
            <button
              type="button"
              onClick={() => setScopeTab('org')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                scopeTab === 'org'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {isAdmin ? 'Organization Balance Database' : 'Direct Reports Ledger'}
            </button>
          </div>

          {scopeTab === 'org' && (
            <div className="flex items-center gap-2.5">
              {isAdmin && (
                <button
                  type="button"
                  onClick={onRunMonthlyAccrual}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
                >
                  <Play className="w-3.5 h-3.5" />
                  Run Monthly Accrual
                </button>
              )}
              <button
                type="button"
                onClick={() => exportBalancesToExcel(orgBalancesFiltered, allEmployees, year)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                Export Excel
              </button>
            </div>
          )}
        </div>
      )}

      {scopeTab === 'my' ? (
        <>
          <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold text-slate-900">
                  Leave Balance Ledger ({year})
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Accounting formula: Closing = Opening + Accrued − Availed
                </p>
              </div>
              <span className="text-xs font-mono tabular-nums text-slate-500">
                {currentEmployee.designation}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70 text-xs font-medium text-slate-600">
                    <th className="py-3 px-6">Leave Category</th>
                    <th className="py-3 px-4 text-right">Opening</th>
                    <th className="py-3 px-4 text-right">Accrued</th>
                    <th className="py-3 px-4 text-right">Availed</th>
                    <th className="py-3 px-4 text-right">Pending Hold</th>
                    <th className="py-3 px-6 text-right">Closing</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 text-sm">
                  {personalRows.map((row) => (
                    <tr key={row.category.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-3 px-6">
                        <span className="font-medium text-slate-900">{row.category.name}</span>
                        <span className="text-slate-300 mx-2" aria-hidden="true">·</span>
                        <span className="text-xs font-mono text-slate-500">{row.category.code}</span>
                      </td>
                      <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-700">
                        {row.opening}
                      </td>
                      <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-700">
                        +{row.accrued}
                      </td>
                      <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-700">
                        {row.availed}
                      </td>
                      <td className="py-3 px-4 text-right font-mono tabular-nums text-amber-700">
                        {row.pending > 0 ? row.pending : '—'}
                      </td>
                      <td
                        className={`py-3 px-6 text-right font-mono tabular-nums font-semibold ${
                          row.closing < 0
                            ? 'text-red-700'
                            : row.closing === 0 && !row.category.allowNegative
                              ? 'text-slate-500'
                              : 'text-emerald-700'
                        }`}
                      >
                        {row.closing}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200">
              <h2 className="text-base font-semibold text-slate-900">My Leave Requests</h2>
            </div>

            {myRequests.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-500">
                No leave requests submitted yet. Use the Apply for Leave form above to submit a request.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50/70 text-xs font-medium text-slate-600">
                      <th className="py-3 px-6">Category</th>
                      <th className="py-3 px-4">Date Range</th>
                      <th className="py-3 px-4 text-right">Days</th>
                      <th className="py-3 px-4">Approver</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-6 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 text-sm">
                    {myRequests.map((req) => (
                      <tr key={req.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-3 px-6">
                          <div className="font-medium text-slate-900">{req.categoryName}</div>
                          <div className="text-xs text-slate-500 truncate max-w-xs" title={req.reason}>
                            {req.reason}
                          </div>
                        </td>
                        <td className="py-3 px-4 font-mono tabular-nums text-xs text-slate-700 whitespace-nowrap">
                          {formatDateRangeLabel(req.startDate, req.endDate, req.halfDay)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-900">
                          {req.workingDays}
                        </td>
                        <td className="py-3 px-4 text-xs text-slate-600">
                          <div>{req.managerEmail}</div>
                          {req.managerComment && (
                            <div className="text-slate-500 mt-0.5 truncate max-w-xs" title={req.managerComment}>
                              Note: {req.managerComment}
                            </div>
                          )}
                        </td>
                        <td className={`py-3 px-4 text-xs capitalize ${STATUS_STYLE[req.status] || 'text-slate-600'}`}>
                          {req.status}
                        </td>
                        <td className="py-3 px-6 text-right">
                          {req.status === 'pending' ? (
                            <button
                              type="button"
                              onClick={() => onCancelRequest(req.id)}
                              className="text-xs font-medium text-slate-600 hover:text-red-700 underline underline-offset-2 cursor-pointer"
                            >
                              Cancel
                            </button>
                          ) : (
                            <span className="text-xs text-slate-400">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : (
        <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                {isAdmin ? `Organization Balance Ledger (${year})` : `Direct Reports Balance Ledger (${year})`}
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                {orgBalancesFiltered.length} balance records · Opening + Accrued − Availed = Closing
              </p>
            </div>
            <div className="relative w-full sm:w-72">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search employee or category..."
                className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>
          </div>

          {orgBalancesFiltered.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500">
              No matching leave balance records found. Sync employees from Google Sheets or Excel to populate balances.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70 text-xs font-medium text-slate-600">
                    <th className="py-3 px-6">Employee</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-3 text-right">Opening</th>
                    <th className="py-3 px-3 text-right">Accrued</th>
                    <th className="py-3 px-3 text-right">Availed</th>
                    <th className="py-3 px-4 text-right">Closing</th>
                    {isAdmin && <th className="py-3 px-6 text-right">Adjust</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 text-sm">
                  {orgBalancesFiltered.map((bal) => (
                    <tr key={bal.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-2.5 px-6">
                        <div className="font-medium text-slate-900">{bal.employeeName}</div>
                        <div className="text-xs text-slate-500">{bal.employeeEmail}</div>
                      </td>
                      <td className="py-2.5 px-4 text-slate-700">{bal.categoryName}</td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-700">
                        {bal.opening}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-700">
                        {bal.accrued}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-700">
                        {bal.availed}
                      </td>
                      <td
                        className={`py-2.5 px-4 text-right font-mono tabular-nums font-semibold ${
                          bal.closing < 0 ? 'text-red-700' : 'text-emerald-700'
                        }`}
                      >
                        {bal.closing}
                      </td>
                      {isAdmin && (
                        <td className="py-2.5 px-6 text-right">
                          <button
                            type="button"
                            onClick={() => openEditModal(bal)}
                            className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-900 cursor-pointer"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                            Edit
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {editingBalance && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4"
          role="dialog"
          aria-modal="true"
        >
          <form
            onSubmit={handleSaveEdit}
            className="bg-white border border-slate-200 rounded-xl max-w-md w-full p-6 space-y-5 shadow-xl"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-base font-semibold text-slate-900">Adjust Leave Balance</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {editingBalance.employeeName} · {editingBalance.categoryName} ({editingBalance.year})
                </p>
              </div>
              <button
                type="button"
                onClick={() => setEditingBalance(null)}
                className="text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  Opening Balance
                </label>
                <input
                  type="number"
                  step="0.5"
                  value={editOpening}
                  onChange={(e) => setEditOpening(e.target.value)}
                  className="w-full px-3 py-2 text-sm font-mono tabular-nums border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  Accrued Balance
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  value={editAccrued}
                  onChange={(e) => setEditAccrued(e.target.value)}
                  className="w-full px-3 py-2 text-sm font-mono tabular-nums border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 flex items-center justify-between text-xs">
              <span className="text-slate-600">
                Availed: <strong className="font-mono tabular-nums">{editingBalance.availed}</strong>
              </span>
              <span className="text-slate-900 font-medium">
                New Closing:{' '}
                <strong className="font-mono tabular-nums">
                  {roundDays((Number(editOpening) || 0) + (Number(editAccrued) || 0) - editingBalance.availed)}
                </strong>
              </span>
            </div>

            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setEditingBalance(null)}
                className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingEdit}
                className="px-4 py-2 text-sm font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 cursor-pointer disabled:opacity-60"
              >
                {savingEdit ? 'Saving...' : 'Save Adjustment'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
