import DrillDownPage from '../components/common/DrillDownPage';
import RatioTrendChart from '../components/charts/RatioTrendChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeries } from '../lib/selectors';
import { formatPct } from '../lib/formatters';

function pctOfRevenueSeries(periods, revenueSeries, costSeries) {
  return periods.map((p) => {
    const rev = revenueSeries?.[p];
    const cost = costSeries?.[p];
    const value = rev && cost != null ? (100 * cost) / rev : null;
    return { period: p, value };
  });
}

export default function CostCommonSizePage() {
  const { financials } = useFinancials();
  const periods = getPeriods(financials, 'annual');
  const revenue = getSeries(financials, 'profit_and_loss', 'total_revenue') || {};

  const series = [
    { key: 'cogs_pct', label: 'COGS % of Revenue', data: pctOfRevenueSeries(periods, revenue, getSeries(financials, 'profit_and_loss', 'cogs')) },
    { key: 'employee_pct', label: 'Employee Cost %', data: pctOfRevenueSeries(periods, revenue, getSeries(financials, 'profit_and_loss', 'employee_benefit_expense')) },
    { key: 'other_pct', label: 'Other Expenses %', data: pctOfRevenueSeries(periods, revenue, getSeries(financials, 'profit_and_loss', 'other_expenses')) },
  ];

  return (
    <DrillDownPage
      title="Common-Size Costs"
      primary={
        <Card title="Cost as % of Revenue, Trended">
          <RatioTrendChart periods={periods} series={series} valueFormatter={(v) => formatPct(v)} />
        </Card>
      }
      secondary={
        <Card title="About this view">
          <p className="text-sm text-slate font-body">
            Each cost line as a share of total revenue for the same year — computed from the parsed P&L, not a
            bundled common-size sheet.
          </p>
        </Card>
      }
    />
  );
}
