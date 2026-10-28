import React, { useState } from 'react';
import { 
  X, 
  Download, 
  FileText, 
  FileSpreadsheet, 
  Code, 
  CheckCircle2, 
  Printer, 
  ShieldCheck, 
  Calendar,
  Building,
  Activity,
  Layers,
  Sparkles
} from 'lucide-react';
import { Company, FinancialStatement, FinancialRatios, CreditAssessment, RedFlag, User } from '../types/financial';
import { 
  downloadPdfReport, 
  downloadExcelFinancialModel, 
  downloadSampleUploadTemplate, 
  downloadJsonAssessment 
} from '../utils/reportGenerator';

interface ReportDownloadModalProps {
  isOpen: boolean;
  onClose: () => void;
  company: Company;
  statements: FinancialStatement[];
  ratios: FinancialRatios;
  assessment: CreditAssessment;
  redFlags: RedFlag[];
  currentUser: User;
}

export const ReportDownloadModal: React.FC<ReportDownloadModalProps> = ({
  isOpen,
  onClose,
  company,
  statements,
  ratios,
  assessment,
  redFlags,
  currentUser
}) => {
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  if (!isOpen) return null;

  const triggerDownload = (type: string, fn: () => void) => {
    fn();
    setDownloadSuccess(type);
    setTimeout(() => setDownloadSuccess(null), 3000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden my-8">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30">
              <Download className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Download Credit Assessment Outputs</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Generate lender-ready reports and multi-year financial modeling spreadsheets for <span className="text-cyan-300 font-semibold">{company.companyName}</span>
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Download Success Alert */}
        {downloadSuccess && (
          <div className="m-6 mb-0 p-3 bg-emerald-950/60 border border-emerald-700 rounded-xl text-emerald-300 text-xs flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Successfully downloaded <strong>{downloadSuccess}</strong>!</span>
          </div>
        )}

        {/* Source Code Archive Banner - For Running Locally */}
        <div className="m-6 mb-0 p-4 bg-gradient-to-r from-blue-950/90 via-indigo-950/80 to-purple-950/90 border border-blue-600/40 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-xl">
          <div className="flex items-start space-x-3.5">
            <div className="p-3 bg-blue-600 text-white rounded-xl shadow-lg shadow-blue-600/30 shrink-0">
              <Download className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-sm font-extrabold text-white">Full Application Source Code (.ZIP)</span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  Ready to Run Locally
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1">
                Complete self-contained project package with React 19, TypeScript, Tailwind CSS, all components, ratio engines, scoring formulas, and README.
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-cyan-300 font-mono">
                <span className="bg-slate-900/80 px-2 py-0.5 rounded border border-slate-700">npm install</span>
                <span>➔</span>
                <span className="bg-slate-900/80 px-2 py-0.5 rounded border border-slate-700">npm run dev</span>
                <span>➔</span>
                <span className="text-slate-400">localhost:3000</span>
              </div>
            </div>
          </div>

          <a
            href="/credimetrics-source-code.zip"
            download="credimetrics-credit-assessment-tool.zip"
            onClick={() => triggerDownload('Complete Project Source Code (.ZIP)', () => {})}
            className="w-full sm:w-auto flex items-center justify-center space-x-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white px-5 py-3 rounded-xl text-xs font-black shadow-lg shadow-cyan-500/30 transition shrink-0 uppercase tracking-wider"
          >
            <Download className="w-4 h-4" />
            <span>Download Project (.ZIP)</span>
          </a>
        </div>

        {/* Report Overview Card */}
        <div className="p-6 space-y-4">
          <div className="bg-slate-850 border border-slate-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Report Metadata</div>
              <div className="text-sm font-bold text-white mt-0.5">{company.companyName}</div>
              <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                <span>CIN: {company.cin}</span>
                <span>•</span>
                <span>PAN: {company.pan}</span>
                <span>•</span>
                <span>Date: {assessment.assessmentDate}</span>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <div className="bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 text-center">
                <span className="text-[9px] text-slate-400 uppercase font-bold block">Credit Grade</span>
                <span className="text-base font-black text-cyan-300">{assessment.creditGrade}</span>
              </div>
              <div className="bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 text-center">
                <span className="text-[9px] text-slate-400 uppercase font-bold block">Health Score</span>
                <span className="text-base font-black text-white">{assessment.healthScore.totalScore}/100</span>
              </div>
              <div className="bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 text-center">
                <span className="text-[9px] text-slate-400 uppercase font-bold block">Sanction Status</span>
                <span className={`text-xs font-black uppercase ${
                  assessment.recommendation === 'Approve' ? 'text-emerald-400' :
                  assessment.recommendation === 'Conditional Approval' ? 'text-amber-400' :
                  assessment.recommendation === 'Review Required' ? 'text-orange-400' : 'text-rose-400'
                }`}>
                  {assessment.recommendation}
                </span>
              </div>
            </div>
          </div>

          {/* Export Options Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            
            {/* 1. PDF Credit Appraisal Memo */}
            <div className="bg-slate-850 hover:bg-slate-800/80 border border-slate-700/80 hover:border-blue-500 rounded-xl p-5 transition flex flex-col justify-between group">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-400 group-hover:bg-blue-500 group-hover:text-white transition">
                    <FileText className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                    Primary Output
                  </span>
                </div>

                <h4 className="text-sm font-bold text-white">Lender-Ready CAM (PDF)</h4>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  Institutional Credit Appraisal Memorandum including Executive Summary, 4-pillar Health Score, Ratio Benchmarks, Red Flag Analysis, Covenants, and Sign-off Authority blocks.
                </p>
                <div className="mt-3 text-[11px] text-slate-400 font-mono">
                  Format: Multi-Page Vector PDF (A4)
                </div>
              </div>

              <button
                type="button"
                onClick={() => triggerDownload('Credit Appraisal Memorandum (PDF)', () => {
                  downloadPdfReport(company, statements, ratios, assessment, redFlags, currentUser);
                })}
                className="mt-4 w-full flex items-center justify-center space-x-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white py-2.5 rounded-xl text-xs font-bold transition shadow-md shadow-blue-600/30"
              >
                <Download className="w-4 h-4" />
                <span>Download PDF Report</span>
              </button>
            </div>

            {/* 2. Excel Financial Model */}
            <div className="bg-slate-850 hover:bg-slate-800/80 border border-slate-700/80 hover:border-emerald-500 rounded-xl p-5 transition flex flex-col justify-between group">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500 group-hover:text-white transition">
                    <FileSpreadsheet className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    Full Workbook
                  </span>
                </div>

                <h4 className="text-sm font-bold text-white">Financial Ratio Model (.xlsx)</h4>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  Complete Excel workbook with 4 structured worksheets: Credit Appraisal Summary, Multi-Year Financial Statements (BS &amp; P&amp;L), Ratio Calculations, and Red Flag Risk Matrix.
                </p>
                <div className="mt-3 text-[11px] text-slate-400 font-mono">
                  Format: Microsoft Excel Workbook (.xlsx)
                </div>
              </div>

              <button
                type="button"
                onClick={() => triggerDownload('Excel Financial Model (.xlsx)', () => {
                  downloadExcelFinancialModel(company, statements, ratios, assessment, redFlags);
                })}
                className="mt-4 w-full flex items-center justify-center space-x-2 bg-slate-800 hover:bg-slate-700 text-emerald-300 hover:text-white border border-slate-700 hover:border-emerald-500 py-2.5 rounded-xl text-xs font-bold transition"
              >
                <Download className="w-4 h-4" />
                <span>Download Excel Model</span>
              </button>
            </div>

            {/* 3. Financial Upload Template */}
            <div className="bg-slate-850 hover:bg-slate-800/80 border border-slate-700/80 hover:border-cyan-500 rounded-xl p-5 transition flex flex-col justify-between group">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 group-hover:bg-cyan-500 group-hover:text-white transition">
                    <Building className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                    Import Template
                  </span>
                </div>

                <h4 className="text-sm font-bold text-white">Blank Import Template (.xlsx)</h4>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  Standardized spreadsheet schema with pre-labeled Balance Sheet and Profit &amp; Loss line items ready to populate and upload into the ratio engine.
                </p>
                <div className="mt-3 text-[11px] text-slate-400 font-mono">
                  Format: Blank Import Workbook (.xlsx)
                </div>
              </div>

              <button
                type="button"
                onClick={() => triggerDownload('Upload Template (.xlsx)', () => {
                  downloadSampleUploadTemplate();
                })}
                className="mt-4 w-full flex items-center justify-center space-x-2 bg-slate-800 hover:bg-slate-700 text-cyan-300 hover:text-white border border-slate-700 hover:border-cyan-500 py-2.5 rounded-xl text-xs font-bold transition"
              >
                <Download className="w-4 h-4" />
                <span>Download Upload Template</span>
              </button>
            </div>

            {/* 4. JSON Assessment Data */}
            <div className="bg-slate-850 hover:bg-slate-800/80 border border-slate-700/80 hover:border-purple-500 rounded-xl p-5 transition flex flex-col justify-between group">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 group-hover:bg-purple-500 group-hover:text-white transition">
                    <Code className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    Data Payload
                  </span>
                </div>

                <h4 className="text-sm font-bold text-white">Raw Assessment JSON</h4>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  Machine-readable JSON data payload containing complete company profile, calculated ratios, category weights, scoring breakdown, and red flag diagnostics.
                </p>
                <div className="mt-3 text-[11px] text-slate-400 font-mono">
                  Format: JSON Export (.json)
                </div>
              </div>

              <button
                type="button"
                onClick={() => triggerDownload('Assessment JSON Data', () => {
                  downloadJsonAssessment(company, statements, ratios, assessment, redFlags);
                })}
                className="mt-4 w-full flex items-center justify-center space-x-2 bg-slate-800 hover:bg-slate-700 text-purple-300 hover:text-white border border-slate-700 hover:border-purple-500 py-2.5 rounded-xl text-xs font-bold transition"
              >
                <Download className="w-4 h-4" />
                <span>Download JSON Data</span>
              </button>
            </div>

          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-850 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>Prepared by: <strong className="text-slate-200">{currentUser.name}</strong> ({currentUser.role})</span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-semibold transition"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
};
