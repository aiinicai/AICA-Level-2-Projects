import React, { useEffect, useMemo, useState } from 'react';
import {
  ArrowUpRight,
  BellPlus,
  Check,
  Code2,
  Play,
  Plus,
  RefreshCw,
  Save,
  Trash2,
} from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { IndianTickerSearchInput } from '../components/IndianTickerSearchInput';
import { StockChartPanel } from '../components/StockChartPanel';
import { useAppData } from '../context/AppDataContext';
import { INDIAN_STOCKS, LiveQuotePayload, STOCK_BY_TICKER } from '../data/indianMarketData';
import {
  backtestCustomIndicator,
  evaluateCustomIndicator,
  INITIAL_CUSTOM_INDICATORS,
} from '../engine/customIndicatorEngine';
import { CustomIndicatorDefinition, IndianStock } from '../types/market';
import { formatINR, formatINRCompact, formatPct } from '../utils/formatters';

type SubTab = 'chart' | 'screener' | 'backtest';

interface CustomIndicatorsViewProps {
  onInspectStock: (ticker: string) => void;
}

function buildOnDemandStock(ticker: string, quote: LiveQuotePayload): IndianStock {
  const base = INDIAN_STOCKS[0];
  return {
    ...base,
    ticker,
    bseCode: '',
    isin: '',
    name: ticker,
    sector: 'NSE / BSE Equity',
    industry: 'Live Market Feed',
    marketCapCr: 0,
    bars: quote.bars,
    latestClose: quote.latestClose,
    prevClose: quote.prevClose,
    dailyChangePct: quote.dailyChangePct,
    avgDailyTurnoverCr: quote.avgDailyTurnoverCr,
  };
}

