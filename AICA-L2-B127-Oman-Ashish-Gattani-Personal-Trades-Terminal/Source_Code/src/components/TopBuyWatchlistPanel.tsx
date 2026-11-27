import React, { useMemo, useState } from 'react';
import { Award, BellPlus, Check, Download, LineChart, RotateCcw, Star } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { UNIVERSE_COUNTS, matchesUniverseScope } from '../data/indianMarketData';
import { resolveStockSectorContext } from '../engine/sectorTrendEngine';
import {
  TopBuyWatchlistItem,
  computeTopBuyWatchlist,
} from '../engine/tradeRadarEngine';
import { IndianStock, MarketCapBucket, UniverseScope } from '../types/market';
import { formatINR, formatINRCompact, formatPct } from '../utils/formatters';

type StrategyLens = 'overall' | 'actionable' | 'breakout' | 'growth';
type CapFilter = 'All' | 'Large' | 'Mid' | 'Small';
type ScoreFilterBasis = 'call_score' | 'matrix_score' | 'sepa_score' | 'combined';
type BreakoutFilterTag = 'ATH_BO' | '52W_BO';
type HvFilterTag = 'HVE' | 'HVY' | 'HVQ';
type DisplayLimit = 10 | 25 | 50 | 0; // 0 = All

interface StockEventFlags {
  isAthBo: boolean;
  is52WBo: boolean;
  hvTag: HvFilterTag | null;
}

const UNIVERSE_SCOPE_OPTIONS: { id: UniverseScope; label: string; count: number }[] = [
  { id: 'all', label: 'All NSE', count: UNIVERSE_COUNTS.total },
  { id: 'nifty500', label: 'NIFTY 500', count: UNIVERSE_COUNTS.nifty500 },
  { id: 'fno', label: 'F&O', count: UNIVERSE_COUNTS.fno },
  { id: 'midcap', label: 'Midcap', count: UNIVERSE_COUNTS.midcap },
  { id: 'smallcap', label: 'Smallcap', count: UNIVERSE_COUNTS.smallcap },
];

const SCORE_BASIS_OPTIONS: { id: ScoreFilterBasis; label: string }[] = [
  { id: 'call_score', label: 'Call / Score' },
  { id: 'matrix_score', label: 'Indicators Matrix Summary' },
  { id: 'sepa_score', label: 'Minervini SEPA Score' },
  { id: 'combined', label: 'All 3 Combined' },
];

const SCORE_PRESETS = [0, 60, 70, 80] as const;

interface TopBuyWatchlistPanelProps {
  stocks: IndianStock[];
  marketVersion: number;
  regimeLabel?: string;
  recommendedExposurePct?: number;
  onInspectStock: (ticker: string) => void;
}

function matchesCap(bucket: MarketCapBucket, filter: CapFilter): boolean {
  if (filter === 'All') return true;
  if (filter === 'Small') return bucket === 'Small' || bucket === 'Micro';
  return bucket === filter;
}

/**
 * Computes ATH BO, 52W BO (10-session recency, holding >=94% of breakout level),
 * and HVE / HVY / HVQ (10-session recency, highest priority HVE > HVY > HVQ)
 * matching analyticsEngine.ts and HighVolumeScannerView.tsx.
 */
function computeEventFlagsForStock(stock: IndianStock): StockEventFlags {
  const bars = stock.bars;
  const n = bars?.length ?? 0;
  let isAthBo = false;
  let is52WBo = false;
  let hvTag: HvFilterTag | null = null;

  if (!bars || n < 70) {
    return { isAthBo, is52WBo, hvTag };
  }

  const lastIdx = n - 1;
  const latestClose = bars[lastIdx].close;

  // 1. 52W BO & ATH BO detection (within last 10 sessions, >=220 sessions of history)
  if (n >= 220) {
    const earliestBoIdx = Math.max(210, n - 10);
    for (let idx = lastIdx; idx >= earliestBoIdx; idx--) {
      const high = bars[idx].high;
      const winStart = idx - Math.min(252, idx);
      let prior52WHigh = -Infinity;
      for (let i = winStart; i < idx; i++) {
        if (bars[i].high > prior52WHigh) prior52WHigh = bars[i].high;
      }

      if (prior52WHigh > 0 && high > prior52WHigh && latestClose >= prior52WHigh * 0.94) {
        is52WBo = true;

        let priorAth = prior52WHigh;
        for (let i = 0; i < winStart; i++) {
          if (bars[i].high > priorAth) priorAth = bars[i].high;
        }
        if (priorAth > 0 && high > priorAth && latestClose >= priorAth * 0.94) {
          isAthBo = true;
          break;
        }
      }
    }
  }

  // 2. HVE / HVY / HVQ detection (within last 10 sessions, priority HVE > HVY > HVQ)
  const qtrLookback = 63;
  const yrLookback = 252;
  const startScanIdx = Math.max(qtrLookback, lastIdx - 9);

  let runningMaxAll = 0;
  for (let i = 0; i < startScanIdx; i++) {
    if (bars[i].volume > runningMaxAll) runningMaxAll = bars[i].volume;
  }

  let bestRank = 0;
  for (let i = startScanIdx; i <= lastIdx; i++) {
    const vol = bars[i].volume;
    if (vol <= 0) continue;

    let tag: HvFilterTag | null = null;
    let rank = 0;

    if (vol > runningMaxAll && i >= qtrLookback) {
      tag = 'HVE';
      rank = 3;
    } else {
      if (i >= yrLookback) {
        let maxYr = 0;
        for (let j = i - yrLookback; j < i; j++) {
          if (bars[j].volume > maxYr) maxYr = bars[j].volume;
        }
        if (vol > maxYr && maxYr > 0) {
          tag = 'HVY';
          rank = 2;
        }
      }
      if (!tag && i >= qtrLookback) {
        let maxQtr = 0;
        for (let j = i - qtrLookback; j < i; j++) {
          if (bars[j].volume > maxQtr) maxQtr = bars[j].volume;
        }
        if (vol > maxQtr && maxQtr > 0) {
          tag = 'HVQ';
          rank = 1;
        }
      }
    }

    if (vol > runningMaxAll) runningMaxAll = vol;
    if (tag && rank >= bestRank) {
      bestRank = rank;
      hvTag = tag;
    }
  }

  return { isAthBo, is52WBo, hvTag };
}

