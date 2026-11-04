// Privacy & consent (DPDP Act 2023): see the notice, your consent, switch AI on/off, withdraw (s.6(4)), exercise rights
// (s.11–14, answered within 90 days), download your data. The CA firm keeps its privacy contact (s.8(9)), engagement end
// dates and company acceptances (from signed engagement letters) here, and answers requests.
import { useState } from 'react';
import { useStore } from '../data/store';
import type { PrivacyRequest } from '../data/types';
import { useTr } from '../i18n';
import { clientConsent, userConsent } from '../lib/consent';
import { fmtDate, fmtDateTime, todayIso } from '../lib/dates';
import { PageHead, useAttempt, useConfirm, useToast } from '../ui/common';
import { NoticeView, useNoticeVars } from '../ui/Notice';
import { isDemo } from '../lib/backend';
import { CODE_TTL_MIN, verifyLink } from '../lib/waVerify';
import { boardReportDue, firstNoticeToBoard, noticeToPerson, reportToBoard72h, type BreachFacts } from '../../supabase/functions/_shared/breach.ts';

/** DPDP Rule 7 notices (CA firm). The firm types the facts; the notices are laid out, blanks stay visible. */
function BreachNotices() {
  const st = useStore();
  const tr = useTr();
  const toast = useToast();
  const firm = st.s.firm;
  const [aware, setAware] = useState('');
  const [f, setF] = useState<BreachFacts>({ firm: firm.name });
  const facts: BreachFacts = { ...f, firm: firm.name, contactName: firm.privacyContactName, contactEmail: firm.privacyEmail, contactPhone: firm.privacyPhone };
  const FIELDS: [keyof BreachFacts, string][] = [
    ['what', 'What happened'], ['data', 'Which personal data, how many people'], ['when', 'When it happened / was found'], ['where', 'Where (system / place)'],
    ['impact', 'Likely consequences'], ['done', 'What has been done / is being done'], ['youCan', 'What people can do to protect themselves'],
    ['cause', 'Causes (for the 72-hour report)'], ['who', 'Who caused it — findings (72-hour report)'], ['prevent', 'Steps so it does not happen again (72-hour report)'],
    ['notified', 'Notices sent to people so far (72-hour report)']
  ];
  const copy = (text: string) => navigator.clipboard.writeText(text).then(() => toast(tr('Copied'))).catch(() => toast(tr('Could not copy — select the text and copy it.'), true));
  const out: [string, string][] = [
    ['To each affected person (English)', noticeToPerson(facts, 'en')], ['To each affected person (Hindi)', noticeToPerson(facts, 'hi')],
    ['To the Data Protection Board — without delay', firstNoticeToBoard(facts)], ['To the Board — detailed report within 72 hours', reportToBoard72h(facts)]
  ];
  return (
    <details className="card pad stack">
      <summary><b>{tr('Breach notices (DPDP Rule 7)')}</b></summary>
      <div className="small">{tr('Use only for a real personal-data breach. Contain it first, then notify without delay. See BREACH-PROCEDURE.md. Counsel should review the wording before first use. For a client’s records the client is the fiduciary — tell the client at once and help it notify.')}</div>
      <div className="field" style={{ maxWidth: 260 }}><label htmlFor="br-aware">{tr('When the firm became aware')}</label>
        <input id="br-aware" type="datetime-local" className="input sm" value={aware} onChange={(e) => setAware(e.target.value)} />
        {aware && <span className="hint err">{tr('Detailed Board report due by {at}', { at: fmtDateTime(boardReportDue(aware)) })}</span>}</div>
      {FIELDS.map(([k, label]) => (
        <div key={k} className="field"><label htmlFor={`br-${k}`}>{tr(label)}</label>
          <textarea id={`br-${k}`} className="input sm" rows={2} value={(f[k] as string) ?? ''} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></div>
      ))}
      {out.map(([title, text]) => (
        <div key={title} className="stack" style={{ gap: 4 }}>
          <div className="row between"><b className="small">{tr(title)}</b><button className="btn sm" onClick={() => copy(text)}>{tr('Copy')}</button></div>
          <pre className="small" style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{text}</pre>
        </div>
      ))}
    </details>
  );
}

