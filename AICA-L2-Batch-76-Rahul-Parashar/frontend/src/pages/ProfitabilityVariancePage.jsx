import Breadcrumb from '../components/layout/Breadcrumb';
import CausalChainView from '../components/causal/CausalChainView';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function ProfitabilityVariancePage() {
  const navigate = useNavigate();
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => navigate(-1)} className="text-slate hover:text-verdigris" aria-label="Back">
          <ArrowLeft size={18} />
        </button>
        <Breadcrumb />
      </div>
      <h1 className="font-heading text-2xl font-semibold text-ink mb-5">YoY Profit Variance</h1>
      <CausalChainView metricKey="pat" />
    </div>
  );
}
