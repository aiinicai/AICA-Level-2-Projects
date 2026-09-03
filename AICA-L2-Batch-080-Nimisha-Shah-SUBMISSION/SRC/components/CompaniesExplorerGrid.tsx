import React, { useState, useMemo } from 'react';
import { 
  Grid3X3, 
  Search, 
  Download, 
  ArrowUpDown, 
  Filter, 
  ExternalLink,
  Building2,
  TrendingUp,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';
import { CompanyEntity, CurrencyUnit, PeriodId } from '../types/finance';
import { getAllCompanies, getAvailableSectors } from '../data/companiesData';
import { calculateDeterministicMetrics, formatCurrency, formatMultiple, formatPercent } from '../utils/financialCalculations';
import { exportUniverseToExcel } from '../utils/exportUtils';

interface CompaniesExplorerGridProps {
  periodId: PeriodId;
  currencyUnit: CurrencyUnit;
  onSelectCompany: (company: CompanyEntity) => void;
}

export const CompaniesExplorerGrid: React.FC<CompaniesExplorerGridProps> = ({
  periodId,
  currencyUnit,
  onSelectCompany
}) => {
  const allCompanies = getAllCompanies();
  const sectors = getAvailableSectors();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSector, setSelectedSector] = useState('ALL');
  const [mcapFilter, setMcapFilter] = useState<'ALL' | 'LARGE' | 'MID' | 'SMALL'>('ALL');
  const [leverageFilter, setLeverageFilter] = useState<'ALL' | 'LOW' | 'HIGH'>('ALL');
  const [roceFilter, setRoceFilter] = useState<'ALL' | 'HIGH' | 'LOW'>('ALL');
  const [sortCol, setSortCol] = useState<string>('mcap');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 25;

  const dataset = useMemo(() => {
    return allCompanies.map(c => {
      const m = calculateDeterministicMetrics(c, periodId);
      return {
        company: c,
        metrics: m
      };
    });
  }, [allCompanies, periodId]);

  const filteredData = useMemo(() => {
    return dataset.filter(({ company, metrics }) => {
      const matchSearch = 
        company.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        company.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
        company.sector.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchSector = selectedSector === 'ALL' || company.sector === selectedSector;

      let matchMcap = true;
      if (mcapFilter === 'LARGE') matchMcap = metrics.marketCap >= 50000;
      if (mcapFilter === 'MID') matchMcap = metrics.marketCap >= 10000 && metrics.marketCap < 50000;
      if (mcapFilter === 'SMALL') matchMcap = metrics.marketCap < 10000;

      let matchLev = true;
      if (leverageFilter === 'LOW') matchLev = metrics.debtToEquity <= 0.5;
      if (leverageFilter === 'HIGH') matchLev = metrics.debtToEquity > 2.0;

      let matchRoce = true;
      if (roceFilter === 'HIGH') matchRoce = metrics.rocePercent >= 15.0;
      if (roceFilter === 'LOW') matchRoce = metrics.rocePercent < 8.0;

      return matchSearch && matchSector && matchMcap && matchLev && matchRoce;
    });
  }, [dataset, searchQuery, selectedSector, mcapFilter, leverageFilter, roceFilter]);

  const sortedData = useMemo(() => {
    return [...filteredData].sort((a, b) => {
      let valA: any = 0;
      let valB: any = 0;
      switch (sortCol) {
        case 'name':
          valA = a.company.name;
          valB = b.company.name;
          return sortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        case 'sector':
          valA = a.company.sector;
          valB = b.company.sector;
          return sortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        case 'mcap':
          valA = a.metrics.marketCap;
          valB = b.metrics.marketCap;
          break;
        case 'rev':
          valA = a.metrics.revenue;
          valB = b.metrics.revenue;
          break;
        case 'ebitda':
          valA = a.metrics.ebitda;
          valB = b.metrics.ebitda;
          break;
        case 'pat':
          valA = a.metrics.pat;
          valB = b.metrics.pat;
          break;
        case 'opm':
          valA = a.metrics.opmPercent;
          valB = b.metrics.opmPercent;
          break;
        case 'npm':
          valA = a.metrics.npmPercent;
          valB = b.metrics.npmPercent;
          break;
        case 'de':
          valA = a.metrics.debtToEquity;
          valB = b.metrics.debtToEquity;
          break;
        case 'icr':
          valA = a.metrics.interestCoverage;
          valB = b.metrics.interestCoverage;
          break;
        case 'roce':
          valA = a.metrics.rocePercent;
          valB = b.metrics.rocePercent;
          break;
        case 'pe':
          valA = a.metrics.peRatio;
          valB = b.metrics.peRatio;
          break;
      }
      return sortDir === 'desc' ? valB - valA : valA - valB;
    });
  }, [filteredData, sortCol, sortDir]);

  const totalPages = Math.ceil(sortedData.length / pageSize);
  const paginatedData = sortedData.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleSort = (column: string) => {
    if (sortCol === column) {
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
    } else {
      setSortCol(column);
      setSortDir('desc');
    }
  };

  // CSV Export Function
  const exportToCSV = () => {
    const headers = [
      'Company Name',
      'Ticker',
      'BSE Code',
      'Sector',
      'Period',
      'Market Cap (INR Cr)',
      'Quarterly Revenue (INR Cr)',
      'Operating EBITDA (INR Cr)',
      'PAT (INR Cr)',
      'OPM %',
      'NPM %',
      'Debt-to-Equity (x)',
      'Interest Coverage (x)',
      'ROCE %',
      'P/E Multiple',
      'Dividend Yield %',
      'Risk Rating'
    ];

    const rows = sortedData.map(({ company, metrics }) => [
      `"${company.name}"`,
      company.ticker,
      company.bseCode,
      `"${company.sector}"`,
      periodId,
      metrics.marketCap,
      metrics.revenue,
      metrics.ebitda,
      metrics.pat,
      metrics.opmPercent.toFixed(2),
      metrics.npmPercent.toFixed(2),
      metrics.debtToEquity.toFixed(2),
      metrics.interestCoverage.toFixed(2),
      metrics.rocePercent.toFixed(2),
      metrics.peRatio.toFixed(2),
      metrics.dividendYield.toFixed(2),
      `"${metrics.riskRating}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `CFO_140_Universe_${periodId.replace(' ', '_')}_Export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Search & Filter Header Panel */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-4 border-b border-gray-800">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Grid3X3 className="w-4 h-4 text-blue-400" />
              <span>140+ Listed Enterprise Intelligence Grid ({periodId})</span>
            </h2>
            <p className="text-xs text-gray-400">
              Showing {filteredData.length} of {allCompanies.length} enterprises in universe
            </p>
          </div>

          {/* Export Buttons */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() => exportUniverseToExcel(periodId)}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition-all font-mono"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Excel (.xlsx)</span>
            </button>
            <button
              onClick={exportToCSV}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/20 transition-all font-mono"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export CSV</span>
            </button>
          </div>
        </div>

        {/* Filter Controls Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-gray-400" />
            <input
              type="text"
              placeholder="Search companies, ticker..."
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
              className="w-full pl-8 pr-3 py-1.5 bg-[#0B0F19] border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 font-sans"
            />
          </div>

          {/* Sector Filter */}
          <div>
            <select
              value={selectedSector}
              onChange={(e) => { setSelectedSector(e.target.value); setCurrentPage(1); }}
              className="w-full px-2.5 py-1.5 bg-[#0B0F19] border border-gray-700 rounded-lg text-cyan-300 focus:outline-none focus:border-blue-500 font-mono"
            >
              <option value="ALL">All Sectors ({sectors.length})</option>
              {sectors.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          {/* Market Cap Filter */}
          <div>
            <select
              value={mcapFilter}
              onChange={(e) => { setMcapFilter(e.target.value as any); setCurrentPage(1); }}
              className="w-full px-2.5 py-1.5 bg-[#0B0F19] border border-gray-700 rounded-lg text-blue-300 focus:outline-none focus:border-blue-500 font-mono"
            >
              <option value="ALL">All Market Caps</option>
              <option value="LARGE">Large Cap (&gt; ₹50,000 Cr)</option>
              <option value="MID">Mid Cap (₹10,000 - ₹50,000 Cr)</option>
              <option value="SMALL">Small Cap (&lt; ₹10,000 Cr)</option>
            </select>
          </div>

          {/* Leverage Filter */}
          <div>
            <select
              value={leverageFilter}
              onChange={(e) => { setLeverageFilter(e.target.value as any); setCurrentPage(1); }}
              className="w-full px-2.5 py-1.5 bg-[#0B0F19] border border-gray-700 rounded-lg text-emerald-300 focus:outline-none focus:border-blue-500 font-mono"
            >
              <option value="ALL">All Leverage Levels</option>
              <option value="LOW">Low Debt (D/E &le; 0.5x)</option>
              <option value="HIGH">High Leverage (D/E &gt; 2.0x)</option>
            </select>
          </div>

          {/* ROCE Filter */}
          <div>
            <select
              value={roceFilter}
              onChange={(e) => { setRoceFilter(e.target.value as any); setCurrentPage(1); }}
              className="w-full px-2.5 py-1.5 bg-[#0B0F19] border border-gray-700 rounded-lg text-purple-300 focus:outline-none focus:border-blue-500 font-mono"
            >
              <option value="ALL">All ROCE Tiers</option>
              <option value="HIGH">High ROCE (&gt; 15.0%)</option>
              <option value="LOW">Low ROCE (&lt; 8.0%)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Comprehensive Data Grid */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg overflow-hidden space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 uppercase text-[10px] tracking-wider bg-gray-900/80">
                <th onClick={() => handleSort('name')} className="py-3 px-3 cursor-pointer hover:text-white">
                  <span className="flex items-center gap-1">Company / Ticker <ArrowUpDown className="w-3 h-3 text-gray-500" /></span>
                </th>
                <th onClick={() => handleSort('sector')} className="py-3 px-3 cursor-pointer hover:text-white">
                  <span className="flex items-center gap-1">Sector <ArrowUpDown className="w-3 h-3 text-gray-500" /></span>
                </th>
                <th onClick={() => handleSort('mcap')} className="py-3 px-3 text-right cursor-pointer hover:text-white">
                  <span className="flex items-center justify-end gap-1">MCap <ArrowUpDown className="w-3 h-3 text-gray-500" /></span>
                </th>
                <th onClick={() => handleSort('rev')} className="py-3 px-3 text-right cursor-pointer hover:text-white">
                  <span className="flex items-center justify-end gap-1">Revenue <ArrowUpDown className="w-3 h-3 text-gray-500" /></span>
                </th>
                <th onClick={() => handleSort('ebitda')} className="py-3 px-3 text-right cursor-pointer hover:text-white">
                  <span className="flex items-center justify-end gap-1">EBITDA <ArrowUpDown className="w-3 h-3 text-gray-500" /></span>
                </th>
                <th onClick={() => handleSort('pat')} className="py-3 px-3 text-right cursor-pointer hover:text-white">
                  <span className="flex items-center justify-end gap-1">PAT <ArrowUpDown className="w-3 h-3 text-gray-500" /></span>
                </th>
                <th onClick={() => handleSort('opm')} className="py-3 px-3 text-right cursor-pointer hover:text-white">
                  <span className="flex items-center justify-end gap-1">OPM % <ArrowUpDown className="w-3 h-3 text-gray-500" /></span>
                </th>
                <th onClick={() => handleSort('de')} className="py-3 px-3 text-right cursor-pointer hover:text-white">
                  <span className="flex items-center justify-end gap-1">D/E <ArrowUpDown className="w-3 h-3 text-gray-500" /></span>
                </th>
                <th onClick={() => handleSort('icr')} className="py-3 px-3 text-right cursor-pointer hover:text-white">
                  <span className="flex items-center justify-end gap-1">Cover <ArrowUpDown className="w-3 h-3 text-gray-500" /></span>
                </th>
                <th onClick={() => handleSort('roce')} className="py-3 px-3 text-right cursor-pointer hover:text-white">
                  <span className="flex items-center justify-end gap-1">ROCE % <ArrowUpDown className="w-3 h-3 text-gray-500" /></span>
                </th>
                <th onClick={() => handleSort('pe')} className="py-3 px-3 text-right cursor-pointer hover:text-white">
                  <span className="flex items-center justify-end gap-1">P/E <ArrowUpDown className="w-3 h-3 text-gray-500" /></span>
                </th>
                <th className="py-3 px-3 text-center">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {paginatedData.map(({ company, metrics }) => (
                <tr key={company.id} className="hover:bg-blue-600/10 transition-colors">
                  <td className="py-2.5 px-3">
                    <div className="font-semibold text-white font-sans truncate max-w-[180px]">{company.name}</div>
                    <div className="text-[10px] text-gray-400">{company.ticker} &bull; BSE {company.bseCode}</div>
                  </td>
                  <td className="py-2.5 px-3 text-[11px] text-gray-300 font-sans truncate max-w-[150px]">
                    {company.sector}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-white">
                    {formatCurrency(metrics.marketCap, currencyUnit)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-blue-300">
                    {formatCurrency(metrics.revenue, currencyUnit)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-cyan-300">
                    {formatCurrency(metrics.ebitda, currencyUnit)}
                  </td>
                  <td className={`py-2.5 px-3 text-right font-bold ${metrics.pat >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {formatCurrency(metrics.pat, currencyUnit)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-cyan-300">
                    {formatPercent(metrics.opmPercent, 1)}
                  </td>
                  <td className={`py-2.5 px-3 text-right font-bold ${metrics.debtToEquity > 2.0 ? 'text-rose-400' : 'text-gray-300'}`}>
                    {formatMultiple(metrics.debtToEquity)}
                  </td>
                  <td className={`py-2.5 px-3 text-right font-bold ${metrics.interestCoverage < 1.5 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {formatMultiple(metrics.interestCoverage)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-bold text-purple-300">
                    {formatPercent(metrics.rocePercent, 1)}
                  </td>
                  <td className="py-2.5 px-3 text-right text-blue-400">
                    {formatMultiple(metrics.peRatio)}
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <button
                      onClick={() => onSelectCompany(company)}
                      className="px-2 py-1 rounded bg-blue-600/80 hover:bg-blue-600 text-white text-[10px] font-sans inline-flex items-center gap-1 transition-colors"
                      title="Inspect enterprise in detail"
                    >
                      <span>View</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination Navigation */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-gray-800 text-xs font-mono">
          <div className="text-gray-400">
            Page <span className="text-white font-bold">{currentPage}</span> of <span className="text-white font-bold">{totalPages || 1}</span> ({filteredData.length} records)
          </div>
          <div className="flex items-center space-x-1">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:pointer-events-none text-white transition-colors"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages || totalPages === 0}
              className="px-3 py-1 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:pointer-events-none text-white transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
