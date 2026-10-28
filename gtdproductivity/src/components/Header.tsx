import React from 'react';
import { Plus, Inbox, Layers, PlayCircle, Sparkles, CalendarCheck, CheckCheck } from 'lucide-react';

interface HeaderProps {
  activeView: 'inbox' | 'next_actions' | 'projects' | 'daily_review' | 'architecture';
  setActiveView: (view: 'inbox' | 'next_actions' | 'projects' | 'daily_review' | 'architecture') => void;
  inboxCount: number;
  isReviewedToday?: boolean;
  onOpenCapture: () => void;
  onStartClarify: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeView,
  setActiveView,
  inboxCount,
  isReviewedToday,
  onOpenCapture,
  onStartClarify,
}) => {
  return (
    <header className="flex items-center justify-between gap-8 px-6 py-4 border-b border-slate-200/90 bg-white/95 backdrop-blur-xs sticky top-0 z-40 shadow-xs">
      {/* Zone 1: Brand Wordmark with Teal & Blue Accent */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-teal-500 via-teal-600 to-blue-700 text-white flex items-center justify-center font-bold text-sm tracking-tight shadow-sm shadow-teal-500/30">
          GTD
        </div>
        <span className="text-lg font-bold tracking-tight text-slate-900 whitespace-nowrap">
          GTD<span className="text-teal-600">Productivity</span>
        </span>
      </div>

      {/* Zone 2: Navigation Links with Red, Blue & Teal Semantics */}
      <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600">
        {/* Inbox: Red / Coral Accent for unprocessed attention loops */}
        <button
          onClick={() => setActiveView('inbox')}
          className={`hover:text-slate-900 transition-colors whitespace-nowrap cursor-pointer flex items-center gap-2 py-1 ${
            activeView === 'inbox'
              ? 'text-rose-700 font-semibold border-b-2 border-rose-600'
              : 'hover:text-rose-700'
          }`}
        >
          <Inbox className={`w-4 h-4 ${activeView === 'inbox' ? 'text-rose-600' : 'text-slate-500'}`} />
          <span>Inbox</span>
          {inboxCount > 0 ? (
            <span className="text-[11px] font-mono font-bold text-white bg-rose-600 px-1.5 py-0.2 rounded-full shadow-2xs animate-pulse">
              {inboxCount}
            </span>
          ) : (
            <span className="text-[11px] font-mono text-slate-400 bg-slate-100 px-1.5 py-0.2 rounded">
              0
            </span>
          )}
        </button>

        {/* Next Actions: Energetic Teal Accent */}
        <button
          onClick={() => setActiveView('next_actions')}
          className={`hover:text-slate-900 transition-colors whitespace-nowrap cursor-pointer flex items-center gap-1.5 py-1 ${
            activeView === 'next_actions'
              ? 'text-teal-700 font-semibold border-b-2 border-teal-600'
              : 'hover:text-teal-700'
          }`}
        >
          <PlayCircle className={`w-4 h-4 ${activeView === 'next_actions' ? 'text-teal-600 fill-teal-50' : 'text-slate-500'}`} />
          <span>Next Actions</span>
        </button>

        {/* Projects: Deep Cobalt Blue Accent */}
        <button
          onClick={() => setActiveView('projects')}
          className={`hover:text-slate-900 transition-colors whitespace-nowrap cursor-pointer flex items-center gap-1.5 py-1 ${
            activeView === 'projects'
              ? 'text-blue-700 font-semibold border-b-2 border-blue-600'
              : 'hover:text-blue-700'
          }`}
        >
          <Layers className={`w-4 h-4 ${activeView === 'projects' ? 'text-blue-600' : 'text-slate-500'}`} />
          <span>Projects</span>
        </button>

        {/* Daily Review: Emerald / Indigo Focus */}
        <button
          onClick={() => setActiveView('daily_review')}
          className={`hover:text-slate-900 transition-colors whitespace-nowrap cursor-pointer flex items-center gap-1.5 py-1 ${
            activeView === 'daily_review'
              ? 'text-emerald-700 font-semibold border-b-2 border-emerald-600'
              : 'hover:text-emerald-700'
          }`}
        >
          <CalendarCheck className={`w-4 h-4 ${activeView === 'daily_review' ? 'text-emerald-600' : 'text-slate-500'}`} />
          <span>Daily Review</span>
          {isReviewedToday ? (
            <span className="w-2 h-2 rounded-full bg-emerald-500" title="Completed today" />
          ) : (
            <span className="text-[10px] font-mono font-bold bg-amber-100 text-amber-800 px-1 py-0.2 rounded" title="Pending daily calibration">
              Today
            </span>
          )}
        </button>

        {/* Architecture: Clean Slate */}
        <button
          onClick={() => setActiveView('architecture')}
          className={`hover:text-slate-900 transition-colors whitespace-nowrap cursor-pointer flex items-center gap-1.5 py-1 ${
            activeView === 'architecture'
              ? 'text-slate-900 font-semibold border-b-2 border-slate-900'
              : 'hover:text-slate-900'
          }`}
        >
          <span>Architecture & Specs</span>
        </button>
      </nav>

      {/* Zone 3: Primary Actions with Crisp Colors */}
      <div className="flex items-center gap-2.5 shrink-0">
        <button
          onClick={() => setActiveView('daily_review')}
          className={`px-3 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer hidden lg:flex items-center gap-1.5 ${
            activeView === 'daily_review'
              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200/80'
          }`}
        >
          <CalendarCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>Review</span>
        </button>

        {inboxCount > 0 && (
          <button
            onClick={onStartClarify}
            className="px-3.5 py-2 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200/80 rounded-lg transition-colors cursor-pointer hidden sm:flex items-center gap-1.5 shadow-2xs"
          >
            <span>Clarify ({inboxCount})</span>
          </button>
        )}
        <button
          onClick={onOpenCapture}
          className="px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-700 hover:to-teal-800 rounded-lg transition-all cursor-pointer flex items-center gap-1.5 shadow-sm shadow-teal-600/30 active:scale-98"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Quick Capture</span>
        </button>
      </div>
    </header>
  );
};
