import React, { useState } from 'react';
import { X, Save, Building2, UserCheck, ShieldCheck } from 'lucide-react';
import { AssesseeDetails } from '../types';

interface AssesseeModalProps {
  isOpen: boolean;
  onClose: () => void;
  assessee: AssesseeDetails;
  onSave: (details: AssesseeDetails) => void;
}

export const AssesseeModal: React.FC<AssesseeModalProps> = ({
  isOpen,
  onClose,
  assessee,
  onSave,
}) => {
  const [formData, setFormData] = useState<AssesseeDetails>({ ...assessee });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="p-4 sm:p-5 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-sky-400" />
            <h3 className="text-base font-bold text-slate-50">
              Client & Auditor Particulars
            </h3>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 overflow-y-auto text-xs">
          
          <div className="bg-sky-50 border border-sky-100 p-3 rounded-xl">
            <h4 className="font-bold text-sky-900 mb-1">Assessee Information (Client Under Audit)</h4>
            <p className="text-sky-700 text-[11px]">These details will be populated in all Form 3CD Clause 20(b) Excel and PDF reports.</p>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Assessee / Company / Client Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:outline-none font-semibold text-slate-900"
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">PAN</label>
              <input
                type="text"
                value={formData.pan}
                onChange={(e) => setFormData({ ...formData, pan: e.target.value.toUpperCase() })}
                maxLength={10}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:outline-none font-mono uppercase"
                required
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Assessment Year</label>
              <input
                type="text"
                value={formData.assessmentYear}
                onChange={(e) => setFormData({ ...formData, assessmentYear: e.target.value })}
                placeholder="2025-26"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:outline-none"
                required
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Financial Year</label>
              <input
                type="text"
                value={formData.financialYear}
                onChange={(e) => setFormData({ ...formData, financialYear: e.target.value })}
                placeholder="2024-25"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:outline-none"
                required
              />
            </div>
          </div>

          <div className="pt-2 border-t border-slate-200">
            <h4 className="font-bold text-slate-800 mb-2 flex items-center gap-1.5">
              <UserCheck className="w-4 h-4 text-amber-600" />
              Tax Auditor Details
            </h4>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Auditor Name</label>
              <input
                type="text"
                value={formData.auditorName}
                onChange={(e) => setFormData({ ...formData, auditorName: e.target.value })}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:outline-none font-semibold text-slate-900"
                required
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Membership No.</label>
              <input
                type="text"
                value={formData.membershipNumber || ''}
                onChange={(e) => setFormData({ ...formData, membershipNumber: e.target.value })}
                placeholder="524189"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:outline-none font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">CA Firm Name</label>
              <input
                type="text"
                value={formData.firmName || ''}
                onChange={(e) => setFormData({ ...formData, firmName: e.target.value })}
                placeholder="Ietikka Gupta & Associates"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Date of Audit Report</label>
              <input
                type="date"
                value={formData.dateOfReport}
                onChange={(e) => setFormData({ ...formData, dateOfReport: e.target.value })}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:outline-none font-mono"
                required
              />
            </div>
          </div>

          {/* Modal Footer */}
          <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg font-bold shadow-md transition flex items-center gap-1.5 cursor-pointer"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Update Details</span>
            </button>
          </div>

        </form>

      </div>
    </div>
  );
};
