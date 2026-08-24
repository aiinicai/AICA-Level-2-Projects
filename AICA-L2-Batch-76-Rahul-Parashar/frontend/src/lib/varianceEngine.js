import { getSeries, getDerivedSeries } from './selectors';
import { FIELD_LABELS } from './fieldDictionary';

function val(series, period) {
  return series && series[period] != null ? series[period] : null;
}

function delta(series, periodA, periodB) {
  const a = val(series, periodA);
  const b = val(series, periodB);
  if (a == null || b == null) return null;
  return b - a;
}

/**
 * `sign` is +1 for a field that helps the metric when it grows (revenue-like) and -1
 * for a field that hurts the metric when it grows (cost-like).
 */
function buildNode(financials, statement, key, periodA, periodB, sign) {
  const series = statement === 'derived_metrics' ? getDerivedSeries(financials, key) : getSeries(financials, statement, key);
  const d = delta(series, periodA, periodB);
  if (d == null) return null;
  const nodeValue = sign * d;
  return {
    id: key,
    label: FIELD_LABELS[key] || key,
    value: nodeValue,
    direction: nodeValue > 0 ? 'positive' : nodeValue < 0 ? 'negative' : 'neutral',
  };
}

const DECOMPOSITIONS = {
  pat: {
    statement: 'profit_and_loss',
    metricLabel: 'Net Profit (PAT)',
    parts: [
      { key: 'total_revenue', sign: 1 },
      { key: 'cogs', sign: -1 },
      { key: 'purchase_of_stock_in_trade', sign: -1 },
      { key: 'changes_in_inventories', sign: -1 },
      { key: 'employee_benefit_expense', sign: -1 },
      { key: 'finance_costs', sign: -1 },
      { key: 'depreciation_amortisation', sign: -1 },
      { key: 'other_expenses', sign: -1 },
      { key: 'exceptional_items', sign: 1 },
      { key: 'total_tax', sign: -1 },
    ],
  },
  ebitda: {
    statement: 'derived_metrics',
    metricLabel: 'EBITDA',
    parts: [
      { key: 'total_revenue', sign: 1, statement: 'profit_and_loss' },
      { key: 'cogs', sign: -1, statement: 'profit_and_loss' },
      { key: 'purchase_of_stock_in_trade', sign: -1, statement: 'profit_and_loss' },
      { key: 'changes_in_inventories', sign: -1, statement: 'profit_and_loss' },
      { key: 'employee_benefit_expense', sign: -1, statement: 'profit_and_loss' },
      { key: 'other_expenses', sign: -1, statement: 'profit_and_loss' },
    ],
  },
  total_revenue: {
    statement: 'profit_and_loss',
    metricLabel: 'Revenue',
    parts: [
      { key: 'revenue_from_operations', sign: 1 },
      { key: 'other_operating_revenue', sign: 1 },
      { key: 'other_income', sign: 1 },
    ],
  },
};

/**
 * Pure, deterministic. Never calls the network. Returns a structured object whose
 * node values always sum exactly to centerDelta (a residual "Other / rounding" node
 * absorbs any gap so the causal chain is always arithmetically honest).
 */
export function explainVariance(financials, metricKey, periodA, periodB) {
  const config = DECOMPOSITIONS[metricKey];
  if (!config) return null;

  const centerSeries =
    config.statement === 'derived_metrics' ? getDerivedSeries(financials, metricKey) : getSeries(financials, config.statement, metricKey);
  const centerDelta = delta(centerSeries, periodA, periodB);

  const nodes = [];
  for (const part of config.parts) {
    const node = buildNode(financials, part.statement || config.statement, part.key, periodA, periodB, part.sign);
    if (node) nodes.push(node);
  }

  if (centerDelta != null) {
    const sumNodes = nodes.reduce((acc, n) => acc + n.value, 0);
    const residual = centerDelta - sumNodes;
    if (Math.abs(residual) > 0.005) {
      nodes.push({
        id: 'other_rounding',
        label: 'Other / Rounding',
        value: residual,
        direction: residual > 0 ? 'positive' : residual < 0 ? 'negative' : 'neutral',
      });
    }
  }

  return {
    metric: metricKey,
    metricLabel: config.metricLabel,
    periodA,
    periodB,
    centerValue: val(centerSeries, periodB),
    centerDelta,
    nodes,
  };
}

export function isExplainable(metricKey) {
  return Boolean(DECOMPOSITIONS[metricKey]);
}
