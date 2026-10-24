import React, { useState, useMemo } from 'react';
import { 
  Building2, 
  ShieldCheck, 
  FileText, 
  BarChart3, 
  TrendingUp, 
  Layers, 
  AlertTriangle, 
  Download, 
  UploadCloud, 
  History, 
  Plus, 
  CheckCircle2, 
  FileSpreadsheet, 
  Coins, 
  Scale, 
  Droplets, 
  HelpCircle,
  ExternalLink,
  ChevronRight
} from 'lucide-react';

import { Company, FinancialStatement, User, AuditLog } from './types/financial';
import { SEED_COMPANIES, SEED_USERS, SEED_STATEMENTS, INITIAL_AUDIT_LOGS } from './data/seedData';
import { calculateRatios } from './utils/ratioEngine';
import { calculateHealthScore, assessCredit } from './utils/healthScoreEngine';
import { detectRedFlags } from './utils/redFlagEngine';
import { downloadPdfReport, downloadExcelFinancialModel, downloadSampleUploadTemplate } from './utils/reportGenerator';

import { Navbar } from './components/Navbar';
import { HealthScoreCard } from './components/HealthScoreCard';
import { CreditDecisionBanner } from './components/CreditDecisionBanner';
import { RedFlagsAlert } from './components/RedFlagsAlert';
import { RatioTable } from './components/RatioTable';
import { TrendAnalysisView } from './components/TrendAnalysisView';
import { UploadModal } from './components/UploadModal';
import { ReportDownloadModal } from './components/ReportDownloadModal';
import { CompanyModal } from './components/CompanyModal';
import { AuditLogsModal } from './components/AuditLogsModal';
import { AiInsightsCard } from './components/AiInsightsCard';

