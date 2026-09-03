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
  Layers
} from 'lucide-react';
import { CompanyEntity, DeterministicMetrics, CurrencyUnit, PeriodId } from '../types/finance';
import { getAllCompanies } from '../data/companiesData';
import { calculateDeterministicMetrics, formatCurrency, formatMultiple, formatPercent } from '../utils/financialCalculations';

interface RiskAuditViewProps {
  company: CompanyEntity;
  metrics: DeterministicMetrics;
  periodId: PeriodId;
  currencyUnit: CurrencyUnit;
  onSelectCompany: (company: CompanyEntity) => void;
}

export const RiskAuditView: React.FC<RiskAuditViewProps> = ({
  company,
  metrics,
  periodId,
  currencyUnit,
  onSelectCompany
}) => {
  const [universeFilter, setUniverseFilter] = useState<'ALL' | 'HIGH_LEVERAGE' | 'WEAK_COVERAGE' | 'NEGATIVE_SCISSORS' | 'NET_LOSS'>('ALL');
  const allCompanies = getAllCompanies();

  // Audit tests for active company
  const auditTests = [
    {
      id: 'leverage',
      name: 'Balance Sheet Leverage (D/E Threshold)',
      rule: 'Debt-to-Equity Ratio must be ≤ 2.00x',
      actual: `${formatMultiple(metrics.debtToEquity)}`,
      passed: !metrics.redFlags.highLeverage,
      severity: 'HIGH RISK',
      impact: 'High debt elevates refinancing risk and leaves little safety cushion in economic downturns.',
      icon: <Scale className="w-4 h-4" />
    },
    {
      id: 'interest_coverage',
      name: 'Debt Servicing Capacity (EBIT / Interest)',
      rule: 'Interest Coverage Ratio must be ≥ 1.50x',
      actual: `${formatMultiple(metrics.interestCoverage)}`,
      passed: !metrics.redFlags.weakInterestCoverage,
      severity: 'CRITICAL',
      impact: 'Low interest coverage impairs ability to meet debt obligations from operating cash flow.',
      icon: <AlertOctagon className="w-4 h-4" />
    },
    {
      id: 'operating_scissors',
      name: 'Operating Scissors Diagnostic',
      rule: 'Revenue growth must not diverge adversely from PAT growth (Sales > 0 & PAT < 0)',
      actual: `Sales ${formatPercent(metrics.salesYoYGrowth, 1, true)} vs PAT ${formatPercent(metrics.patYoYGrowth, 1, true)}`,
      passed: !metrics.redFlags.negativeOperatingScissors,
      severity: 'OPERATIONAL',
      impact: 'Topline growth paired with bottomline contraction indicates severe gross margin erosion or overhead spikes.',
      icon: <Scissors className="w-4 h-4" />
    },
    {
      id: 'roce',
      name: 'Capital Efficiency & Economic Hurdle',
      rule: 'ROCE % must exceed minimum 8.00% hurdle',
      actual: `${formatPercent(metrics.rocePercent, 1)}`,
      passed: !metrics.redFlags.lowROCE,
      severity: 'CAPITAL DILUTION',
      impact: 'Sub-hurdle ROCE destroys economic shareholder value relative to weighted cost of capital.',
      icon: <TrendingDown className="w-4 h-4" />
    },
    {
      id: 'profitability',
      name: 'Quarterly Net Profitability (PAT)',
      rule: 'PAT must be positive (> ₹ 0.00 Cr)',
      actual: `${formatCurrency(metrics.pat, currencyUnit)}`,
      passed: !metrics.redFlags.netLossQuarter,
      severity: 'SOLVENCY',
      impact: 'Quarterly net loss burns capital reserves and weakens book value.',
      icon: <AlertTriangle className="w-4 h-4" />
    },
    {
      id: 'earnings_quality',
      name: 'Earnings Quality & Core Profit Reliance',
      rule: 'Other income must be ≤ 40% of PAT',
      actual: `${formatPercent(metrics.otherIncomeToPATShare, 1)} of PAT`,
      passed: !metrics.redFlags.severeOtherIncomeDependence,
      severity: 'QUALITY',
      impact: 'Excessive reliance on non-operating treasury gains masks underlying operational weakness.',
      icon: <Layers className="w-4 h-4" />
    }
  ];

  const failedCount = auditTests.filter(t => !t.passed).length;
  const passedCount = auditTests.filter(t => t.passed).length;

  // Universe Risk Scanner
  const universeRiskList = allCompanies.map(c => {
    const m = calculateDeterministicMetrics(c, periodId);
    return { company: c, metrics: m };
  }).filter(({ metrics: m }) => {
    if (universeFilter === 'HIGH_LEVERAGE') return m.redFlags.highLeverage;
    if (universeFilter === 'WEAK_COVERAGE') return m.redFlags.weakInterestCoverage;
    if (universeFilter === 'NEGATIVE_SCISSORS') return m.redFlags.negativeOperatingScissors;
    if (universeFilter === 'NET_LOSS') return m.redFlags.netLossQuarter;
    return m.overallRiskScore < 85; // Show all watchlist & distressed by default
  });

  return (
    <div className="space-y-6">
      {/* Active Enterprise Forensic Audit Header */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-gray-800">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              <span>Deterministic Risk & Red Flag Audit: {company.name}</span>
            </h2>
            <p className="text-xs text-gray-400">
              Deterministic 6-point financial stress, leverage, and solvency audit ({periodId})
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono text-gray-400">Audit Result:</span>
            <span className={`px-3 py-1 rounded-lg border text-xs font-bold font-mono ${
              failedCount === 0 
                ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40' 
                : failedCount <= 2 
                ? 'bg-amber-950/80 text-amber-300 border-amber-500/40' 
                : 'bg-red-950/80 text-red-300 border-red-500/40 animate-pulse'
            }`}>
              {passedCount}/6 Checks Passed ({metrics.overallRiskScore}/100 Health Score)
            </span>
          </div>
        </div>

        {/* Audit Test Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {auditTests.map((t) => (
            <div 
              key={t.id} 
              className={`p-4 rounded-xl border transition-all ${
                t.passed 
                  ? 'bg-[#0B0F19]/90 border-gray-800/80 hover:border-emerald-500/30' 
                  : 'bg-red-950/20 border-red-500/40 hover:border-red-500/60 shadow-lg shadow-red-950/20'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <div className={`p-1.5 rounded ${t.passed ? 'bg-gray-800 text-gray-400' : 'bg-red-900/60 text-red-300'}`}>
                    {t.icon}
                  </div>
                  <span className="font-semibold text-xs text-white font-sans">{t.name}</span>
                </div>
                {t.passed ? (
                  <span className="flex items-center text-emerald-400 text-xs font-bold gap-1 font-mono">
                    <CheckCircle2 className="w-3.5 h-3.5" /> PASS
                  </span>
                ) : (
                  <span className="flex items-center text-rose-400 text-xs font-bold gap-1 font-mono animate-pulse">
                    <XCircle className="w-3.5 h-3.5" /> FAIL
                  </span>
                )}
              </div>

              <div className="mt-3 text-xs font-mono space-y-1">
                <div className="text-gray-400 text-[11px]">Threshold: {t.rule}</div>
                <div className="flex justify-between items-baseline pt-1">
                  <span className="text-gray-400 text-[11px]">Actual Metric:</span>
                  <span className={`font-bold ${t.passed ? 'text-cyan-300' : 'text-rose-400 font-extrabold'}`}>
                    {t.actual}
                  </span>
                </div>
              </div>

              <p className="mt-2 pt-2 border-t border-gray-800/80 text-[11px] text-gray-400 leading-relaxed font-sans">
                {t.impact}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Universe Risk & Red Flag Scanner */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-gray-800">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>140+ Listed Universe Risk Scanner & Watchlist</span>
            </h3>
            <p className="text-xs text-gray-400">
              Automated screening identifying entities triggering distress, debt stress or operating scissors
            </p>
          </div>

          {/* Quick Risk Filters */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs font-mono">
            <button
              onClick={() => setUniverseFilter('ALL')}
              className={`px-2.5 py-1 rounded transition-colors ${
                universeFilter === 'ALL' ? 'bg-blue-600 text-white font-bold' : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              All Watchlist ({universeRiskList.length})
            </button>
            <button
              onClick={() => setUniverseFilter('HIGH_LEVERAGE')}
              className={`px-2.5 py-1 rounded transition-colors ${
                universeFilter === 'HIGH_LEVERAGE' ? 'bg-red-600 text-white font-bold' : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              High D/E (&gt;2x)
            </button>
            <button
              onClick={() => setUniverseFilter('NEGATIVE_SCISSORS')}
              className={`px-2.5 py-1 rounded transition-colors ${
                universeFilter === 'NEGATIVE_SCISSORS' ? 'bg-amber-600 text-white font-bold' : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              Operating Scissors
            </button>
            <button
              onClick={() => setUniverseFilter('NET_LOSS')}
              className={`px-2.5 py-1 rounded transition-colors ${
                universeFilter === 'NET_LOSS' ? 'bg-purple-600 text-white font-bold' : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              Net Losses (PAT &lt; 0)
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 uppercase text-[10px] tracking-wider bg-gray-900/60">
                <th className="py-2.5 px-3">Enterprise</th>
                <th className="py-2.5 px-3">Sector</th>
                <th className="py-2.5 px-3 text-right">D/E Ratio</th>
                <th className="py-2.5 px-3 text-right">Interest Cover</th>
                <th className="py-2.5 px-3 text-right">Sales YoY</th>
                <th className="py-2.5 px-3 text-right">PAT YoY</th>
                <th className="py-2.5 px-3 text-right">Health Score</th>
                <th className="py-2.5 px-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {universeRiskList.slice(0, 30).map(({ company: c, metrics: m }) => (
                <tr key={c.id} className="hover:bg-red-950/20 transition-colors">
                  <td className="py-2.5 px-3">
                    <div className="font-semibold text-white font-sans">{c.name}</div>
                    <div className="text-[10px] text-gray-400">{c.ticker}</div>
                  </td>
                  <td className="py-2.5 px-3 text-gray-300 font-sans">{c.sector}</td>
                  <td className={`py-2.5 px-3 text-right font-bold ${m.debtToEquity > 2.0 ? 'text-rose-400' : 'text-gray-300'}`}>
                    {formatMultiple(m.debtToEquity)}
                  </td>
                  <td className={`py-2.5 px-3 text-right font-bold ${m.interestCoverage < 1.5 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {formatMultiple(m.interestCoverage)}
                  </td>
                  <td className="py-2.5 px-3 text-right text-blue-300 font-bold">
                    {formatPercent(m.salesYoYGrowth, 1, true)}
                  </td>
                  <td className={`py-2.5 px-3 text-right font-bold ${m.patYoYGrowth >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {formatPercent(m.patYoYGrowth, 1, true)}
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      m.overallRiskScore >= 70 ? 'bg-amber-900/60 text-amber-300' : 'bg-red-900/60 text-red-300'
                    }`}>
                      {m.overallRiskScore}/100
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <button
                      onClick={() => onSelectCompany(c)}
                      className="px-2 py-1 rounded bg-gray-800 hover:bg-blue-600 text-gray-200 hover:text-white text-[10px] font-sans inline-flex items-center gap-1 transition-colors"
                    >
                      <span>Deep Dive</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
