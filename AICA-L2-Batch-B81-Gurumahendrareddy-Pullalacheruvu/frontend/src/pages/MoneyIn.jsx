// TAB 4 — Money Coming In.
import React, { useState } from 'react'
import { useApp, useEndpoint } from '../lib/store'
import { api } from '../lib/api'
import { MARK, cls, d, days, inr, num, pct } from '../lib/format'
import {
  Card, Dot, Empty, ErrorNote, Field, Icon, Loading, Modal, StatusPill,
  Table, TD, TH,
} from '../components/ui'
import { Stat, StatRow } from '../components/Figure'
import { AgeingBar, ColumnChart } from '../components/charts'

export default function MoneyIn() {
  const { data, loading, error, reload } = useEndpoint('/api/money-in')
  const { openTrace, canWrite, notify } = useApp()
  const [editing, setEditing] = useState(null)

  if (loading && !data) return <Loading label="Reading the receivables book…" rows={4} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data) return null

  const s = data.summary
  const c = data.concentration

  return (
    <div className="space-y-5">
      {/* ---- Tiles --------------------------------------------------- */}
      <Card basis={s.basis}>
        <StatRow cols={5}>
          <Stat label="Total receivable" value={inr(s.total_receivable)} size="lg" />
          <Stat label="Overdue" value={inr(s.overdue)} size="lg"
                sub={`${s.overdue_pct}% of the book`}
                status={s.overdue_pct > 30 ? 'Red' : s.overdue_pct > 15 ? 'Amber' : 'Green'} />
          <Stat label="Weighted collectible, 30 days" value={inr(s.weighted_next_30d)} size="lg"
                basis="Each invoice discounted by how likely it is to actually arrive, based on that client's payment history." />
          <Stat label="DSO" value={s.dso ? days(s.dso) : '—'} size="lg"
                sub={s.dso_trend !== null && s.dso_trend !== undefined
                  ? `${s.dso_trend > 0 ? '+' : ''}${s.dso_trend}d vs 3 months ago` : null}
                status={s.dso > 75 ? 'Amber' : 'Green'} />
          <Stat label="Collected this month" value={inr(s.collected_this_month)} size="lg"
                sub={s.vs_target_pct ? `${s.vs_target_pct}% of target` : null} />
        </StatRow>
      </Card>

      {/* ---- Ageing -------------------------------------------------- */}
      <Card title="Ageing" sub="Disputed invoices sit in their own bucket and never in the others"
            basis={data.ageing.basis}>
        <AgeingBar buckets={data.ageing.buckets}
                   onSelect={(b) => openTrace(b.trace, `${b.bucket} — open invoices`)} />
      </Card>

      {/* ---- By client ----------------------------------------------- */}
      <Card title="By client"
            sub="'Average days taken to pay' is what they actually do, not what they agreed to"
            basis={data.by_client.basis} pad={false}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Client</TH><TH>Outstanding</TH><TH>Overdue</TH><TH>Oldest</TH>
            <TH left>How they actually pay</TH><TH>Weighted, 30 days</TH><TH>% of AR</TH>
            <TH>Last contact</TH><TH left>Owner</TH>
          </tr></thead>
          <tbody>
            {data.by_client.rows.map((r) => (
              <tr key={r.customer_id} className="tr-hover cursor-pointer group"
                  onClick={() => openTrace(r.trace, r.client)}>
                <TD left className="!text-ink font-medium">
                  <span className="flex items-center gap-1.5">
                    {r.client}
                    {r.pct_of_ar > c.threshold_pct && <Dot status="Amber" title="Above the concentration threshold" />}
                    <Icon name="chevronRight" size={12}
                          className="text-ink-faint opacity-0 group-hover:opacity-100" />
                  </span>
                </TD>
                <TD className="font-semibold !text-ink">{inr(r.total_outstanding)}</TD>
                <TD className={r.overdue > 0 ? 'text-amber font-medium' : ''}>
                  {r.overdue > 0 ? inr(r.overdue) : '—'}
                </TD>
                <TD>{r.oldest_days > 0 ? days(r.oldest_days) : '—'}</TD>
                <TD left className="text-ink-muted max-w-[240px] whitespace-normal">{r.behaviour_note}</TD>
                <TD>{inr(r.weighted_30d)}</TD>
                <TD>{r.pct_of_ar}%</TD>
                <TD>{d(r.last_contact)}</TD>
                <TD left>{r.owner || '—'}</TD>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      {/* ---- Concentration ------------------------------------------- */}
      <div className="grid xl:grid-cols-2 gap-5 items-start">
        <Card title="Concentration"
              sub={`Flagged above ${c.threshold_pct}% of receivables`}
              basis={c.basis}>
          <div className="grid grid-cols-2 gap-6">
            <ShareList title="Share of receivables" rows={c.top5_receivables}
                       threshold={c.threshold_pct} />
            <ShareList title="Share of revenue, 12 months" rows={c.top5_revenue} />
          </div>
          {c.impact && (
            <div className={cls('mt-5 rounded-lg border px-4 py-3',
              c.breached ? 'border-amber-line bg-amber-bg' : 'border-line bg-canvas')}>
              <p className={cls('text-[13px] font-medium', c.breached ? 'text-amber' : 'text-ink-soft')}>
                {c.impact.sentence}
              </p>
              <p className="text-2xs text-ink-muted mt-1">
                Runway {num(c.impact.months_before)} months → {num(c.impact.months_after)} months
                under that single assumption.
              </p>
            </div>
          )}
        </Card>

        <Card title="Collection performance"
              sub={data.collection_performance.note}
              basis={data.collection_performance.basis}>
          <ColumnChart data={data.collection_performance.rows} height={230} keys={[
            { key: 'promised', label: 'Promised', colour: MARK.light },
            { key: 'received', label: 'Actually received', colour: MARK.main },
          ]} />
        </Card>
      </div>

      {/* ---- Disputes + invoicing gap -------------------------------- */}
      <div className="space-y-5">
        <Card title="Disputed and withheld"
              sub={`${inr(data.disputes.total)} held up in dispute`}
              basis={data.disputes.basis} pad={false}>
          {data.disputes.rows.length === 0 ? <Empty>No invoices are in dispute.</Empty> : (
            <Table className="px-4 pb-1">
              <thead><tr>
                <TH left>Client</TH><TH left>Invoice</TH><TH>Amount</TH><TH left>Reason</TH>
                <TH>Raised</TH><TH>Open</TH><TH left>Owner</TH><TH>Expected</TH>
              </tr></thead>
              <tbody>
                {data.disputes.rows.map((r) => (
                  <tr key={r.id} className="tr-hover">
                    <TD left className="!text-ink font-medium">{r.client}</TD>
                    <TD left>{r.invoice_no}</TD>
                    <TD className="font-semibold !text-ink">{inr(r.amount)}</TD>
                    <TD left className="text-ink-muted max-w-[300px] whitespace-normal">{r.reason}</TD>
                    <TD>{d(r.raised_on)}</TD>
                    <TD className={r.days_open > 60 ? 'text-amber font-medium' : ''}>
                      {days(r.days_open)}
                    </TD>
                    <TD left>{r.owner || '—'}</TD>
                    <TD>{d(r.expected_resolution)}</TD>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        <Card title="Invoicing gap"
              sub={data.invoicing_gap.note}
              basis={data.invoicing_gap.basis} pad={false}>
          {data.invoicing_gap.rows.length === 0 ? (
            <Empty>Everything delivered has been invoiced.</Empty>
          ) : (
            <Table className="px-4 pb-1">
              <thead><tr>
                <TH left>Client</TH><TH left>Work</TH><TH>Amount</TH><TH>Delivered</TH>
                <TH>Days</TH><TH left>What's holding it</TH><TH left>Owner</TH>
              </tr></thead>
              <tbody>
                {data.invoicing_gap.rows.map((r) => (
                  <tr key={r.id} className="tr-hover">
                    <TD left className="!text-ink font-medium">{r.client}</TD>
                    <TD left className="max-w-[240px] whitespace-normal">{r.description}</TD>
                    <TD className="font-semibold !text-ink">{inr(r.amount)}</TD>
                    <TD>{d(r.delivered_on)}</TD>
                    <TD className={r.days_elapsed > 30 ? 'text-amber font-medium' : ''}>
                      {r.days_elapsed}
                    </TD>
                    <TD left className="text-ink-muted max-w-[240px] whitespace-normal">{r.blocker || '—'}</TD>
                    <TD left>{r.owner || '—'}</TD>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      </div>
    </div>
  )
}

function ShareList({ title, rows, threshold }) {
  const max = Math.max(...rows.map((r) => r.pct), 1)
  return (
    <div>
      <p className="label mb-3">{title}</p>
      <div className="space-y-2.5">
        {rows.map((r) => {
          const over = threshold && r.pct > threshold
          return (
            <div key={r.client}>
              <div className="flex items-baseline justify-between gap-2 mb-1">
                <span className="text-[13px] text-ink-soft truncate">{r.client}</span>
                <span className={cls('text-[13px] font-semibold tnum shrink-0',
                                     over ? 'text-amber' : 'text-ink')}>{r.pct}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-line-soft overflow-hidden">
                <div className="h-full rounded-full"
                     style={{ width: `${(r.pct / max) * 100}%`,
                              background: over ? '#a87c00' : MARK.main }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
