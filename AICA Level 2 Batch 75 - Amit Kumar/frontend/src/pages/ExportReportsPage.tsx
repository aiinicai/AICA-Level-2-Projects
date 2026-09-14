import React from 'react';
import type { Client } from '../types';
import { getExportExcelUrl, getExportPdfUrl, getExportWordUrl } from '../services/api';
import { Download, FileSpreadsheet, FileText, FileCode, ShieldCheck } from 'lucide-react';

interface ExportReportsProps {
  client: Client;
}

export const ExportReportsPage: React.FC<ExportReportsProps> = ({ client }) => {
  const excelUrl = getExportExcelUrl(client.id);
  const pdfUrl = getExportPdfUrl(client.id);
  const wordUrl = getExportWordUrl(client.id);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
        <h1 className="text-xl font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-tight flex items-center gap-2">
          <Download className="w-5 h-5 text-orange-600" />
          EXPORT FINANCIAL STATEMENTS & AUDIT REVIEW PACKS
        </h1>
        <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mt-0.5">
          Generate formula-linked Excel workbooks, print-ready PDF review packs, and editable Word documents (.docx) for {client.name}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Excel Export Card */}
        <div className="studio-card p-6 space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 rounded-lg">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xs font-black text-slate-900 dark:text-white uppercase">Formula-Linked Excel</h3>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">25 Schedule III Tabs with SUMIFS</p>
              </div>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-300">
              Complete formula-linked workbook with input schedules, SUMIFS balance sheet/P&L formulas, and Formula Audit sheet. Protected with <code className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded text-orange-600 font-mono">SWIndiaCA</code>.
            </p>
          </div>

          <a
            href={excelUrl}
            download
            className="ca-button-primary w-full text-xs py-2.5 flex items-center justify-center gap-2"
          >
            <Download className="w-4 h-4" /> Download Excel (.xlsx)
          </a>
        </div>

        {/* Word Export Card */}
        <div className="studio-card p-6 space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-100 dark:bg-blue-950/60 text-blue-600 rounded-lg">
                <FileCode className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xs font-black text-slate-900 dark:text-white uppercase">Editable Word Report</h3>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">12 Sections (.docx Format)</p>
              </div>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-300">
              Fully editable Microsoft Word document (.docx) formatted with navy headers, grey amount column shading, page breaks, and partner sign-off block.
            </p>
          </div>

          <a
            href={wordUrl}
            download
            className="ca-button-primary w-full text-xs py-2.5 flex items-center justify-center gap-2"
          >
            <Download className="w-4 h-4" /> Download Word (.docx)
          </a>
        </div>

        {/* PDF Export Card */}
        <div className="studio-card p-6 space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-amber-100 dark:bg-amber-950/60 text-amber-600 rounded-lg">
                <FileText className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xs font-black text-slate-900 dark:text-white uppercase">Print-Ready PDF Pack</h3>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">A4 PDF Review Document</p>
              </div>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-300">
              Print-ready PDF report with cover page, index, financial statements, accounting policies, detailed notes, ratios, and CA sign-off block.
            </p>
          </div>

          <a
            href={pdfUrl}
            download
            className="ca-button-primary w-full text-xs py-2.5 flex items-center justify-center gap-2"
          >
            <Download className="w-4 h-4" /> Download PDF Review Pack
          </a>
        </div>
      </div>

      {/* Security Note */}
      <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 flex items-center gap-3 text-xs">
        <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0" />
        <span className="text-slate-600 dark:text-slate-300 font-semibold">
          Confidential CA Audit Export Engine: All generated files strictly abide by Schedule III Division I (IGAAP) standards.
        </span>
      </div>
    </div>
  );
};
