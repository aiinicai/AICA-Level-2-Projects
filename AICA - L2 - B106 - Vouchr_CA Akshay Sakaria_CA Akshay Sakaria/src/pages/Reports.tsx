// Registers for audit / GST annual return work. Same columns feed the client's Google Sheet mirror.
import { DpdpNote } from '../ui/DpdpNote';
import { useMemo, useState } from 'react';
import { useStore } from '../data/store';
import type { Expense } from '../data/types';
import { useTr } from '../i18n';
import { downloadCsv } from '../lib/csv';
import { ageBucket, dueDate, outstanding, paidAmount, unallocated } from '../lib/alerts';
import { daysBetween, fyLabel, todayIso } from '../lib/dates';
import { fmtInr, round2 } from '../lib/money';
import { PageHead } from '../ui/common';
import { Icon } from '../ui/Icon';
import { modeLabel } from '../ui/PaymentLines';

export function Reports() {
  const { scoped, s, client } = useStore();
  const tr = useTr();
  const today = todayIso();
  const fys = useMemo(() => [...new Set([fyLabel(today), ...scoped.expenses.map((e) => e.fyLabel)])].sort().reverse(), [scoped.expenses, today]);
  const [fy, setFy] = useState(fys[0]);
  const [vendorId, setVendorId] = useState('');
  const ex = scoped.expenses.filter((e) => e.fyLabel === fy && e.status !== 'rejected' && e.status !== 'draft');
  const head = (id?: string) => s.heads.find((h) => h.id === id)?.name ?? '';
  const vendor = (id?: string) => s.vendors.find((v) => v.id === id);
  const terms = (e: Expense) => vendor(e.vendorId)?.creditDays ?? client?.defaultCreditDays ?? 30;
  const acct = (id?: string) => client?.bankAccounts.find((a) => a.id === id)?.name ?? '';
  const prefix = `${client?.name.replace(/\W+/g, '_')}_FY${fy}`;

  const hsn = useMemo(() => {
    const m = new Map<string, { n: number; taxable: number; igst: number; cgst: number; sgst: number }>();
    for (const e of ex) {
      const k = e.hsnSac || 'NOT CAPTURED';
      const r = m.get(k) ?? { n: 0, taxable: 0, igst: 0, cgst: 0, sgst: 0 };
      m.set(k, { n: r.n + 1, taxable: round2(r.taxable + e.taxableValue), igst: round2(r.igst + e.igst), cgst: round2(r.cgst + e.cgst), sgst: round2(r.sgst + e.sgst) });
    }
    return [...m].sort((a, b) => b[1].taxable - a[1].taxable);
  }, [ex]);
  const missingHsn = ex.filter((e) => !e.hsnSac && e.cgst + e.sgst + e.igst > 0).length;
  const noBill = ex.filter((e) => e.noImageReason);
  const fyPays = scoped.payments.filter((p) => fyLabel(p.paidOn) === fy);

  function vendorStatement() {
    const v = vendor(vendorId);
    if (!v) return;
    const lines: { date: string; text: string; debit: number; credit: number }[] = [
      ...scoped.expenses.filter((e) => e.vendorId === v.id && e.status !== 'rejected' && e.status !== 'draft').map((e) => ({ date: e.invoiceDate, text: `Bill ${e.invoiceNo ?? ''}${e.tdsAmount ? ` (TDS ${e.tdsAmount})` : ''}`, debit: 0, credit: round2(e.totalAmount - e.tdsAmount) })),
      ...scoped.payments.filter((p) => p.vendorId === v.id).map((p) => ({ date: p.paidOn, text: `${modeLabel(p.mode)} ${p.ref ?? ''}${unallocated(p) > 0 ? ` (advance ${unallocated(p)})` : ''}`, debit: p.amount, credit: 0 }))
    ].sort((a, b) => a.date.localeCompare(b.date));
    let bal = 0;
    downloadCsv(`${prefix}_${v.name.replace(/\W+/g, '_')}_statement.csv`, ['Date', 'Particulars', 'Paid (Dr)', 'Billed (Cr)', 'Balance payable'],
      lines.map((l) => { bal = round2(bal + l.credit - l.debit); return [l.date, l.text, l.debit || '', l.credit || '', bal]; }));
  }

  const reports = [
    { title: 'Expense register', desc: tr('{n} bills with head, GST split, TDS, RCM, ITC, payment status', { n: ex.length }), run: () => downloadCsv(`${prefix}_expense_register.csv`,
      ['Date', 'Vendor', 'GSTIN', 'PAN', 'Bill no', 'HSN/SAC', 'Project / branch', 'Narration', 'Drive file', 'Head', 'Gross', 'Discount', 'Taxable', 'CGST', 'SGST', 'IGST', 'Total', 'TDS code', 'TDS', 'RCM', 'RCM tax', 'ITC eligible', 'Blocked 17(5)', 'Status', 'Paid', 'Balance', 'Bill image'],
      ex.map((e) => { const v = vendor(e.vendorId); return [e.invoiceDate, e.vendorName, v?.gstin, v?.pan, e.invoiceNo, e.hsnSac, client?.costCentres.find((c) => c.id === e.costCentreId)?.name, e.narration, e.filePath, head(e.headId), e.grossAmount, e.discount, e.taxableValue, e.cgst, e.sgst, e.igst, e.totalAmount,
        e.tdsCode, e.tdsAmount, e.rcmApplicable ? e.rcmCode : '', e.rcmTax, e.itcEligible ? 'Y' : 'N', e.blockedCode, e.status, paidAmount(e.id, scoped.payments), outstanding(e, scoped.payments), e.imageDataUrl || e.attachmentName ? 'Yes' : `No — ${e.noImageReason ?? ''}`]; })) },
    { title: 'HSN / SAC-wise summary (inward)', desc: tr('{n} codes', { n: hsn.length }) + (missingHsn ? ` · ${tr('{n} GST bills missing HSN', { n: missingHsn })}` : ''), run: () => downloadCsv(`${prefix}_hsn_summary.csv`,
      ['HSN/SAC', 'Bills', 'Taxable', 'IGST', 'CGST', 'SGST'], hsn.map(([k, r]) => [k, r.n, r.taxable, r.igst, r.cgst, r.sgst])) },
    { title: 'Payment register', desc: tr('Every payment with mode, account, bills settled and audit flags'), run: () => downloadCsv(`${prefix}_payments.csv`,
      ['Paid on', 'Vendor', 'Mode', 'Account', 'Reference', 'Amount', 'Bills settled', 'Advance', 'Flags', 'In Tally'],
      fyPays.map((p) => [p.paidOn, p.vendorName, modeLabel(p.mode), acct(p.accountId), p.ref, p.amount,
        p.allocations.map((a) => `${scoped.expenses.find((e) => e.id === a.expenseId)?.invoiceNo ?? '?'}:${a.amount}`).join(' | '), unallocated(p), (p.flags ?? []).join(' '), p.postedAt ? 'Y' : 'N'])) },
    { title: 'Payables ageing', desc: tr('Unpaid bills by days past due date'), run: () => downloadCsv(`${prefix}_ageing.csv`,
      ['Vendor', 'Bill no', 'Bill date', 'Due date', 'Days late', 'Bucket', 'Balance'],
      scoped.expenses.filter((e) => e.status !== 'rejected' && e.status !== 'draft' && outstanding(e, scoped.payments) > 0)
        .map((e) => [e.vendorName, e.invoiceNo, e.invoiceDate, dueDate(e, terms(e)), Math.max(daysBetween(dueDate(e, terms(e)), today), 0), ageBucket(e, today, terms(e)), outstanding(e, scoped.payments)])) },
    { title: 'Project / branch-wise spend', desc: tr('Spend, GST and TDS by project or branch'), run: () => {
      const m = new Map<string, { n: number; taxable: number; gst: number; tds: number }>();
      for (const e of ex) {
        const k = client?.costCentres.find((c) => c.id === e.costCentreId)?.name ?? 'Not tagged';
        const r = m.get(k) ?? { n: 0, taxable: 0, gst: 0, tds: 0 };
        m.set(k, { n: r.n + 1, taxable: round2(r.taxable + e.taxableValue), gst: round2(r.gst + e.cgst + e.sgst + e.igst), tds: round2(r.tds + e.tdsAmount) });
      }
      downloadCsv(`${prefix}_project_branch.csv`, ['Project / branch', 'Bills', 'Taxable', 'GST', 'TDS'], [...m].map(([k, r]) => [k, r.n, r.taxable, r.gst, r.tds]));
    } },
    { title: 'Bills without image', desc: tr('{n} entries with the reason given', { n: noBill.length }), run: () => downloadCsv(`${prefix}_no_bill_image.csv`,
      ['Date', 'Vendor', 'Bill no', 'Total', 'Reason', 'Status'], noBill.map((e) => [e.invoiceDate, e.vendorName, e.invoiceNo, e.totalAmount, e.noImageReason, e.status])) }
  ];

  return (
    <div className="content stack" style={{ maxWidth: 860 }}>
      <PageHead title={tr('Reports')} sub={client?.name}>
        <select className="input sm" style={{ width: 'auto' }} value={fy} onChange={(e) => setFy(e.target.value)} aria-label={tr('Financial year')}>
          {fys.map((f) => <option key={f} value={f}>FY {f}</option>)}
        </select>
      </PageHead>
      <DpdpNote kind="export" />
      <div className="card">
        <div className="list">
          {reports.map((r) => (
            <div key={r.title} className="list-item">
              <div className="grow"><b>{tr(r.title)}</b><div className="small muted">{r.desc}</div></div>
              <button className="btn sm" onClick={r.run}><Icon name="download" size={14} /> CSV</button>
            </div>
          ))}
          <div className="list-item wrap">
            <div className="grow"><b>{tr('Vendor statement')}</b><div className="small muted">{tr('Bills, payments, advances and running balance for one vendor')}</div></div>
            <select className="input sm" style={{ width: 'auto' }} value={vendorId} onChange={(e) => setVendorId(e.target.value)} aria-label={tr('Vendor')}>
              <option value="">{tr('Choose vendor')}</option>
              {scoped.vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
            </select>
            <button className="btn sm" disabled={!vendorId} onClick={vendorStatement}><Icon name="download" size={14} /> CSV</button>
          </div>
        </div>
      </div>
      <div className="card">
        <div className="card-head"><h2>{tr('HSN / SAC summary')}</h2>{missingHsn > 0 && <span className="badge warn">{tr('{n} GST bills missing HSN', { n: missingHsn })}</span>}</div>
        <div className="table-wrap">
          <table className="t num cards-sm">
            <thead><tr><th>HSN/SAC</th><th className="right">{tr('Bills')}</th><th className="right">{tr('Taxable')}</th><th className="right">IGST</th><th className="right">CGST+SGST</th></tr></thead>
            <tbody>{hsn.map(([k, r]) => (
              <tr key={k}><td className="mono">{k === 'NOT CAPTURED' ? tr('Not captured') : k}</td><td className="right">{r.n}</td><td className="right">{fmtInr(r.taxable)}</td><td className="right">{fmtInr(r.igst)}</td><td className="right">{fmtInr(r.cgst + r.sgst)}</td></tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
