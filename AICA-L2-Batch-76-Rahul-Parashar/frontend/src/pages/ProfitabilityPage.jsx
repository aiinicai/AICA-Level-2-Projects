import { useState } from 'react';
import DrillDownPage from '../components/common/DrillDownPage';
import WaterfallBridge from '../components/charts/WaterfallBridge';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeries, getDerivedSeries } from '../lib/selectors';
import { formatINR } from '../lib/formatters';

export default function ProfitabilityPage() {
  const { financials, displayUnit } = useFinancials();
  const periods = getPeriods(financials, 'annual');
  const [year, setYear] = useState(periods[periods.length - 1]);
  const selectedYear = periods.includes(year) ? year : periods[periods.length - 1];

  const revenue = getSeries(financials, 'profit_and_loss', 'total_revenue') || {};
  const ebitda = getDerivedSeries(financials, 'ebitda');
  const ebit = getDerivedSeries(financials, 'ebit');
  const pbt = getSeries(financials, 'profit_and_loss', 'pbt') || {};
  const pat = getSeries(financials, 'profit_and_loss', 'pat') || {};

  const r = revenue[selectedYear];
  const eb = ebitda[selectedYear];
  const ei = ebit[selectedYear];
  const p1 = pbt[selectedYear];
  const p2 = pat[selectedYear];

  const steps = [
    { label: 'Revenue', value: r, isTotal: true },
    { label: 'Less: COGS & Opex', value: r != null && eb != null ? eb - r : null, isTotal: false },
    { label: 'EBITDA', value: eb, isTotal: true },
    { label: 'Less: D&A', value: eb != null && ei != null ? ei - eb : null, isTotal: false },
    { label: 'EBIT', value: ei, isTotal: true },
    { label: 'Less: Finance & Other', value: ei != null && p1 != null ? p1 - ei : null, isTotal: false },
    { label: 'PBT', value: p1, isTotal: true },
    { label: 'Less: Tax', value: p1 != null && p2 != null ? p2 - p1 : null, isTotal: false },
    { label: 'PAT', value: p2, isTotal: true },
  ];

  return (
    <DrillDownPage
      title="Profitability"
      explainMetricKey="pat"
      primary={
        <Card
          title="Revenue → PAT Bridge"
          action={
            <select
              value={selectedYear}
              onChange={(e) => setYear(e.target.value)}
              className="border border-line rounded-lg px-2 py-1 text-xs font-mono-figures bg-paper focus:outline-none focus:ring-2 focus:ring-verdigris"
            >
              {periods.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          }
        >
          <WaterfallBridge steps={steps} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} />
        </Card>
      }
      secondary={
        <Card title="Snapshot">
          <p className="text-xs text-slate font-body">PAT — {selectedYear}</p>
          <p className="font-mono-figures text-2xl text-ink mt-1">{formatINR(p2, { unit: displayUnit })}</p>
        </Card>
      }
      subMetrics={[
        { to: '/profitability/margins', label: 'Margin Trend', description: 'Gross / EBITDA / PAT margin over time' },
        { to: '/profitability/variance', label: 'YoY Variance', description: 'What drove the change in profit' },
      ]}
    />
  );
}
