// CA firm review queue — the only place tax fields are decided.
import { useMemo, useState } from 'react';
import { riskCheck, type Severity } from '../lib/anomaly';
import { useTr } from '../i18n';
import { RuleError, useStore } from '../data/store';
import type { Expense } from '../data/types';
import { BLOCKED_RULES, RCM_RULES } from '../data/masters';
import { suggestHead, suggestItc, suggestRcm, suggestTds } from '../lib/rules';
import { fmtDate } from '../lib/dates';
import { fmtInr, round2 } from '../lib/money';
import { openDocument } from '../lib/storage';
import { Drawer, Empty, PageHead, useToast } from '../ui/common';
import { AiCheck } from '../ui/AiCheck';
import { Icon } from '../ui/Icon';

export function Review() {
  const tr = useTr();
  const { s, me, assignReview } = useStore();
  const [clientFilter, setClientFilter] = useState('all');
  const [open, setOpen] = useState<string>();
  const [order, setOrder] = useState<'oldest' | 'confidence'>('oldest');
  const [who, setWho] = useState<'all' | 'mine' | 'none'>('all');
  const now = Date.now();
  const waitDays = (e: Expense) => Math.max(0, Math.floor((now - new Date(e.resubmittedAt ?? e.createdAt).getTime()) / 864e5));
  const reviewers = s.users.filter((u) => u.role === 'super_admin' && u.active !== false);
  const rows = s.expenses
    .filter((e) => e.status === 'submitted' && (clientFilter === 'all' || e.clientId === clientFilter)
      && (who === 'all' || (who === 'mine' ? e.assignedTo === me?.id : !e.assignedTo)))
    .sort((a, b) => (order === 'oldest' ? waitDays(b) - waitDays(a) || a.createdAt.localeCompare(b.createdAt) : (a.headConfidence ?? 0) - (b.headConfidence ?? 0)));
  const late = rows.filter((e) => waitDays(e) > 3).length;
  const autoDone = s.expenses.filter((e) => e.autoApproved && (clientFilter === 'all' || e.clientId === clientFilter)).sort((a, b) => (b.reviewedAt ?? '').localeCompare(a.reviewedAt ?? '')).slice(0, 20);
  const clientName = (id: string) => s.clients.find((c) => c.id === id)?.name ?? '';
  const current = s.expenses.find((e) => e.id === open);
  // rule-based red flags (Bill risk check) for every bill in the queue — worst severity per bill
  const risk = useMemo(() => {
    const m = new Map<string, { sev: Severity; n: number }>();
    const order: Severity[] = ['high', 'medium', 'low'];
    for (const c of s.clients) for (const f of riskCheck(s.expenses.filter((e) => e.clientId === c.id), s.vendors.filter((v) => v.clientId === c.id), c, s.tdsRates)) {
      if (!f.expenseId) continue;
      const cur = m.get(f.expenseId);
      m.set(f.expenseId, { sev: !cur || order.indexOf(f.severity) < order.indexOf(cur.sev) ? f.severity : cur.sev, n: (cur?.n ?? 0) + 1 });
    }
    return m;
  }, [s.expenses, s.vendors, s.clients, s.tdsRates]);

  return (
    <div className="content">
      <PageHead title={tr('Review queue')} sub={tr('{n} bills awaiting CA review', { n: rows.length }) + (late ? ` · ${tr('{n} waiting more than 3 days', { n: late })}` : '')}>
        <select className="input sm" style={{ width: 'auto' }} aria-label={tr('Client')} value={clientFilter} onChange={(e) => setClientFilter(e.target.value)}>
          <option value="all">{tr('All clients')}</option>
          {s.clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select className="input sm" style={{ width: 'auto' }} aria-label={tr('Order')} value={order} onChange={(e) => setOrder(e.target.value as typeof order)}>
          <option value="oldest">{tr('Waiting longest first')}</option><option value="confidence">{tr('Lowest confidence first')}</option>
        </select>
        <select className="input sm" style={{ width: 'auto' }} aria-label={tr('Assigned to')} value={who} onChange={(e) => setWho(e.target.value as typeof who)}>
          <option value="all">{tr('Everyone')}</option><option value="mine">{tr('Assigned to me')}</option><option value="none">{tr('Not assigned')}</option>
        </select>
      </PageHead>
      <div className="card">
        {rows.length === 0 ? <Empty art="done">{tr('Queue is empty ✓')}</Empty> : (
          <div className="table-wrap">
            <table className="t num cards-sm">
              <thead><tr><th>{tr('Client')}</th><th>{tr('Date')}</th><th>{tr('Vendor')}</th><th>{tr('Suggested head')}</th><th>{tr('Flags')}</th><th>{tr('Waiting')}</th><th className="right">{tr('Total')}</th></tr></thead>
              <tbody>
                {rows.map((e) => (
                  <tr key={e.id} className="click" onClick={() => setOpen(e.id)}>
                    <td className="small">{clientName(e.clientId)}</td>
                    <td className="nowrap">{fmtDate(e.invoiceDate)}</td>
                    <td><b>{e.vendorName}</b><div className="tiny muted">{e.invoiceNo}</div></td>
                    <td>{tr(s.heads.find((h) => h.id === e.headId)?.name ?? '')}<div><Confidence v={e.headConfidence} /></div></td>
                    <td><div className="row wrap" style={{ gap: 4 }}>
                      {risk.get(e.id) && <span className={`badge ${{ high: 'danger', medium: 'warn', low: 'info' }[risk.get(e.id)!.sev]}`} title={tr('Bill risk check')}>⚠ {tr('Risk')} {risk.get(e.id)!.n}</span>}
                      {!(risk.get(e.id) || e.tdsAmount > 0 || e.rcmApplicable || e.blockedCode || e.isBackdated || e.entrySource === 'qr' || e.noImageReason || e.notDuplicateOf || e.resubmittedAt) && <span className="muted">—</span>}
                      {e.tdsAmount > 0 && <span className="badge info">{tr('TDS')}</span>}
                      {e.rcmApplicable && <span className="badge warn">{tr('RCM')}</span>}
                      {e.blockedCode && <span className="badge danger">17(5)</span>}
                      {e.isBackdated && <span className="badge warn">{tr('Past-dated')}</span>}
                      {e.entrySource === 'qr' && <span className="badge ok">{tr('QR')}</span>}
                      {e.noImageReason && <span className="badge danger">{tr('No bill')}</span>}
                      {e.notDuplicateOf && <span className="badge warn" title={tr('User confirmed this is a different bill from a look-alike')}>{tr('Look-alike')}</span>}
                      {e.resubmittedAt && <span className="badge info">{tr('Resubmitted')}</span>}
                      {e.sampleCheck && <span className="badge brand" title={tr('Passed the auto-approval rule — picked for a sample check')}>{tr('Sample check')}</span>}
                    </div></td>
                    <td className="nowrap"><span className={waitDays(e) > 3 ? 'badge warn' : 'small'}>{tr('{n} d', { n: waitDays(e) })}</span>
                      {e.assignedTo && <div className="tiny muted">{s.users.find((u) => u.id === e.assignedTo)?.name}</div>}</td>
                    <td className="right" style={{ fontWeight: 650 }}>{fmtInr(e.totalAmount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {autoDone.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-head"><h2>{tr('Approved by the auto-approval rule')}</h2><span className="tiny muted">{tr('Latest {n}', { n: autoDone.length })}</span></div>
          <div className="list">
            {autoDone.map((e) => (
              <div key={e.id} className="list-item small click" onClick={() => setOpen(e.id)} role="button" tabIndex={0} onKeyDown={(k) => k.key === 'Enter' && setOpen(e.id)}>
                <span className="badge ok">{tr('Auto')}</span><div className="grow"><b>{e.vendorName}</b> · {e.invoiceNo ?? '—'} · {fmtDate(e.invoiceDate)}<div className="tiny muted">{clientName(e.clientId)}</div></div><b className="num">{fmtInr(e.totalAmount)}</b>
              </div>
            ))}
          </div>
        </div>
      )}
      {current && <ReviewDrawer key={current.id} e={current} onClose={() => setOpen(undefined)} reviewers={reviewers} onAssign={(uid) => assignReview([current.id], uid)} />}
    </div>
  );
}

function Confidence({ v = 0 }: { v?: number }) {
  const tr = useTr();
  const tone = v >= 0.85 ? 'ok' : v >= 0.5 ? 'warn' : 'danger';
  return <span className={`badge ${tone}`}>{tr('{p}% sure', { p: Math.round(v * 100) })}</span>;
}

function ReviewDrawer({ e, onClose, reviewers = [], onAssign }: { e: Expense; onClose: () => void; reviewers?: { id: string; name: string }[]; onAssign?: (userId?: string) => void }) {
  const tr = useTr();
  const { s, reviewExpense } = useStore();
  const toast = useToast();
  const vendor = s.vendors.find((v) => v.id === e.vendorId);
  const client = s.clients.find((c) => c.id === e.clientId);
  const [f, setF] = useState<Expense>(e);
  const [note, setNote] = useState('');
  const head = s.heads.find((h) => h.id === f.headId);

  // re-run engine for explanations
  const text = `${e.vendorName} ${e.description ?? ''}`;
  const hs = suggestHead(text, e.hsnSac, s.heads);
  const fyOthers = !e.vendorId ? [] : s.expenses.filter((x) => x.id !== e.id && x.vendorId === e.vendorId && x.fyLabel === e.fyLabel && x.status !== 'rejected');
  const ytd = fyOthers.reduce((a, x) => a + x.taxableValue, 0);
  const ytdUntaxed = fyOthers.filter((x) => !x.tdsAmount).reduce((a, x) => a + x.taxableValue, 0);
  const ts = suggestTds(head, vendor, f.taxableValue, ytd, s.tdsRates, ytdUntaxed);
  const rs = suggestRcm(head, vendor, RCM_RULES);
  const is = suggestItc(head, text, !!vendor?.gstRegistered, BLOCKED_RULES);
  const rate = s.tdsRates.find((r) => r.code === f.tdsCode);

  function setHead(id: string) {
    const h = s.heads.find((x) => x.id === id);
    const t = suggestTds(h, vendor, f.taxableValue, ytd, s.tdsRates, ytdUntaxed);
    const r = suggestRcm(h, vendor, RCM_RULES);
    const i = suggestItc(h, text, !!vendor?.gstRegistered, BLOCKED_RULES);
    setF({ ...f, headId: id, tdsCode: t.code, tdsRatePct: t.ratePct, tdsAmount: t.amount, rcmApplicable: r.applicable, rcmCode: r.code,
      rcmRatePct: r.ratePct, rcmTax: r.applicable && r.ratePct ? round2((f.taxableValue * r.ratePct) / 100) : 0, itcEligible: i.eligible, blockedCode: i.blockedCode });
  }

  function setTdsCode(code: string) {
    const r = s.tdsRates.find((x) => x.code === code);
    const pct = r ? r.ratePct : 0;
    setF({ ...f, tdsCode: code || undefined, tdsRatePct: pct, tdsAmount: round2((f.taxableValue * pct) / 100) });
  }

  function setRcmRate(pct: number) {
    setF({ ...f, rcmRatePct: pct, rcmTax: round2((f.taxableValue * pct) / 100) });
  }

  function approve() {
    try {
      reviewExpense(e.id, { ...f, headConfidence: 1, reviewNote: note || undefined }, 'approved');
      toast(tr('Approved')); onClose();
    } catch (err) {
      if (err instanceof RuleError) toast(tr(err.message, err.vars), true); else throw err;
    }
  }
  function reject() {
    if (!note.trim()) { toast(tr('Add a note for the client'), true); return; }
    try {
      reviewExpense(e.id, { reviewNote: note }, 'rejected');
      toast(tr('Returned to client')); onClose();
    } catch (err) {
      if (err instanceof RuleError) toast(tr(err.message, err.vars), true); else throw err;
    }
  }

  return (
    <Drawer title={`${e.vendorName} · ${fmtInr(e.totalAmount)}`} onClose={onClose}
      footer={<><button className="btn danger" onClick={reject}><Icon name="x" size={16} /> {tr('Return')}</button><button className="btn ok grow" onClick={approve}><Icon name="check" size={16} /> {tr('Approve')}</button></>}>
      {e.autoApproved && <div className="banner ok small"><Icon name="check" size={16} />{tr('Approved by the auto-approval rule. You can still return it.')}</div>}
      {e.sampleCheck && <div className="banner info small"><Icon name="info" size={16} />{tr('Passed the auto-approval rule — picked for a sample check')}</div>}
      {e.status === 'submitted' && reviewers.length > 0 && onAssign && (
        <div className="field" style={{ maxWidth: 280 }}><label htmlFor="rv-assign">{tr('Assigned to')}</label>
          <select id="rv-assign" className="input sm" value={e.assignedTo ?? ''} onChange={(x) => onAssign(x.target.value || undefined)}>
            <option value="">{tr('Not assigned')}</option>
            {reviewers.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
          </select></div>
      )}
      {e.imageDataUrl ? <div className="photo-frame" style={{ maxHeight: 340 }}><img src={e.imageDataUrl} alt="Bill" /></div>
        : e.attachmentName ? <div className="banner info small"><Icon name="info" size={16} />{tr('File attached')}: {e.attachmentName}</div>
        : <div className="banner danger small"><Icon name="alert" size={16} /><span><b>{tr('No bill image.')}</b> Reason given: {e.noImageReason ?? 'none'}. Expense is allowable only with supporting evidence; ITC needs a valid tax invoice.</span></div>}
      {e.resubmittedAt && e.reviewNote && <div className="banner info small">{tr('Resubmitted after your note')}: “{e.reviewNote}”</div>}

      {e.cgst + e.sgst + e.igst > 0 && !vendor?.gstin && (
        <div className="banner danger small"><Icon name="alert" size={16} />{tr('GST charged on the bill but the vendor has no GSTIN on record — ITC cannot be claimed until the GSTIN is captured and appears in 2B.')}</div>
      )}
      <div className="card pad">
        <dl className="kv num small">
          <dt>{tr('Bill')}</dt><dd>{e.invoiceNo ?? '—'} · {fmtDate(e.invoiceDate)}</dd>
          <dt>{tr('Vendor GSTIN')}</dt><dd className="mono">{vendor?.gstin ?? 'Unregistered'}</dd>
          <dt>{tr('Vendor PAN')}</dt><dd className="mono">{vendor?.pan ?? '—'} {vendor?.panStatus && <span className={`badge ${vendor.panStatus === 'Operative' ? 'ok' : 'warn'}`}>{vendor.panStatus}</span>}</dd>
          <dt>{tr('Description')}</dt><dd>{e.description ?? '—'}</dd>
          <dt>{tr('YTD with vendor')}</dt><dd>{fmtInr(ytd)} (before this bill)</dd>
        </dl>
      </div>

      <AiCheck e={e} onUseHead={setHead} onUseTds={setTdsCode} onNarration={(n) => setF((x) => ({ ...x, narration: n.slice(0, 250) }))} onHsn={(h) => setF((x) => ({ ...x, hsnSac: h }))} />

      <div className="card pad stack suggest">
        <div className="row between"><h3 className="req">{tr('Expense head')}</h3><Confidence v={e.headConfidence} /></div>
        <select className="input" value={f.headId} onChange={(x) => setHead(x.target.value)}>
          {s.heads.map((h) => <option key={h.id} value={h.id}>{tr(h.name)}</option>)}
        </select>
        <span className="hint">Engine: {hs.reason}</span>
        <div className="field"><label htmlFor="rv-hsn">{tr('HSN / SAC')}</label><input id="rv-hsn" className="input mono sm" value={f.hsnSac ?? ''} onChange={(x) => setF({ ...f, hsnSac: x.target.value.replace(/\D/g, '').slice(0, 8) || undefined })} /></div>
      </div>

      <div className="card pad stack suggest">
        <h3>{tr('Amounts')}</h3>
        <div className="row">
          <div className="field grow"><label htmlFor="rv-taxableValue">{tr('Taxable')}</label><input id="rv-taxableValue" className="input sm num" value={f.taxableValue} onChange={(x) => setF({ ...f, taxableValue: Number(x.target.value) || 0 })} /></div>
          <div className="field grow"><label htmlFor="rv-discount">{tr('Discount')}</label><input id="rv-discount" className="input sm num" value={f.discount} onChange={(x) => setF({ ...f, discount: Number(x.target.value) || 0 })} /></div>
          <div className="field grow"><label htmlFor="rv-nontax">{tr('Charges without GST')}</label><input id="rv-nontax" className="input sm num" value={f.nonTaxableAmount ?? 0} onChange={(x) => setF({ ...f, nonTaxableAmount: Number(x.target.value) || undefined })} /></div>
        </div>
        <div className="row">
          <div className="field grow"><label htmlFor="rv-cgst">{tr('CGST')}</label><input id="rv-cgst" className="input sm num" value={f.cgst} onChange={(x) => setF({ ...f, cgst: Number(x.target.value) || 0 })} /></div>
          <div className="field grow"><label htmlFor="rv-sgst">{tr('SGST')}</label><input id="rv-sgst" className="input sm num" value={f.sgst} onChange={(x) => setF({ ...f, sgst: Number(x.target.value) || 0 })} /></div>
          <div className="field grow"><label htmlFor="rv-igst">{tr('IGST')}</label><input id="rv-igst" className="input sm num" value={f.igst} onChange={(x) => setF({ ...f, igst: Number(x.target.value) || 0 })} /></div>
        </div>
        {round2(f.taxableValue + (f.nonTaxableAmount ?? 0) + f.cgst + f.sgst + f.igst) !== f.totalAmount && <span className="hint err">{tr('Taxable + non-GST charges + GST ({sum}) ≠ bill total {total} — check round-off.', { sum: fmtInr(round2(f.taxableValue + (f.nonTaxableAmount ?? 0) + f.cgst + f.sgst + f.igst)), total: fmtInr(f.totalAmount) })}</span>}
        <label className="row small"><input type="checkbox" checked={!!f.ecoPaysTax} onChange={(x) => setF({ ...f, ecoPaysTax: x.target.checked || undefined, rcmApplicable: x.target.checked ? false : f.rcmApplicable, rcmTax: x.target.checked ? 0 : f.rcmTax })} /> {tr('GST paid by the app — Zomato, Swiggy, Uber, Ola etc. (section 9(5))')}</label>
        {f.ecoPaysTax && <span className="hint">{tr('The operator paid this GST, so there is no reverse charge for you. Check input credit: food and cab hire are commonly blocked under section 17(5).')}</span>}
      </div>

      <div className="card pad stack suggest">
        <h3>{tr('TDS')}</h3>
        <div className="row">
          <select className="input sm grow" value={f.tdsCode ?? ''} onChange={(x) => setTdsCode(x.target.value)}>
            <option value="">{tr('No TDS')}</option>
            {s.tdsRates.map((r) => <option key={r.code} value={r.code}>{r.description} ({r.ratePct}%)</option>)}
          </select>
          <input className="input sm num" style={{ width: 120 }} value={f.tdsAmount} onChange={(x) => setF({ ...f, tdsAmount: Number(x.target.value) || 0 })} aria-label={tr('TDS amount')} />
        </div>
        <span className="hint">Engine: {ts.reason}{ts.amount ? ` → ${fmtInr(ts.amount)}` : ''}</span>
        {rate && !rate.verified && <span className="hint" style={{ color: 'var(--warn)' }}>⚠ Rate {rate.code} not yet verified in Tax masters.</span>}
      </div>

      <div className="card pad stack suggest">
        <h3>{tr('GST treatment')}</h3>
        <label className="row small"><input type="checkbox" checked={f.rcmApplicable} onChange={(x) => setF({ ...f, rcmApplicable: x.target.checked, rcmCode: x.target.checked ? f.rcmCode ?? head?.rcmCode : undefined })} /> {tr('Reverse charge (RCM) applicable')}</label>
        {f.rcmApplicable && (
          <div className="row wrap">
            <select className="input sm grow" value={f.rcmCode ?? ''} onChange={(x) => { const r = RCM_RULES.find((y) => y.code === x.target.value); setF({ ...f, rcmCode: x.target.value, rcmRatePct: r?.defaultRatePct, rcmTax: r ? round2((f.taxableValue * r.defaultRatePct) / 100) : 0 }); }}>
              <option value="">{tr('Select category')}</option>
              {RCM_RULES.map((r) => <option key={r.code} value={r.code}>{r.description}</option>)}
            </select>
            <select className="input sm" style={{ width: 110 }} value={f.rcmRatePct ?? ''} onChange={(x) => setRcmRate(Number(x.target.value))} aria-label={tr('RCM GST rate')}>
              <option value="">{tr('Rate')}</option>
              {[5, 12, 18, 28].map((r) => <option key={r} value={r}>{r}%</option>)}
            </select>
            <span className="small num">{tr('GST payable:')} <b>{fmtInr(f.rcmTax)}</b></span>
          </div>
        )}
        <span className="hint">Engine: {rs.reason}</span>
        <label className="row small"><input type="checkbox" checked={!!f.itcEligible} onChange={(x) => setF({ ...f, itcEligible: x.target.checked, blockedCode: x.target.checked ? undefined : f.blockedCode })} /> {tr('ITC eligible')}</label>
        {!f.itcEligible && (
          <select className="input sm" value={f.blockedCode ?? ''} onChange={(x) => setF({ ...f, blockedCode: x.target.value || undefined })}>
            <option value="">{tr('Not blocked (other reason)')}</option>
            {BLOCKED_RULES.map((b) => <option key={b.code} value={b.code}>17(5): {b.description}</option>)}
          </select>
        )}
        <span className="hint">Engine: {is.reason}</span>
      </div>

      <div className="card pad stack suggest">
        <h3>{tr('Narration & project')}</h3>
        <div className="field"><label htmlFor="rv-narr">{tr('Narration')}</label>
          <textarea id="rv-narr" className="input" rows={2} maxLength={250} value={f.narration ?? ''} onChange={(x) => setF({ ...f, narration: x.target.value || undefined })} /></div>
        {(client?.costCentres.length ?? 0) > 0 && (
          <div className="field"><label htmlFor="rv-cc">{tr('Project / branch')}</label>
            <select id="rv-cc" className="input sm" value={f.costCentreId ?? ''} onChange={(x) => setF({ ...f, costCentreId: x.target.value || undefined })}>
              <option value="">{tr('None')}</option>
              {client!.costCentres.filter((c) => c.active || c.id === f.costCentreId).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select></div>
        )}
        {e.fileId && <button className="btn sm" style={{ alignSelf: 'flex-start' }} onClick={() => openDocument(e.fileId!)}><Icon name="download" size={14} /> {tr('Open original')}</button>}
      </div>

      <div className="field"><label htmlFor="rv-note" className="req">{tr('Note (required to return)')}</label><textarea id="rv-note" className="input" rows={2} value={note} onChange={(x) => setNote(x.target.value)} placeholder={tr('e.g. Photo unclear — please re-upload')} /></div>
    </Drawer>
  );
}
