import React, { useState } from 'react';
import {
  X,
  Building,
  Plus,
  Check,
  Stethoscope,
  Utensils,
  Factory,
  Globe,
  Briefcase,
  Layers,
} from 'lucide-react';
import { ClientProfile, IndustryType } from '../../types';
import { getAvailableDemoClients } from '../../services/demoData';

interface ClientManagerModalProps {
  currentClient: ClientProfile;
  onSelectClient: (client: ClientProfile) => void;
  onClose: () => void;
}

export const ClientManagerModal: React.FC<ClientManagerModalProps> = ({
  currentClient,
  onSelectClient,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'switch' | 'create'>('switch');
  const demoClients = getAvailableDemoClients();

  // Create Form State
  const [name, setName] = useState('');
  const [legalName, setLegalName] = useState('');
  const [industry, setIndustry] = useState<IndustryType>('medical');
  const [currency, setCurrency] = useState('USD');
  const [currencySymbol, setCurrencySymbol] = useState('$');

  const getIndustryIcon = (ind: IndustryType) => {
    switch (ind) {
      case 'medical':
        return Stethoscope;
      case 'restaurant':
        return Utensils;
      case 'manufacturing':
        return Factory;
      default:
        return Briefcase;
    }
  };

  const handleCreateClient = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const newClient: ClientProfile = {
      id: `client_${Date.now()}`,
      name: name.trim(),
      legalEntityName: legalName.trim() || `${name.trim()} LLC`,
      industry,
      industryName: industry === 'medical' ? 'Healthcare & Clinical Services' : industry === 'restaurant' ? 'Food & Beverage / Multi-Unit' : 'Precision Manufacturing & Assembly',
      businessDescription: 'Client operating entity and CFO advisory portfolio',
      entityType: 'LLC',
      country: 'United States',
      fiscalYearEnd: 'December 31',
      reportingPeriod: 'July 2026',
      businessSize: 'Mid-Market ($5M - $25M)',
      headcount: 24,
      currency,
      currencySymbol,
      taxId: '84-1928471',
      bankAccountMasked: '•••• 7712',
      contactEmail: 'finance@client.com',
      contactPhone: '+1 (555) 019-2831',
      privacyMode: 'strict',
      lastUpdated: new Date().toISOString(),
      createdDate: '2026-08-25',
    };

    onSelectClient(newClient);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 max-w-xl w-full overflow-hidden">
        {/* Header */}
        <div className="bg-slate-900 px-6 py-5 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600/30 rounded-xl text-indigo-400 border border-indigo-500/30">
              <Building className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-black text-white">
                Client Portfolio & Multi-Tenant Management
              </h3>
              <p className="text-xs text-slate-400">
                Switch active client workspace or onboard a new entity
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Toggle */}
        <div className="flex border-b border-slate-200 bg-slate-50 px-6 pt-3 gap-2">
          <button
            onClick={() => setActiveTab('switch')}
            className={`pb-3 text-xs font-bold border-b-2 transition-all px-2 ${
              activeTab === 'switch'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            Switch Active Client ({demoClients.length})
          </button>
          <button
            onClick={() => setActiveTab('create')}
            className={`pb-3 text-xs font-bold border-b-2 transition-all px-2 ${
              activeTab === 'create'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            + Onboard New Client
          </button>
        </div>

        {/* Body Content */}
        <div className="p-6">
          {activeTab === 'switch' ? (
            <div className="space-y-3">
              {demoClients.map(c => {
                const Icon = getIndustryIcon(c.industry);
                const isSelected = c.id === currentClient.id;

                return (
                  <div
                    key={c.id}
                    onClick={() => {
                      onSelectClient(c);
                      onClose();
                    }}
                    className={`p-4 rounded-2xl border transition-all cursor-pointer flex items-center justify-between ${
                      isSelected
                        ? 'bg-indigo-50/60 border-indigo-300 ring-2 ring-indigo-500/20'
                        : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center gap-3.5">
                      <div className="w-10 h-10 rounded-xl bg-slate-900 text-white flex items-center justify-center font-bold">
                        <Icon className="w-5 h-5 text-indigo-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-bold text-slate-900">{c.name}</h4>
                          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.2 rounded-full bg-slate-100 text-slate-700">
                            {c.industry}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {c.industryName} • Reporting: {c.reportingPeriod}
                        </p>
                      </div>
                    </div>

                    {isSelected && (
                      <span className="p-1.5 rounded-full bg-indigo-600 text-white">
                        <Check className="w-4 h-4" />
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <form onSubmit={handleCreateClient} className="space-y-4 text-xs">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Client Trading Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Acme Health Partners"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2 text-xs font-bold text-slate-900 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Legal Entity Registered Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Acme Health Partners Inc."
                  value={legalName}
                  onChange={e => setLegalName(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    Industry Benchmark Model
                  </label>
                  <select
                    value={industry}
                    onChange={e => setIndustry(e.target.value as IndustryType)}
                    className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-bold text-slate-900 focus:outline-hidden focus:border-indigo-500"
                  >
                    <option value="medical">Healthcare & Medical Practice</option>
                    <option value="restaurant">Restaurant & Hospitality</option>
                    <option value="manufacturing">Manufacturing & Assembly</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    Reporting Currency
                  </label>
                  <select
                    value={currency}
                    onChange={e => {
                      setCurrency(e.target.value);
                      setCurrencySymbol(e.target.value === 'EUR' ? '€' : e.target.value === 'GBP' ? '£' : '$');
                    }}
                    className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-bold text-slate-900 focus:outline-hidden focus:border-indigo-500"
                  >
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="GBP">GBP (£)</option>
                    <option value="CAD">CAD ($)</option>
                  </select>
                </div>
              </div>

              <div className="pt-3">
                <button
                  type="submit"
                  className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-md transition-colors"
                >
                  Onboard & Launch Workspace
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
