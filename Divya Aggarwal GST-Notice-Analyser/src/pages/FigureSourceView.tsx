import React from 'react';
import { NoticeCase, NoticeIssue, ReconciliationItem } from '../types';
import { identifyDepartmentFigureSource } from '../services/figureSourceEngine';
import { SearchCode, AlertTriangle, ArrowRight, FileSpreadsheet, Calculator } from 'lucide-react';

interface FigureSourceViewProps {
  activeCase: NoticeCase | null;
  issues: NoticeIssue[];
  reconciliations: ReconciliationItem[];
  onNavigateToTracker: () => void;
  onNavigateToReconciliation: () => void;
}

export const FigureSourceView: React.FC<FigureSourceViewProps> = ({
  activeCase,
  issues,
  reconciliations,
  onNavigateToTracker,
  onNavigateToReconciliation,
}) => {
  if (!activeCase) {
    return (
      <div className="flex items-center justify-center h-full p-8 text-gray-500 text-xs">
        No active notice selected. Please select or upload a notice.
      </div>
    );
  }

  const figureSources = issues.map((iss) =>
    identifyDepartmentFigureSource(iss.allegation, iss.title, iss.taxAmount)
  );
  const reconFor = (issueNumber: number) =>
    reconciliations.find((r) => r.issueNumber === issueNumber);

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full bg-[#F8FAFC]">
      <div className="bg-white rounded-2xl p-5 border border-gray-200 shadow-2xs flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-blue-50 text-blue-700 rounded-xl border border-blue-200">
            <SearchCode className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-base font-bold text-gray-900">
              Department Figure Source Finder
            </h1>
            <p className="text-xs text-gray-500">
              Directly answers: <span className="font-semibold italic text-blue-900">"From where has the tax officer picked this figure?"</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onNavigateToReconciliation}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#4338CA] hover:bg-[#3730A3] text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            <Calculator className="w-4 h-4" />
            <span>Upload returns &amp; reconcile</span>
          </button>
          <button
            onClick={onNavigateToTracker}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold transition-all shadow-2xs cursor-pointer"
          >
            <FileSpreadsheet className="w-4 h-4" />
            <span>Document tracker</span>
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {figureSources.map((fs, idx) => {
          const rec = reconFor(issues[idx]?.issueNumber);
          return (
          <div key={idx} className="bg-white rounded-2xl border border-gray-200 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-[#4338CA] text-white flex items-center justify-center text-xs font-bold">
                  {idx + 1}
                </span>
                <span className="text-sm font-bold text-gray-900">{fs.issueTitle}</span>
                {rec && (
                  <span
                    onClick={onNavigateToReconciliation}
                    className={`cursor-pointer text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                      rec.status === 'MISMATCH' ? 'bg-red-50 text-red-700 border-red-200'
                        : rec.status === 'MATCH' ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-slate-100 text-slate-500 border-slate-200'}`}
                    title="Open in Reconciliation"
                  >
                    Recon: {rec.status === 'MISSING_DATA' ? 'figures pending' : `${rec.status} ₹${rec.variance.toLocaleString('en-IN')}`}
                  </span>
                )}
              </div>
              <div className="text-right">
                <span className="text-xs text-gray-400 font-bold uppercase mr-2">Disputed Amount:</span>
                <span className="text-base font-black text-[#4338CA]">
                  ₹{fs.disputedAmount.toLocaleString('en-IN')}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="bg-gray-50 p-3 rounded-xl border border-gray-200 space-y-1">
                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                  1. Department Data Origin
                </div>
                <div className="font-bold text-gray-900">{fs.departmentSource}</div>
                <div className="text-[11px] text-gray-600 mt-1">
                  <span className="font-semibold">Table Reference:</span> {fs.portalTableReference}
                </div>
              </div>

              <div className="bg-gray-50 p-3 rounded-xl border border-gray-200 space-y-1">
                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                  2. Required Verification Procedure
                </div>
                <div className="font-medium text-gray-800 leading-relaxed">
                  {fs.verificationStep}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="bg-blue-50/60 p-3 rounded-xl border border-blue-200 space-y-1">
                <div className="text-[10px] font-bold text-blue-800 uppercase tracking-wider">
                  3. Exact GST Portal Report to Download
                </div>
                <div className="font-bold text-blue-950">{fs.requiredPortalReport}</div>
                <div className="text-[11px] text-blue-800 font-mono mt-1">
                  Path: {fs.suggestedPortalPath}
                </div>
              </div>

              <div className="bg-amber-50/60 p-3 rounded-xl border border-amber-200 flex flex-col justify-between">
                <div className="space-y-1">
                  <div className="text-[10px] font-bold text-amber-800 uppercase tracking-wider flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                    <span>Missing Data Action Radar</span>
                  </div>
                  <div className="font-medium text-amber-950 text-[11px]">
                    {fs.missingReportAction}
                  </div>
                </div>

                <div className="mt-2 flex justify-end">
                  <button
                    onClick={onNavigateToTracker}
                    className="flex items-center gap-1 px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-[11px] font-bold transition-colors cursor-pointer"
                  >
                    <span>Request Document from Client</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          </div>
          );
        })}
      </div>
    </div>
  );
};
