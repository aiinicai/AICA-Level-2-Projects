import { useState } from 'react';
import { useTr } from '../i18n';
import { useStore } from '../data/store';
import type { TdsRate } from '../data/types';
import { BLOCKED_RULES, RCM_RULES } from '../data/masters';
import { fmtInr } from '../lib/money';
import { PageHead, useToast } from '../ui/common';
import { Icon } from '../ui/Icon';

export function Masters() {
  const tr = useTr();
  const { s } = useStore();
  const [tab, setTab] = useState<'tds' | 'heads' | 'rcm' | 'blocked'>('tds');
  return (
    <div className="content stack">
      <PageHead title={tr('Tax masters')} sub={tr('Platform-wide. Changes are logged in the audit trail. Never auto-updated.')} />
      <div className="banner warn"><Icon name="alert" size={18} /><span>{tr('All starting values come from secondary sources and are marked')} <b>{tr('unverified')}</b>{tr('. A CA must verify each against the Income-tax Act 2025 / Rules 2026 and CGST notifications before go-live.')}</span></div>
      <div className="tabs">
        {([['tds', 'TDS rates'], ['heads', 'Expense heads'], ['rcm', 'RCM categories'], ['blocked', 'Blocked credits 17(5)']] as const).map(([k, l]) => (
          <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{tr(l)}</button>
        ))}
      </div>
      {tab === 'tds' && <div className="stack">{s.tdsRates.map((r) => <RateRow key={r.code} r={r} />)}</div>}
      {tab === 'heads' && (
        <div className="card table-wrap">
          <table className="t">
            <thead><tr><th>{tr('Head')}</th><th>{tr('Tally ledger')}</th><th>{tr('HSN/SAC prefixes')}</th><th>{tr('Default TDS')}</th><th>{tr('Flags')}</th></tr></thead>
            <tbody>{s.heads.map((h) => (
              <tr key={h.id}><td><b>{tr(h.name)}</b><div className="tiny muted">{h.keywords.slice(0, 5).join(', ')}</div></td><td>{h.tallyLedger}</td><td className="mono">{h.sacHsnPrefixes.join(', ') || '—'}</td><td className="mono">{h.defaultTdsCode ?? '—'}</td>
                <td>{h.rcmCode && <span className="badge warn">RCM {h.rcmCode}</span>} {h.blocked175 && <span className="badge danger">17(5)</span>}</td></tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {tab === 'rcm' && (
        <div className="card table-wrap">
          <table className="t"><thead><tr><th>{tr('Code')}</th><th>{tr('Category')}</th><th>{tr('Supplier condition')}</th><th>{tr('Reference')}</th><th>{tr('Status')}</th></tr></thead>
            <tbody>{RCM_RULES.map((r) => <tr key={r.code}><td className="mono">{r.code}</td><td>{r.description}</td><td>{r.supplierCondition.replace(/_/g, ' ')}</td><td className="small">{r.notificationRef}</td><td><span className="badge warn">{tr('Unverified')}</span></td></tr>)}</tbody>
          </table>
          <div className="pad hint" style={{ padding: 12 }}>{tr('RCM on purchases from unregistered suppliers applies only to notified categories — it is not applied to every non-GST bill.')}</div>
        </div>
      )}
      {tab === 'blocked' && (
        <div className="card table-wrap">
          <table className="t"><thead><tr><th>{tr('Code')}</th><th>{tr('Blocked credit')}</th><th>{tr('Detection keywords')}</th></tr></thead>
            <tbody>{BLOCKED_RULES.map((b) => <tr key={b.code}><td className="mono">{b.code}</td><td>{b.description}</td><td className="small muted">{b.keywords.join(', ')}</td></tr>)}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RateRow({ r }: { r: TdsRate }) {
  const tr = useTr();
  const { updateTdsRate } = useStore();
  const toast = useToast();
  const [edit, setEdit] = useState(false);
  const [f, setF] = useState(r);

  return (
    <div className="card pad stack" style={{ gap: 8 }}>
      <div className="row between wrap">
        <div>
          <b>{r.description}</b> <span className="mono muted">{r.code}</span>
          <div className="small muted">{r.actReference ?? tr('Act reference: to be filled by CA')} · {tr('from')} {r.effectiveFrom}</div>
        </div>
        <div className="row">
          {r.verified ? <span className="badge ok">{tr('✓ Verified')}</span> : <span className="badge warn">{tr('Unverified')}</span>}
          <button className="btn sm" onClick={() => setEdit(!edit)}>{edit ? tr('Close') : tr('Edit')}</button>
        </div>
      </div>
      <div className="row wrap small num">
        <span className="badge brand">{r.ratePct}%</span>
        {r.thresholdSingle !== undefined && <span>{tr('Single bill above')} {fmtInr(r.thresholdSingle)}</span>}
        {r.thresholdAggregate !== undefined && <span>{tr('Yearly total above')} {fmtInr(r.thresholdAggregate)}</span>}
        {r.appliesToEntity && <span>{tr('PAN types')}: {r.appliesToEntity.join(', ')}</span>}
        <span>{tr('No / inoperative PAN')}: {r.noPanRatePct}%</span>
      </div>
      <div className="tiny muted">{tr(r.sourceNote)}</div>
      {edit && (
        <div className="stack" style={{ borderTop: '1px solid var(--line)', paddingTop: 12 }}>
          <div className="row wrap">
            <div className="field"><label className="req">{tr('Rate %')}</label><input className="input sm" value={f.ratePct} onChange={(e) => setF({ ...f, ratePct: Number(e.target.value) || 0 })} /></div>
            <div className="field"><label>{tr('Single threshold')}</label><input className="input sm" value={f.thresholdSingle ?? ''} onChange={(e) => setF({ ...f, thresholdSingle: e.target.value ? Number(e.target.value) : undefined })} /></div>
            <div className="field"><label>{tr('Yearly threshold')}</label><input className="input sm" value={f.thresholdAggregate ?? ''} onChange={(e) => setF({ ...f, thresholdAggregate: e.target.value ? Number(e.target.value) : undefined })} /></div>
            <div className="field"><label>{tr('No-PAN rate %')}</label><input className="input sm" value={f.noPanRatePct ?? ''} onChange={(e) => setF({ ...f, noPanRatePct: Number(e.target.value) || undefined })} /></div>
          </div>
          <div className="field"><label>{tr('Act reference (e.g. section & table serial)')}</label><input className="input sm" value={f.actReference ?? ''} onChange={(e) => setF({ ...f, actReference: e.target.value || undefined })} /></div>
          <label className="row small"><input type="checkbox" checked={f.verified} onChange={(e) => setF({ ...f, verified: e.target.checked })} /> {tr('I have verified this against the Act / Rules')}</label>
          <button className="btn primary sm" style={{ alignSelf: 'flex-start' }} onClick={() => { updateTdsRate(f); setEdit(false); toast(tr('Saved & logged')); }}>{tr('Save')}</button>
        </div>
      )}
    </div>
  );
}
