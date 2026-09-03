import { CompanyEntity, DeterministicMetrics, CurrencyUnit, PeriodId } from '../types/finance';
import { formatCurrency, formatMultiple, formatPercent } from '../utils/financialCalculations';

const COMMON_CORP_NAMES = [
  'reliance', 'tata', 'infosys', 'infy', 'hdfc', 'adani', 'wipro', 'itc', 'maruti',
  'bharti', 'airtel', 'icici', 'sbi', 'state bank', 'kotak', 'l&t', 'larson', 'bajaj',
  'zomato', 'swiggy', 'paytm', 'tvs', 'asian paints', 'ultratech', 'sun pharma', 'titan',
  'mahindra', 'm&m', 'hindustan unilever', 'hul', 'axis bank', 'ntpc', 'ongc', 'power grid',
  'coal india', 'jsw steel', 'tata steel', 'dr reddy', 'cipla', 'apollo hospitals',
  'bizedge'
];

export const runDeterministicCfoEngine = (
  prompt: string,
  company: CompanyEntity | any,
  metrics: DeterministicMetrics | any,
  periodId: PeriodId | string
): string => {
  const rev = metrics?.revenue ?? company?.salesLatestQuarter ?? 0;
  const ebitdaVal = metrics?.ebitda ?? company?.ebitdaLatestQuarter ?? 0;
  const opm = metrics?.opmPercent ?? company?.ebitdaMargin ?? 0;
  const patVal = metrics?.pat ?? company?.netProfitLatestQuarter ?? 0;
  const de = metrics?.debtToEquity ?? company?.debtToEquity ?? 0;
  const intCov = metrics?.interestCoverage ?? company?.interestCoverage ?? 0;
  const roceVal = metrics?.rocePercent ?? company?.roce ?? 0;
  const hasScissors = metrics?.hasNegativeScissors ?? company?.hasOperatingScissors ?? false;
  const economicSpread = metrics?.economicSpread ?? (roceVal - 10.0);

  const activeName = company?.name || 'Active Enterprise';
  const activeShort = company?.shortName || activeName;
  const activeTicker = company?.ticker || company?.nseCode || 'N/A';

  // Entity mismatch check: Does the user explicitly mention another well-known entity?
  const promptLower = prompt.toLowerCase();
  const activeIdentifiers = [
    activeName.toLowerCase(),
    activeShort.toLowerCase(),
    activeTicker.toLowerCase(),
    company?.bseCode ? String(company.bseCode) : ''
  ].filter(Boolean);

  const isActiveMentioned = activeIdentifiers.some(id => id.length > 2 && promptLower.includes(id));
  const otherMentionedCorp = COMMON_CORP_NAMES.find(corp => {
    const isThisActive = activeIdentifiers.some(id => id.includes(corp));
    return !isThisActive && promptLower.includes(corp);
  });

  if (otherMentionedCorp && !isActiveMentioned) {
    const formattedCorpName = otherMentionedCorp.charAt(0).toUpperCase() + otherMentionedCorp.slice(1);
    return `[ENTITY CONTEXT MISMATCH NOTICE]
⚠️ **Notice**: The currently active enterprise in this session is **${activeName} (${activeTicker})**.

Your query explicitly references **${formattedCorpName}**. To ensure analytical accuracy and prevent misattributing ${activeShort}'s financial metrics (Revenue: ₹ ${rev.toLocaleString('en-IN')} Cr, OPM: ${formatPercent(opm, 1)}, PAT: ₹ ${patVal.toLocaleString('en-IN')} Cr) to ${formattedCorpName}:

• Please select **${formattedCorpName}** from the **Company Selector** dropdown in the top navigation bar.
• Once selected, all multi-period P&L statements, solvency diagnostics, operating scissors, and AI CFO memos will dynamically ground to that enterprise.`;
  }

  return `[OFFLINE DETERMINISTIC CFO ENGINE]
Strategic analysis for ${activeName} (${activeTicker}) on "${prompt}":

• Executive Overview:
  In ${periodId}, ${activeShort} recorded ₹ ${rev.toLocaleString('en-IN')} Cr in revenue with Operating EBITDA of ₹ ${ebitdaVal.toLocaleString('en-IN')} Cr (OPM: ${formatPercent(opm, 1)}) and PAT of ₹ ${patVal.toLocaleString('en-IN')} Cr.

• Solvency & Debt Servicing:
  Gearing is ${formatMultiple(de)} D/E with an Interest Coverage Ratio of ${formatMultiple(intCov)}. ${de > 2.0 ? 'Capital structure exhibits elevated leverage requiring structured debt amortization.' : 'Balance sheet is prudently leveraged with ample solvency headroom.'}

• Profit Quality & Operating Scissors:
  ${hasScissors ? 'Adverse operating scissors detected (Topline growth outpaces profitability conversion). Immediate focus needed on raw material inflation pass-through and SG&A containment.' : 'Operating conversion is solid with disciplined margin protection.'}

• Capital Productivity:
  ROCE stands at ${formatPercent(roceVal, 1)}, creating an economic value spread of ${formatPercent(economicSpread, 1, true)} over the 10% hurdle rate.

Note: Running in deterministic offline CFO mode. Configure GEMINI_API_KEY on the backend server for live Gemini GenAI reasoning.`;
};

export interface AiCfoResponse {
  text: string;
  source: 'cloud_ai' | 'deterministic_fallback';
  model?: string;
}

export const generateAiCfoAnalysis = async (
  prompt: string,
  company: CompanyEntity | any,
  metrics: DeterministicMetrics | any,
  periodId: PeriodId | string
): Promise<AiCfoResponse> => {
  try {
    const res = await fetch('/api/cfo-memo', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        prompt,
        company,
        metrics,
        periodId
      })
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.error || `Server responded with status ${res.status}`);
    }

    const data = await res.json();
    if (data.success && data.text) {
      return {
        text: data.text,
        source: 'cloud_ai',
        model: 'Gemini 3.7 Flash'
      };
    }

    throw new Error(data.error || 'Server did not return analysis text');
  } catch (err: any) {
    console.warn('Backend Gemini API unavailable, executing deterministic offline engine:', err.message);
    const fallbackText = runDeterministicCfoEngine(prompt, company, metrics, periodId);
    return {
      text: fallbackText,
      source: 'deterministic_fallback'
    };
  }
};
