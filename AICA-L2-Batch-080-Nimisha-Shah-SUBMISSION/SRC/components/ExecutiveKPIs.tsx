import React from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Percent, 
  Layers, 
  Zap, 
  Scale, 
  Compass
} from 'lucide-react';
import { DeterministicMetrics, CurrencyUnit } from '../types/finance';
import { formatCurrency, formatPercent } from '../utils/financialCalculations';

interface ExecutiveKPIsProps {
  metrics: DeterministicMetrics;
  currencyUnit: CurrencyUnit;
}

export const ExecutiveKPIs: React.FC<ExecutiveKPIsProps> = ({
  metrics,
  currencyUnit
}) => {
  const isRevPos = metrics.salesYoYGrowth >= 0;
  const isPatPos = metrics.patYoYGrowth >= 0;
  const isEbitdaPos = metrics.ebitdaYoYGrowth >= 0;
  const isSpreadPos = metrics.economicSpread >= 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* KPI 1: Revenue from Operations */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 shadow-md relative overflow-hidden group hover:border-blue-500/40 transition-all">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wider font-mono">
            Quarterly Revenue (Ops)
          </span>
          <div className="w-7 h-7 rounded-lg bg-blue-900/40 text-blue-400 flex items-center justify-center border border-blue-700/30">
            <DollarSign className="w-4 h-4" />
          </div>
        </div>

        <div className="mt-3">
          <div className="text-2xl font-black text-white font-mono tracking-tight">
            {formatCurrency(metrics.revenue, currencyUnit)}
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-gray-800/80 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-1 font-mono">
            {isRevPos ? (
              <span className="flex items-center text-emerald-400 font-semibold">
                <TrendingUp className="w-3.5 h-3.5 mr-0.5" />
                {formatPercent(metrics.salesYoYGrowth, 1, true)} YoY
              </span>
            ) : (
              <span className="flex items-center text-red-400 font-semibold">
                <TrendingDown className="w-3.5 h-3.5 mr-0.5" />
                {formatPercent(metrics.salesYoYGrowth, 1, true)} YoY
              </span>
            )}
          </div>
          <span className="text-[11px] text-gray-400 font-mono">
            Total Inc: {formatCurrency(metrics.totalIncome, currencyUnit, false)}
          </span>
        </div>
      </div>

      {/* KPI 2: Operating EBITDA & OPM % */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 shadow-md relative overflow-hidden group hover:border-cyan-500/40 transition-all">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wider font-mono">
            Operating EBITDA (OPM %)
          </span>
          <div className="w-7 h-7 rounded-lg bg-cyan-900/40 text-cyan-400 flex items-center justify-center border border-cyan-700/30">
            <Percent className="w-4 h-4" />
          </div>
        </div>

        <div className="mt-3 flex items-baseline justify-between">
          <div className="text-2xl font-black text-white font-mono tracking-tight">
            {formatCurrency(metrics.ebitda, currencyUnit)}
          </div>
          <div className="text-lg font-bold text-cyan-400 font-mono">
            {formatPercent(metrics.opmPercent, 1)}
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-gray-800/80 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-1 font-mono">
            {isEbitdaPos ? (
              <span className="flex items-center text-emerald-400 font-semibold">
                <TrendingUp className="w-3.5 h-3.5 mr-0.5" />
                {formatPercent(metrics.ebitdaYoYGrowth, 1, true)} YoY
              </span>
            ) : (
              <span className="flex items-center text-red-400 font-semibold">
                <TrendingDown className="w-3.5 h-3.5 mr-0.5" />
                {formatPercent(metrics.ebitdaYoYGrowth, 1, true)} YoY
              </span>
            )}
          </div>
          <span className="text-[11px] text-gray-400 font-mono">
            EBITDA Margin: <strong className="text-cyan-300">{formatPercent(metrics.opmPercent, 1)}</strong>
          </span>
        </div>
      </div>

      {/* KPI 3: Profit After Tax (PAT) & NPM % */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 shadow-md relative overflow-hidden group hover:border-emerald-500/40 transition-all">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wider font-mono">
            Profit After Tax (PAT)
          </span>
          <div className="w-7 h-7 rounded-lg bg-emerald-900/40 text-emerald-400 flex items-center justify-center border border-emerald-700/30">
            <Zap className="w-4 h-4" />
          </div>
        </div>

        <div className="mt-3 flex items-baseline justify-between">
          <div className={`text-2xl font-black font-mono tracking-tight ${metrics.pat >= 0 ? 'text-white' : 'text-red-400'}`}>
            {formatCurrency(metrics.pat, currencyUnit)}
          </div>
          <div className={`text-lg font-bold font-mono ${metrics.npmPercent >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            NPM {formatPercent(metrics.npmPercent, 1)}
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-gray-800/80 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-1 font-mono">
            {isPatPos ? (
              <span className="flex items-center text-emerald-400 font-semibold">
                <TrendingUp className="w-3.5 h-3.5 mr-0.5" />
                {formatPercent(metrics.patYoYGrowth, 1, true)} YoY
              </span>
            ) : (
              <span className="flex items-center text-red-400 font-semibold">
                <TrendingDown className="w-3.5 h-3.5 mr-0.5" />
                {formatPercent(metrics.patYoYGrowth, 1, true)} YoY
              </span>
            )}
          </div>
          <span className="text-[11px] text-gray-400 font-mono">
            Run-Rate: {formatCurrency(metrics.annualizedPATRunRate, currencyUnit, false)}
          </span>
        </div>
      </div>

      {/* KPI 4: Return on Capital Employed (ROCE %) & Economic Spread */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 shadow-md relative overflow-hidden group hover:border-purple-500/40 transition-all">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wider font-mono">
            ROCE % & Economic Spread
          </span>
          <div className="w-7 h-7 rounded-lg bg-purple-900/40 text-purple-400 flex items-center justify-center border border-purple-700/30">
            <Compass className="w-4 h-4" />
          </div>
        </div>

        <div className="mt-3 flex items-baseline justify-between">
          <div className="text-2xl font-black text-purple-300 font-mono tracking-tight">
            {formatPercent(metrics.rocePercent, 1)}
          </div>
          <div className="text-xs font-mono text-gray-400">
            Hurdle: 10.0%
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-gray-800/80 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-1 font-mono">
            <span className={`flex items-center font-semibold ${isSpreadPos ? 'text-emerald-400' : 'text-amber-400'}`}>
              <Scale className="w-3.5 h-3.5 mr-1" />
              Spread: {formatPercent(metrics.economicSpread, 1, true)}
            </span>
          </div>
          <span className="text-[11px] text-gray-400 font-mono">
            ROE: <strong className="text-purple-300">{formatPercent(metrics.roePercent, 1)}</strong>
          </span>
        </div>
      </div>
    </div>
  );
};
