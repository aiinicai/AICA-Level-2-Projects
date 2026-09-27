import React, { useMemo, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Building2,
  CheckCircle2,
  Clock,
  ExternalLink,
  Eye,
  FileCheck2,
  FileText,
  Filter,
  HelpCircle,
  Lock,
  MessageSquare,
  RefreshCw,
  Search,
  ShieldAlert,
  XCircle,
} from 'lucide-react';
import { ALL_HOSPITAL_DEPARTMENTS, DepartmentClearanceSummary } from '../engine/clearanceEngine';
import {
  DepartmentClearanceRecord,
  DepartmentClearanceStatus,
  Encounter,
  HospitalDepartment,
  UserRole,
  UserSession,
} from '../types';
import { formatINR } from '../utils/formatters';

import { EmptyWorkspaceState } from './EmptyWorkspaceState';

interface DepartmentClearanceViewProps {
  records: DepartmentClearanceRecord[];
  summary: DepartmentClearanceSummary;
  encounters: Encounter[];
  currentUser: UserSession;
  onUpdateClearanceRecord: (
    recordId: string,
    updates: {
      status: DepartmentClearanceStatus;
      comment?: string;
      evidenceRef?: string;
    }
  ) => void;
  onSelectEncounter: (encounterId: string) => void;
  onNavigateToTab?: (tab: string) => void;
}

