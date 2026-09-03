import React from 'react';
import { BookOpen, Code2, Calculator, Database, CheckCircle2, ShieldAlert } from 'lucide-react';
import { getAvailableSectors, getAllCompanies } from '../data/companiesData';

export const DataSchemaView: React.FC = () => {
  const sectors = getAvailableSectors();
  const allCompanies = getAllCompanies();

  const formulaSpecs = [
    {
      metric: 'Net Worth / Shareholders Equity',
      formula: 'Paid-up Equity Share Capital + Reserves & Surplus (Excl. Reval. Reserves)',
      latex: 'Net Worth = EquityCapital + Reserves',
      unit: '₹ Crores',
      importance: 'Fundamental asset anchor representing the book equity value belonging to equity holders.'
    },
    {
      metric: 'Debt-to-Equity Ratio (D/E)',
      formula: '(Long-Term Borrowings + Short-Term Borrowings) / Net Worth',
      latex: 'D/E = \\frac{LongTermDebt + ShortTermDebt}{NetWorth}',
      unit: 'x (Multiple)',
      importance: 'Measures financial leverage and capital gearing. Flagged as High Leverage when > 2.0x.'
    },
    {
      metric: 'Interest Coverage Ratio (ICR)',
      formula: 'EBIT (Operating Profit) / Gross Finance Costs',
      latex: 'ICR = \\frac{EBIT}{FinanceCosts}',
      unit: 'x (Multiple)',
      importance: 'Assesses debt-servicing buffer. Safe > 3.0x, Adequate 1.5–3.0x, Critical Distress < 1.5x.'
    },
    {
      metric: 'Operating Profit Margin (OPM %)',
      formula: '(Operating EBITDA [Excl. Other Income] / Revenue from Operations) * 100',
      latex: 'OPM\\% = \\left(\\frac{EBITDA_{core}}{Revenue}\\right) \\times 100',
      unit: '%',
      importance: 'Pure operational profitability indicator isolating core business economics from non-operating noise.'
    },
    {
      metric: 'Quarterly Net Profit Margin (NPM %)',
      formula: '(Profit After Tax / Total Revenue) * 100',
      latex: 'NPM\\% = \\left(\\frac{PAT}{TotalRevenue}\\right) \\times 100',
      unit: '%',
      importance: 'Final bottomline conversion rate after operating costs, D&A, interest, and corporate income taxes.'
    },
    {
      metric: 'Annualized PAT Run-Rate',
      formula: 'Quarterly PAT * 4',
      latex: 'RunRate = PAT_{quarter} \\times 4',
      unit: '₹ Crores / Year',
      importance: 'Annualized earnings trajectory used for run-rate P/E multiples and corporate valuation.'
    },
    {
      metric: 'Operating Scissors Diagnostic',
      formula: 'Topline YoY Sales Growth % - Bottomline YoY PAT Growth %',
      latex: 'ScissorsGap = g_{Sales} - g_{PAT}',
      unit: '% Gap',
      importance: 'Detects profit squeeze where revenue expands while profits shrink (Adverse scissors).'
    },
    {
      metric: 'Return on Capital Employed (ROCE %)',
      formula: '((EBIT * 4) / (Net Worth + Total Debt)) * 100',
      latex: 'ROCE\\% = \\left(\\frac{EBIT \\times 4}{CapitalEmployed}\\right) \\times 100',
      unit: '%',
      importance: 'Measures capital productivity across all invested debt and equity capital.'
    },
    {
      metric: 'Economic Spread',
      formula: 'ROCE % - Benchmark Cost of Capital (10.0%)',
      latex: 'EconomicSpread = ROCE\\% - WACC_{hurdle}',
      unit: '% Spread',
      importance: 'Determines whether the business is creating economic shareholder value (Spread > 0) or destroying capital.'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Platform Architecture & Data Dictionary Header */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex items-center space-x-3 pb-4 border-b border-gray-800">
          <div className="w-9 h-9 rounded-lg bg-blue-900/50 text-blue-400 flex items-center justify-center border border-blue-700/40">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">
              CFO Platform Calculation Engine & Data Architecture Schema
            </h2>
            <p className="text-xs text-gray-400">
              Deterministic definitions, mathematical formulas, and coverage metadata
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-3.5 bg-[#0B0F19] border border-gray-800 rounded-lg space-y-1">
            <span className="text-gray-400 uppercase text-[10px]">Universe Coverage</span>
            <div className="text-xl font-bold text-white">{allCompanies.length} Listed Enterprises</div>
            <span className="text-[11px] text-cyan-400">Top Marquee Large & Mid Caps</span>
          </div>
          <div className="p-3.5 bg-[#0B0F19] border border-gray-800 rounded-lg space-y-1">
            <span className="text-gray-400 uppercase text-[10px]">Industry Sectors</span>
            <div className="text-xl font-bold text-blue-400">{sectors.length} Sector Classifications</div>
            <span className="text-[11px] text-gray-400">Full Indian Economy Coverage</span>
          </div>
          <div className="p-3.5 bg-[#0B0F19] border border-gray-800 rounded-lg space-y-1">
            <span className="text-gray-400 uppercase text-[10px]">Reporting Standard</span>
            <div className="text-xl font-bold text-emerald-400">Ind-AS & SEBI LODR</div>
            <span className="text-[11px] text-gray-400">Multi-Period Statements</span>
          </div>
        </div>
      </div>

      {/* Deterministic Financial Formulas Reference */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 pb-3 border-b border-gray-800">
          <Calculator className="w-4 h-4 text-cyan-400" />
          <span>Deterministic Formula Specifications & Business Logic</span>
        </h3>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {formulaSpecs.map((spec, idx) => (
            <div key={idx} className="p-4 bg-[#0B0F19] border border-gray-800/80 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white font-sans">{spec.metric}</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-gray-800 text-cyan-300 border border-gray-700">
                  {spec.unit}
                </span>
              </div>
              <div className="p-2.5 bg-gray-900 rounded border border-gray-800 font-mono text-xs text-blue-300">
                <code>{spec.formula}</code>
              </div>
              <p className="text-[11px] text-gray-400 leading-relaxed font-sans">
                {spec.importance}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Sector Groups Universe List */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 pb-3 border-b border-gray-800">
          <Database className="w-4 h-4 text-purple-400" />
          <span>Active Industry Sectors in Data Lake ({sectors.length} Groups)</span>
        </h3>

        <div className="flex flex-wrap gap-2">
          {sectors.map((s, idx) => {
            const count = allCompanies.filter(c => c.sector === s).length;
            return (
              <span 
                key={idx} 
                className="px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-800 text-xs font-sans text-gray-300 flex items-center gap-2"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                <span>{s}</span>
                <span className="text-[10px] font-mono bg-gray-800 text-cyan-300 px-1.5 py-0.5 rounded">
                  {count}
                </span>
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
};
