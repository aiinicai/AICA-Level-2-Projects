// TAB 12 — Setup. Four layers, grouped away from the daily screens.
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp, useEndpoint } from '../lib/store'
import TallyWizard from './setup/TallyWizard'
import BoardVisibility from './setup/BoardVisibility'
import { api } from '../lib/api'
import { cls, d, inr, num, ts } from '../lib/format'
import {
  Card, Dot, Empty, ErrorNote, Field, Icon, Loading, Modal, StatusPill,
  Table, TD, TH, Toggle, Why,
} from '../components/ui'
import { Stat, StatRow } from '../components/Figure'

const LAYERS = [
  { value: 'sources', label: 'Data sources' },
  { value: 'tally', label: 'Tally' },
  { value: 'import', label: 'Import data' },
  { value: 'plan', label: 'Upload plan' },
  { value: 'rules', label: 'Alert rules' },
  { value: 'board', label: 'Board visibility' },
  { value: 'people', label: 'People & definitions' },
]

export default function Setup() {
  const params = new URLSearchParams(window.location.search)
  const [layer, setLayer] = useState(params.get('layer') || 'sources')
  return (
    <div className="space-y-5">
      <Toggle options={LAYERS} value={layer} onChange={setLayer} size="md" />
      {layer === 'sources' && <Sources />}
      {layer === 'tally' && <TallyWizard />}
      {layer === 'import' && <ImportData />}
      {layer === 'plan' && <PlanUpload />}
      {layer === 'rules' && <Rules />}
      {layer === 'board' && <BoardVisibility />}
      {layer === 'people' && <People />}
    </div>
  )
}

