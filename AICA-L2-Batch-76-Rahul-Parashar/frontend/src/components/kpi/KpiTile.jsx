import { Link } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import Sparkline from './Sparkline';
import DeltaBadge from './DeltaBadge';

export default function KpiTile({ label, valueDisplay, sparklineData, delta, to }) {
  return (
    <div className="relative bg-paper rounded-lg border border-line p-4 hover:border-verdigris transition-colors group">
      <Link to={to} className="block focus:outline-none">
        <p className="font-heading text-xs font-medium text-slate uppercase tracking-wide">{label}</p>
        <p className="font-mono-figures text-xl text-ink mt-1.5">{valueDisplay}</p>
        <div className="flex items-center justify-between mt-1">
          <DeltaBadge delta={delta} />
        </div>
        <Sparkline data={sparklineData} />
      </Link>
      <Link
        to={`${to}?explain=true`}
        aria-label={`Explain ${label}`}
        className="absolute top-3 right-3 text-mist opacity-0 group-hover:opacity-100 focus:opacity-100 hover:text-verdigris focus:outline-none focus:ring-2 focus:ring-verdigris rounded"
      >
        <Sparkles size={14} />
      </Link>
    </div>
  );
}
