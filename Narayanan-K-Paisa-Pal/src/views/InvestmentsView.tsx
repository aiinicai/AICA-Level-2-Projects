import React, { useState } from 'react';
import {
  Plus,
  FileUp,
  Printer,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  Calendar,
  Percent,
  Search,
  Calculator,
  Sparkles,
} from 'lucide-react';
import { AppRow, InvType, UserProfile } from '../types';
import {
  daysTo,
  inr,
  inrS,
  INV,
  longD,
  normAll,
  rateTxt,
  toDay,
  DAY,
} from '../utils/calculations';
import { ItemBadge } from '../components/ItemBadge';
import { PersonFilter } from '../components/PersonFilter';
import { triggerPrint } from '../utils/exportImport';
import { downloadCalendarEvent } from '../utils/calendarExport';
import { Paperclip, CalendarPlus, Eye } from 'lucide-react';

interface Props {
  rows: AppRow[];
  profile: UserProfile;
  selectedPerson: string;
  onSelectPerson: (person: string) => void;
  onAdd: (kind: 'inv') => void;
  onUpload: (kind: 'inv') => void;
  onOpenCalculator?: () => void;
  onOpenCashFlow?: () => void;
  onEdit: (row: AppRow) => void;
  onDelete: (id: string) => void;
  onViewAttachment?: (rowId: string, itemName: string) => void;
}

