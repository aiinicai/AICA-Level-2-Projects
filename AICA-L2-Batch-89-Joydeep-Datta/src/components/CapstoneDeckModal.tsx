import React, { useState } from 'react';
import {
  X,
  Download,
  ChevronLeft,
  ChevronRight,
  Presentation,
  CheckCircle2,
  ShieldCheck,
  Cpu,
  FileCode,
  Sparkles,
  Layers,
  Award,
  AlertTriangle,
  User,
  Mail,
  Calendar,
  Loader2,
  ExternalLink,
  BookOpen,
  FileText,
} from 'lucide-react';
import { generateCapstonePptx, CapstoneDeckMetadata, defaultDeckMetadata } from '../utils/generatePptxDeck';
import { CapstoneReportArtifact } from './CapstoneReportArtifact';

interface CapstoneDeckModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CapstoneDeckModal: React.FC<CapstoneDeckModalProps> = ({ isOpen, onClose }) => {
  const [viewMode, setViewMode] = useState<'report' | 'deck'>('report');
  const [currentSlide, setCurrentSlide] = useState(1);
  const [isGenerating, setIsGenerating] = useState(false);
  const [metadata, setMetadata] = useState<CapstoneDeckMetadata>(defaultDeckMetadata);
  const [showMetadataEdit, setShowMetadataEdit] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  if (!isOpen) return null;

  const totalSlides = 10;

