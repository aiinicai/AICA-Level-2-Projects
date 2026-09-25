// TAB 1 — Today. "Am I fine, and what needs me this week?"
//
// Band 1 must answer that in five seconds without scrolling, so the five
// numbers sit in one row above everything else and nothing is allowed to push
// them down.
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp, useEndpoint } from '../lib/store'
import { cls, d, inr, st } from '../lib/format'
import { Card, Dot, Empty, ErrorNote, Icon, Loading, StatusPill, Table, TD, TH } from '../components/ui'
import { HeroFigure, Stat, StatRow } from '../components/Figure'
import { CashTrend, CategoryBars } from '../components/charts'

export default function Today() {
  const { data, loading, error, reload } = useEndpoint('/api/today')
  const { openTrace } = useApp()
  const nav = useNavigate()

  if (loading && !data) return <Loading label="Working out your position…" rows={5} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data) return null

  return (
    <div className="space-y-5">
      {/* ---- Band 1 — The Five Numbers ---------------------------------- */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
        {data.five_numbers.map((f) => <HeroFigure key={f.label} figure={f} />)}
      </div>

      {/* ---- Band 2 — What Needs Me This Week --------------------------- */}
      <Card
        title="What needs me this week"
        sub={data.what_needs_me.basis}
        right={<span className="text-2xs text-ink-muted">
          {data.what_needs_me.shown} of {data.what_needs_me.total_found}
        </span>}
        pad={false}
      >
        {data.what_needs_me.rows.length === 0 ? (
          <Empty>Nothing needs a decision this week. The position is holding.</Empty>
        ) : (
          <Table className="px-4 pb-1">
            <thead><tr>
              <TH left className="w-10">#</TH>
              <TH left>Item</TH>
              <TH>Amount</TH>
              <TH>By when</TH>
              <TH left>Owner</TH>
              <TH left>Action</TH>
              <TH className="w-8" />
            </tr></thead>
            <tbody>
              {data.what_needs_me.rows.map((r) => (
                <tr key={r.priority} className="tr-hover cursor-pointer group"
                    onClick={() => nav(r.link)}>
                  <TD left className="text-ink-faint font-semibold">{r.priority}</TD>
                  <TD left className="!text-ink font-medium max-w-[420px] whitespace-normal">
                    <span className="flex items-start gap-2">
                      <Dot status={r.severity} className="mt-1.5" />
                      <span>{r.item}</span>
                    </span>
                  </TD>
                  <TD className="font-semibold">{r.amount > 0 ? inr(r.amount) : '—'}</TD>
                  <TD>{d(r.by_when)}</TD>
                  <TD left>{r.owner}</TD>
                  <TD left className="text-ink-muted max-w-[280px] whitespace-normal">{r.action}</TD>
                  <TD>
                    <Icon name="chevronRight" size={14}
                          className="text-ink-faint opacity-0 group-hover:opacity-100 transition-opacity" />
                  </TD>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <div className="grid xl:grid-cols-[1.05fr_1.35fr] gap-5 items-start">
        {/* ---- Band 3 — The Week Ahead --------------------------------- */}
        <WeekAhead week={data.week_ahead} />

        {/* ---- Band 4 — Reading of the Position ------------------------ */}
        <Reading reading={data.reading} />
      </div>

      {/* ---- Band 5 — Two charts, side by side ------------------------- */}
      <div className="grid xl:grid-cols-2 gap-5 items-start">
        <Card title={data.cash_chart.title}
              sub="Actuals solid, forecast dashed, with the range it could fall in"
              basis={data.cash_chart.basis}>
          <CashTrend actual={data.cash_chart.actual} forecast={data.cash_chart.forecast}
                     floor={data.cash_chart.floor} />
        </Card>

        <Card title="Where the cash went — last 3 months"
              sub="Shaded by how controllable each cost is"
              basis={data.where_cash_went.basis}>
          <CategoryBars rows={data.where_cash_went.rows}
                        onSelect={(r) => r?.trace && openTrace(r.trace, r.category)} />
        </Card>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
function WeekAhead({ week }) {
  const rows = [
    ['Opening cash', week.opening_cash, null],
    ['Expected in — gross', week.expected_in_gross, 'What is billed and due'],
    ['Expected in — weighted', week.expected_in_weighted, 'What we actually expect to receive'],
    ['Committed out', -week.committed_out, null],
    ['Net movement', week.net_movement, null],
  ]
  return (
    <Card title="The week ahead"
          sub={`${d(week.week_start)} to ${d(week.week_end)}`}
          basis={week.basis}>
      <div className="space-y-0">
        {rows.map(([label, value, hint], i) => {
          const emphasis = label === 'Expected in — weighted'
          return (
            <div key={label}
                 className={cls('flex items-baseline justify-between gap-4 py-2',
                                i < rows.length - 1 && 'border-b border-line-soft')}>
              <span className="min-w-0">
                <span className={cls('text-[13px]', emphasis ? 'font-semibold text-ink' : 'text-ink-soft')}>
                  {label}
                </span>
                {hint && <span className="block text-2xs text-ink-faint">{hint}</span>}
              </span>
              <span className={cls('tnum shrink-0',
                emphasis ? 'text-[18px] font-semibold text-ink' : 'text-[14px] font-medium text-ink-soft')}>
                {inr(value, { sign: label === 'Net movement' })}
              </span>
            </div>
          )
        })}
      </div>

      <div className="mt-3 pt-3 border-t border-line flex items-baseline justify-between gap-4">
        <span className="text-[13px] font-semibold text-ink">Closing cash</span>
        <span className={cls('text-[20px] font-semibold tnum',
                             week.below_floor ? 'text-red' : 'text-ink')}>
          {inr(week.closing_cash)}
        </span>
      </div>

      <div className="mt-3 rounded-lg bg-canvas border border-line px-3.5 py-3">
        <div className="flex items-center gap-1.5 mb-1">
          <Icon name="alert" size={13} className="text-ink-muted" />
          <span className="label">If the top client slips</span>
        </div>
        <p className="text-2xs text-ink-muted leading-relaxed">
          {week.if_top_client_slips.assumption}
        </p>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-[17px] font-semibold tnum text-ink">
            {inr(week.if_top_client_slips.closing_cash)}
          </span>
          <span className="text-2xs font-semibold text-amber tnum">
            {inr(week.if_top_client_slips.delta, { sign: true })}
          </span>
        </div>
      </div>
    </Card>
  )
}

// ---------------------------------------------------------------------------
function Reading({ reading }) {
  const conf = reading.confidence
  const confStatus = conf === 'High' ? 'Green' : conf === 'Medium' ? 'Amber' : 'Grey'

  return (
    <Card
      title="Reading of the position"
      sub={reading.source === 'ai' ? 'Written by the liquidity agent from the figures above'
                                   : 'Written from the figures above'}
      right={<StatusPill status={confStatus} label={`Confidence: ${conf}`} />}
    >
      {reading.collapsed ? (
        <div className="rounded-lg border border-grey-line bg-grey-bg px-4 py-3.5">
          <p className="text-[13px] text-grey font-medium">{reading.reason}</p>
        </div>
      ) : (
        <p className="text-[14px] leading-[1.75] text-ink-soft">{reading.text}</p>
      )}

      <div className="mt-4 pt-3.5 border-t border-line-soft">
        <div className="flex items-center gap-1.5 mb-2">
          <Icon name="info" size={13} className="text-ink-muted" />
          <span className="label">Not visible to me</span>
        </div>
        <ul className="space-y-1.5">
          {reading.not_visible.map((g, i) => (
            <li key={i} className="flex items-start gap-2 text-2xs text-ink-muted leading-relaxed">
              <span className="mt-1 w-1 h-1 rounded-full bg-grey shrink-0" />
              {g}
            </li>
          ))}
        </ul>
      </div>

      <p className="basis mt-3.5 pt-2.5 border-t border-line-soft">{reading.footer}</p>
    </Card>
  )
}
