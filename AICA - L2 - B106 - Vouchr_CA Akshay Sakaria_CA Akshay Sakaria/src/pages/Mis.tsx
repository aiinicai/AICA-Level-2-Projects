import { useMemo, type ReactNode } from 'react';
import { noteItcDelta } from '../lib/vendorNotes';
import { Link } from 'react-router-dom';
import { useStore } from '../data/store';
import type { Expense } from '../data/types';
import { useTr } from '../i18n';
import { AGE_BUCKETS, ageBucket, outstanding, unallocated } from '../lib/alerts';
import { daysBetween, fyLabel, monthKey, todayIso } from '../lib/dates';
import { fmtInr, fmtInrShort, round2 } from '../lib/money';
import { PageHead } from '../ui/common';
import { Icon } from '../ui/Icon';
import { CountUp } from '../ui/CountUp';
import { modeLabel, PAY_MODES } from '../ui/PaymentLines';
import { MisNotes } from '../ui/MisNotes';

const FY_MONTHS = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'];

export function Mis() {
  const { scoped, s, client } = useStore();
  const tr = useTr();
  const today = todayIso();
  const fy = fyLabel(today);
  const startYear = Number(fy.slice(0, 4));
  const termsOf = (e: Expense) => s.vendors.find((v) => v.id === e.vendorId)?.creditDays ?? client?.defaultCreditDays ?? 30;

  const d = useMemo(() => {
    const ex = scoped.expenses.filter((e) => e.fyLabel === fy && e.status !== 'rejected' && e.status !== 'draft');
    const monthTotals = FY_MONTHS.map((_, i) => {
      const y = i < 9 ? startYear : startYear + 1;
      const key = `${y}-${String(((i + 3) % 12) + 1).padStart(2, '0')}`;
      return round2(ex.filter((e) => monthKey(e.invoiceDate) === key).reduce((x, e) => x + e.taxableValue, 0));
    });
    const byHead = new Map<string, number>();
    const byVendor = new Map<string, number>();
    for (const e of ex) {
      const h = s.heads.find((x) => x.id === e.headId)?.name ?? 'Unclassified';
      byHead.set(h, (byHead.get(h) ?? 0) + e.taxableValue);
      byVendor.set(e.vendorName, (byVendor.get(e.vendorName) ?? 0) + e.totalAmount);
    }
    const ids = new Set(ex.map((e) => e.id));
    const pays = scoped.payments.filter((p) => p.allocations.some((a) => ids.has(a.expenseId)) || !p.allocations.length);
    const due = ex.map((e) => ({ e, d: outstanding(e, scoped.payments) })).filter((x) => x.d > 0);
    const byMode = PAY_MODES.map((m) => ({ mode: m.mode, amt: round2(pays.filter((p) => p.mode === m.mode).reduce((x, p) => x + p.amount, 0)) }));
    return {
      spend: round2(ex.reduce((x, e) => x + e.taxableValue, 0)),
      thisMonth: round2(ex.filter((e) => monthKey(e.invoiceDate) === monthKey(today)).reduce((x, e) => x + e.taxableValue, 0)),
      // credit notes from vendors reduce ITC, debit notes add to it (same financial year)
      itc: round2(ex.filter((e) => e.itcEligible).reduce((x, e) => x + e.cgst + e.sgst + e.igst, 0) + noteItcDelta(scoped.vendorNotes.filter((n) => n.fyLabel === fy))),
      blocked: round2(ex.filter((e) => e.itcEligible === false && e.blockedCode).reduce((x, e) => x + e.cgst + e.sgst + e.igst, 0)),
      tds: round2(ex.reduce((x, e) => x + e.tdsAmount, 0)),
      rcm: round2(ex.reduce((x, e) => x + e.rcmTax, 0)),
      due: round2(due.reduce((x, r) => x + r.d, 0)),
      aging: AGE_BUCKETS.map((b) => ({ b, amt: round2(due.filter((r) => ageBucket(r.e, today, termsOf(r.e)) === b).reduce((x, r) => x + r.d, 0)) })),
      older30: round2(due.filter((r) => daysBetween(r.e.invoiceDate, today) > 30).reduce((x, r) => x + r.d, 0)),
      pending: ex.filter((e) => e.status === 'submitted').length,
      noBill: ex.filter((e) => e.noImageReason).length,
      advances: round2(scoped.payments.reduce((x, p) => x + unallocated(p), 0)),
      byMode, monthTotals,
      heads: [...byHead].sort((a, b) => b[1] - a[1]).slice(0, 7),
      vendors: [...byVendor].sort((a, b) => b[1] - a[1]).slice(0, 5),
      count: ex.length
    };
  }, [scoped, s.heads, fy, startYear, today]); // eslint-disable-line react-hooks/exhaustive-deps

  const maxM = Math.max(...d.monthTotals, 1);
  const m = new Date(today + 'T00:00:00').getMonth();
  const currentIdx = (m + 9) % 12; // Apr = 0
  const maxH = Math.max(...d.heads.map((h) => h[1]), 1);
  const maxA = Math.max(...d.aging.map((a) => a.amt), 1);
  const payTotal = d.byMode.reduce((x, m) => x + m.amt, 0) || 1;
  const modeColor = { cash: 'var(--warn)', upi: 'var(--ok)', bank: 'var(--brand)', cheque: 'var(--info)', card: 'var(--ink-3)' } as const;

  return (
    <div className="content stack lg">
      <PageHead title={tr('MIS dashboard')} sub={`${client?.name} · FY ${fy} · ${tr('{n} bills', { n: d.count })}`} />

      <div className="grid kpi">
        <div className="card kpi-tile kpi-hero">
          <div style={{ position: 'relative', zIndex: 1 }}>
            <div className="kpi-label">{tr('Spend this FY')} · {fy}</div>
            <div className="kpi-value num"><CountUp value={d.spend} format={fmtInrShort} /></div>
            <div className="kpi-sub">{tr('This month')} {fmtInrShort(d.thisMonth)} · {tr('{n} bills', { n: d.count })}</div>
          </div>
          <div className="spark" role="img" aria-label={tr('Monthly spend (taxable value)')}>
            {d.monthTotals.map((v, i) => <i key={i} className={i === currentIdx ? 'now' : ''} style={{ height: `${Math.max((v / maxM) * 100, 5)}%`, animationDelay: `${i * 40}ms` }} title={`${tr(FY_MONTHS[i])}: ${fmtInr(v)}`} />)}
          </div>
        </div>
        <Kpi icon="wallet" label={tr('To pay')} value={<CountUp value={d.due} format={fmtInrShort} />} sub={<><span style={{ color: d.older30 ? 'var(--danger)' : undefined }}>{tr('Older than 30 days')}: {fmtInrShort(d.older30)}</span>{d.advances > 0 && <span className="muted"> · {tr('Advances')} {fmtInrShort(d.advances)}</span>}</>} to="/dues" />
        <Kpi icon="shield" label={tr('ITC available')} value={<CountUp value={d.itc} format={fmtInrShort} />} sub={`${tr('Blocked 17(5)')}: ${fmtInrShort(d.blocked)}`} />
        <Kpi icon="tally" label={tr('TDS deducted')} value={<CountUp value={d.tds} format={fmtInrShort} />} sub={`${tr('RCM GST')} ${fmtInrShort(d.rcm)}`} />
        <Kpi icon="check" label={tr('Awaiting CA review')} value={<CountUp value={d.pending} format={(n) => String(Math.round(n))} />} sub={d.noBill ? tr('{n} without bill image', { n: d.noBill }) : tr('bills')} />

      </div>

      <div className="grid two">
        <div className="card pad">
          <h2>{tr('Monthly spend (taxable value)')}</h2>
          <div className="bars" role="img" aria-label={tr('Monthly spend (taxable value)')}>
            {d.monthTotals.map((v, i) => (
              <div key={i} className="bar-col" title={`${tr(FY_MONTHS[i])}: ${fmtInr(v)}`}>
                <span className="tiny muted num">{v && (v === maxM || i === currentIdx) ? fmtInrShort(v) : ''}</span>
                <div className="bar" style={{ height: `${(v / maxM) * 100}%`, opacity: v ? 1 : 0.15, ['--i' as string]: i }} />
                <span className="tiny muted">{tr(FY_MONTHS[i])}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card pad stack">
          <h2>{tr('Payables ageing')}</h2>
          {d.aging.map(({ b, amt }) => (
            <div key={b} className="hbar-row">
              <span className="small">{b === 'Not due' ? tr('Not yet due') : tr('{b} days late', { b })}</span>
              <div className="hbar-track"><div className="hbar-fill" style={{ width: `${(amt / maxA) * 100}%`, background: b === 'Not due' ? 'var(--ok)' : b === '90+' || b === '61–90' ? 'var(--danger)' : 'var(--warn)' }} /></div>
              <span className="right small num">{fmtInrShort(amt)}</span>
            </div>
          ))}
        </div>

        <div className="card pad stack">
          <h2>{tr('By expense head')}</h2>
          {d.heads.map(([name, v]) => (
            <div key={name} className="hbar-row">
              <span className="ellipsis small">{tr(name)}</span>
              <div className="hbar-track"><div className="hbar-fill" style={{ width: `${(v / maxH) * 100}%` }} /></div>
              <span className="right small num">{fmtInrShort(v)}</span>
            </div>
          ))}
        </div>

        <div className="card pad stack">
          <h2>{tr('Payments by mode')}</h2>
          <div className="hbar-track" style={{ height: 14, display: 'flex' }}>
            {d.byMode.map((m) => <div key={m.mode} style={{ width: `${(m.amt / payTotal) * 100}%`, background: modeColor[m.mode] }} />)}
          </div>
          <div className="row wrap small" style={{ gap: 14 }}>
            {d.byMode.filter((m) => m.amt).map((m) => (
              <span key={m.mode} className="row" style={{ gap: 6 }}><span className="health-dot" style={{ background: modeColor[m.mode] }} />{tr(modeLabel(m.mode))} <b className="num">{fmtInr(m.amt)}</b></span>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-head"><h2>{tr('Top vendors')}</h2></div>
          <div className="list">
            {d.vendors.map(([n, v]) => <div key={n} className="list-item small"><span className="grow ellipsis">{n}</span><b className="num">{fmtInr(v)}</b></div>)}
          </div>
        </div>
      </div>

      <MisNotes figures={{
        spendThisFY: d.spend, spendThisMonth: d.thisMonth, spendLastMonth: currentIdx > 0 ? d.monthTotals[currentIdx - 1] : undefined,
        toPay: d.due, unpaidOlderThan30Days: d.older30, advancesWithVendors: d.advances, itcAvailable: d.itc, itcBlocked175: d.blocked,
        tdsDeducted: d.tds, rcmGst: d.rcm, awaitingReview: d.pending, billsWithoutImage: d.noBill, billCount: d.count,
        topHead: d.heads[0]?.[0], topHeadSpend: d.heads[0]?.[1], topVendor: d.vendors[0]?.[0], topVendorBills: d.vendors[0]?.[1]
      }} />
    </div>
  );
}

function Kpi({ label, value, sub, to, icon }: { label: string; value: ReactNode; sub?: ReactNode; to?: string; icon?: string }) {
  const body = (<><div className="kpi-label">{icon && <span className="kpi-ico"><Icon name={icon} size={15} /></span>}{label}</div><div className="kpi-value num">{value}</div>{sub && <div className="kpi-sub">{sub}</div>}</>);
  return to ? <Link to={to} className="card kpi-tile">{body}</Link> : <div className="card kpi-tile">{body}</div>;
}
