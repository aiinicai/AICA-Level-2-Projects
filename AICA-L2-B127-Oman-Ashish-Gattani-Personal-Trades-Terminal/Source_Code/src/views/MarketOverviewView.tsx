import React, { useMemo, useState } from 'react';
import {
  ArrowRight,
  FileArchive,
  LineChart,
  Plug,
  Star,
  TrendingUp,
} from 'lucide-react';
import { Line, LineChart as RechartsLineChart, ResponsiveContainer } from 'recharts';
import { IndianTickerSearchInput } from '../components/IndianTickerSearchInput';
import { StockChartPanel } from '../components/StockChartPanel';
import { Nifty500MarketHeatmap } from '../components/Nifty500MarketHeatmap';
import { TopBuyWatchlistPanel } from '../components/TopBuyWatchlistPanel';
import { useAppData } from '../context/AppDataContext';
import { BENCHMARKS, INDIAN_STOCKS, STOCK_BY_TICKER } from '../data/indianMarketData';
import {
  DEFAULT_TREND_THRESHOLDS,
  run52WeekBreakoutScanner,
  runMinerviniAnalysis,
} from '../engine/analyticsEngine';
import { computePortfolioSummary } from '../engine/portfolioRiskEngine';
import { computeTrendingSectorsAndSubsectors } from '../engine/sectorTrendEngine';
import { computeMarketRegime, runTradeSetupRadar } from '../engine/tradeRadarEngine';
import { ActiveWorkspace } from '../types/market';
import { formatINR, formatINRCompact, formatPct } from '../utils/formatters';

interface MarketOverviewViewProps {
  onNavigate: (ws: ActiveWorkspace) => void;
  onInspectStock: (ticker: string) => void;
  onOpenConnectors: () => void;
}

