import React, { useState, useMemo } from 'react';
import { 
  FileText, 
  Search, 
  PlusCircle, 
  Filter, 
  FileSpreadsheet, 
  FileDown, 
  Eye, 
  Edit3, 
  Trash2, 
  ChevronDown, 
  ChevronUp, 
  SlidersHorizontal,
  X,
  IndianRupee,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Building,
  RotateCcw
} from 'lucide-react';
import { 
  Observation, 
  Engagement, 
  AuditType, 
  SeverityLevel, 
  ObservationStatus, 
  RectificationStatus,
  FirmProfile 
} from '../../types/audit';
import { 
  formatDate, 
  formatINR, 
  getSeverityBadgeClass, 
  getStatusBadgeClass, 
  getRectificationBadgeClass 
} from '../../utils/formatters';
import { ExportService } from '../../services/exportService';

interface ObservationListProps {
  observations?: Observation[];
  engagements?: Engagement[];
  auditTypes?: AuditType[];
  firmProfile: FirmProfile;
  initialFilters?: any;
  onOpenNewObservation: () => void;
  onViewObservation: (obs: Observation) => void;
  onEditObservation: (obs: Observation) => void;
  onDeleteObservation: (obsId: string) => void;
  onQuickUpdateStatus: (obsId: string, newStatus: ObservationStatus) => void;
}

