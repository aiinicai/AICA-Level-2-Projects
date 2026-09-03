export type PeriodId = 'Q4 FY25' | 'Q3 FY25' | 'Q2 FY25' | 'FY24' | 'FY23';

export type IndustrySector =
  | 'Automobiles & Auto Ancillaries'
  | 'Banking & Financial Services'
  | 'IT - Software & Services'
  | 'Oil, Gas & Petroleum'
  | 'Metals & Mining'
  | 'Pharmaceuticals & Healthcare'
  | 'Fast Moving Consumer Goods (FMCG)'
  | 'Telecommunication'
  | 'Power & Utilities'
  | 'Cement & Building Materials'
  | 'Chemicals & Agrochemicals'
  | 'Capital Goods & Engineering'
  | 'Infrastructure & Construction'
  | 'Consumer Durables & Electronics'
  | 'Real Estate & Urban Dev'
  | 'Retail & E-Commerce'
  | 'Aviation & Defence'
  | 'Textiles & Apparels'
  | 'Renewable Energy'
  | 'Tyres & Rubber Products'
  | 'Logistics & Supply Chain'
  | 'Media & Entertainment'
  | 'Fertilizers & Agriculture'
  | 'Hotels & Hospitality'
  | 'Paper & Forest Products';

export interface PLStatement {
  revenueFromOperations: number; // ₹ Cr
  otherIncome: number; // ₹ Cr
  totalRevenue: number; // ₹ Cr
  costOfMaterialsConsumed: number; // ₹ Cr
  purchaseOfStockInTrade: number; // ₹ Cr
  changesInInventories: number; // ₹ Cr
  employeeBenefitExpenses: number; // ₹ Cr
  financeCosts: number; // ₹ Cr (Interest)
  depreciationAndAmortization: number; // ₹ Cr
  otherExpenses: number; // ₹ Cr
  totalExpenses: number; // ₹ Cr
  profitBeforeTax: number; // ₹ Cr (EBT)
  taxExpense: number; // ₹ Cr
  profitAfterTax: number; // ₹ Cr (PAT)
  
  // Historical / Prior year comparable for Waterfall
  prevYearRevenue?: number;
  prevYearPAT?: number;
  prevYearEBITDA?: number;
}

export interface BalanceSheetCapital {
  equityShareCapital: number; // ₹ Cr
  reservesAndSurplus: number; // ₹ Cr
  longTermBorrowings: number; // ₹ Cr
  shortTermBorrowings: number; // ₹ Cr
  otherLiabilities: number; // ₹ Cr
  totalAssets: number; // ₹ Cr
  fixedAssetsNet: number; // ₹ Cr
  capitalWorkInProgress: number; // ₹ Cr
  investments: number; // ₹ Cr
  cashAndEquivalents: number; // ₹ Cr
  currentAssetsOther: number; // ₹ Cr
}

export interface MarketValuation {
  stockPrice: number; // ₹
  marketCap: number; // ₹ Cr
  peRatio: number;
  pbRatio: number;
  evEbitdaRatio: number;
  dividendYield: number; // %
  fiftyTwoWeekHigh: number; // ₹
  fiftyTwoWeekLow: number; // ₹
  sharesOutstandingCr: number; // Cr shares
}

export interface CompanyEntity {
  id: string;
  ticker: string;
  bseCode: string;
  name: string;
  shortName: string;
  sector: IndustrySector;
  foundedYear: number;
  headquarters: string;
  ceo: string;
  description: string;
  benchmarkCostOfCapital: number; // Default 10.0%
  periods: Record<PeriodId, {
    pl: PLStatement;
    balanceSheet: BalanceSheetCapital;
    valuation: MarketValuation;
  }>;
}

export interface DeterministicMetrics {
  revenue: number;
  otherIncome: number;
  totalIncome: number;
  rawMaterialCost: number;
  employeeCost: number;
  otherOperatingExpenses: number;
  totalOperatingCosts: number;
  ebitda: number; // Operating EBITDA
  ebitdaWithOtherIncome: number;
  depreciation: number;
  ebit: number;
  financeCosts: number;
  ebt: number;
  tax: number;
  pat: number;
  
  // Deterministic calculated ratios
  opmPercent: number; // (EBITDA / Revenue) * 100
  npmPercent: number; // (PAT / Total Revenue) * 100
  effectiveTaxRate: number; // (Tax / EBT) * 100
  
  // Balance sheet & Solvency
  netWorth: number; // Equity Capital + Reserves
  totalDebt: number; // Long Term + Short Term Borrowings
  capitalEmployed: number; // Net Worth + Total Debt (or Total Assets - Current Liab)
  debtToEquity: number; // Total Debt / Net Worth
  interestCoverage: number; // EBIT / Finance Costs
  
  // Returns & Spreads
  annualizedPATRunRate: number; // PAT * 4
  rocePercent: number; // (EBIT * 4 / Capital Employed) * 100
  economicSpread: number; // ROCE - Benchmark Cost of Capital
  roePercent: number; // (PAT * 4 / Net Worth) * 100
  
  // Growth & Operating Scissors
  salesYoYGrowth: number; // %
  patYoYGrowth: number; // %
  ebitdaYoYGrowth: number; // %
  operatingScissorsGap: number; // salesYoYGrowth - patYoYGrowth
  hasNegativeScissors: boolean; // sales > 0 but pat < 0 OR gap > 12%
  
  // Earnings Quality
  coreOperatingProfitShare: number; // (EBIT / (EBIT + Other Income)) * 100
  otherIncomeToPATShare: number; // (Other Income / PAT) * 100
  
  // Valuation metrics
  marketCap: number;
  peRatio: number;
  pbRatio: number;
  evEbitdaRatio: number;
  dividendYield: number;
  enterpriseValue: number; // MCap + Total Debt - Cash
  
  // Risk assessment
  redFlags: {
    highLeverage: boolean; // D/E > 2.0x
    weakInterestCoverage: boolean; // Interest coverage < 1.5x
    negativeOperatingScissors: boolean; // Topline positive, PAT negative growth
    lowROCE: boolean; // ROCE < 8.0%
    netLossQuarter: boolean; // PAT < 0
    severeOtherIncomeDependence: boolean; // Other Income > 40% of PAT
  };
  overallRiskScore: number; // 0 to 100 (100 = safest, 0 = severe distress)
  riskRating: 'PRIME / LOW RISK' | 'MODERATE / WATCHLIST' | 'ELEVATED / CAUTION' | 'DISTRESSED / HIGH RISK';
}

export type ActiveTab =
  | 'executive'
  | 'pl_waterfall'
  | 'solvency_capital'
  | 'operating_scissors'
  | 'valuation_multiples'
  | 'peer_benchmark'
  | 'companies_explorer'
  | 'risk_audit'
  | 'data_schema';

export type CurrencyUnit = 'INR_CRORE' | 'INR_LAKH' | 'USD_MILLION';
