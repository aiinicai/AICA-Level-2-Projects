import React, { useState, useEffect, useRef } from 'react';
import { 
  FileText, 
  UploadCloud, 
  CheckCircle2, 
  ChevronRight, 
  ChevronLeft, 
  X, 
  FileSpreadsheet, 
  Layers, 
  Landmark, 
  ShieldCheck, 
  AlertCircle,
  Loader2,
  Trash2,
  Check,
  Calendar,
  Sparkles
} from 'lucide-react';
import { ApiClient } from '../api/client';
import { formatINR } from '../utils/formatters';

export interface SequentialUploadWizardModalProps {
  proposalId: string;
  proposalCode: string;
  clientName?: string;
  productType?: string;
  requestedAmount?: number | string;
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
}

interface UploadedFileRecord {
  id: string;
  filename: string;
  size: number;
  category: string;
  financialPeriod?: string;
  uploadedAt: string;
}

interface WizardStep {
  id: number;
  category: string;
  title: string;
  shortLabel: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  helperText: string;
  recommendedPeriods: string[];
  acceptedTypes: string;
  colorScheme: {
    bg: string;
    text: string;
    border: string;
    activeTab: string;
  };
}

const WIZARD_STEPS: WizardStep[] = [
  {
    id: 1,
    category: 'financial_statements',
    title: 'Audited Financial Statements & Balance Sheets',
    shortLabel: '1. Financials',
    icon: FileSpreadsheet,
    description: 'Upload complete Audited Financial Statements, Balance Sheets, Profit & Loss Statements, Schedules, and Tax Audit Reports (Form 3CD/3CB) for the last 3 Financial Years.',
    helperText: 'Antigravity financial parser will extract Operating Revenue, EBITDA, PAT, Depreciation, Net Worth, Current Ratio, and Debt figures for your CMA statements.',
    recommendedPeriods: ['FY 2023-24 (Audited)', 'FY 2024-25 (Audited/Provisional)', 'FY 2025-26 (Provisional/Estimated)'],
    acceptedTypes: '.pdf,.xlsx,.xls,.csv',
    colorScheme: {
      bg: 'bg-blue-50',
      text: 'text-blue-700',
      border: 'border-blue-200',
      activeTab: 'bg-[#1b2632] text-white',
    }
  },
  {
    id: 2,
    category: 'gst',
    title: 'Month-wise GST Returns (GSTR-3B & GSTR-1)',
    shortLabel: '2. Month-wise GST',
    icon: Layers,
    description: 'Upload month-wise GST returns (GSTR-3B monthly tax summary & GSTR-1 sales turnover for the trailing 12 months) or annual GSTR-9 reconciliation.',
    helperText: 'Verifies monthly sales turnover consistency against banking credits and flags circular trading or significant turnover variances.',
    recommendedPeriods: ['Q1 (Apr - Jun)', 'Q2 (Jul - Sep)', 'Q3 (Oct - Dec)', 'Q4 (Jan - Mar)', 'Annual GSTR-9'],
    acceptedTypes: '.pdf,.xlsx,.xls,.csv,.json',
    colorScheme: {
      bg: 'bg-emerald-50',
      text: 'text-emerald-700',
      border: 'border-emerald-200',
      activeTab: 'bg-[#1b2632] text-white',
    }
  },
  {
    id: 3,
    category: 'itr',
    title: 'Import Income Tax Returns (ITR-V & Computations)',
    shortLabel: '3. Import ITR',
    icon: FileText,
    description: 'Upload Income Tax Return Acknowledgements (ITR-V with barcode), Computation of Total Income sheets, and Form 26AS / AIS for the last 3 Assessment Years.',
    helperText: 'Cross-checks declared gross business income, tax provisions, partner/promoter remuneration, and TDS deductions.',
    recommendedPeriods: ['AY 2024-25 (FY 23-24)', 'AY 2025-26 (FY 24-25)', 'AY 2026-27 (FY 25-26)'],
    acceptedTypes: '.pdf,.json,.xml',
    colorScheme: {
      bg: 'bg-amber-50',
      text: 'text-amber-700',
      border: 'border-amber-200',
      activeTab: 'bg-[#1b2632] text-white',
    }
  },
  {
    id: 4,
    category: 'bank_statement',
    title: 'Operative Bank Statements & KYC Profile',
    shortLabel: '4. Banking & KYC',
    icon: Landmark,
    description: 'Upload 12 months operative CC / OD / Current account bank statements (PDF or Excel), along with Borrower Entity PAN and Promoter KYC documents.',
    helperText: 'Calculates Average Bank Balance (ABB), monthly total credits, cash withdrawal patterns, and checks for outward cheque/ECS bounces.',
    recommendedPeriods: ['Operative CC/OD Account (12 Months)', 'Current Account (12 Months)', 'Entity PAN & Incorporation'],
    acceptedTypes: '.pdf,.xlsx,.xls,.csv,.png,.jpg',
    colorScheme: {
      bg: 'bg-purple-50',
      text: 'text-purple-700',
      border: 'border-purple-200',
      activeTab: 'bg-[#1b2632] text-white',
    }
  }
];

