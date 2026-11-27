import React, { useEffect, useMemo, useState } from 'react';
import {
  ArrowUpRight,
  Award,
  BookOpen,
  Calculator,
  Check,
  Crosshair,
  LineChart,
  Plus,
  Search,
  ShieldAlert,
  Trash2,
} from 'lucide-react';
import { TopBuyWatchlistPanel } from '../components/TopBuyWatchlistPanel';
import { useAppData } from '../context/AppDataContext';
import { INDIAN_STOCKS, STOCK_BY_TICKER } from '../data/indianMarketData';
import {
  StockTradeDiagnosis,
  TradeSetupTag,
  computeMarketRegime,
  runTradeSetupRadar,
} from '../engine/tradeRadarEngine';
import { TradeJournalEntry } from '../types/market';
import { formatINR, formatINRCompact, formatPct } from '../utils/formatters';

interface TradeRadarViewProps {
  onInspectStock: (ticker: string) => void;
}

type RadarSubTab = 'top10' | 'regime' | 'scanner' | 'journal';

const JOURNAL_STORAGE_KEY = 'artha_trade_journal_v1';

const SETUP_LABELS: Record<TradeSetupTag, string> = {
  POCKET_PIVOT: 'Pocket Pivot',
  RS_BLUE_DOT: 'RS Blue-Dot',
  NR7_SQUEEZE: 'NR7 Squeeze',
  MA_PULLBACK: '21E/50S Pullback',
  EPISODIC_PIVOT: 'Episodic Pivot',
  VCP_BREAKOUT: 'VCP Breakout',
  WEEKLY_STAGE2: 'Weekly Stage 2',
};

const ALL_SETUP_TAGS: TradeSetupTag[] = [
  'POCKET_PIVOT',
  'RS_BLUE_DOT',
  'NR7_SQUEEZE',
  'MA_PULLBACK',
  'EPISODIC_PIVOT',
  'VCP_BREAKOUT',
  'WEEKLY_STAGE2',
];

