import React from 'react';
import { 
  PieChart, 
  DollarSign, 
  TrendingUp, 
  BarChart3, 
  Layers, 
  ArrowRight,
  ShieldAlert,
  Award
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  Cell, 
  Legend 
} from 'recharts';
import { CompanyEntity, DeterministicMetrics, CurrencyUnit, PeriodId } from '../types/finance';
import { getAllCompanies } from '../data/companiesData';
import { formatCurrency, formatMultiple, formatPercent } from '../utils/financialCalculations';

interface ValuationMultiplesViewProps {
  company: CompanyEntity;
  metrics: DeterministicMetrics;
  periodId: PeriodId;
  currencyUnit: CurrencyUnit;
  onSelectPeer: (peer: CompanyEntity) => void;
}

export const ValuationMultiplesView: React.FC<ValuationMultiplesViewProps> = ({
  company,
  metrics,
  periodId,
  currencyUnit,
  onSelectPeer
}) => {
  const allCompanies = getAllCompanies();
  const sectorPeers = allCompanies.filter(c => c.sector === company.sector);

  const peerValuationData = sectorPeers.slice(0, 10).map(p => {
    const val = p.periods[periodId]?.valuation || p.periods['Q4 FY25'].valuation;
    return {
      name: p.shortName,
      ticker: p.ticker,
      pe: val.peRatio || 20,
      evEbitda: val.evEbitdaRatio || 15,
      isCurrent: p.id === company.id,
      company: p
    };
  });

  const sectorMedianPE = sectorPeers.reduce((acc, p) => {
    const pe = p.periods[periodId]?.valuation?.peRatio || 20;
    return acc + pe;
  }, 0) / Math.max(1, sectorPeers.length);

  const bs = company.periods[periodId]?.balanceSheet || company.periods['Q4 FY25'].balanceSheet;
  const cash = bs.cashAndEquivalents || 0;
  const debt = metrics.totalDebt;
  const ev = metrics.enterpriseValue;

  return (
    <div className="space-y-6">
      {/* 4 Core Valuation Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* P/E Ratio */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 shadow-lg space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400 uppercase">Price-to-Earnings (P/E)</span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
              metrics.peRatio <= sectorMedianPE ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/30' : 'bg-amber-950/80 text-amber-400 border border-amber-500/30'
            }`}>
              {metrics.peRatio <= sectorMedianPE ? 'VALUATION DISCOUNT' : 'PREMIUM MULTIPLE'}
            </span>
          </div>
          <div className="text-3xl font-black text-blue-400 font-mono">
            {formatMultiple(metrics.peRatio)}
          </div>
          <div className="text-xs text-gray-400 pt-1 border-t border-gray-800">
            Sector Median P/E: <strong className="text-white font-mono">{formatMultiple(sectorMedianPE)}</strong>
          </div>
        </div>

        {/* P/B Ratio */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 shadow-lg space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400 uppercase">Price-to-Book (P/B)</span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-gray-800 text-gray-300">
              Net Worth Multiple
            </span>
          </div>
          <div className="text-3xl font-black text-cyan-400 font-mono">
            {formatMultiple(metrics.pbRatio)}
          </div>
          <div className="text-xs text-gray-400 pt-1 border-t border-gray-800">
            Book Value / Share: <strong className="text-white font-mono">{formatCurrency(metrics.netWorth, currencyUnit, false)}</strong>
          </div>
        </div>

        {/* EV / EBITDA */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 shadow-lg space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400 uppercase">EV / EBITDA</span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-900/40 text-purple-300 border border-purple-700/30">
              Operating Multiple
            </span>
          </div>
          <div className="text-3xl font-black text-purple-400 font-mono">
            {formatMultiple(metrics.evEbitdaRatio)}
          </div>
          <div className="text-xs text-gray-400 pt-1 border-t border-gray-800">
            Enterprise Value: <strong className="text-white font-mono">{formatCurrency(ev, currencyUnit)}</strong>
          </div>
        </div>

        {/* Dividend Yield */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 shadow-lg space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400 uppercase">Dividend Yield</span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-900/40 text-emerald-300 border border-emerald-700/30">
              Cash Return
            </span>
          </div>
          <div className="text-3xl font-black text-emerald-400 font-mono">
            {formatPercent(metrics.dividendYield)}
          </div>
          <div className="text-xs text-gray-400 pt-1 border-t border-gray-800">
            Annualized Cash Payout Yield
          </div>
        </div>
      </div>

      {/* Peer Valuation Comparison Chart */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-gray-800">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-blue-400" />
              <span>Sector Valuation Multiples Comparison ({company.sector})</span>
            </h3>
            <p className="text-xs text-gray-400">
              Comparing P/E and EV/EBITDA multiples across key industry peers
            </p>
          </div>
          <span className="text-xs text-blue-300 bg-blue-900/40 px-2.5 py-1 rounded border border-blue-700/50 font-mono">
            Active: {company.shortName} ({formatMultiple(metrics.peRatio)} P/E)
          </span>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={peerValuationData} margin={{ top: 20, right: 20, left: 10, bottom: 30 }}>
              <XAxis dataKey="name" stroke="#9CA3AF" fontSize={11} tickLine={false} angle={-15} textAnchor="end" />
              <YAxis stroke="#9CA3AF" fontSize={11} tickFormatter={(v) => `${v}x`} />
              <Tooltip 
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-[#0B0F19] border border-gray-700 p-3 rounded shadow-lg text-xs font-mono">
                        <div className="text-white font-bold">{data.name} ({data.ticker})</div>
                        <div className="text-blue-400 font-bold mt-1">P/E Multiple: {formatMultiple(data.pe)}</div>
                        <div className="text-purple-400 font-bold">EV/EBITDA: {formatMultiple(data.evEbitda)}</div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar dataKey="pe" name="P/E Multiple" radius={[4, 4, 0, 0]}>
                {peerValuationData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={entry.isCurrent ? '#3B82F6' : '#4B5563'} 
                    stroke={entry.isCurrent ? '#93C5FD' : 'transparent'}
                    strokeWidth={entry.isCurrent ? 2 : 0}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Quick Peer Navigation Links */}
        <div className="pt-2 border-t border-gray-800">
          <span className="text-xs text-gray-400 block mb-2 font-mono">Click to inspect sector peers:</span>
          <div className="flex flex-wrap gap-2">
            {sectorPeers.slice(0, 8).map(peer => (
              <button
                key={peer.id}
                onClick={() => onSelectPeer(peer)}
                className={`px-2.5 py-1 rounded text-xs font-mono transition-colors border ${
                  peer.id === company.id 
                    ? 'bg-blue-600 text-white border-blue-400' 
                    : 'bg-gray-800/80 text-gray-300 hover:bg-gray-700 border-gray-700'
                }`}
              >
                {peer.shortName} ({formatMultiple(peer.periods[periodId]?.valuation?.peRatio || 20)})
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Enterprise Value (EV) Bridge Decomposition */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          <span>Enterprise Value (EV) Construction Bridge</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-center font-mono">
          <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg">
            <span className="text-[11px] text-gray-400 block">Market Cap (+)</span>
            <span className="text-base font-bold text-blue-400">{formatCurrency(metrics.marketCap, currencyUnit)}</span>
          </div>
          <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg">
            <span className="text-[11px] text-gray-400 block">Total Debt (+)</span>
            <span className="text-base font-bold text-rose-400">{formatCurrency(debt, currencyUnit)}</span>
          </div>
          <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg">
            <span className="text-[11px] text-gray-400 block">Cash & Equivalents (-)</span>
            <span className="text-base font-bold text-emerald-400">{formatCurrency(cash, currencyUnit)}</span>
          </div>
          <div className="p-3 bg-blue-950/40 border border-blue-700/50 rounded-lg">
            <span className="text-[11px] text-blue-300 block font-semibold">Enterprise Value (=)</span>
            <span className="text-base font-bold text-white">{formatCurrency(ev, currencyUnit)}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
