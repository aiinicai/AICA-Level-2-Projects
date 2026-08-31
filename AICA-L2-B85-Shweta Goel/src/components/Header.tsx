import React from 'react';
import { 
  Building2, 
  FileSpreadsheet, 
  Code2, 
  Settings2, 
  Sparkles, 
  Calendar,
  UserCheck,
  ShieldCheck
} from 'lucide-react';
import { CAFirmProfile } from '../types';

interface HeaderProps {
  firmProfile: CAFirmProfile;
  onOpenSettings: () => void;
  onExportExcel: () => void;
  onOpenRawJson: () => void;
  isProcessing: boolean;
  activeModuleTitle: string;
}

export const Header: React.FC<HeaderProps> = ({
  firmProfile,
  onOpenSettings,
  onExportExcel,
  onOpenRawJson,
  isProcessing,
  activeModuleTitle,
}) => {
  return (
    <header className="h-16 bg-slate-900 flex items-center justify-between px-4 sm:px-6 shrink-0 shadow-lg z-30 border-b border-slate-800">
      {/* Left: CA Firm & Suite Brand */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center shrink-0 shadow-md shadow-indigo-950">
          <div className="w-5 h-5 border-2 border-white rotate-45 transform"></div>
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="text-white font-bold text-base sm:text-lg leading-tight tracking-tight truncate">
              {firmProfile.firmName || 'Shweta Goel & Co.'}
            </h1>
            <span className="hidden sm:inline-flex px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 uppercase tracking-wider">
              CA AUDIT SUITE
            </span>
          </div>
          <div className="flex items-center gap-2.5 text-[11px] text-slate-400 truncate">
            <span className="text-indigo-300 font-semibold uppercase tracking-widest text-[10px]">
              {firmProfile.partnerName || 'CA. SHWETA GOEL, FCA'}
            </span>
            <span className="hidden md:inline text-slate-600">•</span>
            <span className="hidden md:inline text-slate-400">
              Client: <strong className="text-slate-200 font-medium">{firmProfile.clientName}</strong>
            </span>
            <span className="hidden lg:inline text-slate-600">•</span>
            <span className="hidden lg:inline text-slate-400 font-mono">
              {firmProfile.financialYear}
            </span>
          </div>
        </div>
      </div>

      {/* Right: Status Pill & Action Buttons */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* Gemini Engine Status Pill */}
        <div className="hidden sm:flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">
          <div className={`w-2 h-2 rounded-full ${isProcessing ? 'bg-amber-400 animate-ping' : 'bg-emerald-500'}`}></div>
          <span className="text-xs text-slate-300 font-medium">
            {isProcessing ? 'Vision Analysing...' : 'Gemini Vision AI Online'}
          </span>
        </div>

        {/* Raw JSON Modal Trigger */}
        <button
          id="btn-raw-json"
          onClick={onOpenRawJson}
          title="View Raw Gemini Extraction JSON"
          className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white rounded-lg border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors"
        >
          <Code2 className="w-3.5 h-3.5 text-indigo-400" />
          <span className="hidden md:inline">JSON</span>
        </button>

        {/* Primary Export to Excel (.xlsx) */}
        <button
          id="btn-export-excel"
          onClick={onExportExcel}
          className="px-3 sm:px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-md shadow-indigo-900/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
        >
          <FileSpreadsheet className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Export to Excel (.xlsx)</span>
          <span className="sm:hidden">Excel</span>
        </button>

        {/* Profile / Firm Settings */}
        <button
          id="btn-firm-settings"
          onClick={onOpenSettings}
          title="Audit Profile & Firm Settings"
          className="w-8 h-8 sm:w-9 sm:h-9 bg-slate-800 hover:bg-slate-700 rounded-full border border-slate-700 flex items-center justify-center text-slate-300 hover:text-white text-xs font-bold transition-colors"
        >
          <Settings2 className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};