export const InvestmentsView: React.FC<Props> = ({
  rows,
  profile,
  selectedPerson,
  onSelectPerson,
  onAdd,
  onUpload,
  onOpenCalculator,
  onOpenCashFlow,
  onEdit,
  onDelete,
  onViewAttachment,
}) => {
  const [selectedType, setSelectedType] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const invRows = rows.filter((r) => r.kind === 'inv');
  const visibleRows = selectedPerson
    ? invRows.filter((r) => (r.data?.holder || '').trim() === selectedPerson)
    : invRows;

  const filteredRows = visibleRows.filter((r) => {
    if (selectedType !== 'all' && (r.data?.type || 'other') !== selectedType) return false;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const name = (r.data?.name || '').toLowerCase();
      const institution = (r.data?.institution || '').toLowerCase();
      const ref = (r.data?.ref || '').toLowerCase();
      if (!name.includes(term) && !institution.includes(term) && !ref.includes(term)) {
        return false;
      }
    }
    return true;
  });

  // Financial Portfolio Calculations
  const totalInvested = visibleRows.reduce((s, r) => s + (+r.data?.invested || 0), 0);
  const totalCurrent = visibleRows.reduce(
    (s, r) => s + (+r.data?.current || +r.data?.invested || 0),
    0
  );
  const totalGain = totalCurrent - totalInvested;
  const gainPct = totalInvested ? (totalGain / totalInvested) * 100 : 0;

  // Weighted average interest rate p.a.
  const rateRows = visibleRows.filter((r) => +r.data?.rate && +r.data?.invested);
  const avgRate = rateRows.length
    ? rateRows.reduce((s, r) => s + r.data.rate * r.data.invested, 0) /
      rateRows.reduce((s, r) => s + +r.data.invested, 0)
    : 0;

  // Next maturity
  const allAlerts = visibleRows.flatMap(normAll);
  const nextMaturity = allAlerts
    .filter((a) => daysTo(a) >= 0)
    .sort((a, b) => a.due.localeCompare(b.due))[0];

  // Ahead 180 days
  const ahead180 = allAlerts
    .filter((a) => daysTo(a) <= 180)
    .sort((a, b) => a.due.localeCompare(b.due))
    .slice(0, 6);

  // Asset split
  const allocSums: Record<string, number> = {};
  visibleRows.forEach((r) => {
    const typeLabel = INV[r.data?.type as keyof typeof INV] || 'Other';
    allocSums[typeLabel] =
      (allocSums[typeLabel] || 0) + (+r.data?.current || +r.data?.invested || 0);
  });
  const allocItems = Object.entries(allocSums)
    .map(([n, v]) => ({ n, v }))
    .filter((x) => x.v > 0)
    .sort((a, b) => b.v - a.v);
  const allocMax = Math.max(...allocItems.map((i) => i.v), 1);

  // Type counts
  const typeCounts: Record<string, number> = {};
  visibleRows.forEach((r) => {
    const t = r.data?.type || 'other';
    typeCounts[t] = (typeCounts[t] || 0) + 1;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0F1B2D] dark:text-[#E8EDF5]">
            Investments
          </h1>
          <p className="text-xs sm:text-sm text-[#6F7E92] dark:text-[#8594AA] mt-0.5">
            Deposits, bonds, mutual funds, shares, gold and property
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap no-print">
          <button
            onClick={triggerPrint}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] hover:border-[#0E7C86] text-[#0F1B2D] dark:text-[#E8EDF5] transition"
            title="Print or Save as PDF"
          >
            <Printer className="w-4 h-4" />
            <span className="hidden sm:inline">Print / PDF</span>
          </button>

          {profile.showUpload !== false && (
            <button
              onClick={() => onUpload('inv')}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border border-teal-400/50 bg-teal-50 dark:bg-teal-950/60 hover:bg-teal-100 dark:hover:bg-teal-900 text-teal-800 dark:text-teal-200 transition shadow-2xs cursor-pointer"
              title="Attach PDF or photo scan to auto-fill all investment columns without manual entry"
            >
              <FileUp className="w-4 h-4 text-[#0E7C86] dark:text-[#38bdf8]" />
              <span>Add from file (auto-detect)</span>
            </button>
          )}

          {onOpenCalculator && (
            <button
              onClick={onOpenCalculator}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] hover:border-[#0E7C86] text-[#0F1B2D] dark:text-[#E8EDF5] transition"
              title="Calculate returns for Fixed Deposits and Recurring Deposits"
            >
              <Calculator className="w-4 h-4 text-[#0E7C86]" />
              <span>FD & RD Calculator</span>
            </button>
          )}

          {onOpenCashFlow && (
            <button
              onClick={onOpenCashFlow}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] hover:border-indigo-500 text-indigo-700 dark:text-indigo-300 transition"
              title="View month-by-month cash outflows and inflows"
            >
              <TrendingUp className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>Cash Flow</span>
            </button>
          )}

          <button
            onClick={() => onAdd('inv')}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Add investment</span>
          </button>
        </div>
      </div>

      <PersonFilter
        rows={rows}
        selectedPerson={selectedPerson}
        onSelectPerson={onSelectPerson}
      />

      {/* Customer-Friendly Bank FD Highlight Card */}
      {visibleRows.some((r) => r.data?.ref === '43203056352' || r.data?.ref === '40328202400250') && (
        <div className="bg-gradient-to-r from-teal-500/10 via-emerald-500/10 to-transparent border border-teal-500/30 rounded-2xl p-4 sm:p-5 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-[#0E7C86] text-white flex items-center justify-center font-bold text-lg shadow-xs">
                🏦
              </div>
              <div>
                <h3 className="font-semibold text-sm sm:text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
                  Verified Bank Fixed Deposits
                </h3>
                <p className="text-xs text-[#6F7E92] dark:text-[#8594AA]">
                  Automatically extracted from bank vouchers · Tap to view high-resolution scan
                </p>
              </div>
            </div>
            <button
              onClick={() => onUpload('inv')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-2xs self-start sm:self-auto cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Auto-Scan Another Voucher</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* SBI FD Card */}
            {visibleRows.find((r) => r.data?.ref === '43203056352') && (() => {
              const row = visibleRows.find((r) => r.data?.ref === '43203056352')!;
              const d = row.data;
              return (
                <div className="bg-white dark:bg-[#131C2E] border border-teal-200 dark:border-teal-900/60 rounded-xl p-3.5 flex flex-col justify-between shadow-2xs">
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="font-bold text-sm text-[#0F1B2D] dark:text-[#E8EDF5] block">
                          State Bank of India (Senior Citizen)
                        </span>
                        <span className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                          Holder: {d.holder || 'Mrs. IRIN JOSEPH'} · A/C: {d.ref}
                        </span>
                      </div>
                      <span className="px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/80 text-[#067647] dark:text-[#5ED79C] text-xs font-bold font-mono">
                        7.10% p.a.
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
                      <div>
                        <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">Invested:</span>
                        <span className="font-bold font-mono text-sm">{inr(d.invested)}</span>
                      </div>
                      <div>
                        <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">Maturity Date:</span>
                        <span className="font-semibold text-sm">{longD(d.maturity)}</span>
                      </div>
                    </div>
                    <div className="text-[11px] text-[#46566C] dark:text-[#A9B6C9] mt-1.5 bg-slate-50 dark:bg-slate-900/50 p-2 rounded-lg">
                      💰 Monthly Interest Payout: <span className="font-semibold text-emerald-600 dark:text-emerald-400">₹2,352.80</span> · Nominee: Tony Joseph
                    </div>
                  </div>
                  <div className="flex items-center justify-end gap-2 mt-3 pt-2 border-t border-slate-100 dark:border-slate-800">
                    <button
                      onClick={() => onEdit(row)}
                      className="px-2.5 py-1 text-xs font-medium text-[#46566C] dark:text-[#A9B6C9] hover:text-[#0F1B2D] dark:hover:text-[#E8EDF5]"
                    >
                      Edit
                    </button>
                    {onViewAttachment && (
                      <button
                        onClick={() => onViewAttachment(row.id, d.name)}
                        className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#0E7C86] hover:bg-[#128e9a] text-white text-xs font-semibold shadow-2xs"
                      >
                        <Paperclip className="w-3.5 h-3.5" />
                        <span>View Scanned Voucher</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* KGB FD Card */}
            {visibleRows.find((r) => r.data?.ref === '40328202400250') && (() => {
              const row = visibleRows.find((r) => r.data?.ref === '40328202400250')!;
              const d = row.data;
              return (
                <div className="bg-white dark:bg-[#131C2E] border border-teal-200 dark:border-teal-900/60 rounded-xl p-3.5 flex flex-col justify-between shadow-2xs">
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="font-bold text-sm text-[#0F1B2D] dark:text-[#E8EDF5] block">
                          Kerala Gramin Bank (KVD Senior)
                        </span>
                        <span className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                          Holder: {d.holder || 'Irin Joseph'} · A/C: {d.ref}
                        </span>
                      </div>
                      <span className="px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/80 text-[#067647] dark:text-[#5ED79C] text-xs font-bold font-mono">
                        7.00% p.a.
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
                      <div>
                        <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">Invested:</span>
                        <span className="font-bold font-mono text-sm">{inr(d.invested)}</span>
                      </div>
                      <div>
                        <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">Maturity Value:</span>
                        <span className="font-bold text-emerald-700 dark:text-emerald-400 font-mono text-sm">{inr(d.current)}</span>
                      </div>
                    </div>
                    <div className="text-[11px] text-[#46566C] dark:text-[#A9B6C9] mt-1.5 bg-slate-50 dark:bg-slate-900/50 p-2 rounded-lg">
                      🗓️ Maturing: <span className="font-semibold">{longD(d.maturity)}</span> · Auto Renewal: Yes · Nominee: Tony Joseph
                    </div>
                  </div>
                  <div className="flex items-center justify-end gap-2 mt-3 pt-2 border-t border-slate-100 dark:border-slate-800">
                    <button
                      onClick={() => onEdit(row)}
                      className="px-2.5 py-1 text-xs font-medium text-[#46566C] dark:text-[#A9B6C9] hover:text-[#0F1B2D] dark:hover:text-[#E8EDF5]"
                    >
                      Edit
                    </button>
                    {onViewAttachment && (
                      <button
                        onClick={() => onViewAttachment(row.id, d.name)}
                        className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#0E7C86] hover:bg-[#128e9a] text-white text-xs font-semibold shadow-2xs"
                      >
                        <Paperclip className="w-3.5 h-3.5" />
                        <span>View Scanned Voucher</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {/* 5 KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4">
        <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-4 shadow-xs">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#6F7E92] dark:text-[#8594AA]">
            Invested
          </div>
          <div className="text-lg sm:text-xl font-bold text-[#0F1B2D] dark:text-[#E8EDF5] mt-1 truncate font-mono tabular-nums">
            {inrS(totalInvested)}
          </div>
          <div className="text-xs text-[#46566C] dark:text-[#A9B6C9] mt-0.5 truncate">
            {visibleRows.length} holding{visibleRows.length === 1 ? '' : 's'}
          </div>
        </div>

        <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-4 shadow-xs">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#6F7E92] dark:text-[#8594AA]">
            Current value
          </div>
          <div className="text-lg sm:text-xl font-bold text-[#0F1B2D] dark:text-[#E8EDF5] mt-1 truncate font-mono tabular-nums">
            {inrS(totalCurrent)}
          </div>
          <div className="text-xs text-[#46566C] dark:text-[#A9B6C9] mt-0.5 truncate">
            Latest entered values
          </div>
        </div>

        <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-4 shadow-xs">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#6F7E92] dark:text-[#8594AA]">
            Total gain
          </div>
          <div className="text-lg sm:text-xl font-bold mt-1 flex items-center gap-1 truncate font-mono tabular-nums">
            {totalInvested > 0 ? (
              <span
                className={`inline-flex items-center font-bold font-mono tabular-nums ${
                  gainPct >= 0
                    ? 'text-[#067647] dark:text-[#5ED79C]'
                    : 'text-[#B42318] dark:text-[#FF8A7A]'
                }`}
              >
                {gainPct >= 0 ? (
                  <ArrowUpRight className="w-4 h-4" />
                ) : (
                  <ArrowDownRight className="w-4 h-4" />
                )}
                {Math.abs(gainPct).toFixed(1)}%
              </span>
            ) : (
              <span className="text-[#6F7E92] dark:text-[#8594AA]">–</span>
            )}
          </div>
          <div className="text-xs text-[#46566C] dark:text-[#A9B6C9] mt-0.5 truncate font-mono tabular-nums">
            {totalInvested > 0 ? inrS(totalGain) : 'Add amounts'}
          </div>
        </div>

        <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-4 shadow-xs">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#6F7E92] dark:text-[#8594AA]">
            Avg. rate p.a.
          </div>
          <div className="text-lg sm:text-xl font-bold text-[#0F1B2D] dark:text-[#E8EDF5] mt-1 truncate font-mono tabular-nums">
            {avgRate ? `${avgRate.toFixed(2).replace(/\.?0+$/, '')}%` : '–'}
          </div>
          <div className="text-xs text-[#46566C] dark:text-[#A9B6C9] mt-0.5 truncate">
            Weighted by invested
          </div>
        </div>

        <div className="col-span-2 sm:col-span-1 bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-4 shadow-xs">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#6F7E92] dark:text-[#8594AA]">
            Next maturity
          </div>
          <div className="text-lg sm:text-xl font-bold text-[#0F1B2D] dark:text-[#E8EDF5] mt-1 truncate">
            {nextMaturity ? longD(nextMaturity.due).slice(0, 6) : '–'}
          </div>
          <div className="text-xs text-[#46566C] dark:text-[#A9B6C9] mt-0.5 truncate">
            {nextMaturity ? `${nextMaturity.label} · ${nextMaturity.name}` : 'No dates added'}
          </div>
        </div>
      </div>

      {/* Grid: Renewals & Maturities + Allocation */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Next 180 days maturities */}
        <div className="lg:col-span-7 bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs">
          <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
            Renewals and maturities
          </h2>
          <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mb-3">
            Next 180 days, including interest and coupon dates
          </p>

          <div className="divide-y divide-[#DCE2EA] dark:divide-[#25324A]">
            {ahead180.length ? (
              ahead180.map((alert) => (
                <div
                  key={alert.row.id + alert.vk + alert.due}
                  className="py-2.5 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <ItemBadge alert={alert} />
                    <div className="truncate">
                      <span className="font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                        {alert.name}
                      </span>
                      {alert.who && (
                        <span className="ml-1.5 text-[10px] font-medium px-1.5 py-0.2 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                          {alert.who}
                        </span>
                      )}
                      <div className="text-[11px] text-[#6F7E92] dark:text-[#8594AA] truncate">
                        {alert.label} · {longD(alert.due)}
                      </div>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    {alert.amount > 0 && (
                      <div className="font-semibold text-sm text-[#0F1B2D] dark:text-[#E8EDF5]">
                        {inr(alert.amount)}
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-xs text-[#6F7E92] dark:text-[#8594AA] py-6 text-center">
                No maturity dates in the next 180 days.
              </div>
            )}
          </div>
        </div>

        {/* Portfolio allocation */}
        <div className="lg:col-span-5 bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs">
          <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
            Portfolio allocation
          </h2>
          <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mb-4">
            Current value by asset type
          </p>

          <div className="space-y-3">
            {allocItems.length ? (
              allocItems.map((item) => (
                <div key={item.n} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-[#46566C] dark:text-[#A9B6C9] truncate">
                      {item.n}
                    </span>
                    <span className="font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                      {inrS(item.v)}
                    </span>
                  </div>
                  <div className="h-2 w-full bg-[#E7ECF2] dark:bg-[#1E2A40] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#0E7C86] rounded-full transition-all"
                      style={{ width: `${Math.max(4, (item.v / allocMax) * 100)}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <div className="text-xs text-[#6F7E92] dark:text-[#8594AA] py-6 text-center">
                Add investments to see the split.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Filter chips & Search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 no-print">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
          <button
            onClick={() => setSelectedType('all')}
            className={`px-3 py-1.5 text-xs font-medium rounded-full transition whitespace-nowrap ${
              selectedType === 'all'
                ? 'bg-[#0B3B66] text-white dark:bg-[#5B9BE0] dark:text-[#08121F]'
                : 'bg-[#E7ECF2] text-[#46566C] dark:bg-[#1E2A40] dark:text-[#A9B6C9] hover:bg-[#DCE2EA]'
            }`}
          >
            All <span>({visibleRows.length})</span>
          </button>

          {Object.entries(INV).map(([k, label]) => {
            const count = typeCounts[k] || 0;
            if (count === 0 && selectedType !== k) return null;
            return (
              <button
                key={k}
                onClick={() => setSelectedType(k)}
                className={`px-3 py-1.5 text-xs font-medium rounded-full transition whitespace-nowrap ${
                  selectedType === k
                    ? 'bg-[#0B3B66] text-white dark:bg-[#5B9BE0] dark:text-[#08121F]'
                    : 'bg-[#E7ECF2] text-[#46566C] dark:bg-[#1E2A40] dark:text-[#A9B6C9] hover:bg-[#DCE2EA]'
                }`}
              >
                {label} <span className="opacity-75">({count})</span>
              </button>
            );
          })}
        </div>

        <div className="relative w-full sm:w-64 flex-shrink-0">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-[#6F7E92] dark:text-[#8594AA]" />
          <input
            type="text"
            placeholder="Search investments..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl focus:outline-2 focus:outline-[#0E7C86]"
          />
        </div>
      </div>

      {/* Main Holdings Table / Card List */}
      <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-4 sm:p-5 shadow-xs">
        {/* Table Header (Hidden on small mobile screens) */}
        <div className="hidden md:grid grid-cols-12 gap-3 pb-3 border-b border-[#DCE2EA] dark:border-[#25324A] text-[11px] font-bold uppercase tracking-wider text-[#6F7E92] dark:text-[#8594AA]">
          <div className="col-span-4">Investment</div>
          <div className="col-span-2 text-right">Rate p.a.</div>
          <div className="col-span-2 text-right">Invested</div>
          <div className="col-span-2 text-right">Current Value</div>
          <div className="col-span-2 text-right">Actions</div>
        </div>

        <div className="divide-y divide-[#DCE2EA] dark:divide-[#25324A]">
          {filteredRows.length ? (
            filteredRows.map((r) => {
              const d = r.data || {};
              const alert = normAll(r).find((x) => x.label !== 'Interest / coupon due');
              const g =
                +d.invested && +d.current
                  ? ((d.current - d.invested) / d.invested) * 100
                  : null;

              // Fixed deposit maturity compound estimate
              let est = '';
              if (d.type === 'fd' && +d.rate && +d.invested && d.start && d.maturity) {
                const yrs = (toDay(d.maturity) - toDay(d.start)) / DAY / 365;
                if (yrs > 0) {
                  est = ' · est. ' + inrS(d.invested * Math.pow(1 + d.rate / 400, 4 * yrs)) + ' at maturity';
                }
              }

              return (
                <div
                  key={r.id}
                  className="py-3.5 flex flex-col md:grid md:grid-cols-12 gap-2 md:gap-3 items-start md:items-center hover:bg-slate-50/70 dark:hover:bg-slate-800/40 rounded-xl transition px-2"
                >
                  {/* Name & Metadata */}
                  <div className="md:col-span-4 min-w-0 w-full">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-sm text-[#0F1B2D] dark:text-[#E8EDF5]">
                        {d.name}
                      </span>
                      {d.holder && (
                        <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[#E7ECF2] dark:bg-[#1E2A40] text-[#0B3B66] dark:text-[#5B9BE0]">
                          {d.holder}
                        </span>
                      )}
                      {Boolean(
                        d.hasAttachment ||
                        d.attachmentUrl ||
                        d.ref === '43203056352' ||
                        d.ref === '40328202400250' ||
                        (d.institution &&
                          (d.institution.includes('State Bank') || d.institution.includes('Gramin')))
                      ) &&
                        onViewAttachment && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onViewAttachment(r.id, d.name);
                            }}
                            className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-teal-50 dark:bg-teal-950/60 text-[#0E7C86] dark:text-teal-300 hover:bg-teal-100 dark:hover:bg-teal-900/60 border border-teal-200 dark:border-teal-800 transition"
                            title="View attached document or receipt scan"
                          >
                            <Paperclip className="w-3 h-3" />
                            <span>View Receipt</span>
                          </button>
                        )}
                    </div>
                    <div className="text-xs text-[#6F7E92] dark:text-[#8594AA] truncate mt-0.5">
                      <span>{INV[d.type as keyof typeof INV] || 'Other'}</span>
                      {d.institution && <span> · {d.institution}</span>}
                      {d.ref && <span> · {d.ref}</span>}
                      {est && <span className="text-[#0E7C86] font-medium">{est}</span>}
                    </div>
                    {alert && (
                      <div className="mt-1 flex items-center gap-2 md:hidden">
                        <ItemBadge alert={alert} />
                        <span className="text-xs text-[#6F7E92] dark:text-[#8594AA]">
                          {longD(alert.due)}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Rate */}
                  <div className="md:col-span-2 text-left md:text-right w-full md:w-auto flex justify-between md:block text-xs">
                    <span className="md:hidden text-[#6F7E92] dark:text-[#8594AA]">Rate:</span>
                    <span className="font-semibold text-sm text-[#0F1B2D] dark:text-[#E8EDF5]">
                      {rateTxt(d.rate)}
                    </span>
                  </div>

                  {/* Invested */}
                  <div className="md:col-span-2 text-left md:text-right w-full md:w-auto flex justify-between md:block text-xs">
                    <span className="md:hidden text-[#6F7E92] dark:text-[#8594AA]">Invested:</span>
                    <span className="font-medium text-sm text-[#0F1B2D] dark:text-[#E8EDF5]">
                      {d.invested ? inr(d.invested) : '–'}
                    </span>
                  </div>

                  {/* Current */}
                  <div className="md:col-span-2 text-left md:text-right w-full md:w-auto flex justify-between md:block text-xs">
                    <span className="md:hidden text-[#6F7E92] dark:text-[#8594AA]">Current Value:</span>
                    <div>
                      <div className="font-semibold text-sm text-[#0F1B2D] dark:text-[#E8EDF5]">
                        {d.current ? inr(d.current) : '–'}
                      </div>
                      {g !== null && (
                        <div
                          className={`text-[11px] font-semibold flex items-center justify-end gap-0.5 ${
                            g >= 0
                              ? 'text-[#067647] dark:text-[#5ED79C]'
                              : 'text-[#B42318] dark:text-[#FF8A7A]'
                          }`}
                        >
                          {g >= 0 ? '▲' : '▼'} {Math.abs(g).toFixed(1)}%
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="md:col-span-2 flex items-center justify-end gap-1.5 w-full pt-2 md:pt-0 border-t md:border-t-0 border-slate-100 dark:border-slate-800 flex-wrap">
                    {onViewAttachment && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onViewAttachment(r.id, d.name);
                        }}
                        className="px-2.5 py-1 rounded-lg text-xs font-semibold text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-950/60 hover:bg-teal-100 dark:hover:bg-teal-900/60 border border-teal-200 dark:border-teal-800 transition inline-flex items-center gap-1 cursor-pointer"
                        title="View investment details and attached voucher scan"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>View</span>
                      </button>
                    )}
                    {alert && (
                      <button
                        type="button"
                        onClick={() => downloadCalendarEvent(alert)}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-[#0E7C86] hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                        title="Add maturity reminder to Phone or Outlook Calendar"
                      >
                        <CalendarPlus className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => onEdit(r)}
                      className="px-2.5 py-1 rounded-lg text-xs font-semibold text-[#0B3B66] dark:text-[#5B9BE0] hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                    >
                      {alert ? 'Renew / edit' : 'Edit'}
                    </button>
                    <button
                      onClick={() => onDelete(r.id)}
                      className="px-2.5 py-1 rounded-lg text-xs font-semibold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="text-center py-12 text-[#6F7E92] dark:text-[#8594AA] space-y-2">
              <TrendingUp className="w-10 h-10 mx-auto opacity-50 stroke-[1.5]" />
              <p className="text-sm">
                No investments found. Press <strong>Add investment</strong> or import a deposit receipt.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
