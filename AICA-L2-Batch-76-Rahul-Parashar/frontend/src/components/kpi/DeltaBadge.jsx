import { formatPct } from '../../lib/formatters';

export default function DeltaBadge({ delta }) {
  if (!delta) {
    return <span className="text-xs font-mono-figures text-mist">—</span>;
  }
  const { pct, direction } = delta;
  const color = direction === 'up' ? 'text-verdigris bg-verdigris-soft' : direction === 'down' ? 'text-clay bg-clay-soft' : 'text-slate bg-line/40';
  const arrow = direction === 'up' ? '▲' : direction === 'down' ? '▼' : '–';
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-mono-figures px-1.5 py-0.5 rounded ${color}`}>
      {arrow} {formatPct(pct != null ? Math.abs(pct) : null)}
    </span>
  );
}
