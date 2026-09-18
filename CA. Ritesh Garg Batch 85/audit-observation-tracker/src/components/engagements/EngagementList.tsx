import React, { useState } from 'react';
import { 
  Briefcase, 
  Search, 
  PlusCircle, 
  Filter, 
  Calendar, 
  MapPin, 
  UserCheck, 
  FileText, 
  FileDown, 
  Trash2, 
  Edit3, 
  ChevronRight, 
  CheckCircle2,
  Building,
  LayoutGrid,
  List,
  Upload,
  Download,
  FileSpreadsheet
} from 'lucide-react';
import { Engagement, Observation, AuditType, FirmProfile } from '../../types/audit';
import { formatDate, formatINR, getEngagementStatusBadgeClass } from '../../utils/formatters';
import { ExportService } from '../../services/exportService';
import { TemplateService } from '../../services/templateService';
import { BulkEngagementUploadModal } from './BulkEngagementUploadModal';

interface EngagementListProps {
  engagements?: Engagement[];
  observations?: Observation[];
  auditTypes?: AuditType[];
  firmProfile: FirmProfile;
  onOpenNewEngagement: () => void;
  onViewEngagement: (eng: Engagement) => void;
  onEditEngagement: (eng: Engagement) => void;
  onDeleteEngagement: (engId: string) => void;
  onAddObservationForEngagement: (engId: string) => void;
  onImportEngagements?: (engagements: Engagement[]) => void;
}

