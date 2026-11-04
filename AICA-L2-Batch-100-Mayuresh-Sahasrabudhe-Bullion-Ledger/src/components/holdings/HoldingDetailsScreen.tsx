import React, { useState, useMemo } from 'react';
import { HoldingValuation, MetalType, BullionForm } from '../../types';
import {
  formatINR,
  formatGrams,
  formatPercent,
  formatDisplayDate,
} from '../../utils/formatters';
import {
  Search,
  ChevronDown,
  ChevronRight,
  Info,
  Calendar,
  Percent,
  TrendingUp,
  TrendingDown,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

interface HoldingDetailsScreenProps {
  lotValuations: HoldingValuation[];
  selectedDate: string;
}

export const HoldingDetailsScreen: React.FC<HoldingDetailsScreenProps> = ({
  lotValuations,
  selectedDate,
}) => {
  const [search, setSearch] = useState('');
  const [metalFilter, setMetalFilter] = useState<'ALL' | MetalType>('ALL');
  const [formFilter, setFormFilter] = useState<'ALL' | BullionForm>('ALL');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  const filteredLots = useMemo(() => {
    return lotValuations.filter((l) => {
      const p = l.holding;
      if (metalFilter !== 'ALL' && p.metal !== metalFilter) return false;
      if (formFilter !== 'ALL' && p.form !== formFilter) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        const matchSeller = p.seller.toLowerCase().includes(q);
        const matchInvoice = p.invoiceNumber.toLowerCase().includes(q);
        const matchId = p.id.toLowerCase().includes(q);
        if (!matchSeller && !matchInvoice && !matchId) return false;
      }
      return true;
    });
  }, [lotValuations, metalFilter, formFilter, search]);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-stone-900 tracking-tight flex items-center gap-2">
            <span>Holding Details & Lot Returns</span>
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-stone-100 text-stone-600 border border-stone-200">
              {lotValuations.length} active lots
            </span>
          </h2>
          <p className="text-xs text-stone-500">
            Granular valuation, purity adjustments, holding periods, and lot-level XIRR as of{' '}
            <span className="font-semibold text-stone-700">{formatDisplayDate(selectedDate)}</span>
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 flex-wrap w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 text-stone-400 absolute left-2.5 top-2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter by Jeweller or Invoice #..."
              className="w-full pl-8 pr-2.5 py-1 text-xs border border-stone-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#B88B2A] bg-white"
            />
          </div>

          <select
            value={metalFilter}
            onChange={(e) => setMetalFilter(e.target.value as any)}
            className="text-xs px-2.5 py-1 border border-stone-200 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-[#B88B2A]"
          >
            <option value="ALL">All Metals</option>
            <option value="GOLD">Gold</option>
            <option value="SILVER">Silver</option>
          </select>

          <select
            value={formFilter}
            onChange={(e) => setFormFilter(e.target.value as any)}
            className="text-xs px-2.5 py-1 border border-stone-200 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-[#B88B2A]"
          >
            <option value="ALL">All Forms</option>
            <option value="VEDHANI">Vedhani</option>
            <option value="COIN">Coin</option>
            <option value="BAR">Bar</option>
          </select>
        </div>
      </div>

      {/* Lot list table for desktop */}
      <div className="hidden md:block bg-white rounded-xl border border-[#E7E2DA] shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-[#FAF7F2] text-stone-700 border-b border-[#E7E2DA] font-semibold">
              <tr>
                <th className="py-2.5 px-3 w-8"></th>
                <th className="py-2.5 px-3">Holding ID</th>
                <th className="py-2.5 px-3">Jeweller / Invoice</th>
                <th className="py-2.5 px-3">Metal / Form</th>
                <th className="py-2.5 px-3 text-right">Weight (g)</th>
                <th className="py-2.5 px-3 text-right">Invested Cost</th>
                <th className="py-2.5 px-3 text-right">Ref Rate (₹/g)</th>
                <th className="py-2.5 px-3 text-right">Est. Resale</th>
                <th className="py-2.5 px-3 text-right">Net Return</th>
                <th className="py-2.5 px-3 text-right">Days</th>
                <th className="py-2.5 px-3 text-right">Lot XIRR</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {filteredLots.length === 0 ? (
                <tr>
                  <td colSpan={11} className="py-8 text-center text-stone-400">
                    No active holdings found on or before {selectedDate}.
                  </td>
                </tr>
              ) : (
                filteredLots.map((l) => {
                  const p = l.holding;
                  const isExpanded = expandedId === p.id;
                  const isGain = l.gainLossAmount >= 0;

                  return (
                    <React.Fragment key={p.id}>
                      <tr
                        onClick={() => toggleExpand(p.id)}
                        className={`cursor-pointer transition-colors ${
                          isExpanded ? 'bg-[#FAF7F2]' : 'hover:bg-stone-50/70'
                        }`}
                      >
                        <td className="py-2.5 px-3 text-stone-400">
                          {isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5" />
                          )}
                        </td>
                        <td className="py-2.5 px-3 font-mono font-medium text-stone-800">
                          {p.id}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="font-semibold text-stone-900 block">{p.seller}</span>
                          <span className="text-[10px] text-stone-500 font-mono">
                            Inv #{p.invoiceNumber} • {formatDisplayDate(p.purchaseDate)}
                          </span>
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`inline-flex items-center gap-1 font-semibold text-[11px] px-1.5 py-0.5 rounded ${
                              p.metal === 'GOLD'
                                ? 'bg-[#FBF6E9] text-[#B88B2A]'
                                : 'bg-slate-100 text-slate-700'
                            }`}
                          >
                            {p.metal} {p.purity} • {p.form}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-medium text-stone-800">
                          {formatGrams(p.weightGrams)}
                        </td>
                        <td className="py-2.5 px-3 text-right text-stone-700 font-medium">
                          {formatINR(p.investedAmount)}
                        </td>
                        <td className="py-2.5 px-3 text-right text-stone-700 font-mono">
                          {l.hasRate ? `₹${l.ratePerGram.toFixed(2)}` : 'N/A'}
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-stone-900">
                          {l.hasRate ? formatINR(l.estimatedResaleValue) : 'N/A'}
                        </td>
                        <td className="py-2.5 px-3 text-right whitespace-nowrap">
                          {l.hasRate ? (
                            <span
                              className={`font-semibold ${
                                isGain ? 'text-emerald-700' : 'text-rose-700'
                              }`}
                            >
                              {isGain ? '+' : ''}
                              {formatINR(l.gainLossAmount)} (
                              {isGain ? '+' : ''}
                              {formatPercent(l.gainLossPct)})
                            </span>
                          ) : (
                            <span className="text-stone-400">N/A</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right text-stone-600 font-mono">
                          {l.holdingDays}d
                        </td>
                        <td className="py-2.5 px-3 text-right whitespace-nowrap">
                          {l.annualizedXirr !== null ? (
                            <span
                              className={`font-bold font-mono ${
                                l.annualizedXirr >= 0 ? 'text-emerald-700' : 'text-rose-700'
                              }`}
                            >
                              {formatPercent(l.annualizedXirr)}
                            </span>
                          ) : (
                            <span
                              className="text-stone-400 text-[10px]"
                              title={l.xirrStatus}
                            >
                              N/A
                            </span>
                          )}
                        </td>
                      </tr>

                      {/* Expandable Mathematical Breakdown Row */}
                      {isExpanded && (
                        <tr className="bg-[#FAF7F2] border-b border-stone-200">
                          <td colSpan={11} className="p-4">
                            <div className="bg-white rounded-lg p-4 border border-[#E7E2DA] space-y-3">
                              <div className="flex items-center justify-between pb-2 border-b border-stone-100">
                                <span className="text-xs font-bold text-stone-900 flex items-center gap-1.5">
                                  <Info className="w-3.5 h-3.5 text-[#B88B2A]" />
                                  Audit & Mathematical Breakdown for {p.id}
                                </span>
                                <span className="text-[10px] text-stone-500 font-mono">
                                  Evaluated on {selectedDate}
                                </span>
                              </div>

                              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                                {/* Section 1: Cost Basis */}
                                <div className="space-y-1.5 bg-stone-50/60 p-3 rounded-lg border border-stone-200">
                                  <span className="text-[11px] font-bold text-stone-800 uppercase tracking-wider block">
                                    1. Acquisition Cost
                                  </span>
                                  <div className="space-y-1 text-stone-600 text-[11px]">
                                    <div className="flex justify-between">
                                      <span>Bullion Metal Value:</span>
                                      <span className="font-mono">{formatINR(p.bullionValue)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>Taxes Paid (GST/TCS):</span>
                                      <span className="font-mono">{formatINR(p.taxesPaid)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>Other Charges:</span>
                                      <span className="font-mono">{formatINR(p.otherCharges)}</span>
                                    </div>
                                    <div className="flex justify-between font-bold text-stone-900 pt-1 border-t border-stone-200">
                                      <span>Total Invested Cost:</span>
                                      <span className="font-mono">{formatINR(p.investedAmount)}</span>
                                    </div>
                                  </div>
                                </div>

                                {/* Section 2: Valuation & Benchmark Rate */}
                                <div className="space-y-1.5 bg-stone-50/60 p-3 rounded-lg border border-stone-200">
                                  <span className="text-[11px] font-bold text-stone-800 uppercase tracking-wider block">
                                    2. Applicable Benchmark
                                  </span>
                                  <div className="space-y-1 text-stone-600 text-[11px]">
                                    <div className="flex justify-between">
                                      <span>Benchmark Source:</span>
                                      <span className="font-medium text-stone-900">
                                        {l.rateSourceLabel}
                                      </span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>Actual Quote Date:</span>
                                      <span className="font-mono">{l.actualRateDate || 'N/A'}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>Purity Adjustment Ratio:</span>
                                      <span className="font-mono">
                                        {l.isPurityAdjusted
                                          ? `${p.purity} / ${l.referenceFineness} = ${(
                                              l.purityAdjustmentRatio
                                            ).toFixed(4)}`
                                          : 'Direct (1.0000)'}
                                      </span>
                                    </div>
                                    <div className="flex justify-between font-bold text-stone-900 pt-1 border-t border-stone-200">
                                      <span>Adjusted Rate / Gram:</span>
                                      <span className="font-mono">
                                        ₹{l.ratePerGram.toFixed(2)}/g
                                      </span>
                                    </div>
                                  </div>
                                </div>

                                {/* Section 3: Resale & XIRR */}
                                <div className="space-y-1.5 bg-[#FAF7F2] p-3 rounded-lg border border-[#D4AF37]/40">
                                  <span className="text-[11px] font-bold text-[#B88B2A] uppercase tracking-wider block">
                                    3. Resale & Annualized XIRR
                                  </span>
                                  <div className="space-y-1 text-stone-600 text-[11px]">
                                    <div className="flex justify-between">
                                      <span>100% Reference Value:</span>
                                      <span className="font-mono">{formatINR(l.referenceMetalValue)}</span>
                                    </div>
                                    <div className="flex justify-between text-amber-800">
                                      <span>Resale Markdown ({l.markdownPct}%):</span>
                                      <span className="font-mono">
                                        - {formatINR(l.referenceMetalValue * (l.markdownPct / 100))}
                                      </span>
                                    </div>
                                    <div className="flex justify-between font-bold text-stone-900 pt-1 border-t border-stone-200">
                                      <span>Estimated Resale Value:</span>
                                      <span className="font-mono">
                                        {formatINR(l.estimatedResaleValue)}
                                      </span>
                                    </div>
                                    <div className="flex justify-between font-bold pt-1 border-t border-stone-200">
                                      <span>Holding Days & Lot XIRR:</span>
                                      <span className="font-mono text-[#B88B2A]">
                                        {l.holdingDays} days •{' '}
                                        {l.annualizedXirr !== null
                                          ? formatPercent(l.annualizedXirr)
                                          : 'N/A'}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              </div>

                              <div className="text-[10px] text-stone-500 font-mono bg-stone-50 p-2 rounded">
                                Formula: Single Lot XIRR = (Resale Value / Invested Cost)^(365 /
                                Holding Days) - 1 = ({l.estimatedResaleValue.toFixed(2)} /{' '}
                                {p.investedAmount.toFixed(2)})^(365 / {l.holdingDays}) - 1 ={' '}
                                {l.annualizedXirr !== null ? formatPercent(l.annualizedXirr) : 'N/A'}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile Card List with Expandable Audits (No horizontal scroll at 360px) */}
      <div className="md:hidden space-y-3">
        {filteredLots.length === 0 ? (
          <div className="bg-white p-6 rounded-xl border border-stone-200 text-center text-stone-400 text-xs">
            No holdings match your search.
          </div>
        ) : (
          filteredLots.map((l) => {
            const p = l.holding;
            const isExpanded = expandedId === p.id;
            const isGain = l.gainLossAmount >= 0;

            return (
              <div
                key={p.id}
                className="bg-white rounded-xl p-3.5 border border-[#E7E2DA] shadow-xs space-y-2.5"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-mono text-stone-400 block">{p.id}</span>
                    <span className="font-bold text-xs text-stone-900">{p.seller}</span>
                    <span className="text-[10px] text-stone-500">
                      Inv #{p.invoiceNumber} • {formatDisplayDate(p.purchaseDate)}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                      p.metal === 'GOLD'
                        ? 'bg-[#FBF6E9] text-[#B88B2A]'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {p.metal} {p.purity} • {p.form}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs py-2 border-y border-stone-100">
                  <div>
                    <span className="text-[10px] text-stone-500 block">Weight:</span>
                    <span className="font-semibold text-stone-800">
                      {formatGrams(p.weightGrams)}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-stone-500 block">Invested Cost:</span>
                    <span className="font-medium text-stone-800">
                      {formatINR(p.investedAmount)}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-stone-500 block">Est. Resale (3%):</span>
                    <span className="font-semibold text-[#B88B2A]">
                      {l.hasRate ? formatINR(l.estimatedResaleValue) : 'N/A'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-stone-500 block">Lot XIRR:</span>
                    <span
                      className={`font-bold ${
                        l.annualizedXirr !== null && l.annualizedXirr >= 0
                          ? 'text-emerald-700'
                          : 'text-stone-700'
                      }`}
                    >
                      {l.annualizedXirr !== null ? formatPercent(l.annualizedXirr) : 'N/A'}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => toggleExpand(p.id)}
                  className="w-full text-center text-[11px] text-[#B88B2A] font-semibold pt-1 flex items-center justify-center gap-1"
                >
                  <span>{isExpanded ? 'Hide Calculation Audit' : 'View Calculation Audit'}</span>
                  {isExpanded ? (
                    <ChevronDown className="w-3 h-3" />
                  ) : (
                    <ChevronRight className="w-3 h-3" />
                  )}
                </button>

                {isExpanded && (
                  <div className="bg-[#FAF7F2] p-3 rounded-lg border border-[#E7E2DA] space-y-2 text-xs mt-2">
                    <span className="font-bold text-stone-900 block text-[11px]">
                      Arithmetic Breakdown:
                    </span>
                    <div className="space-y-1 text-[10px] text-stone-600">
                      <div className="flex justify-between">
                        <span>Rate Source:</span>
                        <span className="font-medium text-stone-800">{l.rateSourceLabel}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Actual Date:</span>
                        <span>{l.actualRateDate}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Ref Rate:</span>
                        <span>₹{l.ratePerGram.toFixed(2)}/g</span>
                      </div>
                      <div className="flex justify-between">
                        <span>100% Value:</span>
                        <span>{formatINR(l.referenceMetalValue)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Markdown (3%):</span>
                        <span>- {formatINR(l.referenceMetalValue * (l.markdownPct / 100))}</span>
                      </div>
                      <div className="flex justify-between font-bold text-stone-900 pt-1 border-t border-stone-200">
                        <span>Net Gain/Loss:</span>
                        <span className={isGain ? 'text-emerald-700' : 'text-rose-700'}>
                          {isGain ? '+' : ''}
                          {formatINR(l.gainLossAmount)} ({formatPercent(l.gainLossPct)})
                        </span>
                      </div>
                      <div className="flex justify-between font-bold text-[#B88B2A] pt-0.5">
                        <span>Holding Period:</span>
                        <span>{l.holdingDays} days</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
