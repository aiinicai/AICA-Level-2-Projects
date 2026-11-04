import { useState } from 'react';
import { useStore } from '../data/store';
import { runAi, useAiStatus } from '../lib/ai';
import { NoticeReader } from '../ui/NoticeReader';
import { useTr } from '../i18n';
import { fmtDate } from '../lib/dates';
import { Empty, PageHead, useToast } from '../ui/common';
import { Icon } from '../ui/Icon';

const KIND = {
  source_changed: { label: 'Official page changed', tone: 'danger' },
  review_due: { label: 'Quarterly review', tone: 'info' },
  unverified_master: { label: 'Unverified master', tone: 'warn' },
  source_unreachable: { label: 'Could not check', tone: '' },
  ai_suggestion: { label: 'AI found (verify)', tone: 'info' }
} as const;

export function Compliance() {
  const tr = useTr();
  const { s, me, runComplianceCheck, resolveFinding, addAiFindings } = useStore();
  const open = s.findings.filter((f) => f.status === 'open');
  const closed = s.findings.filter((f) => f.status !== 'open').slice(0, 10);
  const lastRun = s.jobs.find((j) => j.job === 'compliance_quarterly');
  const ai = useAiStatus();
  const toast = useToast();
  const [scanning, setScanning] = useState(false);
  async function aiScan() {
    setScanning(true);
    try {
      const since = s.findings.filter((f) => f.kind === 'ai_suggestion').map((f) => f.createdAt.slice(0, 10)).sort().pop() ?? new Date(Date.now() - 100 * 86400000).toISOString().slice(0, 10);
      const r = await runAi<{ items: { area: string; title: string; detail: string; notification_no: string; effective_date: string; source_url: string; verified: boolean; problems: string[] }[] }>('norms_scan', me!.role, { since, tdsTable: s.tdsRates });
      // live: the server files these itself; local test: file them in this demo
      if (ai.mode === 'local') addAiFindings(r.result.items.map((i) => ({ area: i.area, title: i.title,
        detail: `${i.detail}${i.notification_no ? ` · ${i.notification_no}` : ''}${i.effective_date ? ` · w.e.f. ${i.effective_date}` : ''}
${i.verified ? 'Checks passed' : `NEEDS CHECK — ${i.problems.join(', ')}`}: ${i.source_url || 'no source'}` })));
      toast(tr('AI scan done: {n} possible change(s) added for review', { n: r.result.items.length }));
    }
    catch { toast(tr('AI norms scan failed — the page-change watch still runs.'), true); }
    finally { setScanning(false); }
  }

  return (
    <div className="content stack lg">
      <PageHead title={tr('Compliance watch')} sub={tr('Runs automatically on 1 Jan, 1 Apr, 1 Jul, 1 Oct · findings go to the CA team, masters are never changed automatically')}>
        <button className="btn" disabled={!ai.enabled || scanning} onClick={aiScan} title={ai.enabled ? tr('Searches official GST / income-tax sites with Google Search and files what it finds here for review') : tr(ai.reason)}><Icon name="radar" size={16} /> {scanning ? tr('Searching…') : tr('AI scan for rule changes')}</button>
        <button className="btn primary" onClick={runComplianceCheck}><Icon name="refresh" size={16} /> {tr('Run check now')}</button>
      </PageHead>

      <div className="grid kpi">
        <div className="card kpi-tile"><div className="kpi-label">{tr('Open findings')}</div><div className="kpi-value num">{open.length}</div></div>
        <div className="card kpi-tile"><div className="kpi-label">{tr('Last run')}</div><div className="kpi-value" style={{ fontSize: 18 }}>{lastRun ? fmtDate(lastRun.startedAt) : '—'}</div><div className="kpi-sub">{lastRun?.ok ? tr('Completed') : lastRun ? tr('Failed') : ''}</div></div>
        <div className="card kpi-tile"><div className="kpi-label">{tr('Sources watched')}</div><div className="kpi-value num">{s.sources.length}</div></div>
        <div className="card kpi-tile"><div className="kpi-label">{tr('Unverified TDS rates')}</div><div className="kpi-value num">{s.tdsRates.filter((r) => !r.verified).length}</div></div>
      </div>

      <div className="card">
        <div className="card-head"><h2>{tr('Open findings')}</h2></div>
        {open.length === 0 ? <Empty>{tr('No open findings. Press "Run check now" to try the quarterly check.')}</Empty> : (
          <div className="list">
            {open.map((f) => (
              <div key={f.id} className="list-item" style={{ alignItems: 'flex-start' }}>
                <div className="grow stack" style={{ gap: 4 }}>
                  <div className="row wrap"><span className={`badge ${KIND[f.kind].tone}`}>{tr(KIND[f.kind].label)}</span><span className="badge">{f.area.toUpperCase()}</span><span className="tiny muted">{fmtDate(f.createdAt)}</span></div>
                  <b>{f.title}</b>
                  <div className="small muted" style={{ whiteSpace: 'pre-line' }}>{f.detail}</div>
                </div>
                <div className="row">
                  <button className="btn sm" onClick={() => resolveFinding(f.id, 'dismissed')}>{tr('Dismiss')}</button>
                  <button className="btn sm ok" onClick={() => resolveFinding(f.id, 'accepted')}>{tr('Reviewed')}</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <NoticeReader />

      <div className="grid two">
        <div className="card">
          <div className="card-head"><h2>{tr('Watched official sources')}</h2></div>
          <div className="list">
            {s.sources.map((src) => (
              <div key={src.id} className="list-item small">
                <span className="badge">{src.area.toUpperCase()}</span>
                <div className="grow"><div style={{ fontWeight: 600 }}>{src.name}</div><div className="tiny muted ellipsis">{src.url}</div></div>
                <span className="tiny muted">{src.lastCheckedAt ? fmtDate(src.lastCheckedAt) : tr('never')}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="card pad stack small">
          <h2>{tr('How the watch works')}</h2>
          <div>1. <b>{tr('Page-change detection:')}</b> {tr('each official page is fetched, cleaned and fingerprinted. If it differs from last quarter, a finding is raised with the changed text.')}</div>
          <div>2. <b>{tr('Quarterly checklist:')}</b> {tr('TDS rates & thresholds, Form 140 due dates, RCM categories, 17(5) list, GSTR-2B timing.')}</div>
          <div>3. <b>{tr('Unverified masters:')}</b> {tr('any rate a CA has not signed off keeps raising a finding.')}</div>
          <div>{tr('4. A CA reviews and edits')} <b>{tr('Tax masters')}</b>{tr('. Every change is audit-logged. Nothing is changed automatically — a wrong automatic rate change would put every client at risk.')}</div>
          {closed.length > 0 && <div className="muted">{tr('Resolved recently')}: {closed.length}</div>}
        </div>
      </div>
    </div>
  );
}
