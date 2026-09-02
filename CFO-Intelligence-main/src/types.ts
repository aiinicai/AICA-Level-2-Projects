export type IndustryType =
  | 'medical'
  | 'restaurant'
  | 'manufacturing'
  | 'saas'
  | 'professional_services'
  | 'legal'
  | 'accounting'
  | 'dental'
  | 'construction'
  | 'real_estate'
  | 'ecommerce'
  | 'retail'
  | 'logistics'
  | 'nonprofit'
  | 'financial_services'
  | 'wholesale'
  | 'automotive'
  | 'other';

export type EntityType = 'LLC' | 'S-Corp' | 'C-Corp' | 'Pvt Ltd' | 'Partnership' | 'Sole Proprietorship' | 'Non-Profit';
export type BusinessSize = 'Startup (<$1M)' | 'Emerging ($1M - $5M)' | 'Mid-Market ($5M - $25M)' | 'Enterprise ($25M+)';
export type CurrencyCode = 'USD' | 'EUR' | 'GBP' | 'CAD' | 'AUD' | 'INR' | 'SGD';

export type NavigationTab =
  | 'executive_summary'
  | 'financial_statements'
  | 'kpi_benchmarks'
  | 'forecasting'
  | 'scenarios'
  | 'breakeven'
  | 'budget_vs_actual'
  | 'data_quality'
  | 'privacy_shield'
  | 'data_import'
  | 'cfo_pack'
  | 'integrations'
  | 'audit_trail'
  | 'settings';

export interface ClientProfile {
  id: string;
  name: string;
  legalEntityName: string;
  industry: IndustryType;
  industryName: string;
  businessDescription: string;
  entityType: EntityType;
  country: string;
  currency: CurrencyCode;
  currencySymbol: string;
  fiscalYearEnd: string;
  reportingPeriod: string;
  businessSize: BusinessSize;
  headcount: number;
  contactEmail: string;
  contactPhone: string;
  taxId: string;
  bankAccountMasked: string;
  isDemo?: boolean;
  privacyMode: 'standard' | 'strict' | 'maximum';
  lastUpdated: string;
  createdDate?: string;
}

export interface FinancialPeriod {
  periodKey: string; // e.g. "2026-01", "2026-02"
  label: string; // e.g. "Jan 2026"
  isActual: boolean;
  isForecast?: boolean;
  isBudget?: boolean;
}

export interface MonthlyFinancialRecord {
  periodKey: string;
  periodLabel: string;
  
  // P&L
  revenue: number;
  cogs: number;
  grossProfit: number;
  grossMarginPercent: number;
  
  // OPEX breakdown
  salariesAndWages: number;
  salesAndMarketing: number;
  rentAndFacilities: number;
  generalAndAdmin: number;
  depreciationAndAmort: number;
  otherOpex: number;
  totalOpex: number;
  
  ebitda: number;
  ebitdaMarginPercent: number;
  interestExpense: number;
  taxExpense: number;
  netIncome: number;
  netMarginPercent: number;
  
  // Balance Sheet
  cashAndEquivalents: number;
  accountsReceivable: number;
  inventory: number;
  otherCurrentAssets: number;
  totalCurrentAssets: number;
  fixedAssets: number;
  totalAssets: number;
  
  accountsPayable: number;
  shortTermDebt: number;
  accruedLiabilities: number;
  totalCurrentLiabilities: number;
  longTermDebt: number;
  totalLiabilities: number;
  totalEquity: number;
  
  // Cash Flow
  operatingCashFlow: number;
  investingCashFlow: number;
  financingCashFlow: number;
  netCashFlow: number;
  endingCash: number;
  
  // Working Capital metrics
  workingCapital: number;
  currentRatio: number;
  quickRatio: number;
  dso: number; // Days Sales Outstanding
  dpo: number; // Days Payable Outstanding
  dio: number; // Days Inventory Outstanding
  ccc: number; // Cash Conversion Cycle
  
  // Headcount & units
  headcount?: number;
  unitsSold?: number;
  averageSellingPrice?: number;
}

