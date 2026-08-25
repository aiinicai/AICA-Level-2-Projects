import React, { useState } from 'react';
import {
  Users,
  Plus,
  Building2,
  CheckCircle2,
  XCircle,
  Edit2,
  Trash2,
  ShieldAlert,
  Search,
  Check,
  Mail,
  Sliders,
  Globe,
  FileText,
} from 'lucide-react';
import { ClientMaster, EntityType, ExposureLevel, CommunicationLanguage } from '../types';

interface ClientMasterViewProps {
  clients: ClientMaster[];
  onAddClient: (client: ClientMaster) => void;
  onUpdateClient: (client: ClientMaster) => void;
  onDeleteClient: (id: string) => void;
}

export const ClientMasterView: React.FC<ClientMasterViewProps> = ({
  clients,
  onAddClient,
  onUpdateClient,
  onDeleteClient,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEntityType, setSelectedEntityType] = useState('All');
  const [selectedIndustry, setSelectedIndustry] = useState('All');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<ClientMaster | null>(null);

  // Form State
  const [clientName, setClientName] = useState('');
  const [entityType, setEntityType] = useState<EntityType>('Private Limited');
  const [industry, setIndustry] = useState('');
  const [state, setState] = useState('Maharashtra');
  const [annualTurnoverRange, setAnnualTurnoverRange] = useState('₹25 Cr - ₹100 Cr');
  const [gstRegistered, setGstRegistered] = useState(true);
  const [gstin, setGstin] = useState('');
  const [udyamRegistration, setUdyamRegistration] = useState(true);
  const [udyamRegNo, setUdyamRegNo] = useState('');
  const [msmeStatus, setMsmeStatus] = useState<'Micro' | 'Small' | 'Medium' | 'Non-MSME'>('Small');
  const [tdsApplicable, setTdsApplicable] = useState(true);
  const [mcaApplicable, setMcaApplicable] = useState(true);
  const [payroll, setPayroll] = useState(true);
  const [numberOfEmployees, setNumberOfEmployees] = useState(30);
  const [pfApplicable, setPfApplicable] = useState(true);
  const [esiApplicable, setEsiApplicable] = useState(true);
  const [importer, setImporter] = useState(false);
  const [exporter, setExporter] = useState(false);
  const [femaExposure, setFemaExposure] = useState<ExposureLevel>('Medium');
  const [forexExposure, setForexExposure] = useState<ExposureLevel>('Medium');
  const [crudeSensitivity, setCrudeSensitivity] = useState<ExposureLevel>('None');
  const [borrowings, setBorrowings] = useState<ExposureLevel>('Medium');
  const [borrowingsAmount, setBorrowingsAmount] = useState('');
  const [preferredLanguage, setPreferredLanguage] = useState<CommunicationLanguage>('English');
  const [clientEmail, setClientEmail] = useState('');
  const [notes, setNotes] = useState('');

  const filteredClients = clients.filter((c) => {
    const matchesSearch =
      c.clientName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.industry.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.gstin && c.gstin.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesEntity = selectedEntityType === 'All' || c.entityType === selectedEntityType;
    const matchesIndustry = selectedIndustry === 'All' || c.industry === selectedIndustry;
    return matchesSearch && matchesEntity && matchesIndustry;
  });

  const handleOpenAddModal = () => {
    setEditingClient(null);
    setClientName('');
    setEntityType('Private Limited');
    setIndustry('Retail & Distribution');
    setGstin('27AABCU9603R1ZM');
    setUdyamRegNo('UDYAM-MH-03-0021458');
    setPreferredLanguage('English');
    setClientEmail('accounts@client.example.com');
    setNotes('');
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (client: ClientMaster) => {
    setEditingClient(client);
    setClientName(client.clientName);
    setEntityType(client.entityType);
    setIndustry(client.industry);
    setState(client.state);
    setAnnualTurnoverRange(client.annualTurnoverRange);
    setGstRegistered(client.gstRegistered);
    setGstin(client.gstin || '');
    setUdyamRegistration(client.udyamRegistration || false);
    setUdyamRegNo(client.udyamRegNo || '');
    setMsmeStatus(client.msmeStatus || 'Small');
    setTdsApplicable(client.tdsApplicable);
    setMcaApplicable(client.mcaApplicable);
    setPayroll(client.payroll);
    setNumberOfEmployees(client.numberOfEmployees);
    setPfApplicable(client.pfApplicable);
    setEsiApplicable(client.esiApplicable);
    setImporter(client.importer);
    setExporter(client.exporter);
    setFemaExposure(client.femaExposure);
    setForexExposure(client.forexExposure);
    setCrudeSensitivity(client.crudeSensitivity);
    setBorrowings(client.borrowings);
    setBorrowingsAmount(client.borrowingsAmount || '');
    setPreferredLanguage(client.preferredLanguage || 'English');
    setClientEmail(client.clientEmail);
    setNotes(client.notes);
    setIsModalOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientName) return;

    const record: ClientMaster = {
      id: editingClient ? editingClient.id : `cli_${Date.now()}`,
      clientName,
      entityType,
      industry,
      state,
      annualTurnoverRange,
      gstRegistered,
      gstin,
      udyamRegistration,
      udyamRegNo,
      msmeStatus,
      tdsApplicable,
      mcaApplicable,
      payroll,
      numberOfEmployees,
      pfApplicable,
      esiApplicable,
      importer,
      exporter,
      femaExposure,
      forexExposure,
      hasFemaExposure: femaExposure !== 'None',
      hasForeignCurrencyExposure: forexExposure !== 'None',
      crudeSensitivity,
      commoditySensitivity: 'None',
      borrowings,
      borrowingsAmount,
      listed: false,
      riskCategory: 'Medium',
      clientEmail: clientEmail || `finance@${clientName.toLowerCase().replace(/\s+/g, '')}.com`,
      preferredCommunicationStyle: 'Formal Advisory',
      preferredLanguage,
      notes,
    };

    if (editingClient) {
      onUpdateClient(record);
    } else {
      onAddClient(record);
    }

    setIsModalOpen(false);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-teal-600 mb-1">
            <Users className="w-4 h-4" />
            <span>MODULE 5 — CA CLIENT MASTER DIRECTORY V2</span>
          </div>
          <h1 className="text-xl font-bold text-slate-900">Client Master Directory ({clients.length})</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Structured client entity profiles with GSTIN, MSME, turnover & language settings.
          </p>
        </div>

        <button
          onClick={handleOpenAddModal}
          className="flex items-center space-x-2 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-4 py-2.5 rounded-xl shadow-md transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>ADD NEW CLIENT PROFILE</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-xs flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search client name, GSTIN, industry..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:bg-white focus:outline-none"
          />
        </div>

        <select
          value={selectedEntityType}
          onChange={(e) => setSelectedEntityType(e.target.value)}
          className="bg-slate-50 border border-slate-200 text-slate-700 px-3 py-1.5 rounded-lg text-xs"
        >
          <option value="All">All Entity Types</option>
          <option value="Private Limited">Private Limited</option>
          <option value="Public Limited">Public Limited</option>
          <option value="LLP">LLP</option>
          <option value="Partnership">Partnership</option>
          <option value="Sole Proprietorship">Sole Proprietorship</option>
        </select>
      </div>

      {/* Client Master Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredClients.map((client) => (
          <div
            key={client.id}
            className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs hover:shadow-md transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div>
                  <h3 className="text-base font-bold text-slate-900 leading-snug">{client.clientName}</h3>
                  <div className="flex items-center space-x-2 text-xs text-slate-500 mt-0.5">
                    <span className="font-semibold text-teal-700">{client.entityType}</span>
                    <span>•</span>
                    <span>{client.state}</span>
                  </div>
                </div>
                <span className="px-2.5 py-0.5 bg-slate-100 text-slate-700 font-bold text-[10px] rounded-full border border-slate-200">
                  {client.annualTurnoverRange}
                </span>
              </div>

              <div className="text-xs font-semibold text-slate-700 mt-2 mb-2 bg-slate-50 p-2.5 rounded-xl border border-slate-100 space-y-1">
                <div>
                  Industry: <span className="text-slate-900 font-bold">{client.industry}</span>
                </div>
                {client.gstin && (
                  <div>
                    GSTIN: <span className="font-mono text-teal-800 font-bold">{client.gstin}</span>
                  </div>
                )}
                {client.udyamRegNo && (
                  <div>
                    Udyam: <span className="font-mono text-slate-800">{client.udyamRegNo} ({client.msmeStatus})</span>
                  </div>
                )}
                <div>
                  Language: <span className="font-bold text-indigo-700">{client.preferredLanguage || 'English'}</span>
                </div>
              </div>

              {/* Statutory Compliance Badges */}
              <div className="grid grid-cols-2 gap-1.5 text-[11px] mb-3">
                <div className="flex items-center space-x-1 text-slate-700">
                  {client.gstRegistered ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-slate-300 shrink-0" />
                  )}
                  <span>GST Registered</span>
                </div>

                <div className="flex items-center space-x-1 text-slate-700">
                  {client.mcaApplicable ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-slate-300 shrink-0" />
                  )}
                  <span>MCA Corporate</span>
                </div>

                <div className="flex items-center space-x-1 text-slate-700">
                  {client.importer || client.exporter ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-slate-300 shrink-0" />
                  )}
                  <span>Trade Forex: {client.forexExposure}</span>
                </div>

                <div className="flex items-center space-x-1 text-slate-700">
                  {client.payroll ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-slate-300 shrink-0" />
                  )}
                  <span>{client.numberOfEmployees} Employees</span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-[11px] text-slate-400 truncate max-w-[160px]">{client.clientEmail}</span>
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => handleOpenEditModal(client)}
                  className="p-1.5 text-slate-500 hover:text-teal-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                  title="Edit Client"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => onDeleteClient(client.id)}
                  className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                  title="Delete Client"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Add / Edit Client Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl space-y-4">
            <h2 className="text-lg font-bold text-slate-900">
              {editingClient ? 'Edit Client Profile V2' : 'Add New Client Master Profile V2'}
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Client Entity Name *</label>
                <input
                  type="text"
                  required
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  placeholder="e.g. Acme Manufacturing Pvt Ltd"
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Entity Type</label>
                  <select
                    value={entityType}
                    onChange={(e) => setEntityType(e.target.value as EntityType)}
                    className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl"
                  >
                    <option value="Private Limited">Private Limited</option>
                    <option value="Public Limited">Public Limited</option>
                    <option value="LLP">LLP</option>
                    <option value="Partnership">Partnership</option>
                    <option value="Sole Proprietorship">Sole Proprietorship</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Industry Sector</label>
                  <input
                    type="text"
                    required
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    placeholder="e.g. Retail, Manufacturing, IT Services"
                    className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">GSTIN Number</label>
                  <input
                    type="text"
                    value={gstin}
                    onChange={(e) => setGstin(e.target.value)}
                    placeholder="27AABCU9603R1ZM"
                    className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl font-mono"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Preferred Language</label>
                  <select
                    value={preferredLanguage}
                    onChange={(e) => setPreferredLanguage(e.target.value as CommunicationLanguage)}
                    className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl"
                  >
                    <option value="English">English</option>
                    <option value="English + Malayalam">English + Malayalam (മലയാളത്തിൽ)</option>
                    <option value="English + Hindi">English + Hindi (हिंदी में)</option>
                    <option value="English + Tamil">English + Tamil (தமிழில்)</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-slate-600 font-semibold rounded-xl hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-teal-600 text-white font-bold rounded-xl hover:bg-teal-700"
                >
                  Save Client
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
