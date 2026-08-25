import React, { useState, useMemo } from 'react';
import { 
  AlertOctagon, 
  AlertTriangle, 
  CheckCircle2, 
  Search, 
  Copy, 
  Check, 
  Calculator
} from 'lucide-react';
import { InconsistencyItem, RiskLevel } from '../types';

interface Part2InconsistenciesTableProps {
  inconsistencies: InconsistencyItem[];
  onOpenReconciler?: (item: InconsistencyItem) => void;
}

export const Part2InconsistenciesTable: React.FC<Part2InconsistenciesTableProps> = ({
  inconsistencies,
  onOpenReconciler,
}) => {
  const [riskFilter, setRiskFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [copied, setCopied] = useState(false);

  const filteredItems = useMemo(() => {
    return inconsistencies.filter((item) => {
      const matchesRisk = riskFilter === 'ALL' || item.riskLevel.toLowerCase() === riskFilter.toLowerCase();
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        item.lineItem.toLowerCase().includes(q) ||
        item.primaryFigure.toLowerCase().includes(q) ||
        item.noteFigure.toLowerCase().includes(q) ||
        item.discrepancy.toLowerCase().includes(q) ||
        (item.noteRef && item.noteRef.toLowerCase().includes(q));
      return matchesRisk && matchesSearch;
    });
  }, [inconsistencies, riskFilter, searchQuery]);

  const counts = useMemo(() => {
    return {
      total: inconsistencies.length,
      high: inconsistencies.filter((i) => i.riskLevel.toLowerCase() === 'high').length,
      med: inconsistencies.filter((i) => i.riskLevel.toLowerCase() === 'medium' || i.riskLevel.toLowerCase() === 'med').length,
      low: inconsistencies.filter((i) => i.riskLevel.toLowerCase() === 'low').length,
    };
  }, [inconsistencies]);

  const getRiskBadge = (level: RiskLevel | string) => {
    const norm = level.toLowerCase();
    if (norm === 'high') {
      return (
        <span className="bg-red-600 text-white px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider inline-block">
          HIGH RISK
        </span>
      );
    }
    if (norm === 'medium' || norm === 'med') {
      return (
        <span className="bg-orange-500 text-white px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider inline-block">
          MED RISK
        </span>
      );
    }
    return (
      <span className="bg-[#141414] text-white px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider inline-block">
        LOW RISK
      </span>
    );
  };

  const handleCopyTable = () => {
    const header = "Financial Statement Line Item\tPrimary Statement Figure\tCorresponding Note Figure\tDiscrepancy / Observation\tRisk Level\n";
    const rows = filteredItems
      .map((i) => `${i.lineItem}\t${i.primaryFigure}\t${i.noteFigure}\t${i.discrepancy}\t${i.riskLevel}`)
      .join('\n');
    navigator.clipboard.writeText(header + rows);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="part-2-inconsistencies" className="bg-white border-2 border-[#141414] shadow-dense mb-6 overflow-hidden">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between p-4 bg-[#F9F9F7] border-b border-[#141414] gap-3">
        <div>
          <h2 className="text-[11px] font-serif italic uppercase text-[#141414]/70 mb-0.5 tracking-wider">
            Mathematical Casting & Cross-Check • Part 2
          </h2>
          <h3 className="text-base sm:text-lg font-bold uppercase tracking-tight text-[#141414]">
            Part 2: Cross-Referencing & Numerical Inconsistency Findings
          </h3>
          <p className="text-[10px] font-mono text-[#141414]/70 mt-0.5 uppercase">
            PRIMARY VS NOTE RECONCILIATION // BALANCE SHEET, P&L, CASH FLOW DISCREPANCY AUDIT
          </p>
        </div>

        {/* Copy Action */}
        <button
          id="copy-part-2-btn"
          onClick={handleCopyTable}
          className="self-start md:self-center inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-mono font-bold uppercase bg-white hover:bg-neutral-100 text-[#141414] border border-[#141414] transition"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-700" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'COPIED' : 'COPY TABLE'}</span>
        </button>
      </div>

      {/* Filter and Search */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 bg-[#E4E3E0] border-b border-[#141414]">
        {/* Risk Level Filter Buttons */}
        <div className="flex flex-wrap gap-1 w-full sm:w-auto">
          <button
            id="filter-all-risks"
            onClick={() => setRiskFilter('ALL')}
            className={`px-2.5 py-1 text-[10px] font-mono font-bold uppercase transition border border-[#141414] ${
              riskFilter === 'ALL'
                ? 'bg-[#141414] text-white'
                : 'bg-white text-[#141414] hover:bg-neutral-100'
            }`}
          >
            ALL ({counts.total})
          </button>
          <button
            id="filter-high-risks"
            onClick={() => setRiskFilter('high')}
            className={`px-2.5 py-1 text-[10px] font-mono font-bold uppercase transition border border-[#141414] ${
              riskFilter === 'high'
                ? 'bg-red-600 text-white'
                : 'bg-red-100 text-red-700 hover:bg-red-200'
            }`}
          >
            HIGH RISK ({counts.high})
          </button>
          <button
            id="filter-med-risks"
            onClick={() => setRiskFilter('medium')}
            className={`px-2.5 py-1 text-[10px] font-mono font-bold uppercase transition border border-[#141414] ${
              riskFilter === 'medium'
                ? 'bg-orange-500 text-white'
                : 'bg-orange-100 text-orange-800 hover:bg-orange-200'
            }`}
          >
            MED RISK ({counts.med})
          </button>
          <button
            id="filter-low-risks"
            onClick={() => setRiskFilter('low')}
            className={`px-2.5 py-1 text-[10px] font-mono font-bold uppercase transition border border-[#141414] ${
              riskFilter === 'low'
                ? 'bg-[#141414] text-white'
                : 'bg-white text-[#141414] hover:bg-neutral-100'
            }`}
          >
            LOW RISK ({counts.low})
          </button>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#141414]/60" />
          <input
            id="search-inconsistencies-input"
            type="text"
            placeholder="SEARCH LINE ITEM / NOTE..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-2.5 py-1 text-[11px] font-mono uppercase bg-white border border-[#141414] text-[#141414] focus:outline-none focus:ring-1 focus:ring-[#141414]"
          />
        </div>
      </div>

      {/* Structured Inconsistencies Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-[#141414]/20 text-left">
          <thead className="bg-[#141414] text-white text-[10px] uppercase font-bold tracking-widest font-mono">
            <tr>
              <th scope="col" className="py-2.5 px-4 w-52">
                Line Item
              </th>
              <th scope="col" className="py-2.5 px-4 w-40">
                Primary Stmt Figure
              </th>
              <th scope="col" className="py-2.5 px-4 w-44">
                Corresponding Note Figure
              </th>
              <th scope="col" className="py-2.5 px-4">
                Discrepancy / Observation
              </th>
              <th scope="col" className="py-2.5 px-4 w-28 text-center">
                Risk Level
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-[#141414]/10 text-[11px] text-[#141414]">
            {filteredItems.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-6 text-center text-[#141414]/60 font-mono">
                  {inconsistencies.length === 0 ? (
                    <div className="flex flex-col items-center justify-center text-green-700 py-3">
                      <CheckCircle2 className="w-6 h-6 text-green-700 mb-1" />
                      <span className="font-bold text-xs uppercase">CLEAN INTERNAL RECONCILIATION</span>
                      <span className="text-[10px] text-[#141414]/70 mt-0.5 font-mono">
                        ZERO ARITHMETIC OR CROSS-REFERENCING VARIANCES DETECTED BETWEEN PRIMARY STATEMENTS AND NOTES.
                      </span>
                    </div>
                  ) : (
                    'NO NUMERICAL INCONSISTENCIES FOUND MATCHING FILTER CRITERIA.'
                  )}
                </td>
              </tr>
            ) : (
              filteredItems.map((item, idx) => {
                const isHigh = item.riskLevel.toLowerCase() === 'high';
                return (
                  <tr
                    key={idx}
                    className={`hover:bg-[#F5F5F5] transition ${
                      isHigh ? 'bg-red-50/40' : ''
                    }`}
                  >
                    {/* Line Item */}
                    <td className="py-2.5 px-4 font-bold text-[#141414] align-top">
                      <div>{item.lineItem}</div>
                      {item.noteRef && (
                        <div className="text-[10px] font-mono uppercase text-[#141414]/70 mt-0.5">
                          REF: {item.noteRef}
                        </div>
                      )}
                    </td>

                    {/* Primary Statement Figure */}
                    <td className="py-2.5 px-4 font-mono font-bold text-[#141414] align-top">
                      {item.primaryFigure}
                    </td>

                    {/* Note Figure */}
                    <td className="py-2.5 px-4 font-mono font-bold text-[#141414] align-top">
                      {item.noteFigure}
                    </td>

                    {/* Discrepancy / Observation */}
                    <td className="py-2.5 px-4 align-top leading-snug text-[#141414]">
                      <div className="font-serif italic text-[#141414]">{item.discrepancy}</div>
                      {onOpenReconciler && (
                        <button
                          onClick={() => onOpenReconciler(item)}
                          className="mt-1 text-[10px] font-mono font-bold uppercase text-[#141414] hover:underline flex items-center gap-1 bg-[#D1D0CC]/60 px-1.5 py-0.5 border border-[#141414]/30"
                        >
                          <Calculator className="w-3 h-3" />
                          Reconcile Sub-schedules
                        </button>
                      )}
                    </td>

                    {/* Risk Level */}
                    <td className="py-2.5 px-4 align-top text-center">
                      {getRiskBadge(item.riskLevel)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};

