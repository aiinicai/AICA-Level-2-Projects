import React from 'react';
import { 
  FileCheck2, 
  Scale, 
  Download, 
  RotateCcw,
  MessageSquareText,
  Settings,
  Database,
  ShieldCheck,
  Cpu
} from 'lucide-react';
import { AuditReportData } from '../types';

interface HeaderProps {
  currentFramework: string;
  onFrameworkChange: (fw: string) => void;
  report: AuditReportData | null;
  onReset: () => void;
  onOpenChat: () => void;
  onOpenExport: () => void;
  onOpenSettings: () => void;
  onOpenVault: () => void;
  isAuditing: boolean;
  isOfflineMode: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentFramework,
  onFrameworkChange,
  report,
  onReset,
  onOpenChat,
  onOpenExport,
  onOpenSettings,
  onOpenVault,
  isAuditing,
  isOfflineMode,
}) => {
  return (
    <header className="bg-[#141414] text-white border-b-2 border-[#141414] sticky top-0 z-30 shadow-dense-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 sm:h-18">
          {/* Logo & Title */}
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 sm:w-9 sm:h-9 bg-white text-[#141414] flex items-center justify-center font-mono font-black text-sm border border-white shrink-0">
              <FileCheck2 className="w-5 h-5 stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-base sm:text-lg font-bold tracking-tighter uppercase text-white font-sans">
                  FinAudit AI Compliance Engine
                </h1>
                <span className="hidden md:inline-flex items-center gap-1 px-1.5 py-0.2 bg-[#00FF00] text-[#141414] font-mono text-[9px] font-bold uppercase">
                  {isOfflineMode ? (
                    <>
                      <ShieldCheck className="w-2.5 h-2.5" />
                      OFFLINE • 100% PRIVATE
                    </>
                  ) : (
                    'CLOUD AI'
                  )}
                </span>
              </div>
              <p className="text-[10px] text-neutral-400 font-mono tracking-wider uppercase hidden sm:block">
                VERIFICATION LOG: {report?.summary?.reportingPeriod ? `${report.summary.entityName || 'ENTITY'} [${report.summary.reportingPeriod}]` : 'QRB & ICAI STATUTORY AUDIT STANDARD'}
              </p>
            </div>
          </div>

          {/* Right Actions & Metrics */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            {/* Framework Selector */}
            <div className="hidden xl:flex items-center space-x-1.5 bg-[#222222] px-2.5 py-1 border border-neutral-700">
              <Scale className="w-3 h-3 text-neutral-400" />
              <span className="text-[10px] uppercase font-mono text-neutral-400 font-bold">Framework:</span>
              <select
                id="framework-select"
                value={currentFramework}
                onChange={(e) => onFrameworkChange(e.target.value)}
                className="bg-transparent text-[11px] font-mono text-white font-semibold focus:outline-none cursor-pointer pr-1"
              >
                <option value="Ind AS (Schedule III Div II)" className="bg-[#141414] text-white">
                  Ind AS (Schedule III Div II)
                </option>
                <option value="AS (Schedule III Div I)" className="bg-[#141414] text-white">
                  AS (Schedule III Div I)
                </option>
                <option value="Ind AS for NBFCs (Div III)" className="bg-[#141414] text-white">
                  Ind AS for NBFCs (Div III)
                </option>
              </select>
            </div>

            {/* Saved Audits Vault Button */}
            <button
              id="open-vault-btn"
              onClick={onOpenVault}
              className="inline-flex items-center space-x-1 px-2.5 py-1.5 text-xs font-mono font-bold uppercase bg-[#242424] hover:bg-[#333333] text-white border border-neutral-700 transition"
              title="Open Local Audit Vault"
            >
              <Database className="w-3.5 h-3.5 text-green-400" />
              <span className="hidden sm:inline">Vault</span>
            </button>

            {/* Settings Button */}
            <button
              id="open-settings-btn"
              onClick={onOpenSettings}
              className="p-1.5 text-neutral-400 hover:text-white bg-[#242424] hover:bg-[#333333] border border-neutral-700 transition"
              title="Audit Engine & Offline Settings"
            >
              <Settings className="w-4 h-4" />
            </button>

            {report && (
              <>
                <div className="hidden sm:flex items-center gap-4 pl-2 border-l border-white/20">
                  <div className="flex flex-col items-end">
                    <span className="text-[9px] uppercase font-bold tracking-wider text-neutral-400 font-mono">Compliance</span>
                    <span className={`text-lg font-mono font-black leading-none ${
                      report.summary.overallComplianceScore === 'High' ? 'text-[#00FF00]' :
                      report.summary.overallComplianceScore === 'Moderate' ? 'text-amber-400' : 'text-rose-500'
                    }`}>
                      {report.summary.overallComplianceScore === 'High' ? '92.5%' : report.summary.overallComplianceScore === 'Moderate' ? '74.0%' : '52.0%'}
                    </span>
                  </div>
                </div>

                <button
                  id="open-ca-chat-btn"
                  onClick={onOpenChat}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-mono font-bold uppercase bg-[#242424] hover:bg-[#333333] text-white border border-neutral-700 transition"
                  title="Ask CA Assistant follow-up questions"
                >
                  <MessageSquareText className="w-3.5 h-3.5 text-[#00FF00]" />
                  <span className="hidden sm:inline">CA Query</span>
                </button>

                <button
                  id="open-export-btn"
                  onClick={onOpenExport}
                  className="bg-white hover:bg-neutral-200 text-[#141414] px-3 py-1.5 text-xs font-bold uppercase tracking-tight border border-white transition flex items-center space-x-1.5"
                  title="Export formal Audit Working Paper"
                >
                  <Download className="w-3.5 h-3.5 stroke-[2.5]" />
                  <span className="hidden sm:inline">Export</span>
                </button>

                <button
                  id="reset-audit-btn"
                  onClick={onReset}
                  disabled={isAuditing}
                  className="p-1.5 text-neutral-400 hover:text-white hover:bg-neutral-800 border border-transparent hover:border-neutral-700 transition"
                  title="Start New Audit"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
