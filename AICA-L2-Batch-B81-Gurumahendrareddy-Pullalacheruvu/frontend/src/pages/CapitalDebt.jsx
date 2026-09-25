// TAB 9 — Capital & Debt. Amber before breach, not after.
import React from 'react'
import { useEndpoint } from '../lib/store'
import { MARK, cls, d, inr, num, pct } from '../lib/format'
import {
  Card, Dot, Empty, ErrorNote, Icon, Loading, StatusPill, Table, TD, TH, Why,
} from '../components/ui'
import { Stat, StatRow } from '../components/Figure'
import { ColumnChart, TrendLine } from '../components/charts'

export default function CapitalDebt() {
  const { data, loading, error, reload } = useEndpoint('/api/capital-debt')

  if (loading && !data) return <Loading label="Reading facilities and covenants…" rows={4} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data) return null

  const f = data.facilities
  const cov = data.covenants
  const nr = data.next_raise

  return (
    <div className="space-y-5">
      {/* ---- Next raise — the thing with a deadline ------------------- */}
      {nr.exists && (
        <div className={cls('card card-pad border-l-4',
          nr.trigger_passed ? '!border-l-red' : nr.days_until_trigger < 45 ? '!border-l-amber' : '!border-l-green')}>
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div className="flex items-start gap-3 min-w-0">
              <Icon name={nr.trigger_passed ? 'alert' : 'clock'} size={18}
                    className={cls('mt-0.5 shrink-0', nr.trigger_passed ? 'text-red' : 'text-ink-muted')} />
              <div className="min-w-0">
                <p className={cls('text-[15px] font-semibold', nr.trigger_passed ? 'text-red' : 'text-ink')}>
                  {nr.sentence}
                </p>
                <p className="text-2xs text-ink-muted mt-1.5 max-w-2xl leading-relaxed">{nr.notes}</p>
                <p className="basis mt-1.5">{nr.basis}</p>
              </div>
            </div>
            <div className="flex gap-8 shrink-0">
              <div><span className="label block">Target</span>
                   <span className="text-[19px] font-semibold tnum">{inr(nr.target_amount)}</span>
                   <span className="block text-2xs text-ink-muted">{nr.instrument}</span></div>
              <div><span className="label block">Target close</span>
                   <span className="text-[19px] font-semibold tnum">{d(nr.target_close_date)}</span>
                   <span className="block text-2xs text-ink-muted">Trigger {d(nr.trigger_date)}</span></div>
              <div><span className="label block">Runway at close</span>
                   <span className={cls('text-[19px] font-semibold tnum',
                     nr.runway_at_close_status === 'Red' ? 'text-red'
                       : nr.runway_at_close_status === 'Amber' ? 'text-amber' : 'text-ink')}>
                     {num(nr.runway_at_close_months)} mo</span>
                   <span className="block text-2xs text-ink-muted">{nr.status}</span></div>
            </div>
          </div>
        </div>
      )}

      {/* ---- Covenants ------------------------------------------------ */}
      <Card title="Covenants"
            sub="Amber appears while headroom is still positive — a breach is seen before it happens"
            basis={cov.basis} pad={false}
            right={cov.any_breach ? <StatusPill status="Red" label="Breach" />
                 : cov.any_amber ? <StatusPill status="Amber" label="Headroom thin" />
                 : <StatusPill status="Green" label="All clear" />}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Covenant</TH><TH>Required</TH><TH>Current</TH><TH>Headroom</TH>
            <TH>Warning at</TH><TH>Test date</TH><TH left>Frequency</TH><TH left>Status</TH>
          </tr></thead>
          <tbody>
            {cov.rows.map((r) => (
              <tr key={r.id} className={cls('tr-hover',
                r.status === 'Red' ? 'bg-red-bg/30' : r.status === 'Amber' && 'bg-amber-bg/30')}>
                <TD left className="!text-ink font-medium">
                  <span className="flex items-center gap-1.5">
                    {r.name}
                    {r.notes && <Why>{r.notes}</Why>}
                  </span>
                </TD>
                <TD>{r.operator} {r.required_display}</TD>
                <TD className="font-semibold !text-ink">{r.current_display}</TD>
                <TD className={cls('font-semibold',
                  r.status === 'Red' ? '!text-red' : r.status === 'Amber' ? '!text-amber' : '')}>
                  {r.headroom_pct !== null ? pct(r.headroom_pct) : '—'}
                </TD>
                <TD className="text-ink-muted">{pct(r.amber_buffer_pct, { decimals: 0 })}</TD>
                <TD>
                  {d(r.test_date)}
                  {r.days_to_test !== null && (
                    <span className="block text-2xs text-ink-faint">
                      {r.days_to_test < 0 ? 'passed' : `in ${r.days_to_test}d`}
                    </span>
                  )}
                </TD>
                <TD left>{r.test_frequency}</TD>
                <TD left><StatusPill status={r.status} /></TD>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      {/* ---- Facilities ----------------------------------------------- */}
      <Card title="Facilities" basis={f.basis} pad={false}
            right={
              <div className="flex gap-6">
                <Stat label="Sanctioned" value={inr(f.totals.sanctioned)} size="sm" align="right" />
                <Stat label="Drawn" value={inr(f.totals.drawn)} size="sm" align="right" />
                <Stat label="Available to draw" value={inr(f.totals.available_to_draw)} size="sm" align="right" />
              </div>}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Lender</TH><TH left>Type</TH><TH>Sanctioned</TH><TH>Drawn</TH>
            <TH>Available</TH><TH>Rate</TH><TH>Tenure</TH><TH>Next repayment</TH>
            <TH left>Security given</TH>
          </tr></thead>
          <tbody>
            {f.rows.map((r) => (
              <tr key={r.id} className={cls('tr-hover', !r.is_active && 'opacity-50')}>
                <TD left className="!text-ink font-medium">{r.lender}</TD>
                <TD left>{r.facility_type}</TD>
                <TD>{inr(r.sanctioned)}</TD>
                <TD>{inr(r.drawn)}</TD>
                <TD className={r.available_to_draw > 0 ? 'font-semibold !text-ink' : ''}>
                  {inr(r.available_to_draw)}
                </TD>
                <TD>{num(r.interest_rate)}%</TD>
                <TD>{r.tenure_months ? `${r.tenure_months} mo` : '—'}</TD>
                <TD>
                  {r.next_repayment_date ? (
                    <>
                      {inr(r.next_repayment_amount)}
                      <span className="block text-2xs text-ink-faint">{d(r.next_repayment_date)}</span>
                    </>
                  ) : '—'}
                </TD>
                <TD left className="text-ink-muted max-w-[300px] whitespace-normal text-2xs">
                  {r.security_given || '—'}
                </TD>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      {/* ---- Repayment calendar --------------------------------------- */}
      <Card title="Repayment calendar, next 12 months"
            sub={`${inr(data.repayment_calendar.total_12m)} of principal and interest falls due`}
            basis={data.repayment_calendar.basis}>
        <ColumnChart data={data.repayment_calendar.rows} height={230} stacked keys={[
          { key: 'principal', label: 'Principal', colour: MARK.main },
          { key: 'interest', label: 'Interest', colour: MARK.light },
        ]} />
      </Card>

      {/* ---- Funding history ------------------------------------------ */}
      <Card title="Funding history"
            sub={`${inr(data.funding_history.total_raised)} raised to date`}
            basis={data.funding_history.basis} pad={false}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Round</TH><TH>Closed</TH><TH>Amount</TH><TH left>Instrument</TH>
            <TH left>Investor</TH><TH>Post-money</TH><TH>Cash remaining</TH><TH>Deployed</TH>
          </tr></thead>
          <tbody>
            {data.funding_history.rows.map((r) => (
              <tr key={r.id} className="tr-hover">
                <TD left className="!text-ink font-semibold">{r.round_name}</TD>
                <TD>{d(r.closed_on)}</TD>
                <TD className="font-semibold !text-ink">{inr(r.amount)}</TD>
                <TD left>{r.instrument}</TD>
                <TD left className="text-ink-muted max-w-[300px] whitespace-normal">{r.investor || '—'}</TD>
                <TD>{r.post_money_valuation ? inr(r.post_money_valuation) : '—'}</TD>
                <TD>{inr(r.cash_remaining)}</TD>
                <TD>
                  <span className="flex items-center justify-end gap-2">
                    <span className="w-14 h-1.5 rounded-full bg-line-soft overflow-hidden">
                      <span className="block h-full rounded-full bg-navy-500"
                            style={{ width: `${Math.min(r.deployed_pct, 100)}%` }} />
                    </span>
                    {pct(r.deployed_pct, { decimals: 0 })}
                  </span>
                </TD>
              </tr>
            ))}
            {!data.funding_history.rows.length && (
              <tr><TD left colSpan={8}><Empty>No funding rounds recorded.</Empty></TD></tr>
            )}
          </tbody>
        </Table>
      </Card>
    </div>
  )
}
