import React from 'react';
import { 
  X, 
  FileText, 
  FileDown, 
  Edit3, 
  Printer, 
  IndianRupee, 
  Calendar, 
  UserCheck, 
  Building, 
  AlertTriangle, 
  CheckCircle2, 
  MessageSquare, 
  Clock, 
  Paperclip,
  ShieldCheck
} from 'lucide-react';
import { Observation, Engagement, AuditType, FirmProfile } from '../../types/audit';
import { 
  formatDate, 
  formatINR, 
  getSeverityBadgeClass, 
  getStatusBadgeClass, 
  getRectificationBadgeClass 
} from '../../utils/formatters';
import { ExportService } from '../../services/exportService';

interface ObservationDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  observation: Observation | null;
  engagement: Engagement | undefined;
  auditType: AuditType | undefined;
  firmProfile: FirmProfile;
  onEditObservation: (obs: Observation) => void;
  onQuickUpdateStatus: (obsId: string, newStatus: any) => void;
}

export const ObservationDetailModal: React.FC<ObservationDetailModalProps> = ({
  isOpen,
  onClose,
  observation,
  engagement,
  auditType,
  firmProfile,
  onEditObservation,
  onQuickUpdateStatus,
}) => {
  if (!isOpen || !observation) return null;

  const sevStyle = getSeverityBadgeClass(observation.severity);
  const statStyle = getStatusBadgeClass(observation.status);
  const rectStyle = getRectificationBadgeClass(observation.rectificationStatus);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div id="observation-detail-modal-overlay" className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 print:p-0 print:bg-white">
      <div className="bg-white rounded-2xl max-w-3xl w-full shadow-2xl border border-stone-200 overflow-hidden transform transition-all print:border-none print:shadow-none">
        {/* Top Control Bar (Hidden on print) */}
        <div className="px-6 py-3.5 bg-[#5A5A40] text-white flex items-center justify-between print:hidden">
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-amber-300 text-xs bg-black/20 px-2.5 py-1 rounded-md">
              {observation.referenceNo}
            </span>
            <span className="text-xs text-stone-200">Observation Memo</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (engagement) {
                  ExportService.exportSingleObservationPDF(observation, engagement, auditType, firmProfile);
                }
              }}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white/15 hover:bg-white/25 text-xs font-semibold text-white transition-colors"
              title="Download Formatted PDF"
            >
              <FileDown className="w-3.5 h-3.5 text-stone-200" />
              <span>PDF</span>
            </button>

            <button
              onClick={() => {
                if (engagement) {
                  ExportService.exportSingleObservationDocx(observation, engagement, auditType, firmProfile);
                }
              }}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white/15 hover:bg-white/25 text-xs font-semibold text-white transition-colors"
              title="Download Word Document (.docx)"
            >
              <FileText className="w-3.5 h-3.5 text-stone-200" />
              <span>Word</span>
            </button>

            <button
              onClick={handlePrint}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white/15 hover:bg-white/25 text-xs font-semibold text-white transition-colors"
              title="Print Memo"
            >
              <Printer className="w-3.5 h-3.5 text-stone-200" />
              <span>Print</span>
            </button>

            <button
              onClick={() => onEditObservation(observation)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-amber-300 hover:bg-amber-400 text-xs font-bold text-stone-900 transition-colors ml-1"
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>Edit</span>
            </button>

            <button
              onClick={onClose}
              className="p-1 rounded-lg text-stone-300 hover:text-white hover:bg-black/20 transition-colors ml-1"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body / Letterhead Document */}
        <div className="p-6 sm:p-8 space-y-6 max-h-[82vh] overflow-y-auto print:max-h-none print:overflow-visible">
          {/* CA Firm Letterhead Header */}
          <div className="text-center pb-4 border-b border-slate-200 space-y-1">
            <h1 className="text-lg font-bold text-slate-900 tracking-tight uppercase">
              {firmProfile.firmName}
            </h1>
            <p className="text-xs font-semibold text-slate-600">
              Chartered Accountants • FRN: {firmProfile.frn}
            </p>
            <p className="text-[11px] text-slate-500">
              {firmProfile.address}, {firmProfile.city} • Email: {firmProfile.email} • Ph: {firmProfile.phone}
            </p>
          </div>

          {/* Document Title & Reference Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Audit Finding Record</div>
              <div className="font-mono text-base font-bold text-slate-900 mt-0.5">
                {observation.referenceNo}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold border ${sevStyle.bg} ${sevStyle.text} ${sevStyle.border}`}>
                <span className={`w-2 h-2 rounded-full ${sevStyle.dot}`}></span>
                {observation.severity} Risk
              </span>

              <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold border ${statStyle.bg} ${statStyle.text} ${statStyle.border}`}>
                Status: {observation.status}
              </span>

              {observation.financialImpact && observation.financialImpact > 0 ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold bg-rose-50 text-rose-800 border border-rose-200">
                  Exposure: {formatINR(observation.financialImpact)}
                </span>
              ) : null}
            </div>
          </div>

          {/* Assignment Overview Table */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
              <div className="font-bold text-slate-900 flex items-center gap-1.5 text-xs">
                <Building className="w-3.5 h-3.5 text-slate-500" /> Client Details
              </div>
              <p><strong className="text-slate-700">Client:</strong> {engagement?.clientName || 'N/A'}</p>
              <p><strong className="text-slate-700">PAN / GSTIN:</strong> {engagement?.clientPanGstin || 'N/A'}</p>
              <p><strong className="text-slate-700">Audit Type:</strong> {auditType?.name} ({auditType?.code})</p>
              <p><strong className="text-slate-700">Financial Year:</strong> {engagement?.financialYear}</p>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
              <div className="font-bold text-slate-900 flex items-center gap-1.5 text-xs">
                <Calendar className="w-3.5 h-3.5 text-slate-500" /> Audit Timeline & Ownership
              </div>
              <p><strong className="text-slate-700">Observation Date:</strong> {formatDate(observation.dateOfObservation)}</p>
              <p><strong className="text-slate-700">Engagement Partner:</strong> {engagement?.engagementPartner}</p>
              <p><strong className="text-slate-700">Auditor Responsible:</strong> {observation.personResponsible}</p>
              <p><strong className="text-slate-700">Location:</strong> {engagement?.branchLocation || 'Head Office'}</p>
            </div>
          </div>

          {/* Area & Finding */}
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                Audited Area / Process
              </div>
              <div className="text-sm font-bold text-slate-900">{observation.areaProcess}</div>
            </div>

            <div className="space-y-1.5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Observation Finding & Discrepancy
              </h3>
              <div className="p-4 rounded-xl border border-slate-200 bg-white text-slate-800 text-xs sm:text-sm leading-relaxed whitespace-pre-wrap">
                {observation.description}
              </div>
            </div>

            {observation.rootCause && (
              <div className="space-y-1.5">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Root Cause / Deficiency Analysis
                </h3>
                <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-700 text-xs leading-relaxed">
                  {observation.rootCause}
                </div>
              </div>
            )}

            {observation.recommendation && (
              <div className="space-y-1.5">
                <h3 className="text-xs font-bold uppercase tracking-wider text-amber-900">
                  Audit Recommendation & Corrective Action
                </h3>
                <div className="p-3.5 rounded-xl border border-amber-200 bg-amber-50/60 text-amber-950 text-xs font-medium leading-relaxed">
                  {observation.recommendation}
                </div>
              </div>
            )}
          </div>

          {/* Management Discussion & Response Section */}
          <div className="p-4 rounded-xl bg-blue-50/50 border border-blue-200/70 space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-xs font-bold text-blue-900 uppercase flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-blue-700" /> Client Management Discussion
              </div>
              {observation.dateOfDiscussion && (
                <span className="text-[11px] font-semibold text-blue-800">
                  Discussed on: {formatDate(observation.dateOfDiscussion)}
                </span>
              )}
            </div>

            <div className="text-xs space-y-1 text-blue-950">
              <p>
                <strong>Stakeholder(s) Discussed with:</strong>{' '}
                {observation.discussionStakeholder || 'Fieldwork personnel'}
              </p>
            </div>

            <div className="p-3 bg-white rounded-lg border border-blue-200 text-xs text-slate-800 leading-relaxed">
              <div className="font-bold text-slate-900 mb-1 text-[11px] uppercase">Management Response:</div>
              {observation.managementResponse || 'Awaiting formal management comments.'}
            </div>

            {/* Rectification timeline */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs pt-1">
              <div className="flex items-center gap-2">
                <span className="text-slate-600 font-medium">Rectification Status:</span>
                <span className={`px-2 py-0.5 rounded-md font-bold text-[11px] ${rectStyle.bg} ${rectStyle.text}`}>
                  {observation.rectificationStatus}
                </span>
              </div>
              <div className="text-slate-600">
                <span>Target Date: <strong>{formatDate(observation.targetRectificationDate)}</strong></span>
                {observation.actualRectificationDate && (
                  <span className="ml-2">| Actual: <strong className="text-emerald-700">{formatDate(observation.actualRectificationDate)}</strong></span>
                )}
              </div>
            </div>
          </div>

          {/* Supporting & Remarks */}
          {(observation.attachments || observation.remarks) && (
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
              {observation.attachments && (
                <div className="flex items-start gap-2">
                  <Paperclip className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
                  <div>
                    <strong className="text-slate-700">Supporting Attachments / Papers:</strong>
                    <p className="text-slate-600 mt-0.5">{observation.attachments}</p>
                  </div>
                </div>
              )}
              {observation.remarks && (
                <div className="pt-1 border-t border-slate-200/60">
                  <strong className="text-slate-700">Internal Audit Remarks:</strong> {observation.remarks}
                </div>
              )}
            </div>
          )}

          {/* Sign-off footer block */}
          <div className="pt-6 border-t border-slate-200 grid grid-cols-2 gap-6 text-xs text-slate-700">
            <div>
              <p className="font-medium text-slate-500">For {firmProfile?.firmName || 'R. K. Garg & Associates'}</p>
              <p className="font-medium text-slate-500">Chartered Accountants</p>
              <div className="mt-8">
                <p className="font-bold text-slate-900">({firmProfile?.partnerName || 'CA Ritesh Garg, FCA'})</p>
                <p className="text-[11px] text-slate-500">Partner • M. No. {firmProfile?.membershipNo || '098765'}</p>
              </div>
            </div>

            <div className="text-right">
              <p className="font-medium text-slate-500">Client Acknowledgement</p>
              <p className="font-medium text-slate-500">{engagement?.clientName}</p>
              <div className="mt-8">
                <p className="font-bold text-slate-900">
                  ({observation.discussionStakeholder ? observation.discussionStakeholder.split(',')[0] : 'Authorized Signatory'})
                </p>
                <p className="text-[11px] text-slate-500">Management Representative</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
