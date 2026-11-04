import { useStore } from '../data/store';
import { useT, useTr } from '../i18n';
import { buildAlerts } from '../lib/alerts';
import { todayIso } from '../lib/dates';
import { isDemo } from '../lib/backend';
import { Icon } from '../ui/Icon';
import { Empty, PageHead, useToast } from '../ui/common';
import { useEffect, useState } from 'react';
import { disablePush, enablePush, pushState, setEmailAlerts, type PushState } from '../lib/push';

/** Phone notifications and e-mail switches — they say plainly when a channel is not available yet. */
function AlertChannels() {
  const tr = useTr();
  const toast = useToast();
  const [push, setPush] = useState<PushState>();
  useEffect(() => { pushState().then(setPush).catch(() => setPush('unsupported')); }, []);
  const run = (p: Promise<PushState>) => p.then(setPush).catch((e) => toast(tr((e as Error).message), true));
  return (
    <div className="card pad stack" style={{ gap: 8 }}>
      <div className="row between wrap">
        <span className="small"><b>{tr('Phone notifications')}</b></span>
        {push === 'on' ? <button className="btn sm" onClick={() => run(disablePush())}>{tr('Turn off on this phone')}</button>
          : push === 'off' ? <button className="btn sm primary" onClick={() => run(enablePush())}>{tr('Turn on for this phone')}</button>
          : <span className="tiny muted">{tr(push === 'blocked' ? 'Blocked in this browser’s settings' : push === 'unsupported' ? 'This browser cannot receive them (on iPhone, add Vouchr to the Home Screen first)' : 'Not available yet — switches on when the backend is connected')}</span>}
      </div>
      <div className="row between wrap">
        <span className="small"><b>{tr('E-mail alerts')}</b> <span className="tiny muted">{tr('sent if your CA firm has set up e-mail')}</span></span>
        {isDemo ? <span className="tiny muted">{tr('Not available yet — switches on when the backend is connected')}</span>
          : <span className="row" style={{ gap: 6 }}>
              <button className="btn sm" onClick={() => setEmailAlerts(true).then(() => toast(tr('E-mail alerts on'))).catch((e) => toast(tr((e as Error).message), true))}>{tr('On')}</button>
              <button className="btn sm" onClick={() => setEmailAlerts(false).then(() => toast(tr('E-mail alerts off'))).catch((e) => toast(tr((e as Error).message), true))}>{tr('Off')}</button>
            </span>}
      </div>
    </div>
  );
}

const KIND_LABEL: Record<string, string> = {
  itc_180: 'ITC 180-day', payment_overdue_30: 'Payment overdue', tds_due: 'TDS payment', gst_reco: 'GST reconciliation', tally_posting: 'Tally posting'
};

export function Alerts() {
  const tr = useTr();
  const { scoped, me, client, s } = useStore();
  const t = useT();
  let alerts = buildAlerts(scoped.expenses, scoped.payments, todayIso(), { challans: scoped.challans, tallyMode: client?.tallyMode, creditDaysOf: (e) => s.vendors.find((v) => v.id === e.vendorId)?.creditDays ?? client?.defaultCreditDays ?? 30 });
  // staff only see payment reminders; tax alerts go to admins and the CA firm
  if (me?.role === 'sub_user') alerts = alerts.filter((a) => a.kind === 'payment_overdue_30');

  return (
    <div className="content narrow">
      <PageHead title={t('alerts')} sub={tr('Shown here for everyone; admins can also get them on the phone and by e-mail.')} />
      <div className="stack">
        {me?.role !== 'sub_user' && <AlertChannels />}
        {alerts.length === 0 && <div className="card"><Empty art="done">{tr('All clear ✓')}</Empty></div>}
        {alerts.map((a) => (
          <div key={a.id} className="card pad row" style={{ alignItems: 'flex-start' }}>
            <div className="avatar" style={{ background: `var(--${a.severity === 'danger' ? 'danger' : a.severity === 'warn' ? 'warn' : 'info'}-soft)`, color: `var(--${a.severity === 'danger' ? 'danger' : a.severity === 'warn' ? 'warn' : 'info'})`, border: 'none' }}>
              <Icon name={a.kind === 'gst_reco' ? 'reco' : a.kind === 'tds_due' ? 'shield' : a.kind === 'tally_posting' ? 'tally' : 'alert'} size={18} />
            </div>
            <div className="grow">
              <div className="tiny muted" style={{ fontWeight: 650, textTransform: 'uppercase', letterSpacing: '.05em' }}>{tr(KIND_LABEL[a.kind] ?? a.kind)}</div>
              <div style={{ fontWeight: 650 }}>{a.tTitle ? tr(a.tTitle, a.vars) : a.title}</div>
              <div className="small muted">{a.tBody ? tr(a.tBody, a.vars) : a.body}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
