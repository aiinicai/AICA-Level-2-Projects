import { CompanyEntity, DeterministicMetrics, PeriodId, CurrencyUnit } from '../types/finance';

export const calculateDeterministicMetrics = (
  company: CompanyEntity,
  periodId: PeriodId = 'Q4 FY25'
): DeterministicMetrics => {
  const periodData = company.periods[periodId] || company.periods['Q4 FY25'];
  const { pl, balanceSheet, valuation } = periodData;

  const revenue = pl.revenueFromOperations;
  const otherIncome = pl.otherIncome;
  const totalIncome = pl.totalRevenue || (revenue + otherIncome);

  const rawMaterialCost = (pl.costOfMaterialsConsumed || 0) + (pl.purchaseOfStockInTrade || 0) + (pl.changesInInventories || 0);
  const employeeCost = pl.employeeBenefitExpenses || 0;
  const otherOperatingExpenses = pl.otherExpenses || 0;
  const totalOperatingCosts = rawMaterialCost + employeeCost + otherOperatingExpenses;

  // Operating EBITDA excludes Other Income
  const ebitda = revenue - totalOperatingCosts;
  const ebitdaWithOtherIncome = ebitda + otherIncome;
  const depreciation = pl.depreciationAndAmortization || 0;
  const ebit = ebitdaWithOtherIncome - depreciation;
  const financeCosts = pl.financeCosts || 0;
  const ebt = pl.profitBeforeTax || (ebit - financeCosts);
  const tax = pl.taxExpense || 0;
  const pat = pl.profitAfterTax || (ebt - tax);

  // Ratios
  const opmPercent = revenue > 0 ? (ebitda / revenue) * 100 : 0;
  const npmPercent = totalIncome > 0 ? (pat / totalIncome) * 100 : 0;
  const effectiveTaxRate = ebt > 0 ? (tax / ebt) * 100 : 0;

  // Balance Sheet Metrics
  const netWorth = balanceSheet.equityShareCapital + balanceSheet.reservesAndSurplus;
  const totalDebt = balanceSheet.longTermBorrowings + balanceSheet.shortTermBorrowings;
  const capitalEmployed = netWorth + totalDebt;
  const debtToEquity = netWorth > 0 ? totalDebt / netWorth : totalDebt > 0 ? 99.9 : 0;
  
  // Interest Coverage (EBIT / Interest). If financeCosts <= 0.5, company has near zero interest burden => safe (99.9x)
  const interestCoverage = financeCosts > 0.5 ? Math.max(0, ebit / financeCosts) : 99.9;

  // Returns & Spreads
  const annualizedPATRunRate = pat * 4;
  const rocePercent = capitalEmployed > 0 ? ((ebit * 4) / capitalEmployed) * 100 : 0;
  const economicSpread = rocePercent - (company.benchmarkCostOfCapital || 10.0);
  const roePercent = netWorth > 0 ? (annualizedPATRunRate / netWorth) * 100 : 0;

  // Prior period / YoY growth
  const prevRev = pl.prevYearRevenue || (revenue * 0.9);
  const prevPAT = pl.prevYearPAT || (pat * 0.88);
  const prevEBITDA = pl.prevYearEBITDA || (ebitda * 0.91);

  const salesYoYGrowth = prevRev > 0 ? ((revenue - prevRev) / prevRev) * 100 : 0;
  const patYoYGrowth = prevPAT !== 0 ? ((pat - prevPAT) / Math.abs(prevPAT)) * 100 : 0;
  const ebitdaYoYGrowth = prevEBITDA !== 0 ? ((ebitda - prevEBITDA) / Math.abs(prevEBITDA)) * 100 : 0;

  const operatingScissorsGap = salesYoYGrowth - patYoYGrowth;
  // Negative scissors: Sales growing positively while PAT contracting, or massive divergence > 15%
  const hasNegativeScissors = (salesYoYGrowth > 0 && patYoYGrowth < 0) || (salesYoYGrowth > 10 && operatingScissorsGap > 15);

  // Earnings Quality
  const coreOperatingProfitShare = (ebitda > 0) ? (ebitda / (ebitda + Math.max(0, otherIncome))) * 100 : 0;
  const otherIncomeToPATShare = (pat > 0 && otherIncome > 0) ? (otherIncome / pat) * 100 : 0;

  // Valuation
  const marketCap = valuation.marketCap;
  const enterpriseValue = marketCap + totalDebt - (balanceSheet.cashAndEquivalents || 0);
  const peRatio = valuation.peRatio || (annualizedPATRunRate > 0 ? marketCap / annualizedPATRunRate : 0);
  const pbRatio = valuation.pbRatio || (netWorth > 0 ? marketCap / netWorth : 0);
  const evEbitdaRatio = valuation.evEbitdaRatio || (ebitda > 0 ? enterpriseValue / (ebitda * 4) : 0);
  const dividendYield = valuation.dividendYield;

  // Red Flag Deterministic Audit
  const highLeverage = debtToEquity > 2.0;
  const weakInterestCoverage = interestCoverage < 1.5 && financeCosts > 5;
  const negativeOperatingScissors = hasNegativeScissors;
  const lowROCE = rocePercent < 8.0;
  const netLossQuarter = pat < 0;
  const severeOtherIncomeDependence = otherIncomeToPATShare > 40;

  // Risk Score calculation: starts at 100, deducts penalty per red flag
  let riskPenalty = 0;
  if (highLeverage) riskPenalty += 25;
  if (weakInterestCoverage) riskPenalty += 30;
  if (netLossQuarter) riskPenalty += 30;
  if (negativeOperatingScissors) riskPenalty += 15;
  if (lowROCE) riskPenalty += 15;
  if (severeOtherIncomeDependence) riskPenalty += 10;

  const overallRiskScore = Math.max(5, Math.min(100, 100 - riskPenalty));

  let riskRating: 'PRIME / LOW RISK' | 'MODERATE / WATCHLIST' | 'ELEVATED / CAUTION' | 'DISTRESSED / HIGH RISK' = 'PRIME / LOW RISK';
  if (overallRiskScore < 40) {
    riskRating = 'DISTRESSED / HIGH RISK';
  } else if (overallRiskScore < 65) {
    riskRating = 'ELEVATED / CAUTION';
  } else if (overallRiskScore < 85) {
    riskRating = 'MODERATE / WATCHLIST';
  }

  return {
    revenue,
    otherIncome,
    totalIncome,
    rawMaterialCost,
    employeeCost,
    otherOperatingExpenses,
    totalOperatingCosts,
    ebitda,
    ebitdaWithOtherIncome,
    depreciation,
    ebit,
    financeCosts,
    ebt,
    tax,
    pat,
    opmPercent,
    npmPercent,
    effectiveTaxRate,
    netWorth,
    totalDebt,
    capitalEmployed,
    debtToEquity,
    interestCoverage,
    annualizedPATRunRate,
    rocePercent,
    economicSpread,
    roePercent,
    salesYoYGrowth,
    patYoYGrowth,
    ebitdaYoYGrowth,
    operatingScissorsGap,
    hasNegativeScissors,
    coreOperatingProfitShare,
    otherIncomeToPATShare,
    marketCap,
    peRatio,
    pbRatio,
    evEbitdaRatio,
    dividendYield,
    enterpriseValue,
    redFlags: {
      highLeverage,
      weakInterestCoverage,
      negativeOperatingScissors,
      lowROCE,
      netLossQuarter,
      severeOtherIncomeDependence
    },
    overallRiskScore,
    riskRating
  };
};

