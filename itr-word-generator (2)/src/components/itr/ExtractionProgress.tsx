/**
 * ExtractionProgress & Audit Log Component - ITR Computation Studio
 * Displays real-time progress, dynamic processing stages, and extraction diagnostics.
 */

import React from 'react';
import {
  AlertTriangle,
  Terminal,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { ExtractionStatus, CompleteITRData } from '../../itr-types';

interface ExtractionProgressProps {
  status: ExtractionStatus;
  currentData?: CompleteITRData | null;
  logs?: Array<{ time: string; text: string; type?: 'info' | 'success' | 'warn' }>;
  isProcessing?: boolean;
}

export const ExtractionProgress: React.FC<ExtractionProgressProps> = ({
  status,
  currentData,
  logs = [],
  isProcessing = false,
}) => {
  const isComplete = status.step === 'ready';
  const isError = status.step === 'error';

  return (
    <section className="bg-white rounded-lg border border-slate-200 p-4 sm:p-5 shadow-sm flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
          <Terminal className="w-3.5 h-3.5 text-blue-600" />
          <span>Extraction Log & Audit</span>
        </h2>
        <span className="text-[10px] font-mono">
          {isComplete ? (
            <span className="text-emerald-600 font-bold flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Ready
            </span>
          ) : isProcessing ? (
            <span className="text-blue-600 font-bold flex items-center gap-1">
              <Loader2 className="w-3 h-3 animate-spin" /> {status.progress}% Processing
            </span>
          ) : (
            <span className="text-slate-400 font-medium">Idle</span>
          )}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            isError ? 'bg-rose-500' : isComplete ? 'bg-emerald-500' : 'bg-blue-600'
          }`}
          style={{ width: `${Math.max(status.progress, isProcessing ? 15 : 0)}%` }}
        />
      </div>

      {/* Status Line */}
      <div className="text-xs font-medium text-slate-700 flex items-center justify-between">
        <span className="truncate">{status.message || 'Ready to upload ITR'}</span>
        {currentData && currentData.personalInfo.pan && (
          <span className="text-[11px] font-mono text-slate-500 shrink-0">
            {currentData.personalInfo.pan}
          </span>
        )}
      </div>

      {/* Monospace Log Lines */}
      {logs.length > 0 ? (
        <div className="space-y-1.5 font-mono text-[10px] text-slate-600 leading-relaxed bg-slate-50 p-2.5 rounded border border-slate-200 max-h-36 overflow-auto">
          {logs.map((log, idx) => (
            <div key={idx} className="flex gap-2 items-start">
              <span className={log.type === 'warn' ? 'text-rose-500 font-bold' : log.type === 'success' ? 'text-emerald-600 font-semibold' : 'text-blue-500'}>
                [{log.time}]
              </span>
              <span className={log.type === 'success' ? 'text-emerald-700 font-medium' : log.type === 'warn' ? 'text-rose-700' : 'text-slate-700'}>
                {log.text}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-3 bg-slate-50 border border-slate-200 rounded text-center text-xs text-slate-400">
          Upload an ITR PDF or select a sample return to view extraction logs.
        </div>
      )}

      {/* Warning callout if any */}
      {status.warnings && status.warnings.length > 0 && (
        <div className="text-[10px] text-amber-800 bg-amber-50 border border-amber-200 rounded p-2 flex items-start gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
          <span>{status.warnings[0]}</span>
        </div>
      )}
    </section>
  );
};
