import React, { useMemo, useState } from 'react';
import {
  ArrowUpRight,
  Compass,
  Download,
  Layers,
  Search,
  SlidersHorizontal,
} from 'lucide-react';
import {
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';
import { NiftySectorHeatmap } from '../components/NiftySectorHeatmap';
import { useAppData } from '../context/AppDataContext';
import { INDIAN_STOCKS, STOCK_BY_TICKER } from '../data/indianMarketData';
import {
  computeTrendingSectorsAndSubsectors,
  RotationQuadrant,
  SCORING_PRESETS,
  ScoringPresetId,
  TechnicalGroupScore,
  TrendRegimeLabel,
} from '../engine/sectorTrendEngine';
import {
  CallScoreSummary,
  computeSingleStockCallScore,
} from '../engine/tradeRadarEngine';
import { formatCr, formatINR, formatPct } from '../utils/formatters';

interface TrendingSectorsViewProps {
  onInspectStock: (ticker: string) => void;
}

type GroupViewMode = 'sectors' | 'subsectors';
type ReturnHorizon = '1W' | '1M' | '3M' | '6M' | '1Y';
type SortKey = 'score' | 'return' | 'rsRating' | 'rsi' | 'adx' | 'breadth50' | 'volThrust';

const QUADRANT_COLOR: Record<RotationQuadrant, string> = {
  Leading: '#10b981',
  Improving: '#3b82f6',
  Weakening: '#f59e0b',
  Lagging: '#ef4444',
};

const QUADRANT_TEXT_CLASS: Record<RotationQuadrant, string> = {
  Leading: 'text-emerald-600 dark:text-emerald-400',
  Improving: 'text-blue-600 dark:text-blue-400',
  Weakening: 'text-amber-600 dark:text-amber-400',
  Lagging: 'text-red-600 dark:text-red-400',
};

const REGIME_TEXT_CLASS: Record<TrendRegimeLabel, string> = {
  'Strong Uptrend': 'text-emerald-600 dark:text-emerald-400',
  'Trending Bullish': 'text-blue-600 dark:text-blue-400',
  'Emerging / Base': 'text-amber-600 dark:text-amber-400',
  'Neutral / Weakening': 'text-slate-600 dark:text-slate-400',
  Downtrend: 'text-red-600 dark:text-red-400',
};

function getHorizonReturn(item: TechnicalGroupScore, horizon: ReturnHorizon): number {
  switch (horizon) {
    case '1W':
      return item.return1WPct;
    case '1M':
      return item.return1MPct;
    case '3M':
      return item.return3MPct;
    case '6M':
      return item.return6MPct;
    case '1Y':
      return item.return1YPct;
  }
}

export const TrendingSectorsView: React.FC<TrendingSectorsViewProps> = ({ onInspectStock }) => {
  const { marketVersion } = useAppData();

  const [viewMode, setViewMode] = useState<GroupViewMode>('sectors');
  const [presetId, setPresetId] = useState<ScoringPresetId>('balanced');
  const [horizon, setHorizon] = useState<ReturnHorizon>('3M');
  const [quadrantFilter, setQuadrantFilter] = useState<'All' | RotationQuadrant>('All');
  const [parentSectorFilter, setParentSectorFilter] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<SortKey>('score');
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);

  const report = useMemo(
    () => computeTrendingSectorsAndSubsectors(INDIAN_STOCKS, presetId),
    [marketVersion, presetId]
  );

  const activePreset = SCORING_PRESETS[presetId];
  const baseList = viewMode === 'sectors' ? report.sectors : report.subsectors;

  const parentSectors = useMemo(
    () => ['All', ...report.sectors.map((s) => s.name).sort()],
    [report.sectors]
  );

  const filteredList = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const list = baseList.filter((item) => {
      if (quadrantFilter !== 'All' && item.quadrant !== quadrantFilter) return false;
      if (viewMode === 'subsectors' && parentSectorFilter !== 'All' && item.parentSector !== parentSectorFilter) {
        return false;
      }
      if (q) {
        const matchesName = item.name.toLowerCase().includes(q);
        const matchesParent = item.parentSector.toLowerCase().includes(q);
        const matchesStock = item.constituents.some(
          (c) => c.ticker.toLowerCase().includes(q) || c.name.toLowerCase().includes(q)
        );
        if (!matchesName && !matchesParent && !matchesStock) return false;
      }
      return true;
    });

    return [...list].sort((a, b) => {
      switch (sortBy) {
        case 'return':
          return getHorizonReturn(b, horizon) - getHorizonReturn(a, horizon);
        case 'rsRating':
          return b.avgRsRating - a.avgRsRating;
        case 'rsi':
          return b.rsi14 - a.rsi14;
        case 'adx':
          return b.adx14 - a.adx14;
        case 'breadth50':
          return b.pctAbove50Sma - a.pctAbove50Sma;
        case 'volThrust':
          return b.volumeThrustRatio - a.volumeThrustRatio;
        case 'score':
        default:
          return b.compositeScore - a.compositeScore || b.rsRatio - a.rsRatio;
      }
    });
  }, [baseList, quadrantFilter, viewMode, parentSectorFilter, searchQuery, sortBy, horizon]);

  const selectedGroup: TechnicalGroupScore | null = useMemo(() => {
    if (selectedGroupId) {
      const found = baseList.find((g) => g.id === selectedGroupId);
      if (found) return found;
    }
    return filteredList[0] ?? baseList[0] ?? null;
  }, [selectedGroupId, baseList, filteredList]);

  // Compute Call / Score (60/15/25) + Multi-Indicator Signal Matrix Summary for selected group's constituents
  const constituentCallScores = useMemo(() => {
    const map = new Map<string, CallScoreSummary>();
    if (!selectedGroup) return map;
    for (const c of selectedGroup.constituents) {
      const stock = STOCK_BY_TICKER[c.ticker];
      if (!stock || !stock.bars || stock.bars.length < 30) continue;
      const rankIdx = Math.max(
        1,
        report.sectors.findIndex(
          (s) => s.name === (selectedGroup.parentSector || selectedGroup.name)
        ) + 1
      );
      const summary = computeSingleStockCallScore({
        ticker: c.ticker,
        universe: INDIAN_STOCKS,
        bars: stock.bars,
        sectorFallback: {
          sectorName: selectedGroup.parentSector || selectedGroup.name,
          sectorScore: selectedGroup.compositeScore,
          sectorRank: rankIdx,
          sectorTotal: Math.max(1, report.sectors.length),
          sectorQuadrant: selectedGroup.quadrant,
          sectorRegime: selectedGroup.regime,
          sectorRsRatio: selectedGroup.rsRatio,
          sectorRsMomentum: selectedGroup.rsMomentum,
        },
      });
      if (summary) {
        map.set(c.ticker, summary);
      }
    }
    return map;
  }, [selectedGroup, marketVersion]);

  // RRG chart points (all sectors, or top 18 filtered subsectors so labels stay crisp)
  const rrgPoints = useMemo(() => {
    const source = filteredList.length > 0 ? filteredList : baseList;
    return source.slice(0, 18).map((g) => ({
      id: g.id,
      name: g.name,
      parentSector: g.parentSector,
      rsRatio: g.rsRatio,
      rsMomentum: g.rsMomentum,
      score: g.compositeScore,
      quadrant: g.quadrant,
      rsi14: g.rsi14,
      adx14: g.adx14,
      smaStackLabel: g.smaStackLabel,
      return3MPct: g.return3MPct,
      topLeader: g.topLeader?.ticker ?? '—',
      size: Math.max(80, g.compositeScore * 2.4),
    }));
  }, [filteredList, baseList]);

  const topSector = report.sectors[0];
  const topSubsector = report.subsectors[0];

  const handleDrillToSubsectors = (sectorName: string) => {
    setViewMode('subsectors');
    setParentSectorFilter(sectorName);
    setQuadrantFilter('All');
    setSelectedGroupId(null);
  };

  const handleExportCsv = () => {
    const headers = [
      'Rank',
      viewMode === 'sectors' ? 'Sector' : 'Subsector',
      'Parent Sector',
      'Stocks',
      'Trend Score (0-100)',
      'Regime',
      'RRG Quadrant',
      'Trend Pillar',
      'RS Pillar',
      'Momentum Pillar',
      'Breadth Pillar',
      'SMA Stack',
      'RSI (14)',
      'ADX (14)',
      'MACD State',
      'Avg RS Rating',
      'RS-Ratio',
      'RS-Momentum',
      '% > 50 SMA',
      '% Stage 2',
      'Vol Thrust',
      '1M %',
      '3M %',
      'Top Leader',
    ];
    const rows = filteredList.map((g, idx) => [
      String(idx + 1),
      g.name,
      g.parentSector,
      String(g.stockCount),
      String(g.compositeScore),
      g.regime,
      g.quadrant,
      String(g.subScores.trend),
      String(g.subScores.rs),
      String(g.subScores.momentum),
      String(g.subScores.breadth),
      g.smaStackLabel,
      g.rsi14.toFixed(1),
      g.adx14.toFixed(1),
      g.macdSignalState,
      String(g.avgRsRating),
      g.rsRatio.toFixed(2),
      g.rsMomentum.toFixed(2),
      `${g.pctAbove50Sma}%`,
      `${g.pctStage2}%`,
      `${g.volumeThrustRatio.toFixed(2)}x`,
      `${g.return1MPct.toFixed(2)}%`,
      `${g.return3MPct.toFixed(2)}%`,
      g.topLeader?.ticker ?? '',
    ]);

    const csv = [headers, ...rows]
      .map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(','))
      .join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Personal_Trades_Terminal_Trending_${viewMode}_${presetId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header & Workspace Controls */}
      <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Trending Sectors & Subsectors — Technical Scoring Engine
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Identifies and scores NSE sectors and granular subsectors on SMA trend alignment, Relative Strength vs NIFTY 500, RSI/MACD/ADX directional momentum, Stage 2 breadth, and volume thrust.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Sectors vs Subsectors Switch */}
          <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-900 rounded-lg">
            <button
              onClick={() => {
                setViewMode('sectors');
                setParentSectorFilter('All');
                setSelectedGroupId(null);
              }}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors whitespace-nowrap ${
                viewMode === 'sectors'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              Sectors ({report.sectors.length})
            </button>
            <button
              onClick={() => {
                setViewMode('subsectors');
                setSelectedGroupId(null);
              }}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors whitespace-nowrap ${
                viewMode === 'subsectors'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              Subsectors ({report.subsectors.length})
            </button>
          </div>

          {/* Scoring Model Selector */}
          <div className="flex items-center gap-1.5">
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <select
              value={presetId}
              onChange={(e) => setPresetId(e.target.value as ScoringPresetId)}
              aria-label="Technical scoring weight model"
              className="px-2.5 py-2 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            >
              {Object.values(SCORING_PRESETS).map((p) => (
                <option key={p.id} value={p.id}>
                  Model: {p.label}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleExportCsv}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Live Nifty Sector Indices Heatmap (Today · This Week · This Month) */}
      <NiftySectorHeatmap
        onSelectSector={(appSector) => {
          setViewMode('sectors');
          setQuadrantFilter('All');
          const hit = report.sectors.find(
            (s) => s.name.toLowerCase() === appSector.toLowerCase()
          );
          if (hit) {
            setSelectedGroupId(hit.id);
          } else {
            setSearchQuery(appSector);
          }
        }}
      />

      {/* 4-Column Executive Summary Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <div
          onClick={() => {
            if (!topSector) return;
            setViewMode('sectors');
            setSelectedGroupId(topSector.id);
          }}
          className="cursor-pointer border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 hover:border-blue-500/60 transition-colors"
        >
          <div className="text-xs text-slate-500">Top Trending Sector</div>
          <div className="mt-1 flex items-baseline justify-between gap-2">
            <span className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
              {topSector?.name ?? '—'}
            </span>
            <span className="text-lg font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400 shrink-0">
              {topSector?.compositeScore ?? 0}/100
            </span>
          </div>
          <div className="mt-1 text-xs text-slate-500 font-mono tabular-nums flex items-center gap-2">
            <span className={topSector ? QUADRANT_TEXT_CLASS[topSector.quadrant] : ''}>
              {topSector?.quadrant}
            </span>
            <span aria-hidden="true">·</span>
            <span>3M {topSector ? formatPct(topSector.return3MPct) : '—'}</span>
            <span aria-hidden="true">·</span>
            <span>RS {topSector?.avgRsRating ?? 0}</span>
          </div>
        </div>

        <div
          onClick={() => {
            if (!topSubsector) return;
            setViewMode('subsectors');
            setParentSectorFilter('All');
            setSelectedGroupId(topSubsector.id);
          }}
          className="cursor-pointer border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 hover:border-blue-500/60 transition-colors"
        >
          <div className="text-xs text-slate-500">Top Trending Subsector</div>
          <div className="mt-1 flex items-baseline justify-between gap-2">
            <span className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
              {topSubsector?.name ?? '—'}
            </span>
            <span className="text-lg font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400 shrink-0">
              {topSubsector?.compositeScore ?? 0}/100
            </span>
          </div>
          <div className="mt-1 text-xs text-slate-500 flex items-center gap-2 truncate">
            <span className="truncate">{topSubsector?.parentSector}</span>
            <span aria-hidden="true">·</span>
            <span className="font-mono text-slate-700 dark:text-slate-300 shrink-0">
              {topSubsector?.topLeader?.ticker ?? '—'}
            </span>
          </div>
        </div>

        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">Rotation Leadership (RRG)</div>
          <div className="mt-1 flex items-baseline gap-3 font-mono tabular-nums">
            <span className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
              {viewMode === 'sectors'
                ? report.universeBreadth.leadingSectorsCount
                : report.universeBreadth.leadingSubsectorsCount}{' '}
              Leading
            </span>
            <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
              {viewMode === 'sectors'
                ? report.universeBreadth.improvingSectorsCount
                : report.universeBreadth.improvingSubsectorsCount}{' '}
              Improving
            </span>
          </div>
          <div className="mt-1 text-xs text-slate-500">
            Out of {baseList.length} NSE {viewMode} tracked vs NIFTY 500
          </div>
        </div>

        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">NSE Universe Trend Breadth</div>
          <div className="mt-1 flex items-baseline gap-3 font-mono tabular-nums">
            <span className="text-lg font-bold text-slate-900 dark:text-slate-100">
              {report.universeBreadth.pctAbove50Sma}%
            </span>
            <span className="text-xs text-slate-500">above 50 SMA</span>
          </div>
          <div className="mt-1 text-xs text-slate-500 font-mono tabular-nums flex items-center gap-2">
            <span>Stage 2: {report.universeBreadth.pctStage2}%</span>
            <span aria-hidden="true">·</span>
            <span>Avg RS: {report.universeBreadth.avgRsRating}</span>
          </div>
        </div>
      </div>

      {/* Main Analytics Split: Left = RRG Quadrant Scatter Plot | Right = Selected Group Technical Breakdown */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-stretch">
        {/* Left: Relative Rotation Graph (RRG) */}
        <div className="xl:col-span-7 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 flex flex-col justify-between gap-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Compass className="w-4 h-4 text-blue-500" />
                <span>
                  Relative Rotation Map ({viewMode === 'sectors' ? 'All Sectors' : 'Top Subsectors'} vs NIFTY 500)
                </span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                X-axis: RS-Ratio (Relative Trend vs NIFTY 500) · Y-axis: RS-Momentum (Rate of Change) · Click any node to inspect constituents
              </p>
            </div>
            <div className="flex items-center gap-3 text-[11px] font-medium">
              <span className="text-emerald-600 dark:text-emerald-400">Leading</span>
              <span className="text-blue-600 dark:text-blue-400">Improving</span>
              <span className="text-amber-600 dark:text-amber-400">Weakening</span>
              <span className="text-red-600 dark:text-red-400">Lagging</span>
            </div>
          </div>

          <div className="relative" style={{ width: '100%', height: 320 }}>
            {/* Subtle Quadrant Corner Labels */}
            <div className="pointer-events-none absolute top-2 right-4 text-[10px] font-semibold tracking-wide text-emerald-600/80 dark:text-emerald-400/75 z-10">
              LEADING
            </div>
            <div className="pointer-events-none absolute top-2 left-14 text-[10px] font-semibold tracking-wide text-blue-600/80 dark:text-blue-400/75 z-10">
              IMPROVING
            </div>
            <div className="pointer-events-none absolute bottom-10 right-4 text-[10px] font-semibold tracking-wide text-amber-600/80 dark:text-amber-400/75 z-10">
              WEAKENING
            </div>
            <div className="pointer-events-none absolute bottom-10 left-14 text-[10px] font-semibold tracking-wide text-red-600/80 dark:text-red-400/75 z-10">
              LAGGING
            </div>

            <ResponsiveContainer>
              <ScatterChart margin={{ top: 18, right: 20, bottom: 20, left: 6 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.16)" />
                <XAxis
                  type="number"
                  dataKey="rsRatio"
                  name="RS-Ratio"
                  domain={['dataMin - 2', 'dataMax + 2']}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickFormatter={(v) => Number(v).toFixed(0)}
                  label={{
                    value: 'RS-Ratio vs NIFTY 500 (100 = Benchmark)',
                    position: 'bottom',
                    offset: 4,
                    fontSize: 11,
                    fill: '#64748b',
                  }}
                />
                <YAxis
                  type="number"
                  dataKey="rsMomentum"
                  name="RS-Momentum"
                  domain={['dataMin - 2', 'dataMax + 2']}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickFormatter={(v) => Number(v).toFixed(0)}
                  width={44}
                />
                <ZAxis type="number" dataKey="size" range={[90, 280]} />
                <ReferenceLine x={100} stroke="#64748b" strokeDasharray="4 4" strokeWidth={1.25} />
                <ReferenceLine y={100} stroke="#64748b" strokeDasharray="4 4" strokeWidth={1.25} />
                <Tooltip
                  cursor={{ strokeDasharray: '3 3' }}
                  content={({ active, payload }) => {
                    if (!active || !payload || payload.length === 0) return null;
                    const p = payload[0].payload as (typeof rrgPoints)[number];
                    return (
                      <div className="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2.5 text-xs text-slate-100 shadow-lg space-y-1">
                        <div className="font-semibold text-white">{p.name}</div>
                        {viewMode === 'subsectors' && (
                          <div className="text-[11px] text-slate-400">{p.parentSector}</div>
                        )}
                        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 pt-1 font-mono tabular-nums text-[11px]">
                          <span className="text-slate-400">Trend Score</span>
                          <span className="text-right font-semibold text-emerald-400">{p.score}/100</span>
                          <span className="text-slate-400">Quadrant</span>
                          <span className="text-right">{p.quadrant}</span>
                          <span className="text-slate-400">RS-Ratio / Mom</span>
                          <span className="text-right">
                            {p.rsRatio.toFixed(1)} / {p.rsMomentum.toFixed(1)}
                          </span>
                          <span className="text-slate-400">RSI / ADX</span>
                          <span className="text-right">
                            {p.rsi14.toFixed(1)} / {p.adx14.toFixed(1)}
                          </span>
                          <span className="text-slate-400">3M Return</span>
                          <span className="text-right">{formatPct(p.return3MPct)}</span>
                          <span className="text-slate-400">Top Leader</span>
                          <span className="text-right text-blue-400">{p.topLeader}</span>
                        </div>
                      </div>
                    );
                  }}
                />
                <Scatter
                  data={rrgPoints}
                  isAnimationActive={false}
                  onClick={(entry) => {
                    const pt = (entry as { payload?: { id?: string } })?.payload;
                    if (pt?.id) {
                      setSelectedGroupId(pt.id);
                    }
                  }}
                >
                  {rrgPoints.map((pt) => {
                    const isSelected = selectedGroup?.id === pt.id;
                    return (
                      <Cell
                        key={pt.id}
                        fill={QUADRANT_COLOR[pt.quadrant]}
                        fillOpacity={isSelected ? 1 : 0.78}
                        stroke={isSelected ? '#ffffff' : 'rgba(15,23,42,0.4)'}
                        strokeWidth={isSelected ? 2.5 : 1}
                        className="cursor-pointer"
                      />
                    );
                  })}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>

          <div className="pt-2 border-t border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
            <span>
              Active Weighting: <strong className="text-slate-700 dark:text-slate-300">{activePreset.label}</strong> —{' '}
              {activePreset.description}
            </span>
          </div>
        </div>

        {/* Right: Selected Sector / Subsector Technical Breakdown & Constituent Leaders */}
        <div className="xl:col-span-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 flex flex-col gap-4">
          {selectedGroup ? (
            <>
              <div className="flex items-start justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-[11px] text-slate-500">
                    <span>{selectedGroup.kind === 'sector' ? 'Sector Technical Profile' : 'Subsector Technical Profile'}</span>
                    {selectedGroup.kind === 'subsector' && (
                      <>
                        <span aria-hidden="true">·</span>
                        <span className="truncate">{selectedGroup.parentSector}</span>
                      </>
                    )}
                  </div>
                  <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 mt-0.5 truncate">
                    {selectedGroup.name}
                  </h2>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                    <span className={`font-semibold ${REGIME_TEXT_CLASS[selectedGroup.regime]}`}>
                      {selectedGroup.regime}
                    </span>
                    <span className="text-slate-400" aria-hidden="true">·</span>
                    <span className={`font-medium ${QUADRANT_TEXT_CLASS[selectedGroup.quadrant]}`}>
                      {selectedGroup.quadrant} Quadrant
                    </span>
                    <span className="text-slate-400" aria-hidden="true">·</span>
                    <span className="font-mono text-slate-500">
                      {selectedGroup.stockCount} {selectedGroup.stockCount === 1 ? 'stock' : 'stocks'}
                    </span>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <div className="text-[11px] text-slate-500">Tech Score</div>
                  <div className="text-2xl font-extrabold font-mono tabular-nums text-slate-900 dark:text-slate-100">
                    {selectedGroup.compositeScore}
                    <span className="text-xs font-normal text-slate-500">/100</span>
                  </div>
                </div>
              </div>

              {/* 4-Pillar Score Decomposition */}
              <div className="space-y-2.5">
                {[
                  {
                    label: `Trend & SMA Structure (${Math.round(activePreset.trend * 100)}%)`,
                    score: selectedGroup.subScores.trend,
                    pts: selectedGroup.weightedPoints.trend,
                    color: 'bg-blue-500',
                  },
                  {
                    label: `Relative Strength vs NIFTY 500 (${Math.round(activePreset.rs * 100)}%)`,
                    score: selectedGroup.subScores.rs,
                    pts: selectedGroup.weightedPoints.rs,
                    color: 'bg-emerald-500',
                  },
                  {
                    label: `Momentum: RSI · MACD · ADX (${Math.round(activePreset.momentum * 100)}%)`,
                    score: selectedGroup.subScores.momentum,
                    pts: selectedGroup.weightedPoints.momentum,
                    color: 'bg-indigo-500',
                  },
                  {
                    label: `Breadth, Stage 2 & Volume (${Math.round(activePreset.breadth * 100)}%)`,
                    score: selectedGroup.subScores.breadth,
                    pts: selectedGroup.weightedPoints.breadth,
                    color: 'bg-amber-500',
                  },
                ].map((bar) => (
                  <div key={bar.label} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-600 dark:text-slate-400">{bar.label}</span>
                      <span className="font-mono tabular-nums font-semibold text-slate-900 dark:text-slate-100">
                        {bar.score}/100{' '}
                        <span className="text-[11px] font-normal text-slate-500">
                          (+{bar.pts.toFixed(1)} pts)
                        </span>
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${bar.color}`}
                        style={{ width: `${bar.score}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Technical Indicator Readout Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-200 dark:border-slate-800 text-xs">
                <div>
                  <div className="text-[11px] text-slate-500">SMA Stack</div>
                  <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                    {selectedGroup.smaStackLabel}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">RSI (14)</div>
                  <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                    {selectedGroup.rsi14.toFixed(1)}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">ADX (14)</div>
                  <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                    {selectedGroup.adx14.toFixed(1)}{' '}
                    <span className="text-[10px] text-slate-500">
                      {selectedGroup.plusDi14 >= selectedGroup.minusDi14 ? '+DI' : '-DI'}
                    </span>
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">MACD</div>
                  <div className="font-mono font-semibold text-slate-900 dark:text-slate-100 mt-0.5 truncate">
                    {selectedGroup.macdSignalState}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">Dist vs 50 SMA</div>
                  <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                    {formatPct(selectedGroup.distFrom50SmaPct)}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">RS vs N500 (3M)</div>
                  <div
                    className={`font-mono font-semibold tabular-nums mt-0.5 ${
                      selectedGroup.rsVsNifty500_3M >= 0
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-red-600 dark:text-red-400'
                    }`}
                  >
                    {formatPct(selectedGroup.rsVsNifty500_3M)}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">Stage 2 / &gt;50D</div>
                  <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                    {selectedGroup.pctStage2}% / {selectedGroup.pctAbove50Sma}%
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-slate-500">Vol Thrust</div>
                  <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                    {selectedGroup.volumeThrustRatio.toFixed(2)}×
                  </div>
                </div>
              </div>

              {/* Drill to Subsectors CTA (when viewing a Sector) */}
              {selectedGroup.kind === 'sector' && (
                <div className="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-800 text-xs">
                  <span className="text-slate-500">
                    Total Cap: <strong className="font-mono text-slate-700 dark:text-slate-300">{formatCr(selectedGroup.totalMarketCapCr)}</strong>
                  </span>
                  <button
                    onClick={() => handleDrillToSubsectors(selectedGroup.name)}
                    className="inline-flex items-center gap-1 font-semibold text-blue-600 dark:text-blue-400 hover:underline whitespace-nowrap"
                  >
                    <Layers className="w-3.5 h-3.5" />
                    <span>View Subsectors in {selectedGroup.name}</span>
                  </button>
                </div>
              )}

              {/* Constituent Stocks Table */}
              <div className="pt-2 border-t border-slate-200 dark:border-slate-800 flex-1 flex flex-col min-h-0">
                <div className="flex items-center justify-between text-xs mb-2 gap-2">
                  <span className="font-semibold text-slate-900 dark:text-slate-100">
                    Constituent Leaders ({selectedGroup.constituents.length})
                  </span>
                  <span className="text-[11px] text-slate-500">
                    Indicators Matrix Summary · Call / Score · Click to inspect
                  </span>
                </div>
                <div className="overflow-y-auto max-h-[260px] divide-y divide-slate-200/70 dark:divide-slate-800/70">
                  {selectedGroup.constituents.map((c) => {
                    const cs = constituentCallScores.get(c.ticker);
                    const callColor =
                      cs?.rating === 'Strong Buy'
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : cs?.rating === 'Buy'
                        ? 'text-blue-600 dark:text-blue-400'
                        : 'text-amber-600 dark:text-amber-400';
                    const matrixColor =
                      (cs?.matrixScorePct ?? 0) >= 70
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : (cs?.matrixScorePct ?? 0) >= 50
                        ? 'text-blue-600 dark:text-blue-400'
                        : 'text-amber-600 dark:text-amber-400';
                    const shortCall =
                      cs?.rating === 'Accumulate on Pullback'
                        ? 'Accum.'
                        : cs?.rating ?? '—';

                    return (
                      <div
                        key={c.ticker}
                        onClick={() => onInspectStock(c.ticker)}
                        className="py-2 flex items-center justify-between gap-2 text-xs cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40 px-1.5 rounded transition-colors"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono font-semibold text-slate-900 dark:text-slate-100 hover:text-blue-500">
                              {c.ticker}
                            </span>
                            <ArrowUpRight className="w-3 h-3 text-slate-400 shrink-0" />
                            {c.stage2 && (
                              <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400">
                                S2
                              </span>
                            )}
                            {c.vcpDetected && (
                              <span className="text-[10px] font-mono text-blue-600 dark:text-blue-400">
                                VCP
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-500 truncate max-w-[140px]">
                            {c.industry}
                          </div>
                        </div>

                        <div className="flex items-center gap-3 font-mono tabular-nums text-[11px] shrink-0">
                          {/* Price & 3M Return */}
                          <div className="text-right">
                            <div className="text-slate-900 dark:text-slate-100 font-medium">
                              {formatINR(c.latestClose, 0)}
                            </div>
                            <div
                              className={
                                c.return3MPct >= 0
                                  ? 'text-emerald-600 dark:text-emerald-400'
                                  : 'text-red-600 dark:text-red-400'
                              }
                            >
                              3M {formatPct(c.return3MPct)}
                            </div>
                          </div>

                          {/* Multi-Indicator Signal Matrix Summary Score */}
                          <div
                            className="text-right min-w-[66px]"
                            title={
                              cs
                                ? `Indicators Matrix Summary: ${cs.bullishSignals}/${cs.totalSignals} Bullish · ${cs.matrixScorePct}% (${cs.technicalConsensus})`
                                : 'Indicators Matrix Summary'
                            }
                          >
                            <div className="text-[10px] text-slate-500">Indicators Matrix</div>
                            {cs ? (
                              <div className={`font-semibold ${matrixColor}`}>
                                {cs.matrixScorePct}%{' '}
                                <span className="text-[10px] text-slate-500 font-normal">
                                  ({cs.bullishSignals}/{cs.totalSignals})
                                </span>
                              </div>
                            ) : (
                              <div className="text-slate-400">—</div>
                            )}
                          </div>

                          {/* Call / Score (60/15/25) */}
                          <div
                            className="text-right min-w-[74px]"
                            title={
                              cs
                                ? `${cs.rating} · Score ${cs.compositeScore}/100 (Tech ${cs.techScore}/60 · Setup ${cs.setupScore}/15 · Funda ${cs.fundaScore}/25)`
                                : 'Call / Score (60/15/25)'
                            }
                          >
                            {cs ? (
                              <>
                                <div className={`text-[10px] font-semibold truncate ${callColor}`}>
                                  {shortCall}
                                </div>
                                <div className="font-bold text-slate-900 dark:text-slate-100">
                                  {cs.compositeScore}
                                  <span className="text-[10px] font-normal text-slate-500">/100</span>
                                </div>
                              </>
                            ) : (
                              <>
                                <div className="text-slate-500 text-[10px]">RS {c.rsRating}</div>
                                <div className="font-bold text-slate-900 dark:text-slate-100">
                                  {c.stockTechScore}/100
                                </div>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          ) : (
            <div className="p-8 text-center text-xs text-slate-500">
              Select a sector or subsector to inspect technical parameters.
            </div>
          )}
        </div>
      </div>

      {/* Main Ranked Technical Scoring Matrix Table */}
      <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
        {/* Table Toolbar */}
        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Ranked NSE {viewMode === 'sectors' ? 'Sectors' : 'Subsectors'} Technical Scorecard
            </h3>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Click any row to inspect its 4-pillar technical breakdown & constituents · Click Top Leader to open full chart
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Search */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={`Filter ${viewMode} or ticker...`}
                className="w-44 pl-8 pr-2.5 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
              />
            </div>

            {/* Parent Sector Filter (Subsector mode) */}
            {viewMode === 'subsectors' && (
              <select
                value={parentSectorFilter}
                onChange={(e) => setParentSectorFilter(e.target.value)}
                className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
              >
                {parentSectors.map((sec) => (
                  <option key={sec} value={sec}>
                    {sec === 'All' ? 'All Parent Sectors' : sec}
                  </option>
                ))}
              </select>
            )}

            {/* Quadrant Filter */}
            <div className="flex items-center gap-0.5 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg">
              {(['All', 'Leading', 'Improving', 'Weakening', 'Lagging'] as const).map((q) => (
                <button
                  key={q}
                  onClick={() => setQuadrantFilter(q)}
                  className={`px-2 py-1 text-[11px] font-medium rounded-md transition-colors whitespace-nowrap ${
                    quadrantFilter === q
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {q}
                </button>
              ))}
            </div>

            {/* Horizon Switch */}
            <div className="flex items-center gap-0.5 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg">
              {(['1W', '1M', '3M', '6M', '1Y'] as ReturnHorizon[]).map((h) => (
                <button
                  key={h}
                  onClick={() => setHorizon(h)}
                  className={`px-2 py-1 text-[11px] font-mono font-medium rounded-md transition-colors whitespace-nowrap ${
                    horizon === h
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {h}
                </button>
              ))}
            </div>

            {/* Sort Selector */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortKey)}
              className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
            >
              <option value="score">Sort: Tech Score</option>
              <option value="return">Sort: {horizon} Return</option>
              <option value="rsRating">Sort: RS Rating</option>
              <option value="rsi">Sort: RSI (14)</option>
              <option value="adx">Sort: ADX (14)</option>
              <option value="breadth50">Sort: % &gt; 50 SMA</option>
              <option value="volThrust">Sort: Vol Thrust</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
              <tr>
                <th className="py-2.5 px-3 text-center w-10">#</th>
                <th className="py-2.5 px-3 min-w-[200px]">
                  {viewMode === 'sectors' ? 'Sector' : 'Subsector / Parent Sector'}
                </th>
                <th className="py-2.5 px-3 min-w-[140px]">Tech Score</th>
                <th className="py-2.5 px-3">Quadrant</th>
                <th className="py-2.5 px-3 text-right" title="Trend / RS / Momentum / Breadth sub-scores (0-100)">
                  T · RS · M · B
                </th>
                <th className="py-2.5 px-3 whitespace-nowrap">SMA Stack</th>
                <th className="py-2.5 px-2.5 text-right">RSI</th>
                <th className="py-2.5 px-2.5 text-right">ADX</th>
                <th className="py-2.5 px-3 whitespace-nowrap">MACD</th>
                <th className="py-2.5 px-2.5 text-right">RS Rtg</th>
                <th className="py-2.5 px-2.5 text-right">&gt;50D</th>
                <th className="py-2.5 px-2.5 text-right">Vol ×</th>
                <th className="py-2.5 px-2.5 text-right">{horizon} %</th>
                <th className="py-2.5 px-4 text-right">Top Leader</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
              {filteredList.length === 0 ? (
                <tr>
                  <td colSpan={14} className="py-10 text-center text-xs text-slate-500">
                    No {viewMode} match the active filters.{' '}
                    <button
                      onClick={() => {
                        setSearchQuery('');
                        setQuadrantFilter('All');
                        setParentSectorFilter('All');
                      }}
                      className="text-blue-600 dark:text-blue-400 font-semibold underline ml-1"
                    >
                      Reset filters
                    </button>
                  </td>
                </tr>
              ) : (
                filteredList.map((g, idx) => {
                  const isSel = selectedGroup?.id === g.id;
                  const retVal = getHorizonReturn(g, horizon);
                  const barColor =
                    g.compositeScore >= 78
                      ? 'bg-emerald-500'
                      : g.compositeScore >= 64
                      ? 'bg-blue-500'
                      : g.compositeScore >= 48
                      ? 'bg-amber-500'
                      : 'bg-red-500';

                  return (
                    <tr
                      key={g.id}
                      onClick={() => setSelectedGroupId(g.id)}
                      className={`cursor-pointer transition-colors ${
                        isSel
                          ? 'bg-blue-600/10 dark:bg-blue-500/15'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
                      }`}
                    >
                      <td className="py-2.5 px-3 text-center font-mono tabular-nums text-slate-500">
                        {idx + 1}
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">
                          {g.name}
                        </div>
                        <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
                          {viewMode === 'subsectors' && (
                            <>
                              <span className="truncate max-w-[140px]">{g.parentSector}</span>
                              <span aria-hidden="true">·</span>
                            </>
                          )}
                          <span className="font-mono">
                            {g.stockCount} {g.stockCount === 1 ? 'stock' : 'stocks'}
                          </span>
                          <span aria-hidden="true">·</span>
                          <span className={REGIME_TEXT_CLASS[g.regime]}>{g.regime}</span>
                        </div>
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold tabular-nums text-slate-900 dark:text-slate-100 w-7">
                            {g.compositeScore}
                          </span>
                          <div className="flex-1 h-1.5 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden min-w-[68px]">
                            <div
                              className={`h-full rounded-full ${barColor}`}
                              style={{ width: `${g.compositeScore}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className={`py-2.5 px-3 font-semibold whitespace-nowrap ${QUADRANT_TEXT_CLASS[g.quadrant]}`}>
                        {g.quadrant}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-[11px] text-slate-600 dark:text-slate-400 whitespace-nowrap">
                        {g.subScores.trend} · {g.subScores.rs} · {g.subScores.momentum} · {g.subScores.breadth}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-[11px] whitespace-nowrap text-slate-700 dark:text-slate-300">
                        {g.smaStackLabel}
                      </td>
                      <td
                        className={`py-2.5 px-2.5 text-right font-mono tabular-nums ${
                          g.rsi14 >= 55 && g.rsi14 <= 75
                            ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                            : g.rsi14 < 40
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-slate-700 dark:text-slate-300'
                        }`}
                      >
                        {g.rsi14.toFixed(1)}
                      </td>
                      <td
                        className={`py-2.5 px-2.5 text-right font-mono tabular-nums ${
                          g.adx14 >= 22 && g.plusDi14 > g.minusDi14
                            ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                            : 'text-slate-700 dark:text-slate-300'
                        }`}
                      >
                        {g.adx14.toFixed(1)}
                      </td>
                      <td
                        className={`py-2.5 px-3 text-[11px] whitespace-nowrap font-medium ${
                          g.macdSignalState === 'Bullish Expanding'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : g.macdSignalState === 'Bullish'
                            ? 'text-blue-600 dark:text-blue-400'
                            : g.macdSignalState === 'Bearish'
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-slate-500'
                        }`}
                      >
                        {g.macdSignalState}
                      </td>
                      <td className="py-2.5 px-2.5 text-right font-mono tabular-nums font-semibold text-slate-900 dark:text-slate-100">
                        {g.avgRsRating}
                      </td>
                      <td className="py-2.5 px-2.5 text-right font-mono tabular-nums text-slate-700 dark:text-slate-300">
                        {g.pctAbove50Sma}%
                      </td>
                      <td className="py-2.5 px-2.5 text-right font-mono tabular-nums text-slate-700 dark:text-slate-300">
                        {g.volumeThrustRatio.toFixed(2)}×
                      </td>
                      <td
                        className={`py-2.5 px-2.5 text-right font-mono tabular-nums font-semibold ${
                          retVal >= 0
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        {formatPct(retVal)}
                      </td>
                      <td className="py-2.5 px-4 text-right whitespace-nowrap">
                        {g.topLeader ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onInspectStock(g.topLeader.ticker);
                            }}
                            className="inline-flex items-center gap-1 font-mono font-semibold text-blue-600 dark:text-blue-400 hover:underline"
                            title={`Open ${g.topLeader.ticker} full ticker page`}
                          >
                            <span>{g.topLeader.ticker}</span>
                            <ArrowUpRight className="w-3 h-3" />
                          </button>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
