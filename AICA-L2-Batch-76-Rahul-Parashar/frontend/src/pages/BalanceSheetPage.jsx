import DrillDownPage from '../components/common/DrillDownPage';
import TrendChart from '../components/charts/TrendChart';
import DonutComposition from '../components/charts/DonutComposition';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeriesForChart, getSeries, getLatestValue } from '../lib/selectors';
import { formatINR } from '../lib/formatters';

const ASSET_KEYS = [
  ['fixed_assets', 'Fixed Assets'],
  ['non_current_investments', 'Non-Current Investments'],
  ['current_investments', 'Current Investments'],
  ['inventories', 'Inventories'],
  ['trade_receivables', 'Trade Receivables'],
  ['cash_and_bank', 'Cash & Bank'],
  ['other_current_assets', 'Other Current Assets'],
];

const LIAB_KEYS = [
  ['total_shareholders_funds', "Shareholders' Funds"],
  ['long_term_borrowings', 'Long Term Borrowings'],
  ['short_term_borrowings', 'Short Term Borrowings'],
  ['trade_payables', 'Trade Payables'],
  ['other_current_liabilities', 'Other Current Liabilities'],
];

export default function BalanceSheetPage() {
  const { financials, displayUnit } = useFinancials();
  const periods = getPeriods(financials, 'annual');
  const latestPeriod = periods[periods.length - 1];

  const assetItems = ASSET_KEYS.map(([key, label]) => ({
    label,
    value: (getSeries(financials, 'balance_sheet', key) || {})[latestPeriod],
  }));
  const liabItems = LIAB_KEYS.map(([key, label]) => ({
    label,
    value: (getSeries(financials, 'balance_sheet', key) || {})[latestPeriod],
  }));

  const netWorthSeries = [{ key: 'total_shareholders_funds', label: "Shareholders' Funds", data: getSeriesForChart(financials, 'balance_sheet', 'total_shareholders_funds') }];
  const totalAssets = getLatestValue(financials, 'balance_sheet', 'total_assets');

  return (
    <DrillDownPage
      title="Balance Sheet Health"
      primary={
        <Card title="Net Worth Trend" subtitle={`Total Assets (${latestPeriod}): ${formatINR(totalAssets, { unit: displayUnit })}`}>
          <TrendChart periods={periods} series={netWorthSeries} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} />
        </Card>
      }
      secondary={
        <div className="space-y-4">
          <Card title={`Assets — ${latestPeriod}`}>
            <DonutComposition items={assetItems} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} height={200} />
          </Card>
          <Card title={`Liabilities & Equity — ${latestPeriod}`}>
            <DonutComposition items={liabItems} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} height={200} />
          </Card>
        </div>
      }
      subMetrics={[
        { to: '/balance-sheet/assets', label: 'Assets Composition', description: 'Detailed asset breakdown' },
        { to: '/balance-sheet/liabilities', label: 'Liabilities & Net Worth', description: 'Funding mix over time' },
      ]}
    />
  );
}
