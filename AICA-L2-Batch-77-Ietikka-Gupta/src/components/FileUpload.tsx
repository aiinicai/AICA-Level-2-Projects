import React, { useRef, useState } from 'react';
import { 
  UploadCloud, 
  FileCheck, 
  FileWarning, 
  Sparkles, 
  FileText, 
  CheckCircle2, 
  Loader2, 
  Database, 
  Trash2, 
  ShieldCheck, 
  Clock, 
  Lock, 
  FileSpreadsheet, 
  ArrowRight,
  Receipt,
  Layers
} from 'lucide-react';
import { ChallanRecord, AssesseeDetails } from '../types';
import { sampleChallans } from '../utils/sampleData';

interface FileUploadProps {
  onRecordsExtracted: (records: ChallanRecord[]) => void;
  onClearAll: () => void;
  recordCount: number;
  records: ChallanRecord[];
  assessee: AssesseeDetails;
  onExportExcel: () => void;
  onExportPdf: () => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onRecordsExtracted,
  onClearAll,
  recordCount,
  records,
  assessee,
  onExportExcel,
  onExportPdf,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [uploadedFilesList, setUploadedFilesList] = useState<string[]>([]);

  const handleFiles = async (files: FileList | File[]) => {
    const validFiles: File[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file.type === 'application/pdf' || file.name.endsWith('.pdf') || file.type.startsWith('image/')) {
        validFiles.push(file);
      }
    }

    if (validFiles.length === 0) {
      setErrorMsg("Please select valid PDF or image files of EPFO / ESIC challans.");
      return;
    }

    setErrorMsg(null);
    setIsProcessing(true);
    setStatusMessage(`Preparing ${validFiles.length} file(s) for AI digitization...`);

