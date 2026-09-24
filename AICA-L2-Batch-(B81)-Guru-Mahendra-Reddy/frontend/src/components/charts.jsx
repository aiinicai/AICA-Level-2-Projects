// Charts.
//
// Two rules govern every chart here, both from the spec:
//   1. Colour means status only. Data marks are one navy hue; a status colour
//      appears only where a value has actually crossed a threshold.
//   2. Nothing is dual-axis, nothing is a rainbow, and a label never sits on
//      every point — the tooltip and the axis carry the rest.
//
// Ordered encodings (Fixed → Variable → Discretionary, ageing buckets) use a
// validated single-hue ordinal ramp. Waterfalls use a diverging pair chosen so
// that neither pole can be mistaken for a status colour.
import React from 'react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line,
  LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { MARK, cls, inr, inrShort, st } from '../lib/format'

const AXIS = { stroke: MARK.axis, tick: { fill: '#64748b', fontSize: 11 }, tickLine: false }
const GRID = { stroke: MARK.grid, strokeDasharray: '', vertical: false }

// ---------------------------------------------------------------------------
// Tooltip — one component, so every chart explains itself the same way
// ---------------------------------------------------------------------------
export function Tip({ active, payload, label, rows, note, money = true }) {
  if (!active || !payload?.length) return null
  const items = rows ? rows(payload[0].payload) : payload.map((p) => ({
    key: p.name, value: p.value, colour: p.color ?? p.fill,
  }))
  return (
    <div className="rounded-lg bg-ink text-white shadow-pop px-3 py-2.5 min-w-[168px]">
      <p className="text-2xs font-semibold text-white/70 mb-1.5">{label}</p>
      <div className="space-y-1">
        {items.filter((i) => i && i.value !== null && i.value !== undefined).map((i, k) => (
          <div key={k} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-2xs text-white/85">
              {i.colour && <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: i.colour }} />}
              {i.key}
            </span>
            <span className="text-2xs font-semibold tnum">
              {i.raw ?? (money ? inr(i.value) : i.value)}
            </span>
          </div>
        ))}
      </div>
      {note && <p className="text-2xs text-white/55 mt-2 pt-2 border-t border-white/15 max-w-[220px] leading-relaxed">{note}</p>}
    </div>
  )
}

const Frame = ({ height = 240, children }) => (
  <div style={{ height }} className="w-full">
    <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>
  </div>
)

// ---------------------------------------------------------------------------
// Cash — last 12 months (solid) and next 13 weeks (dashed) on one line, with a
// confidence band that widens with distance and the minimum cash floor drawn
// across. SPEC Tab 1, Band 5 left.
// ---------------------------------------------------------------------------
export function CashTrend({ actual = [], forecast = [], floor, height = 268 }) {
  const data = [
    ...actual.map((a) => ({ label: a.label, actual: a.closing_cash, date: a.date })),
    ...forecast.map((f) => ({
      label: f.label, forecast: f.closing_cash, date: f.date,
      band: [f.band_low, f.band_high], confidence: f.confidence,
    })),
  ]
  // Join the two lines so there is no visual gap at the handover.
  const lastActual = actual[actual.length - 1]
  const joinIdx = actual.length - 1
  if (lastActual && data[joinIdx]) data[joinIdx].forecast = lastActual.closing_cash

  return (
    <Frame height={height}>
      <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="label" {...AXIS} interval="preserveStartEnd" minTickGap={28} />
        <YAxis {...AXIS} width={54} tickFormatter={(v) => inrShort(v)} />
        <Tooltip content={<Tip rows={(p) => [
          p.actual !== undefined && { key: 'Actual closing cash', value: p.actual, colour: MARK.main },
          p.forecast !== undefined && { key: 'Forecast closing cash', value: p.forecast, colour: MARK.light },
          p.band && { key: 'Range', raw: `${inrShort(p.band[0])} – ${inrShort(p.band[1])}` },
          p.confidence && { key: 'Confidence', raw: p.confidence },
        ]} />} cursor={{ stroke: MARK.axis }} />
        {floor ? (
          <ReferenceLine y={floor} stroke={MARK.floor} strokeWidth={1.5}
            label={{ value: `Minimum cash floor ${inrShort(floor)}`, position: 'insideTopLeft',
                     fill: MARK.floor, fontSize: 10, fontWeight: 600, dy: -4 }} />
        ) : null}
        <Area type="monotone" dataKey="band" stroke="none" fill={MARK.light}
              fillOpacity={0.16} isAnimationActive={false} connectNulls />
        <Line type="monotone" dataKey="actual" stroke={MARK.main} strokeWidth={2}
              dot={false} isAnimationActive={false} />
        <Line type="monotone" dataKey="forecast" stroke={MARK.light} strokeWidth={2}
              strokeDasharray="5 4" dot={false} isAnimationActive={false} connectNulls />
      </ComposedChart>
    </Frame>
  )
}

