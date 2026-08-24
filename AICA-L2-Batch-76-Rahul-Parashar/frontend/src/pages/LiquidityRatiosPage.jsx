import DrillDownPage from '../components/common/DrillDownPage';
import RatioTrendChart from '../components/charts/RatioTrendChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeriesForChart } from '../lib/selectors';
import { formatRatioX, formatNumber } from '../lib/formatters';

export default function LiquidityRatiosPage() {
  const { financials } = useFinancials();
  const periods = getPeriods(financials, 'annual');

  const series = [
    { key: 'current_ratio_x', label: 'Current Ratio', data: getSeriesForChart(financials, 'ratios', 'current_ratio_x') },
    { key: 'quick_ratio_x', label: 'Quick Ratio', data: getSeriesForChart(financials, 'ratios', 'quick_ratio_x') },
    { key: 'cash_ratio_x', label: 'Cash Ratio', data: getSeriesForChart(financials, 'ratios', 'cash_ratio_x') },
    { key: 'working_capital_turnover_x', label: 'Working Capital Turnover', data: getSeriesForChart(financials, 'ratios', 'working_capital_turnover_x') },
  ];

  return (
    <DrillDownPage
      title="Liquidity Ratios"
      primary={
        <Card title="Liquidity Ratio Trend">
          <RatioTrendChart periods={periods} series={series} valueFormatter={(v) => formatNumber(v)} height={340} />
        </Card>
      }
      secondary={
        <Card title="About this view">
          <p className="text-sm text-slate font-body">All ratios shown in multiples (x), as reported in the Ratio Analysis sheet.</p>
        </Card>
      }
    />
  );
}
