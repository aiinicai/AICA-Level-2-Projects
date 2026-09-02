import React, { useState } from 'react';
import { 
  Building2, 
  X, 
  Plus, 
  Trash2, 
  Sparkles, 
  FileSpreadsheet, 
  CheckCircle2, 
  ShieldCheck, 
  Layers
} from 'lucide-react';
import { Company, IndustryType } from '../types';

interface CompanyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateCompany: (
    company: Omit<Company, 'id' | 'createdAt'>,
    mode: 'blank' | 'template' | 'custom_assets'
  ) => void;
}

const INDUSTRY_OPTIONS: IndustryType[] = [
  'Automotive & Precision Engineering',
  'Pharmaceuticals & Life Sciences',
  'Renewable Energy & Solar Infrastructure',
  'Information Technology & Data Centers',
  'Chemicals & Process Manufacturing',
  'Consumer Goods & FMCG',
  'Heavy Infrastructure & Construction',
  'Other Enterprise'
];

export const CompanyModal: React.FC<CompanyModalProps> = ({
  isOpen,
  onClose,
  onCreateCompany
}) => {
  const [name, setName] = useState('');
  const [shortCode, setShortCode] = useState('');
  const [legalEntityType, setLegalEntityType] = useState<'Public Limited' | 'Private Limited' | 'LLP' | 'Multinational Corporation'>('Public Limited');
  const [cin, setCin] = useState('');
  const [gstin, setGstin] = useState('');
  const [industry, setIndustry] = useState<IndustryType>('Automotive & Precision Engineering');
  const [fiscalYear, setFiscalYear] = useState('2024-2025');
  const [depreciationPolicy, setDepreciationPolicy] = useState<'Companies Act 2013 Sch II (SLM)' | 'Income Tax Act 1961 (WDV)' | 'Dual Depreciation (Both)'>('Dual Depreciation (Both)');
  const [baseCurrency, setBaseCurrency] = useState<'INR' | 'USD' | 'EUR'>('INR');
  const [description, setDescription] = useState('');
  
  // Plants list builder
  const [plants, setPlants] = useState<string[]>(['Main Manufacturing Plant - Unit 1']);
  const [newPlantInput, setNewPlantInput] = useState('');

  // Initial Data Mode
  const [initialDataMode, setInitialDataMode] = useState<'blank' | 'template'>('blank');

  if (!isOpen) return null;

  const handleAddPlant = () => {
    if (newPlantInput.trim() && !plants.includes(newPlantInput.trim())) {
      setPlants([...plants, newPlantInput.trim()]);
      setNewPlantInput('');
    }
  };

  const handleRemovePlant = (index: number) => {
    if (plants.length > 1) {
      setPlants(plants.filter((_, i) => i !== index));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const derivedShortCode = shortCode.trim() || name.substring(0, 3).toUpperCase();
    const derivedCin = cin.trim() || `U${Math.floor(10000 + Math.random() * 90000)}MH${new Date().getFullYear()}PTC${Math.floor(100000 + Math.random() * 900000)}`;
    const derivedGstin = gstin.trim() || `27AAAC${Math.floor(1000 + Math.random() * 9000)}F1Z5`;

    onCreateCompany(
      {
        name: name.trim(),
        shortCode: derivedShortCode,
        legalEntityType,
        cin: derivedCin,
        gstin: derivedGstin,
        industry,
        fiscalYear,
        depreciationPolicy,
        plants: plants.length > 0 ? plants : ['Main Plant Unit 1'],
        baseCurrency,
        description: description.trim() || `${name.trim()} enterprise fixed asset governance workspace.`,
        logoColor: 'from-blue-600 to-indigo-700',
        isCustom: true
      },
      initialDataMode
    );

    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-blue-600/30 border border-blue-500/40 text-blue-400">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold tracking-tight">Create New Company Entity</h2>
              <p className="text-xs text-slate-400">Establish a new fixed asset subledger & risk governance workspace</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          
          {/* Company Name & Short Code */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Company Legal Name <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (!shortCode && e.target.value.length >= 3) {
                    setShortCode(e.target.value.replace(/[^A-Za-z]/g, '').substring(0, 4).toUpperCase());
                  }
                }}
                placeholder="e.g. Apex Precision Technologies Pvt Ltd"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Asset Prefix Code <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                maxLength={5}
                value={shortCode}
                onChange={(e) => setShortCode(e.target.value.toUpperCase())}
                placeholder="e.g. APEX"
                className="w-full px-3 py-2 text-sm uppercase font-mono font-bold border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
              <p className="text-[10px] text-slate-500 mt-0.5">Used in Tag IDs: AST-APEX-0001</p>
            </div>
          </div>

          {/* Legal Structure & Industry */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Legal Entity Type
              </label>
              <select
                value={legalEntityType}
                onChange={(e) => setLegalEntityType(e.target.value as any)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
              >
                <option value="Public Limited">Public Limited Company (Ind AS & CARO Mandatory)</option>
                <option value="Private Limited">Private Limited Company</option>
                <option value="LLP">Limited Liability Partnership (LLP)</option>
                <option value="Multinational Corporation">Multinational Subsidiary / Branch</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Industry & Asset Archetype
              </label>
              <select
                value={industry}
                onChange={(e) => setIndustry(e.target.value as IndustryType)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
              >
                {INDUSTRY_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Statutory Registration Numbers (CIN & GSTIN) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50 p-3.5 rounded-xl border border-slate-200">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Corporate Identity No. (CIN)
              </label>
              <input
                type="text"
                value={cin}
                onChange={(e) => setCin(e.target.value.toUpperCase())}
                placeholder="e.g. L28920MH2018PLC304122"
                className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Primary GSTIN
              </label>
              <input
                type="text"
                value={gstin}
                onChange={(e) => setGstin(e.target.value.toUpperCase())}
                placeholder="e.g. 27AABCA9921F1Z8"
                className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
              />
            </div>
          </div>

          {/* Operating Plants & Locations Builder */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Manufacturing Plants & Operating Facilities
            </label>
            <p className="text-xs text-slate-500 mb-2">
              Define the physical locations where your company's fixed assets are stationed.
            </p>
            
            <div className="space-y-2 mb-2">
              {plants.map((p, idx) => (
                <div key={idx} className="flex items-center space-x-2 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200 text-xs">
                  <span className="font-semibold text-slate-500">#{idx + 1}</span>
                  <span className="flex-1 font-medium text-slate-800">{p}</span>
                  {plants.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemovePlant(idx)}
                      className="text-slate-400 hover:text-rose-600 p-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={newPlantInput}
                onChange={(e) => setNewPlantInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddPlant();
                  }
                }}
                placeholder="Add another location (e.g. Pune Hub, Chennai Toolroom)"
                className="flex-1 px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
              <button
                type="button"
                onClick={handleAddPlant}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold flex items-center space-x-1"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Plant</span>
              </button>
            </div>
          </div>

          {/* Depreciation & Accounting Setup */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Depreciation Policy Model
              </label>
              <select
                value={depreciationPolicy}
                onChange={(e) => setDepreciationPolicy(e.target.value as any)}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
              >
                <option value="Dual Depreciation (Both)">Dual Depreciation (Companies Act Sch II + Income Tax Act)</option>
                <option value="Companies Act 2013 Sch II (SLM)">Companies Act 2013 Straight Line Method (SLM)</option>
                <option value="Income Tax Act 1961 (WDV)">Income Tax Act 1961 Written Down Value (WDV Block)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Active Financial Year
              </label>
              <select
                value={fiscalYear}
                onChange={(e) => setFiscalYear(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
              >
                <option value="2024-2025">FY 2024-25 (Current Period)</option>
                <option value="2023-2024">FY 2023-24 (Previous Period)</option>
                <option value="2025-2026">FY 2025-26 (Budgeted Period)</option>
              </select>
            </div>
          </div>

          {/* Initial Data Starting Mode */}
          <div className="pt-2">
            <label className="block text-xs font-semibold text-slate-700 mb-2">
              Workspace Starting Mode
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label
                className={`flex items-start space-x-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                  initialDataMode === 'blank'
                    ? 'border-blue-600 bg-blue-50/50 ring-1 ring-blue-500'
                    : 'border-slate-200 bg-white hover:bg-slate-50'
                }`}
              >
                <input
                  type="radio"
                  name="initialMode"
                  checked={initialDataMode === 'blank'}
                  onChange={() => setInitialDataMode('blank')}
                  className="mt-0.5 text-blue-600"
                />
                <div>
                  <span className="block text-xs font-bold text-slate-900">
                    Clean Blank Workspace (0 Assets)
                  </span>
                  <span className="block text-[11px] text-slate-500 mt-0.5">
                    Start completely clean. Add your company's assets manually or import via Excel / CSV / PDF.
                  </span>
                </div>
              </label>

              <label
                className={`flex items-start space-x-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                  initialDataMode === 'template'
                    ? 'border-blue-600 bg-blue-50/50 ring-1 ring-blue-500'
                    : 'border-slate-200 bg-white hover:bg-slate-50'
                }`}
              >
                <input
                  type="radio"
                  name="initialMode"
                  checked={initialDataMode === 'template'}
                  onChange={() => setInitialDataMode('template')}
                  className="mt-0.5 text-blue-600"
                />
                <div>
                  <span className="block text-xs font-bold text-slate-900">
                    Pre-seed with Starter Blueprint
                  </span>
                  <span className="block text-[11px] text-slate-500 mt-0.5">
                    Includes 1 sample Ind AS 16 componentised asset matching your selected industry.
                  </span>
                </div>
              </label>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-4 border-t border-slate-200 flex items-center justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 rounded-lg hover:bg-slate-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim()}
              className="px-5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow-sm flex items-center space-x-2 transition-all"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Create Company & Open Workspace</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