// ---------------------------------------------------------------------------
// Where the cash went — horizontal bars by category, shaded by how
// controllable the cost is (Fixed → Variable → Discretionary). Ordered, so a
// single-hue ordinal ramp is the right encoding.
// ---------------------------------------------------------------------------
const NATURE = [
  { key: 'Fixed', colour: MARK.ordinal[0], note: 'Committed — cannot be moved this quarter' },
  { key: 'Variable', colour: MARK.ordinal[1], note: 'Moves with activity' },
  { key: 'Discretionary', colour: MARK.ordinal[2], note: 'Can be cut by decision' },
]

export function CategoryBars({ rows = [], height = 268, onSelect }) {
  return (
    <>
      <Frame height={height}>
        <BarChart data={rows} layout="vertical" barSize={16}
                  margin={{ top: 4, right: 56, bottom: 4, left: 4 }}>
          <CartesianGrid {...GRID} horizontal={false} vertical />
          <XAxis type="number" {...AXIS} tickFormatter={(v) => inrShort(v)} />
          <YAxis type="category" dataKey="category" {...AXIS} width={128} />
          <Tooltip cursor={{ fill: '#f6f7fb' }} content={<Tip rows={(p) => [
            { key: 'Total', value: p.total },
            ...NATURE.filter((n) => p[n.key]).map((n) => ({ key: n.key, value: p[n.key], colour: n.colour })),
            { key: 'Share of spend', raw: `${p.pct}%` },
          ]} />} />
          {NATURE.map((n, i) => (
            <Bar key={n.key} dataKey={n.key} stackId="a" fill={n.colour}
                 stroke="#ffffff" strokeWidth={2}
                 radius={i === NATURE.length - 1 ? [0, 4, 4, 0] : 0}
                 isAnimationActive={false}
                 onClick={(e) => onSelect?.(e?.payload)}
                 cursor={onSelect ? 'pointer' : undefined} />
          ))}
        </BarChart>
      </Frame>
      <Legend items={NATURE.map((n) => ({ label: n.key, colour: n.colour, note: n.note }))} />
    </>
  )
}

// ---------------------------------------------------------------------------
// Waterfall — plan → actual, or runway last month → this month.
// Poles are teal/violet: polarity, deliberately not status hues.
// ---------------------------------------------------------------------------
export function Waterfall({ bars = [], height = 260, money = true, unit = '' }) {
  let running = 0
  const data = bars.map((b) => {
    if (b.type === 'start') { running = b.value; return { ...b, base: 0, span: b.value, kind: 'total' } }
    if (b.type === 'end') return { ...b, base: 0, span: b.value, kind: 'total' }
    const base = b.value >= 0 ? running : running + b.value
    const row = { ...b, base, span: Math.abs(b.value), kind: b.value >= 0 ? 'up' : 'down' }
    running += b.value
    return row
  })
  const fmt = money ? inrShort : (v) => `${Number(v).toFixed(1)}${unit}`

  const lo = Math.min(0, ...data.map((r) => r.base), ...data.map((r) => r.base + r.span))
  const hi = Math.max(...data.map((r) => r.base + r.span), ...data.map((r) => r.base))
  const pad = Math.max((hi - lo) * 0.12, 1)

  return (
    <>
      <Frame height={height}>
        <BarChart data={data} margin={{ top: 16, right: 12, bottom: 4, left: 4 }} barSize={30}>
          <CartesianGrid {...GRID} />
          <XAxis dataKey="label" {...AXIS} interval={0} height={44}
                 tick={{ fill: '#64748b', fontSize: 10 }} angle={-12} textAnchor="end" />
          <YAxis {...AXIS} width={54} tickFormatter={fmt}
                 domain={[Math.max(lo - pad, lo === 0 ? 0 : lo - pad), hi + pad]}
                 allowDataOverflow={false} />
          <Tooltip cursor={{ fill: '#f6f7fb' }} content={<Tip money={false} rows={(p) => [
            { key: p.kind === 'total' ? 'Position' : p.value >= 0 ? 'Improves by' : 'Costs',
              raw: fmt(p.kind === 'total' ? p.value : Math.abs(p.value)),
              colour: p.kind === 'total' ? MARK.deep : p.kind === 'up' ? MARK.pos : MARK.neg },
            p.reverses && { key: 'Reverses', raw: 'Yes — timing only' },
          ]} note={p => undefined} />} />
          <Bar dataKey="base" stackId="w" fill="transparent" isAnimationActive={false} />
          <Bar dataKey="span" stackId="w" radius={3} isAnimationActive={false}
               stroke="#ffffff" strokeWidth={2}>
            {data.map((r, i) => (
              <Cell key={i}
                    fill={r.kind === 'total' ? MARK.deep : r.kind === 'up' ? MARK.pos : MARK.neg}
                    fillOpacity={r.reverses ? 0.45 : 1} />
            ))}
          </Bar>
        </BarChart>
      </Frame>
      <Legend items={[
        { label: 'Opening / closing', colour: MARK.deep },
        { label: 'Improves the position', colour: MARK.pos },
        { label: 'Costs the position', colour: MARK.neg },
        { label: 'Timing — reverses later', colour: MARK.neg, faded: true },
      ]} />
    </>
  )
}

