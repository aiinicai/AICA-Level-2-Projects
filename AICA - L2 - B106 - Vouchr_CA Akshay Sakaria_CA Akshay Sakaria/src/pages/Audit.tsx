// Super-admin panel: is the platform working, what failed, who changed what, what do the APIs cost.
import { useState } from 'react';
import { useTr } from '../i18n';
import { useStore } from '../data/store';
import { fmtDate, fmtDateTime } from '../lib/dates';
import { Empty, PageHead } from '../ui/common';

// Audit trail: the action name is translated; the detail stays exactly as recorded (names, amounts, references).
const ACTION_LABEL: Record<string, string> = {
  INSERT: 'Added', UPDATE: 'Changed', VOID: 'Cancelled', LOGIN: 'Signed in', IMPORT: 'Imported', BULK_UPLOAD: 'Bulk upload', APPLY_ADVANCE: 'Advance applied',
  POSTED_TO_TALLY: 'Posted to Tally', AI_SCAN: 'AI scan', CONSENT: 'Consent given', WITHDRAW: 'Consent withdrawn', AI_OFF: 'AI switched off',
  CLIENT_TERMS: 'Company terms recorded', RESOLVE: 'Request resolved', LOCK: 'Month locked', UNLOCK: 'Month unlocked', SUBMIT_DRAFT: 'Draft submitted',
  RESUBMIT: 'Resubmitted', APPROVED: 'Approved', REJECTED: 'Returned', ACTIVATE: 'User activated', DEACTIVATE: 'User deactivated',
  WHATSAPP_SET: 'WhatsApp number set', WHATSAPP_REMOVE: 'WhatsApp number removed', WHATSAPP_CODE: 'WhatsApp code issued',
  WHATSAPP_CONFIRM: 'WhatsApp number confirmed', WHATSAPP_CODE_FAIL: 'WhatsApp code failed',
  CREDIT_NOTE: 'Credit note recorded', DEBIT_NOTE: 'Debit note recorded', NOTE_LINKED: 'Note linked to a bill', ITC_REVERSED: 'ITC reversal recorded',
  ITC_RECLAIMED: 'ITC re-claim recorded', AUTO_APPROVED: 'Auto-approved', FY_CLOSED: 'Financial year closed'
};
const FLAG_LABEL: Record<string, string> = {
  payment_voided: 'Payment cancelled', backdated_expense: 'Backdated bill', no_bill_image: 'No bill image', payment_moved_to_advance: 'Moved to advance',
  cash_limit: 'Cash above daily limit', paid_before_bill_date: 'Paid before bill date', backdated_payment: 'Backdated', adv_tds_section_differs: 'Advance TDS section differs from the bill — CA to check', auto_approved: 'Auto-approved'
};
const COMPONENTS = ['client_app', 'ocr', 'drive_upload', 'sheets_sync', 'gsp_fetch', 'tally_export', 'email', 'push', 'compliance_watch'];
const LABEL: Record<string, string> = {
  client_app: 'App (devices)', ocr: 'OCR', drive_upload: 'Drive uploads', sheets_sync: 'Sheets mirror', gsp_fetch: 'GSP 2A/2B fetch',
  tally_export: 'Tally export', email: 'Email', push: 'Push', compliance_watch: 'Compliance watch'
};
const time = fmtDateTime;

