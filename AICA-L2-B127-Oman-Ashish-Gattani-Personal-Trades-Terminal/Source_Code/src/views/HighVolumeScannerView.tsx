import React, { useMemo, useState } from 'react';
import {
  BarChart3,
  BellPlus,
  Check,
  Download,
  Flame,
  LineChart,
  Search,
  Star,
} from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import {
  INDIAN_STOCKS,
  UNIVERSE_COUNTS,
  matchesUniverseScope,
} from '../data/indianMarketData';
import { resolveStockSectorContext } from '../engine/sectorTrendEngine';
import {
  BuyRatingLabel,
  TopBuyWatchlistItem,
  computeTopBuyWatchlist,
} from '../engine/tradeRadarEngine';
import { MarketCapBucket, UniverseScope } from '../types/market';
import { formatINR, formatPct } from '../utils/formatters';

interface HighVolumeScannerViewProps {
  onInspectStock: (ticker: string) => void;
}

type HvTag = 'HVE' | 'HVY' | 'HVQ';
type HvFilterType = 'ALL' | HvTag;
type RecencyWindow = 1 | 5 | 10 | 20;
type CandleDirectionFilter = 'all' | 'green' | 'red';
type ScoreFilterMode = 'call_score' | 'matrix_score' | 'sepa_score' | 'combined';
type CallRatingFilter = 'all' | 'strong_buy' | 'buy_plus';
type CapFilter = 'All' | 'Large' | 'Mid' | 'Small';
type SortBy = 'recency_vol' | 'call_score' | 'matrix_score' | 'sepa_score' | 'vol_ratio';

interface HighVolumeScanRow {
  ticker: string;
  tag: HvTag;
  tagRank: number; // HVE=3, HVY=2, HVQ=1
  eventDate: string;
  barsAgo: number;
  barVolume: number;
  volRatio20D: number;
  barChangePct: number;
  isGreenBar: boolean;
  rec: TopBuyWatchlistItem;
}

const UNIVERSE_SCOPE_OPTIONS: { id: UniverseScope; label: string; count: number }[] = [
  { id: 'all', label: 'All NSE', count: UNIVERSE_COUNTS.total },
  { id: 'nifty500', label: 'NIFTY 500', count: UNIVERSE_COUNTS.nifty500 },
  { id: 'fno', label: 'F&O', count: UNIVERSE_COUNTS.fno },
  { id: 'midcap', label: 'Midcap', count: UNIVERSE_COUNTS.midcap },
  { id: 'smallcap', label: 'Smallcap', count: UNIVERSE_COUNTS.smallcap },
];

function matchesCap(bucket: MarketCapBucket, filter: CapFilter): boolean {
  if (filter === 'All') return true;
  if (filter === 'Small') return bucket === 'Small' || bucket === 'Micro';
  return bucket === filter;
}

function formatVolumeShares(v: number): string {
  if (v >= 1e7) return `${(v / 1e7).toFixed(2)} Cr`;
  if (v >= 1e5) return `${(v / 1e5).toFixed(2)} L`;
  return v.toLocaleString('en-IN');
}