// ---------------------------------------------------------------------------
// Weekly cash — in / out bars with the closing line over them and the floor
// drawn across. SPEC Tab 6.
// ---------------------------------------------------------------------------
export function WeeklyCash({ weeks = [], floor, height = 280 }) {
  const data = weeks.map((w) => ({
    label: w.label.split(' · ')[0], week: w.label,
    In: w.total_in, Out: -w.total_out, closing: w.closing_cash,
    below: w.below_floor, confidence: w.confidence,
  }))
  return (
    <>
      <Frame height={height}>
        <ComposedChart data={data} margin={{ top: 10, right: 12, bottom: 4, left: 4 }}
                       barSize={18} barGap={2}>
          <CartesianGrid {...GRID} />
          <XAxis dataKey="label" {...AXIS} interval={0} tick={{ fill: '#64748b', fontSize: 10 }} />
          <YAxis {...AXIS} width={54} tickFormatter={(v) => inrShort(v)} />
          <Tooltip cursor={{ fill: '#f6f7fb' }} content={<Tip rows={(p) => [
            { key: 'Money in', value: p.In, colour: MARK.main },
            { key: 'Money out', value: Math.abs(p.Out), colour: MARK.light },
            { key: 'Closing cash', value: p.closing, colour: MARK.deep },
            { key: 'Confidence', raw: p.confidence },
            p.below && { key: 'Below the floor', raw: 'Yes' },
          ]} />} />
          <ReferenceLine y={0} stroke={MARK.axis} />
          {floor ? <ReferenceLine y={floor} stroke={MARK.floor} strokeWidth={1.5}
            label={{ value: 'Floor', position: 'right', fill: MARK.floor, fontSize: 10, fontWeight: 600 }} /> : null}
          <Bar dataKey="In" fill={MARK.main} radius={[3, 3, 0, 0]} isAnimationActive={false}
               stroke="#ffffff" strokeWidth={2} />
          <Bar dataKey="Out" fill={MARK.light} radius={[0, 0, 3, 3]} isAnimationActive={false}
               stroke="#ffffff" strokeWidth={2} />
          <Line type="monotone" dataKey="closing" stroke={MARK.deep} strokeWidth={2}
                isAnimationActive={false}
                dot={(props) => {
                  const { cx, cy, payload, index } = props
                  return <circle key={index} cx={cx} cy={cy} r={payload.below ? 4.5 : 3}
                                 fill={payload.below ? st('Red').hex : MARK.deep}
                                 stroke="#fff" strokeWidth={2} />
                }} />
        </ComposedChart>
      </Frame>
      <Legend items={[
        { label: 'Money in', colour: MARK.main },
        { label: 'Money out', colour: MARK.light },
        { label: 'Closing cash', colour: MARK.deep },
        { label: 'Week below the floor', colour: st('Red').hex },
      ]} />
    </>
  )
}