export interface FinancialModel {
  client: ClientProfile;
  periods: FinancialPeriod[];
  historicalMonthly: MonthlyFinancialRecord[];
  budgetMonthly: MonthlyFinancialRecord[];
  forecastMonthly: MonthlyFinancialRecord[];
  annualSummaries: {
    year: number;
    revenue: number;
    grossProfit: number;
    ebitda: number;
    netIncome: number;
    operatingCashFlow: number;
    endingCash: number;
  }[];
  summary?: {
    totalRevenue: number;
    totalGrossProfit: number;
    averageGrossMargin: number;
    totalEbitda: number;
    averageEbitdaMargin: number;
    totalNetIncome: number;
    averageNetMargin: number;
    endingCash: number;
    cashRunwayMonths: number;
  };
  budgetBasisConfig?: BudgetForecastBasisConfig;
}

export type RevenueBasisMethod =
  | 'growth_rate'
  | 'headcount_capacity'
  | 'unit_economics'
  | 'mrr_waterfall'
  | 'seasonality_curve'
  | 'custom_targets';

export type GrossMarginBasisMethod =
  | 'target_margin_pct'
  | 'direct_cogs_breakdown'
  | 'volume_tiered';

export interface PlannedNewHire {
  id: string;
  role: string;
  department: 'Sales' | 'Engineering' | 'Operations' | 'Clinical' | 'G&A';
  annualSalary: number;
  startMonth: number; // 1 to 12
}

export interface BudgetForecastBasisConfig {
  name: string;
  description?: string;
  
  // Revenue Basis
  revenueBasis: {
    method: RevenueBasisMethod;
    growthRatePercent: number; // e.g. +12.5% YoY
    revenuePerFte: number; // e.g. $185,000 / employee
    targetHeadcount: number;
    unitVolumeMonthly: number; // e.g. 1,200 units/mo
    averageOrderValue: number; // e.g. $450/unit
    startingMrr: number;
    mrrGrowthPercent: number; // e.g. 3.5% mo/mo
    mrrChurnPercent: number; // e.g. 1.2% mo/mo
    mrrExpansionPercent: number; // e.g. 2.0% mo/mo
    monthlyTargetValues?: number[]; // custom 12-month array
  };

  // Gross Margin & COGS Basis
  grossMarginBasis: {
    method: GrossMarginBasisMethod;
    targetGrossMarginPercent: number; // e.g. 68.0%
    directLaborPercentOfRevenue: number; // e.g. 18.0%
    directMaterialsPercentOfRevenue: number; // e.g. 14.0%
    supplierVolumeDiscountPercent: number; // e.g. 2.5% savings at scale
  };

  // Operating Expenses & Headcount Basis
  opexBasis: {
    payrollCostOfLivingAdjustmentPercent: number; // e.g. 4.0%
    payrollTaxBenefitLoadMultiplier: number; // e.g. 1.22 (22% load)
    plannedNewHires: PlannedNewHire[];
    marketingMethod: 'fixed' | 'percent_of_revenue' | 'cac_target';
    marketingPercentOfRevenue: number; // e.g. 6.5%
    marketingFixedMonthly: number; // e.g. $25,000
    targetCac: number; // e.g. $420
    targetNewCustomersMonthly: number; // e.g. 45
    rentLeaseEscalationPercent: number; // e.g. 3.0%
    generalAdminInflationPercent: number; // e.g. 3.5%
    gnaRevenueScalingStepPercent: number; // e.g. 1.5% increase per $1M rev
  };

  // Working Capital & Cash Buffer Basis
  workingCapitalBasis: {
    targetDsoDays: number; // Days Sales Outstanding target
    targetDpoDays: number; // Days Payable Outstanding target
    targetDioDays: number; // Days Inventory Outstanding target
    minimumCashReserveMonths: number; // Buffer threshold (e.g. 3 months OPEX)
  };

  // Seasonality Tuning (12 indices summing to 12.0)
  seasonalityWeights: number[];
}

// Universal Statement Parsing & AI Disambiguation Types
export type StandardTaxonomyCategory =
  | 'revenue'
  | 'cogs'
  | 'direct_labor'
  | 'salaries_opex'
  | 'sales_marketing_opex'
  | 'rent_facilities_opex'
  | 'gna_opex'
  | 'depreciation_opex'
  | 'depreciation_amort_opex'
  | 'interest_tax'
  | 'cash_current_assets'
  | 'ar_current_assets'
  | 'inventory_current_assets'
  | 'other_current_assets'
  | 'fixed_non_current_assets'
  | 'ap_current_liabilities'
  | 'short_term_debt_liabilities'
  | 'accrued_current_liabilities'
  | 'long_term_liabilities'
  | 'long_term_debt_liabilities'
  | 'equity'
  | 'retained_equity'
  | 'other_income_expense';

