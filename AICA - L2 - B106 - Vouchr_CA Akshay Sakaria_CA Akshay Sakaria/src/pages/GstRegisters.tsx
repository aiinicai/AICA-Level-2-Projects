// GST registers: reverse-charge GST by the month it is due, and the 180-day ITC reversal register (lib/gstRegisters.ts).
import { useMemo, useState } from 'react';
import { useStore } from '../data/store';
import { useTr } from '../i18n';
import { downloadCsv } from '../lib/csv';
import { fmtDate, monthName, todayIso } from '../lib/dates';
import { itcRegister, rcmLiability, type ItcStatus } from '../lib/gstRegisters';
import { fmtInr, round2 } from '../lib/money';
import { RCM_RULES } from '../data/masters';
import { Empty, PageHead, useAttempt } from '../ui/common';
import { Icon } from '../ui/Icon';

const BASIS: Record<string, string> = { payment: 'Paid on this date (earlier)', after_60_days: 'Day after 60 days from the invoice', after_30_days: 'Day after 30 days from the invoice' };

const STATUS: Record<ItcStatus, [string, string]> = {
  not_due: ['Watch — unpaid, 180 days not over', 'info'], paid_in_time: ['Paid in time', 'ok'], reverse: ['Reverse ITC', 'danger'],
  reversed: ['Reversed — waiting for payment', 'warn'], reclaim: ['Paid — re-claim ITC', 'ok'], reclaimed: ['Re-claimed', 'ok']
};

