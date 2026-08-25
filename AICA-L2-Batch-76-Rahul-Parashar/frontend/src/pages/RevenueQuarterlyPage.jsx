import DrillDownPage from '../components/common/DrillDownPage';
import TrendChart from '../components/charts/TrendChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeriesForChart } from '../lib/selectors';
import { formatINR } from '../lib/formatters';

export default function RevenueQuarterlyPage() {
  const { financials, displayUnit } = useFinancials();
  const periods = getPeriods(financials, 'quarterly');

  const series = [
    { key: 'net_sales', label: 'Net Sales', data: getSeriesForChart(financials, 'quarterly', 'net_sales', 'quarterly') },
    { key: 'total_income', label: 'Total Income', data: getSeriesForChart(financials, 'quarterly', 'total_income', 'quarterly') },
  ];

  return (
    <DrillDownPage
      title="Quarterly Revenue Trend"
      primary={
        <Card title="Quarterly Net Sales & Total Income" subtitle={periods.join(', ') || 'No quarterly data detected'}>
          <TrendChart periods={periods} series={series} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} emptyMessage="No quarterly results were found in this workbook." />
        </Card>
      }
      secondary={
        <Card title="About this view">
          <p className="text-sm text-slate font-body">Quarterly figures as reported in the workbook's quarterly results block.</p>
        </Card>
      }
    />
  );
}
