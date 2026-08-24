import { useFinancials } from '../../context/FinancialsContext';
import {
  getPeriods,
  getSeries,
  getDerivedSeries,
  getWorkingCapitalSeries,
  getTotalDebtSeries,
  latestAndPriorFromComputedSeries,
  getYoyDelta,
} from '../../lib/selectors';
import { formatINR, formatPct, formatNumber } from '../../lib/formatters';
import KpiTile from './KpiTile';

function toSparkline(periods, series) {
  return periods.map((p) => ({ period: p, value: series[p] ?? null }));
}

export default function KpiGrid() {
  const { financials, displayUnit } = useFinancials();
  const periods = getPeriods(financials, 'annual');

  const revenue = getSeries(financials, 'profit_and_loss', 'total_revenue') || {};
  const ebitda = getDerivedSeries(financials, 'ebitda');
  const ebitdaMargin = getDerivedSeries(financials, 'ebitda_margin_pct');
  const pat = getSeries(financials, 'profit_and_loss', 'pat') || {};
  const cash = getSeries(financials, 'balance_sheet', 'cash_and_bank') || {};
  const workingCapital = getWorkingCapitalSeries(financials);
  const totalDebt = getTotalDebtSeries(financials);
  const roePat = getSeries(financials, 'ratios', 'roe_pat_pct') || {};
  const roce = getSeries(financials, 'ratios', 'roce_pct') || {};
  const eps = getSeries(financials, 'profit_and_loss', 'basic_eps') || {};

  const latest = (series) => (periods.length ? series[periods[periods.length - 1]] ?? null : null);
  const prior = (series) => (periods.length > 1 ? series[periods[periods.length - 2]] ?? null : null);

  const tiles = [
    {
      label: 'Revenue',
      to: '/revenue',
      valueDisplay: formatINR(latest(revenue), { unit: displayUnit }),
      delta: getYoyDelta(latest(revenue), prior(revenue)),
      sparklineData: toSparkline(periods, revenue),
    },
    {
      label: 'EBITDA',
      to: '/profitability',
      valueDisplay: `${formatINR(latest(ebitda), { unit: displayUnit })} · ${formatPct(latest(ebitdaMargin))}`,
      delta: getYoyDelta(latest(ebitda), prior(ebitda)),
      sparklineData: toSparkline(periods, ebitda),
    },
    {
      label: 'Net Profit (PAT)',
      to: '/profitability',
      valueDisplay: formatINR(latest(pat), { unit: displayUnit }),
      delta: getYoyDelta(latest(pat), prior(pat)),
      sparklineData: toSparkline(periods, pat),
    },
    {
      label: 'Cash & Bank',
      to: '/liquidity',
      valueDisplay: formatINR(latest(cash), { unit: displayUnit }),
      delta: getYoyDelta(latest(cash), prior(cash)),
      sparklineData: toSparkline(periods, cash),
    },
    {
      label: 'Working Capital',
      to: '/liquidity',
      valueDisplay: formatINR(latest(workingCapital), { unit: displayUnit }),
      delta: getYoyDelta(latest(workingCapital), prior(workingCapital)),
      sparklineData: toSparkline(periods, workingCapital),
    },
    {
      label: 'Total Debt',
      to: '/debt',
      valueDisplay: formatINR(latest(totalDebt), { unit: displayUnit }),
      delta: getYoyDelta(latest(totalDebt), prior(totalDebt)),
      sparklineData: toSparkline(periods, totalDebt),
    },
    {
      label: 'ROE (PAT) / ROCE',
      to: '/returns',
      valueDisplay: `${formatPct(latest(roePat) != null ? latest(roePat) * 100 : null)} / ${formatPct(latest(roce) != null ? latest(roce) * 100 : null)}`,
      delta: getYoyDelta(latest(roePat), prior(roePat)),
      sparklineData: toSparkline(periods, roePat),
    },
    {
      label: 'EPS (Basic)',
      to: '/profitability',
      valueDisplay: latest(eps) != null ? `₹${formatNumber(latest(eps))}` : '—',
      delta: getYoyDelta(latest(eps), prior(eps)),
      sparklineData: toSparkline(periods, eps),
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {tiles.map((tile) => (
        <KpiTile key={tile.label} {...tile} />
      ))}
    </div>
  );
}
