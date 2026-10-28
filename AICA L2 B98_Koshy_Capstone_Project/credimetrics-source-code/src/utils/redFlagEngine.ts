import { FinancialStatement, FinancialRatios, RedFlag } from '../types/financial';

/**
 * Detects red flags based on financial statements and computed ratios
 * Implements Section 8: Red Flag Detection Engine
 */
export function detectRedFlags(
  currentStatement: FinancialStatement,
  currentRatios: FinancialRatios,
  historicalStatements: FinancialStatement[] = []
): RedFlag[] {
  const flags: RedFlag[] = [];
  const { currentRatio, quickRatio, debtEquityRatio, interestCoverageRatio, netProfitMargin, daysSalesOutstanding } = currentRatios;
  const { balanceSheet: bs, profitAndLoss: pl } = currentStatement;

  // Sort historical statements chronologically
  const allStatements = [...historicalStatements, currentStatement].sort((a, b) => 
    a.financialYear.localeCompare(b.financialYear)
  );

  // 1. Liquidity Risk
  // Rule: Current Ratio < 1 => Current Liabilities Exceed Current Assets
  if (currentRatio < 1.0) {
    flags.push({
      id: 'rf-cr-1',
      category: 'Liquidity Risk',
      severity: 'Critical',
      title: 'Current Liabilities Exceed Current Assets',
      description: `Current assets (INR ${(bs.cash + bs.bank + bs.receivables + bs.inventory).toFixed(2)} Cr) are insufficient to cover short-term obligations (INR ${(bs.payables + bs.shortTermDebt).toFixed(2)} Cr). Significant working capital deficit.`,
      metric: 'Current Ratio',
      actualValue: `${currentRatio.toFixed(2)}x`,
      threshold: '< 1.00x',
      recommendation: 'Immediate equity infusion or restructuring of short-term loans into long-term funding required.'
    });
  } else if (currentRatio < 1.33) {
    flags.push({
      id: 'rf-cr-tight',
      category: 'Liquidity Risk',
      severity: 'Warning',
      title: 'Tight Working Capital Buffer',
      description: 'Current Ratio is below prudential banking benchmark of 1.33x, leaving slender buffer for unexpected cash flow delays.',
      metric: 'Current Ratio',
      actualValue: `${currentRatio.toFixed(2)}x`,
      threshold: '< 1.33x',
      recommendation: 'Monitor debtor realization and rationalize inventory holding periods.'
    });
  }

  // Rule: Quick Ratio < 0.8
  if (quickRatio < 0.8) {
    flags.push({
      id: 'rf-qr-08',
      category: 'Liquidity Risk',
      severity: currentRatio < 1.0 ? 'Critical' : 'Warning',
      title: 'Severe Quick Liquidity Deficit',
      description: 'Quick ratio is under 0.8x, indicating heavy reliance on slow-moving inventory to meet immediate debt obligations.',
      metric: 'Quick Ratio',
      actualValue: `${quickRatio.toFixed(2)}x`,
      threshold: '< 0.80x',
      recommendation: 'Establish committed emergency liquidity backup lines or expedite bill discounting.'
    });
  }

  // 2. Solvency Risk
  // Rule: Debt Equity Ratio > 3 => Excessive Debt Burden
  if (debtEquityRatio > 3.0) {
    flags.push({
      id: 'rf-de-3',
      category: 'Solvency Risk',
      severity: 'Critical',
      title: 'Excessive Debt Burden',
      description: `Total borrowings are more than 3 times total equity. The firm is excessively leveraged and highly susceptible to external interest rate shocks.`,
      metric: 'Debt to Equity',
      actualValue: `${debtEquityRatio.toFixed(2)}x`,
      threshold: '> 3.00x',
      recommendation: 'Cap any new debt sanctions; require promoter equity dilution or subordinated debt injection.'
    });
  } else if (debtEquityRatio > 2.0) {
    flags.push({
      id: 'rf-de-2',
      category: 'Solvency Risk',
      severity: 'Warning',
      title: 'Elevated Financial Leverage',
      description: 'Debt-to-equity ratio exceeds institutional target of 1.5x - 2.0x.',
      metric: 'Debt to Equity',
      actualValue: `${debtEquityRatio.toFixed(2)}x`,
      threshold: '> 2.00x',
      recommendation: 'Prioritize debt paydown through operational cash flows before initiating capital expenditures.'
    });
  }

  // Rule: Interest Coverage < 1.5 => High Loan Default Risk
  if (interestCoverageRatio < 1.5) {
    flags.push({
      id: 'rf-icr-15',
      category: 'Solvency Risk',
      severity: 'Critical',
      title: 'High Loan Default Risk',
      description: `Operating earnings (EBIT) cover interest expenses by only ${interestCoverageRatio.toFixed(2)}x. Any modest drop in operating profit could result in loan servicing default.`,
      metric: 'Interest Coverage Ratio',
      actualValue: interestCoverageRatio <= 0 ? 'Negative' : `${interestCoverageRatio.toFixed(2)}x`,
      threshold: '< 1.50x',
      recommendation: 'Structure an escrow account with priority charge on operating revenues; consider interest moratorium or reduction.'
    });
  }

  // 3. Profitability Risk
  // Rule: Negative Net Profit
  if (pl.netProfit < 0) {
    flags.push({
      id: 'rf-np-neg',
      category: 'Profitability Risk',
      severity: 'Critical',
      title: 'Negative Net Profit (Operating Loss)',
      description: `Company incurred a net loss of INR ${Math.abs(pl.netProfit).toFixed(2)} Cr in ${currentStatement.financialYear}. Continued losses will erode net worth.`,
      metric: 'Net Profit Margin',
      actualValue: `${netProfitMargin.toFixed(1)}%`,
      threshold: '< 0.0%',
      recommendation: 'Conduct forensic cost analysis and review gross margin viability across business lines.'
    });
  }

  // Multi-Year Trends Check (Continuous profit decline / 3-year revenue decline)
  if (allStatements.length >= 2) {
    const lastIdx = allStatements.length - 1;
    const prevStmt = allStatements[lastIdx - 1];

    // Continuous Profit Decline
    if (allStatements.length >= 3) {
      const prev2Stmt = allStatements[lastIdx - 2];
      const p1 = prev2Stmt.profitAndLoss.netProfit;
      const p2 = prevStmt.profitAndLoss.netProfit;
      const p3 = currentStatement.profitAndLoss.netProfit;

      if (p3 < p2 && p2 < p1) {
        flags.push({
          id: 'rf-profit-decline-3',
          category: 'Profitability Risk',
          severity: 'Critical',
          title: 'Net Profit Declining for Consecutive Years',
          description: `Net profit has contracted over successive years (${p1.toFixed(1)} Cr ➔ ${p2.toFixed(1)} Cr ➔ ${p3.toFixed(1)} Cr). Clear sign of operational deterioration.`,
          metric: 'Profit Trend',
          actualValue: `${(((p3 - p1) / (Math.abs(p1) || 1)) * 100).toFixed(1)}% total drop`,
          threshold: 'Continuous Decline',
          recommendation: 'Evaluate market demand, competitive erosion, or unhedged cost escalations.'
        });
      }

      // 3-Year Revenue Decline
      const r1 = prev2Stmt.profitAndLoss.revenue;
      const r2 = prevStmt.profitAndLoss.revenue;
      const r3 = currentStatement.profitAndLoss.revenue;

      if (r3 < r2 && r2 < r1) {
        flags.push({
          id: 'rf-rev-decline-3',
          category: 'Growth Risk',
          severity: 'Critical',
          title: '3-Year Revenue Decline',
          description: `Topline revenue has shrunk over consecutive years (${r1.toFixed(1)} Cr ➔ ${r2.toFixed(1)} Cr ➔ ${r3.toFixed(1)} Cr).`,
          metric: 'Topline Trend',
          actualValue: `${(((r3 - r1) / (r1 || 1)) * 100).toFixed(1)}% decline`,
          threshold: 'Continuous Contraction',
          recommendation: 'Assess product obsolescence, customer churn, or loss of key distribution accounts.'
        });
      }
    }
  }

  // 4. Efficiency & Working Capital Risk
  if (daysSalesOutstanding > 120) {
    flags.push({
      id: 'rf-dso-120',
      category: 'Working Capital Risk',
      severity: 'Warning',
      title: 'Prolonged Debtor Collection Period',
      description: `Days Sales Outstanding is ${daysSalesOutstanding.toFixed(0)} days. Extended credit terms or uncollected overdue balances tie up valuable liquidity.`,
      metric: 'DSO',
      actualValue: `${daysSalesOutstanding.toFixed(0)} days`,
      threshold: '> 120 days',
      recommendation: 'Institute tighter credit terms, automated collection dunning, and invoice factoring.'
    });
  }

  return flags;
}
