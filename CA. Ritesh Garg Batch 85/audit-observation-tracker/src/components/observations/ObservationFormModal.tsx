import React, { useState, useEffect } from 'react';
import { 
  X, 
  FileText, 
  AlertOctagon, 
  IndianRupee, 
  Calendar, 
  User, 
  CheckCircle2, 
  Paperclip, 
  MessageSquare, 
  ShieldAlert,
  Sparkles,
  HelpCircle
} from 'lucide-react';
import { 
  Observation, 
  Engagement, 
  AuditType, 
  SeverityLevel, 
  ObservationStatus, 
  RectificationStatus 
} from '../../types/audit';
import { storageService } from '../../services/storage';

interface ObservationFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (obsData: Partial<Observation> & { engagementId: string; description: string; severity: SeverityLevel; status: ObservationStatus }) => void;
  observationToEdit?: Observation | null;
  engagements: Engagement[];
  auditTypes: AuditType[];
  preselectedEngagementId?: string;
}

const COMMON_AREA_SUGGESTIONS = [
  'Inventory Valuation & Physical Verification',
  'Sec 43B(h) MSME Overdue Payments',
  'GST Input Tax Credit (GSTR-2B vs 3B)',
  'Fixed Asset Register & Capitalization (Ind AS 16)',
  'Cash & Bank Reconciliation & Negative Balances',
  'TDS / TCS Compliance & Late Deposit (Sec 194C/194Q)',
  'Expired Loan Limits & DP Irregularities',
  'Insurance Under-Coverage & Bank Hypothecation',
  'Revenue Recognition Cut-off & Invoicing',
  'Statutory Dues & PF / ESI Timely Remittance',
  'KYC / AML Documentation Deficiencies',
  'Internal Financial Controls (IFCoFR) Weakness',
];

