import React, { useState } from 'react';
import { 
  Sparkles, 
  X, 
  Copy, 
  Check, 
  Send, 
  FileText, 
  TrendingUp, 
  Scale, 
  Compass, 
  Download, 
  RefreshCw,
  FileSpreadsheet,
  Cpu
} from 'lucide-react';
import { CompanyEntity, DeterministicMetrics, CurrencyUnit, PeriodId } from '../types/finance';
import { formatCurrency, formatMultiple, formatPercent } from '../utils/financialCalculations';
import { exportBoardMemoToPdf, exportCompanyToExcel } from '../utils/exportUtils';
import { generateAiCfoAnalysis } from '../services/geminiService';

interface AiCfoAdvisorModalProps {
  isOpen: boolean;
  onClose: () => void;
  company: CompanyEntity;
  metrics: DeterministicMetrics;
  periodId: PeriodId;
  currencyUnit: CurrencyUnit;
}

export const AiCfoAdvisorModal: React.FC<AiCfoAdvisorModalProps> = ({
  isOpen,
  onClose,
  company,
  metrics,
  periodId,
  currencyUnit
}) => {
  const [selectedTemplate, setSelectedTemplate] = useState<'board_memo' | 'margin_attribution' | 'capital_allocation' | 'dupont' | 'custom'>('board_memo');
  const [customQuestion, setCustomQuestion] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [customResponses, setCustomResponses] = useState<Array<{ q: string; a: string; source?: 'cloud_ai' | 'deterministic_fallback'; model?: string }>>([]);

  if (!isOpen) return null;

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Generate Strategic Board Memo
  const generateBoardMemo = () => {
    const isScissorsAdverse = metrics.hasNegativeScissors;
    const isLevHigh = metrics.debtToEquity > 2.0;

    return `CONFIDENTIAL | BOARD OF DIRECTORS EXECUTIVE MEMORANDUM
DATE: August 26, 2026
COMPANY: ${company.name} (${company.ticker} / BSE: ${company.bseCode})
REPORTING PERIOD: ${periodId} (Ind-AS Format)
EXECUTIVE SUBJECT: Comprehensive Financial Audit & Strategic CFO Directives

1. EXECUTIVE FINANCIAL HIGHLIGHTS
• Revenue from Operations: ${formatCurrency(metrics.revenue, currencyUnit)} (${formatPercent(metrics.salesYoYGrowth, 1, true)} YoY growth).
• Operating EBITDA: ${formatCurrency(metrics.ebitda, currencyUnit)} with Operating Margin (OPM) at ${formatPercent(metrics.opmPercent, 1)}.
• Net Profit After Tax (PAT): ${formatCurrency(metrics.pat, currencyUnit)} (NPM: ${formatPercent(metrics.npmPercent, 1)}), representing an annualized PAT run-rate of ${formatCurrency(metrics.annualizedPATRunRate, currencyUnit)}.
• Capital Productivity (ROCE): ${formatPercent(metrics.rocePercent, 1)} generating an Economic Value Spread of ${formatPercent(metrics.economicSpread, 1, true)} over the 10.0% benchmark cost of capital.

2. FORENSIC MARGIN & OPERATING SCISSORS DIAGNOSTIC
${isScissorsAdverse 
  ? `• [ADVERSE SCISSORS ALERT] Topline revenue expanded by ${formatPercent(metrics.salesYoYGrowth, 1, true)} YoY while bottomline PAT growth contracted at ${formatPercent(metrics.patYoYGrowth, 1, true)} YoY.
• Primary Headwinds: Severe gross margin compression due to unhedged raw material cost increases and elevated fixed overhead absorption.`
  : `• [FAVORABLE MARGIN SYNC] Topline growth (${formatPercent(metrics.salesYoYGrowth, 1, true)} YoY) and operating profitability are well synchronised, demonstrating positive operating leverage and disciplined pricing power.`}

3. SOLVENCY, DEBT SERVICING & CAPITAL POSTURE
• Gearing (Debt-to-Equity): ${formatMultiple(metrics.debtToEquity)} (Total Debt: ${formatCurrency(metrics.totalDebt, currencyUnit)} vs Net Worth: ${formatCurrency(metrics.netWorth, currencyUnit)}).
• Debt Servicing Buffer: Interest Coverage stands at ${formatMultiple(metrics.interestCoverage)} (${metrics.interestCoverage >= 3.0 ? 'SAFE / PRUDENT' : metrics.interestCoverage >= 1.5 ? 'ADEQUATE' : 'CRITICAL - ACTION REQUIRED'}).
${isLevHigh ? `• Leverage Alert: D/E ratio exceeds the 2.0x threshold. Priority must be allocated to debt retirement.` : ''}

4. STRATEGIC CFO RECOMMENDATIONS FOR THE BOARD
1. Pricing & Margin Defense: Introduce dynamic cost-plus indexed contracts for key B2B counterparties to preserve core operating margins.
2. Capital Allocation: Prioritize internal cash flow funding for ongoing capex over debt issuance.
3. Treasury & Working Capital: Tighten receivables collection and rationalize inventory holding to unlock free cash flows.

Submitted by:
Virtual Office of the Chief Financial Officer`;
  };

  // Generate Margin Attribution Analysis
  const generateMarginAttribution = () => {
    const grossMargin = ((metrics.revenue - metrics.rawMaterialCost) / Math.max(1, metrics.revenue)) * 100;
    const cogsRatio = (metrics.rawMaterialCost / Math.max(1, metrics.revenue)) * 100;
    const employeeCostRatio = (metrics.employeeCost / Math.max(1, metrics.revenue)) * 100;
    const otherOpexRatio = (metrics.otherOperatingExpenses / Math.max(1, metrics.revenue)) * 100;
    const interestRatio = (metrics.financeCosts / Math.max(1, metrics.revenue)) * 100;
    const depreciationRatio = (metrics.depreciation / Math.max(1, metrics.revenue)) * 100;
    const otherIncomeToEbitdaRatio = (metrics.otherIncome / Math.max(1, metrics.ebitda)) * 100;

    return `EXECUTIVE MARGIN DRIVER ATTRIBUTION REPORT
COMPANY: ${company.name} | PERIOD: ${periodId}

1. MARGIN WATERFALL:
• Operating EBITDA Margin (OPM): ${formatPercent(metrics.opmPercent, 1)}
• Net Profit Margin (NPM): ${formatPercent(metrics.npmPercent, 1)}
• Gross Margin: ${formatPercent(grossMargin, 1)}

2. COST STRUCTURE RATIOS (% OF REVENUE):
• Raw Materials & COGS: ${formatPercent(cogsRatio, 1)}
• Employee Benefit Expenses: ${formatPercent(employeeCostRatio, 1)}
• Other SG&A Overhead: ${formatPercent(otherOpexRatio, 1)}
• Finance Interest Servicing: ${formatPercent(interestRatio, 1)}
• Depreciation & Amortization: ${formatPercent(depreciationRatio, 1)}

3. EARNINGS QUALITY ATTRIBUTION:
• Treasury / Other Income: ${formatCurrency(metrics.otherIncome, currencyUnit)} (${formatPercent(otherIncomeToEbitdaRatio, 1)} of EBITDA)
${otherIncomeToEbitdaRatio > 25 ? '• Warning: High reliance on non-operating treasury income masks underlying operational compression.' : '• Core operating earnings demonstrate strong cash earnings sustainability.'}`;
  };

  // Generate Capital Allocation Strategy
  const generateCapitalAllocation = () => {
    const annualizedFinanceCost = metrics.financeCosts * 4;

    return `STRATEGIC CAPITAL ALLOCATION & DELEVERAGING FRAMEWORK
COMPANY: ${company.name} | PERIOD: ${periodId}

1. CAPITAL DEPLOYMENT DISCIPLINE:
• Total Capital Employed: ${formatCurrency(metrics.capitalEmployed, currencyUnit)}
• Return on Capital Employed (ROCE): ${formatPercent(metrics.rocePercent, 1)} vs 10.0% Hurdle Rate
• Economic Value Created: ${formatPercent(metrics.economicSpread, 1, true)}

2. DEBT & LEVERAGE POSTURE:
• Current D/E: ${formatMultiple(metrics.debtToEquity)}
• Total Borrowings: ${formatCurrency(metrics.totalDebt, currencyUnit)}
• Annual Interest Cost Burden: ${formatCurrency(annualizedFinanceCost, currencyUnit)}

3. STRATEGIC CFO DIRECTIVES:
${metrics.debtToEquity > 1.5 
  ? `• PRIORITY 1 - DELEVERAGING: Direct 60% of operating cash flows toward debt reduction to restore D/E below 1.0x.
• PRIORITY 2 - SELECTIVE CAPEX: Restrict capex to projects with internal rate of return (IRR) > 18%.
• PRIORITY 3 - PRUDENT PAYOUTS: Moderate dividend distributions to conserve cash reserves.`
  : `• PRIORITY 1 - GROWTH CAPEX: Balance sheet is conservatively leveraged (D/E: ${formatMultiple(metrics.debtToEquity)}). Accelerate high-ROI organic capacity expansion.
• PRIORITY 2 - SHAREHOLDER RETURNS: Support progressive dividend payouts and opportunistic share buybacks.
• PRIORITY 3 - TREASURY EFFICIENCY: Optimize yield on surplus liquid funds.`}`;
  };

  // Generate DuPont Analysis
  const generateDuPontAnalysis = () => {
    const assetTurnover = metrics.capitalEmployed > 0 ? (metrics.revenue * 4) / metrics.capitalEmployed : 1.2;
    const equityMultiplier = metrics.netWorth > 0 ? metrics.capitalEmployed / metrics.netWorth : 1.5;

    return `DUPONT 3-STAGE ROE DECOMPOSITION DIAGNOSTIC
COMPANY: ${company.name} | PERIOD: ${periodId}

FORMULA: ROE = Net Profit Margin × Asset Turnover × Equity Multiplier

1. THREE DRIVER DECOMPOSITION:
• Driver 1: Net Profit Margin (Operating Efficiency): ${formatPercent(metrics.npmPercent, 1)}
• Driver 2: Capital Asset Turnover (Asset Productivity): ${formatMultiple(assetTurnover)}
• Driver 3: Equity Multiplier (Financial Leverage): ${formatMultiple(equityMultiplier)}

2. SYNTHESIS:
• Computed Return on Equity (ROE): ${formatPercent(metrics.roePercent, 1)}
• Primary Value Engine: ${metrics.npmPercent > 12 ? 'High profit margins driven by brand pricing power' : assetTurnover > 1.5 ? 'High velocity volume throughput' : 'Leverage amplified capital structure'}.`;
  };

  const getActiveContent = () => {
    switch (selectedTemplate) {
      case 'board_memo':
        return generateBoardMemo();
      case 'margin_attribution':
        return generateMarginAttribution();
      case 'capital_allocation':
        return generateCapitalAllocation();
      case 'dupont':
        return generateDuPontAnalysis();
      case 'custom':
        return null;
    }
  };

  const handleSendCustom = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customQuestion.trim()) return;

    setIsGenerating(true);
    const q = customQuestion;
    setCustomQuestion('');

    try {
      const res = await generateAiCfoAnalysis(q, company, metrics, periodId);
      setCustomResponses(prev => [...prev, { q, a: res.text, source: res.source, model: res.model }]);
    } catch (err: any) {
      setCustomResponses(prev => [
        ...prev, 
        { 
          q, 
          a: `Strategic analysis error: ${err.message}. Grounded in reported financials, ${company.shortName} exhibits ROCE of ${metrics?.rocePercent || 0}% and D/E of ${metrics?.debtToEquity || 0}x.`,
          source: 'deterministic_fallback'
        }
      ]);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[#111827] border border-gray-700 rounded-2xl w-full max-w-4xl max-h-[90vh] shadow-2xl flex flex-col overflow-hidden text-slate-100">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-gray-800 bg-[#0B0F19] flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-purple-600/30">
              <Sparkles className="w-4 h-4 text-yellow-300 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white">Virtual AI CFO Advisor</h2>
                <span className="text-xs font-mono bg-purple-950/80 text-purple-300 px-2 py-0.5 rounded border border-purple-700/50">
                  {company.shortName} &bull; {periodId}
                </span>
                <span className="text-[10px] font-mono bg-emerald-950 text-emerald-300 px-2.5 py-0.5 rounded border border-emerald-700 flex items-center gap-1.5 shadow-xs">
                  <Cpu className="w-3 h-3 text-emerald-400" />
                  <span>Cloud AI / Deterministic Engine Active</span>
                </span>
              </div>
              <p className="text-xs text-gray-400">
                Context-grounded strategic executive assistant & automated board memo drafter
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Template Switcher Bar */}
        <div className="px-6 py-2.5 bg-gray-900 border-b border-gray-800 flex items-center space-x-2 overflow-x-auto text-xs font-mono">
          <button
            onClick={() => setSelectedTemplate('board_memo')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer ${
              selectedTemplate === 'board_memo' ? 'bg-purple-600 text-white font-bold shadow-lg shadow-purple-600/30' : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Board Memo</span>
          </button>
          <button
            onClick={() => setSelectedTemplate('margin_attribution')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer ${
              selectedTemplate === 'margin_attribution' ? 'bg-purple-600 text-white font-bold shadow-lg shadow-purple-600/30' : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Margin Drivers</span>
          </button>
          <button
            onClick={() => setSelectedTemplate('capital_allocation')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer ${
              selectedTemplate === 'capital_allocation' ? 'bg-purple-600 text-white font-bold shadow-lg shadow-purple-600/30' : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <Scale className="w-3.5 h-3.5" />
            <span>Capital Allocation</span>
          </button>
          <button
            onClick={() => setSelectedTemplate('dupont')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer ${
              selectedTemplate === 'dupont' ? 'bg-purple-600 text-white font-bold shadow-lg shadow-purple-600/30' : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>DuPont 3-Stage</span>
          </button>
          <button
            onClick={() => setSelectedTemplate('custom')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer ${
              selectedTemplate === 'custom' ? 'bg-purple-600 text-white font-bold shadow-lg shadow-purple-600/30' : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Interactive CFO Chat</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4">
          {selectedTemplate !== 'custom' ? (
            <div className="bg-[#0B0F19] border border-gray-800 rounded-xl p-5 font-mono text-xs text-gray-300 whitespace-pre-wrap leading-relaxed shadow-inner">
              {getActiveContent()}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-4 bg-purple-950/30 border border-purple-800/50 rounded-xl text-xs text-purple-200 space-y-1">
                <div className="font-bold flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  <span>Strategic Executive Assistant Chat</span>
                </div>
                <p className="text-purple-300/80">
                  Ask targeted corporate finance questions on leverage, operating scissors, valuation, or margin expansion. Securely routed server-side via Cloud AI (Gemini) with deterministic offline fallback.
                </p>
              </div>

              {/* Chat history */}
              {customResponses.map((item, idx) => (
                <div key={idx} className="space-y-2 text-xs font-mono">
                  <div className="p-3 bg-blue-950/40 border border-blue-800/50 rounded-lg text-blue-200 font-semibold">
                    Q: {item.q}
                  </div>
                  <div className="p-4 bg-[#0B0F19] border border-gray-800 rounded-lg text-gray-300 whitespace-pre-wrap shadow-inner leading-relaxed space-y-2">
                    <div className="flex items-center justify-between pb-2 border-b border-gray-800 text-[10px]">
                      <span className="font-bold text-gray-400">Executive Strategic Response</span>
                      {item.source === 'cloud_ai' ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 font-bold border border-emerald-700 flex items-center gap-1">
                          <Cpu className="w-3 h-3 text-emerald-400" />
                          <span>Cloud AI ({item.model || 'Gemini 2.5 Flash'})</span>
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-300 font-bold border border-gray-700 flex items-center gap-1">
                          <span>⚙️ Deterministic Fallback Engine</span>
                        </span>
                      )}
                    </div>
                    <div>{item.a}</div>
                  </div>
                </div>
              ))}

              {/* Input box */}
              <form onSubmit={handleSendCustom} className="flex gap-2 pt-2">
                <input
                  type="text"
                  value={customQuestion}
                  onChange={(e) => setCustomQuestion(e.target.value)}
                  placeholder={`Ask strategic question about ${company.shortName}...`}
                  className="flex-1 px-4 py-2 bg-[#0B0F19] border border-gray-700 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                  disabled={isGenerating}
                />
                <button
                  type="submit"
                  disabled={isGenerating || !customQuestion.trim()}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition-colors shadow-lg shadow-purple-600/30 flex items-center gap-1.5 cursor-pointer"
                >
                  {isGenerating ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  <span>{isGenerating ? 'Analyzing...' : 'Ask CFO'}</span>
                </button>
              </form>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-gray-800 bg-[#0B0F19] flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {selectedTemplate !== 'custom' && (
              <button
                onClick={() => handleCopy(getActiveContent() || '')}
                className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs font-medium text-gray-200 flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy Text'}</span>
              </button>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => exportCompanyToExcel(company, periodId, metrics)}
              className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs font-medium text-emerald-400 border border-emerald-900/50 flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Export Summary (.xlsx)</span>
            </button>
            <button
              onClick={() => exportBoardMemoToPdf(company, metrics, periodId, getActiveContent() || '')}
              className="px-3 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors shadow-lg shadow-blue-600/30 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Board Memo (.pdf)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
