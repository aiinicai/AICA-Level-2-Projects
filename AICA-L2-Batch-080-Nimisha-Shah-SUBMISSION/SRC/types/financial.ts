export type CurrencyCode = 'INR' | 'USD' | 'EUR';
export type UnitScale = 'crores' | 'lakhs' | 'millions';

export type NavTabId =
  | 'executive'
  | 'profitability'
  | 'solvency'
  | 'growth'
  | 'valuation'
  | 'working_capital'
  | 'peer_benchmark'
  | 'red_flags'
  | 'explorer'
  | 'data_quality';

export interface FinancialPeriod {
  periodId: string;
  revenue: number;
  otherIncome: number;
  totalIncome: number;
  rawMaterialCosts: number;
  employeeCosts: number;
  otherOperatingExpenses: number;
  ebitda: number;
  depreciation: number;
  ebit: number;
  interest: number;
  ebt: number;
  tax: number;
  pat: number;
  opm: number;
  npm: number;
  netWorth: number;
  totalDebt: number;
  debtToEquity: number;
  interestCoverage: number;
  roce: number;
  
  // Working Capital & Cash Flow (₹ Cr)
  tradeReceivables?: number;
  inventory?: number;
  tradePayables?: number;
  netWorkingCapital?: number;
  dso?: number;
  dio?: number;
  dpo?: number;
  ccc?: number;
  capex?: number;
  fcff?: number;
  fcfe?: number;
}

export interface ListedCompany {
  bseCode: string;
  nseCode: string;
  name: string;
  shortName: string;
  sector: string;
  industryGroup: string;
  marketCap: number; // in ₹ Cr
  stockPrice: number; // in ₹
  peRatio: number;
  pbRatio: number;
  dividendYield: number; // %
  fiftyTwoWeekHigh: number;
  fiftyTwoWeekLow: number;
  
  // Latest Reported Quarter & P&L (₹ Cr)
  salesLatestQuarter: number;
  salesPrecedingQuarter: number;
  salesPriorYearQuarter: number;
  salesGrowthYoY: number; // %
  
  ebitdaLatestQuarter: number;
  ebitdaPriorYearQuarter: number;
  ebitdaMargin: number; // % (OPM)
  
  netProfitLatestQuarter: number; // PAT
  netProfitPriorYearQuarter: number;
  netProfitGrowthYoY: number; // %
  netProfitMargin: number; // % (NPM)
  
  annualizedRunRateSales: number;
  annualizedRunRatePAT: number;
  
  // Other Income & Earnings Quality
  otherIncomeLatestQuarter: number;
  otherIncomeShareOfEbidt: number; // % of EBITDA or PAT
  
  // Cost items (₹ Cr)
  costOfMaterials: number;
  employeeExpenses: number;
  otherOperatingExpenses: number;
  financeCosts: number;
  depreciation: number;
  taxExpense: number;
  
  // Solvency & Balance Sheet (₹ Cr)
  netWorth: number;
  debt: number;
  debtToEquity: number;
  interestCoverage: number;
  roce: number; // %
  capitalEmployed: number;
  
  // Working Capital & Cash Flow Items (₹ Cr)
  tradeReceivables?: number;
  inventory?: number;
  tradePayables?: number;
  cashAndEquivalents?: number;
  fixedAssets?: number;
  capex?: number;
  dso?: number; // Days Sales Outstanding
  dio?: number; // Days Inventory Outstanding
  dpo?: number; // Days Payables Outstanding
  ccc?: number; // Cash Conversion Cycle (DSO + DIO - DPO)
  fcff?: number; // Free Cash Flow to Firm
  fcfe?: number; // Free Cash Flow to Equity
  
  // Growth diagnostic & scissors
  hasOperatingScissors: boolean;
  scissorsGap: number; // Sales YoY - PAT YoY
  
  // Executive profile
  ceo: string;
  headquarters: string;
  foundedYear: number;
  description: string;
}

export interface DataQualityReport {
  qualityScore: number;
  totalRecords: number;
  dateRange: string;
  isBalanced: boolean;
  errors: string[];
  warnings: string[];
  missingFields: string[];
  fieldCompleteness: { field: string; percentage: number }[];
}
