import DrillDownPage from '../components/common/DrillDownPage';
import RatioTrendChart from '../components/charts/RatioTrendChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeriesForChart, getLatestValue } from '../lib/selectors';
import { formatDays } from '../lib/formatters';

export default function LiquidityCyclePage() {
  const { financials } = useFinancials();
  const periods = getPeriods(financials, 'annual');

  const series = [
    { key: 'inventory_days', label: 'Inventory Days', data: getSeriesForChart(financials, 'ratios', 'inventory_days') },
    { key: 'days_sales_outstanding', label: 'Days Sales Outstanding', data: getSeriesForChart(financials, 'ratios', 'days_sales_outstanding') },
    { key: 'payables_days', label: 'Payables Days', data: getSeriesForChart(financials, 'ratios', 'payables_days') },
    { key: 'cash_conversion_cycle_days', label: 'Cash Conversion Cycle', data: getSeriesForChart(financials, 'ratios', 'cash_conversion_cycle_days') },
  ];

  const ccc = getLatestValue(financials, 'ratios', 'cash_conversion_cycle_days');

  return (
    <DrillDownPage
      title="Cash Conversion Cycle"
      primary={
        <Card title="Working Capital Cycle Days">
          <RatioTrendChart periods={periods} series={series} valueFormatter={(v) => formatDays(v)} height={340} />
        </Card>
      }
      secondary={
        <Card title="Snapshot">
          <p className="text-xs text-slate font-body">Cash Conversion Cycle (latest)</p>
          <p className="font-mono-figures text-2xl text-ink mt-1">{formatDays(ccc)}</p>
        </Card>
      }
    />
  );
}
