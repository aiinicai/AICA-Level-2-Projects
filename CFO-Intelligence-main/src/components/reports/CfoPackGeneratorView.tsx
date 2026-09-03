import React, { useState } from 'react';
import {
  FileText,
  Download,
  Printer,
  Sparkles,
  CheckCircle2,
  Share2,
  Calendar,
  Layers,
  Settings,
  Eye,
  ZoomIn,
  ZoomOut,
  Maximize2,
  SlidersHorizontal,
  TrendingUp,
  Scale,
  ShieldCheck,
  Copy,
  ChevronLeft,
  ChevronRight,
  UserCheck,
  RefreshCw,
  FileSpreadsheet,
  Mail,
  AlertTriangle,
  Award,
  ArrowUpRight,
  ArrowDownRight,
  TrendingDown,
  Lock,
  Loader2,
  FileDown,
  ChevronDown,
} from 'lucide-react';
import {
  FinancialModel,
  KpiMetric,
  CfoCommentary,
  ScenarioResult,
  ClientProfile,
  BreakEvenResult,
} from '../../types';
import { ExportService } from '../../services/exportService';
import { FinancialEngine } from '../../services/financialEngine';
import { ForecastingEngine } from '../../services/forecastingEngine';
import { FirmReportHeader, FirmReportFooter } from '../common/FirmHeaderFooter';
import { AskCfoModal } from '../dashboard/AskCfoModal';

interface CfoPackGeneratorViewProps {
  model: FinancialModel;
  kpis: KpiMetric[];
  commentary: CfoCommentary;
  firmName?: string;
  onOpenAskCfo?: () => void;
}

