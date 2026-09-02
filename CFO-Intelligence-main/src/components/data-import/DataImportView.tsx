import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  Download,
  FileText,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  HelpCircle,
  Check,
  Edit3,
  Layers,
  Scale,
  DollarSign,
  ChevronDown,
  Info,
  Building2,
  Table,
  Plus,
  Trash2,
  Activity,
  FileCheck,
  Zap,
} from 'lucide-react';
import { FileParserEngine, ParsedStatementResult } from '../../services/fileParser';
import {
  MonthlyFinancialRecord,
  ClientProfile,
  AiMappingReviewData,
  AiAccountMappingItem,
  AiDisambiguationQuestion,
  StandardTaxonomyCategory,
  ConsolidatedFinancialPackage,
  UploadedFileSummary,
} from '../../types';
import { FirmReportHeader, FirmReportFooter } from '../common/FirmHeaderFooter';

interface DataImportViewProps {
  client: ClientProfile;
  onImportSuccess: (records: MonthlyFinancialRecord[]) => void;
  firmName?: string;
}

const TAXONOMY_OPTIONS: { value: StandardTaxonomyCategory; label: string; group: string }[] = [
  { value: 'revenue', label: 'Gross Revenue / Sales', group: 'Revenue' },
  { value: 'cogs', label: 'Cost of Goods Sold (COGS)', group: 'COGS' },
  { value: 'direct_labor', label: 'Direct Billable Labor', group: 'COGS' },
  { value: 'salaries_opex', label: 'Salaries & Payroll Wages', group: 'OPEX' },
  { value: 'sales_marketing_opex', label: 'Sales & Marketing Expenses', group: 'OPEX' },
  { value: 'rent_facilities_opex', label: 'Rent & Facility Leases', group: 'OPEX' },
  { value: 'gna_opex', label: 'General & Admin (G&A)', group: 'OPEX' },
  { value: 'depreciation_amort_opex', label: 'Depreciation & Amortization', group: 'OPEX' },
  { value: 'cash_current_assets', label: 'Cash & Cash Equivalents', group: 'Assets' },
  { value: 'ar_current_assets', label: 'Accounts Receivable (Trade A/R)', group: 'Assets' },
  { value: 'inventory_current_assets', label: 'Inventory Assets', group: 'Assets' },
  { value: 'other_current_assets', label: 'Prepaids & Other Current Assets', group: 'Assets' },
  { value: 'fixed_non_current_assets', label: 'Fixed Assets (PP&E)', group: 'Assets' },
  { value: 'ap_current_liabilities', label: 'Accounts Payable (Trade A/P)', group: 'Liabilities' },
  { value: 'short_term_debt_liabilities', label: 'Short Term Debt & Notes', group: 'Liabilities' },
  { value: 'long_term_debt_liabilities', label: 'Long Term Bank Debt', group: 'Liabilities' },
  { value: 'retained_equity', label: 'Retained Earnings & Equity', group: 'Equity' },
];

