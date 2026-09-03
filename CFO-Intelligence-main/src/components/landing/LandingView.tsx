import React from 'react';
import {
  TrendingUp,
  ShieldCheck,
  Sparkles,
  BarChart3,
  Lock,
  ArrowRight,
  CheckCircle2,
  FileSpreadsheet,
  Layers,
  Scale,
  Award,
  Users,
} from 'lucide-react';
import { ClientProfile } from '../../types';

interface LandingViewProps {
  onEnterWorkspace: () => void;
  firmName?: string;
}

export const LandingView: React.FC<LandingViewProps> = ({
  onEnterWorkspace,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  return (
    <div className="min-h-screen bg-slate-900 text-white selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation */}
      <nav className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-linear-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white font-black shadow-lg shadow-indigo-500/20">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <span className="text-lg font-black tracking-tight text-white block leading-tight">
                CFO Intelligence
              </span>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                {firmName}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={onEnterWorkspace}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-2"
            >
              <span>Launch CFO Workspace</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-16 pb-24 lg:pt-24 lg:pb-32">
        <div className="max-w-7xl mx-auto px-6 relative z-10 text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-bold tracking-wide">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span>Deterministic FP&A + Zero-Knowledge Privacy Shield</span>
          </div>

          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-black tracking-tight text-white max-w-4xl mx-auto leading-tight">
            Virtual CFO & FP&A Intelligence Platform
          </h1>

          <p className="text-base sm:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed font-medium">
            Transform raw general ledgers and trial balances into board-ready CFO advisory packs, 12-month rolling forecasts, what-if sensitivity models, and automated variance audits.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <button
              onClick={onEnterWorkspace}
              className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold shadow-xl shadow-indigo-600/40 transition-all flex items-center justify-center gap-2"
            >
              <span>Open Advisory Workspace</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          <div className="pt-8 text-xs text-slate-500 flex items-center justify-center gap-6">
            <span className="flex items-center gap-1.5"><ShieldCheck className="w-4 h-4 text-emerald-400" /> Zero-Hallucination Deterministic Math</span>
            <span className="flex items-center gap-1.5"><Lock className="w-4 h-4 text-emerald-400" /> Client PII Redaction Layer</span>
            <span className="flex items-center gap-1.5"><Award className="w-4 h-4 text-indigo-400" /> Curated by {firmName}</span>
          </div>
        </div>
      </section>

      {/* Feature Pillar Highlights */}
      <section className="py-20 bg-slate-950/60 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-6 space-y-12">
          <div className="text-center space-y-2">
            <h2 className="text-2xl sm:text-3xl font-black text-white">
              End-to-End FP&A Operating Architecture
            </h2>
            <p className="text-xs sm:text-sm text-slate-400">
              Engineered specifically for accounting firms and finance executives
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-slate-900/90 p-8 rounded-3xl border border-slate-800 space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center">
                <BarChart3 className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Deterministic Financial Model</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Calculates Gross Margin, EBITDA, Cash Conversion Cycle (DSO/DIO/DPO), Fixed vs Variable costs, and Break-even points mathematically in pure TypeScript.
              </p>
            </div>

            <div className="bg-slate-900/90 p-8 rounded-3xl border border-slate-800 space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-emerald-600/20 text-emerald-400 flex items-center justify-center">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Client Privacy Shield</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Redacts all sensitive client names, legal entities, tax IDs, and bank wires with deterministic tokens before AI synthesis. No raw client metadata is ever sent to LLMs.
              </p>
            </div>

            <div className="bg-slate-900/90 p-8 rounded-3xl border border-slate-800 space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-violet-600/20 text-violet-400 flex items-center justify-center">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white">Board-Ready Report Packs</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                One-click export of multi-sheet Excel workbooks and print-optimized PDF board packs branded with Jasleen Daswal & Associates headers and footers.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-10 bg-slate-950 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-6 space-y-2">
          <p className="font-semibold text-slate-400">
            CFO Intelligence • Curated by {firmName}
          </p>
          <p>© 2026 Jasleen Daswal & Associates. All rights reserved. Confidential & Proprietary.</p>
        </div>
      </footer>
    </div>
  );
};