export const TopBuyWatchlistPanel: React.FC<TopBuyWatchlistPanelProps> = ({
  stocks,
  marketVersion,
  regimeLabel,
  recommendedExposurePct,
  onInspectStock,
}) => {
  const {
    watchlist,
    toggleWatchlist,
    addManyToWatchlist,
    addAlert,
    accountCapitalInr,
    defaultRiskPct,
    liveSymbolsCount,
    totalUniverseCount,
    isHydratingExtended,
  } = useAppData();

  const [lens, setLens] = useState<StrategyLens>('overall');
  const [universeScope, setUniverseScope] = useState<UniverseScope>('all');
  const [capFilter, setCapFilter] = useState<CapFilter>('All');
  const [sectorFilter, setSectorFilter] = useState<string>('All');
  const [scoreBasis, setScoreBasis] = useState<ScoreFilterBasis>('call_score');
  const [minCallScore, setMinCallScore] = useState<number>(0);
  const [minMatrixScore, setMinMatrixScore] = useState<number>(0);
  const [minSepaScore, setMinSepaScore] = useState<number>(0);
  const [selectedBreakouts, setSelectedBreakouts] = useState<BreakoutFilterTag[]>([]);
  const [selectedHvTags, setSelectedHvTags] = useState<HvFilterTag[]>([]);
  const [displayLimit, setDisplayLimit] = useState<DisplayLimit>(10);
  const [alertedTickers, setAlertedTickers] = useState<Record<string, boolean>>({});
  const [watchlistSaved, setWatchlistSaved] = useState(false);

  const sectorOptions = useMemo(
    () => Array.from(new Set(stocks.map((s) => s.sector))).sort(),
    [stocks]
  );

  // Precompute ATH BO, 52W BO, and HVE/HVY/HVQ flags once per market snapshot
  const eventFlagsByTicker = useMemo(() => {
    void marketVersion;
    const map = new Map<string, StockEventFlags>();
    for (const s of stocks) {
      map.set(s.ticker, computeEventFlagsForStock(s));
    }
    return map;
  }, [stocks, marketVersion]);

  const filteredUniverse = useMemo(() => {
    void marketVersion;
    return stocks.filter(
      (s) =>
        matchesUniverseScope(s, universeScope) &&
        matchesCap(s.capBucket, capFilter) &&
        (sectorFilter === 'All' || s.sector === sectorFilter)
    );
  }, [stocks, marketVersion, universeScope, capFilter, sectorFilter]);

  // Rank entire filtered universe with full 16-indicator Indicators Matrix Summary
  // (including NSE Sector Scorecard & Quadrant resolved against the complete NSE universe)
  const allRanked = useMemo(() => {
    void marketVersion;
    return computeTopBuyWatchlist(
      filteredUniverse,
      filteredUniverse.length,
      (sec, ind) => resolveStockSectorContext(stocks, sec, ind, marketVersion)
    );
  }, [filteredUniverse, stocks, marketVersion]);

  // Pool after strategy lens + score basis filter (used for live breakout/HV counts too)
  const scoreAndLensFiltered = useMemo(() => {
    let list = allRanked;

    if (lens === 'actionable') {
      list = list.filter((r) => !r.isExtended);
    } else if (lens === 'breakout') {
      list = list.filter(
        (r) =>
          r.setups.includes('VCP_BREAKOUT') ||
          r.setups.includes('POCKET_PIVOT') ||
          r.setups.includes('RS_BLUE_DOT') ||
          r.setups.includes('EPISODIC_PIVOT')
      );
    } else if (lens === 'growth') {
      list = list.filter((r) => r.qtrEpsYoY >= 15 && r.stage === 2);
    }

    // Score Filter Basis threshold filtering
    if (scoreBasis === 'call_score') {
      if (minCallScore > 0) list = list.filter((r) => r.compositeScore >= minCallScore);
    } else if (scoreBasis === 'matrix_score') {
      if (minMatrixScore > 0) list = list.filter((r) => r.matrixScorePct >= minMatrixScore);
    } else if (scoreBasis === 'sepa_score') {
      if (minSepaScore > 0) list = list.filter((r) => r.minerviniScore >= minSepaScore);
    } else {
      if (minCallScore > 0 || minMatrixScore > 0 || minSepaScore > 0) {
        list = list.filter(
          (r) =>
            r.compositeScore >= minCallScore &&
            r.matrixScorePct >= minMatrixScore &&
            r.minerviniScore >= minSepaScore
        );
      }
    }

    return list;
  }, [allRanked, lens, scoreBasis, minCallScore, minMatrixScore, minSepaScore]);

  const eventCounts = useMemo(() => {
    let athBo = 0;
    let w52Bo = 0;
    let hve = 0;
    let hvy = 0;
    let hvq = 0;
    for (const r of scoreAndLensFiltered) {
      const flags = eventFlagsByTicker.get(r.stock.ticker);
      if (!flags) continue;
      if (flags.isAthBo) athBo++;
      if (flags.is52WBo) w52Bo++;
      if (flags.hvTag === 'HVE') hve++;
      else if (flags.hvTag === 'HVY') hvy++;
      else if (flags.hvTag === 'HVQ') hvq++;
    }
    return { athBo, w52Bo, hve, hvy, hvq };
  }, [scoreAndLensFiltered, eventFlagsByTicker]);

  const hasAdvancedFilter =
    minCallScore > 0 ||
    minMatrixScore > 0 ||
    minSepaScore > 0 ||
    selectedBreakouts.length > 0 ||
    selectedHvTags.length > 0 ||
    scoreBasis !== 'call_score';

  const { matchedTotal, visibleWatchlistItems } = useMemo(() => {
    let filtered = scoreAndLensFiltered;

    // Breakout filters (OR within breakout pills)
    if (selectedBreakouts.length > 0) {
      filtered = filtered.filter((r) => {
        const flags = eventFlagsByTicker.get(r.stock.ticker);
        if (!flags) return false;
        return selectedBreakouts.some((tag) =>
          tag === 'ATH_BO' ? flags.isAthBo : flags.is52WBo
        );
      });
    }

    // High-Volume filters (OR within HV pills; AND with breakout pills if both selected)
    if (selectedHvTags.length > 0) {
      filtered = filtered.filter((r) => {
        const flags = eventFlagsByTicker.get(r.stock.ticker);
        if (!flags || !flags.hvTag) return false;
        return selectedHvTags.includes(flags.hvTag);
      });
    }

    // Sort according to active Score Filter Basis (and growth lens when on default call_score)
    const sorted = [...filtered].sort((a, b) => {
      if (scoreBasis === 'matrix_score') {
        if (b.matrixScorePct !== a.matrixScorePct) return b.matrixScorePct - a.matrixScorePct;
        return b.compositeScore - a.compositeScore;
      }
      if (scoreBasis === 'sepa_score') {
        if (b.minerviniScore !== a.minerviniScore) return b.minerviniScore - a.minerviniScore;
        return b.compositeScore - a.compositeScore;
      }
      if (scoreBasis === 'combined') {
        const avgA = (a.compositeScore + a.matrixScorePct + a.minerviniScore) / 3;
        const avgB = (b.compositeScore + b.matrixScorePct + b.minerviniScore) / 3;
        if (Math.abs(avgB - avgA) > 0.001) return avgB - avgA;
        return b.compositeScore - a.compositeScore;
      }
      if (lens === 'growth') {
        return b.fundaScore + b.compositeScore - (a.fundaScore + a.compositeScore);
      }
      return b.compositeScore - a.compositeScore;
    });

    const sliced = displayLimit > 0 ? sorted.slice(0, displayLimit) : sorted;
    return {
      matchedTotal: sorted.length,
      visibleWatchlistItems: sliced.map((item, idx) => ({ ...item, rank: idx + 1 })),
    };
  }, [
    scoreAndLensFiltered,
    selectedBreakouts,
    selectedHvTags,
    eventFlagsByTicker,
    scoreBasis,
    lens,
    displayLimit,
  ]);

  const riskBudgetInr = Math.max(1000, (accountCapitalInr * defaultRiskPct) / 100);

  const summary = useMemo(() => {
    if (!visibleWatchlistItems.length) {
      return {
        strongBuys: 0,
        avgScore: 0,
        avgMatrixPct: 0,
        avgSepaScore: 0,
        avgEpsYoY: 0,
        avgRiskPct: 0,
      };
    }
    const len = visibleWatchlistItems.length;
    const strongBuys = visibleWatchlistItems.filter((r) => r.rating === 'Strong Buy').length;
    const avgScore = Math.round(
      visibleWatchlistItems.reduce((s, r) => s + r.compositeScore, 0) / len
    );
    const avgMatrixPct = Math.round(
      visibleWatchlistItems.reduce((s, r) => s + r.matrixScorePct, 0) / len
    );
    const avgSepaScore = Math.round(
      visibleWatchlistItems.reduce((s, r) => s + r.minerviniScore, 0) / len
    );
    const avgEpsYoY = visibleWatchlistItems.reduce((s, r) => s + r.qtrEpsYoY, 0) / len;
    const avgRiskPct = visibleWatchlistItems.reduce((s, r) => s + r.stopRiskPct, 0) / len;
    return { strongBuys, avgScore, avgMatrixPct, avgSepaScore, avgEpsYoY, avgRiskPct };
  }, [visibleWatchlistItems]);

  const computeOrderSize = (entry: number, stop: number) => {
    const riskPerShare = Math.max(0.5, entry - stop);
    const maxByRisk = Math.floor(riskBudgetInr / riskPerShare);
    const maxByCap = Math.floor((accountCapitalInr * 0.2) / Math.max(1, entry));
    const qty = Math.max(1, Math.min(maxByRisk, maxByCap));
    return {
      qty,
      positionInr: qty * entry,
    };
  };

  const toggleBreakoutTag = (tag: BreakoutFilterTag) => {
    setSelectedBreakouts((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const toggleHvTag = (tag: HvFilterTag) => {
    setSelectedHvTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const activeThreshold =
    scoreBasis === 'call_score'
      ? minCallScore
      : scoreBasis === 'matrix_score'
      ? minMatrixScore
      : scoreBasis === 'sepa_score'
      ? minSepaScore
      : minCallScore === minMatrixScore && minMatrixScore === minSepaScore
      ? minCallScore
      : -1;

  const applyScorePreset = (val: number) => {
    if (scoreBasis === 'call_score') {
      setMinCallScore(val);
    } else if (scoreBasis === 'matrix_score') {
      setMinMatrixScore(val);
    } else if (scoreBasis === 'sepa_score') {
      setMinSepaScore(val);
    } else {
      setMinCallScore(val);
      setMinMatrixScore(val);
      setMinSepaScore(val);
    }
  };

  const handleResetFilters = () => {
    setLens('overall');
    setUniverseScope('all');
    setCapFilter('All');
    setSectorFilter('All');
    setScoreBasis('call_score');
    setMinCallScore(0);
    setMinMatrixScore(0);
    setMinSepaScore(0);
    setSelectedBreakouts([]);
    setSelectedHvTags([]);
  };

  const handleSetAlert = async (rec: TopBuyWatchlistItem) => {
    await addAlert({
      ticker: rec.stock.ticker,
      category: 'vcp_pivot',
      title: `${rec.stock.ticker} — Entry Trigger ${formatINR(rec.entryTriggerInr)} (${rec.rating})`,
      message: `TF Score ${rec.compositeScore}/100 · Matrix ${rec.technicalConsensus} ${rec.matrixScorePct}/100 (${rec.bullishSignals}/${rec.totalSignals}B) · SEPA ${rec.minerviniScore}/100 · ${rec.primarySetup} · Stop ${formatINR(rec.stopLossInr)} (-${rec.stopRiskPct.toFixed(1)}%) · 2R ${formatINR(rec.r2Inr, 0)}`,
    });
    setAlertedTickers((prev) => ({ ...prev, [rec.stock.ticker]: true }));
  };

  const handleWatchlistShown = async () => {
    if (!visibleWatchlistItems.length) return;
    await addManyToWatchlist(visibleWatchlistItems.map((r) => r.stock.ticker));
    setWatchlistSaved(true);
    setTimeout(() => setWatchlistSaved(false), 2500);
  };

  const handleExportCsv = () => {
    if (!visibleWatchlistItems.length) return;
    const headers = [
      'Rank',
      'Ticker',
      'Sector',
      'SectorQuadrant',
      'Cap',
      'Rating',
      'CallScore_100',
      'IndicatorsMatrixSummary_100',
      'MinerviniSEPA_100',
      'ATH_BO',
      '52W_BO',
      'HV_Tag',
      'MatrixConsensus',
      'MatrixSignals',
      'LTP_INR',
      'Change1D_Pct',
      'Stage',
      'TemplatePassed',
      'RSRating',
      'PrimarySetup',
      'QtrEpsYoY_Pct',
      'QtrRevYoY_Pct',
      'ROE_Pct',
      'EntryTrigger_INR',
      'StopLoss_INR',
      'StopRisk_Pct',
      'R2_INR',
      'R3_INR',
      'SizedQty',
      'Rationale',
    ];
    const rows = visibleWatchlistItems.map((r) => {
      const sz = computeOrderSize(r.entryTriggerInr, r.stopLossInr);
      const flags = eventFlagsByTicker.get(r.stock.ticker);
      return [
        r.rank,
        r.stock.ticker,
        `"${r.stock.sector}"`,
        r.sectorQuadrant ?? '',
        r.stock.capBucket,
        r.rating,
        r.compositeScore,
        r.matrixScorePct,
        r.minerviniScore,
        flags?.isAthBo ? 'YES' : 'NO',
        flags?.is52WBo ? 'YES' : 'NO',
        flags?.hvTag ?? '',
        r.technicalConsensus,
        `${r.bullishSignals}/${r.totalSignals}B`,
        r.stock.latestClose.toFixed(2),
        r.stock.dailyChangePct.toFixed(2),
        r.stage,
        `${r.templatePassed}/8`,
        r.rsRating,
        `"${r.primarySetup}"`,
        r.qtrEpsYoY.toFixed(1),
        r.qtrRevYoY.toFixed(1),
        r.roePct.toFixed(1),
        r.entryTriggerInr.toFixed(2),
        r.stopLossInr.toFixed(2),
        r.stopRiskPct.toFixed(2),
        r.r2Inr.toFixed(2),
        r.r3Inr.toFixed(2),
        sz.qty,
        `"${r.rationale.replace(/"/g, '""')}"`,
      ].join(',');
    });
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `personal-trades-top-buy-watchlist-${scoreBasis}-${lens}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const isFiltered =
    universeScope !== 'all' ||
    capFilter !== 'All' ||
    sectorFilter !== 'All' ||
    lens !== 'overall' ||
    hasAdvancedFilter;

  return (
    <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
      {/* Header & Strategy Controls */}
      <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-col gap-3">
        <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-baseline gap-2">
              <div className="flex items-center gap-2">
                <Award className="w-4 h-4 text-emerald-500 shrink-0" />
                <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  Top Buy Watchlist
                </h2>
              </div>
              <span className="font-mono tabular-nums text-[11px] font-semibold text-blue-600 dark:text-blue-400">
                Showing {visibleWatchlistItems.length.toLocaleString('en-IN')} of{' '}
                {matchedTotal.toLocaleString('en-IN')} matches ({stocks.length.toLocaleString('en-IN')} NSE stocks)
                {liveSymbolsCount > 0 && (
                  <span className="text-slate-500 font-normal">
                    {' '}
                    · {liveSymbolsCount.toLocaleString('en-IN')}/{totalUniverseCount.toLocaleString('en-IN')}{' '}
                    {isHydratingExtended ? 'syncing live…' : 'live'}
                  </span>
                )}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              100-pt confluence across NIFTY 500, F&amp;O, Midcap, Smallcap &amp; Microcap: Technical &amp; Trend Structure (60 — SEPA, Stage 2, RS &amp; Indicators Matrix Summary) · Actionable Setup &amp; Timing (15) · Fundamental Growth &amp; Quality (25)
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {/* Universe Scope Filter */}
            <div
              className="inline-flex items-center rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 p-0.5 text-[11px]"
              role="group"
              aria-label="NSE Universe Scope"
            >
              {UNIVERSE_SCOPE_OPTIONS.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => setUniverseScope(opt.id)}
                  className={`px-2 py-1 rounded-md transition-colors whitespace-nowrap ${
                    universeScope === opt.id
                      ? 'bg-blue-600 text-white font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {opt.label} <span className="font-mono text-[10px] opacity-80">{opt.count}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Row 2: Lens, Market Cap, Sector & Rows Limit */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          {/* Strategy Lens */}
          <div
            className="inline-flex items-center rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 p-0.5 text-[11px]"
            role="group"
            aria-label="Top Buy Watchlist Lens"
          >
            {(
              [
                { id: 'overall', label: 'Top Overall' },
                { id: 'actionable', label: 'Non-Extended' },
                { id: 'breakout', label: 'Breakouts & VCP' },
                { id: 'growth', label: 'High-Growth SEPA' },
              ] as { id: StrategyLens; label: string }[]
            ).map((opt) => (
              <button
                key={opt.id}
                onClick={() => setLens(opt.id)}
                className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap ${
                  lens === opt.id
                    ? 'bg-emerald-600 text-white font-semibold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Cap Filter */}
            <div
              className="inline-flex items-center rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 p-0.5 text-[11px]"
              role="group"
              aria-label="Market Cap Filter"
            >
              {(['All', 'Large', 'Mid', 'Small'] as CapFilter[]).map((cap) => (
                <button
                  key={cap}
                  onClick={() => setCapFilter(cap)}
                  className={`px-2 py-1 rounded-md transition-colors whitespace-nowrap ${
                    capFilter === cap
                      ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {cap === 'All' ? 'All Caps' : cap}
                </button>
              ))}
            </div>

            {/* Sector Filter */}
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              aria-label="Filter Top Buy Watchlist by Sector"
              className="px-2.5 py-1.5 text-[11px] font-medium rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="All">All Sectors ({sectorOptions.length})</option>
              {sectorOptions.map((sec) => (
                <option key={sec} value={sec}>
                  {sec}
                </option>
              ))}
            </select>

            {/* Display Limit */}
            <select
              value={displayLimit}
              onChange={(e) => setDisplayLimit(Number(e.target.value) as DisplayLimit)}
              aria-label="Rows to show"
              className="px-2 py-1.5 text-[11px] font-mono font-medium rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value={10}>Show 10</option>
              <option value={25}>Show 25</option>
              <option value={50}>Show 50</option>
              <option value={0}>Show All</option>
            </select>
          </div>
        </div>

        {/* Row 3: Score Filter Basis + Min Score Thresholds */}
        <div className="pt-2.5 border-t border-slate-200/70 dark:border-slate-800/70 flex flex-col lg:flex-row lg:items-center justify-between gap-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400 whitespace-nowrap">
              Score Filter Basis:
            </span>
            <div
              className="inline-flex flex-wrap items-center rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 p-0.5 text-[11px]"
              role="group"
              aria-label="Score Filter Basis"
            >
              {SCORE_BASIS_OPTIONS.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => setScoreBasis(opt.id)}
                  className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap ${
                    scoreBasis === opt.id
                      ? 'bg-blue-600 text-white font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Quick threshold presets */}
            <div className="inline-flex items-center rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 p-0.5 text-[11px] font-mono">
              {SCORE_PRESETS.map((val) => (
                <button
                  key={val}
                  onClick={() => applyScorePreset(val)}
                  className={`px-2 py-0.5 rounded transition-colors ${
                    activeThreshold === val
                      ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {val === 0 ? 'Any' : `≥${val}`}
                </button>
              ))}
            </div>

            {/* Numeric threshold input(s) */}
            {(scoreBasis === 'call_score' || scoreBasis === 'combined') && (
              <label className="inline-flex items-center gap-1.5 text-[11px] text-slate-600 dark:text-slate-400">
                <span>Call ≥</span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={5}
                  value={minCallScore}
                  onChange={(e) =>
                    setMinCallScore(Math.max(0, Math.min(100, Number(e.target.value) || 0)))
                  }
                  className="w-14 px-2 py-1 text-[11px] font-mono rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </label>
            )}
            {(scoreBasis === 'matrix_score' || scoreBasis === 'combined') && (
              <label className="inline-flex items-center gap-1.5 text-[11px] text-slate-600 dark:text-slate-400">
                <span>Matrix ≥</span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={5}
                  value={minMatrixScore}
                  onChange={(e) =>
                    setMinMatrixScore(Math.max(0, Math.min(100, Number(e.target.value) || 0)))
                  }
                  className="w-14 px-2 py-1 text-[11px] font-mono rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </label>
            )}
            {(scoreBasis === 'sepa_score' || scoreBasis === 'combined') && (
              <label className="inline-flex items-center gap-1.5 text-[11px] text-slate-600 dark:text-slate-400">
                <span>SEPA ≥</span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={5}
                  value={minSepaScore}
                  onChange={(e) =>
                    setMinSepaScore(Math.max(0, Math.min(100, Number(e.target.value) || 0)))
                  }
                  className="w-14 px-2 py-1 text-[11px] font-mono rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </label>
            )}
          </div>
        </div>

        {/* Row 4: Breakout (ATH BO / 52W BO) & High-Volume (HVE / HVY / HVQ) Filters */}
        <div className="flex flex-wrap items-center justify-between gap-2.5">
          <div className="flex flex-wrap items-center gap-3">
            {/* Breakout Filters */}
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                Breakout:
              </span>
              <button
                onClick={() => toggleBreakoutTag('ATH_BO')}
                className={`px-2.5 py-1 rounded-md border text-[11px] font-semibold transition-colors whitespace-nowrap ${
                  selectedBreakouts.includes('ATH_BO')
                    ? 'border-emerald-500 bg-emerald-600 text-white'
                    : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:border-emerald-500/60'
                }`}
                title="All-Time High Breakout within last 10 sessions (holding within 6% of breakout)"
              >
                ATH BO{' '}
                <span className="font-mono text-[10px] opacity-80">({eventCounts.athBo})</span>
              </button>
              <button
                onClick={() => toggleBreakoutTag('52W_BO')}
                className={`px-2.5 py-1 rounded-md border text-[11px] font-semibold transition-colors whitespace-nowrap ${
                  selectedBreakouts.includes('52W_BO')
                    ? 'border-blue-500 bg-blue-600 text-white'
                    : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:border-blue-500/60'
                }`}
                title="52-Week High Breakout within last 10 sessions (holding within 6% of breakout)"
              >
                52W BO{' '}
                <span className="font-mono text-[10px] opacity-80">({eventCounts.w52Bo})</span>
              </button>
            </div>

            <span className="hidden sm:inline text-slate-300 dark:text-slate-700">|</span>

            {/* High-Volume Milestone Filters */}
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                Volume Surge:
              </span>
              {(
                [
                  {
                    id: 'HVE',
                    count: eventCounts.hve,
                    activeCls: 'border-amber-500 bg-amber-600 text-white',
                    hoverCls: 'hover:border-amber-500/60',
                    title: 'Highest Volume Ever in last 10 sessions',
                  },
                  {
                    id: 'HVY',
                    count: eventCounts.hvy,
                    activeCls: 'border-violet-500 bg-violet-600 text-white',
                    hoverCls: 'hover:border-violet-500/60',
                    title: 'Highest Volume in Over a Year (252D) in last 10 sessions',
                  },
                  {
                    id: 'HVQ',
                    count: eventCounts.hvq,
                    activeCls: 'border-cyan-500 bg-cyan-600 text-white',
                    hoverCls: 'hover:border-cyan-500/60',
                    title: 'Highest Volume in a Quarter (63D) in last 10 sessions',
                  },
                ] as const
              ).map((hv) => (
                <button
                  key={hv.id}
                  onClick={() => toggleHvTag(hv.id)}
                  title={hv.title}
                  className={`px-2.5 py-1 rounded-md border text-[11px] font-semibold transition-colors whitespace-nowrap ${
                    selectedHvTags.includes(hv.id)
                      ? hv.activeCls
                      : `border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 ${hv.hoverCls}`
                  }`}
                >
                  {hv.id} <span className="font-mono text-[10px] opacity-80">({hv.count})</span>
                </button>
              ))}
            </div>
          </div>

          {isFiltered && (
            <button
              onClick={handleResetFilters}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium rounded-md border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-red-500/50 hover:text-red-500 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Telemetry & Execution Summary Strip */}
      <div className="px-5 py-2.5 border-b border-slate-200/80 dark:border-slate-800/80 bg-slate-50/70 dark:bg-slate-900/50 flex flex-wrap items-center justify-between gap-3 text-xs font-mono tabular-nums">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span>
            <span className="font-sans text-[11px] text-slate-500 mr-1.5">Strong Buys</span>
            <strong className="text-emerald-600 dark:text-emerald-400">
              {summary.strongBuys} / {visibleWatchlistItems.length}
            </strong>
          </span>
          <span className="text-slate-300 dark:text-slate-700">|</span>
          <span>
            <span className="font-sans text-[11px] text-slate-500 mr-1.5">Avg Call / Score</span>
            <strong className="text-slate-900 dark:text-slate-100">
              {summary.avgScore}/100
            </strong>
          </span>
          <span className="text-slate-300 dark:text-slate-700">|</span>
          <span>
            <span className="font-sans text-[11px] text-slate-500 mr-1.5">Avg Indicators Matrix</span>
            <strong className="text-emerald-600 dark:text-emerald-400">
              {summary.avgMatrixPct}/100
            </strong>
          </span>
          <span className="text-slate-300 dark:text-slate-700">|</span>
          <span>
            <span className="font-sans text-[11px] text-slate-500 mr-1.5">Avg SEPA</span>
            <strong className="text-blue-600 dark:text-blue-400">
              {summary.avgSepaScore}/100
            </strong>
          </span>
          <span className="text-slate-300 dark:text-slate-700">|</span>
          <span>
            <span className="font-sans text-[11px] text-slate-500 mr-1.5">Avg Qtr EPS YoY</span>
            <strong className="text-emerald-600 dark:text-emerald-400">
              +{summary.avgEpsYoY.toFixed(1)}%
            </strong>
          </span>
          <span className="text-slate-300 dark:text-slate-700">|</span>
          <span>
            <span className="font-sans text-[11px] text-slate-500 mr-1.5">Avg Stop Risk</span>
            <strong className="text-slate-900 dark:text-slate-100">
              -{summary.avgRiskPct.toFixed(1)}%
            </strong>
          </span>
          <span className="text-slate-300 dark:text-slate-700">|</span>
          <span>
            <span className="font-sans text-[11px] text-slate-500 mr-1.5">Sizing Basis</span>
            <strong className="text-slate-900 dark:text-slate-100">
              {defaultRiskPct}% ({formatINRCompact(riskBudgetInr)} / {formatINRCompact(accountCapitalInr)})
            </strong>
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2 font-sans">
          {regimeLabel && recommendedExposurePct !== undefined && (
            <span className="text-[11px] text-slate-500 dark:text-slate-400 mr-1">
              Regime: <strong className="text-slate-800 dark:text-slate-200">{regimeLabel}</strong> ·{' '}
              <span className="font-mono font-semibold text-blue-600 dark:text-blue-400">
                {recommendedExposurePct}%
              </span>{' '}
              exp
            </span>
          )}
          <button
            onClick={handleWatchlistShown}
            disabled={!visibleWatchlistItems.length}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:border-amber-500/60 hover:text-amber-600 dark:hover:text-amber-400 disabled:opacity-40 transition-colors whitespace-nowrap"
          >
            {watchlistSaved ? (
              <Check className="w-3 h-3 text-emerald-500" />
            ) : (
              <Star className="w-3 h-3 text-amber-500" />
            )}
            {watchlistSaved
              ? `Saved ${visibleWatchlistItems.length}`
              : `Watchlist (${visibleWatchlistItems.length})`}
          </button>
          <button
            onClick={handleExportCsv}
            disabled={!visibleWatchlistItems.length}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:border-blue-500/60 hover:text-blue-600 dark:hover:text-blue-400 disabled:opacity-40 transition-colors whitespace-nowrap"
          >
            <Download className="w-3 h-3" />
            CSV
          </button>
        </div>
      </div>

      {/* Ranked Institutional Buy Table */}
      {visibleWatchlistItems.length === 0 ? (
        <div className="p-8 text-center space-y-2.5">
          <div className="text-xs text-slate-500 dark:text-slate-400">
            No NSE stocks match the active score, breakout (ATH BO / 52W BO), high-volume (HVE / HVY / HVQ), cap, and sector filters.
          </div>
          {isFiltered && (
            <button
              onClick={handleResetFilters}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-blue-500/40 bg-blue-500/10 text-blue-600 dark:text-blue-400 hover:bg-blue-500/20 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset All Filters
            </button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
              <tr>
                <th className="py-2.5 pl-5 pr-2 w-10">#</th>
                <th className="py-2.5 px-3">Stock &amp; TechnoFunda Thesis</th>
                <th className="py-2.5 px-3">Call / Matrix / SEPA</th>
                <th className="py-2.5 px-3 text-right">LTP / 1D</th>
                <th className="py-2.5 px-3">SEPA &amp; Signals</th>
                <th className="py-2.5 px-3 text-right">Growth &amp; ROE</th>
                <th className="py-2.5 px-3 text-right">Entry &amp; Qty</th>
                <th className="py-2.5 px-3 text-right">Stop-Loss</th>
                <th className="py-2.5 px-3 text-right">2R / 3R Levels</th>
                <th className="py-2.5 pl-2 pr-5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
              {visibleWatchlistItems.map((rec) => {
                const watched = watchlist.includes(rec.stock.ticker);
                const alerted = Boolean(alertedTickers[rec.stock.ticker]);
                const orderSize = computeOrderSize(rec.entryTriggerInr, rec.stopLossInr);
                const flags = eventFlagsByTicker.get(rec.stock.ticker);
                const ratingTone =
                  rec.rating === 'Strong Buy'
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : rec.rating === 'Buy'
                    ? 'text-blue-600 dark:text-blue-400'
                    : 'text-amber-600 dark:text-amber-400';

                const matrixTone =
                  rec.technicalConsensus === 'Strong Buy' || rec.technicalConsensus === 'Buy'
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : rec.technicalConsensus === 'Neutral'
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-red-600 dark:text-red-400';

                return (
                  <tr
                    key={rec.stock.ticker}
                    onClick={() => onInspectStock(rec.stock.ticker)}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors cursor-pointer group"
                  >
                    {/* Rank */}
                    <td className="py-3 pl-5 pr-2 font-mono tabular-nums font-bold text-slate-400 dark:text-slate-500 align-top">
                      #{rec.rank}
                    </td>

                    {/* Ticker, Sector, Event Tags & Concise Buy Rationale */}
                    <td className="py-3 px-3 min-w-[240px] max-w-[320px] align-top">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="font-mono font-bold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                          {rec.stock.ticker}
                        </span>
                        <span className="text-[11px] text-slate-500 truncate">
                          {rec.stock.sector} · {rec.stock.capBucket}
                        </span>
                      </div>
                      {flags && (flags.isAthBo || flags.is52WBo || flags.hvTag) && (
                        <div className="flex flex-wrap items-center gap-1 mt-1 font-mono text-[10px] font-semibold">
                          {flags.isAthBo && (
                            <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                              ATH BO
                            </span>
                          )}
                          {flags.is52WBo && (
                            <span className="px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/30">
                              52W BO
                            </span>
                          )}
                          {flags.hvTag && (
                            <span
                              className={`px-1.5 py-0.5 rounded border ${
                                flags.hvTag === 'HVE'
                                  ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30'
                                  : flags.hvTag === 'HVY'
                                  ? 'bg-violet-500/15 text-violet-600 dark:text-violet-400 border-violet-500/30'
                                  : 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 border-cyan-500/30'
                              }`}
                            >
                              {flags.hvTag}
                            </span>
                          )}
                        </div>
                      )}
                      <div className="text-[11px] text-slate-600 dark:text-slate-400 mt-1 leading-snug">
                        {rec.rationale}
                      </div>
                    </td>

                    {/* Call / Score, Indicators Matrix Summary & Minervini SEPA Score */}
                    <td
                      className="py-3 px-3 align-top whitespace-nowrap"
                      title={`Call / Score: ${rec.compositeScore}/100 · Indicators Matrix Summary: ${rec.matrixScorePct}/100 (${rec.bullishSignals}/${rec.totalSignals}B) · Minervini SEPA Score: ${rec.minerviniScore}/100`}
                    >
                      <div className="flex items-baseline gap-1.5">
                        <span className={`font-bold text-xs ${ratingTone}`}>{rec.rating}</span>
                        <span className="font-mono tabular-nums text-[11px] font-semibold text-slate-900 dark:text-slate-100">
                          {rec.compositeScore}/100
                        </span>
                      </div>
                      <div className={`font-mono tabular-nums text-[10px] font-medium mt-0.5 ${matrixTone}`}>
                        Matrix: {rec.matrixScorePct}/100 ({rec.bullishSignals}/{rec.totalSignals}B)
                      </div>
                      <div className="font-mono tabular-nums text-[10px] text-blue-600 dark:text-blue-400 font-medium mt-0.5">
                        SEPA: {rec.minerviniScore}/100
                      </div>
                    </td>

                    {/* LTP & 1D Change */}
                    <td className="py-3 px-3 text-right font-mono tabular-nums align-top whitespace-nowrap">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">
                        {formatINR(rec.stock.latestClose)}
                      </div>
                      <div
                        className={`text-[11px] font-semibold mt-0.5 ${
                          rec.stock.dailyChangePct >= 0
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        {formatPct(rec.stock.dailyChangePct)}
                      </div>
                    </td>

                    {/* SEPA Template, RS, Sector Quadrant & Setup */}
                    <td className="py-3 px-3 font-mono tabular-nums align-top whitespace-nowrap">
                      <div className="text-slate-900 dark:text-slate-100 font-semibold">
                        S{rec.stage} · {rec.templatePassed}/8 · RS {rec.rsRating}
                      </div>
                      <div className="text-[11px] text-emerald-600 dark:text-emerald-400 mt-0.5">
                        {rec.primarySetup}
                        {rec.sectorQuadrant && (
                          <span className="text-slate-500 dark:text-slate-400">
                            {' '}
                            · {rec.sectorQuadrant}
                          </span>
                        )}
                      </div>
                      {rec.isExtended && (
                        <div className="font-sans text-[10px] text-amber-600 dark:text-amber-400">
                          Extended ({rec.distFrom50SmaAtrs.toFixed(1)} ATR above 50D)
                        </div>
                      )}
                    </td>

                    {/* Fundamentals: EPS YoY, Sales YoY, ROE */}
                    <td className="py-3 px-3 text-right font-mono tabular-nums align-top whitespace-nowrap">
                      <div
                        className={`font-semibold ${
                          rec.qtrEpsYoY >= 0
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        EPS {rec.qtrEpsYoY >= 0 ? '+' : ''}
                        {rec.qtrEpsYoY.toFixed(0)}%
                      </div>
                      <div className="text-[11px] text-slate-600 dark:text-slate-400 mt-0.5">
                        Rev {rec.qtrRevYoY >= 0 ? '+' : ''}
                        {rec.qtrRevYoY.toFixed(0)}% · ROE {rec.roePct.toFixed(0)}%
                      </div>
                    </td>

                    {/* Entry Trigger + Position Sizing */}
                    <td className="py-3 px-3 text-right font-mono tabular-nums align-top whitespace-nowrap">
                      <div className="font-semibold text-blue-600 dark:text-blue-400">
                        {formatINR(rec.entryTriggerInr)}
                      </div>
                      <div className="text-[10px] text-slate-600 dark:text-slate-400 mt-0.5">
                        {orderSize.qty} sh · {formatINRCompact(orderSize.positionInr)}
                      </div>
                    </td>

                    {/* Structural Stop-Loss */}
                    <td className="py-3 px-3 text-right font-mono tabular-nums align-top whitespace-nowrap">
                      <div className="font-semibold text-red-600 dark:text-red-400">
                        {formatINR(rec.stopLossInr)}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        -{rec.stopRiskPct.toFixed(1)}% · Vol {rec.volRatio50D.toFixed(1)}×
                      </div>
                    </td>

                    {/* 2R / 3R Mechanical Risk Multiples */}
                    <td className="py-3 px-3 text-right font-mono tabular-nums align-top whitespace-nowrap">
                      <div className="text-emerald-600 dark:text-emerald-400 font-semibold">
                        2R {formatINR(rec.r2Inr, 0)}
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        3R {formatINR(rec.r3Inr, 0)}
                      </div>
                    </td>

                    {/* Watchlist + Alert + Full Ticker Inspect */}
                    <td
                      className="py-3 pl-2 pr-5 text-right align-top whitespace-nowrap"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          onClick={() => toggleWatchlist(rec.stock.ticker)}
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
                          onClick={() => void handleSetAlert(rec)}
                          className={`p-1.5 rounded border transition-colors ${
                            alerted
                              ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-500'
                              : 'border-slate-200 dark:border-slate-700 text-slate-400 hover:text-blue-500 hover:border-blue-500/40'
                          }`}
                          title={
                            alerted
                              ? `Alert created for ${rec.stock.ticker}`
                              : `Set Entry Trigger Alert at ${formatINR(rec.entryTriggerInr)}`
                          }
                        >
                          {alerted ? (
                            <Check className="w-3.5 h-3.5" />
                          ) : (
                            <BellPlus className="w-3.5 h-3.5" />
                          )}
                        </button>
                        <button
                          onClick={() => onInspectStock(rec.stock.ticker)}
                          className="p-1.5 rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-blue-500 hover:border-blue-500/40 transition-colors"
                          title={`Open full TechnoFunda page for ${rec.stock.ticker}`}
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
        </div>
      )}
    </section>
  );
};