export function Audit() {
  const tr = useTr();
  const { s, resetDemo } = useStore();
  const [tab, setTab] = useState<'health' | 'errors' | 'audit' | 'apis'>('health');
  const [lvl, setLvl] = useState<'all' | 'error' | 'warn'>('all');
  const clientName = (id?: string) => s.clients.find((c) => c.id === id)?.name ?? 'Platform';
  const userName = (id: string) => s.users.find((u) => u.id === id)?.name ?? id;

  const health = COMPONENTS.map((c) => {
    const ev = s.events.filter((e) => e.component === c);
    const worst = ev.some((e) => e.level === 'error') ? 'error' : ev.some((e) => e.level === 'warn') ? 'warn' : 'ok';
    return { c, worst, last: ev[0] };
  });
  const flagged = s.audit.filter((a) => a.flag);

  return (
    <div className="content stack">
      <PageHead title={tr('Audit & health')} sub={tr('Platform monitoring for the CA firm')}>
        <button className="btn sm ghost" onClick={resetDemo}>{tr('Reset demo data')}</button>
      </PageHead>
      <div className="tabs">
        {([['health', tr('System health')], ['errors', `${tr('Errors & warnings')} (${s.events.filter((e) => e.level !== 'info').length})`], ['audit', `${tr('Audit trail')} (${s.audit.length})`], ['apis', tr('Shared APIs & cost')]] as const).map(([k, l]) => (
          <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>
        ))}
      </div>

      {tab === 'health' && (
        <div className="stack">
          <div className="grid kpi">
            {health.map(({ c, worst, last }) => (
              <div key={c} className="card kpi-tile">
                <div className="row"><span className="health-dot" style={{ background: worst === 'error' ? 'var(--danger)' : worst === 'warn' ? 'var(--warn)' : 'var(--ok)' }} /><b className="small">{tr(LABEL[c])}</b></div>
                <div className="tiny muted" style={{ marginTop: 6 }}>{last ? `${time(last.at)} · ${tr(last.message, last.vars)}` : tr('No events')}</div>
              </div>
            ))}
          </div>
          <div className="card">
            <div className="card-head"><h2>{tr('Scheduled jobs')}</h2></div>
            <div className="table-wrap">
              <table className="t num">
                <thead><tr><th>{tr('Job')}</th><th>{tr('Last run')}</th><th className="right">{tr('Rows')}</th><th>{tr('Result')}</th></tr></thead>
                <tbody>{s.jobs.slice(0, 12).map((j) => (
                  <tr key={j.id}><td className="mono">{j.job}</td><td>{time(j.startedAt)}</td><td className="right">{j.rows}</td>
                    <td>{j.ok ? <span className="badge ok">{tr('OK')}</span> : <span className="badge danger">{tr('Failed')}</span>} <span className="small muted">{j.error && tr(j.error)}</span></td></tr>
                ))}</tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {tab === 'errors' && (
        <div className="card">
          <div className="card-head">
            <h2>{tr('Event log')}</h2>
            <select className="input sm" style={{ width: 'auto' }} value={lvl} onChange={(e) => setLvl(e.target.value as typeof lvl)}>
              <option value="all">{tr('All levels')}</option><option value="error">{tr('Errors')}</option><option value="warn">{tr('Warnings')}</option>
            </select>
          </div>
          <div className="table-wrap">
            <table className="t">
              <thead><tr><th>{tr('When')}</th><th>{tr('Level')}</th><th>{tr('Component')}</th><th>{tr('Client')}</th><th>{tr('Message')}</th></tr></thead>
              <tbody>{s.events.filter((e) => lvl === 'all' || e.level === lvl).map((e) => (
                <tr key={e.id}><td className="small num">{time(e.at)}</td>
                  <td><span className={`badge ${e.level === 'error' ? 'danger' : e.level === 'warn' ? 'warn' : 'info'}`}>{tr(e.level === 'error' ? 'Error' : e.level === 'warn' ? 'Warning' : 'Info')}</span></td>
                  <td className="small">{tr(LABEL[e.component] ?? e.component)}</td><td className="small">{clientName(e.clientId)}</td><td className="small">{tr(e.message, e.vars)}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'audit' && (
        <div className="stack">
          {flagged.length > 0 && <div className="banner warn">{tr('{n} flagged change(s): backdated entries / payments are highlighted below.', { n: flagged.length })}</div>}
          <div className="card">
            {s.audit.length === 0 ? <Empty>{tr('No changes recorded yet in this demo session. Add or approve an expense to see entries.')}</Empty> : (
              <div className="table-wrap">
                <table className="t">
                  <thead><tr><th>{tr('When')}</th><th>{tr('Who')}</th><th>{tr('Client')}</th><th>{tr('Action')}</th><th>{tr('Detail')}</th></tr></thead>
                  <tbody>{s.audit.map((a) => (
                    <tr key={a.id}><td className="small num">{time(a.at)}</td><td className="small">{userName(a.actor)}</td><td className="small">{clientName(a.clientId)}</td>
                      <td>{tr(ACTION_LABEL[a.action] ?? a.action)} <span className="tiny muted mono">{a.table}</span> {a.flag && <span className="badge warn">{tr(FLAG_LABEL[a.flag] ?? a.flag.replace(/_/g, ' '))}</span>}</td><td className="small">{a.summary}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'apis' && (
        <div className="stack">
          <div className="banner info small">{tr('One account per paid provider is shared by all clients. GSTIN/PAN results are cached platform-wide, so a vendor common to many clients is looked up once. Usage is still metered per client for billing.')}</div>
          <div className="banner warn small">{tr('PAN verification via Protean: its terms bar sharing PAN results with other entities. Confirm with Protean that a CA firm verifying on behalf of its clients is permitted before using one shared registration.')}</div>
          <div className="card table-wrap">
            <table className="t num">
              <thead><tr><th>{tr('Service')}</th><th>{tr('Provider')}</th><th className="right">{tr('Calls this month')}</th><th className="right">{tr('Cache hits')}</th><th>{tr('Status')}</th></tr></thead>
              <tbody>{s.providers.map((p) => (
                <tr key={p.code}><td><b>{p.label}</b></td><td className="small">{p.provider}</td><td className="right">{p.usedThisMonth}</td><td className="right">{p.cachedHits}</td>
                  <td>{p.enabled ? <span className="badge ok">{tr('Connected')}</span> : <span className="badge">{tr('Not connected')}</span>}</td></tr>
              ))}</tbody>
            </table>
          </div>
          <div className="hint">{tr('Last updated')} {fmtDate(new Date().toISOString())}. {tr('Unit costs are entered from vendor quotes; none are assumed.')}</div>
        </div>
      )}
    </div>
  );
}
