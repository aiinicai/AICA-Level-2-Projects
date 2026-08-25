import React, { useState } from 'react';
import { 
  ClipboardCheck, 
  FileText, 
  Sparkles, 
  Printer, 
  Copy, 
  Loader2, 
  ShieldCheck, 
  Check
} from 'lucide-react';
import { Asset, RiskFinding, AssetReliabilityScore } from '../types';
import { generateAuditSummaryWithAI } from '../services/aiService';

interface AuditReadinessProps {
  assets: Asset[];
  risks: RiskFinding[];
  reliabilityScore: AssetReliabilityScore;
  currencyMode: 'Lakhs' | 'Crores' | 'Full';
}

export const AuditReadiness: React.FC<AuditReadinessProps> = ({
  assets,
  risks
}) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [auditReportMarkdown, setAuditReportMarkdown] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Calculations for scorecards
  const totalAssets = assets.length || 1;
  const verifiedAssets = assets.filter((a) => a.verificationStatus === 'Verified').length;
  const pvCoverage = Math.round((verifiedAssets / totalAssets) * 100);

  const missingDocs = risks.filter((r) => r.riskType === 'Missing Documents' && r.status !== 'Closed').length;
  const docCompleteness = Math.max(0, Math.round(((totalAssets - missingDocs * 2) / totalAssets) * 100));

  const openExceptions = risks.filter((r) => r.status !== 'Closed').length;
  const caroReadiness = 88; // Score %

  const handleGenerateSummary = async () => {
    setIsGenerating(true);
    try {
      const stats = {
        totalGrossValueINR: assets.reduce((sum, a) => sum + a.costINR, 0),
        totalNBVINR: assets.reduce((sum, a) => sum + a.nbvINR, 0),
        totalAssets: assets.length
      };

      const result = await generateAuditSummaryWithAI({
        registerStats: stats,
        topRisks: risks.filter((r) => r.severity === 'Critical' || r.severity === 'High'),
        pvCoverage,
        caroReadiness
      });

      setAuditReportMarkdown(result);
    } catch (e) {
      console.error('Failed to generate audit report:', e);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = () => {
    if (!auditReportMarkdown) return;
    navigator.clipboard.writeText(auditReportMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-blue-600">
            <ClipboardCheck className="w-4 h-4 text-blue-600" />
            <span>Statutory Audit Committee Preparation</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-1">
            Audit Readiness & Assurance Center
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Real-time audit evidence dossier, CARO 2020 compliance pack, and automated Big-4 style Executive Audit Summary Generator.
          </p>
        </div>

        <button
          onClick={handleGenerateSummary}
          disabled={isGenerating}
          className="px-4 py-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white text-xs font-bold flex items-center space-x-2 transition-all shadow-xs self-start md:self-auto"
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Synthesizing Audit Memo...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 text-blue-400" />
              <span>Generate Executive Audit Summary</span>
            </>
          )}
        </button>
      </div>

      {/* Audit Readiness Scorecards (4 Columns) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Evidence Completeness</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-2xl font-bold text-emerald-700 font-mono">{docCompleteness}%</span>
            <span className="text-xs text-slate-400 font-medium">Score</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100">
            Matching PO, Invoices, GRN, & Put-to-Use
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Physical Count Coverage</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-2xl font-bold text-blue-700 font-mono">{pvCoverage}%</span>
            <span className="text-xs text-slate-400 font-medium">({verifiedAssets}/{totalAssets})</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100">
            CARO 2020 Clause 3(i)(b) compliant cycle
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Open Control Exceptions</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-2xl font-bold text-amber-700 font-mono">{openExceptions}</span>
            <span className="text-xs text-slate-400 font-medium">Active</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100">
            Under investigation / management review
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">CARO 2020 Readiness</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-2xl font-bold text-emerald-700 font-mono">{caroReadiness}%</span>
            <span className="text-xs text-emerald-800 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              Substantial
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100">
            Title deeds & PPE records validated
          </p>
        </div>
      </div>

      {/* Audit Readiness Checklist & Workpapers Pack */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-blue-600" />
          <span>Statutory Audit Pack Deliverables & Review Checklist</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          {[
            { name: 'Fixed Asset Subledger vs General Ledger Reconciliation', status: 'Ready', desc: '100% mathematical tie-out between FA Subledger and SAP S/4HANA Trial Balance.' },
            { name: 'Ind AS 16 Componentisation Breakdown Dossier', status: 'Ready', desc: 'High-value machine tools split with distinct useful life schedules.' },
            { name: 'Physical Verification Discrepancy & Reconciliation File', status: 'In Review', desc: 'Plant controller investigation notes for 2 material variances.' },
            { name: 'Title Deeds of Immovable Properties (Freehold Land & Buildings)', status: 'Ready', desc: 'State registry certificates and encumbrance certificates bound.' },
            { name: 'Depreciation Recalculation Schedule (Companies Act Sch II vs IT Act)', status: 'Ready', desc: 'SLM vs block WDV calculations with half-year put-to-use analysis.' },
            { name: 'Ind AS 36 Impairment Indicator Assessment Sheet', status: 'In Review', desc: 'Recoverable amount valuation for idle robot cell #3 at Sanand plant.' }
          ].map((item, idx) => (
            <div key={idx} className="bg-slate-50 border border-slate-200 p-3.5 rounded-xl flex items-start justify-between gap-3 shadow-2xs">
              <div className="space-y-1">
                <h4 className="font-bold text-slate-900 text-xs">{item.name}</h4>
                <p className="text-slate-500 text-[11px] leading-tight">{item.desc}</p>
              </div>
              <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold shrink-0 ${
                item.status === 'Ready'
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-amber-50 text-amber-700 border border-amber-200'
              }`}>
                {item.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Generated Executive Audit Summary Report */}
      {auditReportMarkdown ? (
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4 animate-in fade-in duration-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
            <div>
              <span className="text-[10px] font-mono text-blue-600 font-bold uppercase">AI-Synthesized Deliverable</span>
              <h3 className="text-base font-bold text-slate-900">Executive Asset Governance Audit Summary</h3>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={handleCopy}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors border border-slate-200 shadow-2xs"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
              </button>

              <button
                onClick={() => window.print()}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg flex items-center space-x-1.5 transition-colors border border-slate-200 shadow-2xs"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print / PDF Export</span>
              </button>
            </div>
          </div>

          {/* Formatted Markdown Content Container */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 text-slate-800 text-xs font-sans leading-relaxed whitespace-pre-line space-y-3">
            {auditReportMarkdown}
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-[11px] text-slate-500 flex items-center justify-between">
            <span>Prepared for: Audit Committee & Statutory Auditors (Deloitte / EY / PwC / KPMG)</span>
            <span className="font-mono text-emerald-700 font-bold">Status: Ready for Submission</span>
          </div>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center space-y-3 shadow-sm">
          <FileText className="w-10 h-10 text-slate-400 mx-auto" />
          <h4 className="font-bold text-slate-900 text-sm">No Audit Summary Generated Yet</h4>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Click the "Generate Executive Audit Summary" button above to synthesize a complete audit memorandum with CARO 2020 evaluations and Key Audit Matters.
          </p>
          <button
            onClick={handleGenerateSummary}
            disabled={isGenerating}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-lg inline-flex items-center space-x-2 transition-all shadow-xs"
          >
            <Sparkles className="w-4 h-4 text-blue-400" />
            <span>Generate Now</span>
          </button>
        </div>
      )}
    </div>
  );
};
