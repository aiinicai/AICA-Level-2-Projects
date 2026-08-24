/**
 * Thin access layer over a parsed `financials` object. Components should never read
 * `financials.balance_sheet.foo.FY25` directly — always go through these functions,
 * so a typo or a missing field returns `null` instead of throwing.
 */

export function getPeriods(financials, kind = 'annual') {
  return financials?.periods?.[kind] || [];
}

export function getSeries(financials, statement, lineItem) {
  if (!financials || !financials[statement]) return null;
  const series = financials[statement][lineItem];
  return series || null;
}

export function getSeriesForChart(financials, statement, lineItem, kind = 'annual') {
  const series = getSeries(financials, statement, lineItem);
  const periods = getPeriods(financials, kind);
  return periods.map((period) => ({
    period,
    value: series && series[period] != null ? series[period] : null,
  }));
}

/** Same as getSeriesForChart but against an explicit periods array — used to overlay a peer's
 * series (whose own period range may differ) onto the primary company's x-axis. */
export function getSeriesForChartAgainstPeriods(source, statement, lineItem, periods) {
  const series = getSeries(source, statement, lineItem);
  return periods.map((period) => ({
    period,
    value: series && series[period] != null ? series[period] : null,
  }));
}

export function getLatestValue(financials, statement, lineItem, kind = 'annual') {
  const series = getSeries(financials, statement, lineItem);
  const periods = getPeriods(financials, kind);
  if (!series || periods.length === 0) return null;
  const latest = periods[periods.length - 1];
  return series[latest] != null ? series[latest] : null;
}

export function getPriorValue(financials, statement, lineItem, kind = 'annual') {
  const series = getSeries(financials, statement, lineItem);
  const periods = getPeriods(financials, kind);
  if (!series || periods.length < 2) return null;
  const prior = periods[periods.length - 2];
  return series[prior] != null ? series[prior] : null;
}

export function getYoyDelta(latest, prior) {
  if (latest == null || prior == null) return null;
  const absolute = latest - prior;
  const pct = prior !== 0 ? (absolute / Math.abs(prior)) * 100 : null;
  const direction = absolute > 0 ? 'up' : absolute < 0 ? 'down' : 'flat';
  return { absolute, pct, direction };
}

export function hasData(series) {
  if (!series) return false;
  return Object.values(series).some((v) => v != null);
}

export function hasChartData(financials, statement, lineItem, kind = 'annual') {
  return hasData(getSeries(financials, statement, lineItem)) && getPeriods(financials, kind).length > 0;
}

// --- Computed metrics that combine multiple line items (never hardcode the arithmetic in a component) ---

export function getWorkingCapitalSeries(financials) {
  const periods = getPeriods(financials, 'annual');
  const ca = getSeries(financials, 'balance_sheet', 'total_current_assets') || {};
  const cl = getSeries(financials, 'balance_sheet', 'total_current_liabilities') || {};
  const out = {};
  for (const p of periods) {
    out[p] = ca[p] != null && cl[p] != null ? ca[p] - cl[p] : null;
  }
  return out;
}

export function getTotalDebtSeries(financials) {
  const periods = getPeriods(financials, 'annual');
  const ltb = getSeries(financials, 'balance_sheet', 'long_term_borrowings') || {};
  const stb = getSeries(financials, 'balance_sheet', 'short_term_borrowings') || {};
  const out = {};
  for (const p of periods) {
    const l = ltb[p];
    const s = stb[p];
    out[p] = l != null || s != null ? (l || 0) + (s || 0) : null;
  }
  return out;
}

// derived_metrics is keyed by period first ({ FY25: { ebitda, ... } }), the inverse
// shape of every other statement — this adapts it to the same { period: value } series shape.
export function getDerivedSeries(financials, metricKey) {
  const periods = getPeriods(financials, 'annual');
  const out = {};
  for (const p of periods) {
    out[p] = financials?.derived_metrics?.[p]?.[metricKey] ?? null;
  }
  return out;
}

export function latestAndPriorFromComputedSeries(financials, series) {
  const periods = getPeriods(financials, 'annual');
  if (periods.length === 0) return { latest: null, prior: null };
  const latest = series[periods[periods.length - 1]] ?? null;
  const prior = periods.length > 1 ? series[periods[periods.length - 2]] ?? null : null;
  return { latest, prior };
}
