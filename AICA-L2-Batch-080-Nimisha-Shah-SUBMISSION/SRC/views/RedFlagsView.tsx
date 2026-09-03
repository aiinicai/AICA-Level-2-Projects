import React, { useState } from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  AlertOctagon, 
  CheckCircle2, 
  XCircle, 
  TrendingDown, 
  Scissors, 
  Scale, 
  ExternalLink,
  Layers,
  Calendar
} from 'lucide-react';
import { ListedCompany, CurrencyCode, UnitScale } from '../types/financial';
import { LISTED_COMPANIES, getResolvedCompanyFinancials } from '../data/listedCompaniesDataset';
import { formatFinancialValue, getCurrencyUnitLabel } from '../utils/formatUtils';

interface RedFlagsViewProps {
  currentCompany: ListedCompany;
  onSelectCompany: (code: string) => void;
  companies?: ListedCompany[];
  selectedPeriod?: string;
  currency?: CurrencyCode;
  scale?: UnitScale;
}

export const RedFlagsView: React.FC<RedFlagsViewProps> = ({ 
  currentCompany, 
  onSelectCompany, 
  companies = LISTED_COMPANIES,
  selectedPeriod = 'latest',
  currency = 'INR',
  scale = 'crores'
}) => {
  const [universeFilter, setUniverseFilter] = useState<'ALL' | 'HIGH_LEVERAGE' | 'WEAK_COVERAGE' | 'NEGATIVE_SCISSORS' | 'NET_LOSS'>('ALL');
  const fin = getResolvedCompanyFinancials(currentCompany, selectedPeriod);

  const formatVal = (val: number) => formatFinancialValue(val, currency, scale);

  const auditTests = [
    {
      id: 'leverage',
      name: 'Balance Sheet Leverage (D/E Threshold)',
      rule: 'Debt-to-Equity Ratio must be ≤ 2.00x',
      actual: `${fin.debtToEquity.toFixed(2)}x`,
      passed: fin.debtToEquity <= 2.0,
      severity: 'HIGH RISK',
      impact: 'High debt elevates refinancing risk and leaves little safety cushion in economic downturns.',
      icon: <Scale className="w-4 h-4" />
    },
    {
      id: 'interest_coverage',
      name: 'Debt Servicing Capacity (EBIT / Interest)',
      rule: 'Interest Coverage Ratio must be ≥ 1.50x',
      actual: `${fin.interestCoverage.toFixed(1)}x`,
      passed: fin.interestCoverage >= 1.5 || fin.debt <= 10,
      severity: 'CRITICAL',
      impact: 'Low interest coverage impairs ability to meet debt obligations from operating cash flow.',
      icon: <AlertOctagon className="w-4 h-4" />
    },
    {
      id: 'operating_scissors',
      name: 'Operating Scissors Diagnostic',
      rule: 'Revenue growth must not diverge adversely from PAT growth (Sales > 0 & PAT < 0)',
      actual: `Sales ${fin.salesGrowthYoY.toFixed(1)}% vs PAT ${fin.netProfitGrowthYoY.toFixed(1)}%`,
      passed: !fin.hasOperatingScissors,
      severity: 'OPERATIONAL',
      impact: 'Topline growth paired with bottomline contraction indicates severe gross margin erosion or overhead spikes.',
      icon: <Scissors className="w-4 h-4" />
    },
    {
      id: 'roce',
      name: 'Capital Efficiency & Economic Hurdle',
      rule: 'ROCE % must exceed minimum 8.00% hurdle',
      actual: `${fin.roce.toFixed(1)}%`,
      passed: fin.roce >= 8.0 || fin.debt === 0,
      severity: 'CAPITAL DILUTION',
      impact: 'Sub-hurdle ROCE destroys economic shareholder value relative to weighted cost of capital.',
      icon: <TrendingDown className="w-4 h-4" />
    },
    {
      id: 'profitability',
      name: 'Profitability (PAT)',
      rule: 'PAT must be positive (> ₹ 0.00 Cr)',
      actual: formatVal(fin.pat),
      passed: fin.pat >= 0,
      severity: 'SOLVENCY',
      impact: 'Quarterly net loss burns capital reserves and weakens book value.',
      icon: <AlertTriangle className="w-4 h-4" />
    },
    {
      id: 'earnings_quality',
      name: 'Earnings Quality & Core Profit Reliance',
      rule: 'Other income must be ≤ 25% of EBITDA',
      actual: `${fin.otherIncomeShareOfEbidt.toFixed(1)}% of EBITDA`,
      passed: fin.otherIncomeShareOfEbidt <= 25,
      severity: 'QUALITY',
      impact: 'Excessive reliance on non-operating treasury gains masks underlying operational weakness.',
      icon: <Layers className="w-4 h-4" />
    }
  ];

  const failedCount = auditTests.filter(t => !t.passed).length;
  const passedCount = auditTests.filter(t => t.passed).length;

  const flaggedUniverse = companies.filter(c => {
    const cFin = getResolvedCompanyFinancials(c, selectedPeriod);
    if (universeFilter === 'HIGH_LEVERAGE') return cFin.debtToEquity > 2.0;
    if (universeFilter === 'WEAK_COVERAGE') return cFin.interestCoverage < 1.5 && cFin.debt > 10;
    if (universeFilter === 'NEGATIVE_SCISSORS') return cFin.hasOperatingScissors;
    if (universeFilter === 'NET_LOSS') return cFin.pat < 0;
    return cFin.debtToEquity > 1.8 || cFin.hasOperatingScissors || cFin.interestCoverage < 2.0 || cFin.pat < 0;
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Forensic Audit Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600" />
              <span>Deterministic Risk & Red Flag Audit: {currentCompany.name}</span>
              <span className="text-xs font-mono font-bold bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                <span>{fin.periodLabel}</span>
              </span>
              <span className="text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">
                {getCurrencyUnitLabel(currency, scale)}
              </span>
            </h2>
            <p className="text-xs text-slate-500">
              Deterministic 6-point financial stress, leverage, and solvency audit
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono text-slate-500">Audit Result:</span>
            <span className={`px-3 py-1 rounded-lg border text-xs font-bold font-mono ${
              failedCount === 0 
                ? 'bg-emerald-50 text-emerald-700 border-emerald-300' 
                : failedCount <= 2 
                ? 'bg-amber-50 text-amber-700 border-amber-300' 
                : 'bg-red-50 text-red-700 border-red-300'
            }`}>
              {passedCount}/6 Checks Passed ({failedCount} Red Flags)
            </span>
          </div>
        </div>

        {/* 6 Audit Test Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {auditTests.map((t) => (
            <div 
              key={t.id} 
              className={`p-4 rounded-xl border transition-all ${
                t.passed 
                  ? 'bg-white border-slate-200 hover:border-emerald-400' 
                  : 'bg-red-50/40 border-red-300 hover:border-red-400 shadow-sm'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <div className={`p-1.5 rounded ${t.passed ? 'bg-slate-100 text-slate-600' : 'bg-red-100 text-red-700'}`}>
                    {t.icon}
                  </div>
                  <span className="font-semibold text-xs text-slate-900 font-sans">{t.name}</span>
                </div>
                {t.passed ? (
                  <span className="flex items-center text-emerald-600 text-xs font-bold gap-1 font-mono">
                    <CheckCircle2 className="w-3.5 h-3.5" /> PASS
                  </span>
                ) : (
                  <span className="flex items-center text-rose-600 text-xs font-bold gap-1 font-mono">
                    <XCircle className="w-3.5 h-3.5" /> FAIL
                  </span>
                )}
              </div>

              <div className="mt-3 text-xs font-mono space-y-1">
                <div className="text-slate-500 text-[11px]">Threshold: {t.rule}</div>
                <div className="flex justify-between items-baseline pt-1">
                  <span className="text-slate-500 text-[11px]">Actual Metric:</span>
                  <span className={`font-bold ${t.passed ? 'text-blue-600' : 'text-rose-600 font-extrabold'}`}>
                    {t.actual}
                  </span>
                </div>
              </div>

              <p className="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-500 leading-relaxed font-sans">
                {t.impact}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Universe Risk & Red Flag Scanner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span>140+ Listed Universe Risk Scanner & Watchlist</span>
            </h3>
            <p className="text-xs text-slate-500">
              Automated screening identifying entities triggering leverage, coverage, or operating scissors alerts
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 text-xs font-mono">
            <button
              onClick={() => setUniverseFilter('ALL')}
              className={`px-2.5 py-1 rounded transition-colors ${
                universeFilter === 'ALL' ? 'bg-blue-600 text-white font-bold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              All Watchlist ({flaggedUniverse.length})
            </button>
            <button
              onClick={() => setUniverseFilter('HIGH_LEVERAGE')}
              className={`px-2.5 py-1 rounded transition-colors ${
                universeFilter === 'HIGH_LEVERAGE' ? 'bg-rose-600 text-white font-bold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              High D/E (&gt;2x)
            </button>
            <button
              onClick={() => setUniverseFilter('NEGATIVE_SCISSORS')}
              className={`px-2.5 py-1 rounded transition-colors ${
                universeFilter === 'NEGATIVE_SCISSORS' ? 'bg-amber-600 text-white font-bold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Operating Scissors
            </button>
            <button
              onClick={() => setUniverseFilter('NET_LOSS')}
              className={`px-2.5 py-1 rounded transition-colors ${
                universeFilter === 'NET_LOSS' ? 'bg-purple-600 text-white font-bold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Net Losses (PAT &lt; 0)
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 uppercase text-[10px] bg-slate-50">
                <th className="py-2.5 px-3">Enterprise</th>
                <th className="py-2.5 px-3">Sector</th>
                <th className="py-2.5 px-3 text-right">D/E Ratio</th>
                <th className="py-2.5 px-3 text-right">Interest Cover</th>
                <th className="py-2.5 px-3 text-right">Sales YoY</th>
                <th className="py-2.5 px-3 text-right">PAT YoY</th>
                <th className="py-2.5 px-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {flaggedUniverse.slice(0, 30).map((c) => {
                const cFin = getResolvedCompanyFinancials(c, selectedPeriod);
                return (
                  <tr key={c.bseCode} className="hover:bg-red-50/40 transition-colors">
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-slate-900 font-sans">{c.name}</div>
                      <div className="text-[10px] text-slate-500">{c.nseCode}</div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-600 font-sans">{c.sector}</td>
                    <td className={`py-2.5 px-3 text-right font-bold ${cFin.debtToEquity > 2.0 ? 'text-rose-600' : 'text-slate-800'}`}>
                      {cFin.debtToEquity.toFixed(2)}x
                    </td>
                    <td className={`py-2.5 px-3 text-right font-bold ${cFin.interestCoverage < 1.5 ? 'text-rose-600' : 'text-emerald-600'}`}>
                      {cFin.interestCoverage.toFixed(1)}x
                    </td>
                    <td className="py-2.5 px-3 text-right text-blue-600 font-bold">
                      {cFin.salesGrowthYoY >= 0 ? '+' : ''}{cFin.salesGrowthYoY.toFixed(1)}%
                    </td>
                    <td className={`py-2.5 px-3 text-right font-bold ${cFin.netProfitGrowthYoY >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {cFin.netProfitGrowthYoY >= 0 ? '+' : ''}{cFin.netProfitGrowthYoY.toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <button
                        onClick={() => onSelectCompany(c.bseCode)}
                        className="px-2 py-1 rounded bg-slate-100 hover:bg-blue-600 hover:text-white text-slate-700 text-[10px] font-sans inline-flex items-center gap-1 transition-colors"
                      >
                        <span>Deep Dive</span>
                        <ExternalLink className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