export const formatCurrency = (
  valueInCrores: number,
  unit: CurrencyUnit = 'INR_CRORE',
  includeSymbol: boolean = true,
  decimals: number = 2
): string => {
  if (valueInCrores === undefined || valueInCrores === null || isNaN(valueInCrores)) {
    return includeSymbol ? '₹ 0.00 Cr' : '0.00';
  }

  const isNeg = valueInCrores < 0;
  const absVal = Math.abs(valueInCrores);

  if (unit === 'INR_LAKH') {
    const inLakhs = absVal * 100;
    const formatted = inLakhs.toLocaleString('en-IN', {
      maximumFractionDigits: decimals,
      minimumFractionDigits: decimals
    });
    return `${isNeg ? '-' : ''}${includeSymbol ? '₹ ' : ''}${formatted} L`;
  }

  if (unit === 'USD_MILLION') {
    // Approx conversion: 1 Cr INR ~= 0.116M USD (assuming 86.5 INR/USD)
    const inUSDMillion = absVal * 0.116;
    const formatted = inUSDMillion.toLocaleString('en-US', {
      maximumFractionDigits: decimals,
      minimumFractionDigits: decimals
    });
    return `${isNeg ? '-' : ''}${includeSymbol ? '$ ' : ''}${formatted} M`;
  }

  // Default: INR_CRORE in Indian numbering format
  const formatted = absVal.toLocaleString('en-IN', {
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals
  });

  return `${isNeg ? '-' : ''}${includeSymbol ? '₹ ' : ''}${formatted} Cr`;
};

export const formatPercent = (val: number, decimals: number = 2, showSign: boolean = false): string => {
  if (val === undefined || val === null || isNaN(val)) return '0.00%';
  const sign = showSign && val > 0 ? '+' : '';
  return `${sign}${val.toFixed(decimals)}%`;
};

export const formatMultiple = (val: number, decimals: number = 2): string => {
  if (val === undefined || val === null || isNaN(val)) return '0.00x';
  if (val >= 99) return '>99.0x';
  return `${val.toFixed(decimals)}x`;
};
