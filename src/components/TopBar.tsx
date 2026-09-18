import React, { useState } from 'react';
import {
  FileText,
  BookOpen,
  Printer,
  Moon,
  Sun,
  PlusCircle,
  Download,
  Upload,
  RotateCcw,
  ChevronDown,
  ShieldCheck,
  AlertTriangle,
  FileSpreadsheet,
  FileDown,
} from 'lucide-react';
import { EngagementData, ComputedMateriality } from '../types';
import { formatINR, formatCompactINR } from '../utils/calculations';

interface TopBarProps {
  engagement: EngagementData;
  materiality: ComputedMateriality;
  overallPercent: number;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  onOpenKnowledgeBase: () => void;
  onOpenPrintReport: () => void;
  onOpenTBImport: () => void;
  onOpenExportModal: () => void;
  onNavigateToTB: () => void;
  onSelectSample: () => void;
  onNewBlank: () => void;
  onResetSample: () => void;
  onExportJson: () => void;
  onImportJson: (file: File) => void;
  isSample: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  engagement,
  materiality,
  overallPercent,
  darkMode,
  onToggleDarkMode,
  onOpenKnowledgeBase,
  onOpenPrintReport,
  onOpenTBImport,
  onOpenExportModal,
  onNavigateToTB,
  onSelectSample,
  onNewBlank,
  onResetSample,
  onExportJson,
  onImportJson,
  isSample,
}) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const getStatusBadge = () => {
    const revConclusion = engagement.signOffReview?.reviewer?.conclusion;
    const isDeclared = engagement.signOffReview?.preparer?.declared;

    if (revConclusion === 'Planning Approved') {
      return {
        label: 'Approved',
        className: 'bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800',
        icon: ShieldCheck,
      };
    }
    if (revConclusion === 'Approved with Conditions') {
      return {
        label: 'Approved w/ Conditions',
        className: 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800',
        icon: AlertTriangle,
      };
    }
    if (revConclusion === 'Returned for Revision') {
      return {
        label: 'Revision Required',
        className: 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800',
        icon: AlertTriangle,
      };
    }
    if (isDeclared) {
      return {
        label: 'Pending Review',
        className: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800',
        icon: ShieldCheck,
      };
    }
    return {
      label: 'Planning Draft',
      className: 'bg-stone-200 text-stone-700 border-stone-300 dark:bg-stone-800 dark:text-stone-300 dark:border-stone-700',
      icon: FileText,
    };
  };

  const status = getStatusBadge();
  const StatusIcon = status.icon;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onImportJson(e.target.files[0]);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <header className="sticky top-0 z-40 bg-[#f7f6f2] dark:bg-[#14181d] border-b border-[#dedbd2] dark:border-[#272f38] px-4 py-2.5 shadow-sm transition-colors">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        {/* Left: Client Name & FY */}
        <div className="flex items-center gap-3 min-w-[260px]">
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-white dark:bg-[#1c222b] border border-[#d3cfc4] dark:border-[#2e3742] text-left hover:border-amber-700 dark:hover:border-amber-500 transition-colors shadow-xs"
              title="Switch or manage engagements"
            >
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-sm text-[#1e232a] dark:text-[#f3f4f6] truncate max-w-[200px] sm:max-w-[260px]">
                    {engagement.clientName}
                  </span>
                  <ChevronDown className="w-3.5 h-3.5 text-stone-500" />
                </div>
                <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-400">
                  <span className="font-mono-num font-medium text-amber-800 dark:text-amber-400">
                    {engagement.financialYear}
                  </span>
                  <span>•</span>
                  <span className="truncate max-w-[120px]">{engagement.auditType.split(' ')[0]}</span>
                  {isSample && (
                    <span className="px-1.5 py-0.2 rounded text-[10px] uppercase font-bold tracking-wider bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700">
                      Sample
                    </span>
                  )}
                </div>
              </div>
            </button>

            {/* Engagement Management Dropdown */}
            {dropdownOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setDropdownOpen(false)}
                />
                <div className="absolute left-0 mt-1 w-72 rounded-lg bg-white dark:bg-[#1c222b] border border-[#d3cfc4] dark:border-[#2e3742] shadow-xl z-50 py-1 text-sm animate-in fade-in zoom-in-95">
                  <div className="px-3 py-2 border-b border-stone-200 dark:border-stone-800">
                    <p className="text-xs font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-400">
                      Engagements
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      onSelectSample();
                      setDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-stone-100 dark:hover:bg-stone-800 flex items-center justify-between"
                  >
                    <div>
                      <p className="font-medium text-stone-900 dark:text-stone-100">Zenith Fabrics Pvt Ltd</p>
                      <p className="text-xs text-stone-500">FY 2025-26 (Illustrative Sample)</p>
                    </div>
                    {isSample && <span className="text-xs text-amber-700 dark:text-amber-400 font-semibold">Active</span>}
                  </button>
                  <button
                    onClick={() => {
                      onNewBlank();
                      setDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-stone-100 dark:hover:bg-stone-800 flex items-center gap-2 text-stone-800 dark:text-stone-200"
                  >
                    <PlusCircle className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <span>Create Blank Engagement</span>
                  </button>
                  <button
                    onClick={() => {
                      onResetSample();
                      setDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-stone-100 dark:hover:bg-stone-800 flex items-center gap-2 text-stone-800 dark:text-stone-200"
                  >
                    <RotateCcw className="w-4 h-4 text-amber-600" />
                    <span>Reset Sample to Defaults</span>
                  </button>
                  <div className="border-t border-stone-200 dark:border-stone-800 my-1" />
                  <button
                    onClick={() => {
                      onOpenTBImport();
                      setDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-stone-100 dark:hover:bg-stone-800 flex items-center gap-2 text-stone-800 dark:text-stone-200 font-medium"
                  >
                    <FileSpreadsheet className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <span>Import Client Trial Balance</span>
                  </button>
                  <button
                    onClick={() => {
                      onOpenExportModal();
                      setDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-stone-100 dark:hover:bg-stone-800 flex items-center gap-2 text-stone-800 dark:text-stone-200 font-medium"
                  >
                    <FileDown className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                    <span>Export Workpaper (Word/Excel/PDF)</span>
                  </button>
                  <div className="border-t border-stone-200 dark:border-stone-800 my-1" />
                  <button
                    onClick={() => {
                      onExportJson();
                      setDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-stone-100 dark:hover:bg-stone-800 flex items-center gap-2 text-stone-800 dark:text-stone-200"
                  >
                    <Download className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                    <span>Export Engagement JSON</span>
                  </button>
                  <label className="w-full text-left px-3 py-2 hover:bg-stone-100 dark:hover:bg-stone-800 flex items-center gap-2 text-stone-800 dark:text-stone-200 cursor-pointer">
                    <Upload className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                    <span>Import Engagement JSON</span>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".json"
                      onChange={handleFileChange}
                      className="hidden"
                    />
                  </label>
                </div>
              </>
            )}
          </div>

          <div
            className={`hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${status.className}`}
          >
            <StatusIcon className="w-3.5 h-3.5" />
            <span>{status.label}</span>
          </div>
        </div>

        {/* Center: Completion & Materiality Trio */}
        <div className="flex items-center gap-3 sm:gap-4 overflow-x-auto py-1">
          {/* Completion Gauge */}
          <div className="flex items-center gap-2 px-3 py-1 rounded-md bg-white/80 dark:bg-[#1a2027] border border-[#dedbd2] dark:border-[#2e3742] shrink-0">
            <div className="flex flex-col">
              <span className="text-[10px] uppercase font-semibold text-stone-500 tracking-wider">
                Planning Progress
              </span>
              <span className="font-mono-num text-sm font-bold text-stone-900 dark:text-stone-100">
                {overallPercent}%
              </span>
            </div>
            <div className="w-14 h-2 rounded-full bg-stone-200 dark:bg-stone-700 overflow-hidden">
              <div
                className="h-full bg-amber-700 dark:bg-amber-500 transition-all duration-300"
                style={{ width: `${overallPercent}%` }}
              />
            </div>
          </div>

          {/* Three Materiality Figures */}
          <div className="flex items-center divide-x divide-stone-300 dark:divide-stone-700 px-3 py-1 rounded-md bg-white/80 dark:bg-[#1a2027] border border-[#dedbd2] dark:border-[#2e3742] shrink-0">
            {/* Overall Materiality */}
            <div className="pr-3 flex flex-col">
              <span className="text-[10px] uppercase font-semibold text-stone-500 dark:text-stone-400 tracking-wider">
                Overall Mat. (OM)
              </span>
              <span
                className="font-mono-num text-xs sm:text-sm font-bold text-stone-900 dark:text-stone-100"
                title={formatINR(materiality.overallMateriality)}
              >
                {formatCompactINR(materiality.overallMateriality)}
              </span>
            </div>

            {/* Performance Materiality */}
            <div className="px-3 flex flex-col">
              <span className="text-[10px] uppercase font-semibold text-stone-500 dark:text-stone-400 tracking-wider">
                Perf. Mat. (PM)
              </span>
              <span
                className="font-mono-num text-xs sm:text-sm font-bold text-amber-800 dark:text-amber-400"
                title={formatINR(materiality.performanceMateriality)}
              >
                {formatCompactINR(materiality.performanceMateriality)}
              </span>
            </div>

            {/* Clearly Trivial */}
            <div className="pl-3 flex flex-col">
              <span className="text-[10px] uppercase font-semibold text-stone-500 dark:text-stone-400 tracking-wider">
                Clearly Trivial (CT)
              </span>
              <span
                className="font-mono-num text-xs sm:text-sm font-bold text-stone-700 dark:text-stone-300"
                title={formatINR(materiality.clearlyTrivialThreshold)}
              >
                {formatCompactINR(materiality.clearlyTrivialThreshold)}
              </span>
            </div>
          </div>
        </div>

        {/* Right Tools: TB, Export, ICAI KB, Print, Theme */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {/* Trial Balance Quick Nav / Indicator */}
          <button
            onClick={onNavigateToTB}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-white dark:bg-[#1c222b] border border-[#d3cfc4] dark:border-[#2e3742] text-stone-700 dark:text-stone-300 hover:border-amber-600 dark:hover:border-amber-500 text-xs font-medium transition-colors shadow-xs"
            title="View or manage client Trial Balance"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <span className="hidden sm:inline">TB</span>
            {engagement.trialBalance && engagement.trialBalance.items.length > 0 ? (
              <span className="px-1 py-0.2 rounded text-[10px] font-mono-num font-bold bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300">
                {engagement.trialBalance.items.length}
              </span>
            ) : (
              <span className="px-1 py-0.2 rounded text-[10px] bg-stone-100 dark:bg-stone-800 text-stone-500">
                None
              </span>
            )}
          </button>

          {/* Export Workpaper (Word/Excel/PDF) */}
          <button
            onClick={onOpenExportModal}
            className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-md bg-stone-900 hover:bg-stone-800 dark:bg-stone-100 dark:hover:bg-white text-white dark:text-stone-900 text-xs font-semibold shadow-xs transition-colors"
            title="Export complete workpaper to Microsoft Word (.doc), Excel (.xlsx), or PDF (.pdf)"
          >
            <FileDown className="w-3.5 h-3.5 text-amber-400 dark:text-amber-600" />
            <span>Export</span>
          </button>

          <button
            onClick={onOpenKnowledgeBase}
            className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-md bg-amber-50 dark:bg-amber-950/60 border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-300 text-xs font-semibold hover:bg-amber-100 dark:hover:bg-amber-900/50 transition-colors shadow-xs"
            title="ICAI Standards on Auditing Knowledge Base & AI query"
          >
            <BookOpen className="w-3.5 h-3.5 text-amber-700 dark:text-amber-400" />
            <span className="hidden md:inline">ICAI Knowledge Base</span>
            <span className="md:hidden">SAs</span>
          </button>

          <button
            onClick={onOpenPrintReport}
            className="p-1.5 sm:px-2.5 sm:py-1.5 rounded-md bg-white dark:bg-[#1c222b] border border-[#d3cfc4] dark:border-[#2e3742] text-stone-700 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 text-xs font-medium flex items-center gap-1.5 transition-colors shadow-xs"
            title="Print or view Audit Planning Memorandum report"
          >
            <Printer className="w-3.5 h-3.5" />
            <span className="hidden lg:inline">Print Memo</span>
          </button>

          <button
            onClick={onToggleDarkMode}
            className="p-1.5 rounded-md bg-white dark:bg-[#1c222b] border border-[#d3cfc4] dark:border-[#2e3742] text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors shadow-xs"
            title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            aria-label="Toggle dark mode"
          >
            {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-stone-600" />}
          </button>
        </div>
      </div>
    </header>
  );
};
