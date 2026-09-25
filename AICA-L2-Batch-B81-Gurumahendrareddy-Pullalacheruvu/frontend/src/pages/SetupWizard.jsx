// Setting up your own company. Staged, because a forty-field form asking for
// everything up front does not get finished — and because each stage buys
// something specific, which the screen says out loud.
import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useApp, useEndpoint } from '../lib/store'
import { inr } from '../lib/format'
import { Card, ErrorNote, Field, Icon, Loading, Table, TD, TH } from '../components/ui'

const STAGES = [
  { n: 1, title: 'Enough for a runway number',
    buys: 'Cash available, net burn, runway and the cash-out date.',
    needs: ['Bank Accounts', 'Receipts & Payments'] },
  { n: 2, title: 'Open items',
    buys: 'Ageing, DSO, concentration, the 13-week calendar and the statutory gap.',
    needs: ['Open Invoices', 'Open Bills', 'Statutory Dues'] },
  { n: 3, title: 'The judgement layer',
    buys: 'Committed spend that is in no ledger anywhere — the number most cash tools miss.',
    needs: ['Committed Not Billed'] },
]

export default function SetupWizard() {
  const { user, notify } = useApp()
  const nav = useNavigate()
  const [entities, setEntities] = useState(null)
  const [entityId, setEntityId] = useState(null)

  useEffect(() => {
    api.get('/api/onboarding/status', {}, { scoped: false })
      .then((s) => {
        setEntities(s.entities)
        if (s.entities.length) setEntityId(s.entities[0].id)
      })
      .catch(() => setEntities([]))
  }, [])

  if (entities === null) return <Loading rows={3} />

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-5">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[19px] font-semibold text-ink tracking-tight">Set up your company</h1>
          <p className="text-[13px] text-ink-muted mt-1">
            You do not have to finish this in one go. Each stage turns on the screens
            that depend on it, and the ones without their data say so rather than
            showing you a zero.
          </p>
        </div>
        <button onClick={() => nav('/')}
                className="text-[12.5px] text-ink-muted hover:text-ink underline
                           underline-offset-4 whitespace-nowrap pt-1">
          Skip for now
        </button>
      </header>

      {!entities.length
        ? <CreateEntity onCreated={(e) => { setEntities([e]); setEntityId(e.id); notify(e.message) }} />
        : <BringInData entityId={entityId} entities={entities} onEntity={setEntityId} />}
    </div>
  )
}

