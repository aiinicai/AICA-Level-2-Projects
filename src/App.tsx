/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { EngagementData } from './types';
import { SAMPLE_ENGAGEMENT, createBlankEngagement } from './data/sampleEngagement';
import { computeMateriality, computeAllStageProgress } from './utils/calculations';
import { TopBar } from './components/TopBar';
import { Sidebar } from './components/Sidebar';
import { KnowledgeBaseModal } from './components/KnowledgeBaseModal';
import { PrintReportModal } from './components/PrintReportModal';
import { TBImportModal } from './components/TBImportModal';
import { ExportWorkpaperModal } from './components/ExportWorkpaperModal';
import { TrialBalanceView } from './components/TrialBalanceView';
import { ZENITH_SAMPLE_TRIAL_BALANCE } from './data/sampleTrialBalance';
import { TrialBalanceData } from './types';

// Stages
import { StageOverview } from './components/stages/StageOverview';
import { Stage1ClientAcceptance } from './components/stages/Stage1ClientAcceptance';
import { Stage2EntityUnderstanding } from './components/stages/Stage2EntityUnderstanding';
import { Stage3ControlEnvironment } from './components/stages/Stage3ControlEnvironment';
import { Stage4InformationSystems } from './components/stages/Stage4InformationSystems';
import { Stage5ProcessIdentification } from './components/stages/Stage5ProcessIdentification';
import { Stage6Walkthroughs } from './components/stages/Stage6Walkthroughs';
import { Stage7RiskAssessmentFS } from './components/stages/Stage7RiskAssessmentFS';
import { Stage8FraudRisk } from './components/stages/Stage8FraudRisk';
import { Stage9ControlRiskRegister } from './components/stages/Stage9ControlRiskRegister';
import { Stage10Materiality } from './components/stages/Stage10Materiality';
import { Stage11AuditStrategy } from './components/stages/Stage11AuditStrategy';
import { Stage12PlanningMemo } from './components/stages/Stage12PlanningMemo';
import { Stage13SignOffReview } from './components/stages/Stage13SignOffReview';

import { ChevronLeft, ChevronRight, BookOpen, Printer } from 'lucide-react';

const LOCAL_STORAGE_KEY = 'audit_workbench_engagement_v1';
const THEME_STORAGE_KEY = 'audit_workbench_theme';

