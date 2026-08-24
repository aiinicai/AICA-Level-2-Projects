import DrillDownPage from '../components/common/DrillDownPage';
import StackedBreakupChart from '../components/charts/StackedBreakupChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeriesForChart, getLatestValue } from '../lib/selectors';
import { formatINR } from '../lib/formatters';

export default function CostPage() {
  const { financials, displayUnit } = useFinancials();
  const periods = getPeriods(financials, 'annual');

  const series = [
    { key: 'cogs', label: 'COGS', data: getSeriesForChart(financials, 'profit_and_loss', 'cogs') },
    { key: 'employee_benefit_expense', label: 'Employee Cost', data: getSeriesForChart(financials, 'profit_and_loss', 'employee_benefit_expense') },
    { key: 'other_expenses', label: 'Other Expenses', data: getSeriesForChart(financials, 'profit_and_loss', 'other_expenses') },
    { key: 'depreciation_amortisation', label: 'D&A', data: getSeriesForChart(financials, 'profit_and_loss', 'depreciation_amortisation') },
    { key: 'finance_costs', label: 'Finance Costs', data: getSeriesForChart(financials, 'profit_and_loss', 'finance_costs') },
  ];

  const totalExpenses = getLatestValue(financials, 'profit_and_loss', 'total_expenses');

  return (
    <DrillDownPage
      title="Cost Structure & Margins"
      primary={
        <Card title="Expense Breakup by Year">
          <StackedBreakupChart periods={periods} series={series} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} />
        </Card>
      }
      secondary={
        <Card title="Snapshot">
          <p className="text-xs text-slate font-body">Total Expenses (latest)</p>
          <p className="font-mono-figures text-2xl text-ink mt-1">{formatINR(totalExpenses, { unit: displayUnit })}</p>
        </Card>
      }
      subMetrics={[
        { to: '/cost/breakup', label: 'Expense Breakup', description: 'Full cost line-item detail' },
        { to: '/cost/common-size', label: 'Common-Size Costs', description: 'Cost as % of revenue, trended' },
      ]}
    />
  );
}
