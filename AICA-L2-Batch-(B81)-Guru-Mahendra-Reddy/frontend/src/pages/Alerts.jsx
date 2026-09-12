// TAB 11 — Alerts. What the tool said, and whether anyone acted on it.
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp, useEndpoint } from '../lib/store'
import { api } from '../lib/api'
import { cls, d, inr, num, ts } from '../lib/format'
import {
  Card, Dot, Empty, ErrorNote, Field, Icon, Loading, Modal, StatusPill,
  Table, TD, TH, Toggle,
} from '../components/ui'
import { Stat, StatRow } from '../components/Figure'

export default function Alerts() {
  const { canWrite, notify, refresh } = useApp()
  const { data, loading, error, reload } = useEndpoint('/api/alerts')
  const [act, setAct] = useState(null)
  const [running, setRunning] = useState(false)
  const nav = useNavigate()

  if (loading && !data) return <Loading label="Loading alerts…" rows={4} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data) return null

  const perf = data.performance

  async function runNow() {
    setRunning(true)
    try {
      const r = await api.post('/api/alerts/run')
      notify(r.fired.length
        ? `${r.fired.length} alert${r.fired.length === 1 ? '' : 's'} fired.`
        : 'No rule fired. Nothing has crossed a threshold.')
      reload(); refresh()
    } catch (e) { notify(e.message, 'error') }
    setRunning(false)
  }

  return (
    <div className="space-y-5">
      {/* ---- The honest panel ---------------------------------------- */}
      <Card title="Alert performance"
            sub={`Last ${perf.window_days} days`}
            right={canWrite && (
              <button className="btn-ghost btn-sm" disabled={running} onClick={runNow}>
                <Icon name="refresh" size={13} /> {running ? 'Evaluating…' : 'Evaluate rules now'}
              </button>)}
            basis="If most alerts are being ignored, the thresholds are wrong. This panel is here to say so.">
        <StatRow cols={5}>
          <Stat label="Sent" value={perf.sent} size="lg" />
          <Stat label="Acted on" value={perf.acted_on} size="lg"
                sub={perf.acted_pct !== null ? `${perf.acted_pct}%` : null} />
          <Stat label="Ignored" value={perf.ignored} size="lg"
                status={perf.ignored > perf.sent * 0.5 ? 'Amber' : 'Green'} />
          <Stat label="Muted" value={perf.muted} size="lg" />
          <Stat label="Median time to acknowledge" size="lg"
                value={perf.median_hours_to_acknowledge !== null
                  ? `${num(perf.median_hours_to_acknowledge)}h` : '—'} />
        </StatRow>
        <p className={cls('mt-4 pt-3 border-t border-line-soft text-[13px] font-medium',
          perf.ignored > perf.sent * 0.5 ? 'text-amber' : 'text-ink-soft')}>
          {perf.verdict}
        </p>
      </Card>

      {/* ---- Active -------------------------------------------------- */}
      <Card title="Active alerts" pad={false}
            sub="Ranked by severity, then by what is at stake">
        {data.active.length === 0 ? (
          <Empty>Nothing is currently alerting. Every threshold is inside its band.</Empty>
        ) : (
          <div className="px-4 pb-4 space-y-2.5">
            {data.active.map((a) => (
              <AlertRow key={a.id} a={a} canWrite={canWrite} onAct={setAct} nav={nav} />
            ))}
          </div>
        )}
      </Card>

      {/* ---- History ------------------------------------------------- */}
      <Card title="Alert history" pad={false}
            sub="Including whether the message was actually delivered and read">
        {data.history.length === 0 ? <Empty>No resolved or muted alerts yet.</Empty> : (
          <Table className="px-4 pb-1">
            <thead><tr>
              <TH left>Severity</TH><TH left>Alert</TH><TH>Triggered</TH>
              <TH>Trigger vs threshold</TH><TH>At stake</TH>
              <TH left>Acknowledged by</TH><TH>Time to ack</TH>
              <TH left>Channels</TH><TH left>Status</TH>
            </tr></thead>
            <tbody>
              {data.history.map((a) => (
                <tr key={a.id} className="tr-hover">
                  <TD left><StatusPill status={a.severity} /></TD>
                  <TD left className="!text-ink font-medium max-w-[300px] whitespace-normal">{a.title}</TD>
                  <TD>{ts(a.triggered_on)}</TD>
                  <TD className="text-2xs">
                    {a.trigger_value !== null
                      ? `${num(a.trigger_value)} vs ${num(a.threshold_value)} ${a.value_unit || ''}` : '—'}
                  </TD>
                  <TD>{a.amount_at_stake ? inr(a.amount_at_stake) : '—'}</TD>
                  <TD left>{a.acknowledged_by || <span className="text-ink-faint">Nobody</span>}</TD>
                  <TD>{a.hours_to_acknowledge !== null ? `${num(a.hours_to_acknowledge)}h` : '—'}</TD>
                  <TD left><Delivery deliveries={a.deliveries} /></TD>
                  <TD left>
                    <StatusPill status={a.status === 'resolved' ? 'Green' : 'Grey'} label={a.status} />
                  </TD>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <ActModal alert={act} onClose={() => setAct(null)}
                onDone={() => { setAct(null); reload(); refresh(); notify('Recorded.') }} />
    </div>
  )
}

function AlertRow({ a, canWrite, onAct, nav }) {
  const sev = a.severity
  return (
    <div className={cls('rounded-lg border px-4 py-3.5',
      sev === 'Red' ? 'border-red-line bg-red-bg'
        : sev === 'Amber' ? 'border-amber-line bg-amber-bg' : 'border-grey-line bg-grey-bg')}>
      <div className="flex items-start justify-between gap-5 flex-wrap">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <StatusPill status={sev} label={sev === 'Red' ? 'Act this week'
                                          : sev === 'Amber' ? 'Watch' : 'Data incomplete'} />
            <span className="text-[14px] font-semibold text-ink">{a.title}</span>
            {a.status === 'acknowledged' && <StatusPill status="Grey" label="Acknowledged" />}
            {a.status === 'snoozed' && <StatusPill status="Grey" label={`Snoozed to ${d(a.snoozed_until)}`} />}
            {a.escalated_on && <StatusPill status="Red" label="Escalated" />}
          </div>
          <p className="text-[13px] text-ink-soft mt-1.5 leading-relaxed">{a.message}</p>
          <div className="flex items-center gap-4 mt-2.5 flex-wrap text-2xs text-ink-muted">
            <span>Triggered {ts(a.triggered_on)}</span>
            {a.trigger_value !== null && (
              <span className="tnum">
                {num(a.trigger_value)} against a threshold of {num(a.threshold_value)} {a.value_unit}
              </span>
            )}
            {a.amount_at_stake > 0 && (
              <span className="tnum font-semibold text-ink-soft">
                {inr(a.amount_at_stake)} at stake
              </span>
            )}
            <Delivery deliveries={a.deliveries} />
          </div>
          {a.acknowledged_by && (
            <p className="text-2xs text-ink-muted mt-2 pt-2 border-t border-ink/5">
              <span className="font-semibold">{a.acknowledged_by}</span>
              {a.action_taken ? `: ${a.action_taken}` : ' acknowledged this.'}
            </p>
          )}
        </div>

        <div className="shrink-0 flex items-center gap-2">
          {a.deep_link && (
            <button className="btn-ghost btn-sm" onClick={() => nav(a.deep_link)}>
              Open <Icon name="chevronRight" size={12} />
            </button>
          )}
          {canWrite && a.status !== 'resolved' && (
            <button className="btn-primary btn-sm" onClick={() => onAct(a)}>Record action</button>
          )}
        </div>
      </div>
    </div>
  )
}

function Delivery({ deliveries }) {
  if (!deliveries?.length) return <span className="text-2xs text-ink-faint">Not sent</span>
  return (
    <span className="flex items-center gap-2.5">
      {deliveries.map((x, i) => (
        <span key={i} className="inline-flex items-center gap-1 text-2xs"
              title={x.error || `${x.recipient} · ${x.delivered ? 'delivered' : 'failed'}${x.read ? ' · read' : ''}`}>
          <Dot status={x.delivered ? (x.read ? 'Green' : 'Amber') : 'Red'} />
          <span className="capitalize text-ink-muted">{x.channel}</span>
        </span>
      ))}
    </span>
  )
}

function ActModal({ alert, onClose, onDone }) {
  const [action, setAction] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  React.useEffect(() => { if (alert) setAction(alert.action_taken || '') }, [alert])
  if (!alert) return null

  async function go(kind) {
    setBusy(true); setErr(null)
    try {
      if (kind === 'snooze') await api.post(`/api/alerts/${alert.id}/snooze`, { hours: 24 })
      else await api.post(`/api/alerts/${alert.id}/${kind}`, { action_taken: action || null })
      onDone()
    } catch (e) { setErr(e.message); setBusy(false) }
  }

  return (
    <Modal open onClose={onClose} title={alert.title}
           sub="What was done about it is as important as the alert itself."
           footer={<>
             <button className="btn-ghost" onClick={onClose}>Cancel</button>
             <button className="btn-ghost" disabled={busy} onClick={() => go('snooze')}>Snooze 24h</button>
             <button className="btn-ghost" disabled={busy} onClick={() => go('acknowledge')}>Acknowledge</button>
             <button className="btn-primary" disabled={busy} onClick={() => go('resolve')}>Resolve</button>
           </>}>
      <p className="text-[13px] text-ink-soft leading-relaxed mb-4">{alert.message}</p>
      <Field label="Action taken"
             hint="This appears in the alert history and in the activity log against your name.">
        <textarea rows={3} className="input" value={action} onChange={(e) => setAction(e.target.value)}
                  placeholder="Chasing ₹ 50 L from Bharat Metro; will earmark on receipt." />
      </Field>
      {err && <p className="text-[13px] text-red mt-3">{err}</p>}
    </Modal>
  )
}
