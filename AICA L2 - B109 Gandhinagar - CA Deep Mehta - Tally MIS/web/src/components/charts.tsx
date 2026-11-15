import { useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { fmtMoney, fmtValue } from '@shared/format';
import type { Unit } from '@shared/types';

/** Categorical slots in the validated fixed order; colour follows the series, never its rank. */
export const SERIES = ['var(--series-1)', 'var(--series-2)', 'var(--series-3)', 'var(--series-4)', 'var(--series-5)', 'var(--series-6)', 'var(--series-7)', 'var(--series-8)'];

export interface SeriesDef { key: string; label: string; color?: string; dashed?: boolean }

const axisTick = { fill: 'var(--text-muted)', fontSize: 11 };
const compact = (unit: Unit) => (v: number) => (unit === 'currency' ? fmtMoney(v) : fmtValue(v, unit));

function TipBox({ active, payload, label, unit, series }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="tooltip-box">
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{label}</div>
      {payload.map((p: any) => {
        const s = (series as SeriesDef[]).find((x) => x.key === p.dataKey);
        return (
          <div key={p.dataKey} className="row" style={{ gap: 6, flexWrap: 'nowrap' }}>
            <span className="dot" style={{ background: p.color ?? p.payload?.fill }} />
            <span className="secondary">{s?.label ?? p.name}</span><span className="spacer" />
            <span className="num" style={{ fontWeight: 600 }}>{p.value === null || p.value === undefined ? '—' : unit === 'currency' ? fmtMoney(p.value, { exact: false }) : fmtValue(p.value, unit)}</span>
          </div>
        );
      })}
    </div>
  );
}

function Legend({ series }: { series: SeriesDef[] }) {
  if (series.length < 2) return null;
  return (
    <div className="legend">
      {series.map((s, i) => (
        <span key={s.key}><span style={{ width: 14, height: 2, background: s.color ?? SERIES[i], display: 'inline-block', borderTop: s.dashed ? '2px dashed' : undefined }} />{s.label}</span>
      ))}
    </div>
  );
}

