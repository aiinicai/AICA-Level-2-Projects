// Setup › Tally. Four steps, of which only one is interesting: the mapping.
import React, { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import { useApp, useEndpoint } from '../../lib/store'
import { ts } from '../../lib/format'
import {
  Card, Empty, ErrorNote, Field, Icon, Loading, StatusPill, Table, TD, TH,
} from '../../components/ui'

export default function TallyWizard() {
  const { canWrite, notify, refresh } = useApp()
  const status = useEndpoint('/api/connect/status')
  const [step, setStep] = useState(1)

  return (
    <div className="space-y-5">
      <SyncStatusCard data={status.data} loading={status.loading}
                      error={status.error} reload={status.reload} />

      <div className="flex flex-wrap gap-1.5">
        {[[1, 'Connect'], [2, 'Choose company'], [3, 'Map the ledgers'], [4, 'Schedule']]
          .map(([n, l]) => (
            <button key={n} onClick={() => setStep(n)}
                    className={`rounded-lg px-3.5 py-2 text-[13px] font-medium transition
                      ${step === n ? 'bg-navy-700 text-white'
                                   : 'border border-line text-ink hover:bg-paper'}`}>
              <span className="opacity-60 mr-1.5">{n}</span>{l}
            </button>
          ))}
      </div>

      {step === 1 && <StepConnect onNext={() => setStep(2)} />}
      {step === 2 && <StepCompany canWrite={canWrite} notify={notify}
                                  onNext={() => setStep(3)} />}
      {step === 3 && <StepMapping canWrite={canWrite} notify={notify}
                                  refresh={refresh} onNext={() => setStep(4)} />}
      {step === 4 && <StepSchedule canWrite={canWrite} notify={notify} />}
    </div>
  )
}

// ---------------------------------------------------------------------------
function SyncStatusCard({ data, loading, error, reload }) {
  if (loading && !data) return <Loading rows={2} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data) return null

  const tone = { green: 'status-green', amber: 'status-amber', red: 'status-red',
                 grey: 'grey' }[data.level] || 'grey'

  return (
    <div className={`rounded-2xl border p-4 bg-${tone}/5 border-${tone}/30`}
         style={{ borderColor: `var(--tone-${data.level}, #d8dce5)` }}>
      <div className="flex items-start gap-3">
        <span className="mt-1 w-2.5 h-2.5 rounded-full shrink-0"
              style={{ background: `var(--tone-${data.level}, #8a93a6)` }} />
        <div className="flex-1 min-w-0">
          <p className="text-[13.5px] text-ink font-medium">{data.headline}</p>
          <p className="basis mt-1">
            {data.company ? `Company: ${data.company}. ` : ''}
            {data.schedule.enabled
              ? `Daily sync at ${data.schedule.at}, stale after ${data.schedule.stale_after_hours}h.`
              : 'Daily sync is off — syncs happen only when someone presses Sync now.'}
            {data.unmapped_ledgers > 0 &&
              ` ${data.unmapped_ledgers} ledger(s) still need mapping.`}
            {data.consecutive_failures > 1 &&
              ` ${data.consecutive_failures} failed attempts in a row.`}
          </p>
        </div>
        <button onClick={reload} className="text-ink-muted hover:text-ink shrink-0"
                title="Check again">
          <Icon name="refresh" size={15} />
        </button>
      </div>

      {!!data.history?.length && (
        <details className="mt-3">
          <summary className="text-[12px] text-ink-muted cursor-pointer hover:text-ink">
            Sync history — including the failures
          </summary>
          <Table className="mt-2">
            <thead><tr><TH left>When</TH><TH>Status</TH><TH>Records</TH><TH left>Message</TH></tr></thead>
            <tbody>
              {data.history.map((h, i) => (
                <tr key={i}>
                  <TD left>{ts(h.at)}</TD>
                  <TD>
                    <StatusPill
                      status={h.status === 'success' ? 'Green'
                            : h.status === 'partial' ? 'Amber' : 'Red'}
                      label={h.status} />
                  </TD>
                  <TD>{h.records ?? '—'}</TD>
                  <TD left className="text-ink-muted">{h.message || '—'}</TD>
                </tr>
              ))}
            </tbody>
          </Table>
        </details>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
function StepConnect({ onNext }) {
  const [host, setHost] = useState('localhost')
  const [port, setPort] = useState(9000)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  async function test() {
    setBusy(true)
    try { setResult(await api.get('/api/connect/tally/test', { host, port }, { scoped: false })) }
    catch (e) { setResult({ connected: false, message: e.message }) }
    setBusy(false)
  }

  return (
    <Card title="Is Tally reachable"
          sub="Tally speaks XML over HTTP on the machine it runs on. There is no API key — the trade-off is that this application has to be on the same network.">
      <div className="grid sm:grid-cols-3 gap-3 mb-4">
        <Field label="Host"><input className="input" value={host}
                                   onChange={(e) => setHost(e.target.value)} /></Field>
        <Field label="Port"><input className="input" value={port} inputMode="numeric"
                                   onChange={(e) => setPort(Number(e.target.value) || 0)} /></Field>
        <div className="flex items-end">
          <button onClick={test} disabled={busy}
                  className="w-full rounded-lg bg-navy-700 text-white px-4 py-2 text-[13px]
                             font-medium hover:bg-navy-800 disabled:opacity-40">
            {busy ? 'Trying…' : 'Test connection'}
          </button>
        </div>
      </div>

      {result && (
        <div className={`rounded-xl border p-3.5 mb-4
                        ${result.connected ? 'border-status-green/40 bg-status-green/5'
                                           : 'border-status-red/30 bg-status-red/5'}`}>
          <p className="text-[13px] text-ink font-medium">{result.message}</p>
          {!!result.companies?.length && (
            <p className="basis mt-1.5">Open in Tally: {result.companies.join(', ')}</p>
          )}
        </div>
      )}

      {result && !result.connected && !!result.checklist && (
        <div>
          <h4 className="text-[13px] font-medium text-ink mb-2">Check these, in order</h4>
          <ul className="space-y-1.5">
            {result.checklist.map((c, i) => (
              <li key={i} className="text-[12.5px] text-ink leading-relaxed flex gap-2">
                <span className="text-ink-faint">{i + 1}.</span><span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result?.connected && (
        <button onClick={onNext}
                className="rounded-lg border border-line px-4 py-2 text-[13px] hover:bg-paper">
          Next — choose the company
        </button>
      )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
function StepCompany({ canWrite, notify, onNext }) {
  const [ping, setPing] = useState(null)
  const [chosen, setChosen] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get('/api/connect/tally/test', {}, { scoped: false })
      .then((r) => { setPing(r); if (r.companies?.length === 1) setChosen(r.companies[0]) })
      .catch((e) => setPing({ connected: false, message: e.message }))
  }, [])

  async function save() {
    setBusy(true)
    try {
      await api.post('/api/connect/tally/company', { company: chosen })
      notify(`Reading from '${chosen}'.`)
      onNext()
    } catch (e) { notify(e.message, 'error') }
    setBusy(false)
  }

  if (!ping) return <Loading rows={2} />

  return (
    <Card title="Which company"
          sub="Tally can have several open at once. This entity reads from one of them.">
      {!ping.connected
        ? <Empty>Not connected. Go back to step 1.</Empty>
        : !ping.companies?.length
          ? <Empty>
              Tally answered, but no company is open. Open one in Tally and try again —
              a connected-but-empty endpoint is a common cause of a sync that returns
              nothing without failing.
            </Empty>
          : (
            <>
              <Field label="Company">
                <select className="input" value={chosen} onChange={(e) => setChosen(e.target.value)}>
                  <option value="">Choose…</option>
                  {ping.companies.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </Field>
              <button onClick={save} disabled={!chosen || busy || !canWrite}
                      className="mt-4 rounded-lg bg-navy-700 text-white px-4 py-2 text-[13px]
                                 font-medium hover:bg-navy-800 disabled:opacity-40">
                {busy ? 'Saving…' : 'Save and map the ledgers'}
              </button>
            </>
          )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
function StepMapping({ canWrite, notify, refresh, onNext }) {
  const [filter, setFilter] = useState('pending')
  const { data, loading, error, reload } = useEndpoint('/api/connect/tally/mapping',
                                                       { only: filter }, [filter])
  const [edits, setEdits] = useState({})
  const [busy, setBusy] = useState(false)

  async function scan() {
    setBusy(true)
    try {
      const r = await api.post('/api/connect/tally/scan', {})
      notify(r.message)
      reload()
    } catch (e) { notify(e.message, 'error') }
    setBusy(false)
  }

  async function confirmAll() {
    if (!data?.rows.length) return
    setBusy(true)
    try {
      const updates = data.rows.map((r) => ({
        id: r.id,
        ...(edits[r.id] || {}),
        confirmed: true,
      }))
      const res = await api.put('/api/connect/tally/mapping', updates)
      notify(`${res.saved} confirmed, ${res.still_pending} left.`)
      setEdits({})
      reload(); refresh()
    } catch (e) { notify(e.message, 'error') }
    setBusy(false)
  }

  const edit = (id, field) => (e) =>
    setEdits({ ...edits, [id]: { ...(edits[id] || {}), [field]: e.target.value } })

  return (
    <Card
      title="How your ledgers map"
      sub="This is the part that decides whether the numbers are right. Every ledger below is shown with the app's guess — confirm it or change it. A confirmed row is never overwritten by a later sync."
      right={
        <div className="flex gap-2">
          <button onClick={scan} disabled={busy || !canWrite}
                  className="rounded-lg border border-line px-3 py-1.5 text-[12.5px]
                             hover:bg-paper disabled:opacity-40 inline-flex items-center gap-1.5">
            <Icon name="refresh" size={14} /> Read the chart of accounts
          </button>
        </div>
      }>
      {loading && !data ? <Loading rows={4} />
        : error ? <ErrorNote error={error} onRetry={reload} />
        : !data ? null
        : (
          <>
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <div className="flex gap-1.5">
                {[['pending', 'Needs a decision'], ['unmatched', 'Nothing recognised'],
                  ['confirmed', 'Confirmed'], ['all', 'All']].map(([v, l]) => (
                  <button key={v} onClick={() => setFilter(v)}
                          className={`rounded-lg px-3 py-1.5 text-[12.5px] transition
                            ${filter === v ? 'bg-navy-700 text-white'
                                           : 'border border-line hover:bg-paper'}`}>
                    {l}
                  </button>
                ))}
              </div>
              <span className="text-[12.5px] text-ink-muted">
                {data.confirmed} of {data.total} confirmed
              </span>
            </div>

            {!data.rows.length
              ? <Empty>
                  {filter === 'pending'
                    ? 'Nothing is waiting. Every ledger has been confirmed.'
                    : 'Nothing here. Read the chart of accounts to populate this.'}
                </Empty>
              : (
                <>
                  <div className="max-h-[26rem] overflow-y-auto rounded-xl border border-line">
                    <Table>
                      <thead>
                        <tr>
                          <TH left>Tally ledger</TH><TH left>Under</TH>
                          <TH left>Treat as</TH><TH left>Category</TH><TH>State</TH>
                        </tr>
                      </thead>
                      <tbody>
                        {data.rows.map((r) => (
                          <tr key={r.id} className={r.guess_matched ? '' : 'bg-status-amber/5'}>
                            <TD left className="font-medium">{r.ledger_name}</TD>
                            <TD left className="text-ink-muted">{r.parent_group || '—'}</TD>
                            <TD left>
                              <select
                                className="input py-1 text-[12.5px]"
                                value={edits[r.id]?.sub_type ?? r.sub_type ?? 'other'}
                                onChange={edit(r.id, 'sub_type')}
                                disabled={!canWrite}>
                                {data.choices.sub_type.map((s) =>
                                  <option key={s} value={s}>{s}</option>)}
                              </select>
                            </TD>
                            <TD left>
                              <select
                                className="input py-1 text-[12.5px]"
                                value={edits[r.id]?.burn_category ?? r.burn_category ?? ''}
                                onChange={edit(r.id, 'burn_category')}
                                disabled={!canWrite}>
                                <option value="">—</option>
                                {data.choices.burn_category.map((s) =>
                                  <option key={s} value={s}>{s}</option>)}
                              </select>
                            </TD>
                            <TD>
                              {r.confirmed
                                ? <StatusPill status="Green" label="confirmed" />
                                : r.guess_matched
                                  ? <StatusPill status="Grey" label="guessed" />
                                  : <StatusPill status="Amber" label="not recognised" />}
                            </TD>
                          </tr>
                        ))}
                      </tbody>
                    </Table>
                  </div>

                  <div className="flex items-center gap-3 mt-4">
                    <button onClick={confirmAll} disabled={busy || !canWrite}
                            className="rounded-lg bg-navy-700 text-white px-4 py-2 text-[13px]
                                       font-medium hover:bg-navy-800 disabled:opacity-40">
                      {busy ? 'Saving…' : `Confirm these ${data.rows.length}`}
                    </button>
                    <button onClick={onNext}
                            className="rounded-lg border border-line px-4 py-2 text-[13px]
                                       hover:bg-paper">
                      Next — the schedule
                    </button>
                  </div>
                  <p className="basis mt-3">
                    Amber rows are ledgers whose names matched nothing the app knows.
                    They are the ones worth reading carefully — everything in them lands
                    in Other until somebody says otherwise.
                  </p>
                </>
              )}
          </>
        )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
function StepSchedule({ canWrite, notify }) {
  const { data, loading, error, reload } = useEndpoint('/api/connect/schedule')
  const [f, setF] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => { if (data && !f) setF({ ...data }) }, [data]) // eslint-disable-line

  if (loading && !data) return <Loading rows={2} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!f) return null

  async function save() {
    setBusy(true)
    try {
      await api.put('/api/connect/schedule', {
        enabled: f.enabled, hour: Number(f.hour), minute: Number(f.minute),
        lookback_days: Number(f.lookback_days),
        stale_after_hours: Number(f.stale_after_hours),
      })
      notify('Schedule saved.')
      reload()
    } catch (e) { notify(e.message, 'error') }
    setBusy(false)
  }

  return (
    <Card title="When to pull"
          sub="Daily is usually right. Anything more frequent mostly re-reads the same vouchers.">
      <label className="flex items-center gap-2.5 mb-4 text-[13px] text-ink cursor-pointer">
        <input type="checkbox" checked={f.enabled} disabled={!canWrite}
               onChange={(e) => setF({ ...f, enabled: e.target.checked })} />
        Sync automatically every day
      </label>

      <div className="grid sm:grid-cols-4 gap-3">
        <Field label="Hour"><input className="input" value={f.hour} inputMode="numeric"
                                   disabled={!canWrite}
                                   onChange={(e) => setF({ ...f, hour: e.target.value })} /></Field>
        <Field label="Minute"><input className="input" value={f.minute} inputMode="numeric"
                                     disabled={!canWrite}
                                     onChange={(e) => setF({ ...f, minute: e.target.value })} /></Field>
        <Field label="Look back (days)" hint="How far back each pull re-reads.">
          <input className="input" value={f.lookback_days} inputMode="numeric" disabled={!canWrite}
                 onChange={(e) => setF({ ...f, lookback_days: e.target.value })} />
        </Field>
        <Field label="Stale after (hours)" hint="When the banner turns amber.">
          <input className="input" value={f.stale_after_hours} inputMode="numeric" disabled={!canWrite}
                 onChange={(e) => setF({ ...f, stale_after_hours: e.target.value })} />
        </Field>
      </div>

      <div className="mt-4 rounded-xl border border-line bg-paper p-3.5">
        <p className="text-[12.5px] text-ink leading-relaxed">{data.caveat}</p>
      </div>

      <button onClick={save} disabled={busy || !canWrite}
              className="mt-4 rounded-lg bg-navy-700 text-white px-4 py-2 text-[13px]
                         font-medium hover:bg-navy-800 disabled:opacity-40">
        {busy ? 'Saving…' : 'Save the schedule'}
      </button>
    </Card>
  )
}
