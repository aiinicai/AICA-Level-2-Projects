import React from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  HelpCircle, 
  XCircle, 
  ShieldCheck, 
  FileCheck2, 
  Coins, 
  Percent, 
  Lock, 
  FileText 
} from 'lucide-react';
import { CreditAssessment, Company } from '../types/financial';

interface CreditDecisionBannerProps {
  assessment: CreditAssessment;
  company: Company;
  onOpenReportModal: () => void;
}

export const CreditDecisionBanner: React.FC<CreditDecisionBannerProps> = ({
  assessment,
  company,
  onOpenReportModal
}) => {
  const { 
    recommendation, 
    creditGrade, 
    riskLevel, 
    decisionRationale, 
    recommendedCreditLimit, 
    recommendedInterestSpread, 
    collateralRequirement, 
    covenants 
  } = assessment;

  const getDecisionTheme = (rec: string) => {
    switch (rec) {
      case 'Approve':
        return {
          bg: 'bg-gradient-to-r from-emerald-950/70 via-slate-900 to-emerald-950/50',
          border: 'border-emerald-600/40',
          badge: 'bg-emerald-500 text-slate-950',
          icon: <CheckCircle2 className="w-8 h-8 text-emerald-400 shrink-0" />,
          accentText: 'text-emerald-400',
          subtext: 'Meets and exceeds institutional credit underwriting criteria with prime quality indicators.'
        };
      case 'Conditional Approval':
        return {
          bg: 'bg-gradient-to-r from-amber-950/70 via-slate-900 to-amber-950/50',
          border: 'border-amber-600/40',
          badge: 'bg-amber-500 text-slate-950',
          icon: <FileCheck2 className="w-8 h-8 text-amber-400 shrink-0" />,
          accentText: 'text-amber-400',
          subtext: 'Borrower is fundamentally sound; sanction subject to structured covenants and credit monitoring.'
        };
      case 'Review Required':
        return {
          bg: 'bg-gradient-to-r from-orange-950/70 via-slate-900 to-orange-950/50',
          border: 'border-orange-600/40',
          badge: 'bg-orange-500 text-slate-950',
          icon: <HelpCircle className="w-8 h-8 text-orange-400 shrink-0" />,
          accentText: 'text-orange-400',
          subtext: 'Elevated risk parameters detected. Mandatory referral to Central Credit Risk Committee.'
        };
      default: // Reject
        return {
          bg: 'bg-gradient-to-r from-rose-950/70 via-slate-900 to-rose-950/50',
          border: 'border-rose-600/40',
          badge: 'bg-rose-500 text-white',
          icon: <XCircle className="w-8 h-8 text-rose-400 shrink-0" />,
          accentText: 'text-rose-400',
          subtext: 'Credit metrics breach institutional risk tolerance limits. Recommendation is to decline facility.'
        };
    }
  };

  const theme = getDecisionTheme(recommendation);

  return (
    <div className={`rounded-2xl border ${theme.border} ${theme.bg} p-5 lg:p-6 shadow-xl relative overflow-hidden`}>
      {/* Top Banner Row */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-5 border-b border-slate-800">
        <div className="flex items-start space-x-3.5">
          {theme.icon}
          <div>
            <div className="flex items-center space-x-2.5">
              <span className={`text-xs font-black uppercase px-2.5 py-1 rounded-md tracking-wider ${theme.badge}`}>
                {recommendation}
              </span>
              <span className="text-xs text-slate-400 font-mono">Decision Matrix v1.0</span>
            </div>
            <h2 className="text-xl font-black text-white mt-1">
              Credit Underwriting Recommendation: <span className={theme.accentText}>{recommendation}</span>
            </h2>
            <p className="text-xs text-slate-300 mt-0.5">{theme.subtext}</p>
          </div>
        </div>

        {/* Credit Grade Display & Report CTA */}
        <div className="flex items-center space-x-3 w-full lg:w-auto justify-between lg:justify-end">
          <div className="bg-slate-800/80 border border-slate-700 px-4 py-2 rounded-xl text-center">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Institutional Rating</div>
            <div className="text-2xl font-black text-cyan-300 tracking-tight leading-none mt-0.5">
              Grade {creditGrade}
            </div>
            <div className="text-[10px] text-slate-300 font-medium">{riskLevel}</div>
          </div>

          <button
            onClick={onOpenReportModal}
            className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-3 rounded-xl text-xs font-bold shadow-lg shadow-blue-600/30 transition shrink-0"
          >
            <FileText className="w-4 h-4" />
            <span>Generate CAM Report</span>
          </button>
        </div>
      </div>

      {/* Decision Rationale & Facility Parameters */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-5">
        
        {/* Left Column: Decision Matrix Criteria Checks */}
        <div className="lg:col-span-6 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            <span>Underwriting Rationale Checklist</span>
          </h3>

          <div className="space-y-2">
            {decisionRationale.map((rationale, idx) => (
              <div 
                key={idx}
                className="flex items-start space-x-2 text-xs bg-slate-800/60 p-2.5 rounded-lg border border-slate-700/60 text-slate-200"
              >
                <div className="mt-0.5 shrink-0">
                  {recommendation === 'Approve' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : recommendation === 'Conditional Approval' ? (
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                  ) : (
                    <XCircle className="w-4 h-4 text-rose-400" />
                  )}
                </div>
                <span>{rationale}</span>
              </div>
            ))}
          </div>

          {/* Underwriting Covenants */}
          <div className="mt-3 pt-3 border-t border-slate-800/80">
            <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Key Facility Covenants
            </h4>
            <ul className="space-y-1">
              {covenants.slice(0, 3).map((cov, idx) => (
                <li key={idx} className="text-xs text-slate-300 flex items-start space-x-1.5">
                  <span className="text-cyan-400 font-bold">•</span>
                  <span>{cov}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Right Column: Sanction Terms & Exposure Guidelines */}
        <div className="lg:col-span-6 bg-slate-800/50 rounded-xl p-4 border border-slate-700/60 flex flex-col justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center space-x-1.5">
            <Coins className="w-4 h-4 text-amber-400" />
            <span>Recommended Sanction Terms &amp; Exposure Limits</span>
          </h3>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Max Credit Exposure</span>
              <div className="text-lg font-black text-white mt-0.5">
                {recommendation === 'Reject' ? 'INR 0.0 Cr' : `INR ${recommendedCreditLimit} Cr`}
              </div>
              <span className="text-[10px] text-slate-400">Based on cash flow capacity</span>
            </div>

            <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Indicative Pricing</span>
              <div className="text-sm font-bold text-cyan-300 mt-1 truncate" title={recommendedInterestSpread}>
                {recommendedInterestSpread.split(' ')[0]} {recommendedInterestSpread.split(' ')[1] || ''}
              </div>
              <span className="text-[10px] text-slate-400">Risk-adjusted margin</span>
            </div>

            <div className="col-span-2 bg-slate-900/70 p-3 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase font-semibold flex items-center gap-1">
                <Lock className="w-3 h-3 text-indigo-400" /> Collateral &amp; Security Margin
              </span>
              <p className="text-xs font-medium text-slate-200 mt-0.5">
                {collateralRequirement}
              </p>
            </div>
          </div>

          <div className="mt-3 text-[11px] text-slate-400 flex items-center justify-between pt-2 border-t border-slate-800">
            <span>Borrower: <strong className="text-slate-300">{company.companyName}</strong></span>
            <span>Turnover: <strong className="text-slate-300">INR {company.annualTurnover} Cr</strong></span>
          </div>
        </div>

      </div>
    </div>
  );
};
