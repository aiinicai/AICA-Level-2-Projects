import React, { useState } from 'react';
import { useCompany } from '../context/CompanyContext';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { Company } from '../types';
import {
  Building2,
  Plus,
  Edit2,
  Upload,
  CheckCircle2,
  Image as ImageIcon,
  Sliders,
  Layers,
  X
} from 'lucide-react';

export const CompanyManagementPage: React.FC = () => {
  const { companies, refreshCompanies } = useCompany();
  const { isAdmin } = useAuth();

  const [showModal, setShowModal] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [shortName, setShortName] = useState('');
  const [address, setAddress] = useState('');
  const [prefix, setPrefix] = useState('FA');
  const [format, setFormat] = useState('{PREFIX}-{NUM:6}');
  const [startingNumber, setStartingNumber] = useState(1);
  const [isActive, setIsActive] = useState(true);

  // Logo upload state
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [uploadingLogoId, setUploadingLogoId] = useState<number | null>(null);

  const openCreateModal = () => {
    setIsEditing(false);
    setEditId(null);
    setName('');
    setShortName('');
    setAddress('');
    setPrefix('FA');
    setFormat('{PREFIX}-{NUM:6}');
    setStartingNumber(1);
    setIsActive(true);
    setShowModal(true);
  };

  const openEditModal = (c: Company) => {
    setIsEditing(true);
    setEditId(c.id);
    setName(c.name);
    setShortName(c.short_name);
    setAddress(c.address || '');
    setPrefix(c.asset_id_prefix);
    setFormat(c.numbering_format);
    setStartingNumber(c.starting_number);
    setIsActive(c.is_active);
    setShowModal(true);
  };

  const handleSaveCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !shortName || !prefix) {
      alert('Please fill in all mandatory fields.');
      return;
    }

    try {
      if (isEditing && editId) {
        await api.put(`/companies/${editId}`, {
          name,
          short_name: shortName,
          address,
          asset_id_prefix: prefix,
          numbering_format: format,
          starting_number: startingNumber,
          is_active: isActive,
        });
      } else {
        await api.post('/companies', {
          name,
          short_name: shortName,
          address,
          asset_id_prefix: prefix,
          numbering_format: format,
          starting_number: startingNumber,
          is_active: isActive,
        });
      }
      setShowModal(false);
      refreshCompanies();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save company.');
    }
  };

  const handleLogoUpload = async (companyId: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    setUploadingLogoId(companyId);

    try {
      await api.post(`/companies/${companyId}/logo`, formData);
      refreshCompanies();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to upload logo.');
    } finally {
      setUploadingLogoId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Company Management</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure multi-tenant company profiles, logos, asset prefixes, and custom numbering rules
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg shadow-sm transition"
          >
            <Plus className="w-4 h-4" />
            Add New Company
          </button>
        )}
      </div>

      {/* Companies Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {companies.map((comp) => (
          <div
            key={comp.id}
            className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition flex flex-col justify-between"
          >
            <div>
              {/* Header with Logo */}
              <div className="flex items-start justify-between gap-3 pb-3 border-b border-slate-100">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center p-1 overflow-hidden">
                    {comp.logo_path ? (
                      <img src={comp.logo_path} alt={comp.name} className="w-full h-full object-contain" />
                    ) : (
                      <Building2 className="w-6 h-6 text-slate-400" />
                    )}
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 line-clamp-1">{comp.name}</h3>
                    <span className="text-[10px] font-mono bg-blue-50 text-blue-700 font-bold px-1.5 py-0.5 rounded border border-blue-200">
                      Code: {comp.short_name}
                    </span>
                  </div>
                </div>

                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    comp.is_active
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-slate-100 text-slate-500'
                  }`}
                >
                  {comp.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>

              {/* Company Details */}
              <div className="py-3 space-y-2 text-xs">
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                    <span className="text-[10px] text-slate-500 block">Prefix</span>
                    <span className="font-mono font-bold text-slate-900">{comp.asset_id_prefix}</span>
                  </div>
                  <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                    <span className="text-[10px] text-slate-500 block">Current Counter</span>
                    <span className="font-mono font-bold text-blue-600">{comp.current_number}</span>
                  </div>
                </div>

                <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                  <span className="text-[10px] text-slate-500 block">Format Pattern</span>
                  <span className="font-mono font-bold text-slate-800 text-[11px]">{comp.numbering_format}</span>
                </div>

                {comp.address && (
                  <p className="text-[11px] text-slate-500 line-clamp-2 mt-1">
                    {comp.address}
                  </p>
                )}
              </div>
            </div>

            {/* Card Actions */}
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
              {/* Logo upload input */}
              <label className="text-[11px] font-semibold text-blue-600 hover:text-blue-700 cursor-pointer flex items-center gap-1">
                <Upload className="w-3.5 h-3.5" />
                <span>{uploadingLogoId === comp.id ? 'Uploading...' : 'Upload Logo'}</span>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/svg+xml"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleLogoUpload(comp.id, e.target.files[0]);
                    }
                  }}
                />
              </label>

              {isAdmin && (
                <button
                  onClick={() => openEditModal(comp)}
                  className="text-[11px] font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                  Edit
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Add / Edit Company Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-lg w-full p-6 space-y-4 animate-in fade-in">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">
                {isEditing ? 'Edit Company Profile' : 'Add New Client / Company'}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveCompany} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Company Full Legal Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Tata Consultancy Services Ltd"
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 font-medium"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Short Name / Code <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={shortName}
                    onChange={(e) => setShortName(e.target.value)}
                    placeholder="e.g. TATA"
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 font-medium"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Asset ID Prefix <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={prefix}
                    onChange={(e) => setPrefix(e.target.value.toUpperCase())}
                    placeholder="e.g. FA / BIO / INV"
                    className="w-full text-xs font-mono font-bold bg-slate-50 border border-slate-300 rounded-lg p-2 uppercase"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Numbering Pattern Format
                </label>
                <input
                  type="text"
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                  placeholder="e.g. {PREFIX}-{NUM:6} or {PREFIX}/{YEAR}/{NUM:6}"
                  className="w-full text-xs font-mono bg-slate-50 border border-slate-300 rounded-lg p-2 font-bold text-slate-800"
                />
                <p className="mt-1 text-[10px] text-slate-500">
                  Supported tokens: &#123;PREFIX&#125;, &#123;YEAR&#125;, &#123;YY&#125;, &#123;NUM:6&#125;, &#123;NUM:5&#125;, &#123;NUM:4&#125;
                </p>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Corporate Address</label>
                <textarea
                  rows={2}
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="Office / facility address..."
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="company-active-chk"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="company-active-chk" className="text-xs font-semibold text-slate-700 cursor-pointer">
                  Company is Active
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
                >
                  Save Company Profile
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
