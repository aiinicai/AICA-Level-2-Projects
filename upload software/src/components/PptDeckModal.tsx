import React, { useState } from 'react';
import {
  Presentation,
  X,
  ChevronLeft,
  ChevronRight,
  Download,
  FileSpreadsheet,
  FileText,
  Layers,
  ShieldCheck,
  Building,
  Sparkles,
  Calculator,
} from 'lucide-react';
import { EntityDetails, ReconciliationReport } from '../types/accounting';

interface PptDeckModalProps {
  isOpen: boolean;
  onClose: () => void;
  entity?: EntityDetails;
  reconciliation?: ReconciliationReport;
  onDownloadPpt: () => void;
}

export const PptDeckModal: React.FC<PptDeckModalProps> = ({
  isOpen,
  onClose,
  entity,
  reconciliation,
  onDownloadPpt,
}) => {
  const [activeSlide, setActiveSlide] = useState(0);

  if (!isOpen) return null;

  const entityName = entity?.name || 'M/s ABC Enterprises';
  const entityType = entity?.entityType || 'Partnership Firm';
  const financialYear = entity?.financialYear || '2024-25';
  const pan = entity?.pan || 'AAAPF1234K';
  const gst = entity?.gstin || '27AAAPF1234K1Z5';

  const slides = [
    // SLIDE 1: OVERVIEW & CLIENT PROFILE
    {
      id: 1,
      badge: 'SLIDE 1: OVERVIEW',
      title: 'Non-Corporate Financial Statements Automation',
      subtitle: 'Converts raw Trial Balance into standard Vertical Balance Sheet, P&L, and Schedules 1–14 in seconds.',
      theme: 'dark',
      content: (
        <div className="grid grid-cols-2 gap-3.5">
          {/* Client Profile Card */}
          <div className="bg-[#1e293b] p-3.5 border border-slate-700/80">
            <div className="text-[11px] font-mono font-bold text-[#f59e0b] tracking-wider mb-2 flex items-center">
              <Building className="w-3.5 h-3.5 mr-1.5" /> CLIENT PROFILE
            </div>
            <div className="space-y-1.5 text-xs font-mono text-slate-200">
              <div className="flex justify-between border-b border-slate-700/50 pb-1">
                <span className="text-slate-400">Entity Name:</span>
                <span className="font-bold text-white truncate max-w-[180px]">{entityName}</span>
              </div>
              <div className="flex justify-between border-b border-slate-700/50 pb-1">
                <span className="text-slate-400">Constitution:</span>
                <span>{entityType}</span>
              </div>
              <div className="flex justify-between border-b border-slate-700/50 pb-1">
                <span className="text-slate-400">Financial Year:</span>
                <span className="text-emerald-400 font-bold">FY {financialYear}</span>
              </div>
              <div className="flex justify-between border-b border-slate-700/50 pb-1">
                <span className="text-slate-400">PAN / GSTIN:</span>
                <span>{pan} / {gst}</span>
              </div>
              <div className="flex justify-between pt-0.5">
                <span className="text-slate-400">Framework:</span>
                <span className="text-amber-300 font-mono text-[11px]">ICAI Technical Guide</span>
              </div>
            </div>
          </div>

          {/* Key Highlights */}
          <div className="bg-[#1e293b] p-3.5 border border-slate-700/80">
            <div className="text-[11px] font-mono font-bold text-emerald-400 tracking-wider mb-2 flex items-center">
              <ShieldCheck className="w-3.5 h-3.5 mr-1.5" /> KEY HIGHLIGHTS
            </div>
            <ul className="space-y-1.5 text-xs text-slate-300">
              <li className="flex items-start">
                <span className="text-emerald-400 font-bold mr-1.5">•</span>
                <span><strong>Turnkey Speed:</strong> From raw TB to final accounts in &lt;2 mins.</span>
              </li>
              <li className="flex items-start">
                <span className="text-emerald-400 font-bold mr-1.5">•</span>
                <span><strong>Universal ERP:</strong> Tally, Busy, SAP, Marg & Zoho (Excel/CSV).</span>
              </li>
              <li className="flex items-start">
                <span className="text-emerald-400 font-bold mr-1.5">•</span>
                <span><strong>Smart Ingestion:</strong> Auto-cleans headers, footers & totals.</span>
              </li>
              <li className="flex items-start">
                <span className="text-emerald-400 font-bold mr-1.5">•</span>
                <span><strong>ICAI Standard:</strong> Vertical Balance Sheet & Schedules 1–14.</span>
              </li>
              <li className="flex items-start">
                <span className="text-emerald-400 font-bold mr-1.5">•</span>
                <span><strong>Multi-Format Export:</strong> Linked Excel (.xlsx) & Print PDF.</span>
              </li>
            </ul>
          </div>
        </div>
      ),
    },

    // SLIDE 2: 7-STEP PROCESS FLOW
    {
      id: 2,
      badge: 'SLIDE 2: WORKFLOW',
      title: '7-Step End-to-End Preparation Pipeline',
      subtitle: 'Simple, automated workflow from raw ledger import to statutory deliverables',
      theme: 'light',
      content: (
        <div className="grid grid-cols-4 gap-2 text-xs">
          {[
            { step: '01', title: 'Control Sheet', desc: 'Set entity details, policies & schedule visibility.' },
            { step: '02', title: 'TB Upload', desc: 'Drag & drop raw Excel/CSV from any ERP.' },
            { step: '03', title: 'Auto-Map', desc: '100+ rules auto-assign ledgers to Sch 1–14.' },
            { step: '04', title: 'Trading & P&L', desc: 'Auto Gross Profit, Operating Profit & Tax.' },
            { step: '05', title: 'Schedules 1-14', desc: 'Auto Capital Fund & AS-10 Fixed Assets block.' },
            { step: '06', title: 'Balance Sheet', desc: 'Vertical format with drill-down to ledgers.' },
            { step: '07', title: 'Audit & Export', desc: 'Zero-variance check (₹0.00) + Excel & PDF.' },
            { step: '⚡', title: 'Speed', desc: 'Completes in <2 mins with 100% accuracy.' },
          ].map((item, idx) => (
            <div key={idx} className="bg-white p-2.5 border border-slate-200 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 ${idx === 7 ? 'bg-emerald-600 text-white' : 'bg-slate-900 text-white'}`}>
                    {item.step}
                  </span>
                </div>
                <div className="font-bold text-slate-800 text-[11px] mb-1">{item.title}</div>
                <div className="text-[10px] text-slate-600 leading-tight">{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      ),
    },

    // SLIDE 3: SMART INGESTION & AUTO-MAPPING
    {
      id: 3,
      badge: 'SLIDE 3: DATA & RULES',
      title: 'Smart Ingestion & Auto-Mapping Engine',
      subtitle: 'Intelligent noise filtering and 100+ ICAI keyword mapping rules',
      theme: 'light',
      content: (
        <div className="grid grid-cols-2 gap-3.5 text-xs">
          <div className="bg-white p-3.5 border border-slate-200">
            <div className="text-[11px] font-bold text-amber-700 mb-1.5 flex items-center">
              <Layers className="w-3.5 h-3.5 mr-1" /> 1. Smart Upload & Ingestion
            </div>
            <ul className="space-y-1.5 text-[11px] text-slate-700">
              <li className="flex items-start">
                <span className="text-amber-600 font-bold mr-1">•</span>
                <span><strong>Column Detection:</strong> Auto-detects Ledger, Op, Dr, Cr & Closing.</span>
              </li>
              <li className="flex items-start">
                <span className="text-amber-600 font-bold mr-1">•</span>
                <span><strong>Header Cleaning:</strong> Skips company banners & letterheads.</span>
              </li>
              <li className="flex items-start">
                <span className="text-amber-600 font-bold mr-1">•</span>
                <span><strong>Metadata Extraction:</strong> Pulls Client Name, PAN, GSTIN & FY.</span>
              </li>
              <li className="flex items-start">
                <span className="text-amber-600 font-bold mr-1">•</span>
                <span><strong>Total Purging:</strong> Eliminates sub-totals to prevent double counting.</span>
              </li>
            </ul>
          </div>

          <div className="bg-white p-3.5 border border-slate-200">
            <div className="text-[11px] font-bold text-blue-700 mb-1.5 flex items-center">
              <Sparkles className="w-3.5 h-3.5 mr-1" /> 2. Intelligent Auto-Mapping
            </div>
            <ul className="space-y-1.5 text-[11px] text-slate-700">
              <li className="flex items-start">
                <span className="text-blue-600 font-bold mr-1">•</span>
                <span><strong>100+ Rules:</strong> Auto-assigns ledgers to direct/indirect P&L or Sch 1–14.</span>
              </li>
              <li className="flex items-start">
                <span className="text-blue-600 font-bold mr-1">•</span>
                <span><strong>Nature Intelligence:</strong> Capital Dr &rarr; Drawings; Bank OD &rarr; Sch 4.</span>
              </li>
              <li className="flex items-start">
                <span className="text-blue-600 font-bold mr-1">•</span>
                <span><strong>Statutory Dues:</strong> GST ITC/TDS &rarr; Loans/Advances (Sch 13).</span>
              </li>
              <li className="flex items-start">
                <span className="text-blue-600 font-bold mr-1">•</span>
                <span><strong>AI Assistant:</strong> On-demand CA guidance for ambiguous accounts.</span>
              </li>
            </ul>
          </div>
        </div>
      ),
    },

    // SLIDE 4: STATUTORY COMPUTATIONS (SCH 1 & SCH 8)
    {
      id: 4,
      badge: 'SLIDE 4: STATUTORY ENGINES',
      title: 'Capital Movement (Sch 1) & Fixed Assets (Sch 8)',
      subtitle: 'Dynamic mathematical engines for Schedule 1 and Schedule 8',
      theme: 'light',
      content: (
        <div className="grid grid-cols-2 gap-3.5 text-xs">
          {/* Schedule 1: Capital Fund */}
          <div className="bg-white p-3.5 border border-slate-200">
            <div className="text-[11px] font-bold text-emerald-800 mb-1.5 flex items-center">
              <Calculator className="w-3.5 h-3.5 mr-1" /> Schedule 1: Capital Movement Engine
            </div>
            <div className="bg-slate-900 text-slate-100 p-2.5 font-mono text-[10.5px] space-y-0.5 border border-slate-800">
              <div>Opening Capital Balance</div>
              <div className="text-emerald-400">(+) Fresh Capital Introduced</div>
              <div className="text-emerald-400">(+) Partner Remuneration & Interest</div>
              <div className="text-emerald-400">(+) Net Profit for the Year (from P&L)</div>
              <div className="text-rose-400">(-) Drawings for the Year</div>
              <div className="text-rose-400">(-) Personal Taxes & LIC</div>
              <div className="border-t border-slate-700 pt-1 text-amber-300 font-bold">
                (=) Closing Partner Fund / Net Worth
              </div>
            </div>
            <p className="text-[10px] text-slate-500 mt-2">
              * Supports multiple partners and splits profit/drawings based on PSR.
            </p>
          </div>

          {/* Schedule 8: AS-10 Fixed Assets */}
          <div className="bg-white p-3.5 border border-slate-200">
            <div className="text-[11px] font-bold text-blue-800 mb-1.5 flex items-center">
              <Layers className="w-3.5 h-3.5 mr-1" /> Schedule 8: AS-10 Fixed Assets Block
            </div>
            <div className="space-y-1.5 text-[11px] text-slate-700">
              <div className="p-2 bg-slate-50 border border-slate-200">
                <strong className="text-slate-900">1. Gross Block:</strong> Opening + Additions (&gt;180d/&lt;180d) &minus; Sales = Closing Gross.
              </div>
              <div className="p-2 bg-slate-50 border border-slate-200">
                <strong className="text-slate-900">2. Depreciation:</strong> Opening + For Year &minus; Disposals = Closing Dep.
              </div>
              <div className="p-2 bg-slate-50 border border-slate-200">
                <strong className="text-slate-900">3. Net Block:</strong> Gross Block &minus; Depreciation = Net Book Value (Flows to Balance Sheet Assets).
              </div>
            </div>
          </div>
        </div>
      ),
    },

    // SLIDE 5: AUDIT CHECKS & DELIVERABLES
    {
      id: 5,
      badge: 'SLIDE 5: INTEGRITY & EXPORTS',
      title: '3-Way Audit Verification & Deliverables',
      subtitle: 'Zero-variance reconciliation, linked Excel, and audit-ready PDF',
      theme: 'light',
      content: (
        <div className="space-y-3 text-xs">
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-white p-2.5 border border-slate-200">
              <div className="text-[9px] font-mono font-bold text-blue-600 mb-0.5">1. TRIAL BALANCE</div>
              <div className="font-bold text-slate-800 text-[11px]">Input Integrity</div>
              <div className="text-[10px] text-slate-600 mt-0.5">Total Dr = Total Cr. All ledgers accounted for without dropping balances.</div>
            </div>
            <div className="bg-white p-2.5 border border-slate-200">
              <div className="text-[9px] font-mono font-bold text-emerald-600 mb-0.5">2. P&L LINK</div>
              <div className="font-bold text-slate-800 text-[11px]">Surplus Transfer</div>
              <div className="text-[10px] text-slate-600 mt-0.5">Gross Profit & Net Surplus link seamlessly to Capital Fund in Sch 1.</div>
            </div>
            <div className="bg-white p-2.5 border border-slate-200">
              <div className="text-[9px] font-mono font-bold text-amber-600 mb-0.5">3. BALANCE SHEET</div>
              <div className="font-bold text-slate-800 text-[11px]">Tally Verification</div>
              <div className="text-[10px] text-slate-600 mt-0.5">Total Equity & Liab = Total Assets. Guaranteed zero difference (₹0.00).</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-900 text-white p-3 border border-slate-800 flex items-center justify-between">
              <div>
                <div className="text-[10px] font-mono text-emerald-400 font-bold">LINKED EXCEL (.XLSX)</div>
                <div className="text-[11px] text-slate-300 leading-snug">Preserves live formulas (=SUM, sheet links) across all sheets. Perfect for Tax Audit Working Papers.</div>
              </div>
              <FileSpreadsheet className="w-7 h-7 text-emerald-400 shrink-0 ml-3" />
            </div>

            <div className="bg-slate-900 text-white p-3 border border-slate-800 flex items-center justify-between">
              <div>
                <div className="text-[10px] font-mono text-amber-400 font-bold">STATUTORY PDF REPORT</div>
                <div className="text-[11px] text-slate-300 leading-snug">Formatted vertical statements with accounting notes, notes to accounts, and signature blocks.</div>
              </div>
              <FileText className="w-7 h-7 text-amber-400 shrink-0 ml-3" />
            </div>
          </div>
        </div>
      ),
    },
  ];

  const currentSlide = slides[activeSlide];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-[#141414] border border-white/20 w-full max-w-4xl shadow-2xl flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="px-5 py-3.5 bg-[#1a1a1a] border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="p-1.5 bg-[#f59e0b]/20 text-[#f59e0b] border border-[#f59e0b]/30">
              <Presentation className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-sm font-bold text-white tracking-wide">
                  PROJECT PRESENTATION DECK
                </span>
                <span className="px-1.5 py-0.5 bg-[#f59e0b] text-black text-[10px] font-mono font-bold">
                  5 SLIDES
                </span>
              </div>
              <div className="text-[11px] text-zinc-400">
                ICAI Non-Corporate Financial Statements & Automation Notes
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onDownloadPpt}
              className="inline-flex items-center px-3 py-1.5 bg-[#f59e0b] hover:bg-[#d97706] text-black text-xs font-mono font-bold transition shadow-sm"
              id="btn-modal-download-pptx"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              DOWNLOAD .PPTX
            </button>
            <button
              onClick={onClose}
              className="p-1 text-zinc-400 hover:text-white hover:bg-white/10 transition"
              id="btn-close-ppt-modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Slide Stage Container */}
        <div className="p-6 bg-[#0c0c0c] overflow-y-auto flex-1 flex flex-col justify-center items-center">
          <div
            className={`w-full max-w-3xl aspect-[16/9] ${
              currentSlide.theme === 'dark' ? 'bg-[#0f172a] text-white border-slate-700' : 'bg-[#f8fafc] text-slate-900 border-slate-300'
            } border-2 p-6 flex flex-col justify-between shadow-2xl relative transition-all duration-300`}
          >
            {/* Slide Header */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span
                  className={`text-[10px] font-mono font-bold tracking-wider ${
                    currentSlide.theme === 'dark' ? 'text-[#f59e0b]' : 'text-blue-600'
                  }`}
                >
                  {currentSlide.badge}
                </span>
                <span className="text-[10px] font-mono font-bold opacity-60">
                  SLIDE {currentSlide.id} OF 5
                </span>
              </div>

              <h2
                className={`text-lg font-bold leading-snug whitespace-pre-line ${
                  currentSlide.theme === 'dark' ? 'text-white' : 'text-slate-900'
                }`}
              >
                {currentSlide.title}
              </h2>
              <p
                className={`text-xs mt-0.5 ${
                  currentSlide.theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
                }`}
              >
                {currentSlide.subtitle}
              </p>
            </div>

            {/* Slide Body */}
            <div className="my-auto py-2">
              {currentSlide.content}
            </div>

            {/* Slide Footer */}
            <div
              className={`pt-2 border-t flex items-center justify-between text-[9px] font-mono ${
                currentSlide.theme === 'dark'
                  ? 'border-slate-800 text-slate-500'
                  : 'border-slate-200 text-slate-400'
              }`}
            >
              <div>ICAI Technical Guide (Schedules 1-14)</div>
              <div>{entityName} • FY {financialYear}</div>
            </div>
          </div>
        </div>

        {/* Footer Navigation Bar */}
        <div className="px-5 py-3 bg-[#1a1a1a] border-t border-white/10 flex items-center justify-between">
          {/* Thumbnails */}
          <div className="flex items-center space-x-1.5">
            {slides.map((s, idx) => (
              <button
                key={s.id}
                onClick={() => setActiveSlide(idx)}
                className={`px-2.5 py-1 text-xs font-mono transition border ${
                  activeSlide === idx
                    ? 'bg-[#f59e0b] text-black border-[#f59e0b] font-bold'
                    : 'bg-[#222] text-zinc-400 border-white/10 hover:bg-[#333] hover:text-white'
                }`}
              >
                Slide {s.id}
              </button>
            ))}
          </div>

          {/* Prev / Next controls */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setActiveSlide(prev => Math.max(0, prev - 1))}
              disabled={activeSlide === 0}
              className="p-1.5 bg-[#222] hover:bg-[#333] text-white disabled:opacity-30 disabled:cursor-not-allowed border border-white/10 transition"
              title="Previous Slide"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-mono text-zinc-400 px-1">
              {activeSlide + 1} / 5
            </span>
            <button
              onClick={() => setActiveSlide(prev => Math.min(slides.length - 1, prev + 1))}
              disabled={activeSlide === slides.length - 1}
              className="p-1.5 bg-[#222] hover:bg-[#333] text-white disabled:opacity-30 disabled:cursor-not-allowed border border-white/10 transition"
              title="Next Slide"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
