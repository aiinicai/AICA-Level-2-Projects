import { FinancialRatios, FinancialHealthScore, HealthScoreCategory, CreditGrade, RecommendationType, CreditAssessment, Company } from '../types/financial';

/**
 * Calculates Financial Health Score out of 100 based on the 4 weighted categories (25% each)
 * Liquidity: 25%
 * Profitability: 25%
 * Solvency: 25%
 * Efficiency: 25%
 */
export function calculateHealthScore(ratios: FinancialRatios): FinancialHealthScore {
  // 1. Liquidity Score (0 - 100)
  // Evaluates Current Ratio (50%) and Quick Ratio (50%)
  let crScore = 0;
  if (ratios.currentRatio >= 2.0) crScore = 100;
  else if (ratios.currentRatio >= 1.5) crScore = 85 + (ratios.currentRatio - 1.5) * 30;
  else if (ratios.currentRatio >= 1.33) crScore = 75 + (ratios.currentRatio - 1.33) * 58;
  else if (ratios.currentRatio >= 1.0) crScore = 50 + (ratios.currentRatio - 1.0) * 75;
  else crScore = Math.max(0, ratios.currentRatio * 50);

  let qrScore = 0;
  if (ratios.quickRatio >= 1.2) qrScore = 100;
  else if (ratios.quickRatio >= 1.0) qrScore = 85 + (ratios.quickRatio - 1.0) * 75;
  else if (ratios.quickRatio >= 0.8) qrScore = 60 + (ratios.quickRatio - 0.8) * 125;
  else qrScore = Math.max(0, ratios.quickRatio * 75);

  const liquidityRaw = Math.min(100, Math.max(0, crScore * 0.55 + qrScore * 0.45));

  // 2. Profitability Score (0 - 100)
  // Net Profit Margin (35%), Gross Margin (20%), ROE (25%), ROA (20%)
  let npmScore = 0;
  if (ratios.netProfitMargin >= 15) npmScore = 100;
  else if (ratios.netProfitMargin >= 8) npmScore = 75 + ((ratios.netProfitMargin - 8) / 7) * 25;
  else if (ratios.netProfitMargin >= 4) npmScore = 50 + ((ratios.netProfitMargin - 4) / 4) * 25;
  else if (ratios.netProfitMargin > 0) npmScore = Math.max(20, (ratios.netProfitMargin / 4) * 50);
  else npmScore = Math.max(0, 10 + ratios.netProfitMargin * 2);

  let roeScore = 0;
  if (ratios.roe >= 20) roeScore = 100;
  else if (ratios.roe >= 15) roeScore = 80 + ((ratios.roe - 15) / 5) * 20;
  else if (ratios.roe >= 8) roeScore = 50 + ((ratios.roe - 8) / 7) * 30;
  else roeScore = Math.max(0, (ratios.roe / 8) * 50);

  let gmScore = 0;
  if (ratios.grossMargin >= 35) gmScore = 100;
  else if (ratios.grossMargin >= 25) gmScore = 75 + ((ratios.grossMargin - 25) / 10) * 25;
  else if (ratios.grossMargin >= 15) gmScore = 50 + ((ratios.grossMargin - 15) / 10) * 25;
  else gmScore = Math.max(0, (ratios.grossMargin / 15) * 50);

  let roaScore = 0;
  if (ratios.roa >= 10) roaScore = 100;
  else if (ratios.roa >= 6) roaScore = 75 + ((ratios.roa - 6) / 4) * 25;
  else if (ratios.roa >= 3) roaScore = 50 + ((ratios.roa - 3) / 3) * 25;
  else roaScore = Math.max(0, (ratios.roa / 3) * 50);

  const profitabilityRaw = Math.min(100, Math.max(0, npmScore * 0.35 + roeScore * 0.25 + gmScore * 0.2 + roaScore * 0.2));

  // 3. Solvency Score (0 - 100)
  // Debt to Equity (50%), Interest Coverage (50%)
  let deScore = 0;
  if (ratios.debtEquityRatio <= 0.5) deScore = 100;
  else if (ratios.debtEquityRatio <= 1.0) deScore = 90 - (ratios.debtEquityRatio - 0.5) * 20;
  else if (ratios.debtEquityRatio <= 1.5) deScore = 80 - (ratios.debtEquityRatio - 1.0) * 30;
  else if (ratios.debtEquityRatio <= 2.5) deScore = 65 - (ratios.debtEquityRatio - 1.5) * 25;
  else if (ratios.debtEquityRatio <= 4.0) deScore = 40 - (ratios.debtEquityRatio - 2.5) * 20;
  else deScore = Math.max(0, 10 - (ratios.debtEquityRatio - 4.0) * 2);

  let icrScore = 0;
  if (ratios.interestCoverageRatio >= 6.0) icrScore = 100;
  else if (ratios.interestCoverageRatio >= 3.0) icrScore = 75 + ((ratios.interestCoverageRatio - 3.0) / 3.0) * 25;
  else if (ratios.interestCoverageRatio >= 1.5) icrScore = 50 + ((ratios.interestCoverageRatio - 1.5) / 1.5) * 25;
  else if (ratios.interestCoverageRatio >= 1.0) icrScore = 30 + ((ratios.interestCoverageRatio - 1.0) / 0.5) * 20;
  else icrScore = Math.max(0, ratios.interestCoverageRatio * 30);

  const solvencyRaw = Math.min(100, Math.max(0, deScore * 0.5 + icrScore * 0.5));

  // 4. Efficiency Score (0 - 100)
  // Asset Turnover (35%), DSO (35%), Inventory Turnover (30%)
  let atScore = 0;
  if (ratios.assetTurnover >= 1.5) atScore = 100;
  else if (ratios.assetTurnover >= 1.0) atScore = 75 + ((ratios.assetTurnover - 1.0) / 0.5) * 25;
  else if (ratios.assetTurnover >= 0.7) atScore = 50 + ((ratios.assetTurnover - 0.7) / 0.3) * 25;
  else atScore = Math.max(0, (ratios.assetTurnover / 0.7) * 50);

  let dsoScore = 0;
  if (ratios.daysSalesOutstanding <= 45) dsoScore = 100;
  else if (ratios.daysSalesOutstanding <= 60) dsoScore = 85 - ((ratios.daysSalesOutstanding - 45) / 15) * 15;
  else if (ratios.daysSalesOutstanding <= 90) dsoScore = 70 - ((ratios.daysSalesOutstanding - 60) / 30) * 25;
  else if (ratios.daysSalesOutstanding <= 120) dsoScore = 45 - ((ratios.daysSalesOutstanding - 90) / 30) * 25;
  else dsoScore = Math.max(0, 20 - ((ratios.daysSalesOutstanding - 120) / 60) * 20);

  let itScore = 0;
  if (ratios.inventoryTurnover >= 6.0) itScore = 100;
  else if (ratios.inventoryTurnover >= 4.0) itScore = 75 + ((ratios.inventoryTurnover - 4.0) / 2.0) * 25;
  else if (ratios.inventoryTurnover >= 2.5) itScore = 50 + ((ratios.inventoryTurnover - 2.5) / 1.5) * 25;
  else itScore = Math.max(0, (ratios.inventoryTurnover / 2.5) * 50);

  const efficiencyRaw = Math.min(100, Math.max(0, atScore * 0.35 + dsoScore * 0.35 + itScore * 0.3));

  // Weightings: 25% each
  const liquidityWeighted = liquidityRaw * 0.25;
  const profitabilityWeighted = profitabilityRaw * 0.25;
  const solvencyWeighted = solvencyRaw * 0.25;
  const efficiencyWeighted = efficiencyRaw * 0.25;

  const totalScore = Math.round(liquidityWeighted + profitabilityWeighted + solvencyWeighted + efficiencyWeighted);

  // Health Grades per Section 5:
  // 90-100: Excellent
  // 75-89: Good
  // 60-74: Average
  // 40-59: Weak
  // Below 40: High Risk
  const getGrade = (s: number): 'Excellent' | 'Good' | 'Average' | 'Weak' | 'High Risk' => {
    if (s >= 90) return 'Excellent';
    if (s >= 75) return 'Good';
    if (s >= 60) return 'Average';
    if (s >= 40) return 'Weak';
    return 'High Risk';
  };

  const categories: HealthScoreCategory[] = [
    {
      category: 'Liquidity',
      weight: 25,
      score: Math.round(liquidityRaw),
      weightedScore: Number(liquidityWeighted.toFixed(1)),
      grade: getGrade(liquidityRaw),
      keyDriver: `Current Ratio ${ratios.currentRatio.toFixed(2)}x, Quick Ratio ${ratios.quickRatio.toFixed(2)}x`
    },
    {
      category: 'Profitability',
      weight: 25,
      score: Math.round(profitabilityRaw),
      weightedScore: Number(profitabilityWeighted.toFixed(1)),
      grade: getGrade(profitabilityRaw),
      keyDriver: `Net Margin ${ratios.netProfitMargin.toFixed(1)}%, ROE ${ratios.roe.toFixed(1)}%`
    },
    {
      category: 'Solvency',
      weight: 25,
      score: Math.round(solvencyRaw),
      weightedScore: Number(solvencyWeighted.toFixed(1)),
      grade: getGrade(solvencyRaw),
      keyDriver: `Debt/Equity ${ratios.debtEquityRatio.toFixed(2)}x, Interest Coverage ${ratios.interestCoverageRatio >= 90 ? '>50x' : ratios.interestCoverageRatio.toFixed(1) + 'x'}`
    },
    {
      category: 'Efficiency',
      weight: 25,
      score: Math.round(efficiencyRaw),
      weightedScore: Number(efficiencyWeighted.toFixed(1)),
      grade: getGrade(efficiencyRaw),
      keyDriver: `Asset Turnover ${ratios.assetTurnover.toFixed(2)}x, DSO ${ratios.daysSalesOutstanding.toFixed(0)} days`
    }
  ];

  return {
    totalScore,
    rating: getGrade(totalScore),
    categories
  };
}

