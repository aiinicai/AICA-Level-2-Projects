import React from 'react';
import { 
  Scale, 
  ShieldCheck, 
  AlertTriangle, 
  TrendingUp, 
  Zap, 
  PieChart as PieIcon,
  Compass,
  ArrowRight,
  Info
} from 'lucide-react';
import { CompanyEntity, DeterministicMetrics, CurrencyUnit, PeriodId } from '../types/finance';
import { formatCurrency, formatMultiple, formatPercent } from '../utils/financialCalculations';

interface SolvencyCapitalViewProps {
  company: CompanyEntity;
  metrics: DeterministicMetrics;
  periodId: PeriodId;
  currencyUnit: CurrencyUnit;
}

export const SolvencyCapitalView: React.FC<SolvencyCapitalViewProps> = ({
  company,
  metrics,
  periodId,
  currencyUnit
}) => {
  const bs = company.periods[periodId]?.balanceSheet || company.periods['Q4 FY25'].balanceSheet;
  const pl = company.periods[periodId]?.pl || company.periods['Q4 FY25'].pl;

  const netWorth = bs.equityShareCapital + bs.reservesAndSurplus;
  const totalDebt = bs.longTermBorrowings + bs.shortTermBorrowings;
  const totalCapital = netWorth + totalDebt;

  const equityPct = totalCapital > 0 ? (netWorth / totalCapital) * 100 : 0;
  const debtPct = totalCapital > 0 ? (totalDebt / totalCapital) * 100 : 0;

  const getLeverageTier = (de: number) => {
    if (de < 0.5) return { label: 'CONSERVATIVE / LOW LEVERAGE', color: 'text-emerald-400', bg: 'bg-emerald-950/80 border-emerald-500/30' };
    if (de <= 1.2) return { label: 'OPTIMAL / MODERATE LEVERAGE', color: 'text-blue-400', bg: 'bg-blue-950/80 border-blue-500/30' };
    if (de <= 2.0) return { label: 'ELEVATED / WATCHLIST', color: 'text-amber-400', bg: 'bg-amber-950/80 border-amber-500/30' };
    return { label: 'HIGH RISK / OVER-LEVERAGED', color: 'text-red-400', bg: 'bg-red-950/80 border-red-500/30' };
  };

  const getCoverageTier = (icr: number) => {
    if (icr >= 4.0) return { label: 'PRIME SERVICING CAPACITY (>4.0x)', color: 'text-emerald-400', bg: 'bg-emerald-950/80 border-emerald-500/30', status: 'SAFE' };
    if (icr >= 2.0) return { label: 'ADEQUATE SERVICING (2.0x - 4.0x)', color: 'text-blue-400', bg: 'bg-blue-950/80 border-blue-500/30', status: 'ADEQUATE' };
    if (icr >= 1.5) return { label: 'MODERATE BUFFER (1.5x - 2.0x)', color: 'text-amber-400', bg: 'bg-amber-950/80 border-amber-500/30', status: 'WATCH' };
    return { label: 'CRITICAL / DEBT SERVICE STRESS (<1.5x)', color: 'text-red-400', bg: 'bg-red-950/80 border-red-500/30', status: 'CRITICAL' };
  };

  const levTier = getLeverageTier(metrics.debtToEquity);
  const covTier = getCoverageTier(metrics.interestCoverage);

  return (
    <div className="space-y-6">
      {/* Top Solvency & Leverage Executive Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Debt-to-Equity */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400 uppercase tracking-wider">
              Debt-to-Equity (D/E)
            </span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${levTier.bg} ${levTier.color}`}>
              {levTier.label}
            </span>
          </div>

          <div className="text-3xl font-black text-white font-mono tracking-tight">
            {formatMultiple(metrics.debtToEquity)}
          </div>

          <div className="text-xs text-gray-400 space-y-1 pt-2 border-t border-gray-800/80">
            <div className="flex justify-between font-mono">
              <span>Total Debt:</span>
              <strong className="text-white">{formatCurrency(metrics.totalDebt, currencyUnit)}</strong>
            </div>
            <div className="flex justify-between font-mono">
              <span>Net Worth:</span>
              <strong className="text-white">{formatCurrency(metrics.netWorth, currencyUnit)}</strong>
            </div>
          </div>
        </div>

        {/* Interest Coverage Ratio */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400 uppercase tracking-wider">
              Interest Coverage (EBIT/Int)
            </span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${covTier.bg} ${covTier.color}`}>
              {covTier.status}
            </span>
          </div>

          <div className="text-3xl font-black text-cyan-400 font-mono tracking-tight">
            {formatMultiple(metrics.interestCoverage)}
          </div>

          <div className="text-xs text-gray-400 space-y-1 pt-2 border-t border-gray-800/80">
            <div className="flex justify-between font-mono">
              <span>EBIT (Operating Profit):</span>
              <strong className="text-white">{formatCurrency(metrics.ebit, currencyUnit)}</strong>
            </div>
            <div className="flex justify-between font-mono">
              <span>Finance Costs (Quarterly):</span>
              <strong className="text-white">{formatCurrency(metrics.financeCosts, currencyUnit)}</strong>
            </div>
          </div>
        </div>

        {/* Economic Spread (ROCE vs WACC) */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400 uppercase tracking-wider">
              Economic Value Spread
            </span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
              metrics.economicSpread >= 0 ? 'bg-emerald-950/80 text-emerald-400 border-emerald-500/30' : 'bg-rose-950/80 text-rose-400 border-rose-500/30'
            }`}>
              {metrics.economicSpread >= 0 ? 'VALUE CREATING' : 'VALUE DILUTIVE'}
            </span>
          </div>

          <div className={`text-3xl font-black font-mono tracking-tight ${
            metrics.economicSpread >= 0 ? 'text-emerald-400' : 'text-rose-400'
          }`}>
            {formatPercent(metrics.economicSpread, 1, true)}
          </div>

          <div className="text-xs text-gray-400 space-y-1 pt-2 border-t border-gray-800/80">
            <div className="flex justify-between font-mono">
              <span>ROCE %:</span>
              <strong className="text-purple-300">{formatPercent(metrics.rocePercent, 1)}</strong>
            </div>
            <div className="flex justify-between font-mono">
              <span>Benchmark Hurdle Rate:</span>
              <strong className="text-gray-300">10.00%</strong>
            </div>
          </div>
        </div>
      </div>

      {/* Capital Structure Stack & Balance Sheet Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Capital Stack Composition */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Scale className="w-4 h-4 text-blue-400" />
            <span>Capital Structure Distribution (Net Worth vs Borrowings)</span>
          </h3>

          <div className="space-y-2">
            <div className="flex justify-between text-xs font-mono">
              <span className="text-emerald-400 font-semibold">Net Worth: {equityPct.toFixed(1)}% ({formatCurrency(netWorth, currencyUnit)})</span>
              <span className="text-rose-400 font-semibold">Total Debt: {debtPct.toFixed(1)}% ({formatCurrency(totalDebt, currencyUnit)})</span>
            </div>
            <div className="w-full h-4 bg-gray-800 rounded-full overflow-hidden flex shadow-inner">
              <div 
                className="bg-emerald-500 h-full transition-all" 
                style={{ width: `${equityPct}%` }}
              ></div>
              <div 
                className="bg-rose-500 h-full transition-all" 
                style={{ width: `${debtPct}%` }}
              ></div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="bg-[#0B0F19] border border-gray-800/80 rounded-lg p-3 space-y-1">
              <span className="text-[11px] text-gray-400 font-mono">Share Capital</span>
              <div className="text-sm font-bold text-white font-mono">{formatCurrency(bs.equityShareCapital, currencyUnit)}</div>
            </div>
            <div className="bg-[#0B0F19] border border-gray-800/80 rounded-lg p-3 space-y-1">
              <span className="text-[11px] text-gray-400 font-mono">Reserves & Surplus</span>
              <div className="text-sm font-bold text-white font-mono">{formatCurrency(bs.reservesAndSurplus, currencyUnit)}</div>
            </div>
            <div className="bg-[#0B0F19] border border-gray-800/80 rounded-lg p-3 space-y-1">
              <span className="text-[11px] text-gray-400 font-mono">Long Term Borrowings</span>
              <div className="text-sm font-bold text-rose-300 font-mono">{formatCurrency(bs.longTermBorrowings, currencyUnit)}</div>
            </div>
            <div className="bg-[#0B0F19] border border-gray-800/80 rounded-lg p-3 space-y-1">
              <span className="text-[11px] text-gray-400 font-mono">Short Term / Working Capital</span>
              <div className="text-sm font-bold text-rose-300 font-mono">{formatCurrency(bs.shortTermBorrowings, currencyUnit)}</div>
            </div>
          </div>
        </div>

        {/* Debt Servicing Capacity Stress Diagnostic */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            <span>Debt Servicing Resilience & Solvency Audit</span>
          </h3>

          <div className="space-y-3 text-xs">
            <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg flex items-start space-x-3">
              <div className={`w-3 h-3 rounded-full mt-0.5 shrink-0 ${
                metrics.interestCoverage >= 3.0 ? 'bg-emerald-400' : metrics.interestCoverage >= 1.5 ? 'bg-blue-400' : 'bg-red-400 animate-pulse'
              }`}></div>
              <div>
                <div className="font-semibold text-white font-mono">
                  Interest Coverage Rating: {metrics.interestCoverage.toFixed(1)}x
                </div>
                <p className="text-gray-400 text-[11px] mt-0.5">
                  {metrics.interestCoverage >= 3.0
                    ? 'Robust earnings buffer. Operating profit exceeds interest obligations by over 3x.'
                    : metrics.interestCoverage >= 1.5
                    ? 'Adequate coverage. Vulnerable to sharp margin contraction or rising cost of borrowing.'
                    : 'Critical distress flag. Operating profit is insufficient to safely cover gross finance obligations.'}
                </p>
              </div>
            </div>

            <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg flex items-start space-x-3">
              <div className={`w-3 h-3 rounded-full mt-0.5 shrink-0 ${
                metrics.debtToEquity <= 1.0 ? 'bg-emerald-400' : metrics.debtToEquity <= 2.0 ? 'bg-amber-400' : 'bg-red-400'
              }`}></div>
              <div>
                <div className="font-semibold text-white font-mono">
                  Gearing & Leverage Ratio: {metrics.debtToEquity.toFixed(2)}x
                </div>
                <p className="text-gray-400 text-[11px] mt-0.5">
                  {metrics.debtToEquity <= 1.0
                    ? 'Conservative financial structure. High capacity for debt-financed growth or expansion capex.'
                    : metrics.debtToEquity <= 2.0
                    ? 'Moderate gearing. Capital allocation should prioritize debt consolidation.'
                    : 'Over-leveraged balance sheet. High sensitivity to macro interest rate shifts and debt covenants.'}
                </p>
              </div>
            </div>

            <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg flex items-start space-x-3">
              <div className="w-3 h-3 rounded-full mt-0.5 shrink-0 bg-purple-400"></div>
              <div>
                <div className="font-semibold text-white font-mono">
                  Capital Employed: {formatCurrency(metrics.capitalEmployed, currencyUnit)}
                </div>
                <p className="text-gray-400 text-[11px] mt-0.5">
                  Generating {formatCurrency(metrics.ebit * 4, currencyUnit)} in annualized EBIT across total capital assets.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
