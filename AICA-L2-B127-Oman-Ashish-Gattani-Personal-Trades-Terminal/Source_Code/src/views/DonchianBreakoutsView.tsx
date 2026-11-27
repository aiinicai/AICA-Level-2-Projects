import React, { useMemo, useState } from 'react';
import {
  BellPlus,
  Check,
  Download,
  GitCommitHorizontal,
  LineChart,
  Plus,
  Search,
  Star,
} from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import {
  ALL_SECTORS,
  INDIAN_STOCKS,
  UNIVERSE_COUNTS,
  matchesUniverseScope,
} from '../data/indianMarketData';
import { DonchianPeriod, scanDonchianAlerts } from '../engine/tradeRadarEngine';
import { UniverseScope } from '../types/market';
import { formatCr, formatINR, formatPct } from '../utils/formatters';

interface DonchianBreakoutsViewProps {
  onInspectStock: (ticker: string) => void;
}

const UNIVERSE_SCOPE_OPTIONS: { id: UniverseScope; label: string; count: number }[] = [
  { id: 'all', label: 'All NSE', count: UNIVERSE_COUNTS.total },
  { id: 'nifty500', label: 'NIFTY 500', count: UNIVERSE_COUNTS.nifty500 },
  { id: 'fno', label: 'F&O', count: UNIVERSE_COUNTS.fno },
  { id: 'midcap', label: 'Midcap 150', count: UNIVERSE_COUNTS.midcap },
  { id: 'smallcap', label: 'Smallcap 500', count: UNIVERSE_COUNTS.smallcap },
];

const RECENCY_PRESETS: { days: number; label: string }[] = [
  { days: 0, label: 'Today' },
  { days: 5, label: 'This Week (5D)' },
  { days: 10, label: 'Last 2W (10D)' },
  { days: 20, label: 'Last Month (20D)' },
];