export interface AiAccountMappingItem {
  id: string;
  sourceAccountName: string;
  sourceAccountNumber?: string;
  detectedType: 'pnl' | 'balance_sheet' | 'trial_balance';
  targetCategory: StandardTaxonomyCategory;
  categoryLabel: string;
  confidence: number; // 0-100
  needsClarification: boolean;
  sampleValues: Record<string, number>;
  totalDebit?: number;
  totalCredit?: number;
  netBalance?: number;
  notes?: string;
}

export interface AiDisambiguationQuestion {
  id: string;
  accountName: string;
  question: string;
  context: string;
  options: {
    label: string;
    targetCategory: StandardTaxonomyCategory;
    description: string;
    isRecommended?: boolean;
  }[];
  selectedOptionIndex?: number;
  status: 'pending' | 'resolved';
}

export interface AiMappingReviewData {
  fileName: string;
  fileSizeBytes?: number;
  detectedStatementType: 'pnl' | 'balance_sheet' | 'trial_balance' | 'cash_flow' | 'ar_ap_aging' | 'multi_statement_workbook';
  periodsDetected: string[];
  totalDebitSum?: number;
  totalCreditSum?: number;
  isTrialBalanceBalanced?: boolean;
  totalAccountsCount: number;
  ambiguousAccountsCount: number;
  overallConfidenceScore: number;
  mappedAccounts: AiAccountMappingItem[];
  clarificationQuestions: AiDisambiguationQuestion[];
  rawTextPreview?: string;
}

export interface UploadedFileSummary {
  id: string;
  name: string;
  size: number;
  detectedType: 'pnl' | 'balance_sheet' | 'trial_balance' | 'cash_flow' | 'ar_aging' | 'ap_aging' | 'general_ledger' | 'unknown';
  periodsDetected: string[];
  lineItemsCount: number;
  confidence: number;
  status: 'ready' | 'processing' | 'error';
  errorMessage?: string;
  isAiEnhanced?: boolean;
}

export interface CrossReconciliationAudit {
  isTrialBalanceBalanced: boolean;
  totalDebits: number;
  totalCredits: number;
  imbalanceAmount: number;
  pnlNetIncomeMatchesBsEquity: boolean;
  cashMatchesEndingBalance: boolean;
  reconciliationScore: number;
  reconciliationNotes: string[];
}

export interface ConsolidatedFinancialPackage {
  files: UploadedFileSummary[];
  hasPnl: boolean;
  hasBalanceSheet: boolean;
  hasTrialBalance: boolean;
  hasCashFlow: boolean;
  detectedPeriods: string[];
  consolidatedRecords: MonthlyFinancialRecord[];
  allMappedAccounts: (AiAccountMappingItem & { sourceFileName: string })[];
  allClarificationQuestions: (AiDisambiguationQuestion & { sourceFileName: string })[];
  crossReconciliation: CrossReconciliationAudit;
  overallConfidence: number;
  summaryMetrics: {
    totalRevenueYTD: number;
    totalGrossProfitYTD: number;
    totalEbitdaYTD: number;
    latestCashBalance: number;
    latestTotalAssets: number;
    latestTotalLiabilities: number;
    latestTotalEquity: number;
  };
}

// MCP (Model Context Protocol) Types
export interface McpToolParameterProperty {
  type: string;
  description: string;
  enum?: string[];
  default?: any;
}

export interface McpToolDefinition {
  name: string;
  description: string;
  category?: 'accounting' | 'reports' | 'tax' | 'banking';
  supportedConnectors?: ('qbo' | 'tally' | 'zoho' | 'netsuite' | 'xero')[];
  inputSchema: {
    type: 'object';
    properties: Record<string, McpToolParameterProperty>;
    required?: string[];
  };
}

export interface McpToolCallRequest {
  tool: string;
  connectorId: 'qbo' | 'tally' | 'zoho' | 'netsuite' | 'xero';
  arguments: Record<string, any>;
}

export interface McpToolCallResult {
  success: boolean;
  tool: string;
  connectorId: string;
  executionTimeMs: number;
  timestamp: string;
  result: any;
  error?: string;
  mcpProtocolVersion: string;
}

