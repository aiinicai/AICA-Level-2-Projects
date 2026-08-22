import DrillDownPage from '../components/common/DrillDownPage';
import TrendChart from '../components/charts/TrendChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getTotalDebtSeries, latestAndPriorFromComputedSeries, getLatestValue } from '../lib/selectors';
import { formatINR, formatRatioX } from '../lib/formatters';

export default function DebtPage() {
  const { financials, displayUnit } = useFinancials();
  const periods = getPeriods(financials, 'annual');
  const totalDebt = getTotalDebtSeries(financials);
  const { latest } = latestAndPriorFromComputedSeries(financials, totalDebt);
  const interestCoverage = getLatestValue(financials, 'ratios', 'interest_coverage_ratio_x');

  const series = [{ key: 'total_debt', label: 'Total Debt', data: periods.map((p) => ({ period: p, value: totalDebt[p] })) }];

  return (
    <DrillDownPage
      title="Debt & Solvency"
      primary={
        <Card title="Total Debt Trend">
          <TrendChart periods={periods} series={series} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} />
        </Card>
      }
      secondary={
        <Card title="Snapshot">
          <p className="text-xs text-slate font-body">Total Debt (latest)</p>
          <p className="font-mono-figures text-2xl text-ink mt-1">{formatINR(latest, { unit: displayUnit })}</p>
          <p className="text-xs text-slate font-body mt-3">Interest Coverage Ratio</p>
          <p className="font-mono-figures text-xl text-ink mt-1">{formatRatioX(interestCoverage)}</p>
        </Card>
      }
      subMetrics={[{ to: '/debt/coverage', label: 'Debt Coverage', description: 'Debt/Equity & interest coverage trend' }]}
    />
  );
}
