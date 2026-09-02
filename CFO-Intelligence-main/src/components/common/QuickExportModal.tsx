import React, { useState } from 'react';
import {
  X,
  FileText,
  FileSpreadsheet,
  Mail,
  Printer,
  Download,
  CheckCircle2,
  Loader2,
  Sparkles,
  ShieldCheck,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { FinancialModel, KpiMetric, CfoCommentary } from '../../types';
import { ExportService } from '../../services/exportService';
import { FinancialEngine } from '../../services/financialEngine';
import { ForecastingEngine } from '../../services/forecastingEngine';

interface QuickExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  model: FinancialModel;
  kpis: KpiMetric[];
  commentary: CfoCommentary;
  firmName?: string;
  onNavigateToCfoPack?: () => void;
}

export const QuickExportModal: React.FC<QuickExportModalProps> = ({
  isOpen,
  onClose,
  model,
  kpis,
  commentary,
  firmName = 'Jasleen Daswal & Associates',
  onNavigateToCfoPack,
}) => {
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [isExportingExcel, setIsExportingExcel] = useState(false);
  const [pdfStatus, setPdfStatus] = useState<string | null>(null);
  const [copiedMemo, setCopiedMemo] = useState(false);

  if (!isOpen) return null;

  const client = model.client;

  const handleDownloadPdf = async () => {
    setIsExportingPdf(true);
    setPdfStatus('Capturing report canvas...');
    try {
      // Find main view or active content
      const target = document.querySelector('main') || document.body;
      const fileName = `${client.name.replace(/[^a-zA-Z0-9]/g, '_')}_CFO_Advisory_Report_${new Date().toISOString().slice(0, 10)}.pdf`;

      await ExportService.downloadElementAsPdf(target as HTMLElement, fileName, {
        orientation: 'portrait',
        onProgress: msg => setPdfStatus(msg),
      });

      setPdfStatus('PDF Downloaded!');
      setTimeout(() => {
        setPdfStatus(null);
        onClose();
      }, 1800);
    } catch (err) {
      console.error(err);
      setPdfStatus('Fallback to print preview...');
      window.print();
    } finally {
      setIsExportingPdf(false);
    }
  };

  const handleDownloadExcel = () => {
    setIsExportingExcel(true);
    const breakEven = FinancialEngine.calculateBreakEvenAnalysis(model);
    const scenario = ForecastingEngine.generateRolling12MonthForecast(model);
    ExportService.exportFullCfoWorkbook(model, kpis, commentary, scenario, breakEven, firmName);
    setTimeout(() => {
      setIsExportingExcel(false);
      onClose();
    }, 1000);
  };

  const handleCopyMemo = () => {
    const memo = ExportService.generateExecutiveEmailMemo(model, kpis, commentary, firmName);
    navigator.clipboard.writeText(memo);
    setCopiedMemo(true);
    setTimeout(() => setCopiedMemo(false), 2500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-lg rounded-2xl border border-slate-200 shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="bg-[#0F172A] text-white p-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-sky-500/20 text-sky-400 rounded-xl">
              <Download className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold tracking-tight">Export Deliverables & Reports</h3>
              <p className="text-xs text-slate-400">
                {client.name} • Period: {client.reportingPeriod}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content / Options List */}
        <div className="p-6 space-y-4">
          <div className="text-xs text-slate-600 font-medium">
            Select the desired export format for executive presentations, board meetings, and client distribution:
          </div>

          <div className="space-y-3">
            {/* Option 1: PDF Download */}
            <div className="p-4 rounded-xl border-2 border-sky-100 hover:border-sky-300 bg-sky-50/40 transition-all flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-sky-600 text-white rounded-lg shrink-0 mt-0.5">
                  <FileText className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <span>Executive Report (PDF)</span>
                    <span className="text-[10px] bg-sky-100 text-sky-800 font-semibold px-1.5 py-0.2 rounded">
                      High-Res Vector
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Download the current active screen as a clean, high-resolution PDF document with client branding.
                  </p>
                </div>
              </div>

              <button
                onClick={handleDownloadPdf}
                disabled={isExportingPdf}
                className="px-4 py-2 bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow-xs transition-colors shrink-0 flex items-center gap-1.5 cursor-pointer"
              >
                {isExportingPdf ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>{pdfStatus || 'Generating...'}</span>
                  </>
                ) : pdfStatus ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-300" />
                    <span>{pdfStatus}</span>
                  </>
                ) : (
                  <>
                    <Download className="w-3.5 h-3.5" />
                    <span>Download PDF</span>
                  </>
                )}
              </button>
            </div>

            {/* Option 2: Full Multi-Page Board Pack */}
            {onNavigateToCfoPack && (
              <div className="p-4 rounded-xl border border-slate-200 hover:border-indigo-300 bg-indigo-50/20 transition-all flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-indigo-600 text-white rounded-lg shrink-0 mt-0.5">
                    <Layers className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <span>Full 5-Page Board Pack (PDF)</span>
                      <span className="text-[10px] bg-indigo-100 text-indigo-800 font-semibold px-1.5 py-0.2 rounded">
                        Full Advisory
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Open the interactive CFO Pack builder with cover page, statements, KPI trends, scenarios, and partner sign-off.
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => {
                    onClose();
                    onNavigateToCfoPack();
                  }}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg shadow-xs transition-colors shrink-0 flex items-center gap-1 cursor-pointer"
                >
                  <span>Open Pack</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {/* Option 3: Excel Financial Model */}
            <div className="p-4 rounded-xl border border-slate-200 hover:border-emerald-300 bg-emerald-50/20 transition-all flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-emerald-600 text-white rounded-lg shrink-0 mt-0.5">
                  <FileSpreadsheet className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-sm font-bold text-slate-900">Financial Model (.xlsx)</div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Multi-tab Excel workbook with P&L, Balance Sheet, Forecast, KPIs, and Break-Even tabs.
                  </p>
                </div>
              </div>

              <button
                onClick={handleDownloadExcel}
                disabled={isExportingExcel}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow-xs transition-colors shrink-0 flex items-center gap-1.5 cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>{isExportingExcel ? 'Saving...' : 'Download .xlsx'}</span>
              </button>
            </div>

            {/* Option 4: Executive Email Memo */}
            <div className="p-4 rounded-xl border border-slate-200 hover:border-slate-300 bg-slate-50/50 transition-all flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-slate-800 text-white rounded-lg shrink-0 mt-0.5">
                  <Mail className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-sm font-bold text-slate-900">Executive Email Briefing</div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Pre-formatted text memo ready to paste into Outlook, Gmail, or Slack for leadership updates.
                  </p>
                </div>
              </div>

              <button
                onClick={handleCopyMemo}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold rounded-lg shadow-xs transition-colors shrink-0 flex items-center gap-1.5 cursor-pointer"
              >
                {copiedMemo ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Mail className="w-3.5 h-3.5" />
                    <span>Copy Text</span>
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Privilege & Privacy Shield Protected</span>
            </div>
            <button
              onClick={() => window.print()}
              className="text-slate-500 hover:text-slate-900 font-medium underline cursor-pointer"
            >
              Open Browser Print Dialog
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
