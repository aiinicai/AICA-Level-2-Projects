import React, { useState, useMemo } from 'react';
import {
  X,
  TrendingUp,
  ArrowDownRight,
  ArrowUpRight,
  Calendar,
  AlertCircle,
  Printer,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { AppRow, NormalizedAlert } from '../types';
import { inr, inrS, longD, normAll, stateOf } from '../utils/calculations';
import { triggerPrint } from '../utils/exportImport';

interface Props {
  isOpen: boolean;
  rows: AppRow[];
  onClose: () => void;
  onEditItem?: (row: AppRow) => void;
}

interface MonthBucket {
  yearMonth: string; // YYYY-MM
  label: string; // Month Year, e.g. "Nov 2026"
  outflow: number;
  inflow: number;
  net: number;
  outflowItems: NormalizedAlert[];
  inflowItems: NormalizedAlert[];
}

export const CashFlowForecastModal: React.FC<Props> = ({
  isOpen,
  rows,
  onClose,
  onEditItem,
}) => {
  const [forecastMonths, setForecastMonths] = useState<number>(6); // 6 or 12 months
  const [expandedMonth, setExpandedMonth] = useState<string | null>(null);

  const buckets = useMemo(() => {
    const allAlerts = rows.flatMap(normAll);
    const result: MonthBucket[] = [];
    const today = new Date();

    for (let i = 0; i < forecastMonths; i++) {
      const d = new Date(today.getFullYear(), today.getMonth() + i, 1);
      const ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      const monthLabel = d.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });

      // Find dues falling in this month
      const monthDues = allAlerts.filter((a) => {
        if (a.paid || a.amount <= 0) return false;
        if (!a.due || !a.due.startsWith(ym)) return false;
        return a.vk === 'due';
      });

      // Find inflows (maturities / coupons) falling in this month
      const monthInflows = allAlerts.filter((a) => {
        if (a.amount <= 0) return false;
        if (!a.due || !a.due.startsWith(ym)) return false;
        return a.vk === 'mat';
      });

      const outflow = monthDues.reduce((s, a) => s + (a.amount || 0), 0);
      const inflow = monthInflows.reduce((s, a) => s + (a.amount || 0), 0);
      const net = inflow - outflow;

      result.push({
        yearMonth: ym,
        label: monthLabel,
        outflow,
        inflow,
        net,
        outflowItems: monthDues,
        inflowItems: monthInflows,
      });
    }

    return result;
  }, [rows, forecastMonths]);

  const totalForecastOutflow = useMemo(
    () => buckets.reduce((s, b) => s + b.outflow, 0),
    [buckets]
  );
  const totalForecastInflow = useMemo(
    () => buckets.reduce((s, b) => s + b.inflow, 0),
    [buckets]
  );
  const netForecastTotal = totalForecastInflow - totalForecastOutflow;

  const maxOutflow = Math.max(...buckets.map((b) => b.outflow), 1);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-3 sm:p-4 overflow-y-auto"
    >
      <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl max-w-3xl w-full p-5 sm:p-6 shadow-2xl relative text-[#0F1B2D] dark:text-[#E8EDF5] max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#DCE2EA] dark:border-[#25324A] flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold flex-shrink-0">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-lg leading-tight">
                Cash Flow & Liquidity Forecast
              </h3>
              <p className="text-xs text-[#6F7E92] dark:text-[#8594AA]">
                Upcoming payment outflows vs investment maturity inflows
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={triggerPrint}
              className="p-2 rounded-lg border border-[#DCE2EA] dark:border-[#25324A] hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-medium flex items-center gap-1.5 transition no-print"
              title="Print Forecast"
            >
              <Printer className="w-4 h-4 text-slate-600 dark:text-slate-400" />
              <span className="hidden sm:inline">Print</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Forecast Period Toggle & Summary */}
        <div className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#DCE2EA] dark:border-[#25324A] flex-shrink-0">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-[#6F7E92] dark:text-[#8594AA] font-medium">Period:</span>
            <button
              onClick={() => setForecastMonths(6)}
              className={`px-3 py-1 rounded-lg font-semibold transition ${
                forecastMonths === 6
                  ? 'bg-[#0E7C86] text-white shadow-xs'
                  : 'bg-slate-100 dark:bg-slate-800 text-[#46566C] dark:text-[#A9B6C9]'
              }`}
            >
              Next 6 Months
            </button>
            <button
              onClick={() => setForecastMonths(12)}
              className={`px-3 py-1 rounded-lg font-semibold transition ${
                forecastMonths === 12
                  ? 'bg-[#0E7C86] text-white shadow-xs'
                  : 'bg-slate-100 dark:bg-slate-800 text-[#46566C] dark:text-[#A9B6C9]'
              }`}
            >
              Next 12 Months
            </button>
          </div>

          {/* Quick Aggregate Totals */}
          <div className="flex items-center gap-4 text-xs font-medium">
            <div>
              <span className="text-[#6F7E92] dark:text-[#8594AA] mr-1">Outflows:</span>
              <strong className="text-rose-600 dark:text-rose-400">
                {inrS(totalForecastOutflow)}
              </strong>
            </div>
            <div>
              <span className="text-[#6F7E92] dark:text-[#8594AA] mr-1">Inflows:</span>
              <strong className="text-emerald-600 dark:text-emerald-400">
                +{inrS(totalForecastInflow)}
              </strong>
            </div>
            <div>
              <span className="text-[#6F7E92] dark:text-[#8594AA] mr-1">Net:</span>
              <strong
                className={
                  netForecastTotal >= 0
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-amber-600 dark:text-amber-400'
                }
              >
                {netForecastTotal >= 0 ? '+' : ''}
                {inrS(netForecastTotal)}
              </strong>
            </div>
          </div>
        </div>

        {/* Month by month timeline breakdown */}
        <div className="overflow-y-auto flex-1 py-4 space-y-3 pr-1">
          {buckets.map((b) => {
            const isExpanded = expandedMonth === b.yearMonth;
            const hasItems = b.outflowItems.length > 0 || b.inflowItems.length > 0;

            return (
              <div
                key={b.yearMonth}
                className="bg-[#EEF1F5]/60 dark:bg-[#0B1220]/70 border border-[#DCE2EA] dark:border-[#25324A] rounded-xl overflow-hidden transition"
              >
                {/* Month Bar Row */}
                <div
                  onClick={() => hasItems && setExpandedMonth(isExpanded ? null : b.yearMonth)}
                  className={`p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                    hasItems ? 'cursor-pointer hover:bg-slate-100/70 dark:hover:bg-slate-800/50' : 'opacity-70'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-[140px]">
                    <div className="w-8 h-8 rounded-lg bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] flex items-center justify-center font-bold text-xs text-[#0B3B66] dark:text-[#5B9BE0]">
                      <Calendar className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="font-bold text-sm text-[#0F1B2D] dark:text-[#E8EDF5]">
                        {b.label}
                      </h4>
                      <p className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                        {b.outflowItems.length} dues · {b.inflowItems.length} maturities
                      </p>
                    </div>
                  </div>

                  {/* Relative bar visualization */}
                  <div className="flex-1 max-w-xs hidden md:block">
                    <div className="h-2 w-full bg-[#E7ECF2] dark:bg-[#1E2A40] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-rose-500 rounded-full transition-all"
                        style={{ width: `${Math.max(2, (b.outflow / maxOutflow) * 100)}%` }}
                      />
                    </div>
                  </div>

                  {/* Numbers */}
                  <div className="flex items-center justify-between sm:justify-end gap-5 text-xs font-medium">
                    <div className="text-right">
                      <div className="text-[10px] uppercase text-[#6F7E92] dark:text-[#8594AA]">
                        Outflow
                      </div>
                      <div className="font-bold text-rose-600 dark:text-rose-400">
                        {b.outflow > 0 ? `-${inr(b.outflow)}` : '₹0'}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-[10px] uppercase text-[#6F7E92] dark:text-[#8594AA]">
                        Inflow
                      </div>
                      <div className="font-bold text-emerald-600 dark:text-emerald-400">
                        {b.inflow > 0 ? `+${inr(b.inflow)}` : '₹0'}
                      </div>
                    </div>

                    <div className="text-right min-w-[70px]">
                      <div className="text-[10px] uppercase text-[#6F7E92] dark:text-[#8594AA]">
                        Net Balance
                      </div>
                      <div
                        className={`font-bold ${
                          b.net >= 0
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-rose-600 dark:text-rose-400'
                        }`}
                      >
                        {b.net >= 0 ? '+' : ''}
                        {inr(b.net)}
                      </div>
                    </div>

                    {hasItems && (
                      <div className="text-gray-400 pl-1">
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Drilldown items if expanded */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-1 border-t border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] divide-y divide-[#DCE2EA] dark:divide-[#25324A] text-xs">
                    {/* Outflows section */}
                    {b.outflowItems.length > 0 && (
                      <div className="py-2.5">
                        <div className="text-[11px] font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 mb-2 flex items-center gap-1">
                          <ArrowDownRight className="w-3.5 h-3.5" />
                          <span>Bills & Payment Dues</span>
                        </div>
                        <div className="space-y-1.5">
                          {b.outflowItems.map((item) => (
                            <div
                              key={item.row.id + item.due}
                              className="flex items-center justify-between py-1 text-xs"
                            >
                              <div className="flex items-center gap-2 truncate pr-2">
                                <span className="font-medium text-[#0F1B2D] dark:text-[#E8EDF5] truncate">
                                  {item.name}
                                </span>
                                {item.who && (
                                  <span className="text-[10px] px-1.5 py-0.2 bg-slate-100 dark:bg-slate-800 rounded-full text-slate-600 dark:text-slate-300">
                                    {item.who}
                                  </span>
                                )}
                                <span className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                                  Due: {longD(item.due)}
                                </span>
                              </div>
                              <span className="font-semibold text-rose-600 dark:text-rose-400 whitespace-nowrap">
                                -{inr(item.amount)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Inflows section */}
                    {b.inflowItems.length > 0 && (
                      <div className="py-2.5">
                        <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-2 flex items-center gap-1">
                          <ArrowUpRight className="w-3.5 h-3.5" />
                          <span>Investments Maturing</span>
                        </div>
                        <div className="space-y-1.5">
                          {b.inflowItems.map((item) => (
                            <div
                              key={item.row.id + item.due}
                              className="flex items-center justify-between py-1 text-xs"
                            >
                              <div className="flex items-center gap-2 truncate pr-2">
                                <span className="font-medium text-[#0F1B2D] dark:text-[#E8EDF5] truncate">
                                  {item.name}
                                </span>
                                {item.who && (
                                  <span className="text-[10px] px-1.5 py-0.2 bg-slate-100 dark:bg-slate-800 rounded-full text-slate-600 dark:text-slate-300">
                                    {item.who}
                                  </span>
                                )}
                                <span className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                                  Maturity: {longD(item.due)}
                                </span>
                              </div>
                              <span className="font-semibold text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                                +{inr(item.amount)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-[#DCE2EA] dark:border-[#25324A] flex items-center justify-between flex-shrink-0 text-xs">
          <span className="text-[#6F7E92] dark:text-[#8594AA]">
            Tip: Keep a buffer in your savings account during high outflow months.
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#0B3B66] dark:bg-[#5B9BE0] text-white dark:text-[#08121F] hover:brightness-110 transition"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
