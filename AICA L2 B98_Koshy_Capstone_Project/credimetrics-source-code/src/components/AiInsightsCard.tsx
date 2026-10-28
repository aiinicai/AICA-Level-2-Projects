import React, { useState } from 'react';
import { 
  Sparkles, 
  RefreshCw, 
  BrainCircuit, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldCheck, 
  HelpCircle 
} from 'lucide-react';
import { Company, FinancialRatios, CreditAssessment, RedFlag } from '../types/financial';

interface AiInsightsCardProps {
  company: Company;
  ratios: FinancialRatios;
  assessment: CreditAssessment;
  redFlags: RedFlag[];
}

export const AiInsightsCard: React.FC<AiInsightsCardProps> = ({
  company,
  ratios,
  assessment,
  redFlags
}) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');
  const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);

  // Generate deterministic intelligent financial insight narrative
  const generateNarrative = () => {
    const { totalScore, rating } = assessment.healthScore;
    const { recommendation, creditGrade } = assessment;

    let narrative = `### Institutional Credit Underwriting Assessment: ${company.companyName}\n\n`;
    narrative += `**1. Holistic Credit Standing & Risk Classification:**\n`;
    narrative += `The borrower demonstrates an overall Financial Health Score of **${totalScore}/100** (Rating: **${rating}**), assigning an internal credit rating of **Grade ${creditGrade}** with an underwriting stance of **${recommendation.toUpperCase()}**.\n\n`;

    narrative += `**2. Liquidity & Working Capital Dynamics:**\n`;
    if (ratios.currentRatio >= 1.5) {
      narrative += `Working capital buffer is robust with a Current Ratio of **${ratios.currentRatio.toFixed(2)}x** and Quick Ratio of **${ratios.quickRatio.toFixed(2)}x**, comfortably exceeding the standard benchmark (1.33x). Cash conversion is adequate with DSO at **${ratios.daysSalesOutstanding.toFixed(0)} days**.\n\n`;
    } else if (ratios.currentRatio >= 1.0) {
      narrative += `Liquidity reserves are tight with Current Ratio at **${ratios.currentRatio.toFixed(2)}x**. While short-term assets match liabilities, cash buffers are susceptible to debtor collection lags. Working capital cycle requires close monitoring.\n\n`;
    } else {
      narrative += `**Critical Liquidity Stress Detected**: Current liabilities exceed current assets (Current Ratio: **${ratios.currentRatio.toFixed(2)}x**), exposing the borrower to immediate operational liquidity shortfalls unless supplemented by subordinated lines.\n\n`;
    }

    narrative += `**3. Solvency & Debt Servicing Headroom:**\n`;
    if (ratios.debtEquityRatio <= 1.5) {
      narrative += `The balance sheet is conservatively geared with a Debt-to-Equity multiplier of **${ratios.debtEquityRatio.toFixed(2)}x** and Interest Coverage Ratio (ICR) of **${ratios.interestCoverageRatio >= 90 ? '>50x' : ratios.interestCoverageRatio.toFixed(2) + 'x'}**, providing substantial headroom for interest and principal repayment obligations.\n\n`;
    } else if (ratios.debtEquityRatio <= 2.5) {
      narrative += `Leverage is moderately elevated at **${ratios.debtEquityRatio.toFixed(2)}x** D/E. Operating profit (EBIT) covers interest expenses by **${ratios.interestCoverageRatio.toFixed(2)}x**. Further unhedged debt expansion should be constrained.\n\n`;
    } else {
      narrative += `**Extreme Financial Leverage Alert**: Debt-to-Equity is **${ratios.debtEquityRatio.toFixed(2)}x**, significantly above the 2.0x threshold. Interest coverage is strained at **${ratios.interestCoverageRatio.toFixed(2)}x**, elevating default vulnerability.\n\n`;
    }

    narrative += `**4. Committee Sanction Recommendations & Terms:**\n`;
    if (recommendation === 'Approve') {
      narrative += `• Recommended credit facility limit: **INR ${assessment.recommendedCreditLimit} Crores**.\n• Suggested pricing spread: **${assessment.recommendedInterestSpread}**.\n• Security structure: Hypothecation of current assets and standard plant machinery.\n• Stipulate quarterly drawing power submissions.`;
    } else if (recommendation === 'Conditional Approval') {
      narrative += `• Sanction subject to special covenants: Limit exposure to **INR ${assessment.recommendedCreditLimit} Crores**.\n• Mandatory condition: Personal guarantees of promoter directors and escrow on primary revenue accounts.\n• Stipulate minimum Current Ratio of 1.25x throughout facility tenure.`;
    } else if (recommendation === 'Review Required') {
      narrative += `• Refer dossier to Central Credit Risk Committee.\n• Require tangible collateral coverage of at least 150% and external credit enhancement.\n• Conduct forensic verification of aged debtors over 90 days.`;
    } else {
      narrative += `• **Decline Credit Facility Application** due to non-compliance with prudential norms.\n• Re-application contingent upon formal recapitalization and demonstrated consecutive quarters of positive operating profits.`;
    }

    return narrative;
  };

  const handleRefresh = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setAiAnalysis(generateNarrative());
      setIsGenerating(false);
    }, 400);
  };

  const content = aiAnalysis || generateNarrative();

  return (
    <div className="bg-gradient-to-br from-slate-900 via-slate-850 to-indigo-950/40 border border-indigo-900/40 rounded-2xl p-5 lg:p-6 shadow-xl relative overflow-hidden">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
            <BrainCircuit className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span>Financial Intelligence &amp; Credit Insights</span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Institutional AI Engine
              </span>
            </h3>
            <p className="text-xs text-slate-400">Automated underwriting synthesis for Credit Appraisal Memorandum</p>
          </div>
        </div>

        <button
          onClick={handleRefresh}
          disabled={isGenerating}
          className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-semibold border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
          <span>Regenerate</span>
        </button>
      </div>

      {/* Narrative Output */}
      <div className="mt-4 text-xs text-slate-300 space-y-3 leading-relaxed whitespace-pre-line bg-slate-900/70 p-4 rounded-xl border border-slate-800 font-sans">
        {content}
      </div>
    </div>
  );
};
