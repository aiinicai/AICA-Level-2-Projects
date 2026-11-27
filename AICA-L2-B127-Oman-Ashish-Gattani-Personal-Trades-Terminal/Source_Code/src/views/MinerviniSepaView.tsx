import React, { useMemo, useState } from 'react';
import {
  BellPlus,
  CheckCircle2,
  ShieldAlert,
  SlidersHorizontal,
  TrendingUp,
  XCircle,
} from 'lucide-react';
import { StockChartPanel } from '../components/StockChartPanel';
import { useAppData } from '../context/AppDataContext';
import { INDIAN_STOCKS } from '../data/indianMarketData';
import { DEFAULT_TREND_THRESHOLDS, runMinerviniAnalysis } from '../engine/analyticsEngine';
import { MarketStage, TrendTemplateThresholds } from '../types/market';
import { formatINR, formatINRCompact, formatPct } from '../utils/formatters';

interface MinerviniSepaViewProps {
  onInspectStock: (ticker: string) => void;
}

export const MinerviniSepaView: React.FC<MinerviniSepaViewProps> = ({ onInspectStock }) => {
  const {
    accountCapitalInr,
    defaultRiskPct,
    updateRiskPreferences,
    watchlist,
    toggleWatchlist,
    addAlert,
    marketVersion,
  } = useAppData();

  const [thresholds, setThresholds] = useState<TrendTemplateThresholds>(DEFAULT_TREND_THRESHOLDS);
  const [showThresholdConfig, setShowThresholdConfig] = useState(false);
  const [stageFilter, setStageFilter] = useState<'All' | MarketStage>('All');
  const [onlyTemplatePass, setOnlyTemplatePass] = useState(false);
  const [onlyVcp, setOnlyVcp] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState<string>('TRENT');

  // Position sizing editable state
  const [stopLossPct, setStopLossPct] = useState<number>(7.5);
  const [riskPct, setRiskPct] = useState<number>(defaultRiskPct);
  const [capitalInr, setCapitalInr] = useState<number>(accountCapitalInr);
  const [alertSavedMsg, setAlertSavedMsg] = useState<string | null>(null);

  const allAnalyses = useMemo(
    () => runMinerviniAnalysis(INDIAN_STOCKS, thresholds),
    [thresholds, marketVersion]
  );

  const stageCounts = useMemo(() => {
    const counts = { 1: 0, 2: 0, 3: 0, 4: 0 };
    for (const a of allAnalyses) counts[a.stage]++;
    return counts;
  }, [allAnalyses]);

  const filtered = useMemo(() => {
    return allAnalyses.filter((a) => {
      if (stageFilter !== 'All' && a.stage !== stageFilter) return false;
      if (onlyTemplatePass && !a.allPassed) return false;
      if (onlyVcp && !a.vcp.detected) return false;
      return true;
    });
  }, [allAnalyses, stageFilter, onlyTemplatePass, onlyVcp]);

  const active = useMemo(() => {
    return (
      allAnalyses.find((a) => a.stock.ticker === selectedTicker) ??
      filtered[0] ??
      allAnalyses[0]
    );
  }, [allAnalyses, filtered, selectedTicker]);

  // Position sizing math (pure risk management — NO valuation/DCF!)
  const entryPrice = active.stock.latestClose;
  const stopPrice = Number((entryPrice * (1 - stopLossPct / 100)).toFixed(2));
  const riskPerShare = Math.max(0.01, entryPrice - stopPrice);
  const maxRupeeRisk = (capitalInr * riskPct) / 100;
  const recommendedShares = Math.max(0, Math.floor(maxRupeeRisk / riskPerShare));
  const positionValueInr = recommendedShares * entryPrice;
  const positionWeightPct = capitalInr > 0 ? (positionValueInr / capitalInr) * 100 : 0;
  const r2Price = entryPrice + riskPerShare * 2;
  const r3Price = entryPrice + riskPerShare * 3;

  const handleSaveRiskPrefs = async () => {
    await updateRiskPreferences(capitalInr, riskPct);
    setAlertSavedMsg('Saved account capital & risk % preferences to your profile.');
    setTimeout(() => setAlertSavedMsg(null), 2600);
  };

  const handleCreateVcpAlert = async () => {
    await addAlert({
      ticker: active.stock.ticker,
      category: active.vcp.isPivotBreakout ? 'vcp_pivot' : 'trend_template',
      title: `${active.stock.ticker} — SEPA Score ${active.minerviniScore}/100 (Stage ${active.stage})`,
      message: `Trend Template ${active.passedCount}/8 · RS ${active.rsRating} vs NIFTY 500 · Pivot ${formatINR(active.vcp.pivotPrice)} · Stop ${formatINR(stopPrice)} (-${stopLossPct.toFixed(1)}%).`,
    });
    setAlertSavedMsg(`Alert added for ${active.stock.ticker} in Notifications.`);
    setTimeout(() => setAlertSavedMsg(null), 2800);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Mark Minervini SEPA Framework
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            8-Point Trend Template with IBD-style Relative Strength vs NIFTY 500, Stan Weinstein Stage 1–4 classification, algorithmic VCP detection, SEPA fundamentals, and position sizing.
          </p>
        </div>

        <button
          onClick={() => setShowThresholdConfig((s) => !s)}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap self-start lg:self-auto"
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          {showThresholdConfig ? 'Hide Thresholds' : 'Edit Template Thresholds'}
        </button>
      </div>

      {/* Editable Trend Template Thresholds Drawer */}
      {showThresholdConfig && (
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="space-y-1">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
              200D SMA Rising Lookback (Months)
            </label>
            <input
              type="number"
              min={1}
              max={6}
              value={thresholds.sma200TrendMonths}
              onChange={(e) =>
                setThresholds((t) => ({
                  ...t,
                  sma200TrendMonths: Math.max(1, Math.min(6, Number(e.target.value) || 1)),
                }))
              }
              className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
            />
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
              Min % Above 52W Low
            </label>
            <input
              type="number"
              min={5}
              max={150}
              value={thresholds.minAbove52WLowPct}
              onChange={(e) =>
                setThresholds((t) => ({
                  ...t,
                  minAbove52WLowPct: Math.max(5, Number(e.target.value) || 30),
                }))
              }
              className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
            />
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
              Max % Below 52W High
            </label>
            <input
              type="number"
              min={5}
              max={50}
              value={thresholds.maxBelow52WHighPct}
              onChange={(e) =>
                setThresholds((t) => ({
                  ...t,
                  maxBelow52WHighPct: Math.max(5, Number(e.target.value) || 25),
                }))
              }
              className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
            />
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
              Min RS Rating (vs NIFTY 500)
            </label>
            <input
              type="number"
              min={1}
              max={99}
              value={thresholds.minRsRating}
              onChange={(e) =>
                setThresholds((t) => ({
                  ...t,
                  minRsRating: Math.max(1, Math.min(99, Number(e.target.value) || 70)),
                }))
              }
              className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
            />
          </div>
        </div>
      )}

      {/* Stage Analysis Distribution & Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
          {(
            [
              { key: 'All', label: `All (${allAnalyses.length})` },
              { key: 2, label: `Stage 2 Advancing (${stageCounts[2]})` },
              { key: 1, label: `Stage 1 Basing (${stageCounts[1]})` },
              { key: 3, label: `Stage 3 Topping (${stageCounts[3]})` },
              { key: 4, label: `Stage 4 Declining (${stageCounts[4]})` },
            ] as const
          ).map((tab) => (
            <button
              key={String(tab.key)}
              onClick={() => setStageFilter(tab.key)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                stageFilter === tab.key
                  ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3 text-xs">
          <label className="inline-flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={onlyTemplatePass}
              onChange={(e) => setOnlyTemplatePass(e.target.checked)}
              className="rounded border-slate-400 text-blue-600"
            />
            <span>8/8 Trend Template Only</span>
          </label>
          <label className="inline-flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={onlyVcp}
              onChange={(e) => setOnlyVcp(e.target.checked)}
              className="rounded border-slate-400 text-blue-600"
            />
            <span>Active VCP Setup Only</span>
          </label>
        </div>
      </div>

      {/* Main Split: Left Screener Grid (7 cols) + Right Deep SEPA Inspector (5 cols) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left: Screener Table */}
        <div className="xl:col-span-7 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              NSE SEPA Screener ({filtered.length} stocks)
            </span>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Click a row to inspect 8-point checklist, VCP & sizing
            </span>
          </div>
          <div className="overflow-x-auto max-h-[760px] overflow-y-auto">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 z-10 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                <tr>
                  <th className="py-2.5 px-4">Ticker</th>
                  <th className="py-2.5 px-2.5 text-right">LTP (₹)</th>
                  <th className="py-2.5 px-2.5 text-right">Template</th>
                  <th className="py-2.5 px-2.5 text-right">RS</th>
                  <th className="py-2.5 px-2.5">Stage</th>
                  <th className="py-2.5 px-2.5">VCP / Pivot</th>
                  <th className="py-2.5 px-2.5 text-right">Qtr EPS</th>
                  <th className="py-2.5 px-4 text-right">Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/80 dark:divide-slate-800/80 text-xs">
                {filtered.map((item) => {
                  const isSel = item.stock.ticker === active.stock.ticker;
                  return (
                    <tr
                      key={item.stock.ticker}
                      onClick={() => {
                        setSelectedTicker(item.stock.ticker);
                        setStopLossPct(item.suggestedStopPct);
                      }}
                      className={`cursor-pointer transition-colors ${
                        isSel
                          ? 'bg-blue-600/10 dark:bg-blue-500/15'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
                      }`}
                    >
                      <td className="py-2.5 px-4">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedTicker(item.stock.ticker);
                            setStopLossPct(item.suggestedStopPct);
                            onInspectStock(item.stock.ticker);
                          }}
                          className="font-mono font-semibold text-slate-900 dark:text-slate-100 hover:text-blue-500 hover:underline text-left block"
                          title={`Open ${item.stock.ticker} candlestick chart`}
                        >
                          {item.stock.ticker}
                        </button>
                        <div className="text-[11px] text-slate-500 truncate max-w-[130px]">
                          {item.stock.sector}
                        </div>
                      </td>
                      <td className="py-2.5 px-2.5 text-right font-mono tabular-nums text-slate-900 dark:text-slate-100">
                        {formatINR(item.stock.latestClose, 0)}
                      </td>
                      <td className="py-2.5 px-2.5 text-right font-mono tabular-nums font-semibold">
                        <span
                          className={
                            item.allPassed
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : item.passedCount >= 6
                              ? 'text-amber-600 dark:text-amber-400'
                              : 'text-red-600 dark:text-red-400'
                          }
                        >
                          {item.passedCount}/8
                        </span>
                      </td>
                      <td className="py-2.5 px-2.5 text-right font-mono tabular-nums font-semibold text-slate-900 dark:text-slate-100">
                        {item.rsRating}
                      </td>
                      <td className="py-2.5 px-2.5 font-mono text-[11px]">
                        <span
                          className={
                            item.stage === 2
                              ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                              : item.stage === 4
                              ? 'text-red-600 dark:text-red-400'
                              : 'text-slate-600 dark:text-slate-400'
                          }
                        >
                          S{item.stage}
                        </span>
                      </td>
                      <td className="py-2.5 px-2.5 font-mono text-[11px]">
                        {item.vcp.isPivotBreakout ? (
                          <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                            {item.vcp.tCount}T Breakout ({item.vcp.breakoutVolumeRatio}×)
                          </span>
                        ) : item.vcp.detected ? (
                          <span className="text-blue-600 dark:text-blue-400">
                            {item.vcp.tCount}T · {item.vcp.volumeDryUpRatio}× Vol
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td
                        className={`py-2.5 px-2.5 text-right font-mono tabular-nums ${
                          item.stock.fundamentals.qtrEpsYoY >= 20
                            ? 'text-emerald-600 dark:text-emerald-400 font-medium'
                            : item.stock.fundamentals.qtrEpsYoY < 0
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-slate-600 dark:text-slate-300'
                        }`}
                      >
                        {formatPct(item.stock.fundamentals.qtrEpsYoY)}
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono tabular-nums font-bold text-slate-900 dark:text-slate-100">
                        {item.minerviniScore}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Detailed SEPA Inspector */}
        <div className="xl:col-span-5 space-y-5">
          {/* Stock Summary & Chart */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onInspectStock(active.stock.ticker)}
                    className="text-lg font-bold font-mono text-slate-900 dark:text-slate-100 hover:text-blue-500 hover:underline"
                    title="Open full candlestick chart drawer"
                  >
                    {active.stock.ticker}
                  </button>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    · {active.stageLabel}
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                  {active.stock.name} · BSE {active.stock.bseCode}
                </p>
              </div>
              <div className="text-right">
                <div className="text-xs text-slate-500 dark:text-slate-400">Minervini Score</div>
                <div className="text-2xl font-bold font-mono tabular-nums text-blue-600 dark:text-blue-400">
                  {active.minerviniScore}
                  <span className="text-xs font-normal text-slate-400">/100</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => toggleWatchlist(active.stock.ticker)}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                {watchlist.includes(active.stock.ticker) ? 'In Watchlist' : '+ Add to Watchlist'}
              </button>
              <button
                onClick={handleCreateVcpAlert}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700"
              >
                <BellPlus className="w-3.5 h-3.5" />
                Set SEPA Alert
              </button>
            </div>

            {alertSavedMsg && (
              <div className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                {alertSavedMsg}
              </div>
            )}

            <StockChartPanel
              stock={active.stock}
              pivotPrice={active.vcp.pivotPrice}
              stopLossPrice={stopPrice}
              height={220}
            />
          </div>

          {/* 8-Point Trend Template Pass/Fail Checklist */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                8-Point Trend Template ({active.passedCount}/8 Passed)
              </h3>
              <span className="font-mono text-xs text-slate-500">
                RS Rank {active.rsRating}/99
              </span>
            </div>
            <div className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
              {active.conditions.map((c) => (
                <div key={c.id} className="py-2 flex items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-2 min-w-0">
                    {c.passed ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />
                    )}
                    <span className="text-slate-800 dark:text-slate-200 truncate">
                      {c.id}. {c.label}
                    </span>
                  </div>
                  <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400 shrink-0 tabular-nums">
                    {c.detail}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* VCP Volatility Contraction Pattern Panel */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                <TrendingUp className="w-4 h-4 text-emerald-500" />
                <span>VCP Contraction Structure</span>
              </div>
              <span className="text-xs font-mono font-semibold text-slate-700 dark:text-slate-300">
                {active.vcp.isPivotBreakout
                  ? 'Pivot Breakout Confirmed'
                  : active.vcp.detected
                  ? `Constructive ${active.vcp.tCount}T Base`
                  : 'No Tight VCP'}
              </span>
            </div>

            {active.vcp.contractions.length > 0 && (
              <div className="text-xs font-mono text-slate-800 dark:text-slate-200 py-2 px-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                Contraction Sequence:{' '}
                <span className="font-semibold text-blue-600 dark:text-blue-400">
                  {active.vcp.contractions.map((c) => `-${c.depthPct}%`).join(' → ')}
                </span>{' '}
                ({active.vcp.tCount}T over {active.vcp.baseWeeks} wks)
              </div>
            )}

            <div className="grid grid-cols-3 gap-3 text-xs pt-1">
              <div>
                <div className="text-slate-500">Pivot Buy Point</div>
                <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                  {formatINR(active.vcp.pivotPrice)}
                </div>
              </div>
              <div>
                <div className="text-slate-500">Dist. to Pivot</div>
                <div
                  className={`font-mono font-semibold tabular-nums mt-0.5 ${
                    active.vcp.distanceToPivotPct >= 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-amber-600 dark:text-amber-400'
                  }`}
                >
                  {formatPct(active.vcp.distanceToPivotPct)}
                </div>
              </div>
              <div>
                <div className="text-slate-500">Vol Dry-Up (5D/50D)</div>
                <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                  {active.vcp.volumeDryUpRatio.toFixed(2)}×{' '}
                  {active.vcp.isVolumeDryUp ? '(Dry)' : '(Normal)'}
                </div>
              </div>
            </div>
          </div>

          {/* SEPA Fundamentals Check */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                SEPA Fundamental Acceleration
              </h3>
              <span className="font-mono text-xs text-slate-500">
                Score {active.sepaFundamentalScore}/100
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <div>
                <div className="text-slate-500">Qtr EPS YoY</div>
                <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                  {formatPct(active.stock.fundamentals.qtrEpsYoY)}
                </div>
                <div className="text-[11px] text-slate-500">
                  Prev {formatPct(active.stock.fundamentals.prevQtrEpsYoY)} ·{' '}
                  {active.stock.fundamentals.qtrEpsYoY > active.stock.fundamentals.prevQtrEpsYoY
                    ? 'Accelerating'
                    : 'Decelerating'}
                </div>
              </div>
              <div>
                <div className="text-slate-500">Qtr Revenue YoY</div>
                <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                  {formatPct(active.stock.fundamentals.qtrRevYoY)}
                </div>
                <div className="text-[11px] text-slate-500">
                  Prev {formatPct(active.stock.fundamentals.prevQtrRevYoY)}
                </div>
              </div>
              <div>
                <div className="text-slate-500">OPM & Expansion</div>
                <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                  {active.stock.fundamentals.opMarginPct.toFixed(1)}%
                </div>
                <div className="text-[11px] text-slate-500">
                  {active.stock.fundamentals.opMarginExpansionBps >= 0 ? '+' : ''}
                  {active.stock.fundamentals.opMarginExpansionBps} bps YoY
                </div>
              </div>
              <div>
                <div className="text-slate-500">Earnings Surprise</div>
                <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                  {formatPct(active.stock.fundamentals.earningsSurprisePct)}
                </div>
                <div className="text-[11px] text-slate-500">
                  3Y EPS CAGR {active.stock.fundamentals.annualEps3YCagr}%
                </div>
              </div>
              <div>
                <div className="text-slate-500">FII / DII QoQ Δ</div>
                <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                  {formatPct(active.stock.fundamentals.fiiQoQChangePct)} /{' '}
                  {formatPct(active.stock.fundamentals.diiQoQChangePct)}
                </div>
                <div className="text-[11px] text-slate-500">
                  MF {active.stock.fundamentals.mfHoldingPct}%
                </div>
              </div>
              <div>
                <div className="text-slate-500">Promoter / Pledge</div>
                <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                  {active.stock.fundamentals.promoterHoldingPct}% /{' '}
                  {active.stock.fundamentals.promoterPledgePct}%
                </div>
                <div className="text-[11px] text-slate-500">
                  ROE {active.stock.fundamentals.roePct}%
                </div>
              </div>
            </div>
          </div>

          {/* Risk Management & Position Sizing Calculator */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                <ShieldAlert className="w-4 h-4 text-amber-500" />
                <span>SEPA Risk & Position Sizing</span>
              </div>
              <button
                onClick={handleSaveRiskPrefs}
                className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
              >
                Save Defaults
              </button>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="block text-[11px] text-slate-500">Account Equity (₹)</label>
                <input
                  type="number"
                  step={100000}
                  min={50000}
                  value={capitalInr}
                  onChange={(e) => setCapitalInr(Math.max(10000, Number(e.target.value) || 0))}
                  className="w-full px-2.5 py-1.5 text-xs font-mono tabular-nums rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-[11px] text-slate-500">Risk / Trade (%)</label>
                <input
                  type="number"
                  step={0.25}
                  min={0.25}
                  max={5}
                  value={riskPct}
                  onChange={(e) => setRiskPct(Math.max(0.1, Math.min(10, Number(e.target.value) || 1)))}
                  className="w-full px-2.5 py-1.5 text-xs font-mono tabular-nums rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-[11px] text-slate-500">Stop-Loss (%)</label>
                <input
                  type="number"
                  step={0.5}
                  min={2}
                  max={15}
                  value={stopLossPct}
                  onChange={(e) =>
                    setStopLossPct(Math.max(1, Math.min(20, Number(e.target.value) || 7.5)))
                  }
                  className="w-full px-2.5 py-1.5 text-xs font-mono tabular-nums rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-200 dark:border-slate-800 text-xs">
              <div>
                <div className="text-slate-500">Stop-Loss Level</div>
                <div className="font-mono font-semibold text-red-600 dark:text-red-400 tabular-nums">
                  {formatINR(stopPrice)}
                </div>
              </div>
              <div>
                <div className="text-slate-500">Position Size</div>
                <div className="font-mono font-semibold text-slate-900 dark:text-slate-100 tabular-nums">
                  {recommendedShares} sh ({positionWeightPct.toFixed(1)}%)
                </div>
              </div>
              <div>
                <div className="text-slate-500">Capital Required</div>
                <div className="font-mono font-semibold text-slate-900 dark:text-slate-100 tabular-nums">
                  {formatINRCompact(positionValueInr)}
                </div>
              </div>
              <div>
                <div className="text-slate-500">2R / 3R Levels</div>
                <div className="font-mono font-semibold text-emerald-600 dark:text-emerald-400 tabular-nums">
                  ₹{Math.round(r2Price)} / ₹{Math.round(r3Price)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
