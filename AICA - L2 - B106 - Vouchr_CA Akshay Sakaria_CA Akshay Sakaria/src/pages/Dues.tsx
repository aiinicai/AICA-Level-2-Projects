// Payables: what is owed, to whom, how late — and paying it (single, partial, several bills, split modes).
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useStore } from '../data/store';
import type { Expense } from '../data/types';
import { useTr } from '../i18n';
import { AGE_BUCKETS, ageBucket, billStatus, dueDate, outstanding, unallocated, type BillStatus } from '../lib/alerts';
import { daysBetween, fmtDate, todayIso } from '../lib/dates';
import { fmtInr, round2 } from '../lib/money';
import { BillStatusBadge, Empty, PageHead } from '../ui/common';
import { Icon } from '../ui/Icon';
import { ExpenseDrawer } from './ExpenseDrawer';
import { PayDrawer } from './PayDrawer';

export function Dues() {
  const { scoped, s, client, me } = useStore();
  const tr = useTr();
  const today = todayIso();
  const [open, setOpen] = useState<Expense>();
  const [pay, setPay] = useState<{ vendorId?: string; ids: string[] }>();
  const [filter, setFilter] = useState<'all' | BillStatus>('all');
  const [sel, setSel] = useState<string[]>([]);
  const termsOf = (e: Expense) => s.vendors.find((v) => v.id === e.vendorId)?.creditDays ?? client?.defaultCreditDays ?? 30;

  const rows = useMemo(() => scoped.expenses
    .filter((e) => e.status !== 'rejected' && e.status !== 'draft')
    .map((e) => ({ e, due: outstanding(e, scoped.payments), status: billStatus(e, scoped.payments, today, termsOf(e)), late: daysBetween(dueDate(e, termsOf(e)), today), bucket: ageBucket(e, today, termsOf(e)) }))
    .filter((r) => r.due > 0)
    .sort((a, b) => b.late - a.late), [scoped, today]); // eslint-disable-line react-hooks/exhaustive-deps

  const shown = rows.filter((r) => filter === 'all' || r.status === filter);
  const total = round2(rows.reduce((x, r) => x + r.due, 0));
  const buckets = AGE_BUCKETS.map((b) => ({ b, amt: round2(rows.filter((r) => r.bucket === b).reduce((x, r) => x + r.due, 0)) }));
  const advances = round2(scoped.payments.reduce((x, p) => x + unallocated(p), 0));
  const selRows = rows.filter((r) => sel.includes(r.e.id));
  const selVendor = selRows[0]?.e.vendorId;
  const sameVendor = selRows.every((r) => r.e.vendorId === selVendor);
  const staff = me?.role === 'sub_user';

  function whatsapp(e: Expense, due: number) {
    const text = tr('Reminder: bill {no} from {vendor} dated {date} — ₹{amount} is due. Please arrange payment.', { no: e.invoiceNo ?? '', vendor: e.vendorName, date: fmtDate(e.invoiceDate), amount: due });
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener');
  }

  return (
    <div className="content stack">
      <PageHead title={tr('Payments due')} sub={tr('{n} bills · {amount} to pay', { n: rows.length, amount: fmtInr(total) })}>
        <button className="btn primary" onClick={() => setPay({ ids: [] })}><Icon name="wallet" size={16} /> {tr('Record payment')}</button>
      </PageHead>

      <div className="grid kpi">
        {buckets.filter(({ b, amt }) => amt > 0 || b === 'Not due').map(({ b, amt }) => (
          <div key={b} className="card kpi-tile">
            <div className="kpi-label">{b === 'Not due' ? tr('Not yet due') : tr('{b} days late', { b })}</div>
            <div className="kpi-value num" style={{ fontSize: 20, color: b === '90+' && amt ? 'var(--danger)' : undefined }}>{fmtInr(amt)}</div>
          </div>
        ))}
        {advances > 0 && <div className="card kpi-tile"><div className="kpi-label">{tr('Advances with vendors')}</div><div className="kpi-value num" style={{ fontSize: 20, color: 'var(--info)' }}>{fmtInr(advances)}</div></div>}
      </div>

      <div className="row wrap">
        <div className="seg" role="tablist" style={{ flex: 1, minWidth: 280 }}>
          {(['all', 'overdue', 'partial', 'open'] as const).map((f) => (
            <button key={f} role="tab" aria-selected={filter === f} className={filter === f ? 'on' : ''} onClick={() => setFilter(f)}>
              {tr(f === 'all' ? 'All' : f === 'overdue' ? 'Overdue' : f === 'partial' ? 'Partially paid' : 'Unpaid')} ({f === 'all' ? rows.length : rows.filter((r) => r.status === f).length})
            </button>
          ))}
        </div>
      </div>

      {sel.length > 0 && (
        <div className="card pad row between wrap" style={{ borderColor: 'var(--brand)' }}>
          <span><b>{sel.length}</b> {tr('selected')} · {fmtInr(round2(selRows.reduce((x, r) => x + r.due, 0)))}</span>
          <div className="row">
            <button className="btn" onClick={() => setSel([])}>{tr('Clear')}</button>
            <button className="btn primary" disabled={!sameVendor} title={sameVendor ? '' : tr('Select bills of one vendor at a time')} onClick={() => setPay({ vendorId: selVendor, ids: sel })}>{tr('Pay selected')}</button>
          </div>
          {!sameVendor && <span className="hint err" style={{ width: '100%' }}>{tr('Select bills of one vendor at a time')}</span>}
        </div>
      )}

      <div className="card">
        {shown.length === 0 ? <Empty art="done">{tr('Nothing pending.')} 🎉</Empty> : (
          <div className="list">
            {shown.map(({ e, due, status, late }) => (
              <div key={e.id} className="list-item">
                <input type="checkbox" checked={sel.includes(e.id)} aria-label={tr('Select bill {no}', { no: e.invoiceNo ?? '' })}
                  onChange={() => setSel(sel.includes(e.id) ? sel.filter((x) => x !== e.id) : [...sel, e.id])} />
                <button className="grow" style={{ background: 'none', border: 'none', textAlign: 'left', cursor: 'pointer', padding: 0, minWidth: 0 }} onClick={() => setOpen(e)}>
                  <div className="ellipsis" style={{ fontWeight: 600 }}>{e.vendorName}</div>
                  <div className="muted tiny">{fmtDate(e.invoiceDate)}{e.invoiceNo ? ` · #${e.invoiceNo}` : ''} · {late === 1 ? tr('1 day overdue') : late > 0 ? tr('{n} days overdue', { n: late }) : tr('due {date}', { date: fmtDate(dueDate(e, termsOf(e))) })}</div>
                </button>
                <div className="right stack" style={{ gap: 4, alignItems: 'flex-end' }}>
                  <div className="num" style={{ fontWeight: 650 }}>{fmtInr(due)}</div>
                  <BillStatusBadge status={status} />
                </div>
                {!staff && <button className="icon-btn" aria-label={tr('Send reminder on WhatsApp')} title={tr('Send reminder on WhatsApp')} onClick={() => whatsapp(e, due)}><Icon name="share" size={18} /></button>}
              </div>
            ))}
          </div>
        )}
      </div>
      {!staff && <div className="hint">{tr('Have a bank statement? Match many payments at once in')} <Link to="/bank" className="linkish">{tr('Bank statement')}</Link>.</div>}

      {open && <ExpenseDrawer e={scoped.expenses.find((x) => x.id === open.id) ?? open} onClose={() => setOpen(undefined)} />}
      {pay && <PayDrawer vendorId={pay.vendorId} preselect={pay.ids} onClose={() => { setPay(undefined); setSel([]); }} />}
    </div>
  );
}
