import DrillDownPage from '../components/common/DrillDownPage';
import RatioTrendChart from '../components/charts/RatioTrendChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeries, getTotalDebtSeries } from '../lib/selectors';
import { formatRatioX } from '../lib/formatters';

export default function DebtCoveragePage() {
  const { financials } = useFinancials();
  const periods = getPeriods(financials, 'annual');
  const totalDebt = getTotalDebtSeries(financials);
  const equity = getSeries(financials, 'balance_sheet', 'total_shareholders_funds') || {};
  const interestCoverage = getSeries(financials, 'ratios', 'interest_coverage_ratio_x') || {};

  const debtEquitySeries = periods.map((p) => ({
    period: p,
    value: totalDebt[p] != null && equity[p] ? totalDebt[p] / equity[p] : null,
  }));
  const coverageSeries = periods.map((p) => ({ period: p, value: interestCoverage[p] ?? null }));

  return (
    <DrillDownPage
      title="Debt Coverage"
      primary={
        <Card title="Debt / Equity Trend">
          <RatioTrendChart periods={periods} series={[{ key: 'de', label: 'Debt / Equity', data: debtEquitySeries }]} valueFormatter={(v) => formatRatioX(v)} />
        </Card>
      }
      secondary={
        <Card title="Interest Coverage Ratio">
          <RatioTrendChart periods={periods} series={[{ key: 'icr', label: 'Interest Coverage', data: coverageSeries, color: '#B5654A' }]} valueFormatter={(v) => formatRatioX(v)} height={260} />
        </Card>
      }
    />
  );
}
