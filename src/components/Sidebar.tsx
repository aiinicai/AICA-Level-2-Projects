import React from 'react';
import {
  LayoutDashboard,
  CheckCircle2,
  Circle,
  FileCheck,
  Building,
  ShieldAlert,
  Server,
  Workflow,
  Footprints,
  TableProperties,
  Scale,
  SlidersHorizontal,
  Compass,
  FileSignature,
  FileText,
  FileSpreadsheet,
} from 'lucide-react';
import { StageProgress } from '../types';

interface SidebarProps {
  activeStage: number; // 0 for Overview, -1 for Trial Balance, 1-13 for Stages
  onSelectStage: (stage: number) => void;
  stagesProgress: StageProgress[];
  tbItemCount?: number;
}

const STAGE_ICONS: Record<number, React.FC<{ className?: string }>> = {
  1: FileCheck,
  2: Building,
  3: ShieldAlert,
  4: Server,
  5: Workflow,
  6: Footprints,
  7: TableProperties,
  8: ShieldAlert,
  9: SlidersHorizontal,
  10: Scale,
  11: Compass,
  12: FileText,
  13: FileSignature,
};

export const Sidebar: React.FC<SidebarProps> = ({
  activeStage,
  onSelectStage,
  stagesProgress,
  tbItemCount,
}) => {
  return (
    <aside className="w-full md:w-72 lg:w-80 shrink-0 bg-[#f4f2eb] dark:bg-[#12161b] border-r border-[#dedbd2] dark:border-[#272f38] flex flex-col h-[calc(100vh-57px)] sticky top-[57px] overflow-hidden">
      {/* Sidebar Header */}
      <div className="p-3.5 border-b border-[#dedbd2] dark:border-[#272f38]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-amber-800 dark:bg-amber-600 flex items-center justify-center text-white font-serif font-bold text-xs">
              W
            </div>
            <div>
              <h2 className="font-serif font-bold text-sm text-stone-900 dark:text-stone-100 tracking-tight">
                Audit Planning
              </h2>
              <p className="text-[10px] text-stone-500 dark:text-stone-400 uppercase tracking-widest font-semibold">
                ICAI Workpapers
              </p>
            </div>
          </div>
          <span className="text-[11px] font-mono-num font-medium text-stone-600 dark:text-stone-300 bg-stone-200 dark:bg-stone-800 px-2 py-0.5 rounded">
            13 Stages
          </span>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 overflow-y-auto p-2 space-y-0.5 text-xs">
        {/* Overview Tab */}
        <button
          onClick={() => onSelectStage(0)}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-md transition-all text-left ${
            activeStage === 0
              ? 'bg-amber-800 text-white font-medium shadow-xs dark:bg-amber-700'
              : 'text-stone-700 dark:text-stone-300 hover:bg-stone-200/70 dark:hover:bg-stone-800/60'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <LayoutDashboard className="w-4 h-4 shrink-0" />
            <div>
              <span className="text-xs font-semibold block">Planning Overview</span>
              <span className={`text-[10px] block ${activeStage === 0 ? 'text-amber-200' : 'text-stone-400'}`}>
                Dashboard & Key Indicators
              </span>
            </div>
          </div>
        </button>

        {/* Trial Balance Tab */}
        <button
          onClick={() => onSelectStage(-1)}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-md transition-all text-left ${
            activeStage === -1
              ? 'bg-amber-800 text-white font-medium shadow-xs dark:bg-amber-700'
              : 'text-stone-700 dark:text-stone-300 hover:bg-stone-200/70 dark:hover:bg-stone-800/60'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <FileSpreadsheet className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold block">Trial Balance (TB)</span>
                {tbItemCount !== undefined && tbItemCount > 0 ? (
                  <span className="text-[9px] font-mono px-1 rounded bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 font-bold">
                    {tbItemCount}
                  </span>
                ) : (
                  <span className="text-[9px] font-sans px-1 rounded bg-stone-200 dark:bg-stone-800 text-stone-500 font-medium">
                    Import
                  </span>
                )}
              </div>
              <span className={`text-[10px] block ${activeStage === -1 ? 'text-amber-200' : 'text-stone-400'}`}>
                Schedule III & Baseline
              </span>
            </div>
          </div>
        </button>

        <div className="pt-2 pb-1 px-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-stone-400 dark:text-stone-500">
            Workpaper Stages
          </p>
        </div>

        {stagesProgress.map((sp) => {
          const StageIcon = STAGE_ICONS[sp.stageNumber] || FileText;
          const isActive = activeStage === sp.stageNumber;
          const isComplete = sp.percent === 100;
          const hasStarted = sp.percent > 0;

          return (
            <button
              key={sp.stageNumber}
              onClick={() => onSelectStage(sp.stageNumber)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-md transition-all text-left group ${
                isActive
                  ? 'bg-stone-900 text-white font-medium shadow-xs dark:bg-stone-100 dark:text-stone-900'
                  : 'text-stone-700 dark:text-stone-300 hover:bg-stone-200/70 dark:hover:bg-stone-800/60'
              }`}
            >
              <div className="flex items-start gap-2.5 min-w-0 pr-1">
                <span
                  className={`font-mono-num text-[11px] font-bold px-1.5 py-0.5 rounded shrink-0 ${
                    isActive
                      ? 'bg-stone-800 text-amber-300 dark:bg-stone-200 dark:text-amber-800'
                      : 'bg-stone-200/80 text-stone-600 dark:bg-stone-800 dark:text-stone-400 group-hover:text-stone-900 dark:group-hover:text-stone-100'
                  }`}
                >
                  {String(sp.stageNumber).padStart(2, '0')}
                </span>

                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate font-medium text-xs">
                      {sp.shortTitle}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] truncate block ${
                      isActive
                        ? 'text-stone-300 dark:text-stone-600'
                        : 'text-stone-400 dark:text-stone-500'
                    }`}
                  >
                    {sp.saRef}
                  </span>
                </div>
              </div>

              {/* Progress Count / Status */}
              <div className="shrink-0 flex items-center gap-1.5 pl-1">
                <span
                  className={`font-mono-num text-[10px] ${
                    isActive
                      ? 'text-stone-300 dark:text-stone-600 font-semibold'
                      : 'text-stone-400 dark:text-stone-500'
                  }`}
                >
                  {sp.doneCount}/{sp.totalCount}
                </span>
                {isComplete ? (
                  <CheckCircle2 className={`w-3.5 h-3.5 ${isActive ? 'text-emerald-400 dark:text-emerald-600' : 'text-emerald-600 dark:text-emerald-400'}`} />
                ) : hasStarted ? (
                  <div className="w-3.5 h-3.5 rounded-full border border-amber-500 flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                  </div>
                ) : (
                  <Circle className="w-3.5 h-3.5 text-stone-300 dark:text-stone-600" />
                )}
              </div>
            </button>
          );
        })}
      </nav>

      {/* Sidebar Footer Reference */}
      <div className="p-3 border-t border-[#dedbd2] dark:border-[#272f38] bg-[#ebe7dc] dark:bg-[#0e1216] text-[11px] text-stone-500 dark:text-stone-400">
        <p className="font-semibold text-stone-700 dark:text-stone-300">
          Standards on Auditing (ICAI)
        </p>
        <p className="text-[10px] mt-0.5 leading-snug">
          SA 315 (Rev.), SA 240, SA 330, SA 320, SA 450, SQC 1
        </p>
      </div>
    </aside>
  );
};
