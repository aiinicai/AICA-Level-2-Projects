import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import Breadcrumb from '../layout/Breadcrumb';
import SubMetricCard from './SubMetricCard';
import CausalChainView from '../causal/CausalChainView';

export default function DrillDownPage({ title, primary, secondary, subMetrics, explainMetricKey }) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [explainOpen, setExplainOpen] = useState(searchParams.get('explain') === 'true');

  function toggleExplain() {
    const next = !explainOpen;
    setExplainOpen(next);
    const params = new URLSearchParams(searchParams);
    if (next) params.set('explain', 'true');
    else params.delete('explain');
    setSearchParams(params, { replace: true });
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => navigate(-1)} className="text-slate hover:text-verdigris focus:outline-none focus:ring-2 focus:ring-verdigris rounded" aria-label="Back">
          <ArrowLeft size={18} />
        </button>
        <Breadcrumb />
      </div>
      <h1 className="font-heading text-2xl font-semibold text-ink mb-5">{title}</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-5">
        <div className="lg:col-span-2 min-w-0">{primary}</div>
        <div className="min-w-0">{secondary}</div>
      </div>

      {explainMetricKey && (
        <div className="mb-5">
          <button
            onClick={toggleExplain}
            className="text-sm font-body font-medium text-verdigris border border-verdigris rounded-lg px-3 py-1.5 hover:bg-verdigris-soft focus:outline-none focus:ring-2 focus:ring-verdigris"
          >
            {explainOpen ? 'Hide explanation' : 'Explain this'}
          </button>
          {explainOpen && (
            <div className="mt-4">
              <CausalChainView metricKey={explainMetricKey} />
            </div>
          )}
        </div>
      )}

      {subMetrics && subMetrics.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {subMetrics.map((m) => (
            <SubMetricCard key={m.to} {...m} />
          ))}
        </div>
      )}
    </div>
  );
}
