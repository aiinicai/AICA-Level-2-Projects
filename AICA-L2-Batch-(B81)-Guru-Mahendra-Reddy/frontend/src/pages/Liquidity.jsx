// TAB 3 — Liquidity. Where the money is, and whether the position is sound.
import React, { useState } from 'react'
import { useApp, useEndpoint } from '../lib/store'
import { MARK, cls, d, inr, num, pct, st } from '../lib/format'
import {
  Card, Dot, Empty, ErrorNote, Icon, Loading, StatusPill, Table, TD, TH, Toggle, Why,
} from '../components/ui'
import { Stat, StatRow } from '../components/Figure'
import { Spark, TrendLine } from '../components/charts'

const SUBS = [
  { value: 'where', label: 'Where the money is' },
  { value: 'health', label: 'Health & ratios' },
]

export default function Liquidity() {
  const [sub, setSub] = useState('where')
  const { data, loading, error, reload } = useEndpoint('/api/liquidity')

  if (loading && !data) return <Loading label="Reading the cash position…" rows={4} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data) return null

  return (
    <div className="space-y-5">
      <Toggle options={SUBS} value={sub} onChange={setSub} size="md" />
      {sub === 'where' ? <WherePane w={data.where_the_money_is} />
                       : <HealthPane health={data.health} ratios={data.ratios}
                                     history={data.score_history} />}
    </div>
  )
}

// ---------------------------------------------------------------------------
function WherePane({ w }) {
  const t = w.tiles
  const c = w.concentration
  return (
    <div className="space-y-5">
      <div className="grid md:grid-cols-3 gap-3">
        <TileCard label="Freely available" value={t.freely_available}
                  note="Money we can spend today" status="Green" />
        <TileCard label="Restricted or encumbered" value={t.restricted}
                  note="On the balance sheet, not available to us" status="Grey" />
        <TileCard label="Undrawn sanctioned credit" value={t.undrawn_credit}
                  note="Available to draw — not counted as cash on any runway figure"
                  status="Grey" />
      </div>

      <Card title="Every account, and whether the money in it is actually ours to spend"
            basis={w.basis} pad={false}
            right={c.flagged ? <StatusPill status="Amber" label={c.note} /> : null}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Bank / institution</TH><TH left>Purpose</TH><TH>Balance</TH>
            <TH left>Availability</TH><TH>Maturity</TH><TH left>Signatory</TH><TH>Approval limit</TH>
          </tr></thead>
          <tbody>
            {w.rows.map((r) => (
              <tr key={r.id} className={cls('tr-hover', r.availability === 'Restricted' && 'bg-grey-bg/40')}>
                <TD left className="!text-ink font-medium">
                  {r.institution}
                  <span className="block text-2xs text-ink-muted font-normal">
                    {r.account_name}{r.account_masked ? ` · ${r.account_masked}` : ''}
                  </span>
                </TD>
                <TD left>{r.purpose}</TD>
                <TD className="font-semibold !text-ink">{inr(r.balance)}</TD>
                <TD left>
                  <span className="flex items-start gap-1.5">
                    <StatusPill status={r.availability === 'Restricted' ? 'Grey' : 'Green'}
                                label={r.availability} />
                    {r.restriction_reason && <Why>{r.restriction_reason}</Why>}
                  </span>
                </TD>
                <TD>{r.maturity_date ? d(r.maturity_date) : '—'}</TD>
                <TD left className="text-ink-muted max-w-[260px] whitespace-normal">{r.signatory || '—'}</TD>
                <TD>{r.approval_limit ? inr(r.approval_limit) : '—'}</TD>
              </tr>
            ))}
          </tbody>
        </Table>

        <div className="mx-4 mb-4 mt-2 rounded-lg border border-line bg-canvas px-4 py-3">
          <p className="text-[13px] text-ink-soft">
            <span className="font-semibold">{c.note}</span>{' '}
            {c.flagged
              ? `That is above the ${c.threshold_pct}% concentration threshold — a single bank problem would be a company problem.`
              : `That is within the ${c.threshold_pct}% concentration threshold.`}
          </p>
        </div>
      </Card>
    </div>
  )
}