export const DepartmentClearanceView: React.FC<DepartmentClearanceViewProps> = ({
  records,
  summary,
  encounters,
  currentUser,
  onUpdateClearanceRecord,
  onSelectEncounter,
  onNavigateToTab,
}) => {
  // Sub-tabs: 'workbench' | 'matrix' | 'cfo-summary'
  const [activeTab, setActiveTab] = useState<'workbench' | 'matrix' | 'cfo-summary'>('workbench');

  // Filter states
  const isDeptManager = currentUser.role === 'Department Manager';
  const initialDeptFilter = isDeptManager && currentUser.department ? currentUser.department : 'ALL';
  const [selectedDept, setSelectedDept] = useState<string>(initialDeptFilter);
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Multi-select batch action state
  const [selectedRecordIds, setSelectedRecordIds] = useState<Set<string>>(new Set());
  const [batchFeedback, setBatchFeedback] = useState<string | null>(null);

  // Review modal state
  const [reviewingRecord, setReviewingRecord] = useState<DepartmentClearanceRecord | null>(null);
  const [formStatus, setFormStatus] = useState<DepartmentClearanceStatus>('VERIFIED');
  const [formComment, setFormComment] = useState('');
  const [formEvidence, setFormEvidence] = useState('');

  const handleToggleSelectAll = () => {
    if (filteredRecords.length === 0) return;
    const allSelected = filteredRecords.every((r) => selectedRecordIds.has(r.id));
    const next = new Set(selectedRecordIds);
    if (allSelected) {
      filteredRecords.forEach((r) => next.delete(r.id));
    } else {
      filteredRecords.forEach((r) => next.add(r.id));
    }
    setSelectedRecordIds(next);
  };

  const handleToggleOne = (id: string, e?: React.SyntheticEvent) => {
    e?.stopPropagation();
    const next = new Set(selectedRecordIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedRecordIds(next);
  };

  const handleBatchUpdateClearance = (newStatus: DepartmentClearanceStatus, comment: string) => {
    if (selectedRecordIds.size === 0) return;
    const count = selectedRecordIds.size;
    selectedRecordIds.forEach((id) => {
      onUpdateClearanceRecord(id, {
        status: newStatus,
        comment,
      });
    });
    setSelectedRecordIds(new Set());
    setBatchFeedback(`Successfully updated ${count} records to ${newStatus.replace(/_/g, ' ')}.`);
    setTimeout(() => setBatchFeedback(null), 4000);
  };

  // If user is Department Manager, lock department selection to their assigned department
  const effectiveDeptFilter = isDeptManager && currentUser.department ? currentUser.department : selectedDept;

  const deptRecords = useMemo(() => {
    if (isDeptManager && currentUser.department) {
      return records.filter((r) => r.department === currentUser.department);
    }
    return records;
  }, [records, isDeptManager, currentUser.department]);

  // Deduplicate encounters for cross-department clearance matrix
  const uniqueEncounters = useMemo(() => {
    const seen = new Set<string>();
    return encounters.filter((e) => {
      if (!e.Encounter_ID || seen.has(e.Encounter_ID)) return false;
      seen.add(e.Encounter_ID);
      return true;
    });
  }, [encounters]);

  const activeSummary = useMemo(() => {
    if (!isDeptManager || !currentUser.department) return summary;
    const total = deptRecords.length;
    const verified = deptRecords.filter((r) => r.status === 'VERIFIED').length;
    const pending = deptRecords.filter((r) => r.status === 'PENDING_VERIFICATION').length;
    const disputed = deptRecords.filter((r) => r.status === 'DISPUTED').length;
    const correction = deptRecords.filter((r) => r.status === 'CORRECTION_REQUIRED').length;
    const rate = total > 0 ? Number(((verified / total) * 100).toFixed(1)) : 100;
    const pendingExp = deptRecords
      .filter((r) => r.status === 'PENDING_VERIFICATION' || r.status === 'DISPUTED')
      .reduce((sum, r) => sum + r.unbilledExposure + r.varianceExposure, 0);

    return {
      ...summary,
      totalCount: total,
      verifiedCount: verified,
      pendingCount: pending,
      disputedCount: disputed,
      correctionRequiredCount: correction,
      clearancePercent: rate,
      exposureAwaitingVerification: pendingExp,
    };
  }, [isDeptManager, currentUser.department, deptRecords, summary]);

  const filteredRecords = useMemo(() => {
    return records.filter((r) => {
      if (effectiveDeptFilter !== 'ALL' && r.department !== effectiveDeptFilter) return false;
      if (selectedStatus !== 'ALL' && r.status !== selectedStatus) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchEnc = r.encounterId.toLowerCase().includes(q);
        const matchDept = r.department.toLowerCase().includes(q);
        const matchRev = r.revenueCentre.toLowerCase().includes(q);
        const matchComment = r.comment?.toLowerCase().includes(q);
        if (!matchEnc && !matchDept && !matchRev && !matchComment) return false;
      }
      return true;
    });
  }, [records, effectiveDeptFilter, selectedStatus, searchQuery]);

  const openReviewModal = (record: DepartmentClearanceRecord) => {
    setReviewingRecord(record);
    setFormStatus(record.status === 'PENDING_VERIFICATION' ? 'VERIFIED' : record.status);
    setFormComment(record.comment || '');
    setFormEvidence(record.evidenceRef || '');
  };

  const handleSaveReview = () => {
    if (!reviewingRecord) return;
    onUpdateClearanceRecord(reviewingRecord.id, {
      status: formStatus,
      comment: formComment,
      evidenceRef: formEvidence,
    });
    setReviewingRecord(null);
  };

  if (records.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            Departmental Billing Review
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Departments review whether services and charges attributable to them have been captured and billed correctly.
          </p>
        </div>
        <EmptyWorkspaceState
          title="No departmental financial review data available."
          description="Departmental review items are generated from clinical services, encounters, and billing data. Upload your hospital financial extracts to begin departmental charge attribution and billing review."
          badge="Clearance Inactive"
          actionText="Upload Hospital Financial Extracts"
          onAction={() => onNavigateToTab?.('data-intelligence')}
          suggestedDatasets={[
            'Clinical Services & Charge Orders (Service_Code, Revenue_Centre)',
            'Inpatient Encounters (Admission, Discharge, UHID)',
            'Billing Register (Invoice_ID, Billed_Amount)',
          ]}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner & Mode Switcher */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Departmental Billing Review
              </h1>
              <span className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-bold tracking-wider text-teal-800 border border-teal-200 uppercase">
                Charge Attribution Review
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Departments review whether services and charges attributable to them have been captured and billed correctly.
              <span className="text-teal-700 font-semibold ml-1">
                (Financial verification; identifies items requiring review)
              </span>
            </p>
          </div>

          {/* Sub-tab navigation */}
          {!isDeptManager ? (
            <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs font-semibold">
              <button
                onClick={() => setActiveTab('workbench')}
                className={`rounded-md px-3 py-1.5 transition cursor-pointer ${
                  activeTab === 'workbench'
                    ? 'bg-white text-teal-800 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Review Workbench
              </button>
              <button
                onClick={() => setActiveTab('matrix')}
                className={`rounded-md px-3 py-1.5 transition cursor-pointer ${
                  activeTab === 'matrix'
                    ? 'bg-white text-teal-800 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Review Matrix
              </button>
              <button
                onClick={() => setActiveTab('cfo-summary')}
                className={`rounded-md px-3 py-1.5 transition cursor-pointer ${
                  activeTab === 'cfo-summary'
                    ? 'bg-white text-teal-800 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                CFO Departmental Summary
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 rounded-lg border border-teal-200 bg-teal-50 px-3 py-1.5 text-xs font-bold text-teal-900">
              <Building2 className="h-3.5 w-3.5 text-teal-700" />
              <span>{currentUser.department} Billing Review Desk</span>
            </div>
          )}
        </div>

        {/* Quick KPI Strip */}
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 pt-4 border-t border-slate-100 text-xs">
          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Review Completion</div>
            <div className="text-base font-bold text-teal-700">{activeSummary.clearancePercent}%</div>
          </div>
          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Verified</div>
            <div className="text-base font-bold text-emerald-700">{activeSummary.verifiedCount} items</div>
          </div>
          <div className="bg-slate-50 p-2.5 rounded-lg border border-amber-200 bg-amber-50/30">
            <div className="text-[10px] uppercase font-bold text-amber-800">Pending Review</div>
            <div className="text-base font-bold text-amber-900">{activeSummary.pendingCount} items</div>
          </div>
          <div className="bg-slate-50 p-2.5 rounded-lg border border-red-200 bg-red-50/30">
            <div className="text-[10px] uppercase font-bold text-red-800">Disputed</div>
            <div className="text-base font-bold text-red-700">{activeSummary.disputedCount} items</div>
          </div>
          <div className="bg-slate-50 p-2.5 rounded-lg border border-orange-200 bg-orange-50/30">
            <div className="text-[10px] uppercase font-bold text-orange-800">Correction Req.</div>
            <div className="text-base font-bold text-orange-700">{activeSummary.correctionRequiredCount} items</div>
          </div>
          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Pending Exposure</div>
            <div className="text-base font-bold text-amber-900">
              {formatINR(activeSummary.exposureAwaitingVerification)}
            </div>
          </div>
        </div>
      </div>

      {/* SUB-VIEW 1: DEPARTMENT WORKBENCH */}
      {activeTab === 'workbench' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          {/* Filters Bar */}
          <div className="p-4 border-b border-slate-200 bg-slate-50/60 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3">
              {/* Department Filter */}
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                <Building2 className="h-4 w-4 text-slate-400" />
                <span>Department:</span>
                {isDeptManager ? (
                  <span className="rounded bg-teal-100 px-2 py-0.5 text-teal-900 font-bold">
                    {currentUser.department} (Locked)
                  </span>
                ) : (
                  <select
                    value={selectedDept}
                    onChange={(e) => setSelectedDept(e.target.value)}
                    className="border border-slate-300 rounded-md px-2 py-1 text-xs bg-white text-slate-900 font-normal focus:outline-teal-600"
                  >
                    <option value="ALL">All Departments (8)</option>
                    {ALL_HOSPITAL_DEPARTMENTS.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Status Filter */}
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                <Filter className="h-4 w-4 text-slate-400" />
                <span>Status:</span>
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className="border border-slate-300 rounded-md px-2 py-1 text-xs bg-white text-slate-900 font-normal focus:outline-teal-600"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="PENDING_VERIFICATION">Pending Verification</option>
                  <option value="VERIFIED">Verified</option>
                  <option value="DISPUTED">Disputed</option>
                  <option value="CORRECTION_REQUIRED">Correction Required</option>
                  <option value="UNABLE_TO_VERIFY">Unable to Verify</option>
                </select>
              </div>
            </div>

            {/* Search */}
            <div className="relative w-full sm:w-64">
              <Search className="h-3.5 w-3.5 absolute left-2.5 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search encounter, notes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 border border-slate-300 rounded-md text-xs focus:ring-1 focus:ring-teal-600"
              />
            </div>
          </div>

          {/* Batch Feedback Banner */}
          {batchFeedback && (
            <div className="mx-4 mb-2 flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-xs font-semibold text-emerald-800 shadow-2xs">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <span>{batchFeedback}</span>
              </div>
              <button
                onClick={() => setBatchFeedback(null)}
                className="text-emerald-700 hover:text-emerald-900 font-bold cursor-pointer"
              >
                &times;
              </button>
            </div>
          )}

          {/* Batch Action Toolbar */}
          {selectedRecordIds.size > 0 && (
            <div className="mx-4 mb-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-teal-300 bg-teal-50/90 px-4 py-2.5 shadow-xs animate-in fade-in slide-in-from-top-1 text-slate-800">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-6 items-center justify-center rounded-full bg-teal-700 px-2.5 text-xs font-bold text-white">
                  {selectedRecordIds.size}
                </span>
                <span className="text-xs font-bold text-teal-950">Clearance Records Selected</span>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={() => handleBatchUpdateClearance('VERIFIED', 'Batch verified by department/finance')}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-300 bg-emerald-100 hover:bg-emerald-200 px-2.5 py-1 text-xs font-semibold text-emerald-900 shadow-2xs transition cursor-pointer"
                  title="Verify all selected clearance lines"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Verify Selected</span>
                </button>

                <button
                  onClick={() => handleBatchUpdateClearance('DISPUTED', 'Batch disputed - service not performed')}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-rose-100 hover:bg-rose-200 px-2.5 py-1 text-xs font-semibold text-rose-900 shadow-2xs transition cursor-pointer"
                  title="Dispute all selected clearance lines"
                >
                  <AlertTriangle className="h-3.5 w-3.5" />
                  <span>Dispute Selected</span>
                </button>

                <button
                  onClick={() => handleBatchUpdateClearance('CORRECTION_REQUIRED', 'Batch flagged: correction required by nursing/clinical team')}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-orange-300 bg-orange-100 hover:bg-orange-200 px-2.5 py-1 text-xs font-semibold text-orange-900 shadow-2xs transition cursor-pointer"
                  title="Request correction on selected lines"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  <span>Request Correction</span>
                </button>

                <button
                  onClick={() => setSelectedRecordIds(new Set())}
                  className="rounded-lg px-2 py-1 text-xs font-medium text-slate-500 hover:bg-teal-100 hover:text-slate-800 transition cursor-pointer"
                >
                  Deselect All
                </button>
              </div>
            </div>
          )}

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-3 w-10 text-center">
                    <input
                      type="checkbox"
                      checked={filteredRecords.length > 0 && filteredRecords.every((r) => selectedRecordIds.has(r.id))}
                      ref={(el) => {
                        if (el) {
                          const someSelected = filteredRecords.some((r) => selectedRecordIds.has(r.id));
                          const allSelected = filteredRecords.length > 0 && filteredRecords.every((r) => selectedRecordIds.has(r.id));
                          el.indeterminate = someSelected && !allSelected;
                        }
                      }}
                      onChange={handleToggleSelectAll}
                      className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500 cursor-pointer"
                      title="Select All Filtered Clearance Records"
                    />
                  </th>
                  <th className="py-2.5 px-3">Encounter</th>
                  <th className="py-2.5 px-3">Department</th>
                  <th className="py-2.5 px-3">Revenue Centre</th>
                  <th className="py-2.5 px-3 text-right">Service Value</th>
                  <th className="py-2.5 px-3 text-right">Billed Amount</th>
                  <th className="py-2.5 px-3 text-right">Exposure</th>
                  <th className="py-2.5 px-3">Exceptions</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Reviewer Notes</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {filteredRecords.length === 0 ? (
                  <tr>
                    <td colSpan={11} className="py-8 text-center text-xs text-slate-500">
                      No clearance records matching current filter criteria.
                    </td>
                  </tr>
                ) : (
                  filteredRecords.map((r) => {
                    const isSelected = selectedRecordIds.has(r.id);
                    return (
                      <tr
                        key={r.id}
                        className={`hover:bg-slate-50/80 transition ${
                          isSelected ? 'bg-teal-50/70' : ''
                        }`}
                      >
                        {/* Checkbox */}
                        <td className="py-2.5 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => handleToggleOne(r.id, e)}
                            className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500 cursor-pointer"
                          />
                        </td>

                        <td className="py-2.5 px-3 font-mono font-semibold text-teal-800">
                          <button
                            onClick={() => onSelectEncounter(r.encounterId)}
                            className="hover:underline flex items-center gap-1 cursor-pointer"
                          >
                            {r.encounterId}
                            <ExternalLink className="h-3 w-3 opacity-60" />
                          </button>
                        </td>
                      <td className="py-2.5 px-3 font-medium text-slate-800">{r.department}</td>
                      <td className="py-2.5 px-3 text-slate-600">{r.revenueCentre}</td>
                      <td className="py-2.5 px-3 text-right font-medium text-slate-800">
                        {formatINR(r.totalServiceAmount)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-medium text-slate-800">
                        {formatINR(r.totalBilledAmount)}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {r.unbilledExposure + r.varianceExposure > 0 ? (
                          <span className="font-bold text-amber-900">
                            {formatINR(r.unbilledExposure + r.varianceExposure)}
                          </span>
                        ) : (
                          <span className="text-slate-400">₹0</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        {r.exceptionCount > 0 ? (
                          <span className="rounded bg-amber-50 text-amber-800 border border-amber-200 px-1.5 py-0.5 text-[10px] font-bold">
                            {r.exceptionCount} logged
                          </span>
                        ) : (
                          <span className="text-emerald-700 text-[11px] font-medium flex items-center gap-0.5">
                            <CheckCircle2 className="h-3 w-3" /> Clean
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        {r.status === 'VERIFIED' && (
                          <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-800 border border-emerald-200">
                            <CheckCircle2 className="h-3 w-3" /> VERIFIED
                          </span>
                        )}
                        {r.status === 'PENDING_VERIFICATION' && (
                          <span className="inline-flex items-center gap-1 rounded bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200">
                            <Clock className="h-3 w-3" /> PENDING
                          </span>
                        )}
                        {r.status === 'DISPUTED' && (
                          <span className="inline-flex items-center gap-1 rounded bg-red-50 px-2 py-0.5 text-[10px] font-bold text-red-800 border border-red-200">
                            <AlertTriangle className="h-3 w-3" /> DISPUTED
                          </span>
                        )}
                        {r.status === 'CORRECTION_REQUIRED' && (
                          <span className="inline-flex items-center gap-1 rounded bg-orange-50 px-2 py-0.5 text-[10px] font-bold text-orange-800 border border-orange-200">
                            <RefreshCw className="h-3 w-3" /> CORRECTION REQ.
                          </span>
                        )}
                        {r.status === 'UNABLE_TO_VERIFY' && (
                          <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-700 border border-slate-200">
                            <HelpCircle className="h-3 w-3" /> UNABLE
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-slate-600 max-w-xs truncate">
                        {r.comment || <span className="text-slate-400 italic">No notes</span>}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {currentUser.role === 'Auditor' ? (
                          <span className="text-[10px] text-slate-400 font-medium">Read-Only</span>
                        ) : (
                          <button
                            onClick={() => openReviewModal(r)}
                            className="rounded bg-teal-50 border border-teal-200 px-2 py-1 text-xs font-semibold text-teal-800 hover:bg-teal-100 transition cursor-pointer"
                          >
                            Review / Dispute
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                }))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SUB-VIEW 2: DEPARTMENT CLEARANCE MATRIX */}
      {activeTab === 'matrix' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                Departmental Financial Clearance Matrix
              </h2>
              <p className="text-[11px] text-slate-500">
                Cross-departmental clearance map per active encounter &bull; Legend: ✓ Verified &bull; ⚠ Disputed &bull; • Pending &bull; ○ N/A
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1 text-emerald-700 font-semibold">
                ✓ Verified
              </span>
              <span className="flex items-center gap-1 text-amber-700 font-semibold">
                • Pending Review
              </span>
              <span className="flex items-center gap-1 text-red-700 font-semibold">
                ⚠ Disputed
              </span>
              <span className="flex items-center gap-1 text-slate-400">
                ○ Not Applicable
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-center text-xs">
              <thead className="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-3 text-left">Encounter</th>
                  <th className="py-2.5 px-3 text-left">Clinical Ward</th>
                  {ALL_HOSPITAL_DEPARTMENTS.map((d) => (
                    <th key={d} className="py-2.5 px-2">
                      {d}
                    </th>
                  ))}
                  <th className="py-2.5 px-3 text-right">Encounter Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {uniqueEncounters.map((enc, idx) => {
                  return (
                    <tr key={`${enc.Encounter_ID}-${idx}`} className="hover:bg-slate-50/80 transition">
                      <td className="py-2 px-3 text-left font-mono font-semibold text-teal-800">
                        <button
                          onClick={() => onSelectEncounter(enc.Encounter_ID)}
                          className="hover:underline cursor-pointer"
                        >
                          {enc.Encounter_ID}
                        </button>
                      </td>
                      <td className="py-2 px-3 text-left text-slate-600">
                        {enc.Department} ({enc.Ward})
                      </td>
                      {ALL_HOSPITAL_DEPARTMENTS.map((dept) => {
                        const rec = records.find(
                          (r) => r.encounterId === enc.Encounter_ID && r.department === dept
                        );
                        if (!rec) {
                          return (
                            <td key={dept} className="py-2 px-2 text-slate-300">
                              ○
                            </td>
                          );
                        }
                        if (rec.status === 'VERIFIED') {
                          return (
                            <td key={dept} className="py-2 px-2 font-bold text-emerald-600" title="Verified">
                              ✓
                            </td>
                          );
                        }
                        if (rec.status === 'DISPUTED') {
                          return (
                            <td key={dept} className="py-2 px-2 font-bold text-red-600" title="Disputed">
                              ⚠
                            </td>
                          );
                        }
                        if (rec.status === 'CORRECTION_REQUIRED') {
                          return (
                            <td key={dept} className="py-2 px-2 font-bold text-orange-600" title="Correction Required">
                              ↻
                            </td>
                          );
                        }
                        return (
                          <td key={dept} className="py-2 px-2 font-bold text-amber-600" title="Pending Verification">
                            •
                          </td>
                        );
                      })}
                      <td className="py-2 px-3 text-right font-medium">
                        <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                          {enc.Discharge_Status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SUB-VIEW 3: CFO DEPARTMENT CLEARANCE DASHBOARD */}
      {activeTab === 'cfo-summary' && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                Institutional Clearance Rate
              </h3>
              <div className="text-2xl font-bold text-teal-800">
                {summary.clearancePercent}%
              </div>
              <p className="mt-1 text-[11px] text-slate-500">
                {summary.verifiedCount} of {summary.totalRecords} departmental service units fully reconciled.
              </p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-amber-200 bg-amber-50/20 shadow-2xs">
              <h3 className="text-xs font-bold uppercase tracking-wider text-amber-800 mb-1">
                Exposure Pending Clearance
              </h3>
              <div className="text-2xl font-bold text-amber-900">
                {formatINR(summary.exposureAwaitingVerification)}
              </div>
              <p className="mt-1 text-[11px] text-amber-700">
                {summary.pendingCount} departments must complete service audit before final billing closure.
              </p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-red-200 bg-red-50/20 shadow-2xs">
              <h3 className="text-xs font-bold uppercase tracking-wider text-red-800 mb-1">
                Disputed Service Value
              </h3>
              <div className="text-2xl font-bold text-red-700">
                {formatINR(summary.disputedExposure)}
              </div>
              <p className="mt-1 text-[11px] text-red-600">
                {summary.disputedCount} clinical disputed lines requiring Finance Manager intervention.
              </p>
            </div>
          </div>

          {/* Departmental breakdown cards */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
            <h3 className="text-sm font-bold text-slate-900 mb-3">
              Departmental Clearance Status by Operating Unit
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {ALL_HOSPITAL_DEPARTMENTS.map((dept) => {
                const deptRecs = records.filter((r) => r.department === dept);
                const total = deptRecs.length;
                const verified = deptRecs.filter((r) => r.status === 'VERIFIED').length;
                const pending = deptRecs.filter((r) => r.status === 'PENDING_VERIFICATION').length;
                const disputed = deptRecs.filter((r) => r.status === 'DISPUTED').length;
                const pct = total > 0 ? Math.round((verified / total) * 100) : 100;

                return (
                  <div key={dept} className="p-3 rounded-lg border border-slate-200 bg-slate-50/50">
                    <div className="flex items-center justify-between text-xs font-bold text-slate-900 mb-1">
                      <span>{dept}</span>
                      <span className={pct === 100 ? 'text-emerald-700' : 'text-amber-700'}>{pct}%</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-1.5 mb-2">
                      <div
                        className={`h-1.5 rounded-full ${pct === 100 ? 'bg-emerald-600' : 'bg-amber-500'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] text-slate-500">
                      <span>Total: {total}</span>
                      <span className="text-amber-700">Pending: {pending}</span>
                      <span className="text-red-700">Dispute: {disputed}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* REVIEW & DISPUTE MODAL */}
      {reviewingRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full p-6 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <FileCheck2 className="h-5 w-5 text-teal-700" />
                <h3 className="text-sm font-bold text-slate-900">
                  Departmental Financial Clearance Review
                </h3>
              </div>
              <button
                onClick={() => setReviewingRecord(null)}
                className="text-slate-400 hover:text-slate-600 text-lg cursor-pointer"
              >
                &times;
              </button>
            </div>

            <div className="my-4 space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Encounter ID</span>
                  <span className="font-mono font-bold text-teal-800">{reviewingRecord.encounterId}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Department</span>
                  <span className="font-bold text-slate-800">{reviewingRecord.department}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Expected Service Value</span>
                  <span className="font-semibold text-slate-800">
                    {formatINR(reviewingRecord.totalServiceAmount)}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Billed Amount</span>
                  <span className="font-semibold text-slate-800">
                    {formatINR(reviewingRecord.totalBilledAmount)}
                  </span>
                </div>
              </div>

              {/* Department User Constraint Notice */}
              <div className="flex items-center gap-2 p-2 rounded-lg bg-teal-50 border border-teal-200 text-teal-900 text-[11px]">
                <Lock className="h-4 w-4 shrink-0 text-teal-700" />
                <span>
                  Department managers verify service delivery authenticity. Direct alteration of billed figures or ledger entries is restricted to Finance.
                </span>
              </div>

              {/* Verification Status Selector */}
              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">
                  Verification Decision
                </label>
                <select
                  value={formStatus}
                  onChange={(e) => setFormStatus(e.target.value as DepartmentClearanceStatus)}
                  className="w-full border border-slate-300 rounded-lg p-2 text-xs font-semibold text-slate-900 focus:outline-teal-600"
                >
                  <option value="VERIFIED">VERIFIED &mdash; Services confirmed rendered as captured</option>
                  <option value="DISPUTED">DISPUTED &mdash; Service was not performed / wrong patient</option>
                  <option value="CORRECTION_REQUIRED">CORRECTION REQUIRED &mdash; Quantity or item code error</option>
                  <option value="UNABLE_TO_VERIFY">UNABLE TO VERIFY &mdash; Missing clinical service sheet</option>
                  <option value="PENDING_VERIFICATION">PENDING VERIFICATION &mdash; Under clinical review</option>
                </select>
              </div>

              {/* Comments & justification */}
              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">
                  Department Comment / Clinical Justification
                </label>
                <textarea
                  rows={3}
                  value={formComment}
                  onChange={(e) => setFormComment(e.target.value)}
                  placeholder="e.g. Verified against Nursing Administration Record. CBC was drawn twice on Sep 20."
                  className="w-full border border-slate-300 rounded-lg p-2 text-xs text-slate-900 focus:outline-teal-600"
                />
              </div>

              {/* Evidence reference */}
              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">
                  Evidence / Requisition Slip Reference
                </label>
                <input
                  type="text"
                  value={formEvidence}
                  onChange={(e) => setFormEvidence(e.target.value)}
                  placeholder="e.g. LIS-Slip #90214 or OT-Book Vol 4 Page 12"
                  className="w-full border border-slate-300 rounded-lg p-2 text-xs text-slate-900 focus:outline-teal-600"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
              <button
                type="button"
                onClick={() => setReviewingRecord(null)}
                className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveReview}
                className="px-4 py-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-xs font-semibold text-white transition shadow-xs cursor-pointer"
              >
                Submit Verification Record
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
