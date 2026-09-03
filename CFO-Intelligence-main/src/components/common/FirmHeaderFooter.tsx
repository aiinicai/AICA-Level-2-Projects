import React, { useState } from 'react';
import { Download, Printer, CheckCircle2, Loader2, FileDown } from 'lucide-react';
import { ClientProfile } from '../../types';
import { ExportService } from '../../services/exportService';

interface FirmHeaderProps {
  client: ClientProfile;
  reportTitle?: string;
  firmName?: string;
  tagline?: string;
  targetContainerId?: string;
  onDownloadPdf?: () => void;
  showExportActions?: boolean;
}

export const FirmReportHeader: React.FC<FirmHeaderProps> = ({
  client,
  reportTitle = 'Executive CFO Performance & FP&A Report',
  firmName = 'Jasleen Daswal & Associates',
  tagline = 'Chartered Accountants & Virtual CFO Advisory Services',
  targetContainerId,
  onDownloadPdf,
  showExportActions = true,
}) => {
  const [isExporting, setIsExporting] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const handleDownloadPdf = async () => {
    if (onDownloadPdf) {
      onDownloadPdf();
      return;
    }

    // Default container export
    const container = targetContainerId ? document.getElementById(targetContainerId) : document.querySelector('main') || document.body;
    if (!container) return;

    setIsExporting(true);
    setStatusMsg('Generating PDF...');
    try {
      const cleanTitle = reportTitle.replace(/[^a-zA-Z0-9]/g, '_');
      const cleanClient = client.name.replace(/[^a-zA-Z0-9]/g, '_');
      const fileName = `${cleanClient}_${cleanTitle}_${new Date().toISOString().slice(0, 10)}.pdf`;

      await ExportService.downloadElementAsPdf(container as HTMLElement, fileName, {
        orientation: 'portrait',
        onProgress: msg => setStatusMsg(msg),
      });

      setStatusMsg('Downloaded!');
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (err) {
      console.error(err);
      setStatusMsg('Fallback to print...');
      window.print();
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="border-b border-slate-300 pb-3.5 mb-5 print:border-black">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-[#0F172A] text-white font-bold flex items-center justify-center text-xs shadow-xs shrink-0">
              JD
            </div>
            <div>
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">{firmName}</h2>
              <p className="text-[10px] text-slate-500 font-medium">{tagline}</p>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:items-end gap-1.5">
          <div className="sm:text-right">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Client Organization</div>
            <div className="text-sm font-bold text-slate-900">{client.name}</div>
            <div className="text-[11px] text-slate-500 font-medium">
              {client.industryName} • Period: {client.reportingPeriod} ({client.currency})
            </div>
          </div>

          {showExportActions && (
            <div className="flex items-center gap-2 mt-1 print:hidden">
              <button
                onClick={handleDownloadPdf}
                disabled={isExporting}
                title="Download this report directly as a PDF document"
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-sky-50 hover:bg-sky-100 border border-sky-200 text-sky-800 text-xs font-bold transition-all shadow-2xs cursor-pointer disabled:opacity-50"
              >
                {isExporting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-600" />
                    <span>{statusMsg || 'Generating...'}</span>
                  </>
                ) : statusMsg ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>{statusMsg}</span>
                  </>
                ) : (
                  <>
                    <FileDown className="w-3.5 h-3.5 text-sky-600" />
                    <span>Download PDF</span>
                  </>
                )}
              </button>

              <button
                onClick={() => window.print()}
                title="Print or Save via System Dialog"
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 text-xs font-medium transition-all cursor-pointer"
              >
                <Printer className="w-3.5 h-3.5 text-slate-500" />
                <span className="hidden sm:inline">Print</span>
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="mt-2.5 pt-2 border-t border-slate-200/80 flex items-center justify-between text-[10px] text-slate-400 font-mono">
        <span className="font-semibold text-slate-600">DELIVERABLE: {reportTitle.toUpperCase()}</span>
        <span>ISSUED: {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</span>
      </div>
    </div>
  );
};

export const FirmReportFooter: React.FC<{ firmName?: string }> = ({
  firmName = 'Jasleen Daswal & Associates',
}) => {
  return (
    <div className="mt-8 pt-3 border-t border-slate-200 text-[10px] text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-2 print:border-black">
      <div className="flex items-center gap-2">
        <span className="font-bold text-slate-700">Curated by {firmName}</span>
        <span>•</span>
        <span>Confidential CFO Advisory Workspace</span>
      </div>
      <div className="text-slate-400 font-mono">
        Strict Client Privilege • FP&A Engine v4.0
      </div>
    </div>
  );
};