export type McpExecutionResult = McpToolCallResult;

export interface McpServerStatus {
  isRunning: boolean;
  protocolVersion: string;
  sseEndpoint: string;
  messagesEndpoint: string;
  toolsCount: number;
  activeConnectorsCount: number;
  authBearerToken: string;
  lastPingTimestamp: string;
}

export interface KpiMetric {
  id: string;
  name: string;
  category: 'profitability' | 'liquidity' | 'efficiency' | 'growth' | 'industry';
  value: number;
  formattedValue: string;
  benchmarkValue?: number;
  benchmarkFormatted?: string;
  benchmarkStatus: 'outperforming' | 'on_track' | 'lagging' | 'critical' | 'unavailable';
  targetValue?: number;
  trend: 'up' | 'down' | 'stable';
  changePercentage: number;
  changePeriod: string;
  explanation: {
    whatIsIt: string;
    whyItMatters: string;
    whatMyNumberMeans: string;
    formula: string;
  };
  isIndustrySpecific?: boolean;
}

export interface RedFlagAlert {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  metric: string;
  currentValue: string;
  threshold: string;
  impact: string;
  recommendation: string;
  category: 'cash_runway' | 'margins' | 'expenses' | 'collections' | 'debt' | 'concentration' | 'quality';
}

export interface WinHighlight {
  id: string;
  title: string;
  metric: string;
  change: string;
  businessImpact: string;
  category: 'revenue' | 'margin' | 'efficiency' | 'cash';
}

export interface OpportunityInsight {
  id: string;
  title: string;
  potentialImpact: string;
  effort: 'Low' | 'Medium' | 'High';
  timeframe: 'Immediate (<30d)' | 'Quarterly (90d)' | 'Strategic (6-12m)';
  actionPlan: string;
}

export interface CfoCommentary {
  headlineSummary: string;
  whatHappened: string;
  whyItHappened: string;
  whyItMatters: string;
  recommendedActions: string[];
  strategicSummary: string;
  confidenceScore: number;
  isAiGenerated: boolean;
  lastEditedBy?: string;
  lastEditedAt?: string;
}

export interface RedactionToken {
  id: string;
  originalText: string;
  tokenType: 'COMPANY' | 'PERSON' | 'BANK_ACCOUNT' | 'TAX_ID' | 'ADDRESS' | 'PHONE' | 'EMAIL' | 'CARD' | 'CUSTOM';
  tokenValue: string; // e.g. CLIENT_001
  occurrences: number;
  confidence: number;
  status: 'approved' | 'pending' | 'custom' | 'excluded';
  sourceDocuments: string[];
  // Compatibility aliases
  category?: string;
  originalValue?: string;
  token?: string;
}

export interface DataQualityIssue {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  category: 'missing_period' | 'balance_imbalance' | 'outlier' | 'negative_balance' | 'unclassified' | 'budget_gap';
  title: string;
  description: string;
  periodOrAccount?: string;
  remedy: string;
}

export interface DataQualityReport {
  score: number; // 0-100
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  issues: DataQualityIssue[];
  totalPeriodsChecked: number;
  reconciliationStatus: 'balanced' | 'minor_variance' | 'unbalanced';
  lastAudited: string;
}

export interface ScenarioDrivers {
  name: string;
  revenueGrowthRateDelta: number; // e.g. +5%
  grossMarginDelta: number; // e.g. +2%
  priceAdjustmentPercent: number; // e.g. +7%
  headcountDelta: number; // e.g. +3
  averageSalaryNewHires: number; // e.g. $85,000
  marketingBudgetDeltaMonthly: number; // e.g. +$10,000
  opexInflationPercent: number; // e.g. +3%
  dsoImprovementDays: number; // e.g. -10 days (collections faster)
  dpoExtensionDays: number; // e.g. +5 days (vendor terms extended)
}