function TileCard({ label, value, note, status }) {
  return (
    <div className="card card-pad">
      <div className="flex items-center gap-1.5">
        <span className="label">{label}</span>
        <Dot status={status} />
      </div>
      <p className="text-[24px] font-semibold tracking-tight mt-1.5">{inr(value)}</p>
      <p className="text-2xs text-ink-muted mt-1.5 leading-relaxed">{note}</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
function HealthPane({ health, ratios, history }) {
  const { openTrace } = useApp()
  return (
    <div className="space-y-5">
      <div className="grid xl:grid-cols-[1fr_1.5fr] gap-5 items-start">
        <Card title="Liquidity health score" sub={health.delta_text} basis={health.basis}>
          <div className="flex items-end gap-4">
            <div>
              <span className={cls('text-[46px] leading-none font-semibold tracking-tight',
                health.score >= 65 ? 'text-ink' : health.score >= 45 ? 'text-amber' : 'text-red')}>
                {Math.round(health.score)}
              </span>
              <span className="text-[17px] text-ink-muted font-medium">/100</span>
            </div>
            <StatusPill className="mb-2"
              status={health.score >= 65 ? 'Green' : health.score >= 45 ? 'Amber' : 'Red'}
              label={health.band} />
          </div>

          <div className="flex gap-1 mt-4 mb-1">
            {health.bands.slice().reverse().map((b) => (
              <div key={b.name} className="flex-1">
                <div className={cls('h-1.5 rounded-full',
                  health.band === b.name ? 'bg-navy-700' : 'bg-line')} />
                <p className={cls('text-[10px] mt-1',
                  health.band === b.name ? 'text-ink font-semibold' : 'text-ink-faint')}>{b.name}</p>
              </div>
            ))}
          </div>

          <p className="label mt-5 mb-2.5">What makes up the score</p>
          <div className="space-y-3">
            {health.components.map((c) => (
              <div key={c.key}>
                <div className="flex items-baseline justify-between gap-3 mb-1">
                  <span className="text-[13px] text-ink-soft flex items-center gap-1.5">
                    {c.label}
                    {c.direction !== 'flat' && (
                      <Icon name={c.direction === 'up' ? 'arrowUp' : 'arrowDown'} size={11}
                            className={c.direction === 'up' ? 'text-green' : 'text-amber'} />
                    )}
                  </span>
                  <span className="text-[13px] font-semibold tnum shrink-0">
                    {num(c.contribution)}<span className="text-ink-faint font-normal">/{c.max}</span>
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-line-soft overflow-hidden">
                  <div className="h-full rounded-full bg-navy-500"
                       style={{ width: `${(c.contribution / c.max) * 100}%` }} />
                </div>
                <p className="text-2xs text-ink-faint mt-1">{c.explanation}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Score history" sub="With the events that moved it"
              basis={history.basis}>
          <TrendLine data={history.rows} height={210} money={false}
                     formatter={(v) => Math.round(v)}
                     keys={[{ key: 'score', label: 'Liquidity health score', colour: MARK.main }]} />
          <div className="mt-4 space-y-2 max-h-[190px] overflow-y-auto pr-1">
            {history.rows.filter((r) => r.event).reverse().map((r) => (
              <div key={r.month} className="flex items-start gap-3 text-2xs">
                <span className="shrink-0 font-semibold text-ink-soft tnum w-14">{r.label}</span>
                <span className="shrink-0 tnum text-ink-muted w-8">{Math.round(r.score)}</span>
                <span className="text-ink-muted leading-relaxed">{r.event}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <RatioTable title="Primary measures"
                  sub="Lead with these — they are about whether the business can pay its way"
                  rows={ratios.primary} basis={ratios.basis} openTrace={openTrace} />

      <RatioTable title="Lender and covenant ratios"
                  sub={ratios.lender_note}
                  rows={ratios.lender} openTrace={openTrace} />
    </div>
  )
}

function RatioTable({ title, sub, rows, basis, openTrace }) {
  return (
    <Card title={title} sub={sub} basis={basis} pad={false}>
      <Table className="px-4 pb-1">
        <thead><tr>
          <TH left>Measure</TH><TH>Value</TH><TH left>Formula, in words</TH>
          <TH left>Balances used</TH><TH left>6-month trend</TH>
          <TH left>Benchmark</TH><TH left>Status</TH>
        </tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} className="tr-hover">
              <TD left className="!text-ink font-medium">{r.label}</TD>
              <TD className={cls('font-semibold !text-[15px]',
                r.status === 'Red' ? '!text-red' : r.status === 'Amber' ? '!text-amber' : '!text-ink')}>
                {r.value === null ? '—'
                  : r.unit === 'days' ? `${Math.round(r.value)}d`
                  : r.unit === 'ratio' ? `${num(r.value, 2)}x` : num(r.value, 2)}
              </TD>
              <TD left className="text-ink-muted max-w-[300px] whitespace-normal">{r.formula}</TD>
              <TD left>
                <button onClick={() => openTrace(r.trace, r.label)}
                        className="text-2xs linkish">
                  {r.balances_used.length} balance{r.balances_used.length === 1 ? '' : 's'}
                </button>
              </TD>
              <TD left><Spark data={r.trend} status={r.status} /></TD>
              <TD left className="text-ink-muted max-w-[220px] whitespace-normal">{r.benchmark}</TD>
              <TD left><StatusPill status={r.status} /></TD>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  )
}
