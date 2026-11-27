import React, { useMemo, useState } from 'react';
import {
  BellPlus,
  BookmarkPlus,
  CalendarClock,
  Check,
  LineChart,
  Plus,
  Search,
  SlidersHorizontal,
  Trash2,
} from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import {
  ALL_SECTORS,
  INDIAN_STOCKS,
  UNIVERSE_COUNTS,
  matchesUniverseScope,
} from '../data/indianMarketData';
import { run52WeekBreakoutScanner } from '../engine/analyticsEngine';
import { BreakoutScanConfig, MarketCapBucket, UniverseScope } from '../types/market';
import { formatCr, formatINR, formatPct } from '../utils/formatters';

interface BreakoutScannerViewProps {
  onInspectStock: (ticker: string, context?: { prior52WHigh?: number }) => void;
}

const LOOKBACK_PRESETS = [3, 6, 9, 12, 18, 24];

const UNIVERSE_SCOPE_OPTIONS: { id: UniverseScope; label: string; count: number }[] = [
  { id: 'all', label: 'All NSE', count: UNIVERSE_COUNTS.total },
  { id: 'nifty500', label: 'NIFTY 500', count: UNIVERSE_COUNTS.nifty500 },
  { id: 'fno', label: 'F&O', count: UNIVERSE_COUNTS.fno },
  { id: 'midcap', label: 'Midcap 150', count: UNIVERSE_COUNTS.midcap },
  { id: 'smallcap', label: 'Smallcap 500', count: UNIVERSE_COUNTS.smallcap },
];

