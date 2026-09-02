import React, { useState, useMemo, useEffect } from 'react';
import {
  Navbar,
  Sidebar,
  ExecutiveSummaryView,
  FinancialStatementsView,
  KpiDashboardView,
  ForecastingView,
  WhatIfScenarioView,
  BreakEvenView,
  BudgetVsActualView,
  DataQualityView,
  PrivacyShieldView,
  DataImportView,
  CfoPackGeneratorView,
  IntegrationsView,
  AuditTrailView,
  SettingsView,
  MetricExplanationModal,
  MonthlyWorkflowModal,
  ClientManagerModal,
  AskCfoModal,
  LandingView,
  QuickExportModal,
} from './components';
import {
  NavigationTab,
  ClientProfile,
  FinancialModel,
  KpiMetric,
  CfoCommentary,
  MonthlyFinancialRecord,
} from './types';
import {
  getMedicalPracticeDemoData,
  getRestaurantGroupDemoData,
  getManufacturingDemoData,
  getAvailableDemoClients,
} from './services/demoData';
import { FinancialEngine } from './services/financialEngine';
import { PrivacyShield } from './services/privacyShield';
import { ExportService } from './services/exportService';
import { ForecastingEngine } from './services/forecastingEngine';

export default function App() {
  const [showLanding, setShowLanding] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<NavigationTab>('executive_summary');
  const [firmName, setFirmName] = useState<string>('Jasleen Daswal & Associates');

  // Client Management State
  const demoClients = useMemo(() => getAvailableDemoClients(), []);
  const [currentClient, setCurrentClient] = useState<ClientProfile>(demoClients[0]);
  const [clientRecords, setClientRecords] = useState<MonthlyFinancialRecord[]>(() => {
    return getMedicalPracticeDemoData(demoClients[0]);
  });

  // Modals
  const [selectedMetricToExplain, setSelectedMetricToExplain] = useState<KpiMetric | null>(null);
  const [showWorkflowModal, setShowWorkflowModal] = useState<boolean>(false);
  const [showClientModal, setShowClientModal] = useState<boolean>(false);
  const [showAskCfoModal, setShowAskCfoModal] = useState<boolean>(false);
  const [showQuickExportModal, setShowQuickExportModal] = useState<boolean>(false);

  // Switch demo data when client changes
  const handleSelectClient = (client: ClientProfile) => {
    setCurrentClient(client);
    if (client.industry === 'medical') {
      setClientRecords(getMedicalPracticeDemoData(client));
    } else if (client.industry === 'restaurant') {
      setClientRecords(getRestaurantGroupDemoData(client));
    } else if (client.industry === 'manufacturing') {
      setClientRecords(getManufacturingDemoData(client));
    } else {
      // Custom client fallback with synthesized medical base
      setClientRecords(getMedicalPracticeDemoData(client));
    }
  };

  // Build Deterministic Financial Model
  const model: FinancialModel = useMemo(() => {
    return FinancialEngine.buildFinancialModel(currentClient, clientRecords);
  }, [currentClient, clientRecords]);

  // Generate Calculated KPIs
  const kpis: KpiMetric[] = useMemo(() => {
    return FinancialEngine.generateKpiMetrics(model);
  }, [model]);

  // Executive Commentary (Initial deterministic baseline)
  const [commentary, setCommentary] = useState<CfoCommentary>(() => {
    return FinancialEngine.generateDeterministicCommentary(model, kpis);
  });

  // Update commentary when model or client changes
  useEffect(() => {
    setCommentary(FinancialEngine.generateDeterministicCommentary(model, kpis));
  }, [model, kpis]);

  // Data Import Success Handler
  const handleImportSuccess = (newRecords: MonthlyFinancialRecord[]) => {
    setClientRecords(newRecords);
    setActiveTab('executive_summary');
  };

  // AI Narrative Regeneration
  const handleRegenerateAi = async () => {
    try {
      // Privacy tokenization before sending to server
      const sanitizedModel = PrivacyShield.sanitizeFinancialModel(model);
      const res = await fetch('/api/ai/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: sanitizedModel,
          prompt: 'Generate an executive CFO commentary with key drivers and recommendations.',
        }),
      });

      if (!res.ok) throw new Error('AI analysis failed');
      const data = await res.json();

      // De-tokenize back to client presentation
      const deAnonymizedText = PrivacyShield.deAnonymizeText(data.analysis || '');

      setCommentary(prev => ({
        ...prev,
        headlineSummary: deAnonymizedText.slice(0, 180) + '...',
        whatHappened: `Operating revenue reached ${currentClient.currencySymbol}${(model.historicalMonthly[model.historicalMonthly.length - 1].revenue / 1000).toFixed(0)}k with an EBITDA margin of ${model.summary.averageEbitdaMargin.toFixed(1)}%.`,
        whyItHappened: deAnonymizedText,
      }));
    } catch (err) {
      console.warn('Using local deterministic commentary engine fallback:', err);
      setCommentary(FinancialEngine.generateDeterministicCommentary(model, kpis));
    }
  };

  // Quick Export handler
  const handleExportFullPack = () => {
    const breakEven = FinancialEngine.calculateBreakEvenAnalysis(model);
    const scenario = ForecastingEngine.generateRolling12MonthForecast(model);
    ExportService.exportFullCfoWorkbook(model, kpis, commentary, scenario, breakEven, firmName);
  };

  if (showLanding) {
    return (
      <LandingView
        onEnterWorkspace={() => setShowLanding(false)}
        firmName={firmName}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col font-sans text-[#0F172A] selection:bg-sky-500 selection:text-white">
      {/* Top Privacy Shield Strip (Geometric Balance Theme) */}
      <div className="privacy-banner shrink-0">
        <span>
          SHIELD ACTIVE: <b>Redaction Layer v2.1</b> — All PII tokenized. Original identity restored only for final report export.
        </span>
      </div>

      {/* Top Navigation Bar */}
      <Navbar
        client={currentClient}
        currentClient={currentClient}
        allClients={demoClients}
        firmName={firmName}
        onSelectClient={(id) => {
          const found = demoClients.find(c => c.id === id);
          if (found) handleSelectClient(found);
        }}
        onOpenWorkflow={() => setShowWorkflowModal(true)}
        onOpenClientSelector={() => setShowClientModal(true)}
        onOpenPrivacyShield={() => setActiveTab('privacy_shield')}
        onOpenAskCfo={() => setShowAskCfoModal(true)}
        onExportReport={() => setShowQuickExportModal(true)}
        onShowLanding={() => setShowLanding(true)}
      />

      {/* Main Workspace: Sidebar Navigation + Active Viewport */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Navigation Sidebar */}
        <Sidebar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          firmName={firmName}
        />

        {/* Dynamic Center Stage Viewport */}
        <main className="flex-1 flex flex-col overflow-y-auto bg-[#F8FAFC]">
          <div className="flex-1 p-4 sm:p-6 lg:p-8">
            <div className="max-w-7xl mx-auto space-y-6">
              {activeTab === 'executive_summary' && (
                <ExecutiveSummaryView
                  model={model}
                  kpis={kpis}
                  commentary={commentary}
                  onOpenMetricExplain={metric => setSelectedMetricToExplain(metric)}
                  onRegenerateAi={handleRegenerateAi}
                  onOpenAskCfo={() => setShowAskCfoModal(true)}
                  onNavigateToTab={tab => setActiveTab(tab)}
                  firmName={firmName}
                />
              )}

              {activeTab === 'financial_statements' && (
                <FinancialStatementsView
                  model={model}
                  firmName={firmName}
                />
              )}

              {activeTab === 'kpi_benchmarks' && (
                <KpiDashboardView
                  client={currentClient}
                  kpis={kpis}
                  onOpenMetricExplain={metric => setSelectedMetricToExplain(metric)}
                  firmName={firmName}
                />
              )}

              {activeTab === 'forecasting' && (
                <ForecastingView
                  model={model}
                  firmName={firmName}
                />
              )}

              {activeTab === 'scenarios' && (
                <WhatIfScenarioView
                  model={model}
                  firmName={firmName}
                />
              )}

              {activeTab === 'breakeven' && (
                <BreakEvenView
                  model={model}
                  firmName={firmName}
                />
              )}

              {activeTab === 'budget_vs_actual' && (
                <BudgetVsActualView
                  model={model}
                  firmName={firmName}
                />
              )}

              {activeTab === 'data_quality' && (
                <DataQualityView
                  model={model}
                  firmName={firmName}
                />
              )}

              {activeTab === 'privacy_shield' && (
                <PrivacyShieldView
                  client={currentClient}
                  firmName={firmName}
                />
              )}

              {activeTab === 'data_import' && (
                <DataImportView
                  client={currentClient}
                  onImportSuccess={handleImportSuccess}
                  firmName={firmName}
                />
              )}

              {activeTab === 'cfo_pack' && (
                <CfoPackGeneratorView
                  model={model}
                  kpis={kpis}
                  commentary={commentary}
                  firmName={firmName}
                  onOpenAskCfo={() => setShowAskCfoModal(true)}
                />
              )}

              {activeTab === 'integrations' && (
                <IntegrationsView
                  client={currentClient}
                  firmName={firmName}
                />
              )}

              {activeTab === 'audit_trail' && (
                <AuditTrailView
                  client={currentClient}
                  firmName={firmName}
                />
              )}

              {activeTab === 'settings' && (
                <SettingsView
                  client={currentClient}
                  firmName={firmName}
                  onUpdateFirmName={setFirmName}
                />
              )}
            </div>
          </div>

          {/* Geometric Balance Workspace Footer */}
          <footer className="h-11 border-t border-slate-200 bg-white flex items-center justify-between px-6 sm:px-8 text-[11px] text-slate-500 font-medium shrink-0">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5 font-semibold text-slate-700">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                System Status: All Engines Nominal
              </span>
              <span className="hidden sm:inline text-slate-400">|</span>
              <span className="hidden sm:inline text-slate-400">Last Sync: 14m ago (QBO)</span>
            </div>
            <div className="uppercase tracking-wider font-bold text-slate-500 text-[10px]">
              Curated by {firmName}
            </div>
          </footer>
        </main>
      </div>

      {/* Global Interactive Modals */}
      {selectedMetricToExplain && (
        <MetricExplanationModal
          metric={selectedMetricToExplain}
          onClose={() => setSelectedMetricToExplain(null)}
        />
      )}

      {showWorkflowModal && (
        <MonthlyWorkflowModal
          client={currentClient}
          onClose={() => setShowWorkflowModal(false)}
          onNavigateToTab={tab => setActiveTab(tab)}
          onQuickExport={handleExportFullPack}
        />
      )}

      {showClientModal && (
        <ClientManagerModal
          currentClient={currentClient}
          onSelectClient={handleSelectClient}
          onClose={() => setShowClientModal(false)}
        />
      )}

      {showAskCfoModal && (
        <AskCfoModal
          isOpen={showAskCfoModal}
          onClose={() => setShowAskCfoModal(false)}
          model={model}
          kpis={kpis}
          firmName={firmName}
        />
      )}

      {showQuickExportModal && (
        <QuickExportModal
          isOpen={showQuickExportModal}
          onClose={() => setShowQuickExportModal(false)}
          model={model}
          kpis={kpis}
          commentary={commentary}
          firmName={firmName}
          onNavigateToReports={() => setActiveTab('cfo_pack_generator')}
        />
      )}
    </div>
  );
}
