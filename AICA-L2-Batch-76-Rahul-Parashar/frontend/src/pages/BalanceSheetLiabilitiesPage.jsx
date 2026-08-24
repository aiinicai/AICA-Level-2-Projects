import DrillDownPage from '../components/common/DrillDownPage';
import TrendChart from '../components/charts/TrendChart';
import DonutComposition from '../components/charts/DonutComposition';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeriesForChart, getSeries } from '../lib/selectors';
import { formatINR } from '../lib/formatters';

const LIAB_KEYS = [
  ['total_shareholders_funds', "Shareholders' Funds"],
  ['long_term_borrowings', 'Long Term Borrowings'],
  ['short_term_borrowings', 'Short Term Borrowings'],
  ['trade_payables', 'Trade Payables'],
  ['other_current_liabilities', 'Other Current Liabilities'],
];

export default function BalanceSheetLiabilitiesPage() {
  const { financials, displayUnit } = useFinancials();
  const periods = getPeriods(financials, 'annual');
  const latestPeriod = periods[periods.length - 1];

  const liabItems = LIAB_KEYS.map(([key, label]) => ({
    label,
    value: (getSeries(financials, 'balance_sheet', key) || {})[latestPeriod],
  }));

  const trendSeries = [{ key: 'total_shareholders_funds', label: 'Net Worth', data: getSeriesForChart(financials, 'balance_sheet', 'total_shareholders_funds') }];

  return (
    <DrillDownPage
      title="Liabilities & Net Worth"
      primary={
        <Card title="Net Worth Trend">
          <TrendChart periods={periods} series={trendSeries} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} />
        </Card>
      }
      secondary={
        <Card title={`Composition — ${latestPeriod}`}>
          <DonutComposition items={liabItems} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} />
        </Card>
      }
    />
  );
}