export const BreakoutScannerView: React.FC<BreakoutScannerViewProps> = ({
  onInspectStock,
}) => {
  const {
    watchlist,
    toggleWatchlist,
    addManyToWatchlist,
    savedScans,
    saveBreakoutScan,
    deleteBreakoutScan,
    toggleScanSchedule,
    addAlert,
    marketVersion,
  } = useAppData();

  const [lookbackMonths, setLookbackMonths] = useState<number>(3);
  const [recentBreakoutDays, setRecentBreakoutDays] = useState<number>(5);
  const [breakoutType, setBreakoutType] = useState<'all' | 'ath_only' | '52w_only'>('all');
  const [priceBasis, setPriceBasis] = useState<'close' | 'high'>('close');
  const [minVolumeRatio, setMinVolumeRatio] = useState<number>(1.1);
  const [minPriceInr, setMinPriceInr] = useState<number>(50);
  const [minTurnoverCr, setMinTurnoverCr] = useState<number>(10);
  const [universeScope, setUniverseScope] = useState<UniverseScope>('all');
  const [visibleLimit, setVisibleLimit] = useState<number>(80);
  const [capBucket, setCapBucket] = useState<'All' | MarketCapBucket>('All');
  const [sector, setSector] = useState<string>('All');
  const [scanName, setScanName] = useState<string>('');
  const [feedback, setFeedback] = useState<string | null>(null);

  const activeConfig: BreakoutScanConfig = useMemo(
    () => ({
      name: scanName || `${lookbackMonths}M First 52W/ATH High (${minVolumeRatio}× Vol)`,
      lookbackMonths,
      recentBreakoutDays,
      breakoutType,
      priceBasis,
      minVolumeRatio,
      minPriceInr,
      minTurnoverCr,
      capBucket,
      sector,
      scheduleEnabled: true,
      scheduleTimeIst: '15:35 IST',
    }),
    [
      scanName,
      lookbackMonths,
      recentBreakoutDays,
      breakoutType,
      priceBasis,
      minVolumeRatio,
      minPriceInr,
      minTurnoverCr,
      capBucket,
      sector,
    ]
  );

  const scopedStocks = useMemo(() => {
    void marketVersion;
    return INDIAN_STOCKS.filter((s) => matchesUniverseScope(s, universeScope));
  }, [universeScope, marketVersion]);

  const allBreakoutResults = useMemo(
    () => run52WeekBreakoutScanner(scopedStocks, { ...activeConfig, breakoutType: 'all' }),
    [scopedStocks, activeConfig, marketVersion]
  );

  const athCount = useMemo(
    () => allBreakoutResults.filter((r) => r.isAllTimeHighBreakout).length,
    [allBreakoutResults]
  );

  const results = useMemo(() => {
    if (breakoutType === 'ath_only') {
      return allBreakoutResults.filter((r) => r.isAllTimeHighBreakout);
    }
    if (breakoutType === '52w_only') {
      return allBreakoutResults.filter((r) => r.isFirstInNMonths && !r.isAllTimeHighBreakout);
    }
    return allBreakoutResults;
  }, [allBreakoutResults, breakoutType]);

  const showToast = (msg: string) => {
    setFeedback(msg);
    setTimeout(() => setFeedback(null), 3200);
  };

  const handleSaveScan = async () => {
    await saveBreakoutScan({
      ...activeConfig,
      name: scanName.trim() || `${lookbackMonths}M Breakout (${minVolumeRatio}× Vol)`,
    });
    setScanName('');
    showToast('Scan preset saved & scheduled for daily NSE post-close.');
  };

  const handleLoadScan = (s: BreakoutScanConfig) => {
    setLookbackMonths(s.lookbackMonths);
    setPriceBasis(s.priceBasis);
    setMinVolumeRatio(s.minVolumeRatio);
    setMinPriceInr(s.minPriceInr);
    setMinTurnoverCr(s.minTurnoverCr);
    setCapBucket(s.capBucket);
    setSector(s.sector);
    showToast(`Loaded scan: ${s.name}`);
  };

  const handleTriggerAlerts = async () => {
    if (results.length === 0) return;
    const top = results.slice(0, 4);
    for (const r of top) {
      await addAlert({
        ticker: r.stock.ticker,
        category: 'breakout_52w',
        title: `${r.stock.ticker} — ${
          r.isAllTimeHighBreakout ? 'All-Time High & 52W Breakout' : `First 52W High in ${r.monthsSinceLast52WHigh} Months`
        }`,
        message: `${priceBasis === 'close' ? 'Closed' : 'Intraday high'} ${formatPct(
          r.isAllTimeHighBreakout ? r.pctAbovePriorAth : r.pctAbovePriorHigh
        )} above prior ${r.isAllTimeHighBreakout ? 'All-Time High' : '52W high'} (${formatINR(
          r.isAllTimeHighBreakout ? r.priorAllTimeHigh : r.prior52WHigh
        )}) on ${r.volumeRatio.toFixed(2)}× 50D avg volume.`,
      });
    }
    showToast(`Triggered ${top.length} breakout alerts in Notifications.`);
  };

  const handleAddAllWatchlist = async () => {
    if (results.length === 0) return;
    await addManyToWatchlist(results.map((r) => r.stock.ticker));
    showToast(`Added ${results.length} breakout stocks to Watchlist.`);
  };

  return (
    <div className="space-y-6">
      {/* Header Row */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            52-Week &amp; All-Time High Breakout Scanner
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Detects NSE/BSE equities making a fresh <strong className="text-slate-900 dark:text-slate-100">All-Time High (ATH)</strong> or new 52-week high for the first time in{' '}
            <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">
              {lookbackMonths} months
            </span>{' '}
            with configurable volume expansion, turnover, and base structure filters.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleAddAllWatchlist}
            disabled={results.length === 0}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 whitespace-nowrap"
          >
            <Plus className="w-3.5 h-3.5" />
            Add {results.length} to Watchlist
          </button>
          <button
            onClick={handleTriggerAlerts}
            disabled={results.length === 0}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 whitespace-nowrap"
          >
            <BellPlus className="w-3.5 h-3.5" />
            Trigger Breakout Alerts
          </button>
        </div>
      </div>

      {feedback && (
        <div className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
          <Check className="w-4 h-4 shrink-0" />
          <span>{feedback}</span>
        </div>
      )}

      {/* Filter Configuration Surface */}
      <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
            <SlidersHorizontal className="w-4 h-4 text-blue-500" />
            <span>Breakout Lookback & Institutional Filters</span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div
              className="flex flex-wrap items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800"
              role="group"
              aria-label="NSE Universe Scope"
            >
              {UNIVERSE_SCOPE_OPTIONS.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => {
                    setUniverseScope(opt.id);
                    setVisibleLimit(80);
                  }}
                  className={`px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                    universeScope === opt.id
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {opt.label} <span className="font-mono text-[10px] opacity-80">{opt.count}</span>
                </button>
              ))}
            </div>

            <div className="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
              {(
                [
                  { d: 1, label: 'Today (1D)' },
                  { d: 5, label: 'This Week (5D)' },
                  { d: 10, label: '2W (10D)' },
                  { d: 20, label: '1M (20D)' },
                ] as const
              ).map((win) => (
                <button
                  key={win.d}
                  onClick={() => setRecentBreakoutDays(win.d)}
                  className={`px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                    recentBreakoutDays === win.d
                      ? 'bg-emerald-600 text-white font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {win.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
              <button
                onClick={() => {
                  setBreakoutType('all');
                  setVisibleLimit(80);
                }}
                className={`px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                  breakoutType === 'all'
                    ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                All ({allBreakoutResults.length})
              </button>
              <button
                onClick={() => {
                  setBreakoutType('ath_only');
                  setVisibleLimit(80);
                }}
                className={`px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                  breakoutType === 'ath_only'
                    ? 'bg-amber-500 text-slate-950 font-semibold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                All-Time High ({athCount})
              </button>
              <button
                onClick={() => {
                  setBreakoutType('52w_only');
                  setVisibleLimit(80);
                }}
                className={`px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                  breakoutType === '52w_only'
                    ? 'bg-blue-600 text-white font-semibold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                52W Only ({Math.max(0, allBreakoutResults.length - athCount)})
              </button>
            </div>

            <div className="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
              <button
                onClick={() => setPriceBasis('close')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                  priceBasis === 'close'
                    ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400'
                }`}
              >
                Close &gt; High
              </button>
              <button
                onClick={() => setPriceBasis('high')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                  priceBasis === 'high'
                    ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400'
                }`}
              >
                Intraday High
              </button>
            </div>
          </div>
        </div>

        {/* Lookback N Months Selector */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-end">
          <div className="lg:col-span-5 space-y-1.5">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
              No New 52-Week High in Preceding N Months
            </label>
            <div className="flex flex-wrap items-center gap-1.5">
              {LOOKBACK_PRESETS.map((m) => (
                <button
                  key={m}
                  onClick={() => setLookbackMonths(m)}
                  className={`px-3 py-2 text-xs font-mono font-medium rounded-lg border transition-colors whitespace-nowrap ${
                    lookbackMonths === m
                      ? 'border-blue-600 bg-blue-600 text-white'
                      : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:border-slate-400'
                  }`}
                >
                  {m}M
                </button>
              ))}
              <div className="flex items-center gap-1.5 ml-1">
                <input
                  type="number"
                  min={1}
                  max={36}
                  value={lookbackMonths}
                  onChange={(e) =>
                    setLookbackMonths(Math.max(1, Math.min(36, Number(e.target.value) || 1)))
                  }
                  aria-label="Custom lookback months"
                  className="w-16 px-2.5 py-2 text-xs font-mono tabular-nums rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-xs text-slate-500">mo</span>
              </div>
            </div>
          </div>

          <div className="lg:col-span-2 space-y-1.5">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
              Min Vol Ratio (× 50D)
            </label>
            <input
              type="number"
              step={0.1}
              min={0}
              max={10}
              value={minVolumeRatio}
              onChange={(e) => setMinVolumeRatio(Math.max(0, Number(e.target.value) || 0))}
              className="w-full px-3 py-2 text-xs font-mono tabular-nums rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="lg:col-span-2 space-y-1.5">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
              Min Price (₹)
            </label>
            <input
              type="number"
              step={25}
              min={0}
              value={minPriceInr}
              onChange={(e) => setMinPriceInr(Math.max(0, Number(e.target.value) || 0))}
              className="w-full px-3 py-2 text-xs font-mono tabular-nums rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="lg:col-span-3 space-y-1.5">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
              Min Avg Turnover (₹ Cr)
            </label>
            <input
              type="number"
              step={25}
              min={0}
              value={minTurnoverCr}
              onChange={(e) => setMinTurnoverCr(Math.max(0, Number(e.target.value) || 0))}
              className="w-full px-3 py-2 text-xs font-mono tabular-nums rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            />
          </div>
        </div>

        {/* Cap Bucket, Sector, and Save Scan Row */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 pt-4 border-t border-slate-200 dark:border-slate-800 items-end">
          <div className="lg:col-span-4 space-y-1.5">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
              Market-Cap Bucket
            </label>
            <div className="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
              {(['All', 'Large', 'Mid', 'Small', 'Micro'] as const).map((bucket) => (
                <button
                  key={bucket}
                  onClick={() => setCapBucket(bucket)}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                    capBucket === bucket
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400'
                  }`}
                >
                  {bucket}
                </button>
              ))}
            </div>
          </div>

          <div className="lg:col-span-3 space-y-1.5">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
              NSE Sector
            </label>
            <select
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            >
              <option value="All">All Sectors ({INDIAN_STOCKS.length})</option>
              {ALL_SECTORS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div className="lg:col-span-5 flex items-end gap-2">
            <div className="flex-1 space-y-1.5">
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                Save Current Scan Preset
              </label>
              <input
                type="text"
                placeholder={`e.g. ${lookbackMonths}M Fresh Base Breakouts`}
                value={scanName}
                onChange={(e) => setScanName(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>
            <button
              onClick={handleSaveScan}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 hover:opacity-90 whitespace-nowrap"
            >
              <BookmarkPlus className="w-3.5 h-3.5" />
              Save Scan
            </button>
          </div>
        </div>
      </div>

      {/* Scanner Results Table */}
      <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2.5 text-sm font-semibold text-slate-900 dark:text-slate-100">
            <Search className="w-4 h-4 text-blue-500" />
            <span>Qualifying Breakouts ({results.length})</span>
            <span className="text-xs font-mono font-semibold text-amber-600 dark:text-amber-400">
              · {athCount} All-Time High (ATH)
            </span>
          </div>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
            Scanned Universe: {scopedStocks.length.toLocaleString('en-IN')} / {INDIAN_STOCKS.length.toLocaleString('en-IN')} NSE equities · Lookback ≥ {lookbackMonths}M · Vol ≥{' '}
            {minVolumeRatio.toFixed(1)}×
          </span>
        </div>

        {results.length === 0 ? (
          <div className="p-10 text-center space-y-2">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
              No equities match the current breakout filters.
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Try lowering the lookback window (e.g., 6M) or volume multiple (e.g., 1.2×).
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-medium text-slate-500 dark:text-slate-400 bg-slate-50/70 dark:bg-slate-900/40">
                  <th className="py-2.5 px-4">Symbol / Sector</th>
                  <th className="py-2.5 px-3">Breakout Type</th>
                  <th className="py-2.5 px-3 text-right">LTP (₹)</th>
                  <th className="py-2.5 px-3 text-right">Breakout Date</th>
                  <th className="py-2.5 px-3 text-right">Since Last 52W</th>
                  <th className="py-2.5 px-3 text-right">% Above Prior</th>
                  <th className="py-2.5 px-3 text-right">Vol Ratio</th>
                  <th className="py-2.5 px-3 text-right">Base Len / Depth</th>
                  <th className="py-2.5 px-3 text-right">Turnover</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/80 dark:divide-slate-800/80 text-xs">
                {results.slice(0, visibleLimit).map((r) => {
                  const watched = watchlist.includes(r.stock.ticker);
                  return (
                    <tr
                      key={r.stock.ticker}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="py-3 px-4">
                        <button
                          onClick={() =>
                            onInspectStock(r.stock.ticker, {
                              prior52WHigh: r.isAllTimeHighBreakout
                                ? r.priorAllTimeHigh
                                : r.prior52WHigh,
                            })
                          }
                          className="text-left group"
                        >
                          <div className="font-mono font-semibold text-slate-900 dark:text-slate-100 group-hover:text-blue-500">
                            {r.stock.ticker}
                          </div>
                          <div className="text-[11px] text-slate-500 dark:text-slate-400">
                            {r.stock.capBucket} · {r.stock.sector}
                          </div>
                        </button>
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap">
                        {r.isAllTimeHighBreakout ? (
                          <div>
                            <div className="font-semibold text-amber-600 dark:text-amber-400">
                              All-Time High + 52W
                            </div>
                            <div className="text-[10px] font-mono text-slate-500 tabular-nums">
                              Prior ATH {formatINR(r.priorAllTimeHigh, 0)} ({r.athHistoryYears.toFixed(1)}Y)
                            </div>
                          </div>
                        ) : (
                          <div>
                            <div className="font-medium text-blue-600 dark:text-blue-400">
                              52-Week High
                            </div>
                            <div className="text-[10px] font-mono text-slate-500 tabular-nums">
                              {r.pctAbovePriorAth.toFixed(1)}% vs ATH ({formatINR(r.priorAllTimeHigh, 0)})
                            </div>
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums font-medium text-slate-900 dark:text-slate-100">
                        {formatINR(r.stock.latestClose)}
                        <div
                          className={`text-[11px] ${
                            r.stock.dailyChangePct >= 0
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-red-600 dark:text-red-400'
                          }`}
                        >
                          {formatPct(r.stock.dailyChangePct)}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums text-slate-600 dark:text-slate-300">
                        <div>{r.breakoutDate}</div>
                        <div className="text-[10px] text-slate-400">
                          {r.barsAgo === 0 ? 'Latest Session' : `${r.barsAgo ?? 0}D ago`}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums font-semibold text-blue-600 dark:text-blue-400">
                        {r.monthsSinceLast52WHigh.toFixed(1)} mo
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums font-semibold text-emerald-600 dark:text-emerald-400">
                        +{r.isAllTimeHighBreakout ? r.pctAbovePriorAth.toFixed(2) : r.pctAbovePriorHigh.toFixed(2)}%
                        <div className="text-[11px] font-normal text-slate-500">
                          {r.isAllTimeHighBreakout ? 'Prior ATH ' : 'Prior 52W '}
                          {formatINR(r.isAllTimeHighBreakout ? r.priorAllTimeHigh : r.prior52WHigh, 0)}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums font-semibold text-slate-900 dark:text-slate-100">
                        {r.volumeRatio.toFixed(2)}×
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums text-slate-600 dark:text-slate-300">
                        {r.baseLengthWeeks}w / -{r.baseDepthPct}%
                      </td>
                      <td className="py-3 px-3 text-right font-mono tabular-nums text-slate-600 dark:text-slate-300">
                        {formatCr(r.stock.avgDailyTurnoverCr)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            onClick={() =>
                              onInspectStock(r.stock.ticker, { prior52WHigh: r.prior52WHigh })
                            }
                            className="p-1.5 rounded-md border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-blue-500 hover:border-blue-500/40"
                            title="Inspect Chart"
                          >
                            <LineChart className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => toggleWatchlist(r.stock.ticker)}
                            className={`px-2.5 py-1.5 rounded-md text-[11px] font-medium border transition-colors whitespace-nowrap ${
                              watched
                                ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                                : 'border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                            }`}
                          >
                            {watched ? 'Watching' : '+ Watch'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {results.length > visibleLimit && (
              <div className="px-5 py-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs bg-slate-50/50 dark:bg-slate-900/40">
                <span className="text-slate-500 font-mono tabular-nums">
                  Showing {Math.min(visibleLimit, results.length)} of {results.length} qualifying breakouts
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

      {/* Saved Scans & Daily NSE Schedule */}
      <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
            <CalendarClock className="w-4 h-4 text-blue-500" />
            <span>Saved Scans & Daily NSE Schedule (IST)</span>
          </div>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            Runs automatically on NSE trading days
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {savedScans.map((scan) => (
            <div
              key={scan.id}
              className="flex items-center justify-between gap-3 p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50"
            >
              <div className="min-w-0">
                <button
                  onClick={() => handleLoadScan(scan)}
                  className="text-sm font-semibold text-slate-900 dark:text-slate-100 hover:text-blue-500 truncate block text-left"
                >
                  {scan.name}
                </button>
                <div className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5">
                  {scan.lookbackMonths}M · {scan.priceBasis} · Vol ≥ {scan.minVolumeRatio}× ·{' '}
                  {scan.capBucket} Cap · {scan.scheduleTimeIst}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() =>
                    scan.id &&
                    toggleScanSchedule(scan.id, !scan.scheduleEnabled, scan.scheduleTimeIst)
                  }
                  className={`px-2.5 py-1 text-[11px] font-medium rounded-md border transition-colors whitespace-nowrap ${
                    scan.scheduleEnabled
                      ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                      : 'border-slate-300 dark:border-slate-700 text-slate-500'
                  }`}
                >
                  {scan.scheduleEnabled ? 'Scheduled' : 'Paused'}
                </button>
                {scan.id && (
                  <button
                    onClick={() => deleteBreakoutScan(scan.id!)}
                    className="p-1.5 text-slate-400 hover:text-red-500"
                    title="Delete saved scan"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
