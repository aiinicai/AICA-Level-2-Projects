import React, { useState } from 'react';
import { 
  X, 
  Briefcase, 
  FileText, 
  FileDown, 
  PlusCircle, 
  Edit3, 
  Calendar, 
  MapPin, 
  Users, 
  UserCheck, 
  IndianRupee, 
  ShieldAlert,
  CheckCircle2,
  Building,
  FileSpreadsheet
} from 'lucide-react';
import { Engagement, Observation, AuditType, FirmProfile } from '../../types/audit';
import { 
  formatDate, 
  formatINR, 
  getEngagementStatusBadgeClass, 
  getSeverityBadgeClass, 
  getStatusBadgeClass 
} from '../../utils/formatters';
import { ExportService } from '../../services/exportService';

interface EngagementDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  engagement: Engagement | null;
  observations?: Observation[];
  auditTypes?: AuditType[];
  auditType?: AuditType;
  firmProfile: FirmProfile;
  onEditEngagement: (eng: Engagement) => void;
  onAddObservationForEngagement?: (engId: string) => void;
  onAddObservation?: (engId: string) => void;
  onViewObservation: (obs: Observation) => void;
  onEditObservation: (obs: Observation) => void;
  onDeleteObservation?: (obsId: string) => void;
}

export const EngagementDetailModal: React.FC<EngagementDetailModalProps> = ({
  isOpen,
  onClose,
  engagement,
  observations = [],
  auditTypes = [],
  auditType: propAuditType,
  firmProfile,
  onEditEngagement,
  onAddObservationForEngagement,
  onAddObservation,
  onViewObservation,
  onEditObservation,
  onDeleteObservation,
}) => {
  const [activeTab, setActiveTab] = useState<'observations' | 'overview'>('observations');

  if (!isOpen || !engagement) return null;

  const auditType = propAuditType || (auditTypes ? auditTypes.find(at => at.id === engagement.auditTypeId) : undefined);
  const statusStyle = getEngagementStatusBadgeClass(engagement.overallStatus);
  const handleAddObservation = onAddObservationForEngagement || onAddObservation || (() => {});

  const obsList = observations || [];
  const totalObs = obsList.length;
  const closedObs = obsList.filter(o => o.status === 'Closed' || o.status === 'Rectified').length;
  const openObs = totalObs - closedObs;
  const criticalCount = obsList.filter(o => o.severity === 'Critical').length;
  const highCount = obsList.filter(o => o.severity === 'High').length;
  const totalExposure = obsList.reduce((acc, o) => acc + (o.financialImpact || 0), 0);

  return (
    <div id="engagement-detail-modal-overlay" className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6">
      <div className="bg-white rounded-2xl max-w-4xl w-full shadow-2xl border border-stone-200 overflow-hidden transform transition-all">
        {/* Header */}
        <div className="px-6 py-5 bg-[#5A5A40] text-white flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-md bg-amber-300 text-stone-900 font-mono font-bold text-xs">
                {auditType?.code || 'AUD'}
              </span>
              <span className="text-xs text-stone-200 font-mono font-semibold">
                {engagement.id} • {engagement.financialYear}
              </span>
              <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${statusStyle.bg} ${statusStyle.text} ${statusStyle.border}`}>
                {engagement.overallStatus}
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold tracking-tight text-white">
              {engagement.clientName}
            </h2>
            {engagement.clientPanGstin && (
              <p className="text-xs text-stone-200 font-mono">
                PAN/GSTIN: {engagement.clientPanGstin}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-stone-300 hover:text-white hover:bg-black/20 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Action Toolbar */}
        <div className="px-6 py-3 bg-[#F5F2ED] border-b border-stone-200 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-1 bg-stone-200/70 p-1 rounded-lg">
            <button
              onClick={() => setActiveTab('observations')}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
                activeTab === 'observations'
                  ? 'bg-white text-stone-900 shadow-xs'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Observations ({totalObs})
            </button>
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
                activeTab === 'overview'
                  ? 'bg-white text-stone-900 shadow-xs'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Assignment Details
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => ExportService.exportEngagementReportPDF(engagement, observations, auditType, firmProfile)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white border border-stone-300 hover:bg-stone-50 text-stone-700 text-xs font-semibold transition-colors shadow-2xs"
              title="Download Full Audit Memorandum as PDF"
            >
              <FileDown className="w-3.5 h-3.5 text-stone-700" />
              <span>PDF Report</span>
            </button>

            <button
              onClick={() => ExportService.exportEngagementReportDocx(engagement, observations, auditType, firmProfile)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white border border-stone-300 hover:bg-stone-50 text-stone-700 text-xs font-semibold transition-colors shadow-2xs"
              title="Download Word Report (.docx)"
            >
              <FileText className="w-3.5 h-3.5 text-stone-700" />
              <span>Word Report</span>
            </button>

            <button
              onClick={() => ExportService.exportObservationsToExcel(observations, [engagement], auditTypes, `Engagement_${engagement.clientCode}`)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white border border-stone-300 hover:bg-stone-50 text-stone-700 text-xs font-semibold transition-colors shadow-2xs"
              title="Export Observations to Excel"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-[#5A5A40]" />
              <span>Excel</span>
            </button>

            <button
              onClick={() => handleAddObservation(engagement.id)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#5A5A40] hover:bg-[#4A4A34] text-white text-xs font-semibold shadow-xs transition-colors"
            >
              <PlusCircle className="w-3.5 h-3.5 text-amber-300" />
              <span>+ Log Finding</span>
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 max-h-[65vh] overflow-y-auto space-y-6">
          {/* Quick Metrics Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-stone-50 rounded-xl border border-stone-200">
              <span className="text-[11px] font-bold text-stone-500 uppercase">Observations</span>
              <div className="text-lg font-bold text-stone-900 mt-0.5">
                {totalObs} <span className="text-xs font-medium text-stone-500">({openObs} open)</span>
              </div>
            </div>

            <div className="p-3 bg-rose-50/50 rounded-xl border border-rose-100">
              <span className="text-[11px] font-bold text-rose-700 uppercase">High/Critical Risk</span>
              <div className="text-lg font-bold text-rose-700 mt-0.5">
                {criticalCount + highCount}
              </div>
            </div>

            <div className="p-3 bg-amber-50/50 rounded-xl border border-amber-100">
              <span className="text-[11px] font-bold text-amber-800 uppercase">Financial Exposure</span>
              <div className="text-lg font-bold text-stone-900 mt-0.5 truncate">
                {formatINR(totalExposure)}
              </div>
            </div>

            <div className="p-3 bg-teal-50/50 rounded-xl border border-teal-100">
              <span className="text-[11px] font-bold text-teal-800 uppercase">Rectified / Closed</span>
              <div className="text-lg font-bold text-teal-700 mt-0.5">
                {closedObs}
              </div>
            </div>
          </div>

          {activeTab === 'observations' ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-stone-900">
                  Observation Log for this Assignment ({obsList.length})
                </h3>
              </div>

              {obsList.length === 0 ? (
                <div className="p-8 text-center bg-stone-50 rounded-xl border border-stone-200">
                  <FileText className="w-8 h-8 text-stone-400 mx-auto mb-2" />
                  <p className="text-sm font-semibold text-stone-700">No observations logged yet</p>
                  <p className="text-xs text-stone-500 mt-1">
                    Click "+ Log Finding" above to record the first observation for this engagement.
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-stone-100 border border-stone-200 rounded-xl overflow-hidden bg-white shadow-2xs">
                  {obsList.map((obs) => {
                    const sevStyle = getSeverityBadgeClass(obs.severity);
                    const statStyle = getStatusBadgeClass(obs.status);

                    return (
                      <div
                        key={obs.id}
                        className="p-4 hover:bg-slate-50/80 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                      >
                        <div className="space-y-1 max-w-xl">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono font-bold text-xs text-slate-900">
                              {obs.referenceNo}
                            </span>
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${sevStyle.bg} ${sevStyle.text} ${sevStyle.border}`}>
                              {obs.severity}
                            </span>
                            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-md border ${statStyle.bg} ${statStyle.text} ${statStyle.border}`}>
                              {obs.status}
                            </span>
                            {obs.financialImpact && obs.financialImpact > 0 && (
                              <span className="text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-md">
                                {formatINR(obs.financialImpact)}
                              </span>
                            )}
                          </div>
                          <h4 className="text-xs font-bold text-slate-900">{obs.areaProcess}</h4>
                          <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                            {obs.description}
                          </p>
                        </div>

                        <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-center">
                          <button
                            onClick={() => onViewObservation(obs)}
                            className="px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100 text-xs font-semibold transition-colors"
                          >
                            View
                          </button>
                          <button
                            onClick={() => onEditObservation(obs)}
                            className="px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100 text-xs font-semibold transition-colors"
                          >
                            Edit
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                  <div className="text-[11px] font-bold text-slate-500 uppercase flex items-center gap-1.5">
                    <Building className="w-3.5 h-3.5" /> Client & Audit Profile
                  </div>
                  <div className="space-y-1">
                    <p><strong className="text-slate-900">Audit Type:</strong> {auditType?.name} ({auditType?.code})</p>
                    <p><strong className="text-slate-900">Period / FY:</strong> {engagement.financialYear}</p>
                    <p><strong className="text-slate-900">Location:</strong> {engagement.branchLocation || 'Head Office'}</p>
                    <p><strong className="text-slate-900">Timeline:</strong> {formatDate(engagement.startDate)} to {formatDate(engagement.endDate)}</p>
                  </div>
                </div>

                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                  <div className="text-[11px] font-bold text-slate-500 uppercase flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5" /> Audit Team & Governance
                  </div>
                  <div className="space-y-1">
                    <p><strong className="text-slate-900">Engagement Partner:</strong> {engagement.engagementPartner}</p>
                    <p><strong className="text-slate-900">Team Members:</strong> {engagement.teamMembers.join(', ') || 'Assigned Staff'}</p>
                    <p><strong className="text-slate-900">Created On:</strong> {formatDate(engagement.createdAt)}</p>
                    <p><strong className="text-slate-900">Last Modified:</strong> {formatDate(engagement.updatedAt)}</p>
                  </div>
                </div>
              </div>

              {engagement.notes && (
                <div className="p-4 bg-amber-50/50 rounded-xl border border-amber-200/70 space-y-1">
                  <div className="text-[11px] font-bold text-amber-900 uppercase">Scope & Engagement Notes</div>
                  <p className="text-amber-900 leading-relaxed">{engagement.notes}</p>
                </div>
              )}

              <div className="pt-3 flex justify-end">
                <button
                  onClick={() => onEditEngagement(engagement)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 font-semibold text-xs transition-colors"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>Edit Engagement Master Details</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
