import React, { useState, useEffect } from 'react';
import { X, Briefcase, Plus, AlertCircle, Building2, UserCheck, Calendar, MapPin } from 'lucide-react';
import { Engagement, AuditType, EngagementStatus, FirmProfile } from '../../types/audit';
import { generateClientCode } from '../../utils/formatters';

interface EngagementFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (engData: Partial<Engagement> & { clientName: string; auditTypeId: string; financialYear: string; engagementPartner: string }) => void;
  engagementToEdit?: Engagement | null;
  auditTypes: AuditType[];
  firmProfile: FirmProfile;
  onOpenAddAuditType?: () => void;
}

export const EngagementFormModal: React.FC<EngagementFormModalProps> = ({
  isOpen,
  onClose,
  onSave,
  engagementToEdit,
  auditTypes,
  firmProfile,
  onOpenAddAuditType,
}) => {
  const [clientName, setClientName] = useState('');
  const [clientPanGstin, setClientPanGstin] = useState('');
  const [clientCode, setClientCode] = useState('');
  const [auditTypeId, setAuditTypeId] = useState(auditTypes[0]?.id || '');
  const [financialYear, setFinancialYear] = useState('2024-25');
  const [teamMembersInput, setTeamMembersInput] = useState('');
  const [engagementPartner, setEngagementPartner] = useState(firmProfile?.partnerName || 'CA Ritesh Garg');
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);
  const [branchLocation, setBranchLocation] = useState('');
  const [overallStatus, setOverallStatus] = useState<EngagementStatus>('In Progress');
  const [notes, setNotes] = useState('');

  const [errors, setErrors] = useState<{ [key: string]: string }>({});

  useEffect(() => {
    if (engagementToEdit) {
      setClientName(engagementToEdit.clientName);
      setClientPanGstin(engagementToEdit.clientPanGstin || '');
      setClientCode(engagementToEdit.clientCode);
      setAuditTypeId(engagementToEdit.auditTypeId);
      setFinancialYear(engagementToEdit.financialYear);
      setTeamMembersInput(engagementToEdit.teamMembers.join(', '));
      setEngagementPartner(engagementToEdit.engagementPartner);
      setStartDate(engagementToEdit.startDate);
      setEndDate(engagementToEdit.endDate);
      setBranchLocation(engagementToEdit.branchLocation || '');
      setOverallStatus(engagementToEdit.overallStatus);
      setNotes(engagementToEdit.notes || '');
    } else {
      setClientName('');
      setClientPanGstin('');
      setClientCode('');
      setAuditTypeId(auditTypes[0]?.id || '');
      setFinancialYear('2024-25');
      setTeamMembersInput('');
      setEngagementPartner(firmProfile?.partnerName || 'CA Ritesh Garg');
      setStartDate(new Date().toISOString().split('T')[0]);
      setEndDate(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);
      setBranchLocation('');
      setOverallStatus('In Progress');
      setNotes('');
    }
    setErrors({});
  }, [engagementToEdit, isOpen, auditTypes, firmProfile]);

  const handleClientNameChange = (val: string) => {
    setClientName(val);
    if (!engagementToEdit || !clientCode) {
      setClientCode(generateClientCode(val));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: { [key: string]: string } = {};

    if (!clientName.trim()) {
      newErrors.clientName = 'Client Name is required';
    }
    if (!auditTypeId) {
      newErrors.auditTypeId = 'Please select an Audit Type';
    }
    if (!financialYear.trim()) {
      newErrors.financialYear = 'Financial Year is required';
    }
    if (!engagementPartner.trim()) {
      newErrors.engagementPartner = 'Engagement Partner is required';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    const teamMembers = teamMembersInput
      .split(',')
      .map(t => t.trim())
      .filter(Boolean);

    onSave({
      id: engagementToEdit?.id,
      clientName: clientName.trim(),
      clientPanGstin: clientPanGstin.trim() || undefined,
      clientCode: (clientCode || generateClientCode(clientName)).trim().toUpperCase(),
      auditTypeId,
      financialYear: financialYear.trim(),
      teamMembers,
      engagementPartner: engagementPartner.trim(),
      startDate,
      endDate,
      branchLocation: branchLocation.trim() || undefined,
      overallStatus,
      notes: notes.trim() || undefined,
    });

    onClose();
  };

  if (!isOpen) return null;

  return (
    <div id="engagement-form-modal-overlay" className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6">
      <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl border border-stone-200 overflow-hidden transform transition-all">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-[#5A5A40] text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-white/10 text-amber-300 flex items-center justify-center">
              <Briefcase className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold leading-tight">
                {engagementToEdit ? 'Edit Audit Engagement' : 'Create New Audit Assignment'}
              </h2>
              <p className="text-xs text-stone-200">
                {engagementToEdit ? `Engagement ID: ${engagementToEdit.id}` : 'Setup client engagement master record'}
              </p>
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
        <form onSubmit={handleSubmit} className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          {/* Row 1: Client Name & Code */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2 space-y-1.5">
              <label className="text-xs font-bold text-slate-700 flex items-center gap-1">
                Client / Auditee Name <span className="text-rose-600">*</span>
              </label>
              <input
                type="text"
                value={clientName}
                onChange={(e) => handleClientNameChange(e.target.value)}
                placeholder="e.g. Tata Steel Limited, Apex Hospital Pvt Ltd"
                className={`w-full px-3.5 py-2 text-sm rounded-lg border bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10 ${
                  errors.clientName ? 'border-rose-400 bg-rose-50/20' : 'border-slate-300'
                }`}
              />
              {errors.clientName && (
                <p className="text-[11px] text-rose-600 font-medium">{errors.clientName}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 flex items-center gap-1">
                Short Code
                <span className="text-[10px] text-slate-400 font-normal">(for Ref No.)</span>
              </label>
              <input
                type="text"
                value={clientCode}
                onChange={(e) => setClientCode(e.target.value.toUpperCase())}
                placeholder="e.g. TSL, APEX"
                maxLength={6}
                className="w-full px-3.5 py-2 text-sm font-mono uppercase rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
              />
            </div>
          </div>

          {/* Row 2: PAN/GSTIN & Branch/Location */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Client PAN / GSTIN (Optional)</label>
              <input
                type="text"
                value={clientPanGstin}
                onChange={(e) => setClientPanGstin(e.target.value.toUpperCase())}
                placeholder="e.g. 07AAACA1234F1Z8 / AAACA1234F"
                className="w-full px-3.5 py-2 text-sm font-mono rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Branch / Unit / Plant Location</label>
              <input
                type="text"
                value={branchLocation}
                onChange={(e) => setBranchLocation(e.target.value)}
                placeholder="e.g. Plant-1 Manesar / Parliament St Branch"
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
              />
            </div>
          </div>

          {/* Row 3: Audit Type & Financial Year */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-700 flex items-center gap-1">
                  Audit Type <span className="text-rose-600">*</span>
                </label>
                {onOpenAddAuditType && (
                  <button
                    type="button"
                    onClick={onOpenAddAuditType}
                    className="text-[11px] font-semibold text-blue-600 hover:text-blue-800"
                  >
                    + Add New Type
                  </button>
                )}
              </div>
              <select
                value={auditTypeId}
                onChange={(e) => setAuditTypeId(e.target.value)}
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
              >
                {auditTypes.map((at) => (
                  <option key={at.id} value={at.id}>
                    {at.name} ({at.code})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 flex items-center gap-1">
                Financial Year / Audit Period <span className="text-rose-600">*</span>
              </label>
              <input
                type="text"
                value={financialYear}
                onChange={(e) => setFinancialYear(e.target.value)}
                placeholder="e.g. 2024-25, 2025-26, Q3 2024-25"
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
              />
            </div>
          </div>

          {/* Row 4: Partner & Team Members */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 flex items-center gap-1">
                Engagement Partner <span className="text-rose-600">*</span>
              </label>
              <input
                type="text"
                value={engagementPartner}
                onChange={(e) => setEngagementPartner(e.target.value)}
                placeholder="e.g. CA Ritesh Garg"
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Audit Team Members (Comma separated)</label>
              <input
                type="text"
                value={teamMembersInput}
                onChange={(e) => setTeamMembersInput(e.target.value)}
                placeholder="e.g. Ankit Sharma, Rohit Verma (Article)"
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
              />
            </div>
          </div>

          {/* Row 5: Dates & Status */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Audit Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Audit End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Assignment Status</label>
              <select
                value={overallStatus}
                onChange={(e) => setOverallStatus(e.target.value as EngagementStatus)}
                className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
              >
                <option value="Planning">Planning</option>
                <option value="In Progress">In Progress</option>
                <option value="Fieldwork Complete">Fieldwork Complete</option>
                <option value="Report Issued">Report Issued</option>
                <option value="Closed">Closed</option>
              </select>
            </div>
          </div>

          {/* Row 6: Scope Notes */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700">Audit Scope & Background Notes (Optional)</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Concurrent audit of advances above ₹ 2 Cr and Forex desk operations as per Bank guidelines..."
              className="w-full px-3.5 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-slate-900/10"
            />
          </div>

          {/* Form Actions */}
          <div className="pt-4 border-t border-stone-200 flex items-center justify-end gap-3">
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
              {engagementToEdit ? 'Save Changes' : 'Create Engagement'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
