// Payment entry used everywhere money goes out: one row per mode/date, "+ Add another payment" for splits.
import type { BankAccount, PayMode } from '../data/types';
import { sourceKinds, type PaymentLine } from '../data/store';
import { useTr } from '../i18n';
import { cleanAmount } from '../lib/money';
import { todayIso } from '../lib/dates';
import { Icon } from './Icon';

export const PAY_MODES: { mode: PayMode; label: string }[] = [
  { mode: 'cash', label: 'Cash' },
  { mode: 'upi', label: 'UPI' },
  { mode: 'bank', label: 'Bank transfer' },
  { mode: 'cheque', label: 'Cheque' },
  { mode: 'card', label: 'Card' }
];

export const modeLabel = (m: PayMode) => PAY_MODES.find((x) => x.mode === m)?.label ?? m;

export interface LineDraft { mode: PayMode; accountId?: string; ref: string; paidOn: string; amount: string }

/** Active sources that fit a mode (UPI shows UPI IDs first, then banks). */
export const sourcesFor = (mode: PayMode, accounts: BankAccount[]) => {
  const kinds = sourceKinds(mode);
  return accounts.filter((a) => a.active !== false && kinds.includes(a.kind)).sort((a, b) => kinds.indexOf(a.kind) - kinds.indexOf(b.kind));
};

export const newLine = (amount = '', accounts: BankAccount[] = [], mode: PayMode = 'cash'): LineDraft =>
  ({ mode, accountId: sourcesFor(mode, accounts)[0]?.id, ref: '', paidOn: todayIso(), amount });

export const toPaymentLines = (lines: LineDraft[]): PaymentLine[] =>
  lines.filter((l) => Number(l.amount) > 0).map((l) => ({ mode: l.mode, accountId: l.accountId, ref: l.ref, paidOn: l.paidOn, amount: Number(l.amount) }));

export function PaymentLines({ lines, onChange, accounts, minDate, cashLimit }: { lines: LineDraft[]; onChange: (l: LineDraft[]) => void; accounts: BankAccount[]; minDate?: string; cashLimit?: number }) {
  const tr = useTr();
  const set = (i: number, patch: Partial<LineDraft>) => onChange(lines.map((l, j) => (j === i ? { ...l, ...patch } : l)));
  return (
    <div className="stack">
      {lines.map((l, i) => (
        <div key={i} className="pay-line stack" style={{ gap: 8 }}>
          {lines.length > 1 && (
            <div className="row between">
              <b className="small">{tr('Payment {n}', { n: i + 1 })}</b>
              <button className="icon-btn" aria-label={tr('Remove')} onClick={() => onChange(lines.filter((_, j) => j !== i))}><Icon name="x" size={16} /></button>
            </div>
          )}
          <div className="chips" role="radiogroup" aria-label={tr('Paid by')}>
            {PAY_MODES.map((m) => (
              <button key={m.mode} type="button" role="radio" aria-checked={l.mode === m.mode} className={`chip ${l.mode === m.mode ? 'on' : ''}`} onClick={() => set(i, { mode: m.mode, accountId: sourcesFor(m.mode, accounts)[0]?.id })}>
                {tr(m.label)}
              </button>
            ))}
          </div>
          <div className="row wrap" style={{ alignItems: 'flex-start' }}>
            <div className="field grow" style={{ minWidth: 120 }}>
              <label htmlFor={`pl-amt-${i}`} className="req">{tr('Amount')}</label>
              <input id={`pl-amt-${i}`} className="input num" inputMode="decimal" value={l.amount} onChange={(e) => set(i, { amount: cleanAmount(e.target.value) })} placeholder="₹ 0" />
            </div>
            <div className="field grow" style={{ minWidth: 140 }}>
              <label htmlFor={`pl-date-${i}`} className="req">{tr('Paid on')}</label>
              <input id={`pl-date-${i}`} type="date" className="input" value={l.paidOn} min={minDate} max={todayIso()} onChange={(e) => set(i, { paidOn: e.target.value || todayIso() })} />
            </div>
          </div>
          {sourcesFor(l.mode, accounts).length > (l.mode === 'cash' ? 1 : 0) && (
            <div className="field">
              <label className="req">{tr('Paid from')}</label>
              <div className="chips" role="radiogroup" aria-label={tr('Paid from')}>
                {sourcesFor(l.mode, accounts).map((a) => (
                  <button key={a.id} type="button" role="radio" aria-checked={l.accountId === a.id} className={`chip src-chip ${l.accountId === a.id ? 'on' : ''}`} onClick={() => set(i, { accountId: a.id })}>
                    <span className="src-kind">{a.kind === 'upi' ? 'UPI' : a.kind === 'card' ? '💳' : a.kind === 'cash' ? '₹' : '🏦'}</span>{a.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          {l.mode !== 'cash' && (
            <div className="field">
              <label htmlFor={`pl-ref-${i}`}>{l.mode === 'cheque' ? tr('Cheque no.') : l.mode === 'upi' ? tr('UPI transaction ID (optional)') : tr('UTR / reference (optional)')}</label>
              <input id={`pl-ref-${i}`} className="input" maxLength={30} value={l.ref} onChange={(e) => set(i, { ref: e.target.value })} />
            </div>
          )}
          {l.paidOn < todayIso() && <span className="hint">{tr('Earlier date noted for audit.')}</span>}
          {cashLimit !== undefined && l.mode === 'cash' && Number(l.amount) > cashLimit && (
            <span className="hint err">{tr('Cash above ₹{limit} to one vendor in a day may not be allowed as an expense — pay by bank/UPI if possible.', { limit: cashLimit.toLocaleString('en-IN') })}</span>
          )}
        </div>
      ))}
      <button type="button" className="linkish" onClick={() => onChange([...lines, newLine('', accounts, lines[lines.length - 1]?.mode === 'cash' ? 'upi' : 'cash')])}>{tr('+ Add another payment (other mode or date)')}</button>
    </div>
  );
}
