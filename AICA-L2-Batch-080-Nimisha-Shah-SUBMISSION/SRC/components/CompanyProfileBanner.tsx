import React from 'react';
import { 
  Building, 
  MapPin, 
  User, 
  Tag, 
  TrendingUp, 
  ShieldCheck, 
  AlertTriangle,
  Award
} from 'lucide-react';
import { CompanyEntity, DeterministicMetrics, CurrencyUnit } from '../types/finance';
import { formatCurrency, formatMultiple, formatPercent } from '../utils/financialCalculations';

interface CompanyProfileBannerProps {
  company: CompanyEntity;
  metrics: DeterministicMetrics;
  currencyUnit: CurrencyUnit;
}

export const CompanyProfileBanner: React.FC<CompanyProfileBannerProps> = ({
  company,
  metrics,
  currencyUnit
}) => {
  const valuation = company.periods['Q4 FY25']?.valuation || {
    stockPrice: 1000,
    fiftyTwoWeekHigh: 1200,
    fiftyTwoWeekLow: 800,
    peRatio: 25.0,
    dividendYield: 1.2
  };

  const high52 = valuation.fiftyTwoWeekHigh;
  const low52 = valuation.fiftyTwoWeekLow;
  const currentPrice = valuation.stockPrice;
  const rangePct = Math.min(100, Math.max(0, ((currentPrice - low52) / Math.max(1, high52 - low52)) * 100));

  const getRiskBadge = () => {
    switch (metrics.riskRating) {
      case 'PRIME / LOW RISK':
        return (
          <span className="flex items-center space-x-1 px-2.5 py-1 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-500/40 text-xs font-semibold">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Audit: Prime Health ({metrics.overallRiskScore}/100)</span>
          </span>
        );
      case 'MODERATE / WATCHLIST':
        return (
          <span className="flex items-center space-x-1 px-2.5 py-1 rounded-full bg-blue-950/80 text-blue-300 border border-blue-500/40 text-xs font-semibold">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
            <span>Audit: Stable ({metrics.overallRiskScore}/100)</span>
          </span>
        );
      case 'ELEVATED / CAUTION':
        return (
          <span className="flex items-center space-x-1 px-2.5 py-1 rounded-full bg-amber-950/80 text-amber-300 border border-amber-500/40 text-xs font-semibold">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span>Audit: Watchlist ({metrics.overallRiskScore}/100)</span>
          </span>
        );
      case 'DISTRESSED / HIGH RISK':
      default:
        return (
          <span className="flex items-center space-x-1 px-2.5 py-1 rounded-full bg-red-950/80 text-red-300 border border-red-500/40 text-xs font-semibold animate-pulse">
            <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
            <span>Audit: High Risk / Stress ({metrics.overallRiskScore}/100)</span>
          </span>
        );
    }
  };

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg relative overflow-hidden">
      {/* Decorative gradient highlight */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>

      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
        {/* Left Column: Company Metadata */}
        <div className="space-y-2 max-w-2xl">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              {company.name}
            </h1>
            <span className="px-2 py-0.5 rounded bg-gray-800 text-blue-400 border border-gray-700 font-mono text-xs font-bold">
              NSE: {company.ticker}
            </span>
            <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700 font-mono text-xs">
              BSE: {company.bseCode}
            </span>
            {getRiskBadge()}
          </div>

          <p className="text-xs text-gray-400 leading-relaxed">
            {company.description}
          </p>

          <div className="flex flex-wrap items-center gap-4 text-xs text-gray-400 font-sans pt-1">
            <span className="flex items-center gap-1.5 text-gray-300">
              <Tag className="w-3.5 h-3.5 text-cyan-400" />
              <span className="font-semibold text-cyan-300">{company.sector}</span>
            </span>
            <span className="flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-blue-400" />
              <span>CEO: <strong className="text-gray-200">{company.ceo}</strong></span>
            </span>
            <span className="flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-rose-400" />
              <span>HQ: <strong className="text-gray-200">{company.headquarters}</strong></span>
            </span>
            <span className="flex items-center gap-1.5">
              <Building className="w-3.5 h-3.5 text-amber-400" />
              <span>Est. <strong className="text-gray-200">{company.foundedYear}</strong></span>
            </span>
          </div>
        </div>

        {/* Right Column: Market Valuation & 52-Week Snapshot */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-4 gap-3 w-full lg:w-auto bg-[#0B0F19]/90 border border-gray-800/80 rounded-lg p-3.5">
          {/* Market Cap */}
          <div className="space-y-1">
            <span className="text-[11px] text-gray-400 uppercase font-mono tracking-wider">
              Market Capitalization
            </span>
            <div className="text-base font-bold text-white font-mono">
              {formatCurrency(metrics.marketCap, currencyUnit)}
            </div>
            <span className="text-[10px] text-emerald-400 flex items-center gap-0.5">
              <TrendingUp className="w-3 h-3" /> Enterprise Tier
            </span>
          </div>

          {/* Current Stock Price & 52W Bar */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-gray-400 uppercase font-mono tracking-wider">
                LTP (₹)
              </span>
              <span className="text-[10px] font-mono text-cyan-300">
                ₹{currentPrice.toLocaleString('en-IN')}
              </span>
            </div>
            {/* 52W Range Bar */}
            <div className="w-full bg-gray-800 rounded-full h-1.5 mt-1 relative">
              <div 
                className="bg-gradient-to-r from-blue-500 to-cyan-400 h-1.5 rounded-full" 
                style={{ width: `${rangePct}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-[9px] font-mono text-gray-500">
              <span>L: ₹{low52}</span>
              <span>H: ₹{high52}</span>
            </div>
          </div>

          {/* P/E Ratio */}
          <div className="space-y-1">
            <span className="text-[11px] text-gray-400 uppercase font-mono tracking-wider">
              P/E Multiple
            </span>
            <div className="text-base font-bold text-blue-400 font-mono">
              {formatMultiple(metrics.peRatio)}
            </div>
            <span className="text-[10px] text-gray-400">
              P/B: <strong className="text-gray-200 font-mono">{formatMultiple(metrics.pbRatio)}</strong>
            </span>
          </div>

          {/* Dividend Yield & EV/EBITDA */}
          <div className="space-y-1">
            <span className="text-[11px] text-gray-400 uppercase font-mono tracking-wider">
              Div Yield / EV/EBITDA
            </span>
            <div className="text-base font-bold text-purple-400 font-mono">
              {formatPercent(metrics.dividendYield)}
            </div>
            <span className="text-[10px] text-gray-400">
              EV/EBITDA: <strong className="text-gray-200 font-mono">{formatMultiple(metrics.evEbitdaRatio)}</strong>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
