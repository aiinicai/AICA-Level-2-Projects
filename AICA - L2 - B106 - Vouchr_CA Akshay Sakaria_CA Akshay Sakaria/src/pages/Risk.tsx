// Bill risk check: rule-based red flags (fake / inflated / wrongly taxed bills) for the selected client, plus the optional
// AI second opinion when Gemini is connected on the server.
import { useMemo, useState } from 'react';
import { useStore } from '../data/store';
import type { Expense } from '../data/types';
import { useTr } from '../i18n';
import { riskCheck, type Severity } from '../lib/anomaly';
import { useAiStatus } from '../lib/ai';
import { fmtDate } from '../lib/dates';
import { fmtInr } from '../lib/money';
import { Empty, PageHead } from '../ui/common';
import { Icon } from '../ui/Icon';
import { ExpenseDrawer } from './ExpenseDrawer';
import { LookAlikes } from '../ui/LookAlikes';

const SEV_LABEL: Record<Severity, string> = { high: 'High', medium: 'Medium', low: 'Check' };
const SEV_TONE: Record<Severity, string> = { high: 'danger', medium: 'warn', low: 'info' };

export function Risk() {
  const { scoped, s, client } = useStore();
  const tr = useTr();
  const [sev, setSev] = useState<Severity | 'all'>('all');
  const [open, setOpen] = useState<Expense>();
  const flags = useMemo(() => riskCheck(scoped.expenses, scoped.vendors, client, s.tdsRates), [scoped.expenses, scoped.vendors, client, s.tdsRates]);
  const shown = sev === 'all' ? flags : flags.filter((f) => f.severity === sev);
  const count = (x: Severity) => flags.filter((f) => f.severity === x).length;
  const ai = useAiStatus();

  return (
    <div className="content stack" style={{ maxWidth: 980 }}>
      <PageHead title={tr('Bill risk check')} sub={`${client?.name ?? ''} · ${tr('{n} flags', { n: flags.length })}`} />
      <div className="hint">{tr('Rule-based checks for fake, inflated or wrongly taxed bills. A flag is a reason to look, not proof — the CA decides.')}</div>

      <div className="grid kpi">
        {(['high', 'medium', 'low'] as const).map((x) => (
          <button key={x} className={`card kpi-tile ${sev === x ? 'on' : ''}`} style={{ textAlign: 'left', cursor: 'pointer' }} onClick={() => setSev(sev === x ? 'all' : x)} aria-pressed={sev === x}>
            <div className="kpi-label"><span className={`health-dot ${SEV_TONE[x]}`} /> {tr(SEV_LABEL[x])}</div>
            <div className="kpi-value num">{count(x)}</div>
          </button>
        ))}
        <div className="card kpi-tile">
          <div className="kpi-label"><Icon name="radar" size={15} /> {tr('AI second opinion')}</div>
          <div className="small" style={{ marginTop: 6 }}>{ai.enabled ? tr('Connected — open a bill in the review queue and tap "AI check".') : tr(ai.reason)}</div>
        </div>
      </div>

      <div className="card">
        {shown.length === 0 ? <Empty art="done">{tr('No red flags found.')}</Empty> : (
          <div className="list">
            {shown.map((f) => {
              const e = f.expenseId ? scoped.expenses.find((x) => x.id === f.expenseId) : undefined;
              return (
                <div key={f.id} className="list-item" style={{ alignItems: 'flex-start' }}>
                  <span className={`badge ${SEV_TONE[f.severity]}`} style={{ flexShrink: 0 }}>{tr(SEV_LABEL[f.severity])}</span>
                  <div className="grow">
                    <div style={{ fontWeight: 650 }}>{tr(f.title, f.vars)}</div>
                    <div className="small muted">{tr(f.detail, f.vars)}</div>
                    {e && <div className="tiny muted" style={{ marginTop: 4 }}>{e.vendorName} · {e.invoiceNo ? `#${e.invoiceNo} · ` : ''}{fmtDate(e.invoiceDate)} · {fmtInr(e.totalAmount)}</div>}
                  </div>
                  {e && <button className="btn sm" onClick={() => setOpen(e)}>{tr('View bill')}</button>}
                </div>
              );
            })}
          </div>
        )}
      </div>
      <LookAlikes expenses={scoped.expenses} />
      {open && <ExpenseDrawer e={scoped.expenses.find((x) => x.id === open.id) ?? open} onClose={() => setOpen(undefined)} />}
    </div>
  );
}