// ---------------------------------------------------------------------------
// Ageing — one stacked bar. Bucket age IS a status, so the status palette is
// the correct encoding here, and every segment is directly labelled.
// ---------------------------------------------------------------------------
export function AgeingBar({ buckets = [], onSelect }) {
  const total = buckets.reduce((s, b) => s + b.amount, 0) || 1
  return (
    <div>
      <div className="flex w-full h-9 rounded-lg overflow-hidden bg-line-soft gap-[2px]">
        {buckets.filter((b) => b.amount > 0).map((b) => (
          <button key={b.bucket} onClick={() => onSelect?.(b)}
                  title={`${b.bucket} · ${inr(b.amount)} · ${b.pct}%`}
                  style={{ width: `${(b.amount / total) * 100}%`, background: st(b.status).hex }}
                  className="h-full transition-opacity hover:opacity-80 first:rounded-l-lg last:rounded-r-lg" />
        ))}
      </div>
      <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-x-4 gap-y-2">
        {buckets.map((b) => (
          <button key={b.bucket} onClick={() => onSelect?.(b)}
                  className="text-left group min-w-0">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: st(b.status).hex }} />
              <span className="text-2xs text-ink-muted truncate">{b.bucket}</span>
            </span>
            <span className="block text-[13px] font-semibold text-ink tnum mt-0.5 group-hover:text-navy-600">
              {inr(b.amount)}
            </span>
            <span className="block text-2xs text-ink-faint tnum">{b.pct}% · {b.count} inv</span>
          </button>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Trends
// ---------------------------------------------------------------------------
export function TrendLine({ data = [], keys = [], height = 220, floor, money = true,
                           xKey = 'label', formatter }) {
  const fmt = formatter || (money ? inrShort : ((v) => Number(v).toFixed(1)))
  return (
    <>
      <Frame height={height}>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid {...GRID} />
          <XAxis dataKey={xKey} {...AXIS} interval="preserveStartEnd" minTickGap={24} />
          <YAxis {...AXIS} width={52} tickFormatter={fmt} />
          <Tooltip cursor={{ stroke: MARK.axis }} content={<Tip money={money} rows={(p) =>
            keys.map((k) => ({ key: k.label, value: p[k.key], colour: k.colour,
                               raw: p[k.key] === undefined ? undefined : fmt(p[k.key]) }))} />} />
          {floor ? <ReferenceLine y={floor} stroke={MARK.floor} strokeWidth={1.5} /> : null}
          {keys.map((k) => (
            <Line key={k.key} type="monotone" dataKey={k.key} stroke={k.colour || MARK.main}
                  strokeWidth={2} strokeDasharray={k.dashed ? '5 4' : undefined}
                  dot={false} isAnimationActive={false} connectNulls />
          ))}
        </LineChart>
      </Frame>
      {keys.length > 1 && <Legend items={keys.map((k) => ({
        label: k.label, colour: k.colour || MARK.main, dashed: k.dashed }))} />}
    </>
  )
}

export function ColumnChart({ data = [], keys = [], height = 220, xKey = 'label', stacked }) {
  return (
    <>
      <Frame height={height}>
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }} barSize={16}>
          <CartesianGrid {...GRID} />
          <XAxis dataKey={xKey} {...AXIS} interval="preserveStartEnd" minTickGap={16} />
          <YAxis {...AXIS} width={52} tickFormatter={(v) => inrShort(v)} />
          <Tooltip cursor={{ fill: '#f6f7fb' }} content={<Tip rows={(p) =>
            keys.map((k) => ({ key: k.label, value: p[k.key], colour: k.colour }))} />} />
          {keys.map((k, i) => (
            <Bar key={k.key} dataKey={k.key} fill={k.colour || MARK.main}
                 stackId={stacked ? 's' : undefined} stroke="#ffffff" strokeWidth={2}
                 radius={!stacked || i === keys.length - 1 ? [3, 3, 0, 0] : 0}
                 isAnimationActive={false} />
          ))}
        </BarChart>
      </Frame>
      {keys.length > 1 && <Legend items={keys.map((k) => ({ label: k.label, colour: k.colour || MARK.main }))} />}
    </>
  )
}

/** Tiny inline trend for a ratio row. No axes, no labels — the number is beside it. */
export function Spark({ data = [], width = 72, height = 22, status = 'Green' }) {
  if (data.length < 2) return <span className="text-2xs text-ink-faint">—</span>
  const vals = data.map((d) => d.value)
  const min = Math.min(...vals), max = Math.max(...vals)
  const span = max - min || 1
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * (width - 2) + 1
    const y = height - 2 - ((d.value - min) / span) * (height - 4)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  const last = data[data.length - 1]
  const lx = width - 1
  const ly = height - 2 - ((last.value - min) / span) * (height - 4)
  return (
    <svg width={width} height={height} className="overflow-visible" aria-hidden="true">
      <polyline points={pts} fill="none" stroke={MARK.light} strokeWidth="1.6"
                strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={lx} cy={ly} r="2.6" fill={st(status).hex} stroke="#fff" strokeWidth="1.5" />
    </svg>
  )
}

// ---------------------------------------------------------------------------
export function Legend({ items = [] }) {
  if (!items.length) return null
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 mt-3">
      {items.map((i) => (
        <span key={i.label} className="inline-flex items-center gap-1.5 text-2xs text-ink-muted"
              title={i.note}>
          {i.dashed ? (
            <span className="w-4 h-0 border-t-2 border-dashed shrink-0" style={{ borderColor: i.colour }} />
          ) : (
            <span className="w-2.5 h-2.5 rounded-sm shrink-0"
                  style={{ background: i.colour, opacity: i.faded ? 0.45 : 1 }} />
          )}
          {i.label}
        </span>
      ))}
    </div>
  )
}
