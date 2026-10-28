export type UserRole = 'Admin' | 'CA' | 'Bank Officer' | 'Loan Consultant' | 'Viewer';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  organization: string;
  avatar?: string;
}

export interface Company {
  id: string;
  companyName: string;
  cin: string;
  pan: string;
  industry: string;
  address: string;
  yearEstablished: number;
  annualTurnover: number; // in INR Crores
  createdBy: string;
  createdAt: string;
  description?: string;
}

export interface BalanceSheet {
  // Current Assets
  cash: number;
  bank: number;
  receivables: number;
  inventory: number;
  otherCurrentAssets: number;
  
  // Non-Current Assets
  fixedAssets: number; // Net PPE
  investments: number;
  otherNonCurrentAssets: number;
  
  // Current Liabilities
  payables: number;
  shortTermDebt: number;
  otherCurrentLiabilities: number;
  
  // Non-Current Liabilities
  longTermDebt: number;
  otherNonCurrentLiabilities: number;
  
  // Equity
  equity: number; // Share capital
  reserves: number; // Retained earnings & surplus
  
  // Computed helpers
  totalCurrentAssets: number;
  totalCurrentLiabilities: number;
  totalDebt: number;
  totalEquity: number;
  totalAssets: number;
  totalLiabilities: number;
}

export interface ProfitAndLoss {
  revenue: number;
  otherIncome: number;
  cogs: number; // Cost of goods sold
  grossProfit: number;
  operatingExpenses: number; // SG&A, salaries, administrative
  ebitda: number;
  depreciation: number;
  ebit: number; // Operating profit
  interestExpense: number;
  profitBeforeTax: number;
  taxExpense: number;
  netProfit: number;
}

export interface FinancialStatement {
  id: string;
  companyId: string;
  financialYear: string; // e.g. "FY 2024-25" or "FY 2024"
  currency: string;
  unit: string; // e.g. "INR Crores"
  balanceSheet: BalanceSheet;
  profitAndLoss: ProfitAndLoss;
}

export interface RatioItem {
  id: string;
  name: string;
  category: 'Liquidity' | 'Profitability' | 'Solvency' | 'Efficiency';
  value: number;
  formattedValue: string;
  benchmark: string;
  benchmarkMin?: number;
  benchmarkMax?: number;
  status: 'Healthy' | 'Moderate' | 'Risk';
  formula: string;
  interpretation: string;
}

export interface FinancialRatios {
  financialYear: string;
  
  // Liquidity Ratios
  currentRatio: number;
  quickRatio: number;
  cashRatio: number;
  
  // Profitability Ratios
  grossMargin: number; // percentage
  netProfitMargin: number; // percentage
  ebitdaMargin: number; // percentage
  roa: number; // Return on Assets (%)
  roe: number; // Return on Equity (%)
  
  // Solvency Ratios
  debtEquityRatio: number;
  interestCoverageRatio: number;
  debtToAssets: number;
  
  // Efficiency Ratios
  inventoryTurnover: number;
  daysInventoryOutstanding: number; // DIO
  assetTurnover: number;
  receivablesTurnover: number;
  daysSalesOutstanding: number; // DSO
  workingCapitalTurnover: number;
  
  items: RatioItem[];
}

export interface HealthScoreCategory {
  category: 'Liquidity' | 'Profitability' | 'Solvency' | 'Efficiency';
  weight: number; // 25
  score: number; // 0-100
  weightedScore: number; // 0-25
  grade: 'Excellent' | 'Good' | 'Average' | 'Weak' | 'High Risk';
  keyDriver: string;
}

export interface FinancialHealthScore {
  totalScore: number; // 0-100
  rating: 'Excellent' | 'Good' | 'Average' | 'Weak' | 'High Risk';
  categories: HealthScoreCategory[];
}

export type CreditGrade = 'AAA' | 'AA' | 'A' | 'BBB' | 'BB' | 'B';
export type RecommendationType = 'Approve' | 'Conditional Approval' | 'Review Required' | 'Reject';

export interface CreditAssessment {
  id: string;
  companyId: string;
  financialYear: string;
  assessmentDate: string;
  healthScore: FinancialHealthScore;
  creditGrade: CreditGrade;
  riskLevel: 'Very Low Risk' | 'Low Risk' | 'Moderate Risk' | 'Moderate to High' | 'High Risk' | 'Very High Risk';
  recommendation: RecommendationType;
  decisionRationale: string[];
  recommendedCreditLimit: number; // in Crores
  recommendedInterestSpread: string;
  collateralRequirement: string;
  covenants: string[];
  strengths: string[];
  weaknesses: string[];
  analystSummary: string;
}

export interface RedFlag {
  id: string;
  category: 'Liquidity Risk' | 'Profitability Risk' | 'Solvency Risk' | 'Growth Risk' | 'Working Capital Risk';
  severity: 'Critical' | 'Warning' | 'Advisory';
  title: string;
  description: string;
  metric: string;
  actualValue: string;
  threshold: string;
  recommendation: string;
}

export interface AuditLog {
  id: string;
  userId: string;
  userName: string;
  userRole: UserRole;
  action: string;
  details: string;
  timestamp: string;
}
