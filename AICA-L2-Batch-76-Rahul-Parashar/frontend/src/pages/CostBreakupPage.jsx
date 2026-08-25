import DrillDownPage from '../components/common/DrillDownPage';
import StackedBreakupChart from '../components/charts/StackedBreakupChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeriesForChart } from '../lib/selectors';
import { formatINR } from '../lib/formatters';

export default function CostBreakupPage() {
  const { financials, displayUnit } = useFinancials();
  const periods = getPeriods(financials, 'annual');

  const series = [
    { key: 'cogs', label: 'COGS', data: getSeriesForChart(financials, 'profit_and_loss', 'cogs') },
    { key: 'purchase_of_stock_in_trade', label: 'Purchase of Stock-in-Trade', data: getSeriesForChart(financials, 'profit_and_loss', 'purchase_of_stock_in_trade') },
    { key: 'changes_in_inventories', label: 'Changes in Inventories', data: getSeriesForChart(financials, 'profit_and_loss', 'changes_in_inventories') },
    { key: 'employee_benefit_expense', label: 'Employee Cost', data: getSeriesForChart(financials, 'profit_and_loss', 'employee_benefit_expense') },
    { key: 'finance_costs', label: 'Finance Costs', data: getSeriesForChart(financials, 'profit_and_loss', 'finance_costs') },
    { key: 'depreciation_amortisation', label: 'D&A', data: getSeriesForChart(financials, 'profit_and_loss', 'depreciation_amortisation') },
    { key: 'other_expenses', label: 'Other Expenses', data: getSeriesForChart(financials, 'profit_and_loss', 'other_expenses') },
  ];

  return (
    <DrillDownPage
      title="Expense Breakup"
      primary={
        <Card title="Full Expense Line-Items">
          <StackedBreakupChart periods={periods} series={series} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} height={380} />
        </Card>
      }
      secondary={
        <Card title="About this view">
          <p className="text-sm text-slate font-body">Every expense line item extracted from the P&L, stacked by year.</p>
        </Card>
      }
    />
  );
}