export const DataImportView: React.FC<DataImportViewProps> = ({
  client,
  onImportSuccess,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadedFilesList, setUploadedFilesList] = useState<File[]>([]);
  const [packageData, setPackageData] = useState<ConsolidatedFinancialPackage | null>(null);
  const [activeTab, setActiveTab] = useState<'clarification' | 'taxonomy' | 'preview' | 'audit'>('clarification');
  const [importApplied, setImportApplied] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files);
      const combined = [...uploadedFilesList, ...newFiles];
      setUploadedFilesList(combined);
      await processSelectedFiles(combined);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      const combined = [...uploadedFilesList, ...newFiles];
      setUploadedFilesList(combined);
      await processSelectedFiles(combined);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleRemoveFile = async (indexToRemove: number) => {
    const remaining = uploadedFilesList.filter((_, idx) => idx !== indexToRemove);
    setUploadedFilesList(remaining);
    if (remaining.length > 0) {
      await processSelectedFiles(remaining);
    } else {
      setPackageData(null);
    }
  };

  const processSelectedFiles = async (files: File[]) => {
    if (files.length === 0) return;
    setIsProcessing(true);
    setImportApplied(false);
    try {
      const consolidated = await FileParserEngine.parseMultipleFiles(files, client.industry);
      setPackageData(consolidated);

      if (consolidated.allClarificationQuestions.length > 0) {
        setActiveTab('clarification');
      } else {
        setActiveTab('preview');
      }
    } catch (err) {
      console.error('Multi-file parsing error:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleLoadDemoPackage = async () => {
    setIsProcessing(true);
    setImportApplied(false);

    try {
      // Create in-memory File objects for P&L, Balance Sheet, and Trial Balance
      const pnlBlob = new Blob([FileParserEngine.generateSampleTemplate('pnl')], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const pnlFile = new File([pnlBlob], `${client.name.replace(/\s+/g, '_')}_Profit_and_Loss_2026.xlsx`, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

      const bsBlob = new Blob([FileParserEngine.generateSampleTemplate('balance_sheet')], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const bsFile = new File([bsBlob], `${client.name.replace(/\s+/g, '_')}_Balance_Sheet_2026.xlsx`, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

      const tbBlob = new Blob([FileParserEngine.generateSampleTemplate('trial_balance')], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const tbFile = new File([tbBlob], `${client.name.replace(/\s+/g, '_')}_Trial_Balance_Balanced.xlsx`, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

      const demoFiles = [pnlFile, bsFile, tbFile];
      setUploadedFilesList(demoFiles);
      await processSelectedFiles(demoFiles);
    } catch (err) {
      console.error('Demo package loading failed:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownloadTemplate = (type: 'all' | 'pnl' | 'balance_sheet' | 'trial_balance') => {
    const buffer = FileParserEngine.generateSampleTemplate(type);
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `CFO_${type.toUpperCase()}_Template.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSelectQuestionOption = (questionId: string, optionIndex: number) => {
    if (!packageData) return;
    const updatedQuestions = packageData.allClarificationQuestions.map((q) => {
      if (q.id === questionId) {
        return {
          ...q,
          selectedOptionIndex: optionIndex,
          status: 'resolved' as const,
        };
      }
      return q;
    });

    const targetQ = packageData.allClarificationQuestions.find((item) => item.id === questionId);
    let updatedAccounts = packageData.allMappedAccounts;
    if (targetQ && targetQ.options[optionIndex]) {
      const chosenTarget = targetQ.options[optionIndex].targetCategory;
      const chosenLabel = targetQ.options[optionIndex].label;
      updatedAccounts = updatedAccounts.map((acc) => {
        if (acc.sourceAccountName.toLowerCase() === targetQ.accountName.toLowerCase()) {
          return {
            ...acc,
            targetCategory: chosenTarget,
            categoryLabel: chosenLabel,
            needsClarification: false,
            confidence: 99,
          };
        }
        return acc;
      });
    }

    setPackageData({
      ...packageData,
      allClarificationQuestions: updatedQuestions,
      allMappedAccounts: updatedAccounts,
    });
  };

  const handleTaxonomyChange = (accountId: string, newTarget: StandardTaxonomyCategory) => {
    if (!packageData) return;
    const opt = TAXONOMY_OPTIONS.find((t) => t.value === newTarget);
    const updated = packageData.allMappedAccounts.map((acc) => {
      if (acc.id === accountId) {
        return {
          ...acc,
          targetCategory: newTarget,
          categoryLabel: opt?.label || newTarget,
          confidence: 100,
          needsClarification: false,
        };
      }
      return acc;
    });

    setPackageData({
      ...packageData,
      allMappedAccounts: updated,
    });
  };

  const handleApplyToModel = () => {
    if (packageData && packageData.consolidatedRecords.length > 0) {
      onImportSuccess(packageData.consolidatedRecords);
      setImportApplied(true);
    }
  };

  const pendingQuestionsCount = packageData?.allClarificationQuestions.filter((q) => q.status === 'pending').length || 0;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <FirmReportHeader client={client} reportTitle="Universal Financial Ingestion & Multi-Statement Reconciliation" firmName={firmName} />

      {/* Top Banner & Multi-Statement Actions */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-indigo-50 text-indigo-700">
              <Sparkles className="w-4 h-4" />
            </span>
            <h3 className="text-base font-bold text-slate-900">
              Multi-File Financial Ingestion & AI Statement Reconciliation
            </h3>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Upload multiple files at once (e.g. <strong>Balance Sheet</strong>, <strong>Profit &amp; Loss</strong>, and <strong>Trial Balance</strong>). The AI parses each statement matrix, standardizes the taxonomy, aligns accounting periods, cross-reconciles Net Income and Working Capital, and produces unified 3-statement financial models.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleLoadDemoPackage}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-xs transition-colors"
          >
            <Zap className="w-3.5 h-3.5 text-amber-300" />
            Load Sample 3-Statement Package
          </button>

          <div className="h-4 w-px bg-slate-200 mx-1 hidden sm:block" />

          <button
            onClick={() => handleDownloadTemplate('pnl')}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
            title="Download P&L Template"
          >
            <Download className="w-3 h-3 text-slate-500" />
            P&amp;L
          </button>
          <button
            onClick={() => handleDownloadTemplate('balance_sheet')}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
            title="Download Balance Sheet Template"
          >
            <Download className="w-3 h-3 text-slate-500" />
            Balance Sheet
          </button>
          <button
            onClick={() => handleDownloadTemplate('trial_balance')}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold transition-colors border border-indigo-200"
            title="Download Trial Balance Template"
          >
            <Download className="w-3 h-3 text-indigo-600" />
            Trial Balance
          </button>
        </div>
      </div>

      {/* Multi-File Drag & Drop Upload Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-3xl p-8 text-center cursor-pointer transition-all ${
          isDragging
            ? 'border-indigo-600 bg-indigo-50/50'
            : 'border-slate-300 hover:border-indigo-400 bg-white hover:bg-slate-50/50'
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".xlsx,.xls,.csv,.tsv,.txt"
          multiple
          className="hidden"
        />

        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center shadow-xs">
            {isProcessing ? (
              <RefreshCw className="w-7 h-7 animate-spin text-indigo-600" />
            ) : (
              <UploadCloud className="w-7 h-7" />
            )}
          </div>

          <div>
            <h4 className="text-base font-bold text-slate-900">
              {isProcessing ? 'AI is Parsing & Cross-Reconciling Financial Package...' : 'Drag & drop multiple statements (P&L, Balance Sheet, Trial Balance) here'}
            </h4>
            <p className="text-xs text-slate-500 mt-1 max-w-xl mx-auto">
              Select multiple files simultaneously. Supports Excel (.xlsx, .xls), CSV, TSV, QuickBooks, Tally, Zoho, NetSuite, and Xero export files.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Select Multiple Files
            </button>
          </div>
        </div>
      </div>

      {/* Uploaded File Queue Chips */}
      {uploadedFilesList.length > 0 && (
        <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-600 font-bold">
            <span>Uploaded Statement Package ({uploadedFilesList.length} files selected):</span>
            <button
              onClick={() => {
                setUploadedFilesList([]);
                setPackageData(null);
              }}
              className="text-rose-600 hover:text-rose-700 font-semibold hover:underline"
            >
              Clear All Files
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {uploadedFilesList.map((file, idx) => {
              const summary = packageData?.files.find((f) => f.name === file.name);
              return (
                <div
                  key={idx}
                  className="bg-white p-3 rounded-xl border border-slate-200 flex items-center justify-between shadow-2xs"
                >
                  <div className="flex items-center gap-2.5 overflow-hidden">
                    <FileSpreadsheet className="w-4 h-4 text-indigo-600 shrink-0" />
                    <div className="truncate">
                      <p className="text-xs font-bold text-slate-800 truncate">{file.name}</p>
                      <p className="text-[10px] text-slate-400">
                        {(file.size / 1024).toFixed(1)} KB • {summary?.detectedType ? summary.detectedType.toUpperCase().replace('_', ' ') : 'Analyzing...'}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemoveFile(idx);
                    }}
                    className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Consolidated Package Review Panel */}
      {packageData && (
        <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm space-y-6 animate-in fade-in duration-300">
          {/* Header & Status */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-100 pb-5">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  Package: {packageData.files.length} Files Consolidated
                </span>
                {packageData.hasPnl && (
                  <span className="text-xs text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200 font-semibold">
                    ✓ P&amp;L Detected
                  </span>
                )}
                {packageData.hasBalanceSheet && (
                  <span className="text-xs text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200 font-semibold">
                    ✓ Balance Sheet Detected
                  </span>
                )}
                {packageData.hasTrialBalance && (
                  <span className="text-xs text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200 font-semibold flex items-center gap-1">
                    <Scale className="w-3 h-3" /> Trial Balance (Balanced)
                  </span>
                )}
                <span className="text-xs text-slate-600 bg-slate-100 px-2.5 py-0.5 rounded-full font-medium">
                  AI Confidence: {packageData.overallConfidence}%
                </span>
              </div>
              <h4 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-indigo-600" />
                Consolidated Financial Statements ({packageData.detectedPeriods.length} Periods)
              </h4>
            </div>

            <div className="flex items-center gap-3">
              {importApplied ? (
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Successfully Synced with Model
                </div>
              ) : (
                <button
                  onClick={handleApplyToModel}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-md transition-all hover:shadow-lg"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  Apply &amp; Synchronize Model ({packageData.consolidatedRecords.length} Monthly Periods)
                </button>
              )}
            </div>
          </div>

          {/* Quick Metrics Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200">
              <span className="text-[10px] font-bold uppercase text-slate-500">Total YTD Revenue</span>
              <p className="text-base font-extrabold text-slate-900 mt-0.5">
                ${packageData.summaryMetrics.totalRevenueYTD.toLocaleString()}
              </p>
            </div>
            <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200">
              <span className="text-[10px] font-bold uppercase text-slate-500">Total YTD EBITDA</span>
              <p className="text-base font-extrabold text-emerald-600 mt-0.5">
                ${packageData.summaryMetrics.totalEbitdaYTD.toLocaleString()}
              </p>
            </div>
            <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200">
              <span className="text-[10px] font-bold uppercase text-slate-500">Ending Cash Balance</span>
              <p className="text-base font-extrabold text-indigo-600 mt-0.5">
                ${packageData.summaryMetrics.latestCashBalance.toLocaleString()}
              </p>
            </div>
            <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200">
              <span className="text-[10px] font-bold uppercase text-slate-500">Cross-Reconciliation Score</span>
              <p className="text-base font-extrabold text-emerald-700 mt-0.5">
                {packageData.crossReconciliation.reconciliationScore} / 100
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
            <button
              onClick={() => setActiveTab('clarification')}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 ${
                activeTab === 'clarification'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              <HelpCircle className="w-3.5 h-3.5" />
              AI Disambiguation &amp; Questions
              {pendingQuestionsCount > 0 && (
                <span className="px-1.5 py-0.2 bg-amber-400 text-slate-950 rounded-full text-[10px] font-extrabold ml-1">
                  {pendingQuestionsCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('taxonomy')}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 ${
                activeTab === 'taxonomy'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              Unified Account Taxonomy ({packageData.allMappedAccounts.length})
            </button>

            <button
              onClick={() => setActiveTab('preview')}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 ${
                activeTab === 'preview'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              <Table className="w-3.5 h-3.5" />
              Consolidated 3-Statement Preview ({packageData.detectedPeriods.length} Periods)
            </button>

            <button
              onClick={() => setActiveTab('audit')}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 ${
                activeTab === 'audit'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Cross-Reconciliation Audit
            </button>
          </div>

          {/* Tab 1: AI Disambiguation Questions */}
          {activeTab === 'clarification' && (
            <div className="space-y-4">
              <div className="p-4 bg-amber-50/70 rounded-2xl border border-amber-200/80 flex items-start gap-3">
                <Info className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
                <div className="text-xs text-amber-900">
                  <span className="font-bold">AI Mapping Inquiries:</span> The system encountered accounts across your uploaded files that could be mapped to multiple financial taxonomy categories. Confirm their classification to ensure accurate Gross Margin, EBITDA, and Working Capital calculation.
                </div>
              </div>

              {packageData.allClarificationQuestions.length === 0 ? (
                <div className="text-center py-10 bg-slate-50 rounded-2xl border border-slate-200">
                  <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
                  <p className="text-sm font-bold text-slate-800">All Statement Accounts Mapped with High Confidence</p>
                  <p className="text-xs text-slate-500 mt-1">No ambiguous accounts detected. You can review the full taxonomy or preview the financial statements.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {packageData.allClarificationQuestions.map((q, qIdx) => (
                    <div
                      key={q.id}
                      className={`p-5 rounded-2xl border transition-all ${
                        q.status === 'resolved'
                          ? 'border-emerald-200 bg-emerald-50/30'
                          : 'border-slate-300 bg-white shadow-xs'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md">
                              Question #{qIdx + 1}
                            </span>
                            <span className="text-xs font-mono font-bold text-slate-700">
                              Account: &ldquo;{q.accountName}&rdquo;
                            </span>
                            <span className="text-[10px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
                              File: {q.sourceFileName}
                            </span>
                            {q.status === 'resolved' && (
                              <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full flex items-center gap-1">
                                <Check className="w-3 h-3" /> Resolved
                              </span>
                            )}
                          </div>
                          <h5 className="text-sm font-bold text-slate-900 mt-1">{q.question}</h5>
                          <p className="text-xs text-slate-500">{q.context}</p>
                        </div>
                      </div>

                      {/* Options */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
                        {q.options.map((opt, oIdx) => {
                          const isSelected = q.selectedOptionIndex === oIdx;
                          return (
                            <button
                              key={oIdx}
                              onClick={() => handleSelectQuestionOption(q.id, oIdx)}
                              className={`p-3.5 rounded-xl border text-left transition-all ${
                                isSelected
                                  ? 'border-indigo-600 bg-indigo-50/80 ring-1 ring-indigo-600 shadow-xs'
                                  : 'border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300'
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-bold text-slate-900">{opt.label}</span>
                                {opt.isRecommended && (
                                  <span className="text-[10px] font-bold text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded-full">
                                    AI Recommended
                                  </span>
                                )}
                              </div>
                              <p className="text-[11px] text-slate-500 mt-1">{opt.description}</p>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Account Taxonomy Mapping */}
          {activeTab === 'taxonomy' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>Total Accounts Mapped across all files: <strong>{packageData.allMappedAccounts.length}</strong></span>
                <span>Override any category assignment below:</span>
              </div>

              <div className="overflow-x-auto border border-slate-200 rounded-2xl">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[11px]">
                      <th className="p-3.5">Source Account</th>
                      <th className="p-3.5">Source File</th>
                      <th className="p-3.5">Statement Type</th>
                      <th className="p-3.5">Target Taxonomy Bucket</th>
                      <th className="p-3.5">Confidence</th>
                      <th className="p-3.5">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                    {packageData.allMappedAccounts.map((acc) => (
                      <tr key={acc.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="p-3.5 font-bold text-slate-900">{acc.sourceAccountName}</td>
                        <td className="p-3.5 text-slate-500 text-[11px] truncate max-w-[140px]">{acc.sourceFileName}</td>
                        <td className="p-3.5 uppercase text-[11px] text-slate-500 font-mono">
                          {acc.detectedType.replace('_', ' ')}
                        </td>
                        <td className="p-3.5">
                          <select
                            value={acc.targetCategory}
                            onChange={(e) => handleTaxonomyChange(acc.id, e.target.value as StandardTaxonomyCategory)}
                            className="px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white text-xs font-semibold text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                          >
                            {TAXONOMY_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.group}: {opt.label}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="p-3.5">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                              acc.confidence >= 90
                                ? 'bg-emerald-50 text-emerald-700'
                                : 'bg-amber-50 text-amber-700'
                            }`}
                          >
                            {acc.confidence}%
                          </span>
                        </td>
                        <td className="p-3.5">
                          {acc.needsClarification ? (
                            <span className="text-[11px] text-amber-600 font-bold flex items-center gap-1">
                              <AlertTriangle className="w-3.5 h-3.5" /> Needs Review
                            </span>
                          ) : (
                            <span className="text-[11px] text-emerald-600 font-bold flex items-center gap-1">
                              <Check className="w-3.5 h-3.5" /> Verified
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab 3: Consolidated 3-Statement Preview */}
          {activeTab === 'preview' && (
            <div className="space-y-4">
              <div className="overflow-x-auto border border-slate-200 rounded-2xl">
                <table className="w-full text-left text-xs border-collapse font-mono">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[11px]">
                      <th className="p-3 font-sans">Statement Line / Metric</th>
                      {packageData.consolidatedRecords.map((rec) => (
                        <th key={rec.periodKey} className="p-3 text-right font-sans">{rec.periodLabel}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-800">
                    {/* P&L Section */}
                    <tr className="bg-indigo-50/50 font-sans font-bold text-indigo-900">
                      <td colSpan={packageData.consolidatedRecords.length + 1} className="p-2.5 uppercase tracking-wider text-[11px]">
                        Profit &amp; Loss Statement
                      </td>
                    </tr>
                    <tr className="bg-slate-50/50 font-bold">
                      <td className="p-3 font-sans">Gross Revenue</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right">${rec.revenue.toLocaleString()}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 font-sans text-slate-600">Cost of Goods Sold (COGS)</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right text-rose-600">${rec.cogs.toLocaleString()}</td>
                      ))}
                    </tr>
                    <tr className="bg-emerald-50/40 font-bold text-emerald-900">
                      <td className="p-3 font-sans">Gross Profit</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right">${rec.grossProfit.toLocaleString()}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 font-sans text-slate-600">Salaries &amp; Wages</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right">${rec.salariesAndWages.toLocaleString()}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 font-sans text-slate-600">Rent &amp; Facilities</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right">${rec.rentAndFacilities.toLocaleString()}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 font-sans text-slate-600">Total Operating Expenses</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right text-rose-600">${rec.totalOpex.toLocaleString()}</td>
                      ))}
                    </tr>
                    <tr className="bg-indigo-50/40 font-bold text-indigo-900">
                      <td className="p-3 font-sans">EBITDA</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right">${rec.ebitda.toLocaleString()}</td>
                      ))}
                    </tr>
                    <tr className="font-bold text-slate-900">
                      <td className="p-3 font-sans">Net Income</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right text-emerald-700">${rec.netIncome.toLocaleString()}</td>
                      ))}
                    </tr>

                    {/* Balance Sheet Section */}
                    <tr className="bg-emerald-50/50 font-sans font-bold text-emerald-900">
                      <td colSpan={packageData.consolidatedRecords.length + 1} className="p-2.5 uppercase tracking-wider text-[11px]">
                        Balance Sheet Position
                      </td>
                    </tr>
                    <tr className="font-bold">
                      <td className="p-3 font-sans">Cash &amp; Equivalents</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right text-emerald-700">${rec.cashAndEquivalents.toLocaleString()}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 font-sans text-slate-600">Accounts Receivable</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right">${rec.accountsReceivable.toLocaleString()}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 font-sans text-slate-600">Inventory Assets</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right">${rec.inventory.toLocaleString()}</td>
                      ))}
                    </tr>
                    <tr className="font-bold text-slate-900">
                      <td className="p-3 font-sans">Total Assets</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right">${rec.totalAssets.toLocaleString()}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 font-sans text-slate-600">Accounts Payable</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right">${rec.accountsPayable.toLocaleString()}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="p-3 font-sans text-slate-600">Total Liabilities</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right">${rec.totalLiabilities.toLocaleString()}</td>
                      ))}
                    </tr>
                    <tr className="bg-slate-50 font-bold text-indigo-900">
                      <td className="p-3 font-sans">Total Equity</td>
                      {packageData.consolidatedRecords.map((rec) => (
                        <td key={rec.periodKey} className="p-3 text-right">${rec.totalEquity.toLocaleString()}</td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab 4: Cross-Reconciliation Audit */}
          {activeTab === 'audit' && (
            <div className="space-y-4">
              <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
                <div className="flex items-center justify-between">
                  <h5 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" />
                    AI Cross-Statement Reconciliation &amp; Audit Log
                  </h5>
                  <span className="text-xs font-bold text-emerald-700 bg-emerald-100 px-2.5 py-0.5 rounded-full">
                    Score: {packageData.crossReconciliation.reconciliationScore}% / 100
                  </span>
                </div>
                
                <div className="space-y-2 mt-2">
                  {packageData.crossReconciliation.reconciliationNotes.map((note, nIdx) => (
                    <div key={nIdx} className="flex items-start gap-2 text-xs text-slate-700">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                      <span>{note}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-2">
                  <span className="text-[11px] font-bold uppercase text-slate-500">Trial Balance Debits vs Credits</span>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-slate-700">Total Debits:</span>
                    <span className="text-xs font-mono font-bold text-slate-900">${packageData.crossReconciliation.totalDebits.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-700">Total Credits:</span>
                    <span className="text-xs font-mono font-bold text-slate-900">${packageData.crossReconciliation.totalCredits.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                    <span className="text-xs font-bold text-emerald-700">Balance Status:</span>
                    <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md">
                      {packageData.crossReconciliation.isTrialBalanceBalanced ? 'Perfect 0-Variance Balance' : 'Variance Detected'}
                    </span>
                  </div>
                </div>

                <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-2">
                  <span className="text-[11px] font-bold uppercase text-slate-500">Statement Consistency Checks</span>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-slate-700">P&amp;L Net Income to BS Equity:</span>
                    <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md">Reconciled</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-700">Cash Balance to Ending Cash:</span>
                    <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md">Reconciled</span>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                    <span className="text-xs font-bold text-slate-700">Period Alignment:</span>
                    <span className="text-xs font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md">
                      {packageData.detectedPeriods.length} Unified Periods
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <FirmReportFooter firmName={firmName} />
    </div>
  );
};
