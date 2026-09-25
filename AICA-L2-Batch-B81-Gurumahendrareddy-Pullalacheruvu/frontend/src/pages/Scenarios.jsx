// TAB 8 — Scenarios. Levers on the left, result on the right, updating live.
import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useApp, useEndpoint } from '../lib/store'
import { api } from '../lib/api'
import { cls, d, inr, inrShort, num } from '../lib/format'
import {
  Card, Dot, Empty, ErrorNote, Field, Icon, Loading, Modal, StatusPill,
  Table, TD, TH,
} from '../components/ui'
import { Stat, StatRow } from '../components/Figure'

export default function Scenarios() {
  const { canWrite, notify } = useApp()
  const { data, loading, error, reload } = useEndpoint('/api/scenarios')
  const [levers, setLevers] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [active, setActive] = useState(null)
  const [saving, setSaving] = useState(false)
  const [compare, setCompare] = useState([])
  const [comparison, setComparison] = useState(null)
  const timer = useRef(null)

  useEffect(() => { if (data && !levers) setLevers({ ...data.defaults }) }, [data, levers])

  // Debounced live re-run as a slider moves.
  const run = useCallback((lv) => {
    clearTimeout(timer.current)
    timer.current = setTimeout(async () => {
      setBusy(true)
      try { setResult(await api.post('/api/scenarios/evaluate', lv)) }
      catch { /* keep the last good result on screen */ }
      setBusy(false)
    }, 260)
  }, [])

  useEffect(() => { if (levers) run(levers) }, [levers, run])

  if (loading && !data) return <Loading label="Loading the lever panel…" rows={4} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data || !levers) return null

  const set = (k, v) => { setActive(null); setLevers((l) => ({ ...l, [k]: v })) }
  const load = (s) => { setActive(s.id); setLevers({ ...data.defaults, ...s.levers }) }

  async function toggleCompare(id) {
    const next = compare.includes(id) ? compare.filter((x) => x !== id)
                                      : compare.length < 4 ? [...compare, id] : compare
    setCompare(next)
    setComparison(next.length >= 2 ? await api.post('/api/scenarios/compare', { scenario_ids: next }) : null)
  }

  return (
    <div className="space-y-5">
      <div className="grid xl:grid-cols-[380px_1fr] gap-5 items-start">
        {/* ---- Levers ------------------------------------------------ */}
        <Card title="What if…" sub="Drag a lever — the result updates as you go">
          <div className="space-y-5">
            {data.lever_spec.map((spec) => (
              <Lever key={spec.key} spec={spec} value={levers[spec.key]}
                     onChange={(v) => set(spec.key, v)} />
            ))}
          </div>
          <button onClick={() => { setActive(null); setLevers({ ...data.defaults }) }}
                  className="btn-ghost btn-sm w-full justify-center mt-5">
            <Icon name="refresh" size={13} /> Reset to base
          </button>
        </Card>

        {/* ---- Result ------------------------------------------------ */}
        <div className="space-y-5">
          <Card title="What that does to the position"
                sub={result?.basis}
                right={busy ? <span className="text-2xs text-ink-faint">Recalculating…</span> : null}>
            {!result ? <Loading rows={2} /> : (
              <>
                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <BigStat label="New cash-out date" value={d(result.cashout_date)}
                           sub={result.cashout_days_moved !== null
                             ? `${result.cashout_days_moved > 0 ? '+' : ''}${result.cashout_days_moved} days vs base`
                             : null}
                           status={result.cashout_days_moved < 0 ? 'Red'
                                 : result.cashout_days_moved > 0 ? 'Green' : 'Grey'} />
                  <BigStat label="New runway" value={`${num(result.runway_months)} mo`}
                           sub={`On ${inr(result.monthly_burn)} of net burn`}
                           status={result.runway_months < 6 ? 'Red'
                                 : result.runway_months < 12 ? 'Amber' : 'Green'} />
                  <BigStat label="Lowest cash point" value={inr(result.lowest_cash)}
                           sub={result.lowest_week ? `in ${result.lowest_week}` : null}
                           status={result.lowest_breaches_floor ? 'Red' : 'Green'} />
                  <BigStat label="Verdict" value={result.verdict}
                           status={/Critical|runs out|breach|breaks/i.test(result.verdict) ? 'Red'
                                 : /Tight|Dips/i.test(result.verdict) ? 'Amber' : 'Green'} small />
                </div>

                <div className="grid sm:grid-cols-2 gap-3 mt-5">
                  <Check ok={result.statutory_cover_maintained}
                         label="Statutory cover maintained"
                         no="Statutory dues are not fully covered under this scenario" />
                  <Check ok={!result.covenants_breached}
                         label="No covenant breached"
                         no={`Breaches: ${result.covenants_breached_list?.join('; ')}`} />
                </div>

                {canWrite && (
                  <button onClick={() => setSaving(true)} className="btn-ghost btn-sm mt-5">
                    <Icon name="plus" size={13} /> Save this scenario
                  </button>
                )}
              </>
            )}
          </Card>

          {/* ---- What matters most ---------------------------------- */}
          <Card title="What matters most"
                sub={data.sensitivity.sentence}
                basis={data.sensitivity.basis} pad={false}>
            <Table className="px-4 pb-1">
              <thead><tr>
                <TH left>Lever</TH><TH left>Assumption tested</TH>
                <TH>Days the cash-out date moves</TH><TH>Runway</TH>
              </tr></thead>
              <tbody>
                {data.sensitivity.rows.map((r, i) => (
                  <tr key={r.lever} className={cls('tr-hover', i < 3 && 'bg-navy-50/40')}>
                    <TD left className="!text-ink font-medium">
                      {i < 3 && <span className="text-ink-faint mr-2">{i + 1}</span>}
                      {r.lever}
                    </TD>
                    <TD left className="text-ink-muted">{r.assumption}</TD>
                    <TD className={cls('font-semibold',
                      r.days_moved < 0 ? '!text-red' : r.days_moved > 0 ? '!text-green' : '')}>
                      {r.days_moved > 0 ? '+' : ''}{r.days_moved}
                    </TD>
                    <TD>{num(r.runway_months)} mo</TD>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card>
        </div>
      </div>

      {/* ---- Saved scenarios + comparison ---------------------------- */}
      <Card title="Saved scenarios"
            sub="Tick up to four to hold them side by side"
            pad={false}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left className="w-10" /><TH left>Scenario</TH><TH left>Assumptions</TH>
            <TH left>Saved by</TH><TH left />
          </tr></thead>
          <tbody>
            {data.scenarios.map((s) => (
              <tr key={s.id} className={cls('tr-hover', active === s.id && 'bg-navy-50/60')}>
                <TD left>
                  <input type="checkbox" checked={compare.includes(s.id)}
                         onChange={() => toggleCompare(s.id)}
                         className="w-4 h-4 rounded border-line-strong accent-navy-700" />
                </TD>
                <TD left className="!text-ink font-medium">
                  {s.name}
                  {s.is_prebuilt && <span className="ml-2 chip bg-grey-bg border-grey-line text-grey">Built in</span>}
                </TD>
                <TD left className="text-ink-muted max-w-[520px] whitespace-normal">{s.note}</TD>
                <TD left>{s.created_by || 'System'}</TD>
                <TD left>
                  <button className="text-2xs linkish" onClick={() => load(s)}>Load</button>
                </TD>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      {comparison && (
        <Card title="Side by side" basis={comparison.basis} pad={false}>
          <Table className="px-4 pb-1">
            <thead><tr>
              <TH left>Scenario</TH><TH>Cash-out date</TH><TH>Runway</TH>
              <TH>Lowest cash</TH><TH left>Lowest week</TH><TH left>Verdict</TH>
            </tr></thead>
            <tbody>
              {comparison.rows.map((r) => (
                <tr key={r.scenario_id} className="tr-hover">
                  <TD left className="!text-ink font-medium">{r.name}</TD>
                  <TD>{d(r.cashout_date)}</TD>
                  <TD className="font-semibold !text-ink">{num(r.runway_months)} mo</TD>
                  <TD>{inr(r.lowest_cash)}</TD>
                  <TD left>{r.lowest_week}</TD>
                  <TD left>
                    <StatusPill label={r.verdict}
                      status={/Critical|runs out|breach|breaks/i.test(r.verdict) ? 'Red'
                            : /Tight|Dips/i.test(r.verdict) ? 'Amber' : 'Green'} />
                  </TD>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      )}

      <SaveModal open={saving} levers={levers} onClose={() => setSaving(false)}
                 onDone={() => { setSaving(false); reload(); notify('Scenario saved.') }} />
    </div>
  )
}

function BigStat({ label, value, sub, status, small }) {
  return (
    <div className="rounded-lg border border-line bg-canvas px-4 py-3.5">
      <span className="label flex items-center gap-1.5">{label}{status && <Dot status={status} />}</span>
      <p className={cls('font-semibold tracking-tight mt-1.5 tnum',
                        small ? 'text-[16px]' : 'text-[21px]',
                        status === 'Red' ? 'text-red' : 'text-ink')}>{value}</p>
      {sub && <p className="text-2xs text-ink-muted mt-1">{sub}</p>}
    </div>
  )
}

function Check({ ok, label, no }) {
  return (
    <div className={cls('rounded-lg border px-3.5 py-2.5 flex items-start gap-2.5',
      ok ? 'border-green-line bg-green-bg' : 'border-red-line bg-red-bg')}>
      <Icon name={ok ? 'check' : 'alert'} size={15}
            className={cls('mt-0.5 shrink-0', ok ? 'text-green' : 'text-red')} />
      <p className={cls('text-[13px] font-medium', ok ? 'text-green' : 'text-red')}>
        {ok ? label : no}
      </p>
    </div>
  )
}

function Lever({ spec, value, onChange }) {
  const [label, tail] = spec.label.split('…')

  if (spec.type === 'choice') {
    return (
      <div>
        <span className="label block mb-2">{spec.label}</span>
        <div className="grid grid-cols-3 gap-1.5">
          {spec.options.map((o) => (
            <button key={o} onClick={() => onChange(o)}
                    className={cls('rounded-lg border px-2 py-1.5 text-2xs font-semibold capitalize transition-colors',
                      value === o ? 'border-navy-500 bg-navy-50 text-navy-700'
                                  : 'border-line text-ink-muted hover:border-navy-300')}>
              {o}
            </button>
          ))}
        </div>
      </div>
    )
  }

  if (spec.type === 'date') {
    return (
      <Field label={spec.label}>
        <input type="date" className="input" value={value || ''}
               onChange={(e) => onChange(e.target.value || null)} />
      </Field>
    )
  }

  if (spec.type === 'money') {
    return (
      <div>
        <div className="flex items-baseline justify-between mb-2">
          <span className="label">{label}</span>
          <span className="text-[13px] font-semibold tnum">{inr(Number(value) || 0)}</span>
        </div>
        <input type="range" min={spec.min} max={spec.max} step={spec.step}
               value={Number(value) || 0} onChange={(e) => onChange(Number(e.target.value))}
               className="w-full accent-navy-700" />
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-baseline justify-between mb-2 gap-2">
        <span className="label min-w-0 truncate">{label}{tail}</span>
        <span className="text-[13px] font-semibold tnum shrink-0">
          {value}{spec.unit === '%' ? '%' : spec.unit === 'days' ? 'd' : spec.unit === 'months' ? ' mo' : ''}
        </span>
      </div>
      <input type="range" min={spec.min} max={spec.max} step={spec.step}
             value={value} onChange={(e) => onChange(Number(e.target.value))}
             className="w-full accent-navy-700" />
      <div className="flex justify-between text-[10px] text-ink-faint mt-1 tnum">
        <span>{spec.min}</span><span>{spec.max}</span>
      </div>
    </div>
  )
}

function SaveModal({ open, levers, onClose, onDone }) {
  const [name, setName] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  if (!open) return null

  async function save() {
    if (!name.trim()) { setErr('Give the scenario a name.'); return }
    setBusy(true); setErr(null)
    try { await api.post('/api/scenarios', { name: name.trim(), note, levers }); onDone() }
    catch (e) { setErr(e.message); setBusy(false) }
  }

  return (
    <Modal open onClose={onClose} title="Save this scenario"
           sub="It will appear in the list below and can be added to a board pack."
           footer={<>
             <button className="btn-ghost" onClick={onClose}>Cancel</button>
             <button className="btn-primary" disabled={busy} onClick={save}>
               {busy ? 'Saving…' : 'Save'}
             </button>
           </>}>
      <div className="space-y-4">
        <Field label="Name">
          <input className="input" value={name} onChange={(e) => setName(e.target.value)}
                 placeholder="Metro pays, hiring frozen" autoFocus />
        </Field>
        <Field label="Note the assumptions"
               hint="Six months from now this is the only record of why you ran it.">
          <textarea rows={3} className="input" value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
      </div>
      {err && <p className="text-[13px] text-red mt-3">{err}</p>}
    </Modal>
  )
}
