import React, { useState } from 'react';
import { 
  Sparkles, 
  X, 
  Copy, 
  Check, 
  Send, 
  FileText, 
  TrendingUp, 
  Scale as ScaleIcon, 
  Compass, 
  Download, 
  RefreshCw,
  FileSpreadsheet,
  Cpu
} from 'lucide-react';
import { ListedCompany, FinancialPeriod, CurrencyCode, UnitScale } from '../types/financial';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import * as XLSX from 'xlsx';
import { generateAiCfoAnalysis } from '../services/geminiService';

interface AICFOAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
  company: ListedCompany;
  currentRecord: FinancialPeriod;
  currency: CurrencyCode;
  scale: UnitScale;
}

export const AICFOAssistantModal: React.FC<AICFOAssistantModalProps> = ({
  isOpen,
  onClose,
  company,
  currentRecord,
  currency,
  scale
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

  const formatCurr = (val: number) => {
    if (scale === 'lakhs') return `₹ ${(val * 100).toLocaleString('en-IN')} Lakh`;
    if (scale === 'millions') return `₹ ${(val * 10).toLocaleString('en-IN')} M`;
    return `₹ ${val.toLocaleString('en-IN')} Cr`;
  };

  // Generate Strategic Board Memo
  const generateBoardMemo = () => {
    const isScissorsAdverse = company.hasOperatingScissors;
    const isLevHigh = company.debtToEquity > 2.0;

    return `CONFIDENTIAL | BOARD OF DIRECTORS EXECUTIVE MEMORANDUM
DATE: August 26, 2026
COMPANY: ${company.name} (${company.nseCode} / BSE: ${company.bseCode})
REPORTING PERIOD: Latest Reported Quarter (Ind-AS)
EXECUTIVE SUBJECT: Financial Performance, Solvency Audit & Strategic CFO Recommendations

1. EXECUTIVE FINANCIAL HIGHLIGHTS
• Quarterly Revenue from Operations: ${formatCurr(company.salesLatestQuarter)} (${company.salesGrowthYoY >= 0 ? '+' : ''}${company.salesGrowthYoY.toFixed(1)}% YoY growth).
• Operating EBITDA: ${formatCurr(company.ebitdaLatestQuarter)} with Operating Margin (OPM) at ${company.ebitdaMargin.toFixed(1)}%.
• Net Profit After Tax (PAT): ${formatCurr(company.netProfitLatestQuarter)} (NPM: ${company.netProfitMargin.toFixed(1)}%), representing an annualized PAT run-rate of ${formatCurr(company.annualizedRunRatePAT)}.
• Capital Productivity (ROCE): ${company.roce.toFixed(1)}% generating an Economic Value Spread of ${(company.roce - 10.0).toFixed(1)}% over the 10.0% benchmark cost of capital.

2. FORENSIC MARGIN & OPERATING SCISSORS DIAGNOSTIC
${isScissorsAdverse 
  ? `• [ADVERSE SCISSORS ALERT] Topline revenue expanded by ${company.salesGrowthYoY.toFixed(1)}% YoY while bottomline PAT growth contracted/diverged at ${company.netProfitGrowthYoY.toFixed(1)}% YoY (Scissors Gap: ${company.scissorsGap.toFixed(1)}%).
• Primary Headwinds: Higher input raw material costs (${formatCurr(company.costOfMaterials)}, representing ${(company.costOfMaterials / Math.max(1, company.salesLatestQuarter) * 100).toFixed(1)}% of revenue) combined with SG&A overhead.`
  : `• [FAVORABLE MARGIN SYNC] Topline growth (${company.salesGrowthYoY.toFixed(1)}% YoY) and operating profitability are well synchronised, demonstrating positive operating leverage and disciplined cost absorption.`}

3. SOLVENCY, DEBT SERVICING & CAPITAL POSTURE
• Gearing (Debt-to-Equity): ${company.debtToEquity.toFixed(2)}x (Total Debt: ${formatCurr(company.debt)} vs Net Worth: ${formatCurr(company.netWorth)}).
• Debt Servicing Buffer: Interest Coverage stands at ${company.interestCoverage.toFixed(1)}x (${company.interestCoverage >= 3.0 ? 'SAFE / PRUDENT' : company.interestCoverage >= 1.5 ? 'ADEQUATE' : 'CRITICAL - ACTION REQUIRED'}).
${isLevHigh ? `• Risk Flag: D/E ratio exceeds the 2.0x target threshold. Priority must be allocated to debt consolidation.` : ''}

4. STRATEGIC CFO RECOMMENDATIONS FOR THE BOARD
1. Pricing & Gross Margin Defense: Implement indexed dynamic pricing on core product categories to ensure complete pass-through of commodity volatility.
2. Capital Allocation: Prioritize internally funded growth capex over external borrowings to maintain financial flexibility and protect investment-grade debt ratings.
3. Treasury & Working Capital: Optimize debtor days and streamline finished goods inventories to unlock additional free cash flow (FCF).

Submitted by:
Virtual Office of the Chief Financial Officer`;
  };

  // Generate Margin Attribution Analysis
  const generateMarginAttribution = () => {
    return `EXECUTIVE MARGIN DRIVER ATTRIBUTION REPORT
COMPANY: ${company.name}

1. MARGIN WATERFALL SUMMARY:
• Gross Operating Margin (OPM): ${company.ebitdaMargin.toFixed(1)}%
• Net Profit Margin (NPM): ${company.netProfitMargin.toFixed(1)}%

2. COST STRUCTURE COMPOSITION (% OF SALES):
• Cost of Materials & COGS: ${(company.costOfMaterials / Math.max(1, company.salesLatestQuarter) * 100).toFixed(1)}% (${formatCurr(company.costOfMaterials)})
• Employee Benefit Expenses: ${(company.employeeExpenses / Math.max(1, company.salesLatestQuarter) * 100).toFixed(1)}% (${formatCurr(company.employeeExpenses)})
• Other SG&A Overhead: ${(company.otherOperatingExpenses / Math.max(1, company.salesLatestQuarter) * 100).toFixed(1)}% (${formatCurr(company.otherOperatingExpenses)})
• Depreciation & Amortization: ${(company.depreciation / Math.max(1, company.salesLatestQuarter) * 100).toFixed(1)}% (${formatCurr(company.depreciation)})
• Finance Interest Servicing: ${(company.financeCosts / Math.max(1, company.salesLatestQuarter) * 100).toFixed(1)}% (${formatCurr(company.financeCosts)})

3. EARNINGS QUALITY ATTRIBUTION:
• Other / Treasury Income: ${formatCurr(company.otherIncomeLatestQuarter)} (${company.otherIncomeShareOfEbidt.toFixed(1)}% of EBITDA)
${company.otherIncomeShareOfEbidt > 25 ? '• Warning: High reliance on non-operating treasury income masks underlying operational compression.' : '• Core operating earnings demonstrate strong cash earnings sustainability.'}`;
  };

  // Generate Capital Allocation Strategy
  const generateCapitalAllocation = () => {
    return `STRATEGIC CAPITAL ALLOCATION & DELEVERAGING FRAMEWORK
COMPANY: ${company.name}

1. CAPITAL DEPLOYMENT DISCIPLINE:
• Total Capital Employed: ${formatCurr(company.capitalEmployed)}
• Return on Capital Employed (ROCE): ${company.roce.toFixed(1)}% vs 10.0% Hurdle Rate

2. DEBT & LEVERAGE POSTURE:
• Current D/E: ${company.debtToEquity.toFixed(2)}x
• Total Borrowings: ${formatCurr(company.debt)}
• Annual Interest Cost Burden: ${formatCurr(company.financeCosts * 4)}

3. STRATEGIC CFO DIRECTIVES:
${company.debtToEquity > 1.5 
  ? `• PRIORITY 1 - DELEVERAGING: Direct 60% of operating cash flows toward debt reduction to restore D/E below 1.0x and expand interest coverage above 3.0x.
• PRIORITY 2 - SELECTIVE CAPEX: Restrict expansion capex to high-ROI projects with internal rate of return (IRR) > 18%.
• PRIORITY 3 - PRUDENT PAYOUTS: Maintain dividend yield at ${company.dividendYield.toFixed(2)}% to conserve capital.`
  : `• PRIORITY 1 - GROWTH CAPEX: Balance sheet is lightly geared (D/E: ${company.debtToEquity.toFixed(2)}x). Accelerate high-value organic capacity expansion and technological automation.
• PRIORITY 2 - SHAREHOLDER RETURNS: Support progressive dividend payouts and opportunistic share repurchases.
• PRIORITY 3 - TREASURY EFFICIENCY: Maintain liquidity buffer in high-grade liquid funds.`}`;
  };

  // Generate DuPont Analysis
  const generateDuPontAnalysis = () => {
    const netProfitMargin = company.netProfitMargin;
    const assetTurnover = company.salesLatestQuarter > 0 && company.capitalEmployed > 0 ? (company.salesLatestQuarter * 4) / company.capitalEmployed : 1.2;
    const equityMultiplier = company.netWorth > 0 ? company.capitalEmployed / company.netWorth : 1.5;
    const computedROE = (netProfitMargin / 100) * assetTurnover * equityMultiplier * 100;

    return `DUPONT 3-STAGE ROE DECOMPOSITION DIAGNOSTIC
COMPANY: ${company.name}

FORMULA: ROE = Net Profit Margin × Asset Turnover × Equity Multiplier (Financial Leverage)

1. THREE DRIVER DECOMPOSITION:
• Driver 1: Net Profit Margin (Operating Efficiency): ${netProfitMargin.toFixed(1)}%
• Driver 2: Capital Asset Turnover (Asset Productivity): ${assetTurnover.toFixed(2)}x
• Driver 3: Equity Multiplier (Financial Leverage): ${equityMultiplier.toFixed(2)}x

2. SYNTHESIS:
• Computed ROE: ${computedROE.toFixed(1)}%
• Core Value Engine: ${netProfitMargin > 12 ? 'High profit margins driven by brand pricing power' : assetTurnover > 1.5 ? 'High velocity volume throughput' : 'Leverage amplified capital structure'}.`;
  };

  const getActiveContent = () => {
    switch (selectedTemplate) {
      case 'board_memo': return generateBoardMemo();
      case 'margin_attribution': return generateMarginAttribution();
      case 'capital_allocation': return generateCapitalAllocation();
      case 'dupont': return generateDuPontAnalysis();
      case 'custom': return null;
    }
  };

  const exportPDF = () => {
    const doc = new jsPDF();
    doc.setFillColor(15, 23, 42);
    doc.rect(0, 0, 210, 35, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(15);
    doc.setFont('helvetica', 'bold');
    doc.text('CFO FINANCIAL INTELLIGENCE & BOARD MEMORANDUM', 14, 16);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(147, 197, 253);
    doc.text(`${company.name} (${company.nseCode}) | BSE: ${company.bseCode}`, 14, 25);

    autoTable(doc, {
      startY: 42,
      head: [['Metric', 'Quarterly Actual', 'Ratio / Growth %', 'Audit Status']],
      body: [
        ['Revenue from Operations', `₹ ${company.salesLatestQuarter.toLocaleString('en-IN')} Cr`, `${company.salesGrowthYoY.toFixed(1)}% YoY`, 'Topline Volume'],
        ['Operating EBITDA', `₹ ${company.ebitdaLatestQuarter.toLocaleString('en-IN')} Cr`, `OPM: ${company.ebitdaMargin.toFixed(1)}%`, company.ebitdaMargin >= 15 ? 'Healthy' : 'Moderate'],
        ['Net Profit (PAT)', `₹ ${company.netProfitLatestQuarter.toLocaleString('en-IN')} Cr`, `NPM: ${company.netProfitMargin.toFixed(1)}%`, company.netProfitLatestQuarter >= 0 ? 'Profitable' : 'Loss'],
        ['Debt-to-Equity', `${company.debtToEquity.toFixed(2)}x`, `Debt: ₹ ${company.debt.toLocaleString('en-IN')} Cr`, company.debtToEquity <= 1.0 ? 'Prudent' : 'Elevated'],
        ['Interest Coverage', `${company.interestCoverage.toFixed(1)}x`, `Finance Cost: ₹ ${company.financeCosts.toLocaleString('en-IN')} Cr`, company.interestCoverage >= 3.0 ? 'Safe' : 'Watchlist'],
        ['ROCE %', `${company.roce.toFixed(1)}%`, `Spread: ${(company.roce - 10).toFixed(1)}%`, company.roce >= 10.0 ? 'Value Accretive' : 'Sub-Hurdle']
      ],
      theme: 'grid',
      headStyles: { fillColor: [37, 99, 235], textColor: [255, 255, 255], fontStyle: 'bold' }
    });

    const finalY = (doc as any).lastAutoTable.finalY || 100;
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(15, 23, 42);
    doc.text('Strategic CFO Analysis & Board Directives:', 14, finalY + 10);

    doc.setFontSize(8.5);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(51, 65, 85);
    const splitText = doc.splitTextToSize(getActiveContent() || '', 180);
    doc.text(splitText, 14, finalY + 18);

    doc.save(`${company.nseCode}_Board_Memo.pdf`);
  };

  const exportExcel = () => {
    const wb = XLSX.utils.book_new();
    const data = [
      { Metric: 'Company Name', Value: company.name },
      { Metric: 'NSE / BSE Ticker', Value: `${company.nseCode} / ${company.bseCode}` },
      { Metric: 'Sector', Value: company.sector },
      { Metric: 'Market Cap (₹ Cr)', Value: company.marketCap },
      { Metric: 'Revenue from Operations (₹ Cr)', Value: company.salesLatestQuarter },
      { Metric: 'Operating EBITDA (₹ Cr)', Value: company.ebitdaLatestQuarter },
      { Metric: 'Net Profit PAT (₹ Cr)', Value: company.netProfitLatestQuarter },
      { Metric: 'Debt-to-Equity (x)', Value: company.debtToEquity },
      { Metric: 'Interest Coverage (x)', Value: company.interestCoverage },
      { Metric: 'ROCE %', Value: company.roce }
    ];
    const ws = XLSX.utils.json_to_sheet(data);
    XLSX.utils.book_append_sheet(wb, ws, 'Executive Snapshot');
    XLSX.writeFile(wb, `${company.nseCode}_Financial_Summary.xlsx`);
  };

  const handleSendCustom = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customQuestion.trim()) return;

    setIsGenerating(true);
    const q = customQuestion;
    setCustomQuestion('');

    const metricsContext = {
      revenue: company.salesLatestQuarter,
      salesYoYGrowth: company.salesGrowthYoY,
      otherIncome: company.otherIncomeLatestQuarter,
      ebitda: company.ebitdaLatestQuarter,
      opmPercent: company.ebitdaMargin,
      pat: company.netProfitLatestQuarter,
      patYoYGrowth: company.netProfitGrowthYoY,
      npmPercent: company.netProfitMargin,
      annualizedPATRunRate: company.annualizedRunRatePAT,
      totalDebt: company.debt,
      netWorth: company.netWorth,
      debtToEquity: company.debtToEquity,
      interestCoverage: company.interestCoverage,
      rocePercent: company.roce,
      economicSpread: company.roce - 10.0,
      hasNegativeScissors: company.hasOperatingScissors,
      overallRiskScore: 88,
      riskRating: 'Investment Grade'
    };

    try {
      const res = await generateAiCfoAnalysis(q, company, metricsContext, 'Latest Reported Quarter');
      setCustomResponses(prev => [...prev, { q, a: res.text, source: res.source, model: res.model }]);
    } catch (err: any) {
      setCustomResponses(prev => [
        ...prev, 
        { 
          q, 
          a: `Strategic analysis error: ${err.message}. Grounded in reported financials, ${company.shortName} exhibits ROCE of ${company.roce.toFixed(1)}% and D/E of ${company.debtToEquity.toFixed(2)}x.`,
          source: 'deterministic_fallback'
        }
      ]);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/75 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-4xl max-h-[90vh] shadow-2xl flex flex-col overflow-hidden text-slate-800">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center shadow-lg">
              <Sparkles className="w-4 h-4 text-yellow-300 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white">AI CFO Strategic Assistant</h2>
                <span className="text-xs font-mono bg-purple-950 text-purple-300 px-2 py-0.5 rounded border border-purple-700">
                  {company.shortName} &bull; {company.nseCode}
                </span>
                <span className="text-[10px] font-mono bg-emerald-950 text-emerald-300 px-2.5 py-0.5 rounded border border-emerald-700 flex items-center gap-1.5 shadow-xs">
                  <Cpu className="w-3 h-3 text-emerald-400" />
                  <span>Cloud AI / Deterministic Engine Active</span>
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Grounded executive corporate finance advisory & automated board memorandum drafter
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Template Switcher Bar */}
        <div className="px-6 py-2.5 bg-slate-100 border-b border-slate-200 flex items-center space-x-2 overflow-x-auto text-xs font-mono">
          <button
            onClick={() => setSelectedTemplate('board_memo')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer ${
              selectedTemplate === 'board_memo' ? 'bg-purple-600 text-white font-bold shadow' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Board Memo</span>
          </button>
          <button
            onClick={() => setSelectedTemplate('margin_attribution')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer ${
              selectedTemplate === 'margin_attribution' ? 'bg-purple-600 text-white font-bold shadow' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Margin Drivers</span>
          </button>
          <button
            onClick={() => setSelectedTemplate('capital_allocation')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer ${
              selectedTemplate === 'capital_allocation' ? 'bg-purple-600 text-white font-bold shadow' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
            }`}
          >
            <ScaleIcon className="w-3.5 h-3.5" />
            <span>Capital Allocation</span>
          </button>
          <button
            onClick={() => setSelectedTemplate('dupont')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer ${
              selectedTemplate === 'dupont' ? 'bg-purple-600 text-white font-bold shadow' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>DuPont 3-Stage</span>
          </button>
          <button
            onClick={() => setSelectedTemplate('custom')}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all cursor-pointer ${
              selectedTemplate === 'custom' ? 'bg-purple-600 text-white font-bold shadow' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Interactive CFO Chat</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4">
          {selectedTemplate !== 'custom' ? (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 font-mono text-xs text-slate-800 whitespace-pre-wrap leading-relaxed shadow-inner">
              {getActiveContent()}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl text-xs text-purple-900 space-y-1 font-sans">
                <div className="font-bold flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-purple-600" />
                  <span>Strategic Executive Assistant Chat</span>
                </div>
                <p className="text-purple-700">
                  Ask targeted corporate finance questions on leverage, operating scissors, valuation, or margin expansion. Securely routed server-side via Cloud AI (Gemini) with deterministic offline fallback.
                </p>
              </div>

              {/* Chat history */}
              {customResponses.map((item, idx) => (
                <div key={idx} className="space-y-2 text-xs font-mono">
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-900 font-semibold">
                    Q: {item.q}
                  </div>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 whitespace-pre-wrap shadow-inner leading-relaxed space-y-2">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-[10px]">
                      <span className="font-bold text-slate-600">Executive Strategic Response</span>
                      {item.source === 'cloud_ai' ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold border border-emerald-300 flex items-center gap-1">
                          <Cpu className="w-3 h-3 text-emerald-600" />
                          <span>Cloud AI ({item.model || 'Gemini 2.5 Flash'})</span>
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-slate-200 text-slate-700 font-bold border border-slate-300 flex items-center gap-1">
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
                  className="flex-1 px-4 py-2 bg-white border border-slate-300 rounded-xl text-xs focus:outline-none focus:border-purple-600 shadow-xs"
                  disabled={isGenerating}
                />
                <button
                  type="submit"
                  disabled={isGenerating || !customQuestion.trim()}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition-colors shadow flex items-center gap-1.5 cursor-pointer"
                >
                  {isGenerating ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  <span>{isGenerating ? 'Analyzing...' : 'Ask CFO'}</span>
                </button>
              </form>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {selectedTemplate !== 'custom' && (
              <button
                onClick={() => handleCopy(getActiveContent() || '')}
                className="px-3 py-1.5 bg-white hover:bg-slate-100 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 flex items-center gap-1.5 transition-colors shadow-2xs cursor-pointer"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy Text'}</span>
              </button>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={exportExcel}
              className="px-3 py-1.5 bg-white hover:bg-slate-100 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 flex items-center gap-1.5 transition-colors shadow-2xs cursor-pointer"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
              <span>Export Summary (.xlsx)</span>
            </button>
            <button
              onClick={exportPDF}
              className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors shadow-2xs cursor-pointer"
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
