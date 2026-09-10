export type RiskLevel = 'Low' | 'Moderate' | 'Significant';
export type InherentRisk = 'Low' | 'Medium' | 'Moderate' | 'Significant' | '';
export type MatrixScale = 'Low' | 'Medium' | 'Moderate' | 'High';

export type Assertion =
  | 'Existence'
  | 'Completeness'
  | 'Accuracy'
  | 'Valuation'
  | 'Rights & Obligations'
  | 'Cutoff'
  | 'Classification'
  | 'Existence / Occurrence'
  | 'Valuation / Allocation'
  | 'Presentation & Disclosure';

export type AssertionType = Assertion;

export interface AcceptanceChecklistItem {
  id: string;
  item: string;
  standardRef: string;
  status: 'Yes' | 'No' | 'N.A.';
  rationale: string;
}

export interface ControlEnvironmentFactor {
  id: string;
  factorName: string;
  description: string;
  rating: 'Effective' | 'Partially Effective' | 'Ineffective';
  notes: string;
}

export interface ITSystem {
  id: string;
  systemName: string;
  name?: string;
  purpose: string;
  criticality: 'High' | 'Medium' | 'Low';
  hosting: string;
  observations: string;
  vendor?: string;
  type?: string;
  userCount?: number;
  businessProcess?: string;
  auditorReliance?: string;
}

export interface BusinessProcess {
  id: string;
  processName: string;
  name?: string;
  owner: string;
  processOwner?: string;
  nature: 'Significant' | 'Routine';
  classification?: string;
  itSystemUsed: string;
  itSystem?: string;
  notes: string;
  walkthroughScoped?: boolean;
  assertions?: Assertion[];
}

export interface WalkthroughItem {
  id: string;
  processId: string;
  processName: string;
  performed: boolean;
  date: string;
  performedBy: string;
  sampleDocRef: string;
  observations: string;
  controlGaps: string;
  conclusion: 'Design and implementation verified' | 'Control gaps identified' | 'Pending walkthrough';
  datePerformed?: string;
  auditor?: string;
  sampleDocumentRef?: string;
  observedControls?: string;
  processCycle?: string;
  keyControlObjective?: string;
  identifiedGaps?: string;
  evaluationSummary?: string;
}

export type ProcessWalkthrough = WalkthroughItem;

export interface FSLineItemRisk {
  id: string;
  lineItemName: string;
  lineItem?: string;
  scheduleIIICategory: string;
  category?: string;
  assertions: Assertion[];
  relevantAssertions?: Assertion[];
  inherentRisk: InherentRisk | RiskLevel;
  quantitativeSignificance: string;
  rationale: string;
}

export interface AdditionalFraudRisk {
  id: string;
  lineItemName?: string;
  fraudType?: string;
  identified?: boolean;
  rationale?: string;
  plannedResponse?: string;
  riskDescription?: string;
  fraudTriangleCategory?: string;
  impactedAccounts?: string;
  plannedProcedures?: string;
}

export type FraudRiskItem = AdditionalFraudRisk;

export interface FraudRiskAssessment {
  revenuePresumption: {
    rebutted: boolean;
    rationale: string;
    plannedResponse: string;
  } | string;
  revenueRationale?: string;
  revenueRebuttalJustification?: string;
  managementOverride: {
    rationale: string;
    plannedResponse: string;
  } | string;
  managementOverrideProcedures?: string;
  additionalRisks: AdditionalFraudRisk[];
  identifiedRisks?: AdditionalFraudRisk[];
  journalEntryTestingNotes?: string;
  accountingEstimatesBiasNotes?: string;
  unusualTransactionsNotes?: string;
}

export interface ControlRiskItem {
  id: string;
  lineItemOrRisk?: string;
  lineItemOrProcess?: string;
  inherentRisk?: InherentRisk | RiskLevel;
  controlDesign?: 'Effective' | 'Partially Effective' | 'Ineffective' | string;
  controlOperatingEffectiveness?: 'Operating Effectively' | 'Deviations Observed' | 'Not Tested / Substantive Only' | string;
  controlsIdentified?: string;
  associatedControls?: string;
  probability: MatrixScale;
  magnitude: MatrixScale;
  suggestedRating: RiskLevel;
  finalRating: RiskLevel;
  isOverridden: boolean;
  overrideRationale: string;
  isSignificantRisk?: boolean;
}

export type ControlRiskEntry = ControlRiskItem;
export type ProbabilityLevel = MatrixScale;
export type MagnitudeLevel = MatrixScale;

export type BenchmarkBasis =
  | 'Profit before Tax'
  | 'Profit Before Tax (PBT) from Continuing Operations'
  | 'Revenue from Operations'
  | 'Total Revenue / Turnover'
  | 'Net Assets (Equity)'
  | 'Total Equity / Net Assets'
  | 'Gross Profit'
  | 'Total Assets';

export type MaterialityBenchmark = BenchmarkBasis;

export interface SpecificMaterialityItem {
  id: string;
  areaOrAccount: string;
  materialityAmount: number;
  rationale: string;
}

export interface MaterialityConfig {
  benchmarkBasis: BenchmarkBasis;
  benchmarkAmount: number; // in INR
  omPercent: number; // Overall Materiality %
  pmPercent: number; // Performance Materiality % of OM
  ctPercent?: number; // Clearly Trivial % of OM
  clearlyTrivialPercent?: number; // Clearly Trivial % of OM
  rationale: string;
  specificMateriality?: SpecificMaterialityItem[];
}

