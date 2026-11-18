import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { KpiResult } from '@shared/types';
import { fmtMoney, fmtValue } from '@shared/format';
import { Sparkline, TrendChart } from './charts';
import { Modal, Notes, StatusBadge } from './ui';

function comparisonText(k: KpiResult) {
  const c = k.comparison;
  if (!c) return null;
  if (c.previous === null) return <span className="muted">No comparison value</span>;
  const abs = c.absChange ?? 0;
  const good = k.better === 'neutral' ? null : k.better === 'higher' ? abs > 0 : abs < 0;
  const color = abs === 0 || good === null ? 'var(--text-secondary)' : good ? 'var(--good)' : 'var(--critical)';
  const absTxt = k.unit === 'percent' ? `${abs >= 0 ? '+' : ''}${abs.toFixed(1)} pts` : k.unit === 'currency' ? fmtMoney(abs) : `${abs >= 0 ? '+' : ''}${fmtValue(abs, k.unit)}`;
  return (
    <span>
      <span style={{ color }}>{abs > 0 ? '▲' : abs < 0 ? '▼' : '■'} {absTxt}</span>
      {c.pctChange !== null ? <span style={{ color }}> ({c.pctChange >= 0 ? '+' : ''}{c.pctChange.toFixed(1)}%)</span> : null}
      <span className="muted"> vs {fmtValue(c.previous, k.unit)}</span>
    </span>
  );
}

export function KpiCard({ k }: { k: KpiResult }) {
  const [open, setOpen] = useState(false);
  const thr = k.thresholdState === 'bad' ? 'bad' : k.thresholdState === 'warn' ? 'warn' : '';
  return (
    <>
      <button className={`card kpi ${thr}`} onClick={() => setOpen(true)} aria-haspopup="dialog" aria-label={`${k.name}: ${fmtValue(k.current.value, k.unit)}. Open calculation details`}>
        <span className="name">{k.name}<span className="spacer" /><StatusBadge status={k.current.status} /></span>
        <span className="value">{k.current.status === 'unavailable' ? <span className="muted" style={{ fontSize: 15 }}>Unavailable</span> : fmtValue(k.current.value, k.unit)}</span>
        <span className="cmp">{comparisonText(k)}</span>
        {thr && <span className="small" style={{ color: thr === 'bad' ? 'var(--critical)' : 'var(--text-secondary)' }}>{thr === 'bad' ? '▲ Outside threshold' : '◆ Near threshold'}</span>}
        <Sparkline data={k.trend} />
      </button>
      {open && <KpiDetail k={k} onClose={() => setOpen(false)} />}
    </>
  );
}

export function KpiDetail({ k, onClose }: { k: KpiResult; onClose: () => void }) {
  const nav = useNavigate();
  const [sp] = useSearchParams();
  return (
    <Modal title={k.name} onClose={onClose}>
      <div className="row mb"><span style={{ fontSize: 26, fontWeight: 650 }}>{fmtValue(k.current.value, k.unit, false)}</span><StatusBadge status={k.current.status} /><span className="badge">{k.measureType}</span></div>
      <p>{k.description}</p>
      <p className="small"><strong>Formula:</strong> <code>{k.expression}</code></p>
      {k.comparison && <p className="small"><strong>Comparison:</strong> {comparisonText(k)}{k.comparison.pctNote ? <span className="muted"> — {k.comparison.pctNote}</span> : null}</p>}
      <Notes notes={k.current.notes} />
      {k.drivers && k.drivers.length > 0 && (
        <>
          <h3 className="mt">Largest drivers of the change</h3>
          <table className="data"><tbody>{k.drivers.map((d) => <tr key={d.label}><td>{d.label}</td><td className="num" style={{ color: d.change >= 0 ? 'var(--good)' : 'var(--critical)' }}>{fmtMoney(d.change)}</td></tr>)}</tbody></table>
          <p className="small muted">Ledger-level changes between the periods, signed by their effect on this KPI. Observed movements — not a causal explanation.</p>
        </>
      )}
      {k.trend.length > 1 && <div className="mt"><TrendChart title="Last 12 months" data={k.trend.map((t) => ({ label: t.period, value: t.value }))} series={[{ key: 'value', label: k.name }]} unit={k.unit} height={180} /></div>}
      {k.drill && <button className="btn primary mt" onClick={() => { onClose(); const [p, q] = k.drill!.target.split('?'); const n = new URLSearchParams(sp); if (q) for (const [a, b] of new URLSearchParams(q)) n.set(a, b); nav(`${p}?${n}`); }}>Open supporting analysis →</button>}
    </Modal>
  );
}
