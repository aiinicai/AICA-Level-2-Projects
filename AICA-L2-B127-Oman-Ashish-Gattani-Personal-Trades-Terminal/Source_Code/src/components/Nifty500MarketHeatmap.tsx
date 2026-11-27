import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import { ArrowLeft, LayoutGrid } from 'lucide-react';
import { IndianStock, MarketCapBucket } from '../types/market';
import { formatCr, formatINR, formatPct } from '../utils/formatters';

export type HeatmapHorizon = '1D' | '1W' | '1M' | '3M' | '1Y';
type SizeMode = 'mcap' | 'equal';
type CapFilter = 'All' | 'Large' | 'Mid' | 'Small';

interface Nifty500MarketHeatmapProps {
  stocks: IndianStock[];
  marketVersion: number;
  onSelectTicker: (ticker: string) => void;
}

interface StockMetricRow {
  stock: IndianStock;
  periodReturnPct: number;
  weightValue: number;
  mcapSharePct: number;
}

interface SectorAggregate {
  sector: string;
  totalMarketCapCr: number;
  weightedReturnPct: number;
  advancers: number;
  decliners: number;
  count: number;
  stocks: StockMetricRow[];
}

interface HeatmapNode {
  name: string;
  isSector?: boolean;
  sectorReturnPct?: number;
  sectorMarketCapCr?: number;
  stockRow?: StockMetricRow;
  value?: number;
  children?: HeatmapNode[];
}

const HORIZON_CONFIG: Record<
  HeatmapHorizon,
  { label: string; tradingDays: number; scaleMax: number }
> = {
  '1D': { label: '1D', tradingDays: 1, scaleMax: 4 },
  '1W': { label: '1W', tradingDays: 5, scaleMax: 8 },
  '1M': { label: '1M', tradingDays: 21, scaleMax: 15 },
  '3M': { label: '3M', tradingDays: 63, scaleMax: 25 },
  '1Y': { label: '1Y', tradingDays: 252, scaleMax: 45 },
};

const COLOR_STOPS = [
  '#dc2626',
  '#991b1b',
  '#5b232a',
  '#263040',
  '#1d4b3a',
  '#15803d',
  '#16a34a',
];

function computeHorizonReturnPct(stock: IndianStock, horizon: HeatmapHorizon): number {
  if (horizon === '1D') {
    return Number.isFinite(stock.dailyChangePct) ? stock.dailyChangePct : 0;
  }
  const bars = stock.bars;
  if (!bars || bars.length < 2) return 0;
  const lookback = HORIZON_CONFIG[horizon].tradingDays;
  const refIdx = Math.max(0, bars.length - 1 - lookback);
  const refClose = bars[refIdx]?.close;
  const latest = stock.latestClose || bars[bars.length - 1]?.close || 0;
  if (!refClose || refClose <= 0 || !latest) return 0;
  return ((latest - refClose) / refClose) * 100;
}

function formatLakhCr(totalCr: number): string {
  if (!Number.isFinite(totalCr) || totalCr <= 0) return '₹0 Cr';
  if (totalCr >= 100000) {
    return `₹${(totalCr / 100000).toFixed(2)} L Cr`;
  }
  return formatCr(totalCr);
}

function shortenSectorLabel(sector: string, maxChars: number): string {
  if (sector.length <= maxChars) return sector;
  const aliases: Record<string, string> = {
    'Banking & Financial Services': 'Banking & Fin.',
    'Information Technology': 'IT Services',
    'Capital Goods & Defence': 'Cap Goods & Def.',
    'Pharmaceuticals & Healthcare': 'Pharma & Health',
    'Automobiles & Auto Components': 'Automobiles',
    'Consumer Durables & Retail': 'Consumer & Retail',
    'Oil, Gas & Consumable Fuels': 'Oil & Gas',
    'Metals & Mining': 'Metals',
    'Fast Moving Consumer Goods': 'FMCG',
    'Telecom & Digital': 'Telecom',
    'Chemicals & Materials': 'Chemicals',
    'Energy & Power': 'Energy & Power',
  };
  const compact = aliases[sector] ?? sector;
  if (compact.length <= maxChars) return compact;
  return `${compact.slice(0, Math.max(4, maxChars - 1))}…`;
}

