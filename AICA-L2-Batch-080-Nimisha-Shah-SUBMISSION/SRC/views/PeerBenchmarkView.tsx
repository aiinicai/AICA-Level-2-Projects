import React, { useState } from 'react';
import { 
  BarChart3, 
  Layers, 
  TrendingUp, 
  Award, 
  ArrowUpDown, 
  ArrowRight,
  ExternalLink,
  Users2
} from 'lucide-react';
import { ListedCompany, CurrencyCode, UnitScale } from '../types/financial';
import { LISTED_COMPANIES } from '../data/listedCompaniesDataset';
import { formatFinancialValue, getCurrencyUnitLabel } from '../utils/formatUtils';

interface PeerBenchmarkViewProps {
  currentCompany: ListedCompany;
  onSelectCompany: (code: string) => void;
  companies?: ListedCompany[];
  currency?: CurrencyCode;
  scale?: UnitScale;
}

export const PeerBenchmarkView: React.FC<PeerBenchmarkViewProps> = ({ 
  currentCompany, 
  onSelectCompany, 
  companies = LISTED_COMPANIES,
  currency = 'INR',
  scale = 'crores'
}) => {
  const [selectedSector, setSelectedSector] = useState<string>(currentCompany.sector);
  const [sortBy, setSortBy] = useState<'marketCap' | 'sales' | 'roce' | 'opm' | 'de'>('marketCap');

  const formatVal = (val: number) => formatFinancialValue(val, currency, scale);

  const allSectors = Array.from(new Set(companies.map(c => c.sector)));
  const sectorCompanies = companies.filter(c => c.sector === selectedSector);

  // Sector Aggregates
  const totalMCap = sectorCompanies.reduce((acc, c) => acc + c.marketCap, 0);
  const totalSales = sectorCompanies.reduce((acc, c) => acc + c.salesLatestQuarter, 0);
  const totalEbitda = sectorCompanies.reduce((acc, c) => acc + c.ebitdaLatestQuarter, 0);
  const avgROCE = sectorCompanies.length > 0 ? sectorCompanies.reduce((acc, c) => acc + c.roce, 0) / sectorCompanies.length : 0;
  const avgDE = sectorCompanies.length > 0 ? sectorCompanies.reduce((acc, c) => acc + c.debtToEquity, 0) / sectorCompanies.length : 0;
  const sectorOPM = totalSales > 0 ? (totalEbitda / totalSales) * 100 : 0;

  const sortedList = [...sectorCompanies].sort((a, b) => {
    if (sortBy === 'marketCap') return b.marketCap - a.marketCap;
    if (sortBy === 'sales') return b.salesLatestQuarter - a.salesLatestQuarter;
    if (sortBy === 'roce') return b.roce - a.roce;
    if (sortBy === 'opm') return b.ebitdaMargin - a.ebitdaMargin;
    if (sortBy === 'de') return a.debtToEquity - b.debtToEquity;
    return 0;
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Sector Benchmark Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-blue-600" />
              <span>Cross-Company Sector Intelligence & Benchmark</span>
              <span className="text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">
                {getCurrencyUnitLabel(currency, scale)}
              </span>
            </h2>
            <p className="text-xs text-slate-500">
              Aggregated sector economics, peer ranking and profitability leadership
            </p>
          </div>

          {/* Sector Selector */}
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono text-slate-500">Sector:</span>
            <select
              value={selectedSector}
              onChange={(e) => setSelectedSector(e.target.value)}
              className="bg-slate-50 border border-slate-300 font-bold text-slate-900 text-xs rounded-lg px-3 py-1.5 focus:outline-none cursor-pointer"
            >
              {allSectors.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 4 Sector Aggregates Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
            <span className="text-slate-500 uppercase text-[10px]">Combined Sector MCap</span>
            <div className="text-xl font-bold text-slate-900">{formatVal(totalMCap)}</div>
            <span className="text-[11px] text-slate-500">{sectorCompanies.length} Entities Tracked</span>
          </div>

          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
            <span className="text-slate-500 uppercase text-[10px]">Combined Quarterly Revenue</span>
            <div className="text-xl font-bold text-blue-600">{formatVal(totalSales)}</div>
            <span className="text-[11px] text-slate-500">Latest Reported Quarter</span>
          </div>

          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
            <span className="text-slate-500 uppercase text-[10px]">Sector Weighted OPM %</span>
            <div className="text-xl font-bold text-emerald-600">{sectorOPM.toFixed(1)}%</div>
            <span className="text-[11px] text-slate-500">EBITDA: {formatVal(totalEbitda)}</span>
          </div>

          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
            <span className="text-slate-500 uppercase text-[10px]">Average ROCE / D/E</span>
            <div className="text-xl font-bold text-purple-600">{avgROCE.toFixed(1)}% &bull; {avgDE.toFixed(2)}x</div>
            <span className="text-[11px] text-slate-500">Industry Capital Efficiency</span>
          </div>
        </div>
      </div>

      {/* Sector Leaderboard */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Award className="w-4 h-4 text-amber-500" />
            <span>{selectedSector} Enterprise Ranking</span>
          </h3>

          <div className="flex items-center space-x-2 text-xs font-mono">
            <span className="text-slate-500">Sort by:</span>
            <div className="flex bg-slate-100 p-0.5 rounded border border-slate-200">
              <button
                onClick={() => setSortBy('marketCap')}
                className={`px-2 py-0.5 rounded text-[11px] ${sortBy === 'marketCap' ? 'bg-white text-slate-900 font-bold shadow-2xs' : 'text-slate-500'}`}
              >
                MCap
              </button>
              <button
                onClick={() => setSortBy('sales')}
                className={`px-2 py-0.5 rounded text-[11px] ${sortBy === 'sales' ? 'bg-white text-slate-900 font-bold shadow-2xs' : 'text-slate-500'}`}
              >
                Revenue
              </button>
              <button
                onClick={() => setSortBy('roce')}
                className={`px-2 py-0.5 rounded text-[11px] ${sortBy === 'roce' ? 'bg-white text-slate-900 font-bold shadow-2xs' : 'text-slate-500'}`}
              >
                ROCE
              </button>
              <button
                onClick={() => setSortBy('opm')}
                className={`px-2 py-0.5 rounded text-[11px] ${sortBy === 'opm' ? 'bg-white text-slate-900 font-bold shadow-2xs' : 'text-slate-500'}`}
              >
                OPM
              </button>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 uppercase text-[10px] bg-slate-50">
                <th className="py-2.5 px-3">Rank</th>
                <th className="py-2.5 px-3">Enterprise</th>
                <th className="py-2.5 px-3 text-right">Market Cap</th>
                <th className="py-2.5 px-3 text-right">Revenue</th>
                <th className="py-2.5 px-3 text-right">OPM %</th>
                <th className="py-2.5 px-3 text-right">ROCE %</th>
                <th className="py-2.5 px-3 text-right">D/E</th>
                <th className="py-2.5 px-3 text-center">Deep Dive</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sortedList.map((c, idx) => {
                const isCurrent = c.bseCode === currentCompany.bseCode;
                return (
                  <tr key={c.bseCode} className={`hover:bg-slate-50 transition-colors ${isCurrent ? 'bg-blue-50/80 font-bold' : ''}`}>
                    <td className="py-2.5 px-3 text-slate-400 font-bold">#{idx + 1}</td>
                    <td className="py-2.5 px-3 font-sans">
                      <div className="font-semibold text-slate-900 flex items-center gap-1.5">
                        <span>{c.name}</span>
                        {isCurrent && (
                          <span className="text-[10px] font-mono font-bold bg-blue-600 text-white px-1.5 py-0.2 rounded">
                            Active
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono">{c.nseCode} &bull; {c.industryGroup}</div>
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-900">
                      {formatVal(c.marketCap)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-blue-600 font-bold">
                      {formatVal(c.salesLatestQuarter)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-emerald-600">
                      {c.ebitdaMargin.toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-purple-600">
                      {c.roce.toFixed(1)}%
                    </td>
                    <td className={`py-2.5 px-3 text-right font-bold ${c.debtToEquity > 2.0 ? 'text-rose-600' : 'text-slate-800'}`}>
                      {c.debtToEquity.toFixed(2)}x
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <button
                        onClick={() => onSelectCompany(c.bseCode)}
                        className={`px-2 py-1 rounded text-[11px] font-sans inline-flex items-center gap-1 transition-colors ${
                          isCurrent 
                            ? 'bg-blue-600 text-white' 
                            : 'bg-slate-100 hover:bg-blue-600 hover:text-white text-slate-700'
                        }`}
                      >
                        <span>Select</span>
                        <ArrowRight className="w-3 h-3" />
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
