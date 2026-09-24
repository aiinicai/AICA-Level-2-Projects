// TAB 7 — Plan vs Actual. Every number is stamped with the plan it is
// measured against, and variance type is a fixed list, never free text.
import React, { useState } from 'react'
import { useApp, useEndpoint } from '../lib/store'
import { api } from '../lib/api'
import { MARK, cls, d, inr, mon, num, pct, ts } from '../lib/format'
import {
  Card, Dot, Empty, ErrorNote, Field, Icon, Loading, Modal, StatusPill,
  Table, TD, TH,
} from '../components/ui'
import { Stat, StatRow } from '../components/Figure'
import { TrendLine, Waterfall } from '../components/charts'

export default function PlanVsActual() {
  const [planId, setPlanId] = useState(null)
  const { canWrite, notify } = useApp()
  const { data, loading, error, reload } = useEndpoint(
    '/api/plan-vs-actual', planId ? { plan_id: planId } : {}, [planId])
  const [explain, setExplain] = useState(null)

  if (loading && !data) return <Loading label="Measuring actuals against the plan…" rows={4} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data) return null

  if (!data.plan) {
    return (
      <Card>
        <Empty>
          No plan has been uploaded yet. Go to Setup › Upload Plan — until then this
          tab has nothing to measure against.
        </Empty>
      </Card>
    )
  }

  const t = data.tiles
  const p = data.plan

  const chart = data.rows.map((r) => ({
    label: r.label,
    plan: r.plan_closing,
    actual: r.actual_closing,
    prior: r.prior_plan_closing,
  }))

  return (
    <div className="space-y-5">
      {/* ---- Plan selector — mandatory, at the top -------------------- */}
      <Card>
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div className="min-w-0">
            <span className="label block mb-1.5">Measured against</span>
            <div className="flex items-center gap-3 flex-wrap">
              <select value={planId ?? p.id}
                      onChange={(e) => setPlanId(Number(e.target.value))}
                      className="rounded-lg border border-line bg-white px-3 py-1.5 text-[13px]
                                 font-semibold outline-none focus:border-navy-400">
                {data.plans.map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.name} {x.version}{x.is_active ? ' · active' : ''}
                  </option>
                ))}
              </select>
              {p.board_approved
                ? <StatusPill status="Green" label="Board-approved" />
                : <StatusPill status="Grey" label="Not tabled to the board" />}
              {p.is_locked && <StatusPill status="Grey" label="Locked" />}
            </div>
            <p className="text-2xs text-ink-muted mt-2 max-w-2xl leading-relaxed">{p.note}</p>
            <p className="basis mt-1.5">
              Uploaded by {p.uploaded_by} on {ts(p.uploaded_on)}
              {p.approved_by && ` · approved by ${p.approved_by}, seconded by ${p.seconded_by}, on ${d(p.approved_on)}`}
            </p>
          </div>
        </div>
      </Card>

      {/* ---- Tiles ---------------------------------------------------- */}
      <Card basis={data.basis}>
        <StatRow cols={4}>
          <Stat label="This month variance" value={inr(t.this_month_variance, { sign: true })} size="lg"
                sub={t.this_month_variance_pct !== null ? pct(t.this_month_variance_pct, { sign: true }) : null}
                status={(t.this_month_variance ?? 0) < 0 ? 'Amber' : 'Green'} />
          <Stat label="Year to date variance" value={inr(t.ytd_variance, { sign: true })} size="lg"
                sub={pct(t.ytd_variance_pct, { sign: true })}
                status={(t.ytd_variance ?? 0) < 0 ? 'Amber' : 'Green'} />
          <Stat label="Cash-out: plan vs actual trajectory" size="lg"
                value={t.cashout_actual ? d(t.cashout_actual) : '—'}
                sub={t.cashout_per_plan
                  ? `Plan said ${d(t.cashout_per_plan)}${t.cashout_gap_days !== null
                      ? ` · ${Math.abs(t.cashout_gap_days)} days ${t.cashout_gap_days < 0 ? 'earlier' : 'later'}` : ''}`
                  : 'The plan does not run to zero cash'}
                status={t.cashout_gap_days !== null && t.cashout_gap_days < -14 ? 'Red' : 'Green'} />
          <Stat label="Forecast accuracy" value={t.forecast_accuracy ? `${Math.round(t.forecast_accuracy)}/100` : '—'}
                size="lg" basis="How close the weekly forecast has been over the last 8 weeks." />
        </StatRow>
      </Card>

      <div className="grid xl:grid-cols-[1.3fr_1fr] gap-5 items-start">
        <Card title="Cash position — plan vs actual"
              sub={data.prior_plan
                ? `Ghosted line is ${data.prior_plan.name} ${data.prior_plan.version}, so plan drift is visible`
                : 'No earlier plan version to compare against'}>
          <TrendLine data={chart} height={270} keys={[
            { key: 'plan', label: `Plan ${p.version}`, colour: MARK.main },
            { key: 'actual', label: 'Actual', colour: MARK.deep },
            ...(data.prior_plan ? [{ key: 'prior', label: `Plan ${data.prior_plan.version}`,
                                     colour: MARK.pale, dashed: true }] : []),
          ]} />
        </Card>

        <Card title="Plan cash to actual cash"
              sub="Grouped by variance type. Timing bars are faded — they reverse."
              basis={`Explained ${inr(data.waterfall.explained)} of ${inr(data.waterfall.total_variance)}. `
                     + `${inr(Math.abs(data.waterfall.unexplained))} is still unexplained.`}>
          {data.waterfall.bars.length > 2
            ? <Waterfall bars={data.waterfall.bars} height={270} />
            : <Empty>Not enough explained variance to draw a bridge yet.</Empty>}
        </Card>
      </div>

      {/* ---- Monthly variance table ----------------------------------- */}
      <Card title="Monthly variance"
            sub="Type is a fixed list — a slipped collection and a lost deal are different events"
            pad={false}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Month</TH><TH>Plan</TH><TH>Actual</TH><TH>Variance</TH><TH>%</TH>
            <TH left>Type</TH><TH left>Driver</TH><TH left>Owner</TH><TH left>Status</TH>
            {canWrite && <TH left />}
          </tr></thead>
          <tbody>
            {data.rows.map((r) => (
              <tr key={r.month} className={cls('tr-hover', !r.is_actual && 'opacity-55')}>
                <TD left className="!text-ink font-medium">{r.label}</TD>
                <TD>{inr(r.plan_net)}</TD>
                <TD>{r.is_actual ? inr(r.actual_net) : '—'}</TD>
                <TD className={cls('font-semibold',
                  r.variance === null ? '' : r.variance < 0 ? '!text-amber' : '!text-green')}>
                  {r.variance !== null ? inr(r.variance, { sign: true }) : '—'}
                </TD>
                <TD>{r.variance_pct !== null ? pct(r.variance_pct, { sign: true }) : '—'}</TD>
                <TD left>
                  {r.variance_type
                    ? <span className="chip bg-navy-50 border-navy-200 text-navy-700">
                        {r.variance_type}
                        {['Timing'].includes(r.variance_type) && ' ↩'}
                      </span>
                    : <span className="text-ink-faint">—</span>}
                </TD>
                <TD left className="text-ink-muted max-w-[340px] whitespace-normal">{r.driver || '—'}</TD>
                <TD left>{r.owner || '—'}</TD>
                <TD left>
                  {r.status
                    ? <StatusPill status={r.status === 'open' ? 'Amber' : r.status === 'closed' ? 'Green' : 'Grey'}
                                  label={r.status} />
                    : '—'}
                </TD>
                {canWrite && (
                  <TD left>
                    {r.is_actual && (
                      <button className="text-2xs linkish"
                              onClick={() => setExplain({ ...r, plan_id: p.id })}>
                        {r.variance_type ? 'Edit' : 'Explain'}
                      </button>
                    )}
                  </TD>
                )}
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      {/* ---- Line item variance --------------------------------------- */}
      <Card title="Line-item variance, this month"
            sub="Whether the miss is top-line or spend" pad={false}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Line</TH><TH>Plan</TH><TH>Actual</TH><TH>Variance</TH><TH>%</TH>
          </tr></thead>
          <tbody>
            {data.line_items.map((r) => (
              <tr key={r.line} className={cls('tr-hover', r.kind === 'revenue' && 'bg-navy-50/50')}>
                <TD left className="!text-ink font-medium">
                  {r.line}
                  {r.kind === 'revenue' && <span className="ml-2 text-2xs text-ink-muted font-normal">revenue</span>}
                </TD>
                <TD>{inr(r.plan)}</TD>
                <TD>{inr(r.actual)}</TD>
                <TD className={cls('font-semibold', r.variance < 0 ? '!text-amber' : '!text-green')}>
                  {inr(r.variance, { sign: true })}
                </TD>
                <TD>{pct(r.variance_pct, { sign: true })}</TD>
              </tr>
            ))}
          </tbody>
        </Table>
        <p className="basis px-4 pb-4 pt-2">
          For cost lines a positive variance means we spent less than plan.
        </p>
      </Card>

      {/* ---- Plan history --------------------------------------------- */}
      <Card title="Plan history" sub="Every version ever uploaded. Nothing is overwritten." pad={false}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Version</TH><TH left>Name</TH><TH left>Uploaded by</TH><TH>Uploaded</TH>
            <TH left>Note</TH><TH left>Active</TH><TH left>Locked</TH>
          </tr></thead>
          <tbody>
            {data.plans.map((x) => (
              <tr key={x.id} className="tr-hover cursor-pointer" onClick={() => setPlanId(x.id)}>
                <TD left className="!text-ink font-semibold">{x.version}</TD>
                <TD left>{x.name}</TD>
                <TD left>{x.uploaded_by}</TD>
                <TD>{ts(x.uploaded_on)}</TD>
                <TD left className="text-ink-muted max-w-[380px] whitespace-normal">{x.note || '—'}</TD>
                <TD left>{x.is_active ? <StatusPill status="Green" label="Active" /> : '—'}</TD>
                <TD left>{x.is_locked ? <Icon name="lock" size={13} className="text-ink-muted" /> : '—'}</TD>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <ExplainModal row={explain} types={data.variance_types}
                    onClose={() => setExplain(null)}
                    onDone={() => { setExplain(null); reload(); notify('Variance explained.') }} />
    </div>
  )
}

function ExplainModal({ row, types, onClose, onDone }) {
  const [form, setForm] = useState({})
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  React.useEffect(() => {
    if (row) setForm({
      variance_type: row.variance_type || '', driver: row.driver || '',
      owner: row.owner || '', comment: row.comment || '', status: row.status || 'open',
    })
  }, [row])
  if (!row) return null

  async function save() {
    if (!form.variance_type || !form.driver) { setErr('Type and driver are both required.'); return }
    setBusy(true); setErr(null)
    try {
      await api.post('/api/variance-notes', {
        plan_id: row.plan_id, month: row.month, note_id: row.note_id ?? undefined,
        ...form,
      })
      onDone()
    } catch (e) { setErr(e.message); setBusy(false) }
  }

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  return (
    <Modal open onClose={onClose}
           title={`Explain the ${row.label} variance`}
           sub={`${inr(row.variance, { sign: true })} against plan. What kind of event was this?`}
           footer={<>
             <button className="btn-ghost" onClick={onClose}>Cancel</button>
             <button className="btn-primary" disabled={busy} onClick={save}>
               {busy ? 'Saving…' : 'Save explanation'}
             </button>
           </>}>
      <div className="space-y-4">
        <Field label="Type"
               hint="Timing reverses. Permanent does not. The waterfall shades them differently.">
          <div className="grid grid-cols-3 gap-2">
            {types.map((t) => (
              <button key={t} type="button"
                      onClick={() => setForm((f) => ({ ...f, variance_type: t }))}
                      className={cls('rounded-lg border px-3 py-2 text-[13px] font-medium transition-colors',
                        form.variance_type === t
                          ? 'border-navy-500 bg-navy-50 text-navy-700'
                          : 'border-line text-ink-soft hover:border-navy-300')}>
                {t}
              </button>
            ))}
          </div>
        </Field>

        <Field label="Driver" hint="One sentence. What actually happened.">
          <input className="input" value={form.driver} onChange={set('driver')}
                 placeholder="Two enterprise deals in the Q2 pipeline pushed to Q3." />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Owner">
            <input className="input" value={form.owner} onChange={set('owner')} />
          </Field>
          <Field label="Status">
            <select className="input" value={form.status} onChange={set('status')}>
              {['open', 'explained', 'actioned', 'closed'].map((s) =>
                <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>
        </div>

        <Field label="Comment">
          <textarea rows={3} className="input" value={form.comment} onChange={set('comment')} />
        </Field>
      </div>
      {err && <p className="text-[13px] text-red mt-3">{err}</p>}
    </Modal>
  )
}
