import DrillDownPage from '../components/common/DrillDownPage';
import RatioTrendChart from '../components/charts/RatioTrendChart';
import Card from '../components/common/Card';
import { useFinancials } from '../context/FinancialsContext';
import { getPeriods, getSeries } from '../lib/selectors';
import { formatPct, formatRatioX } from '../lib/formatters';

function computeDupont(periods, pat, revenue, assetTurnover, assets, equity) {
  const margin = {};
  const leverage = {};
  const roe = {};
  for (const p of periods) {
    margin[p] = pat[p] != null && revenue[p] ? (100 * pat[p]) / revenue[p] : null;
    leverage[p] = assets[p] != null && equity[p] ? assets[p] / equity[p] : null;
    const at = assetTurnover[p];
    roe[p] = margin[p] != null && at != null && leverage[p] != null ? (margin[p] / 100) * at * leverage[p] * 100 : null;
  }
  return { margin, leverage, roe };
}

export default function ReturnsDupontPage() {
  const { financials } = useFinancials();
  const periods = getPeriods(financials, 'annual');

  const pat = getSeries(financials, 'profit_and_loss', 'pat') || {};
  const revenue = getSeries(financials, 'profit_and_loss', 'total_revenue') || {};
  const assetTurnover = getSeries(financials, 'ratios', 'total_asset_turnover_x') || {};
  const assets = getSeries(financials, 'balance_sheet', 'total_assets') || {};
  const equity = getSeries(financials, 'balance_sheet', 'total_shareholders_funds') || {};

  const { margin, leverage, roe } = computeDupont(periods, pat, revenue, assetTurnover, assets, equity);

  const marginSeries = periods.map((p) => ({ period: p, value: margin[p] }));
  const roeSeries = periods.map((p) => ({ period: p, value: roe[p] }));

  return (
    <DrillDownPage
      title="DuPont ROE Decomposition"
      primary={
        <Card title="Net Margin × Asset Turnover × Leverage = ROE" subtitle="Computed ROE (dashed sanity-check) vs. Net Margin trend">
          <RatioTrendChart
            periods={periods}
            series={[
              { key: 'margin', label: 'Net Profit Margin %', data: marginSeries },
              { key: 'roe_computed', label: 'ROE (computed)', data: roeSeries, dashed: true, color: '#B5654A' },
            ]}
            valueFormatter={(v) => formatPct(v)}
          />
        </Card>
      }
      secondary={
        <Card title="Latest Year Components">
          <table className="w-full text-sm">
            <tbody>
              <tr className="border-b border-line">
                <td className="py-1.5 text-slate font-body">Net Profit Margin</td>
                <td className="py-1.5 text-right font-mono-figures text-ink">{formatPct(margin[periods[periods.length - 1]])}</td>
              </tr>
              <tr className="border-b border-line">
                <td className="py-1.5 text-slate font-body">Asset Turnover</td>
                <td className="py-1.5 text-right font-mono-figures text-ink">{formatRatioX(assetTurnover[periods[periods.length - 1]])}</td>
              </tr>
              <tr className="border-b border-line">
                <td className="py-1.5 text-slate font-body">Equity Multiplier</td>
                <td className="py-1.5 text-right font-mono-figures text-ink">{formatRatioX(leverage[periods[periods.length - 1]])}</td>
              </tr>
              <tr>
                <td className="py-1.5 text-ink font-body font-medium">ROE (computed)</td>
                <td className="py-1.5 text-right font-mono-figures text-verdigris font-medium">{formatPct(roe[periods[periods.length - 1]])}</td>
              </tr>
            </tbody>
          </table>
        </Card>
      }
    />
  );
}
