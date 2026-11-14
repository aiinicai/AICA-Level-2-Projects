import { useNavigate } from 'react-router-dom';
import { useTr } from '../i18n';
import { useStore } from '../data/store';
import { buildAlerts, outstanding } from '../lib/alerts';
import { todayIso } from '../lib/dates';
import { fmtInrShort } from '../lib/money';
import { Logo, PageHead } from '../ui/common';
import { Icon } from '../ui/Icon';
import { CountUp } from '../ui/CountUp';

export function FirmOverview() {
  const tr = useTr();
  const { s, setActiveClient } = useStore();
  const nav = useNavigate();
  const today = todayIso();
  const openFindings = s.findings.filter((f) => f.status === 'open').length;
  const errors24h = s.events.filter((e) => e.level === 'error').length;
  const unverified = s.tdsRates.filter((r) => !r.verified).length;

  const rows = s.clients.map((c) => {
    const ex = s.expenses.filter((e) => e.clientId === c.id);
    const pays = s.payments.filter((p) => p.clientId === c.id);
    return {
      c,
      pending: ex.filter((e) => e.status === 'submitted').length,
      toPost: ex.filter((e) => e.status === 'approved').length,
      due: ex.filter((e) => e.status !== 'rejected').reduce((a, e) => a + Math.max(outstanding(e, pays), 0), 0),
      alerts: buildAlerts(ex, pays, today).length
    };
  });

  return (
    <div className="content stack lg">
      <PageHead title={tr('Firm overview')} sub={tr('{n} clients', { n: s.clients.length })} />
      <div className="grid kpi">
        <Tile label={tr('Awaiting review')} value={rows.reduce((a, r) => a + r.pending, 0)} onClick={() => nav('/review')} icon="check" />
        <Tile label={tr('Ready for Tally')} value={rows.reduce((a, r) => a + r.toPost, 0)} icon="tally" />
        <Tile label={tr('Compliance findings')} value={openFindings} onClick={() => nav('/compliance')} icon="radar" tone={openFindings ? 'warn' : undefined} />
        <Tile label={tr('Unverified tax rates')} value={unverified} onClick={() => nav('/masters')} icon="sliders" tone={unverified ? 'warn' : undefined} />
        <Tile label={tr('System errors (recent)')} value={errors24h} onClick={() => nav('/audit')} icon="pulse" tone={errors24h ? 'danger' : undefined} />
      </div>

      <div className="card">
        <div className="card-head"><h2>{tr('Clients')}</h2></div>
        <div className="table-wrap">
          <table className="t num cards-sm">
            <thead><tr><th>{tr('Client')}</th><th className="right">{tr('To review')}</th><th className="right">{tr('To post')}</th><th className="right">{tr('Outstanding')}</th><th className="right">{tr('Alerts')}</th><th>{tr('Tally')}</th><th /></tr></thead>
            <tbody>
              {rows.map(({ c, pending, toPost, due, alerts }) => (
                <tr key={c.id} className="click" onClick={() => { setActiveClient(c.id); nav('/mis'); }}>
                  <td><div className="row"><Logo name={c.name} url={c.logoUrl} size={30} /><div><b>{c.name}</b><div className="tiny muted mono">{c.gstin}</div></div></div></td>
                  <td className="right">{pending}</td>
                  <td className="right">{toPost}</td>
                  <td className="right">{fmtInrShort(due)}</td>
                  <td className="right">{alerts ? <span className="badge warn">{alerts}</span> : '—'}</td>
                  <td><span className="badge">{c.tallyMode === 'none' ? tr('Sheets only') : c.tallyMode === 'bridge' ? tr('Bridge') : 'XML'}</span></td>
                  <td><Icon name="chevron" size={16} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Tile({ label, value, icon, onClick, tone }: { label: string; value: number; icon: string; onClick?: () => void; tone?: 'warn' | 'danger' }) {
  return (
    <button className="card kpi-tile" style={{ textAlign: 'left', cursor: onClick ? 'pointer' : 'default' }} onClick={onClick}>
      <div className="row between"><span className="kpi-label">{label}</span><span style={{ color: tone ? `var(--${tone})` : 'var(--ink-3)' }}><Icon name={icon} size={18} /></span></div>
      <div className="kpi-value num" style={{ color: tone ? `var(--${tone})` : undefined }}><CountUp value={value} format={(n) => String(Math.round(n))} /></div>
    </button>
  );
}