/** Number check: the person sends a one-time code FROM their WhatsApp — proof that the number is theirs. */
function WhatsappVerify() {
  const st = useStore();
  const tr = useTr();
  const toast = useToast();
  const attempt = useAttempt();
  const [code, setCode] = useState<string>();
  const firmNo = st.s.firm.whatsappNumber;
  const me = st.me!;
  const MSG: Record<string, string> = {
    verified: 'Number confirmed — bills from it now go to your Inbox.', wrong: 'That code does not match. Ask for a new code if needed.',
    expired: 'The code has expired — ask for a new one.', too_many: 'Too many wrong codes — ask for a new one.', no_code: 'Ask for a code first.'
  };
  async function getCode() {
    try { setCode(await st.startWhatsappVerify()); } catch (e) { toast(tr((e as Error).message), true); }
  }
  async function simulate() {
    const r = await st.receiveWhatsappText(me.whatsapp!, `VERIFY ${code}`);
    toast(tr(MSG[r] ?? r), r !== 'verified');
  }
  return (
    <div className="stack" style={{ gap: 8 }}>
      <div className="small">{tr('To confirm the number is yours, send a one-time code from it on WhatsApp. Typing "yes" is not enough — this stops bills arriving from a wrong or someone else’s number.')}</div>
      {!code ? (
        <div className="row wrap">
          <button className="btn sm primary" onClick={getCode}>{tr('Get my code')}</button>
          <button className="btn sm" onClick={() => attempt(() => st.removeMyWhatsapp(), 'Saved & logged')}>{tr('Not my number — remove it')}</button>
        </div>
      ) : (
        <div className="banner info stack" style={{ gap: 6 }}>
          <div>{tr('Send this from your WhatsApp ({num}):', { num: `+${me.whatsapp}` })} <b className="mono" style={{ fontSize: 18 }}>VERIFY {code}</b></div>
          <div className="tiny">{tr('Valid for {min} minutes. Do not share it with anyone.', { min: CODE_TTL_MIN })}</div>
          <div className="row wrap">
            {firmNo
              ? <a className="btn sm primary" href={verifyLink(firmNo, code)} target="_blank" rel="noopener noreferrer">{tr('Open WhatsApp to send it')}</a>
              : <span className="hint err">{tr('Your CA firm has not added its WhatsApp number yet — ask them.')}</span>}
            {isDemo && <button className="btn sm" onClick={simulate}>{tr('Demo: simulate sending it')}</button>}
            <button className="btn sm" onClick={getCode}>{tr('New code')}</button>
          </div>
        </div>
      )}
    </div>
  );
}

const KINDS: { kind: PrivacyRequest['kind']; label: string }[] = [
  { kind: 'access', label: 'Summary of my personal data' }, { kind: 'correction', label: 'Correct or update my data' },
  { kind: 'erasure', label: 'Erase my data' }, { kind: 'nominate', label: 'Nominate someone to act for me' }, { kind: 'grievance', label: 'Complaint / grievance' }
];