export interface ScenarioResult {
  driverConfig: ScenarioDrivers;
  annualRevenue: number;
  annualGrossProfit: number;
  annualEbitda: number;
  annualNetIncome: number;
  endingCash: number;
  cashRunwayMonths: number;
  breakEvenMonthlyRevenue: number;
  totalProjectedRevenue?: number;
  totalProjectedGrossProfit?: number;
  totalProjectedEbitda?: number;
  totalProjectedNetIncome?: number;
  totalProjectedCashFlow?: number;
  endingCashBalance?: number;
  monthlyProjections: {
    month: string;
    revenue: number;
    cogs?: number;
    grossProfit: number;
    totalOpex?: number;
    ebitda: number;
    netIncome: number;
    cashBalance: number;
    netCashFlow: number;
  }[];
}

export interface BreakEvenParameters {
  sellingPricePerUnit: number;
  variableCostPerUnit: number;
  monthlyFixedCosts: number;
  currentMonthlyUnits: number;
  targetMonthlyUnits: number;
  targetMonthlyProfit: number;
}

export interface BreakEvenResult {
  contributionMarginPerUnit: number;
  contributionMarginRatio: number;
  breakEvenUnits: number;
  breakEvenRevenue: number;
  marginOfSafetyUnits: number;
  marginOfSafetyRevenue: number;
  marginOfSafetyPercent: number;
  currentProfit: number;
  targetVolumeProfit: number;
  chartPoints: {
    units: number;
    revenue: number;
    totalCosts: number;
    fixedCosts: number;
  }[];
}

export interface AccountingConnector {
  id: 'qbo' | 'tally' | 'xero' | 'netsuite' | 'sage' | 'zoho';
  name: string;
  status: 'connected' | 'disconnected' | 'syncing' | 'error';
  lastSynced?: string;
  companyName?: string;
  supportedEntities: string[];
  syncFrequency: 'Manual' | 'Daily' | 'Hourly';
  authType: 'OAuth2' | 'API Key' | 'Agent Bridge';
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  category: 'AUTH' | 'DATA_IMPORT' | 'PRIVACY_REDACTION' | 'REPORT_EXPORT' | 'SCENARIO_SAVED' | 'COMMENTARY_EDIT';
  details: string;
  ipAddress?: string;
}

export interface ReportSectionConfig {
  id: string;
  title: string;
  category: string;
  included: boolean;
  customNotes?: string;
  chartType?: 'bar' | 'line' | 'waterfall' | 'area' | 'table';
}

export interface SavedCfoReport {
  id: string;
  title: string;
  clientId: string;
  clientName: string;
  version: string;
  createdAt: string;
  curatedBy: string;
  firmName: string;
  sections: ReportSectionConfig[];
  commentary: CfoCommentary;
  scenarioUsed?: string;
}

export interface WeeklyCashForecastItem {
  weekNumber: number;
  weekLabel: string;
  startDate: string;
  beginningCash: number;
  // Inflows
  arCollections: number;
  cashSales: number;
  otherInflows: number;
  totalInflows: number;
  // Outflows
  payrollAndBenefits: number;
  cogsSupplierPayments: number;
  rentAndFacilities: number;
  operatingExpenses: number;
  taxAndStatutory: number;
  debtService: number;
  capexOutlays: number;
  totalOutflows: number;
  // Bottom line
  netCashFlow: number;
  endingCash: number;
  minCashThreshold: number;
  isBelowThreshold: boolean;
  runwayWeeks: number;
}

export interface MonthlyCashForecastItem {
  monthIndex: number;
  monthLabel: string;
  beginningCash: number;
  operatingCashInflows: number;
  operatingCashOutflows: number;
  netOperatingCash: number;
  capexAndInvesting: number;
  financingAndDebt: number;
  taxPayments: number;
  netCashFlow: number;
  endingCash: number;
  burnRate: number;
  cashRunwayMonths: number;
  isNegative: boolean;
}

export interface SensitivityMatrixCell {
  rowValue: number; // e.g. Revenue growth % (+10%)
  colValue: number; // e.g. OpEx change % (+5%)
  revenue: number;
  grossProfit: number;
  cogs: number;
  opex: number;
  ebitda: number;
  netIncome: number;
  netMarginPercent: number;
  endingCash: number;
  isBaseline: boolean;
  isActiveSelection: boolean;
}

export interface SensitivityMatrixData {
  rowAxisName: string;
  colAxisName: string;
  rowUnit: string;
  colUnit: string;
  rowValues: number[];
  colValues: number[];
  grid: SensitivityMatrixCell[][];
  minNetIncome: number;
  maxNetIncome: number;
  baseNetIncome: number;
}

