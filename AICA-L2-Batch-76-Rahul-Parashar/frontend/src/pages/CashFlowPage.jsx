import Breadcrumb from '../components/layout/Breadcrumb';
import EmptyState from '../components/common/EmptyState';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function CashFlowPage() {
  const navigate = useNavigate();
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => navigate(-1)} className="text-slate hover:text-verdigris" aria-label="Back">
          <ArrowLeft size={18} />
        </button>
        <Breadcrumb />
      </div>
      <h1 className="font-heading text-2xl font-semibold text-ink mb-5">Cash Flow (CFO / CFI / CFF)</h1>
      <EmptyState message="Cash Flow Statement was not populated in the source workbook (this Ratio-file template ships a Cash Flow tab, but this file's copy is a blank template). Wire this page up once CFO/CFI/CFF data is available in an uploaded file." />
    </div>
  );
}
