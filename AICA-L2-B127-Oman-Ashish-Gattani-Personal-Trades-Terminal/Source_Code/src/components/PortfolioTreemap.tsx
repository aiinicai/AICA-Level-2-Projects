import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import { EnrichedHolding } from '../engine/portfolioRiskEngine';
import { formatINRCompact, formatPct } from '../utils/formatters';

interface PortfolioTreemapProps {
  holdings: EnrichedHolding[];
  onSelectTicker?: (ticker: string) => void;
}

interface TreeNodeData {
  name: string;
  ticker?: string;
  sector?: string;
  value?: number;
  dailyChangePct?: number;
  weightPct?: number;
  unrealizedPnlPct?: number;
  children?: TreeNodeData[];
}

export const PortfolioTreemap: React.FC<PortfolioTreemapProps> = ({
  holdings,
  onSelectTicker,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ width: 760, height: 340 });
  const [groupBySector, setGroupBySector] = useState(true);
  const [hovered, setHovered] = useState<{
    ticker: string;
    name: string;
    sector: string;
    value: number;
    dailyChangePct: number;
    weightPct: number;
    unrealizedPnlPct: number;
    x: number;
    y: number;
  } | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = Math.max(320, Math.floor(entry.contentRect.width));
        setSize({ width: w, height: 340 });
      }
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const colorScale = useMemo(() => {
    return d3
      .scaleLinear<string>()
      .domain([-4.0, -1.5, 0, 1.5, 4.0])
      .range(['#991b1b', '#dc2626', '#334155', '#15803d', '#047857'])
      .clamp(true);
  }, []);

  const layout = useMemo(() => {
    if (holdings.length === 0) return { leaves: [], groups: [] };

    let rootData: TreeNodeData;
    if (groupBySector) {
      const bySector = new Map<string, EnrichedHolding[]>();
      for (const h of holdings) {
        const arr = bySector.get(h.sector) ?? [];
        arr.push(h);
        bySector.set(h.sector, arr);
      }
      rootData = {
        name: 'Portfolio',
        children: Array.from(bySector.entries()).map(([sector, items]) => ({
          name: sector,
          children: items.map((item) => ({
            name: item.name,
            ticker: item.holding.ticker,
            sector: item.sector,
            value: Math.max(1, item.marketValueInr),
            dailyChangePct: item.dailyChangePct,
            weightPct: item.currentWeightPct,
            unrealizedPnlPct: item.unrealizedPnlPct,
          })),
        })),
      };
    } else {
      rootData = {
        name: 'Portfolio',
        children: holdings.map((item) => ({
          name: item.name,
          ticker: item.holding.ticker,
          sector: item.sector,
          value: Math.max(1, item.marketValueInr),
          dailyChangePct: item.dailyChangePct,
          weightPct: item.currentWeightPct,
          unrealizedPnlPct: item.unrealizedPnlPct,
        })),
      };
    }

    const hierarchy = d3
      .hierarchy<TreeNodeData>(rootData)
      .sum((d) => d.value ?? 0)
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

    const treemapLayout = d3
      .treemap<TreeNodeData>()
      .size([size.width, size.height])
      .tile(d3.treemapSquarify)
      .paddingOuter(4)
      .paddingInner(3)
      .paddingTop(groupBySector ? 20 : 4);

    const root = treemapLayout(hierarchy);
    const groups = groupBySector ? root.children ?? [] : [];
    const leaves = root.leaves();
    return { leaves, groups };
  }, [holdings, groupBySector, size]);

  if (holdings.length === 0) {
    return (
      <div className="h-[340px] flex items-center justify-center border border-slate-200 dark:border-slate-800 rounded-lg text-sm text-slate-500">
        Add NSE/BSE holdings to render the D3 portfolio allocation treemap.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
          <button
            onClick={() => setGroupBySector(true)}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
              groupBySector
                ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            Group by Sector
          </button>
          <button
            onClick={() => setGroupBySector(false)}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
              !groupBySector
                ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            Flat Holdings
          </button>
        </div>

        <div className="flex items-center gap-2 text-[11px] font-mono text-slate-500 dark:text-slate-400">
          <span>-4%</span>
          <div
            className="w-28 h-2.5 rounded-sm"
            style={{
              background:
                'linear-gradient(90deg, #991b1b 0%, #dc2626 25%, #334155 50%, #15803d 75%, #047857 100%)',
            }}
          />
          <span>+4% Daily Return</span>
        </div>
      </div>

      <div ref={containerRef} className="relative w-full select-none">
        <svg
          width={size.width}
          height={size.height}
          className="block rounded-lg overflow-hidden bg-slate-100 dark:bg-[#0B0F17] border border-slate-200 dark:border-slate-800"
        >
          {layout.groups.map((grp) => {
            const w = grp.x1 - grp.x0;
            const h = grp.y1 - grp.y0;
            if (w < 4 || h < 4) return null;
            return (
              <g key={grp.data.name}>
                <rect
                  x={grp.x0}
                  y={grp.y0}
                  width={w}
                  height={h}
                  rx={4}
                  className="fill-slate-200/70 dark:fill-slate-900/90 stroke-slate-300 dark:stroke-slate-800"
                  strokeWidth={1}
                />
                {w > 64 && (
                  <text
                    x={grp.x0 + 6}
                    y={grp.y0 + 13}
                    className="fill-slate-700 dark:fill-slate-300 text-[10px] font-medium"
                  >
                    {grp.data.name.length > Math.floor(w / 6.5)
                      ? `${grp.data.name.slice(0, Math.max(4, Math.floor(w / 6.5) - 1))}…`
                      : grp.data.name}
                  </text>
                )}
              </g>
            );
          })}

          {layout.leaves.map((leaf) => {
            const w = Math.max(0, leaf.x1 - leaf.x0);
            const h = Math.max(0, leaf.y1 - leaf.y0);
            const d = leaf.data;
            const fill = colorScale(d.dailyChangePct ?? 0);
            return (
              <g
                key={d.ticker}
                transform={`translate(${leaf.x0},${leaf.y0})`}
                className="cursor-pointer transition-opacity hover:opacity-90"
                onClick={() => d.ticker && onSelectTicker?.(d.ticker)}
                onMouseMove={(evt) => {
                  const bounds = containerRef.current?.getBoundingClientRect();
                  if (!bounds || !d.ticker) return;
                  setHovered({
                    ticker: d.ticker,
                    name: d.name,
                    sector: d.sector ?? '',
                    value: d.value ?? 0,
                    dailyChangePct: d.dailyChangePct ?? 0,
                    weightPct: d.weightPct ?? 0,
                    unrealizedPnlPct: d.unrealizedPnlPct ?? 0,
                    x: evt.clientX - bounds.left,
                    y: evt.clientY - bounds.top,
                  });
                }}
                onMouseLeave={() => setHovered(null)}
              >
                <rect
                  width={w}
                  height={h}
                  rx={3}
                  fill={fill}
                  stroke="rgba(15,23,42,0.45)"
                  strokeWidth={1}
                />
                {w > 54 && h > 36 && (
                  <>
                    <text
                      x={8}
                      y={18}
                      fill="#ffffff"
                      fontSize={w > 110 ? 12 : 10}
                      fontWeight={700}
                      fontFamily="JetBrains Mono, monospace"
                    >
                      {d.ticker}
                    </text>
                    <text
                      x={8}
                      y={33}
                      fill="rgba(255,255,255,0.92)"
                      fontSize={10}
                      fontFamily="JetBrains Mono, monospace"
                    >
                      {formatPct(d.dailyChangePct ?? 0)}
                    </text>
                  </>
                )}
                {w > 98 && h > 56 && (
                  <text
                    x={8}
                    y={48}
                    fill="rgba(255,255,255,0.78)"
                    fontSize={10}
                    fontFamily="JetBrains Mono, monospace"
                  >
                    {formatINRCompact(d.value ?? 0)} · {(d.weightPct ?? 0).toFixed(1)}%
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {hovered && (
          <div
            className="pointer-events-none absolute z-20 w-56 rounded-lg border border-slate-700 bg-slate-950/95 text-slate-100 p-3 shadow-lg text-xs space-y-1"
            style={{
              left: Math.min(size.width - 232, Math.max(8, hovered.x + 12)),
              top: Math.min(size.height - 115, Math.max(8, hovered.y + 12)),
            }}
          >
            <div className="flex items-center justify-between font-mono font-semibold">
              <span>{hovered.ticker}</span>
              <span
                className={
                  hovered.dailyChangePct >= 0 ? 'text-emerald-400' : 'text-red-400'
                }
              >
                {formatPct(hovered.dailyChangePct)}
              </span>
            </div>
            <div className="text-slate-400 truncate">{hovered.name}</div>
            <div className="text-slate-400 text-[11px]">{hovered.sector}</div>
            <div className="pt-1.5 mt-1 border-t border-slate-800 flex justify-between font-mono tabular-nums">
              <span className="text-slate-400">Value ({hovered.weightPct.toFixed(1)}%)</span>
              <span>{formatINRCompact(hovered.value)}</span>
            </div>
            <div className="flex justify-between font-mono tabular-nums">
              <span className="text-slate-400">Total P&L</span>
              <span
                className={
                  hovered.unrealizedPnlPct >= 0 ? 'text-emerald-400' : 'text-red-400'
                }
              >
                {formatPct(hovered.unrealizedPnlPct)}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
