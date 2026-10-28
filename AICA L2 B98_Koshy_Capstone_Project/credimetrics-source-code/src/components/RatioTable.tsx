import React, { useState } from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Filter, 
  HelpCircle, 
  Layers, 
  Droplets, 
  TrendingUp, 
  Scale, 
  Zap,
  Info
} from 'lucide-react';
import { FinancialRatios, FinancialStatement, RatioItem } from '../types/financial';

interface RatioTableProps {
  currentRatios: FinancialRatios;
  allStatements: FinancialStatement[];
  allRatiosByYear: Record<string, FinancialRatios>;
}

export const RatioTable: React.FC<RatioTableProps> = ({
  currentRatios,
  allStatements,
  allRatiosByYear
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [activeTooltip, setActiveTooltip] = useState<string | null>(null);

  const categories = ['All', 'Liquidity', 'Profitability', 'Solvency', 'Efficiency'];

  const filteredItems = selectedCategory === 'All'
    ? currentRatios.items
    : currentRatios.items.filter(item => item.category === selectedCategory);

  const getStatusBadge = (status: 'Healthy' | 'Moderate' | 'Risk') => {
    switch (status) {
      case 'Healthy':
        return (
          <span className="inline-flex items-center space-x-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" />
            <span>Healthy</span>
          </span>
        );
      case 'Moderate':
        return (
          <span className="inline-flex items-center space-x-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="w-3 h-3" />
            <span>Moderate</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <XCircle className="w-3 h-3" />
            <span>Risk</span>
          </span>
        );
    }
  };

  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case 'Liquidity': return <Droplets className="w-3.5 h-3.5 text-cyan-400" />;
      case 'Profitability': return <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />;
      case 'Solvency': return <Scale className="w-3.5 h-3.5 text-indigo-400" />;
      case 'Efficiency': return <Zap className="w-3.5 h-3.5 text-amber-400" />;
      default: return <Layers className="w-3.5 h-3.5 text-blue-400" />;
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
      {/* Header and Category Filters */}
      <div className="p-5 lg:p-6 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-base font-bold text-white tracking-tight">Financial Ratio Computation Engine</h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
              {currentRatios.financialYear}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Standardized ratios evaluated against institutional underwriting criteria and historical baselines.
          </p>
        </div>

        {/* Category Pills */}
        <div className="flex flex-wrap items-center gap-1.5 bg-slate-800/80 p-1 rounded-xl border border-slate-700/80">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                selectedCategory === cat 
                  ? 'bg-blue-600 text-white shadow' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/60'
              }`}
            >
              {getCategoryIcon(cat)}
              <span>{cat}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-800/50 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
            <tr>
              <th className="py-3 px-4">Ratio Name</th>
              <th className="py-3 px-4">Formula</th>
              {/* Multi-Year Columns */}
              {allStatements.map(stmt => (
                <th key={stmt.id} className="py-3 px-3 text-right">
                  {stmt.financialYear}
                </th>
              ))}
              <th className="py-3 px-4 text-center">Benchmark</th>
              <th className="py-3 px-4 text-center">Status</th>
              <th className="py-3 px-4">Analytical Interpretation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-200">
            {filteredItems.map(item => {
              return (
                <tr key={item.id} className="hover:bg-slate-800/40 transition">
                  {/* Name */}
                  <td className="py-3.5 px-4 font-semibold text-white whitespace-nowrap">
                    <div className="flex items-center space-x-2">
                      <span className="text-slate-400">{getCategoryIcon(item.category)}</span>
                      <span>{item.name}</span>
                    </div>
                  </td>

                  {/* Formula */}
                  <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px] whitespace-nowrap">
                    {item.formula}
                  </td>

                  {/* Multi-year comparison */}
                  {allStatements.map(stmt => {
                    const yearRatios = allRatiosByYear[stmt.financialYear];
                    const matchedItem = yearRatios?.items.find(i => i.id === item.id);
                    const isCurrentYear = stmt.financialYear === currentRatios.financialYear;
                    return (
                      <td 
                        key={stmt.id} 
                        className={`py-3.5 px-3 text-right font-mono font-bold whitespace-nowrap ${
                          isCurrentYear ? 'text-cyan-300 text-sm' : 'text-slate-400'
                        }`}
                      >
                        {matchedItem ? matchedItem.formattedValue : '—'}
                      </td>
                    );
                  })}

                  {/* Benchmark */}
                  <td className="py-3.5 px-4 text-center text-slate-300 font-mono whitespace-nowrap">
                    {item.benchmark}
                  </td>

                  {/* Status */}
                  <td className="py-3.5 px-4 text-center whitespace-nowrap">
                    {getStatusBadge(item.status)}
                  </td>

                  {/* Interpretation */}
                  <td className="py-3.5 px-4 text-slate-300 text-[11px] max-w-xs">
                    {item.interpretation}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Summary Footer */}
      <div className="p-4 bg-slate-800/40 border-t border-slate-800 text-xs text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-2">
        <span>Displaying {filteredItems.length} computed ratios across {allStatements.length} audited financial years.</span>
        <span className="text-slate-400 text-[11px]">Values in <strong className="text-cyan-300">cyan</strong> indicate current underwriting period ({currentRatios.financialYear}).</span>
      </div>
    </div>
  );
};
