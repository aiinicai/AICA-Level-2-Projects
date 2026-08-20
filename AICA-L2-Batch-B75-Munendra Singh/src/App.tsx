import React, { useState, useEffect } from 'react';
import { 
  FileCheck2, 
  AlertCircle, 
  Calculator, 
  FileCode, 
  BookOpenCheck,
  ShieldCheck,
  Cpu
} from 'lucide-react';
import { Header } from './components/Header';
import { DocumentIntake } from './components/DocumentIntake';
import { ExecutiveSummaryCard } from './components/ExecutiveSummaryCard';
import { Part1DisclosuresTable } from './components/Part1DisclosuresTable';
import { Part2InconsistenciesTable } from './components/Part2InconsistenciesTable';
import { Part3RecommendationsList } from './components/Part3RecommendationsList';
import { NoteReconcilerModal } from './components/NoteReconcilerModal';
import { AuditChatDrawer } from './components/AuditChatDrawer';
import { ExportModal } from './components/ExportModal';
import { SettingsModal } from './components/SettingsModal';
import { SavedAuditsDrawer } from './components/SavedAuditsDrawer';
import { AuditReportData, InconsistencyItem } from './types';
import { runOfflineAudit } from './engine/offlineAuditEngine';
import { getSavedSettings, saveAuditToVault, AppSettings, getSavedAudits } from './utils/localVault';

