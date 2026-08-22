import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

export default function SubMetricCard({ to, label, value, description }) {
  return (
    <Link
      to={to}
      className="flex items-center justify-between gap-3 bg-paper rounded-lg border border-line p-4 hover:border-verdigris focus:outline-none focus:ring-2 focus:ring-verdigris transition-colors"
    >
      <div>
        <p className="font-heading text-sm font-medium text-ink">{label}</p>
        {description && <p className="text-xs text-slate font-body mt-0.5">{description}</p>}
        {value != null && <p className="font-mono-figures text-lg text-ink mt-1">{value}</p>}
      </div>
      <ChevronRight size={18} className="text-mist shrink-0" />
    </Link>
  );
}
