import React from 'react';
import { HelpCircle, BookOpen, SearchCheck, CheckCircle2, ArrowRight } from 'lucide-react';

interface ProgressIndicatorProps {
  currentStage: number; // 1: ASK, 2: RESEARCH, 3: VERIFY, 4: ACT
  hasReport: boolean;
}

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({ currentStage, hasReport }) => {
  const stages = [
    {
      num: 1,
      circleNum: '①',
      label: 'ASK',
      helper: 'Case & AI draft answer',
      icon: HelpCircle
    },
    {
      num: 2,
      circleNum: '②',
      label: 'RESEARCH',
      helper: 'Authoritative sources',
      icon: BookOpen
    },
    {
      num: 3,
      circleNum: '③',
      label: 'VERIFY',
      helper: 'Audit & missed issues',
      icon: SearchCheck
    },
    {
      num: 4,
      circleNum: '④',
      label: 'ACT',
      helper: 'Professional report',
      icon: CheckCircle2
    }
  ];

  return (
    <div className="w-full bg-white rounded-xl border border-slate-200 shadow-xs px-3 sm:px-5 py-2.5 transition-all">
      <div className="flex items-center justify-between overflow-x-auto gap-2 no-scrollbar">
        {stages.map((st, idx) => {
          const Icon = st.icon;
          const isActive = currentStage === st.num;
          const isCompleted = st.num < currentStage || (st.num === 4 && hasReport);

          return (
            <React.Fragment key={st.num}>
              <div className="flex items-center gap-2.5 shrink-0">
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold transition-colors ${
                    isCompleted
                      ? 'bg-emerald-600 text-white shadow-xs'
                      : isActive
                      ? 'bg-slate-900 text-white shadow-xs'
                      : 'bg-slate-100 text-slate-500 border border-slate-200'
                  }`}
                >
                  {isCompleted ? '✓' : st.num}
                </div>
                <div className="text-left">
                  <div className="flex items-center gap-1.5">
                    <Icon
                      className={`w-3.5 h-3.5 ${
                        isCompleted
                          ? 'text-emerald-600'
                          : isActive
                          ? 'text-slate-900'
                          : 'text-slate-400'
                      }`}
                    />
                    <span
                      className={`text-xs font-bold tracking-tight ${
                        isActive || isCompleted ? 'text-slate-900' : 'text-slate-400'
                      }`}
                    >
                      {st.circleNum} {st.label}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500 hidden md:block">
                    {st.helper}
                  </p>
                </div>
              </div>

              {idx < stages.length - 1 && (
                <div className="shrink-0 text-slate-300 px-1 sm:px-2">
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