export interface ComputedMateriality {
  overallMateriality: number;
  performanceMateriality: number;
  clearlyTrivialThreshold: number;
}

export interface AuditStrategyItem {
  id: string;
  riskId?: string;
  riskDescription?: string;
  lineItem?: string;
  lineItemOrRisk?: string;
  riskLevel?: RiskLevel;
  assessedRiskLevel?: RiskLevel;
  testOfControls: boolean;
  testOfDetails: boolean;
  analyticalProcedures: boolean;
  extent: 'Limited' | 'Moderate' | 'Extensive' | string;
  timing: 'Interim' | 'Year-End' | 'Continuous' | string;
  proceduresNotes: string;
}

export type AuditStrategyResponse = AuditStrategyItem;

export interface MemoSection {
  id: string;
  title: string;
  content: string;
  autoTemplate: string;
}

export interface PlanningMemo {
  sections?: MemoSection[];
  executiveSummary?: string;
  scopeAndObjectives?: string;
  entityAndRiskAssessment?: string;
  materialityDetermination?: string;
  significantRisksAndFraud?: string;
  auditApproachAndStaffing?: string;
  [key: string]: any;
}

export interface ReviewNote {
  id: string;
  raisedBy?: string;
  date?: string;
  stageNumber?: number;
  stageRef?: string;
  noteText?: string;
  query?: string;
  status: 'Open' | 'Cleared';
  preparerResponse?: string;
  response?: string;
}

export type ReviewNoteItem = ReviewNote;

export type ReviewStatus = 'Draft' | 'Pending Review' | 'Approved' | 'Approved with Conditions' | 'Returned for Revision';

export interface SignOffReviewData {
  preparer: {
    name: string;
    designation?: string;
    date: string;
    declared: boolean;
  };
  reviewer: {
    name: string;
    designation?: string;
    date: string;
    conclusion: 'Planning Approved' | 'Approved with Conditions' | 'Returned for Revision' | 'Pending Review';
    concludingRemarks?: string;
    comments?: string;
  };
  reviewNotes: ReviewNote[];
}

export interface EngagementData {
  id: string;
  clientName: string;
  cin: string;
  pan: string;
  financialYear: string;
  auditPeriod: string;
  registeredAddress: string;
  engagementPartner: string;
  auditSenior: string;
  precedingAuditor: string;
  dateOfAcceptance: string;
  auditType: string;
  acceptanceChecklist: AcceptanceChecklistItem[];
  acceptanceConclusion: 'Accepted' | 'Accepted with Conditions' | 'Declined';
  acceptanceNotes: string;
  entityUnderstanding: {
    natureOfBusiness: string;
    ownershipAndGovernance: string;
    objectivesAndStrategies: string;
    industryFactors: string;
    regulatoryFactors: string;
    otherExternalFactors: string;
    performanceMeasures: string;
    entityLevelRisks: string;
  };
  controlEnvironment: {
    factors: ControlEnvironmentFactor[];
    overallConclusion: 'Effective' | 'Partially Deficient' | 'Ineffective / High Risk';
    overallNotes: string;
  };
  itSystems: ITSystem[];
  informationSystems?: {
    generalReliance: string;
    systems: ITSystem[];
    itgcNotes: string;
  };
  itRelianceNotes: string;
  itgcObservations: string;
  businessProcesses: BusinessProcess[];
  walkthroughs: WalkthroughItem[];
  fsLineItemRisks: FSLineItemRisk[];
  fraudRisks: FraudRiskAssessment;
  fraudRisk?: any;
  controlRiskRegister: ControlRiskItem[];
  materiality: MaterialityConfig;
  auditStrategy: AuditStrategyItem[];
  planningMemo: PlanningMemo;
  signOffReview: SignOffReviewData;
  trialBalance?: TrialBalanceData;
}

export type TBCategory = 'Assets' | 'Liabilities' | 'Equity' | 'Revenue' | 'Expenses';

export interface TrialBalanceItem {
  id: string;
  accountCode: string;
  accountName: string;
  scheduleIIIGroup: string;
  category: TBCategory;
  currentYearDebit: number;
  currentYearCredit: number;
  currentYearNet: number;
  priorYearBalance?: number;
  varianceAmount?: number;
  variancePercent?: number;
  materialityFlag?: 'Material (>OM)' | 'Significant (>PM)' | 'Clearly Trivial' | 'Normal';
  notes?: string;
}

export interface TrialBalanceSummary {
  totalDebit: number;
  totalCredit: number;
  isBalanced: boolean;
  difference: number;
  totalRevenue: number;
  totalExpenses: number;
  profitBeforeTax: number;
  totalAssets: number;
  totalLiabilities: number;
  totalEquity: number;
  totalBorrowings: number;
  itemCount: number;
}

export interface TrialBalanceData {
  importedAt?: string;
  fileName?: string;
  items: TrialBalanceItem[];
  summary: TrialBalanceSummary;
}

export interface StageProgress {
  stageNumber: number;
  title: string;
  shortTitle: string;
  saRef: string;
  doneCount: number;
  totalCount: number;
  percent: number;
}
