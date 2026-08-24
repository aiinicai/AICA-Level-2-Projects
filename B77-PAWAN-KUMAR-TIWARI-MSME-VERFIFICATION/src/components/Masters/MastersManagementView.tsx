import React, { useState } from 'react';
import {
  Settings2,
  Plus,
  Percent,
  Calendar,
  ShieldAlert,
  Scale,
  Save,
  CheckCircle2,
  Clock,
  RotateCcw,
  Info,
  X,
  Edit2,
  Trash2,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { RateMasterEntry, StatutoryRuleConfig } from '../../types';
import { formatDate } from '../../utils/formatters';

export const MastersManagementView: React.FC = () => {
  const {
    rateMaster,
    statutoryRules,
    updateStatutoryRules,
    addRateMasterEntry,
    deleteRateMasterEntry,
    currentUserRole,
  } = useApp();

  const [rulesForm, setRulesForm] = useState<StatutoryRuleConfig>({ ...statutoryRules });
  const [isSavedSuccess, setIsSavedSuccess] = useState(false);
  const [isAddRateModalOpen, setIsAddRateModalOpen] = useState(false);

  const handleSaveRules = (e: React.FormEvent) => {
    e.preventDefault();
    updateStatutoryRules(rulesForm);
    setIsSavedSuccess(true);
    setTimeout(() => setIsSavedSuccess(false), 3000);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Masters & Statutory Rules Configuration</h2>
          <p className="text-xs text-slate-500">
            Configure RBI reference rates, statutory limits under Section 15, compounding parameters and 43B(h) thresholds
          </p>
        </div>

        {currentUserRole === 'Auditor' && (
          <div className="px-3 py-1.5 bg-amber-50 border border-amber-200 text-amber-800 text-xs rounded-lg font-semibold">
            Read-Only Audit Mode: Master modifications restricted to Admin / Finance Manager
          </div>
        )}
      </div>

      {/* Section 1: Rate Master */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Percent className="w-5 h-5 text-emerald-700" />
            <div>
              <h3 className="font-bold text-slate-800 text-sm">RBI Reference Rate Master</h3>
              <p className="text-xs text-slate-500">
                Formula: <strong>Applicable MSME Rate = RBI Reference Rate × Multiplier</strong> (Section 16)
              </p>
            </div>
          </div>

          {currentUserRole !== 'Auditor' && (
            <button
              onClick={() => setIsAddRateModalOpen(true)}
              className="px-3.5 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold rounded-lg shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              Add Rate Entry
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100/80 text-slate-600 font-bold text-[10px] uppercase">
              <tr>
                <th className="px-4 py-3">Financial Year</th>
                <th className="px-4 py-3">Effective Period</th>
                <th className="px-4 py-3 text-right">RBI Bank Rate (%)</th>
                <th className="px-4 py-3 text-center">Multiplier</th>
                <th className="px-4 py-3 text-right bg-emerald-50 text-emerald-900">Applicable MSME Rate (%)</th>
                <th className="px-4 py-3">Notification Reference</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rateMaster.map((rate) => (
                <tr key={rate.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3.5 font-bold text-slate-900">{rate.financialYear}</td>
                  <td className="px-4 py-3.5 text-slate-700">
                    {formatDate(rate.effectiveFrom)} to {formatDate(rate.effectiveTo)}
                  </td>
                  <td className="px-4 py-3.5 text-right font-mono font-bold text-slate-800">
                    {rate.referenceRate.toFixed(2)}%
                  </td>
                  <td className="px-4 py-3.5 text-center font-bold text-slate-600">× {rate.multiplier}</td>
                  <td className="px-4 py-3.5 text-right font-mono font-black text-emerald-700 text-sm bg-emerald-50/40">
                    {rate.applicableMSMERate.toFixed(2)}% p.a.
                  </td>
                  <td className="px-4 py-3.5 text-slate-500 text-[11px]">
                    {rate.notificationRef || 'RBI/2026/Monetary-Policy'}
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    {currentUserRole !== 'Auditor' && rateMaster.length > 1 && (
                      <button
                        onClick={() => deleteRateMasterEntry(rate.id)}
                        className="p-1 text-rose-600 hover:bg-rose-50 rounded transition-colors"
                        title="Delete Rate Entry"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section 2: Statutory Rules & Limits */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale className="w-5 h-5 text-emerald-700" />
            <div>
              <h3 className="font-bold text-slate-800 text-sm">Statutory Rules & Compliance Limits</h3>
              <p className="text-xs text-slate-500">
                Governed by MSMED Act, 2006 and Income Tax Act, 1961 provisions
              </p>
            </div>
          </div>

          {isSavedSuccess && (
            <span className="text-xs font-bold text-emerald-700 bg-emerald-100 px-3 py-1 rounded-md flex items-center gap-1">
              <CheckCircle2 className="w-4 h-4" /> Parameters saved successfully!
            </span>
          )}
        </div>

        <form onSubmit={handleSaveRules} className="p-6 space-y-6 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Rule 1: Max with Agreement */}
            <div className="space-y-1.5">
              <label className="block font-bold text-slate-800">
                Max Credit Days with Written Agreement (Sec 15)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  max={90}
                  disabled={currentUserRole === 'Auditor'}
                  value={rulesForm.maxCreditDaysWithAgreement}
                  onChange={(e) =>
                    setRulesForm({ ...rulesForm, maxCreditDaysWithAgreement: Number(e.target.value) })
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-bold text-slate-900 focus:outline-hidden disabled:bg-slate-100"
                />
                <span className="text-slate-500 font-semibold shrink-0">Days (Statutory: 45)</span>
              </div>
              <p className="text-[11px] text-slate-500">
                Under Section 15, the credit period agreed in writing between buyer and supplier shall not exceed 45 days.
              </p>
            </div>

            {/* Rule 2: Max without Agreement */}
            <div className="space-y-1.5">
              <label className="block font-bold text-slate-800">
                Max Credit Days without Written Agreement (Sec 15)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  max={45}
                  disabled={currentUserRole === 'Auditor'}
                  value={rulesForm.maxCreditDaysWithoutAgreement}
                  onChange={(e) =>
                    setRulesForm({ ...rulesForm, maxCreditDaysWithoutAgreement: Number(e.target.value) })
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-bold text-slate-900 focus:outline-hidden disabled:bg-slate-100"
                />
                <span className="text-slate-500 font-semibold shrink-0">Days (Statutory: 15)</span>
              </div>
              <p className="text-[11px] text-slate-500">
                Where there is no agreement, payment must be made on or before the appointed day (15 days from acceptance).
              </p>
            </div>

            {/* Rule 3: Deemed Acceptance */}
            <div className="space-y-1.5">
              <label className="block font-bold text-slate-800">
                Deemed Acceptance Window
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  max={30}
                  disabled={currentUserRole === 'Auditor'}
                  value={rulesForm.deemedAcceptanceWindowDays}
                  onChange={(e) =>
                    setRulesForm({ ...rulesForm, deemedAcceptanceWindowDays: Number(e.target.value) })
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-bold text-slate-900 focus:outline-hidden disabled:bg-slate-100"
                />
                <span className="text-slate-500 font-semibold shrink-0">Days (Default: 15)</span>
              </div>
              <p className="text-[11px] text-slate-500">
                If no objection is raised in writing within 15 days of material receipt, deemed acceptance is triggered.
              </p>
            </div>

            {/* Rule 4: Compounding Frequency */}
            <div className="space-y-1.5">
              <label className="block font-bold text-slate-800">
                Statutory Compounding Rest Frequency (Sec 16)
              </label>
              <select
                disabled={currentUserRole === 'Auditor'}
                value={rulesForm.compoundingFrequency}
                onChange={(e) =>
                  setRulesForm({ ...rulesForm, compoundingFrequency: e.target.value as any })
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-semibold text-slate-900 focus:outline-hidden disabled:bg-slate-100"
              >
                <option value="MONTHLY_REST">Monthly Rest (Mandated by Section 16)</option>
                <option value="QUARTERLY_REST">Quarterly Rest</option>
                <option value="ANNUAL_REST">Annual Rest</option>
              </select>
              <p className="text-[11px] text-slate-500">
                MSMED Act Section 16 explicitly requires compounding with monthly rests.
              </p>
            </div>

            {/* Rule 5: Section 43B(h) Warning Window */}
            <div className="space-y-1.5">
              <label className="block font-bold text-slate-800">
                Section 43B(h) Disallowance Alert Window
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  max={60}
                  disabled={currentUserRole === 'Auditor'}
                  value={rulesForm.section43BHWarningWindowDays}
                  onChange={(e) =>
                    setRulesForm({ ...rulesForm, section43BHWarningWindowDays: Number(e.target.value) })
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-bold text-slate-900 focus:outline-hidden disabled:bg-slate-100"
                />
                <span className="text-slate-500 font-semibold shrink-0">Days prior to due date</span>
              </div>
              <p className="text-[11px] text-slate-500">
                Advance threshold to alert finance teams before invoice breaches the 43B(h) disallowance limit.
              </p>
            </div>

            {/* Rule 6: Interest Multiplier */}
            <div className="space-y-1.5">
              <label className="block font-bold text-slate-800">
                Statutory Rate Multiplier
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  max={5}
                  disabled={currentUserRole === 'Auditor'}
                  value={rulesForm.penaltyInterestMultiplier}
                  onChange={(e) =>
                    setRulesForm({ ...rulesForm, penaltyInterestMultiplier: Number(e.target.value) })
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-bold text-slate-900 focus:outline-hidden disabled:bg-slate-100"
                />
                <span className="text-slate-500 font-semibold shrink-0">× RBI Bank Rate (Default: 3)</span>
              </div>
              <p className="text-[11px] text-slate-500">
                Section 16 specifies three times of the bank rate notified by the Reserve Bank of India.
              </p>
            </div>
          </div>

          {currentUserRole !== 'Auditor' && (
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setRulesForm({ ...statutoryRules })}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 font-semibold rounded-lg text-xs"
              >
                Reset Defaults
              </button>
              <button
                type="submit"
                className="px-5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow-xs text-xs flex items-center gap-1.5 transition-all"
              >
                <Save className="w-3.5 h-3.5" />
                Save & Apply Statutory Rules
              </button>
            </div>
          )}
        </form>
      </div>

      {/* Add Rate Master Modal */}
      {isAddRateModalOpen && (
        <AddRateModal
          isOpen={isAddRateModalOpen}
          onClose={() => setIsAddRateModalOpen(false)}
          onAdd={(data) => {
            addRateMasterEntry(data);
            setIsAddRateModalOpen(false);
          }}
        />
      )}
    </div>
  );
};

/* --- Add Rate Modal --- */
const AddRateModal: React.FC<{ isOpen: boolean; onClose: () => void; onAdd: (data: any) => void }> = ({
  isOpen,
  onClose,
  onAdd,
}) => {
  const [financialYear, setFinancialYear] = useState('2026-27');
  const [effectiveFrom, setEffectiveFrom] = useState('2026-04-01');
  const [effectiveTo, setEffectiveTo] = useState('2027-03-31');
  const [referenceRate, setReferenceRate] = useState(6.5);
  const [multiplier, setMultiplier] = useState(3);
  const [notificationRef, setNotificationRef] = useState('RBI/2026/MSME-Notification');

  if (!isOpen) return null;

  const applicableRate = referenceRate * multiplier;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd({
      financialYear,
      effectiveFrom,
      effectiveTo,
      referenceRate: Number(referenceRate),
      multiplier: Number(multiplier),
      notificationRef,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <h3 className="font-bold text-slate-800 text-sm">Add RBI Reference Rate Entry</h3>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          <div>
            <label className="block font-bold text-slate-700 mb-1">Financial Year</label>
            <input
              type="text"
              required
              value={financialYear}
              onChange={(e) => setFinancialYear(e.target.value)}
              placeholder="e.g. 2026-27"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Effective From</label>
              <input
                type="date"
                required
                value={effectiveFrom}
                onChange={(e) => setEffectiveFrom(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block font-bold text-slate-700 mb-1">Effective To</label>
              <input
                type="date"
                required
                value={effectiveTo}
                onChange={(e) => setEffectiveTo(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-bold text-slate-700 mb-1">RBI Bank Rate (%)</label>
              <input
                type="number"
                step="0.05"
                required
                value={referenceRate}
                onChange={(e) => setReferenceRate(Number(e.target.value))}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono font-bold"
              />
            </div>
            <div>
              <label className="block font-bold text-slate-700 mb-1">Multiplier</label>
              <input
                type="number"
                required
                value={multiplier}
                onChange={(e) => setMultiplier(Number(e.target.value))}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-bold"
              />
            </div>
          </div>

          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
            <span className="text-[11px] text-emerald-800 font-semibold block">Calculated Applicable MSME Rate:</span>
            <span className="text-lg font-black text-emerald-700 font-mono">
              {applicableRate.toFixed(2)}% per annum
            </span>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Gazette / RBI Notification Ref</label>
            <input
              type="text"
              value={notificationRef}
              onChange={(e) => setNotificationRef(e.target.value)}
              placeholder="e.g. RBI/2026-27/04"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow-xs"
            >
              Save Rate Entry
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
