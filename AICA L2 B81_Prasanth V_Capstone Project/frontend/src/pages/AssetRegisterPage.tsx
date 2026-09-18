import React, { useState, useEffect } from 'react';
import {
  Layers,
  Search,
  Filter,
  Download,
  Printer,
  RefreshCw,
  Eye,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  X,
  FileText
} from 'lucide-react';
import api from '../services/api';
import { Asset, Company } from '../types';
import { useCompany } from '../context/CompanyContext';
import { AssetTagPreview } from '../components/AssetTagPreview';

export const AssetRegisterPage: React.FC = () => {
  const { companies } = useCompany();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [companyFilter, setCompanyFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedAssetIds, setSelectedAssetIds] = useState<number[]>([]);

  // Asset Details & Reprint Modal
  const [activeAsset, setActiveAsset] = useState<Asset | null>(null);
  const [showReprintModal, setShowReprintModal] = useState(false);
  const [reprintReason, setReprintReason] = useState('');
  const [reprinting, setReprinting] = useState(false);

  const fetchAssets = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (search) params.search = search;
      if (companyFilter) params.company_id = companyFilter;
      if (typeFilter) params.asset_type = typeFilter;
      if (statusFilter) params.status_filter = statusFilter;

      const res = await api.get<Asset[]>('/assets', { params });
      setAssets(res.data);
    } catch (e) {
      console.error('Error fetching assets:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      fetchAssets();
    }, 250);
    return () => clearTimeout(delayDebounce);
  }, [search, companyFilter, typeFilter, statusFilter]);

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedAssetIds(assets.map((a) => a.id));
    } else {
      setSelectedAssetIds([]);
    }
  };

  const handleToggleSelect = (id: number) => {
    setSelectedAssetIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleExportExcel = () => {
    const params = new URLSearchParams();
    if (companyFilter) params.append('company_id', companyFilter);
    if (typeFilter) params.append('asset_type', typeFilter);
    window.open(`/api/assets/export/excel?${params.toString()}`, '_blank');
  };

  const handleReprint = async () => {
    if (!activeAsset) return;
    if (!reprintReason.trim() || reprintReason.trim().length < 3) {
      alert('Please provide a valid reprint reason.');
      return;
    }
    setReprinting(true);
    try {
      const res = await api.post<Asset>(`/assets/${activeAsset.id}/reprint`, {
        reason: reprintReason.trim(),
      });
      setActiveAsset(res.data);
      setShowReprintModal(false);
      setReprintReason('');
      fetchAssets();
    } catch (e: any) {
      alert('Failed to reprint asset.');
    } finally {
      setReprinting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Asset Register & Generation History</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Query, inspect, reprint, and export all corporate asset tags and physical print statuses
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportExcel}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-sm transition"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            Export to Excel (.xlsx)
          </button>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {/* Search */}
        <div className="lg:col-span-2 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search Asset ID, SAP No, Description, Serial, Custodian..."
            className="w-full text-xs pl-9 pr-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Company Filter */}
        <div>
          <select
            value={companyFilter}
            onChange={(e) => setCompanyFilter(e.target.value)}
            className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Companies</option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.short_name}
              </option>
            ))}
          </select>
        </div>

        {/* Asset Type Filter */}
        <div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Asset Types</option>
            <option value="FIXED_ASSET">Fixed Asset</option>
            <option value="STOCK">Stock / Inventory</option>
          </select>
        </div>

        {/* Status Filter */}
        <div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Statuses</option>
            <option value="GENERATED">Generated</option>
            <option value="PRINTED">Printed</option>
            <option value="REPRINTED">Reprinted</option>
          </select>
        </div>
      </div>

      {/* Asset Register Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-3 bg-slate-50/70 border-b border-slate-200 flex items-center justify-between text-xs text-slate-600 font-medium">
          <div className="flex items-center gap-2">
            <span>Showing <strong className="text-slate-900">{assets.length}</strong> records</span>
            {selectedAssetIds.length > 0 && (
              <span className="bg-blue-100 text-blue-800 font-bold px-2 py-0.5 rounded text-[11px]">
                {selectedAssetIds.length} selected
              </span>
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 uppercase text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-3 text-center w-10">
                  <input
                    type="checkbox"
                    checked={assets.length > 0 && selectedAssetIds.length === assets.length}
                    onChange={handleSelectAll}
                    className="rounded text-blue-600 focus:ring-blue-500"
                  />
                </th>
                <th className="py-3 px-3">Asset ID</th>
                <th className="py-3 px-3">Company</th>
                <th className="py-3 px-3">Type</th>
                <th className="py-3 px-3">Description</th>
                <th className="py-3 px-3">Location</th>
                <th className="py-3 px-3">SAP No</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3 text-center">Prints</th>
                <th className="py-3 px-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-400">
                    <RefreshCw className="w-4 h-4 animate-spin inline-block mr-2" />
                    Querying records...
                  </td>
                </tr>
              ) : assets.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-400">
                    No matching asset tags found.
                  </td>
                </tr>
              ) : (
                assets.map((asset) => (
                  <tr
                    key={asset.id}
                    className="hover:bg-slate-50/70 transition cursor-pointer"
                    onClick={() => setActiveAsset(asset)}
                  >
                    <td className="py-3 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedAssetIds.includes(asset.id)}
                        onChange={() => handleToggleSelect(asset.id)}
                        className="rounded text-blue-600 focus:ring-blue-500"
                      />
                    </td>
                    <td className="py-3 px-3 font-mono font-bold text-slate-900">
                      {asset.asset_id}
                    </td>
                    <td className="py-3 px-3 font-semibold text-slate-700 truncate max-w-[130px]">
                      {asset.company_name || '—'}
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          asset.asset_type === 'FIXED_ASSET'
                            ? 'bg-blue-50 text-blue-700 border border-blue-200'
                            : 'bg-purple-50 text-purple-700 border border-purple-200'
                        }`}
                      >
                        {asset.asset_type === 'FIXED_ASSET' ? 'Fixed Asset' : 'Stock'}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-semibold text-slate-900 truncate max-w-[160px]">
                      {asset.description || '—'}
                    </td>
                    <td className="py-3 px-3 text-slate-600 truncate max-w-[100px]">
                      {asset.location || '—'}
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-600">
                      {asset.sap_number || '—'}
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded ${
                          asset.status === 'PRINTED'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : asset.status === 'REPRINTED'
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {asset.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center font-mono font-semibold text-slate-700">
                      {asset.print_count}
                    </td>
                    <td className="py-3 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => setActiveAsset(asset)}
                        className="p-1 text-slate-500 hover:text-blue-600 hover:bg-slate-100 rounded transition"
                        title="View Asset Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Asset Detail & Reprint Drawer Modal */}
      {activeAsset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-2xl w-full p-6 space-y-5 animate-in fade-in">
            {/* Header */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900">Asset Record Details</h3>
                <div className="text-xs font-mono font-semibold text-blue-600">{activeAsset.asset_id}</div>
              </div>
              <button
                onClick={() => setActiveAsset(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tag Preview */}
            <div className="flex justify-center p-4 bg-slate-50 rounded-xl border border-slate-200/80">
              <AssetTagPreview
                companyName={activeAsset.company_name || 'REFERENCE'}
                logoUrl={activeAsset.company_logo_path}
                assetId={activeAsset.asset_id}
                sapNumber={activeAsset.sap_number}
                description={activeAsset.description}
                location={activeAsset.location}
                codeType={activeAsset.code_type}
                showActions={true}
                id={activeAsset.id}
              />
            </div>

            {/* Metadata Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs bg-slate-50/50 p-4 rounded-xl border border-slate-200/60">
              <div>
                <div className="text-slate-500 font-medium">Department</div>
                <div className="font-bold text-slate-900">{activeAsset.department || '—'}</div>
              </div>
              <div>
                <div className="text-slate-500 font-medium">Cost Centre</div>
                <div className="font-bold text-slate-900">{activeAsset.cost_centre || '—'}</div>
              </div>
              <div>
                <div className="text-slate-500 font-medium">Custodian</div>
                <div className="font-bold text-slate-900">{activeAsset.custodian || '—'}</div>
              </div>
              <div>
                <div className="text-slate-500 font-medium">Serial No</div>
                <div className="font-bold text-slate-900">{activeAsset.serial_number || '—'}</div>
              </div>
              <div>
                <div className="text-slate-500 font-medium">Created Date</div>
                <div className="font-bold text-slate-900">{activeAsset.created_at?.substring(0, 10)}</div>
              </div>
              <div>
                <div className="text-slate-500 font-medium">Reprint Count</div>
                <div className="font-bold text-amber-700 font-mono">{activeAsset.print_count} times</div>
              </div>
            </div>

            {/* Override status note */}
            {activeAsset.is_override && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900">
                <div className="font-bold flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  Duplicate Override Record
                </div>
                <div className="mt-1">Reason: "{activeAsset.override_reason}"</div>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowReprintModal(true)}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-lg transition"
              >
                <RotateCcw className="w-4 h-4" />
                Reprint Tag
              </button>

              <button
                type="button"
                onClick={() => setActiveAsset(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reprint Justification Modal */}
      {showReprintModal && activeAsset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-amber-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 text-amber-700 rounded-lg">
                <RotateCcw className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">Reprint Asset Tag</h4>
                <div className="text-xs font-mono text-slate-500">{activeAsset.asset_id}</div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Reason for Reprinting <span className="text-red-500">*</span>
              </label>
              <textarea
                rows={3}
                value={reprintReason}
                onChange={(e) => setReprintReason(e.target.value)}
                placeholder="e.g., Physical label damaged, adhesive failure, re-location..."
                className="w-full text-xs rounded-lg border border-slate-300 p-2.5 focus:outline-none focus:ring-2 focus:ring-amber-500"
              />
              <p className="mt-1 text-[11px] text-slate-500">
                Reprinting will increment the print counter and record this in the audit log.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowReprintModal(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleReprint}
                disabled={reprinting}
                className="px-4 py-1.5 text-xs font-bold bg-amber-600 hover:bg-amber-700 text-white rounded-lg transition"
              >
                {reprinting ? 'Logging...' : 'Confirm Reprint'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
