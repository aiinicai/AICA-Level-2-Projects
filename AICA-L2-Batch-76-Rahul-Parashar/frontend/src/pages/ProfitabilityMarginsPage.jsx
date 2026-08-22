import DrillDownPage from '../components/common/DrillDownPage';
import MarginTrendChart from '../components/charts/MarginTrendChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getDerivedSeries, getSeries } from '../lib/selectors';
import { formatPct } from '../lib/formatters';

function scale100(series, periods) {
  return periods.map((p) => ({ period: p, value: series[p] != null ? series[p] * 100 : null }));
}

function asIs(series, periods) {
  return periods.map((p) => ({ period: p, value: series[p] ?? null }));
}

export default function ProfitabilityMarginsPage() {
  const { financials } = useFinancials();
  const periods = getPeriods(financials, 'annual');

  const series = [
    { key: 'gross_margin_pct', label: 'Gross Margin', data: asIs(getDerivedSeries(financials, 'gross_margin_pct'), periods) },
    { key: 'ebitda_margin_pct', label: 'EBITDA Margin', data: asIs(getDerivedSeries(financials, 'ebitda_margin_pct'), periods) },
    { key: 'net_profit_margin_pct', label: 'PAT Margin', data: scale100(getSeries(financials, 'ratios', 'net_profit_margin_pct') || {}, periods) },
  ];

  return (
    <DrillDownPage
      title="Margin Trend"
      primary={
        <Card title="Gross / EBITDA / PAT Margin">
          <MarginTrendChart periods={periods} series={series} valueFormatter={(v) => formatPct(v)} />
        </Card>
      }
      secondary={
        <Card title="About this view">
          <p className="text-sm text-slate font-body">
            Gross and EBITDA margin are computed from parsed P&L line items; PAT margin is read from the Ratio
            Analysis sheet.
          </p>
        </Card>
      }
    />
  );
}
