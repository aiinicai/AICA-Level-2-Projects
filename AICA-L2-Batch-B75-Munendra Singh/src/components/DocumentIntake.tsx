import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  FileText, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  ShieldCheck, 
  ArrowRight, 
  SlidersHorizontal,
  Terminal
} from 'lucide-react';
import { SAMPLE_STATEMENTS } from '../data/sampleStatements';
import { SampleFinancialStatement } from '../types';

import { extractTextFromFile } from '../utils/pdfExtractor';

interface DocumentIntakeProps {
  onAnalyze: (payload: {
    text: string;
    fileData?: string;
    mimeType?: string;
    fileName?: string;
    options: {
      strictTolerance: boolean;
      checkCARO: boolean;
      standardsFocus: string[];
    };
  }) => void;
  isAuditing: boolean;
  activeFramework: string;
}

export const DocumentIntake: React.FC<DocumentIntakeProps> = ({
  onAnalyze,
  isAuditing,
  activeFramework,
}) => {
  const [activeTab, setActiveTab] = useState<'upload' | 'paste' | 'samples'>('samples');
  const [inputText, setInputText] = useState('');
  const [selectedFile, setSelectedFile] = useState<{
    name: string;
    size: number;
    mimeType: string;
    base64: string;
  } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);

  // Audit configuration settings
  const [strictTolerance, setStrictTolerance] = useState(true);
  const [checkCARO, setCheckCARO] = useState(true);
  const [selectedStandards, setSelectedStandards] = useState<string[]>([
    'Ind AS 1', 'Ind AS 7', 'Ind AS 16', 'Ind AS 24', 'Ind AS 37', 'Ind AS 107/109', 'Ind AS 115', 'Ind AS 116', 'Schedule III'
  ]);
  const [showConfig, setShowConfig] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const ALL_STANDARDS = [
    { id: 'Ind AS 1', label: 'Ind AS 1: Presentation & Current/Non-current' },
    { id: 'Ind AS 7', label: 'Ind AS 7: Cash Flow Statement' },
    { id: 'Ind AS 12', label: 'Ind AS 12: Income Taxes & Tax Reconciliations' },
    { id: 'Ind AS 16', label: 'Ind AS 16: PPE, Additions & Capitalized Borrowing' },
    { id: 'Ind AS 19', label: 'Ind AS 19: Employee Benefits & Actuarial Gains' },
    { id: 'Ind AS 24', label: 'Ind AS 24: Related Party & KMP Remuneration' },
    { id: 'Ind AS 33', label: 'Ind AS 33: Earnings Per Share (Basic/Diluted)' },
    { id: 'Ind AS 37', label: 'Ind AS 37: Contingent Liabilities & Provisions' },
    { id: 'Ind AS 107/109', label: 'Ind AS 107/109: Financial Instruments & ECL' },
    { id: 'Ind AS 108', label: 'Ind AS 108: Operating Segments' },
    { id: 'Ind AS 115', label: 'Ind AS 115: Revenue from Contracts' },
    { id: 'Ind AS 116', label: 'Ind AS 116: Leases & ROU Asset Rollforward' },
    { id: 'Schedule III', label: 'Schedule III: MSME Dues, Ratios & Promoters' },
  ];

  const handleToggleStandard = (id: string) => {
    setSelectedStandards((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const processFile = async (file: File) => {
    setFileError(null);
    setIsExtracting(true);
    const validMimes = [
      'application/pdf',
      'image/png',
      'image/jpeg',
      'image/webp',
      'text/plain',
      'text/csv',
    ];

    if (!validMimes.includes(file.type) && !file.name.endsWith('.csv') && !file.name.endsWith('.txt') && !file.name.endsWith('.pdf')) {
      setFileError('Please upload a PDF document, Image (PNG/JPEG), or text/csv financial extract.');
      setIsExtracting(false);
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setFileError('File size exceeds 25 MB limit. Please upload a smaller section or paste the text.');
      setIsExtracting(false);
      return;
    }

    try {
      // 1. Extract text offline on-device
      const extractedText = await extractTextFromFile(file);
      if (extractedText && extractedText.trim().length > 0) {
        setInputText(extractedText);
      }

      // 2. Also read base64 for image/file preview or optional cloud analysis
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string;
        const base64Data = result.split(',')[1] || result;
        setSelectedFile({
          name: file.name,
          size: file.size,
          mimeType: file.type || 'text/plain',
          base64: base64Data,
        });
        setIsExtracting(false);
      };
      reader.onerror = () => setIsExtracting(false);
      reader.readAsDataURL(file);
    } catch (err: any) {
      console.error('File extraction error:', err);
      setFileError(err.message || 'Failed to extract text from file.');
      setIsExtracting(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleSelectSample = (sample: SampleFinancialStatement) => {
    setInputText(sample.fullText);
    setSelectedFile(null);
    onAnalyze({
      text: sample.fullText,
      fileName: sample.title,
      options: {
        strictTolerance,
        checkCARO,
        standardsFocus: selectedStandards,
      },
    });
  };

  const handleStartAudit = () => {
    if (activeTab === 'upload' && selectedFile?.base64) {
      onAnalyze({
        text: inputText,
        fileData: selectedFile.base64,
        mimeType: selectedFile.mimeType,
        fileName: selectedFile.name,
        options: {
          strictTolerance,
          checkCARO,
          standardsFocus: selectedStandards,
        },
      });
    } else if (inputText.trim()) {
      onAnalyze({
        text: inputText.trim(),
        fileName: selectedFile?.name || 'Financial Statement Extract',
        options: {
          strictTolerance,
          checkCARO,
          standardsFocus: selectedStandards,
        },
      });
    }
  };

  const canSubmit = (activeTab === 'upload' && selectedFile) || (activeTab === 'paste' && inputText.trim().length > 50);

  return (
    <div className="bg-white border-2 border-[#141414] shadow-dense mb-6 overflow-hidden">
      {/* Header Banner */}
      <div className="bg-[#141414] text-white p-4 sm:p-5 border-b border-[#141414]">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="px-1.5 py-0.2 bg-[#00FF00] text-[#141414] font-mono text-[9px] font-bold uppercase">
                STATUTORY ENGINE
              </span>
              <span className="text-[10px] text-neutral-400 font-mono uppercase">
                ACTIVE FRAMEWORK: <strong className="text-white">{activeFramework}</strong>
              </span>
            </div>
            <h2 className="text-base sm:text-lg font-bold uppercase tracking-tight text-white">
              Financial Statement Audit Intake & Verification
            </h2>
            <p className="text-[11px] text-neutral-300 max-w-3xl mt-0.5 font-serif italic">
              Upload draft Financial Statements (PDF/Image), paste Note extracts, or execute pre-configured benchmark cases against Ind AS standards.
            </p>
          </div>

          <button
            id="toggle-audit-settings-btn"
            onClick={() => setShowConfig(!showConfig)}
            className="self-start md:self-center inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-mono font-bold uppercase bg-[#242424] hover:bg-[#333333] text-white border border-neutral-700 transition"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-[#00FF00]" />
            <span>Audit Scope ({selectedStandards.length})</span>
          </button>
        </div>

        {/* Expandable Standards & Config Panel */}
        {showConfig && (
          <div className="mt-4 pt-4 border-t border-neutral-700 grid grid-cols-1 md:grid-cols-3 gap-4 animate-fadeIn">
            <div className="md:col-span-2">
              <label className="text-[10px] font-mono font-bold text-[#00FF00] uppercase tracking-wider mb-2 block flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-[#00FF00]" />
                Mandatory Ind AS Disclosure Matrices to Audit:
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[11px]">
                {ALL_STANDARDS.map((std) => (
                  <label
                    key={std.id}
                    className="flex items-center space-x-2 p-1 bg-[#1c1c1c] hover:bg-[#282828] cursor-pointer text-neutral-200 border border-neutral-800 transition"
                  >
                    <input
                      type="checkbox"
                      checked={selectedStandards.includes(std.id)}
                      onChange={() => handleToggleStandard(std.id)}
                      className="rounded border-neutral-600 text-black focus:ring-0 bg-neutral-800 h-3.5 w-3.5"
                    />
                    <span className="truncate font-mono text-[10px]">{std.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-3 border-l border-neutral-800 pl-0 md:pl-4">
              <label className="text-[10px] font-mono font-bold text-[#00FF00] uppercase tracking-wider block">
                Verification Controls:
              </label>

              <label className="flex items-start space-x-2 cursor-pointer bg-[#1c1c1c] p-2 border border-neutral-800">
                <input
                  type="checkbox"
                  checked={strictTolerance}
                  onChange={(e) => setStrictTolerance(e.target.checked)}
                  className="mt-0.5 rounded border-neutral-600 text-black bg-neutral-800 h-3.5 w-3.5"
                />
                <div>
                  <span className="text-[11px] font-mono font-bold text-white block uppercase">Strict Footing & Casting</span>
                  <span className="text-[10px] text-neutral-400 font-serif italic block">Flag any rounding or subtotal variance &gt; ₹0.01 Lakh</span>
                </div>
              </label>

              <label className="flex items-start space-x-2 cursor-pointer bg-[#1c1c1c] p-2 border border-neutral-800">
                <input
                  type="checkbox"
                  checked={checkCARO}
                  onChange={(e) => setCheckCARO(e.target.checked)}
                  className="mt-0.5 rounded border-neutral-600 text-black bg-neutral-800 h-3.5 w-3.5"
                />
                <div>
                  <span className="text-[11px] font-mono font-bold text-white block uppercase">CARO 2020 & MSME Checks</span>
                  <span className="text-[10px] text-neutral-400 font-serif italic block">Cross-verify inventory, fixed assets & MSME interest</span>
                </div>
              </label>
            </div>
          </div>
        )}
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-[#141414] bg-[#E4E3E0] px-4 pt-2 gap-1">
        <button
          id="tab-samples"
          onClick={() => setActiveTab('samples')}
          className={`px-3 py-1.5 text-xs font-mono font-bold uppercase flex items-center space-x-1.5 border-t-2 border-x-2 transition ${
            activeTab === 'samples'
              ? 'bg-white border-[#141414] text-[#141414] -mb-[1px]'
              : 'border-transparent text-[#141414]/70 hover:text-[#141414]'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-[#141414]" />
          <span>Benchmark Case Studies</span>
        </button>

        <button
          id="tab-upload"
          onClick={() => setActiveTab('upload')}
          className={`px-3 py-1.5 text-xs font-mono font-bold uppercase flex items-center space-x-1.5 border-t-2 border-x-2 transition ${
            activeTab === 'upload'
              ? 'bg-white border-[#141414] text-[#141414] -mb-[1px]'
              : 'border-transparent text-[#141414]/70 hover:text-[#141414]'
          }`}
        >
          <UploadCloud className="w-3.5 h-3.5 text-[#141414]" />
          <span>Upload PDF / Image</span>
        </button>

        <button
          id="tab-paste"
          onClick={() => setActiveTab('paste')}
          className={`px-3 py-1.5 text-xs font-mono font-bold uppercase flex items-center space-x-1.5 border-t-2 border-x-2 transition ${
            activeTab === 'paste'
              ? 'bg-white border-[#141414] text-[#141414] -mb-[1px]'
              : 'border-transparent text-[#141414]/70 hover:text-[#141414]'
          }`}
        >
          <FileText className="w-3.5 h-3.5 text-[#141414]" />
          <span>Paste Note Extracts</span>
        </button>
      </div>

      {/* Tab Contents */}
      <div className="p-4 sm:p-5 bg-white">
        {/* TAB 1: Benchmark Samples */}
        {activeTab === 'samples' && (
          <div>
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h3 className="text-xs font-mono font-bold uppercase text-[#141414]">
                  Select Pre-Configured Audit Benchmark Case:
                </h3>
                <p className="text-[11px] font-serif italic text-[#141414]/70">
                  Select a real-world draft statement to inspect how the auditor catches KMP discrepancies, footing mismatches, and missing statutory disclosures.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {SAMPLE_STATEMENTS.map((sample) => (
                <div
                  key={sample.id}
                  id={`sample-card-${sample.id}`}
                  className="border border-[#141414] bg-[#F9F9F7] hover:bg-white p-3.5 transition flex flex-col justify-between shadow-dense-sm"
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="px-1.5 py-0.2 bg-[#D1D0CC] text-[#141414] font-mono text-[9px] font-bold border border-[#141414]/40 uppercase">
                        {sample.period}
                      </span>
                      {sample.id === 'zenith-consumer-fy25' ? (
                        <span className="text-[9px] font-mono font-bold uppercase text-white bg-green-700 px-1.5 py-0.2">
                          CLEAN DRAFT
                        </span>
                      ) : (
                        <span className="text-[9px] font-mono font-bold uppercase text-white bg-red-600 px-1.5 py-0.2">
                          DISCREPANCIES
                        </span>
                      )}
                    </div>

                    <h4 className="font-bold text-[#141414] text-xs uppercase tracking-tight">
                      {sample.title}
                    </h4>
                    <p className="text-[11px] font-serif italic text-[#141414]/80 mt-0.5 line-clamp-2">
                      {sample.description}
                    </p>

                    <div className="mt-2 p-1.5 bg-white border border-[#141414]/30 text-[10px] text-[#141414] font-mono line-clamp-3">
                      {sample.previewSnippet}
                    </div>

                    <div className="mt-2 text-[10px] text-red-900 bg-red-100 p-1.5 border border-red-300 font-mono">
                      <strong>TRIGGER:</strong> {sample.knownIssuesSummary}
                    </div>
                  </div>

                  <button
                    id={`btn-load-${sample.id}`}
                    onClick={() => handleSelectSample(sample)}
                    disabled={isAuditing}
                    className="mt-3 w-full py-1.5 px-3 text-xs font-mono font-bold uppercase bg-[#141414] hover:bg-neutral-800 text-white flex items-center justify-center space-x-1.5 transition border border-[#141414]"
                  >
                    <span>Execute Audit</span>
                    <ArrowRight className="w-3.5 h-3.5 text-[#00FF00]" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 2: Upload File */}
        {activeTab === 'upload' && (
          <div>
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed p-6 text-center cursor-pointer transition ${
                isDragging
                  ? 'border-[#141414] bg-[#D1D0CC]'
                  : selectedFile
                  ? 'border-green-700 bg-green-50'
                  : 'border-[#141414] bg-[#F9F9F7] hover:bg-[#E4E3E0]'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.csv"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    processFile(e.target.files[0]);
                  }
                }}
              />

              <div className="flex flex-col items-center justify-center">
                <UploadCloud className="w-8 h-8 text-[#141414] mb-2" />

                {selectedFile ? (
                  <div>
                    <div className="flex items-center justify-center space-x-2 text-green-800 font-bold text-xs uppercase font-mono">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>{selectedFile.name}</span>
                    </div>
                    <p className="text-[10px] text-[#141414]/70 mt-1 font-mono">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • {selectedFile.mimeType} READY FOR AUDIT.
                    </p>
                    <span className="inline-block mt-1 text-[10px] text-[#141414] font-bold underline font-mono">
                      CLICK TO CHANGE FILE
                    </span>
                  </div>
                ) : (
                  <div>
                    <p className="text-xs font-bold text-[#141414] uppercase font-mono">
                      DRAG & DROP FINANCIAL STATEMENT (PDF/IMAGE) OR <span className="underline">BROWSE</span>
                    </p>
                    <p className="text-[11px] font-serif italic text-[#141414]/70 mt-0.5">
                      Supports PDF Annual Reports, Balance Sheet Scans, P&L extracts, and detailed Notes to Accounts (Max 25MB).
                    </p>
                  </div>
                )}
              </div>
            </div>

            {fileError && (
              <div className="mt-2 p-2 bg-red-100 border border-red-400 text-xs text-red-800 flex items-center space-x-2 font-mono">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{fileError}</span>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: Direct Paste */}
        {activeTab === 'paste' && (
          <div>
            <div className="mb-1 flex items-center justify-between">
              <label htmlFor="financial-text-input" className="text-[10px] font-mono font-bold uppercase text-[#141414]">
                Paste Financial Statement Text, Schedules, or Notes:
              </label>
              <span className="text-[10px] font-mono text-[#141414]/60">
                {inputText.length} CHARACTERS
              </span>
            </div>

            <textarea
              id="financial-text-input"
              rows={8}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Paste Balance Sheet, Profit & Loss, Cash Flow Statement, and Note schedules here...

Example:
BALANCE SHEET AS AT MARCH 31, 2025 (₹ in Lakhs)
Property, Plant & Equipment (Note 3): ₹1,45,200.00
Trade Receivables (Note 11): ₹18,450.00
Trade Payables MSME (Note 23): ₹1,850.00
...
NOTE 33: RELATED PARTY DISCLOSURES (Ind AS 24)..."
              className="w-full font-mono text-xs p-3 border border-[#141414] focus:outline-none focus:ring-1 focus:ring-[#141414] bg-[#F9F9F7] text-[#141414]"
            />
          </div>
        )}

        {/* Run Action Bar */}
        {(activeTab === 'upload' || activeTab === 'paste') && (
          <div className="mt-4 flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-[#141414]/20">
            <div className="text-[10px] font-mono text-[#141414]/70 uppercase">
              STANDARDS: ICAI, SCHEDULE III DIV II, IND AS 1–116 CASTING VERIFICATION
            </div>

            <button
              id="run-audit-btn"
              onClick={handleStartAudit}
              disabled={!canSubmit || isAuditing}
              className={`w-full sm:w-auto px-5 py-2 text-xs font-mono font-bold uppercase flex items-center justify-center space-x-2 transition border border-[#141414] ${
                canSubmit && !isAuditing
                  ? 'bg-[#141414] hover:bg-neutral-800 text-white cursor-pointer'
                  : 'bg-[#D1D0CC] text-[#141414]/40 cursor-not-allowed border-neutral-400'
              }`}
            >
              <ShieldCheck className="w-4 h-4 text-[#00FF00]" />
              <span>{isAuditing ? 'Auditing Statements...' : 'Execute Statutory Audit'}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

