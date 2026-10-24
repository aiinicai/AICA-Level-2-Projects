import { FinancialStatement, FinancialRatios, RatioItem } from '../types/financial';

/**
 * Calculates all financial ratios from a balance sheet and P&L statement
 */
export function calculateRatios(statement: FinancialStatement, previousStatement?: FinancialStatement): FinancialRatios {
  const { balanceSheet: bs, profitAndLoss: pl } = statement;

  // Derived balance sheet items
  const currentAssets = bs.cash + bs.bank + bs.receivables + bs.inventory + (bs.otherCurrentAssets || 0);
  const currentLiabilities = bs.payables + bs.shortTermDebt + (bs.otherCurrentLiabilities || 0);
  const totalDebt = bs.shortTermDebt + bs.longTermDebt;
  const totalEquity = bs.equity + bs.reserves;
  const totalAssets = bs.totalAssets || (currentAssets + bs.fixedAssets + bs.investments + (bs.otherNonCurrentAssets || 0));

  // 1. Liquidity Ratios
  // Current Ratio = Current Assets / Current Liabilities
  const currentRatio = currentLiabilities > 0 ? currentAssets / currentLiabilities : 0;
  
  // Quick Ratio = (Current Assets - Inventory) / Current Liabilities
  const quickRatio = currentLiabilities > 0 ? (currentAssets - bs.inventory) / currentLiabilities : 0;
  
  // Cash Ratio = (Cash + Bank) / Current Liabilities
  const cashRatio = currentLiabilities > 0 ? (bs.cash + bs.bank) / currentLiabilities : 0;

  // 2. Profitability Ratios
  const revenue = pl.revenue || 0.0001;
  const grossMargin = (pl.grossProfit / revenue) * 100;
  const netProfitMargin = (pl.netProfit / revenue) * 100;
  const ebitdaMargin = (pl.ebitda / revenue) * 100;
  
  // Return on Assets (ROA) = Net Profit / Total Assets
  const roa = totalAssets > 0 ? (pl.netProfit / totalAssets) * 100 : 0;
  
  // Return on Equity (ROE) = Net Profit / Total Shareholder Equity
  const roe = totalEquity > 0 ? (pl.netProfit / totalEquity) * 100 : 0;

  // 3. Solvency Ratios
  // Debt Equity Ratio = Total Debt / Total Equity
  const debtEquityRatio = totalEquity > 0 ? totalDebt / totalEquity : (totalDebt > 0 ? 99 : 0);
  
  // Interest Coverage Ratio = EBIT / Interest Expense
  const interestCoverageRatio = pl.interestExpense > 0 ? pl.ebit / pl.interestExpense : (pl.ebit > 0 ? 99 : 0);
  
  // Debt to Assets = Total Debt / Total Assets
  const debtToAssets = totalAssets > 0 ? totalDebt / totalAssets : 0;

  // 4. Efficiency Ratios
  // Inventory Turnover = COGS / Inventory (or Average Inventory if previous year exists)
  const avgInventory = previousStatement ? (bs.inventory + previousStatement.balanceSheet.inventory) / 2 : bs.inventory;
  const inventoryTurnover = avgInventory > 0 ? pl.cogs / avgInventory : 0;
  const daysInventoryOutstanding = inventoryTurnover > 0 ? 365 / inventoryTurnover : 0;

  // Asset Turnover = Revenue / Total Assets
  const assetTurnover = totalAssets > 0 ? revenue / totalAssets : 0;

  // Receivables Turnover = Revenue / Receivables
  const avgReceivables = previousStatement ? (bs.receivables + previousStatement.balanceSheet.receivables) / 2 : bs.receivables;
  const receivablesTurnover = avgReceivables > 0 ? revenue / avgReceivables : 0;
  const daysSalesOutstanding = receivablesTurnover > 0 ? 365 / receivablesTurnover : 0;

  // Working Capital Turnover = Revenue / Net Working Capital
  const netWorkingCapital = currentAssets - currentLiabilities;
  const workingCapitalTurnover = netWorkingCapital > 0 ? revenue / netWorkingCapital : 0;

  // Build items list with benchmarks & status
  const items: RatioItem[] = [
    // Liquidity
    {
      id: 'cr',
      name: 'Current Ratio',
      category: 'Liquidity',
      value: currentRatio,
      formattedValue: `${currentRatio.toFixed(2)}x`,
      benchmark: '1.33x - 2.00x',
      benchmarkMin: 1.33,
      status: currentRatio >= 1.33 ? 'Healthy' : currentRatio >= 1.0 ? 'Moderate' : 'Risk',
      formula: 'Current Assets / Current Liabilities',
      interpretation: currentRatio >= 1.5 ? 'Strong short-term solvency' : currentRatio >= 1.0 ? 'Acceptable buffer' : 'Liquidity strain'
    },
    {
      id: 'qr',
      name: 'Quick Ratio',
      category: 'Liquidity',
      value: quickRatio,
      formattedValue: `${quickRatio.toFixed(2)}x`,
      benchmark: '≥ 1.00x',
      benchmarkMin: 1.0,
      status: quickRatio >= 1.0 ? 'Healthy' : quickRatio >= 0.8 ? 'Moderate' : 'Risk',
      formula: '(Current Assets - Inventory) / Current Liabilities',
      interpretation: quickRatio >= 1.0 ? 'Excellent liquid reserve' : quickRatio >= 0.8 ? 'Adequate liquidity' : 'Dependent on inventory liquidation'
    },
    {
      id: 'cash_r',
      name: 'Cash Ratio',
      category: 'Liquidity',
      value: cashRatio,
      formattedValue: `${cashRatio.toFixed(2)}x`,
      benchmark: '≥ 0.20x',
      benchmarkMin: 0.2,
      status: cashRatio >= 0.2 ? 'Healthy' : cashRatio >= 0.1 ? 'Moderate' : 'Risk',
      formula: '(Cash + Bank) / Current Liabilities',
      interpretation: cashRatio >= 0.2 ? 'Substantial instant liquidity' : 'Reliance on collections'
    },

    // Profitability
    {
      id: 'gm',
      name: 'Gross Margin',
      category: 'Profitability',
      value: grossMargin,
      formattedValue: `${grossMargin.toFixed(2)}%`,
      benchmark: '≥ 25.0%',
      benchmarkMin: 25.0,
      status: grossMargin >= 25.0 ? 'Healthy' : grossMargin >= 15.0 ? 'Moderate' : 'Risk',
      formula: 'Gross Profit / Revenue × 100',
      interpretation: grossMargin >= 25 ? 'Robust pricing power' : 'Cost pressures visible'
    },
    {
      id: 'npm',
      name: 'Net Profit Margin',
      category: 'Profitability',
      value: netProfitMargin,
      formattedValue: `${netProfitMargin.toFixed(2)}%`,
      benchmark: '≥ 8.0%',
      benchmarkMin: 8.0,
      status: netProfitMargin >= 8.0 ? 'Healthy' : netProfitMargin >= 4.0 ? 'Moderate' : 'Risk',
      formula: 'Net Profit / Revenue × 100',
      interpretation: netProfitMargin >= 8 ? 'Strong bottom line generation' : netProfitMargin > 0 ? 'Modest profitability' : 'Operating at a loss'
    },
    {
      id: 'roa',
      name: 'Return on Assets (ROA)',
      category: 'Profitability',
      value: roa,
      formattedValue: `${roa.toFixed(2)}%`,
      benchmark: '≥ 6.0%',
      benchmarkMin: 6.0,
      status: roa >= 6.0 ? 'Healthy' : roa >= 3.0 ? 'Moderate' : 'Risk',
      formula: 'Net Profit / Total Assets × 100',
      interpretation: roa >= 6 ? 'Productive asset utilization' : 'Sub-optimal asset returns'
    },
    {
      id: 'roe',
      name: 'Return on Equity (ROE)',
      category: 'Profitability',
      value: roe,
      formattedValue: `${roe.toFixed(2)}%`,
      benchmark: '≥ 15.0%',
      benchmarkMin: 15.0,
      status: roe >= 15.0 ? 'Healthy' : roe >= 8.0 ? 'Moderate' : 'Risk',
      formula: 'Net Profit / Shareholder Equity × 100',
      interpretation: roe >= 15 ? 'Superior return for capital providers' : 'Depressed equity return'
    },

    // Solvency
    {
      id: 'de',
      name: 'Debt to Equity Ratio',
      category: 'Solvency',
      value: debtEquityRatio,
      formattedValue: `${debtEquityRatio.toFixed(2)}x`,
      benchmark: '≤ 1.50x',
      benchmarkMax: 1.5,
      status: debtEquityRatio <= 1.5 ? 'Healthy' : debtEquityRatio <= 2.5 ? 'Moderate' : 'Risk',
      formula: 'Total Debt / Total Equity',
      interpretation: debtEquityRatio <= 1.5 ? 'Prudent capital structure' : debtEquityRatio <= 2.5 ? 'Moderate leverage' : 'Over-leveraged capital base'
    },
    {
      id: 'icr',
      name: 'Interest Coverage Ratio',
      category: 'Solvency',
      value: interestCoverageRatio,
      formattedValue: interestCoverageRatio >= 90 ? '> 50x' : `${interestCoverageRatio.toFixed(2)}x`,
      benchmark: '≥ 3.00x',
      benchmarkMin: 3.0,
      status: interestCoverageRatio >= 3.0 ? 'Healthy' : interestCoverageRatio >= 1.5 ? 'Moderate' : 'Risk',
      formula: 'EBIT / Interest Expense',
      interpretation: interestCoverageRatio >= 3.0 ? 'Comfortable debt servicing headroom' : interestCoverageRatio >= 1.5 ? 'Tight debt servicing' : 'Imminent default risk on interest'
    },
    {
      id: 'da',
      name: 'Debt to Total Assets',
      category: 'Solvency',
      value: debtToAssets,
      formattedValue: `${(debtToAssets * 100).toFixed(1)}%`,
      benchmark: '≤ 50.0%',
      benchmarkMax: 0.5,
      status: debtToAssets <= 0.5 ? 'Healthy' : debtToAssets <= 0.7 ? 'Moderate' : 'Risk',
      formula: 'Total Debt / Total Assets',
      interpretation: debtToAssets <= 0.5 ? 'Low leverage risk' : 'High creditor reliance'
    },

    // Efficiency
    {
      id: 'inv_turn',
      name: 'Inventory Turnover',
      category: 'Efficiency',
      value: inventoryTurnover,
      formattedValue: `${inventoryTurnover.toFixed(1)}x`,
      benchmark: '≥ 4.0x',
      benchmarkMin: 4.0,
      status: inventoryTurnover >= 4.0 ? 'Healthy' : inventoryTurnover >= 2.5 ? 'Moderate' : 'Risk',
      formula: 'COGS / Inventory',
      interpretation: `${daysInventoryOutstanding.toFixed(0)} days inventory holding period`
    },
    {
      id: 'asset_turn',
      name: 'Asset Turnover',
      category: 'Efficiency',
      value: assetTurnover,
      formattedValue: `${assetTurnover.toFixed(2)}x`,
      benchmark: '≥ 1.00x',
      benchmarkMin: 1.0,
      status: assetTurnover >= 1.0 ? 'Healthy' : assetTurnover >= 0.7 ? 'Moderate' : 'Risk',
      formula: 'Revenue / Total Assets',
      interpretation: assetTurnover >= 1.0 ? 'Efficient asset monetization' : 'Sluggish asset throughput'
    },
    {
      id: 'dso',
      name: 'Days Sales Outstanding (DSO)',
      category: 'Efficiency',
      value: daysSalesOutstanding,
      formattedValue: `${daysSalesOutstanding.toFixed(0)} days`,
      benchmark: '≤ 60 days',
      benchmarkMax: 60,
      status: daysSalesOutstanding <= 60 ? 'Healthy' : daysSalesOutstanding <= 90 ? 'Moderate' : 'Risk',
      formula: '365 / (Revenue / Receivables)',
      interpretation: daysSalesOutstanding <= 60 ? 'Prompt debtor collections' : daysSalesOutstanding <= 90 ? 'Average payment cycle' : 'Slow collections / locked cash'
    }
  ];

  return {
    financialYear: statement.financialYear,
    currentRatio,
    quickRatio,
    cashRatio,
    grossMargin,
    netProfitMargin,
    ebitdaMargin,
    roa,
    roe,
    debtEquityRatio,
    interestCoverageRatio,
    debtToAssets,
    inventoryTurnover,
    daysInventoryOutstanding,
    assetTurnover,
    receivablesTurnover,
    daysSalesOutstanding,
    workingCapitalTurnover,
    items
  };
}