/** Data table alternative to every chart (accessibility, exact values). */
function TableView({ data, xKey, series, unit }: { data: any[]; xKey: string; series: SeriesDef[]; unit: Unit }) {
  return (
    <div className="table-wrap" style={{ maxHeight: 260 }}>
      <table className="data">
        <thead><tr><th>{xKey}</th>{series.map((s) => <th key={s.key} className="num">{s.label}</th>)}</tr></thead>
        <tbody>{data.map((d, i) => <tr key={i}><td>{d[xKey]}</td>{series.map((s) => <td key={s.key} className="num">{fmtValue(d[s.key], unit, false)}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

function Frame({ title, subtitle, children, table }: { title?: string; subtitle?: string; children: React.ReactNode; table: React.ReactNode }) {
  const [showTable, setShowTable] = useState(false);
  return (
    <div>
      <div className="row" style={{ alignItems: 'baseline' }}>
        {title && <h2 style={{ marginBottom: 2 }}>{title}</h2>}
        <span className="spacer" />
        <button className="btn sm no-print" onClick={() => setShowTable(!showTable)} aria-pressed={showTable}>{showTable ? 'Chart' : 'Table'}</button>
      </div>
      {subtitle && <p className="small muted">{subtitle}</p>}
      {showTable ? table : children}
    </div>
  );
}

export function TrendChart({ data, xKey = 'label', series, unit = 'currency', height = 240, title, subtitle, zeroLine }: {
  data: any[]; xKey?: string; series: SeriesDef[]; unit?: Unit; height?: number; title?: string; subtitle?: string; zeroLine?: boolean;
}) {
  return (
    <Frame title={title} subtitle={subtitle} table={<TableView data={data} xKey={xKey} series={series} unit={unit} />}>
      <Legend series={series} />
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 6, right: 12, left: 4, bottom: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey={xKey} tick={axisTick} tickLine={false} axisLine={{ stroke: 'var(--border)' }} minTickGap={12} />
          <YAxis tick={axisTick} tickLine={false} axisLine={false} tickFormatter={compact(unit)} width={70} />
          {zeroLine && <ReferenceLine y={0} stroke="var(--text-muted)" />}
          <Tooltip content={<TipBox unit={unit} series={series} />} cursor={{ stroke: 'var(--text-muted)', strokeDasharray: '3 3' }} />
          {series.map((s, i) => (
            <Line key={s.key} type="linear" dataKey={s.key} name={s.label} stroke={s.color ?? SERIES[i]} strokeWidth={2} strokeDasharray={s.dashed ? '5 4' : undefined}
              dot={data.length <= 1 ? { r: 4 } : false} activeDot={{ r: 5, strokeWidth: 2, stroke: 'var(--surface-1)' }} connectNulls={false} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Frame>
  );
}

export function BarsChart({ data, xKey = 'label', series, unit = 'currency', height = 240, title, subtitle, horizontal, stacked, colorBySign }: {
  data: any[]; xKey?: string; series: SeriesDef[]; unit?: Unit; height?: number; title?: string; subtitle?: string; horizontal?: boolean; stacked?: boolean; colorBySign?: boolean;
}) {
  const h = horizontal ? Math.max(height, data.length * 28 + 30) : height;
  return (
    <Frame title={title} subtitle={subtitle} table={<TableView data={data} xKey={xKey} series={series} unit={unit} />}>
      <Legend series={series} />
      <ResponsiveContainer width="100%" height={h}>
        <BarChart data={data} layout={horizontal ? 'vertical' : 'horizontal'} margin={{ top: 6, right: 12, left: 4, bottom: 0 }} barGap={2} barCategoryGap="22%">
          <CartesianGrid stroke="var(--grid)" vertical={!!horizontal} horizontal={!horizontal} />
          {horizontal ? (
            <>
              <XAxis type="number" tick={axisTick} tickLine={false} axisLine={false} tickFormatter={compact(unit)} />
              <YAxis type="category" dataKey={xKey} tick={axisTick} tickLine={false} axisLine={{ stroke: 'var(--border)' }} width={150} interval={0} />
            </>
          ) : (
            <>
              <XAxis dataKey={xKey} tick={axisTick} tickLine={false} axisLine={{ stroke: 'var(--border)' }} minTickGap={8} />
              <YAxis tick={axisTick} tickLine={false} axisLine={false} tickFormatter={compact(unit)} width={70} />
            </>
          )}
          <ReferenceLine {...(horizontal ? { x: 0 } : { y: 0 })} stroke="var(--text-muted)" />
          <Tooltip content={<TipBox unit={unit} series={series} />} cursor={{ fill: 'var(--surface-2)' }} />
          {series.map((s, i) => (
            <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color ?? SERIES[i]} stackId={stacked ? 'a' : undefined} radius={stacked ? 0 : horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]}
              stroke="var(--surface-1)" strokeWidth={stacked ? 1 : 0} isAnimationActive={false} maxBarSize={42}>
              {colorBySign && data.map((d, j) => <Cell key={j} fill={(d[s.key] ?? 0) < 0 ? 'var(--series-8)' : s.color ?? SERIES[i]} />)}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </Frame>
  );
}

/** Tiny trend line for KPI cards (decorative — values are in the card and its detail dialog). */
export function Sparkline({ data }: { data: { value: number | null }[] }) {
  if (data.filter((d) => d.value !== null).length < 2) return <div style={{ height: 28 }} />;
  return (
    <div aria-hidden style={{ height: 28 }}>
      <ResponsiveContainer width="100%" height={28}>
        <LineChart data={data}><Line dataKey="value" stroke="var(--series-1)" strokeWidth={1.5} dot={false} isAnimationActive={false} connectNulls={false} /></LineChart>
      </ResponsiveContainer>
    </div>
  );
}