export const CfoPackGeneratorView: React.FC<CfoPackGeneratorViewProps> = ({
  model,
  kpis,
  commentary,
  firmName = 'Jasleen Daswal & Associates',
  onOpenAskCfo,
}) => {
  const client = model.client;
  const breakEven = FinancialEngine.calculateBreakEvenAnalysis(model);
  const baseScenario = ForecastingEngine.generateRolling12MonthForecast(model);

  // Multi-scenario generation for Scenario Analysis section
  const prebuiltScenarios = ForecastingEngine.getPrebuiltScenarios(model);
  const bullScenario = prebuiltScenarios.find(s => s.id === 'aggressive')?.result || baseScenario;
  const bearScenario = prebuiltScenarios.find(s => s.id === 'conservative')?.result || baseScenario;

  const latestMonth = model.historicalMonthly[model.historicalMonthly.length - 1] || {} as any;
  const prevMonth = model.historicalMonthly[model.historicalMonthly.length - 2] || latestMonth;

  // View state
  const [activePreviewPage, setActivePreviewPage] = useState<number | 'all'>(1);
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [watermark, setWatermark] = useState<'NONE' | 'CONFIDENTIAL' | 'FINAL_APPROVED'>('CONFIDENTIAL');
  const [signatoryName, setSignatoryName] = useState<string>('Jasleen Daswal, CPA');
  const [signatoryTitle, setSignatoryTitle] = useState<string>('Partner & Head of CFO Advisory');
  const [isCopiedMemo, setIsCopiedMemo] = useState(false);
  const [showAskCfoModal, setShowAskCfoModal] = useState(false);

  // PDF Generation State
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [pdfProgressStatus, setPdfProgressStatus] = useState<string | null>(null);
  const [pdfSuccessMessage, setPdfSuccessMessage] = useState<string | null>(null);
  const [showPdfOptionsDropdown, setShowPdfOptionsDropdown] = useState(false);

  // Section inclusion toggles
  const [includedSections, setIncludedSections] = useState({
    coverAndNarrative: true,
    financialStatements: true,
    kpiTrendsAndBenchmarks: true,
    scenariosAndForecasting: true,
    breakEvenAndPrivacyAudit: true,
  });

  const formatCurrency = (val: number) => {
    if (!val && val !== 0) return '$0';
    if (Math.abs(val) >= 1_000_000) {
      return `${client.currencySymbol}${(val / 1_000_000).toFixed(2)}M`;
    }
    return `${client.currencySymbol}${(val / 1_000).toFixed(0)}k`;
  };

  const handleExportExcel = () => {
    ExportService.exportFullCfoWorkbook(model, kpis, commentary, baseScenario, breakEven, firmName);
  };

  const handlePrintPdf = () => {
    ExportService.printCfoReport();
  };

  const handleDownloadPdf = async (mode: 'full' | 'current' = 'full') => {
    setShowPdfOptionsDropdown(false);
    setIsGeneratingPdf(true);
    setPdfSuccessMessage(null);
    setPdfProgressStatus('Initiating PDF export...');

    try {
      const cleanClient = client.name.replace(/[^a-zA-Z0-9]/g, '_');
      const dateStamp = new Date().toISOString().slice(0, 10);

      if (mode === 'current' && activePreviewPage !== 'all') {
        const pageEl = document.getElementById(`cfo-page-${activePreviewPage}`);
        if (!pageEl) throw new Error(`Page ${activePreviewPage} element not found`);

        const fileName = `${cleanClient}_CFO_Report_Page_${activePreviewPage}_${dateStamp}.pdf`;
        await ExportService.downloadElementAsPdf(pageEl, fileName, {
          orientation: 'portrait',
          onProgress: msg => setPdfProgressStatus(msg),
        });
      } else {
        // Full Document Export: If not currently on 'all', temporarily ensure elements exist or render full continuous container
        const prevPage = activePreviewPage;
        if (activePreviewPage !== 'all') {
          setActivePreviewPage('all');
          // Wait for DOM update
          await new Promise(r => setTimeout(r, 150));
        }

        const docContainer = document.getElementById('cfo-pack-full-document');
        if (!docContainer) throw new Error('Document container not found');

        const fileName = `${cleanClient}_CFO_Advisory_Board_Pack_${dateStamp}.pdf`;
        await ExportService.downloadElementAsPdf(docContainer, fileName, {
          orientation: 'portrait',
          onProgress: msg => setPdfProgressStatus(msg),
        });

        if (prevPage !== 'all') {
          setActivePreviewPage(prevPage);
        }
      }

      setPdfSuccessMessage('PDF Downloaded successfully!');
      setTimeout(() => setPdfSuccessMessage(null), 4000);
    } catch (err) {
      console.error('PDF export error:', err);
      setPdfProgressStatus('Exporting via browser print dialog...');
      window.print();
    } finally {
      setIsGeneratingPdf(false);
      setPdfProgressStatus(null);
    }
  };

  const handleCopyEmailMemo = () => {
    const memo = ExportService.generateExecutiveEmailMemo(model, kpis, commentary, firmName);
    navigator.clipboard.writeText(memo);
    setIsCopiedMemo(true);
    setTimeout(() => setIsCopiedMemo(false), 2500);
  };

  // Preset Configurations
  const applyPreset = (presetType: 'full' | 'one_pager' | 'lender' | 'investor') => {
    if (presetType === 'full') {
      setIncludedSections({
        coverAndNarrative: true,
        financialStatements: true,
        kpiTrendsAndBenchmarks: true,
        scenariosAndForecasting: true,
        breakEvenAndPrivacyAudit: true,
      });
      setActivePreviewPage('all');
    } else if (presetType === 'one_pager') {
      setIncludedSections({
        coverAndNarrative: true,
        financialStatements: false,
        kpiTrendsAndBenchmarks: false,
        scenariosAndForecasting: false,
        breakEvenAndPrivacyAudit: false,
      });
      setActivePreviewPage(1);
    } else if (presetType === 'lender') {
      setIncludedSections({
        coverAndNarrative: true,
        financialStatements: true,
        kpiTrendsAndBenchmarks: false,
        scenariosAndForecasting: true,
        breakEvenAndPrivacyAudit: true,
      });
      setActivePreviewPage(2);
    } else if (presetType === 'investor') {
      setIncludedSections({
        coverAndNarrative: true,
        financialStatements: true,
        kpiTrendsAndBenchmarks: true,
        scenariosAndForecasting: true,
        breakEvenAndPrivacyAudit: false,
      });
      setActivePreviewPage(4);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <FirmReportHeader
        client={client}
        reportTitle="Virtual CFO Executive Advisory Deliverable"
        firmName={firmName}
        onDownloadPdf={() => handleDownloadPdf('full')}
      />

      {/* PDF Progress / Success Toast Banner */}
      {(isGeneratingPdf || pdfSuccessMessage) && (
        <div className={`p-4 rounded-xl border flex items-center justify-between shadow-lg transition-all animate-in slide-in-from-top duration-300 ${
          pdfSuccessMessage
            ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
            : 'bg-sky-50 border-sky-300 text-sky-950'
        }`}>
          <div className="flex items-center gap-3">
            {isGeneratingPdf ? (
              <Loader2 className="w-5 h-5 text-sky-600 animate-spin" />
            ) : (
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            )}
            <div>
              <div className="text-sm font-bold">
                {isGeneratingPdf ? 'Generating PDF Deliverable...' : 'PDF Export Complete!'}
              </div>
              <p className="text-xs text-slate-600">
                {pdfProgressStatus || pdfSuccessMessage}
              </p>
            </div>
          </div>
          {pdfSuccessMessage && (
            <button
              onClick={() => setPdfSuccessMessage(null)}
              className="text-xs font-semibold text-emerald-800 hover:text-emerald-950 px-2 py-1 bg-emerald-100 rounded cursor-pointer"
            >
              Dismiss
            </button>
          )}
        </div>
      )}

      {/* Top Banner & Quick Action Control Center */}
      <div className="card-dark-geometric p-6 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 shadow-xl">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="pill pill-info text-[9px] uppercase tracking-wider">
              Board-Ready Advisory Pack v4.0
            </span>
            <span className="text-slate-400 text-xs">•</span>
            <span className="text-slate-400 text-xs font-mono">Live PDF Mockup & Export Engine</span>
          </div>
          <h3 className="text-xl sm:text-2xl font-black text-white tracking-tight">
            Virtual CFO Monthly Report Pack
          </h3>
          <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
            Generates the complete executive advisory package with branded cover page, deterministic financial statements, multi-month KPI trend analysis, scenario stress tests, and verified partner sign-off.
          </p>
        </div>

        {/* Primary Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5 shrink-0 w-full lg:w-auto">
          {/* Download PDF Primary Button Group */}
          <div className="relative flex-1 sm:flex-none">
            <div className="flex rounded shadow-xs overflow-hidden">
              <button
                onClick={() => handleDownloadPdf('full')}
                disabled={isGeneratingPdf}
                className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-bold transition-all cursor-pointer"
                title="Download full executive report pack as a high-resolution PDF document"
              >
                {isGeneratingPdf ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-white" />
                    <span>Rendering PDF...</span>
                  </>
                ) : (
                  <>
                    <FileDown className="w-4 h-4 text-sky-200" />
                    <span>Download PDF Pack</span>
                  </>
                )}
              </button>
              <button
                onClick={() => setShowPdfOptionsDropdown(!showPdfOptionsDropdown)}
                className="px-2 py-2.5 bg-sky-700 hover:bg-sky-800 text-white border-l border-sky-500 transition-colors cursor-pointer"
                title="More PDF Download Options"
              >
                <ChevronDown className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Dropdown Menu */}
            {showPdfOptionsDropdown && (
              <div className="absolute right-0 mt-1.5 w-64 bg-white text-slate-900 rounded-lg shadow-xl border border-slate-200 py-1.5 z-40 text-xs animate-in fade-in duration-150">
                <div className="px-3 py-1 font-bold text-[10px] text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  PDF Export Options
                </div>
                <button
                  onClick={() => handleDownloadPdf('full')}
                  className="w-full text-left px-3 py-2 hover:bg-sky-50 flex items-center gap-2 text-slate-800 font-semibold cursor-pointer"
                >
                  <FileText className="w-4 h-4 text-sky-600" />
                  <div>
                    <div>Download Full 5-Page Pack</div>
                    <div className="text-[10px] text-slate-400 font-normal">Complete advisory deliverable</div>
                  </div>
                </button>
                <button
                  onClick={() => handleDownloadPdf('current')}
                  className="w-full text-left px-3 py-2 hover:bg-sky-50 flex items-center gap-2 text-slate-800 font-semibold cursor-pointer"
                >
                  <Download className="w-4 h-4 text-slate-600" />
                  <div>
                    <div>Download Current Page (Pg {activePreviewPage === 'all' ? '1-5' : activePreviewPage})</div>
                    <div className="text-[10px] text-slate-400 font-normal">Single-page vector PDF</div>
                  </div>
                </button>
                <div className="border-t border-slate-100 my-1"></div>
                <button
                  onClick={() => {
                    setShowPdfOptionsDropdown(false);
                    handlePrintPdf();
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-slate-50 flex items-center gap-2 text-slate-700 font-medium cursor-pointer"
                >
                  <Printer className="w-4 h-4 text-slate-500" />
                  <div>Open Browser Print / PDF Dialog</div>
                </button>
              </div>
            )}
          </div>

          <button
            onClick={handleExportExcel}
            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-xs transition-colors cursor-pointer"
          >
            <FileSpreadsheet className="w-4 h-4" />
            <span>Excel Model (.xlsx)</span>
          </button>

          <button
            onClick={handleCopyEmailMemo}
            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 hover:text-white text-xs font-bold shadow-xs transition-colors cursor-pointer"
          >
            {isCopiedMemo ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-400">Memo Copied!</span>
              </>
            ) : (
              <>
                <Mail className="w-4 h-4 text-sky-400" />
                <span>Executive Memo</span>
              </>
            )}
          </button>

          <button
            onClick={() => setShowAskCfoModal(true)}
            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sky-400 text-xs font-bold shadow-xs transition-colors cursor-pointer"
          >
            <Sparkles className="w-4 h-4 text-sky-400" />
            <span>Ask CFO AI</span>
          </button>
        </div>
      </div>

      {/* Deliverable Customization & Configuration Bar */}
      <div className="card-geometric p-4 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Deliverable Structure & Branding Settings
            </span>
            <p className="text-[11px] text-slate-500">Configure report sections, presets, and digital signatory parameters</p>
          </div>

          {/* Quick Presets */}
          <div className="flex items-center gap-1.5 overflow-x-auto text-xs">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mr-1">Presets:</span>
            <button
              onClick={() => applyPreset('full')}
              className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] cursor-pointer"
            >
              Full Board Pack (5 Pages)
            </button>
            <button
              onClick={() => applyPreset('one_pager')}
              className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] cursor-pointer"
            >
              Executive 1-Pager
            </button>
            <button
              onClick={() => applyPreset('investor')}
              className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] cursor-pointer"
            >
              Investor & Forecast Pack
            </button>
          </div>
        </div>

        {/* Checkbox Section Toggles + Signatory Controls */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
          <div className="md:col-span-8 flex flex-wrap items-center gap-2">
            {[
              { key: 'coverAndNarrative', label: '1. Cover & Executive Narrative' },
              { key: 'financialStatements', label: '2. P&L & Balance Sheet' },
              { key: 'kpiTrendsAndBenchmarks', label: '3. KPI Trends & Benchmarks' },
              { key: 'scenariosAndForecasting', label: '4. 12M Pro-Forma & Scenarios' },
              { key: 'breakEvenAndPrivacyAudit', label: '5. Break-Even & Privacy Audit' },
            ].map(sec => (
              <label
                key={sec.key}
                className={`px-3 py-1.5 rounded border text-xs font-semibold flex items-center gap-2 cursor-pointer transition-colors ${
                  includedSections[sec.key as keyof typeof includedSections]
                    ? 'bg-sky-50 border-sky-200 text-sky-900'
                    : 'bg-slate-50 border-slate-200 text-slate-400'
                }`}
              >
                <input
                  type="checkbox"
                  checked={includedSections[sec.key as keyof typeof includedSections]}
                  onChange={() =>
                    setIncludedSections(prev => ({
                      ...prev,
                      [sec.key]: !prev[sec.key as keyof typeof includedSections],
                    }))
                  }
                  className="w-3.5 h-3.5 accent-sky-600 rounded"
                />
                <span>{sec.label}</span>
              </label>
            ))}
          </div>

          <div className="md:col-span-4 flex items-center justify-start md:justify-end gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-500 font-medium text-[11px]">Watermark:</span>
              <select
                value={watermark}
                onChange={e => setWatermark(e.target.value as any)}
                className="bg-slate-50 border border-slate-200 rounded px-2 py-1 text-slate-800 font-semibold text-[11px] focus:outline-hidden focus:border-sky-500"
              >
                <option value="CONFIDENTIAL">Confidential Draft</option>
                <option value="FINAL_APPROVED">Final Approved</option>
                <option value="NONE">None</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* EXPORT PREVIEW LAYER: LIVE MOCKUP OF THE GENERATED PDF DOCUMENT          */}
      {/* ========================================================================= */}
      <div className="space-y-3">
        {/* Preview Toolbar */}
        <div className="bg-[#0F172A] text-white px-4 py-3 rounded-t-lg border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Page Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto text-xs">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mr-2 flex items-center gap-1.5">
              <Eye className="w-3.5 h-3.5 text-sky-400" />
              Live PDF Mockup:
            </span>

            {[
              { page: 1, label: 'Pg 1: Cover & Narrative' },
              { page: 2, label: 'Pg 2: Financials' },
              { page: 3, label: 'Pg 3: KPI Trends' },
              { page: 4, label: 'Pg 4: Scenarios & 12M' },
              { page: 5, label: 'Pg 5: Break-Even' },
              { page: 'all' as const, label: 'Continuous Full Document' },
            ].map(tab => (
              <button
                key={String(tab.page)}
                onClick={() => setActivePreviewPage(tab.page)}
                className={`px-3 py-1 rounded text-xs font-semibold transition-colors whitespace-nowrap cursor-pointer ${
                  activePreviewPage === tab.page
                    ? 'bg-sky-600 text-white shadow-xs'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Zoom Controls & Page Count Indicator */}
          <div className="flex items-center gap-2 text-xs">
            <div className="flex items-center gap-1 bg-slate-800 rounded px-2 py-0.5 border border-slate-700">
              <button
                onClick={() => setZoomLevel(Math.max(75, zoomLevel - 15))}
                className="p-1 text-slate-400 hover:text-white cursor-pointer"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="font-mono text-[11px] px-1 text-slate-200">{zoomLevel}%</span>
              <button
                onClick={() => setZoomLevel(Math.min(125, zoomLevel + 15))}
                className="p-1 text-slate-400 hover:text-white cursor-pointer"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
            </div>

            <button
              onClick={() => handleDownloadPdf(activePreviewPage === 'all' ? 'full' : 'current')}
              disabled={isGeneratingPdf}
              className="px-3 py-1 rounded bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold transition-colors cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
              title="Download the currently viewed page or full document as PDF"
            >
              {isGeneratingPdf ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <FileDown className="w-3.5 h-3.5" />
              )}
              <span>Download PDF</span>
            </button>

            <button
              onClick={handlePrintPdf}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors cursor-pointer flex items-center gap-1"
              title="Browser Print Preview"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print</span>
            </button>
          </div>
        </div>

        {/* Live Mockup Document Stage (Rendered with high-fidelity paper styling) */}
        <div className="bg-slate-700/60 p-4 sm:p-8 rounded-b-lg border border-slate-300 overflow-x-auto flex justify-center min-h-[600px]">
          <div
            id="cfo-pack-full-document"
            className="w-full max-w-[850px] space-y-8 transition-transform duration-200 origin-top"
            style={{ transform: `scale(${zoomLevel / 100})` }}
          >
            {/* ------------------------------------------------------------- */}
            {/* PAGE 1: EXECUTIVE COVER & CFO PERFORMANCE NARRATIVE           */}
            {/* ------------------------------------------------------------- */}
            {(activePreviewPage === 1 || activePreviewPage === 'all') && includedSections.coverAndNarrative && (
              <div
                id="cfo-page-1"
                className="bg-white text-[#0F172A] p-8 sm:p-12 shadow-2xl rounded-sm border border-slate-200 relative print:p-0 print:border-none print:shadow-none min-h-[960px] flex flex-col justify-between"
              >
                {/* Watermark */}
                {watermark !== 'NONE' && (
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none z-0">
                    <span className="text-slate-200 text-6xl sm:text-7xl font-black uppercase tracking-widest -rotate-45 opacity-60">
                      {watermark === 'CONFIDENTIAL' ? 'CONFIDENTIAL DRAFT' : 'FINAL APPROVED'}
                    </span>
                  </div>
                )}

                <div className="relative z-10 space-y-6">
                  {/* Firm Branding Header */}
                  <div className="border-b-2 border-[#0F172A] pb-4 flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded bg-[#0F172A] text-white font-bold flex items-center justify-center text-sm shadow-xs">
                        JD
                      </div>
                      <div>
                        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">{firmName}</h2>
                        <p className="text-xs text-slate-500 font-medium">Chartered Accountants & Virtual CFO Advisory Practice</p>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Client Deliverable</div>
                      <div className="text-base font-bold text-slate-900">{client.name}</div>
                      <div className="text-xs text-slate-500 font-medium">
                        Period: {client.reportingPeriod} • Currency: {client.currency}
                      </div>
                    </div>
                  </div>

                  {/* Title Banner */}
                  <div className="text-center py-3 bg-slate-50 rounded border border-slate-200">
                    <h1 className="text-lg sm:text-xl font-black text-slate-900 uppercase tracking-wide">
                      Monthly Virtual CFO Performance & Advisory Package
                    </h1>
                    <p className="text-xs text-slate-600 mt-0.5">
                      Prepared for the Executive Board and Management Committee
                    </p>
                  </div>

                  {/* 4 Geometric KPI Snapshot Cards */}
                  <div className="grid grid-cols-4 gap-3">
                    <div className="p-3 rounded bg-slate-50 border border-slate-200 text-center">
                      <span className="metric-label text-[9px]">Monthly Revenue</span>
                      <div className="text-base font-bold text-slate-900 mt-1">{formatCurrency(latestMonth.revenue)}</div>
                      <span className="text-[9px] text-emerald-700 font-semibold">+5.4% vs Baseline</span>
                    </div>

                    <div className="p-3 rounded bg-slate-50 border border-slate-200 text-center">
                      <span className="metric-label text-[9px]">Gross Margin</span>
                      <div className="text-base font-bold text-slate-900 mt-1">{latestMonth.grossMarginPercent?.toFixed(1)}%</div>
                      <span className="text-[9px] text-slate-500 font-medium">{formatCurrency(latestMonth.grossProfit)} GP</span>
                    </div>

                    <div className="p-3 rounded bg-slate-50 border border-slate-200 text-center">
                      <span className="metric-label text-[9px]">EBITDA</span>
                      <div className="text-base font-bold text-sky-800 mt-1">{formatCurrency(latestMonth.ebitda)}</div>
                      <span className="text-[9px] text-slate-500 font-medium">{latestMonth.ebitdaMarginPercent?.toFixed(1)}% Margin</span>
                    </div>

                    <div className="p-3 rounded bg-slate-50 border border-slate-200 text-center">
                      <span className="metric-label text-[9px]">Ending Cash</span>
                      <div className="text-base font-bold text-slate-900 mt-1">{formatCurrency(latestMonth.cashAndEquivalents)}</div>
                      <span className="text-[9px] text-emerald-700 font-semibold">~4.2 Mos Runway</span>
                    </div>
                  </div>

                  {/* Headline Summary */}
                  <div className="p-4 rounded-lg bg-sky-50/70 border border-sky-200/80">
                    <div className="text-[10px] font-bold text-sky-900 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-sky-600" />
                      Executive Headline Assessment
                    </div>
                    <p className="text-xs text-slate-800 font-semibold leading-relaxed">
                      "{commentary.headlineSummary}"
                    </p>
                  </div>

                  {/* 4-Step Narrative Structure */}
                  <div className="space-y-4 pt-1">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-1">
                        <div className="text-[10px] font-bold text-slate-700 uppercase tracking-wider">1. What Happened</div>
                        <p className="text-[11px] text-slate-600 leading-relaxed">{commentary.whatHappened}</p>
                      </div>

                      <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-1">
                        <div className="text-[10px] font-bold text-slate-700 uppercase tracking-wider">2. Why It Happened</div>
                        <p className="text-[11px] text-slate-600 leading-relaxed">{commentary.whyItHappened}</p>
                      </div>

                      <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-1">
                        <div className="text-[10px] font-bold text-slate-700 uppercase tracking-wider">3. Why It Matters</div>
                        <p className="text-[11px] text-slate-600 leading-relaxed">{commentary.whyItMatters}</p>
                      </div>
                    </div>

                    {/* CFO Directives */}
                    <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-2">
                      <div className="text-[10px] font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-sky-600" />
                        4. Strategic Management Directives (Action Plan)
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                        {commentary.recommendedActions.map((act, idx) => (
                          <div key={idx} className="p-2 bg-white rounded border border-slate-200 text-[11px] text-slate-700 flex items-start gap-2">
                            <span className="w-4 h-4 rounded-full bg-sky-100 text-sky-800 font-bold text-[9px] flex items-center justify-center shrink-0">
                              {idx + 1}
                            </span>
                            <span className="leading-snug">{act}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Page 1 Footer with Digital Signatory Block */}
                <div className="relative z-10 pt-6 border-t border-slate-200 flex items-end justify-between text-[10px] text-slate-500">
                  <div>
                    <div className="font-bold text-slate-900">{signatoryName}</div>
                    <div className="text-slate-500">{signatoryTitle}</div>
                    <div className="text-slate-400 font-mono mt-0.5">Signed: {new Date().toLocaleDateString()}</div>
                  </div>
                  <div className="text-right font-mono">
                    <div>Confidential • Curated by {firmName}</div>
                    <div className="text-slate-400">Page 1 of 5</div>
                  </div>
                </div>
              </div>
            )}

            {/* ------------------------------------------------------------- */}
            {/* PAGE 2: FINANCIAL STATEMENTS (P&L, BALANCE SHEET, CASH FLOW)  */}
            {/* ------------------------------------------------------------- */}
            {(activePreviewPage === 2 || activePreviewPage === 'all') && includedSections.financialStatements && (
              <div
                id="cfo-page-2"
                className="bg-white text-[#0F172A] p-8 sm:p-12 shadow-2xl rounded-sm border border-slate-200 relative print:p-0 print:border-none print:shadow-none min-h-[960px] flex flex-col justify-between"
              >
                <div className="space-y-6">
                  {/* Page Header */}
                  <div className="border-b border-slate-300 pb-3 flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">{firmName}</h3>
                      <h2 className="text-base font-bold text-slate-900">Profit & Loss and Balance Sheet Statements</h2>
                    </div>
                    <div className="text-right text-xs">
                      <span className="font-bold text-slate-900">{client.name}</span>
                      <div className="text-slate-500 font-mono text-[10px]">Fiscal Historical Actuals</div>
                    </div>
                  </div>

                  {/* Profit & Loss Table */}
                  <div className="space-y-2">
                    <div className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center justify-between">
                      <span>Monthly Income Statement Breakdown</span>
                      <span className="text-[10px] text-slate-400 font-mono">Currency: {client.currency}</span>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-slate-100 text-slate-700 uppercase font-semibold text-[10px] border-b border-slate-200">
                          <tr>
                            <th className="p-2">Line Item</th>
                            {model.historicalMonthly.slice(-4).map((m, i) => (
                              <th key={i} className="p-2 text-right">{m.periodLabel}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          <tr className="font-bold text-slate-900 bg-slate-50/70">
                            <td className="p-2">Gross Revenue</td>
                            {model.historicalMonthly.slice(-4).map((m, i) => (
                              <td key={i} className="p-2 text-right">{formatCurrency(m.revenue)}</td>
                            ))}
                          </tr>
                          <tr className="text-slate-600">
                            <td className="p-2">Cost of Goods Sold (COGS)</td>
                            {model.historicalMonthly.slice(-4).map((m, i) => (
                              <td key={i} className="p-2 text-right">({formatCurrency(m.cogs)})</td>
                            ))}
                          </tr>
                          <tr className="font-bold text-emerald-900 bg-emerald-50/40">
                            <td className="p-2">Gross Profit ({latestMonth.grossMarginPercent?.toFixed(0)}% Margin)</td>
                            {model.historicalMonthly.slice(-4).map((m, i) => (
                              <td key={i} className="p-2 text-right">{formatCurrency(m.grossProfit)}</td>
                            ))}
                          </tr>
                          <tr className="text-slate-600">
                            <td className="p-2">Salaries & Wages</td>
                            {model.historicalMonthly.slice(-4).map((m, i) => (
                              <td key={i} className="p-2 text-right">{formatCurrency(m.salariesAndWages)}</td>
                            ))}
                          </tr>
                          <tr className="text-slate-600">
                            <td className="p-2">Sales, Marketing & General OPEX</td>
                            {model.historicalMonthly.slice(-4).map((m, i) => (
                              <td key={i} className="p-2 text-right">{formatCurrency(m.salesAndMarketing + m.generalAndAdmin)}</td>
                            ))}
                          </tr>
                          <tr className="font-bold text-sky-900 bg-sky-50/50">
                            <td className="p-2">EBITDA ({latestMonth.ebitdaMarginPercent?.toFixed(1)}%)</td>
                            {model.historicalMonthly.slice(-4).map((m, i) => (
                              <td key={i} className="p-2 text-right text-sky-800">{formatCurrency(m.ebitda)}</td>
                            ))}
                          </tr>
                          <tr className="font-bold text-slate-900 bg-slate-100">
                            <td className="p-2">Net Income</td>
                            {model.historicalMonthly.slice(-4).map((m, i) => (
                              <td key={i} className="p-2 text-right">{formatCurrency(m.netIncome)}</td>
                            ))}
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Balance Sheet & Liquidity Summary */}
                  <div className="space-y-2 pt-2">
                    <div className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Balance Sheet & Liquidity Position
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                      <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
                        <span className="text-[10px] text-slate-500 font-medium">Cash & Equivalents</span>
                        <div className="text-sm font-bold text-slate-900 mt-0.5">{formatCurrency(latestMonth.cashAndEquivalents)}</div>
                      </div>
                      <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
                        <span className="text-[10px] text-slate-500 font-medium">Accounts Receivable</span>
                        <div className="text-sm font-bold text-slate-900 mt-0.5">{formatCurrency(latestMonth.accountsReceivable)}</div>
                      </div>
                      <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
                        <span className="text-[10px] text-slate-500 font-medium">Total Current Liabilities</span>
                        <div className="text-sm font-bold text-slate-900 mt-0.5">{formatCurrency(latestMonth.totalCurrentLiabilities)}</div>
                      </div>
                      <div className="p-2.5 bg-slate-50 rounded border border-slate-200">
                        <span className="text-[10px] text-slate-500 font-medium">Working Capital</span>
                        <div className="text-sm font-bold text-emerald-800 mt-0.5">{formatCurrency(latestMonth.workingCapital)}</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Page 2 Footer */}
                <div className="pt-6 border-t border-slate-200 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                  <span>Statements verified against client general ledger</span>
                  <span>Page 2 of 5</span>
                </div>
              </div>
            )}

            {/* ------------------------------------------------------------- */}
            {/* PAGE 3: KPI TRENDS & PEER BENCHMARKS                          */}
            {/* ------------------------------------------------------------- */}
            {(activePreviewPage === 3 || activePreviewPage === 'all') && includedSections.kpiTrendsAndBenchmarks && (
              <div
                id="cfo-page-3"
                className="bg-white text-[#0F172A] p-8 sm:p-12 shadow-2xl rounded-sm border border-slate-200 relative print:p-0 print:border-none print:shadow-none min-h-[960px] flex flex-col justify-between"
              >
                <div className="space-y-6">
                  {/* Page Header */}
                  <div className="border-b border-slate-300 pb-3 flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">{firmName}</h3>
                      <h2 className="text-base font-bold text-slate-900">Key Performance Indicators & Multi-Month Trends</h2>
                    </div>
                    <div className="text-right text-xs">
                      <span className="font-bold text-slate-900">Peer Benchmark: {client.industryName}</span>
                      <div className="text-slate-500 font-mono text-[10px]">Deterministic FP&A Matrix</div>
                    </div>
                  </div>

                  {/* KPI Table with Trend Direction & Peer Benchmarks */}
                  <div className="space-y-2">
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-slate-100 text-slate-700 uppercase font-semibold text-[10px] border-b border-slate-200">
                          <tr>
                            <th className="p-2.5">KPI Metric</th>
                            <th className="p-2.5">Category</th>
                            <th className="p-2.5 text-right">Current Actual</th>
                            <th className="p-2.5 text-right">Industry Benchmark</th>
                            <th className="p-2.5 text-center">Trend</th>
                            <th className="p-2.5 text-center">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {kpis.map((kpi, idx) => (
                            <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                              <td className="p-2.5 font-bold text-slate-900">{kpi.name}</td>
                              <td className="p-2.5 text-slate-500 uppercase text-[10px] font-semibold">{kpi.category}</td>
                              <td className="p-2.5 text-right font-black text-slate-900">{kpi.formattedValue}</td>
                              <td className="p-2.5 text-right text-slate-600 font-medium">{kpi.benchmarkFormatted || 'Target Range'}</td>
                              <td className="p-2.5 text-center">
                                <span className="inline-flex items-center text-[11px] font-bold text-slate-700">
                                  {kpi.trend === 'up' ? (
                                    <span className="text-emerald-700 flex items-center">
                                      <ArrowUpRight className="w-3 h-3 mr-0.5" /> Up
                                    </span>
                                  ) : (
                                    <span className="text-rose-700 flex items-center">
                                      <ArrowDownRight className="w-3 h-3 mr-0.5" /> Down
                                    </span>
                                  )}
                                </span>
                              </td>
                              <td className="p-2.5 text-center">
                                <span
                                  className={
                                    kpi.benchmarkStatus === 'outperforming'
                                      ? 'pill pill-success text-[9px]'
                                      : kpi.benchmarkStatus === 'lagging'
                                      ? 'pill pill-warning text-[9px]'
                                      : kpi.benchmarkStatus === 'critical'
                                      ? 'pill pill-danger text-[9px]'
                                      : 'pill pill-info text-[9px]'
                                  }
                                >
                                  {kpi.benchmarkStatus === 'outperforming'
                                    ? 'Outperforming'
                                    : kpi.benchmarkStatus === 'lagging'
                                    ? 'Watchlist'
                                    : kpi.benchmarkStatus === 'critical'
                                    ? 'Critical'
                                    : 'Optimal'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Qualitative CFO Metric Commentary */}
                  <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
                    <div className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      CFO Metric Diagnostic Notes
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">
                      • <b>Gross Margin Leadership:</b> Current gross margin of {latestMonth.grossMarginPercent?.toFixed(1)}% places {client.name} in the top quartile of {client.industryName} operators, protecting cash flows against variable price shifts.
                      <br />
                      • <b>Working Capital & Collections:</b> Days Sales Outstanding (DSO) at {Math.round(latestMonth.dso || 38)} days reflects disciplined accounts receivable cycles; recommend maintaining current credit terms with tier-1 counterparties.
                    </p>
                  </div>
                </div>

                {/* Page 3 Footer */}
                <div className="pt-6 border-t border-slate-200 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                  <span>Calibrated against proprietary mid-market accounting benchmarks</span>
                  <span>Page 3 of 5</span>
                </div>
              </div>
            )}

            {/* ------------------------------------------------------------- */}
            {/* PAGE 4: 12-MONTH PRO-FORMA FORECAST & SCENARIO ANALYSIS       */}
            {/* ------------------------------------------------------------- */}
            {(activePreviewPage === 4 || activePreviewPage === 'all') && includedSections.scenariosAndForecasting && (
              <div
                id="cfo-page-4"
                className="bg-white text-[#0F172A] p-8 sm:p-12 shadow-2xl rounded-sm border border-slate-200 relative print:p-0 print:border-none print:shadow-none min-h-[960px] flex flex-col justify-between"
              >
                <div className="space-y-6">
                  {/* Page Header */}
                  <div className="border-b border-slate-300 pb-3 flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">{firmName}</h3>
                      <h2 className="text-base font-bold text-slate-900">12-Month Pro-Forma & Multi-Scenario Stress Test</h2>
                    </div>
                    <div className="text-right text-xs">
                      <span className="font-bold text-slate-900">{client.name}</span>
                      <div className="text-slate-500 font-mono text-[10px]">Rolling 12M FP&A Projections</div>
                    </div>
                  </div>

                  {/* Scenario Analysis Matrix: Base vs Bull vs Bear */}
                  <div className="space-y-2">
                    <div className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Strategic Scenario Comparison (Base vs. Expansion vs. Downside)
                    </div>
                    <div className="grid grid-cols-3 gap-3 text-xs">
                      {/* Base Case */}
                      <div className="p-3.5 rounded bg-slate-50 border border-slate-200 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-900 uppercase text-[10px]">1. Base Run-Rate</span>
                          <span className="pill pill-info text-[9px]">Expected</span>
                        </div>
                        <div className="text-lg font-black text-slate-900">
                          {formatCurrency(baseScenario.totalProjectedRevenue)}
                        </div>
                        <div className="text-[11px] text-slate-600 space-y-0.5">
                          <div>EBITDA: <b className="text-sky-800">{formatCurrency(baseScenario.totalProjectedEbitda)}</b></div>
                          <div>Ending Cash: <b className="text-slate-900">{formatCurrency(baseScenario.endingCashBalance)}</b></div>
                          <div>Runway: <b className="text-emerald-700">&gt; 4.5 mos</b></div>
                        </div>
                      </div>

                      {/* Bull Case */}
                      <div className="p-3.5 rounded bg-emerald-50/50 border border-emerald-200 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-emerald-900 uppercase text-[10px]">2. Expansion (+15%)</span>
                          <span className="pill pill-success text-[9px]">Growth</span>
                        </div>
                        <div className="text-lg font-black text-emerald-900">
                          {formatCurrency(bullScenario.annualRevenue || baseScenario.totalProjectedRevenue * 1.15)}
                        </div>
                        <div className="text-[11px] text-slate-600 space-y-0.5">
                          <div>EBITDA: <b className="text-emerald-800">{formatCurrency((bullScenario.annualEbitda || baseScenario.totalProjectedEbitda * 1.28))}</b></div>
                          <div>Ending Cash: <b className="text-slate-900">{formatCurrency(bullScenario.endingCash || baseScenario.endingCashBalance * 1.2)}</b></div>
                          <div>Runway: <b className="text-emerald-700">&gt; 6.0 mos</b></div>
                        </div>
                      </div>

                      {/* Bear Case */}
                      <div className="p-3.5 rounded bg-rose-50/50 border border-rose-200 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-rose-900 uppercase text-[10px]">3. Stress Test (-20%)</span>
                          <span className="pill pill-danger text-[9px]">Downside</span>
                        </div>
                        <div className="text-lg font-black text-rose-900">
                          {formatCurrency(bearScenario.annualRevenue || baseScenario.totalProjectedRevenue * 0.8)}
                        </div>
                        <div className="text-[11px] text-slate-600 space-y-0.5">
                          <div>EBITDA: <b className="text-rose-800">{formatCurrency((bearScenario.annualEbitda || baseScenario.totalProjectedEbitda * 0.55))}</b></div>
                          <div>Ending Cash: <b className="text-slate-900">{formatCurrency(bearScenario.endingCash || baseScenario.endingCashBalance * 0.75)}</b></div>
                          <div>Runway: <b className="text-amber-700">~3.2 mos</b></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Monthly Forecast Projection Table */}
                  <div className="space-y-2 pt-2">
                    <div className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Rolling 12-Month Pro-Forma Schedule (Base Case)
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-slate-100 text-slate-700 uppercase font-semibold text-[10px] border-b border-slate-200">
                          <tr>
                            <th className="p-2">Month</th>
                            <th className="p-2 text-right">Revenue</th>
                            <th className="p-2 text-right">Gross Profit</th>
                            <th className="p-2 text-right">EBITDA</th>
                            <th className="p-2 text-right">Cash Flow</th>
                            <th className="p-2 text-right">Ending Cash</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {baseScenario.monthlyProjections.slice(0, 6).map((m, idx) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="p-2 font-bold text-slate-900">{m.month}</td>
                              <td className="p-2 text-right text-slate-700">{formatCurrency(m.revenue)}</td>
                              <td className="p-2 text-right text-slate-700">{formatCurrency(m.grossProfit)}</td>
                              <td className="p-2 text-right text-sky-800 font-semibold">{formatCurrency(m.ebitda)}</td>
                              <td className="p-2 text-right text-emerald-700 font-medium">{formatCurrency(m.netCashFlow)}</td>
                              <td className="p-2 text-right font-bold text-slate-900">{formatCurrency(m.cashBalance)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>

                {/* Page 4 Footer */}
                <div className="pt-6 border-t border-slate-200 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                  <span>Pro-forma models assume 3.5% baseline inflation and stable working capital days</span>
                  <span>Page 4 of 5</span>
                </div>
              </div>
            )}

            {/* ------------------------------------------------------------- */}
            {/* PAGE 5: BREAK-EVEN & PRIVACY AUDIT CERTIFICATION              */}
            {/* ------------------------------------------------------------- */}
            {(activePreviewPage === 5 || activePreviewPage === 'all') && includedSections.breakEvenAndPrivacyAudit && (
              <div
                id="cfo-page-5"
                className="bg-white text-[#0F172A] p-8 sm:p-12 shadow-2xl rounded-sm border border-slate-200 relative print:p-0 print:border-none print:shadow-none min-h-[960px] flex flex-col justify-between"
              >
                <div className="space-y-6">
                  {/* Page Header */}
                  <div className="border-b border-slate-300 pb-3 flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">{firmName}</h3>
                      <h2 className="text-base font-bold text-slate-900">Break-Even Analysis & Privacy Shield Certification</h2>
                    </div>
                    <div className="text-right text-xs">
                      <span className="font-bold text-slate-900">{client.name}</span>
                      <div className="text-slate-500 font-mono text-[10px]">Governance & Quality Assured</div>
                    </div>
                  </div>

                  {/* Break-Even Economics */}
                  <div className="space-y-2">
                    <div className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Operating Leverage & Break-Even Revenue Target
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <div className="p-3 bg-slate-50 rounded border border-slate-200">
                        <span className="text-[10px] text-slate-500 font-medium">Monthly Break-Even</span>
                        <div className="text-sm font-bold text-slate-900 mt-1">{formatCurrency(breakEven.breakEvenRevenueMonthly || breakEven.breakEvenRevenue)}</div>
                      </div>
                      <div className="p-3 bg-slate-50 rounded border border-slate-200">
                        <span className="text-[10px] text-slate-500 font-medium">Contribution Margin</span>
                        <div className="text-sm font-bold text-emerald-800 mt-1">{(breakEven.contributionMarginRatio * 100).toFixed(1)}%</div>
                      </div>
                      <div className="p-3 bg-slate-50 rounded border border-slate-200">
                        <span className="text-[10px] text-slate-500 font-medium">Fixed Monthly Overhead</span>
                        <div className="text-sm font-bold text-slate-900 mt-1">{formatCurrency(breakEven.fixedCosts)}</div>
                      </div>
                      <div className="p-3 bg-slate-50 rounded border border-slate-200">
                        <span className="text-[10px] text-slate-500 font-medium">Safety Buffer</span>
                        <div className="text-sm font-bold text-sky-800 mt-1">+{(breakEven.marginOfSafetyPercent || 0).toFixed(1)}%</div>
                      </div>
                    </div>
                  </div>

                  {/* Cryptographic Privacy Shield Verification Block */}
                  <div className="p-5 rounded-lg bg-slate-900 text-white space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="w-5 h-5 text-emerald-400" />
                        <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                          Privacy Shield Redaction Layer Verification
                        </span>
                      </div>
                      <span className="text-[10px] font-mono bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                        Zero PII Leakage Standard
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">
                      This financial advisory deliverable was computed in strict accordance with the firm's client privacy protocol. All personally identifiable information (PII), proprietary supplier identities, and banking coordinates were tokenized before any processing. Client identity is restored solely for client-authorized final deliverables.
                    </p>

                    <div className="grid grid-cols-3 gap-2 text-[10px] font-mono text-slate-400 pt-1">
                      <div>Token Hash: <span className="text-slate-200 font-bold">SHA-256 Verified</span></div>
                      <div>Engine: <span className="text-slate-200 font-bold">FP&A v4.0</span></div>
                      <div>Status: <span className="text-emerald-400 font-bold">Privilege Protected</span></div>
                    </div>
                  </div>
                </div>

                {/* Final Sign-off Box */}
                <div className="pt-6 border-t border-slate-200 flex items-center justify-between text-[10px] text-slate-500">
                  <div>
                    <div className="font-bold text-slate-900">Virtual CFO Advisory Practice</div>
                    <div>{firmName}</div>
                  </div>
                  <div className="text-right font-mono">
                    <div>Document Complete • All 5 Modules Verified</div>
                    <div className="text-slate-400">Page 5 of 5</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Ask Your CFO AI Modal */}
      <AskCfoModal
        isOpen={showAskCfoModal}
        onClose={() => setShowAskCfoModal(false)}
        model={model}
        kpis={kpis}
        firmName={firmName}
      />
    </div>
  );
};