export default function App() {
  const [currentFramework, setCurrentFramework] = useState('Ind AS (Schedule III Div II)');
  const [report, setReport] = useState<AuditReportData | null>(null);
  const [isAuditing, setIsAuditing] = useState(false);
  const [auditStep, setAuditStep] = useState<string>('Initializing');
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<AppSettings>(getSavedSettings());

  // Modals & Drawers
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isReconcilerOpen, setIsReconcilerOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isVaultOpen, setIsVaultOpen] = useState(false);
  const [selectedInconsistency, setSelectedInconsistency] = useState<InconsistencyItem | null>(null);
  const [showRawMarkdown, setShowRawMarkdown] = useState(false);

  const handleStartAudit = async (payload: {
    text: string;
    fileData?: string;
    mimeType?: string;
    fileName?: string;
    options: {
      strictTolerance: boolean;
      checkCARO: boolean;
      standardsFocus: string[];
    };
  }) => {
    setIsAuditing(true);
    setError(null);
    setAuditStep('Phase 1/4: Parsing primary statements, schedules & commentary text...');

    const stepTimer1 = setTimeout(() => {
      setAuditStep('Phase 2/4: Cross-referencing against Ind AS mandatory disclosure matrix...');
    }, 600);

    const stepTimer2 = setTimeout(() => {
      setAuditStep('Phase 3/4: Mathematical casting, footing & balance sheet reconciliation check...');
    }, 1200);

    const stepTimer3 = setTimeout(() => {
      setAuditStep('Phase 4/4: Calculating compliance score & synthesizing CA audit action plan...');
    }, 1800);

    try {
      if (settings.useOfflineEngine) {
        // 100% Offline Client-Side Execution (Deterministic & Instant)
        await new Promise((resolve) => setTimeout(resolve, 2000));
        
        const offlineReport = await runOfflineAudit(
          payload.text,
          payload.fileName,
          {
            strictTolerance: payload.options.strictTolerance,
            checkCARO: payload.options.checkCARO,
            standardsFocus: payload.options.standardsFocus,
            framework: currentFramework,
          }
        );

        clearTimeout(stepTimer1);
        clearTimeout(stepTimer2);
        clearTimeout(stepTimer3);

        if (settings.autoSaveReports) {
          saveAuditToVault(offlineReport);
        }

        setReport(offlineReport);
      } else {
        // Optional Cloud Gemini API Analysis
        const response = await fetch('/api/audit/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: payload.text,
            fileData: payload.fileData,
            mimeType: payload.mimeType,
            fileName: payload.fileName,
            options: payload.options,
          }),
        });

        clearTimeout(stepTimer1);
        clearTimeout(stepTimer2);
        clearTimeout(stepTimer3);

        const data = await response.json();

        if (!response.ok || !data.success) {
          throw new Error(data.error || 'Failed to complete cloud statutory disclosure audit.');
        }

        if (settings.autoSaveReports) {
          saveAuditToVault(data.data);
        }

        setReport(data.data);
      }
    } catch (err: any) {
      console.warn('Primary audit execution encountered issue, trying offline fallback:', err);
      try {
        // Fallback to offline engine if remote server fails
        const offlineReport = await runOfflineAudit(
          payload.text,
          payload.fileName,
          {
            strictTolerance: payload.options.strictTolerance,
            checkCARO: payload.options.checkCARO,
            standardsFocus: payload.options.standardsFocus,
            framework: currentFramework,
          }
        );
        if (settings.autoSaveReports) {
          saveAuditToVault(offlineReport);
        }
        setReport(offlineReport);
      } catch (fallbackErr: any) {
        setError(fallbackErr.message || err.message || 'An unexpected error occurred during audit analysis.');
      }
    } finally {
      setIsAuditing(false);
    }
  };

  const handleReset = () => {
    setReport(null);
    setError(null);
    setSelectedInconsistency(null);
  };

  const handleOpenReconciler = (item?: InconsistencyItem) => {
    if (item) {
      setSelectedInconsistency(item);
    } else if (report && report.part2Inconsistencies.length > 0) {
      setSelectedInconsistency(report.part2Inconsistencies[0]);
    } else {
      setSelectedInconsistency(null);
    }
    setIsReconcilerOpen(true);
  };

  return (
    <div className="min-h-screen bg-[#E4E3E0] text-[#141414] font-sans flex flex-col selection:bg-[#141414] selection:text-[#00FF00]">
      {/* Top Header */}
      <Header
        currentFramework={currentFramework}
        onFrameworkChange={setCurrentFramework}
        report={report}
        onReset={handleReset}
        onOpenChat={() => setIsChatOpen(true)}
        onOpenExport={() => setIsExportOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenVault={() => setIsVaultOpen(true)}
        isAuditing={isAuditing}
        isOfflineMode={settings.useOfflineEngine}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5 sm:py-6">
        {/* Offline Engine Active Banner */}
        {settings.useOfflineEngine && (
          <div className="mb-4 py-2 px-3.5 bg-[#F9F9F7] border border-[#141414] flex items-center justify-between shadow-dense-sm font-mono text-xs">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-[#00FF00] animate-pulse"></span>
              <span className="font-bold uppercase text-[11px] text-[#141414]">
                Offline CA Engine Active
              </span>
              <span className="text-neutral-500 hidden sm:inline text-[10px]">
                — 100% on-device processing. Client financial data remains strictly local.
              </span>
            </div>
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="text-[10px] uppercase font-bold text-neutral-700 hover:text-black underline"
            >
              Engine Settings
            </button>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 bg-red-100 border-2 border-red-600 text-red-900 flex items-start space-x-3 shadow-dense-sm font-mono text-xs">
            <AlertCircle className="w-5 h-5 text-red-700 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-bold uppercase tracking-tight">Audit Verification Error</h4>
              <p className="mt-0.5">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-700 hover:text-red-900 font-bold uppercase underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Document Intake Workspace (Shown when no report or resetting) */}
        {!report && (
          <DocumentIntake
            onAnalyze={handleStartAudit}
            isAuditing={isAuditing}
            activeFramework={currentFramework}
          />
        )}

        {/* Live Auditing Multi-Phase Progress State */}
        {isAuditing && (
          <div className="bg-white border-2 border-[#141414] shadow-dense p-8 sm:p-10 text-center max-w-2xl mx-auto my-8 animate-pulse">
            <div className="w-14 h-14 bg-[#141414] text-[#00FF00] flex items-center justify-center mx-auto mb-4 border border-[#141414]">
              <FileCheck2 className="w-7 h-7 animate-spin" />
            </div>

            <h3 className="text-base sm:text-lg font-bold uppercase tracking-tight text-[#141414] mb-1 font-sans">
              Executing Multi-Phase Statutory Financial Statement Audit
            </h3>
            <p className="text-[11px] text-[#141414]/70 font-mono mb-6 max-w-lg mx-auto uppercase">
              {auditStep}
            </p>

            {/* Step Indicators */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-left text-xs">
              <div className="p-2.5 bg-[#F9F9F7] border border-[#141414]">
                <span className="font-bold text-[#141414] font-mono text-[10px] uppercase block">1. Extraction</span>
                <span className="text-[10px] font-serif italic text-[#141414]/70">Tables & notes</span>
              </div>
              <div className="p-2.5 bg-[#F9F9F7] border border-[#141414]">
                <span className="font-bold text-[#141414] font-mono text-[10px] uppercase block">2. Ind AS Check</span>
                <span className="text-[10px] font-serif italic text-[#141414]/70">Mandatory matrices</span>
              </div>
              <div className="p-2.5 bg-[#F9F9F7] border border-[#141414]">
                <span className="font-bold text-[#141414] font-mono text-[10px] uppercase block">3. Castings</span>
                <span className="text-[10px] font-serif italic text-[#141414]/70">Cross-referencing</span>
              </div>
              <div className="p-2.5 bg-[#F9F9F7] border border-[#141414]">
                <span className="font-bold text-[#141414] font-mono text-[10px] uppercase block">4. Action Plan</span>
                <span className="text-[10px] font-serif italic text-[#141414]/70">Risk & sign-off</span>
              </div>
            </div>
          </div>
        )}

        {/* Audit Results Dashboard */}
        {report && !isAuditing && (
          <div className="space-y-2 animate-fadeIn">
            {/* Action Bar Above Report */}
            <div className="flex flex-wrap items-center justify-between pb-3 gap-2">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 bg-[#141414] text-white text-[10px] font-mono font-bold uppercase">
                  AUDIT ID: {report.id}
                </span>
                <span className="text-[10px] font-mono text-[#141414]/70 uppercase">
                  GENERATED {new Date(report.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  id="btn-reconciler-tool"
                  onClick={() => handleOpenReconciler()}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-mono font-bold uppercase bg-white hover:bg-neutral-100 text-[#141414] border border-[#141414] shadow-dense-sm transition"
                >
                  <Calculator className="w-3.5 h-3.5 text-[#141414]" />
                  <span>Interactive Note Reconciler</span>
                </button>

                <button
                  id="btn-toggle-raw-md"
                  onClick={() => setShowRawMarkdown(!showRawMarkdown)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-mono font-bold uppercase bg-white hover:bg-neutral-100 text-[#141414] border border-[#141414] shadow-dense-sm transition"
                >
                  <FileCode className="w-3.5 h-3.5 text-[#141414]" />
                  <span>{showRawMarkdown ? 'Show Structured Tables' : 'View Full Markdown'}</span>
                </button>
              </div>
            </div>

            {/* View Mode 1: Full Raw Markdown Report */}
            {showRawMarkdown && report.rawMarkdownReport ? (
              <div className="bg-white border-2 border-[#141414] shadow-dense p-5 font-mono text-xs text-[#141414] whitespace-pre-wrap leading-relaxed overflow-x-auto">
                <div className="font-bold text-xs uppercase text-[#141414] pb-2 mb-3 border-b border-[#141414] flex items-center justify-between">
                  <span>Standard Formal Audit Report (Markdown Output)</span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(report.rawMarkdownReport || '');
                    }}
                    className="text-xs text-[#141414] font-bold uppercase underline"
                  >
                    Copy Markdown Text
                  </button>
                </div>
                {report.rawMarkdownReport}
              </div>
            ) : (
              /* View Mode 2: Interactive 4-Section Structured Report */
              <div className="space-y-4">
                {/* 1. Executive Compliance Summary */}
                <ExecutiveSummaryCard
                  summary={report.summary}
                  documentTitle={report.documentTitle}
                  financialHighlights={report.financialHighlights}
                />

                {/* 2. Part 1: Ind AS Mandatory Disclosure Check */}
                <Part1DisclosuresTable disclosures={report.part1Disclosures} />

                {/* 3. Part 2: Cross-Referencing & Numerical Inconsistency Findings */}
                <Part2InconsistenciesTable
                  inconsistencies={report.part2Inconsistencies}
                  onOpenReconciler={handleOpenReconciler}
                />

                {/* 4. Part 3: Actionable Audit Recommendations */}
                <Part3RecommendationsList recommendations={report.part3Recommendations} />
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-[#141414] border-t border-[#141414] text-neutral-400 text-xs py-4 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 font-mono">
          <div className="flex items-center space-x-2">
            <BookOpenCheck className="w-4 h-4 text-[#00FF00]" />
            <span className="text-white text-[11px] uppercase">
              IND AS / AS DISCLOSURE VERIFICATION & INTERNAL CONSISTENCY AUDIT ENGINE
            </span>
          </div>
          <div className="text-neutral-400 text-[10px] uppercase text-center sm:text-right">
            DESIGNED FOR STATUTORY AUDITORS, QRB & CHARTERED ACCOUNTANTS
          </div>
        </div>
      </footer>

      {/* Modals & Drawers */}
      <NoteReconcilerModal
        isOpen={isReconcilerOpen}
        onClose={() => setIsReconcilerOpen(false)}
        initialItem={selectedInconsistency}
      />

      <AuditChatDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        report={report}
        isOfflineMode={settings.useOfflineEngine}
      />

      <ExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        report={report}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        settings={settings}
        onSaveSettings={(newSettings) => setSettings(newSettings)}
        onRefreshAudits={() => {}}
      />

      <SavedAuditsDrawer
        isOpen={isVaultOpen}
        onClose={() => setIsVaultOpen(false)}
        onSelectAudit={(savedReport) => {
          setReport(savedReport);
        }}
      />
    </div>
  );
}
