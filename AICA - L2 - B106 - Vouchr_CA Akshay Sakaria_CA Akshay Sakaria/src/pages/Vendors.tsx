import { useState } from 'react';
import { DpdpNote } from '../ui/DpdpNote';
import { useTr } from '../i18n';
import { RuleError, useStore } from '../data/store';
import type { Vendor } from '../data/types';
import { checkGstin, checkPan } from '../lib/validators';
import { stateName } from '../lib/states';
import { fmtInr } from '../lib/money';
import { Drawer, Empty, Initials, PageHead, useAttempt, useToast } from '../ui/common';
import { NoteDrawer } from './NoteDrawer';
import { vendorLevelBalance } from '../lib/vendorNotes';
import { fmtDate } from '../lib/dates';
import { Icon } from '../ui/Icon';

const blank = (clientId: string): Vendor => ({ id: Math.random().toString(36).slice(2, 10), clientId, name: '', gstRegistered: false, panStatus: 'Unverified' });

export function Vendors() {
  const tr = useTr();
  const { scoped, clientId } = useStore();
  const [edit, setEdit] = useState<Vendor>();
  const spend = (id: string) => scoped.expenses.filter((e) => e.vendorId === id).reduce((s, e) => s + e.totalAmount, 0);

  return (
    <div className="content">
      <PageHead title={tr('Vendors')} sub={tr('{n} vendors', { n: scoped.vendors.length })}>
        <button className="btn primary" onClick={() => clientId && setEdit(blank(clientId))}>{tr('+ Add vendor')}</button>
      </PageHead>
      <div className="card">
        {scoped.vendors.length === 0 ? <Empty>{tr('No vendors yet')}</Empty> : (
          <div className="table-wrap">
            <table className="t cards-sm">
              <thead><tr><th>{tr('Vendor')}</th><th>{tr('GSTIN')}</th><th>{tr('PAN')}</th><th>{tr('Checks')}</th><th className="right">{tr('Spend')}</th></tr></thead>
              <tbody>
                {scoped.vendors.map((v) => (
                  <tr key={v.id} className="click" onClick={() => setEdit(v)}>
                    <td><div className="row"><Initials name={v.name} /><b>{v.name}</b></div></td>
                    <td className="mono">{v.gstin ?? <span className="muted">{tr('Not registered')}</span>}</td>
                    <td className="mono">{v.pan ?? '—'}<div className="tiny muted">{tr(v.panEntityType ?? '')}</div></td>
                    <td><div className="row wrap" style={{ gap: 4 }}>
                      {v.gstin && <span className={`badge ${v.gstinStatus === 'Active' ? 'ok' : 'warn'}`}>GST {tr(v.gstinStatus ?? 'unverified')}</span>}
                      <span className={`badge ${v.panStatus === 'Operative' ? 'ok' : v.panStatus === 'Inoperative' ? 'danger' : 'warn'}`}>PAN {tr(v.panStatus ?? 'unverified')}</span>
                    </div></td>
                    <td className="right num">{fmtInr(spend(v.id))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {edit && <VendorForm v={edit} onClose={() => setEdit(undefined)} />}
    </div>
  );
}

function VendorForm({ v, onClose }: { v: Vendor; onClose: () => void }) {
  const tr = useTr();
  const { saveVendor, scoped, me } = useStore();
  const isCA = me?.role === 'super_admin'; // verification status is the CA firm's (DB rule 0006)
  const toast = useToast();
  const [f, setF] = useState<Vendor>(v);
  const g = f.gstin ? checkGstin(f.gstin) : undefined;
  const p = f.pan ? checkPan(f.pan) : undefined;
  const panMismatch = g?.ok && p?.ok && g.pan !== f.pan;
  const dupGstin = f.gstin && scoped.vendors.some((x) => x.id !== f.id && x.gstin === f.gstin);

  function setGstin(val: string) {
    const gst = val.toUpperCase().replace(/\s/g, '');
    const c = checkGstin(gst);
    setF((x) => ({ ...x, gstin: gst || undefined, gstRegistered: !!gst, ...(c.ok ? { pan: c.pan, stateCode: c.stateCode, panEntityType: checkPan(c.pan!).entityType } : {}) }));
  }

  function save() {
    try { saveVendor({ ...f, name: f.name.trim() }); toast(tr('Vendor saved')); onClose(); }
    catch (err) { if (err instanceof RuleError) toast(tr(err.message, err.vars), true); else throw err; }
  }

  const ok = f.name.trim().length > 1 && !(g && !g.ok) && !(p && !p.ok) && !panMismatch && !dupGstin;

  return (
    <Drawer title={v.name || tr('New vendor')} onClose={onClose}
      footer={<><button className="btn" onClick={onClose}>{tr('Cancel')}</button><button className="btn primary grow" disabled={!ok} onClick={save}>{tr('Save vendor')}</button></>}>
      <div className="card pad stack">
        <p className="tiny muted req-legend"><b>*</b> {tr('Required')}</p>
        <DpdpNote kind="vendor" />
        <div className="field"><label htmlFor="vd-name" className="req">{tr('Vendor name')}</label><input id="vd-name" aria-required="true" className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
        <div className="field">
          <label>{tr('GSTIN (leave blank if not registered)')}</label>
          <input className="input mono" style={{ fontSize: 16 }} maxLength={15} value={f.gstin ?? ''} onChange={(e) => setGstin(e.target.value)} />
          {g && <span className={`hint ${g.ok ? 'ok' : 'err'}`}>{g.ok ? `✓ ${tr('Format & check digit valid')} · ${stateName(g.stateCode) ?? g.stateCode}` : tr(g.reason ?? '')}</span>}
          {dupGstin && <span className="hint err">{tr('Another vendor already has this GSTIN')}</span>}
        </div>
        <div className="field">
          <label>{tr('PAN')}</label>
          <input className="input mono" style={{ fontSize: 16 }} maxLength={10} value={f.pan ?? ''} onChange={(e) => { const pan = e.target.value.toUpperCase(); const c = checkPan(pan); setF({ ...f, pan: pan || undefined, panEntityType: c.entityType }); }} />
          {p && <span className={`hint ${p.ok ? 'ok' : 'err'}`}>{p.ok ? `✓ ${tr('Format valid')} · ${tr(p.entityType ?? '')}` : tr(p.reason ?? '')}</span>}
          {panMismatch && <span className="hint err">{tr('PAN does not match the PAN inside the GSTIN')}</span>}
        </div>
        <div className="row wrap" style={{ alignItems: 'flex-start' }}>
          <div className="field grow"><label htmlFor="vd-terms">{tr('Credit days (blank = client default)')}</label>
            <input id="vd-terms" className="input sm num" inputMode="numeric" value={f.creditDays ?? ''} onChange={(e) => setF({ ...f, creditDays: e.target.value ? Math.min(Number(e.target.value.replace(/\D/g, '')), 365) : undefined })} /></div>
          <div className="field grow"><label htmlFor="vd-ledger">{tr('Tally ledger name (if different)')}</label>
            <input id="vd-ledger" className="input sm" value={f.tallyLedger ?? ''} onChange={(e) => setF({ ...f, tallyLedger: e.target.value || undefined })} /></div>
        </div>
      </div>

      <div className="card pad stack">
        <h3>{tr('Live verification')}</h3>
        <div className="row between">
          <div className="small"><b>{tr('GSTIN status')}</b><div className="muted tiny">{tr('Active / cancelled, legal name — via shared GSP account')}</div></div>
          <button className="btn sm" disabled title={tr('Connect the GSTIN verification API in Audit & health → APIs')}>{tr('Verify')}</button>
        </div>
        <div className="row between">
          <div className="small"><b>{tr('PAN status')}</b><div className="muted tiny">{tr('Operative / inoperative (Aadhaar link) — needed for TDS rate')}</div></div>
          <button className="btn sm" disabled title={tr('Connect the PAN verification API in Audit & health → APIs')}>{tr('Verify')}</button>
        </div>
        <div className="row wrap" style={{ alignItems: 'flex-start' }}>
          {f.gstin && (
            <div className="field grow"><label>{tr('GSTIN status (checked on GST portal)')}</label>
              <select className="input sm" disabled={!isCA} value={f.gstinStatus ?? ''} onChange={(e) => setF({ ...f, gstinStatus: e.target.value || undefined })}>
                <option value="">{tr('Not checked')}</option><option value="Active">{tr('Active')}</option><option value="Cancelled">{tr('Cancelled')}</option><option value="Suspended">{tr('Suspended')}</option>
              </select>
            </div>
          )}
          <div className="field grow"><label>{tr('PAN status (checked on Income-tax portal)')}</label>
            <select className="input sm" disabled={!isCA} value={f.panStatus ?? 'Unverified'} onChange={(e) => setF({ ...f, panStatus: e.target.value as Vendor['panStatus'] })}>
              <option value="Unverified">{tr('Not checked')}</option><option value="Operative">{tr('Operative')}</option><option value="Inoperative">{tr('Inoperative')}</option>
            </select>
          </div>
        </div>
        {!isCA && <div className="hint">🔒 {tr('PAN / GSTIN status is set by your CA (or the verification service) because it decides the TDS rate and input credit.')}</div>}
        {f.panStatus === 'Inoperative' && <div className="banner danger small">{tr('Inoperative PAN → TDS at the higher rate on this vendor\'s bills.')}</div>}
        {f.gstinStatus && f.gstinStatus !== 'Active' && <div className="banner danger small">{tr('GSTIN not active → ITC on its bills is at risk; tax invoices from a cancelled GSTIN are not valid for ITC.')}</div>}
        <div className="banner info small"><Icon name="info" size={16} />{tr('Free checks (format, check digit, PAN-in-GSTIN) run instantly. Live checks switch on once the paid API is connected; results are cached platform-wide so one lookup serves every client.')}</div>
      </div>
      {v.name && me?.role !== 'sub_user' && <VendorNotes vendorId={v.id} />}
    </Drawer>
  );
}

/** Credit / debit notes of this vendor; vendor-level ones can be linked to the bill they correct. */
function VendorNotes({ vendorId }: { vendorId: string }) {
  const st = useStore();
  const tr = useTr();
  const attempt = useAttempt();
  const [adding, setAdding] = useState(false);
  const [linkTo, setLinkTo] = useState<Record<string, string>>({});
  const notes = st.scoped.vendorNotes.filter((n) => n.vendorId === vendorId && n.status === 'active');
  const bills = st.scoped.expenses.filter((e) => e.vendorId === vendorId && e.status !== 'rejected' && e.status !== 'draft');
  const level = vendorLevelBalance(vendorId, st.scoped.vendorNotes);
  if (adding) return <NoteDrawer vendorId={vendorId} onClose={() => setAdding(false)} />;
  return (
    <div className="card">
      <div className="card-head"><h3>{tr('Credit / debit notes')}</h3><button className="linkish small" onClick={() => setAdding(true)}>{tr('+ Record a note')}</button></div>
      {level !== 0 && <div className="banner info small" style={{ margin: '0 16px' }}>{level < 0 ? tr('Vendor credit not linked to a bill: {amt}', { amt: fmtInr(-level) }) : tr('Vendor charge not linked to a bill: {amt}', { amt: fmtInr(level) })}</div>}
      {notes.length === 0 ? <div className="empty small">{tr('None')}</div> : (
        <div className="list">
          {notes.map((n) => {
            const b = bills.find((x) => x.id === n.expenseId);
            return (
              <div key={n.id} className="list-item small" style={{ alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <span className={`badge ${n.kind === 'credit' ? 'warn' : ''}`}>{tr(n.kind === 'credit' ? 'Credit note' : 'Debit note')}</span>
                <div className="grow">{n.noteNo} · {fmtDate(n.noteDate)}<div className="tiny muted">{b ? tr('Against bill {no}', { no: b.invoiceNo ?? '—' }) : tr('Vendor level — not linked yet')}</div></div>
                <b className="num">{n.kind === 'credit' ? '−' : '+'}{fmtInr(n.totalAmount)}</b>
                {!n.expenseId && !n.postedAt && bills.length > 0 && (
                  <div className="row" style={{ gap: 6, width: '100%' }}>
                    <select className="input sm grow" aria-label={tr('Against bill')} value={linkTo[n.id] ?? ''} onChange={(e) => setLinkTo({ ...linkTo, [n.id]: e.target.value })}>
                      <option value="">{tr('Choose the bill it corrects')}</option>
                      {bills.map((x) => <option key={x.id} value={x.id}>{x.invoiceNo ?? '—'} · {fmtDate(x.invoiceDate)} · {fmtInr(x.totalAmount)}</option>)}
                    </select>
                    <button className="btn sm" disabled={!linkTo[n.id]} onClick={() => attempt(() => st.linkVendorNote(n.id, linkTo[n.id]), 'Note linked to the bill')}>{tr('Link')}</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

