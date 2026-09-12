import React, { useState } from 'react';
import {
  FileSpreadsheet,
  Download,
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ShieldAlert,
  ArrowRight,
  Archive,
  Printer,
  FileText,
  RefreshCw,
  Edit2,
  Grid,
  Eye,
  X
} from 'lucide-react';
import api from '../services/api';
import { BulkValidationSummary, BulkValidationRow, Asset } from '../types';
import { AssetTagPreview } from '../components/AssetTagPreview';

export const BulkUploadPage: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<BulkValidationSummary | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationComplete, setGenerationComplete] = useState(false);
  const [createdAssetIds, setCreatedAssetIds] = useState<number[]>([]);
  const [generatedAssets, setGeneratedAssets] = useState<any[]>([]);
  const [generatedCount, setGeneratedCount] = useState(0);

  // Sheet configuration for bulk export
  const [bulkLabelsPerSheet, setBulkLabelsPerSheet] = useState<number>(14);
  const [showBulkPreviewModal, setShowBulkPreviewModal] = useState(false);

  // Active override editor
  const [activeOverrideRow, setActiveOverrideRow] = useState<BulkValidationRow | null>(null);
  const [overrideReasonInput, setOverrideReasonInput] = useState('');

  const handleDownloadTemplate = () => {
    window.open('/api/bulk/template', '_blank');
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setValidationResult(null);
      setGenerationComplete(false);
    }
  };

  const handleValidateUpload = async () => {
    if (!file) return;
    setIsValidating(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post<BulkValidationSummary>('/bulk/validate', formData);
      setValidationResult(res.data);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to validate Excel file.');
    } finally {
      setIsValidating(false);
    }
  };

  const applyRowOverride = (rowNumber: number, reason: string) => {
    if (!validationResult) return;
    const updatedRows = validationResult.rows.map((r) => {
      if (r.row_number === rowNumber) {
        return {
          ...r,
          override_reason: reason,
          status: 'VALID' as const,
        };
      }
      return r;
    });

    const newValidCount = updatedRows.filter((r) => r.status === 'VALID').length;
    const newDupCount = updatedRows.filter((r) => r.status.includes('DUPLICATE')).length;

    setValidationResult({
      ...validationResult,
      valid_count: newValidCount,
      duplicate_count: newDupCount,
      rows: updatedRows,
    });
    setActiveOverrideRow(null);
    setOverrideReasonInput('');
  };

  const handleGenerateAll = async () => {
    if (!validationResult) return;
    const validRows = validationResult.rows.filter((r) => r.status === 'VALID');
    if (validRows.length === 0) {
      alert('No valid rows available to generate tags.');
      return;
    }

    setIsGenerating(true);
    setGenerationProgress(10);

    const progressTimer = setInterval(() => {
      setGenerationProgress((p) => (p < 85 ? p + 15 : p));
    }, 200);

    try {
      const res = await api.post('/bulk/generate', { rows: validRows });
      clearInterval(progressTimer);
      setGenerationProgress(100);
      const ids = res.data.assets.map((a: any) => a.id);
      setCreatedAssetIds(ids);
      setGeneratedAssets(res.data.assets);
      setGeneratedCount(res.data.count);
      setGenerationComplete(true);
    } catch (err: any) {
      clearInterval(progressTimer);
      alert(err.response?.data?.detail || 'Bulk tag generation failed.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownloadZip = () => {
    if (createdAssetIds.length === 0) return;
    api
      .post('/bulk/download-zip', createdAssetIds, { responseType: 'blob' })
      .then((response) => {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'Asset_Tags_Batch.zip');
        document.body.appendChild(link);
        link.click();
        link.remove();
      });
  };

  const handleDownloadBulkSheetPdf = () => {
    if (createdAssetIds.length === 0) return;
    const cols = bulkLabelsPerSheet === 21 || bulkLabelsPerSheet === 24 || bulkLabelsPerSheet === 30 ? 3 : 2;
    const rows = Math.ceil(bulkLabelsPerSheet / cols);

    const config = {
      page_size: 'A4',
      orientation: 'PORTRAIT',
      label_width_mm: cols === 3 ? 60.0 : 70.0,
      label_height_mm: 35.0,
      margin_top_mm: 10.0,
      margin_bottom_mm: 10.0,
      margin_left_mm: 10.0,
      margin_right_mm: 10.0,
      horizontal_gap_mm: 3.0,
      vertical_gap_mm: 3.0,
      columns: cols,
      rows: rows,
    };

    api
      .post('/printing/generate-sheet-pdf', config, {
        params: { asset_ids: createdAssetIds },
        responseType: 'blob',
      })
      .then((response) => {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `Asset_Tags_Bulk_Sheet_${bulkLabelsPerSheet}_per_page.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      });
  };

  const handleDownloadBulkSheetDocx = () => {
    if (createdAssetIds.length === 0) return;
    const cols = bulkLabelsPerSheet === 21 || bulkLabelsPerSheet === 24 || bulkLabelsPerSheet === 30 ? 3 : 2;
    const rows = Math.ceil(bulkLabelsPerSheet / cols);

    const config = {
      page_size: 'A4',
      orientation: 'PORTRAIT',
      label_width_mm: 70.0,
      label_height_mm: 35.0,
      columns: cols,
      rows: rows,
    };

    api
      .post('/printing/generate-sheet-docx', config, {
        params: { asset_ids: createdAssetIds },
        responseType: 'blob',
      })
      .then((response) => {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `Asset_Tags_Bulk_Sheet.docx`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Bulk Asset Tag Generation</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Upload Excel rosters, validate schema & duplicates, and batch-produce named asset tags
          </p>
        </div>
        <button
          onClick={handleDownloadTemplate}
          className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-sm transition"
        >
          <Download className="w-4 h-4 text-blue-400" />
          Download Excel Template (.xlsx)
        </button>
      </div>

      {/* Step 1: Upload Box */}
      {!validationResult && (
        <div className="bg-white rounded-xl border-2 border-dashed border-slate-300 p-8 flex flex-col items-center justify-center text-center shadow-sm hover:border-blue-500 transition">
          <div className="p-4 bg-blue-50 text-blue-600 rounded-2xl mb-4">
            <UploadCloud className="w-8 h-8" />
          </div>
          <h2 className="text-base font-bold text-slate-900">Upload Filled Asset Excel File</h2>
          <p className="text-xs text-slate-500 mt-1 max-w-md">
            Drag and drop your populated spreadsheet here, or select a file from your computer. Supports .xlsx, .xls, and .csv formats.
          </p>

          <div className="mt-6 flex items-center gap-3">
            <input
              type="file"
              id="excel-file-input"
              accept=".xlsx,.xls,.csv"
              onChange={handleFileChange}
              className="hidden"
            />
            <label
              htmlFor="excel-file-input"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg cursor-pointer shadow-sm transition"
            >
              {file ? file.name : 'Choose Excel File'}
            </label>

            {file && (
              <button
                onClick={handleValidateUpload}
                disabled={isValidating}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white font-semibold text-xs rounded-lg shadow-sm transition flex items-center gap-1.5"
              >
                {isValidating ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Validating...
                  </>
                ) : (
                  <>
                    <span>Validate Roster</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Step 2: Validation Results & Batch Review */}
      {validationResult && !generationComplete && (
        <div className="space-y-6">
          {/* Validation Metrics Banner */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm text-center">
              <div className="text-[11px] font-semibold text-slate-500">Total Uploaded</div>
              <div className="text-xl font-bold font-mono text-slate-900 mt-1">{validationResult.total_rows}</div>
            </div>
            <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-200 shadow-sm text-center">
              <div className="text-[11px] font-semibold text-emerald-700">Valid Records</div>
              <div className="text-xl font-bold font-mono text-emerald-700 mt-1">{validationResult.valid_count}</div>
            </div>
            <div className="bg-amber-50 p-4 rounded-xl border border-amber-200 shadow-sm text-center">
              <div className="text-[11px] font-semibold text-amber-800">Duplicates</div>
              <div className="text-xl font-bold font-mono text-amber-800 mt-1">{validationResult.duplicate_count}</div>
            </div>
            <div className="bg-rose-50 p-4 rounded-xl border border-rose-200 shadow-sm text-center">
              <div className="text-[11px] font-semibold text-rose-700">Missing Fields</div>
              <div className="text-xl font-bold font-mono text-rose-700 mt-1">{validationResult.missing_fields_count}</div>
            </div>
            <div className="bg-purple-50 p-4 rounded-xl border border-purple-200 shadow-sm text-center">
              <div className="text-[11px] font-semibold text-purple-700">Invalid Format</div>
              <div className="text-xl font-bold font-mono text-purple-700 mt-1">{validationResult.invalid_format_count}</div>
            </div>
          </div>

          {/* Validation Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Roster Verification & Duplicate Analysis
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setValidationResult(null)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg transition font-medium"
                >
                  Upload Another File
                </button>
                <button
                  onClick={handleGenerateAll}
                  disabled={isGenerating || validationResult.valid_count === 0}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow-sm transition flex items-center gap-1.5"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Generate All Valid ({validationResult.valid_count}) Tags</span>
                </button>
              </div>
            </div>

            {/* Progress bar during generation */}
            {isGenerating && (
              <div className="p-6 bg-blue-50/50 border-b border-blue-100 space-y-2">
                <div className="flex justify-between text-xs font-bold text-blue-900">
                  <span>Batch Tag Generation in Progress...</span>
                  <span>{generationProgress}%</span>
                </div>
                <div className="w-full bg-blue-200 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-blue-600 h-full rounded-full transition-all duration-300"
                    style={{ width: `${generationProgress}%` }}
                  />
                </div>
              </div>
            )}

            <div className="overflow-x-auto max-h-[420px]">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 uppercase text-[10px] tracking-wider sticky top-0">
                  <tr>
                    <th className="py-2.5 px-3 text-center">Row</th>
                    <th className="py-2.5 px-3">Asset ID</th>
                    <th className="py-2.5 px-3">Description</th>
                    <th className="py-2.5 px-3">SAP No</th>
                    <th className="py-2.5 px-3">Location</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Diagnostics / Note</th>
                    <th className="py-2.5 px-3 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {validationResult.rows.map((r) => {
                    const isDup = r.status.includes('DUPLICATE');
                    const isErr = r.status === 'MISSING_REQUIRED' || r.status === 'INVALID_FORMAT';
                    return (
                      <tr key={r.row_number} className={`hover:bg-slate-50/70 transition ${isDup ? 'bg-amber-50/30' : isErr ? 'bg-rose-50/30' : ''}`}>
                        <td className="py-2.5 px-3 text-center font-mono font-semibold text-slate-500">{r.row_number}</td>
                        <td className="py-2.5 px-3 font-mono font-bold text-slate-900">{r.asset_id || '<Auto Generate>'}</td>
                        <td className="py-2.5 px-3 font-semibold truncate max-w-[180px]">{r.description || '—'}</td>
                        <td className="py-2.5 px-3 font-mono text-slate-600">{r.sap_number || '—'}</td>
                        <td className="py-2.5 px-3 text-slate-600">{r.location || '—'}</td>
                        <td className="py-2.5 px-3">
                          {r.status === 'VALID' && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded">
                              <CheckCircle2 className="w-3 h-3" /> Valid
                            </span>
                          )}
                          {isDup && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded">
                              <AlertTriangle className="w-3 h-3" /> Duplicate
                            </span>
                          )}
                          {isErr && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-700 bg-rose-100 px-2 py-0.5 rounded">
                              <XCircle className="w-3 h-3" /> Error
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-slate-500 text-[11px] truncate max-w-[220px]">
                          {r.override_reason ? (
                            <span className="text-emerald-700 font-medium">Overridden: "{r.override_reason}"</span>
                          ) : (
                            r.error_message || 'Ready for generation'
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          {isDup && !r.override_reason && (
                            <button
                              type="button"
                              onClick={() => {
                                setActiveOverrideRow(r);
                                setOverrideReasonInput('');
                              }}
                              className="px-2.5 py-1 text-[11px] font-bold bg-amber-600 hover:bg-amber-700 text-white rounded shadow-2xs transition inline-flex items-center gap-1"
                            >
                              <ShieldAlert className="w-3 h-3" />
                              Override
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Batch Completion Actions & Multi-Format Downloader */}
      {generationComplete && (
        <div className="bg-white rounded-xl border border-slate-200 p-8 shadow-sm space-y-6 animate-in fade-in">
          <div className="text-center space-y-2">
            <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto shadow-sm">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h2 className="text-lg font-bold text-slate-900">Bulk Generation Completed Successfully</h2>
            <p className="text-xs text-slate-500">
              Generated <span className="font-bold text-slate-900">{generatedCount}</span> high-resolution asset labels. Choose your download or sheet printing format below:
            </p>
          </div>

          {/* Sheet Format Configurator */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 max-w-xl mx-auto flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Grid className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-bold text-slate-800">Labels per Sheet:</span>
            </div>
            <select
              value={bulkLabelsPerSheet}
              onChange={(e) => setBulkLabelsPerSheet(Number(e.target.value))}
              className="text-xs bg-white border border-slate-300 rounded-lg px-3 py-1.5 font-bold text-slate-900 focus:ring-2 focus:ring-blue-500"
            >
              <option value={14}>14 Labels / Sheet (2 cols × 7 rows)</option>
              <option value={21}>21 Labels / Sheet (3 cols × 7 rows)</option>
              <option value={24}>24 Labels / Sheet (3 cols × 8 rows)</option>
              <option value={12}>12 Labels / Sheet (2 cols × 6 rows)</option>
              <option value={6}>6 Labels / Sheet (2 cols × 3 rows)</option>
              <option value={30}>30 Labels / Sheet (3 cols × 10 rows)</option>
            </select>
          </div>

          {/* Multi-Format Action Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl mx-auto">
            {/* 1. Download ZIP */}
            <button
              type="button"
              onClick={handleDownloadZip}
              className="p-5 bg-white border border-slate-200 hover:border-blue-500 hover:shadow-md rounded-xl text-left transition group flex flex-col justify-between"
            >
              <div>
                <div className="p-2.5 bg-blue-50 text-blue-600 rounded-lg inline-block mb-3 group-hover:bg-blue-600 group-hover:text-white transition">
                  <Archive className="w-5 h-5" />
                </div>
                <div className="text-xs font-bold text-slate-900">Download Individual PNGs</div>
                <div className="text-[11px] text-slate-500 mt-0.5">ZIP archive of named files (e.g. TATA-000001.png)</div>
              </div>
              <div className="mt-4 text-xs font-bold text-blue-600 flex items-center gap-1">
                <span>Download .ZIP</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </div>
            </button>

            {/* 2. Download PDF Sheet */}
            <button
              type="button"
              onClick={handleDownloadBulkSheetPdf}
              className="p-5 bg-white border border-slate-200 hover:border-blue-500 hover:shadow-md rounded-xl text-left transition group flex flex-col justify-between"
            >
              <div>
                <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-lg inline-block mb-3 group-hover:bg-emerald-600 group-hover:text-white transition">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="text-xs font-bold text-slate-900">Download PDF Sheet</div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  Multi-page A4 PDF ({bulkLabelsPerSheet} labels/sheet)
                </div>
              </div>
              <div className="mt-4 text-xs font-bold text-emerald-600 flex items-center gap-1">
                <span>Download .PDF</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </div>
            </button>

            {/* 3. Download Word Docx */}
            <button
              type="button"
              onClick={handleDownloadBulkSheetDocx}
              className="p-5 bg-white border border-slate-200 hover:border-blue-500 hover:shadow-md rounded-xl text-left transition group flex flex-col justify-between"
            >
              <div>
                <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-lg inline-block mb-3 group-hover:bg-indigo-600 group-hover:text-white transition">
                  <FileSpreadsheet className="w-5 h-5" />
                </div>
                <div className="text-xs font-bold text-slate-900">Download Word (.docx)</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Editable Microsoft Word table sheet</div>
              </div>
              <div className="mt-4 text-xs font-bold text-indigo-600 flex items-center gap-1">
                <span>Download .DOCX</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </div>
            </button>
          </div>

          <div className="text-center pt-4 border-t border-slate-100">
            <button
              onClick={() => {
                setValidationResult(null);
                setGenerationComplete(false);
                setFile(null);
              }}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition"
            >
              Upload Another Roster
            </button>
          </div>
        </div>
      )}

      {/* Inline Duplicate Override Modal for Table Rows */}
      {activeOverrideRow && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-amber-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 rounded-lg text-amber-700">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">Override Duplicate Row #{activeOverrideRow.row_number}</h3>
                <div className="text-xs font-mono text-slate-500">Asset ID: {activeOverrideRow.asset_id}</div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Mandatory Override Justification <span className="text-red-500">*</span>
              </label>
              <textarea
                rows={3}
                value={overrideReasonInput}
                onChange={(e) => setOverrideReasonInput(e.target.value)}
                placeholder="e.g. Master correction / field re-tagging..."
                className="w-full text-xs rounded-lg border border-slate-300 p-2.5 focus:outline-none focus:ring-2 focus:ring-amber-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setActiveOverrideRow(null)}
                className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  if (overrideReasonInput.trim().length >= 5) {
                    applyRowOverride(activeOverrideRow.row_number, overrideReasonInput.trim());
                  } else {
                    alert('Reason must be at least 5 characters long.');
                  }
                }}
                className="px-4 py-1.5 text-xs font-bold bg-amber-600 hover:bg-amber-700 text-white rounded-lg transition"
              >
                Apply Override
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