export function Privacy() {
  const st = useStore();
  const { s, me, client, clientId } = st;
  const tr = useTr();
  const attempt = useAttempt();
  const vars = useNoticeVars();
  const today = todayIso();
  const [showNotice, setShowNotice] = useState(false);
  const [kind, setKind] = useState<PrivacyRequest['kind']>('access');
  const [details, setDetails] = useState('');
  if (!me) return null;
  const mine = userConsent(s.consents, me.id, today);
  const cc = clientId ? clientConsent(s.consents, clientId, today) : undefined;
  const admin = me.role !== 'sub_user';
  const myReqs = s.privacyRequests.filter((r) => r.userId === me.id);

  const confirm = useConfirm();
  async function confirmAnd(msg: string, fn: () => void) { if (await confirm(tr(msg), { danger: true })) attempt(fn); }

  function downloadMyData() {
    const data = {
      exportedAt: new Date().toISOString(), user: me, consents: s.consents.filter((c) => c.userId === me!.id), requests: myReqs,
      entriesCreated: s.expenses.filter((e) => e.createdBy === me!.id).map((e) => ({ id: e.id, vendor: e.vendorName, billNo: e.invoiceNo, date: e.invoiceDate, total: e.totalAmount, status: e.status })),
      paymentsRecorded: s.payments.filter((p) => p.createdBy === me!.id).map((p) => ({ id: p.id, vendor: p.vendorName, mode: p.mode, amount: p.amount, paidOn: p.paidOn })),
      activityLog: s.audit.filter((a) => a.actor === me!.id)
    };
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    a.download = `vouchr-my-data-${today}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="content stack" style={{ maxWidth: 900 }}>
      <PageHead title={tr('Privacy & consent')} sub={tr('Digital Personal Data Protection Act, 2023')} />

      <div className="card pad stack">
        <h2>{tr('Your consent')}</h2>
        {mine ? (
          <div className="small">{tr('Given on {date} · notice {v} · AI assistance: {ai}', { date: fmtDateTime(mine.acceptedAt), v: mine.noticeVersion, ai: mine.purposes.ai ? tr('On') : tr('Off') })}
            {mine.validUntil && <> · {tr('valid until {date}', { date: fmtDate(mine.validUntil) })}</>}</div>
        ) : <div className="small">{tr('No active consent.')}</div>}
        <div className="row wrap">
          <button className="btn sm" onClick={() => setShowNotice(!showNotice)}>{showNotice ? tr('Hide notice') : tr('Read the privacy notice')}</button>
          {mine && (mine.purposes.ai
            ? <button className="btn sm" onClick={() => attempt(() => st.withdrawConsent('user', { aiOnly: true }), 'AI assistance switched off')}>{tr('Switch AI off')}</button>
            : <button className="btn sm" onClick={() => attempt(() => st.giveConsent({ lang: s.lang, ai: true, ageConfirmed: true }), 'AI assistance switched on')}>{tr('Switch AI on')}</button>)}
          {mine && <button className="btn sm danger" onClick={() => confirmAnd('Withdraw your consent? You will be signed out and cannot use Vouchr until you agree again. Records the law requires are kept.', () => st.withdrawConsent('user'))}>{tr('Withdraw my consent')}</button>}
        </div>
        {showNotice && <NoticeView lang={s.lang} />}
      </div>

      {me.role === 'client_admin' && cc && (
        <div className="card pad stack">
          <h2>{tr('Company consent')} · {client?.name}</h2>
          <div className="small">{cc.state === 'active'
            ? tr('Accepted on {date} ({how}) · AI for company documents: {ai}', { date: fmtDateTime(cc.consent.acceptedAt), how: cc.consent.method === 'engagement_letter' ? cc.consent.reference ?? '' : tr('in the app'), ai: cc.consent.purposes.ai ? tr('On') : tr('Off') })
            : tr('Not yet accepted. Your CA firm can record it from the signed engagement letter.')}</div>
          {cc.state === 'active' && (
            <div className="row wrap">
              {cc.consent.purposes.ai && <button className="btn sm" onClick={() => attempt(() => st.withdrawConsent('client', { aiOnly: true }), 'AI assistance switched off')}>{tr('Switch AI off for the company')}</button>}
              <button className="btn sm danger" onClick={() => confirmAnd('Withdraw your company’s consent? Vouchr will stop for everyone in your company. Records the law requires are kept.', () => st.withdrawConsent('client'))}>{tr('Withdraw company consent')}</button>
            </div>
          )}
        </div>
      )}

      {me.whatsapp && (
        <div className="card pad stack">
          <h2>💬 {tr('Sending bills by WhatsApp')}</h2>
          <div className="small">{tr('Your admin added +{num} for you. Bills sent from this number to {firm} on WhatsApp go to your Inbox as drafts.', { num: `${me.whatsapp.slice(0, 2)} ${me.whatsapp.slice(2)}`, firm: s.firm.whatsappNumber ? `+${s.firm.whatsappNumber}` : s.firm.name })}</div>
          {me.whatsappVerifiedAt
            ? <div className="row wrap"><span className="badge ok">{tr('Confirmed')}</span><button className="btn sm" onClick={() => attempt(() => st.removeMyWhatsapp(), 'Saved & logged')}>{tr('Stop — remove my number')}</button></div>
            : <WhatsappVerify />}
        </div>
      )}

      <div className="card pad stack">
        <h2>{tr('Your rights')}</h2>
        <div className="small muted">{tr('We reply within 90 days at most. Contact for privacy questions: {contact}', { contact: vars.contact })}</div>
        <div className="row wrap" style={{ alignItems: 'flex-end' }}>
          <div className="field"><label htmlFor="pr-kind">{tr('Request')}</label>
            <select id="pr-kind" className="input sm" value={kind} onChange={(e) => setKind(e.target.value as PrivacyRequest['kind'])}>{KINDS.map((k) => <option key={k.kind} value={k.kind}>{tr(k.label)}</option>)}</select></div>
          <div className="field grow"><label htmlFor="pr-det" className="req">{tr('Details')}</label><input id="pr-det" className="input sm" value={details} onChange={(e) => setDetails(e.target.value)} /></div>
          <button className="btn sm primary" onClick={() => { if (attempt(() => st.addPrivacyRequest(kind, details), 'Request sent')) setDetails(''); }}>{tr('Send')}</button>
        </div>
        <button className="btn sm" style={{ alignSelf: 'flex-start' }} onClick={downloadMyData}>{tr('Download my data (JSON)')}</button>
        {myReqs.length > 0 && <div className="list">{myReqs.map((r) => <div key={r.id} className="list-item small"><span className="grow">{tr(KINDS.find((k) => k.kind === r.kind)!.label)} — {r.details}</span><span className={`badge ${r.status === 'open' ? 'warn' : 'ok'}`}>{r.status === 'open' ? tr('Due by {date}', { date: fmtDate(r.dueBy) }) : tr('Resolved')}</span></div>)}</div>}
        <div className="tiny muted">{tr('If you are not satisfied, you may complain to the Data Protection Board of India.')}</div>
      </div>

      {me.role === 'super_admin' && <FirmPrivacy />}
      {admin && me.role !== 'super_admin' && vars.contactMissing && <div className="banner warn small">{tr('Your CA firm has not yet added its privacy contact.')}</div>}
    </div>
  );
}

function FirmPrivacy() {
  const st = useStore();
  const { s } = st;
  const tr = useTr();
  const attempt = useAttempt();
  const today = todayIso();
  const [f, setF] = useState(s.firm);
  const [ref, setRef] = useState<Record<string, string>>({});
  const [ends, setEnds] = useState<Record<string, string>>({});
  const [ai, setAi] = useState<Record<string, boolean>>({});
  const [res, setRes] = useState<Record<string, string>>({});
  const open = s.privacyRequests.filter((r) => r.status === 'open').sort((a, b) => a.dueBy.localeCompare(b.dueBy));

  return (
    <>
      <div className="card pad stack">
        <h2>{tr('Firm privacy contact')}</h2>
        <div className="row wrap" style={{ alignItems: 'flex-end' }}>
          <div className="field"><label htmlFor="fp-n" className="req">{tr('Firm name')}</label><input id="fp-n" className="input sm" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
          <div className="field"><label htmlFor="fp-c">{tr('Contact person / DPO')}</label><input id="fp-c" className="input sm" value={f.privacyContactName ?? ''} onChange={(e) => setF({ ...f, privacyContactName: e.target.value || undefined })} /></div>
          <div className="field"><label htmlFor="fp-e">{tr('E-mail')}</label><input id="fp-e" className="input sm" value={f.privacyEmail ?? ''} onChange={(e) => setF({ ...f, privacyEmail: e.target.value || undefined })} /></div>
          <div className="field"><label htmlFor="fp-p">{tr('Phone')}</label><input id="fp-p" className="input sm" value={f.privacyPhone ?? ''} onChange={(e) => setF({ ...f, privacyPhone: e.target.value || undefined })} /></div>
          <div className="field"><label htmlFor="fp-w">{tr('Firm WhatsApp number for bills')}</label><input id="fp-w" className="input sm" inputMode="tel" value={f.whatsappNumber ?? ''} onChange={(e) => setF({ ...f, whatsappNumber: e.target.value.replace(/\D/g, '') || undefined })} /></div>
          <button className="btn sm primary" onClick={() => attempt(() => st.updateFirm(f), 'Saved & logged')}>{tr('Save')}</button>
        </div>
        <div className="field">
          <label htmlFor="fp-irp">{tr('E-invoice portal public key (to check signed QR codes)')}</label>
          <textarea id="fp-irp" className="input sm mono" rows={3} placeholder="-----BEGIN PUBLIC KEY-----" value={f.irpPublicKeyPem ?? ''} onChange={(e) => setF({ ...f, irpPublicKeyPem: e.target.value.trim() || undefined })} />
          <span className="hint">{tr('Download it from the official e-invoice (IRP) portal and paste it here. Without it, QR codes are read but marked “signature not checked”.')}</span>
        </div>
      </div>

      <BreachNotices />

      <div className="card">
        <div className="card-head"><h2>{tr('Company consent by client')}</h2></div>
        <div className="list">
          {s.clients.map((c) => {
            const cc = clientConsent(s.consents, c.id, today);
            return (
              <div key={c.id} className="list-item stack" style={{ alignItems: 'stretch', gap: 6 }}>
                <div className="row between wrap"><b>{c.name}</b>
                  <span className={`badge ${cc.state === 'active' ? 'ok' : cc.state === 'missing' ? 'warn' : 'danger'}`}>{tr(cc.state === 'active' ? 'Accepted' : cc.state === 'missing' ? 'Not recorded' : cc.state === 'withdrawn' ? 'Withdrawn' : 'Expired')}</span></div>
                {cc.state !== 'missing' && <div className="tiny muted">{cc.consent.method === 'engagement_letter' ? cc.consent.reference : tr('in the app')} · {fmtDateTime(cc.consent.acceptedAt)} · AI {cc.consent.purposes.ai ? tr('On') : tr('Off')}{cc.consent.validUntil ? ` · ${tr('valid until {date}', { date: fmtDate(cc.consent.validUntil) })}` : ''}</div>}
                {cc.state !== 'active' && (
                  <div className="row wrap" style={{ alignItems: 'flex-end' }}>
                    <div className="field grow"><label htmlFor={`cr-${c.id}`} className="req">{tr('Engagement letter reference & date')}</label><input id={`cr-${c.id}`} className="input sm" placeholder={tr('e.g. EL/2026/14 dated 01-04-2026')} value={ref[c.id] ?? ''} onChange={(e) => setRef({ ...ref, [c.id]: e.target.value })} /></div>
                    <div className="field"><label htmlFor={`ce-${c.id}`}>{tr('Engagement ends on')}</label><input id={`ce-${c.id}`} type="date" className="input sm" min={today} value={ends[c.id] ?? c.engagementEndsOn ?? ''} onChange={(e) => setEnds({ ...ends, [c.id]: e.target.value })} /></div>
                    <label className="row small"><input type="checkbox" checked={!!ai[c.id]} onChange={(e) => setAi({ ...ai, [c.id]: e.target.checked })} /> {tr('Letter allows AI')}</label>
                    <button className="btn sm primary" onClick={() => attempt(() => st.recordClientConsent(c.id, { reference: ref[c.id] ?? '', ai: !!ai[c.id], validUntil: ends[c.id] || undefined }), 'Saved & logged')}>{tr('Record')}</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="card">
        <div className="card-head"><h2>{tr('Open rights requests')} · {open.length}</h2></div>
        {open.length === 0 ? <div className="pad small muted">{tr('None.')}</div> : (
          <div className="list">{open.map((r) => (
            <div key={r.id} className="list-item stack" style={{ alignItems: 'stretch', gap: 6 }}>
              <div className="small"><b>{tr(KINDS.find((k) => k.kind === r.kind)!.label)}</b> · {s.users.find((u) => u.id === r.userId)?.name} · {r.details}</div>
              <div className="row wrap">
                <span className={`badge ${r.dueBy < today ? 'danger' : 'warn'}`}>{tr('Due by {date}', { date: fmtDate(r.dueBy) })}</span>
                <input className="input sm grow" placeholder={tr('What was done')} aria-label={tr('What was done')} value={res[r.id] ?? ''} onChange={(e) => setRes({ ...res, [r.id]: e.target.value })} />
                <button className="btn sm" onClick={() => attempt(() => st.resolvePrivacyRequest(r.id, res[r.id] ?? ''), 'Saved & logged')}>{tr('Mark resolved')}</button>
              </div>
            </div>
          ))}</div>
        )}
      </div>
    </>
  );
}
