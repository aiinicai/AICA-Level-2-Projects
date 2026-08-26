import React, { useState, useRef } from 'react';
import {
  Upload, Folder, FileSpreadsheet, FileText, FileCode, CheckCircle2,
  AlertTriangle, RefreshCw, ArrowRight, Hash, Shield, Layers, HelpCircle,
  FileCheck2, Database
} from 'lucide-react';
import { IngestionResult } from '../types';

interface DataIngestionViewProps {
  onFileUpload: (file: File) => Promise<void>;
  onPathUpload: (path: string) => Promise<void>;
  ingestionResult: IngestionResult | null;
  isLoading: boolean;
  onUpdateColumnMapping: (mapping: Record<string, string>) => void;
  onProceedToBenford: () => void;
}

export const DataIngestionView: React.FC<DataIngestionViewProps> = ({
  onFileUpload,
  onPathUpload,
  ingestionResult,
  isLoading,
  onUpdateColumnMapping,
  onProceedToBenford
}) => {
  const [pathInput, setPathInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const supportedFormats = [
    { label: 'Excel (.xlsx, .xls, .xlsm)', icon: FileSpreadsheet, color: 'text-emerald-400', ext: 'XLSX, XLS, XLSM' },
    { label: 'Word (.docx)', icon: FileText, color: 'text-blue-400', ext: 'DOCX' },
    { label: 'PDF Documents (.pdf)', icon: FileText, color: 'text-rose-400', ext: 'PDF' },
    { label: 'Delimited / CSV (.csv, .tsv, .psv)', icon: FileCode, color: 'text-amber-400', ext: 'CSV, TSV, PSV' },
    { label: 'Text & Logs (.txt, .log, .dat)', icon: FileText, color: 'text-slate-300', ext: 'TXT, LOG, DAT' },
    { label: 'Semi-Structured (.json, .jsonl, .xml)', icon: FileCode, color: 'text-purple-400', ext: 'JSON, XML' },
    { label: 'High-Perf & DB (.parquet, .sqlite, .db)', icon: Layers, color: 'text-cyan-400', ext: 'PARQUET, SQLITE' }
  ];

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileUpload(e.target.files[0]);
    }
  };

  const handlePathSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pathInput.trim()) {
      onPathUpload(pathInput.trim());
    }
  };

  const handleMappingChange = (field: string, selectedCol: string) => {
    if (!ingestionResult) return;
    const updated = { ...ingestionResult.column_mapping, [field]: selectedCol };
    onUpdateColumnMapping(updated);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto py-4">
      {/* Title & Guidelines */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-brand-400" />
            Universal Multi-Format Ingestion &amp; Schema Mapping
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Ingest local files, directories, or connected network server paths (UNC). Supports all major financial data formats.
          </p>
        </div>
      </div>

      {/* Format Capability Badges (Top Overview) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2">
        {supportedFormats.map((fmt, i) => {
          const Icon = fmt.icon;
          return (
            <div
              key={i}
              className="p-2 rounded-lg bg-slate-900/70 border border-slate-800/90 flex items-center gap-1.5 text-[11px] text-slate-300"
            >
              <Icon className={`w-3.5 h-3.5 ${fmt.color} flex-shrink-0`} />
              <span className="truncate font-medium">{fmt.ext}</span>
            </div>
          );
        })}
      </div>

      {/* Diagnostic Limitation / Warning Banner (if file unreadable / password protected / scanned image) */}
      {ingestionResult && !ingestionResult.success && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs space-y-2">
          <div className="flex items-center gap-2 font-bold text-amber-300 text-sm">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span>Format Limitation / Ingestion Notice</span>
          </div>
          <p>{ingestionResult.error_message}</p>
          {ingestionResult.limitation_warning && (
            <p className="text-slate-300">
              <b>Diagnosis:</b> {ingestionResult.limitation_warning}
            </p>
          )}
          {ingestionResult.recommendation && (
            <div className="p-2.5 bg-slate-950/60 rounded-lg border border-amber-500/20 text-slate-200">
              <span className="font-semibold text-brand-400">Recommendation: </span>
              {ingestionResult.recommendation}
            </div>
          )}
        </div>
      )}

      {/* Ingestion Inputs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 1. Drag & Drop File Upload */}
        <div className="forensic-card p-6 flex flex-col justify-between">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-all duration-200 flex flex-col items-center justify-center min-h-[160px] ${
              isDragging
                ? 'border-brand-500 bg-brand-500/10'
                : 'border-slate-700/80 bg-slate-950/60 hover:border-slate-600 hover:bg-slate-900/80'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileChange}
              accept=".csv,.tsv,.psv,.xlsx,.xls,.xlsm,.docx,.pdf,.json,.jsonl,.xml,.parquet,.sqlite,.db,.txt,.log,.dat"
              className="hidden"
            />
            <div className="w-12 h-12 rounded-xl bg-brand-500/10 border border-brand-500/30 flex items-center justify-center text-brand-400 mb-2">
              <Upload className="w-6 h-6" />
            </div>
            <p className="text-xs font-bold text-white">
              Drag &amp; Drop Financial Data File Here
            </p>
            <p className="text-[11px] text-slate-400 mt-0.5">
              or click to browse local filesystem
            </p>
          </div>

          {/* Non-intrusive format tags around input field */}
          <div className="mt-3 pt-2.5 border-t border-slate-800 flex flex-wrap items-center gap-1.5 text-[10px] text-slate-400">
            <span className="font-semibold text-slate-500">Supported:</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-emerald-400 font-mono">Excel (.xlsx, .xls)</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-blue-400 font-mono">Word (.docx)</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-rose-400 font-mono">PDF (.pdf)</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-amber-400 font-mono">CSV / TSV</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-purple-400 font-mono">JSON / XML</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-cyan-400 font-mono">Parquet / SQLite</span>
          </div>
        </div>

        {/* 2. Direct File / Folder / Network UNC Path Input */}
        <div className="forensic-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2.5 text-slate-200 font-semibold text-sm mb-2">
              <Folder className="w-4 h-4 text-forensic-gold" />
              <span>Local File, Folder, or Network Server UNC Path</span>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Point directly to any directory or file on local drives or shared network servers (e.g. <code className="text-slate-300 font-mono">\\192.168.1.100\Audit\Ledger.xlsx</code> or <code className="text-slate-300 font-mono">D:\Clients\2026\Data</code>).
            </p>

            <form onSubmit={handlePathSubmit} className="space-y-3">
              <input
                type="text"
                value={pathInput}
                onChange={(e) => setPathInput(e.target.value)}
                placeholder="e.g. \\server\shared\bank_statements.csv or C:\Audit\q4.xlsx"
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 font-mono"
              />
              <button
                type="submit"
                disabled={isLoading || !pathInput.trim()}
                className="w-full py-2 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-white transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Folder className="w-3.5 h-3.5" />}
                Scan &amp; Ingest Path
              </button>
            </form>
          </div>

          {/* Non-intrusive path format tags */}
          <div className="mt-3 pt-2.5 border-t border-slate-800 flex flex-wrap items-center justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1 text-emerald-400 font-medium">
              <Shield className="w-3 h-3" /> Zero Cloud Egress
            </span>
            <span className="font-mono text-slate-500">
              Accepts directory paths, UNC shares, and single files
            </span>
          </div>
        </div>
      </div>

      {/* Dataset Summary & Smart Column Mapping (when loaded) */}
      {ingestionResult && ingestionResult.success && (
        <div className="forensic-card p-6 space-y-6">
          {/* Metadata Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  {ingestionResult.file_name}
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                    {ingestionResult.row_count.toLocaleString()} Records
                  </span>
                </h3>
                <p className="text-xs text-slate-400 font-mono flex items-center gap-1 mt-0.5">
                  <Hash className="w-3 h-3 text-slate-500" />
                  SHA-256: <span className="text-slate-300">{ingestionResult.dataset_hash}</span>
                </p>
              </div>
            </div>

            <button
              onClick={onProceedToBenford}
              disabled={!ingestionResult.column_mapping.amount}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-xs font-bold shadow-lg shadow-brand-500/20 transition-all flex items-center gap-2 disabled:opacity-50"
            >
              <span>Proceed to Forensic Audit &amp; Benford's Law Suite</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* Smart Column Mapping Selectors */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Forensic Column Mapping (Auto-Discovered)
              </h4>
              <span className="text-[11px] text-slate-400">
                * Amount column is mandatory for Benford's Law tests
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
              {/* Amount */}
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <label className="block text-[11px] font-semibold text-brand-400 mb-1">
                  Amount / Debit / Credit *
                </label>
                <select
                  value={ingestionResult.column_mapping.amount || ''}
                  onChange={(e) => handleMappingChange('amount', e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500"
                >
                  <option value="">-- Select Column --</option>
                  {ingestionResult.columns.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              {/* Date */}
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                  Transaction Date
                </label>
                <select
                  value={ingestionResult.column_mapping.date || ''}
                  onChange={(e) => handleMappingChange('date', e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500"
                >
                  <option value="">-- Optional --</option>
                  {ingestionResult.columns.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              {/* Vendor / Party */}
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                  Vendor / Party Name
                </label>
                <select
                  value={ingestionResult.column_mapping.vendor || ''}
                  onChange={(e) => handleMappingChange('vendor', e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500"
                >
                  <option value="">-- Optional --</option>
                  {ingestionResult.columns.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              {/* Invoice / Ref */}
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                  Invoice / Voucher ID
                </label>
                <select
                  value={ingestionResult.column_mapping.invoice_no || ''}
                  onChange={(e) => handleMappingChange('invoice_no', e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500"
                >
                  <option value="">-- Optional --</option>
                  {ingestionResult.columns.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              {/* Description */}
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                  Narration / Remarks
                </label>
                <select
                  value={ingestionResult.column_mapping.description || ''}
                  onChange={(e) => handleMappingChange('description', e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500"
                >
                  <option value="">-- Optional --</option>
                  {ingestionResult.columns.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Sample Ingestion Preview Table */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              Ingested Records Preview (First 10 Rows)
            </h4>
            <div className="overflow-x-auto border border-slate-800 rounded-lg max-h-60">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase tracking-wider text-[10px] sticky top-0">
                  <tr>
                    <th className="px-3 py-2">#</th>
                    {ingestionResult.columns.map((col) => (
                      <th key={col} className="px-3 py-2 whitespace-nowrap">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {ingestionResult.sample_records.slice(0, 10).map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/30">
                      <td className="px-3 py-1.5 text-slate-500">{idx + 1}</td>
                      {ingestionResult.columns.map((col) => (
                        <td key={col} className="px-3 py-1.5 whitespace-nowrap text-slate-200">
                          {String(row[col] !== null && row[col] !== undefined ? row[col] : '-')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