/**
 * Assesses credit recommendation according to Section 6 Decision Matrix
 */
export function assessCredit(
  company: Company,
  ratios: FinancialRatios,
  healthScore: FinancialHealthScore
): CreditAssessment {
  const { totalScore } = healthScore;
  const { debtEquityRatio, currentRatio } = ratios;

  // Credit Grades per Section 6:
  // AAA: Very Low Risk
  // AA: Low Risk
  // A: Moderate Risk
  // BBB: Moderate to High
  // BB: High Risk
  // B: Very High Risk
  let creditGrade: CreditGrade = 'B';
  let riskLevel: 'Very Low Risk' | 'Low Risk' | 'Moderate Risk' | 'Moderate to High' | 'High Risk' | 'Very High Risk' = 'Very High Risk';

  if (totalScore >= 88) {
    creditGrade = 'AAA';
    riskLevel = 'Very Low Risk';
  } else if (totalScore >= 78) {
    creditGrade = 'AA';
    riskLevel = 'Low Risk';
  } else if (totalScore >= 68) {
    creditGrade = 'A';
    riskLevel = 'Moderate Risk';
  } else if (totalScore >= 58) {
    creditGrade = 'BBB';
    riskLevel = 'Moderate to High';
  } else if (totalScore >= 45) {
    creditGrade = 'BB';
    riskLevel = 'High Risk';
  } else {
    creditGrade = 'B';
    riskLevel = 'Very High Risk';
  }

  // Decision Matrix per Section 6:
  // Approve: Health Score > 85 AND Debt Equity < 1.5 AND Current Ratio > 1.5
  // Conditional Approval: Health Score 65 - 84
  // Review Required: Health Score 50 - 64
  // Reject: Health Score < 50
  let recommendation: RecommendationType = 'Reject';
  const decisionRationale: string[] = [];

  if (totalScore > 85 && debtEquityRatio < 1.5 && currentRatio > 1.5) {
    recommendation = 'Approve';
    decisionRationale.push(`Financial Health Score (${totalScore}/100) exceeds threshold (>85)`);
    decisionRationale.push(`Debt-to-Equity (${debtEquityRatio.toFixed(2)}x) is well within limit (<1.5x)`);
    decisionRationale.push(`Current Ratio (${currentRatio.toFixed(2)}x) demonstrates ample working capital buffer (>1.5x)`);
  } else if (totalScore >= 65) {
    recommendation = 'Conditional Approval';
    decisionRationale.push(`Financial Health Score (${totalScore}/100) qualifies for conditional approval band (65 - 84)`);
    if (debtEquityRatio >= 1.5) {
      decisionRationale.push(`Debt-to-Equity is elevated at ${debtEquityRatio.toFixed(2)}x (Threshold: <1.5x) - requires deleveraging condition`);
    }
    if (currentRatio < 1.5) {
      decisionRationale.push(`Current Ratio is tight at ${currentRatio.toFixed(2)}x (Threshold: >1.5x) - requires working capital monitoring`);
    }
  } else if (totalScore >= 50) {
    recommendation = 'Review Required';
    decisionRationale.push(`Financial Health Score (${totalScore}/100) falls within discretionary review range (50 - 64)`);
    decisionRationale.push('Senior Credit Committee review mandated before commitment');
    if (ratios.interestCoverageRatio < 2.0) {
      decisionRationale.push(`Interest Coverage is narrow at ${ratios.interestCoverageRatio.toFixed(2)}x`);
    }
  } else {
    recommendation = 'Reject';
    decisionRationale.push(`Financial Health Score (${totalScore}/100) is below minimum credit eligibility threshold (<50)`);
    if (debtEquityRatio > 3.0) {
      decisionRationale.push(`Excessive debt burden: Debt-to-Equity of ${debtEquityRatio.toFixed(2)}x exceeds maximum tolerance (3.0x)`);
    }
    if (currentRatio < 1.0) {
      decisionRationale.push(`Critical liquidity strain: Current liabilities exceed current assets (CR: ${currentRatio.toFixed(2)}x)`);
    }
    if (ratios.netProfitMargin < 0) {
      decisionRationale.push('Borrower is operating with negative net profit margins');
    }
  }

  // Recommended Credit Exposure: 15% - 25% of annual turnover, scaled by health score
  const baseLimit = (company.annualTurnover * 0.20) * (totalScore / 100);
  const recommendedCreditLimit = Math.max(0.5, Number(baseLimit.toFixed(2)));

  // Pricing & Terms
  let recommendedInterestSpread = 'Repo + 2.50% (Standard)';
  let collateralRequirement = '100% Primary + 25% Collateral';

  if (recommendation === 'Approve') {
    recommendedInterestSpread = 'Repo + 1.25% to 1.75% (Prime Borrower Rate)';
    collateralRequirement = '100% Primary (Hypothecation of Assets) + 15% Collateral Margin';
  } else if (recommendation === 'Conditional Approval') {
    recommendedInterestSpread = 'Repo + 2.25% to 3.00% (Risk Adjusted)';
    collateralRequirement = '100% Primary + 35% Tangible Collateral / Personal Guarantee';
  } else if (recommendation === 'Review Required') {
    recommendedInterestSpread = 'Repo + 3.75% to 4.75% (Subordinated Risk Spread)';
    collateralRequirement = '100% Primary + 60% Liquid / Real Estate Collateral + Corporate Guarantee';
  } else {
    recommendedInterestSpread = 'N/A (Credit Application Declined)';
    collateralRequirement = 'N/A (Exceeds acceptable risk parameters)';
  }

  // Covenants
  const covenants: string[] = [];
  if (recommendation === 'Approve') {
    covenants.push('Maintain minimum Current Ratio of 1.33x during the loan facility tenure');
    covenants.push('Debt Service Coverage Ratio (DSCR) to be maintained above 1.50x');
    covenants.push('Submission of quarterly audited financial statements within 45 days');
  } else if (recommendation === 'Conditional Approval') {
    covenants.push('Maintain minimum Current Ratio of 1.25x and submit monthly drawing power statements');
    covenants.push('Prior approval required for capital expenditure exceeding INR 5.0 Crores');
    covenants.push('No dividend distribution without lender prior written consent');
    covenants.push('Promoter personal guarantees and pledge of 25% equity shares');
  } else if (recommendation === 'Review Required') {
    covenants.push('Restructuring of existing debt portfolio and reduction in leverage below 2.0x');
    covenants.push('Escrow account arrangement for direct collections of major receivables');
    covenants.push('Quarterly stock and receivables inspection by bank empaneled auditor');
  } else {
    covenants.push('Application declined: Borrower does not satisfy minimum prudential credit norms');
  }

  // Strengths & Weaknesses
  const strengths: string[] = [];
  const weaknesses: string[] = [];

  if (ratios.currentRatio >= 1.5) strengths.push(`Strong liquidity buffer with Current Ratio of ${ratios.currentRatio.toFixed(2)}x`);
  else if (ratios.currentRatio < 1.0) weaknesses.push(`Severely compressed liquidity: Current Ratio at ${ratios.currentRatio.toFixed(2)}x`);

  if (ratios.netProfitMargin >= 8) strengths.push(`Healthy net profitability margin of ${ratios.netProfitMargin.toFixed(1)}%`);
  else if (ratios.netProfitMargin <= 0) weaknesses.push(`Negative bottom line with Net Margin of ${ratios.netProfitMargin.toFixed(1)}%`);

  if (ratios.debtEquityRatio <= 1.0) strengths.push(`Conservative leverage with low Debt-to-Equity of ${ratios.debtEquityRatio.toFixed(2)}x`);
  else if (ratios.debtEquityRatio > 2.5) weaknesses.push(`High financial leverage: Debt-to-Equity stands at ${ratios.debtEquityRatio.toFixed(2)}x`);

  if (ratios.interestCoverageRatio >= 4.0) strengths.push(`Substantial debt servicing headroom with ICR of ${ratios.interestCoverageRatio >= 90 ? '>50x' : ratios.interestCoverageRatio.toFixed(1) + 'x'}`);
  else if (ratios.interestCoverageRatio < 1.5) weaknesses.push(`Debt service vulnerability: Interest coverage is dangerously low at ${ratios.interestCoverageRatio.toFixed(2)}x`);

  if (ratios.daysSalesOutstanding <= 60) strengths.push(`Prompt receivables cycle with DSO of ${ratios.daysSalesOutstanding.toFixed(0)} days`);
  else if (ratios.daysSalesOutstanding > 90) weaknesses.push(`Extended debtor collection period with DSO of ${ratios.daysSalesOutstanding.toFixed(0)} days`);

  if (ratios.roe >= 15) strengths.push(`Superior equity efficiency with ROE of ${ratios.roe.toFixed(1)}%`);

  const analystSummary = recommendation === 'Approve'
    ? `${company.companyName} presents a prime credit profile rated ${creditGrade} with a high Financial Health Score of ${totalScore}/100. Robust liquidity, solid operational margins, and modest leverage justify credit sanction up to INR ${recommendedCreditLimit} Cr.`
    : recommendation === 'Conditional Approval'
    ? `${company.companyName} is fundamentally viable with a credit grade of ${creditGrade} (Score: ${totalScore}/100), but requires targeted structuring and tight monitoring conditions regarding working capital and debt caps.`
    : recommendation === 'Review Required'
    ? `${company.companyName} displays moderate-to-high risk (Grade: ${creditGrade}, Score: ${totalScore}/100). Heightened scrutiny by the Credit Committee and additional collateral security are mandatory.`
    : `${company.companyName} exhibits critical credit risk (Grade: ${creditGrade}, Score: ${totalScore}/100). Deteriorated liquidity and unsustainable debt metrics fail institutional underwriting criteria. Recommendation is to Reject.`;

  return {
    id: `ASSESS-${company.id}-${ratios.financialYear}`,
    companyId: company.id,
    financialYear: ratios.financialYear,
    assessmentDate: new Date().toISOString().split('T')[0],
    healthScore,
    creditGrade,
    riskLevel,
    recommendation,
    decisionRationale,
    recommendedCreditLimit,
    recommendedInterestSpread,
    collateralRequirement,
    covenants,
    strengths,
    weaknesses,
    analystSummary
  };
}