function loadJournal(): TradeJournalEntry[] {
  try {
    const raw = localStorage.getItem(JOURNAL_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export const TradeRadarView: React.FC<TradeRadarViewProps> = ({ onInspectStock }) => {
  const { marketVersion } = useAppData();

  const [activeTab, setActiveTab] = useState<RadarSubTab>('scanner');

  // Scanner Filters
  const [setupFilter, setSetupFilter] = useState<'ALL' | TradeSetupTag>('ALL');
  const [sectorFilter, setSectorFilter] = useState<string>('ALL');
  const [hideExtended, setHideExtended] = useState<boolean>(false);
  const [minConviction, setMinConviction] = useState<number>(40);
  const [minAdrPct, setMinAdrPct] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortKey, setSortKey] = useState<'conviction' | 'rs' | 'adr' | 'vol' | 'dist50'>('conviction');

  // Compute live radar + regime on every market price refresh
  const radarRows = useMemo(() => runTradeSetupRadar(INDIAN_STOCKS), [marketVersion]);
  const regime = useMemo(
    () => computeMarketRegime(INDIAN_STOCKS, radarRows),
    [radarRows, marketVersion]
  );

  // Position Sizer & Trade Execution Ticket state
  const [ticketTicker, setTicketTicker] = useState<string>(() => radarRows[0]?.ticker || 'HAL');
  const [accountCapitalInr, setAccountCapitalInr] = useState<number>(1000000);
  const [riskPerTradePct, setRiskPerTradePct] = useState<number>(1.0);
  const [customEntry, setCustomEntry] = useState<string>('');
  const [customStop, setCustomStop] = useState<string>('');
  const [tradeNotes, setTradeNotes] = useState<string>('');
  const [journalStatusMsg, setJournalStatusMsg] = useState<string | null>(null);

  // Persistent Trade Journal
  const [journal, setJournal] = useState<TradeJournalEntry[]>(() => loadJournal());
  const [journalFilter, setJournalFilter] = useState<'ALL' | 'OPEN' | 'CLOSED'>('ALL');

  useEffect(() => {
    try {
      localStorage.setItem(JOURNAL_STORAGE_KEY, JSON.stringify(journal));
    } catch {
      // ignore storage quota errors
    }
  }, [journal]);

  const selectedDiag = useMemo(
    () => radarRows.find((r) => r.ticker === ticketTicker) || radarRows[0],
    [radarRows, ticketTicker]
  );

  const loadIntoTicket = (row: StockTradeDiagnosis) => {
    setTicketTicker(row.ticker);
    setCustomEntry(String(row.entryTriggerInr));
    setCustomStop(String(row.stopLossInr));
    setTradeNotes(`${row.primarySetup} · RS ${row.rsRating} · ADR ${row.adrPct20}%`);
    setActiveTab('journal');
  };

  const effectiveEntry =
    Number(customEntry) > 0 ? Number(customEntry) : selectedDiag?.entryTriggerInr || 100;
  const effectiveStop =
    Number(customStop) > 0 && Number(customStop) < effectiveEntry
      ? Number(customStop)
      : selectedDiag?.stopLossInr || effectiveEntry * 0.95;

  const riskPerShare = Math.max(0.05, effectiveEntry - effectiveStop);
  const stopPct = (riskPerShare / Math.max(0.01, effectiveEntry)) * 100;
  const rupeeRiskBudget = Math.max(0, (accountCapitalInr * riskPerTradePct) / 100);
  const rawQty = Math.floor(rupeeRiskBudget / riskPerShare);
  const maxAffordableQty = Math.floor(accountCapitalInr / Math.max(0.01, effectiveEntry));
  const shareQty = Math.max(0, Math.min(rawQty, maxAffordableQty));
  const positionValueInr = shareQty * effectiveEntry;
  const capitalAllocPct =
    accountCapitalInr > 0 ? (positionValueInr / accountCapitalInr) * 100 : 0;
  const r1Price = effectiveEntry + riskPerShare;
  const r2Price = effectiveEntry + 2 * riskPerShare;
  const r3Price = effectiveEntry + 3 * riskPerShare;

  const handleLogTrade = () => {
    if (!selectedDiag || shareQty <= 0) return;
    const entry: TradeJournalEntry = {
      id: `tr_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      ticker: selectedDiag.ticker,
      setup: selectedDiag.primarySetup,
      entryDate: new Date().toISOString().slice(0, 10),
      entryPrice: Number(effectiveEntry.toFixed(2)),
      stopLoss: Number(effectiveStop.toFixed(2)),
      shares: shareQty,
      status: 'OPEN',
      notes: tradeNotes.trim() || `${selectedDiag.primarySetup} (Conviction ${selectedDiag.convictionScore})`,
    };
    setJournal((prev) => [entry, ...prev]);
    setJournalStatusMsg(
      `Logged ${entry.shares} shares of ${entry.ticker} at ${formatINR(entry.entryPrice)} (Stop ${formatINR(entry.stopLoss)}).`
    );
    setTimeout(() => setJournalStatusMsg(null), 3500);
  };

  const handleCloseTradeAtLtp = (id: string) => {
    setJournal((prev) =>
      prev.map((tr) => {
        if (tr.id !== id) return tr;
        const ltp = STOCK_BY_TICKER[tr.ticker]?.latestClose ?? tr.entryPrice;
        return {
          ...tr,
          status: 'CLOSED',
          exitDate: new Date().toISOString().slice(0, 10),
          exitPrice: Number(ltp.toFixed(2)),
        };
      })
    );
  };

  const handleDeleteTrade = (id: string) => {
    setJournal((prev) => prev.filter((tr) => tr.id !== id));
  };

  // Filtered & sorted radar rows
  const sectorsList = useMemo(
    () => Array.from(new Set(radarRows.map((r) => r.sector))).sort(),
    [radarRows]
  );

  const filteredRadar = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const list = radarRows.filter((r) => {
      if (setupFilter !== 'ALL' && !r.setups.includes(setupFilter)) return false;
      if (sectorFilter !== 'ALL' && r.sector !== sectorFilter) return false;
      if (hideExtended && r.isExtended) return false;
      if (r.convictionScore < minConviction) return false;
      if (r.adrPct20 < minAdrPct) return false;
      if (q && !r.ticker.toLowerCase().includes(q) && !r.name.toLowerCase().includes(q)) return false;
      return true;
    });

    return list.sort((a, b) => {
      if (sortKey === 'rs') return b.rsRating - a.rsRating;
      if (sortKey === 'adr') return b.adrPct20 - a.adrPct20;
      if (sortKey === 'vol') return b.volRatio50D - a.volRatio50D;
      if (sortKey === 'dist50') return a.distFrom50SmaAtrs - b.distFrom50SmaAtrs;
      return b.convictionScore - a.convictionScore || b.rsRating - a.rsRating;
    });
  }, [radarRows, setupFilter, sectorFilter, hideExtended, minConviction, minAdrPct, searchQuery, sortKey]);

  // Journal Performance Stats (R-Multiple Analytics)
  const journalStats = useMemo(() => {
    let openPnlInr = 0;
    let realizedPnlInr = 0;
    let wins = 0;
    let closedCount = 0;
    let sumClosedR = 0;
    let openCount = 0;

    for (const tr of journal) {
      const rUnit = Math.max(0.05, tr.entryPrice - tr.stopLoss);
      if (tr.status === 'OPEN') {
        openCount++;
        const ltp = STOCK_BY_TICKER[tr.ticker]?.latestClose ?? tr.entryPrice;
        openPnlInr += (ltp - tr.entryPrice) * tr.shares;
      } else {
        closedCount++;
        const exitP = tr.exitPrice ?? tr.entryPrice;
        const pnl = (exitP - tr.entryPrice) * tr.shares;
        realizedPnlInr += pnl;
        const rMult = (exitP - tr.entryPrice) / rUnit;
        sumClosedR += rMult;
        if (pnl > 0) wins++;
      }
    }

    const winRatePct = closedCount > 0 ? (wins / closedCount) * 100 : 0;
    const avgR = closedCount > 0 ? sumClosedR / closedCount : 0;
    return { openCount, closedCount, winRatePct, avgR, openPnlInr, realizedPnlInr };
  }, [journal, marketVersion]);

  const regimeColor =
    regime.regimeLabel === 'Confirmed Uptrend'
      ? 'text-emerald-600 dark:text-emerald-400'
      : regime.regimeLabel === 'Market in Correction'
      ? 'text-red-600 dark:text-red-400'
      : 'text-amber-600 dark:text-amber-400';

  const visibleJournal = journal.filter(
    (tr) => journalFilter === 'ALL' || tr.status === journalFilter
  );

  return (
    <div className="space-y-6">
      {/* Header & Workspace Sub-Tabs */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Trade Setup Radar, Market Regime &amp; Execution Desk
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            O&apos;Neil distribution day tracking, NSE sector rotation, multi-setup signal confluence (Pocket Pivots, RS Blue-Dots, NR7 Squeezes, Pullbacks), and R-multiple position execution.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 self-start lg:self-auto">
          {(
            [
              ['top10', 'Top Buy Watchlist', Award],
              ['scanner', 'Multi-Setup Radar', Crosshair],
              ['regime', 'Market Regime & Sectors', ShieldAlert],
              ['journal', `Position Sizer & Journal (${journal.length})`, BookOpen],
            ] as const
          ).map(([id, label, Icon]) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                activeTab === id
                  ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Always-Visible Compact Market Posture & Exposure Banner */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">NIFTY 50 Market Regime</div>
          <div className={`text-base font-bold mt-1 ${regimeColor}`}>{regime.regimeLabel}</div>
          <div className="text-[11px] font-mono text-slate-500 mt-1 tabular-nums">
            {regime.nifty50Close.toLocaleString('en-IN', { maximumFractionDigits: 1 })} ·{' '}
            {regime.nifty50Above50Sma ? '> 50D' : '< 50D'} ·{' '}
            {regime.nifty50Above200Sma ? '> 200D' : '< 200D'}
          </div>
        </div>

        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">Suggested Equity Exposure</div>
          <div className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
            {regime.recommendedExposurePct}%
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            {100 - regime.recommendedExposurePct}% Cash / LiquidBees
          </div>
        </div>

        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">25D Distribution Days</div>
          <div
            className={`text-2xl font-bold font-mono tabular-nums mt-0.5 ${
              regime.distributionDays25 >= 5
                ? 'text-red-600 dark:text-red-400'
                : regime.distributionDays25 >= 3
                ? 'text-amber-600 dark:text-amber-400'
                : 'text-emerald-600 dark:text-emerald-400'
            }`}
          >
            {regime.distributionDays25}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            {regime.distributionDays25 <= 2
              ? 'Institutional Accumulation'
              : regime.distributionDays25 <= 4
              ? 'Caution · Tighten Stops'
              : 'Heavy Supply Warning'}
          </div>
        </div>

        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">Internal Breadth (&gt;50D / &gt;200D)</div>
          <div className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
            {regime.pctAbove50Sma}%{' '}
            <span className="text-sm font-normal text-slate-400">/ {regime.pctAbove200Sma}%</span>
          </div>
          <div className="text-[11px] font-mono text-slate-500 mt-0.5">
            Stage 2: {regime.stageCounts[2]} · 52W H/L: {regime.new52WHighs}/{regime.new52WLows}
          </div>
        </div>

        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">Active Institutional Signals</div>
          <div className="text-2xl font-bold font-mono tabular-nums text-blue-600 dark:text-blue-400 mt-0.5">
            {regime.pocketPivotCount + regime.rsBlueDotCount + regime.squeezeCount}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            {regime.pocketPivotCount} PP · {regime.rsBlueDotCount} RS-Dot · {regime.squeezeCount} NR7
          </div>
        </div>
      </div>

      {/* ====================================================================
          TAB 0: TOP BUY WATCHLIST
          ==================================================================== */}
      {activeTab === 'top10' && (
        <TopBuyWatchlistPanel
          stocks={INDIAN_STOCKS}
          marketVersion={marketVersion}
          regimeLabel={regime.regimeLabel}
          recommendedExposurePct={regime.recommendedExposurePct}
          onInspectStock={onInspectStock}
        />
      )}

      {/* ====================================================================
          TAB 1: MULTI-SETUP INSTITUTIONAL TRADE RADAR
          ==================================================================== */}
      {activeTab === 'scanner' && (
        <div className="space-y-4">
          {/* Interactive Setup Filter Bar */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 space-y-3">
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                onClick={() => setSetupFilter('ALL')}
                className={`px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap ${
                  setupFilter === 'ALL'
                    ? 'border-blue-600 bg-blue-600 text-white'
                    : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                All Setups ({radarRows.length})
              </button>
              {ALL_SETUP_TAGS.map((tag) => {
                const count = radarRows.filter((r) => r.setups.includes(tag)).length;
                return (
                  <button
                    key={tag}
                    onClick={() => setSetupFilter(tag)}
                    className={`px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap ${
                      setupFilter === tag
                        ? 'border-blue-600 bg-blue-600 text-white'
                        : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                    }`}
                  >
                    {SETUP_LABELS[tag]} ({count})
                  </button>
                );
              })}
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-1 text-xs">
              <div className="relative flex-1 min-w-[180px] max-w-xs">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter symbol or company..."
                  className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-xs"
                />
              </div>

              <select
                value={sectorFilter}
                onChange={(e) => setSectorFilter(e.target.value)}
                className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-xs"
              >
                <option value="ALL">All Sectors</option>
                {sectorsList.map((sec) => (
                  <option key={sec} value={sec}>
                    {sec}
                  </option>
                ))}
              </select>

              <select
                value={sortKey}
                onChange={(e) => setSortKey(e.target.value as typeof sortKey)}
                className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-xs"
              >
                <option value="conviction">Sort: Conviction Score</option>
                <option value="rs">Sort: RS Rating</option>
                <option value="adr">Sort: ADR% (20D)</option>
                <option value="vol">Sort: Volume Ratio 50D</option>
                <option value="dist50">Sort: Tightest to 50-SMA</option>
              </select>

              <label className="inline-flex items-center gap-2 text-slate-600 dark:text-slate-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={hideExtended}
                  onChange={(e) => setHideExtended(e.target.checked)}
                  className="rounded border-slate-300 dark:border-slate-700"
                />
                Hide Extended (&gt;3.5 ATR from 50D)
              </label>

              <div className="flex items-center gap-2 font-mono text-[11px] text-slate-600 dark:text-slate-400">
                <span>Min Score: {minConviction}</span>
                <input
                  type="range"
                  min={0}
                  max={85}
                  step={5}
                  value={minConviction}
                  onChange={(e) => setMinConviction(Number(e.target.value))}
                  className="w-20 accent-blue-600"
                />
              </div>

              <div className="flex items-center gap-2 font-mono text-[11px] text-slate-600 dark:text-slate-400">
                <span>Min ADR: {minAdrPct}%</span>
                <input
                  type="range"
                  min={0}
                  max={5}
                  step={0.5}
                  value={minAdrPct}
                  onChange={(e) => setMinAdrPct(Number(e.target.value))}
                  className="w-20 accent-blue-600"
                />
              </div>
            </div>
          </div>

          {/* Setup Results Table */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-900 dark:text-slate-100">
                Actionable Trade Identification Queue ({filteredRadar.length} NSE Stocks)
              </span>
              <span className="text-slate-500">
                Click any ticker to open Daily/Weekly Candlestick chart · Click Size to build risk ticket
              </span>
            </div>

            {filteredRadar.length === 0 ? (
              <div className="p-10 text-center text-xs text-slate-500 space-y-2">
                <div>No NSE stocks match the current setup &amp; conviction filters.</div>
                <button
                  onClick={() => {
                    setSetupFilter('ALL');
                    setSectorFilter('ALL');
                    setHideExtended(false);
                    setMinConviction(0);
                    setMinAdrPct(0);
                    setSearchQuery('');
                  }}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  Reset Filters
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                    <tr>
                      <th className="py-2.5 px-4">Ticker / Sector</th>
                      <th className="py-2.5 px-3 text-right">LTP / 1D</th>
                      <th className="py-2.5 px-3 text-right">Score</th>
                      <th className="py-2.5 px-3">Primary Setup &amp; Signals</th>
                      <th className="py-2.5 px-3 text-right">RS / Stage</th>
                      <th className="py-2.5 px-3 text-right">ADR% / Vol</th>
                      <th className="py-2.5 px-3 text-right">Ext vs 50D</th>
                      <th className="py-2.5 px-3 text-right">Trigger / Stop</th>
                      <th className="py-2.5 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                    {filteredRadar.map((r) => (
                      <tr
                        key={r.ticker}
                        className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                      >
                        <td className="py-2.5 px-4">
                          <button
                            onClick={() => onInspectStock(r.ticker)}
                            className="text-left group"
                          >
                            <div className="font-mono font-bold text-slate-900 dark:text-slate-100 group-hover:text-blue-500">
                              {r.ticker}
                            </div>
                            <div className="text-[11px] text-slate-500 truncate max-w-[160px]">
                              {r.sector} · {r.capBucket}
                            </div>
                          </button>
                        </td>

                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          <div className="font-semibold text-slate-900 dark:text-slate-100">
                            {formatINR(r.close)}
                          </div>
                          <div
                            className={`text-[11px] ${
                              r.dailyChangePct >= 0
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-red-600 dark:text-red-400'
                            }`}
                          >
                            {formatPct(r.dailyChangePct)}
                          </div>
                        </td>

                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          <div
                            className={`text-sm font-bold ${
                              r.convictionScore >= 75
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : r.convictionScore >= 55
                                ? 'text-blue-600 dark:text-blue-400'
                                : 'text-slate-500'
                            }`}
                          >
                            {r.convictionScore}
                          </div>
                          <div className="text-[10px] text-slate-500">T {r.templatePassed}/8</div>
                        </td>

                        <td className="py-2.5 px-3 max-w-[260px]">
                          <div className="font-semibold text-slate-900 dark:text-slate-100">
                            {r.primarySetup}
                          </div>
                          <div className="text-[11px] text-slate-500 truncate">
                            {r.setups.length > 0
                              ? r.setups.map((s) => SETUP_LABELS[s]).join(' · ')
                              : 'No active trigger'}
                          </div>
                        </td>

                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          <div className="font-semibold">RS {r.rsRating}</div>
                          <div className="text-[11px] text-slate-500">
                            S{r.stage} {r.weeklyStage2 ? '· W-S2' : ''}
                          </div>
                        </td>

                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          <div>{r.adrPct20.toFixed(1)}%</div>
                          <div className="text-[11px] text-slate-500">{r.volRatio50D.toFixed(1)}× vol</div>
                        </td>

                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          <div
                            className={
                              r.isExtended
                                ? 'font-semibold text-amber-600 dark:text-amber-400'
                                : 'text-slate-700 dark:text-slate-300'
                            }
                          >
                            {r.distFrom50SmaAtrs >= 0 ? '+' : ''}
                            {r.distFrom50SmaAtrs.toFixed(1)} ATR
                          </div>
                          <div className="text-[11px] text-slate-500">
                            {r.isExtended ? 'Extended' : `${formatPct(r.distFrom50SmaPct)}`}
                          </div>
                        </td>

                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          <div className="text-slate-900 dark:text-slate-100">
                            {formatINR(r.entryTriggerInr)}
                          </div>
                          <div className="text-[11px] text-red-600 dark:text-red-400">
                            SL {formatINR(r.stopLossInr)} (-{r.stopDistancePct.toFixed(1)}%)
                          </div>
                        </td>

                        <td className="py-2.5 px-4 text-right whitespace-nowrap">
                          <div className="inline-flex items-center gap-1.5">
                            <button
                              onClick={() => onInspectStock(r.ticker)}
                              className="p-1.5 rounded-md border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-blue-500"
                              title="Open Candlestick Chart"
                            >
                              <LineChart className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => loadIntoTicket(r)}
                              className="px-2.5 py-1 text-[11px] font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700"
                            >
                              Size
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ====================================================================
          TAB 2: MARKET REGIME, BREADTH & SECTOR ROTATION MATRIX
          ==================================================================== */}
      {activeTab === 'regime' && (
        <div className="space-y-6">
          {/* Breadth & Distribution Day Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
              <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                NSE Internal Breadth &amp; Stage Distribution
              </div>

              {[
                { label: 'Stocks Above 20-Day EMA (Short-Term)', pct: regime.pctAbove20Ema },
                { label: 'Stocks Above 50-Day SMA (Intermediate)', pct: regime.pctAbove50Sma },
                { label: 'Stocks Above 200-Day SMA (Secular)', pct: regime.pctAbove200Sma },
              ].map((b) => (
                <div key={b.label} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-600 dark:text-slate-400">{b.label}</span>
                    <span className="font-mono font-bold tabular-nums">{b.pct}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        b.pct >= 60
                          ? 'bg-emerald-500'
                          : b.pct >= 40
                          ? 'bg-amber-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${b.pct}%` }}
                    />
                  </div>
                </div>
              ))}

              <div className="pt-3 border-t border-slate-200 dark:border-slate-800 grid grid-cols-4 gap-2 text-center font-mono">
                {([1, 2, 3, 4] as const).map((st) => (
                  <div key={st} className="p-2 rounded-lg bg-slate-50 dark:bg-slate-900">
                    <div className="text-[11px] font-sans text-slate-500">Stage {st}</div>
                    <div
                      className={`text-lg font-bold tabular-nums ${
                        st === 2
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : st === 4
                          ? 'text-red-600 dark:text-red-400'
                          : 'text-slate-900 dark:text-slate-100'
                      }`}
                    >
                      {regime.stageCounts[st]}
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-1.5">
                <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  Active NIFTY 50 Distribution Dates (Last 25 Sessions)
                </div>
                {regime.distributionDates.length === 0 ? (
                  <div className="text-xs text-emerald-600 dark:text-emerald-400">
                    Zero active distribution days on NIFTY 50 — clean institutional accumulation.
                  </div>
                ) : (
                  <div className="text-xs font-mono text-slate-600 dark:text-slate-400">
                    {regime.distributionDates.join(' · ')}
                  </div>
                )}
              </div>
            </div>

            {/* Indian Sector Rotation Matrix (RRG Quadrants) */}
            <div className="lg:col-span-7 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  NSE Sector Rotation &amp; Relative Strength Matrix (vs NIFTY 500)
                </div>
                <span className="text-[11px] text-slate-500">Sorted by 3M Alpha</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                    <tr>
                      <th className="py-2.5 px-4">Sector</th>
                      <th className="py-2.5 px-3">Quadrant</th>
                      <th className="py-2.5 px-3 text-right">1W</th>
                      <th className="py-2.5 px-3 text-right">1M</th>
                      <th className="py-2.5 px-3 text-right">3M vs N500</th>
                      <th className="py-2.5 px-3 text-right">% S2</th>
                      <th className="py-2.5 px-4">Top RS Leaders</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                    {regime.sectors.map((sec) => {
                      const qColor =
                        sec.quadrant === 'Leading'
                          ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                          : sec.quadrant === 'Improving'
                          ? 'text-blue-600 dark:text-blue-400 font-semibold'
                          : sec.quadrant === 'Weakening'
                          ? 'text-amber-600 dark:text-amber-400 font-semibold'
                          : 'text-red-600 dark:text-red-400 font-semibold';
                      return (
                        <tr
                          key={sec.sector}
                          className="hover:bg-slate-50 dark:hover:bg-slate-800/40"
                        >
                          <td className="py-2.5 px-4">
                            <button
                              onClick={() => {
                                setSectorFilter(sec.sector);
                                setActiveTab('scanner');
                              }}
                              className="text-left font-semibold text-slate-900 dark:text-slate-100 hover:text-blue-500"
                            >
                              {sec.sector}
                              <span className="text-[11px] font-normal text-slate-500 ml-1.5">
                                ({sec.stockCount})
                              </span>
                            </button>
                          </td>
                          <td className={`py-2.5 px-3 text-xs ${qColor}`}>{sec.quadrant}</td>
                          <td
                            className={`py-2.5 px-3 text-right font-mono tabular-nums ${
                              sec.ret1W >= 0
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-red-600 dark:text-red-400'
                            }`}
                          >
                            {formatPct(sec.ret1W)}
                          </td>
                          <td
                            className={`py-2.5 px-3 text-right font-mono tabular-nums ${
                              sec.ret1M >= 0
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-red-600 dark:text-red-400'
                            }`}
                          >
                            {formatPct(sec.ret1M)}
                          </td>
                          <td
                            className={`py-2.5 px-3 text-right font-mono tabular-nums font-semibold ${
                              sec.rsVsNifty3M >= 0
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-red-600 dark:text-red-400'
                            }`}
                          >
                            {formatPct(sec.rsVsNifty3M)}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                            {sec.pctStage2}%
                          </td>
                          <td className="py-2.5 px-4">
                            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 font-mono text-[11px]">
                              {sec.topLeaders.map((l) => (
                                <button
                                  key={l.ticker}
                                  onClick={() => onInspectStock(l.ticker)}
                                  className="text-blue-600 dark:text-blue-400 hover:underline"
                                  title={`Open ${l.ticker} Candlestick Chart (RS ${l.rsRating})`}
                                >
                                  {l.ticker}
                                </button>
                              ))}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ====================================================================
          TAB 3: RISK-DEFINED POSITION SIZER & PERSISTENT TRADE JOURNAL
          ==================================================================== */}
      {activeTab === 'journal' && (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          {/* Left: Risk-Defined Position Sizer Ticket */}
          <div className="xl:col-span-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <Calculator className="w-4 h-4 text-blue-500" />
                <span>Risk-Defined Position Sizer (NSE Delivery)</span>
              </div>
              {selectedDiag && (
                <button
                  onClick={() => onInspectStock(selectedDiag.ticker)}
                  className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
                >
                  Open Chart <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {journalStatusMsg && (
              <div className="flex items-center gap-2 px-3 py-2 text-xs rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
                <Check className="w-4 h-4 shrink-0" />
                <span>{journalStatusMsg}</span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 text-xs">
              <label className="space-y-1 col-span-2">
                <span className="text-slate-500">NSE Symbol</span>
                <select
                  value={ticketTicker}
                  onChange={(e) => {
                    const next = radarRows.find((r) => r.ticker === e.target.value);
                    setTicketTicker(e.target.value);
                    if (next) {
                      setCustomEntry(String(next.entryTriggerInr));
                      setCustomStop(String(next.stopLossInr));
                    }
                  }}
                  className="w-full px-3 py-2 font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                >
                  {radarRows.map((r) => (
                    <option key={r.ticker} value={r.ticker}>
                      {r.ticker} — {r.primarySetup} (Score {r.convictionScore})
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-1">
                <span className="text-slate-500">Account Capital (₹)</span>
                <input
                  type="number"
                  min={50000}
                  step={50000}
                  value={accountCapitalInr}
                  onChange={(e) => setAccountCapitalInr(Math.max(0, Number(e.target.value)))}
                  className="w-full px-3 py-2 font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
              </label>

              <label className="space-y-1">
                <span className="text-slate-500">Risk Per Trade (%)</span>
                <input
                  type="number"
                  min={0.25}
                  max={5}
                  step={0.25}
                  value={riskPerTradePct}
                  onChange={(e) => setRiskPerTradePct(Math.max(0.1, Number(e.target.value)))}
                  className="w-full px-3 py-2 font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
              </label>

              <label className="space-y-1">
                <span className="text-slate-500">Entry Trigger (₹)</span>
                <input
                  type="number"
                  step={0.5}
                  value={customEntry || selectedDiag?.entryTriggerInr || ''}
                  onChange={(e) => setCustomEntry(e.target.value)}
                  className="w-full px-3 py-2 font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
              </label>

              <label className="space-y-1">
                <span className="text-slate-500">Hard Stop-Loss (₹)</span>
                <input
                  type="number"
                  step={0.5}
                  value={customStop || selectedDiag?.stopLossInr || ''}
                  onChange={(e) => setCustomStop(e.target.value)}
                  className="w-full px-3 py-2 font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
              </label>
            </div>

            {/* Computed Sizing Outputs */}
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-3 font-mono tabular-nums text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="font-sans text-[11px] text-slate-500">Exact Share Quantity</div>
                  <div className="text-xl font-bold text-blue-600 dark:text-blue-400">
                    {shareQty.toLocaleString('en-IN')} sh
                  </div>
                </div>
                <div>
                  <div className="font-sans text-[11px] text-slate-500">Position Value / Alloc</div>
                  <div className="text-xl font-bold text-slate-900 dark:text-slate-100">
                    {formatINRCompact(positionValueInr)}
                  </div>
                  <div className="text-[11px] text-slate-500">{capitalAllocPct.toFixed(1)}% of equity</div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                <div>
                  <div className="font-sans text-[10px] text-slate-500">Stop Distance</div>
                  <div className="font-semibold text-red-600 dark:text-red-400">
                    -{stopPct.toFixed(2)}% ({formatINR(riskPerShare)})
                  </div>
                </div>
                <div>
                  <div className="font-sans text-[10px] text-slate-500">Max ₹ Risk</div>
                  <div className="font-semibold">{formatINR(shareQty * riskPerShare, 0)}</div>
                </div>
                <div>
                  <div className="font-sans text-[10px] text-slate-500">ATR(14)</div>
                  <div className="font-semibold">{formatINR(selectedDiag?.atr14 ?? 0)}</div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                <div>
                  <div className="font-sans text-[10px] text-slate-500">1R Milestone</div>
                  <div className="font-semibold text-emerald-600 dark:text-emerald-400">
                    {formatINR(r1Price)}
                  </div>
                </div>
                <div>
                  <div className="font-sans text-[10px] text-slate-500">2R Milestone</div>
                  <div className="font-semibold text-emerald-600 dark:text-emerald-400">
                    {formatINR(r2Price)}
                  </div>
                </div>
                <div>
                  <div className="font-sans text-[10px] text-slate-500">3R Milestone</div>
                  <div className="font-semibold text-emerald-600 dark:text-emerald-400">
                    {formatINR(r3Price)}
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-2 text-xs">
              <input
                type="text"
                value={tradeNotes}
                onChange={(e) => setTradeNotes(e.target.value)}
                placeholder="Execution thesis / catalyst note (optional)..."
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
              />
              <button
                onClick={handleLogTrade}
                disabled={shareQty <= 0}
                className="w-full inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50"
              >
                <Plus className="w-4 h-4" />
                Log Trade to Execution Journal
              </button>
            </div>
          </div>

          {/* Right: Persistent R-Multiple Trade Execution Journal */}
          <div className="xl:col-span-7 space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono tabular-nums">
              <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-3.5">
                <div className="font-sans text-slate-500">Open / Closed</div>
                <div className="text-lg font-bold mt-0.5">
                  {journalStats.openCount} / {journalStats.closedCount}
                </div>
              </div>
              <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-3.5">
                <div className="font-sans text-slate-500">Closed Win Rate</div>
                <div className="text-lg font-bold mt-0.5">{journalStats.winRatePct.toFixed(1)}%</div>
              </div>
              <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-3.5">
                <div className="font-sans text-slate-500">Avg Closed R</div>
                <div
                  className={`text-lg font-bold mt-0.5 ${
                    journalStats.avgR >= 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {journalStats.avgR >= 0 ? '+' : ''}
                  {journalStats.avgR.toFixed(2)}R
                </div>
              </div>
              <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-3.5">
                <div className="font-sans text-slate-500">Total MTM + Realized</div>
                <div
                  className={`text-lg font-bold mt-0.5 ${
                    journalStats.openPnlInr + journalStats.realizedPnlInr >= 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {formatINR(journalStats.openPnlInr + journalStats.realizedPnlInr, 0)}
                </div>
              </div>
            </div>

            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-2">
                <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                  Trade Execution Ledger (Live NSE Mark-to-Market)
                </span>
                <div className="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 text-[11px]">
                  {(['ALL', 'OPEN', 'CLOSED'] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setJournalFilter(f)}
                      className={`px-2 py-0.5 rounded font-medium ${
                        journalFilter === f
                          ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100'
                          : 'text-slate-500'
                      }`}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>

              {visibleJournal.length === 0 ? (
                <div className="p-10 text-center text-xs text-slate-500 space-y-1">
                  <div className="font-semibold text-slate-700 dark:text-slate-300">
                    No trades logged yet
                  </div>
                  <div>
                    Use the Risk-Defined Position Sizer on the left (or click Size on any Trade Radar setup) to log your first NSE execution.
                  </div>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                      <tr>
                        <th className="py-2.5 px-4">Ticker / Setup</th>
                        <th className="py-2.5 px-3 text-right">Qty</th>
                        <th className="py-2.5 px-3 text-right">Entry / Stop</th>
                        <th className="py-2.5 px-3 text-right">Current / Exit</th>
                        <th className="py-2.5 px-3 text-right">P&amp;L (₹ / R)</th>
                        <th className="py-2.5 px-4 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                      {visibleJournal.map((tr) => {
                        const liveLtp = STOCK_BY_TICKER[tr.ticker]?.latestClose ?? tr.entryPrice;
                        const markPrice = tr.status === 'CLOSED' ? (tr.exitPrice ?? liveLtp) : liveLtp;
                        const pnlInr = (markPrice - tr.entryPrice) * tr.shares;
                        const rUnit = Math.max(0.05, tr.entryPrice - tr.stopLoss);
                        const rMult = (markPrice - tr.entryPrice) / rUnit;
                        return (
                          <tr
                            key={tr.id}
                            className="hover:bg-slate-50 dark:hover:bg-slate-800/40"
                          >
                            <td className="py-2.5 px-4">
                              <button
                                onClick={() => onInspectStock(tr.ticker)}
                                className="font-mono font-bold text-slate-900 dark:text-slate-100 hover:text-blue-500"
                              >
                                {tr.ticker}
                              </button>
                              <div className="text-[11px] text-slate-500 truncate max-w-[180px]">
                                {tr.status} · {tr.entryDate} · {tr.setup}
                              </div>
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                              {tr.shares}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                              <div>{formatINR(tr.entryPrice)}</div>
                              <div className="text-[11px] text-red-500">
                                SL {formatINR(tr.stopLoss)}
                              </div>
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                              {formatINR(markPrice)}
                            </td>
                            <td
                              className={`py-2.5 px-3 text-right font-mono tabular-nums font-semibold ${
                                pnlInr >= 0
                                  ? 'text-emerald-600 dark:text-emerald-400'
                                  : 'text-red-600 dark:text-red-400'
                              }`}
                            >
                              <div>{formatINR(pnlInr, 0)}</div>
                              <div className="text-[11px]">
                                {rMult >= 0 ? '+' : ''}
                                {rMult.toFixed(2)}R
                              </div>
                            </td>
                            <td className="py-2.5 px-4 text-right whitespace-nowrap">
                              <div className="inline-flex items-center gap-2">
                                {tr.status === 'OPEN' && (
                                  <button
                                    onClick={() => handleCloseTradeAtLtp(tr.id)}
                                    className="px-2 py-1 text-[11px] font-medium rounded border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800"
                                  >
                                    Close @ LTP
                                  </button>
                                )}
                                <button
                                  onClick={() => handleDeleteTrade(tr.id)}
                                  className="p-1 text-slate-400 hover:text-red-500"
                                  title="Delete entry"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