// The set-up workbook is reachable after onboarding too — data arrives in
// batches, not once.
function ImportData() {
  const nav = useNavigate()
  const readiness = useEndpoint('/api/onboarding/readiness')
  return (
    <div className="space-y-5">
      <Card title="Bring in more data"
            sub={readiness.data?.headline || 'Checking what is in place…'}>
        <p className="text-[13px] text-ink leading-relaxed mb-4">
          The set-up workbook is not a one-time thing. Download it, fill in whichever
          sheets have new figures, and upload — every row is checked before anything is
          saved, and you choose whether it adds to what is there or replaces it.
        </p>
        <button onClick={() => nav('/set-up')}
                className="rounded-lg bg-navy-700 text-white px-4 py-2.5 text-[13px]
                           font-medium hover:bg-navy-800 inline-flex items-center gap-2">
          <Icon name="upload" size={15} /> Open the import screen
        </button>
      </Card>

      <StartAgain />

      {readiness.data && (
        <Card title="What each screen still needs"
              sub="A screen without its data says so, rather than showing a confident zero.">
          {!Object.keys(readiness.data.tabs_needing_data || {}).length
            ? <Empty>Every screen has what it needs.</Empty>
            : (
              <Table>
                <thead><tr><TH left>Screen</TH><TH left>Waiting on</TH></tr></thead>
                <tbody>
                  {Object.entries(readiness.data.tabs_needing_data).map(([tab, needs]) => (
                    <tr key={tab}>
                      <TD left className="font-medium">{tab}</TD>
                      <TD left className="text-ink-muted">{needs.join(' ')}</TD>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
        </Card>
      )}
    </div>
  )
}

// Clearing everything is what makes the first-run screen demonstrable more than
// once — and what lets someone who loaded the demo to look around start their
// own set-up without hunting for a database file.
function StartAgain() {
  const { canApprove, notify } = useApp()
  const [open, setOpen] = useState(false)
  const [phrase, setPhrase] = useState('')
  const [busy, setBusy] = useState(false)

  if (!canApprove) return null

  async function go() {
    setBusy(true)
    try {
      const r = await api.post('/api/onboarding/reset', { confirm: phrase }, {})
      notify(r.message)
      setTimeout(() => { window.location.href = '/welcome' }, 700)
    } catch (e) { notify(e.message, 'error'); setBusy(false) }
  }

  return (
    <>
      <Card title="Start again"
            sub="Clears every figure and returns to the first-run screen.">
        <p className="text-[13px] text-ink leading-relaxed mb-4">
          Sign-in accounts, definitions and alert rules are kept — this puts the
          application back where a fresh install starts, not somewhere unusable.
          Useful if you loaded the demonstration company to look around and now
          want to set up your own.
        </p>
        <button onClick={() => { setPhrase(''); setOpen(true) }}
                className="rounded-lg border border-status-red/40 text-status-red px-4
                           py-2 text-[13px] font-medium hover:bg-status-red/5">
          Clear everything and start again
        </button>
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="Clear everything?"
             sub="This cannot be undone from inside the application.">
        <p className="text-[13px] text-ink leading-relaxed mb-4">
          Every entity, balance, invoice, bill, plan, alert and board pack will be
          deleted. To confirm, type <strong>start again</strong> below.
        </p>
        <input className="input" value={phrase} onChange={(e) => setPhrase(e.target.value)}
               placeholder="start again" autoFocus />
        <div className="flex gap-2 mt-4">
          <button onClick={go} disabled={busy || phrase.trim().toLowerCase() !== 'start again'}
                  className="rounded-lg bg-status-red text-white px-4 py-2 text-[13px]
                             font-medium disabled:opacity-40">
            {busy ? 'Clearing…' : 'Clear everything'}
          </button>
          <button onClick={() => setOpen(false)}
                  className="rounded-lg border border-line px-4 py-2 text-[13px] hover:bg-paper">
            Cancel
          </button>
        </div>
      </Modal>
    </>
  )
}

// ===========================================================================
// 12A — Data sources
// ===========================================================================
function Sources() {
  const { canWrite, notify, refresh } = useApp()
  const { data, loading, error, reload } = useEndpoint('/api/setup/data-sources')
  const manual = useEndpoint('/api/manual-entries')
  const [ping, setPing] = useState(null)
  const [busy, setBusy] = useState(false)

  if (loading && !data) return <Loading rows={3} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data) return null

  async function testConnection() {
    setBusy(true)
    try { setPing(await api.get('/api/setup/tally/ping', {}, { scoped: false })) }
    catch (e) { setPing({ connected: false, message: e.message }) }
    setBusy(false)
  }

  async function sync() {
    setBusy(true)
    try {
      const r = await api.post('/api/setup/tally/sync', {})
      notify(`Sync ${r.status} — ${r.records} record(s).`)
      reload(); refresh()
    } catch (e) { notify(e.message, 'error') }
    setBusy(false)
  }

  return (
    <div className="space-y-5">
      <Card title="Accounting connection"
            sub="Tally Prime over its local XML endpoint. No credentials leave your network."
            right={canWrite && (
              <div className="flex gap-2">
                <button className="btn-ghost btn-sm" disabled={busy} onClick={testConnection}>
                  Test connection
                </button>
                <button className="btn-primary btn-sm" disabled={busy} onClick={sync}>
                  <Icon name="refresh" size={13} /> Sync now
                </button>
              </div>)}>
        <StatRow cols={4}>
          <Stat label="Connector" value={data.connector.name}
                sub={data.connector.company || 'No company configured'} />
          <Stat label="Endpoint" value={data.connector.url} size="sm" />
          <Stat label="Last successful sync"
                value={data.last_success ? ts(data.last_success.at) : 'Never'} size="sm"
                sub={data.last_success ? `${data.last_success.records} records` : null}
                status={data.last_success ? 'Green' : 'Red'} />
          <Stat label="Schedule" value={data.schedule} size="sm" />
        </StatRow>

        {ping && (
          <div className={cls('mt-4 rounded-lg border px-4 py-3 flex items-start gap-2.5',
            ping.connected ? 'border-green-line bg-green-bg' : 'border-red-line bg-red-bg')}>
            <Icon name={ping.connected ? 'check' : 'alert'} size={15}
                  className={cls('mt-0.5', ping.connected ? 'text-green' : 'text-red')} />
            <p className={cls('text-[13px]', ping.connected ? 'text-green' : 'text-red')}>
              {ping.message}
            </p>
          </div>
        )}

        <div className="mt-5 pt-4 border-t border-line-soft">
          <span className="label block mb-2">Other accounting systems</span>
          <div className="flex flex-wrap gap-2">
            {data.roadmap.map((r) => (
              <span key={r.name} className="chip bg-grey-bg border-grey-line text-grey">
                {r.name} — {r.status}
              </span>
            ))}
          </div>
          <p className="basis mt-2">
            The internal schema is source-agnostic, so adding one of these means writing an
            adapter, not changing any screen.
          </p>
        </div>
      </Card>

      <Card title="Sync history" sub="Including the failures — a connector that quietly stops is the worst data problem"
            pad={false}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Started</TH><TH left>Source</TH><TH left>Status</TH>
            <TH>Records</TH><TH left>Message</TH><TH left>Triggered by</TH>
          </tr></thead>
          <tbody>
            {data.history.map((r) => (
              <tr key={r.id} className="tr-hover">
                <TD left>{ts(r.started_at)}</TD>
                <TD left className="capitalize">{r.source}</TD>
                <TD left>
                  <StatusPill status={r.status === 'success' ? 'Green'
                                    : r.status === 'partial' ? 'Amber' : 'Red'}
                              label={r.status} />
                </TD>
                <TD>{r.records.toLocaleString('en-IN')}</TD>
                <TD left className="text-ink-muted max-w-[440px] whitespace-normal text-2xs">
                  {r.message || '—'}
                </TD>
                <TD left>{r.triggered_by}</TD>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card title="Bank statements" pad={false}
            sub="Uploading a statement is what makes the books-vs-bank check meaningful">
        {data.bank_statements.length === 0 ? (
          <Empty>No statement uploaded. The bank position is the balance recorded manually.</Empty>
        ) : (
          <Table className="px-4 pb-1">
            <thead><tr>
              <TH left>File</TH><TH>As on</TH><TH>Closing balance</TH>
              <TH>Rows accepted</TH><TH>Rejected</TH><TH left>Uploaded by</TH><TH>Uploaded</TH>
            </tr></thead>
            <tbody>
              {data.bank_statements.map((s) => (
                <tr key={s.id} className="tr-hover">
                  <TD left className="!text-ink font-medium">{s.filename}</TD>
                  <TD>{d(s.as_on)}</TD><TD>{inr(s.closing_balance)}</TD>
                  <TD>{s.rows_accepted}</TD><TD>{s.rows_rejected}</TD>
                  <TD left>{s.uploaded_by}</TD><TD>{ts(s.uploaded_at)}</TD>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {/* Manual entries register */}
      <Card title="Manual entries register"
            sub="Everything not in the books — who added it, and when"
            basis={manual.data?.basis} pad={false}>
        {manual.loading ? <div className="px-5 pb-4"><Loading rows={2} /></div>
         : manual.error ? <div className="px-5 pb-4"><ErrorNote error={manual.error} /></div>
         : (
          <Table className="px-4 pb-1">
            <thead><tr>
              <TH left>Kind</TH><TH left>Item</TH><TH>Amount</TH><TH>Effective</TH>
              <TH left>Source</TH><TH left>Added by</TH><TH>Last updated</TH>
            </tr></thead>
            <tbody>
              {manual.data.rows.slice(0, 40).map((r, i) => (
                <tr key={`${r.kind}-${r.id}-${i}`} className="tr-hover">
                  <TD left><span className="chip bg-navy-50 border-navy-200 text-navy-700">{r.kind}</span></TD>
                  <TD left className="!text-ink max-w-[380px] whitespace-normal">{r.label}</TD>
                  <TD>{inr(r.amount)}</TD>
                  <TD>{d(r.effective_date)}</TD>
                  <TD left className="capitalize text-ink-muted">{r.source}</TD>
                  <TD left>{r.created_by || '—'}</TD>
                  <TD>{ts(r.updated_at || r.created_at)}</TD>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </div>
  )
}

// ===========================================================================
// 12B — Upload plan
// ===========================================================================
function PlanUpload() {
  const { canWrite, notify } = useApp()
  const [file, setFile] = useState(null)
  const [report, setReport] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [meta, setMeta] = useState({ name: '', version: '', note: '', make_active: true })

  async function validate(f, mapping) {
    setBusy(true); setErr(null)
    const fd = new FormData()
    fd.append('file', f)
    if (mapping) fd.append('mapping', JSON.stringify(mapping))
    try { setReport(await api.form('/api/setup/plan/validate', fd)) }
    catch (e) { setErr(e.message) }
    setBusy(false)
  }

  function onPick(e) {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f); setReport(null)
    setMeta((m) => ({ ...m, name: m.name || f.name.replace(/\.(xlsx|csv)$/i, '') }))
    validate(f)
  }

  async function save() {
    if (!meta.name || !meta.version) { setErr('A name and a version number are both required.'); return }
    setBusy(true); setErr(null)
    const fd = new FormData()
    fd.append('file', file)
    fd.append('name', meta.name)
    fd.append('version', meta.version)
    if (meta.note) fd.append('note', meta.note)
    fd.append('mapping', JSON.stringify(report.mapping))
    fd.append('make_active', String(meta.make_active))
    try {
      await api.form('/api/setup/plan/save', fd)
      notify('Plan saved as a new version.')
      setFile(null); setReport(null); setMeta({ name: '', version: '', note: '', make_active: true })
    } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  return (
    <div className="space-y-5">
      <Card title="Upload a plan"
            sub="Nothing is saved until the file passes validation. Versions are never overwritten."
            right={
              <button className="btn-ghost btn-sm"
                      onClick={() => api.download('/api/setup/plan/template', 'Cash_Runway_Plan_Template.xlsx')}>
                <Icon name="download" size={13} /> Download template
              </button>}>
        <label className={cls('block rounded-xl border-2 border-dashed px-6 py-10 text-center cursor-pointer transition-colors',
          file ? 'border-navy-300 bg-navy-50/50' : 'border-line-strong hover:border-navy-300 hover:bg-navy-50/30')}>
          <input type="file" accept=".xlsx,.csv" className="hidden" onChange={onPick} disabled={!canWrite} />
          <Icon name="upload" size={22} className="mx-auto text-ink-muted mb-2" />
          <p className="text-[14px] font-medium text-ink">
            {file ? file.name : 'Drop a plan file here, or click to browse'}
          </p>
          <p className="text-2xs text-ink-muted mt-1">.xlsx or .csv · one row per month</p>
        </label>
        {err && <p className="text-[13px] text-red mt-3">{err}</p>}
        {busy && <div className="mt-4"><Loading label="Validating the file…" rows={2} /></div>}
      </Card>

      {report && (
        <>
          <Card title="Validation report" sub={report.summary}
                right={report.can_save
                  ? <StatusPill status="Green" label="Ready to save" />
                  : <StatusPill status="Red" label="Cannot save" />}>
            <StatRow cols={4}>
              <Stat label="Rows accepted" value={report.accepted} size="lg" status="Green" />
              <Stat label="Rows rejected" value={report.rejected.length} size="lg"
                    status={report.rejected.length ? 'Red' : 'Green'} />
              <Stat label="Period continuity" size="lg"
                    value={report.continuity.ok ? 'Continuous' : 'Broken'}
                    status={report.continuity.ok ? 'Green' : 'Red'}
                    sub={report.continuity.gaps.join(', ') || null} />
              <Stat label="Closing cash tie-in" size="lg"
                    value={report.totals_check.ok ? 'Ties' : `${report.totals_check.mismatches.length} mismatch`}
                    status={report.totals_check.ok ? 'Green' : 'Amber'} />
            </StatRow>

            <div className="mt-5 pt-4 border-t border-line-soft grid sm:grid-cols-2 gap-4 text-2xs">
              <div>
                <span className="label block mb-1">Opening cash used</span>
                <span className="text-[14px] font-semibold tnum">{inr(report.opening_cash)}</span>
                <span className="block text-ink-muted mt-0.5">{report.opening_cash_source}</span>
              </div>
              <div>
                <span className="label block mb-1">Period</span>
                <span className="text-[14px] font-semibold">
                  {d(report.period_from)} to {d(report.period_to)}
                </span>
              </div>
            </div>

            {report.rejected.length > 0 && (
              <div className="mt-4">
                <span className="label block mb-2">Rejected rows, with the reason</span>
                <div className="space-y-1">
                  {report.rejected.slice(0, 8).map((r, i) => (
                    <p key={i} className="text-2xs text-red">
                      Row {r.row}: {r.reason}{r.value ? ` — "${r.value}"` : ''}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {report.totals_check.mismatches.length > 0 && (
              <div className="mt-4">
                <span className="label block mb-2">Where the stated closing cash does not tie</span>
                <Table>
                  <thead><tr>
                    <TH left>Month</TH><TH>Stated</TH><TH>Derived</TH><TH>Difference</TH>
                  </tr></thead>
                  <tbody>
                    {report.totals_check.mismatches.map((m) => (
                      <tr key={m.month}>
                        <TD left>{m.month}</TD><TD>{inr(m.stated_closing)}</TD>
                        <TD>{inr(m.derived_closing)}</TD>
                        <TD className="!text-amber font-semibold">{inr(m.difference, { sign: true })}</TD>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            )}

            {(report.unknown_columns.length > 0 || report.missing_categories.length > 0) && (
              <p className="basis mt-4">
                {report.unknown_columns.length > 0 &&
                  `Ignored columns: ${report.unknown_columns.join(', ')}. `}
                {report.missing_categories.length > 0 &&
                  `Treated as nil: ${report.missing_categories.join(', ')}.`}
              </p>
            )}
          </Card>

          {report.diff && (
            <Card title="Preview — how this differs from the active plan"
                  sub={report.diff.note} pad={false}>
              <Table className="px-4 pb-1">
                <thead><tr>
                  <TH left>Month</TH><TH>Inflow now</TH><TH>Inflow new</TH><TH>Δ</TH>
                  <TH>Outflow now</TH><TH>Outflow new</TH><TH>Δ</TH><TH>Closing new</TH>
                </tr></thead>
                <tbody>
                  {report.diff.rows.map((r) => (
                    <tr key={r.month} className="tr-hover">
                      <TD left className="!text-ink font-medium">{r.label}</TD>
                      <TD>{r.old_inflow !== null ? inr(r.old_inflow) : '—'}</TD>
                      <TD>{inr(r.new_inflow)}</TD>
                      <TD className={cls(r.inflow_delta < 0 ? '!text-amber' : r.inflow_delta > 0 ? '!text-green' : '')}>
                        {r.inflow_delta !== null ? inr(r.inflow_delta, { sign: true }) : '—'}
                      </TD>
                      <TD>{r.old_outflow !== null ? inr(r.old_outflow) : '—'}</TD>
                      <TD>{inr(r.new_outflow)}</TD>
                      <TD className={cls(r.outflow_delta > 0 ? '!text-amber' : r.outflow_delta < 0 ? '!text-green' : '')}>
                        {r.outflow_delta !== null ? inr(r.outflow_delta, { sign: true }) : '—'}
                      </TD>
                      <TD className="font-semibold !text-ink">{inr(r.new_closing)}</TD>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card>
          )}

          {report.can_save && canWrite && (
            <Card title="Save as a new version">
              <div className="grid sm:grid-cols-3 gap-4">
                <Field label="Plan name">
                  <input className="input" value={meta.name}
                         onChange={(e) => setMeta({ ...meta, name: e.target.value })} />
                </Field>
                <Field label="Version" hint="Must be new — versions are never overwritten.">
                  <input className="input" value={meta.version} placeholder="v3.0"
                         onChange={(e) => setMeta({ ...meta, version: e.target.value })} />
                </Field>
                <Field label="Make this the active plan">
                  <select className="input" value={String(meta.make_active)}
                          onChange={(e) => setMeta({ ...meta, make_active: e.target.value === 'true' })}>
                    <option value="true">Yes — measure against this from now on</option>
                    <option value="false">No — keep the current active plan</option>
                  </select>
                </Field>
              </div>
              <Field label="Note" className="mt-4"
                     hint="Why this version exists. It appears in plan history.">
                <textarea rows={2} className="input" value={meta.note}
                          onChange={(e) => setMeta({ ...meta, note: e.target.value })} />
              </Field>
              <button className="btn-primary mt-4" disabled={busy} onClick={save}>
                {busy ? 'Saving…' : 'Save plan version'}
              </button>
            </Card>
          )}
        </>
      )}
    </div>
  )
}

// ===========================================================================
// 12C — Alert rules
// ===========================================================================
function Rules() {
  const { canWrite, notify } = useApp()
  const { data, loading, error, reload } = useEndpoint('/api/alerts/rules')
  const [edit, setEdit] = useState(null)
  const [test, setTest] = useState(false)

  if (loading && !data) return <Loading rows={4} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data) return null

  return (
    <div className="space-y-5">
      <Card title="Alert rules" pad={false}
            sub="Ten rules. Each one fires against the same calculation engine the screens use."
            right={canWrite && (
              <button className="btn-ghost btn-sm" onClick={() => setTest(true)}>
                Send a test message
              </button>)}>
        <Table className="px-4 pb-1">
          <thead><tr>
            <TH left>Rule</TH><TH left>On</TH><TH>Threshold</TH><TH left>Severity</TH>
            <TH left>Channel</TH><TH>Cooldown</TH><TH left>Quiet hours</TH>
            <TH left>Recipients</TH><TH>Escalate after</TH><TH left>Last fired</TH>
            {canWrite && <TH left />}
          </tr></thead>
          <tbody>
            {data.rows.map((r) => (
              <tr key={r.id} className={cls('tr-hover', !r.enabled && 'opacity-50')}>
                <TD left className="!text-ink font-medium max-w-[240px] whitespace-normal">
                  <span className="flex items-start gap-1.5">
                    {r.name}<Why>{r.description}</Why>
                  </span>
                </TD>
                <TD left>
                  <StatusPill status={r.enabled ? 'Green' : 'Grey'} label={r.enabled ? 'On' : 'Off'} />
                </TD>
                <TD className="font-semibold !text-ink">
                  {r.threshold_unit === 'inr' ? inr(r.threshold)
                    : r.threshold_unit === 'pct' ? `${num(r.threshold, 0)}%`
                    : `${num(r.threshold, 0)} ${r.threshold_unit}`}
                </TD>
                <TD left><StatusPill status={r.severity} /></TD>
                <TD left className="text-2xs capitalize">{r.channels.join(', ')}</TD>
                <TD>{r.cooldown_hours}h</TD>
                <TD left className="text-2xs tnum">
                  {String(r.quiet_hours_start).padStart(2, '0')}:00–
                  {String(r.quiet_hours_end).padStart(2, '0')}:00
                </TD>
                <TD left className="text-2xs text-ink-muted max-w-[180px] truncate"
                    title={r.recipients}>{r.recipients}</TD>
                <TD>{r.escalate_after_hours ? `${r.escalate_after_hours}h` : '—'}</TD>
                <TD left className="text-2xs">
                  {r.last_fired_at ? ts(r.last_fired_at) : 'Never'}
                  {r.in_cooldown && <span className="block text-ink-faint">in cooldown</span>}
                </TD>
                {canWrite && (
                  <TD left><button className="text-2xs linkish" onClick={() => setEdit(r)}>Edit</button></TD>
                )}
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <RuleModal rule={edit} channels={data.channels} severities={data.severities}
                 onClose={() => setEdit(null)}
                 onDone={() => { setEdit(null); reload(); notify('Rule updated.') }} />
      <TestModal open={test} onClose={() => setTest(false)} notify={notify} />
    </div>
  )
}

function RuleModal({ rule, channels, severities, onClose, onDone }) {
  const [f, setF] = useState({})
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  React.useEffect(() => {
    if (rule) setF({
      enabled: rule.enabled, threshold: rule.threshold, severity: rule.severity,
      channels: rule.channels.join(','), cooldown_hours: rule.cooldown_hours,
      quiet_hours_start: rule.quiet_hours_start, quiet_hours_end: rule.quiet_hours_end,
      recipients: rule.recipients, escalate_after_hours: rule.escalate_after_hours,
    })
  }, [rule])
  if (!rule) return null

  async function save() {
    setBusy(true); setErr(null)
    try {
      await api.patch(`/api/alerts/rules/${rule.id}`, {
        ...f, threshold: Number(f.threshold),
        cooldown_hours: Number(f.cooldown_hours),
        quiet_hours_start: Number(f.quiet_hours_start),
        quiet_hours_end: Number(f.quiet_hours_end),
        escalate_after_hours: Number(f.escalate_after_hours),
      })
      onDone()
    } catch (e) { setErr(e.message); setBusy(false) }
  }
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  return (
    <Modal open onClose={onClose} width="max-w-xl" title={rule.name} sub={rule.description}
           footer={<>
             <button className="btn-ghost" onClick={onClose}>Cancel</button>
             <button className="btn-primary" disabled={busy} onClick={save}>
               {busy ? 'Saving…' : 'Save rule'}
             </button>
           </>}>
      <div className="grid grid-cols-2 gap-4">
        <Field label="On / off">
          <select className="input" value={String(f.enabled)}
                  onChange={(e) => setF({ ...f, enabled: e.target.value === 'true' })}>
            <option value="true">On</option><option value="false">Off</option>
          </select>
        </Field>
        <Field label={`Threshold (${rule.threshold_unit})`}>
          <input type="number" className="input tnum" value={f.threshold} onChange={set('threshold')} />
        </Field>
        <Field label="Severity">
          <select className="input" value={f.severity} onChange={set('severity')}>
            {severities.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="Channels">
          <select className="input" value={f.channels} onChange={set('channels')}>
            <option value="sms">SMS</option>
            <option value="email">Email</option>
            <option value="sms,email">SMS and email</option>
          </select>
        </Field>
        <Field label="Cooldown (hours)" hint="How long before this rule may fire again.">
          <input type="number" className="input tnum" value={f.cooldown_hours}
                 onChange={set('cooldown_hours')} />
        </Field>
        <Field label="Escalate after (hours)" hint="0 means never escalate.">
          <input type="number" className="input tnum" value={f.escalate_after_hours}
                 onChange={set('escalate_after_hours')} />
        </Field>
        <Field label="Quiet hours from (IST)">
          <input type="number" min={0} max={23} className="input tnum"
                 value={f.quiet_hours_start} onChange={set('quiet_hours_start')} />
        </Field>
        <Field label="Quiet hours to (IST)">
          <input type="number" min={0} max={23} className="input tnum"
                 value={f.quiet_hours_end} onChange={set('quiet_hours_end')} />
        </Field>
      </div>
      <Field label="Recipients" className="mt-4"
             hint="Comma-separated phone numbers in E.164 form, or email addresses.">
        <input className="input" value={f.recipients} onChange={set('recipients')} />
      </Field>
      <p className="basis mt-3">
        An alert raised during quiet hours is still recorded — only the message is held back.
      </p>
      {err && <p className="text-[13px] text-red mt-3">{err}</p>}
    </Modal>
  )
}

function TestModal({ open, onClose, notify }) {
  const [to, setTo] = useState('')
  const [channel, setChannel] = useState('sms')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  if (!open) return null

  async function send() {
    setBusy(true); setResult(null)
    try { setResult(await api.post('/api/alerts/rules/test', { to, channel })) }
    catch (e) { setResult({ delivered: false, error: e.message }) }
    setBusy(false)
  }

  return (
    <Modal open onClose={onClose} title="Send a test message"
           sub="Prove delivery works before relying on it."
           footer={<>
             <button className="btn-ghost" onClick={onClose}>Close</button>
             <button className="btn-primary" disabled={busy || !to} onClick={send}>
               {busy ? 'Sending…' : 'Send test'}
             </button>
           </>}>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Channel">
          <select className="input" value={channel} onChange={(e) => setChannel(e.target.value)}>
            <option value="sms">SMS</option><option value="email">Email</option>
          </select>
        </Field>
        <Field label={channel === 'sms' ? 'Phone (E.164)' : 'Email'}>
          <input className="input" value={to} onChange={(e) => setTo(e.target.value)}
                 placeholder={channel === 'sms' ? '+919900112233' : 'you@company.in'} />
        </Field>
      </div>
      {result && (
        <div className={cls('mt-4 rounded-lg border px-4 py-3',
          result.delivered ? 'border-green-line bg-green-bg' : 'border-red-line bg-red-bg')}>
          <p className={cls('text-[13px] font-medium', result.delivered ? 'text-green' : 'text-red')}>
            {result.delivered
              ? `Accepted by ${result.transport}${result.segments ? ` — ${result.characters} characters, ${result.segments} SMS segment(s)` : ''}.`
              : `Not delivered: ${result.error}`}
          </p>
        </div>
      )}
      <p className="basis mt-3">
        SMS goes through Twilio. Set CR_TWILIO_ACCOUNT_SID, CR_TWILIO_AUTH_TOKEN and
        CR_TWILIO_FROM to enable it, or CR_ALERT_CHANNEL=console to print messages to
        the server log instead. Accepted means Twilio took the message, not that a
        handset showed it — delivery is asynchronous.
      </p>
    </Modal>
  )
}

// ===========================================================================
// 12D — People & definitions
// ===========================================================================
function People() {
  const { canApprove } = useApp()
  const users = useEndpoint('/api/setup/users')
  const defs = useEndpoint('/api/definitions')
  const activity = useEndpoint('/api/activity', { limit: 60 })
  const settings = useEndpoint('/api/setup/settings')

  return (
    <div className="space-y-5">
      <Card title="Users" pad={false}
            sub="Role decides what a person can change. Board access is read-only, always.">
        {users.loading ? <div className="px-5 pb-4"><Loading rows={2} /></div> : (
          <>
            <Table className="px-4 pb-1">
              <thead><tr>
                <TH left>Name</TH><TH left>Email</TH><TH left>Role</TH><TH left>Access</TH>
                <TH left>Phone</TH><TH>Last login</TH>
              </tr></thead>
              <tbody>
                {users.data?.rows.map((u) => (
                  <tr key={u.id} className={cls('tr-hover', !u.is_active && 'opacity-50')}>
                    <TD left className="!text-ink font-medium">{u.name}</TD>
                    <TD left>{u.email}</TD>
                    <TD left><StatusPill status="Grey" label={u.role} /></TD>
                    <TD left className="text-2xs text-ink-muted">
                      {u.can_approve ? 'Can approve plans' : u.can_write ? 'Can edit' : 'Read-only'}
                    </TD>
                    <TD left className="tnum">{u.phone || '—'}</TD>
                    <TD>{u.last_login ? ts(u.last_login) : 'Never'}</TD>
                  </tr>
                ))}
              </tbody>
            </Table>
            <div className="px-5 py-3 border-t border-line-soft grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {Object.entries(users.data?.role_notes || {}).map(([role, note]) => (
                <div key={role}>
                  <p className="text-2xs font-semibold text-ink-soft">{role}</p>
                  <p className="text-2xs text-ink-muted mt-0.5 leading-relaxed">{note}</p>
                </div>
              ))}
            </div>
          </>
        )}
      </Card>

      <Card title="Thresholds and settings" pad={false}
            sub="Changing one of these is recorded against your name">
        {settings.loading ? <div className="px-5 pb-4"><Loading rows={2} /></div> : (
          <Table className="px-4 pb-1">
            <thead><tr>
              <TH left>Setting</TH><TH left>Value</TH><TH left>Last changed by</TH><TH>When</TH>
            </tr></thead>
            <tbody>
              {settings.data?.rows.map((s) => (
                <tr key={s.id} className="tr-hover">
                  <TD left className="!text-ink font-medium">{s.label || s.key}</TD>
                  <TD left className="tnum">
                    {s.key.includes('floor') || s.key.includes('amber') || s.key.includes('red')
                      ? inr(Number(s.value)) : s.value}
                  </TD>
                  <TD left>{s.updated_by || '—'}</TD>
                  <TD>{ts(s.updated_at)}</TD>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Card title="Definitions"
            sub="Every argument about a number traces back to here, so it is written down and visible"
            pad={false}>
        {defs.loading ? <div className="px-5 pb-4"><Loading rows={3} /></div> : (
          <div className="px-5 pb-5 space-y-3">
            {Object.entries((defs.data || []).reduce((acc, x) => {
              (acc[x.category] ||= []).push(x); return acc
            }, {})).map(([cat, items]) => (
              <div key={cat}>
                <p className="label mb-2">{cat}</p>
                <div className="grid lg:grid-cols-2 gap-2.5">
                  {items.map((x) => (
                    <div key={x.id} className="rounded-lg border border-line px-3.5 py-3">
                      <p className="text-[13px] font-semibold text-ink">{x.term}</p>
                      <p className="text-[13px] text-ink-soft mt-1 leading-relaxed">{x.plain_english}</p>
                      {x.formula && (
                        <p className="text-2xs text-ink-muted mt-2 font-medium">{x.formula}</p>
                      )}
                      {x.basis_note && (
                        <p className="text-2xs text-ink-faint mt-1 leading-relaxed">{x.basis_note}</p>
                      )}
                      <p className="text-[10px] text-ink-faint mt-2">
                        Last updated by {x.updated_by || '—'} on {d(x.updated_at)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Activity log" pad={false}
            sub="Who changed a threshold, uploaded a plan, reclassified a one-off, or exported a pack">
        {activity.loading ? <div className="px-5 pb-4"><Loading rows={3} /></div> : (
          <Table className="px-4 pb-1">
            <thead><tr>
              <TH left>When</TH><TH left>Who</TH><TH left>Action</TH>
              <TH left>Object</TH><TH left>What changed</TH>
            </tr></thead>
            <tbody>
              {(activity.data || []).map((a) => (
                <tr key={a.id} className="tr-hover">
                  <TD left>{ts(a.at)}</TD>
                  <TD left className="!text-ink font-medium">{a.user || 'System'}</TD>
                  <TD left className="capitalize">{a.action}</TD>
                  <TD left className="text-ink-muted">{a.object_type}</TD>
                  <TD left className="max-w-[560px] whitespace-normal">{a.summary}</TD>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </div>
  )
}