export const HighVolumeScannerView: React.FC<HighVolumeScannerViewProps> = ({
  onInspectStock,
}) => {
  const {
    watchlist,
    toggleWatchlist,
    addManyToWatchlist,
    addAlert,
    marketVersion,
  } = useAppData();

  const [hvFilter, setHvFilter] = useState<HvFilterType>('ALL');
  const [recencyDays, setRecencyDays] = useState<RecencyWindow>(10);
  const [directionFilter, setDirectionFilter] = useState<CandleDirectionFilter>('all');
  const [scoreMode, setScoreMode] = useState<ScoreFilterMode>('call_score');
  const [minCallScore, setMinCallScore] = useState<number>(60);
  const [minMatrixScore, setMinMatrixScore] = useState<number>(60);
  const [minSepaScore, setMinSepaScore] = useState<number>(60);
  const [callRatingFilter, setCallRatingFilter] = useState<CallRatingFilter>('all');
  const [universeScope, setUniverseScope] = useState<UniverseScope>('all');
  const [capFilter, setCapFilter] = useState<CapFilter>('All');
  const [sectorFilter, setSectorFilter] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<SortBy>('call_score');
  const [toast, setToast] = useState<string | null>(null);
  const [alertedTickers, setAlertedTickers] = useState<Record<string, boolean>>({});

  const notify = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const sectorOptions = useMemo(
    () => Array.from(new Set(INDIAN_STOCKS.map((s) => s.sector))).sort(),
    []
  );

  // Scan the full NSE universe for HVE / HVY / HVQ volume milestones within the chosen recency window,
  // joined with exact 60/15/25 Call/Score, 16-Indicator Signal Matrix Summary, and Minervini SEPA Score.
  const allHvEvents = useMemo<HighVolumeScanRow[]>(() => {
    void marketVersion;
    const allRecs = computeTopBuyWatchlist(
      INDIAN_STOCKS,
      INDIAN_STOCKS.length,
      (sec, ind) => resolveStockSectorContext(INDIAN_STOCKS, sec, ind, marketVersion)
    );
    const recByTicker = new Map(allRecs.map((r) => [r.stock.ticker, r]));

    const rows: HighVolumeScanRow[] = [];
    const qtrLookback = 63;
    const yrLookback = 252;

    for (const stock of INDIAN_STOCKS) {
      const rec = recByTicker.get(stock.ticker);
      if (!rec) continue;
      const bars = stock.bars;
      if (!bars || bars.length < 70) continue;

      const lastIdx = bars.length - 1;
      const startScanIdx = Math.max(qtrLookback, lastIdx - (recencyDays - 1));

      // Precompute running all-time max up to startScanIdx - 1
      let runningMaxAll = 0;
      for (let i = 0; i < startScanIdx; i++) {
        if (bars[i].volume > runningMaxAll) runningMaxAll = bars[i].volume;
      }

      // Find the highest-priority (HVE > HVY > HVQ), most recent HV event inside the lookback window
      let bestHit: {
        tag: HvTag;
        tagRank: number;
        idx: number;
        vol: number;
        volRatio20D: number;
      } | null = null;

      for (let i = startScanIdx; i <= lastIdx; i++) {
        const vol = bars[i].volume;
        if (vol <= 0) continue;

        let tag: HvTag | null = null;
        let tagRank = 0;

        if (vol > runningMaxAll && i >= qtrLookback) {
          tag = 'HVE';
          tagRank = 3;
        } else {
          if (i >= yrLookback) {
            let maxYr = 0;
            for (let j = i - yrLookback; j < i; j++) {
              if (bars[j].volume > maxYr) maxYr = bars[j].volume;
            }
            if (vol > maxYr && maxYr > 0) {
              tag = 'HVY';
              tagRank = 2;
            }
          }
          if (!tag && i >= qtrLookback) {
            let maxQtr = 0;
            for (let j = i - qtrLookback; j < i; j++) {
              if (bars[j].volume > maxQtr) maxQtr = bars[j].volume;
            }
            if (vol > maxQtr && maxQtr > 0) {
              tag = 'HVQ';
              tagRank = 1;
            }
          }
        }

        if (vol > runningMaxAll) runningMaxAll = vol;

        if (tag) {
          // Compute 20-day average volume prior to this bar
          const avgStart = Math.max(0, i - 20);
          let sum20 = 0;
          let cnt20 = 0;
          for (let j = avgStart; j < i; j++) {
            sum20 += bars[j].volume;
            cnt20++;
          }
          const avg20 = cnt20 > 0 ? sum20 / cnt20 : vol;
          const volRatio20D = avg20 > 0 ? Number((vol / avg20).toFixed(2)) : 1;

          // Keep strongest tag (HVE > HVY > HVQ), or most recent if same priority
          if (!bestHit || tagRank > bestHit.tagRank || (tagRank === bestHit.tagRank && i > bestHit.idx)) {
            bestHit = { tag, tagRank, idx: i, vol, volRatio20D };
          }
        }
      }

      if (bestHit) {
        const bar = bars[bestHit.idx];
        const prevClose = bestHit.idx > 0 ? bars[bestHit.idx - 1].close : bar.open;
        const barChangePct = prevClose > 0 ? ((bar.close - prevClose) / prevClose) * 100 : 0;
        rows.push({
          ticker: stock.ticker,
          tag: bestHit.tag,
          tagRank: bestHit.tagRank,
          eventDate: bar.date,
          barsAgo: lastIdx - bestHit.idx,
          barVolume: bestHit.vol,
          volRatio20D: bestHit.volRatio20D,
          barChangePct,
          isGreenBar: bar.close >= bar.open,
          rec,
        });
      }
    }

    return rows;
  }, [recencyDays, marketVersion]);

  const filteredRows = useMemo(() => {
    const q = searchQuery.trim().toUpperCase();
    return allHvEvents
      .filter((row) => {
        if (hvFilter !== 'ALL' && row.tag !== hvFilter) return false;
        if (directionFilter === 'green' && !row.isGreenBar) return false;
        if (directionFilter === 'red' && row.isGreenBar) return false;
        if (!matchesUniverseScope(row.rec.stock, universeScope)) return false;
        if (!matchesCap(row.rec.stock.capBucket, capFilter)) return false;
        if (sectorFilter !== 'All' && row.rec.stock.sector !== sectorFilter) return false;

        if (callRatingFilter === 'strong_buy' && row.rec.rating !== 'Strong Buy') return false;
        if (
          callRatingFilter === 'buy_plus' &&
          row.rec.rating !== 'Strong Buy' &&
          row.rec.rating !== 'Buy'
        ) {
          return false;
        }

        // Score-based filtering by Call / Score, Multi-Indicator Signal Matrix Summary, Minervini SEPA, or Combined
        if (scoreMode === 'call_score') {
          if (row.rec.compositeScore < minCallScore) return false;
        } else if (scoreMode === 'matrix_score') {
          if (row.rec.matrixScorePct < minMatrixScore) return false;
        } else if (scoreMode === 'sepa_score') {
          if (row.rec.minerviniScore < minSepaScore) return false;
        } else {
          if (
            row.rec.compositeScore < minCallScore ||
            row.rec.matrixScorePct < minMatrixScore ||
            row.rec.minerviniScore < minSepaScore
          ) {
            return false;
          }
        }

        if (q) {
          const hit =
            row.ticker.includes(q) ||
            row.rec.stock.name.toUpperCase().includes(q) ||
            row.rec.stock.sector.toUpperCase().includes(q);
          if (!hit) return false;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'call_score') {
          if (b.rec.compositeScore !== a.rec.compositeScore) {
            return b.rec.compositeScore - a.rec.compositeScore;
          }
          return b.volRatio20D - a.volRatio20D;
        }
        if (sortBy === 'matrix_score') {
          if (b.rec.matrixScorePct !== a.rec.matrixScorePct) {
            return b.rec.matrixScorePct - a.rec.matrixScorePct;
          }
          return b.rec.compositeScore - a.rec.compositeScore;
        }
        if (sortBy === 'sepa_score') {
          if (b.rec.minerviniScore !== a.rec.minerviniScore) {
            return b.rec.minerviniScore - a.rec.minerviniScore;
          }
          return b.rec.rsRating - a.rec.rsRating;
        }
        if (sortBy === 'vol_ratio') {
          return b.volRatio20D - a.volRatio20D;
        }
        // recency_vol: HVE > HVY > HVQ, then most recent, then highest vol multiple
        if (b.tagRank !== a.tagRank) return b.tagRank - a.tagRank;
        if (a.barsAgo !== b.barsAgo) return a.barsAgo - b.barsAgo;
        return b.volRatio20D - a.volRatio20D;
      });
  }, [
    allHvEvents,
    hvFilter,
    directionFilter,
    universeScope,
    capFilter,
    sectorFilter,
    callRatingFilter,
    scoreMode,
    minCallScore,
    minMatrixScore,
    minSepaScore,
    searchQuery,
    sortBy,
  ]);

  const counts = useMemo(() => {
    const hve = allHvEvents.filter((r) => r.tag === 'HVE').length;
    const hvy = allHvEvents.filter((r) => r.tag === 'HVY').length;
    const hvq = allHvEvents.filter((r) => r.tag === 'HVQ').length;
    const strongBuys = filteredRows.filter((r) => r.rec.rating === 'Strong Buy').length;
    const avgCall = filteredRows.length
      ? Math.round(filteredRows.reduce((s, r) => s + r.rec.compositeScore, 0) / filteredRows.length)
      : 0;
    const avgMatrix = filteredRows.length
      ? Math.round(filteredRows.reduce((s, r) => s + r.rec.matrixScorePct, 0) / filteredRows.length)
      : 0;
    const avgSepa = filteredRows.length
      ? Math.round(filteredRows.reduce((s, r) => s + r.rec.minerviniScore, 0) / filteredRows.length)
      : 0;
    return { hve, hvy, hvq, strongBuys, avgCall, avgMatrix, avgSepa };
  }, [allHvEvents, filteredRows]);

  const handleWatchlistTop = async () => {
    const batch = filteredRows.slice(0, 25).map((r) => r.ticker);
    if (!batch.length) return;
    await addManyToWatchlist(batch);
    notify(`Added ${batch.length} HVE/HVY/HVQ stocks to your Watchlist.`);
  };

  const handleCreateAlert = async (row: HighVolumeScanRow) => {
    await addAlert({
      ticker: row.ticker,
      category: 'vcp_pivot',
      title: `${row.ticker} — ${row.tag} (${row.volRatio20D.toFixed(1)}× Vol) · ${row.rec.rating} ${row.rec.compositeScore}/100`,
      message: `${row.tag} on ${row.eventDate} (${formatVolumeShares(row.barVolume)}) · Call ${row.rec.compositeScore}/100 · Matrix ${row.rec.matrixScorePct}/100 · SEPA ${row.rec.minerviniScore}/100`,
    });
    setAlertedTickers((prev) => ({ ...prev, [row.ticker]: true }));
    notify(`Alert created for ${row.ticker}.`);
  };

  const handleExportCsv = () => {
    if (!filteredRows.length) return;
    const headers = [
      'Ticker',
      'VolumeMilestone',
      'EventDate',
      'BarsAgo',
      'VolumeShares',
      'VolRatio20D',
      'BarChange_Pct',
      'CallRating',
      'CallScore_100',
      'Tech_60',
      'Setup_15',
      'Funda_25',
      'SignalMatrixConsensus',
      'SignalMatrixScore_100',
      'MatrixSignals',
      'MinerviniSEPA_100',
      'Stage',
      'TemplatePassed',
      'RSRating',
      'Sector',
      'SectorQuadrant',
      'LTP_INR',
      'EntryTrigger_INR',
      'StopLoss_INR',
      'R2_INR',
    ];
    const csvRows = filteredRows.map((row) => [
      row.ticker,
      row.tag,
      row.eventDate,
      row.barsAgo,
      row.barVolume,
      row.volRatio20D.toFixed(2),
      row.barChangePct.toFixed(2),
      row.rec.rating,
      row.rec.compositeScore,
      row.rec.techScore,
      row.rec.setupScore,
      row.rec.fundaScore,
      row.rec.technicalConsensus,
      row.rec.matrixScorePct,
      `${row.rec.bullishSignals}/${row.rec.totalSignals}B`,
      row.rec.minerviniScore,
      row.rec.stage,
      `${row.rec.templatePassed}/8`,
      row.rec.rsRating,
      `"${row.rec.stock.sector}"`,
      row.rec.sectorQuadrant ?? '',
      row.rec.stock.latestClose.toFixed(2),
      row.rec.entryTriggerInr.toFixed(2),
      row.rec.stopLossInr.toFixed(2),
      row.rec.r2Inr.toFixed(2),
    ]);
    const csv = [headers.join(','), ...csvRows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hv-screener-${hvFilter.toLowerCase()}-${recencyDays}d.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const activeThresholdValue =
    scoreMode === 'call_score'
      ? minCallScore
      : scoreMode === 'matrix_score'
      ? minMatrixScore
      : minSepaScore;

  const setActiveThresholdValue = (val: number) => {
    const clamped = Math.max(0, Math.min(100, val));
    if (scoreMode === 'call_score') setMinCallScore(clamped);
    else if (scoreMode === 'matrix_score') setMinMatrixScore(clamped);
    else setMinSepaScore(clamped);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Flame className="w-5 h-5 text-amber-500 shrink-0" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              HVE / HVY / HVQ Institutional Volume Screener
            </h1>
          </div>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Detects <strong className="text-amber-600 dark:text-amber-400">HVE</strong> (Highest Volume Ever),{' '}
            <strong className="text-sky-600 dark:text-sky-400">HVY</strong> (Highest Volume in Over a Year), and{' '}
            <strong className="text-purple-600 dark:text-purple-400">HVQ</strong> (Highest Volume in a Quarter) across{' '}
            {INDIAN_STOCKS.length.toLocaleString('en-IN')} NSE stocks — filterable by Call / Score, Indicators Matrix Summary, or Minervini SEPA Score.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 self-start lg:self-auto">
          <button
            type="button"
            onClick={() => void handleWatchlistTop()}
            disabled={filteredRows.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 hover:border-amber-500/60 disabled:opacity-40 whitespace-nowrap"
          >
            <Star className="w-3.5 h-3.5 text-amber-500" />
            Watchlist Top {Math.min(25, filteredRows.length)}
          </button>
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={filteredRows.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 whitespace-nowrap"
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

      {/* KPI Summary Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-3.5">
          <div className="text-[11px] text-slate-500">Matched Stocks</div>
          <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-1">
            {filteredRows.length}
          </div>
          <div className="text-[11px] text-slate-500 font-mono">
            of {allHvEvents.length} HV events ({recencyDays}D)
          </div>
        </div>

        <button
          type="button"
          onClick={() => setHvFilter((v) => (v === 'HVE' ? 'ALL' : 'HVE'))}
          className={`text-left border rounded-xl p-3.5 transition-colors ${
            hvFilter === 'HVE'
              ? 'border-amber-500 bg-amber-500/10'
              : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] hover:border-amber-500/50'
          }`}
        >
          <div className="text-[11px] text-amber-600 dark:text-amber-400 font-semibold">HVE (Ever)</div>
          <div className="text-xl font-bold font-mono tabular-nums text-amber-600 dark:text-amber-400 mt-1">
            {counts.hve}
          </div>
          <div className="text-[11px] text-slate-500">All-time volume record</div>
        </button>

        <button
          type="button"
          onClick={() => setHvFilter((v) => (v === 'HVY' ? 'ALL' : 'HVY'))}
          className={`text-left border rounded-xl p-3.5 transition-colors ${
            hvFilter === 'HVY'
              ? 'border-sky-500 bg-sky-500/10'
              : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] hover:border-sky-500/50'
          }`}
        >
          <div className="text-[11px] text-sky-600 dark:text-sky-400 font-semibold">HVY (1 Year+)</div>
          <div className="text-xl font-bold font-mono tabular-nums text-sky-600 dark:text-sky-400 mt-1">
            {counts.hvy}
          </div>
          <div className="text-[11px] text-slate-500">252-day volume high</div>
        </button>

        <button
          type="button"
          onClick={() => setHvFilter((v) => (v === 'HVQ' ? 'ALL' : 'HVQ'))}
          className={`text-left border rounded-xl p-3.5 transition-colors ${
            hvFilter === 'HVQ'
              ? 'border-purple-500 bg-purple-500/10'
              : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] hover:border-purple-500/50'
          }`}
        >
          <div className="text-[11px] text-purple-600 dark:text-purple-400 font-semibold">HVQ (Quarter)</div>
          <div className="text-xl font-bold font-mono tabular-nums text-purple-600 dark:text-purple-400 mt-1">
            {counts.hvq}
          </div>
          <div className="text-[11px] text-slate-500">63-day volume high</div>
        </button>

        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-3.5">
          <div className="text-[11px] text-slate-500">Avg Call / Matrix</div>
          <div className="text-xl font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400 mt-1">
            {counts.avgCall} <span className="text-slate-400 text-sm">/</span> {counts.avgMatrix}
          </div>
          <div className="text-[11px] text-slate-500">{counts.strongBuys} Strong Buys</div>
        </div>

        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-3.5">
          <div className="text-[11px] text-slate-500">Avg Minervini SEPA</div>
          <div className="text-xl font-bold font-mono tabular-nums text-blue-600 dark:text-blue-400 mt-1">
            {counts.avgSepa}/100
          </div>
          <div className="text-[11px] text-slate-500">Trend Template strength</div>
        </div>
      </div>

      {/* Filter & Score Control Panel */}
      <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 space-y-3.5">
        {/* Row 1: Volume Milestone + Recency Window + Candle Direction + Universe Scope */}
        <div className="flex flex-wrap items-center justify-between gap-2.5">
          <div className="flex flex-wrap items-center gap-2">
            {/* HV Type */}
            <div className="inline-flex items-center p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-[11px]">
              {(
                [
                  { id: 'ALL', label: 'All HV' },
                  { id: 'HVE', label: 'HVE Only' },
                  { id: 'HVY', label: 'HVY Only' },
                  { id: 'HVQ', label: 'HVQ Only' },
                ] as { id: HvFilterType; label: string }[]
              ).map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setHvFilter(opt.id)}
                  className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap ${
                    hvFilter === opt.id
                      ? opt.id === 'HVE'
                        ? 'bg-amber-500 text-white font-semibold'
                        : opt.id === 'HVY'
                        ? 'bg-sky-500 text-white font-semibold'
                        : opt.id === 'HVQ'
                        ? 'bg-purple-500 text-white font-semibold'
                        : 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold'
                      : 'text-slate-600 dark:text-slate-400'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {/* Recency Window */}
            <div className="inline-flex items-center p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-[11px]">
              {(
                [
                  { days: 1, label: 'Latest (1D)' },
                  { days: 5, label: 'Last 5D' },
                  { days: 10, label: 'Last 10D' },
                  { days: 20, label: 'Last 20D' },
                ] as { days: RecencyWindow; label: string }[]
              ).map((opt) => (
                <button
                  key={opt.days}
                  type="button"
                  onClick={() => setRecencyDays(opt.days)}
                  className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap ${
                    recencyDays === opt.days
                      ? 'bg-blue-600 text-white font-semibold'
                      : 'text-slate-600 dark:text-slate-400'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {/* Candle Direction */}
            <div className="inline-flex items-center p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-[11px]">
              {(
                [
                  { id: 'all', label: 'All Bars' },
                  { id: 'green', label: 'Up / Accum' },
                  { id: 'red', label: 'Down / Dist' },
                ] as { id: CandleDirectionFilter; label: string }[]
              ).map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setDirectionFilter(opt.id)}
                  className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap ${
                    directionFilter === opt.id
                      ? opt.id === 'green'
                        ? 'bg-emerald-600 text-white font-semibold'
                        : opt.id === 'red'
                        ? 'bg-red-600 text-white font-semibold'
                        : 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold'
                      : 'text-slate-600 dark:text-slate-400'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Universe Scope */}
          <div className="inline-flex items-center p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-[11px]">
            {UNIVERSE_SCOPE_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setUniverseScope(opt.id)}
                className={`px-2 py-1 rounded-md transition-colors whitespace-nowrap ${
                  universeScope === opt.id
                    ? 'bg-blue-600 text-white font-semibold'
                    : 'text-slate-600 dark:text-slate-400'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Row 2: Score Filter Basis — Call / Score | Multi-Indicator Signal Matrix | Minervini SEPA | Combined */}
        <div className="pt-3 border-t border-slate-200/80 dark:border-slate-800/80 flex flex-col xl:flex-row xl:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">
              Score Filter Basis:
            </span>
            <div className="inline-flex items-center p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-[11px]">
              {(
                [
                  { id: 'call_score', label: 'Call / Score' },
                  { id: 'matrix_score', label: 'Indicators Matrix Summary' },
                  { id: 'sepa_score', label: 'Minervini SEPA Score' },
                  { id: 'combined', label: 'All 3 Combined' },
                ] as { id: ScoreFilterMode; label: string }[]
              ).map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => {
                    setScoreMode(opt.id);
                    if (opt.id === 'call_score') setSortBy('call_score');
                    else if (opt.id === 'matrix_score') setSortBy('matrix_score');
                    else if (opt.id === 'sepa_score') setSortBy('sepa_score');
                  }}
                  className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap ${
                    scoreMode === opt.id
                      ? 'bg-emerald-600 text-white font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {scoreMode !== 'combined' ? (
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="text-[11px] text-slate-500">Min Score:</span>
                <div className="inline-flex items-center gap-1">
                  {[0, 50, 60, 70, 75, 80].map((v) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => setActiveThresholdValue(v)}
                      className={`px-2 py-1 rounded-md font-mono text-[11px] border transition-colors ${
                        activeThresholdValue === v
                          ? 'border-blue-600 bg-blue-600 text-white font-semibold'
                          : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-blue-500/50'
                      }`}
                    >
                      {v === 0 ? 'Any' : `≥${v}`}
                    </button>
                  ))}
                </div>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={activeThresholdValue}
                  onChange={(e) => setActiveThresholdValue(Number(e.target.value) || 0)}
                  aria-label="Minimum Score Threshold"
                  className="w-16 px-2 py-1 text-xs font-mono tabular-nums rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                />
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-3 text-[11px]">
                <label className="inline-flex items-center gap-1.5">
                  <span className="text-slate-500">Call ≥</span>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={minCallScore}
                    onChange={(e) => setMinCallScore(Math.max(0, Math.min(100, Number(e.target.value) || 0)))}
                    className="w-14 px-2 py-1 font-mono rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  />
                </label>
                <label className="inline-flex items-center gap-1.5">
                  <span className="text-slate-500">Matrix ≥</span>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={minMatrixScore}
                    onChange={(e) => setMinMatrixScore(Math.max(0, Math.min(100, Number(e.target.value) || 0)))}
                    className="w-14 px-2 py-1 font-mono rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  />
                </label>
                <label className="inline-flex items-center gap-1.5">
                  <span className="text-slate-500">SEPA ≥</span>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={minSepaScore}
                    onChange={(e) => setMinSepaScore(Math.max(0, Math.min(100, Number(e.target.value) || 0)))}
                    className="w-14 px-2 py-1 font-mono rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                  />
                </label>
              </div>
            )}
          </div>

          {/* Secondary Filters: Call Rating, Cap, Sector, Sort, Search */}
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={callRatingFilter}
              onChange={(e) => setCallRatingFilter(e.target.value as CallRatingFilter)}
              aria-label="Filter by Call Rating"
              className="px-2.5 py-1.5 text-[11px] font-medium rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-200"
            >
              <option value="all">All Calls</option>
              <option value="buy_plus">Strong Buy &amp; Buy</option>
              <option value="strong_buy">Strong Buy Only</option>
            </select>

            <select
              value={capFilter}
              onChange={(e) => setCapFilter(e.target.value as CapFilter)}
              aria-label="Filter by Market Cap"
              className="px-2.5 py-1.5 text-[11px] font-medium rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-200"
            >
              <option value="All">All Caps</option>
              <option value="Large">Large Cap</option>
              <option value="Mid">Mid Cap</option>
              <option value="Small">Small / Micro</option>
            </select>

            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              aria-label="Filter by Sector"
              className="px-2.5 py-1.5 text-[11px] font-medium rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-200"
            >
              <option value="All">All Sectors ({sectorOptions.length})</option>
              {sectorOptions.map((sec) => (
                <option key={sec} value={sec}>
                  {sec}
                </option>
              ))}
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortBy)}
              aria-label="Sort results"
              className="px-2.5 py-1.5 text-[11px] font-medium rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-200"
            >
              <option value="call_score">Sort: Call / Score</option>
              <option value="matrix_score">Sort: Indicators Matrix Summary</option>
              <option value="sepa_score">Sort: Minervini SEPA</option>
              <option value="vol_ratio">Sort: Vol Multiple (20D)</option>
              <option value="recency_vol">Sort: HVE → HVY → HVQ</option>
            </select>

            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search ticker…"
                className="w-32 sm:w-40 pl-8 pr-2.5 py-1.5 text-[11px] rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Screener Table */}
      <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 font-bold text-slate-900 dark:text-slate-100">
            <BarChart3 className="w-4 h-4 text-blue-500" />
            <span>
              Institutional Volume Footprints ({filteredRows.length} Stocks)
            </span>
          </div>
          <span className="text-[11px] text-slate-500">
            Click any row to inspect the volume candle chart with HVE / HVY / HVQ plotted directly above the bar
          </span>
        </div>

        {filteredRows.length === 0 ? (
          <div className="p-10 text-center text-xs text-slate-500 space-y-2">
            <div>No NSE stocks match the current HVE/HVY/HVQ and score filter criteria.</div>
            <div>Try lowering the minimum score threshold or widening the lookback window to 10D / 20D.</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                <tr>
                  <th className="py-2.5 pl-5 pr-3">Stock &amp; Sector</th>
                  <th className="py-2.5 px-3">HV Signal &amp; Bar</th>
                  <th className="py-2.5 px-3">Call / Score (60/15/25)</th>
                  <th className="py-2.5 px-3">Indicators Matrix Summary</th>
                  <th className="py-2.5 px-3">Minervini SEPA</th>
                  <th className="py-2.5 px-3 text-right">LTP / 1D</th>
                  <th className="py-2.5 px-3 text-right">Entry / Stop / 2R</th>
                  <th className="py-2.5 pl-2 pr-5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                {filteredRows.slice(0, 120).map((row) => {
                  const rec = row.rec;
                  const watched = watchlist.includes(row.ticker);
                  const alerted = Boolean(alertedTickers[row.ticker]);

                  const tagStyle =
                    row.tag === 'HVE'
                      ? 'text-amber-600 dark:text-amber-400 border-amber-500/40 bg-amber-500/10'
                      : row.tag === 'HVY'
                      ? 'text-sky-600 dark:text-sky-400 border-sky-500/40 bg-sky-500/10'
                      : 'text-purple-600 dark:text-purple-400 border-purple-500/40 bg-purple-500/10';

                  const callColor =
                    rec.rating === 'Strong Buy'
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : rec.rating === 'Buy'
                      ? 'text-blue-600 dark:text-blue-400'
                      : 'text-amber-600 dark:text-amber-400';

                  const matrixColor =
                    rec.technicalConsensus === 'Strong Buy' || rec.technicalConsensus === 'Buy'
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : rec.technicalConsensus === 'Neutral'
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-red-600 dark:text-red-400';

                  return (
                    <tr
                      key={row.ticker}
                      onClick={() => onInspectStock(row.ticker)}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors cursor-pointer group"
                    >
                      <td className="py-3 pl-5 pr-3 align-top whitespace-nowrap">
                        <div className="font-mono font-bold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                          {row.ticker}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {rec.stock.sector}
                          {rec.sectorQuadrant && (
                            <span className="ml-1 font-medium text-slate-600 dark:text-slate-400">
                              · {rec.sectorQuadrant}
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="py-3 px-3 align-top whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-1.5 py-0.5 font-mono text-[10px] font-bold rounded border ${tagStyle}`}
                          >
                            {row.tag}
                          </span>
                          <span className="font-mono font-semibold text-slate-900 dark:text-slate-100 tabular-nums">
                            {row.volRatio20D.toFixed(1)}× avg
                          </span>
                          <span
                            className={`font-mono text-[11px] font-semibold tabular-nums ${
                              row.barChangePct >= 0
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-red-600 dark:text-red-400'
                            }`}
                          >
                            {formatPct(row.barChangePct)}
                          </span>
                        </div>
                        <div className="font-mono text-[10px] text-slate-500 tabular-nums mt-0.5">
                          {formatVolumeShares(row.barVolume)} ·{' '}
                          {row.barsAgo === 0 ? 'Latest Bar' : `${row.barsAgo}D ago (${row.eventDate})`}
                        </div>
                      </td>

                      <td
                        className="py-3 px-3 align-top whitespace-nowrap"
                        title={`Technical & Trend ${rec.techScore}/60 · Setup ${rec.setupScore}/15 · Fundamentals ${rec.fundaScore}/25`}
                      >
                        <div className="flex items-baseline gap-1.5">
                          <span className={`font-bold ${callColor}`}>{rec.rating as BuyRatingLabel}</span>
                          <span className="font-mono font-bold tabular-nums text-slate-900 dark:text-slate-100">
                            {rec.compositeScore}/100
                          </span>
                        </div>
                        <div className="font-mono text-[10px] text-slate-500 tabular-nums mt-0.5">
                          T{rec.techScore} · S{rec.setupScore} · F{rec.fundaScore}
                        </div>
                      </td>

                      <td className="py-3 px-3 align-top whitespace-nowrap">
                        <div className={`font-mono font-bold tabular-nums ${matrixColor}`}>
                          {rec.technicalConsensus} · {rec.matrixScorePct}/100
                        </div>
                        <div className="font-mono text-[10px] text-slate-500 tabular-nums mt-0.5">
                          {rec.bullishSignals}B · {rec.neutralSignals}N · {rec.bearishSignals}S / {rec.totalSignals}
                        </div>
                      </td>

                      <td className="py-3 px-3 align-top whitespace-nowrap font-mono tabular-nums">
                        <div
                          className={`font-bold ${
                            rec.minerviniScore >= 70
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : rec.minerviniScore >= 50
                              ? 'text-blue-600 dark:text-blue-400'
                              : 'text-amber-600 dark:text-amber-400'
                          }`}
                        >
                          {rec.minerviniScore}/100 · {rec.templatePassed}/8
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          Stage {rec.stage} · RS {rec.rsRating} · {rec.primarySetup}
                        </div>
                      </td>

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

                      <td className="py-3 px-3 text-right font-mono tabular-nums align-top whitespace-nowrap">
                        <div className="text-blue-600 dark:text-blue-400 font-semibold">
                          E {formatINR(rec.entryTriggerInr, 0)} · 2R {formatINR(rec.r2Inr, 0)}
                        </div>
                        <div className="text-[10px] text-red-600 dark:text-red-400 mt-0.5">
                          SL {formatINR(rec.stopLossInr, 0)} (-{rec.stopRiskPct.toFixed(1)}%)
                        </div>
                      </td>

                      <td
                        className="py-3 pl-2 pr-5 text-right align-top whitespace-nowrap"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="inline-flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => void toggleWatchlist(row.ticker)}
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
                            type="button"
                            onClick={() => void handleCreateAlert(row)}
                            className={`p-1.5 rounded border transition-colors ${
                              alerted
                                ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-500'
                                : 'border-slate-200 dark:border-slate-700 text-slate-400 hover:text-blue-500'
                            }`}
                            title="Create Volume Footprint Alert"
                          >
                            {alerted ? (
                              <Check className="w-3.5 h-3.5" />
                            ) : (
                              <BellPlus className="w-3.5 h-3.5" />
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => onInspectStock(row.ticker)}
                            className="p-1.5 rounded border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-blue-500"
                            title={`Inspect ${row.ticker} chart`}
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
    </div>
  );
};