export const MarketOverviewView: React.FC<MarketOverviewViewProps> = ({
  onNavigate,
  onInspectStock,
  onOpenConnectors,
}) => {
  const {
    watchlist,
    toggleWatchlist,
    holdings,
    connectors,
    updateConnectors,
    marketVersion,
  } = useAppData();

  const [chartTarget, setChartTarget] = useState<'NIFTY50' | 'NIFTY500' | 'SENSEX' | string>('NIFTY50');

  const minerviniAll = useMemo(
    () => runMinerviniAnalysis(INDIAN_STOCKS, DEFAULT_TREND_THRESHOLDS),
    [marketVersion]
  );
  const minerviniByTicker = useMemo(
    () => Object.fromEntries(minerviniAll.map((m) => [m.stock.ticker, m])),
    [minerviniAll]
  );
  const radarRows = useMemo(() => runTradeSetupRadar(INDIAN_STOCKS), [marketVersion]);
  const regime = useMemo(
    () => computeMarketRegime(INDIAN_STOCKS, radarRows),
    [radarRows, marketVersion]
  );
  const sectorPulse = useMemo(() => {
    void marketVersion;
    const { sectors, subsectors } = computeTrendingSectorsAndSubsectors(INDIAN_STOCKS, 'balanced');
    return {
      topSector: sectors[0] ?? null,
      topSubsector: subsectors[0] ?? null,
    };
  }, [marketVersion]);

  const freshBreakouts = useMemo(
    () =>
      run52WeekBreakoutScanner(INDIAN_STOCKS, {
        name: 'Default 6M',
        lookbackMonths: 6,
        priceBasis: 'close',
        minVolumeRatio: 1.5,
        minPriceInr: 50,
        minTurnoverCr: 25,
        capBucket: 'All',
        sector: 'All',
        scheduleEnabled: true,
        scheduleTimeIst: '15:35 IST',
      }),
    [marketVersion]
  );

  const portfolioSummary = useMemo(
    () => computePortfolioSummary(holdings),
    [holdings, marketVersion]
  );

  const topDividendStock = useMemo(
    () =>
      [...INDIAN_STOCKS].sort(
        (a, b) => b.dividend.dividendYieldPct - a.dividend.dividendYieldPct
      )[0],
    [marketVersion]
  );

  const templateLeadersCount = minerviniAll.filter((m) => m.allPassed).length;
  const vcpBreakoutCount = minerviniAll.filter((m) => m.vcp.isPivotBreakout).length;

  const watchedRows = useMemo(
    () =>
      watchlist
        .map((t) => STOCK_BY_TICKER[t])
        .filter((s): s is NonNullable<typeof s> => Boolean(s)),
    [watchlist, marketVersion]
  );

  const benchmarksList = [BENCHMARKS.NIFTY50, BENCHMARKS.NIFTY500, BENCHMARKS.SENSEX];
  const activeBenchmark =
    chartTarget === 'NIFTY50' || chartTarget === 'NIFTY500' || chartTarget === 'SENSEX'
      ? BENCHMARKS[chartTarget]
      : null;
  const activeStockForChart = !activeBenchmark ? STOCK_BY_TICKER[chartTarget] : undefined;

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Indian Equity Command Center
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            NSE & BSE breadth, benchmark indices, SEPA leaders, 52-week high breakouts, and your synced watchlist.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 self-start md:self-auto">
          <IndianTickerSearchInput
            onSelectTicker={(ticker) => onInspectStock(ticker)}
            placeholder="Analyze any NSE / BSE stock (MARUTI, SBIN, ZOMATO)..."
            className="w-72"
          />
          <button
            onClick={onOpenConnectors}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
          >
            <Plug className="w-3.5 h-3.5 text-blue-500" />
            Connectors: NSE · BSE · {connectors.brokerConnectorName}
          </button>
        </div>
      </div>

      {/* Benchmark Indices Row: NIFTY 50, NIFTY 500, SENSEX */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {benchmarksList.map((bm) => {
          const spark = bm.bars.slice(-60).map((b) => ({ c: b.close }));
          const positive = bm.changePct >= 0;
          const yrAgo = bm.bars[Math.max(0, bm.bars.length - 252)].close;
          const yrRet = ((bm.latestClose - yrAgo) / yrAgo) * 100;
          return (
            <button
              key={bm.id}
              onClick={() => setChartTarget(bm.id)}
              className={`text-left border rounded-xl p-4 flex items-center justify-between gap-4 transition-colors ${
                chartTarget === bm.id
                  ? 'border-blue-500 bg-white dark:bg-[#111827]'
                  : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] hover:border-slate-400 dark:hover:border-slate-700'
              }`}
            >
              <div className="space-y-1">
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  {bm.exchange} Benchmark · {bm.name}
                </div>
                <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100">
                  {bm.latestClose.toLocaleString('en-IN', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </div>
                <div className="flex items-center gap-2 text-xs font-mono tabular-nums">
                  <span
                    className={
                      positive
                        ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                        : 'text-red-600 dark:text-red-400 font-semibold'
                    }
                  >
                    {formatPct(bm.changePct)} 1D
                  </span>
                  <span className="text-slate-400">·</span>
                  <span className="text-slate-500">{formatPct(yrRet)} 1Y</span>
                </div>
              </div>
              <div className="w-28 h-12 shrink-0">
                <ResponsiveContainer>
                  <RechartsLineChart data={spark}>
                    <Line
                      type="monotone"
                      dataKey="c"
                      stroke={positive ? '#10b981' : '#ef4444'}
                      strokeWidth={1.8}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </RechartsLineChart>
                </ResponsiveContainer>
              </div>
            </button>
          );
        })}
      </div>

      {/* Live Market Regime, Distribution Days & Equity Exposure Strip */}
      <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs">
          <div>
            <div className="text-[11px] text-slate-500">Market Regime Posture</div>
            <div
              className={`font-bold text-sm ${
                regime.regimeLabel === 'Confirmed Uptrend'
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : regime.regimeLabel === 'Market in Correction'
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-amber-600 dark:text-amber-400'
              }`}
            >
              {regime.regimeLabel}
            </div>
          </div>
          <div className="font-mono tabular-nums">
            <div className="font-sans text-[11px] text-slate-500">Suggested Exposure</div>
            <div className="font-bold text-sm text-slate-900 dark:text-slate-100">
              {regime.recommendedExposurePct}% Equity
            </div>
          </div>
          <div className="font-mono tabular-nums">
            <div className="font-sans text-[11px] text-slate-500">25D Distribution Days</div>
            <div className="font-bold text-sm text-slate-900 dark:text-slate-100">
              {regime.distributionDays25}
            </div>
          </div>
          <div className="font-mono tabular-nums">
            <div className="font-sans text-[11px] text-slate-500">Breadth &gt;50D / Stage 2</div>
            <div className="font-bold text-sm text-slate-900 dark:text-slate-100">
              {regime.pctAbove50Sma}% · {regime.stageCounts[2]} stocks
            </div>
          </div>
          <div className="font-mono tabular-nums">
            <div className="font-sans text-[11px] text-slate-500">Active Signals ({INDIAN_STOCKS.length} NSE)</div>
            <div className="font-bold text-sm text-blue-600 dark:text-blue-400">
              {regime.pocketPivotCount} PP · {regime.rsBlueDotCount} RS-Dot · {regime.squeezeCount} NR7
            </div>
          </div>
          {sectorPulse.topSector && (
            <button
              onClick={() => onNavigate('sectors')}
              className="text-left group"
              title="Open Trending Sectors & Subsectors technical scoreboard"
            >
              <div className="font-sans text-[11px] text-slate-500 group-hover:text-blue-500 transition-colors">
                #1 Trending Sector · Subsector
              </div>
              <div className="font-bold text-sm text-emerald-600 dark:text-emerald-400 truncate max-w-[260px]">
                {sectorPulse.topSector.name} ({sectorPulse.topSector.compositeScore})
                {sectorPulse.topSubsector ? ` · ${sectorPulse.topSubsector.name}` : ''}
              </div>
            </button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2 self-start lg:self-auto shrink-0">
          <button
            onClick={() => onNavigate('sectors')}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 hover:border-blue-500/60 hover:text-blue-600 dark:hover:text-blue-400 whitespace-nowrap"
          >
            Trending Sectors
          </button>
          <button
            onClick={() => onNavigate('radar')}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 whitespace-nowrap"
          >
            Open Trade Radar
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Top Buy Watchlist */}
      <TopBuyWatchlistPanel
        stocks={INDIAN_STOCKS}
        marketVersion={marketVersion}
        regimeLabel={regime.regimeLabel}
        recommendedExposurePct={regime.recommendedExposurePct}
        onInspectStock={onInspectStock}
      />

      {/* Live Interactive Candlestick & Technical Chart Panel */}
      <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="text-xs font-bold text-slate-900 dark:text-slate-100">
            Interactive Live Chart —{' '}
            <span className="font-mono text-blue-600 dark:text-blue-400">
              {activeBenchmark ? activeBenchmark.name : activeStockForChart?.ticker}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-mono">
            {(['NIFTY50', 'NIFTY500', 'SENSEX', 'RELIANCE', 'HDFCBANK', 'TRENT', 'HAL', 'M&M'] as const).map(
              (sym) => (
                <button
                  key={sym}
                  onClick={() => setChartTarget(sym)}
                  className={`px-2 py-1 rounded border transition-colors ${
                    chartTarget === sym
                      ? 'border-blue-600 bg-blue-600 text-white'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-400 dark:hover:border-slate-600'
                  }`}
                >
                  {sym}
                </button>
              )
            )}
          </div>
        </div>

        <StockChartPanel
          stock={activeStockForChart}
          barsOverride={activeBenchmark ? activeBenchmark.bars : undefined}
          symbolLabel={activeBenchmark ? activeBenchmark.name : activeStockForChart?.ticker}
          height={340}
          defaultStyle="volume_candles"
          defaultRange="6M"
        />
      </div>

      {/* D3 NIFTY 500 Sector-Based Market Heatmap */}
      <Nifty500MarketHeatmap
        stocks={INDIAN_STOCKS}
        marketVersion={marketVersion}
        onSelectTicker={onInspectStock}
      />

      {/* Live Three Indian Market Connectors Strip — Always Visible */}
      <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-slate-100">
            <Plug className="w-4 h-4 text-blue-500" />
            <span>Active Indian Market Connectors (3)</span>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <button
              onClick={() => onNavigate('closingbell')}
              className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 font-medium hover:underline"
            >
              <FileArchive className="w-3.5 h-3.5" />
              Open Closing Bell Lab (21 Bhavcopy Metrics)
            </button>
            <button
              onClick={() => onNavigate('connectors')}
              className="text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 underline"
            >
              Manage Feeds &amp; NSE Calendar
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          {/* Connector 1 */}
          <div className="p-3 rounded-lg border border-slate-200/80 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                1. NSE India Equity &amp; Bhavcopy ZIP
              </div>
              <div className="text-[11px] text-slate-500 truncate">
                NIFTY 50 / 500 · PR &amp; UDiFF Auto-Ingest
              </div>
            </div>
            <button
              onClick={() =>
                updateConnectors({
                  ...connectors,
                  nseConnectorEnabled: !connectors.nseConnectorEnabled,
                })
              }
              className={`px-2.5 py-1 rounded-md font-mono text-[11px] font-semibold shrink-0 ${
                connectors.nseConnectorEnabled
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
              }`}
            >
              {connectors.nseConnectorEnabled ? 'Connected' : 'Paused'}
            </button>
          </div>

          {/* Connector 2 */}
          <div className="p-3 rounded-lg border border-slate-200/80 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                2. BSE Sensex &amp; XBRL Filings
              </div>
              <div className="text-[11px] text-slate-500 truncate">
                SENSEX · EPS / Shareholding / Dividends
              </div>
            </div>
            <button
              onClick={() =>
                updateConnectors({
                  ...connectors,
                  bseConnectorEnabled: !connectors.bseConnectorEnabled,
                })
              }
              className={`px-2.5 py-1 rounded-md font-mono text-[11px] font-semibold shrink-0 ${
                connectors.bseConnectorEnabled
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
              }`}
            >
              {connectors.bseConnectorEnabled ? 'Connected' : 'Paused'}
            </button>
          </div>

          {/* Connector 3 */}
          <div className="p-3 rounded-lg border border-slate-200/80 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                3. Indian Execution Broker Bridge
              </div>
              <div className="text-[11px] text-slate-500 truncate">
                Demat Holdings &amp; Rebalance Orders
              </div>
            </div>
            <select
              value={connectors.brokerConnectorName}
              onChange={(e) =>
                updateConnectors({
                  ...connectors,
                  brokerConnectorName: e.target.value as typeof connectors.brokerConnectorName,
                })
              }
              className="px-2 py-1 text-[11px] font-mono font-semibold rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 shrink-0"
            >
              <option value="Zerodha Kite">Zerodha Kite</option>
              <option value="Dhan HQ">Dhan HQ</option>
              <option value="Upstox Pro">Upstox Pro</option>
              <option value="Disconnected">Disconnected</option>
            </select>
          </div>
        </div>
      </div>

      {/* 4-Column Quick Analytical Summary Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <button
          onClick={() => onNavigate('breakout')}
          className="text-left border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 hover:border-blue-500/50 transition-colors group"
        >
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Fresh 52W Breakouts (≥6M)</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </div>
          <div className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-1.5">
            {freshBreakouts.length}
          </div>
          <div className="text-xs text-slate-500 mt-1 truncate">
            Top: {freshBreakouts.slice(0, 3).map((b) => b.stock.ticker).join(', ') || 'None'}
          </div>
        </button>

        <button
          onClick={() => onNavigate('minervini')}
          className="text-left border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 hover:border-blue-500/50 transition-colors group"
        >
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Minervini 8/8 Template</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </div>
          <div className="text-2xl font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400 mt-1.5">
            {templateLeadersCount}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {vcpBreakoutCount} active VCP pivot breakouts
          </div>
        </button>

        <button
          onClick={() => onNavigate('portfolio')}
          className="text-left border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 hover:border-blue-500/50 transition-colors group"
        >
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Tracked Portfolio</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </div>
          <div className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-1.5">
            {formatINRCompact(portfolioSummary.totalMarketValueInr)}
          </div>
          <div className="text-xs font-mono text-emerald-600 dark:text-emerald-400 mt-1">
            {formatPct(portfolioSummary.totalUnrealizedPnlPct)} total P&L · β{' '}
            {portfolioSummary.portfolioBeta}
          </div>
        </button>

        <button
          onClick={() => onNavigate('fundamental')}
          className="text-left border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 hover:border-blue-500/50 transition-colors group"
        >
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>Dividend & FCF Lab</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </div>
          <div className="text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-1.5">
            {topDividendStock.dividend.dividendYieldPct.toFixed(2)}%
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Top trailing yield ({topDividendStock.ticker} ·{' '}
            {(
              topDividendStock.dividend.fcfPerShareInr /
              Math.max(0.01, topDividendStock.dividend.annualDpsInr)
            ).toFixed(2)}
            × FCF cover)
          </div>
        </button>
      </div>

      {/* Watchlist & Top SEPA Leaders Split */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        <div className="xl:col-span-8 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
              <Star className="w-4 h-4 text-amber-500" />
              <span>Your NSE Watchlist ({watchedRows.length})</span>
            </div>
            <span className="text-xs text-slate-500">Press / anywhere to search & add</span>
          </div>

          {watchedRows.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              Your watchlist is empty. Press <kbd className="font-mono px-1.5 py-0.5 border rounded">/</kbd> to search NSE stocks or add breakouts from the scanner.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                  <tr>
                    <th className="py-2.5 px-4">Ticker / Name</th>
                    <th className="py-2.5 px-3 text-right">LTP (₹)</th>
                    <th className="py-2.5 px-3 text-right">1D Chg</th>
                    <th className="py-2.5 px-3 text-right">RS Rank</th>
                    <th className="py-2.5 px-3">Stage / Template</th>
                    <th className="py-2.5 px-3 text-right">SEPA Score</th>
                    <th className="py-2.5 px-4 text-right">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                  {watchedRows.map((s) => {
                    const m = minerviniByTicker[s.ticker];
                    return (
                      <tr
                        key={s.ticker}
                        className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                      >
                        <td className="py-2.5 px-4">
                          <button
                            onClick={() => onInspectStock(s.ticker)}
                            className="text-left group"
                          >
                            <div className="font-mono font-semibold text-slate-900 dark:text-slate-100 group-hover:text-blue-500">
                              {s.ticker}
                            </div>
                            <div className="text-[11px] text-slate-500 truncate max-w-[170px]">
                              {s.name}
                            </div>
                          </button>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums font-medium">
                          {formatINR(s.latestClose)}
                        </td>
                        <td
                          className={`py-2.5 px-3 text-right font-mono tabular-nums font-semibold ${
                            s.dailyChangePct >= 0
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-red-600 dark:text-red-400'
                          }`}
                        >
                          {formatPct(s.dailyChangePct)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold">
                          {m?.rsRating ?? '—'}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[11px] text-slate-600 dark:text-slate-300">
                          S{m?.stage ?? '-'} · {m?.passedCount ?? 0}/8
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums font-bold text-blue-600 dark:text-blue-400">
                          {m?.minerviniScore ?? '—'}
                        </td>
                        <td className="py-2.5 px-4 text-right">
                          <div className="inline-flex items-center gap-2">
                            <button
                              onClick={() => onInspectStock(s.ticker)}
                              className="p-1.5 rounded border border-slate-200 dark:border-slate-700 hover:text-blue-500"
                              title="Open stock chart"
                            >
                              <LineChart className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => toggleWatchlist(s.ticker)}
                              className="text-[11px] text-slate-400 hover:text-red-500"
                            >
                              Remove
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

        {/* Right: Top Fresh Breakouts & VCP Leaders */}
        <div className="xl:col-span-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
              <TrendingUp className="w-4 h-4 text-emerald-500" />
              <span>Highest-Conviction SEPA Setups</span>
            </div>
            <button
              onClick={() => onNavigate('minervini')}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
            >
              View All
            </button>
          </div>

          <div className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
            {minerviniAll.slice(0, 6).map((m) => (
              <button
                key={m.stock.ticker}
                onClick={() => onInspectStock(m.stock.ticker)}
                className="w-full py-3 flex items-center justify-between gap-3 text-left hover:opacity-80 transition-opacity"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-900 dark:text-slate-100">
                      {m.stock.ticker}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      · RS {m.rsRating} · {m.vcp.tCount}T VCP
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 truncate mt-0.5">
                    {m.vcp.isPivotBreakout
                      ? `Pivot breakout on ${m.vcp.breakoutVolumeRatio}× volume`
                      : `Pivot ${formatINR(m.vcp.pivotPrice)} · Qtr EPS ${formatPct(m.stock.fundamentals.qtrEpsYoY)}`}
                  </div>
                </div>
                <div className="text-right font-mono tabular-nums shrink-0">
                  <div className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                    {m.minerviniScore}/100
                  </div>
                  <div className="text-[11px] text-slate-500">
                    {formatINR(m.stock.latestClose, 0)}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
