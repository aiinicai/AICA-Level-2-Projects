import React, { useState } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  BarChart3, 
  Layers, 
  DollarSign, 
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  Minus
} from 'lucide-react';
import { FinancialStatement, FinancialRatios } from '../types/financial';

interface TrendAnalysisViewProps {
  statements: FinancialStatement[];
  ratiosByYear: Record<string, FinancialRatios>;
}

export const TrendAnalysisView: React.FC<TrendAnalysisViewProps> = ({
  statements,
  ratiosByYear
}) => {
  // Sort statements chronologically
  const sortedStatements = [...statements].sort((a, b) => a.financialYear.localeCompare(b.financialYear));
  const years = sortedStatements.map(s => s.financialYear);

  // Calculate YoY metrics
  const trends = sortedStatements.map((curr, idx) => {
    const prev = idx > 0 ? sortedStatements[idx - 1] : null;
    const rev = curr.profitAndLoss.revenue;
    const pat = curr.profitAndLoss.netProfit;
    const assets = curr.balanceSheet.totalAssets;
    const debt = curr.balanceSheet.totalDebt;
    const equity = curr.balanceSheet.totalEquity;
    const currentAssets = curr.balanceSheet.cash + curr.balanceSheet.bank + curr.balanceSheet.receivables + curr.balanceSheet.inventory + (curr.balanceSheet.otherCurrentAssets || 0);
    const currentLiab = curr.balanceSheet.payables + curr.balanceSheet.shortTermDebt + (curr.balanceSheet.otherCurrentLiabilities || 0);
    const workingCapital = currentAssets - currentLiab;

    let revGrowth = 0;
    let patGrowth = 0;
    let assetGrowth = 0;
    let debtGrowth = 0;

    if (prev) {
      revGrowth = ((rev - prev.profitAndLoss.revenue) / (prev.profitAndLoss.revenue || 1)) * 100;
      patGrowth = prev.profitAndLoss.netProfit !== 0 
        ? ((pat - prev.profitAndLoss.netProfit) / Math.abs(prev.profitAndLoss.netProfit)) * 100 
        : 0;
      assetGrowth = ((assets - prev.balanceSheet.totalAssets) / (prev.balanceSheet.totalAssets || 1)) * 100;
      debtGrowth = ((debt - prev.balanceSheet.totalDebt) / (prev.balanceSheet.totalDebt || 1)) * 100;
    }

    return {
      year: curr.financialYear,
      revenue: rev,
      revGrowth,
      netProfit: pat,
      patGrowth,
      totalAssets: assets,
      assetGrowth,
      totalDebt: debt,
      debtGrowth,
      totalEquity: equity,
      workingCapital,
      ratios: ratiosByYear[curr.financialYear]
    };
  });

  // Calculate CAGR for revenue and profit if multiple years exist
  let revCAGR: number | null = null;
  let patCAGR: number | null = null;
  if (trends.length >= 2) {
    const first = trends[0];
    const last = trends[trends.length - 1];
    const n = trends.length - 1;
    if (first.revenue > 0 && last.revenue > 0) {
      revCAGR = (Math.pow(last.revenue / first.revenue, 1 / n) - 1) * 100;
    }
    if (first.netProfit > 0 && last.netProfit > 0) {
      patCAGR = (Math.pow(last.netProfit / first.netProfit, 1 / n) - 1) * 100;
    }
  }

  // Max values for chart scaling
  const maxRevenue = Math.max(...trends.map(t => Math.max(t.revenue, t.totalAssets, 10)));
  const maxDebtEquity = Math.max(...trends.map(t => Math.max(t.totalDebt, t.totalEquity, 10)));

  const renderGrowthBadge = (val: number, isFirst: boolean) => {
    if (isFirst) return <span className="text-slate-400 font-mono">— Base</span>;
    if (val > 0) {
      return (
        <span className="inline-flex items-center text-emerald-400 font-mono font-semibold">
          <ArrowUpRight className="w-3.5 h-3.5" /> +{val.toFixed(1)}%
        </span>
      );
    }
    if (val < 0) {
      return (
        <span className="inline-flex items-center text-rose-400 font-mono font-semibold">
          <ArrowDownRight className="w-3.5 h-3.5" /> {val.toFixed(1)}%
        </span>
      );
    }
    return <span className="text-slate-400 font-mono">0.0%</span>;
  };

  return (
    <div className="space-y-6">
      
      {/* Top Growth Highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Topline CAGR</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className={`text-2xl font-black ${revCAGR !== null && revCAGR >= 10 ? 'text-emerald-400' : revCAGR !== null && revCAGR >= 0 ? 'text-cyan-300' : 'text-rose-400'}`}>
              {revCAGR !== null ? `${revCAGR.toFixed(1)}%` : '—'}
            </span>
            <span className="text-xs text-slate-400">Compounded</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Over {trends.length} recorded reporting periods</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Profit CAGR</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className={`text-2xl font-black ${patCAGR !== null && patCAGR >= 10 ? 'text-emerald-400' : patCAGR !== null && patCAGR >= 0 ? 'text-cyan-300' : 'text-rose-400'}`}>
              {patCAGR !== null ? `${patCAGR.toFixed(1)}%` : '—'}
            </span>
            <span className="text-xs text-slate-400">Net Profit</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Bottom-line trajectory</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Current Net Working Capital</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className={`text-2xl font-black ${trends[trends.length - 1].workingCapital >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              INR {trends[trends.length - 1].workingCapital.toFixed(1)} Cr
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Current Assets minus Current Liab</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Leverage Trajectory</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-2xl font-black text-white">
              {trends[trends.length - 1].ratios?.debtEquityRatio.toFixed(2) || '0.00'}x
            </span>
            <span className="text-xs text-slate-400">Debt/Equity</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {trends.length >= 2 && trends[trends.length - 1].totalDebt < trends[0].totalDebt
              ? 'Deleveraging balance sheet'
              : 'Debt expanded over time'}
          </p>
        </div>

      </div>

      {/* Visual Chart 1: Revenue vs Net Profit Bar Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Chart A: Revenue vs Net Profit */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="text-sm font-bold text-white">Revenue vs Net Profit Trajectory</h4>
              <p className="text-xs text-slate-400">Comparison of top-line scale to bottom-line realization (INR Cr)</p>
            </div>
            <div className="flex items-center space-x-3 text-xs">
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-blue-500 inline-block"></span> Revenue</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-emerald-400 inline-block"></span> Net Profit</span>
            </div>
          </div>

          {/* Bar Chart Visualization */}
          <div className="h-56 flex items-end justify-around gap-4 pt-4 border-b border-slate-800 pb-2">
            {trends.map(t => {
              const revHeight = Math.max(8, (t.revenue / maxRevenue) * 180);
              const isProfitPositive = t.netProfit >= 0;
              const profitHeight = Math.max(4, (Math.abs(t.netProfit) / maxRevenue) * 180);

              return (
                <div key={t.year} className="flex-1 flex flex-col items-center justify-end h-full group">
                  <div className="w-full flex items-end justify-center space-x-1.5 h-full">
                    
                    {/* Revenue Bar */}
                    <div className="w-1/2 flex flex-col items-center">
                      <span className="text-[10px] font-mono text-blue-300 opacity-0 group-hover:opacity-100 transition mb-1">
                        {t.revenue.toFixed(1)}
                      </span>
                      <div 
                        className="w-full bg-gradient-to-t from-blue-700 to-blue-500 rounded-t-md transition-all duration-500 shadow-sm"
                        style={{ height: `${revHeight}px` }}
                      />
                    </div>

                    {/* Profit Bar */}
                    <div className="w-1/2 flex flex-col items-center">
                      <span className={`text-[10px] font-mono opacity-0 group-hover:opacity-100 transition mb-1 ${isProfitPositive ? 'text-emerald-300' : 'text-rose-400'}`}>
                        {t.netProfit.toFixed(1)}
                      </span>
                      <div 
                        className={`w-full rounded-t-md transition-all duration-500 shadow-sm ${
                          isProfitPositive 
                            ? 'bg-gradient-to-t from-emerald-600 to-emerald-400' 
                            : 'bg-gradient-to-t from-rose-700 to-rose-500'
                        }`}
                        style={{ height: `${profitHeight}px` }}
                      />
                    </div>

                  </div>
                  <span className="text-xs font-semibold text-slate-300 mt-2 truncate w-full text-center">
                    {t.year}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
            <span>Scale: INR Crores</span>
            <span>Hover bars for exact metrics</span>
          </div>
        </div>

        {/* Chart B: Capital Structure (Debt vs Equity) */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="text-sm font-bold text-white">Capital Structure &amp; Solvency Trend</h4>
              <p className="text-xs text-slate-400">Total Borrowings vs Net Worth &amp; Retained Earnings (INR Cr)</p>
            </div>
            <div className="flex items-center space-x-3 text-xs">
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-indigo-500 inline-block"></span> Total Debt</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-cyan-400 inline-block"></span> Total Equity</span>
            </div>
          </div>

          {/* Bar Chart Visualization */}
          <div className="h-56 flex items-end justify-around gap-4 pt-4 border-b border-slate-800 pb-2">
            {trends.map(t => {
              const debtHeight = Math.max(8, (t.totalDebt / maxDebtEquity) * 180);
              const eqHeight = Math.max(8, (Math.max(1, t.totalEquity) / maxDebtEquity) * 180);

              return (
                <div key={t.year} className="flex-1 flex flex-col items-center justify-end h-full group">
                  <div className="w-full flex items-end justify-center space-x-1.5 h-full">
                    
                    {/* Debt Bar */}
                    <div className="w-1/2 flex flex-col items-center">
                      <span className="text-[10px] font-mono text-indigo-300 opacity-0 group-hover:opacity-100 transition mb-1">
                        {t.totalDebt.toFixed(1)}
                      </span>
                      <div 
                        className="w-full bg-gradient-to-t from-indigo-700 to-indigo-500 rounded-t-md transition-all duration-500 shadow-sm"
                        style={{ height: `${debtHeight}px` }}
                      />
                    </div>

                    {/* Equity Bar */}
                    <div className="w-1/2 flex flex-col items-center">
                      <span className="text-[10px] font-mono text-cyan-300 opacity-0 group-hover:opacity-100 transition mb-1">
                        {t.totalEquity.toFixed(1)}
                      </span>
                      <div 
                        className="w-full bg-gradient-to-t from-cyan-600 to-cyan-400 rounded-t-md transition-all duration-500 shadow-sm"
                        style={{ height: `${eqHeight}px` }}
                      />
                    </div>

                  </div>
                  <span className="text-xs font-semibold text-slate-300 mt-2 truncate w-full text-center">
                    {t.year}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
            <span>D/E Multiplier: {trends[trends.length - 1].ratios?.debtEquityRatio.toFixed(2)}x</span>
            <span>Leverage health indicator</span>
          </div>
        </div>

      </div>

      {/* Comprehensive Multi-Year Growth Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        <div className="p-4 bg-slate-800/60 border-b border-slate-800 flex items-center justify-between">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Multi-Year Financial Statement Performance Summary
          </h4>
          <span className="text-xs text-slate-400 font-mono">Figures in INR Crores</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-800/30 text-slate-400 border-b border-slate-800 text-[11px]">
              <tr>
                <th className="py-2.5 px-4">Financial Metric</th>
                {trends.map(t => (
                  <th key={t.year} className="py-2.5 px-3 text-right">
                    {t.year}
                  </th>
                ))}
                <th className="py-2.5 px-4 text-right">Latest YoY Growth</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              <tr>
                <td className="py-3 px-4 font-semibold text-white">Revenue from Operations</td>
                {trends.map(t => (
                  <td key={t.year} className="py-3 px-3 text-right font-mono font-bold text-slate-200">
                    {t.revenue.toFixed(2)}
                  </td>
                ))}
                <td className="py-3 px-4 text-right font-mono">
                  {renderGrowthBadge(trends[trends.length - 1].revGrowth, trends.length === 1)}
                </td>
              </tr>

              <tr>
                <td className="py-3 px-4 font-semibold text-white">Net Profit (PAT)</td>
                {trends.map(t => (
                  <td key={t.year} className={`py-3 px-3 text-right font-mono font-bold ${t.netProfit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {t.netProfit.toFixed(2)}
                  </td>
                ))}
                <td className="py-3 px-4 text-right font-mono">
                  {renderGrowthBadge(trends[trends.length - 1].patGrowth, trends.length === 1)}
                </td>
              </tr>

              <tr>
                <td className="py-3 px-4 font-semibold text-white">Total Assets</td>
                {trends.map(t => (
                  <td key={t.year} className="py-3 px-3 text-right font-mono text-slate-200">
                    {t.totalAssets.toFixed(2)}
                  </td>
                ))}
                <td className="py-3 px-4 text-right font-mono">
                  {renderGrowthBadge(trends[trends.length - 1].assetGrowth, trends.length === 1)}
                </td>
              </tr>

              <tr>
                <td className="py-3 px-4 font-semibold text-white">Total Debt</td>
                {trends.map(t => (
                  <td key={t.year} className="py-3 px-3 text-right font-mono text-indigo-300">
                    {t.totalDebt.toFixed(2)}
                  </td>
                ))}
                <td className="py-3 px-4 text-right font-mono">
                  {renderGrowthBadge(trends[trends.length - 1].debtGrowth, trends.length === 1)}
                </td>
              </tr>

              <tr>
                <td className="py-3 px-4 font-semibold text-white">Net Working Capital</td>
                {trends.map(t => (
                  <td key={t.year} className={`py-3 px-3 text-right font-mono ${t.workingCapital >= 0 ? 'text-cyan-300' : 'text-rose-400'}`}>
                    {t.workingCapital.toFixed(2)}
                  </td>
                ))}
                <td className="py-3 px-4 text-right font-mono text-slate-400">
                  {trends[trends.length - 1].workingCapital >= 0 ? 'Surplus' : 'Deficit'}
                </td>
              </tr>

              <tr className="bg-slate-800/30">
                <td className="py-3 px-4 font-semibold text-white">Current Ratio</td>
                {trends.map(t => (
                  <td key={t.year} className="py-3 px-3 text-right font-mono font-bold text-cyan-300">
                    {t.ratios?.currentRatio.toFixed(2)}x
                  </td>
                ))}
                <td className="py-3 px-4 text-right font-mono text-slate-400">
                  Benchmark ≥ 1.33x
                </td>
              </tr>

              <tr className="bg-slate-800/30">
                <td className="py-3 px-4 font-semibold text-white">Debt / Equity Ratio</td>
                {trends.map(t => (
                  <td key={t.year} className="py-3 px-3 text-right font-mono font-bold text-amber-300">
                    {t.ratios?.debtEquityRatio.toFixed(2)}x
                  </td>
                ))}
                <td className="py-3 px-4 text-right font-mono text-slate-400">
                  Benchmark ≤ 1.50x
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
