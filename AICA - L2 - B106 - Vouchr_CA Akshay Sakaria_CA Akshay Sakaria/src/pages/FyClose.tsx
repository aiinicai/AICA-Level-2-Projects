// Financial-year close for the CA firm (lib/fyClose.ts): checklist → carry-forward sheet → close (locks the 12 months).
import { useMemo, useState } from 'react';
import { useStore } from '../data/store';
import { useTr } from '../i18n';
import { downloadCsv } from '../lib/csv';
import { fmtDate, fyLabel, todayIso } from '../lib/dates';
import { carryForward, fyChecklist, fyEnd } from '../lib/fyClose';
import { fmtInr, round2 } from '../lib/money';
import { PageHead, useAttempt, useConfirm } from '../ui/common';
import { Icon } from '../ui/Icon';

const KIND: Record<string, string> = { open_bill: 'Open bill', advance: 'Advance not yet applied', advance_tds: 'TDS on advance not yet used', vendor_note: 'Notes not linked to a bill' };

export function FyClose() {
  const st = useStore();
  const { scoped, client, s } = st;
  const tr = useTr();
  const attempt = useAttempt();
  const confirm = useConfirm();
  const today = todayIso();
  const lastFy = fyLabel(`${Number(fyLabel(today).slice(0, 4)) - 1}-06-01`);
  const years = [...new Set([lastFy, ...scoped.expenses.map((e) => e.fyLabel)])].filter((y) => fyEnd(y) < today).sort().reverse();
  const [fy, setFy] = useState(years[0] ?? lastFy);
  const [ack, setAck] = useState<string[]>([]);
  const closed = (s.fyCloses ?? []).find((c) => c.clientId === client?.id && c.fy === fy);
  const checks = useMemo(() => fyChecklist(fy, { client, expenses: scoped.expenses, payments: scoped.payments, challans: scoped.challans, itcReversals: scoped.itcReversals }, today),
    [fy, client, scoped, today]);
  const carry = useMemo(() => carryForward(fy, scoped), [fy, scoped]);
  const blocked = checks.some((c) => c.blocker && c.count > 0);
  const warns = checks.filter((c) => !c.blocker && c.count > 0);
  const total = (k: string) => round2(carry.filter((c) => c.kind === k).reduce((x, c) => x + c.amount, 0));

  async function close() {
    if (await confirm(tr('Close FY {fy}? All 12 months are locked. Only the CA firm can unlock a month again.', { fy }), { danger: true, ok: tr('Close the year') }))
      attempt(() => st.closeFy(fy, ack), 'Financial year closed');
  }

  return (
    <div className="content narrow stack">
      <PageHead title={tr('Close the financial year')} sub={client?.name}>
        <select className="input sm" style={{ width: 'auto' }} aria-label={tr('Financial year')} value={fy} onChange={(e) => { setFy(e.target.value); setAck([]); }}>
          {years.map((y) => <option key={y} value={y}>FY {y}</option>)}
        </select>
      </PageHead>
      {years.length === 0 && <div className="banner info small"><Icon name="info" size={16} />{tr('No financial year has ended yet for this client.')}</div>}
      {closed && <div className="banner ok"><Icon name="check" size={18} /><span>{tr('FY {fy} was closed on {date}. Its months are locked.', { fy, date: fmtDate(closed.at.slice(0, 10)) })}</span></div>}

      <div className="card">
        <div className="card-head"><h2>{tr('1. Checklist')}</h2></div>
        <div className="list">
          {checks.map((c) => (
            <div key={c.key} className="list-item small">
              <Icon name={c.count === 0 ? 'check' : 'alert'} size={18} />
              <div className="grow">{c.count === 0 ? <span className="muted">{tr(c.label, { n: 0, amt: fmtInr(0) })}</span> : tr(c.label, { n: c.count, amt: fmtInr(c.amount ?? 0) })}</div>
              {c.count === 0 ? <span className="badge ok">{tr('Done')}</span> : c.blocker ? <span className="badge danger">{tr('Must be cleared')}</span>
                : <label className="row tiny" style={{ gap: 4 }}><input type="checkbox" disabled={!!closed} checked={ack.includes(c.key)} onChange={(e) => setAck(e.target.checked ? [...ack, c.key] : ack.filter((k) => k !== c.key))} /> {tr('Seen — close anyway')}</label>}
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-head"><h2>{tr('2. Carried into the next year')}</h2>
          <button className="btn sm" disabled={!carry.length} onClick={() => downloadCsv(`carry_forward_FY${fy}.csv`, ['Kind', 'Vendor', 'Reference', 'Date', 'Amount'], carry.map((c) => [KIND[c.kind], c.vendor, c.ref, c.date, c.amount]))}>
            <Icon name="download" size={14} /> CSV</button></div>
        <dl className="kv num" style={{ padding: '0 16px 12px' }}>
          <dt>{tr('Open bills (balance)')}</dt><dd>{fmtInr(total('open_bill'))}</dd>
          <dt>{tr('Advances not yet applied')}</dt><dd>{fmtInr(total('advance'))}</dd>
          <dt>{tr('TDS on advances not yet used')}</dt><dd>{fmtInr(total('advance_tds'))}</dd>
          <dt>{tr('Notes not linked to a bill')}</dt><dd>{fmtInr(total('vendor_note'))}</dd>
        </dl>
        <div className="hint" style={{ padding: '0 16px 12px' }}>{tr('Nothing is moved or deleted — these items simply continue into the next year. Balances are as in the books today.')}</div>
      </div>

      {!closed && (
        <div className="card pad stack">
          <h2>{tr('3. Close')}</h2>
          <div className="small">{tr('Closing locks all 12 months of the year, so nothing dated in it can be added or changed. Files stay in their FY folders in Drive.')}</div>
          <button className="btn primary lg" disabled={blocked || years.length === 0 || warns.some((w) => !ack.includes(w.key))} onClick={close}>{tr('Close FY {fy}', { fy })}</button>
          {blocked && <span className="hint err">{tr('Clear the items marked “Must be cleared” first.')}</span>}
        </div>
      )}
    </div>
  );
}
