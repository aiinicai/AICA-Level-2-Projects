import React from 'react';
import { formatMoney } from '../engine/kpiEngine';
import type { CurrencyCode } from '../types/mis';

interface WaterfallStep {
  label: string;
  amount: number;
  type: 'total' | 'plus' | 'minus';
}

export const WaterfallChart: React.FC<{
  steps: WaterfallStep[];
  currency: CurrencyCode;
  masked: boolean;
}> = ({ steps, currency, masked }) => {
  const width = 620;
  const height = 240;
  const pad = { top: 24, right: 16, bottom: 44, left: 60 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  let running = 0;
  const bars = steps.map((s) => {
    if (s.type === 'total') {
      const start = 0;
      const end = s.amount;
      running = s.amount;
      return { ...s, start, end };
    }
    const start = running;
    const end = running + s.amount;
    running = end;
    return { ...s, start, end };
  });

  const maxVal = Math.max(1, ...bars.map((b) => Math.max(b.start, b.end, 0)));
  const minVal = Math.min(0, ...bars.map((b) => Math.min(b.start, b.end)));
  const range = Math.max(1, maxVal - minVal);
  const yOf = (v: number) => pad.top + ((maxVal - v) / range) * plotH;
  const bandW = plotW / bars.length;

  return (
    <div dir="ltr">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto" role="img" aria-label="Income Statement Waterfall Bridge">
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const val = minVal + range * t;
          const y = yOf(val);
          return (
            <g key={t}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="var(--re-border)" strokeDasharray="3 3" />
              <text x={pad.left - 6} y={y + 3} textAnchor="end" fontSize="9.5" fill="var(--re-text-muted)" className="font-mono-num">
                {masked ? '•••' : `${(val / 1_000_000).toFixed(1)}M`}
              </text>
            </g>
          );
        })}
        {bars.map((b, i) => {
          const y1 = yOf(Math.max(b.start, b.end));
          const y2 = yOf(Math.min(b.start, b.end));
          const barH = Math.max(3, y2 - y1);
          const x = pad.left + i * bandW + bandW * 0.18;
          const w = bandW * 0.64;
          const fill =
            b.type === 'total'
              ? 'var(--re-primary)'
              : b.amount >= 0
              ? '#16a34a'
              : '#dc2626';

          return (
            <g key={b.label}>
              <rect x={x} y={y1} width={w} height={barH} rx={3} fill={fill} opacity={0.9}>
                <title>{`${b.label}: ${formatMoney(b.amount, currency, masked)}`}</title>
              </rect>
              <text
                x={x + w / 2}
                y={Math.max(12, y1 - 5)}
                textAnchor="middle"
                fontSize="9"
                fill="var(--re-text)"
                className="font-mono-num"
              >
                {masked ? '••' : `${(b.amount / 1_000_000).toFixed(2)}M`}
              </text>
              <text
                x={x + w / 2}
                y={height - 14}
                textAnchor="middle"
                fontSize="9.5"
                fill="var(--re-text-muted)"
              >
                {b.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

export const TrendLineChart: React.FC<{
  series: { label: string; primary: number; secondary: number; tertiary?: number }[];
  primaryName: string;
  secondaryName: string;
  tertiaryName?: string;
  masked: boolean;
}> = ({ series, primaryName, secondaryName, tertiaryName, masked }) => {
  const width = 640;
  const height = 240;
  const pad = { top: 20, right: 16, bottom: 38, left: 56 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const maxVal = Math.max(
    1,
    ...series.flatMap((s) => [s.primary, s.secondary, s.tertiary ?? 0])
  );
  const xOf = (i: number) => pad.left + (i / Math.max(1, series.length - 1)) * plotW;
  const yOf = (v: number) => pad.top + ((maxVal - v) / maxVal) * plotH;

  const buildPath = (vals: number[]) =>
    vals.map((v, i) => `${i === 0 ? 'M' : 'L'} ${xOf(i).toFixed(1)} ${yOf(v).toFixed(1)}`).join(' ');

  return (
    <div>
      <div className="flex flex-wrap items-center gap-4 mb-2 text-xs" style={{ color: 'var(--re-text-muted)' }}>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-3 h-0.5 inline-block" style={{ backgroundColor: 'var(--re-accent)' }} />
          {primaryName}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-3 h-0.5 inline-block bg-emerald-600" />
          {secondaryName}
        </span>
        {tertiaryName && (
          <span className="inline-flex items-center gap-1.5">
            <span className="w-3 h-0.5 inline-block bg-sky-600" />
            {tertiaryName}
          </span>
        )}
      </div>
      <div dir="ltr">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto" role="img" aria-label="24-Month Trend Chart">
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const val = maxVal * t;
          const y = yOf(val);
          return (
            <g key={t}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="var(--re-border)" strokeDasharray="3 3" />
              <text x={pad.left - 6} y={y + 3} textAnchor="end" fontSize="9.5" fill="var(--re-text-muted)" className="font-mono-num">
                {masked ? '•••' : `${(val / 1_000_000).toFixed(1)}M`}
              </text>
            </g>
          );
        })}
        <path d={buildPath(series.map((s) => s.primary))} fill="none" stroke="var(--re-accent)" strokeWidth="2.5" />
        <path d={buildPath(series.map((s) => s.secondary))} fill="none" stroke="#16a34a" strokeWidth="2.2" />
        {tertiaryName && (
          <path
            d={buildPath(series.map((s) => s.tertiary ?? 0))}
            fill="none"
            stroke="#0284c7"
            strokeWidth="2"
            strokeDasharray="4 3"
          />
        )}
        {series.map((s, i) => {
          if (series.length > 14 && i % 3 !== 0 && i !== series.length - 1) return null;
          return (
            <text
              key={s.label}
              x={xOf(i)}
              y={height - 12}
              textAnchor="middle"
              fontSize="9"
              fill="var(--re-text-muted)"
              className="font-mono-num"
            >
              {s.label}
            </text>
          );
        })}
        </svg>
      </div>
    </div>
  );
};

export const SCurveChart: React.FC<{
  points: { period: string; plannedPct: number; actualPct: number; certifiedPct: number }[];
}> = ({ points }) => {
  const width = 640;
  const height = 240;
  const pad = { top: 18, right: 18, bottom: 36, left: 44 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const xOf = (i: number) => pad.left + (i / Math.max(1, points.length - 1)) * plotW;
  const yOf = (pct: number) => pad.top + ((100 - Math.min(100, Math.max(0, pct))) / 100) * plotH;

  const pathFor = (fn: (p: typeof points[number]) => number) =>
    points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xOf(i).toFixed(1)} ${yOf(fn(p)).toFixed(1)}`).join(' ');

  return (
    <div>
      <div className="flex flex-wrap items-center gap-4 mb-2 text-xs" style={{ color: 'var(--re-text-muted)' }}>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-3 h-0.5 inline-block bg-slate-400" /> Planned Progress %
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-3 h-0.5 inline-block" style={{ backgroundColor: 'var(--re-accent)' }} /> Actual Physical %
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-3 h-0.5 inline-block bg-emerald-600" /> Certified Progress %
        </span>
      </div>
      <div dir="ltr">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto" role="img" aria-label="Construction S-Curve">
        {[0, 25, 50, 75, 100].map((v) => {
          const y = yOf(v);
          return (
            <g key={v}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} stroke="var(--re-border)" strokeDasharray="3 3" />
              <text x={pad.left - 6} y={y + 3} textAnchor="end" fontSize="9.5" fill="var(--re-text-muted)" className="font-mono-num">
                {v}%
              </text>
            </g>
          );
        })}
        <path d={pathFor((p) => p.plannedPct)} fill="none" stroke="#94a3b8" strokeWidth="2" strokeDasharray="5 3" />
        <path d={pathFor((p) => p.actualPct)} fill="none" stroke="var(--re-accent)" strokeWidth="2.6" />
        <path d={pathFor((p) => p.certifiedPct)} fill="none" stroke="#16a34a" strokeWidth="2" />
        {points.map((p, i) => {
          if (points.length > 12 && i % 4 !== 0 && i !== points.length - 1) return null;
          return (
            <text
              key={p.period}
              x={xOf(i)}
              y={height - 10}
              textAnchor="middle"
              fontSize="9"
              fill="var(--re-text-muted)"
              className="font-mono-num"
            >
              {p.period}
            </text>
          );
        })}
        </svg>
      </div>
    </div>
  );
};
