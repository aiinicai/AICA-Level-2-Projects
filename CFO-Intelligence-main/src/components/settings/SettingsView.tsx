import React, { useState } from 'react';
import {
  Settings,
  Building,
  Save,
  CheckCircle2,
  Shield,
  DollarSign,
  Users,
  Sparkles,
  Award,
} from 'lucide-react';
import { ClientProfile } from '../../types';
import { FirmReportHeader, FirmReportFooter } from '../common/FirmHeaderFooter';

interface SettingsViewProps {
  client: ClientProfile;
  firmName: string;
  onUpdateFirmName: (name: string) => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  client,
  firmName,
  onUpdateFirmName,
}) => {
  const [currentFirmName, setCurrentFirmName] = useState(firmName);
  const [tagline, setTagline] = useState('Chartered Accountants & Virtual CFO Advisory Services');
  const [leadPartner, setLeadPartner] = useState('Jasleen Daswal, CPA / Lead FP&A Principal');
  const [partnerEmail, setPartnerEmail] = useState('advisory@daswal-associates.com');
  const [defaultCurrency, setDefaultCurrency] = useState('USD');
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSaveSettings = () => {
    onUpdateFirmName(currentFirmName);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <FirmReportHeader client={client} reportTitle="Firm Configuration & Advisory Branding" firmName={firmName} />

      {/* Top Banner */}
      <div className="flex items-center justify-between bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <h3 className="text-base font-bold text-slate-900">
            Advisory Firm Settings & Deliverable Customization
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure white-label firm branding, report footers, default currency units, and security parameters.
          </p>
        </div>

        <button
          onClick={handleSaveSettings}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold shadow-sm transition-all"
        >
          <Save className="w-4 h-4 text-indigo-400" />
          {savedSuccess ? 'Settings Saved!' : 'Save Firm Settings'}
        </button>
      </div>

      {/* Settings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1: Firm White-label Branding */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Award className="w-5 h-5 text-indigo-600" />
            <h4 className="text-sm font-bold text-slate-900">Advisory Branding & Header/Footer</h4>
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Advisory Firm Legal Name
              </label>
              <input
                type="text"
                value={currentFirmName}
                onChange={e => setCurrentFirmName(e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2 text-xs font-bold text-slate-900 focus:outline-hidden focus:border-indigo-500"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">
                Rendered on all CFO report covers, footers, and exported workbooks.
              </span>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Firm Tagline / Subtitle
              </label>
              <input
                type="text"
                value={tagline}
                onChange={e => setTagline(e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 focus:outline-hidden focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Lead Partner Sign-Off Name & Credentials
              </label>
              <input
                type="text"
                value={leadPartner}
                onChange={e => setLeadPartner(e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2 text-xs font-semibold text-slate-900 focus:outline-hidden focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Partner Contact Email
              </label>
              <input
                type="email"
                value={partnerEmail}
                onChange={e => setPartnerEmail(e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 focus:outline-hidden focus:border-indigo-500"
              />
            </div>
          </div>
        </div>

        {/* Card 2: Engine, Security & Currency */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Shield className="w-5 h-5 text-emerald-600" />
            <h4 className="text-sm font-bold text-slate-900">Intelligence Engine & Compliance</h4>
          </div>

          <div className="space-y-4 text-xs">
            <div className="p-4 bg-emerald-50/50 rounded-xl border border-emerald-200 space-y-1.5">
              <span className="font-bold text-emerald-900 block">
                Server-Side Gemini 3.7 Flash Engine Active
              </span>
              <p className="text-slate-600 leading-relaxed">
                Deterministic calculation logic handles all mathematics; AI is utilized exclusively for executive narrative interpretation and root-cause diagnosis.
              </p>
            </div>

            <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-200 space-y-1.5">
              <span className="font-bold text-indigo-950 block">
                Deterministic Calculation Enforcement
              </span>
              <p className="text-slate-600 leading-relaxed">
                Break-even formulas, 12-month rolling forecasts, and variance math are locked into zero-hallucination TypeScript logic.
              </p>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Default Currency System
              </label>
              <select
                value={defaultCurrency}
                onChange={e => setDefaultCurrency(e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2 text-xs font-bold text-slate-900 focus:outline-hidden focus:border-indigo-500"
              >
                <option value="USD">USD ($) - United States Dollar</option>
                <option value="EUR">EUR (€) - Euro</option>
                <option value="GBP">GBP (£) - British Pound</option>
                <option value="CAD">CAD ($) - Canadian Dollar</option>
                <option value="AUD">AUD ($) - Australian Dollar</option>
                <option value="INR">INR (₹) - Indian Rupee</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <FirmReportFooter firmName={firmName} />
    </div>
  );
};
