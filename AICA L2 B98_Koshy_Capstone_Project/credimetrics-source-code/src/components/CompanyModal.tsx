import React, { useState } from 'react';
import { X, Building2, Plus, CheckCircle2, AlertCircle } from 'lucide-react';
import { Company, User } from '../types/financial';

interface CompanyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaveCompany: (company: Company) => void;
  currentUser: User;
}

export const CompanyModal: React.FC<CompanyModalProps> = ({
  isOpen,
  onClose,
  onSaveCompany,
  currentUser
}) => {
  const [companyName, setCompanyName] = useState('');
  const [cin, setCin] = useState('');
  const [pan, setPan] = useState('');
  const [industry, setIndustry] = useState('Manufacturing & Engineering');
  const [address, setAddress] = useState('');
  const [yearEstablished, setYearEstablished] = useState<number>(2015);
  const [annualTurnover, setAnnualTurnover] = useState<number>(50.0);
  const [description, setDescription] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const industries = [
    'Manufacturing & Engineering',
    'Automotive & Precision Components',
    'IT Services & Enterprise SaaS',
    'Infrastructure & EPC Construction',
    'Pharmaceuticals & Healthcare',
    'Textiles & Garments',
    'FMCG & Consumer Goods',
    'Logistics & Multi-Modal Supply Chain',
    'Chemicals & Specialty Materials',
    'Renewable Energy & Power'
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim()) {
      setErrorMsg('Company Name is required.');
      return;
    }

    const newCompany: Company = {
      id: `comp-${Date.now()}`,
      companyName: companyName.trim(),
      cin: cin.trim() || `U${Math.floor(10000 + Math.random() * 90000)}MH${yearEstablished}PLC${Math.floor(100000 + Math.random() * 900000)}`,
      pan: pan.trim().toUpperCase() || 'AAACB' + Math.floor(1000 + Math.random() * 9000) + 'K',
      industry,
      address: address.trim() || 'Corporate Head Office, Mumbai, Maharashtra',
      yearEstablished: Number(yearEstablished) || 2015,
      annualTurnover: Number(annualTurnover) || 10.0,
      createdBy: currentUser.name,
      createdAt: new Date().toISOString(),
      description: description.trim() || `${industry} corporate borrower.`
    };

    onSaveCompany(newCompany);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden my-8">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-850">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-blue-600/20 text-blue-400 rounded-lg">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Add Borrower Company</h3>
              <p className="text-xs text-slate-400">Register corporate entity for financial statement review</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Company Legal Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Acme Precision Technologies Ltd."
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                CIN (Corporate ID)
              </label>
              <input
                type="text"
                placeholder="e.g. L72200MH2010PLC123456"
                value={cin}
                onChange={(e) => setCin(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-blue-500 uppercase"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Income Tax PAN
              </label>
              <input
                type="text"
                placeholder="e.g. AAACA1234K"
                value={pan}
                onChange={(e) => setPan(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-blue-500 uppercase"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Industry Sector
              </label>
              <select
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              >
                {industries.map(ind => (
                  <option key={ind} value={ind}>{ind}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Year Established
              </label>
              <input
                type="number"
                min="1950"
                max="2026"
                value={yearEstablished}
                onChange={(e) => setYearEstablished(parseInt(e.target.value) || 2015)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Annual Turnover (INR Crores)
            </label>
            <input
              type="number"
              step="any"
              min="0.1"
              value={annualTurnover}
              onChange={(e) => setAnnualTurnover(parseFloat(e.target.value) || 10)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Registered Office Address
            </label>
            <input
              type="text"
              placeholder="e.g. MIDC Industrial Estate, Andheri East, Mumbai 400093"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Business Description &amp; Scope
            </label>
            <textarea
              rows={2}
              placeholder="Brief summary of business operations, market standing, and products..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 rounded-xl text-xs font-bold transition shadow-lg shadow-blue-600/30"
            >
              <Plus className="w-4 h-4" />
              <span>Create Borrower</span>
            </button>
          </div>

        </form>

      </div>
    </div>
  );
};
