// TAB 2 — Runway & Burn. Three sub-tabs: Runway, Burn Anatomy, People Cost.
import React, { useState } from 'react'
import { useApp, useEndpoint } from '../lib/store'
import { api } from '../lib/api'
import { MARK, cls, d, inr, mon, num, pct, st } from '../lib/format'
import {
  Card, Dot, Empty, ErrorNote, Icon, Loading, Modal, Section, StatusPill,
  Table, TD, TH, Toggle,
} from '../components/ui'
import { Delta, Stat, StatRow } from '../components/Figure'
import { ColumnChart, TrendLine, Waterfall } from '../components/charts'

const SUBS = [
  { value: 'runway', label: 'Runway' },
  { value: 'burn', label: 'Burn anatomy' },
  { value: 'people', label: 'People cost' },
]

export default function RunwayBurn() {
  const [sub, setSub] = useState('runway')
  const { data, loading, error, reload } = useEndpoint('/api/runway-burn')

  if (loading && !data) return <Loading label="Working out burn and runway…" rows={4} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data) return null

  return (
    <div className="space-y-5">
      <Toggle options={SUBS} value={sub} onChange={setSub} size="md" />
      {sub === 'runway' && <RunwayPane runway={data.runway} />}
      {sub === 'burn' && <BurnPane burn={data.burn} reload={reload} />}
      {sub === 'people' && <PeoplePane people={data.people} />}
    </div>
  )
}

// ---------------------------------------------------------------------------
function RunwayPane({ runway }) {
  const { openTrace } = useApp()
  const s = runway.summary
  const m = runway.movement
  const ms = runway.milestones

  return (
    <div className="space-y-5">
      <Card title="Runway under each assumption"
            sub="The same cash, four different views of how long it lasts"
            basis={s.basis} pad={false}
            right={<Stat label="Cash available" value={inr(s.cash_available)} size="sm"
                         align="right" className="!w-auto" />}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Scenario</TH>
            <TH>Monthly burn assumed</TH>
            <TH>Months left</TH>
            <TH>Cash-out date</TH>
            <TH left>What this assumes</TH>
          </tr></thead>
          <tbody>
            {s.rows.map((r) => (
              <tr key={r.key} className={cls('tr-hover', r.key === 'current' && 'bg-navy-50/50')}>
                <TD left className="!text-ink font-semibold">
                  {r.scenario}
                  {r.key === 'current' && <span className="ml-2 chip bg-navy-100 border-navy-200 text-navy-700">Headline</span>}
                </TD>
                <TD>{inr(r.monthly_burn)}</TD>
                <TD className={cls('font-semibold', r.months < 6 ? 'text-red' : r.months < 12 ? 'text-amber' : '')}>
                  {num(r.months)}
                </TD>
                <TD>{d(r.cashout_date)}</TD>
                <TD left className="text-ink-muted max-w-[420px] whitespace-normal">{r.assumes}</TD>
              </tr>
            ))}
          </tbody>
        </Table>

        <div className={cls('mx-4 mb-4 mt-2 rounded-lg border px-4 py-3 flex items-start gap-3',
          s.fundraise_trigger_passed ? 'border-red-line bg-red-bg' : 'border-line bg-canvas')}>
          <Icon name={s.fundraise_trigger_passed ? 'alert' : 'clock'} size={16}
                className={cls('mt-0.5', s.fundraise_trigger_passed ? 'text-red' : 'text-ink-muted')} />
          <div>
            <p className={cls('text-[13px] font-semibold',
                              s.fundraise_trigger_passed ? 'text-red' : 'text-ink')}>
              Fundraise trigger date: {d(s.fundraise_trigger_date)}
              {s.fundraise_trigger_passed && ' — already passed'}
            </p>
            <p className="text-2xs text-ink-muted mt-0.5">
              Cash-out date less {s.fundraise_lead_months} months of lead time to close a round.
            </p>
          </div>
        </div>
      </Card>

      <div className="grid xl:grid-cols-[1.3fr_1fr] gap-5 items-start">
        <Card title="Why runway moved"
              sub={m.narrative || 'Not enough history yet'}
              basis={m.basis}>
          {m.bars?.length ? (
            <Waterfall bars={m.bars} money={false} unit=" mo" height={260} />
          ) : <Empty>Two months of history are needed before this chart says anything.</Empty>}
        </Card>

        <Card title="Runway to the milestone that matters"
              basis="Cash-out date against the target close of the next round.">
          {ms.to_zero_months ? (
            <>
              <div className="space-y-4">
                <MilestoneBar label="Runway to zero" months={ms.to_zero_months}
                              max={Math.max(ms.to_zero_months, ms.to_milestone_months) * 1.15}
                              caption={d(ms.cashout_date)} status={ms.covered ? 'Green' : 'Red'} />
                <MilestoneBar label={`Runway to ${ms.milestone_name}`} months={ms.to_milestone_months}
                              max={Math.max(ms.to_zero_months, ms.to_milestone_months) * 1.15}
                              caption={d(ms.milestone_date)} status="Grey" />
              </div>
              <div className={cls('mt-4 rounded-lg border px-4 py-3',
                ms.covered ? 'border-green-line bg-green-bg' : 'border-red-line bg-red-bg')}>
                <p className={cls('text-[13px] font-medium', ms.covered ? 'text-green' : 'text-red')}>
                  {ms.note}
                </p>
              </div>
              {ms.trigger_date && (
                <p className="basis mt-3">
                  Trigger to start raising: {d(ms.trigger_date)}
                  {ms.days_until_trigger !== null && (
                    ms.trigger_passed
                      ? ` — ${Math.abs(ms.days_until_trigger)} days ago.`
                      : ` — ${ms.days_until_trigger} days away.`)}
                </p>
              )}
            </>
          ) : <Empty>No funding milestone recorded. Add one in Capital &amp; Debt.</Empty>}
        </Card>
      </div>
    </div>
  )
}

