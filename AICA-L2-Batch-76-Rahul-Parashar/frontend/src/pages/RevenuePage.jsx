import DrillDownPage from '../components/common/DrillDownPage';
import TrendChart from '../components/charts/TrendChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeriesForChart, getSeriesForChartAgainstPeriods, getLatestValue, getPriorValue, getYoyDelta } from '../lib/selectors';
import { formatINR, formatPct } from '../lib/formatters';

export default function RevenuePage() {
  const { financials, displayUnit, peer } = useFinancials();
  const periods = getPeriods(financials, 'annual');
  const revenueSeries = getSeriesForChart(financials, 'profit_and_loss', 'total_revenue');
  const opRevSeries = getSeriesForChart(financials, 'profit_and_loss', 'revenue_from_operations');

  const latest = getLatestValue(financials, 'profit_and_loss', 'total_revenue');
  const prior = getPriorValue(financials, 'profit_and_loss', 'total_revenue');
  const delta = getYoyDelta(latest, prior);

  const series = [{ key: 'total_revenue', label: 'Total Revenue', data: revenueSeries }];
  if (peer) {
    series.push({
      key: 'peer_revenue',
      label: `${peer.name} Revenue`,
      data: getSeriesForChartAgainstPeriods(peer.financials, 'profit_and_loss', 'total_revenue', periods),
      dashed: true,
      color: '#6B7280',
    });
  }

  return (
    <DrillDownPage
      title="Revenue & Top-line Growth"
      explainMetricKey="total_revenue"
      primary={
        <Card title="Total Revenue Trend" subtitle={`${periods[0] || ''}–${periods[periods.length - 1] || ''}`}>
          <TrendChart periods={periods} series={series} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} />
        </Card>
      }
      secondary={
        <Card title="Snapshot">
          <p className="text-xs text-slate font-body">Latest Total Revenue</p>
          <p className="font-mono-figures text-2xl text-ink mt-1">{formatINR(latest, { unit: displayUnit })}</p>
          <p className="text-xs text-slate font-body mt-3">YoY Growth</p>
          <p className="font-mono-figures text-lg text-ink mt-1">{delta ? formatPct(delta.pct, { signed: true }) : '—'}</p>
          <p className="text-xs text-slate font-body mt-3">Revenue from Operations (latest)</p>
          <p className="font-mono-figures text-lg text-ink mt-1">
            {formatINR(opRevSeries[opRevSeries.length - 1]?.value, { unit: displayUnit })}
          </p>
        </Card>
      }
      subMetrics={[
        { to: '/revenue/mix', label: 'Revenue Mix', description: 'Operating vs. other revenue' },
        { to: '/revenue/quarterly', label: 'Quarterly Trend', description: 'FY26 quarterly progression' },
      ]}
    />
  );
}