export const SequentialUploadWizardModal: React.FC<SequentialUploadWizardModalProps> = ({
  proposalId,
  proposalCode,
  clientName,
  productType,
  requestedAmount,
  isOpen,
  onClose,
  onComplete,
}) => {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [selectedPeriod, setSelectedPeriod] = useState<string>('');
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileRecord[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeStep = WIZARD_STEPS[currentStepIndex];

  // Load existing documents for proposal on mount
  useEffect(() => {
    if (isOpen && proposalId) {
      loadProposalDocuments();
      setSelectedPeriod(activeStep.recommendedPeriods[0] || '');
    }
  }, [isOpen, proposalId]);

  useEffect(() => {
    setSelectedPeriod(activeStep.recommendedPeriods[0] || '');
    setUploadError(null);
  }, [currentStepIndex]);

  const loadProposalDocuments = async () => {
    try {
      const docs = await ApiClient.request<any[]>(`/proposals/${proposalId}/documents`);
      const mapped: UploadedFileRecord[] = docs.map(d => ({
        id: d.id,
        filename: d.original_filename,
        size: d.file_size || 0,
        category: d.category,
        uploadedAt: d.created_at,
      }));
      setUploadedFiles(mapped);
    } catch (err) {
      console.error('Failed to load proposal documents:', err);
    }
  };

  if (!isOpen) return null;

  // Filter files belonging to current step category
  const currentStepFiles = uploadedFiles.filter(f => {
    if (activeStep.category === 'bank_statement') {
      return f.category === 'bank_statement' || f.category === 'kyc';
    }
    return f.category === activeStep.category;
  });

  const handleFilesSelected = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    setUploadError(null);

    const targetCategory = activeStep.category;
    let successCount = 0;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append('category', targetCategory);
      formData.append('file', file);
      if (selectedPeriod) {
        formData.append('financial_period', selectedPeriod);
      }

      try {
        const res = await ApiClient.uploadFile<any>(`/proposals/${proposalId}/documents`, formData);
        setUploadedFiles(prev => [
          ...prev,
          {
            id: res.id,
            filename: res.original_filename || file.name,
            size: res.file_size || file.size,
            category: res.category || targetCategory,
            financialPeriod: selectedPeriod,
            uploadedAt: new Date().toISOString(),
          }
        ]);
        successCount++;
      } catch (err: any) {
        console.error(`Error uploading ${file.name}:`, err);
        setUploadError(err.message || `Failed to upload ${file.name}`);
      }
    }

    setIsUploading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files) {
      handleFilesSelected(e.dataTransfer.files);
    }
  };

  const handleNext = () => {
    if (currentStepIndex < WIZARD_STEPS.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
    } else {
      // Completed all steps
      onComplete();
    }
  };

  const handleBack = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const StepIcon = activeStep.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full border border-slate-200 overflow-hidden flex flex-col max-h-[92vh] animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-[#1b2632] via-[#243344] to-[#1b2632] text-white px-6 py-5 border-b border-slate-800 flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="bg-[#a45139] text-white text-[10px] font-black tracking-wider uppercase px-2 py-0.5 rounded shadow-sm">
                Case Initialized
              </span>
              <span className="font-mono text-xs font-semibold text-sky-200">
                {proposalCode}
              </span>
              {productType && (
                <span className="text-[11px] text-slate-300">
                  • {productType.replace(/_/g, ' ').toUpperCase()}
                </span>
              )}
              {requestedAmount && (
                <span className="text-[11px] font-semibold text-emerald-400">
                  • {formatINR(requestedAmount, 'standard')}
                </span>
              )}
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <span>Guided Document Upload Wizard</span>
              <Sparkles className="w-4 h-4 text-amber-400 inline" />
            </h2>
            <p className="text-xs text-slate-300">
              Borrower: <strong className="text-white">{clientName || 'Valued Client'}</strong>. Please upload documents in a logical sequence to initialize financial evaluations.
            </p>
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-700/50 transition-colors"
            title="Upload Later"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Wizard Step Progression Bar */}
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-3">
          <div className="grid grid-cols-4 gap-2">
            {WIZARD_STEPS.map((step, idx) => {
              const Icon = step.icon;
              const isCurrent = idx === currentStepIndex;
              const isPast = idx < currentStepIndex;
              const stepCount = uploadedFiles.filter(f => 
                step.category === 'bank_statement' 
                  ? (f.category === 'bank_statement' || f.category === 'kyc') 
                  : f.category === step.category
              ).length;

              return (
                <button
                  key={step.id}
                  onClick={() => setCurrentStepIndex(idx)}
                  className={`text-left p-2.5 rounded-xl transition-all border flex items-center gap-2.5 ${
                    isCurrent 
                      ? 'bg-[#1b2632] text-white border-[#1b2632] shadow-sm ring-2 ring-[#a45139]/50' 
                      : isPast
                        ? 'bg-emerald-50 text-emerald-900 border-emerald-200 hover:bg-emerald-100/70'
                        : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100/60'
                  }`}
                >
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold ${
                    isCurrent 
                      ? 'bg-[#a45139] text-white' 
                      : isPast 
                        ? 'bg-emerald-600 text-white' 
                        : 'bg-slate-100 text-slate-500'
                  }`}>
                    {isPast ? <Check className="w-4 h-4" /> : step.id}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-bold truncate leading-tight">
                      {step.shortLabel}
                    </p>
                    <p className={`text-[10px] truncate ${isCurrent ? 'text-slate-300' : 'text-slate-500'}`}>
                      {stepCount > 0 ? `${stepCount} file${stepCount > 1 ? 's' : ''} added` : 'Pending'}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Step Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          {/* Step Banner */}
          <div className="flex items-start gap-4 p-4 rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white shadow-sm">
            <div className={`p-3 rounded-xl border ${activeStep.colorScheme.bg} ${activeStep.colorScheme.text} ${activeStep.colorScheme.border} shadow-sm shrink-0`}>
              <StepIcon className="w-6 h-6" />
            </div>
            <div className="flex-1 space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-extrabold uppercase px-2 py-0.5 rounded bg-slate-200 text-slate-800">
                  Step {activeStep.id} of 4
                </span>
                <h3 className="text-base font-bold text-slate-900">
                  {activeStep.title}
                </h3>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                {activeStep.description}
              </p>
              <p className="text-[11px] font-medium text-slate-500 flex items-center gap-1.5 pt-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>{activeStep.helperText}</span>
              </p>
            </div>
          </div>

          {/* Period Selector & Tag */}
          <div className="bg-white p-3.5 rounded-xl border border-slate-200 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-[#a45139]" />
                <span>Select Target Financial Year / Period Tag:</span>
              </label>
              <span className="text-[11px] text-slate-400">
                Helps parser auto-assign data columns
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {activeStep.recommendedPeriods.map(period => (
                <button
                  key={period}
                  type="button"
                  onClick={() => setSelectedPeriod(period)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                    selectedPeriod === period
                      ? 'bg-[#1b2632] text-white border-[#1b2632] shadow-sm ring-1 ring-[#a45139]'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {period}
                </button>
              ))}
            </div>
          </div>

          {/* Drag & Drop Upload Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-2xl p-6 text-center transition-all cursor-pointer ${
              isDragOver 
                ? 'border-[#a45139] bg-[#faece7]/40 scale-[0.99]' 
                : 'border-slate-300 hover:border-[#a45139]/60 hover:bg-slate-50/70 bg-white'
            }`}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={activeStep.acceptedTypes}
              onChange={(e) => handleFilesSelected(e.target.files)}
              className="hidden"
            />
            
            <div className="max-w-md mx-auto space-y-3">
              <div className="w-12 h-12 mx-auto rounded-full bg-[#faece7] text-[#a45139] flex items-center justify-center shadow-inner">
                {isUploading ? (
                  <Loader2 className="w-6 h-6 animate-spin text-[#a45139]" />
                ) : (
                  <UploadCloud className="w-6 h-6 text-[#a45139]" />
                )}
              </div>

              <div>
                <p className="text-sm font-bold text-slate-900">
                  {isUploading ? 'Uploading & parsing document...' : 'Click to browse or drag & drop files here'}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Supported formats: <span className="font-mono text-slate-700">{activeStep.acceptedTypes.replace(/\./g, ' ').toUpperCase()}</span> (Up to 50 MB per file)
                </p>
                <p className="text-[11px] text-[#a45139] font-medium mt-1">
                  You can select multiple files at once.
                </p>
              </div>

              <button
                type="button"
                disabled={isUploading}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1b2632] hover:bg-[#243344] text-white text-xs font-bold shadow transition-colors"
              >
                <UploadCloud className="w-4 h-4 text-[#a45139]" />
                <span>Select {activeStep.shortLabel.split(' ')[1]} Files</span>
              </button>
            </div>
          </div>

          {/* Upload Error Banner */}
          {uploadError && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}

          {/* Uploaded Documents List in this Step */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Uploaded for this Step ({currentStepFiles.length})</span>
              </h4>
              {currentStepFiles.length > 0 && (
                <span className="text-[11px] text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  ✓ Ready for extraction
                </span>
              )}
            </div>

            {currentStepFiles.length === 0 ? (
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 text-center text-xs text-slate-500">
                No documents uploaded for this section yet. You can upload files now or skip to the next step.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {currentStepFiles.map((file) => (
                  <div
                    key={file.id}
                    className="p-3 rounded-xl border border-slate-200 bg-white hover:border-slate-300 shadow-sm flex items-center justify-between gap-3"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="p-2 rounded-lg bg-slate-100 text-[#1b2632] shrink-0">
                        <FileText className="w-4 h-4 text-[#a45139]" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-slate-900 truncate" title={file.filename}>
                          {file.filename}
                        </p>
                        <p className="text-[11px] text-slate-500 flex items-center gap-1">
                          <span>{formatFileSize(file.size)}</span>
                          {file.financialPeriod && (
                            <span>• <strong className="text-slate-700">{file.financialPeriod}</strong></span>
                          )}
                        </p>
                      </div>
                    </div>
                    <span className="shrink-0 text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 flex items-center gap-1">
                      <Check className="w-3 h-3" />
                      <span>Ingested</span>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="bg-slate-50 border-t border-slate-200 px-6 py-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleBack}
              disabled={currentStepIndex === 0}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors ${
                currentStepIndex === 0
                  ? 'text-slate-300 bg-slate-100 cursor-not-allowed'
                  : 'text-slate-700 bg-white border border-slate-300 hover:bg-slate-100 shadow-sm'
              }`}
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Back</span>
            </button>

            <button
              type="button"
              onClick={onClose}
              className="text-xs text-slate-500 hover:text-slate-800 underline px-2 py-1"
            >
              Upload later (Open Workspace)
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleNext}
              className="px-4 py-2 rounded-xl text-xs font-bold text-slate-700 bg-white border border-slate-300 hover:bg-slate-100 transition-colors shadow-sm"
            >
              {currentStepIndex === WIZARD_STEPS.length - 1 ? 'Skip & Finish' : 'Skip Step →'}
            </button>

            <button
              type="button"
              onClick={handleNext}
              className="px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-[#1b2632] to-[#a45139] hover:opacity-95 transition-all shadow-md flex items-center gap-2"
            >
              {currentStepIndex === WIZARD_STEPS.length - 1 ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Complete Ingestion & Open Workspace</span>
                </>
              ) : (
                <>
                  <span>Proceed to {WIZARD_STEPS[currentStepIndex + 1].shortLabel}</span>
                  <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
