import React, { useState } from 'react';
import {
  PortfolioSummary,
  ChartDataPoint,
  HoldingValuation,
  Purchase,
} from '../../types';
import { formatINR, formatGrams, formatPercent } from '../../utils/formatters';
import { PortfolioChart } from './PortfolioChart';
import {
  TrendingUp,
  TrendingDown,
  Coins,
  ShieldAlert,
  Info,
  Calendar,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  PlusCircle,
  FolderOpen,
} from 'lucide-react';

interface DashboardScreenProps {
  summary: PortfolioSummary;
  lotValuations: HoldingValuation[];
  allPurchases?: Purchase[];
  chartData: ChartDataPoint[];
  selectedDate: string;
  onSelectDate: (date: string) => void;
  onOpenAddModal: () => void;
  onLoadDemoData: () => void;
}

type MetalFilter = 'ALL' | 'GOLD' | 'SILVER';

export const DashboardScreen: React.FC<DashboardScreenProps> = ({
  summary,
  lotValuations,
  allPurchases = [],
  chartData,
  selectedDate,
  onSelectDate,
  onOpenAddModal,
  onLoadDemoData,
}) => {
  const [filter, setFilter] = useState<MetalFilter>('ALL');

  const activeHoldingsInLedger = allPurchases.filter((p) => !p.deleted);
  const totalLedgerCount = activeHoldingsInLedger.length;
  const valuedCount = summary.totalHoldingsCount;
  const isGain = summary.gainLossAmount >= 0;

  // Find latest purchase date if any
  const latestPurchaseDate = activeHoldingsInLedger.reduce(
    (max, p) => (p.purchaseDate > max ? p.purchaseDate : max),
    ''
  );
  const hasFuturePurchases =
    latestPurchaseDate && latestPurchaseDate > selectedDate;

  // Stale/carried-forward check
  const carriedLots = lotValuations.filter(
    (l) => l.hasRate && l.isCarriedForward
  );
  const unvaluedLots = lotValuations.filter((l) => !l.hasRate);

  // Active view values based on filter
  const activeInvested =
    filter === 'ALL'
      ? summary.investedAmount
      : filter === 'GOLD'
      ? summary.gold.investedAmount
      : summary.silver.investedAmount;

  const activeReference =
    filter === 'ALL'
      ? summary.referenceValue
      : filter === 'GOLD'
      ? summary.gold.referenceValue
      : summary.silver.referenceValue;

  const activeResale =
    filter === 'ALL'
      ? summary.resaleValue
      : filter === 'GOLD'
      ? summary.gold.resaleValue
      : summary.silver.resaleValue;

  const activeGainLoss =
    filter === 'ALL'
      ? summary.gainLossAmount
      : filter === 'GOLD'
      ? summary.gold.gainLossAmount
      : summary.silver.gainLossAmount;

  const activeGainLossPct =
    filter === 'ALL'
      ? summary.gainLossPct
      : filter === 'GOLD'
      ? summary.gold.gainLossPct
      : summary.silver.gainLossPct;

  const activeXirr =
    filter === 'ALL'
      ? summary.annualizedXirr
      : filter === 'GOLD'
      ? summary.gold.annualizedXirr
      : summary.silver.annualizedXirr;

  const activeXirrStatus =
    filter === 'ALL'
      ? summary.xirrStatus
      : filter === 'GOLD'
      ? summary.gold.xirrStatus
      : summary.silver.xirrStatus;

  return (
    <div className="space-y-6">
      {/* 1. Empty State Banner (Only when ledger is truly empty) */}
      {totalLedgerCount === 0 && (
        <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-5 text-amber-900 shadow-2xs">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold flex items-center gap-2">
                <Coins className="w-5 h-5 text-[#B88B2A]" />
                Your Bullion Ledger is Ready
              </h2>
              <p className="text-xs text-amber-800 mt-1 max-w-2xl">
                Start tracking physical gold and silver across Vedhani, Coins, and Bars. You
                can record an invoice manually, upload an Excel/CSV spreadsheet, or test the
                system instantly with a curated demo portfolio.
              </p>
            </div>
            <div className="flex items-center gap-2.5 shrink-0">
              <button
                type="button"
                onClick={onLoadDemoData}
                className="px-3.5 py-2 text-xs font-semibold bg-white hover:bg-amber-100 text-stone-800 border border-stone-300 rounded-lg shadow-2xs transition-colors flex items-center gap-1.5"
              >
                <FolderOpen className="w-4 h-4 text-[#B88B2A]" />
                <span>Load Demo Portfolio</span>
              </button>
              <button
                type="button"
                onClick={onOpenAddModal}
                className="px-3.5 py-2 text-xs font-semibold bg-[#B88B2A] hover:bg-[#8E6B1D] text-white rounded-lg shadow-2xs transition-colors flex items-center gap-1.5"
              >
                <PlusCircle className="w-4 h-4" />
                <span>Add First Purchase</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. Future Purchases Notice (When ledger has purchases, but valuation date is set before them) */}
      {totalLedgerCount > 0 && valuedCount === 0 && (
        <div className="bg-[#FBF6E9] border-2 border-[#D4AF37] rounded-xl p-4 text-[#8E6B1D] shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <h3 className="text-xs font-bold text-stone-900 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-[#B88B2A]" />
              <span>{totalLedgerCount} Purchase(s) Recorded in Ledger</span>
            </h3>
            <p className="text-xs text-stone-600">
              Your purchases are safely saved, but their purchase dates are newer than the selected valuation date (<span className="font-semibold text-stone-800">{selectedDate}</span>).
            </p>
          </div>
          <button
            type="button"
            onClick={() => onSelectDate(latestPurchaseDate || selectedDate)}
            className="px-4 py-2 bg-[#B88B2A] hover:bg-[#8E6B1D] text-white text-xs font-semibold rounded-lg shadow-xs transition-colors shrink-0 flex items-center gap-1.5"
          >
            <span>Valuate as of {latestPurchaseDate}</span>
          </button>
        </div>
      )}

      {/* 3. Partial Historical Snapshot Notice (When some holdings are newer than valuation date) */}
      {totalLedgerCount > valuedCount && valuedCount > 0 && (
        <div className="bg-stone-50 border border-stone-200 rounded-lg p-3 text-xs text-stone-700 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-[#B88B2A] shrink-0" />
            <span>
              Historical Snapshot: Showing <strong>{valuedCount}</strong> of <strong>{totalLedgerCount}</strong> holdings as of {selectedDate}. ({totalLedgerCount - valuedCount} purchase(s) made after this date are omitted from this snapshot).
            </span>
          </div>
          <button
            type="button"
            onClick={() => onSelectDate(latestPurchaseDate || selectedDate)}
            className="text-[11px] font-bold text-[#B88B2A] hover:underline shrink-0"
          >
            View All ({totalLedgerCount}) as of {latestPurchaseDate} →
          </button>
        </div>
      )}

      {/* Carried Forward / Gap Information Notice */}
      {(carriedLots.length > 0 || unvaluedLots.length > 0) && (
        <div className="bg-stone-50 border border-stone-200 rounded-lg p-3 text-xs text-stone-700 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-[#B88B2A] shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold text-stone-900">
              Valuation Rate Information as of {selectedDate}:
            </span>
            {carriedLots.length > 0 && (
              <p className="text-stone-600">
                {carriedLots.length} lot(s) use market closing rates carried forward from preceding
                trading sessions (e.g. weekends or exchange holidays).
              </p>
            )}
            {unvaluedLots.length > 0 && (
              <p className="text-amber-800 font-medium">
                {unvaluedLots.length} lot(s) could not be valued because no publication exists on or
                before {selectedDate}.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Filter Selector & Summary Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-stone-900 tracking-tight">Portfolio Summary</h2>
          <p className="text-xs text-stone-500">
            Valuation evaluated on {selectedDate} • {summary.totalHoldingsCount} active holdings
          </p>
        </div>

        {/* Metal view filter tabs */}
        <div className="flex items-center bg-stone-100 p-1 rounded-lg border border-stone-200">
          <button
            type="button"
            onClick={() => setFilter('ALL')}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
              filter === 'ALL'
                ? 'bg-white text-stone-900 font-bold shadow-2xs'
                : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            All Metals
          </button>
          <button
            type="button"
            onClick={() => setFilter('GOLD')}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
              filter === 'GOLD'
                ? 'bg-[#FBF6E9] text-[#B88B2A] font-bold shadow-2xs'
                : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            Gold Only
          </button>
          <button
            type="button"
            onClick={() => setFilter('SILVER')}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
              filter === 'SILVER'
                ? 'bg-slate-100 text-slate-800 font-bold shadow-2xs'
                : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            Silver Only
          </button>
        </div>
      </div>

      {/* 5 Primary Valuation KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        {/* Card 1: Invested Amount */}
        <div className="bg-white rounded-xl p-4 border border-[#E7E2DA] shadow-xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-stone-500 block">
            Invested Amount
          </span>
          <div className="text-xl font-bold text-stone-900 mt-1">
            {formatINR(activeInvested)}
          </div>
          <span className="text-[11px] text-stone-500 mt-1 block">
            Includes taxes & charges
          </span>
        </div>

        {/* Card 2: Reference Metal Value */}
        <div className="bg-white rounded-xl p-4 border border-[#E7E2DA] shadow-xs">
          <span className="text-[11px] font-bold uppercase tracking-wider text-stone-500 block">
            Reference Metal Value
          </span>
          <div className="text-xl font-bold text-stone-800 mt-1">
            {formatINR(activeReference)}
          </div>
          <span className="text-[11px] text-stone-500 mt-1 block">
            At 100% benchmark rate
          </span>
        </div>

        {/* Card 3: Estimated Resale Value */}
        <div className="bg-[#FAF7F2] rounded-xl p-4 border border-[#D4AF37]/40 shadow-xs relative overflow-hidden">
          <div className="absolute top-0 right-0 w-16 h-16 bg-[#B88B2A]/5 rounded-bl-full pointer-events-none" />
          <span className="text-[11px] font-bold uppercase tracking-wider text-[#B88B2A] block">
            Estimated Resale Value
          </span>
          <div className="text-xl font-bold text-stone-900 mt-1">
            {formatINR(activeResale)}
          </div>
          <span className="text-[11px] text-stone-500 mt-1 block">
            After default 3% markdown
          </span>
        </div>

        {/* Card 4: Unrealized Gain/Loss */}
        <div
          className={`rounded-xl p-4 border shadow-xs ${
            activeGainLoss >= 0
              ? 'bg-emerald-50/50 border-emerald-200'
              : 'bg-rose-50/50 border-rose-200'
          }`}
        >
          <div className="flex items-center justify-between">
            <span
              className={`text-[11px] font-bold uppercase tracking-wider ${
                activeGainLoss >= 0 ? 'text-emerald-800' : 'text-rose-800'
              }`}
            >
              {activeGainLoss >= 0 ? 'Unrealized Gain' : 'Unrealized Loss'}
            </span>
            {activeGainLoss >= 0 ? (
              <ArrowUpRight className="w-4 h-4 text-emerald-600" />
            ) : (
              <ArrowDownRight className="w-4 h-4 text-rose-600" />
            )}
          </div>
          <div
            className={`text-xl font-bold mt-1 ${
              activeGainLoss >= 0 ? 'text-emerald-700' : 'text-rose-700'
            }`}
          >
            {activeGainLoss >= 0 ? '+' : ''}
            {formatINR(activeGainLoss)}
          </div>
          <span
            className={`text-[11px] font-semibold mt-1 block ${
              activeGainLoss >= 0 ? 'text-emerald-600' : 'text-rose-600'
            }`}
          >
            {activeGainLoss >= 0 ? '+' : ''}
            {formatPercent(activeGainLossPct)} on cost
          </span>
        </div>

        {/* Card 5: Annualized XIRR */}
        <div className="bg-white rounded-xl p-4 border border-[#E7E2DA] shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-stone-500">
              Portfolio XIRR
            </span>
            <span className="text-[10px] text-stone-400 font-mono">Actual/365</span>
          </div>
          <div className="text-xl font-bold text-stone-900 mt-1">
            {activeXirr !== null ? (
              <span className={activeXirr >= 0 ? 'text-emerald-700' : 'text-rose-700'}>
                {formatPercent(activeXirr)}
              </span>
            ) : (
              <span className="text-stone-400 text-sm font-normal">N/A</span>
            )}
          </div>
          <span
            className="text-[10px] text-stone-500 mt-1 block truncate"
            title={activeXirrStatus}
          >
            {activeXirr !== null ? 'Annualized return p.a.' : activeXirrStatus}
          </span>
        </div>
      </div>

      {/* Gold & Silver Detailed Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Gold Summary Card */}
        <div className="bg-white rounded-xl p-4 border border-[#E7E2DA] shadow-xs hover:border-[#D4AF37]/50 transition-colors">
          <div className="flex items-center justify-between pb-3 border-b border-stone-100">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-md bg-[#FBF6E9] border border-[#D4AF37]/40 flex items-center justify-center text-[#B88B2A]">
                <Coins className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-stone-900">Physical Gold</h3>
                <span className="text-[11px] text-stone-500">
                  {summary.gold.holdingsCount} lot(s) held
                </span>
              </div>
            </div>
            <div className="text-right">
              <span className="text-xs font-bold text-stone-900">
                {formatGrams(summary.gold.totalGrams)}
              </span>
              <span className="text-[10px] text-stone-500 block">Total physical weight</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 py-3 text-xs border-b border-stone-100">
            <div>
              <span className="text-[10px] text-stone-500 block">Invested Cost</span>
              <span className="font-semibold text-stone-800">
                {formatINR(summary.gold.investedAmount)}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-stone-500 block">Est. Resale (3%)</span>
              <span className="font-semibold text-[#B88B2A]">
                {formatINR(summary.gold.resaleValue)}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-stone-500 block">Gold XIRR</span>
              <span
                className={`font-semibold ${
                  summary.gold.annualizedXirr !== null && summary.gold.annualizedXirr >= 0
                    ? 'text-emerald-700'
                    : 'text-stone-700'
                }`}
              >
                {summary.gold.annualizedXirr !== null
                  ? formatPercent(summary.gold.annualizedXirr)
                  : 'N/A'}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2.5 text-xs">
            <span className="text-stone-500">Unrealized Net Return:</span>
            <span
              className={`font-bold flex items-center gap-1 ${
                summary.gold.gainLossAmount >= 0 ? 'text-emerald-700' : 'text-rose-700'
              }`}
            >
              {summary.gold.gainLossAmount >= 0 ? '+' : ''}
              {formatINR(summary.gold.gainLossAmount)} (
              {summary.gold.gainLossAmount >= 0 ? '+' : ''}
              {formatPercent(summary.gold.gainLossPct)})
            </span>
          </div>
        </div>

        {/* Silver Summary Card */}
        <div className="bg-white rounded-xl p-4 border border-[#E7E2DA] shadow-xs hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between pb-3 border-b border-stone-100">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-md bg-slate-100 border border-slate-300 flex items-center justify-center text-slate-700">
                <Coins className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-stone-900">Physical Silver</h3>
                <span className="text-[11px] text-stone-500">
                  {summary.silver.holdingsCount} lot(s) held
                </span>
              </div>
            </div>
            <div className="text-right">
              <span className="text-xs font-bold text-stone-900">
                {formatGrams(summary.silver.totalGrams)}
              </span>
              <span className="text-[10px] text-stone-500 block">Total physical weight</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 py-3 text-xs border-b border-stone-100">
            <div>
              <span className="text-[10px] text-stone-500 block">Invested Cost</span>
              <span className="font-semibold text-stone-800">
                {formatINR(summary.silver.investedAmount)}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-stone-500 block">Est. Resale (3%)</span>
              <span className="font-semibold text-slate-800">
                {formatINR(summary.silver.resaleValue)}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-stone-500 block">Silver XIRR</span>
              <span
                className={`font-semibold ${
                  summary.silver.annualizedXirr !== null && summary.silver.annualizedXirr >= 0
                    ? 'text-emerald-700'
                    : 'text-stone-700'
                }`}
              >
                {summary.silver.annualizedXirr !== null
                  ? formatPercent(summary.silver.annualizedXirr)
                  : 'N/A'}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2.5 text-xs">
            <span className="text-stone-500">Unrealized Net Return:</span>
            <span
              className={`font-bold flex items-center gap-1 ${
                summary.silver.gainLossAmount >= 0 ? 'text-emerald-700' : 'text-rose-700'
              }`}
            >
              {summary.silver.gainLossAmount >= 0 ? '+' : ''}
              {formatINR(summary.silver.gainLossAmount)} (
              {summary.silver.gainLossAmount >= 0 ? '+' : ''}
              {formatPercent(summary.silver.gainLossPct)})
            </span>
          </div>
        </div>
      </div>

      {/* Portfolio Growth Chart */}
      <PortfolioChart data={chartData} selectedDate={selectedDate} />
    </div>
  );
};
