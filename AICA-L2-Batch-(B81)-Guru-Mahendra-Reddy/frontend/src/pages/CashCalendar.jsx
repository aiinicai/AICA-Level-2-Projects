// TAB 6 — Cash Calendar. Which specific week do I have a problem in?
import React, { useState } from 'react'
import { useEndpoint } from '../lib/store'
import { cls, d, inr, inrShort, num, pct } from '../lib/format'
import {
  Card, Dot, Empty, ErrorNote, Icon, Loading, StatusPill, Table, TD, TH, Toggle,
} from '../components/ui'
import { Stat, StatRow } from '../components/Figure'
import { TrendLine, WeeklyCash } from '../components/charts'

const HORIZONS = [{ value: 4, label: '4 weeks' }, { value: 13, label: '13 weeks' },
                  { value: 26, label: '26 weeks' }]

const ROWS = [
  { key: 'opening_cash', label: 'Opening cash', kind: 'total' },
  { key: 'collections_expected', label: 'Collections expected', kind: 'in' },
  { key: 'funding_other_in', label: 'Funding / other in', kind: 'in' },
  { key: 'total_in', label: 'Total in', kind: 'sub' },
  { key: 'people_cost', label: 'People cost', kind: 'out' },
  { key: 'statutory', label: 'Statutory', kind: 'out' },
  { key: 'vendor_payments', label: 'Vendor payments', kind: 'out' },
  { key: 'other_out', label: 'Other out', kind: 'out' },
  { key: 'total_out', label: 'Total out', kind: 'sub' },
  { key: 'net_movement', label: 'Net movement', kind: 'sub' },
  { key: 'closing_cash', label: 'Closing cash', kind: 'total' },
]

