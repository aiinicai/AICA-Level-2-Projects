import React, { useState, useEffect } from 'react';
import { X, Building2, Save, Check } from 'lucide-react';
import { CAFirmProfile } from '../types';

interface FirmSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  firmProfile: CAFirmProfile;
  onSave: (updated: CAFirmProfile) => void;
}

export const FirmSettingsModal: React.FC<FirmSettingsModalProps> = ({
  isOpen,
  onClose,
  firmProfile,
  onSave,
}) => {
  const [formData, setFormData] = useState<CAFirmProfile>({ ...firmProfile });
  const [saved, setSaved] = useState<boolean>(false);

  useEffect(() => {
    setFormData({ ...firmProfile });
  }, [firmProfile, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    setSaved(true);
    setTimeout(() => {
      setSaved(false);
      onClose();
    }, 600);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-xl flex flex-col shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100">
              <Building2 className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800">CA Firm &amp; Audit Engagement Profile</h3>
              <p className="text-[11px] text-slate-500">Configure audit header and client metadata</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          
          <div className="space-y-1.5">
            <label className="text-slate-700 font-bold">Chartered Accountancy Firm Name</label>
            <input
              type="text"
              required
              value={formData.firmName}
              onChange={(e) => setFormData({ ...formData, firmName: e.target.value })}
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-indigo-500 shadow-2xs"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-slate-700 font-bold">Firm Reg. No (FRN)</label>
              <input
                type="text"
                value={formData.frnNumber}
                onChange={(e) => setFormData({ ...formData, frnNumber: e.target.value })}
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-indigo-500 shadow-2xs"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-slate-700 font-bold">Engagement Partner (FCA / ACA)</label>
              <input
                type="text"
                required
                value={formData.partnerName}
                onChange={(e) => setFormData({ ...formData, partnerName: e.target.value })}
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-indigo-500 shadow-2xs"
              />
            </div>
          </div>

          <div className="border-t border-slate-100 pt-3 space-y-3">
            <span className="text-[11px] font-bold text-indigo-700 uppercase tracking-wider block">
              Active Client Under Audit
            </span>

            <div className="space-y-1.5">
              <label className="text-slate-700 font-bold">Client Entity Name</label>
              <input
                type="text"
                required
                value={formData.clientName}
                onChange={(e) => setFormData({ ...formData, clientName: e.target.value })}
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-indigo-500 shadow-2xs"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <label className="text-slate-700 font-bold">Client GSTIN</label>
                <input
                  type="text"
                  value={formData.clientGSTIN}
                  onChange={(e) => setFormData({ ...formData, clientGSTIN: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 font-mono uppercase focus:outline-none focus:border-indigo-500 shadow-2xs"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-slate-700 font-bold">Client PAN</label>
                <input
                  type="text"
                  value={formData.clientPAN}
                  onChange={(e) => setFormData({ ...formData, clientPAN: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 font-mono uppercase focus:outline-none focus:border-indigo-500 shadow-2xs"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-slate-700 font-bold">Financial Year</label>
                <select
                  value={formData.financialYear}
                  onChange={(e) => setFormData({ ...formData, financialYear: e.target.value })}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-indigo-500 shadow-2xs"
                >
                  <option value="FY 2025-26 (AY 2026-27)">FY 2025-26 (AY 2026-27)</option>
                  <option value="FY 2024-25 (AY 2025-26)">FY 2024-25 (AY 2025-26)</option>
                  <option value="FY 2023-24 (AY 2024-25)">FY 2023-24 (AY 2024-25)</option>
                  <option value="FY 2022-23 (AY 2023-24)">FY 2022-23 (AY 2023-24)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 -mx-5 -mb-5 border-t border-slate-100 bg-slate-50 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold shadow-2xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors"
            >
              {saved ? <Check className="w-3.5 h-3.5" /> : <Save className="w-3.5 h-3.5" />}
              <span>{saved ? 'Saved!' : 'Save Firm Settings'}</span>
            </button>
          </div>

        </form>

      </div>
    </div>
  );
};
