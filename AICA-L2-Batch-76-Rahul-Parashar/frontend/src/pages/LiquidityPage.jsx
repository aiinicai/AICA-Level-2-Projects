import DrillDownPage from '../components/common/DrillDownPage';
import RatioTrendChart from '../components/charts/RatioTrendChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeriesForChart, getLatestValue } from '../lib/selectors';
import { formatRatioX } from '../lib/formatters';

export default function LiquidityPage() {
  const { financials } = useFinancials();
  const periods = getPeriods(financials, 'annual');

  const series = [
    { key: 'current_ratio_x', label: 'Current Ratio', data: getSeriesForChart(financials, 'ratios', 'current_ratio_x') },
    { key: 'quick_ratio_x', label: 'Quick Ratio', data: getSeriesForChart(financials, 'ratios', 'quick_ratio_x') },
    { key: 'cash_ratio_x', label: 'Cash Ratio', data: getSeriesForChart(financials, 'ratios', 'cash_ratio_x') },
  ];

  const currentRatio = getLatestValue(financials, 'ratios', 'current_ratio_x');

  return (
    <DrillDownPage
      title="Liquidity & Working Capital"
      primary={
        <Card title="Current / Quick / Cash Ratio Trend">
          <RatioTrendChart periods={periods} series={series} valueFormatter={(v) => formatRatioX(v)} />
        </Card>
      }
      secondary={
        <Card title="Snapshot">
          <p className="text-xs text-slate font-body">Current Ratio (latest)</p>
          <p className="font-mono-figures text-2xl text-ink mt-1">{formatRatioX(currentRatio)}</p>
        </Card>
      }
      subMetrics={[
        { to: '/liquidity/ratios', label: 'Liquidity Ratios', description: 'Full ratio trend detail' },
        { to: '/liquidity/cycle', label: 'Cash Conversion Cycle', description: 'Inventory, receivable & payable days' },
      ]}
    />
  );
}