  const handleDownload = async () => {
    try {
      setIsGenerating(true);
      setDownloadSuccess(false);
      await generateCapstonePptx(metadata);
      setDownloadSuccess(true);
      setTimeout(() => setDownloadSuccess(false), 4000);
    } catch (err) {
      console.error('Failed to generate PPTX:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  const nextSlide = () => {
    if (currentSlide < totalSlides) setCurrentSlide(currentSlide + 1);
  };

  const prevSlide = () => {
    if (currentSlide > 1) setCurrentSlide(currentSlide - 1);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700 w-full max-w-6xl h-[92vh] max-h-[850px] rounded-2xl shadow-2xl flex flex-col overflow-hidden text-slate-100">
        {/* Top Control Bar */}
        <div className="bg-slate-950 border-b border-slate-800 px-4 py-3 flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md shrink-0">
              <Presentation className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm sm:text-base font-bold text-white tracking-tight">
                  Capstone Project Artifact & Presentation
                </h2>
                <span className="px-2 py-0.5 text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-md">
                  AY 2026–27
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Full Technical Report Specification & 10-Slide Downloadable PowerPoint (.pptx)
              </p>
            </div>
          </div>

          {/* View Mode Toggle Pill */}
          <div className="flex items-center bg-slate-900 border border-slate-700 rounded-xl p-1">
            <button
              type="button"
              onClick={() => setViewMode('report')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                viewMode === 'report'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileText className="h-3.5 w-3.5" />
              <span>Project Report Artifact</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('deck')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                viewMode === 'deck'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Presentation className="h-3.5 w-3.5" />
              <span>10-Slide Deck (16:9)</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowMetadataEdit(!showMetadataEdit)}
              className="text-xs px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 rounded-lg transition-colors cursor-pointer"
            >
              {showMetadataEdit ? 'Hide Author' : 'Edit Author'}
            </button>

            <button
              type="button"
              onClick={handleDownload}
              disabled={isGenerating}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg text-xs font-bold transition-all shadow-md cursor-pointer disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Building .pptx...</span>
                </>
              ) : downloadSuccess ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-white" />
                  <span>Downloaded!</span>
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  <span>Download PowerPoint (.pptx)</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Optional Metadata Editor Drawer */}
        {showMetadataEdit && (
          <div className="bg-slate-900/90 border-b border-slate-800 p-3 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs animate-in slide-in-from-top-2">
            <div>
              <label className="text-[11px] text-slate-400 font-medium">Candidate Name</label>
              <div className="flex items-center gap-1.5 mt-1 bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5">
                <User className="h-3.5 w-3.5 text-slate-500" />
                <input
                  type="text"
                  value={metadata.studentName}
                  onChange={(e) => setMetadata({ ...metadata, studentName: e.target.value })}
                  className="bg-transparent text-white outline-none w-full text-xs"
                />
              </div>
            </div>
            <div>
              <label className="text-[11px] text-slate-400 font-medium">Email Address</label>
              <div className="flex items-center gap-1.5 mt-1 bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5">
                <Mail className="h-3.5 w-3.5 text-slate-500" />
                <input
                  type="text"
                  value={metadata.studentEmail}
                  onChange={(e) => setMetadata({ ...metadata, studentEmail: e.target.value })}
                  className="bg-transparent text-white outline-none w-full text-xs"
                />
              </div>
            </div>
            <div>
              <label className="text-[11px] text-slate-400 font-medium">Submission Date</label>
              <div className="flex items-center gap-1.5 mt-1 bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5">
                <Calendar className="h-3.5 w-3.5 text-slate-500" />
                <input
                  type="text"
                  value={metadata.submissionDate}
                  onChange={(e) => setMetadata({ ...metadata, submissionDate: e.target.value })}
                  className="bg-transparent text-white outline-none w-full text-xs"
                />
              </div>
            </div>
          </div>
        )}

        {/* Content Body: Either Full Report Artifact or 10-Slide Viewer */}
        {viewMode === 'report' ? (
          <div className="flex-1 overflow-hidden flex flex-col">
            <CapstoneReportArtifact metadata={metadata} />
          </div>
        ) : (
          <>
            {/* Slide Viewer Stage (16:9 Canvas Aspect Ratio) */}
            <div className="flex-1 bg-slate-950 p-4 sm:p-6 overflow-y-auto flex items-center justify-center">
              <div className="w-full max-w-4xl aspect-[16/9] bg-white rounded-xl shadow-2xl border border-slate-700 overflow-hidden flex flex-col text-slate-900 relative">
                {/* Slide Header (Except Slide 1 & 10) */}
                {currentSlide !== 1 && currentSlide !== 10 && (
                  <div className="bg-slate-900 px-6 py-3 flex items-center justify-between border-b border-indigo-900/30">
                    <div>
                      <span className="text-[10px] font-bold text-indigo-400 tracking-wider uppercase block">
                        {getSlideCategory(currentSlide)}
                      </span>
                      <h3 className="text-base sm:text-lg font-bold text-white leading-tight">
                        {getSlideTitle(currentSlide)}
                      </h3>
                    </div>
                    <span className="text-xs font-mono font-bold text-slate-400 bg-slate-800/80 px-2 py-1 rounded">
                      {currentSlide} / {totalSlides}
                    </span>
                  </div>
                )}

                {/* Slide Body Content */}
                <div className="flex-1 p-5 sm:p-6 overflow-y-auto">
                  {renderSlideContent(currentSlide, metadata)}
                </div>

                {/* Slide Footer */}
                <div className="bg-slate-100 px-6 py-2 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500">
                  <span className="truncate">
                    Capstone Submission | {metadata.projectName} | {metadata.studentName}
                  </span>
                  <span className="shrink-0 font-medium">AY 2026–27 Statutory Compliance</span>
                </div>
              </div>
            </div>

            {/* Bottom Navigation & Speaker Notes */}
            <div className="bg-slate-950 border-t border-slate-800 p-3 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3 shrink-0">
              {/* Thumbnails / Pills */}
              <div className="flex items-center gap-1.5 overflow-x-auto max-w-full pb-1 sm:pb-0">
                {Array.from({ length: totalSlides }).map((_, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setCurrentSlide(i + 1)}
                    className={`h-7 px-2.5 rounded-lg text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
                      currentSlide === i + 1
                        ? 'bg-indigo-600 text-white shadow-xs'
                        : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                    }`}
                  >
                    {i + 1}
                  </button>
                ))}
              </div>

              {/* Slide Switchers */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400 font-mono">
                  Slide {currentSlide} of {totalSlides}
                </span>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={prevSlide}
                    disabled={currentSlide === 1}
                    className="p-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-lg transition-colors cursor-pointer"
                    title="Previous slide"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={nextSlide}
                    disabled={currentSlide === totalSlides}
                    className="p-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-lg transition-colors cursor-pointer"
                    title="Next slide"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

function getSlideCategory(slide: number): string {
  switch (slide) {
    case 2:
      return '1. Context & Objectives';
    case 3:
      return '2. System Engineering';
    case 4:
      return '3. What Has Been Done';
    case 5:
      return '4. Core Logic & Precision';
    case 6:
      return '5. AI Advisory';
    case 7:
      return '6. Methodology';
    case 8:
      return '7. Security Review';
    case 9:
      return '8. Enterprise Readiness';
    default:
      return '';
  }
}

function getSlideTitle(slide: number): string {
  switch (slide) {
    case 2:
      return 'Problem Statement: The Indian Payroll & Tax Dilemma';
    case 3:
      return 'System Architecture & Full-Stack Tech Stack';
    case 4:
      return 'Core Application Modules & Feature Deliverables';
    case 5:
      return 'Deep Dive: Deterministic Statutory Indian Tax Engine';
    case 6:
      return 'Google Gemini AI Integration & Circuit-Breaker Architecture';
    case 7:
      return 'Vibe Coding Methodology: From Idea to Enterprise Prototype';
    case 8:
      return 'Data Security, Confidentiality & Privacy Architecture';
    case 9:
      return 'Production Readiness Checklist & Deployment Roadmap';
    default:
      return '';
  }
}

function renderSlideContent(slide: number, metadata: CapstoneDeckMetadata) {
  switch (slide) {
    case 1:
      return (
        <div className="h-full flex flex-col justify-between bg-slate-900 text-white -m-5 sm:-m-6 p-6 sm:p-8">
          <div>
            <span className="inline-block px-3 py-1 bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-full text-xs font-bold uppercase tracking-wider mb-4">
              Capstone Submission
            </span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-tight">
              Next-Gen Indian Statutory Payroll & AI Tax Advisory System
            </h1>
            <p className="mt-2 text-sm sm:text-base text-slate-300 max-w-2xl">
              An enterprise-grade, deterministic dual-regime payroll engine paired with a multi-model Google Gemini tax
              copilot built using Vibe Coding methodology.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 bg-slate-800/80 border border-slate-700/80 rounded-xl p-4 text-xs">
            <div>
              <p className="text-indigo-400 font-bold uppercase text-[10px]">Author / Candidate</p>
              <p className="text-sm font-bold text-white mt-0.5">{metadata.studentName}</p>
              <p className="text-slate-400 font-mono text-[11px]">{metadata.studentEmail}</p>
              <p className="text-slate-300 mt-2 font-medium">Full-Stack Vibe Coding & LLM Systems</p>
            </div>
            <div>
              <p className="text-indigo-400 font-bold uppercase text-[10px]">Statutory & Tech Scope</p>
              <p className="text-sm font-bold text-white mt-0.5">AY 2026–27 Statutory Compliance</p>
              <p className="text-emerald-400 font-medium text-[11px] mt-0.5">
                React 19 + TypeScript + Express + @google/genai SDK
              </p>
              <p className="text-slate-400 mt-2 text-[11px]">Submission Date: {metadata.submissionDate}</p>
            </div>
          </div>
        </div>
      );

    case 2:
      return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs h-full">
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex flex-col">
            <h4 className="font-bold text-indigo-700 text-sm mb-2">Statutory Maze</h4>
            <ul className="space-y-2 text-slate-600">
              <li>
                <strong className="text-slate-800">Dual Tax Regimes:</strong> Employees must choose Old vs New Regime
                for AY 2026-27, each with separate tax slabs, standard deductions, and 87A rebate rules.
              </li>
              <li>
                <strong className="text-slate-800">Statutory Deductions:</strong> EPF 12% with ₹15k wage ceiling lock;
                ESI at gross ≤ ₹21,000; State-specific Professional Tax (PT).
              </li>
              <li>
                <strong className="text-slate-800">HRA Exemption:</strong> Section 10(13A) evaluates the minimum of 3
                dynamic conditions across metro and non-metro cities.
              </li>
            </ul>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex flex-col">
            <h4 className="font-bold text-rose-700 text-sm mb-2">Employee Pain Points</h4>
            <ul className="space-y-2 text-slate-600">
              <li>
                <strong className="text-slate-800">Regret of Wrong Choice:</strong> Locking the wrong regime upfront
                leads to tens of thousands of rupees lost in excess TDS.
              </li>
              <li>
                <strong className="text-slate-800">Last-Minute Scramble:</strong> Employees panic in Q4 trying to submit
                Chapter VI-A proofs without knowing marginal tax savings.
              </li>
              <li>
                <strong className="text-slate-800">HR Advisory Bottleneck:</strong> Payroll teams lack time to explain
                salary restructuring to every employee.
              </li>
            </ul>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex flex-col">
            <h4 className="font-bold text-emerald-700 text-sm mb-2">The Solution</h4>
            <ul className="space-y-2 text-slate-600">
              <li>
                <strong className="text-slate-800">Deterministic Engine:</strong> 100% auditable pure TypeScript
                calculations for calendar proration and monthly TDS smoothing.
              </li>
              <li>
                <strong className="text-slate-800">Gemini AI Copilot:</strong> Real-time personalized advisory grounded
                in official tax laws.
              </li>
              <li>
                <strong className="text-slate-800">Unified UX:</strong> Dual HR Admin and Employee Self-Service in a
                single reactive platform.
              </li>
            </ul>
          </div>
        </div>
      );

    case 3:
      return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs h-full">
          <div className="bg-emerald-50/60 border border-emerald-200 rounded-xl p-3.5 flex flex-col">
            <div className="flex items-center gap-1.5 text-emerald-800 font-bold text-sm mb-2">
              <Cpu className="h-4 w-4" />
              <span>Frontend SPA</span>
            </div>
            <ul className="space-y-1.5 text-slate-700">
              <li>
                <strong>Framework:</strong> React 19 + TypeScript (Strict mode)
              </li>
              <li>
                <strong>Bundler:</strong> Vite 6 with instant Hot Module Reloading
              </li>
              <li>
                <strong>Styling:</strong> Tailwind CSS v4 with accessible zero-pill design
              </li>
              <li>
                <strong>Icons:</strong> Lucide React icons
              </li>
              <li>
                <strong>Client State:</strong> Pure deterministic taxEngine.ts & payrollEngine.ts
              </li>
            </ul>
          </div>

          <div className="bg-indigo-50/60 border border-indigo-200 rounded-xl p-3.5 flex flex-col">
            <div className="flex items-center gap-1.5 text-indigo-800 font-bold text-sm mb-2">
              <Layers className="h-4 w-4" />
              <span>Server & AI Gateway</span>
            </div>
            <ul className="space-y-1.5 text-slate-700">
              <li>
                <strong>Runtime:</strong> Node.js with Express & tsx loader
              </li>
              <li>
                <strong>Proxy Routes:</strong> /api/ai/tax-optimize & /api/ai/tax-ask
              </li>
              <li>
                <strong>Secret Isolation:</strong> Zero client-side API key leakage
              </li>
              <li>
                <strong>Model Cascading:</strong> gemini-flash-latest → 3.1-flash-lite → 3.8-flash
              </li>
              <li>
                <strong>Timeout Defense:</strong> 12-second abort timeout per call
              </li>
            </ul>
          </div>

          <div className="bg-amber-50/60 border border-amber-200 rounded-xl p-3.5 flex flex-col">
            <div className="flex items-center gap-1.5 text-amber-800 font-bold text-sm mb-2">
              <FileCode className="h-4 w-4" />
              <span>Data & Exports</span>
            </div>
            <ul className="space-y-1.5 text-slate-700">
              <li>
                <strong>Google Gen AI:</strong> @google/genai SDK
              </li>
              <li>
                <strong>Excel Pipeline:</strong> xlsx library for templates & register exports
              </li>
              <li>
                <strong>PDF Generator:</strong> html2canvas + jspdf for official payslips
              </li>
              <li>
                <strong>PPTX Generation:</strong> pptxgenjs for client-side slide compilation
              </li>
            </ul>
          </div>
        </div>
      );

    case 4:
      return (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5 text-xs h-full">
          {[
            {
              title: '1. Master Structuring',
              desc: 'Detailed CTC breakdown (Basic, HRA, Conveyance, Education, LTA, Special & Other allowances, PF ceiling toggles).',
              color: 'border-l-indigo-600',
            },
            {
              title: '2. Monthly Payroll Run',
              desc: 'Month-by-month gross-to-net computation, EPF (12% split), ESI, state PT, and progressive monthly TDS.',
              color: 'border-l-emerald-600',
            },
            {
              title: '3. Employee Self-Service',
              desc: 'Dual portal view for personal salary slips, downloadable PDF payslips, and regime declaration locking.',
              color: 'border-l-amber-600',
            },
            {
              title: '4. Declarations & Audit',
              desc: 'Chapter VI-A investment declarations (80C, 80D, 80CCD, 80E, 80G) and HRA rent verification with landlord PAN.',
              color: 'border-l-cyan-600',
            },
            {
              title: '5. Tax Simulator',
              desc: 'Live what-if sliders for annual CTC, rent paid, and 80C investments with instant Old vs New take-home projection.',
              color: 'border-l-purple-600',
            },
            {
              title: '6. Gemini Copilot',
              desc: 'Bespoke AI tax recommendations and floating Copilot chat drawer accessible anywhere in the application.',
              color: 'border-l-rose-600',
            },
          ].map((item, i) => (
            <div key={i} className={`bg-slate-50 border border-slate-200 border-l-4 ${item.color} rounded-lg p-3`}>
              <h5 className="font-bold text-slate-900 text-xs">{item.title}</h5>
              <p className="text-slate-600 text-[11px] mt-1 leading-snug">{item.desc}</p>
            </div>
          ))}
        </div>
      );

    case 5:
      return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs h-full">
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
            <h4 className="font-bold text-indigo-700 text-sm mb-2">AY 2026–27 Statutory Tax Slabs</h4>
            <div className="space-y-2 text-slate-700">
              <p>
                <strong className="text-slate-900">New Regime (Section 115BAC):</strong>
                <br />
                ₹0–3L (Nil), ₹3–7L (5%), ₹7–10L (10%), ₹10–12L (15%), ₹12–15L (20%), &gt;₹15L (30%).
                <br />
                <span className="text-emerald-700 font-semibold">• ₹75,000 Standard Deduction</span> (Budget 2024) +
                Full Rebate u/s 87A up to ₹7,00,000 net income.
              </p>
              <p>
                <strong className="text-slate-900">Old Regime (Elective):</strong>
                <br />
                ₹0–2.5L (Nil), ₹2.5–5L (5%), ₹5–10L (20%), &gt;₹10L (30%).
                <br />
                Standard deduction of ₹50,000. Permits Section 80C (₹1.5L), Section 80D (₹25k/₹50k), Section 80CCD(1B)
                NPS (₹50k), and HRA Section 10(13A).
              </p>
            </div>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
            <h4 className="font-bold text-emerald-700 text-sm mb-2">Key Mathematical Formulations</h4>
            <div className="space-y-2 text-slate-700">
              <div className="bg-white p-2 border border-slate-200 rounded font-mono text-[10px] text-teal-800">
                Exempt HRA = min(
                <br />
                &nbsp;&nbsp;1. Actual HRA received,
                <br />
                &nbsp;&nbsp;2. Rent paid - 10% of Basic,
                <br />
                &nbsp;&nbsp;3. 50% (Metro) or 40% (Non-Metro) of Basic
                <br />)
              </div>
              <p>
                <strong className="text-slate-900">Progressive Monthly TDS Smoothing:</strong>
                <br />
                <code className="text-indigo-800 font-semibold">TDS = (Annual Tax - Cumulative TDS) / Remaining Months</code>
                <br />
                Guarantees smooth monthly cash flow without sudden year-end salary cuts.
              </p>
              <p className="text-[11px] text-slate-500">
                <strong>Audit Principle:</strong> All financial and tax math is strictly calculated in pure TypeScript
                without delegating math to an LLM.
              </p>
            </div>
          </div>
        </div>
      );

    case 6:
      return (
        <div className="space-y-2.5 text-xs h-full">
          {[
            {
              step: 'Step 1: Context Ingestion',
              desc: 'The server constructs a sanitized prompt combining employee CTC components, declared investments, and deterministic tax figures from both regimes.',
            },
            {
              step: 'Step 2: Multi-Model Tier Cascading',
              desc: 'Calls gemini-flash-latest -> gemini-3.1-flash-lite -> gemini-3.8-flash for optimal speed, latency, and throughput.',
            },
            {
              step: 'Step 3: Circuit Breaker & Timeout Defense',
              desc: 'Enforces a 12-second abort timeout. If upstream latency spikes, the system automatically falls back to a deterministic chartered accountant tax advice engine.',
            },
            {
              step: 'Step 4: Dual Interface Delivery',
              desc: 'Structured JSON response renders interactive regime cards in Smart Tax Advisor, while free-text responses power the persistent Floating AI Tax Copilot.',
            },
          ].map((item, i) => (
            <div key={i} className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex items-start gap-3">
              <span className="h-6 w-6 rounded-full bg-indigo-600 text-white font-bold text-xs flex items-center justify-center shrink-0">
                {i + 1}
              </span>
              <div>
                <h5 className="font-bold text-slate-900">{item.step}</h5>
                <p className="text-slate-600 text-[11px] mt-0.5">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      );

    case 7:
      return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs h-full">
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
            <h4 className="font-bold text-indigo-700 text-sm mb-2">The Vibe Coding Paradigm</h4>
            <p className="text-slate-600 mb-2">
              High-velocity, intent-driven software development where natural language prompts and domain
              specifications guide the generation, testing, and continuous refinement of production software.
            </p>
            <ol className="list-decimal pl-4 space-y-1.5 text-slate-700">
              <li>
                <strong>Domain Modeling:</strong> Codified statutory tax rules into strong TypeScript types.
              </li>
              <li>
                <strong>Iterative Components:</strong> Built modular tabs for Salary Register, Master, and Simulator.
              </li>
              <li>
                <strong>UX Polish:</strong> Accessible input fields, form submit handling, and auto-scrolling chat.
              </li>
              <li>
                <strong>Hardening:</strong> Model timeouts, fallback circuits, and zero build errors.
              </li>
            </ol>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
            <h4 className="font-bold text-emerald-700 text-sm mb-2">Engineering Discipline</h4>
            <ul className="space-y-2 text-slate-700">
              <li>
                <strong className="text-slate-900">100% Strict TypeScript:</strong> Zero `any` shortcuts in payroll
                calculations; comprehensive interfaces for all entities.
              </li>
              <li>
                <strong className="text-slate-900">Continuous Compilation:</strong> Validated continuously with{' '}
                <code>tsc --noEmit</code> and Vite production builds.
              </li>
              <li>
                <strong className="text-slate-900">Clean Architectural Boundaries:</strong> Clear separation between
                UI presentation, pure deterministic calculation utilities, and server proxy routes.
              </li>
            </ul>
          </div>
        </div>
      );

    case 8:
      return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs h-full">
          <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-3 flex flex-col">
            <h4 className="font-bold text-emerald-800 text-sm mb-1.5">Current Strengths</h4>
            <ul className="space-y-2 text-slate-700">
              <li>
                <strong>Corporate SSO & RBAC Isolation:</strong> Mandatory login gateway; employees log in with <code className="text-indigo-700 font-mono">firstname@xyz.com</code> (strictly locked to personal payslips), while admin logs in with <code className="text-indigo-700 font-mono">admin@xyz.com</code>.
              </li>
              <li>
                <strong>Server-Isolated Secrets:</strong> GEMINI_API_KEY is never exposed to browser bundles.
              </li>
              <li>
                <strong>Deterministic Calculations:</strong> Pure functions prevent prompt injection from altering financial payout amounts.
              </li>
              <li>
                <strong>Graceful Degradation:</strong> Timeout guards & model fallbacks prevent denial of service.
              </li>
            </ul>
          </div>

          <div className="bg-rose-50/70 border border-rose-200 rounded-xl p-3 flex flex-col">
            <h4 className="font-bold text-rose-800 text-sm mb-1.5">Security Gaps in Prototype</h4>
            <ul className="space-y-2 text-slate-700">
              <li>
                <strong>Client Session State:</strong> In-memory authentication susceptible to client tampering.
              </li>
              <li>
                <strong>BOLA / IDOR Exposure:</strong> Endpoints accept employee objects without verifying server-side
                session identity.
              </li>
              <li>
                <strong>Unencrypted PII:</strong> PAN numbers and bank details are not encrypted with Field-Level
                Encryption.
              </li>
            </ul>
          </div>

          <div className="bg-indigo-50/70 border border-indigo-200 rounded-xl p-3 flex flex-col">
            <h4 className="font-bold text-indigo-800 text-sm mb-1.5">Statutory Compliance</h4>
            <ul className="space-y-2 text-slate-700">
              <li>
                <strong>India DPDP Act 2023:</strong> Requires explicit consent management and purpose limitation for
                payroll data.
              </li>
              <li>
                <strong>Income Tax Act 1961:</strong> Section 192 mandates accurate TDS deduction and Form 24Q quarterly
                filing.
              </li>
              <li>
                <strong>Tamper-Evident Logs:</strong> Requires immutable audit trails for salary revisions and tax regime
                elections.
              </li>
            </ul>
          </div>
        </div>
      );

    case 9:
      return (
        <div className="h-full flex flex-col justify-between overflow-x-auto text-xs">
          <table className="w-full border-collapse border border-slate-300 text-left text-[11px]">
            <thead>
              <tr className="bg-slate-900 text-white">
                <th className="p-2 border border-slate-700">Domain Pillar</th>
                <th className="p-2 border border-slate-700">Required Enterprise Control</th>
                <th className="p-2 border border-slate-700">Current Status</th>
                <th className="p-2 border border-slate-700">Target Implementation</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-slate-200 bg-white">
                <td className="p-2 font-bold text-slate-900 border border-slate-200">Authentication</td>
                <td className="p-2 text-slate-600 border border-slate-200">Enterprise SSO (SAML 2.0 / OIDC) + MFA</td>
                <td className="p-2 font-bold text-amber-600 border border-slate-200">Mock / In-Memory</td>
                <td className="p-2 text-slate-800 border border-slate-200">Firebase Auth / Okta with HttpOnly cookies</td>
              </tr>
              <tr className="border-b border-slate-200 bg-slate-50">
                <td className="p-2 font-bold text-slate-900 border border-slate-200">Authorization</td>
                <td className="p-2 text-slate-600 border border-slate-200">Server-side RBAC & Tenant Isolation</td>
                <td className="p-2 font-bold text-rose-600 border border-slate-200">Client Guarded</td>
                <td className="p-2 text-slate-800 border border-slate-200">Express middleware verifying JWT claims</td>
              </tr>
              <tr className="border-b border-slate-200 bg-white">
                <td className="p-2 font-bold text-slate-900 border border-slate-200">Data Persistence</td>
                <td className="p-2 text-slate-600 border border-slate-200">Relational DB with AES-256 encryption at rest</td>
                <td className="p-2 font-bold text-rose-600 border border-slate-200">In-Memory / Local</td>
                <td className="p-2 text-slate-800 border border-slate-200">Cloud SQL PostgreSQL with Drizzle ORM</td>
              </tr>
              <tr className="border-b border-slate-200 bg-slate-50">
                <td className="p-2 font-bold text-slate-900 border border-slate-200">PII Protection</td>
                <td className="p-2 text-slate-600 border border-slate-200">Field-Level Encryption (FLE) for PAN & Bank Details</td>
                <td className="p-2 font-bold text-amber-600 border border-slate-200">Masked in UI</td>
                <td className="p-2 text-slate-800 border border-slate-200">KMS-backed column encryption & masking</td>
              </tr>
              <tr className="border-b border-slate-200 bg-white">
                <td className="p-2 font-bold text-slate-900 border border-slate-200">Audit Logging</td>
                <td className="p-2 text-slate-600 border border-slate-200">Append-only immutable audit ledger</td>
                <td className="p-2 font-bold text-emerald-600 border border-slate-200">SHA256 Hash Stamp</td>
                <td className="p-2 text-slate-800 border border-slate-200">Write-once event log for all payroll runs</td>
              </tr>
              <tr className="bg-slate-50">
                <td className="p-2 font-bold text-slate-900 border border-slate-200">Infrastructure</td>
                <td className="p-2 text-slate-600 border border-slate-200">Containerized auto-scaling & Cloudflare WAF</td>
                <td className="p-2 font-bold text-emerald-600 border border-slate-200">Cloud Run / Docker</td>
                <td className="p-2 text-slate-800 border border-slate-200">Multi-region failover & rate limiting</td>
              </tr>
            </tbody>
          </table>
        </div>
      );

    case 10:
      return (
        <div className="h-full flex flex-col justify-between bg-slate-900 text-white -m-5 sm:-m-6 p-6 sm:p-8">
          <div>
            <span className="inline-block px-3 py-1 bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-full text-xs font-bold uppercase tracking-wider mb-2">
              Conclusion & Future Scope
            </span>
            <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
              Capstone Summary & Engineering Impact
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-2 text-xs">
            <div className="bg-slate-800/80 border border-slate-700 rounded-xl p-3.5">
              <h5 className="font-bold text-indigo-400 mb-1.5">Project Achievements</h5>
              <ul className="space-y-1.5 text-slate-300 text-[11px]">
                <li>• Engineered full-stack dual-regime payroll engine for AY 2026-27.</li>
                <li>• Built 6 core functional modules with dual HR & Employee views.</li>
                <li>• Implemented resilient Gemini AI advisory with fallback circuit.</li>
                <li>• Multi-format exports: Excel, PDF payslips, PPTX deck.</li>
              </ul>
            </div>

            <div className="bg-slate-800/80 border border-slate-700 rounded-xl p-3.5">
              <h5 className="font-bold text-emerald-400 mb-1.5">Vibe Coding Takeaways</h5>
              <ul className="space-y-1.5 text-slate-300 text-[11px]">
                <li>• Conversational specs accelerate complex UI/UX prototyping.</li>
                <li>• Strict TypeScript types prevent domain logic drift.</li>
                <li>• Zero-hallucination rule: keep legal math in code.</li>
                <li>• Continuous compilation catches regressions instantly.</li>
              </ul>
            </div>

            <div className="bg-slate-800/80 border border-slate-700 rounded-xl p-3.5">
              <h5 className="font-bold text-amber-400 mb-1.5">Future Roadmap</h5>
              <ul className="space-y-1.5 text-slate-300 text-[11px]">
                <li>• Direct bank integration for NEFT/NACH salary file disbursement.</li>
                <li>• Automated government Form 16 Part A & B generation.</li>
                <li>• Biometric attendance API sync with automated loss of pay (LOP).</li>
                <li>• Enterprise Cloud SQL migration with full SOC 2 compliance.</li>
              </ul>
            </div>
          </div>

          <p className="text-slate-400 text-xs italic text-center">
            Thank you to the evaluation committee. Open for questions and code walkthrough.
          </p>
        </div>
      );

    default:
      return null;
  }
}
