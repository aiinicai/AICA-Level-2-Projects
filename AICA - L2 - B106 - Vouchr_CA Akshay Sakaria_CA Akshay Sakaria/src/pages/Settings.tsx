import { useState } from 'react';
import { AUTO_DEFAULTS } from '../lib/autoApprove';
import { DpdpNote } from '../ui/DpdpNote';
import type { BankAccount, CostCentre } from '../data/types';
import { useTr } from '../i18n';
import { RuleError, useStore } from '../data/store';
import { monthName, toIso } from '../lib/dates';
import { Initials, PageHead, useAttempt, useConfirm, useToast } from '../ui/common';
import { Icon } from '../ui/Icon';
import { saveDocument } from '../lib/storage';

const ROLE = { super_admin: 'Super admin', client_admin: 'Admin', sub_user: 'Staff' };

export function Settings() {
  const tr = useTr();
  const st = useStore();
  const { client, s, me } = st;
  const isCA = st.me?.role === 'super_admin'; // control settings are the CA firm's (DB rule 0006)
  const confirm = useConfirm();
  const toast = useToast();
  const [color, setColor] = useState(client?.brandColor ?? '#0f2a44');
  const [newName, setNewName] = useState('');
  const [newRole, setNewRole] = useState<'sub_user' | 'client_admin'>('sub_user');
  const attempt = useAttempt();
  if (!client) return null;

  // last 6 months
  const months = Array.from({ length: 6 }, (_, i) => { const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - i); return toIso(d).slice(0, 7); });
  const team = s.users.filter((u) => u.clientId === client.id);

  function onLogo(f?: File) {
    if (!f) return;
    if (f.size > 300_000) { toast(tr('Logo must be under 300 KB'), true); return; }
    const r = new FileReader();
    r.onload = () => { st.updateClient({ ...client!, logoUrl: String(r.result) }); toast(tr('Logo updated')); };
    saveDocument({ clientId: client!.id, clientName: client!.name, fy: '', kind: 'Branding', file: f, name: `logo.${(/\.(\w+)$/.exec(f.name)?.[1] ?? 'png').toLowerCase()}` })
      .catch((err) => st.logEvent('error', 'drive_upload', 'File could not be saved: {err}', { err: (err as Error).message }));
    r.readAsDataURL(f);
  }

  return (
    <div className="content stack lg" style={{ maxWidth: 820 }}>
      <PageHead title={tr('Settings')} sub={client.name} />

      <div className="card pad stack">
        <h2>{tr('Branding')}</h2>
        <div className="row wrap">
          {client.logoUrl ? <img src={client.logoUrl} alt="Logo" style={{ width: 64, height: 64, objectFit: 'contain', borderRadius: 12, border: '1px solid var(--line)' }} />
            : <div className="logo-fallback" style={{ width: 64, height: 64, fontSize: 24 }}>{client.name[0]}</div>}
          <label className="btn"><Icon name="upload" size={16} /> {tr('Upload logo')}<input type="file" accept="image/png,image/svg+xml,image/jpeg" hidden onChange={(e) => onLogo(e.target.files?.[0])} /></label>
          {client.logoUrl && <button className="btn ghost" onClick={() => st.updateClient({ ...client, logoUrl: undefined })}>{tr('Remove')}</button>}
        </div>
        <div className="row wrap">
          <input type="color" value={color} onChange={(e) => setColor(e.target.value)} style={{ width: 48, height: 40, border: 'none', background: 'none' }} aria-label={tr('Brand colour')} />
          <span className="mono">{color}</span>
          <button className="btn primary sm" onClick={() => { st.updateClient({ ...client, brandColor: color }); toast(tr('Brand colour applied')); }}>{tr('Apply colour')}</button>
        </div>
        <div className="hint">{tr('Your logo appears on the login screen, app header and reports. Colour applies to buttons and highlights.')}</div>
      </div>

      <div className="card">
        <div className="card-head"><h2>{tr('Month lock')}</h2><span className="hint">{me?.role === 'super_admin' ? tr('Locked months cannot be edited by anyone.') : tr('Locked months cannot be edited by anyone — only the CA firm can unlock.')}</span></div>
        <div className="list">
          {months.map((m) => {
            const locked = st.isLocked(client.id, m + '-01');
            return (
              <div key={m} className="list-item">
                <Icon name={locked ? 'lock' : 'unlock'} size={18} />
                <span className="grow">{monthName(m)}</span>
                {locked ? <span className="badge brand">{tr('Locked')}</span> : <span className="badge">{tr('Open')}</span>}
                <button className="btn sm" onClick={async () => {
                  const open = st.scoped.expenses.filter((e) => e.invoiceDate.startsWith(m) && e.status === 'submitted').length;
                  if (!locked && open && !(await confirm(tr('{n} bill(s) in {month} are still awaiting CA review. Locking will block their approval until unlocked. Lock anyway?', { n: open, month: monthName(m) }), { ok: tr('Lock') }))) return;
                  try { st.toggleLock(m); } catch (err) { if (err instanceof RuleError) toast(tr(err.message, err.vars), true); }
                }}>
                  {locked ? tr('Unlock') : tr('Lock')}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      <div className="card">
        <div className="card-head"><h2>{tr('Team')}</h2><span className="hint">{tr('Demo: users are added locally. Live: an e-mail invite with one-time login code.')}</span></div>
        <div className="list">
          {team.map((u) => (
            <div key={u.id} className="list-item">
              <Initials name={u.name} /><span className="grow" style={{ opacity: u.active === false ? 0.5 : 1 }}>{u.name}</span>
              <span className="badge">{tr(ROLE[u.role])}</span>
              {u.active === false && <span className="badge danger">{tr('Inactive')}</span>}
              <WhatsappCell user={u} />
              {u.id !== me?.id && <button className="btn sm" onClick={() => { try { st.toggleUser(u.id); } catch (err) { if (err instanceof RuleError) toast(tr(err.message, err.vars), true); } }}>{u.active === false ? tr('Activate') : tr('Deactivate')}</button>}
            </div>
          ))}
        </div>
        <div className="pad row wrap" style={{ padding: 12, borderTop: '1px solid var(--line)' }}>
          <input className="input sm grow" style={{ minWidth: 160 }} aria-required="true" aria-label={tr('Full name')} placeholder={tr('Full name') + ' *'} value={newName} onChange={(e) => setNewName(e.target.value)} />
          <select className="input sm" style={{ width: 'auto' }} aria-label={tr('Role')} value={newRole} onChange={(e) => setNewRole(e.target.value as 'sub_user' | 'client_admin')}>
            <option value="sub_user">{tr('Staff')}</option><option value="client_admin">{tr('Admin')}</option>
          </select>
          <button className="btn primary sm" onClick={() => { if (attempt(() => st.addUser(newName, newRole), 'User added')) setNewName(''); }}>{tr('+ Add user')}</button>
          <DpdpNote kind="users" />
        </div>
      </div>

      <div className="card pad stack">
        <h2>{tr('Entry rules')}</h2>
        {isCA && (
          <div className="field" style={{ maxWidth: 260 }}><label htmlFor="set-back">{tr('Staff may add bills up to this many days old')}</label>
            <input id="set-back" className="input sm num" inputMode="numeric" value={client.backdateWindowDays} onChange={(e) => attempt(() => st.updateClient({ ...client, backdateWindowDays: Math.min(Number(e.target.value.replace(/\D/g, '')) || 0, 90) }))} /></div>
        )}
        <div className="small">{tr('Staff can add bills from the')} <b>{tr('current month')}</b>{client.backdateWindowDays ? ` ${tr('and the last {n} days', { n: client.backdateWindowDays })}` : ''}. {tr('Older bills are added by an admin and flagged as past-dated in the audit trail. Staff may record backdated payments; these are flagged too.')}</div>
      </div>

      <div className="card pad stack">
        <h2>{tr('Payments & policies')}</h2>
        <div className="row wrap" style={{ alignItems: 'flex-start' }}>
          <div className="field"><label htmlFor="set-terms">{tr('Default credit days')}</label>
            <input id="set-terms" className="input sm num" inputMode="numeric" value={client.defaultCreditDays} onChange={(e) => st.updateClient({ ...client, defaultCreditDays: Math.min(Number(e.target.value.replace(/\D/g, '')) || 0, 365) })} /></div>
          <div className="field"><label htmlFor="set-cash">{tr('Cash limit per vendor per day (₹)')}</label>
            <input id="set-cash" className="input sm num" inputMode="numeric" readOnly={!isCA} aria-readonly={!isCA} value={client.cashLimitPerDay} onChange={(e) => attempt(() => st.updateClient({ ...client, cashLimitPerDay: Number(e.target.value.replace(/\D/g, '')) || 0 }))} />
            {!isCA && <span className="hint">🔒 {tr('Set by your CA')}</span>}</div>
          <div className="field"><label htmlFor="set-note">{tr('Bills above this need a note (₹)')}</label>
            <input id="set-note" className="input sm num" inputMode="numeric" readOnly={!isCA} aria-readonly={!isCA} value={client.noteAboveAmount} onChange={(e) => attempt(() => st.updateClient({ ...client, noteAboveAmount: Number(e.target.value.replace(/\D/g, '')) || 0 }))} />
            {!isCA && <span className="hint">🔒 {tr('Set by your CA')}</span>}</div>
          <div className="field"><label htmlFor="set-cashl">{tr('Cash ledger in Tally')}</label>
            <input id="set-cashl" className="input sm" value={client.cashLedger} onChange={(e) => st.updateClient({ ...client, cashLedger: e.target.value })} /></div>
        </div>
        <div className="hint">{tr('Cash paid to one vendor in a day above the limit is flagged (income-tax disallowance; the limit under the Income-tax Act 2025 must be confirmed by the CA).')}</div>
        <PaymentSources />
      </div>

      {(isCA || client.autoApprove?.enabled) && (() => {
        const aa = { ...AUTO_DEFAULTS, ...(client.autoApprove ?? {}) };
        const set = (patch: Partial<typeof aa>) => attempt(() => st.updateClient({ ...client, autoApprove: { ...aa, ...patch } }));
        const n = (v: string) => Number(v.replace(/\D/g, '')) || 0;
        return (
          <div className="card pad stack">
            <h2>{tr('Auto-approval of low-risk bills')}</h2>
            <div className="small">{tr('Off unless the CA firm switches it on. A bill is approved without review only if ALL of these hold: within the amount limit, bill image attached, no TDS, no reverse charge, no blocked credit, no aggregator / 9(5) part, not past-dated or resubmitted, no look-alike or risk flag, totals add up, and the vendor has enough approved bills all treated the same way. A share of them still goes for a sample check.')}</div>
            <label className="row small"><input type="checkbox" disabled={!isCA} checked={aa.enabled} onChange={(e) => set({ enabled: e.target.checked })} /> <b>{tr('Auto-approve low-risk bills for this client')}</b></label>
            <div className="row wrap" style={{ alignItems: 'flex-start' }}>
              <div className="field"><label htmlFor="aa-max">{tr('Up to this bill total (₹)')}</label>
                <input id="aa-max" className="input sm num" inputMode="numeric" readOnly={!isCA} value={aa.maxAmount} onChange={(e) => set({ maxAmount: Math.min(n(e.target.value), 50000) })} /></div>
              <div className="field"><label htmlFor="aa-min">{tr('Approved bills needed from the vendor')}</label>
                <input id="aa-min" className="input sm num" inputMode="numeric" readOnly={!isCA} value={aa.minHistory} onChange={(e) => set({ minHistory: Math.max(2, Math.min(n(e.target.value), 20)) })} /></div>
              <div className="field"><label htmlFor="aa-sample">{tr('Sample check (% sent to the CA anyway)')}</label>
                <input id="aa-sample" className="input sm num" inputMode="numeric" readOnly={!isCA} value={aa.samplePct} onChange={(e) => set({ samplePct: Math.max(5, Math.min(n(e.target.value), 100)) })} /></div>
            </div>
            {!isCA && <span className="hint">🔒 {tr('Set by your CA')}</span>}
          </div>
        );
      })()}

      {isCA && (
        <div className="card pad stack">
          <h2>{tr('Client access to their Drive folder')}</h2>
          <label className="row small"><input type="checkbox" checked={!!client.driveShareWithAdmins} onChange={(e) => attempt(() => st.updateClient({ ...client, driveShareWithAdmins: e.target.checked }), 'Saved & logged')} />
            {tr('Share this client’s Drive folder (view only) with its admins')}</label>
          <div className="hint">{tr('Live: the drive-share function gives each active client admin view access to Vouchr/<client> and removes it when the admin is deactivated. Staff never get Drive access. In the demo, files stay on this device.')}</div>
        </div>
      )}

      <div className="card pad stack">
        <h2>{tr('Projects & branches')}</h2>
        <div className="hint">{tr('Optional. Staff can tag a bill to a project or branch; reports and Tally (cost centres) use it.')}</div>
        <CostCentres />
      </div>
    </div>
  );
}

const KIND_LABEL = { bank: 'Bank account', upi: 'UPI ID', card: 'Card', cash: 'Cash box' } as const;

function PaymentSources() {
  const st = useStore();
  const { client } = st;
  const tr = useTr();
  if (!client) return null;
  const used = (id: string) => st.scoped.payments.some((p) => p.accountId === id);
  const banks = client.bankAccounts.filter((a) => a.kind === 'bank');
  const set = (i: number, patch: Partial<BankAccount>) => st.updateClient({ ...client, bankAccounts: client.bankAccounts.map((x, j) => (j === i ? { ...x, ...patch } : x)) });
  const add = (kind: BankAccount['kind']) => st.updateClient({ ...client, bankAccounts: [...client.bankAccounts, {
    id: Math.random().toString(36).slice(2, 8), kind, name: tr(KIND_LABEL[kind]), linkedBankId: kind === 'upi' ? banks[0]?.id : undefined,
    tallyLedger: kind === 'cash' ? 'Cash' : kind === 'card' ? 'Credit Card' : kind === 'upi' ? banks[0]?.tallyLedger ?? 'Bank' : 'Bank' }] });
  return (
    <div className="stack">
      <h3>{tr('Paid from (payment sources)')}</h3>
      <div className="list">
        {client.bankAccounts.map((a, i) => (
          <div key={a.id} className="list-item wrap" style={{ alignItems: 'flex-start', opacity: a.active === false ? 0.55 : 1 }}>
            <span className="badge" style={{ marginTop: 8 }}>{tr(KIND_LABEL[a.kind])}</span>
            <div className="grow stack" style={{ gap: 6, minWidth: 'min(220px, 100%)' }}>
              <input className="input sm" aria-label={tr('Name')} value={a.name} onChange={(e) => set(i, { name: e.target.value })} />
              {a.kind === 'upi' && (
                <div className="row wrap">
                  <input className="input sm grow mono" aria-label={tr('UPI ID')} placeholder="name@okhdfcbank" value={a.upiId ?? ''} onChange={(e) => set(i, { upiId: e.target.value.trim() || undefined })} />
                  <select className="input sm grow" aria-label={tr('Debits bank account')} value={a.linkedBankId ?? ''} onChange={(e) => { const b = banks.find((x) => x.id === e.target.value); set(i, { linkedBankId: b?.id, tallyLedger: b?.tallyLedger ?? a.tallyLedger }); }}>
                    <option value="">{tr('Debits which bank?')}</option>
                    {banks.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                  </select>
                </div>
              )}
              <input className="input sm" aria-label={tr('Tally ledger')} placeholder={tr('Tally ledger')} value={a.tallyLedger} disabled={a.kind === 'upi' && !!a.linkedBankId} onChange={(e) => set(i, { tallyLedger: e.target.value })} />
              {a.kind === 'upi' && a.upiId && !/^[\w.\-]{2,}@[a-zA-Z]{2,}$/.test(a.upiId) && <span className="hint err">{tr('UPI ID looks wrong (e.g. name@okhdfcbank)')}</span>}
            </div>
            {used(a.id)
              ? <button className="btn sm" onClick={() => set(i, { active: a.active === false })}>{a.active === false ? tr('Activate') : tr('Deactivate')}</button>
              : <button className="icon-btn" aria-label={tr('Remove')} onClick={() => st.updateClient({ ...client, bankAccounts: client.bankAccounts.filter((x) => x.id !== a.id) })}><Icon name="x" size={16} /></button>}
          </div>
        ))}
      </div>
      <div className="row wrap">
        {(['bank', 'upi', 'card', 'cash'] as const).map((k) => <button key={k} className="btn sm" onClick={() => add(k)}>+ {tr(KIND_LABEL[k])}</button>)}
      </div>
      <div className="hint">{tr('Sources already used in payments can be deactivated but not deleted, so history stays correct.')}</div>
    </div>
  );
}

function CostCentres() {
  const st = useStore();
  const { client } = st;
  const tr = useTr();
  const [name, setName] = useState('');
  const [kind, setKind] = useState<CostCentre['kind']>('branch');
  if (!client) return null;
  const used = (id: string) => st.scoped.expenses.some((e) => e.costCentreId === id);
  const add = () => {
    const n = name.trim();
    if (n.length < 2 || client.costCentres.some((c) => c.name.toLowerCase() === n.toLowerCase())) return;
    st.updateClient({ ...client, costCentres: [...client.costCentres, { id: Math.random().toString(36).slice(2, 8), kind, name: n, active: true }] });
    setName('');
  };
  return (
    <div className="stack">
      <div className="list">
        {client.costCentres.map((c) => (
          <div key={c.id} className="list-item" style={{ opacity: c.active ? 1 : 0.55 }}>
            <span className="badge">{tr(c.kind === 'project' ? 'Project' : 'Branch')}</span>
            <span className="grow">{c.name}</span>
            {used(c.id)
              ? <button className="btn sm" onClick={() => st.updateClient({ ...client, costCentres: client.costCentres.map((x) => (x.id === c.id ? { ...x, active: !x.active } : x)) })}>{c.active ? tr('Close project') : tr('Re-open')}</button>
              : <button className="icon-btn" aria-label={tr('Remove')} onClick={() => st.updateClient({ ...client, costCentres: client.costCentres.filter((x) => x.id !== c.id) })}><Icon name="x" size={16} /></button>}
          </div>
        ))}
      </div>
      <div className="row wrap">
        <select className="input sm" style={{ width: 'auto' }} value={kind} onChange={(e) => setKind(e.target.value as CostCentre['kind'])} aria-label={tr('Type')}>
          <option value="branch">{tr('Branch')}</option><option value="project">{tr('Project')}</option>
        </select>
        <input className="input sm grow" aria-required="true" aria-label={tr('Name')} placeholder={tr('Name, e.g. Nashik Branch') + ' *'} value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && add()} />
        <button className="btn primary sm" onClick={add} disabled={name.trim().length < 2}>{tr('Add')}</button>
      </div>
    </div>
  );
}

/** WhatsApp number for sending bills. An admin sets it; the person confirms it from their own login before bills are accepted. */
function WhatsappCell({ user }: { user: import('../data/types').User }) {
  const st = useStore();
  const tr = useTr();
  const attempt = useAttempt();
  const [edit, setEdit] = useState(false);
  const [num, setNum] = useState(user.whatsapp ? `+${user.whatsapp}` : '');
  if (edit) return (
    <span className="row" style={{ gap: 6 }}>
      <input className="input sm" style={{ width: 150 }} inputMode="tel" placeholder={tr('WhatsApp number')} aria-label={tr('WhatsApp number')} value={num} onChange={(e) => setNum(e.target.value)} />
      <button className="btn sm primary" onClick={() => { if (attempt(() => st.setUserWhatsapp(user.id, num), 'Saved & logged')) setEdit(false); }}>{tr('Save')}</button>
    </span>
  );
  return (
    <button className="btn sm" onClick={() => setEdit(true)} title={tr('WhatsApp number for sending bills')}>
      💬 {user.whatsapp ? `+${user.whatsapp.slice(0, 2)} ••••${user.whatsapp.slice(-4)}` : tr('Add WhatsApp')}
      {user.whatsapp && <span className={`badge ${user.whatsappVerifiedAt ? 'ok' : 'warn'}`} style={{ marginLeft: 6 }}>{user.whatsappVerifiedAt ? tr('Confirmed') : tr('Not confirmed')}</span>}
    </button>
  );
}
