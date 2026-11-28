export type ThemeId =
  | 'navy-gold'
  | 'corporate-blue'
  | 'midnight-dark'
  | 'emerald-finance'
  | 'graphite-copper'
  | 'minimal-pro';

export type LanguageCode = 'en' | 'ar';
export type CurrencyCode = 'OMR' | 'AED' | 'SAR' | 'USD';
export type ReportingBasis = 'Monthly' | 'Quarterly' | 'Annual' | 'YTD' | 'ITD';
export type FontSizeScale = 'compact' | 'standard' | 'large';

export type ModuleId =
  | 'executive'
  | 'financial-mis'
  | 'cashflow-treasury'
  | 'project-performance'
  | 'sales-inventory'
  | 'collections'
  | 'construction'
  | 'budget-cost'
  | 'contracts'
  | 'financing'
  | 'feasibility'
  | 'risk-compliance'
  | 'handover-warranty'
  | 'rental-properties'
  | 'ai-analyst'
  | 'data-upload'
  | 'workflow-controls'
  | 'reports-exports'
  | 'settings-admin';

export type WorkflowStage =
  | 'Open'
  | 'Uploaded'
  | 'Validated'
  | 'KpiCalculated'
  | 'ExceptionReview'
  | 'Approved'
  | 'Published'
  | 'Locked';

export type UserRole = 'CFO_Admin' | 'Finance_Controller' | 'Project_Director' | 'Board_Viewer';

export interface Company {
  id: string;
  code: string;
  name: string;
  nameAr: string;
  type: 'Parent' | 'SPV';
  ownershipPct: number;
  baseCurrency: CurrencyCode;
  crNumber: string;
  vatNumber: string;
  fiscalYearStartMonth: number;
}

export type ProjectCategory = 'Residential' | 'Commercial' | 'Mixed-Use' | 'Master Development';
export type RevenueRecognitionMethod = 'IFRS15_OverTime_PoC' | 'IFRS15_PointInTime_Handover' | 'IAS40_Rental';

export interface Project {
  id: string;
  companyId: string;
  code: string;
  name: string;
  nameAr: string;
  category: ProjectCategory;
  location: string;
  revenueMethod: RevenueRecognitionMethod;
  phases: number;
  buildings: number;
  totalUnits: number;
  totalSellableSqm: number;
  landAreaSqm: number;
  startDate: string; // YYYY-MM
  plannedCompletion: string; // YYYY-MM
  forecastCompletion: string; // YYYY-MM
  escrowAccountNo: string;
  escrowBank: string;
  status: 'Active' | 'Handover' | 'Completed';
  hasSupportingSchedule: boolean;
}

export type UnitStatus = 'Sold' | 'Booked' | 'Available' | 'Cancelled' | 'Handed Over';

export interface UnitRecord {
  id: string;
  projectId: string;
  companyId: string;
  unitCode: string;
  phase: string;
  building: string;
  floor: number;
  unitType: 'Apartment' | 'Villa' | 'Townhouse' | 'Office' | 'Retail' | 'Plot';
  areaSqm: number;
  listPriceOMR: number;
  discountOMR: number;
  contractedPriceOMR: number;
  invoicedOMR: number;
  collectedOMR: number;
  overdueOMR: number;
  status: UnitStatus;
  saleMonth: string | null; // YYYY-MM
  customerName: string | null;
  handoverStatus: 'Pending' | 'Snagging' | 'Completed' | 'N/A';
  dlpExpiryMonth: string | null;
}

export type AccountClass =
  | 'Revenue'
  | 'COGS'
  | 'OpEx'
  | 'FinanceCost'
  | 'Tax'
  | 'CashUnrestricted'
  | 'CashEscrow'
  | 'Receivables'
  | 'InventoryWIP'
  | 'ContractAsset'
  | 'InvestmentProperty'
  | 'FixedAssets'
  | 'Payables'
  | 'CustomerAdvances'
  | 'RetentionPayable'
  | 'Debt'
  | 'Equity'
  | 'Intercompany';