export function GstRegisters() {
  const st = useStore();
  const { scoped, me } = st;
  const tr = useTr();
  const attempt = useAttempt();
  const today = todayIso();
  const isCA = me?.role === 'super_admin';
  const rcm = useMemo(() => rcmLiability(scoped.expenses, scoped.payments, RCM_RULES, today), [scoped.expenses, scoped.payments, today]);
  const itc = useMemo(() => itcRegister(scoped.expenses, scoped.payments, scoped.itcReversals, today), [scoped.expenses, scoped.payments, scoped.itcReversals, today]);
  const byMonth = [...rcm.reduce((m, r) => m.set(r.month, round2((m.get(r.month) ?? 0) + r.amount)), new Map<string, number>())].sort();
  const [month, setMonth] = useState<Record<string, string>>({});

  const exportRcm = () => downloadCsv('rcm_by_month.csv', ['Month (GSTR-3B 3.1(d))', 'Date due', 'Vendor', 'Bill no', 'RCM GST', 'Basis', 'Supply'],
    rcm.map((r) => [r.month, r.date, r.vendorName, r.invoiceNo ?? '', r.amount, BASIS[r.basis], r.supply]));
  const exportItc = () => downloadCsv('itc_180_day_register.csv', ['Vendor', 'Bill no', 'Bill date', 'Day 180', 'ITC on bill', 'Unpaid at day 180', 'ITC to reverse', 'Reverse in', 'Status', 'Reversed', 'Reversed in', 'Re-claimed', 'Re-claimed in'],
    itc.map((r) => [r.vendorName, r.invoiceNo ?? '', r.invoiceDate, r.day180, r.itc, r.unpaidAt180, r.reverseAmount, r.reverseMonth, STATUS[r.status][0], r.record?.amount ?? '', r.record?.reversedIn ?? '', r.record?.reclaimedAmount ?? '', r.record?.reclaimedIn ?? '']));

  return (
    <div className="content stack">
      <PageHead title={tr('GST registers')} sub={tr('Reverse-charge GST by month, and ITC on bills unpaid after 180 days')} />
      <div className="banner warn small"><Icon name="alert" size={16} /><span>{tr('Rules: CGST Act s.13(3) / s.12(3) for when reverse-charge GST is due, and s.16(2) second proviso for the 180-day ITC reversal. The CA confirms the rules and the figures before filing.')}</span></div>

      <div className="card">
        <div className="card-head"><h2>{tr('Reverse-charge (RCM) GST by month')}</h2>
          <button className="btn sm" disabled={!rcm.length} onClick={exportRcm}><Icon name="download" size={14} /> CSV</button></div>
        {rcm.length === 0 ? <Empty>{tr('No reverse-charge bills')}</Empty> : (
          <>
            <div className="row wrap" style={{ padding: '0 16px', gap: 8 }}>
              {byMonth.map(([m, amt]) => <span key={m} className="badge">{monthName(m)} · {fmtInr(amt)}</span>)}
            </div>
            <div className="table-wrap">
              <table className="t num cards-sm">
                <thead><tr><th>{tr('Due on')}</th><th>{tr('Vendor')}</th><th>{tr('Bill no.')}</th><th>{tr('Why this date')}</th><th className="right">{tr('RCM GST')}</th></tr></thead>
                <tbody>{rcm.map((r, i) => (
                  <tr key={i}><td>{fmtDate(r.date)}{r.upcoming && <span className="badge info" style={{ marginLeft: 6 }}>{tr('Upcoming')}</span>}</td>
                    <td>{r.vendorName}</td><td>{r.invoiceNo ?? '—'}</td>
                    <td className="small">{tr(BASIS[r.basis])}
                      {r.receiptUnknown && <div className="tiny muted">{tr('Goods receipt date not recorded — if the goods arrived earlier, GST was due earlier.')}</div>}</td>
                    <td className="right">{fmtInr(r.amount)}</td></tr>
                ))}</tbody>
              </table>
            </div>
            <div className="hint" style={{ padding: '0 16px 12px' }}>{tr('Pay in cash with GSTR-3B for that month (table 3.1(d)); the input credit is claimed after paying.')}</div>
          </>
        )}
      </div>

      <div className="card">
        <div className="card-head"><h2>{tr('ITC 180-day register')}</h2>
          <button className="btn sm" disabled={!itc.length} onClick={exportItc}><Icon name="download" size={14} /> CSV</button></div>
        {itc.length === 0 ? <Empty art="done">{tr('No bills unpaid near or past 180 days')}</Empty> : (
          <div className="table-wrap">
            <table className="t num cards-sm">
              <thead><tr><th>{tr('Vendor')}</th><th>{tr('Bill')}</th><th>{tr('Day 180')}</th><th className="right">{tr('ITC to reverse')}</th><th>{tr('Status')}</th><th /></tr></thead>
              <tbody>{itc.map((r) => (
                <tr key={r.expenseId}>
                  <td>{r.vendorName}</td>
                  <td>{r.invoiceNo ?? '—'}<div className="tiny muted">{fmtDate(r.invoiceDate)} · ITC {fmtInr(r.itc)}</div></td>
                  <td>{fmtDate(r.day180)}</td>
                  <td className="right">{r.reverseAmount > 0 ? fmtInr(r.reverseAmount) : '—'}{r.status !== 'not_due' && r.reverseAmount > 0 && <div className="tiny muted">{tr('in {month}', { month: monthName(r.reverseMonth) })}</div>}</td>
                  <td><span className={`badge ${STATUS[r.status][1]}`}>{tr(STATUS[r.status][0])}</span>
                    {r.record && <div className="tiny muted">{tr('Reversed {amt} in {month}', { amt: fmtInr(r.record.amount), month: monthName(r.record.reversedIn) })}{r.record.reclaimedAmount ? ` · ${tr('re-claimed {amt}', { amt: fmtInr(r.record.reclaimedAmount) })}` : ''}</div>}</td>
                  <td>
                    {isCA && (r.status === 'reverse' || r.status === 'reclaim') && (
                      <div className="row" style={{ gap: 6 }}>
                        <input type="month" className="input sm" aria-label={tr('Return period')} value={month[r.expenseId] ?? (r.status === 'reverse' ? r.reverseMonth : today.slice(0, 7))}
                          onChange={(e) => setMonth({ ...month, [r.expenseId]: e.target.value })} />
                        {r.status === 'reverse'
                          ? <button className="btn sm" onClick={() => attempt(() => st.recordItcReversal(r.expenseId, r.reverseAmount, month[r.expenseId] ?? r.reverseMonth), 'Saved & logged')}>{tr('Record reversal')}</button>
                          : <button className="btn sm" onClick={() => attempt(() => st.recordItcReclaim(r.record!.id, r.reclaimable, month[r.expenseId] ?? today.slice(0, 7)), 'Saved & logged')}>{tr('Record re-claim {amt}', { amt: fmtInr(r.reclaimable) })}</button>}
                      </div>
                    )}
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
        <div className="hint" style={{ padding: '0 16px 12px' }}>{tr('Only the part unpaid on day 180 is reversed. TDS deducted counts as paid. Reverse-charge bills are not part of this rule. Interest, if any, is for the CA to work out.')}</div>
      </div>
    </div>
  );
}
