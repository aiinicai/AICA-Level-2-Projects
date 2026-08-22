import React from 'react';
import { 
  ShieldCheck, 
  AlertTriangle, 
  AlertOctagon, 
  CheckCircle2, 
  Building2, 
  Calendar, 
  Hash, 
  FileWarning, 
  HelpCircle,
  Coins
} from 'lucide-react';
import { ExecutiveSummary, ComplianceScore } from '../types';

interface ExecutiveSummaryCardProps {
  summary: ExecutiveSummary;
  documentTitle: string;
  financialHighlights?: {
    totalRevenue?: string;
    pat?: string;
    totalAssets?: string;
    totalDebt?: string;
    netWorth?: string;
  };
}

export const ExecutiveSummaryCard: React.FC<ExecutiveSummaryCardProps> = ({
  summary,
  documentTitle,
  financialHighlights,
}) => {
  const getScoreBadge = (score: ComplianceScore) => {
    switch (score) {
      case 'High':
        return {
          bg: 'bg-emerald-600 text-white border border-[#141414]',
          accentText: 'text-[#00FF00]',
          label: 'HIGH COMPLIANCE',
          desc: 'Substantially complies with Ind AS disclosure mandates and internal consistency rules.',
        };
      case 'Moderate':
        return {
          bg: 'bg-amber-500 text-[#141414] border border-[#141414]',
          accentText: 'text-[#141414]',
          label: 'MODERATE RISK',
          desc: 'Notable disclosure omissions or minor numerical discrepancies requiring rectification.',
        };
      case 'Needs Immediate Revision':
      default:
        return {
          bg: 'bg-red-600 text-white border border-[#141414]',
          accentText: 'text-white',
          label: 'REVISION REQUIRED',
          desc: 'Material non-compliances, casting errors, or related party variances detected.',
        };
    }
  };

  const scoreInfo = getScoreBadge(summary.overallComplianceScore);

  return (
    <section id="executive-compliance-summary" className="bg-white border-2 border-[#141414] shadow-dense p-4 sm:p-5 mb-6">
      {/* Title Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-3.5 border-b border-[#141414] gap-3">
        <div>
          <h2 className="text-[11px] font-serif italic uppercase text-[#141414]/70 mb-0.5 tracking-wider">
            Executive Summary & Compliance Evaluation
          </h2>
          <div className="flex items-center gap-2">
            <h3 className="text-lg sm:text-xl font-bold uppercase tracking-tight text-[#141414]">
              {summary.entityName || documentTitle || 'Entity Compliance Audit'}
            </h3>
            {summary.reportingPeriod && (
              <span className="px-2 py-0.5 bg-[#D1D0CC] text-[#141414] font-mono text-[10px] font-bold border border-[#141414]">
                {summary.reportingPeriod}
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3 mt-1 text-[11px] text-[#141414]/80 font-mono">
            {summary.reportingScale && (
              <span>DENOMINATION: <strong className="text-[#141414]">{summary.reportingScale}</strong></span>
            )}
            <span>STATUS: <strong className="text-[#141414]">STATUTORY EVALUATION COMPLETED</strong></span>
          </div>
        </div>

        {/* Overall Compliance Score Badge */}
        <div className={`flex items-center space-x-3 px-3.5 py-2 ${scoreInfo.bg}`}>
          <div>
            <div className="text-[9px] uppercase tracking-widest font-mono font-bold opacity-85">
              OVERALL COMPLIANCE
            </div>
            <div className="text-sm sm:text-base font-mono font-black tracking-tight">
              {scoreInfo.label}
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 my-4">
        {/* Total Discrepancies */}
        <div className="bg-[#F9F9F7] p-3 border border-[#141414]">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-bold uppercase text-[#141414]/80 font-mono">Total Discrepancies</p>
            <Hash className="w-3.5 h-3.5 text-[#141414]/60" />
          </div>
          <p className="text-2xl sm:text-3xl font-mono font-black text-[#141414] mt-0.5">
            {summary.totalDiscrepancies}
          </p>
          <span className="text-[10px] font-mono text-[#141414]/60 uppercase">
            Missing Disclosures + Mismatches
          </span>
        </div>

        {/* Missing Disclosures */}
        <div className="bg-amber-50 p-3 border border-[#141414]">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-bold uppercase text-amber-900 font-mono">Missing Disclosures</p>
            <HelpCircle className="w-3.5 h-3.5 text-amber-800" />
          </div>
          <p className="text-2xl sm:text-3xl font-mono font-black text-amber-950 mt-0.5">
            {summary.missingDisclosuresCount}
          </p>
          <span className="text-[10px] font-mono text-amber-800 uppercase">
            Mandatory Ind AS Notes Absent
          </span>
        </div>

        {/* Numerical Mismatches */}
        <div className="bg-red-50 p-3 border border-[#141414]">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-bold uppercase text-red-700 font-mono">Numerical Mismatches</p>
            <FileWarning className="w-3.5 h-3.5 text-red-700" />
          </div>
          <p className="text-2xl sm:text-3xl font-mono font-black text-red-700 mt-0.5">
            {summary.numericalMismatchesCount}
          </p>
          <span className="text-[10px] font-mono text-red-700 uppercase">
            Casting & Cross-Ref Variances
          </span>
        </div>
      </div>

      {/* Key Risk Areas Box */}
      <div className="p-3 bg-red-100 border border-red-400">
        <p className="text-[10px] font-bold text-red-700 uppercase tracking-wider font-mono mb-1 flex items-center gap-1.5">
          <AlertOctagon className="w-3.5 h-3.5 text-red-700 stroke-[2.5]" />
          Key Risk Areas & Auditor Observations
        </p>
        <p className="text-[11px] sm:text-xs leading-relaxed text-red-950 font-medium">
          {summary.keyRiskAreas}
        </p>
      </div>

      {/* Financial Highlights if detected */}
      {financialHighlights && (financialHighlights.totalRevenue || financialHighlights.pat || financialHighlights.totalAssets) && (
        <div className="mt-3.5 pt-3 border-t border-[#141414]/15 flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono bg-[#D1D0CC]/40 p-2.5 border border-[#141414]/20">
          <span className="text-[#141414] font-bold uppercase tracking-wider flex items-center gap-1.5 text-[10px]">
            <Coins className="w-3 h-3 text-[#141414]" />
            EXTRACTED BALANCES:
          </span>
          <div className="flex flex-wrap gap-4 text-[#141414]">
            {financialHighlights.totalRevenue && (
              <span>REVENUE: <strong>{financialHighlights.totalRevenue}</strong></span>
            )}
            {financialHighlights.pat && (
              <span>PAT: <strong>{financialHighlights.pat}</strong></span>
            )}
            {financialHighlights.totalAssets && (
              <span>TOTAL ASSETS: <strong>{financialHighlights.totalAssets}</strong></span>
            )}
            {financialHighlights.totalDebt && (
              <span>TOTAL DEBT: <strong>{financialHighlights.totalDebt}</strong></span>
            )}
          </div>
        </div>
      )}
    </section>
  );
};

