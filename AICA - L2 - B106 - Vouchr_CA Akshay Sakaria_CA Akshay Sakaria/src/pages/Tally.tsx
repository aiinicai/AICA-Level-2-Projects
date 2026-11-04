import { useMemo, useState } from 'react';
import { useStore } from '../data/store';
import type { Payment } from '../data/types';
import { useTr } from '../i18n';
import { buildTallyXml } from '../lib/tallyXml';
import { monthKey, monthName, toIso, todayIso } from '../lib/dates';
import { fmtInr } from '../lib/money';
import { Empty, PageHead, useToast } from '../ui/common';
import { Icon } from '../ui/Icon';
import { modeLabel } from '../ui/PaymentLines';

export function Tally() {
  const { scoped, client, s, markPosted } = useStore();
  const tr = useTr();
  const toast = useToast();
  const ready = scoped.expenses.filter((e) => e.status === 'approved');
  const months = useMemo(() => [...new Set(ready.map((e) => monthKey(e.invoiceDate)))].sort(), [ready]);
  const [month, setMonth] = useState<string>('all');
  const [pending, setPending] = useState<{ e: string[]; p: string[]; n: string[]; file: string }>();
  const rows = ready.filter((e) => month === 'all' || monthKey(e.invoiceDate) <= month);
  // a payment goes to Tally once every bill it settles is posted (or being posted now); pure advances go straight away
  const inTally = new Set([...scoped.expenses.filter((e) => e.status === 'posted').map((e) => e.id), ...rows.map((e) => e.id)]);
  const pays = scoped.payments.filter((p) => !p.postedAt && p.allocations.every((a) => inTally.has(a.expenseId)) && (month === 'all' || monthKey(p.paidOn) <= month));
  const waiting = scoped.payments.filter((p) => !p.postedAt && !pays.includes(p)).length;
  // notes go once the bill they correct is posted (or being posted now); vendor-level notes go straight away
  const notes = scoped.vendorNotes.filter((n) => n.status === 'active' && !n.postedAt && (!n.expenseId || inTally.has(n.expenseId)) && (month === 'all' || monthKey(n.noteDate) <= month));
  const pendingReview = scoped.expenses.filter((e) => e.status === 'submitted').length;

  const today = todayIso();
  const prevMonth = (() => { const d = new Date(today + 'T00:00:00'); d.setDate(1); d.setMonth(d.getMonth() - 1); return toIso(d).slice(0, 7); })();
  const party = (vendorId: string | undefined, name: string) => s.vendors.find((v) => v.id === vendorId)?.tallyLedger || name;
  const payLedger = (p: Payment) => client?.bankAccounts.find((a) => a.id === p.accountId)?.tallyLedger ?? (p.mode === 'cash' ? client?.cashLedger ?? 'Cash' : 'Bank');

  function download() {
    if (!client) return;
    try {
      const xml = buildTallyXml(client.tallyCompany ?? client.name, rows, s.heads, { payments: pays, allPayments: scoped.payments, allExpenses: scoped.expenses, partyLedger: party, paymentLedger: payLedger, notes, costCentreOf: (e) => client.costCentres.find((c) => c.id === e.costCentreId)?.name });
      const file = `${client.name.replace(/\W+/g, '_')}_${month === 'all' ? 'approved' : month}_tally.xml`;
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([xml], { type: 'application/xml' }));
      a.download = file;
      a.click();
      URL.revokeObjectURL(a.href);
      setPending({ e: rows.map((x) => x.id), p: pays.map((x) => x.id), n: notes.map((x) => x.id), file });
    } catch (err) {
      toast((err as Error).message, true);
    }
  }

  if (client?.tallyMode === 'none') {
    return (
      <div className="content narrow">
        <PageHead title={tr('Tally posting')} />
        <div className="banner info"><Icon name="info" size={18} />{tr('This client does not maintain Tally. All data is kept in the Google Sheet MIS and the Reports page instead.')}</div>
      </div>
    );
  }

  return (
    <div className="content stack">
      <PageHead title={tr('Tally posting')} sub={`${tr('Company')}: ${client?.tallyCompany ?? client?.name} · ${client?.tallyMode === 'bridge' ? tr('Bridge (auto)') : tr('XML file import')}`} />
      <div className="banner warn"><Icon name="alert" size={18} /><span>{tr('Deadline: post {month} by the 25th of this month.', { month: monthName(prevMonth) })} {pendingReview > 0 && tr("{n} bill(s) still awaiting CA review won't be included.", { n: pendingReview })}</span></div>

      {pending && (
        <div className="card pad stack" style={{ borderColor: 'var(--brand)' }}>
          <b>{tr('Downloaded')} {pending.file}</b>
          <div className="small">{tr('Import it in Tally, then confirm here. Entries are marked “Posted” only after you confirm, so a failed import never hides bills.')}</div>
          <div className="row wrap">
            <button className="btn ok" onClick={() => { markPosted(pending.e, pending.p, pending.n); setPending(undefined); toast(tr('Marked as posted')); }}><Icon name="check" size={16} /> {tr('Import succeeded — mark posted')}</button>
            <button className="btn" onClick={() => setPending(undefined)}>{tr('Import failed — keep pending')}</button>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-head">
          <h2>{tr('Ready to post')}</h2>
          <div className="row">
            <select className="input sm" style={{ width: 'auto' }} value={month} onChange={(e) => setMonth(e.target.value)} aria-label={tr('Up to month')}>
              <option value="all">{tr('All months')}</option>
              {months.map((m) => <option key={m} value={m}>{tr('Up to')} {monthName(m)}</option>)}
            </select>
            <button className="btn primary sm" disabled={!rows.length && !pays.length && !notes.length} onClick={download}><Icon name="download" size={16} /> {tr('Download Tally XML')}</button>
          </div>
        </div>
        {rows.length === 0 && pays.length === 0 && notes.length === 0 ? <Empty art="done">{tr('Nothing to post')}</Empty> : (
          <div className="table-wrap">
            <table className="t num cards-sm">
              <thead><tr><th>{tr('Voucher')}</th><th>{tr('Date')}</th><th>{tr('Party ledger')}</th><th>{tr('Debit / bank ledger')}</th><th className="right">{tr('Amount')}</th><th className="right">TDS / RCM</th></tr></thead>
              <tbody>
                {rows.map((e) => (
                  <tr key={e.id}>
                    <td><span className="badge">{tr('Journal')}</span></td><td>{e.invoiceDate}</td><td>{party(e.vendorId, e.vendorName)}</td>
                    <td>{s.heads.find((h) => h.id === e.headId)?.tallyLedger}</td>
                    <td className="right">{fmtInr(e.totalAmount)}</td>
                    <td className="right small">{e.tdsAmount ? `TDS ${fmtInr(e.tdsAmount)}` : ''}{e.rcmTax ? ` RCM ${fmtInr(e.rcmTax)}` : ''}{!e.tdsAmount && !e.rcmTax ? '—' : ''}</td>
                  </tr>
                ))}
                {pays.map((p) => (
                  <tr key={p.id}>
                    <td><span className="badge info">{tr('Payment')}</span></td><td>{p.paidOn}</td><td>{party(p.vendorId, p.vendorName)}</td>
                    <td>{payLedger(p)} <span className="tiny muted">({tr(modeLabel(p.mode))})</span></td><td className="right">{fmtInr(p.amount)}</td>
                    <td className="right small">{p.allocations.length ? tr('{n} bill(s)', { n: p.allocations.length }) : tr('Advance')}</td>
                  </tr>
                ))}
                {notes.map((n) => (
                  <tr key={n.id}>
                    <td><span className={`badge ${n.kind === 'credit' ? 'warn' : ''}`}>{tr(n.kind === 'credit' ? 'Debit Note' : 'Journal')}</span></td><td>{n.noteDate}</td><td>{party(n.vendorId, n.vendorName)}</td>
                    <td>{tr(n.kind === 'credit' ? 'Credit note from vendor' : 'Debit note from vendor')} {n.noteNo}</td>
                    <td className="right">{n.kind === 'credit' ? '−' : ''}{fmtInr(n.totalAmount)}</td><td className="right small">—</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {waiting > 0 && <div className="hint" style={{ padding: '0 16px 12px' }}>{tr('{n} payment(s) wait until their bills are approved and posted.', { n: waiting })}</div>}
      </div>

      <div className="card pad stack small">
        <h3>{tr('How to import (2 steps)')}</h3>
        <div>1. {tr('In TallyPrime: Import → Transactions → choose the downloaded XML.')}</div>
        <div>2. {tr('Check the import summary. Any ledger that does not exist in Tally is reported — create it once and re-import.')}</div>
        <div className="muted">{tr('Bridge mode (automatic posting via Tally’s XML port, on the client PC or on AWS-hosted Tally) is planned for phase 2.')}</div>
      </div>
    </div>
  );
}
