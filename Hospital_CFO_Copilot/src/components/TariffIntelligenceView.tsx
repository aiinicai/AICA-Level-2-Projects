import React, { useMemo, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Building2,
  Calendar,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileSpreadsheet,
  Filter,
  HelpCircle,
  Layers,
  Search,
  ShieldAlert,
} from 'lucide-react';
import { TariffIntelligenceSummary } from '../engine/tariffEngine';
import {
  Encounter,
  HospitalDepartment,
  TariffDeviationItem,
  TariffMasterItem,
  UserSession,
} from '../types';
import { formatINR } from '../utils/formatters';
import { EmptyWorkspaceState } from './EmptyWorkspaceState';

interface TariffIntelligenceViewProps {
  tariffMaster: TariffMasterItem[];
  deviations: TariffDeviationItem[];
  summary: TariffIntelligenceSummary;
  currentUser: UserSession;
  onInvestigateDeviation?: (
    deviationId: string,
    updates: {
      status: TariffDeviationItem['status'];
      notes?: string;
    }
  ) => void;
  onSelectEncounter?: (encounterId: string) => void;
  onNavigateToTab?: (tab: string) => void;
}

export const TariffIntelligenceView: React.FC<TariffIntelligenceViewProps> = ({
  tariffMaster,
  deviations,
  summary,
  currentUser,
  onInvestigateDeviation,
  onSelectEncounter,
  onNavigateToTab,
}) => {
  const [activeTab, setActiveTab] = useState<'variances' | 'master'>('variances');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Investigation modal state
  const [investigatingItem, setInvestigatingItem] = useState<TariffDeviationItem | null>(null);
  const [invStatus, setInvStatus] = useState<TariffDeviationItem['status']>('VERIFIED_ACCEPTED');
  const [invNotes, setInvNotes] = useState('');
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);

  // Multi-select batch action state
  const [selectedDeviationIds, setSelectedDeviationIds] = useState<Set<string>>(new Set());
  const [batchFeedback, setBatchFeedback] = useState<string | null>(null);

  const handleToggleSelectAll = () => {
    if (filteredDeviations.length === 0) return;
    const allSelected = filteredDeviations.every((d) => selectedDeviationIds.has(d.id));
    const next = new Set(selectedDeviationIds);
    if (allSelected) {
      filteredDeviations.forEach((d) => next.delete(d.id));
    } else {
      filteredDeviations.forEach((d) => next.add(d.id));
    }
    setSelectedDeviationIds(next);
  };

  const handleToggleOne = (id: string, e?: React.SyntheticEvent) => {
    e?.stopPropagation();
    const next = new Set(selectedDeviationIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedDeviationIds(next);
  };

  const handleBatchUpdateTariff = (newStatus: TariffDeviationItem['status'], notes: string) => {
    if (selectedDeviationIds.size === 0) return;
    const count = selectedDeviationIds.size;
    selectedDeviationIds.forEach((id) => {
      onInvestigateDeviation?.(id, {
        status: newStatus,
        notes,
      });
    });
    setSelectedDeviationIds(new Set());
    setBatchFeedback(`Successfully updated ${count} tariff variances to ${newStatus.replace(/_/g, ' ')}.`);
    setTimeout(() => setBatchFeedback(null), 4000);
  };

  const filteredDeviations = useMemo(() => {
    return deviations.filter((d) => {
      if (typeFilter !== 'ALL' && d.varianceType !== typeFilter) return false;
      if (statusFilter !== 'ALL' && d.status !== statusFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchCode = d.serviceCode.toLowerCase().includes(q);
        const matchDesc = d.serviceDescription.toLowerCase().includes(q);
        const matchEnc = d.encounterId.toLowerCase().includes(q);
        const matchPayer = d.payer.toLowerCase().includes(q);
        if (!matchCode && !matchDesc && !matchEnc && !matchPayer) return false;
      }
      return true;
    });
  }, [deviations, typeFilter, statusFilter, searchQuery]);

  const openInvestigation = (item: TariffDeviationItem) => {
    setInvestigatingItem(item);
    setInvStatus(item.status);
    setInvNotes(item.notes || '');
  };

  const handleSaveInvestigation = () => {
    if (!investigatingItem) return;
    const targetId = investigatingItem.id;
    onInvestigateDeviation?.(targetId, {
      status: invStatus,
      notes: invNotes,
    });
    setInvestigatingItem(null);
    setSaveSuccessMessage(`Response saved for variance ${targetId}: updated to ${invStatus.replace(/_/g, ' ')}.`);
    setTimeout(() => setSaveSuccessMessage(null), 4000);
  };

  if (tariffMaster.length === 0 && deviations.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            Tariff &amp; Rate Review
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Audit billed line-items against approved hospital standard &amp; payor contracted rate schedules.
          </p>
        </div>
        <EmptyWorkspaceState
          title="No tariff master has been uploaded."
          description="Rate variance auditing requires the hospital tariff master schedule and billed clinical services. Upload your rate contracts and billing registers to evaluate contract adherence."
          badge="Tariff Inactive"
          actionText="Upload Hospital Financial Extracts"
          onAction={() => onNavigateToTab?.('data-intelligence')}
          suggestedDatasets={[
            'Tariff Master / Charge Master (Service_Code, Standard_Tariff, Payer)',
            'Clinical Services with Billed Amounts (Service_Code, Expected_Amount)',
            'Billing Invoices and Line Items',
          ]}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Save Success Banner */}
      {saveSuccessMessage && (
        <div className="flex items-center justify-between gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-medium text-emerald-800 shadow-xs animate-in fade-in slide-in-from-top-1">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            <span>{saveSuccessMessage}</span>
          </div>
          <button
            onClick={() => setSaveSuccessMessage(null)}
            className="text-emerald-700 hover:text-emerald-900 font-bold ml-2 cursor-pointer text-base leading-none"
          >
            &times;
          </button>
        </div>
      )}

      {/* Top Banner */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Tariff &amp; Rate Review
              </h1>
              <span className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-bold tracking-wider text-teal-800 border border-teal-200 uppercase">
                Contract Adherence
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Audit billed line-items against approved hospital standard &amp; payor contracted rate schedules.
              Identifies <span className="font-semibold text-teal-800">Billing Amount Variances</span> for investigation and resolution.
            </p>
          </div>

          <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs font-semibold">
            <button
              onClick={() => setActiveTab('variances')}
              className={`rounded-md px-3 py-1.5 transition cursor-pointer ${
                activeTab === 'variances'
                  ? 'bg-white text-teal-800 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Potential Tariff Variances ({deviations.length})
            </button>
            <button
              onClick={() => setActiveTab('master')}
              className={`rounded-md px-3 py-1.5 transition cursor-pointer ${
                activeTab === 'master'
                  ? 'bg-white text-teal-800 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Tariff Master Schedule ({tariffMaster.length})
            </button>
          </div>
        </div>

        {/* Metric summary strip */}
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-4 border-t border-slate-100 text-xs">
          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Total Analyzed</div>
            <div className="text-base font-bold text-slate-900">{summary.totalServicesAnalyzed} items</div>
          </div>
          <div className="bg-slate-50 p-2.5 rounded-lg border border-amber-200 bg-amber-50/20">
            <div className="text-[10px] uppercase font-bold text-amber-800">Potential Variances</div>
            <div className="text-base font-bold text-amber-900">{summary.deviationsCount} items</div>
          </div>
          <div className="bg-slate-50 p-2.5 rounded-lg border border-red-200 bg-red-50/20">
            <div className="text-[10px] uppercase font-bold text-red-800">Underbilled Exposure</div>
            <div className="text-base font-bold text-red-700">{formatINR(summary.underbilledExposure)}</div>
          </div>
          <div className="bg-slate-50 p-2.5 rounded-lg border border-blue-200 bg-blue-50/20">
            <div className="text-[10px] uppercase font-bold text-blue-800">Overbilled Exposure</div>
            <div className="text-base font-bold text-blue-700">{formatINR(summary.overbilledExposure)}</div>
          </div>
          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Expired Tariffs</div>
            <div className="text-base font-bold text-orange-700">{summary.expiredTariffCount} items</div>
          </div>
          <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Missing Tariffs</div>
            <div className="text-base font-bold text-slate-700">{summary.missingTariffCount} items</div>
          </div>
        </div>
      </div>

      {/* VIEW 1: POTENTIAL TARIFF VARIANCES */}
      {activeTab === 'variances' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          {/* Filter Bar */}
          <div className="p-4 border-b border-slate-200 bg-slate-50/60 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                <Filter className="h-4 w-4 text-slate-400" />
                <span>Variance Type:</span>
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  className="border border-slate-300 rounded-md px-2 py-1 text-xs bg-white text-slate-900 font-normal focus:outline-teal-600"
                >
                  <option value="ALL">All Types</option>
                  <option value="UNDERBILLING">Underbilling</option>
                  <option value="OVERBILLING">Overbilling</option>
                  <option value="PAYER_TARIFF_VARIANCE">Payer Tariff Variance</option>
                  <option value="EXPIRED_TARIFF">Expired Tariff</option>
                  <option value="MISSING_TARIFF">Missing Tariff</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                <span>Status:</span>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="border border-slate-300 rounded-md px-2 py-1 text-xs bg-white text-slate-900 font-normal focus:outline-teal-600"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="PENDING_INVESTIGATION">Pending Investigation</option>
                  <option value="VERIFIED_ACCEPTED">Verified &amp; Accepted</option>
                  <option value="ADJUSTMENT_REQUIRED">Adjustment Required</option>
                </select>
              </div>
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="h-3.5 w-3.5 absolute left-2.5 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search code, description, encounter..."
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
          {selectedDeviationIds.size > 0 && (
            <div className="mx-4 mb-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-teal-300 bg-teal-50/90 px-4 py-2.5 shadow-xs animate-in fade-in slide-in-from-top-1 text-slate-800">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-6 items-center justify-center rounded-full bg-teal-700 px-2.5 text-xs font-bold text-white">
                  {selectedDeviationIds.size}
                </span>
                <span className="text-xs font-bold text-teal-950">Tariff Variances Selected</span>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={() => handleBatchUpdateTariff('VERIFIED_ACCEPTED', 'Batch approved: Contractual deviation verified & accepted')}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-300 bg-emerald-100 hover:bg-emerald-200 px-2.5 py-1 text-xs font-semibold text-emerald-900 shadow-2xs transition cursor-pointer"
                  title="Verify & Accept Selected Variances"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Verify &amp; Accept Selected</span>
                </button>

                <button
                  onClick={() => handleBatchUpdateTariff('ADJUSTMENT_REQUIRED', 'Batch flagged: Rate adjustment required in billing ledger')}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-orange-300 bg-orange-100 hover:bg-orange-200 px-2.5 py-1 text-xs font-semibold text-orange-900 shadow-2xs transition cursor-pointer"
                  title="Mark Selected as Adjustment Required"
                >
                  <AlertTriangle className="h-3.5 w-3.5" />
                  <span>Mark Adjustment Required</span>
                </button>

                <button
                  onClick={() => handleBatchUpdateTariff('PENDING_INVESTIGATION', 'Batch reset to Pending Investigation')}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-amber-100 hover:bg-amber-200 px-2.5 py-1 text-xs font-semibold text-amber-900 shadow-2xs transition cursor-pointer"
                  title="Mark as Under Investigation"
                >
                  <Clock className="h-3.5 w-3.5" />
                  <span>Under Investigation</span>
                </button>

                <button
                  onClick={() => setSelectedDeviationIds(new Set())}
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
                      checked={filteredDeviations.length > 0 && filteredDeviations.every((d) => selectedDeviationIds.has(d.id))}
                      ref={(el) => {
                        if (el) {
                          const someSelected = filteredDeviations.some((d) => selectedDeviationIds.has(d.id));
                          const allSelected = filteredDeviations.length > 0 && filteredDeviations.every((d) => selectedDeviationIds.has(d.id));
                          el.indeterminate = someSelected && !allSelected;
                        }
                      }}
                      onChange={handleToggleSelectAll}
                      className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500 cursor-pointer"
                      title="Select All Filtered Variances"
                    />
                  </th>
                  <th className="py-2.5 px-3">Encounter</th>
                  <th className="py-2.5 px-3">Service Code</th>
                  <th className="py-2.5 px-3">Description</th>
                  <th className="py-2.5 px-3">Payer</th>
                  <th className="py-2.5 px-3 text-right">Expected Tariff</th>
                  <th className="py-2.5 px-3 text-right">Actual Billed</th>
                  <th className="py-2.5 px-3 text-right">Variance</th>
                  <th className="py-2.5 px-3 text-right">Variance %</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {filteredDeviations.length === 0 ? (
                  <tr>
                    <td colSpan={12} className="py-8 text-center text-xs text-slate-500">
                      No tariff variances found matching current filter.
                    </td>
                  </tr>
                ) : (
                  filteredDeviations.map((d) => {
                    const isSelected = selectedDeviationIds.has(d.id);
                    return (
                      <tr
                        key={d.id}
                        className={`hover:bg-slate-50/80 transition ${
                          isSelected ? 'bg-teal-50/70' : ''
                        }`}
                      >
                        {/* Checkbox */}
                        <td className="py-2.5 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => handleToggleOne(d.id, e)}
                            className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500 cursor-pointer"
                          />
                        </td>

                        <td className="py-2.5 px-3 font-mono font-semibold text-teal-800">
                          <button
                            onClick={() => onSelectEncounter?.(d.encounterId)}
                            className="hover:underline flex items-center gap-1 cursor-pointer"
                          >
                            {d.encounterId}
                          </button>
                        </td>
                      <td className="py-2.5 px-3 font-mono font-semibold text-slate-900">{d.serviceCode}</td>
                      <td className="py-2.5 px-3 text-slate-700 max-w-xs truncate">{d.serviceDescription}</td>
                      <td className="py-2.5 px-3 text-slate-600">{d.payer}</td>
                      <td className="py-2.5 px-3 text-right font-medium text-slate-800">
                        {formatINR(d.expectedTariff)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-medium text-slate-800">
                        {formatINR(d.actualBilled)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold">
                        <span className={d.variance < 0 ? 'text-red-700' : 'text-blue-700'}>
                          {d.variance > 0 ? `+${formatINR(d.variance)}` : `-${formatINR(Math.abs(d.variance))}`}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-semibold text-slate-700">
                        {d.variancePercent}%
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            d.varianceType === 'UNDERBILLING'
                              ? 'bg-red-50 text-red-700 border border-red-200'
                              : d.varianceType === 'OVERBILLING'
                              ? 'bg-blue-50 text-blue-700 border border-blue-200'
                              : d.varianceType === 'EXPIRED_TARIFF'
                              ? 'bg-orange-50 text-orange-700 border border-orange-200'
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}
                        >
                          {d.varianceType.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-semibold ${
                            d.status === 'VERIFIED_ACCEPTED'
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                              : d.status === 'ADJUSTMENT_REQUIRED'
                              ? 'bg-orange-50 text-orange-800 border border-orange-200'
                              : 'bg-amber-50 text-amber-800 border border-amber-200'
                          }`}
                        >
                          {d.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {currentUser.role === 'Auditor' ? (
                          <span className="text-[10px] text-slate-400">Read-Only</span>
                        ) : (
                          <button
                            onClick={() => openInvestigation(d)}
                            className="rounded bg-teal-50 border border-teal-200 px-2 py-1 text-xs font-semibold text-teal-800 hover:bg-teal-100 transition cursor-pointer"
                          >
                            Investigate
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

      {/* VIEW 2: TARIFF MASTER SCHEDULE */}
      {activeTab === 'master' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900">
              Active Tariff Schedule &amp; Contracted Payer Rates
            </h2>
            <span className="text-xs text-slate-500">
              Deterministic reference master for IPD/OPD billing
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Service Code</th>
                  <th className="py-2.5 px-3">Service Description</th>
                  <th className="py-2.5 px-3">Revenue Centre</th>
                  <th className="py-2.5 px-3 text-right">Standard Tariff</th>
                  <th className="py-2.5 px-3">Payer</th>
                  <th className="py-2.5 px-3 text-right">Payer Contract Tariff</th>
                  <th className="py-2.5 px-3">Effective Range</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {tariffMaster.map((t, idx) => (
                  <tr key={`${t.Service_Code}-${t.Payer}-${idx}`} className="hover:bg-slate-50/80 transition">
                    <td className="py-2.5 px-3 font-mono font-semibold text-teal-800">{t.Service_Code}</td>
                    <td className="py-2.5 px-3 text-slate-900 font-medium">{t.Service_Description}</td>
                    <td className="py-2.5 px-3 text-slate-600">{t.Revenue_Centre}</td>
                    <td className="py-2.5 px-3 text-right font-semibold text-slate-900">
                      {formatINR(t.Standard_Tariff)}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-slate-800">{t.Payer}</td>
                    <td className="py-2.5 px-3 text-right font-bold text-teal-800">
                      {formatINR(t.Payer_Tariff)}
                    </td>
                    <td className="py-2.5 px-3 text-slate-500 font-mono text-[11px]">
                      {t.Effective_From} &rarr; {t.Effective_To}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* INVESTIGATION MODAL */}
      {investigatingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full p-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <h3 className="text-sm font-bold text-slate-900">
                Investigate Potential Tariff Variance
              </h3>
              <button
                onClick={() => setInvestigatingItem(null)}
                className="text-slate-400 hover:text-slate-600 text-lg cursor-pointer"
              >
                &times;
              </button>
            </div>

            <div className="my-4 space-y-3 text-xs">
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-slate-500">Service:</span>
                  <span className="font-semibold text-slate-900">{investigatingItem.serviceCode} - {investigatingItem.serviceDescription}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Encounter:</span>
                  <span className="font-mono font-bold text-teal-800">{investigatingItem.encounterId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Expected Tariff:</span>
                  <span className="font-semibold text-slate-800">{formatINR(investigatingItem.expectedTariff)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Actual Billed:</span>
                  <span className="font-semibold text-slate-800">{formatINR(investigatingItem.actualBilled)}</span>
                </div>
                <div className="flex justify-between font-bold">
                  <span className="text-slate-700">Variance:</span>
                  <span className={investigatingItem.variance < 0 ? 'text-red-700' : 'text-blue-700'}>
                    {formatINR(investigatingItem.variance)} ({investigatingItem.variancePercent}%)
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">
                  Investigation Finding &amp; Disposition
                </label>
                <select
                  value={invStatus}
                  onChange={(e) => setInvStatus(e.target.value as TariffDeviationItem['status'])}
                  className="w-full border border-slate-300 rounded-lg p-2 text-xs font-semibold text-slate-900 focus:outline-teal-600"
                >
                  <option value="VERIFIED_ACCEPTED">Verified &amp; Accepted &mdash; Contractual concession or emergency add-on approved</option>
                  <option value="ADJUSTMENT_REQUIRED">Adjustment Required &mdash; Tariff error confirmed; raise credit/debit memo</option>
                  <option value="PENDING_INVESTIGATION">Pending Investigation &mdash; In review with billing head</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase text-slate-700 mb-1">
                  Investigation Notes / Concession Reference
                </label>
                <textarea
                  rows={3}
                  value={invNotes}
                  onChange={(e) => setInvNotes(e.target.value)}
                  placeholder="e.g. Contract Amendment #24 allows 10% volume discount for Star Health on this code."
                  className="w-full border border-slate-300 rounded-lg p-2 text-xs text-slate-900 focus:outline-teal-600"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
              <button
                type="button"
                onClick={() => setInvestigatingItem(null)}
                className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveInvestigation}
                className="px-4 py-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-xs font-semibold text-white transition shadow-xs cursor-pointer"
              >
                Save Investigation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