export default function App() {
  const [engagement, setEngagement] = useState<EngagementData>(() => {
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn('Could not read from localStorage', e);
    }
    return SAMPLE_ENGAGEMENT;
  });

  const [activeStage, setActiveStage] = useState<number>(0); // 0 = Overview, 1-13 = Stages
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    return localStorage.getItem(THEME_STORAGE_KEY) === 'dark';
  });

  const [isKnowledgeBaseOpen, setIsKnowledgeBaseOpen] = useState(false);
  const [isPrintReportOpen, setIsPrintReportOpen] = useState(false);
  const [isTBImportModalOpen, setIsTBImportModalOpen] = useState(false);
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);

  // Sync to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(engagement));
    } catch (e) {
      console.error('Error saving to localStorage', e);
    }
  }, [engagement]);

  // Handle Dark Mode
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem(THEME_STORAGE_KEY, 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem(THEME_STORAGE_KEY, 'light');
    }
  }, [darkMode]);

  // Computations
  const materiality = computeMateriality(engagement.materiality);
  const progressResult = computeAllStageProgress(engagement);
  const stagesProgress = progressResult.stages;
  const overallPercent = progressResult.overallPercent;

  const isSample = engagement.clientName === 'Zenith Fabrics Private Limited';

  const handleSelectSample = () => {
    setEngagement(SAMPLE_ENGAGEMENT);
  };

  const handleNewBlank = () => {
    setEngagement(createBlankEngagement());
    setActiveStage(1);
  };

  const handleResetSample = () => {
    if (window.confirm('Reset current engagement back to the original Zenith Fabrics sample data?')) {
      setEngagement(SAMPLE_ENGAGEMENT);
    }
  };

  // Trial Balance Handlers
  const handleApplyTB = (tbData: TrialBalanceData, syncWithMateriality: boolean) => {
    setEngagement((prev) => {
      const updated = { ...prev, trialBalance: tbData };

      if (syncWithMateriality) {
        // Auto-update benchmark amount based on current chosen benchmark basis
        const currentBasis = prev.materiality.benchmarkBasis.toLowerCase();
        let newBenchmarkAmount = prev.materiality.benchmarkAmount;

        if (currentBasis.includes('turnover') || currentBasis.includes('revenue')) {
          newBenchmarkAmount = tbData.summary.totalRevenue;
        } else if (currentBasis.includes('pbt') || currentBasis.includes('profit')) {
          newBenchmarkAmount = tbData.summary.profitBeforeTax;
        } else if (currentBasis.includes('asset')) {
          newBenchmarkAmount = tbData.summary.totalAssets;
        } else if (currentBasis.includes('equity') || currentBasis.includes('net worth')) {
          newBenchmarkAmount = tbData.summary.totalEquity;
        }

        updated.materiality = {
          ...prev.materiality,
          benchmarkAmount: newBenchmarkAmount > 0 ? newBenchmarkAmount : prev.materiality.benchmarkAmount,
        };
      }

      return updated;
    });
  };

  const handleSyncMaterialityBenchmark = (benchmarkBasis: string, amount: number) => {
    setEngagement((prev) => ({
      ...prev,
      materiality: {
        ...prev.materiality,
        benchmarkBasis,
        benchmarkAmount: amount,
      },
    }));
  };

  const handleClearTB = () => {
    setEngagement((prev) => {
      const updated = { ...prev };
      delete updated.trialBalance;
      return updated;
    });
  };

  const handleLoadSampleTB = () => {
    setEngagement((prev) => ({
      ...prev,
      trialBalance: ZENITH_SAMPLE_TRIAL_BALANCE,
    }));
  };

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(engagement, null, 2));
    const downloadAnchor = document.createElement('a');
    const safeClient = engagement.clientName.replace(/[^a-zA-Z0-9]/g, '_');
    const safeFY = engagement.financialYear.replace(/[^a-zA-Z0-9]/g, '_');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `Audit_Planning_${safeClient}_${safeFY}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleImportJson = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const parsed = JSON.parse(e.target?.result as string);
        if (parsed && parsed.clientName && parsed.materiality) {
          setEngagement(parsed);
          alert(`Successfully imported engagement: ${parsed.clientName}`);
        } else {
          alert('Invalid engagement file format.');
        }
      } catch (err) {
        alert('Failed to parse JSON file.');
      }
    };
    reader.readAsText(file);
  };

  const handlePrevStage = () => {
    if (activeStage > 0) setActiveStage(activeStage - 1);
  };

  const handleNextStage = () => {
    if (activeStage < 13) setActiveStage(activeStage + 1);
  };

  return (
    <div className="min-h-screen bg-[#f7f6f2] dark:bg-[#0f1318] text-[#1c222b] dark:text-[#f3f4f6] flex flex-col font-sans transition-colors">
      {/* Top Bar */}
      <TopBar
        engagement={engagement}
        materiality={materiality}
        overallPercent={overallPercent}
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode(!darkMode)}
        onOpenKnowledgeBase={() => setIsKnowledgeBaseOpen(true)}
        onOpenPrintReport={() => setIsPrintReportOpen(true)}
        onOpenTBImport={() => setIsTBImportModalOpen(true)}
        onOpenExportModal={() => setIsExportModalOpen(true)}
        onNavigateToTB={() => setActiveStage(-1)}
        onSelectSample={handleSelectSample}
        onNewBlank={handleNewBlank}
        onResetSample={handleResetSample}
        onExportJson={handleExportJson}
        onImportJson={handleImportJson}
        isSample={isSample}
      />

      {/* Main Layout: Sidebar + Stage Content */}
      <div className="flex-1 flex flex-col md:flex-row max-w-7xl w-full mx-auto">
        <Sidebar
          activeStage={activeStage}
          onSelectStage={(stage) => setActiveStage(stage)}
          stagesProgress={stagesProgress}
          tbItemCount={engagement.trialBalance?.items.length}
        />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 min-w-0 overflow-y-auto">
          {/* Stage Context Bar */}
          {activeStage !== 0 && (
            <div className="mb-4 flex items-center justify-between py-2 border-b border-[#dedbd2] dark:border-[#272f38] text-xs text-stone-500">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveStage(0)}
                  className="hover:text-amber-800 dark:hover:text-amber-400 transition-colors"
                >
                  Overview
                </button>
                <span>/</span>
                <span className="font-semibold text-stone-800 dark:text-stone-200">
                  {activeStage === -1 ? 'Trial Balance & Schedule III Mapping' : `Stage ${activeStage} of 13`}
                </span>
              </div>

              {activeStage > 0 && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={handlePrevStage}
                    disabled={activeStage === 1}
                    className="px-2.5 py-1 rounded border border-stone-300 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 disabled:opacity-40 flex items-center gap-1 transition-colors"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                    <span>Previous</span>
                  </button>
                  <button
                    onClick={handleNextStage}
                    disabled={activeStage === 13}
                    className="px-2.5 py-1 rounded border border-stone-300 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 disabled:opacity-40 flex items-center gap-1 transition-colors"
                  >
                    <span>Next</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Dynamic Stage Render */}
          {activeStage === -1 && (
            <TrialBalanceView
              trialBalance={engagement.trialBalance}
              onOpenImportModal={() => setIsTBImportModalOpen(true)}
              onClearTB={handleClearTB}
              onLoadSample={handleLoadSampleTB}
              onSyncMaterialityBenchmark={handleSyncMaterialityBenchmark}
              onNavigateToMateriality={() => setActiveStage(10)}
            />
          )}

          {activeStage === 0 && (
            <StageOverview
              engagement={engagement}
              stagesProgress={stagesProgress}
              materiality={materiality}
              overallPercent={overallPercent}
              onSelectStage={(s) => setActiveStage(s)}
            />
          )}

          {activeStage === 1 && (
            <Stage1ClientAcceptance
              engagement={engagement}
              onChange={setEngagement}
            />
          )}

          {activeStage === 2 && (
            <Stage2EntityUnderstanding
              engagement={engagement}
              onChange={setEngagement}
              onOpenKnowledgeBase={() => setIsKnowledgeBaseOpen(true)}
            />
          )}

          {activeStage === 3 && (
            <Stage3ControlEnvironment
              engagement={engagement}
              onChange={setEngagement}
            />
          )}

          {activeStage === 4 && (
            <Stage4InformationSystems
              engagement={engagement}
              onChange={setEngagement}
            />
          )}

          {activeStage === 5 && (
            <Stage5ProcessIdentification
              engagement={engagement}
              onChange={setEngagement}
            />
          )}

          {activeStage === 6 && (
            <Stage6Walkthroughs
              engagement={engagement}
              onChange={setEngagement}
            />
          )}

          {activeStage === 7 && (
            <Stage7RiskAssessmentFS
              engagement={engagement}
              onChange={setEngagement}
            />
          )}

          {activeStage === 8 && (
            <Stage8FraudRisk
              engagement={engagement}
              onChange={setEngagement}
            />
          )}

          {activeStage === 9 && (
            <Stage9ControlRiskRegister
              engagement={engagement}
              onChange={setEngagement}
            />
          )}

          {activeStage === 10 && (
            <Stage10Materiality
              engagement={engagement}
              onChange={setEngagement}
            />
          )}

          {activeStage === 11 && (
            <Stage11AuditStrategy
              engagement={engagement}
              onChange={setEngagement}
            />
          )}

          {activeStage === 12 && (
            <Stage12PlanningMemo
              engagement={engagement}
              onChange={setEngagement}
              onOpenPrintReport={() => setIsPrintReportOpen(true)}
            />
          )}

          {activeStage === 13 && (
            <Stage13SignOffReview
              engagement={engagement}
              onChange={setEngagement}
            />
          )}

          {/* Bottom Stage Navigation */}
          {activeStage > 0 && (
            <div className="mt-8 pt-4 border-t border-[#dedbd2] dark:border-[#272f38] flex items-center justify-between text-xs">
              <button
                onClick={handlePrevStage}
                className="px-3.5 py-2 rounded-lg border border-stone-300 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-700 dark:text-stone-300 flex items-center gap-1.5 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                <span>Previous Stage</span>
              </button>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsKnowledgeBaseOpen(true)}
                  className="px-3 py-2 rounded-lg text-stone-500 hover:text-amber-800 dark:hover:text-amber-400 flex items-center gap-1.5 transition-colors"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>Consult ICAI SAs</span>
                </button>

                {activeStage < 13 ? (
                  <button
                    onClick={handleNextStage}
                    className="px-4 py-2 rounded-lg bg-amber-800 hover:bg-amber-900 dark:bg-amber-700 text-white font-medium flex items-center gap-1.5 transition-colors shadow-xs"
                  >
                    <span>Proceed to Stage {activeStage + 1}</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                ) : (
                  <button
                    onClick={() => setIsPrintReportOpen(true)}
                    className="px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-medium flex items-center gap-1.5 transition-colors shadow-xs"
                  >
                    <Printer className="w-4 h-4" />
                    <span>Print Completed Planning Memo</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Modals */}
      <KnowledgeBaseModal
        isOpen={isKnowledgeBaseOpen}
        onClose={() => setIsKnowledgeBaseOpen(false)}
      />

      <PrintReportModal
        isOpen={isPrintReportOpen}
        onClose={() => setIsPrintReportOpen(false)}
        engagement={engagement}
        materiality={materiality}
      />

      <TBImportModal
        isOpen={isTBImportModalOpen}
        onClose={() => setIsTBImportModalOpen(false)}
        onApplyTB={handleApplyTB}
      />

      <ExportWorkpaperModal
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
        engagement={engagement}
        materiality={materiality}
      />
    </div>
  );
}
