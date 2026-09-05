import React, { useState } from 'react';
import type { Client } from '../types';
import { uploadScheduleFile, loadSampleData, getSampleTemplateUrl } from '../services/api';
import { Upload, Download, RefreshCw, CheckCircle2, FileSpreadsheet, AlertCircle } from 'lucide-react';

interface UploadCenterProps {
  client: Client;
  onUploadSuccess: () => void;
}

export const UploadCenterPage: React.FC<UploadCenterProps> = ({ client, onUploadSuccess }) => {
  const [uploadStatus, setUploadStatus] = useState<Record<string, string>>({});
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  const [loadingSample, setLoadingSample] = useState(false);

  const schedules = [
    { key: 'trial-balance', name: '1. Trial Balance', templateKey: 'trial_balance', mandatory: true, desc: 'Ledger Code, Ledger Name, Original Group, CY Amount, PY Amount, Type' },
    { key: 'ar-ageing', name: '2. AR Ageing Schedule', templateKey: 'ar_ageing', mandatory: true, desc: 'Customer Code, Name, Outstanding, Not Due, <6M, 6M-1Y, 1-2Y, 2-3Y, >3Y, Disputed' },
    { key: 'ap-ageing', name: '3. AP Ageing Schedule', templateKey: 'ap_ageing', mandatory: true, desc: 'Vendor Code, Name, MSME, Outstanding, Not Due, <1Y, 1-2Y, 2-3Y, >3Y, Disputed' },
    { key: 'cwip-ageing', name: '4. CWIP Ageing Schedule', templateKey: 'cwip_ageing', mandatory: false, desc: 'Project Name, Opening, Additions, Capitalised, Closing, Ageing, Completion Status' },
    { key: 'related-parties', name: '5. Related Party Schedule', templateKey: 'related_party', mandatory: false, desc: 'Related Party Name, Relationship, Nature of Transaction, Opening, Closing, Terms' },
    { key: 'borrowings', name: '6. Borrowings Schedule', templateKey: 'borrowings', mandatory: false, desc: 'Lender Name, Loan Type, Secured/Unsecured, Balances, Rate, Defaults, Terms' },
    { key: 'contingencies', name: '7. Contingent Liabilities', templateKey: 'contingencies', mandatory: false, desc: 'Nature, Forum/Authority, CY Amount, PY Amount, Assessment, Provision Required' },
  ];

  const handleFileUpload = async (key: string, file: File) => {
    setLoadingKey(key);
    try {
      const res = await uploadScheduleFile(key, client.id, file);
      setUploadStatus(prev => ({ ...prev, [key]: res.message || 'Uploaded successfully' }));
      onUploadSuccess();
    } catch (e) {
      setUploadStatus(prev => ({ ...prev, [key]: 'Upload failed. Please check file format.' }));
    } finally {
      setLoadingKey(null);
    }
  };

  const handleLoadSample = async () => {
    setLoadingSample(true);
    try {
      await loadSampleData(client.id);
      setUploadStatus({
        'trial-balance': 'Sample data loaded',
        'ar-ageing': 'Sample data loaded',
        'ap-ageing': 'Sample data loaded',
        'cwip-ageing': 'Sample data loaded',
        'related-parties': 'Sample data loaded',
        'borrowings': 'Sample data loaded',
        'contingencies': 'Sample data loaded',
      });
      onUploadSuccess();
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingSample(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b-2 border-slate-200 pb-4">
        <div>
          <h1 className="text-xl font-black text-[#1B365D] uppercase tracking-tight flex items-center gap-2">
            <Upload className="w-5 h-5 text-orange-600" />
            UPLOAD CENTER & SCHEDULE INGESTION
          </h1>
          <p className="text-xs font-semibold text-slate-500 mt-0.5">Upload Excel / CSV trial balances and supporting schedule workbooks for {client.name}.</p>
        </div>

        <button onClick={handleLoadSample} disabled={loadingSample} className="ca-button-primary text-xs">
          <RefreshCw className={`w-3.5 h-3.5 ${loadingSample ? 'animate-spin' : ''}`} />
          {loadingSample ? 'Loading Data...' : 'Use Pre-Packaged Sample Data'}
        </button>
      </div>

      {/* Grid of Upload Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {schedules.map((s) => {
          const statusText = uploadStatus[s.key];
          const isLoading = loadingKey === s.key;

          return (
            <div key={s.key} className="ca-card bg-white border-2 border-slate-200 space-y-3 shadow-2xs">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <FileSpreadsheet className="w-4 h-4 text-orange-600 shrink-0" />
                    <h3 className="text-xs font-black text-[#1B365D] uppercase tracking-wide">{s.name}</h3>
                    {s.mandatory && <span className="text-[9px] bg-rose-100 text-rose-900 border border-rose-300 font-extrabold px-1.5 py-0.5 rounded">REQUIRED</span>}
                  </div>
                  <p className="text-[11px] font-semibold text-slate-600 mt-1.5 leading-snug">{s.desc}</p>
                </div>
              </div>

              {statusText && (
                <div className="p-2.5 bg-emerald-50 border border-emerald-300 text-emerald-950 text-[11px] rounded-md flex items-center gap-2 font-bold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>{statusText}</span>
                </div>
              )}

              <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                <a
                  href={getSampleTemplateUrl(s.templateKey)}
                  download
                  className="text-xs text-[#1B365D] font-extrabold hover:text-orange-600 flex items-center gap-1.5"
                >
                  <Download className="w-3.5 h-3.5 text-slate-500" />
                  Download Sample Template
                </a>

                <label className="ca-button-outline text-xs cursor-pointer">
                  <Upload className="w-3.5 h-3.5 text-orange-600" />
                  {isLoading ? 'Uploading...' : 'Upload Excel'}
                  <input
                    type="file"
                    accept=".xlsx, .xls, .csv"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleFileUpload(s.key, e.target.files[0]);
                      }
                    }}
                  />
                </label>
              </div>
            </div>
          );
        })}
      </div>

      <div className="p-4 bg-slate-100 border border-slate-300 rounded-md text-xs text-slate-800 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-orange-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-extrabold text-[#1B365D]">FS BUILDER LITE Office Rule for Trial Balance Uploads:</span>
          <p className="text-[11px] text-slate-700 leading-normal font-medium">
            - Assets & Expenses: Enter as positive numbers.<br />
            - Liabilities, Equity & Income: Enter as negative numbers.<br />
            Trial Balance items will automatically run through the rule-based keyword mapping engine upon upload.
          </p>
        </div>
      </div>
    </div>
  );
};
