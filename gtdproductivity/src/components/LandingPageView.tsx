import React from 'react';
import {
  Award,
  CheckCircle2,
  Layers,
  Inbox,
  PlayCircle,
  CalendarCheck,
  ShieldCheck,
  ArrowRight,
  Database,
  Tag,
  Clock,
  Sparkles,
  FileCheck2,
  UserCheck,
  BookOpen,
  Briefcase,
  ChevronRight,
  ExternalLink
} from 'lucide-react';
import { UserSession } from '../types/auth';

interface LandingPageViewProps {
  onEnterWorkspace: (initialView?: 'inbox' | 'next_actions' | 'projects' | 'daily_review' | 'architecture') => void;
  onOpenJuryCheck: () => void;
  onOpenLogin: () => void;
  currentUser: UserSession;
}

export const LandingPageView: React.FC<LandingPageViewProps> = ({
  onEnterWorkspace,
  onOpenJuryCheck,
  onOpenLogin,
  currentUser,
}) => {
  return (
    <div className="space-y-16 py-4">
      {/* 1. Official Capstone Assessment Banner */}
      <section className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-2xl p-6 sm:p-8 shadow-xl border border-indigo-800/40 relative overflow-hidden">
        {/* Subtle decorative background watermark */}
        <div className="absolute -right-12 -top-12 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute right-1/4 -bottom-12 w-80 h-80 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-3 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-full text-xs font-semibold tracking-wide uppercase">
              <Award className="w-3.5 h-3.5 text-amber-400" />
              <span>Capstone Project · Jury Assessment Ready</span>
            </div>
            
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white leading-tight">
              Enterprise GTD Productivity & Workflow Engine
            </h1>
            
            <div className="flex flex-wrap items-center gap-y-2 gap-x-4 text-xs sm:text-sm text-slate-300">
              <div className="flex items-center gap-1.5 font-medium text-slate-200">
                <span className="text-teal-400 font-semibold">Author:</span>
                <span className="font-bold text-white tracking-wide">CA Prashant Nathvani</span>
              </div>
              <span className="text-slate-600 hidden sm:inline">•</span>
              <div className="flex items-center gap-1.5 font-mono text-amber-300 bg-amber-950/60 px-2.5 py-0.5 rounded border border-amber-500/30">
                <span>ICAI Membership No:</span>
                <span className="font-bold">177366</span>
              </div>
              <span className="text-slate-600 hidden sm:inline">•</span>
              <div className="flex items-center gap-1 text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>Defense & Rubric Evaluation Ready</span>
              </div>
            </div>

            <p className="text-slate-300 text-sm sm:text-base leading-relaxed pt-1">
              A high-integrity personal & enterprise task manager engineered on David Allen’s <em>Getting Things Done®</em> methodology 
              and OmniFocus availability DAG mathematics. Built specifically to eliminate cognitive leaks in high-stakes auditing, taxation, 
              and executive management workflows.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row lg:flex-col gap-3 w-full lg:w-auto shrink-0">
            <button
              onClick={onOpenJuryCheck}
              className="px-5 py-3 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold rounded-xl transition-all shadow-lg shadow-amber-500/25 flex items-center justify-center gap-2 cursor-pointer group text-sm"
            >
              <Award className="w-4 h-4 group-hover:scale-110 transition-transform" />
              <span>Open Jury Assessment Suite</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>

            <button
              onClick={() => onEnterWorkspace('inbox')}
              className="px-5 py-3 bg-white/10 hover:bg-white/15 text-white font-semibold rounded-xl border border-white/20 transition-all flex items-center justify-center gap-2 cursor-pointer text-sm"
            >
              <span>Launch Live Workspace</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </section>

      {/* 2. Candidate Credential & Capstone Dossier Card */}
      <section className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-slate-100">
          <div>
            <div className="text-xs font-bold text-teal-600 uppercase tracking-wider mb-1">
              Official Candidate Verification
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-slate-900">
              CA Prashant Nathvani · Membership # 177366
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              The Institute of Chartered Accountants of India (ICAI) · Capstone Evaluation Module
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <span className="px-3 py-1 bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg border border-slate-200 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
              Deterministic Availability DAG
            </span>
            <span className="px-3 py-1 bg-teal-50 text-teal-800 text-xs font-semibold rounded-lg border border-teal-200 flex items-center gap-1.5">
              <Tag className="w-3.5 h-3.5 text-teal-600" />
              Context Filtering Engine
            </span>
            <span className="px-3 py-1 bg-emerald-50 text-emerald-800 text-xs font-semibold rounded-lg border border-emerald-200 flex items-center gap-1.5">
              <CalendarCheck className="w-3.5 h-3.5 text-emerald-600" />
              Daily Review & Calibration
            </span>
          </div>
        </div>

        {/* Executive summary grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70">
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">The Professional Problem</div>
            <p className="text-xs sm:text-sm text-slate-700 mt-2 leading-relaxed">
              Chartered Accountants manage concurrent statutory audits, tax filings, and client advisory. Standard to-do lists fail because they lack <strong>dependency ordering</strong>, <strong>context grouping</strong> (@office, @phone), and <strong>clear delegation tracking</strong>.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70">
            <div className="text-xs font-bold text-teal-700 uppercase tracking-wider">The Engineered Solution</div>
            <p className="text-xs sm:text-sm text-slate-700 mt-2 leading-relaxed">
              A mathematical task engine that cleanly differentiates between <strong>Sequential Projects</strong> (where action n+1 is blocked until n finishes) and <strong>Parallel Projects</strong>, with full <strong>Daily Inbox Zero calibration</strong> and <strong>Waiting-For accountability</strong>.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70">
            <div className="text-xs font-bold text-indigo-700 uppercase tracking-wider">Jury Evaluation Readiness</div>
            <p className="text-xs sm:text-sm text-slate-700 mt-2 leading-relaxed">
              Includes an interactive <strong>Jury Scoring Rubric</strong>, pre-configured test scenarios, database schema DDL with normalized relational indexes, and live state transitions for immediate hands-on verification.
            </p>
          </div>
        </div>
      </section>

      {/* 3. Core Functional Modules - Interactive Showcase */}
      <section className="space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Designed for Cognitive Integrity & Frictionless Execution
          </h2>
          <p className="text-sm text-slate-600">
            Every feature is rigorously grounded in the five pillars of GTD and hardened with enterprise ergonomics.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Module 1: Inbox Zero & Clarify */}
          <div 
            onClick={() => onEnterWorkspace('inbox')}
            className="group p-6 rounded-2xl bg-white border border-slate-200 hover:border-rose-300 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                <Inbox className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-base group-hover:text-rose-600 transition-colors">
                1. Universal Capture & Clarify
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Instant idea capture with global keyboard shortcuts (<kbd className="px-1 bg-slate-100 rounded text-[10px] font-mono">c</kbd>). 6-way clarification wizard adhering strictly to the 2-minute rule.
              </p>
            </div>
            <div className="pt-4 mt-2 flex items-center text-xs font-semibold text-rose-600 group-hover:translate-x-1 transition-transform">
              <span>Test Inbox Processing</span>
              <ChevronRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>

          {/* Module 2: Next Actions & Contexts */}
          <div 
            onClick={() => onEnterWorkspace('next_actions')}
            className="group p-6 rounded-2xl bg-white border border-slate-200 hover:border-teal-300 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                <PlayCircle className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-base group-hover:text-teal-600 transition-colors">
                2. Contexts & Due Deadlines
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Filter next actions by energy and location context: <span className="font-mono text-teal-700">@office</span>, <span className="font-mono text-teal-700">@phone</span>, <span className="font-mono text-teal-700">@computer</span>. Real-time overdue badges and flags.
              </p>
            </div>
            <div className="pt-4 mt-2 flex items-center text-xs font-semibold text-teal-600 group-hover:translate-x-1 transition-transform">
              <span>Explore Context Filters</span>
              <ChevronRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>

          {/* Module 3: Sequential & Parallel Projects */}
          <div 
            onClick={() => onEnterWorkspace('projects')}
            className="group p-6 rounded-2xl bg-white border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                <Layers className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-base group-hover:text-blue-600 transition-colors">
                3. Sequential / Parallel Engine
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Mathematically resolves task availability. Sequential projects hide downstream actions from the next actions list until the prerequisite task completes.
              </p>
            </div>
            <div className="pt-4 mt-2 flex items-center text-xs font-semibold text-blue-600 group-hover:translate-x-1 transition-transform">
              <span>Inspect Project DAG</span>
              <ChevronRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>

          {/* Module 4: Daily Review & Calibration */}
          <div 
            onClick={() => onEnterWorkspace('daily_review')}
            className="group p-6 rounded-2xl bg-white border border-slate-200 hover:border-emerald-300 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                <CalendarCheck className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-slate-900 text-base group-hover:text-emerald-600 transition-colors">
                4. Daily Review & Calibration
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Guided 3-step ritual: clear inbox with checklist, audit delegated & waiting-for items with follow-up logs, and incubate Someday/Maybe ideas.
              </p>
            </div>
            <div className="pt-4 mt-2 flex items-center text-xs font-semibold text-emerald-600 group-hover:translate-x-1 transition-transform">
              <span>Run Daily Review</span>
              <ChevronRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>
        </div>
      </section>

      {/* 4. CA Practice Use-Cases / Real-World Scenarios */}
      <section className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white rounded-2xl p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-700/60">
          <div>
            <span className="text-xs font-bold text-teal-400 uppercase tracking-wider">Applied Domain Engineering</span>
            <h3 className="text-xl sm:text-2xl font-bold text-white mt-1">
              Field Applications in Chartered Accountancy & Advisory
            </h3>
          </div>
          <div className="text-xs font-mono text-slate-400">
            Validated for ICAI Professional Standards
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
          <div className="p-5 rounded-xl bg-slate-800/80 border border-slate-700 space-y-3">
            <div className="flex items-center gap-2 text-teal-400 font-semibold text-sm">
              <Briefcase className="w-4 h-4" />
              <span>Statutory Audit Management</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Managing complex multi-step audit programs: <em>Trial Balance analysis → Sample vouching → Substantive procedures → Management representation letter</em>. Sequential dependency ensures workpapers are reviewed in strict order.
            </p>
            <div className="text-[11px] font-mono text-teal-300 bg-teal-950/60 px-2 py-1 rounded inline-block">
              Project Type: Sequential DAG
            </div>
          </div>

          <div className="p-5 rounded-xl bg-slate-800/80 border border-slate-700 space-y-3">
            <div className="flex items-center gap-2 text-blue-400 font-semibold text-sm">
              <Clock className="w-4 h-4" />
              <span>Direct Tax & Litigation Appeals</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Tracking non-negotiable statutory due dates (ITR filings, CIT(A) submissions). Context tags like <span className="text-amber-300 font-mono">@office</span> for paper documentation and <span className="text-teal-300 font-mono">@phone</span> for client consultations prevent missed deadlines.
            </p>
            <div className="text-[11px] font-mono text-blue-300 bg-blue-950/60 px-2 py-1 rounded inline-block">
              Feature: Context + Due Date Alerts
            </div>
          </div>

          <div className="p-5 rounded-xl bg-slate-800/80 border border-slate-700 space-y-3">
            <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
              <UserCheck className="w-4 h-4" />
              <span>Partner & Articled Assistant Delegation</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Every delegated inquiry to junior associates or bank confirmation requests is parked in <strong>Waiting For</strong> with assigned person names and follow-up history, reviewed daily to maintain zero communication drag.
            </p>
            <div className="text-[11px] font-mono text-amber-300 bg-amber-950/60 px-2 py-1 rounded inline-block">
              Workflow: Waiting-For Calibration
            </div>
          </div>
        </div>
      </section>

      {/* 5. Jury Quick-Access Callout */}
      <section className="bg-amber-50 rounded-2xl p-6 sm:p-8 border border-amber-200/90 shadow-xs flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-900 bg-amber-100 px-2.5 py-0.5 rounded-full">
            <Award className="w-3.5 h-3.5 text-amber-700" />
            <span>Honorable Jury Members & Assessors</span>
          </div>
          <h3 className="text-xl sm:text-2xl font-bold text-amber-950">
            Interactive Scoring Rubric & System Inspection Available
          </h3>
          <p className="text-xs sm:text-sm text-amber-900/80 leading-relaxed">
            Click into the dedicated <strong>Jury Assessment</strong> tab on the top navigation bar to evaluate the 5 technical dimensions, test live features with pre-seeded data, inspect the database architecture, and record your assessment notes.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 shrink-0 w-full md:w-auto">
          <button
            onClick={onOpenJuryCheck}
            className="px-6 py-3 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-xl text-sm transition-all shadow-md shadow-amber-600/20 cursor-pointer flex items-center justify-center gap-2"
          >
            <Award className="w-4 h-4" />
            <span>Open Jury Assessment</span>
          </button>
          <button
            onClick={onOpenLogin}
            className="px-5 py-3 bg-white hover:bg-amber-100/60 text-amber-900 font-semibold border border-amber-300 rounded-xl text-sm transition-all cursor-pointer flex items-center justify-center gap-2"
          >
            <span>Login as Jury Assessor</span>
          </button>
        </div>
      </section>

      {/* 6. Technical Specifications Summary */}
      <section className="border-t border-slate-200 pt-8 pb-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div>
            <strong>Capstone Project</strong> · CA Prashant Nathvani (ICAI Membership No: 177366)
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => onEnterWorkspace('architecture')}
              className="text-teal-700 hover:text-teal-900 font-semibold flex items-center gap-1 cursor-pointer"
            >
              <Database className="w-3.5 h-3.5" />
              <span>View SQL Schema & 10 ADRs</span>
            </button>
            <span>•</span>
            <span>Tailwind v4 & React 19 Engine</span>
          </div>
        </div>
      </section>
    </div>
  );
};
