import React from 'react';
import { 
  FileText, 
  Download, 
  Printer, 
  Monitor, 
  FolderDown, 
  RotateCcw, 
  Save, 
  Check, 
  Sparkles,
  Layers,
  Eye,
  SlidersHorizontal,
  ChevronDown,
  FileDown,
  Loader2
} from 'lucide-react';
import { IndustryPreset } from '../types';
import { usePWAInstall } from '../hooks/usePWAInstall';
import { TrialBadge } from './TrialBadge';
import { LicenseStatus } from '../utils/licenseManager';

interface NavbarProps {
  onPreview: () => void;
  onDownloadWord: () => void;
  onDownloadPDF: () => void;
  onPrint?: () => void;
  isExportingPdf?: boolean;
  onOpenDesktopModal: () => void;
  onSaveDraft: () => void;
  onReset: () => void;
  presets: IndustryPreset[];
  onSelectPreset: (preset: IndustryPreset) => void;
  lastSavedTime: string | null;
  activeView: 'form' | 'preview' | 'split';
  setActiveView: (view: 'form' | 'preview' | 'split') => void;
  firmName?: string;
  deedType?: 'original' | 'supplementary' | 'dissolution';
  onSelectDeedType?: (type: 'original' | 'supplementary' | 'dissolution') => void;
  licenseStatus?: LicenseStatus;
  onOpenActivation?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onPreview,
  onDownloadWord,
  onDownloadPDF,
  onPrint,
  isExportingPdf = false,
  onOpenDesktopModal,
  onSaveDraft,
  onReset,
  presets,
  onSelectPreset,
  lastSavedTime,
  activeView,
  setActiveView,
  firmName,
  deedType = 'original',
  onSelectDeedType,
  licenseStatus,
  onOpenActivation,
}) => {
  const { isInstallable, isInstalled, install } = usePWAInstall();

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 sm:px-6 lg:px-8 shrink-0 text-slate-800 select-none z-30 print:hidden">
      
      <div className="flex items-center gap-3">
        <img 
          src="./icon.svg" 
          alt="Partnership Deed Drafter Logo" 
          className="w-9 h-9 rounded-xl shadow-md border border-amber-400/40 shrink-0 object-cover"
        />
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-base tracking-tight text-slate-900">
              DeedDraft<span className="text-blue-600">Pro</span>
            </span>
            <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
              IT Act 2025 Sec 35(e)
            </span>
          </div>
          <p className="text-[11px] text-slate-500 hidden sm:block leading-none mt-0.5">
            Indian Partnership Act 1932 Conveyancing Engine
          </p>
        </div>
      </div>

      {/* Middle: Current Project Indicator & Presets */}
      <div className="hidden lg:flex items-center gap-4">
        {firmName && (
          <div className="text-right border-r border-slate-200 pr-4 max-w-[220px]">
            <span className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Current Project
            </span>
            <span className="block text-xs font-semibold text-slate-800 truncate" title={firmName}>
              {firmName}
            </span>
          </div>
        )}

        {/* Deed Format Switcher (Original, Supplementary, Dissolution) */}
        {onSelectDeedType && (
          <div className="relative group">
            <button
              type="button"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-blue-200 bg-blue-50/70 hover:bg-blue-100 text-xs font-bold text-blue-900 transition shadow-2xs"
            >
              <FileText className="w-3.5 h-3.5 text-blue-700" />
              <span>
                {deedType === 'supplementary' 
                  ? 'Format: Supplementary Deed' 
                  : deedType === 'dissolution' 
                  ? 'Format: Dissolution Deed' 
                  : 'Format: Original Deed'}
              </span>
              <ChevronDown className="w-3 h-3 text-blue-600 ml-0.5" />
            </button>
            <div className="absolute left-0 mt-1 w-72 bg-white border border-slate-200 rounded-xl shadow-xl p-2 hidden group-hover:block transition-all z-50">
              <div className="text-[10px] font-bold text-slate-400 px-2 py-1 uppercase tracking-wider">
                Select Deed Legal Format
              </div>
              <button
                type="button"
                onClick={() => onSelectDeedType('original')}
                className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition flex items-start gap-2.5 ${
                  deedType === 'original' 
                    ? 'bg-blue-50 text-blue-800 font-bold' 
                    : 'text-slate-700 hover:bg-slate-50 font-medium'
                }`}
              >
                <div className="w-2 h-2 rounded-full bg-blue-600 mt-1.5 shrink-0"></div>
                <div>
                  <div className="font-bold">Original Partnership Deed</div>
                  <div className="text-[10px] text-slate-500 font-normal">New firm formation under Act of 1932</div>
                </div>
              </button>
              <button
                type="button"
                onClick={() => onSelectDeedType('supplementary')}
                className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition flex items-start gap-2.5 ${
                  deedType === 'supplementary' 
                    ? 'bg-blue-50 text-blue-800 font-bold' 
                    : 'text-slate-700 hover:bg-slate-50 font-medium'
                }`}
              >
                <div className="w-2 h-2 rounded-full bg-indigo-600 mt-1.5 shrink-0"></div>
                <div>
                  <div className="font-bold">Supplementary / Modification Deed</div>
                  <div className="text-[10px] text-slate-500 font-normal">OCR PDF scan, partner/clause/remun change</div>
                </div>
              </button>
              <button
                type="button"
                onClick={() => onSelectDeedType('dissolution')}
                className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition flex items-start gap-2.5 ${
                  deedType === 'dissolution' 
                    ? 'bg-blue-50 text-blue-800 font-bold' 
                    : 'text-slate-700 hover:bg-slate-50 font-medium'
                }`}
              >
                <div className="w-2 h-2 rounded-full bg-red-600 mt-1.5 shrink-0"></div>
                <div>
                  <div className="font-bold">Deed of Dissolution</div>
                  <div className="text-[10px] text-slate-500 font-normal">OCR scan, firm winding up & asset division</div>
                </div>
              </button>
            </div>
          </div>
        )}

        {/* Industry Presets Dropdown */}
        <div className="relative group">
          <button 
            type="button" 
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition shadow-2xs"
          >
            <Layers className="w-3.5 h-3.5 text-blue-600" />
            <span>Load Presets</span>
            <ChevronDown className="w-3 h-3 text-slate-400 ml-0.5" />
          </button>
          <div className="absolute left-0 mt-1 w-64 bg-white border border-slate-200 rounded-xl shadow-xl p-2 hidden group-hover:block transition-all z-50">
            <div className="text-[10px] font-bold text-slate-400 px-2 py-1 uppercase tracking-wider">
              Quick Business Templates
            </div>
            {presets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => onSelectPreset(preset)}
                className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:bg-blue-50 hover:text-blue-700 transition flex items-center gap-2"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-blue-600 shrink-0"></span>
                <span className="truncate">{preset.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* View Switcher: Editor / Split / Preview */}
        <div className="flex bg-slate-100 p-0.5 rounded-lg border border-slate-200">
          <button
            type="button"
            onClick={() => setActiveView('form')}
            className={`px-3 py-1 rounded-md text-xs font-semibold transition ${
              activeView === 'form' 
                ? 'bg-white text-blue-700 shadow-xs' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Form Editor
          </button>
          <button
            type="button"
            onClick={() => setActiveView('split')}
            className={`hidden xl:block px-3 py-1 rounded-md text-xs font-semibold transition ${
              activeView === 'split' 
                ? 'bg-white text-blue-700 shadow-xs' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Split View
          </button>
          <button
            type="button"
            onClick={() => setActiveView('preview')}
            className={`px-3 py-1 rounded-md text-xs font-semibold transition ${
              activeView === 'preview' 
                ? 'bg-white text-blue-700 shadow-xs' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Live Deed Preview
          </button>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        
        {/* Commercial License / Trial Status Badge */}
        {licenseStatus && onOpenActivation && (
          <TrialBadge status={licenseStatus} onOpenActivation={onOpenActivation} />
        )}

        {/* Save Draft Button */}
        <button
          type="button"
          onClick={onSaveDraft}
          title="Save draft to local browser storage"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 text-xs font-semibold hover:bg-slate-50 transition shadow-2xs"
        >
          <Save className="w-3.5 h-3.5 text-slate-500" />
          <span className="hidden sm:inline">Save Draft</span>
        </button>

        {/* Install PWA if supported */}
        {isInstallable && !isInstalled && (
          <button
            type="button"
            onClick={install}
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-300 hover:bg-emerald-100 text-xs font-semibold transition shadow-2xs"
          >
            <FolderDown className="w-3.5 h-3.5" />
            <span>Install</span>
          </button>
        )}

        {/* Download Word */}
        <button
          type="button"
          onClick={onDownloadWord}
          title="Download Microsoft Word formatted .doc file"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold transition shadow-xs"
        >
          <Download className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Word (.doc)</span>
          <span className="sm:hidden">.DOC</span>
        </button>

        {/* Save PDF */}
        <button
          type="button"
          onClick={onDownloadPDF}
          disabled={isExportingPdf}
          title="Download PDF document directly"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold transition shadow-xs disabled:opacity-60"
        >
          {isExportingPdf ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span className="hidden sm:inline">Exporting...</span>
              <span className="sm:hidden">...</span>
            </>
          ) : (
            <>
              <FileDown className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Save PDF</span>
              <span className="sm:hidden">PDF</span>
            </>
          )}
        </button>

        {/* Print A4 */}
        <button
          type="button"
          onClick={onPrint || onDownloadPDF}
          title="Print formatted A4 legal document"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold transition shadow-xs"
        >
          <Printer className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Print</span>
        </button>

        {/* Reset button */}
        <button
          type="button"
          onClick={onReset}
          title="Reset to default template"
          className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition"
        >
          <RotateCcw className="w-4 h-4" />
        </button>

      </div>

    </header>
  );
};
