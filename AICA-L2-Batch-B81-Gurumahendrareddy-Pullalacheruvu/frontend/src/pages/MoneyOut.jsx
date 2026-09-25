// TAB 5 — Money Going Out. Four sub-tabs.
import React, { useState } from 'react'
import { useApp, useEndpoint } from '../lib/store'
import { api } from '../lib/api'
import { cls, d, days, inr, num } from '../lib/format'
import {
  Card, Dot, Empty, ErrorNote, Field, Icon, Loading, Modal, StatusPill,
  Table, TD, TH, Toggle, Why,
} from '../components/ui'
import { Stat, StatRow } from '../components/Figure'

const SUBS = [
  { value: 'due', label: 'Due now' },
  { value: 'statutory', label: 'Statutory dues' },
  { value: 'commitments', label: 'Committed, not yet billed' },
  { value: 'vendors', label: 'Vendor position' },
]

export default function MoneyOut() {
  const params = new URLSearchParams(window.location.search)
  const [sub, setSub] = useState(params.get('sub') || 'due')
  const { data, loading, error, reload } = useEndpoint('/api/money-out')

  if (loading && !data) return <Loading label="Reading what has to be paid…" rows={4} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data) return null

  return (
    <div className="space-y-5">
      <Toggle options={SUBS} value={sub} onChange={setSub} size="md" />
      {sub === 'due' && <DuePane ob={data.obligations} />}
      {sub === 'statutory' && <StatutoryPane s={data.statutory} reload={reload} />}
      {sub === 'commitments' && <CommitmentsPane c={data.commitments} />}
      {sub === 'vendors' && <VendorsPane v={data.vendors} reload={reload} />}
    </div>
  )
}

// ---------------------------------------------------------------------------
function DuePane({ ob }) {
  const { openTrace } = useApp()
  const t = ob.tiles
  return (
    <div className="space-y-5">
      <Card basis={ob.basis}>
        <StatRow cols={4}>
          <Stat label="Due this week" value={inr(t.due_this_week)} size="lg" />
          <Stat label="Due next 30 days" value={inr(t.due_next_30d)} size="lg" />
          <Stat label="Of which non-deferrable" value={inr(t.non_deferrable_30d)} size="lg"
                status="Red"
                basis="Statutory dues, debt service, and vendor bills where delay costs money or stops the service." />
          <Stat label="Overdue to vendors" value={inr(t.overdue_to_vendors)} size="lg"
                status={t.overdue_to_vendors > 0 ? 'Amber' : 'Green'} />
        </StatRow>
      </Card>

      <Card title="Everything that has to leave"
            sub="Non-deferrable first, then by date — that ordering is the point of this screen"
            basis={ob.basis} pad={false}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH>Due date</TH><TH left>Item</TH><TH left>Vendor / authority</TH>
            <TH left>Category</TH><TH>Amount</TH><TH left>Deferrable?</TH>
            <TH left>Penalty on delay</TH><TH left>Approver</TH><TH left>Status</TH>
          </tr></thead>
          <tbody>
            {ob.rows.slice(0, 60).map((r) => (
              <tr key={r.id} className={cls('tr-hover cursor-pointer group',
                                            !r.deferrable && 'bg-red-bg/25')}
                  onClick={() => openTrace(r.trace, r.item)}>
                <TD className={cls('tnum', r.days_to_due < 0 ? 'text-red font-semibold' : '')}>
                  {d(r.due_date)}
                  <span className="block text-2xs text-ink-faint font-normal">
                    {r.days_to_due < 0 ? `${Math.abs(r.days_to_due)}d overdue` : `in ${r.days_to_due}d`}
                  </span>
                </TD>
                <TD left className="!text-ink font-medium max-w-[260px] whitespace-normal">
                  <span className="flex items-center gap-1.5">
                    {r.item}
                    <Icon name="chevronRight" size={12}
                          className="text-ink-faint opacity-0 group-hover:opacity-100" />
                  </span>
                </TD>
                <TD left>{r.counterparty}</TD>
                <TD left className="text-ink-muted">{r.category}</TD>
                <TD className="font-semibold !text-ink">{inr(r.amount)}</TD>
                <TD left>
                  {r.deferrable
                    ? <span className="text-2xs text-ink-muted">
                        Yes{r.deferral_cost ? ` · costs ${inr(r.deferral_cost)}` : ''}
                      </span>
                    : <StatusPill status="Red" label="No" />}
                </TD>
                <TD left className="text-ink-muted max-w-[240px] whitespace-normal text-2xs">{r.penalty}</TD>
                <TD left>{r.approver || '—'}</TD>
                <TD left><span className="text-2xs text-ink-muted capitalize">{r.status}</span></TD>
              </tr>
            ))}
          </tbody>
        </Table>
        {ob.rows.length > 60 && (
          <p className="basis px-4 pb-4">Showing the first 60 of {ob.rows.length} open items.</p>
        )}
      </Card>
    </div>
  )
}

