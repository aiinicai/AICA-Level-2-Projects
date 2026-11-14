// "Pay bills" — one place to pay one or many bills of a vendor, in one or several modes/dates,
// apply earlier advances, and keep any extra as an advance (Zoho Books "Payments made" / QuickBooks "Pay bills").
import { useEffect, useMemo, useState } from 'react';
import { RuleError, useStore } from '../data/store';
import { useTr } from '../i18n';
import { outstanding, unallocated } from '../lib/alerts';
import { allocateLines } from '../lib/payalloc';
import { fmtDate, fyLabel, todayIso } from '../lib/dates';
import { grossUpTds, maxApplicable, suggestAdvanceTds } from '../lib/tdsAdvance';
import { fmtInr, round2 } from '../lib/money';
import { Drawer, useAttempt } from '../ui/common';
import { newLine, PaymentLines, toPaymentLines, type LineDraft } from '../ui/PaymentLines';
import { modeLabel } from '../ui/PaymentLines';

export function PayDrawer({ vendorId, preselect = [], onClose }: { vendorId?: string; preselect?: string[]; onClose: () => void }) {
  const st = useStore();
  const { scoped, client } = st;
  const tr = useTr();
  const attempt = useAttempt();
  const [vid, setVid] = useState(vendorId ?? '');
  const bills = useMemo(() => scoped.expenses
    .filter((e) => e.vendorId === vid && e.status !== 'rejected' && e.status !== 'draft')
    .map((e) => ({ e, due: outstanding(e, scoped.payments) }))
    .filter((b) => b.due > 0)
    .sort((a, b) => a.e.invoiceDate.localeCompare(b.e.invoiceDate)), [scoped, vid]);
  const advances = scoped.payments.filter((p) => p.vendorId === vid && unallocated(p) > 0);

  const [pick, setPick] = useState<Record<string, string>>(() =>
    Object.fromEntries(bills.filter((b) => preselect.includes(b.e.id)).map((b) => [b.e.id, String(b.due)])));
  const picked = bills.filter((b) => pick[b.e.id] !== undefined);
  const billTotal = round2(picked.reduce((s, b) => s + (Number(pick[b.e.id]) || 0), 0));
  const [lines, setLines] = useState<LineDraft[]>(() => [newLine(billTotal ? String(billTotal) : '', client?.bankAccounts)]);
  const paid = round2(lines.reduce((s, l) => s + (Number(l.amount) || 0), 0));
  const diff = round2(paid - billTotal);
  const overBill = picked.find((b) => (Number(pick[b.e.id]) || 0) > b.due + 0.01);
  const [syncLine, setSyncLine] = useState(false);

  // TDS on the advance part (s.393: TDS is due at payment when it comes before the bill). The app suggests; the user decides.
  const paidOn = lines.map((l) => l.paidOn).filter(Boolean).sort()[0] ?? todayIso();
  const vendor = scoped.vendors.find((v) => v.id === vid);
  const [advCode, setAdvCode] = useState<string>();
  const [advTds, setAdvTds] = useState<boolean>();
  const sugg = diff > 0 ? suggestAdvanceTds(vendor, scoped.expenses, scoped.payments, st.s.tdsRates, diff, paidOn, fyLabel(paidOn), advCode) : undefined;
  const deductTds = diff > 0 && !!sugg?.code && sugg.ratePct > 0 && (advTds ?? sugg.applies);
  const advTdsAmt = deductTds ? grossUpTds(diff, sugg!.ratePct) : 0;

  // balances change when an advance is applied: keep chosen amounts within the new balance, drop fully settled bills
  useEffect(() => {
    setPick((prev) => {
      const next = { ...prev };
      let changed = false;
      for (const id of Object.keys(next)) {
        const b = bills.find((x) => x.e.id === id);
        if (!b) { delete next[id]; changed = true; }
        else if ((Number(next[id]) || 0) > b.due) { next[id] = String(b.due); changed = true; }
      }
      return changed ? next : prev;
    });
  }, [bills]);
  useEffect(() => {
    if (!syncLine || overBill) return; // wait until chosen amounts are clamped to the new balances
    setLines((ls) => (ls.length === 1 ? [{ ...ls[0], amount: billTotal ? String(billTotal) : '' }] : ls));
    setSyncLine(false);
  }, [billTotal, syncLine, overBill]);

  function toggle(id: string, due: number) {
    const next = { ...pick };
    if (next[id] !== undefined) delete next[id]; else next[id] = String(due);
    setPick(next);
    const total = round2(bills.filter((b) => next[b.e.id] !== undefined).reduce((s, b) => s + (Number(next[b.e.id]) || 0), 0));
    if (lines.length === 1) setLines([{ ...lines[0], amount: total ? String(total) : '' }]);
  }

  function save() {
    const pl = toPaymentLines(lines);
    const targets = picked.map((b) => ({ expenseId: b.e.id, amount: Number(pick[b.e.id]) || 0 }));
    const allocs = allocateLines(pl.map((l) => l.amount), targets);
    const ok = attempt(() => {
      if (!pl.length) throw new RuleError('Enter the amount paid');
      pl.forEach((l, i) => {
        const left = l.amount - allocs[i].reduce((s, a) => s + a.amount, 0);
        st.recordPayment({ ...l, vendorId: vid, allocations: allocs[i], ...(deductTds && left > 0.005 ? { tdsOnAdvance: { code: sugg!.code! } } : {}) });
      });
    }, diff > 0 ? (deductTds ? 'Payment saved — extra kept as advance, TDS recorded' : 'Payment saved — extra kept as advance') : 'Payment saved');
    if (ok) onClose();
  }

  function applyAdv(pid: string) {
    const p = advances.find((x) => x.id === pid)!;
    let left = unallocated(p);
    attempt(() => {
      for (const b of (picked.length ? picked : bills)) {
        if (left <= 0) break;
        const a = maxApplicable(b.e, st.s.payments, st.s.payments.find((x) => x.id === pid) ?? p, left); // TDS already deducted on the advance also settles the bill
        if (a <= 0) continue;
        st.applyAdvance(pid, b.e.id, a);
        left = round2(left - a);
      }
    }, 'Advance applied');
    setSyncLine(true);
  }

  const vendors = scoped.vendors.filter((v) => v.name);
  return (
    <Drawer title={tr('Record payment')} onClose={onClose}
      footer={<><button className="btn" onClick={onClose}>{tr('Cancel')}</button>
        <button className="btn primary grow" disabled={!vid || !(paid > 0) || !!overBill} onClick={save}>{tr('Save payment')} · {fmtInr(paid)}</button></>}>
      <div className="field">
        <label htmlFor="pay-vendor" className="req">{tr('Vendor')}</label>
        <select id="pay-vendor" className="input" value={vid} onChange={(e) => { setVid(e.target.value); setPick({}); setLines([newLine('', client?.bankAccounts)]); }}>
          <option value="">{tr('Choose vendor')}</option>
          {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
        </select>
      </div>

      {vid && (
        <div className="card">
          <div className="card-head"><h3>{tr('Unpaid bills')}</h3>
            {bills.length > 0 && <button className="linkish small" onClick={() => { const all = Object.fromEntries(bills.map((b) => [b.e.id, String(b.due)])); setPick(all); if (lines.length === 1) setLines([{ ...lines[0], amount: String(round2(bills.reduce((s, b) => s + b.due, 0))) }]); }}>{tr('Pay all in full')}</button>}
          </div>
          {bills.length === 0 ? <div className="empty small">{tr('No unpaid bills — anything you pay now is kept as an advance.')}</div> : (
            <div className="list">
              {bills.map((b) => (
                <div key={b.e.id} className="list-item small">
                  <input type="checkbox" checked={pick[b.e.id] !== undefined} onChange={() => toggle(b.e.id, b.due)} aria-label={tr('Select bill {no}', { no: b.e.invoiceNo ?? '' })} />
                  <div className="grow"><b>{b.e.invoiceNo ?? '—'}</b> · {fmtDate(b.e.invoiceDate)}<div className="tiny muted">{tr('Balance')} {fmtInr(b.due)}</div></div>
                  {pick[b.e.id] !== undefined && (
                    <input className="input sm num" style={{ width: 110 }} inputMode="decimal" aria-label={tr('Amount for this bill')} value={pick[b.e.id]}
                      onChange={(e) => setPick({ ...pick, [b.e.id]: e.target.value.replace(/[^0-9.]/g, '') })} />
                  )}
                </div>
              ))}
            </div>
          )}
          {overBill && <div className="hint err" style={{ padding: '0 16px 12px' }}>{tr('More than the balance of bill {no} (₹{due})', { no: overBill.e.invoiceNo ?? '', due: overBill.due })}</div>}
        </div>
      )}

      {advances.length > 0 && (
        <div className="card pad stack" style={{ gap: 8 }}>
          <h3>{tr('Advances available')}</h3>
          {advances.map((p) => (
            <div key={p.id} className="row between small">
              <span>{fmtDate(p.paidOn)} · {tr(modeLabel(p.mode))} · <b>{fmtInr(unallocated(p))}</b>
                {p.tdsOnAdvance && <span className="tiny muted"> · {tr('TDS ₹{amt} already deducted ({code})', { amt: p.tdsOnAdvance.amount, code: p.tdsOnAdvance.code })}</span>}</span>
              <button className="btn sm" disabled={!bills.length} onClick={() => applyAdv(p.id)}>{tr('Apply to bills')}</button>
            </div>
          ))}
        </div>
      )}

      {vid && (
        <div className="card pad stack">
          <h3>{tr('How was it paid?')}</h3>
          <PaymentLines lines={lines} onChange={setLines} accounts={client?.bankAccounts ?? []} cashLimit={client?.cashLimitPerDay} />
          {diff > 0 && sugg && (
            <div className="banner info small stack" style={{ gap: 6 }}>
              <label className="row" style={{ gap: 8 }}>
                <input type="checkbox" checked={deductTds} disabled={!sugg.code || !(sugg.ratePct > 0)} onChange={(e) => setAdvTds(e.target.checked)} />
                <b>{tr('Deduct TDS on this advance')}</b>
              </label>
              <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
                <label htmlFor="adv-tds-code" className="tiny">{tr('TDS section')}</label>
                <select id="adv-tds-code" className="input sm" value={sugg.code ?? ''} onChange={(e) => setAdvCode(e.target.value || undefined)}>
                  <option value="">{tr('Choose')}</option>
                  {st.s.tdsRates.filter((r) => r.ratePct > 0).map((r) => <option key={r.code} value={r.code}>{r.code} · {r.ratePct}%</option>)}
                </select>
              </div>
              {bills.some((b) => b.e.tdsAmount > 0 && b.e.invoiceDate <= paidOn && pick[b.e.id] === undefined) && (
                <span className="tiny" style={{ color: 'var(--warn)' }}>{tr('This vendor has unpaid bills dated before this payment. If you are paying them, select them above — their TDS is already counted on the bill.')}</span>
              )}
              <span className="tiny">{tr(sugg.reason, sugg.vars)} {sugg.noPan && tr('Higher rate: PAN missing or inoperative.')} {tr('TDS is due when the advance is paid if that is before the bill (s.393). Please confirm with your CA.')}</span>
            </div>
          )}
          <div className="totals num">
            <div className="row"><span className="muted">{tr('Bills selected')}</span><span>{fmtInr(billTotal)}</span></div>
            <div className="row"><span className="muted">{tr('Paying now')}</span><span>{fmtInr(paid)}</span></div>
            {diff > 0 && <div className="row" style={{ color: 'var(--info)' }}><span>{tr('Kept as advance')}</span><span>{fmtInr(diff)}</span></div>}
            {deductTds && <div className="row"><span className="muted">{tr('TDS on advance ({code}, {rate}%)', { code: sugg!.code!, rate: sugg!.ratePct })}</span><span>{fmtInr(advTdsAmt)}</span></div>}
            {deductTds && <div className="row"><span className="muted">{tr('Vendor credited with')}</span><span>{fmtInr(round2(diff + advTdsAmt))}</span></div>}
            {diff < 0 && <div className="row" style={{ color: 'var(--warn)' }}><span>{tr('Still due after this')}</span><span>{fmtInr(-diff)}</span></div>}
          </div>
        </div>
      )}
    </Drawer>
  );
}