export const ObservationList: React.FC<ObservationListProps> = ({
  observations = [],
  engagements = [],
  auditTypes = [],
  firmProfile,
  initialFilters,
  onOpenNewObservation,
  onViewObservation,
  onEditObservation,
  onDeleteObservation,
  onQuickUpdateStatus,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEngagement, setSelectedEngagement] = useState('ALL');
  const [selectedAuditType, setSelectedAuditType] = useState('ALL');
  const [selectedFY, setSelectedFY] = useState('ALL');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [selectedRectification, setSelectedRectification] = useState<string>('ALL');
  const [hasFinancialImpactOnly, setHasFinancialImpactOnly] = useState(false);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  // Sorting
  const [sortField, setSortField] = useState<'referenceNo' | 'dateOfObservation' | 'severity' | 'financialImpact' | 'status'>('dateOfObservation');
  const [sortAsc, setSortAsc] = useState(false);

  // Selection for bulk actions
  const [selectedObsIds, setSelectedObsIds] = useState<Set<string>>(new Set());

  const obsList = observations || [];
  const engList = engagements || [];
  const typeList = auditTypes || [];

  const auditTypeMap = useMemo(() => new Map(typeList.map(at => [at.id, at])), [typeList]);
  const engagementMap = useMemo(() => new Map(engList.map(e => [e.id, e])), [engList]);

  // Distinct FYs
  const distinctFYs = useMemo(() => {
    return Array.from(new Set(engList.map(e => e.financialYear))).sort().reverse();
  }, [engList]);

  // Apply initial filters if passed
  React.useEffect(() => {
    if (initialFilters) {
      if (initialFilters.severity && initialFilters.severity.length === 1) {
        setSelectedSeverity(initialFilters.severity[0]);
      } else if (initialFilters.severity && initialFilters.severity.includes('Critical')) {
        setSelectedSeverity('CRITICAL_HIGH');
      }
      if (initialFilters.auditTypeId) {
        setSelectedAuditType(initialFilters.auditTypeId);
      }
      if (initialFilters.status && initialFilters.status.length > 0) {
        setSelectedStatus('OPEN_ONLY');
      }
      if (initialFilters.engagementId) {
        setSelectedEngagement(initialFilters.engagementId);
      }
    }
  }, [initialFilters]);

  // Filtered observations
  const filteredObservations = useMemo(() => {
    return obsList.filter((obs) => {
      const eng = engagementMap.get(obs.engagementId);
      if (!eng && selectedEngagement !== 'ALL') return false;

      // Engagement filter
      if (selectedEngagement !== 'ALL' && obs.engagementId !== selectedEngagement) return false;

      // Audit Type filter
      if (selectedAuditType !== 'ALL' && eng?.auditTypeId !== selectedAuditType) return false;

      // FY filter
      if (selectedFY !== 'ALL' && eng?.financialYear !== selectedFY) return false;

      // Severity filter
      if (selectedSeverity === 'CRITICAL_HIGH') {
        if (obs.severity !== 'Critical' && obs.severity !== 'High') return false;
      } else if (selectedSeverity !== 'ALL' && obs.severity !== selectedSeverity) {
        return false;
      }

      // Status filter
      if (selectedStatus === 'OPEN_ONLY') {
        if (obs.status === 'Closed' || obs.status === 'Rectified') return false;
      } else if (selectedStatus === 'CLOSED_RECTIFIED') {
        if (obs.status !== 'Closed' && obs.status !== 'Rectified') return false;
      } else if (selectedStatus !== 'ALL' && obs.status !== selectedStatus) {
        return false;
      }

      // Rectification filter
      if (selectedRectification !== 'ALL' && obs.rectificationStatus !== selectedRectification) return false;

      // Financial impact toggle
      if (hasFinancialImpactOnly && (!obs.financialImpact || obs.financialImpact <= 0)) return false;

      // Search keyword
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const clientName = eng?.clientName.toLowerCase() || '';
        const atName = eng ? auditTypeMap.get(eng.auditTypeId)?.name.toLowerCase() || '' : '';
        const match =
          obs.referenceNo.toLowerCase().includes(q) ||
          obs.areaProcess.toLowerCase().includes(q) ||
          obs.description.toLowerCase().includes(q) ||
          (obs.rootCause && obs.rootCause.toLowerCase().includes(q)) ||
          (obs.recommendation && obs.recommendation.toLowerCase().includes(q)) ||
          (obs.discussionStakeholder && obs.discussionStakeholder.toLowerCase().includes(q)) ||
          (obs.managementResponse && obs.managementResponse.toLowerCase().includes(q)) ||
          obs.personResponsible.toLowerCase().includes(q) ||
          clientName.includes(q) ||
          atName.includes(q);

        if (!match) return false;
      }

      return true;
    });
  }, [
    observations,
    engagementMap,
    auditTypeMap,
    selectedEngagement,
    selectedAuditType,
    selectedFY,
    selectedSeverity,
    selectedStatus,
    selectedRectification,
    hasFinancialImpactOnly,
    searchQuery,
  ]);

  // Sorted observations
  const sortedObservations = useMemo(() => {
    return [...filteredObservations].sort((a, b) => {
      let comparison = 0;
      if (sortField === 'referenceNo') {
        comparison = a.referenceNo.localeCompare(b.referenceNo);
      } else if (sortField === 'dateOfObservation') {
        comparison = new Date(a.dateOfObservation).getTime() - new Date(b.dateOfObservation).getTime();
      } else if (sortField === 'severity') {
        const order = { Critical: 0, High: 1, Medium: 2, Low: 3 };
        comparison = order[a.severity] - order[b.severity];
      } else if (sortField === 'financialImpact') {
        comparison = (a.financialImpact || 0) - (b.financialImpact || 0);
      } else if (sortField === 'status') {
        comparison = a.status.localeCompare(b.status);
      }
      return sortAsc ? comparison : -comparison;
    });
  }, [filteredObservations, sortField, sortAsc]);

  // Sorting handler
  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  // Selection toggle
  const toggleSelectAll = () => {
    if (selectedObsIds.size === sortedObservations.length) {
      setSelectedObsIds(new Set());
    } else {
      setSelectedObsIds(new Set(sortedObservations.map(o => o.id)));
    }
  };

  const toggleSelectObs = (id: string) => {
    const next = new Set(selectedObsIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedObsIds(next);
  };

  const handleResetFilters = () => {
    setSearchQuery('');
    setSelectedEngagement('ALL');
    setSelectedAuditType('ALL');
    setSelectedFY('ALL');
    setSelectedSeverity('ALL');
    setSelectedStatus('ALL');
    setSelectedRectification('ALL');
    setHasFinancialImpactOnly(false);
  };

  const handleDeleteConfirm = (e: React.MouseEvent, obs: Observation) => {
    e.stopPropagation();
    if (window.confirm(`Are you sure you want to delete observation "${obs.referenceNo}"?`)) {
      onDeleteObservation(obs.id);
    }
  };

  // Selected observations for export
  const exportTargetObservations = selectedObsIds.size > 0
    ? obsList.filter(o => selectedObsIds.has(o.id))
    : sortedObservations;

  return (
    <div id="observations-list-container" className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-stone-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-stone-800 tracking-tight">Audit Observation Register</h1>
            <span className="px-2.5 py-0.5 rounded-full bg-stone-100 text-stone-800 text-xs font-bold border border-stone-200">
              {filteredObservations.length} of {obsList.length} Logged
            </span>
          </div>
          <p className="text-sm text-stone-500 mt-0.5">
            Comprehensive lifecycle tracking of audit discrepancies, discussions, and rectifications.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            id="obs-export-excel-btn"
            onClick={() => ExportService.exportObservationsToExcel(exportTargetObservations, engList, typeList, 'Audit_Observations_Filtered')}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-stone-300 bg-white hover:bg-[#F5F2ED] text-stone-700 text-xs font-semibold shadow-xs transition-colors"
            title="Download formatted Excel (.xlsx) with Executive Summary tab and full Data tab"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-700" />
            <span>Excel Export {selectedObsIds.size > 0 ? `(${selectedObsIds.size})` : ''}</span>
          </button>

          <button
            id="obs-export-pdf-btn"
            onClick={() => ExportService.exportFilteredObservationsPDF(exportTargetObservations, engList, typeList, firmProfile, 'Filtered Observation Register')}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-stone-300 bg-white hover:bg-[#F5F2ED] text-stone-700 text-xs font-semibold shadow-xs transition-colors"
            title="Download PDF Table Summary"
          >
            <FileDown className="w-4 h-4 text-rose-700" />
            <span>PDF Register</span>
          </button>

          <button
            id="btn-log-new-observation"
            onClick={onOpenNewObservation}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#5A5A40] hover:bg-[#4A4A34] text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <PlusCircle className="w-4 h-4 text-amber-300" />
            <span>+ Log Finding</span>
          </button>
        </div>
      </div>

      {/* Quick Filter Chips & Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-stone-200 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row items-center gap-3">
          {/* Keyword Search */}
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-stone-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by Ref No (e.g. SA-2425), Area, Description, Client, Stakeholder..."
              className="w-full pl-9 pr-3.5 py-1.5 text-xs bg-stone-50 border border-stone-200 rounded-lg text-stone-800 placeholder-stone-400 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-[#5A5A40]/10 focus:border-[#5A5A40]"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-2 text-stone-400 hover:text-stone-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Quick Primary Filters */}
          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            <select
              value={selectedEngagement}
              onChange={(e) => setSelectedEngagement(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 font-medium focus:bg-white focus:outline-hidden max-w-[180px] truncate"
            >
              <option value="ALL">All Engagements</option>
              {engagements.map((eng) => (
                <option key={eng.id} value={eng.id}>
                  {eng.clientName} ({eng.financialYear})
                </option>
              ))}
            </select>

            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 font-medium focus:bg-white focus:outline-hidden"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL_HIGH">Critical & High Only</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 font-medium focus:bg-white focus:outline-hidden"
            >
              <option value="ALL">All Statuses</option>
              <option value="OPEN_ONLY">All Open (Pending)</option>
              <option value="Open">Open</option>
              <option value="Under Discussion">Under Discussion</option>
              <option value="Management Response Awaited">Response Awaited</option>
              <option value="Rectified">Rectified</option>
              <option value="Closed">Closed</option>
              <option value="CLOSED_RECTIFIED">Closed / Rectified</option>
              <option value="Not Accepted">Not Accepted</option>
            </select>

            <button
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
                showAdvancedFilters || hasFinancialImpactOnly || selectedAuditType !== 'ALL' || selectedFY !== 'ALL' || selectedRectification !== 'ALL'
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Filters</span>
            </button>

            {(selectedEngagement !== 'ALL' || selectedSeverity !== 'ALL' || selectedStatus !== 'ALL' || selectedAuditType !== 'ALL' || selectedFY !== 'ALL' || selectedRectification !== 'ALL' || hasFinancialImpactOnly || searchQuery) && (
              <button
                onClick={handleResetFilters}
                className="inline-flex items-center gap-1 text-xs text-rose-600 hover:text-rose-800 font-semibold px-2 py-1"
                title="Reset all filters"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>

        {/* Quick Filter Chips Bar */}
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-100 text-xs">
          <span className="text-slate-400 font-medium text-[11px]">Quick Views:</span>
          
          <button
            onClick={() => { setSelectedStatus('OPEN_ONLY'); setSelectedSeverity('CRITICAL_HIGH'); }}
            className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border transition-colors ${
              selectedStatus === 'OPEN_ONLY' && selectedSeverity === 'CRITICAL_HIGH'
                ? 'bg-rose-100 text-rose-800 border-rose-300'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            🔥 Critical & High Open
          </button>

          <button
            onClick={() => { setSelectedStatus('OPEN_ONLY'); setSelectedSeverity('ALL'); }}
            className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border transition-colors ${
              selectedStatus === 'OPEN_ONLY' && selectedSeverity === 'ALL'
                ? 'bg-blue-100 text-blue-800 border-blue-300'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            ⏳ All Pending / Open
          </button>

          <button
            onClick={() => setHasFinancialImpactOnly(!hasFinancialImpactOnly)}
            className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border transition-colors ${
              hasFinancialImpactOnly
                ? 'bg-amber-100 text-amber-900 border-amber-300'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            💰 Financial Impact Exposure &gt; ₹0
          </button>

          <button
            onClick={() => setSelectedStatus('Management Response Awaited')}
            className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border transition-colors ${
              selectedStatus === 'Management Response Awaited'
                ? 'bg-purple-100 text-purple-800 border-purple-300'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            📬 Management Response Awaited
          </button>

          <button
            onClick={() => setSelectedStatus('CLOSED_RECTIFIED')}
            className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border transition-colors ${
              selectedStatus === 'CLOSED_RECTIFIED'
                ? 'bg-teal-100 text-teal-800 border-teal-300'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            ✅ Closed & Rectified
          </button>
        </div>

        {/* Expandable Advanced Filters Drawer */}
        {showAdvancedFilters && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200 mt-2 text-xs">
            <div>
              <label className="font-bold text-slate-700 block mb-1">Filter by Audit Type</label>
              <select
                value={selectedAuditType}
                onChange={(e) => setSelectedAuditType(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-md p-1.5 text-xs text-slate-900"
              >
                <option value="ALL">All Audit Types</option>
                {auditTypes.map((at) => (
                  <option key={at.id} value={at.id}>
                    {at.name} ({at.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="font-bold text-slate-700 block mb-1">Filter by Financial Year</label>
              <select
                value={selectedFY}
                onChange={(e) => setSelectedFY(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-md p-1.5 text-xs text-slate-900"
              >
                <option value="ALL">All Financial Years</option>
                {distinctFYs.map((fy) => (
                  <option key={fy} value={fy}>
                    {fy}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="font-bold text-slate-700 block mb-1">Filter by Rectification</label>
              <select
                value={selectedRectification}
                onChange={(e) => setSelectedRectification(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-md p-1.5 text-xs text-slate-900"
              >
                <option value="ALL">All Rectification Statuses</option>
                <option value="Not Started">Not Started</option>
                <option value="In Progress">In Progress</option>
                <option value="Rectified">Rectified</option>
                <option value="Not Rectified">Not Rectified</option>
                <option value="Not Applicable">Not Applicable</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Observations Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {/* Bulk Action Bar (when rows are checked) */}
        {selectedObsIds.size > 0 && (
          <div className="bg-slate-900 text-white px-4 py-2 flex items-center justify-between text-xs animate-fadeIn">
            <div className="flex items-center gap-2">
              <span className="font-bold text-amber-400">{selectedObsIds.size} observations selected</span>
              <button
                onClick={() => setSelectedObsIds(new Set())}
                className="text-slate-400 hover:text-white underline text-[11px]"
              >
                Deselect all
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => ExportService.exportObservationsToExcel(exportTargetObservations, engagements, auditTypes, 'Selected_Observations')}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-white font-semibold transition-colors"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
                <span>Export Selected to Excel</span>
              </button>

              <button
                onClick={() => ExportService.exportFilteredObservationsPDF(exportTargetObservations, engagements, auditTypes, firmProfile, 'Selected Observations')}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-white font-semibold transition-colors"
              >
                <FileDown className="w-3.5 h-3.5 text-rose-400" />
                <span>Export Selected to PDF</span>
              </button>
            </div>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider select-none">
                <th className="py-3 px-3 w-8">
                  <input
                    type="checkbox"
                    checked={sortedObservations.length > 0 && selectedObsIds.size === sortedObservations.length}
                    onChange={toggleSelectAll}
                    className="rounded text-slate-900 focus:ring-slate-900/10 cursor-pointer"
                  />
                </th>

                <th 
                  onClick={() => handleSort('referenceNo')}
                  className="py-3 px-4 cursor-pointer hover:text-slate-900"
                >
                  <div className="flex items-center gap-1">
                    <span>Ref No. & Client</span>
                    {sortField === 'referenceNo' && (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                  </div>
                </th>

                <th 
                  onClick={() => handleSort('dateOfObservation')}
                  className="py-3 px-4 cursor-pointer hover:text-slate-900"
                >
                  <div className="flex items-center gap-1">
                    <span>Date</span>
                    {sortField === 'dateOfObservation' && (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                  </div>
                </th>

                <th className="py-3 px-4">Area / Process & Finding</th>

                <th 
                  onClick={() => handleSort('severity')}
                  className="py-3 px-4 cursor-pointer hover:text-slate-900"
                >
                  <div className="flex items-center gap-1">
                    <span>Severity</span>
                    {sortField === 'severity' && (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                  </div>
                </th>

                <th 
                  onClick={() => handleSort('financialImpact')}
                  className="py-3 px-4 cursor-pointer hover:text-slate-900"
                >
                  <div className="flex items-center gap-1">
                    <span>Impact (₹)</span>
                    {sortField === 'financialImpact' && (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                  </div>
                </th>

                <th 
                  onClick={() => handleSort('status')}
                  className="py-3 px-4 cursor-pointer hover:text-slate-900"
                >
                  <div className="flex items-center gap-1">
                    <span>Status</span>
                    {sortField === 'status' && (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)}
                  </div>
                </th>

                <th className="py-3 px-4">Rectification</th>
                <th className="py-3 px-4">Responsible</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100 text-xs">
              {sortedObservations.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-400">
                    <FileText className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                    <p className="font-semibold text-slate-700">No observations match your filter criteria</p>
                    <p className="text-xs text-slate-400 mt-1">Try clearing filters or search keyword.</p>
                    <button
                      onClick={handleResetFilters}
                      className="mt-3 px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 text-xs font-semibold hover:bg-slate-50 transition-colors"
                    >
                      Clear All Filters
                    </button>
                  </td>
                </tr>
              ) : (
                sortedObservations.map((obs) => {
                  const eng = engagementMap.get(obs.engagementId);
                  const at = eng ? auditTypeMap.get(eng.auditTypeId) : undefined;
                  const sevStyle = getSeverityBadgeClass(obs.severity);
                  const statStyle = getStatusBadgeClass(obs.status);
                  const rectStyle = getRectificationBadgeClass(obs.rectificationStatus);
                  const isChecked = selectedObsIds.has(obs.id);

                  return (
                    <tr
                      key={obs.id}
                      onClick={() => onViewObservation(obs)}
                      className={`hover:bg-slate-50/80 transition-colors cursor-pointer ${
                        isChecked ? 'bg-amber-50/30' : ''
                      }`}
                    >
                      <td className="py-3.5 px-3" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleSelectObs(obs.id)}
                          className="rounded text-slate-900 focus:ring-slate-900/10 cursor-pointer"
                        />
                      </td>

                      {/* Reference No & Client */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="font-mono font-bold text-slate-900 text-xs">
                          {obs.referenceNo}
                        </div>
                        <div className="text-[11px] text-slate-600 font-medium truncate max-w-[180px] mt-0.5">
                          {eng?.clientName || 'Unknown'} ({eng?.financialYear})
                        </div>
                      </td>

                      {/* Date */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-600">
                        {formatDate(obs.dateOfObservation)}
                      </td>

                      {/* Area & Description */}
                      <td className="py-3.5 px-4 max-w-[280px]">
                        <div className="font-bold text-slate-900 truncate">{obs.areaProcess}</div>
                        <div className="text-[11px] text-slate-500 line-clamp-2 mt-0.5 leading-relaxed">
                          {obs.description}
                        </div>
                      </td>

                      {/* Severity */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold border ${sevStyle.bg} ${sevStyle.text} ${sevStyle.border}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${sevStyle.dot}`}></span>
                          {obs.severity}
                        </span>
                      </td>

                      {/* Financial Impact */}
                      <td className="py-3.5 px-4 whitespace-nowrap font-bold text-slate-900">
                        {formatINR(obs.financialImpact)}
                      </td>

                      {/* Status Dropdown */}
                      <td className="py-3.5 px-4 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        <select
                          value={obs.status}
                          onChange={(e) => onQuickUpdateStatus(obs.id, e.target.value as ObservationStatus)}
                          className={`text-xs font-semibold rounded-md px-2 py-1 border focus:outline-hidden cursor-pointer ${statStyle.bg} ${statStyle.text} ${statStyle.border}`}
                        >
                          <option value="Open">Open</option>
                          <option value="Under Discussion">Under Discussion</option>
                          <option value="Management Response Awaited">Response Awaited</option>
                          <option value="Rectified">Rectified</option>
                          <option value="Closed">Closed</option>
                          <option value="Not Accepted">Not Accepted</option>
                        </select>
                      </td>

                      {/* Rectification */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${rectStyle.bg} ${rectStyle.text}`}>
                          {obs.rectificationStatus}
                        </span>
                        {obs.targetRectificationDate && (
                          <div className="text-[10px] text-slate-400 mt-0.5">
                            Target: {formatDate(obs.targetRectificationDate)}
                          </div>
                        )}
                      </td>

                      {/* Responsible */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-700 truncate max-w-[130px]">
                        {obs.personResponsible}
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-right space-x-1" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => onViewObservation(obs)}
                          className="p-1.5 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                          title="View Letterhead Memo"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => onEditObservation(obs)}
                          className="p-1.5 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                          title="Edit Observation"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            if (eng) {
                              ExportService.exportSingleObservationPDF(obs, eng, at, firmProfile);
                            }
                          }}
                          className="p-1.5 rounded-md text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                          title="Download PDF"
                        >
                          <FileDown className="w-4 h-4 text-rose-600" />
                        </button>
                        <button
                          onClick={(e) => handleDeleteConfirm(e, obs)}
                          className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                          title="Delete Observation"
                        >
                          <Trash2 className="w-4 h-4" />
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
    </div>
  );
};