export interface TrialBalanceRow {
  id: string;
  companyId: string;
  projectId: string | null;
  period: string; // YYYY-MM
  accountCode: string;
  accountName: string;
  costCentre: string;
  department: string;
  accountClass: AccountClass | 'Unmapped';
  openingDebit: number;
  openingCredit: number;
  periodDebit: number;
  periodCredit: number;
  closingDebit: number;
  closingCredit: number;
  isIntercompany: boolean;
  eliminatedWithCompanyId?: string | null;
}

export interface GlMappingRule {
  id: string;
  accountCode: string;
  accountNamePattern: string;
  targetClass: AccountClass;
  defaultProjectId: string | null;
  allocationRule: string;
  approvedBy: string;
  updatedAt: string;
}

export interface ProjectBudgetLine {
  projectId: string;
  costCategory: 'Land' | 'Infrastructure' | 'Substructure & Superstructure' | 'MEP & Finishes' | 'Consultancy & Design' | 'Marketing & Sales' | 'Capitalized Interest' | 'Contingency';
  originalBudgetOMR: number;
  revisedBudgetOMR: number;
  actualCostOMR: number;
  accrualsOMR: number;
  committedContractsOMR: number; // Remaining uncertified value on signed contracts (excludes actual+accruals)
  approvedVariationsOMR: number;
  pendingVariationsOMR: number;
  estimatedCostToCompleteOMR: number; // Additional ETC beyond commitments
}

export interface ContractorRecord {
  id: string;
  projectId: string;
  contractorName: string;
  packageTitle: string;
  originalContractOMR: number;
  approvedVariationsOMR: number;
  pendingClaimsOMR: number;
  certifiedToDateOMR: number;
  paidToDateOMR: number;
  advanceUnrecoveredOMR: number;
  retentionHeldOMR: number;
  performanceBondOMR: number;
  status: 'Active' | 'Near Completion' | 'Disputed' | 'Closed';
}

export interface ConstructionProgressPoint {
  projectId: string;
  period: string; // YYYY-MM
  plannedPhysicalPct: number;
  actualPhysicalPct: number;
  certifiedProgressPct: number;
  financialProgressPct: number;
  plannedValueOMR: number; // PV
  earnedValueOMR: number;   // EV
  actualCostOMR: number;    // AC
}

export interface FinancingFacility {
  id: string;
  companyId: string;
  projectId: string | null;
  lenderName: string;
  facilityType: 'Term Loan' | 'Construction Murabaha' | 'Revolving Credit' | 'Sukuk Tranche';
  facilityLimitOMR: number;
  drawnAmountOMR: number;
  interestRatePct: number;
  maturityDate: string; // YYYY-MM
  minDscrCovenant: number;
  maxLtvCovenantPct: number;
  maxLtcCovenantPct: number;
  collateralValueOMR: number;
  totalProjectCostOMR: number;
  ebitdaAnnualizedOMR: number;
  annualDebtServiceOMR: number;
}

export interface RiskItem {
  id: string;
  projectId: string | null;
  companyId: string;
  category: 'Financial' | 'Construction' | 'Commercial' | 'Liquidity' | 'Contractual' | 'Regulatory' | 'Operational';
  title: string;
  likelihood: 1 | 2 | 3 | 4 | 5;
  impact: 1 | 2 | 3 | 4 | 5;
  financialExposureOMR: number;
  mitigationOwner: string;
  dueDate: string;
  status: 'Open' | 'Mitigating' | 'Closed' | 'Escalated';
}

export interface HandoverWarrantyRecord {
  id: string;
  projectId: string;
  totalUnitsForHandover: number;
  completionCertificateStatus: 'Issued' | 'Partial' | 'In Progress' | 'Pending Municipality';
  unitsHandedOver: number;
  unitsInSnagging: number;
  openWarrantyClaims: number;
  resolvedWarrantyClaims: number;
  dlpReserveOMR: number;
  outstandingObligationsOMR: number;
}

