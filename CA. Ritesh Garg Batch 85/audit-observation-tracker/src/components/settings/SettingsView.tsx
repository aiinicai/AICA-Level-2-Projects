import React, { useState } from 'react';
import { 
  Settings, 
  Building2, 
  PlusCircle, 
  Trash2, 
  Edit3, 
  Save, 
  Download, 
  Upload, 
  RotateCcw, 
  CheckCircle2, 
  AlertCircle,
  Tag,
  ShieldCheck,
  Database
} from 'lucide-react';
import { AuditType, FirmProfile } from '../../types/audit';

interface SettingsViewProps {
  auditTypes: AuditType[];
  firmProfile: FirmProfile;
  onSaveAuditType: (type: Partial<AuditType> & { name: string; code: string }) => void;
  onDeleteAuditType: (id: string) => void;
  onSaveFirmProfile: (profile: FirmProfile) => void;
  onExportJsonBackup: () => void;
  onImportJsonBackup: (jsonStr: string) => boolean;
  onResetSampleData: () => void;
  onClearClientData?: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  auditTypes,
  firmProfile,
  onSaveAuditType,
  onDeleteAuditType,
  onSaveFirmProfile,
  onExportJsonBackup,
  onImportJsonBackup,
  onResetSampleData,
  onClearClientData,
}) => {
  // Firm Profile Form state
  const [profileForm, setProfileForm] = useState<FirmProfile>(firmProfile);
  const [profileSavedMsg, setProfileSavedMsg] = useState(false);

  // New/Edit Audit Type Form state
  const [editingType, setEditingType] = useState<AuditType | null>(null);
  const [newTypeName, setNewTypeName] = useState('');
  const [newTypeCode, setNewTypeCode] = useState('');
  const [newTypeDesc, setNewTypeDesc] = useState('');
  const [typeError, setTypeError] = useState('');
  const [typeSuccessMsg, setTypeSuccessMsg] = useState('');

  // Backup state
  const [importStatus, setImportStatus] = useState<string | null>(null);

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    onSaveFirmProfile(profileForm);
    setProfileSavedMsg(true);
    setTimeout(() => setProfileSavedMsg(false), 3000);
  };

  const handleStartEditType = (at: AuditType) => {
    setEditingType(at);
    setNewTypeName(at.name);
    setNewTypeCode(at.code);
    setNewTypeDesc(at.description || '');
    setTypeError('');
  };

  const handleCancelEditType = () => {
    setEditingType(null);
    setNewTypeName('');
    setNewTypeCode('');
    setNewTypeDesc('');
    setTypeError('');
  };

  const handleSaveAuditType = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTypeName.trim()) {
      setTypeError('Audit Type Name is required');
      return;
    }
    if (!newTypeCode.trim()) {
      setTypeError('Audit Type Code is required (e.g. SA, TA, CAG)');
      return;
    }

    onSaveAuditType({
      id: editingType ? editingType.id : undefined,
      name: newTypeName.trim(),
      code: newTypeCode.trim().toUpperCase(),
      description: newTypeDesc.trim() || undefined,
    });

    setTypeSuccessMsg(editingType ? 'Audit Type updated successfully' : 'New Audit Type added');
    setTimeout(() => setTypeSuccessMsg(''), 3000);
    handleCancelEditType();
  };

  const handleFileImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content) {
        const success = onImportJsonBackup(content);
        if (success) {
          setImportStatus('Backup restored successfully!');
        } else {
          setImportStatus('Failed to restore backup: Invalid file format');
        }
        setTimeout(() => setImportStatus(null), 4000);
      }
    };
    reader.readAsText(file);
  };

  return (
    <div id="settings-view-container" className="space-y-6">
      {/* Header */}
      <div className="bg-white p-5 rounded-2xl border border-stone-200 shadow-sm">
        <h1 className="text-xl font-bold text-stone-800 tracking-tight">Configuration & Master Setup</h1>
        <p className="text-sm text-stone-500 mt-0.5">
          Configure customizable audit types, CA firm letterhead credentials, and data backups.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Col: Configurable Audit Types Master */}
        <div className="bg-white p-6 rounded-2xl border border-stone-200 shadow-sm space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-stone-200">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#F5F2ED] text-[#5A5A40] flex items-center justify-center">
                <Tag className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-stone-800">Configurable Audit Types Master</h2>
                <p className="text-xs text-stone-500">
                  Add new audit types without code changes. Used for reference numbers and filters.
                </p>
              </div>
            </div>
          </div>

          {/* Form to add or edit audit type */}
          <form onSubmit={handleSaveAuditType} className="p-4 bg-stone-50 rounded-2xl border border-stone-200 space-y-3">
            <div className="text-xs font-bold text-stone-800">
              {editingType ? `Edit Audit Type: ${editingType.name}` : '+ Add New Audit Type'}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <label className="text-[11px] font-bold text-stone-700 block mb-1">Type Name *</label>
                <input
                  type="text"
                  value={newTypeName}
                  onChange={(e) => setNewTypeName(e.target.value)}
                  placeholder="e.g. Forensic Audit, CSR Audit"
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-stone-700 block mb-1">Prefix Code *</label>
                <input
                  type="text"
                  value={newTypeCode}
                  onChange={(e) => setNewTypeCode(e.target.value.toUpperCase())}
                  placeholder="e.g. FA, CSR"
                  maxLength={5}
                  className="w-full px-3 py-1.5 text-xs font-mono uppercase rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] font-bold text-stone-700 block mb-1">Scope / Description (Optional)</label>
              <input
                type="text"
                value={newTypeDesc}
                onChange={(e) => setNewTypeDesc(e.target.value)}
                placeholder="e.g. Special audit for fraud detection & fund diversion"
                className="w-full px-3 py-1.5 text-xs rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
              />
            </div>

            {typeError && (
              <p className="text-xs text-rose-600 font-medium">{typeError}</p>
            )}

            {typeSuccessMsg && (
              <p className="text-xs text-emerald-700 font-medium">{typeSuccessMsg}</p>
            )}

            <div className="flex items-center justify-end gap-2 pt-1">
              {editingType && (
                <button
                  type="button"
                  onClick={handleCancelEditType}
                  className="px-3 py-1 text-xs rounded-lg border border-stone-300 text-stone-700 hover:bg-stone-100 font-semibold"
                >
                  Cancel
                </button>
              )}
              <button
                type="submit"
                className="px-3.5 py-1.5 text-xs rounded-lg bg-[#5A5A40] hover:bg-[#4A4A34] text-white font-semibold shadow-xs transition-colors"
              >
                {editingType ? 'Update Type' : '+ Add Audit Type'}
              </button>
            </div>
          </form>

          {/* Existing types listing */}
          <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
            <div className="text-xs font-bold text-stone-700">Current Active Audit Types ({auditTypes.length})</div>
            <div className="divide-y divide-stone-100 border border-stone-200 rounded-xl overflow-hidden bg-white">
              {auditTypes.map((at) => (
                <div key={at.id} className="p-3 flex items-center justify-between gap-2 hover:bg-stone-50 transition-colors">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded-md bg-[#5A5A40] text-amber-300 font-mono font-bold text-[10px]">
                        {at.code}
                      </span>
                      <span className="text-xs font-bold text-stone-800">{at.name}</span>
                    </div>
                    {at.description && (
                      <p className="text-[11px] text-stone-500 line-clamp-1">{at.description}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => handleStartEditType(at)}
                      className="p-1 text-stone-500 hover:text-stone-900 hover:bg-stone-100 rounded-md"
                      title="Edit Type"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    {!at.isDefault && (
                      <button
                        onClick={() => {
                          if (window.confirm(`Delete custom audit type "${at.name}"?`)) {
                            onDeleteAuditType(at.id);
                          }
                        }}
                        className="p-1 text-stone-400 hover:text-rose-600 hover:bg-rose-50 rounded-md"
                        title="Delete Type"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Col: CA Firm Profile & Letterhead Master */}
        <div className="bg-white p-6 rounded-2xl border border-stone-200 shadow-sm space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-stone-200">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#F5F2ED] text-[#5A5A40] flex items-center justify-center">
                <Building2 className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-stone-800">CA Firm Letterhead Profile</h2>
                <p className="text-xs text-stone-500">
                  Populated on all PDF & Word audit reports, memorandums, and sign-off blocks.
                </p>
              </div>
            </div>
          </div>

          <form onSubmit={handleSaveProfile} className="space-y-3.5 text-xs">
            <div className="space-y-1">
              <label className="font-bold text-stone-700">CA Firm Name *</label>
              <input
                type="text"
                value={profileForm.firmName}
                onChange={(e) => setProfileForm({ ...profileForm, firmName: e.target.value })}
                required
                className="w-full px-3 py-1.5 rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="font-bold text-stone-700">ICAI Firm Reg. No. (FRN) *</label>
                <input
                  type="text"
                  value={profileForm.frn}
                  onChange={(e) => setProfileForm({ ...profileForm, frn: e.target.value })}
                  required
                  className="w-full px-3 py-1.5 rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
                />
              </div>

              <div className="space-y-1">
                <label className="font-bold text-stone-700">Partner Membership No. *</label>
                <input
                  type="text"
                  value={profileForm.membershipNo}
                  onChange={(e) => setProfileForm({ ...profileForm, membershipNo: e.target.value })}
                  required
                  className="w-full px-3 py-1.5 rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="font-bold text-stone-700">Engagement Partner Name *</label>
              <input
                type="text"
                value={profileForm.partnerName}
                onChange={(e) => setProfileForm({ ...profileForm, partnerName: e.target.value })}
                required
                className="w-full px-3 py-1.5 rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
              />
            </div>

            <div className="space-y-1">
              <label className="font-bold text-stone-700">Registered Office Address</label>
              <input
                type="text"
                value={profileForm.address}
                onChange={(e) => setProfileForm({ ...profileForm, address: e.target.value })}
                className="w-full px-3 py-1.5 rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="font-bold text-stone-700">City / State & PIN</label>
                <input
                  type="text"
                  value={profileForm.city}
                  onChange={(e) => setProfileForm({ ...profileForm, city: e.target.value })}
                  className="w-full px-3 py-1.5 rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
                />
              </div>

              <div className="space-y-1">
                <label className="font-bold text-stone-700">Official Email</label>
                <input
                  type="email"
                  value={profileForm.email}
                  onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })}
                  className="w-full px-3 py-1.5 rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="font-bold text-stone-700">Phone / Landline</label>
              <input
                type="text"
                value={profileForm.phone}
                onChange={(e) => setProfileForm({ ...profileForm, phone: e.target.value })}
                className="w-full px-3 py-1.5 rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
              />
            </div>

            {profileSavedMsg && (
              <div className="p-2 bg-emerald-50 text-emerald-800 rounded-lg flex items-center gap-1.5 text-xs font-semibold border border-emerald-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                Firm profile saved and applied to all report exports!
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                type="submit"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#5A5A40] hover:bg-[#4A4A34] text-white font-semibold shadow-xs transition-colors"
              >
                <Save className="w-4 h-4" />
                <span>Save Letterhead Profile</span>
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Bottom Section: Data Persistence & Backup */}
      <div className="bg-white p-6 rounded-2xl border border-stone-200 shadow-sm space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-stone-200">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
            <Database className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-stone-800">Data Persistence, Backup & Sample Data</h3>
            <p className="text-xs text-stone-500">
              All audit records persist in browser storage. You can backup to a JSON file or restore anytime.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 bg-stone-50 rounded-2xl border border-stone-200 space-y-2">
            <h4 className="text-xs font-bold text-stone-800">1. Download JSON</h4>
            <p className="text-[11px] text-stone-500">
              Save a full backup of all engagements, observations, audit types, and firm settings.
            </p>
            <button
              onClick={onExportJsonBackup}
              className="mt-2 w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#5A5A40] hover:bg-[#4A4A34] text-white text-xs font-semibold shadow-xs transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Backup</span>
            </button>
          </div>

          <div className="p-4 bg-stone-50 rounded-2xl border border-stone-200 space-y-2">
            <h4 className="text-xs font-bold text-stone-800">2. Restore JSON</h4>
            <p className="text-[11px] text-stone-500">
              Upload a previously exported JSON backup file to restore audit records.
            </p>
            <label className="mt-2 w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg border border-stone-300 bg-white hover:bg-[#F5F2ED] text-stone-700 text-xs font-semibold shadow-2xs transition-colors cursor-pointer">
              <Upload className="w-3.5 h-3.5" />
              <span>Select File</span>
              <input
                type="file"
                accept=".json"
                onChange={handleFileImport}
                className="hidden"
              />
            </label>
          </div>

          <div className="p-4 bg-stone-50 rounded-2xl border border-stone-200 space-y-2">
            <h4 className="text-xs font-bold text-stone-800">3. Clear All Client Data</h4>
            <p className="text-[11px] text-stone-500">
              Wipe all client engagements and observations to maintain a clean slate.
            </p>
            <button
              onClick={() => {
                if (window.confirm('Are you sure you want to remove all client engagements and observations?')) {
                  if (onClearClientData) {
                    onClearClientData();
                  }
                }
              }}
              className="mt-2 w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg border border-rose-300 bg-white hover:bg-rose-50 text-rose-700 text-xs font-semibold shadow-xs transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5 text-rose-600" />
              <span>Clear Client Data</span>
            </button>
          </div>

          <div className="p-4 bg-amber-50/50 rounded-2xl border border-amber-200/70 space-y-2">
            <h4 className="text-xs font-bold text-amber-950">4. Sample CA Data</h4>
            <p className="text-[11px] text-amber-900">
              Load realistic sample CA audit records (Stock Audit, Tax Audit, CAG, etc.).
            </p>
            <button
              onClick={() => {
                if (window.confirm('Load sample CA audit records? Current data will be replaced.')) {
                  onResetSampleData();
                }
              }}
              className="mt-2 w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#5A5A40] hover:bg-[#4A4A34] text-white text-xs font-semibold shadow-xs transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Load Sample Data</span>
            </button>
          </div>
        </div>

        {importStatus && (
          <div className="p-3 bg-[#5A5A40] text-white rounded-xl text-xs font-semibold">
            {importStatus}
          </div>
        )}
      </div>
    </div>
  );
};