export default function CashCalendar() {
  const [weeks, setWeeks] = useState(13)
  const [open, setOpen] = useState(null)
  const { data, loading, error, reload } = useEndpoint('/api/cash-calendar', { weeks }, [weeks])

  if (loading && !data) return <Loading label="Building the forecast from open items…" rows={5} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data) return null

  const low = data.lowest_point
  const acc = data.accuracy

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <Toggle options={HORIZONS} value={weeks} onChange={setWeeks} size="md" />
        <p className="text-2xs text-ink-muted">{data.detail_note}</p>
      </div>

      {/* ---- The single most important output of this tab ------------- */}
      {low && (
        <div className={cls('card card-pad border-l-4',
          low.breaches_zero ? '!border-l-red' : low.breaches_floor ? '!border-l-red' : '!border-l-green')}>
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div className="flex items-start gap-3 min-w-0">
              <Icon name={low.breaches_floor ? 'alert' : 'check'} size={18}
                    className={cls('mt-0.5 shrink-0', low.breaches_floor ? 'text-red' : 'text-green')} />
              <div className="min-w-0">
                <p className={cls('text-[15px] font-semibold',
                                  low.breaches_floor ? 'text-red' : 'text-ink')}>
                  {low.sentence}
                </p>
                <p className="text-2xs text-ink-muted mt-1.5">{data.basis}</p>
              </div>
            </div>
            <div className="flex gap-8 shrink-0">
              <div>
                <span className="label block">Lowest point</span>
                <span className={cls('text-[22px] font-semibold tnum',
                                     low.breaches_floor ? 'text-red' : 'text-ink')}>
                  {inr(low.amount)}
                </span>
              </div>
              <div>
                <span className="label block">Floor</span>
                <span className="text-[22px] font-semibold tnum text-ink-muted">{inr(low.floor)}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <Card title={`Cash in, cash out and the closing balance — next ${weeks} weeks`}
            sub="The floor is drawn across; any week that breaks it is marked"
            basis={data.basis}>
        <WeeklyCash weeks={data.weeks} floor={data.floor} height={300} />
      </Card>

      {/* ---- The grid ------------------------------------------------- */}
      <Card title="Week by week" pad={false}
            sub={`Weeks 1–4 are named invoices and named payments. Beyond that, category estimates.`}>
        <div className="overflow-x-auto px-4 pb-1">
          <table className="border-collapse min-w-full">
            <thead>
              <tr>
                <th className="th th-l sticky left-0 bg-white z-10 min-w-[180px]">&nbsp;</th>
                {data.weeks.map((w) => (
                  <th key={w.index} className="th min-w-[104px]">
                    <button onClick={() => setOpen(w)} className="w-full hover:text-navy-600">
                      <span className="block">{w.label}</span>
                      <span className="block font-normal normal-case tracking-normal mt-0.5">
                        <StatusPill className="!py-0 !text-[10px]"
                          status={w.confidence === 'High' ? 'Green' : w.confidence === 'Medium' ? 'Amber' : 'Grey'}
                          label={w.confidence} />
                      </span>
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.key} className={cls(
                  row.kind === 'total' && 'bg-navy-50/60',
                  row.kind === 'sub' && 'border-t border-line')}>
                  <td className={cls('td text-left sticky left-0 z-10',
                    row.kind === 'total' ? 'bg-navy-50/60 !text-ink font-semibold'
                      : row.kind === 'sub' ? 'bg-white !text-ink font-semibold' : 'bg-white')}>
                    {row.kind === 'out' && <span className="text-ink-faint mr-1.5">−</span>}
                    {row.label}
                  </td>
                  {data.weeks.map((w) => {
                    const v = w[row.key]
                    const breach = row.key === 'closing_cash' && w.below_floor
                    return (
                      <td key={w.index} className={cls('td',
                        row.kind === 'total' && 'font-semibold !text-ink',
                        row.kind === 'sub' && 'font-medium !text-ink',
                        breach && '!text-red font-bold')}>
                        {v === 0 ? <span className="text-ink-faint">—</span> : inrShort(v)}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="basis px-4 pb-4 pt-2 border-t border-line-soft mx-4">
          Amounts are shortened for width — click any week header for the line items behind it.
        </p>
      </Card>

      {/* ---- Forecast accuracy ---------------------------------------- */}
      <div className="grid xl:grid-cols-[1fr_1.4fr] gap-5 items-start">
        <Card title="How much to trust this grid"
              sub={acc.sentence}
              basis="Computed from forecasts as they stood at the time, never re-forecast with hindsight.">
          {acc.weeks ? (
            <StatRow cols={2}>
              <Stat label="Average error" value={`${num(acc.mean_abs_pct)}%`} size="lg"
                    status={acc.mean_abs_pct < 6 ? 'Green' : acc.mean_abs_pct < 12 ? 'Amber' : 'Red'}
                    sub={`Range ${num(acc.min_pct)}% to ${num(acc.max_pct)}%`} />
              <Stat label="Accuracy score" value={`${Math.round(acc.score)}/100`} size="lg" />
            </StatRow>
          ) : <Empty>{acc.sentence}</Empty>}
        </Card>

        {acc.rows?.length > 0 && (
          <Card title="Forecast against actual, last 8 weeks">
            <TrendLine data={acc.rows} height={210} keys={[
              { key: 'forecast', label: 'Forecast closing', colour: '#8b98e2', dashed: true },
              { key: 'actual', label: 'Actual closing', colour: '#2c3690' },
            ]} />
          </Card>
        )}
      </div>

      <WeekDetail week={open} onClose={() => setOpen(null)} floor={data.floor} />
    </div>
  )
}

function WeekDetail({ week, onClose, floor }) {
  if (!week) return null
  const ins = week.items.filter((i) => i.direction === 'in')
  const outs = week.items.filter((i) => i.direction === 'out')

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-ink/25" onClick={onClose} />
      <aside className="relative bg-white h-full w-full max-w-2xl shadow-pop flex flex-col animate-slide">
        <header className="px-5 py-4 border-b border-line flex items-start justify-between gap-4">
          <div>
            <h3 className="text-[15px] font-semibold tracking-tight">
              Week {week.index} · {d(week.week_start)} to {d(week.week_end)}
            </h3>
            <p className="text-2xs text-ink-muted mt-1">
              {week.detail_level === 'line-item'
                ? 'Named invoices and named payments'
                : 'Category-level estimate from the run-rate'} · {week.contracted_pct}% contracted
            </p>
          </div>
          <button onClick={onClose} className="text-ink-faint hover:text-ink p-1 rounded hover:bg-line-soft">
            <Icon name="x" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <div className="card card-pad">
            <div className="grid grid-cols-3 gap-4">
              <div><span className="label block">Opening</span>
                   <span className="text-[17px] font-semibold tnum">{inr(week.opening_cash)}</span></div>
              <div><span className="label block">Net movement</span>
                   <span className="text-[17px] font-semibold tnum">{inr(week.net_movement, { sign: true })}</span></div>
              <div><span className="label block">Closing</span>
                   <span className={cls('text-[17px] font-semibold tnum',
                                        week.below_floor ? 'text-red' : '')}>
                     {inr(week.closing_cash)}</span></div>
            </div>
            {week.below_floor && (
              <p className="mt-3 pt-3 border-t border-line-soft text-[13px] text-red font-medium">
                This week closes below the {inr(floor)} floor.
              </p>
            )}
          </div>

          {week.items.length === 0 ? (
            <Empty>
              This week is a category-level estimate — there are no named items behind it.
              Open weeks 1 to 4 for line-item detail.
            </Empty>
          ) : (
            <>
              <ItemList title="Money in" items={ins} />
              <ItemList title="Money out" items={outs} />
            </>
          )}
        </div>
      </aside>
    </div>
  )
}

function ItemList({ title, items }) {
  if (!items.length) return null
  const total = items.reduce((s, i) => s + i.amount, 0)
  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <span className="label">{title}</span>
        <span className="text-[13px] font-semibold tnum">{inr(total)}</span>
      </div>
      <div className="space-y-1.5">
        {items.map((i, k) => (
          <div key={k} className="rounded-lg border border-line px-3 py-2 flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[13px] text-ink truncate">{i.label}</p>
              <p className="text-2xs text-ink-muted mt-0.5">
                {d(i.date)} · {i.counterparty}
                {!i.contracted && ' · estimated'}
                {i.probability !== null && i.probability !== undefined
                  && ` · ${Math.round(i.probability * 100)}% likely`}
              </p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-[13px] font-semibold tnum">{inr(i.amount)}</p>
              {i.gross !== i.amount && (
                <p className="text-2xs text-ink-faint tnum">of {inr(i.gross)}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
