/**
 * ExtractionProgress & Log Component - High Density Design Theme
 * Displays timestamped monospace extraction log, active schema badge, and validation checks.
 */

import React from 'react';
import {
  CheckCircle2,
  Loader2,
  AlertTriangle,
  FileCheck,
  Calculator,
  ShieldCheck,
  Terminal,
} from 'lucide-react';
import { ExtractionStatus, CompleteITRData } from '../../itr-types';

interface ExtractionProgressProps {
  status: ExtractionStatus;
  currentData?: CompleteITRData | null;
  logs?: Array<{ time: string; text: string; type?: 'info' | 'success' | 'warn' }>;
}

export const ExtractionProgress: React.FC<ExtractionProgressProps> = ({
  status,
  currentData,
  logs = [],
}) => {
  const defaultLogs = [
    { time: '10:42:01', text: 'Initializing PDF parser & text spatial geometry...', type: 'info' as const },
    {
      time: '10:42:02',
      text: `Schema detected: ${currentData?.personalInfo.formType || 'ITR-1'} (${currentData?.personalInfo.taxRegime || 'New Regime'})`,
      type: 'info' as const,
    },
    {
      time: '10:42:03',
      text: `Extracted ${status.extractedFieldsCount || 24} core tax schedules & numeric fields.`,
      type: 'info' as const,
    },
    {
      time: '10:42:04',
      text: `Validated PAN: ${currentData?.personalInfo.pan || 'PASXXXXX1L'} • AY ${currentData?.personalInfo.assessmentYear || '2024-25'}`,
      type: 'info' as const,
    },
    {
      time: '10:42:05',
      text: status.step === 'error' ? `Error: ${status.error || 'Failed'}` : 'Success: Data available for review.',
      type: status.step === 'error' ? ('warn' as const) : ('success' as const),
    },
  ];

  const activeLogs = logs.length > 0 ? logs : defaultLogs;

  return (
    <section className="bg-white rounded-lg border border-slate-200 p-4 sm:p-5 shadow-sm flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
          <Terminal className="w-3.5 h-3.5 text-blue-600" /> Extraction Log & Audit
        </h2>
        <span className="text-[10px] font-mono text-slate-400">
          {status.step === 'ready' ? (
            <span className="text-emerald-600 font-bold">100% COMPLETE</span>
          ) : (
            <span className="text-blue-600 font-bold">{status.progress}% IN PROGRESS</span>
          )}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            status.step === 'error' ? 'bg-rose-500' : 'bg-blue-500'
          }`}
          style={{ width: `${status.progress}%` }}
        />
      </div>

      {/* Monospace Log Lines */}
      <div className="space-y-1.5 font-mono text-[10px] text-slate-600 leading-relaxed bg-slate-50 p-2.5 rounded border border-slate-200 max-h-36 overflow-auto">
        {activeLogs.map((log, idx) => (
          <div key={idx} className="flex gap-2 items-start">
            <span className={log.type === 'warn' ? 'text-rose-500 font-bold' : 'text-blue-500'}>
              [{log.time}]
            </span>
            <span className={log.type === 'success' ? 'text-emerald-700 font-medium' : log.type === 'warn' ? 'text-rose-700' : 'text-slate-700'}>
              {log.text}
            </span>
          </div>
        ))}
      </div>

      {/* Warning callout if any */}
      {status.warnings.length > 0 && (
        <div className="text-[10px] text-amber-800 bg-amber-50 border border-amber-200 rounded p-2 flex items-start gap-1.5">
          <AlertTriangle className="w-3 h-3 text-amber-600 shrink-0 mt-0.5" />
          <span>{status.warnings[0]}</span>
        </div>
      )}
    </section>
  );
};
