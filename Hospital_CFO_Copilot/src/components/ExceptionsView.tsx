import React, { useState, useMemo } from 'react';
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Clock,
  Download,
  Search,
  ShieldAlert,
  ShieldCheck,
  X,
} from 'lucide-react';
import { Encounter, ExceptionStatus, FinancialException, UserRole } from '../types';
import { exportDatasetToCSV } from '../utils/fileImport';
import { formatIndianDate, formatINR } from '../utils/formatters';

interface ExceptionsViewProps {
  exceptions: FinancialException[];
  encounters: Encounter[];
  userRole: UserRole;
  selectedException: FinancialException | null;
  onSelectException: (exc: FinancialException | null) => void;
  onSelectEncounter: (encounterId: string) => void;
  onUpdateException: (
    exceptionId: string,
    updates: {
      status: ExceptionStatus;
      assignedTo: string;
      resolution: string;
    }
  ) => void;
}

export const ExceptionsView: React.FC<ExceptionsViewProps> = ({
  exceptions,
  encounters,
  userRole,
  selectedException,
  onSelectException,
  onSelectEncounter,
  onUpdateException,
}) => {
  // Filters
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('OPEN_OR_REVIEW');
  const [filterControl, setFilterControl] = useState<string>('ALL');
  const [filterDept, setFilterDept] = useState<string>('ALL');
  const [filterRevCenter, setFilterRevCenter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Multi-select batch action state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchActionFeedback, setBatchActionFeedback] = useState<string | null>(null);

  // Encounter Map for quick lookups
  const encounterMap = new Map<string, Encounter>();
  encounters.forEach((e) => encounterMap.set(e.Encounter_ID, e));

  // Dropdown options
  const revCentres = Array.from(new Set(exceptions.map((e) => e.Revenue_Centre))).sort();
  const departments = Array.from(
    new Set(encounters.map((e) => e.Department).filter(Boolean))
  ).sort();

  // Filter evaluation
  const filteredExceptions = exceptions.filter((exc) => {
    const enc = encounterMap.get(exc.Encounter_ID);

    if (filterSeverity !== 'ALL' && exc.Severity !== filterSeverity) return false;

    if (filterStatus === 'OPEN_OR_REVIEW') {
      if (exc.Status !== 'OPEN' && exc.Status !== 'UNDER_REVIEW') return false;
    } else if (filterStatus !== 'ALL' && exc.Status !== filterStatus) {
      return false;
    }

    if (filterControl !== 'ALL' && exc.Control_ID !== filterControl) return false;
    if (filterRevCenter !== 'ALL' && exc.Revenue_Centre !== filterRevCenter) return false;
    if (filterDept !== 'ALL' && enc?.Department !== filterDept) return false;

    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      const match =
        exc.Exception_ID.toLowerCase().includes(q) ||
        exc.Encounter_ID.toLowerCase().includes(q) ||
        exc.Description.toLowerCase().includes(q) ||
        exc.Revenue_Centre.toLowerCase().includes(q) ||
        (exc.Assigned_To && exc.Assigned_To.toLowerCase().includes(q));
      if (!match) return false;
    }

    return true;
  });

  const totalExposureFiltered = filteredExceptions.reduce(
    (sum, e) => sum + e.Exposure_Amount,
    0
  );

  // Batch action exposure calculation
  const selectedExceptionsList = useMemo(() => {
    return exceptions.filter((e) => selectedIds.has(e.Exception_ID));
  }, [exceptions, selectedIds]);

  const selectedTotalExposure = useMemo(() => {
    return selectedExceptionsList.reduce((sum, e) => sum + e.Exposure_Amount, 0);
  }, [selectedExceptionsList]);

  const handleToggleSelectAll = () => {
    if (filteredExceptions.length === 0) return;
    const allSelected = filteredExceptions.every((e) => selectedIds.has(e.Exception_ID));
    const next = new Set(selectedIds);
    if (allSelected) {
      filteredExceptions.forEach((e) => next.delete(e.Exception_ID));
    } else {
      filteredExceptions.forEach((e) => next.add(e.Exception_ID));
    }
    setSelectedIds(next);
  };

  const handleToggleOne = (id: string, e?: React.SyntheticEvent) => {
    e?.stopPropagation();
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  const handleBatchUpdateStatus = (
    newStatus: ExceptionStatus,
    resolutionNote: string,
    assignedToNote?: string
  ) => {
    if (selectedIds.size === 0) return;
    const count = selectedIds.size;
    selectedIds.forEach((id) => {
      const existing = exceptions.find((e) => e.Exception_ID === id);
      onUpdateException(id, {
        status: newStatus,
        assignedTo: assignedToNote || existing?.Assigned_To || `${userRole} Desk`,
        resolution: resolutionNote,
      });
    });
    setSelectedIds(new Set());
    setBatchActionFeedback(`Successfully updated ${count} exceptions to ${newStatus}.`);
    setTimeout(() => setBatchActionFeedback(null), 4000);
  };

  // Modal edit state for active selected exception
  const [editStatus, setEditStatus] = useState<ExceptionStatus>('OPEN');
  const [editAssignedTo, setEditAssignedTo] = useState('');
  const [editResolution, setEditResolution] = useState('');

  const openModal = (exc: FinancialException) => {
    onSelectException(exc);
    setEditStatus(exc.Status);
    setEditAssignedTo(exc.Assigned_To || '');
    setEditResolution(exc.Resolution || '');
  };

  const handleSaveModal = () => {
    if (!selectedException) return;
    onUpdateException(selectedException.Exception_ID, {
      status: editStatus,
      assignedTo: editAssignedTo,
      resolution: editResolution,
    });
    onSelectException(null);
  };

  const handleExportCSV = () => {
    exportDatasetToCSV(filteredExceptions, `Financial_Exceptions_Export_${Date.now()}`);
  };

  return (
    <div className="space-y-4">
      {/* Control Banner & Summary KPI */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-amber-600" />
              Financial Exceptions Lifecycle &amp; Resolution Desk
            </h2>
            <p className="text-xs text-slate-500">
              Deterministic exceptions flagged by controls C01 through C08. Active role:{' '}
              <strong className="text-teal-700">{userRole}</strong>.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleExportCSV}
              className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 transition shadow-2xs cursor-pointer"
              title="Export filtered exceptions to CSV"
            >
              <Download className="h-3.5 w-3.5 text-slate-500" />
              <span>Export CSV</span>
            </button>
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-1.5 text-xs shadow-2xs">
              <span className="text-amber-900 font-medium">Filtered Potential Financial Impact: </span>
              <span className="text-amber-900 font-bold">
                {formatINR(totalExposureFiltered)}
              </span>
            </div>
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="mt-3 grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-6">
          {/* Search */}
          <div className="col-span-2 sm:col-span-1 lg:col-span-2 relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search exception ID, encounter, text..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:border-teal-600 focus:outline-none"
            />
          </div>

          {/* Severity Filter */}
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-800 focus:border-teal-600 focus:outline-none cursor-pointer"
          >
            <option value="ALL">Severity: All</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>

          {/* Status Filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-800 focus:border-teal-600 focus:outline-none cursor-pointer"
          >
            <option value="OPEN_OR_REVIEW">Open &amp; Under Review</option>
            <option value="ALL">Status: All Statuses</option>
            <option value="OPEN">OPEN Only</option>
            <option value="UNDER_REVIEW">UNDER_REVIEW</option>
            <option value="RESOLVED">RESOLVED</option>
            <option value="ACCEPTED">ACCEPTED</option>
          </select>

          {/* Control Filter */}
          <select
            value={filterControl}
            onChange={(e) => setFilterControl(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-800 focus:border-teal-600 focus:outline-none cursor-pointer"
          >
            <option value="ALL">Control: All C01-C08</option>
            <option value="C01">C01 Unbilled Service</option>
            <option value="C02">C02 Quantity Mismatch</option>
            <option value="C03">C03 Amount Mismatch</option>
            <option value="C04">C04 Post-Billing Service</option>
            <option value="C05">C05 Missing Final Bill</option>
            <option value="C06">C06 TPA Shortfall</option>
            <option value="C07">C07 Overdue Receivable</option>
            <option value="C08">C08 Unusual Discount</option>
          </select>

          {/* Department Filter */}
          <select
            value={filterDept}
            onChange={(e) => setFilterDept(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-800 focus:border-teal-600 focus:outline-none cursor-pointer"
          >
            <option value="ALL">Dept: All</option>
            {departments.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Batch Feedback Banner */}
      {batchActionFeedback && (
        <div className="flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-xs font-semibold text-emerald-800 shadow-2xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span>{batchActionFeedback}</span>
          </div>
          <button
            onClick={() => setBatchActionFeedback(null)}
            className="text-emerald-700 hover:text-emerald-900 font-bold cursor-pointer"
          >
            &times;
          </button>
        </div>
      )}

      {/* Batch Action Toolbar */}
      {selectedIds.size > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-teal-300 bg-teal-50/90 px-4 py-3 shadow-xs animate-in fade-in slide-in-from-top-1 text-slate-800">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-6 items-center justify-center rounded-full bg-teal-700 px-2.5 text-xs font-bold text-white">
              {selectedIds.size}
            </span>
            <div className="text-xs">
              <span className="font-bold text-teal-950">Exceptions Selected</span>
              <span className="mx-1.5 text-teal-400">&bull;</span>
              <span className="text-slate-600">Combined Exposure: </span>
              <strong className="text-amber-900">{formatINR(selectedTotalExposure)}</strong>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => handleBatchUpdateStatus('UNDER_REVIEW', 'Batch marked Under Review by user')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-sky-300 bg-sky-100 hover:bg-sky-200 px-2.5 py-1.5 text-xs font-semibold text-sky-900 shadow-2xs transition cursor-pointer"
              title="Mark all selected exceptions as Under Review"
            >
              <Clock className="h-3.5 w-3.5" />
              <span>Mark as Reviewed</span>
            </button>

            <button
              onClick={() => handleBatchUpdateStatus('OPEN', 'Batch disputed by department/finance', 'Disputed')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-rose-100 hover:bg-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-900 shadow-2xs transition cursor-pointer"
              title="Mark selected exceptions as Disputed"
            >
              <AlertTriangle className="h-3.5 w-3.5" />
              <span>Dispute Selected</span>
            </button>

            <button
              onClick={() => handleBatchUpdateStatus('RESOLVED', 'Batch resolved and reconciled with patient ledger')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-300 bg-emerald-100 hover:bg-emerald-200 px-2.5 py-1.5 text-xs font-semibold text-emerald-900 shadow-2xs transition cursor-pointer"
              title="Mark all selected exceptions as Resolved"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Resolve Selected</span>
            </button>

            {(userRole === 'CFO' || userRole === 'Finance/Billing Manager') && (
              <button
                onClick={() => handleBatchUpdateStatus('ACCEPTED', 'Batch risk formally accepted by CFO')}
                className="inline-flex items-center gap-1.5 rounded-lg border border-purple-300 bg-purple-100 hover:bg-purple-200 px-2.5 py-1.5 text-xs font-semibold text-purple-900 shadow-2xs transition cursor-pointer"
                title="Formally accept risk for selected exceptions"
              >
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Accept Risk (CFO)</span>
              </button>
            )}

            <button
              onClick={() => setSelectedIds(new Set())}
              className="rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-500 hover:bg-teal-100 hover:text-slate-800 transition cursor-pointer"
            >
              Deselect All
            </button>
          </div>
        </div>
      )}

      {/* Exceptions Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-3 px-3 w-10 text-center">
                  <input
                    type="checkbox"
                    checked={filteredExceptions.length > 0 && filteredExceptions.every((e) => selectedIds.has(e.Exception_ID))}
                    ref={(el) => {
                      if (el) {
                        const someSelected = filteredExceptions.some((e) => selectedIds.has(e.Exception_ID));
                        const allSelected = filteredExceptions.length > 0 && filteredExceptions.every((e) => selectedIds.has(e.Exception_ID));
                        el.indeterminate = someSelected && !allSelected;
                      }
                    }}
                    onChange={handleToggleSelectAll}
                    className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500 cursor-pointer"
                    title="Select All Filtered Exceptions"
                  />
                </th>
                <th className="py-3 px-3 font-semibold">Severity</th>
                <th className="py-3 px-3 font-semibold">Exception ID</th>
                <th className="py-3 px-3 font-semibold">Encounter</th>
                <th className="py-3 px-3 font-semibold">Control</th>
                <th className="py-3 px-3 font-semibold">Revenue Centre</th>
                <th className="py-3 px-3 font-semibold">Description</th>
                <th className="py-3 px-3 font-semibold text-right">Potential Exposure</th>
                <th className="py-3 px-3 font-semibold text-center">Status</th>
                <th className="py-3 px-3 font-semibold">Assigned Owner</th>
                <th className="py-3 px-3 font-semibold text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-sans">
              {filteredExceptions.length === 0 ? (
                <tr>
                  <td colSpan={11} className="py-12 text-center text-xs text-slate-400">
                    <CheckCircle2 className="mx-auto h-6 w-6 text-emerald-600 mb-1" />
                    No exceptions matched the selected filter criteria.
                  </td>
                </tr>
              ) : (
                filteredExceptions.map((exc, idx) => {
                  const isCrit = exc.Severity === 'CRITICAL';
                  const isHigh = exc.Severity === 'HIGH';
                  const isSelected = selectedIds.has(exc.Exception_ID);

                  return (
                    <tr
                      key={`${exc.Exception_ID}-${idx}`}
                      onClick={() => openModal(exc)}
                      className={`hover:bg-slate-50 transition cursor-pointer ${
                        isSelected ? 'bg-teal-50/70' : ''
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-2.5 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => handleToggleOne(exc.Exception_ID, e)}
                          className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500 cursor-pointer"
                        />
                      </td>

                      {/* Severity */}
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-flex rounded px-2 py-0.5 text-[10px] font-bold ${
                            isCrit
                              ? 'bg-rose-50 text-rose-700 border border-rose-200'
                              : isHigh
                              ? 'bg-amber-50 text-amber-800 border border-amber-200'
                              : 'bg-slate-100 text-slate-700 border border-slate-200'
                          }`}
                        >
                          {exc.Severity}
                        </span>
                      </td>

                      {/* Exception ID */}
                      <td className="py-2.5 px-3 font-mono font-bold text-teal-800">
                        {exc.Exception_ID}
                      </td>

                      {/* Encounter */}
                      <td className="py-2.5 px-3 font-mono font-semibold">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectEncounter(exc.Encounter_ID);
                          }}
                          className="text-slate-900 hover:text-teal-700 hover:underline cursor-pointer"
                        >
                          {exc.Encounter_ID}
                        </button>
                      </td>

                      {/* Control */}
                      <td className="py-2.5 px-3 font-mono">
                        <span className="bg-slate-100 px-1.5 py-0.5 rounded text-[10px] text-slate-700 border border-slate-200">
                          {exc.Control_ID}
                        </span>
                      </td>

                      {/* Revenue Centre */}
                      <td className="py-2.5 px-3 font-medium text-slate-800">
                        {exc.Revenue_Centre}
                      </td>

                      {/* Description */}
                      <td
                        className="py-2.5 px-3 text-slate-600 max-w-xs truncate"
                        title={exc.Description}
                      >
                        {exc.Description}
                      </td>

                      {/* Exposure */}
                      <td className="py-2.5 px-3 text-right font-semibold text-amber-900">
                        {formatINR(exc.Exposure_Amount)}
                      </td>

                      {/* Status */}
                      <td className="py-2.5 px-3 text-center">
                        <span
                          className={`inline-flex rounded px-2 py-0.5 text-[10px] font-bold ${
                            exc.Status === 'RESOLVED'
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                              : exc.Status === 'UNDER_REVIEW'
                              ? 'bg-sky-50 text-sky-800 border border-sky-200'
                              : exc.Status === 'ACCEPTED'
                              ? 'bg-purple-50 text-purple-800 border border-purple-200'
                              : 'bg-rose-50 text-rose-700 border border-rose-200'
                          }`}
                        >
                          {exc.Status}
                        </span>
                      </td>

                      {/* Assigned To */}
                      <td className="py-2.5 px-3 text-slate-700 font-medium text-[11px]">
                        {exc.Assigned_To || <span className="text-slate-400 italic">Unassigned</span>}
                      </td>

                      {/* Action */}
                      <td className="py-2.5 px-3 text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            openModal(exc);
                          }}
                          className="rounded bg-slate-100 hover:bg-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-800 border border-slate-200 transition cursor-pointer"
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Exception Resolution Detail Modal */}
      {selectedException && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl text-slate-800 space-y-4">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <span
                  className={`rounded px-2 py-0.5 text-xs font-bold ${
                    selectedException.Severity === 'CRITICAL'
                      ? 'bg-rose-50 text-rose-700 border border-rose-200'
                      : selectedException.Severity === 'HIGH'
                      ? 'bg-amber-50 text-amber-800 border border-amber-200'
                      : 'bg-slate-100 text-slate-700 border border-slate-200'
                  }`}
                >
                  {selectedException.Severity}
                </span>
                <h3 className="text-base font-bold text-slate-900 font-mono">
                  {selectedException.Exception_ID} &bull; {selectedException.Control_ID}
                </h3>
              </div>
              <button
                onClick={() => onSelectException(null)}
                className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="space-y-4 text-xs">
              <div className="rounded-lg bg-slate-50 p-3.5 border border-slate-200 space-y-2">
                <div className="flex justify-between items-center text-slate-600">
                  <span>Encounter ID:</span>
                  <button
                    onClick={() => {
                      onSelectEncounter(selectedException.Encounter_ID);
                      onSelectException(null);
                    }}
                    className="font-mono font-bold text-teal-800 hover:underline cursor-pointer"
                  >
                    {selectedException.Encounter_ID} &rarr; View Financials
                  </button>
                </div>
                <div className="flex justify-between items-center text-slate-600">
                  <span>Revenue Centre:</span>
                  <span className="font-semibold text-slate-900">{selectedException.Revenue_Centre}</span>
                </div>
                <div className="flex justify-between items-center text-slate-600">
                  <span>Potential Financial Exposure:</span>
                  <span className="font-semibold text-sm text-amber-900">
                    {formatINR(selectedException.Exposure_Amount)}
                  </span>
                </div>
                <div className="pt-2 border-t border-slate-200">
                  <div className="text-slate-600 font-medium mb-1">Exception Details:</div>
                  <p className="text-slate-800 leading-relaxed bg-white p-2.5 rounded border border-slate-200">
                    {selectedException.Description}
                  </p>
                </div>
              </div>

              {/* Status & Assignment Inputs */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="text-[11px] uppercase font-bold text-slate-600">
                    Resolution Status
                  </label>
                  <select
                    value={editStatus}
                    onChange={(e) => setEditStatus(e.target.value as ExceptionStatus)}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 focus:outline-none focus:border-teal-600"
                  >
                    <option value="OPEN">OPEN — Action required</option>
                    <option value="UNDER_REVIEW">UNDER_REVIEW — Investigating discrepancy</option>
                    <option value="RESOLVED">RESOLVED — Reconciled and bill adjusted</option>
                    <option value="ACCEPTED">ACCEPTED — Risk approved by CFO</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] uppercase font-bold text-slate-600">
                    Assigned Owner
                  </label>
                  <input
                    type="text"
                    value={editAssignedTo}
                    onChange={(e) => setEditAssignedTo(e.target.value)}
                    placeholder="e.g. Billing Lead / Duty Manager"
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-teal-600"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] uppercase font-bold text-slate-600">
                  Resolution Rationale &amp; Audit Notes
                </label>
                <textarea
                  rows={3}
                  value={editResolution}
                  onChange={(e) => setEditResolution(e.target.value)}
                  placeholder="Record formal justification: tariff verified against insurance schedule, supplementary bill issued, or pharmacy dispensation voided."
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 focus:outline-none focus:border-teal-600 resize-none"
                />
              </div>

              <div className="text-[10px] text-slate-500 flex justify-between">
                <span>Run ID: {selectedException.Run_ID}</span>
                <span>Flagged Date: {formatIndianDate(selectedException.Created_Date)}</span>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => onSelectException(null)}
                className="rounded-lg px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveModal}
                className="rounded-lg bg-teal-700 hover:bg-teal-800 px-4 py-2 text-xs font-semibold text-white shadow-xs transition cursor-pointer"
              >
                Save Resolution Audit Entry
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