export interface RentalLeaseRecord {
  id: string;
  projectId: string;
  propertyName: string;
  leasableSqm: number;
  occupiedSqm: number;
  annualPassingRentOMR: number;
  operatingExpensesOMR: number;
  propertyFairValueOMR: number;
  tenantArrearsOMR: number;
  expiringWithin12MonthsPct: number;
}

export interface AccountingPolicyConfig {
  ifrs15OverTimeThresholdPct: number; // e.g., enforceable right to payment + PoC threshold
  ifrs9EclStage1Pct: number;
  ifrs9EclStage2Pct: number;
  ifrs9EclStage3Pct: number;
  ias2NrvHaircutThresholdPct: number;
  ias23CapitalizeBorrowingCosts: boolean;
  ias40FairValueModel: boolean;
  omanVatRatePct: number; // 5%
  omanCorporateTaxRatePct: number; // 15%
  omanWithholdingTaxPct: number; // 10%
  materialityThresholdOMR: number; // e.g. 500.000 OMR
}

export interface ManagementAdjustment {
  id: string;
  period: string;
  companyId: string;
  projectId: string | null;
  description: string;
  debitAccountClass: AccountClass;
  creditAccountClass: AccountClass;
  amountOMR: number;
  preparedBy: string;
  approvedBy: string | null;
  status: 'Pending Approval' | 'Approved' | 'Rejected';
  createdAt: string;
}

export interface PeriodWorkflowState {
  period: string; // YYYY-MM
  stage: WorkflowStage;
  tbUploaded: boolean;
  schedulesCompleted: number;
  schedulesTotal: number;
  reconciled: boolean;
  openExceptions: number;
  preparedBy: string;
  approvedBy: string | null;
  lockedAt: string | null;
  departmentalComments: { department: string; author: string; comment: string; timestamp: string }[];
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  actor: string;
  role: UserRole;
  action: string;
  entity: string;
  details: string;
}

export interface ScenarioParameters {
  name: string;
  sellingPriceDeltaPct: number; // -25 to +25
  salesVelocityDeltaPct: number; // -40 to +40
  collectionDelayMonths: number; // 0 to 12
  cancellationRatePct: number; // 0 to 20
  constructionCostDeltaPct: number; // -15 to +30
  projectDelayMonths: number; // 0 to 18
  interestRateDeltaBps: number; // -200 to +400
  landAndClaimsDeltaOMR: number; // -2000000 to +5000000
  phasingShiftMonths: number; // 0 to 12
  fundingCapOMR: number | null; // null = uncapped
}

export interface TraceableKpi {
  id: string;
  label: string;
  labelAr: string;
  value: number | null;
  formatted: string;
  unit: 'OMR' | 'Pct' | 'Ratio' | 'Count' | 'Months' | 'Sqm';
  formula: string;
  source: string;
  period: string;
  assumptions: string;
  rag: 'green' | 'amber' | 'red' | 'neutral';
}

export interface LicenseState {
  deviceId: string;
  edition: 'Trial' | 'Permanent' | 'Subscription';
  status: 'Active' | 'Expired';
  trialStartedAt: string;
  expiresAt: string | null;
  licensedTo: string;
  signatureHash: string;
}

export interface BackupMetadata {
  id: string;
  filename: string;
  createdAt: string;
  sizeBytes: number;
  type: 'Automatic' | 'Manual';
  checksum: string;
}

export interface MisDataset {
  companies: Company[];
  projects: Project[];
  units: UnitRecord[];
  periods: string[]; // 24 months YYYY-MM
  trialBalance: TrialBalanceRow[];
  glMappings: GlMappingRule[];
  budgets: ProjectBudgetLine[];
  contractors: ContractorRecord[];
  constructionLogs: ConstructionProgressPoint[];
  facilities: FinancingFacility[];
  risks: RiskItem[];
  handovers: HandoverWarrantyRecord[];
  rentals: RentalLeaseRecord[];
  policies: AccountingPolicyConfig;
  adjustments: ManagementAdjustment[];
  workflows: PeriodWorkflowState[];
  auditLogs: AuditLogEntry[];
  license: LicenseState;
  backups: BackupMetadata[];
}
