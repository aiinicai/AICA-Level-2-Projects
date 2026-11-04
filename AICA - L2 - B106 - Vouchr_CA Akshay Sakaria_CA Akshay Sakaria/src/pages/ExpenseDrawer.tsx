import { useState } from 'react';
import { NoteDrawer } from './NoteDrawer';
import { REASON_LABEL } from '../lib/vendorNotes';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../data/store';
import type { Expense } from '../data/types';
import { useTr } from '../i18n';
import { billStatus, dueDate, netPayable, outstanding } from '../lib/alerts';
import { fmtDate, todayIso } from '../lib/dates';
import { fmtInr } from '../lib/money';
import { BillStatusBadge, Drawer, StatusBadge, useAttempt, useToast, useAskText } from '../ui/common';
import { openDocument } from '../lib/storage';
import { Icon } from '../ui/Icon';
import { modeLabel } from '../ui/PaymentLines';
import { PayDrawer } from './PayDrawer';

const FLAG_LABEL: Record<string, string> = {
  cash_limit: 'Cash above daily limit', paid_before_bill_date: 'Paid before bill date', backdated_payment: 'Backdated',
  adv_tds_section_differs: 'Advance TDS section differs from the bill — CA to check'
};

export function ExpenseDrawer({ e, onClose }: { e: Expense; onClose: () => void }) {
  const st = useStore();
  const { me, s, client } = st;
  const tr = useTr();
  const nav = useNavigate();
  const attempt = useAttempt();
  const [paying, setPaying] = useState(false);
  const [noting, setNoting] = useState(false);
  const vendor = s.vendors.find((v) => v.id === e.vendorId);
  const terms = vendor?.creditDays ?? client?.defaultCreditDays ?? 30;
  const pays = st.scoped.payments.filter((p) => p.allocations.some((a) => a.expenseId === e.id));
  const due = outstanding(e, st.scoped.payments);
  const head = s.heads.find((h) => h.id === e.headId);
  const staff = me?.role === 'sub_user';
  const canFix = (e.status === 'rejected' || e.status === 'draft') && (!staff || e.createdBy === me?.id);
  const acct = (id?: string) => client?.bankAccounts.find((a) => a.id === id)?.name;
  const centre = client?.costCentres.find((c) => c.id === e.costCentreId);
  const toast = useToast();
  const askText = useAskText();

  if (paying) return <PayDrawer vendorId={e.vendorId} preselect={[e.id]} onClose={() => setPaying(false)} />;
  if (noting && e.vendorId) return <NoteDrawer vendorId={e.vendorId} expenseId={e.id} onClose={() => setNoting(false)} />;
  const notes = st.scoped.vendorNotes.filter((n) => n.expenseId === e.id && n.status === 'active');

  return (
    <Drawer title={e.vendorName || tr('Draft')} onClose={onClose}>
      <div className="row between wrap">
        <div className="row"><StatusBadge status={e.status} />{e.status !== 'draft' && <BillStatusBadge status={billStatus(e, st.scoped.payments, todayIso(), terms)} />}</div>
        {e.isBackdated && <span className="badge warn">{tr('Past-dated entry')}</span>}
      </div>
      {e.reviewNote && <div className="banner warn">{tr('CA note')}: {e.reviewNote}</div>}
      {canFix && <button className="btn primary lg block" onClick={() => nav(`/capture?edit=${e.id}`)}>{e.status === 'draft' ? tr('Complete & submit') : tr('Fix & resubmit')}</button>}
      {e.imageDataUrl && <div className="photo-frame"><img src={e.imageDataUrl} alt={tr('Bill')} /></div>}
      {e.fileId && (
        <div className="row between wrap small">
          <span className="muted ellipsis" title={e.filePath}>📁 {e.filePath}</span>
          <button className="btn sm" onClick={async () => { if (!(await openDocument(e.fileId!))) toast(tr('Original file not found on this device'), true); }}><Icon name="download" size={14} /> {tr('Open original')}</button>
        </div>
      )}
      {!e.imageDataUrl && e.attachmentName && <div className="banner info small"><Icon name="info" size={16} />{tr('File attached')}: {e.attachmentName}</div>}
      {e.noImageReason && <div className="banner warn small"><Icon name="alert" size={16} />{tr('No bill image')} — {e.noImageReason}</div>}
      <div className="card pad">
        <dl className="kv num">
          <dt>{tr('Bill no.')}</dt><dd>{e.invoiceNo ?? '—'}</dd>
          <dt>{tr('Bill date')}</dt><dd>{fmtDate(e.invoiceDate)}</dd>
          <dt>{tr('Due date')}</dt><dd>{fmtDate(dueDate(e, terms))} <span className="muted small">({tr('{n} days credit', { n: terms })})</span></dd>
          {e.discount > 0 && <><dt>{tr('Discount')}</dt><dd>{fmtInr(e.discount)}</dd></>}
          <dt>{tr('Taxable value')}</dt><dd>{fmtInr(e.taxableValue)}</dd>
          <dt>GST</dt><dd>{fmtInr(e.cgst + e.sgst + e.igst)} {e.igst ? '(IGST)' : e.cgst ? '(CGST+SGST)' : ''}</dd>
          {(e.nonTaxableAmount ?? 0) > 0 && <><dt>{tr('Charges without GST')}</dt><dd>{fmtInr(e.nonTaxableAmount!)}</dd></>}
          <dt>{tr('Bill total')}</dt><dd>{fmtInr(e.totalAmount)}</dd>
          {e.ecoPaysTax && <><dt>{tr('GST paid by')}</dt><dd>{tr('App / e-commerce operator (section 9(5))')}{e.ecoGstin ? ` · ${e.ecoGstin}` : ''}</dd></>}
          {centre && <><dt>{tr('Project / branch')}</dt><dd>{centre.name}</dd></>}
          {e.narration && <><dt>{tr('Narration')}</dt><dd style={{ fontWeight: 400 }}>{e.narration}</dd></>}
          {!staff && <>
            <dt>{tr('Expense head')}</dt><dd>{head ? tr(head.name) : '—'}</dd>
            <dt>HSN / SAC</dt><dd>{e.hsnSac ?? '—'}</dd>
            <dt>TDS</dt><dd>{e.tdsAmount ? `${fmtInr(e.tdsAmount)} (${e.tdsCode} @ ${e.tdsRatePct}%)` : tr('Nil')}</dd>
            <dt>RCM</dt><dd>{e.rcmApplicable ? `${tr('Yes')} — ${e.rcmCode} · ${tr('GST payable')} ${fmtInr(e.rcmTax)}` : tr('No')}</dd>
            <dt>ITC</dt><dd>{e.itcEligible ? tr('Eligible') : e.blockedCode ? `${tr('Blocked')} (${e.blockedCode})` : tr('Not available')}</dd>
          </>}
          <dt>{tr('Net payable')}</dt><dd>{fmtInr(netPayable(e))}</dd>
          <dt>{tr('Balance due')}</dt><dd style={{ color: due > 0 ? 'var(--danger)' : 'var(--ok)' }}>{due > 0 ? fmtInr(due) : tr('Paid')}</dd>
        </dl>
      </div>

      <div className="card">
        <div className="card-head"><h3>{tr('Payments')}</h3><span className="muted small">{tr('{n} payment(s)', { n: pays.length })}</span></div>
        {pays.length === 0 ? <div className="empty small">{tr('No payment recorded')}</div> : (
          <div className="list">
            {pays.map((p) => {
              const part = p.allocations.filter((a) => a.expenseId === e.id).reduce((s2, a) => s2 + a.amount, 0);
              return (
                <div key={p.id} className="list-item small" style={{ alignItems: 'flex-start' }}>
                  <span className="badge">{tr(modeLabel(p.mode))}</span>
                  <div className="grow">
                    {fmtDate(p.paidOn)}{p.ref ? ` · ${p.ref}` : ''}{acct(p.accountId) ? ` · ${acct(p.accountId)}` : ''}
                    {part < p.amount && <div className="tiny muted">{tr('Part of a {amount} payment', { amount: fmtInr(p.amount) })}</div>}
                    <div className="row wrap" style={{ gap: 4, marginTop: 2 }}>
                      {(p.flags ?? []).map((f) => <span key={f} className={`badge ${f === 'cash_limit' ? 'danger' : 'warn'}`}>{tr(FLAG_LABEL[f] ?? f)}</span>)}
                      {p.postedAt && <span className="badge brand">{tr('In Tally')}</span>}
                      {p.source === 'bank_import' && <span className="badge info">{tr('From bank statement')}</span>}
                    </div>
                  </div>
                  <b className="num">{fmtInr(part)}</b>
                  {!staff && !p.postedAt && (
                    <button className="icon-btn" aria-label={tr('Cancel payment')} title={tr('Cancel payment')} onClick={async () => {
                      const why = await askText(tr('Cancel this payment? It stays in the audit trail.'), { label: tr('Reason'), ok: tr('Cancel payment'), danger: true });
                      if (why !== null) attempt(() => st.voidPayment(p.id, why), 'Payment cancelled');
                    }}><Icon name="x" size={16} /></button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {(notes.length > 0 || (!staff && e.vendorId && e.status !== 'rejected' && e.status !== 'draft')) && (
        <div className="card">
          <div className="card-head"><h3>{tr('Credit / debit notes')}</h3>
            {!staff && e.vendorId && e.status !== 'rejected' && e.status !== 'draft' && <button className="linkish small" onClick={() => setNoting(true)}>{tr('+ Record a note')}</button>}</div>
          {notes.length === 0 ? <div className="empty small">{tr('None')}</div> : (
            <div className="list">
              {notes.map((n) => (
                <div key={n.id} className="list-item small" style={{ alignItems: 'flex-start' }}>
                  <span className={`badge ${n.kind === 'credit' ? 'warn' : ''}`}>{tr(n.kind === 'credit' ? 'Credit note' : 'Debit note')}</span>
                  <div className="grow">{n.noteNo} · {fmtDate(n.noteDate)}
                    <div className="tiny muted">{tr(REASON_LABEL[n.reason])}{n.postedAt ? ` · ${tr('In Tally')}` : ''}</div>
                    {n.flags?.includes('tds_on_original') && <span className="badge warn">{tr('TDS on original amount — CA to check')}</span>}</div>
                  <b className="num">{n.kind === 'credit' ? '−' : '+'}{fmtInr(n.totalAmount)}</b>
                  {!staff && !n.postedAt && (
                    <button className="icon-btn" aria-label={tr('Cancel note')} title={tr('Cancel note')} onClick={async () => {
                      const why = await askText(tr('Cancel this note? It stays in the audit trail.'), { label: tr('Reason'), ok: tr('Cancel note'), danger: true });
                      if (why !== null) attempt(() => st.voidVendorNote(n.id, why), 'Note cancelled');
                    }}><Icon name="x" size={16} /></button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {due < 0 && <div className="banner info small"><Icon name="info" size={16} />{tr('After the credit note(s), the vendor owes {amt} back on this bill — get a refund or adjust it against the next bill.', { amt: fmtInr(-due) })}</div>}
      {due > 0 && e.status !== 'rejected' && e.status !== 'draft' && (
        <button className="btn primary lg block" onClick={() => setPaying(true)}>{tr('Record payment')}</button>
      )}
    </Drawer>
  );
}