export default function App() {
  // 1. Core State
  const [companies, setCompanies] = useState<Company[]>(SEED_COMPANIES);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>(SEED_COMPANIES[0].id);
  const [allStatementsByCompany, setAllStatementsByCompany] = useState<Record<string, FinancialStatement[]>>(SEED_STATEMENTS);
  const [currentUser, setCurrentUser] = useState<User>(SEED_USERS[0]); // CA Rajesh Verma default
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>(INITIAL_AUDIT_LOGS);

  // Active Main Tab
  const [activeTab, setActiveTab] = useState<'overview' | 'ratios' | 'trends' | 'statements' | 'appraisal'>('overview');

  // Modals state
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [isCompanyModalOpen, setIsCompanyModalOpen] = useState(false);
  const [isAuditLogsOpen, setIsAuditLogsOpen] = useState(false);

  // Selected financial year selector for current company
  const [selectedYearOverride, setSelectedYearOverride] = useState<string | null>(null);

  // 2. Selected Company Object
  const selectedCompany = useMemo(() => {
    return companies.find(c => c.id === selectedCompanyId) || companies[0];
  }, [companies, selectedCompanyId]);

  // 3. Statements for active company (sorted chronologically)
  const companyStatements = useMemo(() => {
    const raw = allStatementsByCompany[selectedCompany.id] || [];
    return [...raw].sort((a, b) => a.financialYear.localeCompare(b.financialYear));
  }, [allStatementsByCompany, selectedCompany.id]);

  // Selected year statement (defaults to latest available year)
  const currentStatement = useMemo(() => {
    if (companyStatements.length === 0) return null;
    if (selectedYearOverride) {
      const match = companyStatements.find(s => s.financialYear === selectedYearOverride);
      if (match) return match;
    }
    return companyStatements[companyStatements.length - 1];
  }, [companyStatements, selectedYearOverride]);

  const previousStatement = useMemo(() => {
    if (!currentStatement || companyStatements.length < 2) return undefined;
    const currentIdx = companyStatements.findIndex(s => s.financialYear === currentStatement.financialYear);
    return currentIdx > 0 ? companyStatements[currentIdx - 1] : undefined;
  }, [companyStatements, currentStatement]);

  // 4. Compute Ratios for all years of the active company
  const ratiosByYear = useMemo(() => {
    const map: Record<string, ReturnType<typeof calculateRatios>> = {};
    companyStatements.forEach((stmt, idx) => {
      const prev = idx > 0 ? companyStatements[idx - 1] : undefined;
      map[stmt.financialYear] = calculateRatios(stmt, prev);
    });
    return map;
  }, [companyStatements]);

  // 5. Current Year Ratios
  const currentRatios = useMemo(() => {
    if (!currentStatement) return null;
    return ratiosByYear[currentStatement.financialYear] || calculateRatios(currentStatement, previousStatement);
  }, [currentStatement, previousStatement, ratiosByYear]);

  // 6. Financial Health Score (25% weights)
  const healthScore = useMemo(() => {
    if (!currentRatios) return null;
    return calculateHealthScore(currentRatios);
  }, [currentRatios]);

  // 7. Credit Assessment (Decision Matrix)
  const creditAssessment = useMemo(() => {
    if (!currentRatios || !healthScore) return null;
    return assessCredit(selectedCompany, currentRatios, healthScore);
  }, [selectedCompany, currentRatios, healthScore]);

  // 8. Red Flags
  const redFlags = useMemo(() => {
    if (!currentStatement || !currentRatios) return [];
    const historical = companyStatements.filter(s => s.financialYear !== currentStatement.financialYear);
    return detectRedFlags(currentStatement, currentRatios, historical);
  }, [currentStatement, currentRatios, companyStatements]);

  // 9. Handlers
  const addAuditLog = (action: string, details: string) => {
    const newLog: AuditLog = {
      id: `log-${Date.now()}`,
      userId: currentUser.id,
      userName: currentUser.name,
      userRole: currentUser.role,
      action,
      details,
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19)
    };
    setAuditLogs(prev => [newLog, ...prev]);
  };

  const handleSelectCompany = (company: Company) => {
    setSelectedCompanyId(company.id);
    setSelectedYearOverride(null);
    addAuditLog('Switched Company', `Active borrower switched to ${company.companyName} (${company.cin}).`);
  };

  const handleSaveNewCompany = (newComp: Company) => {
    setCompanies(prev => [newComp, ...prev]);
    setSelectedCompanyId(newComp.id);
    setSelectedYearOverride(null);
    addAuditLog('Created Borrower Company', `New company ${newComp.companyName} registered by ${currentUser.name}.`);
  };

  const handleStatementsUploaded = (newStatements: FinancialStatement[]) => {
    setAllStatementsByCompany(prev => {
      const existing = prev[selectedCompany.id] || [];
      // Merge or update statements
      const updatedMap = new Map<string, FinancialStatement>();
      existing.forEach(s => updatedMap.set(s.financialYear, s));
      newStatements.forEach(s => updatedMap.set(s.financialYear, s));
      return {
        ...prev,
        [selectedCompany.id]: Array.from(updatedMap.values())
      };
    });
    addAuditLog(
      'Financial Statement Uploaded', 
      `Imported ${newStatements.length} statement(s) for ${selectedCompany.companyName}. Ratios and credit scoring updated.`
    );
  };

  const handleQuickDownloadPdf = () => {
    if (currentStatement && currentRatios && creditAssessment) {
      downloadPdfReport(selectedCompany, companyStatements, currentRatios, creditAssessment, redFlags, currentUser);
      addAuditLog(
        'Downloaded PDF CAM Report', 
        `Downloaded Credit Appraisal Memorandum for ${selectedCompany.companyName} (${creditAssessment.creditGrade}).`
      );
    }
  };

  const handleQuickDownloadExcel = () => {
    if (currentStatement && currentRatios && creditAssessment) {
      downloadExcelFinancialModel(selectedCompany, companyStatements, currentRatios, creditAssessment, redFlags);
      addAuditLog(
        'Downloaded Excel Model', 
        `Downloaded Financial Ratio Model (.xlsx) for ${selectedCompany.companyName}.`
      );
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      
      {/* 1. Institutional Top Navbar */}
      <Navbar
        companies={companies}
        selectedCompany={selectedCompany}
        onSelectCompany={handleSelectCompany}
        currentUser={currentUser}
        onSwitchUser={(user) => {
          setCurrentUser(user);
          addAuditLog('Role Switched', `Active session persona changed to ${user.name} (${user.role}).`);
        }}
        availableUsers={SEED_USERS}
        onOpenUpload={() => setIsUploadOpen(true)}
        onOpenNewCompany={() => setIsCompanyModalOpen(true)}
        onOpenReportModal={() => setIsReportOpen(true)}
        onOpenAuditLogs={() => setIsAuditLogsOpen(true)}
        onQuickDownloadPdf={handleQuickDownloadPdf}
      />

      {/* 2. Sub-Header: Company Meta & Quick Action Bar */}
      <section className="bg-slate-900/80 border-b border-slate-800 backdrop-blur-sm px-4 sm:px-6 lg:px-8 py-3.5">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-3">
          
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm font-bold text-white flex items-center gap-1.5">
              <Building2 className="w-4 h-4 text-cyan-400" />
              {selectedCompany.companyName}
            </span>
            <span className="text-xs text-slate-400 font-mono">CIN: {selectedCompany.cin}</span>
            <span className="text-xs text-slate-400 font-mono">PAN: {selectedCompany.pan}</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {selectedCompany.industry}
            </span>
          </div>

          {/* Reporting Period Picker & Direct Output Downloads */}
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-400 font-medium">Reporting Period:</span>
            <select
              value={currentStatement?.financialYear || ''}
              onChange={(e) => setSelectedYearOverride(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-cyan-300 font-bold focus:outline-none focus:border-blue-500"
            >
              {companyStatements.map(stmt => (
                <option key={stmt.id} value={stmt.financialYear}>
                  {stmt.financialYear}
                </option>
              ))}
            </select>

            {/* Direct Instant Download Buttons (Explicitly satisfies downloadable output requirement) */}
            <button
              onClick={handleQuickDownloadPdf}
              className="flex items-center space-x-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 hover:text-white px-3 py-1 rounded-lg text-xs font-semibold border border-blue-500/30 transition"
              title="Direct Download PDF Report"
            >
              <FileText className="w-3.5 h-3.5 text-blue-400" />
              <span>PDF CAM</span>
            </button>

            <button
              onClick={handleQuickDownloadExcel}
              className="flex items-center space-x-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 hover:text-white px-3 py-1 rounded-lg text-xs font-semibold border border-emerald-500/30 transition"
              title="Direct Download Excel Model (.xlsx)"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
              <span>Excel Model</span>
            </button>
          </div>

        </div>
      </section>

      {/* 3. Main Navigation Tab Pills */}
      <div className="border-b border-slate-800/80 bg-slate-900/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-2 overflow-x-auto py-2.5 scrollbar-none">
            
            <button
              onClick={() => setActiveTab('overview')}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'overview'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
              }`}
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Health Score &amp; Credit Decision</span>
            </button>

            <button
              onClick={() => setActiveTab('ratios')}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'ratios'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
              }`}
            >
              <Scale className="w-4 h-4" />
              <span>Financial Ratios Engine</span>
            </button>

            <button
              onClick={() => setActiveTab('trends')}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'trends'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
              }`}
            >
              <TrendingUp className="w-4 h-4" />
              <span>Multi-Year Trend Analysis</span>
            </button>

            <button
              onClick={() => setActiveTab('statements')}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'statements'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
              }`}
            >
              <FileSpreadsheet className="w-4 h-4" />
              <span>Financial Statements (BS &amp; P&amp;L)</span>
            </button>

            <button
              onClick={() => setActiveTab('appraisal')}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-bold whitespace-nowrap transition ${
                activeTab === 'appraisal'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
              }`}
            >
              <Coins className="w-4 h-4" />
              <span>Credit Underwriting Appraisal</span>
            </button>

          </nav>
        </div>
      </div>

      {/* 4. Main Body Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        
        {/* If no financial statements available */}
        {!currentStatement ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center max-w-lg mx-auto my-12">
            <UploadCloud className="w-12 h-12 text-blue-400 mx-auto mb-3" />
            <h3 className="text-base font-bold text-white">No Financial Statements Loaded</h3>
            <p className="text-xs text-slate-400 mt-1">
              Upload an Excel (.xlsx) file, CSV, or enter statements manually for {selectedCompany.companyName}.
            </p>
            <button
              onClick={() => setIsUploadOpen(true)}
              className="mt-4 inline-flex items-center space-x-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-lg"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Upload Statements</span>
            </button>
          </div>
        ) : (
          <>
            {/* TAB 1: OVERVIEW & HEALTH SCORE */}
            {activeTab === 'overview' && (
              <div className="space-y-6">
                
                {/* Credit Decision Banner (Decision Matrix Outcome) */}
                {creditAssessment && (
                  <CreditDecisionBanner
                    assessment={creditAssessment}
                    company={selectedCompany}
                    onOpenReportModal={() => setIsReportOpen(true)}
                  />
                )}

                {/* Financial Health Score Matrix (25% weights across 4 categories) */}
                {healthScore && (
                  <HealthScoreCard healthScore={healthScore} />
                )}

                {/* Red Flags Alert Engine */}
                <RedFlagsAlert redFlags={redFlags} />

                {/* AI Executive Commentary & Underwriting Synthesis */}
                {creditAssessment && currentRatios && (
                  <AiInsightsCard
                    company={selectedCompany}
                    ratios={currentRatios}
                    assessment={creditAssessment}
                    redFlags={redFlags}
                  />
                )}

                {/* Quick Ratio Preview Row */}
                {currentRatios && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                      <span className="text-[10px] uppercase font-bold text-slate-400">Current Ratio</span>
                      <div className="text-xl font-bold text-cyan-300 mt-1 font-mono">
                        {currentRatios.currentRatio.toFixed(2)}x
                      </div>
                      <span className="text-[10px] text-slate-400">Target: ≥ 1.33x</span>
                    </div>

                    <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                      <span className="text-[10px] uppercase font-bold text-slate-400">Debt to Equity</span>
                      <div className="text-xl font-bold text-amber-300 mt-1 font-mono">
                        {currentRatios.debtEquityRatio.toFixed(2)}x
                      </div>
                      <span className="text-[10px] text-slate-400">Target: ≤ 1.50x</span>
                    </div>

                    <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                      <span className="text-[10px] uppercase font-bold text-slate-400">Net Profit Margin</span>
                      <div className={`text-xl font-bold mt-1 font-mono ${currentRatios.netProfitMargin >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {currentRatios.netProfitMargin.toFixed(1)}%
                      </div>
                      <span className="text-[10px] text-slate-400">Target: ≥ 8.0%</span>
                    </div>

                    <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                      <span className="text-[10px] uppercase font-bold text-slate-400">Interest Coverage</span>
                      <div className="text-xl font-bold text-indigo-300 mt-1 font-mono">
                        {currentRatios.interestCoverageRatio >= 90 ? '>50x' : `${currentRatios.interestCoverageRatio.toFixed(2)}x`}
                      </div>
                      <span className="text-[10px] text-slate-400">Target: ≥ 3.00x</span>
                    </div>
                  </div>
                )}

              </div>
            )}

            {/* TAB 2: FINANCIAL RATIOS ENGINE */}
            {activeTab === 'ratios' && currentRatios && (
              <div className="space-y-6">
                <RatioTable
                  currentRatios={currentRatios}
                  allStatements={companyStatements}
                  allRatiosByYear={ratiosByYear}
                />
              </div>
            )}

            {/* TAB 3: MULTI-YEAR TREND ANALYSIS */}
            {activeTab === 'trends' && (
              <div className="space-y-6">
                <TrendAnalysisView
                  statements={companyStatements}
                  ratiosByYear={ratiosByYear}
                />
              </div>
            )}

            {/* TAB 4: FINANCIAL STATEMENTS (BS & P&L) */}
            {activeTab === 'statements' && (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl overflow-hidden p-6 space-y-6">
                
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-3">
                  <div>
                    <h3 className="text-base font-bold text-white">Audited Financial Statements</h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Multi-year Balance Sheet &amp; Profit and Loss statement comparison (INR Crores)
                    </p>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setIsUploadOpen(true)}
                      className="flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add / Upload Statement</span>
                    </button>
                  </div>
                </div>

                {/* Balance Sheet Table */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-400 mb-2">
                    Balance Sheet
                  </h4>
                  <div className="overflow-x-auto border border-slate-800 rounded-xl">
                    <table className="w-full text-left text-xs divide-y divide-slate-800">
                      <thead className="bg-slate-800/60 text-slate-400 text-[11px]">
                        <tr>
                          <th className="py-2.5 px-4">Line Item (INR Crores)</th>
                          {companyStatements.map(s => (
                            <th key={s.id} className="py-2.5 px-3 text-right">{s.financialYear}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-slate-300">
                        <tr className="bg-slate-850/40 font-bold text-slate-200">
                          <td colSpan={companyStatements.length + 1} className="py-2 px-4 text-cyan-300 text-[11px]">
                            ASSETS
                          </td>
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Cash &amp; Bank Balances</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{(s.balanceSheet.cash + s.balanceSheet.bank).toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Trade Receivables (Debtors)</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.balanceSheet.receivables.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Inventories / Stock</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.balanceSheet.inventory.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Other Current Assets</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.balanceSheet.otherCurrentAssets.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr className="bg-slate-800/30 font-semibold text-slate-200">
                          <td className="py-2 px-4">Total Current Assets</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono text-cyan-300">
                              {(s.balanceSheet.cash + s.balanceSheet.bank + s.balanceSheet.receivables + s.balanceSheet.inventory + s.balanceSheet.otherCurrentAssets).toFixed(2)}
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Fixed Assets (Net PPE)</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.balanceSheet.fixedAssets.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Non-Current Investments</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.balanceSheet.investments.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr className="bg-slate-800 font-bold text-white border-t border-slate-700">
                          <td className="py-2.5 px-4">TOTAL ASSETS</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2.5 px-3 text-right font-mono text-sm text-cyan-300">
                              {s.balanceSheet.totalAssets.toFixed(2)}
                            </td>
                          ))}
                        </tr>

                        <tr className="bg-slate-850/40 font-bold text-slate-200">
                          <td colSpan={companyStatements.length + 1} className="py-2 px-4 text-indigo-300 text-[11px]">
                            LIABILITIES &amp; EQUITY
                          </td>
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Trade Payables (Creditors)</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.balanceSheet.payables.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Short-Term Borrowings</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.balanceSheet.shortTermDebt.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Other Current Liabilities</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.balanceSheet.otherCurrentLiabilities.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr className="bg-slate-800/30 font-semibold text-slate-200">
                          <td className="py-2 px-4">Total Current Liabilities</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono text-amber-300">
                              {(s.balanceSheet.payables + s.balanceSheet.shortTermDebt + s.balanceSheet.otherCurrentLiabilities).toFixed(2)}
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Long-Term Debt</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.balanceSheet.longTermDebt.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Shareholder Equity Capital</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.balanceSheet.equity.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Reserves &amp; Surplus</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.balanceSheet.reserves.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr className="bg-slate-800 font-bold text-white border-t border-slate-700">
                          <td className="py-2.5 px-4">TOTAL LIABILITIES &amp; EQUITY</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2.5 px-3 text-right font-mono text-sm text-cyan-300">
                              {s.balanceSheet.totalLiabilities.toFixed(2)}
                            </td>
                          ))}
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Profit & Loss Table */}
                <div className="pt-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400 mb-2">
                    Profit &amp; Loss Statement (Income Statement)
                  </h4>
                  <div className="overflow-x-auto border border-slate-800 rounded-xl">
                    <table className="w-full text-left text-xs divide-y divide-slate-800">
                      <thead className="bg-slate-800/60 text-slate-400 text-[11px]">
                        <tr>
                          <th className="py-2.5 px-4">Line Item (INR Crores)</th>
                          {companyStatements.map(s => (
                            <th key={s.id} className="py-2.5 px-3 text-right">{s.financialYear}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-slate-300">
                        <tr className="font-bold text-white">
                          <td className="py-2 px-4">Revenue from Operations</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.profitAndLoss.revenue.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Cost of Goods Sold (COGS)</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.profitAndLoss.cogs.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr className="bg-slate-800/20 font-semibold text-slate-200">
                          <td className="py-2 px-4">Gross Profit</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono text-emerald-400">{s.profitAndLoss.grossProfit.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Operating Expenses (SG&amp;A)</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.profitAndLoss.operatingExpenses.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr className="bg-slate-800/30 font-semibold text-slate-200">
                          <td className="py-2 px-4">EBITDA</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.profitAndLoss.ebitda.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Depreciation &amp; Amortization</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.profitAndLoss.depreciation.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr className="bg-slate-800/30 font-semibold text-slate-200">
                          <td className="py-2 px-4">Operating Profit (EBIT)</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.profitAndLoss.ebit.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Interest &amp; Finance Costs</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.profitAndLoss.interestExpense.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Profit Before Tax (PBT)</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.profitAndLoss.profitBeforeTax.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr>
                          <td className="py-2 px-4">Tax Provision</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className="py-2 px-3 text-right font-mono">{s.profitAndLoss.taxExpense.toFixed(2)}</td>
                          ))}
                        </tr>
                        <tr className="bg-slate-800 font-bold text-white border-t border-slate-700">
                          <td className="py-2.5 px-4">NET PROFIT AFTER TAX (PAT)</td>
                          {companyStatements.map(s => (
                            <td key={s.id} className={`py-2.5 px-3 text-right font-mono text-sm ${s.profitAndLoss.netProfit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {s.profitAndLoss.netProfit.toFixed(2)}
                            </td>
                          ))}
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            )}

            {/* TAB 5: CREDIT APPRAISAL & DECISION */}
            {activeTab === 'appraisal' && creditAssessment && (
              <div className="space-y-6">
                
                {/* Executive Underwriting Summary Card */}
                <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-slate-800 gap-3">
                    <div>
                      <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Institutional CAM Memo</span>
                      <h3 className="text-lg font-bold text-white mt-0.5">Credit Committee Appraisal Memo</h3>
                    </div>
                    <button
                      onClick={() => setIsReportOpen(true)}
                      className="flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-lg"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download Full Appraisal Package</span>
                    </button>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed mt-4 bg-slate-850 p-4 rounded-xl border border-slate-800">
                    {creditAssessment.analystSummary}
                  </p>

                  {/* SWOT Breakdown */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                    
                    <div className="bg-emerald-950/20 border border-emerald-800/40 p-4 rounded-xl">
                      <h4 className="text-xs font-bold uppercase text-emerald-400 flex items-center gap-1.5 mb-2">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Key Financial Strengths</span>
                      </h4>
                      <ul className="space-y-1.5 text-xs text-slate-200">
                        {creditAssessment.strengths.map((str, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="text-emerald-400 font-bold">•</span>
                            <span>{str}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="bg-rose-950/20 border border-rose-800/40 p-4 rounded-xl">
                      <h4 className="text-xs font-bold uppercase text-rose-400 flex items-center gap-1.5 mb-2">
                        <AlertTriangle className="w-4 h-4" />
                        <span>Key Risk Weaknesses &amp; Gaps</span>
                      </h4>
                      <ul className="space-y-1.5 text-xs text-slate-200">
                        {creditAssessment.weaknesses.length > 0 ? (
                          creditAssessment.weaknesses.map((wk, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-rose-400 font-bold">•</span>
                              <span>{wk}</span>
                            </li>
                          ))
                        ) : (
                          <li className="text-slate-400 italic">No significant financial impairment detected.</li>
                        )}
                      </ul>
                    </div>

                  </div>

                  {/* Sanction Covenants & Approvals Table */}
                  <div className="mt-6 pt-5 border-t border-slate-800">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200 mb-3">
                      Recommended Terms of Sanction &amp; Legal Covenants
                    </h4>
                    <div className="bg-slate-850 rounded-xl p-4 border border-slate-800 space-y-2 text-xs">
                      {creditAssessment.covenants.map((cov, idx) => (
                        <div key={idx} className="flex items-start gap-2 text-slate-300">
                          <span className="text-cyan-400 font-bold">Covenant {idx + 1}:</span>
                          <span>{cov}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                </div>

              </div>
            )}
          </>
        )}

      </main>

      {/* 5. Institutional Footer */}
      <footer className="bg-slate-900 border-t border-slate-800 py-4 text-center text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>CrediMetrics Financial Ratio Analysis &amp; Credit Assessment Tool</span>
          <span className="text-[11px] text-slate-400">Institutional Banking &amp; CA Edition • Basel &amp; RBI Calibrated</span>
        </div>
      </footer>

      {/* MODALS */}
      {/* 1. Upload Modal */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        company={selectedCompany}
        onStatementsUploaded={handleStatementsUploaded}
      />

      {/* 2. Download Modal (Primary requirement: provide output file as downloadable) */}
      {currentStatement && currentRatios && creditAssessment && (
        <ReportDownloadModal
          isOpen={isReportOpen}
          onClose={() => setIsReportOpen(false)}
          company={selectedCompany}
          statements={companyStatements}
          ratios={currentRatios}
          assessment={creditAssessment}
          redFlags={redFlags}
          currentUser={currentUser}
        />
      )}

      {/* 3. Company Modal */}
      <CompanyModal
        isOpen={isCompanyModalOpen}
        onClose={() => setIsCompanyModalOpen(false)}
        onSaveCompany={handleSaveNewCompany}
        currentUser={currentUser}
      />

      {/* 4. Audit Logs Modal */}
      <AuditLogsModal
        isOpen={isAuditLogsOpen}
        onClose={() => setIsAuditLogsOpen(false)}
        logs={auditLogs}
      />

    </div>
  );
}