export const DonchianBreakoutsView: React.FC<DonchianBreakoutsViewProps> = ({
  onInspectStock,
}) => {
  const {
    watchlist,
    toggleWatchlist,
    addManyToWatchlist,
    addAlert,
    marketVersion,
    liveSymbolsCount,
    totalUniverseCount,
    isHydratingExtended,
  } = useAppData();

  const [period, setPeriod] = useState<DonchianPeriod>(20);
  const [maxBarsAgo, setMaxBarsAgo] = useState<number>(5); // Default: This Week including Today
  const [signalFilter, setSignalFilter] = useState<'BUY' | 'SELL' | 'ALL'>('BUY');
  const [universeScope, setUniverseScope] = useState<UniverseScope>('all');
  const [sectorFilter, setSectorFilter] = useState<string>('All');
  const [minVolRatio, setMinVolRatio] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [visibleLimit, setVisibleLimit] = useState<number>(80);
  const [alertedTickers, setAlertedTickers] = useState<Record<string, boolean>>({});
  const [toast, setToast] = useState<string | null>(null);

  const notify = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const scopedStocks = useMemo(() => {
    void marketVersion;
    return INDIAN_STOCKS.filter((s) => matchesUniverseScope(s, universeScope));
  }, [universeScope, marketVersion]);

  const rawRows = useMemo(() => {
    void marketVersion;
    return scanDonchianAlerts(scopedStocks, period, maxBarsAgo);
  }, [scopedStocks, period, maxBarsAgo, marketVersion]);

  const stockByTicker = useMemo(() => {
    void marketVersion;
    return new Map(INDIAN_STOCKS.map((s) => [s.ticker, s]));
  }, [marketVersion]);

  const filteredRows = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return rawRows.filter((row) => {
      if (signalFilter !== 'ALL' && row.alert.type !== signalFilter) return false;
      if (sectorFilter !== 'All' && row.sector !== sectorFilter) return false;
      if (row.alert.volRatio < minVolRatio) return false;
      if (q) {
        const hitTicker = row.ticker.toLowerCase().includes(q);
        const hitName = row.name.toLowerCase().includes(q);
        const hitSector = row.sector.toLowerCase().includes(q);
        if (!hitTicker && !hitName && !hitSector) return false;
      }
      return true;
    });
  }, [rawRows, signalFilter, sectorFilter, minVolRatio, searchQuery]);

  const kpis = useMemo(() => {
    const todayBuys = rawRows.filter((r) => r.alert.type === 'BUY' && r.alert.barsAgo === 0).length;
    const weekBuys = rawRows.filter((r) => r.alert.type === 'BUY').length;
    const weekSells = rawRows.filter((r) => r.alert.type === 'SELL').length;
    const highVolBuys = rawRows.filter(
      (r) => r.alert.type === 'BUY' && r.alert.volRatio >= 1.5
    ).length;
    return { todayBuys, weekBuys, weekSells, highVolBuys };
  }, [rawRows]);

  const handleAddTopToWatchlist = async () => {
    if (filteredRows.length === 0) return;
    const batch = filteredRows.slice(0, 25).map((r) => r.ticker);
    await addManyToWatchlist(batch);
    notify(`Added ${batch.length} Donchian breakout stocks to Watchlist.`);
  };

  const handleCreateAlert = async (row: (typeof filteredRows)[number]) => {
    await addAlert({
      ticker: row.ticker,
      category: 'price',
      title: `${row.ticker} — DC(${period}) ${row.alert.type} @ ${formatINR(row.alert.triggerPrice)}`,
      message: `${row.alert.type === 'BUY' ? 'Broke above' : 'Broke below'} prior ${period}D channel ${
        row.alert.type === 'BUY' ? 'high' : 'low'
      } (${formatINR(row.alert.channelLevel)}) on ${row.alert.date} (${row.alert.volRatio.toFixed(2)}× vol).`,
    });
    setAlertedTickers((prev) => ({ ...prev, [row.ticker]: true }));
  };

  const handleExportCsv = () => {
    if (filteredRows.length === 0) return;
    const headers = [
      'Ticker',
      'Sector',
      'Cap',
      'Signal',
      'AlertDate',
      'BarsAgo',
      'DC_TriggerPrice_INR',
      'PriorChannelLevel_INR',
      'BreakoutPct',
      'CurrentLTP_INR',
      'MoveSinceBreakoutPct',
      'VolRatio',
      'ChannelWidthPct',
      'TurnoverCr',
    ];
    const lines = filteredRows.map((r) =>
      [
        r.ticker,
        `"${r.sector}"`,
        r.capBucket,
        r.alert.type,
        r.alert.date,
        r.alert.barsAgo,
        r.alert.triggerPrice.toFixed(2),
        r.alert.channelLevel.toFixed(2),
        r.alert.breakoutPct.toFixed(2),
        r.close.toFixed(2),
        r.alert.rawMovePct.toFixed(2),
        r.alert.volRatio.toFixed(2),
        r.channelWidthPct.toFixed(1),
        (stockByTicker.get(r.ticker)?.avgDailyTurnoverCr ?? 0).toFixed(1),
      ].join(',')
    );
    const csv = [headers.join(','), ...lines].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `donchian-${period}d-breakouts-${maxBarsAgo === 0 ? 'today' : `${maxBarsAgo}d`}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Donchian Channel Breakouts Scanner
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Live non-repainting Donchian Channel ({period}D) breakouts happening this week including today across{' '}
            <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">
              {scopedStocks.length.toLocaleString('en-IN')}
            </span>{' '}
            NSE equities ({liveSymbolsCount.toLocaleString('en-IN')}/{totalUniverseCount.toLocaleString('en-IN')}{' '}
            {isHydratingExtended ? 'syncing live…' : 'live'}).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleAddTopToWatchlist}
            disabled={filteredRows.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 whitespace-nowrap"
          >
            <Plus className="w-3.5 h-3.5" />
            Watchlist Top {Math.min(25, filteredRows.length)}
          </button>
          <button
            onClick={handleExportCsv}
            disabled={filteredRows.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 whitespace-nowrap"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </button>
        </div>
      </div>

      {toast && (
        <div className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
          <Check className="w-4 h-4 shrink-0" />
          <span>{toast}</span>
        </div>
      )}

      {/* 4 KPI Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">DC({period}) Buy Breakouts Today</div>
          <div className="text-xl font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400 mt-1">
            {kpis.todayBuys}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">Fresh session close &gt; {period}D high</div>
        </div>
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">
            Buy Breakouts ({maxBarsAgo === 0 ? 'Today' : `Last ${maxBarsAgo}D`})
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-1">
            {kpis.weekBuys}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">Active upside channel breakouts</div>
        </div>
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">High-Volume Breakouts (≥1.5×)</div>
          <div className="text-xl font-bold font-mono tabular-nums text-blue-600 dark:text-blue-400 mt-1">
            {kpis.highVolBuys}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">Institutional demand expansion</div>
        </div>
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">
            Sell Breakdowns ({maxBarsAgo === 0 ? 'Today' : `Last ${maxBarsAgo}D`})
          </div>
          <div className="text-xl font-bold font-mono tabular-nums text-red-600 dark:text-red-400 mt-1">
            {kpis.weekSells}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">Closed below prior {period}D low</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Recency Window */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-slate-500">Breakout Window:</span>
            <div className="inline-flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
              {RECENCY_PRESETS.map((opt) => (
                <button
                  key={opt.days}
                  onClick={() => {
                    setMaxBarsAgo(opt.days);
                    setVisibleLimit(80);
                  }}
                  className={`px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                    maxBarsAgo === opt.days
                      ? 'bg-blue-600 text-white font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Donchian Channel Length + Signal Type */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
              {([10, 20, 55] as DonchianPeriod[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-2.5 py-1.5 text-xs font-mono font-medium rounded-md transition-colors whitespace-nowrap ${
                    period === p
                      ? 'bg-cyan-600 text-white font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  DC ({p}D)
                </button>
              ))}
            </div>

            <div className="inline-flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
              {(
                [
                  { id: 'BUY', label: 'Buy Breakouts' },
                  { id: 'SELL', label: 'Sell Breakdowns' },
                  { id: 'ALL', label: 'All Signals' },
                ] as const
              ).map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => setSignalFilter(opt.id)}
                  className={`px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                    signalFilter === opt.id
                      ? opt.id === 'SELL'
                        ? 'bg-red-600 text-white font-semibold'
                        : 'bg-emerald-600 text-white font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Row 2: Universe Scope, Search, Sector & Volume Filter */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
          <div className="flex flex-wrap items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
            {UNIVERSE_SCOPE_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                onClick={() => {
                  setUniverseScope(opt.id);
                  setVisibleLimit(80);
                }}
                className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                  universeScope === opt.id
                    ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                {opt.label} <span className="font-mono text-[10px] opacity-75">{opt.count}</span>
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search ticker or sector…"
                className="w-44 pl-8 pr-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>

            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            >
              <option value="All">All Sectors</option>
              {ALL_SECTORS.map((sec) => (
                <option key={sec} value={sec}>
                  {sec}
                </option>
              ))}
            </select>

            <select
              value={minVolRatio}
              onChange={(e) => setMinVolRatio(Number(e.target.value))}
              className="px-2.5 py-1.5 font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            >
              <option value={0}>Any Vol</option>
              <option value={1.0}>Vol ≥ 1.0×</option>
              <option value={1.3}>Vol ≥ 1.3×</option>
              <option value={1.5}>Vol ≥ 1.5×</option>
              <option value={2.0}>Vol ≥ 2.0×</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results Table */}
      <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
            <GitCommitHorizontal className="w-4 h-4 text-cyan-500" />
            <span>
              Matching Donchian ({period}D) Signals ({filteredRows.length})
            </span>
          </div>
          <span className="text-xs font-mono text-slate-500">
            Sorted by newest breakout first, then volume expansion
          </span>
        </div>

        {filteredRows.length === 0 ? (
          <div className="p-10 text-center space-y-2">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
              No Donchian ({period}D) signals match the active filters.
            </p>
            <p className="text-xs text-slate-500">
              Try widening the Breakout Window (e.g., This Week or Last 2W) or lowering the volume multiple.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                <tr>
                  <th className="py-2.5 px-4">Ticker / Sector</th>
                  <th className="py-2.5 px-3">Signal</th>
                  <th className="py-2.5 px-3">Breakout Date</th>
                  <th className="py-2.5 px-3 text-right">DC Signal Price</th>
                  <th className="py-2.5 px-3 text-right">Prior {period}D Level</th>
                  <th className="py-2.5 px-3 text-right">Current LTP</th>
                  <th className="py-2.5 px-3 text-right">Move Since DC</th>
                  <th className="py-2.5 px-3 text-right">Vol Ratio</th>
                  <th className="py-2.5 px-3 text-right">Turnover</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                {filteredRows.slice(0, visibleLimit).map((row) => {
                  const watched = watchlist.includes(row.ticker);
                  const alerted = Boolean(alertedTickers[row.ticker]);
                  const isBuy = row.alert.type === 'BUY';
                  const turnoverCr = stockByTicker.get(row.ticker)?.avgDailyTurnoverCr ?? 0;
                  return (
                    <tr
                      key={`${row.ticker}-${row.alert.id}`}
                      onClick={() => onInspectStock(row.ticker)}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors cursor-pointer group"
                    >
                      <td className="py-3 px-4">
                        <div className="font-mono font-bold text-slate-900 dark:text-slate-100 group-hover:text-blue-500">
                          {row.ticker}
                        </div>
                        <div className="text-[11px] text-slate-500 truncate max-w-[200px]">
                          {row.capBucket} · {row.sector}
                        </div>
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap font-bold">
                        <span
                          className={
                            isBuy
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-red-600 dark:text-red-400'
                          }
                        >
                          {isBuy ? '▲ BUY Breakout' : '▼ SELL Breakdown'}
                        </span>
                        <div className="font-mono text-[10px] font-normal text-slate-500">
                          Break {row.alert.breakoutPct >= 0 ? '+' : ''}
                          {row.alert.breakoutPct.toFixed(2)}%
                        </div>
                      </td>
                      <td className="py-3 px-3 font-mono tabular-nums whitespace-nowrap">
                        <div className="text-slate-800 dark:text-slate-200 font-medium">
                          {row.alert.date}
                        </div>
                        <div
                          className={`text-[10px] font-semibold ${
                            row.alert.barsAgo === 0
                              ? 'text-blue-600 dark:text-blue-400'
                              : 'text-slate-500'
                          }`}
                        >
                          {row.alert.barsAgo === 0 ? 'Today (Latest)' : `${row.alert.barsAgo}D ago`}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums font-semibold text-slate-900 dark:text-slate-100">
                        {formatINR(row.alert.triggerPrice)}
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums text-slate-600 dark:text-slate-300">
                        {formatINR(row.alert.channelLevel)}
                        <div className="text-[10px] text-slate-400">
                          W {row.channelWidthPct.toFixed(1)}%
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">
                          {formatINR(row.close)}
                        </div>
                        <div
                          className={`text-[10px] ${
                            row.dailyChangePct >= 0
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-red-600 dark:text-red-400'
                          }`}
                        >
                          {formatPct(row.dailyChangePct)} 1D
                        </div>
                      </td>
                      <td
                        className={`py-3 px-3 text-right font-mono tabular-nums font-semibold ${
                          row.alert.rawMovePct >= 0
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        {formatPct(row.alert.rawMovePct)}
                      </td>
                      <td
                        className={`py-3 px-3 text-right font-mono tabular-nums font-semibold ${
                          row.alert.volRatio >= 1.5
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-slate-700 dark:text-slate-300'
                        }`}
                      >
                        {row.alert.volRatio.toFixed(2)}×
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums text-slate-600 dark:text-slate-300">
                        {formatCr(turnoverCr)}
                      </td>
                      <td
                        className="py-3 px-4 text-right whitespace-nowrap"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            onClick={() => toggleWatchlist(row.ticker)}
                            className={`p-1.5 rounded border transition-colors ${
                              watched
                                ? 'border-amber-500/40 bg-amber-500/10 text-amber-500'
                                : 'border-slate-200 dark:border-slate-700 text-slate-400 hover:text-amber-500'
                            }`}
                            title={watched ? 'Remove from Watchlist' : 'Add to Watchlist'}
                          >
                            <Star className="w-3.5 h-3.5" fill={watched ? 'currentColor' : 'none'} />
                          </button>
                          <button
                            onClick={() => void handleCreateAlert(row)}
                            className={`p-1.5 rounded border transition-colors ${
                              alerted
                                ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-500'
                                : 'border-slate-200 dark:border-slate-700 text-slate-400 hover:text-blue-500'
                            }`}
                            title="Save to Notifications"
                          >
                            {alerted ? (
                              <Check className="w-3.5 h-3.5" />
                            ) : (
                              <BellPlus className="w-3.5 h-3.5" />
                            )}
                          </button>
                          <button
                            onClick={() => onInspectStock(row.ticker)}
                            className="p-1.5 rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-blue-500"
                            title={`Inspect ${row.ticker} Chart`}
                          >
                            <LineChart className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {filteredRows.length > visibleLimit && (
              <div className="px-5 py-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs bg-slate-50/50 dark:bg-slate-900/40">
                <span className="text-slate-500 font-mono tabular-nums">
                  Showing {Math.min(visibleLimit, filteredRows.length)} of {filteredRows.length} signals
                </span>
                <button
                  onClick={() => setVisibleLimit((v) => v + 80)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium whitespace-nowrap"
                >
                  Show 80 More
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
