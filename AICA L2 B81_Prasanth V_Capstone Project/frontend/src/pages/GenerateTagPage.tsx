import React, { useState, useEffect } from 'react';
import { useCompany } from '../context/CompanyContext';
import { AssetTagPreview } from '../components/AssetTagPreview';
import { DuplicateWarningModal } from '../components/DuplicateWarningModal';
import api from '../services/api';
import { Asset, AssetType, CodeType } from '../types';
import {
  Tag,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Download,
  FileText,
  Printer,
  RefreshCw,
  Sliders,
  Layers
} from 'lucide-react';

export const GenerateTagPage: React.FC = () => {
  const { companies, selectedCompany, setSelectedCompany } = useCompany();

  // Form State
  const [assetType, setAssetType] = useState<AssetType>('FIXED_ASSET');
  const [idMode, setIdMode] = useState<'MANUAL' | 'AUTO'>('MANUAL');
  const [manualAssetId, setManualAssetId] = useState('');
  const [autoAssetId, setAutoAssetId] = useState('');
  const [sapNumber, setSapNumber] = useState('36007672-0');
  const [description, setDescription] = useState('WEIG-MCHN');
  const [location, setLocation] = useState('MCP');
  const [serialNumber, setSerialNumber] = useState('');
  const [department, setDepartment] = useState('Production');
  const [costCentre, setCostCentre] = useState('CC-4010');
  const [custodian, setCustodian] = useState('Rajesh Kumar');
  const [purchaseDate, setPurchaseDate] = useState('');
  const [codeType, setCodeType] = useState<CodeType>('BARCODE');

  // Dimension settings
  const [labelWidth, setLabelWidth] = useState(70);
  const [labelHeight, setLabelHeight] = useState(35);

  // Status & Duplicate Controls
  const [isDuplicate, setIsDuplicate] = useState(false);
  const [existingRecord, setExistingRecord] = useState<any>(null);
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [createdAsset, setCreatedAsset] = useState<Asset | null>(null);
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  // Fetch next available auto ID when company changes
  const fetchNextAutoId = async () => {
    if (!selectedCompany) return;
    try {
      const res = await api.get<{ next_asset_id: string }>(`/companies/${selectedCompany.id}/next-asset-id`);
      setAutoAssetId(res.data.next_asset_id);
    } catch (e) {
      console.error('Failed to get next ID:', e);
    }
  };

  useEffect(() => {
    fetchNextAutoId();
  }, [selectedCompany]);

  const activeAssetId = idMode === 'AUTO' ? autoAssetId : manualAssetId;

  // Real-time duplicate check
  const handleCheckDuplicate = async (idToCheck: string) => {
    if (!selectedCompany || !idToCheck.trim() || idMode === 'AUTO') {
      setIsDuplicate(false);
      return;
    }
    try {
      const res = await api.post('/assets/check-duplicate', {
        company_id: selectedCompany.id,
        asset_id: idToCheck.trim(),
      });
      setIsDuplicate(res.data.is_duplicate);
      setExistingRecord(res.data.existing_asset);
    } catch (e) {
      console.error('Duplicate check error:', e);
    }
  };

  // Submission handler
  const handleGenerate = async (overrideReason?: string) => {
    if (!selectedCompany) return;
    if (idMode === 'MANUAL' && !manualAssetId.trim()) {
      alert('Please enter an Asset ID.');
      return;
    }
    if (!description.trim()) {
      alert('Asset Description is required.');
      return;
    }

    // If duplicate detected and no override reason provided yet, open modal
    if (isDuplicate && !overrideReason) {
      setShowOverrideModal(true);
      return;
    }

    setLoading(true);
    setSuccessMessage('');

    try {
      const payload = {
        company_id: selectedCompany.id,
        asset_id: idMode === 'AUTO' ? '' : manualAssetId.trim(),
        auto_generate_id: idMode === 'AUTO',
        asset_type: assetType,
        description: description.trim(),
        location: location.trim(),
        sap_number: sapNumber.trim(),
        serial_number: serialNumber.trim() || null,
        department: department.trim() || null,
        cost_centre: costCentre.trim() || null,
        custodian: custodian.trim() || null,
        purchase_date: purchaseDate || null,
        code_type: codeType,
        is_override: !!overrideReason,
        override_reason: overrideReason || null,
      };

      const res = await api.post<Asset>('/assets', payload);
      setCreatedAsset(res.data);
      setShowOverrideModal(false);
      setSuccessMessage(
        overrideReason
          ? `Asset Tag ${res.data.asset_id} generated successfully with duplicate override audit!`
          : `Asset Tag ${res.data.asset_id} generated successfully!`
      );
      // Refresh auto sequence for next tag
      fetchNextAutoId();
    } catch (err: any) {
      if (err.response?.data?.detail?.includes('Duplicate')) {
        setIsDuplicate(true);
        setShowOverrideModal(true);
      } else {
        alert(err.response?.data?.detail || 'Failed to generate tag.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Generate Asset Tag</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Create scannable Barcode & QR asset labels with duplicate prevention controls
          </p>
        </div>
        {successMessage && (
          <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs px-3.5 py-2 rounded-lg font-medium animate-in fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            {successMessage}
          </div>
        )}
      </div>

      {/* Two Column Layout: Generator Form & Live Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Form (7 Cols) */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-5">
          {/* Section 1: Company & Asset Type */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pb-4 border-b border-slate-100">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1.5">
                Target Company <span className="text-red-500">*</span>
              </label>
              <select
                value={selectedCompany?.id || ''}
                onChange={(e) => {
                  const comp = companies.find((c) => c.id === Number(e.target.value));
                  if (comp) setSelectedCompany(comp);
                }}
                className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 font-medium text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              >
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.asset_id_prefix})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1.5">
                Asset Classification <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setAssetType('FIXED_ASSET')}
                  className={`py-2 px-3 text-xs font-bold rounded-lg border text-center transition ${
                    assetType === 'FIXED_ASSET'
                      ? 'bg-blue-50 border-blue-500 text-blue-700 shadow-2xs'
                      : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  Fixed Asset
                </button>
                <button
                  type="button"
                  onClick={() => setAssetType('STOCK')}
                  className={`py-2 px-3 text-xs font-bold rounded-lg border text-center transition ${
                    assetType === 'STOCK'
                      ? 'bg-blue-50 border-blue-500 text-blue-700 shadow-2xs'
                      : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  Stock / Inventory
                </button>
              </div>
            </div>
          </div>

          {/* Section 2: Asset ID Mode (Manual vs Auto) */}
          <div className="pb-4 border-b border-slate-100">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold text-slate-700">
                Asset ID Allocation Mode <span className="text-red-500">*</span>
              </label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setIdMode('MANUAL');
                    setIsDuplicate(false);
                  }}
                  className={`px-2.5 py-1 text-xs font-semibold rounded-md border transition ${
                    idMode === 'MANUAL'
                      ? 'bg-slate-900 text-white border-slate-900'
                      : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  Option A: Manual Entry
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIdMode('AUTO');
                    setIsDuplicate(false);
                    fetchNextAutoId();
                  }}
                  className={`px-2.5 py-1 text-xs font-semibold rounded-md border transition flex items-center gap-1 ${
                    idMode === 'AUTO'
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Option B: Auto Generate
                </button>
              </div>
            </div>

            {idMode === 'MANUAL' ? (
              <div>
                <div className="relative">
                  <input
                    type="text"
                    value={manualAssetId}
                    onChange={(e) => {
                      setManualAssetId(e.target.value.toUpperCase());
                      setIsDuplicate(false);
                    }}
                    onBlur={() => handleCheckDuplicate(manualAssetId)}
                    placeholder="e.g. FA-000001 or AST-9021"
                    className={`w-full text-xs font-mono font-bold bg-slate-50 border rounded-lg p-2.5 text-slate-900 uppercase focus:outline-none focus:ring-2 ${
                      isDuplicate
                        ? 'border-amber-500 focus:ring-amber-500 bg-amber-50/30'
                        : 'border-slate-300 focus:ring-blue-500'
                    }`}
                  />
                  {isDuplicate && (
                    <div className="mt-1.5 flex items-center justify-between text-xs text-amber-700 bg-amber-50 border border-amber-200 p-2 rounded-lg font-medium">
                      <div className="flex items-center gap-1.5">
                        <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                        <span>Duplicate Asset ID detected in database!</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setShowOverrideModal(true)}
                        className="text-[11px] font-bold text-amber-900 underline hover:text-amber-950"
                      >
                        Override Justification
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between bg-blue-50/70 border border-blue-200 p-3 rounded-lg">
                <div>
                  <div className="text-xs text-blue-900 font-medium">Next Atomic Numbering Sequence:</div>
                  <div className="text-sm font-mono font-black text-blue-700">{autoAssetId || 'Calculating...'}</div>
                </div>
                <button
                  type="button"
                  onClick={fetchNextAutoId}
                  className="p-1.5 text-blue-600 hover:bg-blue-100 rounded-lg transition"
                  title="Recalculate Next ID"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          {/* Section 3: Asset Details (Reference Fields) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                SAP Number / Ref No
              </label>
              <input
                type="text"
                value={sapNumber}
                onChange={(e) => setSapNumber(e.target.value)}
                placeholder="e.g. 36007672-0"
                className="w-full text-xs font-mono bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Asset Description <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. WEIG-MCHN"
                className="w-full text-xs font-bold bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900 uppercase focus:ring-2 focus:ring-blue-500 focus:outline-none"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Location / Bay
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. MCP / LAB-2 / WH-01"
                className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900 uppercase focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Serial Number
              </label>
              <input
                type="text"
                value={serialNumber}
                onChange={(e) => setSerialNumber(e.target.value)}
                placeholder="e.g. SN-892140"
                className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Department
              </label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                placeholder="e.g. Production Weighing"
                className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Custodian / User
              </label>
              <input
                type="text"
                value={custodian}
                onChange={(e) => setCustodian(e.target.value)}
                placeholder="e.g. Rajesh Kumar"
                className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-900 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Section 4: Code Type (Barcode vs QR Code) */}
          <div className="pt-2">
            <label className="block text-xs font-bold text-slate-700 mb-1.5">
              Code Symbology & Placement <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setCodeType('BARCODE')}
                className={`p-3 rounded-lg border text-left transition flex items-start gap-2.5 ${
                  codeType === 'BARCODE'
                    ? 'bg-blue-50/70 border-blue-500 text-blue-900 shadow-2xs'
                    : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                }`}
              >
                <div className="w-4 h-4 rounded-full border border-blue-600 flex items-center justify-center mt-0.5 shrink-0">
                  {codeType === 'BARCODE' && <div className="w-2 h-2 rounded-full bg-blue-600" />}
                </div>
                <div>
                  <div className="text-xs font-bold">1D Barcode (Code 128)</div>
                  <div className="text-[11px] text-slate-500">Positioned at bottom section (Reference Layout)</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setCodeType('QR_CODE')}
                className={`p-3 rounded-lg border text-left transition flex items-start gap-2.5 ${
                  codeType === 'QR_CODE'
                    ? 'bg-blue-50/70 border-blue-500 text-blue-900 shadow-2xs'
                    : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                }`}
              >
                <div className="w-4 h-4 rounded-full border border-blue-600 flex items-center justify-center mt-0.5 shrink-0">
                  {codeType === 'QR_CODE' && <div className="w-2 h-2 rounded-full bg-blue-600" />}
                </div>
                <div>
                  <div className="text-xs font-bold">2D QR Code</div>
                  <div className="text-[11px] text-slate-500">Positioned on right side with left text reflow</div>
                </div>
              </button>
            </div>
          </div>

          {/* Submission Button */}
          <div className="pt-3">
            <button
              type="button"
              onClick={() => handleGenerate()}
              disabled={loading}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-lg shadow-blue-600/30 transition flex items-center justify-center gap-2"
            >
              <Tag className="w-4 h-4" />
              <span>{loading ? 'Processing Tag...' : 'Save & Generate Asset Tag'}</span>
            </button>
          </div>
        </div>

        {/* Right Live Preview Column (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col items-center">
            <div className="w-full flex items-center justify-between pb-3 mb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Tag className="w-4 h-4 text-blue-600" />
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Real-Time Live Tag Preview
                </h3>
              </div>
              <span className="text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded font-bold">
                100% Scannable DPI
              </span>
            </div>

            {/* Render Live Preview Component */}
            <div className="my-2 py-4 px-2 w-full flex justify-center bg-slate-50/70 border border-slate-200/80 rounded-xl">
              <AssetTagPreview
                companyName={selectedCompany?.name || 'REFERENCE'}
                logoUrl={selectedCompany?.logo_path}
                assetId={activeAssetId || 'FA-000001'}
                sapNumber={sapNumber}
                description={description}
                location={location}
                codeType={codeType}
                widthMm={labelWidth}
                heightMm={labelHeight}
                showActions={true}
                scale={1.05}
                id={createdAsset?.id}
              />
            </div>

            {/* Configurable tag dimensions info */}
            <div className="w-full mt-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-2">
              <div className="font-bold text-slate-700 flex items-center justify-between">
                <span>Label Physical Dimension:</span>
                <span className="font-mono text-slate-900">{labelWidth} × {labelHeight} mm</span>
              </div>
              <div className="text-[11px] text-slate-500">
                Encodes <strong className="text-slate-800">Asset ID only</strong> in accordance with strict physical scanner specifications.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Duplicate Override Modal */}
      <DuplicateWarningModal
        isOpen={showOverrideModal}
        onClose={() => setShowOverrideModal(false)}
        onConfirmOverride={(reason) => handleGenerate(reason)}
        duplicateAssetId={manualAssetId}
        existingRecord={existingRecord}
        loading={loading}
      />
    </div>
  );
};
