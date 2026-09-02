import React, { useState } from 'react';
import {
  X,
  CalendarCheck,
  CheckCircle2,
  Circle,
  ArrowRight,
  ShieldCheck,
  FileSpreadsheet,
  TrendingUp,
  Sparkles,
  Download,
} from 'lucide-react';
import { ClientProfile } from '../../types';

interface MonthlyWorkflowModalProps {
  client: ClientProfile;
  onClose: () => void;
  onNavigateToTab: (tab: any) => void;
  onQuickExport: () => void;
}

export const MonthlyWorkflowModal: React.FC<MonthlyWorkflowModalProps> = ({
  client,
  onClose,
  onNavigateToTab,
  onQuickExport,
}) => {
  const [completedSteps, setCompletedSteps] = useState<Record<number, boolean>>({
    1: true,
    2: true,
    3: true,
    4: true,
    5: false,
    6: false,
  });

  const toggleStep = (stepNum: number) => {
    setCompletedSteps(prev => ({
      ...prev,
      [stepNum]: !prev[stepNum],
    }));
  };

  const steps = [
    {
      num: 1,
      title: 'Import & Reconcile Monthly Financials',
      desc: 'Ingest monthly P&L, Balance Sheet, or Trial Balance from Excel / QBO / Tally.',
      tab: 'data_import',
      icon: FileSpreadsheet,
    },
    {
      num: 2,
      title: 'Execute Data Quality & Audit Check (96/100)',
      desc: 'Verify mathematical integrity across gross margins, EBITDA, and cash conversion cycle.',
      tab: 'data_quality',
      icon: CheckCircle2,
    },
    {
      num: 3,
      title: 'Apply Privacy Shield Tokenization',
      desc: 'Ensure all confidential PII, tax IDs, and bank wire routes are tokenized before AI synthesis.',
      tab: 'privacy_shield',
      icon: ShieldCheck,
    },
    {
      num: 4,
      title: 'Review Executive Commentary & Wins',
      desc: 'Review 4-part CFO narrative (What happened, Why, Why it matters, Actions) and sign off.',
      tab: 'executive_summary',
      icon: Sparkles,
    },
    {
      num: 5,
      title: 'Review 12-Month Pro-Forma & Scenarios',
      desc: 'Test what-if sensitivity drivers and confirm client margin of safety.',
      tab: 'scenarios',
      icon: TrendingUp,
    },
    {
      num: 6,
      title: 'Generate & Export Board-Ready CFO Pack',
      desc: 'Download multi-sheet Excel financial workbook and printable client PDF.',
      action: onQuickExport,
      icon: Download,
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 max-w-2xl w-full overflow-hidden">
        {/* Header */}
        <div className="bg-slate-900 px-6 py-5 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600/30 rounded-xl text-indigo-400 border border-indigo-500/30">
              <CalendarCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="text-xs text-indigo-400 font-bold uppercase tracking-wider">
                Virtual CFO Standard Operating Procedure
              </div>
              <h3 className="text-lg font-black text-white">
                Monthly Close & Client FP&A Review Checklist
              </h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          <div className="text-xs text-slate-500">
            Client Workspace: <span className="font-bold text-slate-900">{client.name}</span> • Period: {client.reportingPeriod}
          </div>

          <div className="space-y-3">
            {steps.map(step => {
              const isDone = completedSteps[step.num];
              const Icon = step.icon;
              return (
                <div
                  key={step.num}
                  className={`p-4 rounded-2xl border transition-all flex items-center justify-between gap-4 ${
                    isDone
                      ? 'bg-emerald-50/40 border-emerald-200'
                      : 'bg-white border-slate-200 hover:border-indigo-200'
                  }`}
                >
                  <div className="flex items-start gap-3.5">
                    <button
                      onClick={() => toggleStep(step.num)}
                      className="mt-0.5 text-emerald-600 hover:scale-110 transition-transform"
                    >
                      {isDone ? (
                        <CheckCircle2 className="w-5 h-5 fill-emerald-100 text-emerald-600" />
                      ) : (
                        <Circle className="w-5 h-5 text-slate-300" />
                      )}
                    </button>
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-bold ${isDone ? 'line-through text-slate-500' : 'text-slate-900'}`}>
                          Step {step.num}: {step.title}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 leading-relaxed">{step.desc}</p>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      if (step.tab) {
                        onNavigateToTab(step.tab);
                        onClose();
                      } else if (step.action) {
                        step.action();
                      }
                    }}
                    className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold shrink-0 transition-colors flex items-center gap-1"
                  >
                    <span>Open</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="bg-slate-50 px-6 py-4 border-t border-slate-200 flex items-center justify-between">
          <div className="text-xs text-slate-500">
            {Object.values(completedSteps).filter(Boolean).length} of 6 Steps Completed
          </div>
          <button
            onClick={onClose}
            className="px-5 py-2 bg-slate-900 text-white text-xs font-bold rounded-xl hover:bg-slate-800 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
