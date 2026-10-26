import React from 'react';
import {
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  Calendar,
  Plus,
  FileUp,
  Share2,
  Sparkles,
  ExternalLink,
  Download,
  FolderArchive,
  Zap,
  HeartPulse,
  UserCheck,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';
import {
  downloadMasterTrialExcel,
  downloadMasterTrialXlsx,
  downloadAllTrialAssetsZip,
} from '../data/dummyDocuments';
import { AppRow, Kind, UserProfile } from '../types';
import {
  daysTo,
  inr,
  inrS,
  INV,
  longD,
  normAll,
  stateOf,
  todayIST,
  toDay,
} from '../utils/calculations';
import { ItemRow } from '../components/ItemRow';
import { PersonFilter } from '../components/PersonFilter';
import { PWAInstallButton } from '../components/PWAInstallButton';
import { usePWAInstall } from '../hooks/usePWAInstall';

interface Props {
  rows: AppRow[];
  profile: UserProfile;
  selectedPerson: string;
  onSelectPerson: (person: string) => void;
  onAdd: (kind: 'due') => void;
  onUpload: (kind: Kind | 'auto') => void;
  onOpenWhatsApp: () => void;
  onOpenCashFlow?: () => void;
  onOpenShareTrial?: () => void;
  onLoadSample: () => void;
  onMarkPaid: (id: string) => void;
  onEdit: (row: AppRow) => void;
  onDelete: (id: string) => void;
  onViewAttachment?: (rowId: string, itemName: string) => void;
  onOpenTrialDocuments?: () => void;
  onNavigate?: (tab: 'home' | 'util' | 'due' | 'inv' | 'rec' | 'set') => void;
}

export const DashboardView: React.FC<Props> = ({
  rows,
  profile,
  selectedPerson,
  onSelectPerson,
  onAdd,
  onUpload,
  onOpenWhatsApp,
  onOpenCashFlow,
  onOpenShareTrial,
  onLoadSample,
  onMarkPaid,
  onEdit,
  onDelete,
  onViewAttachment,
  onNavigate,
}) => {
  const { isInstalled, isInIframe, openInNewTab } = usePWAInstall();

  const visibleRows = selectedPerson
    ? rows.filter((r) => (r.data?.holder || r.data?.policyholder || '').trim() === selectedPerson)
    : rows;

  const today = todayIST();
  const todayMs = toDay(today);

  // 1. Investments (Strictly excludes utility bills, insurance premiums, and sums insured)
  const invRows = visibleRows.filter((r) => r.kind === 'inv');
  const totalInvested = invRows.reduce((s, r) => s + (+r.data?.invested || 0), 0);
  const totalCurrent = invRows.reduce((s, r) => s + (+r.data?.current || +r.data?.invested || 0), 0);
  const gainPct = totalInvested ? ((totalCurrent - totalInvested) / totalInvested) * 100 : 0;

  // 2. Records (Identity Documents + Insurance Policies)
  const allRecRows = visibleRows.filter((r) => r.kind === 'rec');
  const identityRows = allRecRows.filter(
    (r) =>
      !(
        r.data?.category === 'insurance' ||
        r.data?.type === 'policy' ||
        r.data?.type === 'insurance' ||
        r.data?.policyNumber ||
        r.data?.insurer
      )
  );
  const insuranceRows = allRecRows.filter(
    (r) =>
      r.data?.category === 'insurance' ||
      r.data?.type === 'policy' ||
      r.data?.type === 'insurance' ||
      r.data?.policyNumber ||
      r.data?.insurer
  );

  // 3. Utilities (Electricity, Water, Gas, Broadband, etc.)
  const utilRows = visibleRows.filter(
    (r) =>
      r.kind === 'util' ||
      (r.kind === 'due' && (r.data?.category === 'utility' || r.data?.category === 'lpg'))
  );
  const unpaidUtilities = utilRows.filter((r) => r.data?.status !== 'paid');
  const totalUnpaidUtilities = unpaidUtilities.reduce((s, r) => {
    const d = r.data || {};
    const amt =
      d.balanceOutstanding != null && d.balanceOutstanding !== ''
        ? +d.balanceOutstanding
        : +d.billAmount || +d.amount || 0;
    return s + amt;
  }, 0);
  const overdueUtilities = unpaidUtilities.filter((r) => {
    const d = r.data?.dueDate || r.data?.due;
    return d && toDay(d) < todayMs;
  });

  // 4. Alerts & Actionable Timeline (IST)
  const allAlerts = visibleRows.flatMap(normAll);
  const pendingDues = allAlerts.filter((a) => !a.paid && a.row.kind === 'due');

  const sum = (list: typeof allAlerts) => list.reduce((s, a) => s + (a.amount || 0), 0);
  const overdueList = allAlerts.filter((a) => stateOf(a) === 'overdue');
  const todayList = allAlerts.filter((a) => stateOf(a) === 'today');
  const soonList = allAlerts.filter((a) => stateOf(a) === 'soon');

  const withinDays = (lo: number, hi: number) =>
    pendingDues.filter((a) => {
      const d = daysTo(a);
      return d >= lo && d <= hi;
    });

  const due7 = withinDays(0, 7);
  const due30 = withinDays(0, 30);
  const due90 = withinDays(0, 90);

  const attentionList = allAlerts
    .filter((a) => ['overdue', 'today', 'soon'].includes(stateOf(a)))
    .sort((a, b) => a.due.localeCompare(b.due));

  // Categories distribution for next 90 days
  const catSums: Record<string, number> = {};
  due90.forEach((a) => {
    catSums[a.label] = (catSums[a.label] || 0) + a.amount;
  });
  const catItems = Object.entries(catSums)
    .map(([n, v]) => ({ n, v }))
    .filter((x) => x.v > 0)
    .sort((a, b) => b.v - a.v)
    .slice(0, 6);
  const catMax = Math.max(...catItems.map((i) => i.v), 1);

  // Asset Allocation
  const allocSums: Record<string, number> = {};
  invRows.forEach((r) => {
    const typeLabel = INV[r.data?.type as keyof typeof INV] || 'Other';
    allocSums[typeLabel] =
      (allocSums[typeLabel] || 0) + (+r.data?.current || +r.data?.invested || 0);
  });
  const allocItems = Object.entries(allocSums)
    .map(([n, v]) => ({ n, v }))
    .filter((x) => x.v > 0)
    .sort((a, b) => b.v - a.v)
    .slice(0, 6);
  const allocMax = Math.max(...allocItems.map((i) => i.v), 1);

  // Bar chart buckets
  const buckets = [
    { label: 'Overdue', value: sum(overdueList), bad: true },
    { label: '0-7 days', value: sum(withinDays(0, 7)), bad: false },
    { label: '8-14 days', value: sum(withinDays(8, 14)), bad: false },
    { label: '15-21 days', value: sum(withinDays(15, 21)), bad: false },
    { label: '22-30 days', value: sum(withinDays(22, 30)), bad: false },
  ];
  const maxBucket = Math.max(...buckets.map((b) => b.value), 1);

  // Renewals and expiries ahead in next 90 days
  const ahead = allAlerts
    .filter((a) => a.vk !== 'due' && daysTo(a) <= 90)
    .sort((a, b) => a.due.localeCompare(b.due))
    .slice(0, 6);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#0F1B2D] dark:text-[#E8EDF5]">
            Dashboard
          </h1>
          <p className="text-xs sm:text-sm text-[#6F7E92] dark:text-[#8594AA] mt-0.5">
            {longD(todayIST())} ·{' '}
            {attentionList.length
              ? `${attentionList.length} item${attentionList.length === 1 ? '' : 's'} need attention`
              : 'Nothing needs attention today. All clear!'}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={onOpenWhatsApp}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] hover:border-emerald-600 text-emerald-700 dark:text-emerald-300 transition"
          >
            <Share2 className="w-4 h-4 text-emerald-600" />
            <span>Send alerts on WhatsApp</span>
          </button>

          {onOpenCashFlow && (
            <button
              onClick={onOpenCashFlow}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] hover:border-indigo-500 text-indigo-700 dark:text-indigo-300 transition"
              title="View month-by-month cash outflows and inflows"
            >
              <TrendingUp className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>Cash Flow Forecast</span>
            </button>
          )}

          {isInIframe && (
            <button
              onClick={openInNewTab}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] hover:bg-slate-50 dark:hover:bg-slate-800 text-[#0F1B2D] dark:text-[#E8EDF5] transition shadow-xs"
              title="Open Paisa Pal in a standalone desktop browser tab"
            >
              <ExternalLink className="w-3.5 h-3.5 text-[#0E7C86] dark:text-[#3CB7C2]" />
              <span>Open in New Tab</span>
            </button>
          )}

          {onOpenShareTrial && (
            <button
              onClick={onOpenShareTrial}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border border-[#0E7C86]/30 bg-[#0E7C86]/10 hover:bg-[#0E7C86]/20 text-[#0E7C86] dark:text-[#3CB7C2] transition"
              title="Send Paisa Pal direct link for trial to phone or desktop"
            >
              <Share2 className="w-4 h-4 text-[#0E7C86] dark:text-[#3CB7C2]" />
              <span>Send for Trial</span>
            </button>
          )}

          {profile.showUpload !== false && (
            <button
              onClick={() => onUpload('auto')}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold border border-teal-400/50 bg-teal-50 dark:bg-teal-950/60 hover:bg-teal-100 dark:hover:bg-teal-900 text-teal-800 dark:text-teal-200 transition shadow-2xs cursor-pointer"
              title="Upload document, photo or spreadsheet to auto-detect and populate columns"
            >
              <FileUp className="w-4 h-4 text-[#0E7C86] dark:text-[#38bdf8]" />
              <span>⚡ Upload Document / Scan Receipt</span>
            </button>
          )}

          <button
            onClick={() => onAdd('due')}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Add due date</span>
          </button>
        </div>
      </div>

      <PersonFilter
        rows={rows}
        selectedPerson={selectedPerson}
        onSelectPerson={onSelectPerson}
      />

      {/* Install Helper Banner */}
      {!isInstalled && (
        <div className="no-print bg-gradient-to-r from-[#0E7C86]/10 via-[#0B3B66]/10 to-transparent border border-[#0E7C86]/30 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#0E7C86] text-white flex items-center justify-center text-lg font-bold flex-shrink-0">
              📲
            </div>
            <div>
              <div className="text-xs sm:text-sm font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                Install Paisa Pal on Desktop or Mobile
              </div>
              <div className="text-[11px] sm:text-xs text-[#6F7E92] dark:text-[#8594AA]">
                {isInIframe
                  ? 'To install on your phone or PC, open the app directly in a full browser tab.'
                  : 'Fast, secure, offline-ready application on your home screen or desktop taskbar.'}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto flex-shrink-0">
            <PWAInstallButton variant="full" />
          </div>
        </div>
      )}

      {/* Empty State Welcome */}
      {rows.length === 0 && (
        <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5] flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-500" />
              <span>Welcome to Paisa Pal! Start with your own entries</span>
            </h2>
            <p className="text-xs sm:text-sm text-[#6F7E92] dark:text-[#8594AA] mt-1 max-w-xl">
              Add your bills, fixed deposits, insurance policies and document expiries. Or load sample data to explore how the dashboard organizes your finances. Everything stays securely on this device.
            </p>
          </div>
          <button
            onClick={onLoadSample}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#0B3B66] dark:bg-[#5B9BE0] text-white dark:text-[#08121F] hover:brightness-110 transition whitespace-nowrap"
          >
            Load sample data
          </button>
        </div>
      )}

      {/* 4 Clickable Dashboard Summaries (Exact Count Parity With Underlying Sections) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-4">
        {/* 1. Investment Assets Summary */}
        <div
          onClick={() => onNavigate?.('inv')}
          className="bg-white dark:bg-[#131C2E] border border-gray-200 dark:border-gray-800 hover:border-emerald-500/50 dark:hover:border-emerald-500/50 rounded-2xl p-4 sm:p-5 shadow-xs transition cursor-pointer group"
          title="Click to view Investments list"
        >
          <div className="flex items-center justify-between">
            <div className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Investment Assets</span>
            </div>
            <ChevronRight className="w-3.5 h-3.5 text-gray-400 group-hover:text-emerald-600 group-hover:translate-x-0.5 transition" />
          </div>

          <div className="text-xl sm:text-2xl font-black text-gray-900 dark:text-white mt-1.5 truncate font-mono">
            {invRows.length ? inrS(totalCurrent) : '₹0'}
          </div>

          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 flex items-center justify-between gap-1">
            <span className="truncate">
              {invRows.length} active asset{invRows.length === 1 ? '' : 's'}
            </span>
            {invRows.length > 0 && totalInvested > 0 && (
              <span
                className={`font-bold text-[11px] px-1.5 py-0.2 rounded ${
                  gainPct >= 0
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300'
                    : 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300'
                }`}
              >
                {gainPct >= 0 ? '+' : ''}{gainPct.toFixed(1)}%
              </span>
            )}
          </div>
          <div className="text-[10px] text-gray-400 mt-0.5">
            Strictly excludes bills &amp; insurance
          </div>
        </div>

        {/* 2. Official Records & Insurance Summary */}
        <div
          onClick={() => onNavigate?.('rec')}
          className="bg-white dark:bg-[#131C2E] border border-gray-200 dark:border-gray-800 hover:border-purple-500/50 dark:hover:border-purple-500/50 rounded-2xl p-4 sm:p-5 shadow-xs transition cursor-pointer group"
          title="Click to view Records & Insurance"
        >
          <div className="flex items-center justify-between">
            <div className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
              <FolderArchive className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
              <span>Official Records</span>
            </div>
            <ChevronRight className="w-3.5 h-3.5 text-gray-400 group-hover:text-purple-600 group-hover:translate-x-0.5 transition" />
          </div>

          <div className="text-xl sm:text-2xl font-black text-gray-900 dark:text-white mt-1.5 truncate">
            {allRecRows.length} Saved
          </div>

          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-1.5 truncate">
            <UserCheck className="w-3.5 h-3.5 text-amber-500" />
            <span>{identityRows.length} IDs</span>
            <span>·</span>
            <HeartPulse className="w-3.5 h-3.5 text-rose-500" />
            <span>{insuranceRows.length} Insurance</span>
          </div>
          <div className="text-[10px] text-gray-400 mt-0.5">
            Privacy masked with reveal toggle
          </div>
        </div>

        {/* 3. Household Utilities Summary */}
        <div
          onClick={() => onNavigate?.('util')}
          className={`bg-white dark:bg-[#131C2E] border rounded-2xl p-4 sm:p-5 shadow-xs transition cursor-pointer group ${
            overdueUtilities.length > 0
              ? 'border-rose-300 dark:border-rose-900 bg-rose-50/15 hover:border-rose-500'
              : 'border-gray-200 dark:border-gray-800 hover:border-cyan-500/50'
          }`}
          title="Click to view Utilities & Household bills"
        >
          <div className="flex items-center justify-between">
            <div className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
              <span>Utilities &amp; Bills</span>
            </div>
            <ChevronRight className="w-3.5 h-3.5 text-gray-400 group-hover:text-cyan-600 group-hover:translate-x-0.5 transition" />
          </div>

          <div className="text-xl sm:text-2xl font-black text-gray-900 dark:text-white mt-1.5 truncate font-mono">
            {inrS(totalUnpaidUtilities)}
          </div>

          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-1 truncate">
            {overdueUtilities.length > 0 ? (
              <span className="text-rose-600 dark:text-rose-400 font-bold flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                {overdueUtilities.length} Overdue ⚠
              </span>
            ) : (
              <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                All bills on schedule
              </span>
            )}
            <span>· {unpaidUtilities.length} Unpaid</span>
          </div>
          <div className="text-[10px] text-gray-400 mt-0.5">
            Electricity, water, gas &amp; broadband
          </div>
        </div>

        {/* 4. Actionable Alerts & Due Dates Summary (IST) */}
        <div
          onClick={() => onNavigate?.('due')}
          className={`bg-white dark:bg-[#131C2E] border rounded-2xl p-4 sm:p-5 shadow-xs transition cursor-pointer group ${
            overdueList.length > 0
              ? 'border-rose-300 dark:border-rose-900 bg-rose-50/15 hover:border-rose-500'
              : 'border-gray-200 dark:border-gray-800 hover:border-amber-500/50'
          }`}
          title="Click to view Actionable Timeline & Due Dates"
        >
          <div className="flex items-center justify-between">
            <div className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
              <span>Upcoming &amp; Renewals</span>
            </div>
            <ChevronRight className="w-3.5 h-3.5 text-gray-400 group-hover:text-amber-600 group-hover:translate-x-0.5 transition" />
          </div>

          <div className="text-xl sm:text-2xl font-black text-gray-900 dark:text-white mt-1.5 truncate font-mono">
            {attentionList.length} Alerts
          </div>

          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-1.5 truncate">
            {overdueList.length > 0 ? (
              <span className="text-rose-600 dark:text-rose-400 font-bold">
                {overdueList.length} Overdue
              </span>
            ) : (
              <span className="text-emerald-600 dark:text-emerald-400">0 Overdue</span>
            )}
            <span>·</span>
            <span>{todayList.length} Today</span>
            <span>·</span>
            <span>{soonList.length} Coming up</span>
          </div>
          <div className="text-[10px] text-gray-400 mt-0.5">
            IST calculated reminder windows
          </div>
        </div>
      </div>

      {/* Grid: Money going out + Where it goes */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Money going out bar chart */}
        <div className="lg:col-span-7 bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs">
          <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
            Money going out
          </h2>
          <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mb-4">
            Pending dues by when they fall, next 30 days
          </p>

          <div className="w-full">
            <svg
              className="w-full h-auto"
              viewBox="0 0 520 220"
              role="img"
              aria-label="Amount due by period"
            >
              {buckets.map((d, i) => {
                const W = 520;
                const H = 220;
                const pt = 28;
                const pb = 34;
                const pl = 10;
                const pr = 10;
                const bw = (W - pl - pr) / buckets.length;
                const gap = 20;
                const h = d.value ? Math.max(4, ((H - pt - pb) * d.value) / maxBucket) : 0;
                const x = pl + i * bw + gap / 2;
                const w = bw - gap;
                const y = H - pb - h;
                const cx = x + w / 2;

                return (
                  <g key={d.label}>
                    <title>
                      {d.label}: {d.value ? inr(d.value) : 'nothing due'}
                    </title>
                    {h > 0 && (
                      <rect
                        x={x}
                        y={y}
                        width={w}
                        height={h}
                        rx={4}
                        fill={d.bad ? 'var(--bad)' : 'var(--accent)'}
                      />
                    )}
                    <text
                      x={cx}
                      y={h ? y - 7 : H - pb - 7}
                      className="fill-[#0F1B2D] dark:fill-[#E8EDF5] font-semibold text-[11px]"
                      textAnchor="middle"
                    >
                      {d.value ? inrS(d.value) : '–'}
                    </text>
                    <text
                      x={cx}
                      y={H - pb + 20}
                      className="fill-[#46566C] dark:fill-[#A9B6C9] text-[11px]"
                      textAnchor="middle"
                    >
                      {d.label}
                    </text>
                  </g>
                );
              })}
              <line
                x1={10}
                x2={510}
                y1={220 - 34}
                y2={220 - 34}
                className="stroke-[#DCE2EA] dark:stroke-[#25324A]"
                strokeWidth={1}
              />
            </svg>
          </div>
        </div>

        {/* Where it goes breakdown */}
        <div className="lg:col-span-5 bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs">
          <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
            Where it goes
          </h2>
          <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mb-4">
            Pending dues by type, next 90 days
          </p>

          <div className="space-y-3">
            {catItems.length ? (
              catItems.map((item) => (
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
                      style={{ width: `${Math.max(4, (item.v / catMax) * 100)}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <div className="text-xs text-[#6F7E92] dark:text-[#8594AA] py-8 text-center">
                No pending dues in the next 90 days.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Needs Attention List */}
      <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
              Needs attention
            </h2>
            <p className="text-xs text-[#6F7E92] dark:text-[#8594AA]">
              Overdue, due today, or inside your alert window
            </p>
          </div>
          {attentionList.length > 0 && (
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-rose-100 dark:bg-rose-950/70 text-rose-700 dark:text-rose-300">
              {attentionList.length} urgent
            </span>
          )}
        </div>

        <div className="divide-y divide-[#DCE2EA] dark:divide-[#25324A] mt-3">
          {attentionList.length ? (
            attentionList.map((alert) => (
              <ItemRow
                key={alert.row.id + alert.vk + alert.due}
                alert={alert}
                onMarkPaid={onMarkPaid}
                onEdit={onEdit}
                onDelete={onDelete}
                onViewAttachment={onViewAttachment}
              />
            ))
          ) : (
            <div className="text-xs sm:text-sm text-[#6F7E92] dark:text-[#8594AA] py-8 text-center">
              All clear. Nothing is due inside your alert windows.
            </div>
          )}
        </div>
      </div>

      {/* Grid: Renewals & Expiries Ahead + Investment Mix */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Renewals & Expiries Ahead */}
        <div className="lg:col-span-7 bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs">
          <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
            Renewals and expiries ahead
          </h2>
          <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mb-3">
            FD renewals, maturities, interest dates and document expiries in the next 90 days
          </p>

          <div className="divide-y divide-[#DCE2EA] dark:divide-[#25324A]">
            {ahead.length ? (
              ahead.map((alert) => (
                <ItemRow
                  key={alert.row.id + alert.vk + alert.due}
                  alert={alert}
                  compact
                  onEdit={onEdit}
                  onDelete={onDelete}
                />
              ))
            ) : (
              <div className="text-xs text-[#6F7E92] dark:text-[#8594AA] py-8 text-center">
                Nothing is maturing or expiring in the next 90 days.
              </div>
            )}
          </div>
        </div>

        {/* Investment mix */}
        <div className="lg:col-span-5 bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs">
          <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
            Investment mix
          </h2>
          <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mb-4">
            Current portfolio split by asset type
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
                      className="h-full bg-[#0B3B66] dark:bg-[#5B9BE0] rounded-full transition-all"
                      style={{ width: `${Math.max(4, (item.v / allocMax) * 100)}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <div className="text-xs text-[#6F7E92] dark:text-[#8594AA] py-8 text-center">
                Add investments to see how your money is spread.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
