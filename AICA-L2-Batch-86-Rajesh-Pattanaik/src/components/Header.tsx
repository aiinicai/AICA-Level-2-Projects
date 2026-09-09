import React from 'react';
import { ShieldCheck } from 'lucide-react';

interface HeaderProps {
  currentStage?: number;
  hasReport?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ currentStage = 1, hasReport = false }) => {
  return (
    <header className="bg-slate-900 text-white px-4 sm:px-8 py-3.5 sm:py-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-4 shadow-md sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-emerald-400 shrink-0">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              CA VerifyAI
            </h1>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-slate-800 text-emerald-400 border border-slate-700">
              AICA Level 2
            </span>
          </div>
          <p className="text-xs text-slate-300 font-medium">
            Don’t just check what AI said. Check what AI may have missed.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between sm:justify-end w-full sm:w-auto gap-4 sm:gap-6">
        {/* 4-Stage Workflow indicator in Header */}
        <div className="flex items-center space-x-1.5 sm:space-x-2 text-[10px] sm:text-[11px] font-bold uppercase tracking-widest">
          <span className={currentStage >= 1 ? 'text-emerald-400' : 'text-slate-500'}>
            ① Ask
          </span>
          <span className="text-slate-600">→</span>
          <span className={currentStage >= 2 ? 'text-emerald-400' : 'text-slate-500'}>
            ② Research
          </span>
          <span className="text-slate-600">→</span>
          <span className={currentStage >= 3 ? 'text-emerald-400' : 'text-slate-500'}>
            ③ Verify
          </span>
          <span className="text-slate-600">→</span>
          <span
            className={
              hasReport || currentStage >= 4
                ? 'text-white border-b-2 border-emerald-400 pb-0.5'
                : 'text-slate-500'
            }
          >
            ④ Act
          </span>
        </div>

        {/* Project & City Attribution */}
        <div className="hidden lg:block text-right text-[10px] text-slate-400 leading-tight">
          <p className="font-semibold text-slate-200">Developed by CA Rajesh Kumar Pattanaik</p>
          <p>Bhubaneswar, Odisha · AICA Level 2 Capstone</p>
        </div>
      </div>
    </header>
  );
};
