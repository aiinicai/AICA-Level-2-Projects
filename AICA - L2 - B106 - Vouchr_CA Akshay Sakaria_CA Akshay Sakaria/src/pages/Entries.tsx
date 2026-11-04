import { useMemo, useState } from 'react';
import { useStore } from '../data/store';
import type { Expense, ExpenseStatus } from '../data/types';
import { useT, useTr } from '../i18n';
import { fmtDate, monthKey, monthName } from '../lib/dates';
import { fmtInr } from '../lib/money';
import { Empty, PageHead, StatusBadge } from '../ui/common';
import { ExpenseDrawer } from './ExpenseDrawer';

export function Entries() {
  const tr = useTr();
  const { me, scoped, s } = useStore();
  const t = useT();
  const staff = me?.role === 'sub_user';
  const base = staff ? scoped.expenses.filter((e) => e.createdBy === me?.id) : scoped.expenses;
  const months = useMemo(() => [...new Set(base.map((e) => monthKey(e.invoiceDate)))].sort().reverse(), [base]);
  const [month, setMonth] = useState('all');
  const [status, setStatus] = useState<'all' | ExpenseStatus>('all');
  const [q, setQ] = useState('');
  const [open, setOpen] = useState<Expense>();

  const rows = base
    .filter((e) => month === 'all' || monthKey(e.invoiceDate) === month)
    .filter((e) => status === 'all' || e.status === status)
    .filter((e) => !q || `${e.vendorName} ${e.invoiceNo ?? ''}`.toLowerCase().includes(q.toLowerCase()))
    .sort((a, b) => b.invoiceDate.localeCompare(a.invoiceDate));
  const sum = rows.reduce((x, e) => x + e.totalAmount, 0);
  const headName = (id?: string) => { const n = s.heads.find((h) => h.id === id)?.name; return n ? tr(n) : '—'; };

  return (
    <div className="content">
      <PageHead title={me?.role === 'sub_user' ? t('entries') : tr('Expenses')} sub={`${rows.length} · ${fmtInr(sum)}`} />
      <div className="row wrap" style={{ marginBottom: 12 }}>
        <input className="input sm grow" style={{ minWidth: 180 }} aria-label={tr('Search vendor or bill no.')} placeholder={tr('Search vendor or bill no.')} value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input sm" style={{ width: 'auto' }} aria-label={tr('Month')} value={month} onChange={(e) => setMonth(e.target.value)}>
          <option value="all">{tr('All months')}</option>
          {months.map((m) => <option key={m} value={m}>{monthName(m)}</option>)}
        </select>
        <select className="input sm" style={{ width: 'auto' }} aria-label={tr('Status')} value={status} onChange={(e) => setStatus(e.target.value as typeof status)}>
          <option value="all">{tr('All status')}</option>
          {(['submitted', 'approved', 'posted', 'rejected'] as const).map((x) => <option key={x} value={x}>{t(`status_${x}`)}</option>)}
        </select>
      </div>

      <div className="card">
        {rows.length === 0 ? <Empty art="search">{tr('No entries')}</Empty> : staff ? (
          <div className="list">
            {rows.map((e) => (
              <button key={e.id} className="list-item" onClick={() => setOpen(e)}>
                <div className="grow">
                  <div className="ellipsis" style={{ fontWeight: 600 }}>{e.vendorName}</div>
                  <div className="muted tiny">{fmtDate(e.invoiceDate)}{e.invoiceNo ? ` · #${e.invoiceNo}` : ''}</div>
                </div>
                <div className="right"><div className="num" style={{ fontWeight: 650 }}>{fmtInr(e.totalAmount)}</div><StatusBadge status={e.status} /></div>
              </button>
            ))}
          </div>
        ) : (
          <div className="table-wrap">
            <table className="t num cards-sm">
              <thead><tr><th>{tr('Date')}</th><th>{tr('Vendor')}</th><th>{tr('Bill no.')}</th><th>{tr('Head')}</th><th className="right">{tr('Taxable')}</th><th className="right">{tr('GST')}</th><th className="right">{tr('TDS')}</th><th className="right">{tr('Total')}</th><th>{tr('Status')}</th></tr></thead>
              <tbody>
                {rows.map((e) => (
                  <tr key={e.id} className="click" onClick={() => setOpen(e)}>
                    <td className="nowrap">{fmtDate(e.invoiceDate)}</td>
                    <td><div style={{ fontWeight: 600 }}>{e.vendorName}</div>{e.rcmApplicable && <span className="badge warn">{tr('RCM')}</span>} {e.isBackdated && <span className="badge warn">{tr('Past-dated')}</span>}</td>
                    <td>{e.invoiceNo ?? '—'}</td>
                    <td>{headName(e.headId)}</td>
                    <td className="right">{fmtInr(e.taxableValue)}</td>
                    <td className="right">{fmtInr(e.cgst + e.sgst + e.igst)}</td>
                    <td className="right">{e.tdsAmount ? fmtInr(e.tdsAmount) : '—'}</td>
                    <td className="right" style={{ fontWeight: 650 }}>{fmtInr(e.totalAmount)}</td>
                    <td><StatusBadge status={e.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {open && <ExpenseDrawer e={scoped.expenses.find((x) => x.id === open.id) ?? open} onClose={() => setOpen(undefined)} />}
    </div>
  );
}