function matchesCapFilter(bucket: MarketCapBucket, filter: CapFilter): boolean {
  if (filter === 'All') return true;
  if (filter === 'Small') return bucket === 'Small' || bucket === 'Micro';
  return bucket === filter;
}

export const Nifty500MarketHeatmap: React.FC<Nifty500MarketHeatmapProps> = ({
  stocks,
  marketVersion,
  onSelectTicker,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 960, height: 470 });
  const [horizon, setHorizon] = useState<HeatmapHorizon>('1D');
  const [capFilter, setCapFilter] = useState<CapFilter>('All');
  const [sizeMode, setSizeMode] = useState<SizeMode>('mcap');
  const [selectedSector, setSelectedSector] = useState<string>('All');
  const [hovered, setHovered] = useState<{
    row: StockMetricRow;
    x: number;
    y: number;
  } | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const updateSize = () => {
      const rect = el.getBoundingClientRect();
      if (rect.width > 0) {
        const nextHeight = rect.width < 640 ? 520 : rect.width < 1024 ? 480 : 470;
        setDimensions({ width: Math.floor(rect.width), height: nextHeight });
      }
    };
    updateSize();
    const ro = new ResizeObserver(updateSize);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const colorScale = useMemo(() => {
    const m = HORIZON_CONFIG[horizon].scaleMax;
    return d3
      .scaleLinear<string>()
      .domain([-m, -m * 0.5, -m * 0.14, 0, m * 0.14, m * 0.5, m])
      .range(COLOR_STOPS)
      .clamp(true);
  }, [horizon]);

  // Compute filtered stocks, sector aggregates, and breadth metrics
  const {
    sectorAggregates,
    visibleSectors,
    totalMarketCapCr,
    weightedUniverseReturnPct,
    advancersCount,
    declinersCount,
    unchangedCount,
    visibleStockCount,
  } = useMemo(() => {
    // marketVersion ensures recomputation whenever live quotes hydrate
    void marketVersion;

    const capFiltered = stocks.filter((s) => matchesCapFilter(s.capBucket, capFilter));
    const universeCap = capFiltered.reduce((sum, s) => sum + Math.max(0, s.marketCapCr), 0);

    const bySector = new Map<string, StockMetricRow[]>();
    for (const stock of capFiltered) {
      const ret = computeHorizonReturnPct(stock, horizon);
      const row: StockMetricRow = {
        stock,
        periodReturnPct: ret,
        weightValue: sizeMode === 'mcap' ? Math.max(150, stock.marketCapCr) : 1,
        mcapSharePct: universeCap > 0 ? (stock.marketCapCr / universeCap) * 100 : 0,
      };
      const list = bySector.get(stock.sector);
      if (list) list.push(row);
      else bySector.set(stock.sector, [row]);
    }

    const aggregates: SectorAggregate[] = Array.from(bySector.entries())
      .map(([sector, rows]) => {
        const totalCap = rows.reduce((acc, r) => acc + Math.max(0, r.stock.marketCapCr), 0);
        const weightedRet =
          totalCap > 0
            ? rows.reduce(
                (acc, r) => acc + r.periodReturnPct * Math.max(0, r.stock.marketCapCr),
                0
              ) / totalCap
            : rows.reduce((acc, r) => acc + r.periodReturnPct, 0) / Math.max(1, rows.length);
        const adv = rows.filter((r) => r.periodReturnPct > 0.05).length;
        const dec = rows.filter((r) => r.periodReturnPct < -0.05).length;
        return {
          sector,
          totalMarketCapCr: totalCap,
          weightedReturnPct: weightedRet,
          advancers: adv,
          decliners: dec,
          count: rows.length,
          stocks: rows.sort((a, b) => b.weightValue - a.weightValue),
        };
      })
      .sort((a, b) => b.totalMarketCapCr - a.totalMarketCapCr);

    const activeSectors =
      selectedSector === 'All'
        ? aggregates
        : aggregates.filter((s) => s.sector === selectedSector);

    const rawEffective = activeSectors.length > 0 ? activeSectors : aggregates;
    // Preserve true breadth/returns over all 1,100+ stocks while capping D3 overview tiles cleanly to top 160
    const effectiveSectors =
      selectedSector === 'All' && capFiltered.length > 160
        ? rawEffective.map((sec) => {
            const share = Math.max(4, Math.round((sec.count / capFiltered.length) * 160));
            return { ...sec, stocks: sec.stocks.slice(0, share) };
          })
        : rawEffective;
    const visibleRows = effectiveSectors.flatMap((s) => s.stocks);
    const visCap = visibleRows.reduce((sum, r) => sum + Math.max(0, r.stock.marketCapCr), 0);
    const visWeightedRet =
      visCap > 0
        ? visibleRows.reduce(
            (sum, r) => sum + r.periodReturnPct * Math.max(0, r.stock.marketCapCr),
            0
          ) / visCap
        : 0;

    const advancers = visibleRows.filter((r) => r.periodReturnPct > 0.05).length;
    const decliners = visibleRows.filter((r) => r.periodReturnPct < -0.05).length;
    const unchanged = visibleRows.length - advancers - decliners;

    return {
      sectorAggregates: aggregates,
      visibleSectors: effectiveSectors,
      totalMarketCapCr: visCap,
      weightedUniverseReturnPct: visWeightedRet,
      advancersCount: advancers,
      declinersCount: decliners,
      unchangedCount: unchanged,
      visibleStockCount: visibleRows.length,
    };
  }, [stocks, marketVersion, capFilter, horizon, sizeMode, selectedSector]);

  // Reset selectedSector if it no longer exists under the chosen cap filter
  useEffect(() => {
    if (
      selectedSector !== 'All' &&
      !sectorAggregates.some((s) => s.sector === selectedSector)
    ) {
      setSelectedSector('All');
    }
  }, [sectorAggregates, selectedSector]);

  // Build D3 squarified hierarchical treemap layout
  const { sectorNodes, leafNodes } = useMemo(() => {
    if (visibleSectors.length === 0 || dimensions.width <= 0) {
      return {
        sectorNodes: [] as d3.HierarchyRectangularNode<HeatmapNode>[],
        leafNodes: [] as d3.HierarchyRectangularNode<HeatmapNode>[],
      };
    }

    const hierarchyData: HeatmapNode = {
      name: 'NIFTY 500',
      children: visibleSectors.map((sec) => ({
        name: sec.sector,
        isSector: true,
        sectorReturnPct: sec.weightedReturnPct,
        sectorMarketCapCr: sec.totalMarketCapCr,
        children: sec.stocks.map((row) => ({
          name: row.stock.ticker,
          stockRow: row,
          value: row.weightValue,
        })),
      })),
    };

    const root = d3
      .hierarchy<HeatmapNode>(hierarchyData)
      .sum((d) => d.value ?? 0)
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

    const layout = d3
      .treemap<HeatmapNode>()
      .tile(d3.treemapSquarify.ratio(1.25))
      .size([dimensions.width, dimensions.height])
      .paddingOuter(4)
      .paddingTop(22)
      .paddingInner(2)
      .round(true);

    const laidOut = layout(root);
    return {
      sectorNodes: laidOut.children ?? [],
      leafNodes: laidOut.leaves(),
    };
  }, [visibleSectors, dimensions]);

  const sortedSectorsByPerf = useMemo(
    () => [...sectorAggregates].sort((a, b) => b.weightedReturnPct - a.weightedReturnPct),
    [sectorAggregates]
  );

  const scaleMax = HORIZON_CONFIG[horizon].scaleMax;
  const advPct = visibleStockCount > 0 ? (advancersCount / visibleStockCount) * 100 : 50;

  return (
    <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
      {/* Header & Controls Bar */}
      <div className="px-4 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <LayoutGrid className="w-4 h-4 text-blue-500 shrink-0" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
              NIFTY 500 Sector Market Heatmap
            </h2>
            {selectedSector !== 'All' && (
              <button
                onClick={() => setSelectedSector('All')}
                className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded border border-blue-500/40 text-blue-600 dark:text-blue-400 hover:bg-blue-500/10 whitespace-nowrap"
              >
                <ArrowLeft className="w-3 h-3" />
                All Sectors
              </button>
            )}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
            {sizeMode === 'mcap'
              ? 'Tile area weighted by NSE Market Cap (₹ Cr)'
              : 'Equal-weight constituent tiles'}{' '}
            · Color by {horizon} % change · Click sector header to zoom, click any stock for full TechnoFunda page
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          {/* Horizon Segmented Control */}
          <div
            className="inline-flex items-center rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 p-0.5 text-[11px] font-mono"
            role="group"
            aria-label="Return Horizon"
          >
            {(['1D', '1W', '1M', '3M', '1Y'] as HeatmapHorizon[]).map((h) => (
              <button
                key={h}
                onClick={() => setHorizon(h)}
                className={`px-2 py-1 rounded-md transition-colors whitespace-nowrap ${
                  horizon === h
                    ? 'bg-blue-600 text-white font-semibold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                {h}
              </button>
            ))}
          </div>

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

          {/* Size Metric Toggle */}
          <div
            className="inline-flex items-center rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 p-0.5 text-[11px]"
            role="group"
            aria-label="Tile Sizing"
          >
            <button
              onClick={() => setSizeMode('mcap')}
              className={`px-2 py-1 rounded-md transition-colors whitespace-nowrap ${
                sizeMode === 'mcap'
                  ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              Mkt Cap
            </button>
            <button
              onClick={() => setSizeMode('equal')}
              className={`px-2 py-1 rounded-md transition-colors whitespace-nowrap ${
                sizeMode === 'equal'
                  ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              Equal
            </button>
          </div>
        </div>
      </div>

      {/* Breadth Telemetry & Diverging Color Scale Bar */}
      <div className="px-4 py-2.5 border-b border-slate-200/80 dark:border-slate-800/80 bg-slate-50/70 dark:bg-slate-900/50 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono tabular-nums">
          <span className="text-slate-600 dark:text-slate-300">
            <span className="font-sans text-[11px] text-slate-500 mr-1.5">
              {selectedSector === 'All' ? 'NIFTY 500 Cap-Wtd' : selectedSector}
            </span>
            <strong
              className={
                weightedUniverseReturnPct >= 0
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-red-600 dark:text-red-400'
              }
            >
              {formatPct(weightedUniverseReturnPct)}
            </strong>
          </span>

          <span className="text-slate-300 dark:text-slate-700">|</span>

          <span className="text-slate-600 dark:text-slate-300">
            <span className="font-sans text-[11px] text-slate-500 mr-1.5">Visible MCap</span>
            <strong>{formatLakhCr(totalMarketCapCr)}</strong>
          </span>

          <span className="text-slate-300 dark:text-slate-700">|</span>

          <div className="inline-flex items-center gap-2">
            <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
              {advancersCount} Adv
            </span>
            <div className="w-16 h-1.5 rounded-full bg-red-500/80 overflow-hidden">
              <div
                className="h-full bg-emerald-500 transition-all duration-300"
                style={{ width: `${Math.min(100, Math.max(0, advPct))}%` }}
              />
            </div>
            <span className="text-red-600 dark:text-red-400 font-semibold">
              {declinersCount} Dec
            </span>
            {unchangedCount > 0 && (
              <span className="text-slate-400 text-[11px]">({unchangedCount} Flat)</span>
            )}
          </div>
        </div>

        {/* Continuous Diverging Color Scale Legend */}
        <div className="flex items-center gap-1.5 text-[10px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
          <span>-{scaleMax}%</span>
          <div className="flex items-center rounded overflow-hidden border border-slate-300 dark:border-slate-700 h-2.5">
            {COLOR_STOPS.map((color, idx) => (
              <span
                key={idx}
                className="w-5 h-full block"
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
          <span>+{scaleMax}%</span>
        </div>
      </div>

      {/* D3 Squarified Hierarchical Treemap Canvas */}
      <div
        ref={containerRef}
        className="relative w-full bg-[#0b1120] select-none"
        style={{ height: dimensions.height }}
        onMouseLeave={() => setHovered(null)}
      >
        {leafNodes.length === 0 ? (
          <div className="h-full flex items-center justify-center text-xs text-slate-400">
            No NIFTY 500 constituents match the selected cap filter.
          </div>
        ) : (
          <svg
            width={dimensions.width}
            height={dimensions.height}
            className="block"
            role="img"
            aria-label="NIFTY 500 Sector Market Heatmap"
          >
            <defs>
              {leafNodes.map((node) => {
                const ticker = node.data.stockRow?.stock.ticker ?? node.data.name;
                const safeId = ticker.replace(/[^a-zA-Z0-9_-]/g, '_');
                const w = Math.max(0, node.x1 - node.x0);
                const h = Math.max(0, node.y1 - node.y0);
                return (
                  <clipPath key={`clip-${safeId}`} id={`hm-clip-${safeId}`}>
                    <rect x={0} y={0} width={w} height={h} rx={2} />
                  </clipPath>
                );
              })}
            </defs>

            {/* Depth 1: Sector Container Boxes & Interactive Sector Headers */}
            {sectorNodes.map((secNode) => {
              const sw = Math.max(0, secNode.x1 - secNode.x0);
              const sh = Math.max(0, secNode.y1 - secNode.y0);
              const sectorName = secNode.data.name;
              const secRet = secNode.data.sectorReturnPct ?? 0;
              const maxLabelChars = Math.max(6, Math.floor((sw - 60) / 6.2));
              const showRet = sw >= 96;
              const isFocused = selectedSector === sectorName;

              return (
                <g
                  key={`sec-${sectorName}`}
                  transform={`translate(${secNode.x0}, ${secNode.y0})`}
                >
                  {/* Outer Sector Frame */}
                  <rect
                    width={sw}
                    height={sh}
                    rx={3}
                    fill="#111827"
                    stroke={isFocused ? '#3b82f6' : '#1e293b'}
                    strokeWidth={isFocused ? 1.5 : 1}
                  />

                  {/* Clickable Sector Header Strip */}
                  <g
                    onClick={() =>
                      setSelectedSector((prev) => (prev === sectorName ? 'All' : sectorName))
                    }
                    className="cursor-pointer group"
                  >
                    <rect
                      x={1}
                      y={1}
                      width={Math.max(0, sw - 2)}
                      height={20}
                      rx={2}
                      fill="#0f172a"
                      className="group-hover:fill-slate-800 transition-colors"
                    />
                    {sw >= 42 && (
                      <text
                        x={6}
                        y={14}
                        fill="#e2e8f0"
                        fontSize={10}
                        fontWeight={700}
                        fontFamily="Inter, system-ui, sans-serif"
                        style={{ letterSpacing: '0.02em' }}
                      >
                        {shortenSectorLabel(sectorName, maxLabelChars).toUpperCase()}
                      </text>
                    )}
                    {showRet && (
                      <text
                        x={sw - 6}
                        y={14}
                        textAnchor="end"
                        fill={secRet >= 0 ? '#34d399' : '#f87171'}
                        fontSize={10}
                        fontWeight={700}
                        fontFamily="JetBrains Mono, monospace"
                      >
                        {formatPct(secRet)}
                      </text>
                    )}
                  </g>
                </g>
              );
            })}

            {/* Depth 2: Individual Stock Tiles */}
            {leafNodes.map((node) => {
              const row = node.data.stockRow;
              if (!row) return null;
              const { stock, periodReturnPct } = row;
              const w = Math.max(0, node.x1 - node.x0);
              const h = Math.max(0, node.y1 - node.y0);
              const fill = colorScale(periodReturnPct);
              const safeId = stock.ticker.replace(/[^a-zA-Z0-9_-]/g, '_');
              const isHovered = hovered?.row.stock.ticker === stock.ticker;

              // Adaptive typography based on tile geometry
              const showTicker = w >= 32 && h >= 18;
              const showPct = w >= 38 && h >= 33;
              const showPrice = w >= 78 && h >= 54;
              const showMcap = w >= 115 && h >= 74;

              const tickerFontSize =
                w >= 130 && h >= 85
                  ? 14
                  : w >= 85 && h >= 55
                  ? 12
                  : w >= 55 && h >= 34
                  ? 10.5
                  : 9;

              const pctFontSize =
                w >= 130 && h >= 85 ? 12 : w >= 85 && h >= 55 ? 10.5 : 9.5;

              const centerX = w / 2;
              const centerY = h / 2;

              // Vertical offset logic so multi-line labels stay optically centered
              let tickerY = centerY + 3.5;
              let pctY = centerY + 15;
              let priceY = centerY + 27;
              let mcapY = centerY + 39;

              if (showMcap) {
                tickerY = centerY - 14;
                pctY = centerY + 2;
                priceY = centerY + 16;
                mcapY = centerY + 29;
              } else if (showPrice) {
                tickerY = centerY - 9;
                pctY = centerY + 6;
                priceY = centerY + 19;
              } else if (showPct) {
                tickerY = centerY - 3;
                pctY = centerY + 10;
              }

              return (
                <g
                  key={stock.ticker}
                  transform={`translate(${node.x0}, ${node.y0})`}
                  clipPath={`url(#hm-clip-${safeId})`}
                  className="cursor-pointer"
                  onClick={() => onSelectTicker(stock.ticker)}
                  onMouseEnter={(e) => {
                    const rect = containerRef.current?.getBoundingClientRect();
                    if (!rect) return;
                    setHovered({
                      row,
                      x: e.clientX - rect.left,
                      y: e.clientY - rect.top,
                    });
                  }}
                  onMouseMove={(e) => {
                    const rect = containerRef.current?.getBoundingClientRect();
                    if (!rect) return;
                    setHovered({
                      row,
                      x: e.clientX - rect.left,
                      y: e.clientY - rect.top,
                    });
                  }}
                >
                  <rect
                    width={w}
                    height={h}
                    rx={2}
                    fill={fill}
                    stroke={isHovered ? '#ffffff' : '#0b1120'}
                    strokeWidth={isHovered ? 2 : 0.8}
                  />

                  {showTicker && (
                    <text
                      x={centerX}
                      y={tickerY}
                      textAnchor="middle"
                      fill="#ffffff"
                      fontSize={tickerFontSize}
                      fontWeight={700}
                      fontFamily="JetBrains Mono, monospace"
                      style={{ pointerEvents: 'none' }}
                    >
                      {stock.ticker}
                    </text>
                  )}

                  {showPct && (
                    <text
                      x={centerX}
                      y={pctY}
                      textAnchor="middle"
                      fill="rgba(255,255,255,0.92)"
                      fontSize={pctFontSize}
                      fontWeight={600}
                      fontFamily="JetBrains Mono, monospace"
                      style={{ pointerEvents: 'none' }}
                    >
                      {formatPct(periodReturnPct)}
                    </text>
                  )}

                  {showPrice && (
                    <text
                      x={centerX}
                      y={priceY}
                      textAnchor="middle"
                      fill="rgba(255,255,255,0.75)"
                      fontSize={9.5}
                      fontFamily="JetBrains Mono, monospace"
                      style={{ pointerEvents: 'none' }}
                    >
                      {formatINR(stock.latestClose, 0)}
                    </text>
                  )}

                  {showMcap && (
                    <text
                      x={centerX}
                      y={mcapY}
                      textAnchor="middle"
                      fill="rgba(255,255,255,0.62)"
                      fontSize={9}
                      fontFamily="JetBrains Mono, monospace"
                      style={{ pointerEvents: 'none' }}
                    >
                      {formatLakhCr(stock.marketCapCr)}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        )}

        {/* Rich Floating Hover Tooltip */}
        {hovered && (
          <div
            className="pointer-events-none absolute z-30 w-64 rounded-lg border border-slate-700 bg-slate-950/95 p-3 text-xs text-slate-100 shadow-xl backdrop-blur-sm"
            style={{
              left: Math.max(
                10,
                hovered.x + 276 > dimensions.width ? hovered.x - 268 : hovered.x + 14
              ),
              top: Math.max(
                10,
                hovered.y + 190 > dimensions.height ? hovered.y - 180 : hovered.y + 14
              ),
            }}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="font-mono font-bold text-sm text-white">
                  {hovered.row.stock.ticker}
                </div>
                <div className="text-[11px] text-slate-400 truncate">
                  {hovered.row.stock.name}
                </div>
              </div>
              <div
                className={`font-mono font-bold text-sm tabular-nums shrink-0 ${
                  hovered.row.periodReturnPct >= 0 ? 'text-emerald-400' : 'text-red-400'
                }`}
              >
                {formatPct(hovered.row.periodReturnPct)}
              </div>
            </div>

            <div className="mt-1 text-[10px] text-slate-400 truncate">
              {hovered.row.stock.sector} · {hovered.row.stock.capBucket} Cap
            </div>

            <div className="mt-2.5 pt-2 border-t border-slate-800 grid grid-cols-2 gap-x-3 gap-y-1.5 font-mono text-[11px] tabular-nums">
              <span className="text-slate-400 font-sans">Last Price</span>
              <span className="text-right font-semibold text-white">
                {formatINR(hovered.row.stock.latestClose)}
              </span>

              {horizon !== '1D' && (
                <>
                  <span className="text-slate-400 font-sans">1D Change</span>
                  <span
                    className={`text-right font-semibold ${
                      hovered.row.stock.dailyChangePct >= 0
                        ? 'text-emerald-400'
                        : 'text-red-400'
                    }`}
                  >
                    {formatPct(hovered.row.stock.dailyChangePct)}
                  </span>
                </>
              )}

              <span className="text-slate-400 font-sans">Market Cap</span>
              <span className="text-right text-slate-200">
                {formatCr(hovered.row.stock.marketCapCr)}
              </span>

              <span className="text-slate-400 font-sans">Universe Weight</span>
              <span className="text-right text-slate-200">
                {hovered.row.mcapSharePct.toFixed(2)}%
              </span>

              <span className="text-slate-400 font-sans">Avg Turnover</span>
              <span className="text-right text-slate-200">
                {formatCr(hovered.row.stock.avgDailyTurnoverCr)}
              </span>
            </div>

            <div className="mt-2 pt-1.5 border-t border-slate-800 text-[10px] text-blue-400 font-medium">
              Click tile for full TechnoFunda analysis →
            </div>
          </div>
        )}
      </div>

      {/* Interactive Sector Leadership Strip */}
      <div className="px-4 py-2.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/40 flex items-center gap-2 overflow-x-auto">
        <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 whitespace-nowrap shrink-0">
          Sectors ({horizon}):
        </span>
        <button
          onClick={() => setSelectedSector('All')}
          className={`px-2 py-1 rounded text-[11px] font-medium whitespace-nowrap transition-colors shrink-0 ${
            selectedSector === 'All'
              ? 'bg-blue-600 text-white'
              : 'text-slate-600 dark:text-slate-300 hover:bg-slate-200/70 dark:hover:bg-slate-800'
          }`}
        >
          All ({sectorAggregates.reduce((s, a) => s + a.count, 0)})
        </button>
        {sortedSectorsByPerf.map((sec) => {
          const active = selectedSector === sec.sector;
          const pos = sec.weightedReturnPct >= 0;
          return (
            <button
              key={sec.sector}
              onClick={() => setSelectedSector(active ? 'All' : sec.sector)}
              className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] whitespace-nowrap transition-colors shrink-0 border ${
                active
                  ? 'border-blue-500 bg-blue-500/10 text-blue-700 dark:text-blue-300 font-semibold'
                  : 'border-slate-200/80 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:border-slate-400 dark:hover:border-slate-600'
              }`}
            >
              <span>{shortenSectorLabel(sec.sector, 16)}</span>
              <span
                className={`font-mono tabular-nums font-semibold ${
                  pos ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                }`}
              >
                {formatPct(sec.weightedReturnPct)}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
};
