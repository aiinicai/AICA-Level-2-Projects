import KpiGrid from '../components/kpi/KpiGrid';
import { useFinancials } from '../context/FinancialsContext';

export default function Home() {
  const { financials } = useFinancials();
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
      <h1 className="font-heading text-2xl font-semibold text-ink">{financials?.company}</h1>
      <p className="text-slate font-body text-sm mb-6">
        {financials?.basis} basis · {financials?.periods?.annual?.[0]}–{financials?.periods?.annual?.[financials?.periods?.annual?.length - 1]}
      </p>
      <KpiGrid />
    </div>
  );
}