// ---------------------------------------------------------------------------
function StatutoryPane({ s, reload }) {
  const { canWrite, notify } = useApp()
  const [earmark, setEarmark] = useState(null)
  const c = s.cover

  return (
    <div className="space-y-5">
      <div className={cls('card card-pad border-l-4',
        c.status === 'Red' ? '!border-l-red' : '!border-l-green')}>
        <div className="flex items-start gap-3">
          <Icon name={c.status === 'Red' ? 'alert' : 'check'} size={18}
                className={cls('mt-0.5 shrink-0', c.status === 'Red' ? 'text-red' : 'text-green')} />
          <div className="min-w-0 flex-1">
            <p className={cls('text-[15px] font-semibold',
                              c.status === 'Red' ? 'text-red' : 'text-ink')}>
              {c.sentence}
            </p>
            <p className="text-2xs text-ink-muted mt-1.5">
              Statutory dues are first charge, carry penal interest, and are never negotiable.
              Cover of {num(c.ratio, 2)}x — anything below 1.00x is a funding gap.
            </p>
          </div>
          <div className="shrink-0 text-right">
            <span className="label block">Cover</span>
            <span className={cls('text-[24px] font-semibold tnum',
                                 c.ratio >= 1 ? 'text-green' : 'text-red')}>{num(c.ratio, 2)}x</span>
          </div>
        </div>
      </div>

      <Card title="Falling due" basis={s.basis} pad={false}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Head</TH><TH left>Period</TH><TH>Due date</TH><TH>Amount</TH>
            <TH>Earmarked</TH><TH>Gap</TH><TH>Days to due</TH><TH left>Status</TH>
            {canWrite && <TH left />}
          </tr></thead>
          <tbody>
            {s.rows.filter((r) => r.amount > 0).map((r) => (
              <tr key={r.id} className={cls('tr-hover', r.gap > 0 && 'bg-red-bg/25')}>
                <TD left className="!text-ink font-semibold">{r.head}</TD>
                <TD left>{r.period}</TD>
                <TD>{d(r.due_date)}</TD>
                <TD className="font-semibold !text-ink">{inr(r.amount)}</TD>
                <TD>{inr(r.earmarked)}</TD>
                <TD className={r.gap > 0 ? 'text-red font-semibold' : ''}>
                  {r.gap > 0 ? inr(r.gap) : '—'}
                </TD>
                <TD className={r.days_to_due < 0 ? 'text-red font-semibold' : ''}>
                  {r.days_to_due < 0 ? `${Math.abs(r.days_to_due)}d late` : r.days_to_due}
                </TD>
                <TD left>
                  <span className="flex items-center gap-1.5">
                    <StatusPill status={r.severity} label={r.funded ? 'Funded' : 'Not funded'} />
                    {r.notes && <Why>{r.notes}</Why>}
                  </span>
                </TD>
                {canWrite && (
                  <TD left>
                    <button className="text-2xs linkish" onClick={() => setEarmark(r)}>Earmark</button>
                  </TD>
                )}
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card title="Payment history, 12 months"
            sub={s.history_summary.note} pad={false}
            right={s.history_summary.penalty_paid > 0
              ? <StatusPill status="Amber" label={`${inr(s.history_summary.penalty_paid)} in penalties`} />
              : <StatusPill status="Green" label="No penalties paid" />}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Head</TH><TH left>Period</TH><TH>Due</TH><TH>Paid</TH>
            <TH>Amount</TH><TH>Days late</TH><TH>Interest / penalty</TH>
          </tr></thead>
          <tbody>
            {s.history.slice(0, 24).map((r) => (
              <tr key={r.id} className="tr-hover">
                <TD left className="!text-ink font-medium">{r.head}</TD>
                <TD left>{r.period}</TD>
                <TD>{d(r.due_date)}</TD>
                <TD>{d(r.paid_on)}</TD>
                <TD>{inr(r.amount)}</TD>
                <TD className={r.days_late > 0 ? 'text-amber font-semibold' : ''}>
                  {r.days_late || '—'}
                </TD>
                <TD className={r.interest_penalty_paid > 0 ? 'text-amber font-semibold' : ''}>
                  {r.interest_penalty_paid > 0 ? inr(r.interest_penalty_paid) : '—'}
                </TD>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <EarmarkModal row={earmark} onClose={() => setEarmark(null)}
                    onDone={() => { setEarmark(null); reload(); notify('Cash earmarked.') }} />
    </div>
  )
}

function EarmarkModal({ row, onClose, onDone }) {
  const [amount, setAmount] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  React.useEffect(() => { if (row) setAmount(String(row.amount)) }, [row])
  if (!row) return null

  async function save() {
    setBusy(true); setErr(null)
    try {
      await api.patch(`/api/statutory/${row.id}`, { earmarked_amount: Number(amount) })
      onDone()
    } catch (e) { setErr(e.message); setBusy(false) }
  }

  return (
    <Modal open onClose={onClose}
           title={`Earmark cash for ${row.head} — ${row.period}`}
           sub={`${inr(row.amount)} falls due on ${d(row.due_date)}.`}
           footer={<>
             <button className="btn-ghost" onClick={onClose}>Cancel</button>
             <button className="btn-primary" disabled={busy} onClick={save}>
               {busy ? 'Saving…' : 'Earmark'}
             </button>
           </>}>
      <Field label="Amount earmarked"
             hint="Earmarking records that this cash is committed. It does not move any money.">
        <input type="number" className="input tnum" value={amount}
               onChange={(e) => setAmount(e.target.value)} />
      </Field>
      <div className="mt-4 rounded-lg bg-canvas border border-line px-3.5 py-3">
        <div className="flex justify-between text-[13px]">
          <span className="text-ink-soft">Gap after this change</span>
          <span className={cls('font-semibold tnum',
            row.amount - Number(amount || 0) > 0 ? 'text-red' : 'text-green')}>
            {inr(Math.max(row.amount - Number(amount || 0), 0))}
          </span>
        </div>
      </div>
      {err && <p className="text-[13px] text-red mt-3">{err}</p>}
    </Modal>
  )
}

// ---------------------------------------------------------------------------
function CommitmentsPane({ c }) {
  const s = c.summary
  return (
    <div className="space-y-5">
      <Card basis={c.basis}>
        <p className="text-[15px] font-semibold text-ink mb-4">{s.sentence}</p>
        <StatRow cols={4}>
          <Stat label="Remaining commitment" value={inr(s.remaining)} size="lg" />
          <Stat label="Non-cancellable" value={inr(s.non_cancellable)} size="lg" status="Red" />
          <Stat label="Cancellable" value={inr(s.cancellable)} size="lg"
                sub={`Exit cost ${inr(s.total_exit_cost)}`} />
          <Stat label="Monthly run-rate" value={inr(s.monthly_runrate)} size="lg" />
        </StatRow>
      </Card>

      <Card title="Committed but not yet billed"
            sub="Money already promised that no invoice has arrived for — the most commonly missed number in any cash tool"
            pad={false}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Type</TH><TH left>Counterparty</TH><TH>Total value</TH>
            <TH>Consumed</TH><TH>Remaining</TH><TH left>Cancellable?</TH>
            <TH>Notice</TH><TH>Exit cost</TH><TH>Ends</TH><TH left>Owner</TH>
          </tr></thead>
          <tbody>
            {c.rows.map((r) => (
              <tr key={r.id} className={cls('tr-hover', !r.cancellable && 'bg-red-bg/20')}>
                <TD left className="!text-ink font-medium">{r.commitment_type}</TD>
                <TD left>
                  {r.counterparty}
                  {r.description && <span className="block text-2xs text-ink-muted">{r.description}</span>}
                </TD>
                <TD>{inr(r.total_value)}</TD>
                <TD>{inr(r.consumed)}</TD>
                <TD className="font-semibold !text-ink">{inr(r.remaining)}</TD>
                <TD left>
                  {r.cancellable
                    ? <span className="text-2xs text-ink-muted">Yes</span>
                    : <StatusPill status="Red" label="No" />}
                </TD>
                <TD>{r.notice_period_days ? `${r.notice_period_days}d` : '—'}</TD>
                <TD>{r.exit_cost ? inr(r.exit_cost) : '—'}</TD>
                <TD>{d(r.ends_on)}</TD>
                <TD left>{r.owner || '—'}</TD>
              </tr>
            ))}
            {!c.rows.length && <tr><TD left colSpan={10}><Empty>No commitments recorded.</Empty></TD></tr>}
          </tbody>
        </Table>
      </Card>
    </div>
  )
}

// ---------------------------------------------------------------------------
function VendorsPane({ v, reload }) {
  const { canWrite, notify } = useApp()
  return (
    <div className="space-y-5">
      <Card basis={v.basis}>
        <StatRow cols={3}>
          <Stat label="Total payable" value={inr(v.total_payable)} size="lg" />
          <Stat label="Overdue" value={inr(v.total_overdue)} size="lg"
                status={v.total_overdue > 0 ? 'Amber' : 'Green'} />
          <Stat label="Vendors with an open balance" value={v.rows.length} size="lg" />
        </StatRow>
      </Card>

      <Card title="Top 10 vendors by exposure"
            sub="Criticality decides who can safely be stretched and who cannot" pad={false}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Vendor</TH><TH>Payable</TH><TH>Overdue</TH><TH>Open bills</TH>
            <TH>Days we take</TH><TH>Terms agreed</TH><TH left>Criticality</TH><TH left>On hold?</TH>
          </tr></thead>
          <tbody>
            {v.top10.map((r) => (
              <tr key={r.vendor_id} className="tr-hover">
                <TD left className="!text-ink font-medium">{r.vendor}</TD>
                <TD className="font-semibold !text-ink">{inr(r.payable)}</TD>
                <TD className={r.overdue > 0 ? 'text-amber font-medium' : ''}>
                  {r.overdue > 0 ? inr(r.overdue) : '—'}
                </TD>
                <TD>{r.open_bills}</TD>
                <TD className={r.avg_days_we_take > r.credit_terms_days ? 'text-amber' : ''}>
                  {r.avg_days_we_take ? `${r.avg_days_we_take}d` : '—'}
                </TD>
                <TD>{r.credit_terms_days ? `${r.credit_terms_days}d` : '—'}</TD>
                <TD left>
                  <StatusPill status={r.criticality === 'High' ? 'Red'
                                    : r.criticality === 'Medium' ? 'Amber' : 'Grey'}
                              label={r.criticality} />
                </TD>
                <TD left>{r.on_hold ? <StatusPill status="Amber" label="On hold" /> : '—'}</TD>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  )
}
