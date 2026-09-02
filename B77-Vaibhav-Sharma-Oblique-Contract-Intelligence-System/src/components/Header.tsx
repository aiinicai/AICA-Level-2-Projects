import React from 'react';
import { 
  Menu,
  PlayCircle,
  Sparkles,
  FileCheck2,
  FileText,
  Building2,
  Coins
} from 'lucide-react';
import { ContractDocument } from '../types/contract';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  contract: ContractDocument | null;
  onLoadDemo: () => void;
  onNewAnalysis: () => void;
  onExportReport: () => void;
  onToggleMobileMenu?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  contract,
  onLoadDemo,
  onNewAnalysis,
  onExportReport,
  onToggleMobileMenu
}) => {
  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 sm:px-6 lg:px-8 sticky top-0 z-30 shadow-xs">
      {/* Left: Mobile hamburger & Active Analysis tag */}
      <div className="flex items-center gap-3">
        {onToggleMobileMenu && (
          <button
            onClick={onToggleMobileMenu}
            className="lg:hidden p-1.5 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100"
            title="Open menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        <div className="flex items-center gap-2 text-xs">
          <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider hidden sm:inline">
            Active Analysis:
          </span>
          {contract ? (
            <span 
              onClick={() => setActiveTab('viewer')}
              className="font-semibold text-gray-900 italic underline decoration-blue-500 decoration-2 underline-offset-2 cursor-pointer max-w-[220px] sm:max-w-xs md:max-w-md truncate"
              title={contract.identity.title}
            >
              {contract.identity.title}
            </span>
          ) : (
            <span className="text-gray-400 italic text-xs">No active contract loaded</span>
          )}
        </div>
      </div>

      {/* Right: Quick Action Buttons & CA Badge */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Load Demo Button */}
        <button
          id="load-demo-btn"
          onClick={onLoadDemo}
          className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 rounded text-xs font-semibold text-gray-700 hover:bg-gray-50 transition cursor-pointer"
          title="Load turnkey demo agreement"
        >
          <PlayCircle className="w-3.5 h-3.5 text-emerald-600" />
          <span>Demo Contract</span>
        </button>

        {/* New Analysis Button */}
        <button
          id="new-analysis-btn"
          onClick={onNewAnalysis}
          className="inline-flex items-center gap-1.5 px-3 sm:px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold shadow-xs transition cursor-pointer"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>+ New Analysis</span>
        </button>

        {/* Export Report Button */}
        {contract && (
          <button
            id="export-report-btn"
            onClick={onExportReport}
            className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 rounded text-xs font-semibold text-gray-700 hover:bg-gray-50 transition cursor-pointer"
          >
            <FileCheck2 className="w-3.5 h-3.5 text-blue-600" />
            <span>Export Report</span>
          </button>
        )}

        {/* CA Profile Avatar Badge */}
        <div 
          onClick={() => setActiveTab('settings')}
          className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 text-xs font-bold border border-blue-200 cursor-pointer shadow-xs"
          title="Chartered Accountant Reviewer Settings"
        >
          CA
        </div>
      </div>
    </header>
  );
};