export const EngagementList: React.FC<EngagementListProps> = ({
  engagements = [],
  observations = [],
  auditTypes = [],
  firmProfile,
  onOpenNewEngagement,
  onViewEngagement,
  onEditEngagement,
  onDeleteEngagement,
  onAddObservationForEngagement,
  onImportEngagements,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAuditType, setSelectedAuditType] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [selectedFY, setSelectedFY] = useState('ALL');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [isBulkModalOpen, setIsBulkModalOpen] = useState(false);

  const engList = engagements || [];
  const obsList = observations || [];
  const typeList = auditTypes || [];

  const auditTypeMap = new Map<string, AuditType>(typeList.map(at => [at.id, at]));

  // Get distinct FYs
  const distinctFYs = Array.from(new Set(engList.map(e => e.financialYear))).sort().reverse();

  // Filter logic
  const filteredEngagements = engList.filter((eng) => {
    if (selectedAuditType !== 'ALL' && eng.auditTypeId !== selectedAuditType) return false;
    if (selectedStatus !== 'ALL' && eng.overallStatus !== selectedStatus) return false;
    if (selectedFY !== 'ALL' && eng.financialYear !== selectedFY) return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const atName = auditTypeMap.get(eng.auditTypeId)?.name.toLowerCase() || '';
      return (
        eng.clientName.toLowerCase().includes(q) ||
        eng.clientCode.toLowerCase().includes(q) ||
        (eng.clientPanGstin && eng.clientPanGstin.toLowerCase().includes(q)) ||
        (eng.branchLocation && eng.branchLocation.toLowerCase().includes(q)) ||
        eng.engagementPartner.toLowerCase().includes(q) ||
        atName.includes(q)
      );
    }
    return true;
  });

  const handleDeleteConfirm = (e: React.MouseEvent, eng: Engagement) => {
    e.stopPropagation();
    const obsCount = obsList.filter(o => o.engagementId === eng.id).length;
    const confirmMsg = obsCount > 0
      ? `Are you sure you want to delete engagement "${eng.clientName}"? This will also remove ${obsCount} linked observation(s).`
      : `Are you sure you want to delete engagement "${eng.clientName}"?`;

    if (window.confirm(confirmMsg)) {
      onDeleteEngagement(eng.id);
    }
  };

  const handleDownloadSample = () => {
    TemplateService.downloadAssignmentsSampleTemplate(auditTypes);
  };

  return (
    <div id="engagements-list-container" className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-stone-200 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-stone-800 tracking-tight">Audit Engagements Master</h1>
          <p className="text-sm text-stone-500 mt-0.5">
            Manage client audit assignments, team allocations, and overall audit progress.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
          <button
            onClick={handleDownloadSample}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-stone-300 bg-white text-stone-700 text-xs font-semibold hover:bg-stone-100 transition-colors shadow-2xs"
            title="Download sample Excel template for bulk assignments"
          >
            <Download className="w-3.5 h-3.5 text-stone-600" />
            <span>Sample Template (.xlsx)</span>
          </button>

          <button
            onClick={() => setIsBulkModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900 text-xs font-semibold transition-colors shadow-2xs"
          >
            <Upload className="w-3.5 h-3.5 text-amber-800" />
            <span>Bulk Upload (Excel)</span>
          </button>

          <button
            id="btn-create-new-engagement"
            onClick={onOpenNewEngagement}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#5A5A40] hover:bg-[#4A4A34] text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <PlusCircle className="w-4 h-4 text-amber-300" />
            <span>+ Create Engagement</span>
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-2xl border border-stone-200 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-stone-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by Client Name, PAN/GSTIN, Code, Location, Partner..."
              className="w-full pl-9 pr-3.5 py-1.5 text-xs bg-stone-50 border border-stone-200 rounded-lg text-stone-800 placeholder-stone-400 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-[#5A5A40]/10 focus:border-[#5A5A40]"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            <select
              value={selectedAuditType}
              onChange={(e) => setSelectedAuditType(e.target.value)}
              className="text-xs bg-stone-50 border border-stone-200 rounded-lg px-2.5 py-1.5 text-stone-700 font-medium focus:bg-white focus:outline-hidden"
            >
              <option value="ALL">All Audit Types</option>
              {auditTypes.map((at) => (
                <option key={at.id} value={at.id}>
                  {at.name}
                </option>
              ))}
            </select>

            <select
              value={selectedFY}
              onChange={(e) => setSelectedFY(e.target.value)}
              className="text-xs bg-stone-50 border border-stone-200 rounded-lg px-2.5 py-1.5 text-stone-700 font-medium focus:bg-white focus:outline-hidden"
            >
              <option value="ALL">All Financial Years</option>
              {distinctFYs.map((fy) => (
                <option key={fy} value={fy}>
                  {fy}
                </option>
              ))}
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="text-xs bg-stone-50 border border-stone-200 rounded-lg px-2.5 py-1.5 text-stone-700 font-medium focus:bg-white focus:outline-hidden"
            >
              <option value="ALL">All Statuses</option>
              <option value="Planning">Planning</option>
              <option value="In Progress">In Progress</option>
              <option value="Fieldwork Complete">Fieldwork Complete</option>
              <option value="Report Issued">Report Issued</option>
              <option value="Closed">Closed</option>
            </select>

            {/* View Mode Toggle */}
            <div className="flex items-center border border-stone-200 rounded-lg overflow-hidden p-0.5 bg-stone-50 ml-auto">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-1 rounded-md transition-colors ${viewMode === 'grid' ? 'bg-white shadow-xs text-stone-900' : 'text-stone-400 hover:text-stone-700'}`}
                title="Grid View"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setViewMode('table')}
                className={`p-1 rounded-md transition-colors ${viewMode === 'table' ? 'bg-white shadow-xs text-stone-900' : 'text-stone-400 hover:text-stone-700'}`}
                title="Table View"
              >
                <List className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Content View */}
      {filteredEngagements.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-2xl border border-stone-200 shadow-sm">
          <Briefcase className="w-10 h-10 text-stone-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-stone-800">No Engagements Found</h3>
          <p className="text-xs text-stone-500 mt-1 max-w-sm mx-auto">
            Try adjusting your search criteria or create a new audit engagement to get started.
          </p>
          <button
            onClick={onOpenNewEngagement}
            className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#5A5A40] text-white text-xs font-semibold hover:bg-[#4A4A34] transition-colors"
          >
            <PlusCircle className="w-3.5 h-3.5 text-amber-300" />
            <span>Create Engagement</span>
          </button>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredEngagements.map((eng) => {
            const auditType = auditTypeMap.get(eng.auditTypeId);
            const statusStyle = getEngagementStatusBadgeClass(eng.overallStatus);
            const engObs = obsList.filter(o => o.engagementId === eng.id);
            const openObsCount = engObs.filter(o => o.status !== 'Closed' && o.status !== 'Rectified').length;
            const criticalCount = engObs.filter(o => o.severity === 'Critical' || o.severity === 'High').length;
            const totalImpact = engObs.reduce((s, o) => s + (o.financialImpact || 0), 0);

            return (
              <div
                key={eng.id}
                onClick={() => onViewEngagement(eng)}
                className="bg-white rounded-2xl border border-stone-200 shadow-sm hover:border-stone-300 hover:shadow-md transition-all p-5 flex flex-col justify-between cursor-pointer group"
              >
                <div>
                  {/* Top line */}
                  <div className="flex items-center justify-between gap-2">
                    <span className="px-2 py-0.5 rounded-md bg-[#5A5A40] text-amber-300 font-mono font-bold text-[11px]">
                      {auditType?.code || 'AUD'}
                    </span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusStyle.bg} ${statusStyle.text} ${statusStyle.border}`}>
                      {eng.overallStatus}
                    </span>
                  </div>

                  {/* Title & Info */}
                  <h3 className="font-bold text-sm text-stone-800 group-hover:text-[#5A5A40] transition-colors mt-2.5 line-clamp-1">
                    {eng.clientName}
                  </h3>
                  <div className="text-[11px] text-stone-500 font-medium flex items-center gap-2 mt-0.5">
                    <span>{auditType?.name}</span>
                    <span>•</span>
                    <span className="font-semibold text-stone-700">{eng.financialYear}</span>
                  </div>

                  {eng.branchLocation && (
                    <div className="flex items-center gap-1 text-[11px] text-slate-500 mt-2 truncate">
                      <MapPin className="w-3 h-3 text-slate-400 shrink-0" />
                      <span className="truncate">{eng.branchLocation}</span>
                    </div>
                  )}

                  <div className="flex items-center gap-1 text-[11px] text-slate-500 mt-1">
                    <UserCheck className="w-3 h-3 text-slate-400 shrink-0" />
                    <span className="truncate">Partner: {eng.engagementPartner}</span>
                  </div>
                </div>

                {/* Bottom stats & action */}
                <div className="mt-4 pt-3 border-t border-slate-100 space-y-3">
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="p-1.5 bg-slate-50 rounded-lg">
                      <span className="text-[10px] text-slate-500 font-medium block">Obs</span>
                      <span className="text-xs font-bold text-slate-900">{engObs.length}</span>
                    </div>
                    <div className="p-1.5 bg-rose-50/60 rounded-lg">
                      <span className="text-[10px] text-rose-700 font-medium block">Open</span>
                      <span className="text-xs font-bold text-rose-700">{openObsCount}</span>
                    </div>
                    <div className="p-1.5 bg-amber-50/60 rounded-lg">
                      <span className="text-[10px] text-amber-800 font-medium block">Exposure</span>
                      <span className="text-[11px] font-bold text-slate-900 truncate block">
                        {totalImpact > 0 ? formatINR(totalImpact) : '₹0'}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onAddObservationForEngagement(eng.id);
                      }}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-800 hover:text-slate-950 hover:underline"
                    >
                      <PlusCircle className="w-3.5 h-3.5 text-amber-500" />
                      <span>+ Log Finding</span>
                    </button>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          ExportService.exportEngagementReportPDF(eng, engObs, auditType, firmProfile);
                        }}
                        className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors"
                        title="Download PDF Audit Report"
                      >
                        <FileDown className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onEditEngagement(eng);
                        }}
                        className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors"
                        title="Edit Engagement"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={(e) => handleDeleteConfirm(e, eng)}
                        className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors"
                        title="Delete Engagement"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Client & Code</th>
                  <th className="py-3 px-4">Audit Type</th>
                  <th className="py-3 px-4">FY / Period</th>
                  <th className="py-3 px-4">Partner & Team</th>
                  <th className="py-3 px-4">Timeline</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Obs / Open</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {filteredEngagements.map((eng) => {
                  const auditType = auditTypeMap.get(eng.auditTypeId);
                  const statusStyle = getEngagementStatusBadgeClass(eng.overallStatus);
                  const engObs = obsList.filter(o => o.engagementId === eng.id);
                  const openCount = engObs.filter(o => o.status !== 'Closed' && o.status !== 'Rectified').length;

                  return (
                    <tr 
                      key={eng.id}
                      onClick={() => onViewEngagement(eng)}
                      className="hover:bg-slate-50/80 transition-colors cursor-pointer"
                    >
                      <td className="py-3.5 px-4">
                        <div className="font-bold text-slate-900">{eng.clientName}</div>
                        <div className="text-[11px] font-mono text-slate-500">{eng.id} ({eng.clientCode})</div>
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded-md bg-slate-900 text-amber-400 font-bold text-[10px] mr-1.5">
                          {auditType?.code}
                        </span>
                        <span className="text-slate-700 font-medium">{auditType?.name}</span>
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap font-semibold text-slate-800">
                        {eng.financialYear}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-medium text-slate-800">{eng.engagementPartner}</div>
                        <div className="text-[11px] text-slate-500 truncate max-w-[150px]">{eng.teamMembers.join(', ')}</div>
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-600">
                        {formatDate(eng.startDate)} - {formatDate(eng.endDate)}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${statusStyle.bg} ${statusStyle.text} ${statusStyle.border}`}>
                          {eng.overallStatus}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className="font-bold text-slate-900">{engObs.length}</span>
                        {openCount > 0 && (
                          <span className="ml-1 text-[11px] font-semibold text-rose-600">({openCount} open)</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap text-right space-x-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onAddObservationForEngagement(eng.id);
                          }}
                          className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors"
                          title="Add Observation"
                        >
                          <PlusCircle className="w-4 h-4 text-amber-500" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            ExportService.exportEngagementReportPDF(eng, engObs, auditType, firmProfile);
                          }}
                          className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors"
                          title="Export PDF"
                        >
                          <FileDown className="w-4 h-4 text-rose-600" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onEditEngagement(eng);
                          }}
                          className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors"
                          title="Edit"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => handleDeleteConfirm(e, eng)}
                          className="p-1.5 text-slate-600 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Bulk Upload Modal */}
      {onImportEngagements && (
        <BulkEngagementUploadModal
          isOpen={isBulkModalOpen}
          onClose={() => setIsBulkModalOpen(false)}
          auditTypes={typeList}
          firmProfile={firmProfile}
          onImportEngagements={onImportEngagements}
        />
      )}
    </div>
  );
};
