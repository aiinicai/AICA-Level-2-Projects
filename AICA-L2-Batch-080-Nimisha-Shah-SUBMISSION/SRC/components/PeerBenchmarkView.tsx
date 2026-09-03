import React, { useState, useMemo } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Building, 
  Layers, 
  Search, 
  ArrowUpDown, 
  ExternalLink,
  PieChart as PieIcon,
  Award
} from 'lucide-react';
import { CompanyEntity, CurrencyUnit, PeriodId } from '../types/finance';
import { getAllCompanies, getAvailableSectors } from '../data/companiesData';
import { calculateDeterministicMetrics, formatCurrency, formatMultiple, formatPercent } from '../utils/financialCalculations';

interface PeerBenchmarkViewProps {
  periodId: PeriodId;
  currencyUnit: CurrencyUnit;
  onSelectCompany: (company: CompanyEntity) => void;
}

export const PeerBenchmarkView: React.FC<PeerBenchmarkViewProps> = ({
  periodId,
  currencyUnit,
  onSelectCompany
}) => {
  const allCompanies = getAllCompanies();
  const sectors = getAvailableSectors();

  const [selectedSector, setSelectedSector] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortField, setSortField] = useState<'mcap' | 'revenue' | 'ebitda' | 'opm' | 'roce' | 'de'>('mcap');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Compute metrics for all companies
  const companyMetricsList = useMemo(() => {
    return allCompanies.map(comp => {
      const metrics = calculateDeterministicMetrics(comp, periodId);
      return {
        company: comp,
        metrics
      };
    });
  }, [allCompanies, periodId]);

  // Filtered list
  const filteredList = useMemo(() => {
    return companyMetricsList.filter(item => {
      const matchSector = selectedSector === 'ALL' || item.company.sector === selectedSector;
      const matchSearch = item.company.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.company.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.company.sector.toLowerCase().includes(searchQuery.toLowerCase());
      return matchSector && matchSearch;
    });
  }, [companyMetricsList, selectedSector, searchQuery]);

  // Sorted list
  const sortedList = useMemo(() => {
    return [...filteredList].sort((a, b) => {
      let valA = 0;
      let valB = 0;
      switch (sortField) {
        case 'mcap':
          valA = a.metrics.marketCap;
          valB = b.metrics.marketCap;
          break;
        case 'revenue':
          valA = a.metrics.revenue;
          valB = b.metrics.revenue;
          break;
        case 'ebitda':
          valA = a.metrics.ebitda;
          valB = b.metrics.ebitda;
          break;
        case 'opm':
          valA = a.metrics.opmPercent;
          valB = b.metrics.opmPercent;
          break;
        case 'roce':
          valA = a.metrics.rocePercent;
          valB = b.metrics.rocePercent;
          break;
        case 'de':
          valA = a.metrics.debtToEquity;
          valB = b.metrics.debtToEquity;
          break;
      }
      return sortDirection === 'desc' ? valB - valA : valA - valB;
    });
  }, [filteredList, sortField, sortDirection]);

  // Aggregate stats for the active sector selection
  const sectorAggregates = useMemo(() => {
    const totalMCap = filteredList.reduce((acc, item) => acc + item.metrics.marketCap, 0);
    const totalRev = filteredList.reduce((acc, item) => acc + item.metrics.revenue, 0);
    const totalEbitda = filteredList.reduce((acc, item) => acc + item.metrics.ebitda, 0);
    const totalDebt = filteredList.reduce((acc, item) => acc + item.metrics.totalDebt, 0);
    const totalNetWorth = filteredList.reduce((acc, item) => acc + item.metrics.netWorth, 0);

    const meanROCE = filteredList.length > 0
      ? filteredList.reduce((acc, item) => acc + item.metrics.rocePercent, 0) / filteredList.length
      : 0;

    const aggregateOPM = totalRev > 0 ? (totalEbitda / totalRev) * 100 : 0;
    const aggregateDE = totalNetWorth > 0 ? totalDebt / totalNetWorth : 0;

    return {
      count: filteredList.length,
      totalMCap,
      totalRev,
      totalEbitda,
      aggregateOPM,
      meanROCE,
      aggregateDE
    };
  }, [filteredList]);

  const handleSort = (field: 'mcap' | 'revenue' | 'ebitda' | 'opm' | 'roce' | 'de') => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'desc' ? 'asc' : 'desc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  return (
    <div className="space-y-6">
      {/* Sector Intelligence & Aggregate Dashboard */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-4 border-b border-gray-800">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-blue-400" />
              <span>Cross-Company Multi-Entity Industry Aggregates</span>
            </h2>
            <p className="text-xs text-gray-400">
              Benchmarking {sectorAggregates.count} listed enterprises across {sectors.length} sectors ({periodId})
            </p>
          </div>

          {/* Sector Selector Filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400 font-mono">Sector:</span>
            <select
              value={selectedSector}
              onChange={(e) => setSelectedSector(e.target.value)}
              className="bg-[#0B0F19] border border-gray-700 text-xs font-semibold text-cyan-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500 max-w-xs"
            >
              <option value="ALL">ALL SECTORS (140+ Universe)</option>
              {sectors.map(s => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Aggregate KPI Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg space-y-1">
            <span className="text-[10px] text-gray-400 uppercase font-mono">Total Market Cap</span>
            <div className="text-base font-bold text-white font-mono">
              {formatCurrency(sectorAggregates.totalMCap, currencyUnit)}
            </div>
            <span className="text-[10px] text-cyan-400 font-mono">{sectorAggregates.count} Enterprises</span>
          </div>

          <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg space-y-1">
            <span className="text-[10px] text-gray-400 uppercase font-mono">Combined Topline</span>
            <div className="text-base font-bold text-blue-400 font-mono">
              {formatCurrency(sectorAggregates.totalRev, currencyUnit)}
            </div>
            <span className="text-[10px] text-gray-400 font-mono">Quarterly Ops</span>
          </div>

          <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg space-y-1">
            <span className="text-[10px] text-gray-400 uppercase font-mono">Aggregate OPM %</span>
            <div className="text-base font-bold text-cyan-400 font-mono">
              {formatPercent(sectorAggregates.aggregateOPM, 1)}
            </div>
            <span className="text-[10px] text-gray-400 font-mono">Operating Margin</span>
          </div>

          <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg space-y-1">
            <span className="text-[10px] text-gray-400 uppercase font-mono">Mean ROCE %</span>
            <div className="text-base font-bold text-purple-400 font-mono">
              {formatPercent(sectorAggregates.meanROCE, 1)}
            </div>
            <span className="text-[10px] text-emerald-400 font-mono">
              Spread: {formatPercent(sectorAggregates.meanROCE - 10, 1, true)}
            </span>
          </div>

          <div className="p-3 bg-[#0B0F19] border border-gray-800 rounded-lg space-y-1">
            <span className="text-[10px] text-gray-400 uppercase font-mono">Aggregate Gearing</span>
            <div className="text-base font-bold text-emerald-400 font-mono">
              {formatMultiple(sectorAggregates.aggregateDE)}
            </div>
            <span className="text-[10px] text-gray-400 font-mono">Sector D/E</span>
          </div>
        </div>
      </div>

      {/* Sortable Leaderboard Table */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg overflow-hidden space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-gray-800">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Award className="w-4 h-4 text-amber-400" />
              <span>Enterprise Peer Benchmark Leaderboard</span>
            </h3>
            <p className="text-xs text-gray-400">
              Ranked cross-company metrics for selected sector. Click column headers to sort.
            </p>
          </div>

          {/* Table Search Input */}
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-gray-400" />
            <input
              type="text"
              placeholder="Filter by company or ticker..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-[#0B0F19] border border-gray-700 rounded-lg text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 font-sans"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 uppercase text-[10px] tracking-wider bg-gray-900/70">
                <th className="py-3 px-3">#</th>
                <th className="py-3 px-3">Enterprise Name & Symbol</th>
                <th className="py-3 px-3">Sector</th>
                <th 
                  onClick={() => handleSort('mcap')} 
                  className="py-3 px-3 text-right cursor-pointer hover:text-white transition-colors"
                >
                  <span className="flex items-center justify-end gap-1">
                    Market Cap <ArrowUpDown className="w-3 h-3 text-gray-500" />
                  </span>
                </th>
                <th 
                  onClick={() => handleSort('revenue')} 
                  className="py-3 px-3 text-right cursor-pointer hover:text-white transition-colors"
                >
                  <span className="flex items-center justify-end gap-1">
                    Revenue <ArrowUpDown className="w-3 h-3 text-gray-500" />
                  </span>
                </th>
                <th 
                  onClick={() => handleSort('opm')} 
                  className="py-3 px-3 text-right cursor-pointer hover:text-white transition-colors"
                >
                  <span className="flex items-center justify-end gap-1">
                    OPM % <ArrowUpDown className="w-3 h-3 text-gray-500" />
                  </span>
                </th>
                <th 
                  onClick={() => handleSort('roce')} 
                  className="py-3 px-3 text-right cursor-pointer hover:text-white transition-colors"
                >
                  <span className="flex items-center justify-end gap-1">
                    ROCE % <ArrowUpDown className="w-3 h-3 text-gray-500" />
                  </span>
                </th>
                <th 
                  onClick={() => handleSort('de')} 
                  className="py-3 px-3 text-right cursor-pointer hover:text-white transition-colors"
                >
                  <span className="flex items-center justify-end gap-1">
                    D/E <ArrowUpDown className="w-3 h-3 text-gray-500" />
                  </span>
                </th>
                <th className="py-3 px-3 text-right">Int. Cover</th>
                <th className="py-3 px-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {sortedList.slice(0, 50).map((item, idx) => (
                <tr 
                  key={item.company.id} 
                  className="hover:bg-blue-600/10 transition-colors group"
                >
                  <td className="py-2.5 px-3 text-gray-500 font-mono">{idx + 1}</td>
                  <td className="py-2.5 px-3">
                    <div className="font-semibold text-white font-sans truncate max-w-[200px]">{item.company.name}</div>
                    <div className="text-[10px] text-gray-400 font-mono">{item.company.ticker} &bull; BSE: {item.company.bseCode}</div>
                  </td>
                  <td className="py-2.5 px-3 text-[11px] text-gray-300 font-sans truncate max-w-[180px]">
                    {item.company.sector}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-white">
                    {formatCurrency(item.metrics.marketCap, currencyUnit)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-blue-300">
                    {formatCurrency(item.metrics.revenue, currencyUnit)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-cyan-300">
                    {formatPercent(item.metrics.opmPercent, 1)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-purple-300">
                    {formatPercent(item.metrics.rocePercent, 1)}
                  </td>
                  <td className={`py-2.5 px-3 text-right font-bold ${
                    item.metrics.debtToEquity > 2.0 ? 'text-rose-400' : 'text-gray-300'
                  }`}>
                    {formatMultiple(item.metrics.debtToEquity)}
                  </td>
                  <td className={`py-2.5 px-3 text-right font-bold ${
                    item.metrics.interestCoverage < 1.5 ? 'text-rose-400' : 'text-emerald-400'
                  }`}>
                    {formatMultiple(item.metrics.interestCoverage)}
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <button
                      onClick={() => onSelectCompany(item.company)}
                      className="px-2 py-1 rounded bg-blue-600/80 hover:bg-blue-600 text-white text-[11px] font-sans transition-colors inline-flex items-center gap-1"
                      title="Inspect enterprise in deep-dive mode"
                    >
                      <span>Cockpit</span>
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