// ---------------------------------------------------------------------------
function CreateEntity({ onCreated }) {
  const [f, setF] = useState({ name: '', code: '', currency: 'INR',
                               min_cash_floor: '', books_closed_upto: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  async function save() {
    setBusy(true); setError(null)
    try {
      const r = await api.post('/api/onboarding/entity', {
        name: f.name.trim(),
        code: f.code.trim().toUpperCase(),
        currency: f.currency,
        min_cash_floor: Number(f.min_cash_floor || 0),
        books_closed_upto: f.books_closed_upto || null,
      }, {})
      onCreated(r)
    } catch (e) { setError(e.message) }
    setBusy(false)
  }

  return (
    <Card title="The company" sub="Step 1 of 2 — the entity everything else hangs off.">
      {error && <div className="mb-4 text-[13px] text-status-red">{error}</div>}
      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Registered name" hint="As it appears on the books.">
          <input className="input" value={f.name} onChange={set('name')}
                 placeholder="Acme Robotics Pvt Ltd" />
        </Field>
        <Field label="Short code" hint="Two or three letters, used in the entity dropdown.">
          <input className="input" value={f.code} onChange={set('code')} placeholder="IN" />
        </Field>
        <Field label="Books closed up to"
               hint="The date the accounts are reliable to. Every figure is stated as at this date.">
          <input type="date" className="input" value={f.books_closed_upto}
                 onChange={set('books_closed_upto')} />
        </Field>
        <Field label="Minimum cash floor"
               hint="The balance you will not go below — usually one payroll plus statutory plus a buffer. In rupees.">
          <input className="input" value={f.min_cash_floor} onChange={set('min_cash_floor')}
                 placeholder="20000000" inputMode="numeric" />
          {Number(f.min_cash_floor) > 0 && (
            <span className="basis block mt-1">{inr(Number(f.min_cash_floor))}</span>
          )}
        </Field>
      </div>
      <button onClick={save} disabled={busy || !f.name.trim() || !f.code.trim()}
              className="mt-5 rounded-lg bg-navy-700 text-white px-4 py-2.5 text-[13px]
                         font-medium hover:bg-navy-800 disabled:opacity-40">
        {busy ? 'Creating…' : 'Create and continue'}
      </button>
    </Card>
  )
}

// ---------------------------------------------------------------------------
function BringInData({ entityId, entities, onEntity }) {
  const [readiness, setReadiness] = useState(null)
  const [tab, setTab] = useState('workbook')

  const load = React.useCallback(() => {
    if (!entityId) return
    api.get('/api/onboarding/readiness', { entity_id: entityId }, { scoped: false })
      .then(setReadiness).catch(() => {})
  }, [entityId])
  useEffect(load, [load])

  return (
    <div className="space-y-5">
      {entities.length > 1 && (
        <Field label="Entity">
          <select className="input" value={entityId || ''}
                  onChange={(e) => onEntity(Number(e.target.value))}>
            {entities.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
          </select>
        </Field>
      )}

      <Progress readiness={readiness} />

      <div className="flex gap-1.5">
        {[['workbook', 'Fill in a workbook'], ['tally', 'Connect Tally']].map(([v, l]) => (
          <button key={v} onClick={() => setTab(v)}
                  className={`rounded-lg px-3.5 py-2 text-[13px] font-medium transition
                    ${tab === v ? 'bg-navy-700 text-white'
                                : 'border border-line text-ink hover:bg-paper'}`}>
            {l}
          </button>
        ))}
      </div>

      {tab === 'workbook' && <Workbook entityId={entityId} onImported={load} />}
      {tab === 'tally' && <TallyPointer />}
    </div>
  )
}

function Progress({ readiness }) {
  return (
    <Card title="Where you are"
          sub={readiness?.headline || 'Checking what is already in place…'}>
      <div className="grid md:grid-cols-3 gap-3">
        {STAGES.map((s) => {
          const done = readiness?.[`stage${s.n}`]
          return (
            <div key={s.n}
                 className={`rounded-xl border p-3.5 ${done ? 'border-status-green/40 bg-status-green/5'
                                                            : 'border-line'}`}>
              <div className="flex items-center gap-2 mb-1.5">
                <span className={`w-4 h-4 rounded-full grid place-items-center text-[10px]
                                  font-semibold ${done ? 'bg-status-green text-white'
                                                       : 'bg-line text-ink-muted'}`}>
                  {done ? '✓' : s.n}
                </span>
                <span className="text-[13px] font-medium text-ink">{s.title}</span>
              </div>
              <p className="text-[12px] text-ink-muted leading-relaxed mb-2">{s.buys}</p>
              <p className="text-[11.5px] text-ink-muted">{s.needs.join(' · ')}</p>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

// ---------------------------------------------------------------------------
function Workbook({ entityId, onImported }) {
  const { notify } = useApp()
  const [report, setReport] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [replace, setReplace] = useState(false)

  async function download(which) {
    const path = which === 'example' ? '/api/onboarding/example' : '/api/onboarding/template'
    const name = which === 'example'
      ? 'Cash_Runway_Setup_EXAMPLE_Northwind.xlsx'
      : 'Cash_Runway_Setup_Template.xlsx'
    try { await api.download(path, name, {}) }
    catch (e) { notify(e.message, 'error') }
  }

  async function upload(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setBusy(true); setError(null); setReport(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      setReport(await api.form('/api/onboarding/validate', fd, { entity_id: entityId }))
    } catch (err) { setError(err.message) }
    setBusy(false)
  }

  async function commit() {
    setBusy(true)
    try {
      const r = await api.post(`/api/onboarding/commit/${report.batch_id}`,
                               { replace }, { entity_id: entityId })
      notify(r.message)
      setReport(null)
      onImported()
    } catch (err) { notify(err.message, 'error') }
    setBusy(false)
  }

  return (
    <div className="space-y-4">
      <Card title="The set-up workbook"
            sub="One file, one sheet per thing the tool needs. Fill in what you have — the sheets you leave blank simply keep those screens switched off.">
        <div className="flex flex-wrap gap-2.5">
          <button onClick={() => download('template')}
                  className="rounded-lg bg-navy-700 text-white px-3.5 py-2 text-[13px]
                             font-medium hover:bg-navy-800 inline-flex items-center gap-2">
            <Icon name="download" size={15} /> Blank template
          </button>
          <button onClick={() => download('example')}
                  className="rounded-lg border border-line px-3.5 py-2 text-[13px]
                             hover:bg-paper inline-flex items-center gap-2">
            <Icon name="file" size={15} /> Worked example
          </button>
          <label className="rounded-lg border border-line px-3.5 py-2 text-[13px]
                            hover:bg-paper inline-flex items-center gap-2 cursor-pointer">
            <Icon name="upload" size={15} /> {busy ? 'Reading…' : 'Upload a filled-in file'}
            <input type="file" accept=".xlsx,.xlsm" className="hidden" onChange={upload} />
          </label>
        </div>
        <p className="basis mt-3">
          The worked example is the same workbook filled in with the demonstration
          company's figures — useful for seeing the shape a completed sheet takes.
        </p>
      </Card>

      {error && <ErrorNote error={error} />}
      {report && <Report report={report} replace={replace} setReplace={setReplace}
                         onCommit={commit} busy={busy} />}
    </div>
  )
}

function Report({ report, onCommit, busy, replace, setReplace }) {
  const clean = report.rejected === 0
  return (
    <Card title="What is in that file"
          sub="Nothing has been saved yet. This is what would be."
          right={
            <span className={`text-[12px] font-medium px-2.5 py-1 rounded-full
                              ${clean ? 'bg-status-green/10 text-status-green'
                                      : 'bg-status-amber/10 text-status-amber'}`}>
              {report.accepted} ready · {report.rejected} rejected
            </span>
          }>
      <p className="text-[13px] text-ink mb-4">{report.verdict}</p>

      <Table className="mb-4">
        <thead>
          <tr><TH left>Sheet</TH><TH>Stage</TH><TH>Ready</TH><TH>Rejected</TH></tr>
        </thead>
        <tbody>
          {report.summary.map((s) => (
            <tr key={s.sheet} className={!s.present ? 'opacity-45' : ''}>
              <TD left>{s.sheet}</TD>
              <TD>{s.stage}</TD>
              <TD>{s.present ? s.accepted : '—'}</TD>
              <TD className={s.rejected ? 'text-status-red font-medium' : ''}>
                {s.present ? s.rejected : 'not in file'}
              </TD>
            </tr>
          ))}
        </tbody>
      </Table>

      {!!report.errors?.length && (
        <div className="mb-4">
          <h4 className="text-[13px] font-medium text-ink mb-2">
            Rejected rows — each with the reason
          </h4>
          <div className="max-h-72 overflow-y-auto rounded-xl border border-line">
            <Table>
              <thead>
                <tr><TH left>Sheet</TH><TH>Row</TH><TH left>What is wrong</TH></tr>
              </thead>
              <tbody>
                {report.errors.map((e, i) => (
                  <tr key={i}>
                    <TD left>{e.sheet}</TD>
                    <TD>{e.row ?? '—'}</TD>
                    <TD left className="text-status-red">{e.message}</TD>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
          {report.errors_truncated && (
            <p className="basis mt-2">Only the first 400 are listed.</p>
          )}
        </div>
      )}

      {!!report.warnings?.length && (
        <div className="mb-4 rounded-xl border border-status-amber/30 bg-status-amber/5 p-3.5">
          <h4 className="text-[13px] font-medium text-ink mb-2">Worth knowing</h4>
          <ul className="space-y-1.5">
            {report.warnings.map((w, i) => (
              <li key={i} className="text-[12.5px] text-ink leading-relaxed">• {w}</li>
            ))}
          </ul>
        </div>
      )}

      <label className="flex items-start gap-2.5 mb-4 text-[12.5px] text-ink cursor-pointer">
        <input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)}
               className="mt-0.5" />
        <span>
          Clear what is already in this entity first.
          <span className="basis block">
            Leave this off to add to what is there. Turn it on if you are re-uploading a
            corrected file — otherwise you will have both versions.
          </span>
        </span>
      </label>

      <button onClick={onCommit} disabled={busy || !report.accepted}
              className="rounded-lg bg-navy-700 text-white px-4 py-2.5 text-[13px]
                         font-medium hover:bg-navy-800 disabled:opacity-40">
        {busy ? 'Importing…' : `Import ${report.accepted} row(s)`}
      </button>
    </Card>
  )
}

function TallyPointer() {
  const nav = useNavigate()
  return (
    <Card title="Connect Tally instead"
          sub="If your books are in Tally Prime, the connector will bring ledgers, vouchers and outstanding bills across.">
      <p className="text-[13px] text-ink leading-relaxed mb-4">
        The connection itself takes a minute. What takes longer, and matters more, is
        confirming how each of your ledgers maps into the tool — every Tally company
        has its own chart of accounts, and a connector that guesses and moves on is how
        the numbers quietly go wrong. The wizard walks through it.
      </p>
      <button onClick={() => nav('/setup?layer=tally')}
              className="rounded-lg bg-navy-700 text-white px-4 py-2.5 text-[13px]
                         font-medium hover:bg-navy-800 inline-flex items-center gap-2">
        <Icon name="plug" size={15} /> Open the Tally wizard
      </button>
      <p className="basis mt-3">
        Tally cannot push data. A daily sync means this application polls Tally at a set
        time, which only happens if it is running then — the wizard says so too.
      </p>
    </Card>
  )
}
