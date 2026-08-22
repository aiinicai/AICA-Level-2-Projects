import DrillDownPage from '../components/common/DrillDownPage';
import RatioTrendChart from '../components/charts/RatioTrendChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeries, getLatestValue } from '../lib/selectors';
import { formatPct } from '../lib/formatters';

function pctSeries(series, periods) {
  return periods.map((p) => ({ period: p, value: series[p] != null ? series[p] * 100 : null }));
}

export default function ReturnsPage() {
  const { financials } = useFinancials();
  const periods = getPeriods(financials, 'annual');

  const series = [
    { key: 'roe_pat_pct', label: 'ROE (PAT)', data: pctSeries(getSeries(financials, 'ratios', 'roe_pat_pct') || {}, periods) },
    { key: 'roce_pct', label: 'ROCE', data: pctSeries(getSeries(financials, 'ratios', 'roce_pct') || {}, periods) },
  ];

  const roe = getLatestValue(financials, 'ratios', 'roe_pat_pct');
  const roce = getLatestValue(financials, 'ratios', 'roce_pct');

  return (
    <DrillDownPage
      title="Returns & Efficiency"
      primary={
        <Card title="ROE (PAT) vs. ROCE Trend">
          <RatioTrendChart periods={periods} series={series} valueFormatter={(v) => formatPct(v)} />
        </Card>
      }
      secondary={
        <Card title="Snapshot">
          <p className="text-xs text-slate font-body">ROE (PAT) — latest</p>
          <p className="font-mono-figures text-xl text-ink mt-1">{formatPct(roe != null ? roe * 100 : null)}</p>
          <p className="text-xs text-slate font-body mt-3">ROCE — latest</p>
          <p className="font-mono-figures text-xl text-ink mt-1">{formatPct(roce != null ? roce * 100 : null)}</p>
        </Card>
      }
      subMetrics={[{ to: '/returns/dupont', label: 'DuPont ROE Decomposition', description: 'Margin × Turnover × Leverage' }]}
    />
  );
}
