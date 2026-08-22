export const ROUTES = [
  { path: '/', label: 'Home' },
  { path: '/revenue', label: 'Revenue' },
  { path: '/revenue/mix', label: 'Revenue Mix' },
  { path: '/revenue/quarterly', label: 'Quarterly Trend' },
  { path: '/cost', label: 'Cost Structure' },
  { path: '/cost/breakup', label: 'Expense Breakup' },
  { path: '/cost/common-size', label: 'Common-Size Costs' },
  { path: '/profitability', label: 'Profitability' },
  { path: '/profitability/margins', label: 'Margin Trend' },
  { path: '/profitability/variance', label: 'YoY Variance' },
  { path: '/balance-sheet', label: 'Balance Sheet Health' },
  { path: '/balance-sheet/assets', label: 'Assets Composition' },
  { path: '/balance-sheet/liabilities', label: 'Liabilities & Net Worth' },
  { path: '/liquidity', label: 'Liquidity & Working Capital' },
  { path: '/liquidity/ratios', label: 'Liquidity Ratios' },
  { path: '/liquidity/cycle', label: 'Cash Conversion Cycle' },
  { path: '/cash-flow', label: 'Cash Flow' },
  { path: '/returns', label: 'Returns & Efficiency' },
  { path: '/returns/dupont', label: 'DuPont ROE' },
  { path: '/debt', label: 'Debt & Solvency' },
  { path: '/debt/coverage', label: 'Debt Coverage' },
];

export function routeLabel(path) {
  const r = ROUTES.find((r) => r.path === path);
  return r ? r.label : path;
}

export function breadcrumbTrail(pathname) {
  const segments = pathname.split('/').filter(Boolean);
  const trail = [{ path: '/', label: 'Home' }];
  let acc = '';
  for (const seg of segments) {
    acc += `/${seg}`;
    trail.push({ path: acc, label: routeLabel(acc) });
  }
  return trail;
}
