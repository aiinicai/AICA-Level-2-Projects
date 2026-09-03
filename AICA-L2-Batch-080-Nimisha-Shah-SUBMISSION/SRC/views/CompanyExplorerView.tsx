import React, { useState, useMemo } from 'react';
import { 
  TableProperties, 
  Search, 
  Filter, 
  ArrowUpDown, 
  Download, 
  ChevronLeft, 
  ChevronRight, 
  Building2, 
  ExternalLink,
  Layers,
  FileSpreadsheet
} from 'lucide-react';
import { ListedCompany, CurrencyCode, UnitScale } from '../types/financial';
import { LISTED_COMPANIES } from '../data/listedCompaniesDataset';
import { formatFinancialValue, getCurrencyUnitLabel } from '../utils/formatUtils';
import * as XLSX from 'xlsx';

interface CompanyExplorerViewProps {
  currentCompany: ListedCompany;
  onSelectCompany: (code: string) => void;
  companies?: ListedCompany[];
  currency?: CurrencyCode;
  scale?: UnitScale;
}

export const CompanyExplorerView: React.FC<CompanyExplorerViewProps> = ({
  currentCompany,
  onSelectCompany,
  companies = LISTED_COMPANIES,
  currency = 'INR',
  scale = 'crores'
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSector, setSelectedSector] = useState('ALL');
  const [sortField, setSortField] = useState<keyof ListedCompany>('marketCap');
  const [sortAsc, setSortAsc] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;

  const formatVal = (val: number) => formatFinancialValue(val, currency, scale);

  const sectors = useMemo(() => {
    return Array.from(new Set(companies.map(c => c.sector)));
  }, [companies]);

  const filteredData = useMemo(() => {
    return companies.filter(c => {
      const matchSearch = 
        c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.nseCode.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.bseCode.includes(searchTerm);
      const matchSector = selectedSector === 'ALL' || c.sector === selectedSector;
      return matchSearch && matchSector;
    }).sort((a, b) => {
      const aIsCustom = Number(a.bseCode) >= 600000;
      const bIsCustom = Number(b.bseCode) >= 600000;
      if (aIsCustom && !bIsCustom) return -1;
      if (!aIsCustom && bIsCustom) return 1;

      const aVal = a[sortField];
      const bVal = b[sortField];
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortAsc ? aVal - bVal : bVal - aVal;
      }
      return sortAsc 
        ? String(aVal).localeCompare(String(bVal)) 
        : String(bVal).localeCompare(String(aVal));
    });
  }, [companies, searchTerm, selectedSector, sortField, sortAsc]);

  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredData.slice(start, start + itemsPerPage);
  }, [filteredData, currentPage]);

  const handleSort = (field: keyof ListedCompany) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const exportToExcel = () => {
    const exportRows = filteredData.map(c => ({
      'Company Name': c.name,
      'NSE Code': c.nseCode,
      'BSE Code': c.bseCode,
      'Sector': c.sector,
      'Industry Group': c.industryGroup,
      'Market Cap (₹ Cr)': c.marketCap,
      'Stock Price (₹)': c.stockPrice,
      'PE Ratio': c.peRatio,
      'PB Ratio': c.pbRatio,
      'Dividend Yield %': c.dividendYield,
      'Revenue (₹ Cr)': c.salesLatestQuarter,
      'Operating EBITDA (₹ Cr)': c.ebitdaLatestQuarter,
      'EBITDA Margin %': c.ebitdaMargin,
      'Net Profit (₹ Cr)': c.netProfitLatestQuarter,
      'PAT Margin %': c.netProfitMargin,
      'Debt to Equity': c.debtToEquity,
      'Interest Coverage': c.interestCoverage,
      'ROCE %': c.roce,
      'Sales YoY %': c.salesGrowthYoY,
      'PAT YoY %': c.netProfitGrowthYoY
    }));

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(exportRows);
    XLSX.utils.book_append_sheet(wb, ws, 'Enterprises Data');
    XLSX.writeFile(wb, 'CFO_Enterprise_Universe_Dataset.xlsx');
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <TableProperties className="w-4 h-4 text-blue-600" />
              <span>140+ Listed Corporate Financials Grid</span>
              <span className="text-xs font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">
                {getCurrencyUnitLabel(currency, scale)}
              </span>
            </h2>
            <p className="text-xs text-slate-500">
              Interactive financial intelligence database with sorting, filtering, and 1-click Excel export
            </p>
          </div>

          <button
            onClick={exportToExcel}
            className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold font-mono transition-colors shadow flex items-center gap-1.5 shrink-0"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export to Excel (.xlsx)</span>
          </button>
        </div>

        {/* Search and Filters */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="relative sm:col-span-2">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by company name, ticker (e.g. RELIANCE, TCS), or BSE code..."
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
              className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 font-sans"
            />
          </div>

          <div>
            <select
              value={selectedSector}
              onChange={(e) => { setSelectedSector(e.target.value); setCurrentPage(1); }}
              className="w-full py-2 px-3 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 font-sans cursor-pointer text-slate-800 font-medium"
            >
              <option value="ALL">All Sectors ({sectors.length})</option>
              {sectors.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Main Data Grid */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 uppercase text-[10px] tracking-wider bg-slate-50">
                <th onClick={() => handleSort('name')} className="py-3 px-3 cursor-pointer hover:text-slate-900">
                  <div className="flex items-center space-x-1">
                    <span>Enterprise</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-3">Sector</th>
                <th onClick={() => handleSort('marketCap')} className="py-3 px-3 text-right cursor-pointer hover:text-slate-900">
                  <div className="flex items-center justify-end space-x-1">
                    <span>MCap</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th onClick={() => handleSort('salesLatestQuarter')} className="py-3 px-3 text-right cursor-pointer hover:text-slate-900">
                  <div className="flex items-center justify-end space-x-1">
                    <span>Revenue</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th onClick={() => handleSort('ebitdaMargin')} className="py-3 px-3 text-right cursor-pointer hover:text-slate-900">
                  <div className="flex items-center justify-end space-x-1">
                    <span>OPM %</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th onClick={() => handleSort('netProfitLatestQuarter')} className="py-3 px-3 text-right cursor-pointer hover:text-slate-900">
                  <div className="flex items-center justify-end space-x-1">
                    <span>PAT</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th onClick={() => handleSort('debtToEquity')} className="py-3 px-3 text-right cursor-pointer hover:text-slate-900">
                  <div className="flex items-center justify-end space-x-1">
                    <span>D/E</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th onClick={() => handleSort('roce')} className="py-3 px-3 text-right cursor-pointer hover:text-slate-900">
                  <div className="flex items-center justify-end space-x-1">
                    <span>ROCE %</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paginatedData.map((c) => {
                const isSelected = c.bseCode === currentCompany.bseCode;
                return (
                  <tr 
                    key={c.bseCode} 
                    className={`hover:bg-slate-50 transition-colors ${isSelected ? 'bg-blue-50/70 font-semibold' : ''}`}
                  >
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-slate-900 font-sans">{c.name}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{c.nseCode} &bull; {c.bseCode}</div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-600 font-sans">{c.sector}</td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-900">
                      {formatVal(c.marketCap)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-blue-600 font-bold">
                      {formatVal(c.salesLatestQuarter)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-emerald-600">
                      {c.ebitdaMargin.toFixed(1)}%
                    </td>
                    <td className={`py-2.5 px-3 text-right font-bold ${c.netProfitLatestQuarter >= 0 ? 'text-indigo-600' : 'text-rose-600'}`}>
                      {formatVal(c.netProfitLatestQuarter)}
                    </td>
                    <td className={`py-2.5 px-3 text-right font-bold ${c.debtToEquity > 2.0 ? 'text-rose-600' : 'text-slate-800'}`}>
                      {c.debtToEquity.toFixed(2)}x
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-purple-600">
                      {c.roce.toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <button
                        onClick={() => onSelectCompany(c.bseCode)}
                        className={`px-2.5 py-1 rounded text-[11px] font-sans transition-colors ${
                          isSelected 
                            ? 'bg-blue-600 text-white font-bold' 
                            : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                        }`}
                      >
                        {isSelected ? 'Active' : 'Analyze'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs font-mono">
          <div className="text-slate-500">
            Showing <span className="font-bold text-slate-900">{(currentPage - 1) * itemsPerPage + 1}</span> to{' '}
            <span className="font-bold text-slate-900">{Math.min(currentPage * itemsPerPage, filteredData.length)}</span> of{' '}
            <span className="font-bold text-slate-900">{filteredData.length}</span> listed companies
          </div>

          <div className="flex items-center space-x-1">
            <button
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="p-1.5 rounded border border-slate-300 bg-white hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <span className="px-3 py-1 font-bold text-slate-900">
              Page {currentPage} of {Math.max(1, totalPages)}
            </span>

            <button
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages || totalPages === 0}
              className="p-1.5 rounded border border-slate-300 bg-white hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
