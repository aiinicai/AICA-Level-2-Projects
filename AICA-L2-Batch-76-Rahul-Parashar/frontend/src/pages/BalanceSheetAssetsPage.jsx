import DrillDownPage from '../components/common/DrillDownPage';
import TrendChart from '../components/charts/TrendChart';
import DonutComposition from '../components/charts/DonutComposition';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeriesForChart, getSeries } from '../lib/selectors';
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

export default function BalanceSheetAssetsPage() {
  const { financials, displayUnit } = useFinancials();
  const periods = getPeriods(financials, 'annual');
  const latestPeriod = periods[periods.length - 1];

  const assetItems = ASSET_KEYS.map(([key, label]) => ({
    label,
    value: (getSeries(financials, 'balance_sheet', key) || {})[latestPeriod],
  }));

  const trendSeries = [
    { key: 'total_current_assets', label: 'Current Assets', data: getSeriesForChart(financials, 'balance_sheet', 'total_current_assets') },
    { key: 'total_non_current_assets', label: 'Non-Current Assets', data: getSeriesForChart(financials, 'balance_sheet', 'total_non_current_assets') },
  ];

  return (
    <DrillDownPage
      title="Assets Composition"
      primary={
        <Card title="Current vs. Non-Current Assets Trend">
          <TrendChart periods={periods} series={trendSeries} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} />
        </Card>
      }
      secondary={
        <Card title={`Composition — ${latestPeriod}`}>
          <DonutComposition items={assetItems} valueFormatter={(v) => formatINR(v, { unit: displayUnit })} />
        </Card>
      }
    />
  );
}