export const ObservationFormModal: React.FC<ObservationFormModalProps> = ({
  isOpen,
  onClose,
  onSave,
  observationToEdit,
  engagements,
  auditTypes,
  preselectedEngagementId,
}) => {
  const [engagementId, setEngagementId] = useState('');
  const [referenceNo, setReferenceNo] = useState('');
  const [dateOfObservation, setDateOfObservation] = useState(new Date().toISOString().split('T')[0]);
  const [areaProcess, setAreaProcess] = useState('');
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState<SeverityLevel>('Medium');
  const [financialImpact, setFinancialImpact] = useState<string>('');
  const [rootCause, setRootCause] = useState('');
  const [recommendation, setRecommendation] = useState('');
  const [discussionStakeholder, setDiscussionStakeholder] = useState('');
  const [dateOfDiscussion, setDateOfDiscussion] = useState('');
  const [managementResponse, setManagementResponse] = useState('');
  const [status, setStatus] = useState<ObservationStatus>('Open');
  const [rectificationStatus, setRectificationStatus] = useState<RectificationStatus>('Not Started');
  const [targetRectificationDate, setTargetRectificationDate] = useState('');
  const [actualRectificationDate, setActualRectificationDate] = useState('');
  const [personResponsible, setPersonResponsible] = useState('');
  const [attachments, setAttachments] = useState('');
  const [remarks, setRemarks] = useState('');

  const [errors, setErrors] = useState<{ [key: string]: string }>({});

  // Initialize form state
  useEffect(() => {
    if (observationToEdit) {
      setEngagementId(observationToEdit.engagementId);
      setReferenceNo(observationToEdit.referenceNo);
      setDateOfObservation(observationToEdit.dateOfObservation);
      setAreaProcess(observationToEdit.areaProcess);
      setDescription(observationToEdit.description);
      setSeverity(observationToEdit.severity);
      setFinancialImpact(observationToEdit.financialImpact !== undefined ? String(observationToEdit.financialImpact) : '');
      setRootCause(observationToEdit.rootCause || '');
      setRecommendation(observationToEdit.recommendation || '');
      setDiscussionStakeholder(observationToEdit.discussionStakeholder || '');
      setDateOfDiscussion(observationToEdit.dateOfDiscussion || '');
      setManagementResponse(observationToEdit.managementResponse || '');
      setStatus(observationToEdit.status);
      setRectificationStatus(observationToEdit.rectificationStatus);
      setTargetRectificationDate(observationToEdit.targetRectificationDate || '');
      setActualRectificationDate(observationToEdit.actualRectificationDate || '');
      setPersonResponsible(observationToEdit.personResponsible || '');
      setAttachments(observationToEdit.attachments || '');
      setRemarks(observationToEdit.remarks || '');
    } else {
      const defaultEngId = preselectedEngagementId || engagements[0]?.id || '';
      setEngagementId(defaultEngId);
      setDateOfObservation(new Date().toISOString().split('T')[0]);
      setAreaProcess('');
      setDescription('');
      setSeverity('Medium');
      setFinancialImpact('');
      setRootCause('');
      setRecommendation('');
      setDiscussionStakeholder('');
      setDateOfDiscussion('');
      setManagementResponse('');
      setStatus('Open');
      setRectificationStatus('Not Started');
      setTargetRectificationDate('');
      setActualRectificationDate('');
      setAttachments('');
      setRemarks('');

      if (defaultEngId) {
        const eng = engagements.find(e => e.id === defaultEngId);
        setPersonResponsible(eng?.teamMembers[0] || eng?.engagementPartner || 'Audit Team Senior');
        setReferenceNo(storageService.generateObservationRefNo(defaultEngId));
      } else {
        setPersonResponsible('Audit Team Senior');
        setReferenceNo('');
      }
    }
    setErrors({});
  }, [observationToEdit, isOpen, preselectedEngagementId, engagements]);

  // Update auto Reference No when changing engagement in create mode
  const handleEngagementChange = (newEngId: string) => {
    setEngagementId(newEngId);
    if (!observationToEdit && newEngId) {
      const eng = engagements.find(e => e.id === newEngId);
      if (eng) {
        setPersonResponsible(eng.teamMembers[0] || eng.engagementPartner || 'Audit Senior');
      }
      setReferenceNo(storageService.generateObservationRefNo(newEngId));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: { [key: string]: string } = {};

    if (!engagementId) {
      newErrors.engagementId = 'Please select a linked Engagement';
    }
    if (!description.trim()) {
      newErrors.description = 'Observation description is mandatory';
    }
    if (!areaProcess.trim()) {
      newErrors.areaProcess = 'Area / Process is mandatory';
    }
    if (!personResponsible.trim()) {
      newErrors.personResponsible = 'Person responsible is required';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    onSave({
      id: observationToEdit?.id,
      referenceNo: observationToEdit ? observationToEdit.referenceNo : referenceNo,
      engagementId,
      dateOfObservation,
      areaProcess: areaProcess.trim(),
      description: description.trim(),
      severity,
      financialImpact: financialImpact.trim() !== '' ? Number(financialImpact.replace(/[^0-9.]/g, '')) : undefined,
      rootCause: rootCause.trim() || undefined,
      recommendation: recommendation.trim() || undefined,
      discussionStakeholder: discussionStakeholder.trim() || undefined,
      dateOfDiscussion: dateOfDiscussion || undefined,
      managementResponse: managementResponse.trim() || undefined,
      status,
      rectificationStatus,
      targetRectificationDate: targetRectificationDate || undefined,
      actualRectificationDate: actualRectificationDate || undefined,
      personResponsible: personResponsible.trim(),
      attachments: attachments.trim() || undefined,
      remarks: remarks.trim() || undefined,
    });

    onClose();
  };

  if (!isOpen) return null;

  const selectedEngagement = engagements.find(e => e.id === engagementId);
  const selectedAuditType = selectedEngagement ? auditTypes.find(at => at.id === selectedEngagement.auditTypeId) : null;

  return (
    <div id="observation-form-modal-overlay" className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6">
      <div className="bg-white rounded-2xl max-w-3xl w-full shadow-2xl border border-stone-200 overflow-hidden transform transition-all">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-[#5A5A40] text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-white/10 text-amber-300 flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold leading-tight">
                {observationToEdit ? 'Edit Audit Observation' : 'Log New Audit Observation'}
              </h2>
              <div className="flex items-center gap-2 mt-0.5 text-xs text-stone-200">
                <span className="font-mono bg-black/20 px-2 py-0.5 rounded text-amber-300 font-bold">
                  {observationToEdit ? observationToEdit.referenceNo : referenceNo || 'Ref: Auto-Generated'}
                </span>
                <span>• Non-editable reference</span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-stone-300 hover:text-white hover:bg-black/20 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6 max-h-[82vh] overflow-y-auto">
          {/* SECTION 1: Audit Assignment & Context */}
          <div className="space-y-3.5 pb-4 border-b border-slate-200">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <span>1. Assignment & Reference Context</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="sm:col-span-2 space-y-1.5">
                <label className="text-xs font-bold text-slate-700 flex items-center gap-1">
                  Linked Audit Engagement <span className="text-rose-600">*</span>
                </label>
                <select
                  value={engagementId}
                  disabled={!!observationToEdit || engagements.length === 0}
                  onChange={(e) => handleEngagementChange(e.target.value)}
                  className={`w-full px-3.5 py-2 text-sm rounded-lg border bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10 ${
                    errors.engagementId ? 'border-rose-400 bg-rose-50/20' : 'border-slate-300'
                  }`}
                >
                  {engagements.length === 0 ? (
                    <option value="">-- No Audit Engagements Available (Create Client First) --</option>
                  ) : (
                    engagements.map((eng) => (
                      <option key={eng.id} value={eng.id}>
                        {eng.clientName} ({eng.financialYear}) — {eng.clientCode}
                      </option>
                    ))
                  )}
                </select>
                {errors.engagementId && (
                  <p className="text-[11px] text-rose-600 font-medium">{errors.engagementId}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Date of Observation</label>
                <input
                  type="date"
                  value={dateOfObservation}
                  onChange={(e) => setDateOfObservation(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
                />
              </div>
            </div>

            {/* Area / Process with suggestions */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 flex items-center justify-between">
                <span>Area / Process Audited <span className="text-rose-600">*</span></span>
                <span className="text-[11px] text-slate-400 font-normal">Click a standard chip below or type custom</span>
              </label>
              <input
                type="text"
                value={areaProcess}
                onChange={(e) => setAreaProcess(e.target.value)}
                placeholder="e.g. Inventory Valuation, Sec 43B(h) MSME, GST ITC Reconciliation"
                className={`w-full px-3.5 py-2 text-sm rounded-lg border bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10 ${
                  errors.areaProcess ? 'border-rose-400 bg-rose-50/20' : 'border-slate-300'
                }`}
              />
              {errors.areaProcess && (
                <p className="text-[11px] text-rose-600 font-medium">{errors.areaProcess}</p>
              )}

              {/* Quick Area Chips */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {COMMON_AREA_SUGGESTIONS.slice(0, 6).map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => setAreaProcess(chip)}
                    className="text-[11px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200 transition-colors"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* SECTION 2: Finding, Severity & Exposure */}
          <div className="space-y-3.5 pb-4 border-b border-slate-200">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <span>2. Finding, Risk Severity & Financial Exposure</span>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 flex items-center gap-1">
                Observation Description & Discrepancy <span className="text-rose-600">*</span>
              </label>
              <textarea
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Detail the specific audit finding, non-compliance with law/standard/sanction terms, quantity or value discrepancies..."
                className={`w-full px-3.5 py-2 text-sm rounded-lg border bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10 ${
                  errors.description ? 'border-rose-400 bg-rose-50/20' : 'border-slate-300'
                }`}
              />
              {errors.description && (
                <p className="text-[11px] text-rose-600 font-medium">{errors.description}</p>
              )}
            </div>

            {/* Severity Level Selector */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Risk / Severity Level</label>
                <div className="grid grid-cols-4 gap-1.5">
                  {(['Critical', 'High', 'Medium', 'Low'] as SeverityLevel[]).map((level) => {
                    const isSelected = severity === level;
                    const colors = {
                      Critical: isSelected ? 'bg-rose-600 text-white border-rose-600 shadow-xs' : 'bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100',
                      High: isSelected ? 'bg-amber-600 text-white border-amber-600 shadow-xs' : 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100',
                      Medium: isSelected ? 'bg-yellow-500 text-white border-yellow-500 shadow-xs' : 'bg-yellow-50 text-yellow-800 border-yellow-200 hover:bg-yellow-100',
                      Low: isSelected ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs' : 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100',
                    };
                    return (
                      <button
                        key={level}
                        type="button"
                        onClick={() => setSeverity(level)}
                        className={`py-1.5 text-xs font-bold rounded-lg border transition-all text-center ${colors[level]}`}
                      >
                        {level}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Financial Impact / Amount Involved (₹)</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-slate-400 text-sm font-bold">
                    ₹
                  </span>
                  <input
                    type="number"
                    value={financialImpact}
                    onChange={(e) => setFinancialImpact(e.target.value)}
                    placeholder="e.g. 3850000"
                    className="w-full pl-8 pr-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10 font-medium"
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Root Cause / Deficiency Analysis</label>
                <input
                  type="text"
                  value={rootCause}
                  onChange={(e) => setRootCause(e.target.value)}
                  placeholder="e.g. Lack of automated ERP alerts, manual delay in TOC..."
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Audit Recommendation</label>
                <input
                  type="text"
                  value={recommendation}
                  onChange={(e) => setRecommendation(e.target.value)}
                  placeholder="e.g. Segregate non-moving inventory; clear overdue MSME dues..."
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
                />
              </div>
            </div>
          </div>

          {/* SECTION 3: Client Discussion & Management Response */}
          <div className="space-y-3.5 pb-4 border-b border-slate-200">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <span>3. Management Discussion & Status Lifecycle</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Discussion Stakeholder(s) Name & Designation</label>
                <input
                  type="text"
                  value={discussionStakeholder}
                  onChange={(e) => setDiscussionStakeholder(e.target.value)}
                  placeholder="e.g. Mr. Rajesh Taneja (CFO), Ms. Neha (VP Finance)"
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Date of Discussion</label>
                <input
                  type="date"
                  value={dateOfDiscussion}
                  onChange={(e) => setDateOfDiscussion(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Management Response / Comments</label>
              <textarea
                rows={2}
                value={managementResponse}
                onChange={(e) => setManagementResponse(e.target.value)}
                placeholder="Enter client response, agreed timeline, or explanation..."
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
              />
            </div>

            {/* Status & Rectification Controls */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Overall Observation Status</label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value as ObservationStatus)}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10 font-medium"
                >
                  <option value="Open">Open</option>
                  <option value="Under Discussion">Under Discussion</option>
                  <option value="Management Response Awaited">Management Response Awaited</option>
                  <option value="Rectified">Rectified</option>
                  <option value="Closed">Closed</option>
                  <option value="Not Accepted">Not Accepted</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Rectification Status</label>
                <select
                  value={rectificationStatus}
                  onChange={(e) => setRectificationStatus(e.target.value as RectificationStatus)}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10 font-medium"
                >
                  <option value="Not Started">Not Started</option>
                  <option value="In Progress">In Progress</option>
                  <option value="Rectified">Rectified</option>
                  <option value="Not Rectified">Not Rectified</option>
                  <option value="Not Applicable">Not Applicable</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Target Rectification Date</label>
                <input
                  type="date"
                  value={targetRectificationDate}
                  onChange={(e) => setTargetRectificationDate(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Actual Rectification Date (if done)</label>
                <input
                  type="date"
                  value={actualRectificationDate}
                  onChange={(e) => setActualRectificationDate(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
                />
              </div>
            </div>
          </div>

          {/* SECTION 4: Team Responsibility & Supporting References */}
          <div className="space-y-3.5">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <span>4. Audit Team Follow-up & Evidence</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700 flex items-center gap-1">
                  Auditor Responsible for Follow-up <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  value={personResponsible}
                  onChange={(e) => setPersonResponsible(e.target.value)}
                  placeholder="e.g. Ankit Sharma (Senior)"
                  className={`w-full px-3.5 py-2 text-sm rounded-lg border bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10 ${
                    errors.personResponsible ? 'border-rose-400 bg-rose-50/20' : 'border-slate-300'
                  }`}
                />
                {errors.personResponsible && (
                  <p className="text-[11px] text-rose-600 font-medium">{errors.personResponsible}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Attachments / Supporting Workpapers</label>
                <input
                  type="text"
                  value={attachments}
                  onChange={(e) => setAttachments(e.target.value)}
                  placeholder="e.g. Annexure_Stock_Aging.xlsx, MGT_Letter_Ref4.pdf"
                  className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Internal Audit Remarks / Follow-up Notes</label>
              <input
                type="text"
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="e.g. Verified revised DP certificate on 24-Jan. Complied."
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
              />
            </div>
          </div>

          {/* Form Actions */}
          <div className="pt-4 border-t border-stone-200 flex items-center justify-between">
            <div className="text-xs text-stone-500">
              * Reference No. <strong className="font-mono text-stone-800">{referenceNo || 'Auto'}</strong>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-lg border border-stone-300 text-stone-700 hover:bg-[#F5F2ED] text-sm font-semibold transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-5 py-2 rounded-lg bg-[#5A5A40] hover:bg-[#4A4A34] text-white text-sm font-semibold shadow-xs transition-colors"
              >
                {observationToEdit ? 'Update Observation' : 'Save Observation'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