    try {
      // Convert all files to base64
      const filePayloads = await Promise.all(
        validFiles.map(async (file) => {
          return new Promise<{ name: string; mimeType: string; base64Data: string }>(
            (resolve, reject) => {
              const reader = new FileReader();
              reader.onload = () => {
                const result = reader.result as string;
                resolve({
                  name: file.name,
                  mimeType: file.type || 'application/pdf',
                  base64Data: result,
                });
              };
              reader.onerror = reject;
            }
          );
        })
      );

      setStatusMessage("AI is digitizing challans & analyzing Section 36(1)(va) statutory due dates...");

      const response = await fetch("/api/analyze-challan", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ files: filePayloads }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.message || "Failed to digitize challan files.");
      }

      if (data.records && data.records.length > 0) {
        onRecordsExtracted(data.records);
        setUploadedFilesList(prev => [...prev, ...validFiles.map(f => f.name)]);
        setStatusMessage(`Successfully digitized ${data.records.length} challan record(s)!`);
      } else {
        setErrorMsg("No PF or ESI challan records could be identified in the uploaded file(s). You can also load our sample dataset or enter records manually.");
      }
    } catch (err: any) {
      console.error("Upload error:", err);
      setErrorMsg(err.message || "Error processing files. Please ensure valid EPFO / ESIC PDF documents are provided.");
    } finally {
      setIsProcessing(false);
      setTimeout(() => setStatusMessage(''), 4000);
    }
  };

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
      handleFiles(e.dataTransfer.files);
    }
  };

  const loadSampleDataset = (type: 'full' | 'pf' | 'esi') => {
    setErrorMsg(null);
    if (type === 'full') {
      onRecordsExtracted(sampleChallans);
      setUploadedFilesList(['FY_2024_25_Full_Year_Challans.zip']);
    } else if (type === 'pf') {
      const pfSamples = sampleChallans.filter(c => c.fundType === 'PF');
      onRecordsExtracted(pfSamples);
      setUploadedFilesList(['PF_ECR_Challans_2024_25.pdf']);
    } else if (type === 'esi') {
      const esiSamples = sampleChallans.filter(c => c.fundType === 'ESI');
      onRecordsExtracted(esiSamples);
      setUploadedFilesList(['ESIC_Monthly_Challans_2024_25.pdf']);
    }
  };

  const latestRecord = records.length > 0 ? records[0] : null;
  const totalAmount = records.reduce((s, r) => s + r.totalChallanAmount, 0);
  const totalDisallowed = records.reduce((s, r) => s + r.disallowableAmount, 0);

  return (
    <div className="space-y-4">
      
      {/* Bento Grid Main Hub */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        
        {/* Bento Tile 1: Primary Document Upload Hub (Span 8 on desktop) */}
        <div 
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          id="challan-bento-dropzone"
          className={`md:col-span-8 bg-white rounded-2xl border-2 border-dashed p-6 flex flex-col justify-center items-center relative overflow-hidden group cursor-pointer transition-all duration-200 min-h-[260px] ${
            isDragging
              ? 'border-indigo-500 bg-indigo-50/50 scale-[0.99]'
              : 'border-indigo-200 hover:border-indigo-400 bg-indigo-50/30 hover:bg-indigo-50/50'
          }`}
        >
          {/* Subtle Radial Dot Pattern */}
          <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#4f46e5_1px,transparent_1px)] [background-size:20px_20px] pointer-events-none"></div>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,image/*,application/pdf"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                handleFiles(e.target.files);
                e.target.value = '';
              }
            }}
          />

          {isProcessing ? (
            <div className="flex flex-col items-center text-center z-10 p-4">
              <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 ring-8 ring-indigo-100">
                <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-1">{statusMessage}</h3>
              <p className="text-xs text-slate-500 max-w-sm">
                Parsing EPFO ECR TRRN & ESIC Monthly Contribution Challans under Sec 36(1)(va)...
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center text-center z-10">
              <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 ring-8 ring-indigo-100 group-hover:scale-105 transition-transform duration-200">
                <UploadCloud className="w-8 h-8 text-indigo-600" />
              </div>
              <h3 className="text-lg font-bold text-slate-800">Upload Audit Documents</h3>
              <p className="text-slate-500 text-xs sm:text-sm mb-4 max-w-md">
                Select ESI or PF Challan PDFs for AI Digitization & Clause 20(b) Compliance
              </p>
              
              <div className="flex flex-wrap items-center justify-center gap-2">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                  className="bg-indigo-600 text-white px-6 py-2.5 rounded-xl font-bold text-xs shadow-lg shadow-indigo-200 hover:bg-indigo-700 active:scale-95 transition-all cursor-pointer"
                >
                  Browse PDF Files
                </button>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    loadSampleDataset('full');
                  }}
                  className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 px-4 py-2.5 rounded-xl font-semibold text-xs transition cursor-pointer"
                >
                  Load 12-Month Audit Pack
                </button>
              </div>

              {/* Badges */}
              <div className="flex flex-wrap items-center justify-center gap-2 mt-4 text-[11px] text-slate-500">
                <span className="inline-flex items-center gap-1 bg-white px-2.5 py-1 rounded-lg border border-slate-200">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Batch PDF Extraction
                </span>
                <span className="inline-flex items-center gap-1 bg-white px-2.5 py-1 rounded-lg border border-slate-200">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Auto 15th Due Date
                </span>
                <span className="inline-flex items-center gap-1 bg-white px-2.5 py-1 rounded-lg border border-slate-200">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Sec 36(1)(va) Disallowance
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Bento Tile 2: Active Analysis / Telemetry Card (Span 4 on desktop) */}
        <div className="md:col-span-4 bg-white rounded-2xl border border-slate-200 p-5 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-600" />
                Active Analysis
              </h3>
              <span className="text-[10px] bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-bold uppercase">
                {recordCount > 0 ? `${recordCount} Processed` : 'Standby'}
              </span>
            </div>

            <div className="space-y-2.5">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <p className="text-[10px] uppercase font-bold text-slate-400 mb-0.5">Primary Scope</p>
                <p className="text-xs font-bold text-slate-800 truncate">
                  {latestRecord 
                    ? `${latestRecord.fundType} Challan • ${latestRecord.wageMonth}` 
                    : 'EPFO ECR & ESIC Monthly'}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2.5">
                <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
                  <p className="text-[10px] uppercase font-bold text-slate-400 mb-0.5">Statutory Due</p>
                  <p className="text-xs font-bold text-slate-900 font-mono">
                    {latestRecord ? latestRecord.statutoryDueDate : '15th Next Mo.'}
                  </p>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-100">
                  <p className="text-[10px] uppercase font-bold text-slate-400 mb-0.5">Payment Date</p>
                  <p className={`text-xs font-bold font-mono ${latestRecord?.status === 'DELAYED' ? 'text-rose-600' : 'text-slate-900'}`}>
                    {latestRecord ? latestRecord.actualPaymentDate : 'Actual Realized'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Indigo Bento Metric Box */}
          <div className="p-3.5 bg-indigo-600 rounded-xl shadow-inner text-white mt-3">
            <div className="flex items-center justify-between">
              <p className="text-[10px] uppercase font-bold text-indigo-200">Total Challan Amount</p>
              <Receipt className="w-3.5 h-3.5 text-indigo-200" />
            </div>
            <p className="text-lg font-black text-white mt-0.5 font-mono">
              ₹ {totalAmount.toLocaleString('en-IN')}
            </p>
            {totalDisallowed > 0 && (
              <div className="mt-1 text-[10px] text-rose-200 font-semibold flex items-center justify-between">
                <span>Disallowed: ₹{totalDisallowed.toLocaleString('en-IN')}</span>
                <span>(Clause 20(b))</span>
              </div>
            )}
          </div>
        </div>

        {/* Bento Row 2: 3 Sub-Cards (5 - 3 - 4 col ratio or equal 4-4-4) */}
        
        {/* Bento Tile 3: Quick Samples & Audit Packs (Span 5 on desktop) */}
        <div className="md:col-span-5 bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                <Database className="w-4 h-4 text-slate-500" />
                Audit Datasets & Previews
              </h3>
              <span className="text-[10px] text-slate-400 font-medium">Instant Test</span>
            </div>

            <div className="space-y-2">
              <button
                type="button"
                onClick={() => loadSampleDataset('full')}
                className="w-full text-left p-2.5 bg-slate-50 hover:bg-indigo-50/60 border border-slate-200 hover:border-indigo-200 rounded-xl text-xs transition flex items-center justify-between group cursor-pointer"
              >
                <div>
                  <p className="font-bold text-slate-800 group-hover:text-indigo-700">Full FY 2024-25 Audit Pack</p>
                  <p className="text-[10px] text-slate-500">24 Challans (12 PF + 12 ESI with real audit delays)</p>
                </div>
                <span className="text-xs font-bold text-indigo-600 group-hover:translate-x-1 transition">→</span>
              </button>

              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => loadSampleDataset('pf')}
                  className="p-2 bg-slate-50 hover:bg-sky-50 border border-slate-200 hover:border-sky-200 rounded-xl text-xs font-semibold text-slate-700 text-center transition cursor-pointer"
                >
                  PF Pack Only (12)
                </button>
                <button
                  type="button"
                  onClick={() => loadSampleDataset('esi')}
                  className="p-2 bg-slate-50 hover:bg-indigo-50 border border-slate-200 hover:border-indigo-200 rounded-xl text-xs font-semibold text-slate-700 text-center transition cursor-pointer"
                >
                  ESI Pack Only (12)
                </button>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 mt-2">
            <span>Records Active: <strong className="text-slate-800">{recordCount}</strong></span>
            {recordCount > 0 && (
              <button
                type="button"
                onClick={onClearAll}
                className="text-red-600 hover:text-red-700 font-semibold inline-flex items-center gap-1 cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear Workspace
              </button>
            )}
          </div>
        </div>

        {/* Bento Tile 4: Dark Slate-900 Bento Card - Export Report Vault (Span 3 on desktop) */}
        <div className="md:col-span-3 bg-slate-900 rounded-2xl p-5 text-white flex flex-col justify-between shadow-lg">
          <div>
            <h3 className="font-bold text-sm text-white mb-0.5">Export Reports</h3>
            <p className="text-slate-400 text-xs">Generate Form 3CD schedules</p>
          </div>

          <div className="space-y-2 my-3">
            <button
              type="button"
              onClick={onExportExcel}
              disabled={recordCount === 0}
              className={`w-full text-xs font-bold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 transition ${
                recordCount === 0 
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                  : 'bg-slate-800 hover:bg-slate-700 text-white cursor-pointer active:scale-95'
              }`}
            >
              <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
              <span>Download Excel</span>
            </button>

            <button
              type="button"
              onClick={onExportPdf}
              disabled={recordCount === 0}
              className={`w-full text-xs font-bold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 transition ${
                recordCount === 0 
                  ? 'bg-indigo-950 text-indigo-400 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-950 cursor-pointer active:scale-95'
              }`}
            >
              <FileText className="w-4 h-4 text-white" />
              <span>Generate PDF</span>
            </button>
          </div>

          <div className="text-[10px] text-slate-400 text-center font-mono">
            Form 3CD Clause 20(b)
          </div>
        </div>

        {/* Bento Tile 5: Secure Audit Vault (Span 4 on desktop) */}
        <div className="md:col-span-4 bg-white rounded-2xl border border-slate-200 p-5 flex flex-col justify-between shadow-xs relative overflow-hidden">
          <div>
            <div className="flex items-center mb-2">
              <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mr-2.5 shrink-0">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-800 text-sm">Secure Audit Vault</h3>
                <p className="text-[10px] text-emerald-600 font-semibold">ICAI Privacy Compliant</p>
              </div>
            </div>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Client challans processed in transient memory. Zero persistent document storage with automated statutory validation.
            </p>
          </div>

          <div className="pt-3 border-t border-slate-100 flex justify-between items-center mt-3">
            <span className="text-[10px] text-slate-400 font-mono">Status: Verified Safe</span>
            <div className="flex space-x-1.5 items-center">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
              <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
              <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
            </div>
          </div>

          <div className="absolute -bottom-6 -right-6 w-24 h-24 bg-emerald-50 rounded-full opacity-40 pointer-events-none"></div>
        </div>

      </div>

      {/* Error notification */}
      {errorMsg && (
        <div className="p-3.5 bg-red-50 border border-red-200 rounded-2xl flex items-start gap-2.5 text-xs text-red-800 shadow-2xs">
          <FileWarning className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-bold text-red-900">Upload Issue</p>
            <p className="text-red-700 mt-0.5">{errorMsg}</p>
          </div>
        </div>
      )}

      {/* Success notification */}
      {statusMessage && !isProcessing && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-2 text-xs text-emerald-800 shadow-2xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span className="font-semibold">{statusMessage}</span>
        </div>
      )}

    </div>
  );
};
