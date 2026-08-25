import DrillDownPage from '../components/common/DrillDownPage';
import StackedBreakupChart from '../components/charts/StackedBreakupChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeriesForChart } from '../lib/selectors';
import { formatINR } from '../lib/formatters';

export default function RevenueMixPage() {
  const { financials, displayUnit } = useFinancials();
  const periods = getPeriods(financials, 'annual');

  const series = [
    { key: 'revenue_from_operations', label: 'Revenue from Operations', data: getSeriesForChart(financials, 'profit_and_loss', 'revenue_from_operations') },
    { key: 'other_operating_revenue', label: 'Other Operating Revenue', data: getSeriesForChart(financials, 'profit_and_loss', 'other_operating_revenue') },
    { key: 'other_income', label: 'Other Income', data: getSeriesForChart(financials, 'profit_and_loss', 'other_income') },
  ];

  return (
    <DrillDownPage
      title="Revenue Mix"
      primary={
        <Card title="Revenue Composition by Year">
          <StackedBreakupChart periods={periods} series={series} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} />
        </Card>
      }
      secondary={
        <Card title="About this view">
          <p className="text-sm text-slate font-body">
            Shows how much of total revenue comes from core operations versus other operating revenue and other
            income, year over year.
          </p>
        </Card>
      }
    />
  );
}