export const CustomIndicatorsView: React.FC<CustomIndicatorsViewProps> = ({ onInspectStock }) => {
  const {
    customIndicators,
    saveCustomIndicator,
    deleteCustomIndicator,
    watchlist,
    toggleWatchlist,
    addAlert,
    marketVersion,
  } = useAppData();

  const initialIndicator = customIndicators[0] ?? INITIAL_CUSTOM_INDICATORS[0];

  const [selectedId, setSelectedId] = useState<string>(initialIndicator.id);
  const [draft, setDraft] = useState<CustomIndicatorDefinition>(initialIndicator);
  const [selectedTicker, setSelectedTicker] = useState<string>('TRENT');
  const [subTab, setSubTab] = useState<SubTab>('chart');
  const [screenerFilter, setScreenerFilter] = useState<'ALL' | 'BUY' | 'SELL'>('ALL');
  const [backtestCapital, setBacktestCapital] = useState<number>(10_00_000);
  const [toast, setToast] = useState<string | null>(null);

  // On-demand OHLCV loading for ANY Indian NSE/BSE stock outside the 38 core stocks
  const [onDemandQuote, setOnDemandQuote] = useState<LiveQuotePayload | null>(null);
  const [loadingSymbol, setLoadingSymbol] = useState<boolean>(false);
  const [symbolError, setSymbolError] = useState<string | null>(null);

  const coreStock = STOCK_BY_TICKER[selectedTicker] ?? null;

  useEffect(() => {
    if (coreStock) {
      setOnDemandQuote(null);
      setLoadingSymbol(false);
      setSymbolError(null);
      return;
    }

    let cancelled = false;
    setLoadingSymbol(true);
    setSymbolError(null);
    setOnDemandQuote(null);

    fetch(`/api/market/quote/${encodeURIComponent(selectedTicker)}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Live NSE/BSE OHLCV data unavailable for ${selectedTicker}`);
        return (await res.json()) as LiveQuotePayload;
      })
      .then((data) => {
        if (!cancelled) {
          if (!data.bars || data.bars.length < 25) {
            setSymbolError(`Insufficient daily price history for ${selectedTicker}.`);
          } else {
            setOnDemandQuote(data);
          }
          setLoadingSymbol(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setSymbolError(
            err instanceof Error ? err.message : `Failed to fetch candles for ${selectedTicker}`
          );
          setLoadingSymbol(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedTicker, coreStock]);

  const activeStock: IndianStock | null = useMemo(() => {
    if (coreStock) return coreStock;
    if (onDemandQuote) return buildOnDemandStock(selectedTicker, onDemandQuote);
    return null;
  }, [coreStock, onDemandQuote, selectedTicker, marketVersion]);

  const handleSelectIndicator = (ind: CustomIndicatorDefinition) => {
    setSelectedId(ind.id);
    setDraft({ ...ind });
  };

  const handleNewIndicator = () => {
    const fresh: CustomIndicatorDefinition = {
      id: `custom_${Date.now()}`,
      code: 'MY_MOM',
      name: 'Custom EMA Trend & RSI Momentum',
      description: 'Percentage spread between Close and p1-day EMA filtered by RSI(14) strength.',
      formula: '((close - ema(close, p1)) / ema(close, p1)) * 100',
      buyRule: 'val > 0 && prev(val, 1) <= 0 && rsi(close, 14) > p2',
      sellRule: 'val < -2.5 || rsi(close, 14) < 42',
      plotType: 'subchart',
      color: '#0ea5e9',
      param1Name: 'emaLen',
      param1Value: 21,
      param2Name: 'minRsi',
      param2Value: 55,
    };
    setSelectedId(fresh.id);
    setDraft(fresh);
  };

  const handleDelete = async (id: string) => {
    await deleteCustomIndicator(id);
    const remaining = customIndicators.filter((c) => c.id !== id);
    const fallback = remaining[0] ?? INITIAL_CUSTOM_INDICATORS[0];
    setSelectedId(fallback.id);
    setDraft({ ...fallback });
    notify('Deleted custom indicator.');
  };

  const liveEval = useMemo(() => {
    if (!activeStock) {
      return {
        values: [],
        buySignals: [],
        sellSignals: [],
        latestValue: 0,
        latestSignal: 'NEUTRAL' as const,
      };
    }
    return evaluateCustomIndicator(activeStock, draft);
  }, [activeStock, draft, marketVersion]);

  const screenerRows = useMemo(() => {
    if (liveEval.error) return [];
    const universe: IndianStock[] =
      activeStock && !coreStock ? [activeStock, ...INDIAN_STOCKS] : INDIAN_STOCKS;

    return universe
      .map((s) => {
        const ev = evaluateCustomIndicator(s, draft);
        return {
          stock: s,
          latestValue: ev.latestValue,
          latestSignal: ev.latestSignal,
          recentBuys20d: ev.buySignals.slice(-20).filter(Boolean).length,
        };
      })
      .filter((r) => screenerFilter === 'ALL' || r.latestSignal === screenerFilter)
      .sort((a, b) => {
        const rank = { BUY: 2, SELL: 1, NEUTRAL: 0 };
        return rank[b.latestSignal] - rank[a.latestSignal] || b.latestValue - a.latestValue;
      });
  }, [draft, liveEval.error, screenerFilter, marketVersion, activeStock, coreStock]);

  const backtestResult = useMemo(() => {
    if (!activeStock || liveEval.error) return null;
    return backtestCustomIndicator(activeStock, draft, backtestCapital, 504);
  }, [activeStock, draft, backtestCapital, liveEval.error, marketVersion]);

  const notify = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const handleSave = async () => {
    if (liveEval.error) return;
    try {
      await saveCustomIndicator(draft);
      notify(`Saved indicator ${draft.code} (${draft.name}).`);
    } catch {
      notify(`Saved indicator ${draft.code} locally.`);
    }
  };

  const handleAttachAlert = async (ticker: string) => {
    await addAlert({
      ticker,
      category: 'custom_indicator',
      title: `${ticker} — ${draft.code} Alert Active (${liveEval.latestSignal})`,
      message: `Monitoring formula "${draft.formula}" · Buy rule: ${draft.buyRule || 'N/A'} · Latest value: ${liveEval.latestValue}.`,
    });
    notify(`Attached ${draft.code} alert on ${ticker} in Notifications.`);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Custom Indicators &amp; Strategy Lab
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Write vectorized formulas over any NSE/BSE stock OHLCV, NIFTY 500 relative strength, and built-in indicators. Plot on charts, screen equities, run Indian delivery cost-adjusted backtests, and attach alerts.
          </p>
        </div>

        <button
          onClick={handleNewIndicator}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 whitespace-nowrap self-start lg:self-auto"
        >
          <Plus className="w-3.5 h-3.5" />
          New Custom Indicator
        </button>
      </div>

      {toast && (
        <div className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
          <Check className="w-4 h-4 shrink-0" />
          <span>{toast}</span>
        </div>
      )}

      {/* Indicator Library Selector Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {customIndicators.map((ind) => {
          const active = ind.id === selectedId || ind.code === draft.code;
          return (
            <div
              key={ind.id}
              onClick={() => handleSelectIndicator(ind)}
              className={`cursor-pointer p-4 rounded-xl border transition-colors ${
                active
                  ? 'border-blue-500 bg-blue-500/5 dark:bg-blue-500/10'
                  : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs font-bold text-slate-900 dark:text-slate-100">
                  {ind.code}
                </span>
                <span className="text-[11px] text-slate-500">
                  {ind.plotType === 'overlay' ? 'Overlay' : 'Subchart'} · {ind.param1Name}={ind.param1Value}
                </span>
              </div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100 mt-1">
                {ind.name}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                {ind.description}
              </p>
            </div>
          );
        })}
      </div>

      {/* Builder + Output Split */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left: Formula Builder Editor (5 cols) */}
        <div className="xl:col-span-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
              <Code2 className="w-4 h-4 text-blue-500" />
              <span>Formula &amp; Signal Rule Builder</span>
            </div>
            {!draft.isBuiltIn && (
              <button
                onClick={() => handleDelete(draft.id)}
                className="p-1.5 text-slate-400 hover:text-red-500"
                title="Delete custom indicator"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1">
              <label className="block text-[11px] text-slate-500">Short Code</label>
              <input
                type="text"
                value={draft.code}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    code: e.target.value
                      .toUpperCase()
                      .replace(/[^A-Z0-9_]/g, '')
                      .slice(0, 16),
                  })
                }
                className="w-full px-2.5 py-1.5 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
              />
            </div>
            <div className="col-span-2 space-y-1">
              <label className="block text-[11px] text-slate-500">Indicator Name</label>
              <input
                type="text"
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="block text-[11px] text-slate-500">
              Indicator Formula (outputs series <code className="font-mono">val</code>)
            </label>
            <textarea
              rows={2}
              value={draft.formula}
              onChange={(e) => setDraft({ ...draft, formula: e.target.value })}
              className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-[11px] text-slate-500">Buy Signal Rule (boolean)</label>
            <textarea
              rows={2}
              value={draft.buyRule}
              onChange={(e) => setDraft({ ...draft, buyRule: e.target.value })}
              className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-emerald-700 dark:text-emerald-300"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-[11px] text-slate-500">Sell / Exit Rule (boolean)</label>
            <textarea
              rows={2}
              value={draft.sellRule}
              onChange={(e) => setDraft({ ...draft, sellRule: e.target.value })}
              className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-red-700 dark:text-red-300"
            />
          </div>

          {liveEval.error && (
            <div className="p-2.5 rounded-lg border border-red-500/40 bg-red-500/10 text-xs font-mono text-red-600 dark:text-red-400">
              Syntax Error: {liveEval.error}
            </div>
          )}

          {/* Parameters & Plot Mode */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="block text-[11px] text-slate-500">
                Param p1 ({draft.param1Name})
              </label>
              <input
                type="number"
                step={1}
                value={draft.param1Value}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setDraft({ ...draft, param1Value: Number.isFinite(v) ? v : 1 });
                }}
                className="w-full px-2.5 py-1.5 text-xs font-mono tabular-nums rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-[11px] text-slate-500">
                Param p2 ({draft.param2Name})
              </label>
              <input
                type="number"
                step={0.1}
                value={draft.param2Value}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setDraft({ ...draft, param2Value: Number.isFinite(v) ? v : 1 });
                }}
                className="w-full px-2.5 py-1.5 text-xs font-mono tabular-nums rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
              />
            </div>
          </div>

          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
              {(['subchart', 'overlay'] as const).map((pt) => (
                <button
                  key={pt}
                  onClick={() => setDraft({ ...draft, plotType: pt })}
                  className={`px-3 py-1 text-xs font-medium rounded-md capitalize ${
                    draft.plotType === pt
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-500'
                  }`}
                >
                  {pt}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => handleAttachAlert(selectedTicker)}
                disabled={Boolean(liveEval.error)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 whitespace-nowrap"
              >
                <BellPlus className="w-3.5 h-3.5" />
                Attach Alert
              </button>
              <button
                onClick={handleSave}
                disabled={Boolean(liveEval.error)}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 hover:opacity-90 disabled:opacity-40 whitespace-nowrap"
              >
                <Save className="w-3.5 h-3.5" />
                Save
              </button>
            </div>
          </div>

          {/* Supported Functions Quick Reference */}
          <div className="pt-3 border-t border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 space-y-1">
            <div className="font-medium text-slate-700 dark:text-slate-300">
              Available Series &amp; Functions
            </div>
            <div className="font-mono leading-relaxed">
              open, high, low, close, volume, nifty50, nifty500, rs_ratio, val, p1, p2 · sma(x,n),
              ema(x,n), rsi(x,n), atr(n), stdev(x,n), highest(x,n), lowest(x,n), roc(x,n), vwap(n),
              max_down_vol(n), prev(x,n), cross_above(a,b), cross_below(a,b)
            </div>
          </div>
        </div>

        {/* Right: Plot / Screener / Backtester Workspace (7 cols) */}
        <div className="xl:col-span-7 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
              {(
                [
                  { id: 'chart', label: 'Chart Plot' },
                  { id: 'screener', label: 'Universe Screener' },
                  { id: 'backtest', label: 'Strategy Backtest' },
                ] as const
              ).map((t) => (
                <button
                  key={t.id}
                  onClick={() => setSubTab(t.id)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                    subTab === t.id
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <IndianTickerSearchInput
                currentTicker={selectedTicker}
                onSelectTicker={(t) => setSelectedTicker(t)}
                placeholder="Any NSE / BSE stock..."
                className="w-56"
                compact
              />
              <button
                onClick={() => onInspectStock(selectedTicker)}
                title={`Open full ticker analysis page for ${selectedTicker}`}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
              >
                <span>Full Page</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {loadingSymbol ? (
            <div className="py-16 text-center text-xs text-slate-500 flex flex-col items-center gap-2.5">
              <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
              <span>Loading live 3-year NSE/BSE daily OHLCV candles for {selectedTicker}…</span>
            </div>
          ) : symbolError || !activeStock ? (
            <div className="py-14 text-center space-y-2 text-xs text-slate-500">
              <div className="text-red-600 dark:text-red-400 font-medium">
                {symbolError || `No data loaded for ${selectedTicker}`}
              </div>
              <button
                onClick={() => setSelectedTicker('TRENT')}
                className="text-blue-600 dark:text-blue-400 font-semibold underline"
              >
                Reset to TRENT
              </button>
            </div>
          ) : (
            <>
              {subTab === 'chart' && (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
                    <div className="flex items-center gap-3 font-mono">
                      <span className="font-bold text-slate-900 dark:text-slate-100">
                        {activeStock.ticker} {formatINR(activeStock.latestClose)}
                      </span>
                      <span className="text-slate-500">
                        {draft.code}:{' '}
                        <strong className="text-slate-900 dark:text-slate-100">
                          {liveEval.latestValue}
                        </strong>
                      </span>
                      <span
                        className={`font-semibold ${
                          liveEval.latestSignal === 'BUY'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : liveEval.latestSignal === 'SELL'
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-slate-500'
                        }`}
                      >
                        Signal: {liveEval.latestSignal}
                      </span>
                    </div>
                    <span className="text-slate-500">
                      {activeStock.sector} · NSE/BSE Daily OHLCV ({activeStock.bars.length} bars)
                    </span>
                  </div>

                  <StockChartPanel
                    stock={coreStock ?? undefined}
                    barsOverride={!coreStock ? activeStock.bars : undefined}
                    symbolLabel={activeStock.ticker}
                    customIndicator={draft}
                    height={270}
                  />
                </div>
              )}

              {subTab === 'screener' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
                      {(['ALL', 'BUY', 'SELL'] as const).map((f) => (
                        <button
                          key={f}
                          onClick={() => setScreenerFilter(f)}
                          className={`px-3 py-1 text-xs font-medium rounded-md ${
                            screenerFilter === f
                              ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                              : 'text-slate-500'
                          }`}
                        >
                          {f === 'ALL' ? `All (${screenerRows.length})` : `${f} Signals`}
                        </button>
                      ))}
                    </div>
                    <span className="text-xs text-slate-500 font-mono">
                      Showing {screenerRows.length} NSE equities
                    </span>
                  </div>

                  <div className="overflow-x-auto max-h-[420px] overflow-y-auto border border-slate-200 dark:border-slate-800 rounded-lg">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead className="sticky top-0 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                        <tr>
                          <th className="py-2 px-3">Ticker</th>
                          <th className="py-2 px-3 text-right">LTP (₹)</th>
                          <th className="py-2 px-3 text-right">{draft.code} Value</th>
                          <th className="py-2 px-3 text-right">20D Buys</th>
                          <th className="py-2 px-3">Current Signal</th>
                          <th className="py-2 px-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                        {screenerRows.map((row) => (
                          <tr
                            key={row.stock.ticker}
                            onClick={() => setSelectedTicker(row.stock.ticker)}
                            className={`cursor-pointer transition-colors ${
                              row.stock.ticker === selectedTicker
                                ? 'bg-blue-600/10 dark:bg-blue-500/15'
                                : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
                            }`}
                          >
                            <td className="py-2.5 px-3">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedTicker(row.stock.ticker);
                                  onInspectStock(row.stock.ticker);
                                }}
                                className="font-mono font-semibold text-slate-900 dark:text-slate-100 hover:text-blue-500 hover:underline"
                                title={`Open ${row.stock.ticker} full ticker page`}
                              >
                                {row.stock.ticker}
                              </button>
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                              {formatINR(row.stock.latestClose)}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold">
                              {row.latestValue.toFixed(2)}
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-500">
                              {row.recentBuys20d}
                            </td>
                            <td className="py-2.5 px-3 font-mono font-semibold">
                              <span
                                className={
                                  row.latestSignal === 'BUY'
                                    ? 'text-emerald-600 dark:text-emerald-400'
                                    : row.latestSignal === 'SELL'
                                    ? 'text-red-600 dark:text-red-400'
                                    : 'text-slate-400'
                                }
                              >
                                {row.latestSignal}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-right">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleWatchlist(row.stock.ticker);
                                }}
                                className="text-[11px] font-medium text-blue-600 dark:text-blue-400 hover:underline mr-2"
                              >
                                {watchlist.includes(row.stock.ticker) ? 'Watching' : '+ Watch'}
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleAttachAlert(row.stock.ticker);
                                }}
                                className="text-[11px] font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
                              >
                                Alert
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {subTab === 'backtest' && backtestResult && (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
                      <Play className="w-3.5 h-3.5 text-emerald-500" />
                      <span>
                        2-Year NSE Delivery Backtest on{' '}
                        <strong className="font-mono text-slate-900 dark:text-slate-100">
                          {activeStock.ticker}
                        </strong>{' '}
                        (STT + Stamp + Exchange + GST + DP deducted)
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-slate-500">Capital (₹):</span>
                      <input
                        type="number"
                        step={100000}
                        min={100000}
                        value={backtestCapital}
                        onChange={(e) =>
                          setBacktestCapital(Math.max(50000, Number(e.target.value) || 1000000))
                        }
                        className="w-28 px-2.5 py-1 font-mono tabular-nums rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                      />
                    </div>
                  </div>

                  {/* Backtest KPI Strip */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs border-y border-slate-200 dark:border-slate-800 py-3">
                    <div>
                      <div className="text-slate-500">Strategy Return</div>
                      <div
                        className={`font-mono text-base font-bold tabular-nums ${
                          backtestResult.totalReturnPct >= 0
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        {formatPct(backtestResult.totalReturnPct)}
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        NIFTY 500: {formatPct(backtestResult.benchmarkReturnPct)}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500">CAGR / Sharpe</div>
                      <div className="font-mono text-base font-bold tabular-nums text-slate-900 dark:text-slate-100">
                        {formatPct(backtestResult.cagrPct)}
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        Sharpe {backtestResult.sharpeRatio.toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500">Win Rate / PF</div>
                      <div className="font-mono text-base font-bold tabular-nums text-slate-900 dark:text-slate-100">
                        {backtestResult.winRatePct.toFixed(1)}%
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        PF {backtestResult.profitFactor.toFixed(2)} · {backtestResult.totalTrades} trades
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500">Max DD / Costs</div>
                      <div className="font-mono text-base font-bold tabular-nums text-red-600 dark:text-red-400">
                        -{backtestResult.maxDrawdownPct.toFixed(1)}%
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        Fees {formatINR(backtestResult.totalCostsInr, 0)}
                      </div>
                    </div>
                  </div>

                  {/* Equity Curve vs NIFTY 500 */}
                  <div style={{ width: '100%', height: 220 }}>
                    <ResponsiveContainer>
                      <LineChart
                        data={backtestResult.equityCurve}
                        margin={{ top: 8, right: 12, left: 4, bottom: 0 }}
                      >
                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="rgba(148,163,184,0.14)"
                          vertical={false}
                        />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 10, fill: '#64748b' }}
                          tickLine={false}
                          axisLine={false}
                          minTickGap={36}
                        />
                        <YAxis
                          orientation="right"
                          tick={{ fontSize: 10, fill: '#64748b' }}
                          tickLine={false}
                          axisLine={false}
                          tickFormatter={(v) => formatINRCompact(v)}
                          width={72}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#0f172a',
                            border: '1px solid #334155',
                            borderRadius: '8px',
                            fontSize: '12px',
                            color: '#f8fafc',
                          }}
                          formatter={(val: unknown, name: string | number | undefined) => [
                            formatINR(Number(val), 0),
                            String(name ?? '') === 'strategyEquity'
                              ? `${draft.code} Strategy`
                              : 'NIFTY 500 Benchmark',
                          ]}
                        />
                        <Line
                          type="monotone"
                          dataKey="strategyEquity"
                          stroke="#10b981"
                          strokeWidth={2}
                          dot={false}
                          isAnimationActive={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="benchmarkEquity"
                          stroke="#64748b"
                          strokeWidth={1.4}
                          strokeDasharray="4 4"
                          dot={false}
                          isAnimationActive={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Trade Ledger */}
                  <div className="overflow-x-auto max-h-[210px] overflow-y-auto border border-slate-200 dark:border-slate-800 rounded-lg">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead className="sticky top-0 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                        <tr>
                          <th className="py-2 px-3">Entry → Exit</th>
                          <th className="py-2 px-3 text-right">Buy / Sell ₹</th>
                          <th className="py-2 px-3 text-right">Shares</th>
                          <th className="py-2 px-3 text-right">Costs ₹</th>
                          <th className="py-2 px-3 text-right">Net P&amp;L</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70 font-mono tabular-nums">
                        {backtestResult.trades.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="py-6 text-center font-sans text-slate-500">
                              No completed round-trip trades triggered under current rules.
                            </td>
                          </tr>
                        ) : (
                          backtestResult.trades.map((tr, i) => (
                            <tr key={`${tr.entryDate}-${i}`}>
                              <td className="py-2 px-3 text-slate-700 dark:text-slate-300">
                                {tr.entryDate} → {tr.exitDate} ({tr.holdingDays}d)
                              </td>
                              <td className="py-2 px-3 text-right">
                                {formatINR(tr.entryPrice, 0)} / {formatINR(tr.exitPrice, 0)}
                              </td>
                              <td className="py-2 px-3 text-right">{tr.shares}</td>
                              <td className="py-2 px-3 text-right text-slate-500">
                                {formatINR(tr.costsInr)}
                              </td>
                              <td
                                className={`py-2 px-3 text-right font-semibold ${
                                  tr.netPnlInr >= 0
                                    ? 'text-emerald-600 dark:text-emerald-400'
                                    : 'text-red-600 dark:text-red-400'
                                }`}
                              >
                                {formatINR(tr.netPnlInr, 0)} ({formatPct(tr.returnPct)})
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
