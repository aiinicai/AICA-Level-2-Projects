import React, { useState, useRef } from 'react';
import { 
  Upload, 
  FileText, 
  Sparkles, 
  CheckCircle2, 
  Circle, 
  AlertCircle, 
  PlayCircle, 
  RefreshCw, 
  ArrowRight,
  ShieldCheck,
  FileCode,
  Layers,
  HelpCircle
} from 'lucide-react';
import { ContractDocument, AnalysisProgressStage } from '../types/contract';

interface NewAnalysisProps {
  onAnalysisComplete: (contract: ContractDocument) => void;
  onLoadDemo: () => void;
}

export const NewAnalysis: React.FC<NewAnalysisProps> = ({
  onAnalysisComplete,
  onLoadDemo
}) => {
  const [activeInputTab, setActiveInputTab] = useState<'upload' | 'paste'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [pastedText, setPastedText] = useState<string>('');
  const [contractType, setContractType] = useState<string>('Turnkey Supply & Installation');
  const [selectedFramework, setSelectedFramework] = useState<'Ind AS' | 'Accounting Standards (AS)' | 'Company Financial Reporting' | 'To Be Confirmed'>('Ind AS');
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Staged progress tracking
  const [stages, setStages] = useState<AnalysisProgressStage[]>([
    { id: '1', name: 'Reading contract & extracting text', status: 'pending' },
    { id: '2', name: 'Identifying clauses & structural segmentation', status: 'pending' },
    { id: '3', name: 'Extracting key commercial terms & pricing structure', status: 'pending' },
    { id: '4', name: 'Analyzing Accounting & Ind AS implications (Revenue, Retention, CWIP)', status: 'pending' },
    { id: '5', name: 'Analyzing GST, TDS & MSME / Sec 43B(h) compliance', status: 'pending' },
    { id: '6', name: 'Performing Cross-Clause 2nd-pass reasoning review', status: 'pending' },
    { id: '7', name: 'Preparing CA review points, management questions & evidence checklist', status: 'pending' }
  ]);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const updateStage = (stageIndex: number, status: 'pending' | 'in_progress' | 'completed' | 'error', detail?: string) => {
    setStages(prev => prev.map((s, idx) => {
      if (idx === stageIndex) {
        return { ...s, status, detail };
      }
      return s;
    }));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      setFile(droppedFile);
      setErrorMessage(null);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setErrorMessage(null);
    }
  };

  const runAnalysis = async () => {
    if (!file && !pastedText.trim()) {
      setErrorMessage('Please select a contract file or paste contract text to proceed.');
      return;
    }

    setIsAnalyzing(true);
    setErrorMessage(null);

    // Reset stages
    setStages(prev => prev.map(s => ({ ...s, status: 'pending', detail: undefined })));

    try {
      // Stage 1: Document extraction
      updateStage(0, 'in_progress', 'Uploading and parsing document structure...');

      let docMetadata: any = null;

      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('contractType', contractType);
        formData.append('selectedFramework', selectedFramework);

        const uploadRes = await fetch('/api/upload-contract', {
          method: 'POST',
          body: formData
        });

        if (!uploadRes.ok) {
          const errData = await uploadRes.json().catch(() => ({}));
          throw new Error(errData.error || `Upload failed with HTTP ${uploadRes.status}`);
        }

        const uploadData = await uploadRes.json();
        docMetadata = uploadData.documentMetadata;
      } else {
        // Pasted text
        const uploadRes = await fetch('/api/upload-contract', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: pastedText,
            fileName: 'Manual_Contract_Review.txt',
            contractType,
            selectedFramework
          })
        });

        if (!uploadRes.ok) {
          const errData = await uploadRes.json().catch(() => ({}));
          throw new Error(errData.error || `Upload failed with HTTP ${uploadRes.status}`);
        }

        const uploadData = await uploadRes.json();
        docMetadata = uploadData.documentMetadata;
      }

      updateStage(0, 'completed', `Extracted ${docMetadata.rawText.length.toLocaleString()} characters across ${docMetadata.pageCount} pages.`);

      // Stage 2 & 3: Clause & Commercial extraction
      updateStage(1, 'in_progress', 'Segmenting clauses and mapping page references...');
      updateStage(2, 'in_progress', 'Extracting commercial value, credit period, retention, advance...');

      // Stage 4 & 5: Deep Professional Impact Analysis
      updateStage(3, 'in_progress', 'Checking revenue recognition, retention discounting, CWIP capitalization...');
      updateStage(4, 'in_progress', 'Checking GST composite supply, TDS under 194C/J/Q, MSMED Act & 43B(h)...');

      // Stage 6: Cross-clause second pass
      updateStage(5, 'in_progress', 'Evaluating compound clause interactions & hidden compliance clashes...');

      // Stage 7: CA Review points
      updateStage(6, 'in_progress', 'Structuring management questions, evidence requirements, and audit points...');

      const analyzeRes = await fetch('/api/analyze-contract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rawText: docMetadata.rawText,
          pages: docMetadata.pages,
          fileName: docMetadata.fileName,
          fileSize: docMetadata.fileSize,
          fileType: docMetadata.fileType,
          selectedFramework
        })
      });

      if (!analyzeRes.ok) {
        const errData = await analyzeRes.json().catch(() => ({}));
        throw new Error(errData.error || `Analysis failed with HTTP ${analyzeRes.status}`);
      }

      const analyzeData = await analyzeRes.json();
      const contractDoc: ContractDocument = analyzeData.contract;

      // Mark all stages completed
      for (let i = 1; i <= 6; i++) {
        updateStage(i, 'completed');
      }

      setTimeout(() => {
        setIsAnalyzing(false);
        onAnalysisComplete(contractDoc);
      }, 500);

    } catch (err: any) {
      console.error('Analysis error:', err);
      setIsAnalyzing(false);
      setErrorMessage(err.message || 'An error occurred during AI analysis. Please retry.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="text-center space-y-1">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Analyse a Contract</h1>
        <p className="text-sm text-slate-500">
          Identify accounting, tax, and compliance considerations before they become audit issues.
        </p>
      </div>

      {!isAnalyzing ? (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
          {/* Tabs: Upload vs Paste */}
          <div className="flex border-b border-slate-200 text-xs font-semibold">
            <button
              onClick={() => setActiveInputTab('upload')}
              className={`pb-3 px-4 flex items-center space-x-2 border-b-2 transition ${
                activeInputTab === 'upload'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <Upload className="w-4 h-4" />
              <span>Upload Document (PDF / DOCX / TXT)</span>
            </button>
            <button
              onClick={() => setActiveInputTab('paste')}
              className={`pb-3 px-4 flex items-center space-x-2 border-b-2 transition ${
                activeInputTab === 'paste'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              <FileCode className="w-4 h-4" />
              <span>Paste Text / Raw Clauses</span>
            </button>
          </div>

          {/* Input Area */}
          {activeInputTab === 'upload' ? (
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
                file
                  ? 'border-emerald-400 bg-emerald-50/30'
                  : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.doc,.txt"
                onChange={handleFileChange}
                className="hidden"
              />

              <div className="w-12 h-12 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto mb-3">
                <Upload className="w-6 h-6" />
              </div>

              {file ? (
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-emerald-800">
                    Selected File: {file.name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {(file.size / 1024).toFixed(1)} KB • Click or drop to replace
                  </p>
                </div>
              ) : (
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-slate-800">
                    Drop contract here or <span className="text-indigo-600 underline">browse files</span>
                  </p>
                  <p className="text-xs text-slate-500">
                    Supports text & scanned PDFs, DOCX agreements, and plain text contracts up to 20MB.
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700">
                Paste Full Agreement Text or Specific Clauses
              </label>
              <textarea
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                placeholder="Paste contract text including parties, value, milestone clauses, retention terms, warranty, etc..."
                rows={10}
                className="w-full text-xs font-mono p-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-slate-50"
              />
            </div>
          )}

          {/* Config: Contract Type & Accounting Framework */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-slate-100 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Contract Type (Optional)
              </label>
              <select
                value={contractType}
                onChange={(e) => setContractType(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-slate-300 bg-white text-slate-800 font-medium focus:ring-2 focus:ring-indigo-500"
              >
                <option value="Turnkey Supply & Installation">Turnkey Supply & Installation</option>
                <option value="Sale of Goods / Manufacturing">Sale of Goods / Manufacturing</option>
                <option value="Service / AMC Agreement">Service / AMC Agreement</option>
                <option value="EPC / Construction Contract">EPC / Construction Contract</option>
                <option value="Commercial Lease / Rent">Commercial Lease / Rent</option>
                <option value="Consultancy & Professional Services">Consultancy & Professional Services</option>
                <option value="Related Party Contract">Related Party Contract</option>
                <option value="Other Commercial Agreement">Other Commercial Agreement</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Which Accounting Framework is relevant?
              </label>
              <select
                value={selectedFramework}
                onChange={(e) => setSelectedFramework(e.target.value as any)}
                className="w-full p-2.5 rounded-lg border border-slate-300 bg-white text-slate-800 font-medium focus:ring-2 focus:ring-indigo-500"
              >
                <option value="Ind AS">Ind AS (Indian Accounting Standards - Converged with IFRS)</option>
                <option value="Accounting Standards (AS)">Accounting Standards (AS / Indian GAAP)</option>
                <option value="Company Financial Reporting">Company Financial Reporting (Schedule III)</option>
                <option value="To Be Confirmed">Not sure / To Be Confirmed by Auditor</option>
              </select>
            </div>
          </div>

          {errorMessage && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Action Row */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
            <button
              onClick={onLoadDemo}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-4 py-2.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 transition"
            >
              <PlayCircle className="w-4 h-4 text-emerald-600" />
              <span>Or Load Pre-Configured Demo Contract (₹5.2 Cr)</span>
            </button>

            <button
              id="start-analysis-btn"
              onClick={runAnalysis}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-2.5 rounded-lg text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition"
            >
              <Sparkles className="w-4 h-4" />
              <span>Run Professional Impact Analysis</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      ) : (
        /* Progress Live Stepper */
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 space-y-6">
          <div className="text-center space-y-2">
            <div className="inline-flex p-3 bg-indigo-50 rounded-full text-indigo-600 animate-pulse">
              <RefreshCw className="w-6 h-6 animate-spin" />
            </div>
            <h2 className="text-lg font-bold text-slate-900">Processing Contract Analysis</h2>
            <p className="text-xs text-slate-500">
              Applying Indian CA, Ind AS, CGST, TDS, MSME, and Companies Act compliance evaluation models...
            </p>
          </div>

          <div className="space-y-4 max-w-xl mx-auto pt-4">
            {stages.map((stage, idx) => (
              <div key={stage.id} className="flex items-start space-x-3 text-xs">
                {stage.status === 'completed' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                ) : stage.status === 'in_progress' ? (
                  <RefreshCw className="w-5 h-5 text-indigo-600 animate-spin shrink-0 mt-0.5" />
                ) : (
                  <Circle className="w-5 h-5 text-slate-300 shrink-0 mt-0.5" />
                )}

                <div className="space-y-0.5 flex-1">
                  <span className={`font-semibold ${
                    stage.status === 'completed' ? 'text-slate-800' :
                    stage.status === 'in_progress' ? 'text-indigo-700 font-bold' :
                    'text-slate-400'
                  }`}>
                    {stage.name}
                  </span>
                  {stage.detail && (
                    <p className="text-[11px] text-slate-500">{stage.detail}</p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {errorMessage && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
              <button
                onClick={runAnalysis}
                className="px-3 py-1 rounded bg-rose-600 text-white font-semibold hover:bg-rose-700"
              >
                Retry
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