function MilestoneBar({ label, months, max, caption, status }) {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="text-[13px] text-ink-soft">{label}</span>
        <span className="text-[15px] font-semibold tnum">{num(months)} mo</span>
      </div>
      <div className="h-2.5 rounded-full bg-line-soft overflow-hidden">
        <div className="h-full rounded-full" style={{
          width: `${Math.min((months / max) * 100, 100)}%`,
          background: status === 'Grey' ? MARK.light : st(status).hex,
        }} />
      </div>
      <p className="text-2xs text-ink-faint mt-1">{caption}</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
function BurnPane({ burn, reload }) {
  const { openTrace, canWrite, notify } = useApp()
  const [reclass, setReclass] = useState(null)
  const s = burn.summary
  const oneOff = burn.recurring_vs_one_off
  const cats = burn.by_category

  const windows = [
    ['This month', s.this_month], ['3-month average', s.avg_3m],
    ['6-month average', s.avg_6m], [s.same_month_last_year.label, s.same_month_last_year],
  ]

  return (
    <div className="space-y-5">
      <Card title="Burn summary" sub="Gross out, cash in, and what the month actually cost"
            basis={s.basis} pad={false}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Period</TH><TH>Gross burn</TH><TH>Collections</TH><TH>Net burn</TH>
          </tr></thead>
          <tbody>
            {windows.map(([label, w]) => (
              <tr key={label} className="tr-hover">
                <TD left className="!text-ink font-medium">{w.label || label}</TD>
                <TD>{inr(w.gross_burn)}</TD>
                <TD>{inr(w.collections)}</TD>
                <TD className="!text-ink font-semibold">{inr(w.net_burn)}</TD>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <div className="grid xl:grid-cols-2 gap-5 items-start">
        <Card title="Gross burn and collections, 18 months"
              sub="Normalised — one-off items excluded">
          <TrendLine data={burn.monthly_normalised} height={230} keys={[
            { key: 'gross_burn', label: 'Gross burn', colour: MARK.main },
            { key: 'collections', label: 'Collections', colour: MARK.light },
            { key: 'net_burn', label: 'Net burn', colour: MARK.deep, dashed: true },
          ]} />
        </Card>

        <Card title="Recurring vs one-off"
              sub={`Last ${oneOff.window_months} months`} basis={oneOff.basis}>
          <StatRow cols={3}>
            <Stat label="Total burn" value={inr(oneOff.total_burn)} />
            <Stat label="Recurring" value={inr(oneOff.recurring)} sub="What a normal month costs" />
            <Stat label="One-off" value={inr(oneOff.one_off)} sub={`${oneOff.one_off_pct}% of the total`} />
          </StatRow>

          <p className="label mt-5 mb-2">One-off items excluded</p>
          <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-1">
            {oneOff.excluded_items.map((it) => (
              <div key={it.id}
                   className={cls('rounded-lg border px-3 py-2 flex items-start justify-between gap-3',
                                  it.in_current_window ? 'border-line bg-white' : 'border-line-soft bg-canvas')}>
                <div className="min-w-0">
                  <p className="text-[13px] text-ink truncate">{it.narration}</p>
                  <p className="text-2xs text-ink-muted mt-0.5">
                    {it.month} · {it.party} · classified by {it.classified_by}
                    {!it.in_current_window && ' · outside the window'}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-[13px] font-semibold tnum">{inr(Math.abs(it.amount))}</p>
                  {canWrite && (
                    <button onClick={() => setReclass(it)}
                            className="text-2xs linkish mt-0.5">Reclassify</button>
                  )}
                </div>
              </div>
            ))}
            {!oneOff.excluded_items.length && <Empty>Nothing has been classified as one-off.</Empty>}
          </div>
        </Card>
      </div>

      <Card title={`Burn by category — ${cats.month_label}`}
            sub="Nine top-level categories, never buried"
            basis={cats.basis} pad={false}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Category</TH><TH>This month</TH><TH>3-mth avg</TH><TH>% of total</TH>
            <TH left>Nature</TH><TH>Plan</TH><TH>vs plan</TH><TH left>Trend</TH>
          </tr></thead>
          <tbody>
            {cats.rows.map((r) => (
              <tr key={r.category} className="tr-hover cursor-pointer group"
                  onClick={() => openTrace(r.trace, r.category)}>
                <TD left className="!text-ink font-medium">
                  <span className="flex items-center gap-1.5">
                    {r.category}
                    <Icon name="chevronRight" size={12}
                          className="text-ink-faint opacity-0 group-hover:opacity-100" />
                  </span>
                </TD>
                <TD className="font-semibold !text-ink">{inr(r.this_month)}</TD>
                <TD>{inr(r.avg_3m)}</TD>
                <TD>{r.pct_of_total}%</TD>
                <TD left><NatureChip nature={r.cost_nature} /></TD>
                <TD>{r.plan !== null ? inr(r.plan) : '—'}</TD>
                <TD className={cls(r.vs_plan > 0 ? 'text-amber font-medium' : '')}>
                  {r.vs_plan !== null ? inr(r.vs_plan, { sign: true }) : '—'}
                </TD>
                <TD left>
                  <span className="flex items-center gap-1 text-2xs">
                    {r.trend !== 'flat' && (
                      <Icon name={r.trend === 'up' ? 'arrowUp' : 'arrowDown'} size={11}
                            className={r.trend === 'up' ? 'text-amber' : 'text-green'} />
                    )}
                    <span className="text-ink-muted tnum">{pct(r.trend_pct, { sign: true })}</span>
                  </span>
                </TD>
              </tr>
            ))}
          </tbody>
          <tfoot><tr>
            <TD left className="!text-ink font-semibold !border-t !border-line">Total</TD>
            <TD className="!text-ink font-semibold !border-t !border-line">{inr(cats.total)}</TD>
            <TD colSpan={6} className="!border-t !border-line" />
          </tr></tfoot>
        </Table>
      </Card>

      <Card title="Burn per unit" sub="What each head and each rupee of revenue costs us"
            basis={burn.per_unit.basis}>
        <StatRow cols={2} className="mb-4">
          <Stat label="Burn per head, per month" value={inr(burn.per_unit.current_burn_per_head)} size="lg" />
          <Stat label="Burn per rupee collected" value={`${num(burn.per_unit.current_burn_to_revenue, 2)}x`} size="lg"
                sub="Above 1.0 means we spend more than we collect" />
        </StatRow>
        <TrendLine data={burn.per_unit.rows} height={200} money={false}
                   formatter={(v) => (v > 1000 ? `${(v / 1e5).toFixed(1)}L` : Number(v).toFixed(2))}
                   keys={[{ key: 'burn_per_head', label: 'Burn per head', colour: MARK.main }]} />
      </Card>

      <ReclassifyModal item={reclass} onClose={() => setReclass(null)}
                       onDone={() => { setReclass(null); reload(); notify('Reclassified.') }} />
    </div>
  )
}

function NatureChip({ nature }) {
  const i = ['Fixed', 'Variable', 'Discretionary'].indexOf(nature)
  if (i < 0) return <span className="text-ink-faint">—</span>
  return (
    <span className="inline-flex items-center gap-1.5 text-2xs text-ink-muted">
      <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: MARK.ordinal[i] }} />
      {nature}
    </span>
  )
}

function ReclassifyModal({ item, onClose, onDone }) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  if (!item) return null

  async function save(isOneOff) {
    setBusy(true); setErr(null)
    try {
      await api.post(`/api/ledger/${item.id}/reclassify`,
        { is_one_off: isOneOff, note: note || item.narration })
      onDone()
    } catch (e) { setErr(e.message); setBusy(false) }
  }

  return (
    <Modal open onClose={onClose} title="Reclassify this item"
           sub="Your name is recorded against the classification, and the change appears in the activity log."
           footer={<>
             <button className="btn-ghost" onClick={onClose}>Cancel</button>
             <button className="btn-ghost" disabled={busy} onClick={() => save(false)}>
               Mark as recurring
             </button>
             <button className="btn-primary" disabled={busy} onClick={() => save(true)}>
               Mark as one-off
             </button>
           </>}>
      <div className="card card-pad mb-4">
        <p className="text-[14px] font-medium text-ink">{item.narration}</p>
        <p className="text-2xs text-ink-muted mt-1">{item.month} · {item.party}</p>
        <p className="text-[18px] font-semibold tnum mt-2">{inr(Math.abs(item.amount))}</p>
      </div>
      <label className="block">
        <span className="label block mb-1.5">Why (optional)</span>
        <textarea rows={3} className="input" value={note} onChange={(e) => setNote(e.target.value)}
                  placeholder="Settlement of a one-time claim, not expected to recur." />
      </label>
      <p className="basis mt-3">
        One-off items are excluded from normalised net burn, which is what runway is
        built on. Reclassifying this will move the runway figure.
      </p>
      {err && <p className="text-[13px] text-red mt-3">{err}</p>}
    </Modal>
  )
}

// ---------------------------------------------------------------------------
function PeoplePane({ people }) {
  const h = people.headcount
  const imp = people.hiring_impact
  const liab = people.liability

  return (
    <div className="space-y-5">
      <Card title="Headcount" sub={`As at ${mon(h.as_on)}`} basis={people.basis}>
        <StatRow cols={4}>
          <Stat label="Funded" value={h.funded ?? '—'} size="lg" />
          <Stat label="Actual" value={h.actual ?? '—'} size="lg" />
          <Stat label="Approved, unfilled" value={h.approved_unfilled ?? '—'} size="lg"
                status={h.approved_unfilled > 3 ? 'Amber' : 'Green'} />
          <Stat label="Offers accepted, not joined" value={h.offers_accepted_not_joined ?? '—'} size="lg" />
        </StatRow>
      </Card>

      <div className="grid xl:grid-cols-2 gap-5 items-start">
        <Card title="Fully-loaded cost per head, by function" pad={false}>
          <Table className="px-4 pb-1">
            <thead><tr>
              <TH left>Function</TH><TH>Heads</TH><TH>Cost per head</TH><TH>Total</TH><TH>% of people cost</TH>
            </tr></thead>
            <tbody>
              {people.by_function.map((f) => (
                <tr key={f.function} className="tr-hover">
                  <TD left className="!text-ink font-medium">{f.function}</TD>
                  <TD>{f.headcount}</TD>
                  <TD>{inr(f.cost_per_head)}</TD>
                  <TD className="font-semibold !text-ink">{inr(f.total_cost)}</TD>
                  <TD>{f.pct}%</TD>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>

        <Card title="People cost, 12 months">
          <TrendLine data={people.monthly_trend} height={230} keys={[
            { key: 'people_cost', label: 'People cost', colour: MARK.main },
          ]} />
        </Card>
      </div>

      <Card title="Hiring plan — cash impact"
            sub={imp.sentence}
            basis="Recurring cost plus one-time recruitment cost, month by month.">
        <StatRow cols={4} className="mb-5">
          <Stat label="Six-month cash cost" value={inr(imp.six_month_cash)} size="lg" />
          <Stat label="Added to monthly run-rate" value={inr(imp.added_monthly_runrate)} size="lg" />
          <Stat label="Cash-out date, before" value={d(imp.cashout_before)} size="lg" />
          <Stat label="Cash-out date, with hiring" value={d(imp.cashout_after)} size="lg"
                status={imp.days_moved < 0 ? 'Amber' : 'Green'}
                sub={imp.days_moved !== null ? `${Math.abs(imp.days_moved)} days ${imp.days_moved < 0 ? 'earlier' : 'later'}` : null} />
        </StatRow>
        <ColumnChart data={imp.rows} height={200} stacked keys={[
          { key: 'recurring', label: 'Recurring cost', colour: MARK.main },
          { key: 'one_time', label: 'One-time cost', colour: MARK.light },
        ]} />
      </Card>

      <div className="grid xl:grid-cols-[1.4fr_1fr] gap-5 items-start">
        <Card title="Open roles" pad={false}>
          <Table className="px-4 pb-1">
            <thead><tr>
              <TH left>Role</TH><TH left>Function</TH><TH>Positions</TH><TH>Start</TH>
              <TH>Monthly cost</TH><TH>One-time</TH><TH left>Status</TH>
            </tr></thead>
            <tbody>
              {people.hiring_plan.map((h2) => (
                <tr key={h2.id} className="tr-hover">
                  <TD left className="!text-ink font-medium">{h2.role}</TD>
                  <TD left>{h2.function}</TD>
                  <TD>{h2.positions}</TD>
                  <TD>{d(h2.planned_start)}</TD>
                  <TD>{inr(h2.monthly_cost_total)}</TD>
                  <TD>{h2.one_time_cost ? inr(h2.one_time_cost) : '—'}</TD>
                  <TD left>
                    <StatusPill status={h2.status === 'accepted' ? 'Amber' : h2.status === 'planned' ? 'Grey' : 'Amber'}
                                label={h2.status} />
                  </TD>
                </tr>
              ))}
              {!people.hiring_plan.length && (
                <tr><TD left colSpan={7}><Empty>No open roles recorded.</Empty></TD></tr>
              )}
            </tbody>
          </Table>
        </Card>

        {liab && (
          <Card title="Gratuity and leave liability"
                sub={`Accrued as at ${d(liab.as_on)}`}
                basis={liab.notes}>
            <div className="space-y-2.5">
              {[['Gratuity', liab.gratuity], ['Leave encashment', liab.leave_encashment],
                ['Bonus', liab.bonus]].map(([l, v]) => (
                <div key={l} className="flex items-baseline justify-between py-1.5 border-b border-line-soft">
                  <span className="text-[13px] text-ink-soft">{l}</span>
                  <span className="text-[14px] font-medium tnum">{inr(v)}</span>
                </div>
              ))}
              <div className="flex items-baseline justify-between pt-1.5">
                <span className="text-[13px] font-semibold">Total accrued</span>
                <span className="text-[18px] font-semibold tnum">{inr(liab.total)}</span>
              </div>
            </div>
            {liab.unfunded > 0 && (
              <div className="mt-3 rounded-lg border border-amber-line bg-amber-bg px-3.5 py-2.5">
                <p className="text-[13px] text-amber font-medium">
                  {inr(liab.unfunded)} of this is unfunded — a future cash call not in any
                  runway figure.
                </p>
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  )
}
