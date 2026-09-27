/**
 * DischargeStatus: Clinical discharge status of a patient encounter.
 * Note: 'Pending Financial Review' indicates the encounter's billing records are awaiting
 * departmental verification — this is a FINANCIAL flag only and does not imply that
 * the application has clinical authority over patient discharge.
 */
export type DischargeStatus = 'Discharged' | 'Admitted' | 'Pending Financial Review' | 'AMA';

export interface Encounter {
  Encounter_ID: string;
  Admission_Date: string;
  Discharge_Date: string | null;
  Department: string;
  Ward: string;
  Bed_Type: string;
  Payer_Type: string;
  Discharge_Status: DischargeStatus;
}

export interface Service {
  Service_ID: string;
  Encounter_ID: string;
  Service_DateTime: string;
  Revenue_Centre: string;
  Service_Code: string;
  Description: string;
  Quantity: number;
  Expected_Amount: number;
}

export type BillStatus = 'Provisional' | 'Final' | 'Cancelled';

export interface Billing {
  Bill_ID: string;
  Encounter_ID: string;
  Service_ID: string;
  Bill_DateTime: string;
  Bill_Date?: string;
  Billed_Quantity: number;
  Billed_Amount: number;
  Discount: number;
  Bill_Status: BillStatus;
}

export type ClaimStatus =
  | 'Submitted'
  | 'Approved'
  | 'Partially Approved'
  | 'Rejected'
  | 'Pending Info'
  | 'Under Query'
  | 'In Adjudication';

export interface Claim {
  Claim_ID: string;
  Encounter_ID: string;
  Payer?: string;
  Claim_Amount: number;
  Approved_Amount: number;
  Rejected_Amount: number;
  Claim_Status: ClaimStatus;
  Submission_Date: string;
  Approval_Date: string | null;
}

export type PaymentMode = 'Cash' | 'Credit Card' | 'Bank Transfer' | 'NEFT/RTGS' | 'Cheque' | 'TPA Settlement';

export interface Collection {
  Receipt_ID: string;
  Encounter_ID: string;
  Receipt_Date: string;
  Amount: number;
  Payment_Mode: PaymentMode;
}

export type ControlId =
  | 'C01' // Unbilled Service
  | 'C02' // Quantity Mismatch
  | 'C03' // Amount Mismatch
  | 'C04' // Post-Billing Service
  | 'C05' // Missing/Pending Final Bill
  | 'C06' // TPA Shortfall
  | 'C07' // Collection Outstanding
  | 'C08'; // Unusual Discount

export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type ExceptionStatus = 'OPEN' | 'UNDER_REVIEW' | 'RESOLVED' | 'ACCEPTED';

export interface FinancialException {
  Exception_ID: string;
  Run_ID: string;
  Encounter_ID: string;
  Control_ID: ControlId;
  Revenue_Centre: string;
  Description: string;
  Exposure_Amount: number;
  Severity: Severity;
  Status: ExceptionStatus;
  Created_Date: string;
  Assigned_To: string;
  Resolution: string;
  Resolved_Date: string | null;
}

export interface ControlRuleConfig {
  amountMismatchTolerancePercent: number; // default 5%
  tpaShortfallTolerancePercent: number; // default 5%
  collectionDueDays: number; // default 30 days
  unusualDiscountPercent: number; // default 10%
  criticalExposureThreshold: number; // default $5000
  highExposureThreshold: number; // default $1500
}

export interface AuditTrailRun {
  Run_ID: string;
  Run_Date_Time: string;
  Data_Period: string;
  Records_Processed: number;
  Controls_Executed: number;
  Exceptions_Generated: number;
  User: string;
}

export type UserRole = 'CFO' | 'Finance/Billing Manager' | 'Department Manager' | 'Auditor';

export type HospitalDepartment =
  | 'Laboratory'
  | 'Pharmacy'
  | 'Radiology'
  | 'OT/Surgery'
  | 'ICU'
  | 'Operations'
  | 'Stores'
  | 'Finance/Admin';

export interface UserSession {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  department?: HospitalDepartment;
  avatarInitials: string;
  lastLogin: string;
}

export type DepartmentClearanceStatus =
  | 'PENDING_VERIFICATION'
  | 'VERIFIED'
  | 'DISPUTED'
  | 'CORRECTION_REQUIRED'
  | 'UNABLE_TO_VERIFY';

export interface DepartmentClearanceRecord {
  id: string;
  encounterId: string;
  department: HospitalDepartment;
  revenueCentre: string;
  totalServicesCount: number;
  totalServiceAmount: number;
  totalBilledAmount: number;
  unbilledExposure: number;
  varianceExposure: number;
  status: DepartmentClearanceStatus;
  reviewedBy?: string;
  reviewedAt?: string;
  comment?: string;
  evidenceRef?: string;
  exceptionCount: number;
}

export interface TariffMasterItem {
  Service_Code: string;
  Service_Description: string;
  Revenue_Centre: string;
  Standard_Tariff: number;
  Effective_From: string;
  Effective_To: string;
  Payer: string;
  Payer_Tariff: number;
}

export type TariffVarianceType =
  | 'STANDARD_VARIANCE'
  | 'PAYER_TARIFF_VARIANCE'
  | 'UNDERBILLING'
  | 'OVERBILLING'
  | 'EXPIRED_TARIFF'
  | 'MISSING_TARIFF';

export interface TariffDeviationItem {
  id: string;
  serviceId: string;
  encounterId: string;
  serviceCode: string;
  serviceDescription: string;
  revenueCentre: string;
  payer: string;
  expectedTariff: number;
  applicableTariff: number;
  actualBilled: number;
  variance: number;
  variancePercent: number;
  varianceType: TariffVarianceType;
  effectiveFrom: string;
  effectiveTo: string;
  status: 'PENDING_INVESTIGATION' | 'VERIFIED_ACCEPTED' | 'ADJUSTMENT_REQUIRED';
  investigatedBy?: string;
  notes?: string;
}

export interface BudgetRecord {
  Month: string; // e.g. '2026-09'
  Department: HospitalDepartment;
  Revenue_Budget: number;
  Expense_Budget: number;
}

export interface BudgetVarianceSummary {
  month: string;
  department: HospitalDepartment | string;
  revenueBudget: number;
  revenueActual: number;
  revenueVariance: number;
  revenueVariancePercent: number;
  expenseBudget: number;
  expenseActual: number | null;
  expenseVariance: number | null;
  expenseVariancePercent: number | null;
  isSignificant: boolean;
  ytdRevenueBudget: number;
  ytdRevenueActual: number;
  ytdRevenueVariance: number;
}

export type AuditActionType =
  | 'LOGIN'
  | 'LOGOUT'
  | 'DATA_IMPORT'
  | 'CONTROL_RUN'
  | 'THRESHOLD_CHANGE'
  | 'EXCEPTION_CREATION'
  | 'EXCEPTION_ASSIGNMENT'
  | 'DEPARTMENT_VERIFICATION'
  | 'DEPARTMENT_DISPUTE'
  | 'FINANCE_RESOLUTION'
  | 'EXCEPTION_ACCEPTANCE'
  | 'REPORT_GENERATION'
  | 'CFO_PACK_GENERATION'
  | 'TARIFF_INVESTIGATION'
  | 'CFO_REVIEW_GENERATED'
  | 'CFO_REVIEW_APPROVED';

export interface ComprehensiveAuditLog {
  id: string;
  timestamp: string;
  user: string;
  role: UserRole;
  action: AuditActionType;
  entityType: 'Encounter' | 'Exception' | 'DepartmentClearance' | 'Tariff' | 'Config' | 'Dataset' | 'Report';
  entityId: string;
  details: string;
  previousValue?: string;
  newValue?: string;
}

export interface DashboardMetrics {
  todaysDischarges: number;
  grossBilling: number;
  totalExpectedAmount: number;
  potentialFinancialExposure: number;
  openExceptionsCount: number;
  tpaPendingAmount: number;
  outstandingCollections: number;
  /** Billing Capture Rate: grossBilling / totalExpectedAmount * 100. Computed once in controlEngine. */
  billingCaptureRate: number;
  /** Gross billed amount BEFORE applying discounts (Billed_Amount + Discount). */
  grossBilledPreDiscount: number;
  criticalExceptionsCount: number;
  highExceptionsCount: number;
  mediumExceptionsCount: number;
  lowExceptionsCount: number;
  exposureByRevenueCentre: { name: string; amount: number; count: number }[];
  exceptionsByControl: { controlId: ControlId; title: string; count: number; exposure: number }[];
  exceptionsByDepartment: { department: string; count: number; exposure: number }[];
  priorityExceptions: FinancialException[];
  funnel: {
    captured: number;
    billed: number;
    claimed: number;
    approved: number;
    collected: number;
  };
}

export interface DischargeMonitorRow {
  Encounter_ID: string;
  Department: string;
  Ward: string;
  Payer_Type: string;
  Discharge_Status: DischargeStatus;
  Admission_Date: string;
  Discharge_Date: string | null;
  Billed_Amount: number;
  Expected_Amount: number;
  Billing_Completeness: 'Complete' | 'Provisional Only' | 'Unbilled Items' | 'No Billing';
  TPA_Status: 'Approved' | 'Partially Approved' | 'Pending' | 'Rejected' | 'Not Applicable';
  Collection_Status: 'Fully Collected' | 'Partially Collected' | 'Uncollected' | 'Overdue >30d';
  Exception_Count: number;
  Highest_Severity: Severity | 'NONE';
  Total_Exposure: number;
}

export interface ControlDefinition {
  id: ControlId;
  name: string;
  subtitle: string;
  description: string;
  exposureCalculation: string;
}

export const CONTROL_DEFINITIONS: Record<ControlId, ControlDefinition> = {
  C01: {
    id: 'C01',
    name: 'Unbilled Service',
    subtitle: 'Service captured without billing record',
    description: 'A clinical or diagnostic service exists in services log but has no corresponding billing entry.',
    exposureCalculation: 'Expected Amount of the unbilled service',
  },
  C02: {
    id: 'C02',
    name: 'Quantity Mismatch',
    subtitle: 'Service quantity differs from billed quantity',
    description: 'Captured service quantity does not match the quantity billed on invoice.',
    exposureCalculation: '(Service Qty - Billed Qty) × Unit Expected Amount',
  },
  C03: {
    id: 'C03',
    name: 'Amount Mismatch',
    subtitle: 'Billed amount deviates from expected tariff',
    description: 'Billed amount differs materially from expected service tariff beyond configured tolerance.',
    exposureCalculation: '|Expected Amount - Billed Amount|',
  },
  C04: {
    id: 'C04',
    name: 'Post-Billing Service',
    subtitle: 'Service entered after final bill generated',
    description: 'Service timestamp is recorded after the final bill was closed, causing revenue leakage at discharge.',
    exposureCalculation: 'Expected Amount of the late-entered service',
  },
  C05: {
    id: 'C05',
    name: 'Missing / Pending Final Bill',
    subtitle: 'Discharged encounter without final bill closure',
    description: 'Encounter marked as Discharged has no final billing record or remains in Provisional status.',
    exposureCalculation: 'Relevant unbilled services + provisional amount pending finalization',
  },
  C06: {
    id: 'C06',
    name: 'TPA Shortfall',
    subtitle: 'Insurance approved amount below claim request',
    description: 'Third-party administrator (TPA) / insurer approved amount falls short of claimed amount beyond tolerance.',
    exposureCalculation: 'Claim Amount - Approved Amount (Disallowed portion)',
  },
  C07: {
    id: 'C07',
    name: 'Collection Outstanding',
    subtitle: 'Uncollected balance beyond 30 days',
    description: 'Discharged patient balance remains uncollected past 30 days from discharge date.',
    exposureCalculation: 'Total Billed Amount - Total Receipts Collected',
  },
  C08: {
    id: 'C08',
    name: 'Unusual Discount',
    subtitle: 'Discounts exceeding authorized threshold',
    description: 'Discounts applied on billing lines exceed the authorized threshold (default 10%).',
    exposureCalculation: 'Total discount amount applied',
  },
};

export type CfoReviewStatus = 'DRAFT' | 'APPROVED' | 'REJECTED';
export type CfoReviewNarrativeSource = 'ai_gemini' | 'deterministic_fallback';

// ---------------------------------------------------------------------------
// Multi-Stage Orchestrator Types
// ---------------------------------------------------------------------------

/** The canonical identifier for each specialist agent stage */
export type AgentStageId =
  | 'CONTROL_POSITION'
  | 'REVENUE_REVIEW'
  | 'EXCEPTION_REVIEW'
  | 'RECEIVABLES_REVIEW'
  | 'TPA_REVIEW'
  | 'DEPARTMENT_REVIEW'
  | 'TARIFF_REVIEW'
  | 'BUDGET_REVIEW'
  | 'FINANCIAL_SYNTHESIS'
  | 'CFO_BRIEFING';

/** Lifecycle state of a single specialist stage */
export type AgentStageStatus =
  | 'PENDING'    // Not yet started
  | 'RUNNING'    // Currently executing
  | 'COMPLETED'  // Finished with findings or no-material-finding
  | 'SKIPPED'    // Intentionally skipped
  | 'NO_DATA'    // No data available for this stage
  | 'ERROR';     // Stage encountered an execution error

/** Per-stage execution record — the "log line" for each specialist stage */
export interface StageExecutionRecord {
  stageId: AgentStageId;
  stageName: string;
  purpose: string;
  status: AgentStageStatus;
  toolsUsed: string[];
  recordsProcessed: number;
  metricsReturned: number;
  /** Human-readable summary of what the stage found or why it was skipped/no-data */
  finding: string;
  /** ISO timestamp when the stage completed */
  completedAt: string;
  /** Evidence IDs referenced by this stage */
  evidenceIds: string[];
  /** If status=ERROR, the error message */
  errorMessage?: string;
}

/** Progress event emitted during orchestrator execution */
export interface CfoReviewProgress {
  /** Current stage number (1-based) */
  step: number;
  /** Total stages */
  totalSteps: number;
  /** Stage label for display */
  label: string;
  /** Whether this stage is complete */
  isComplete: boolean;
  /** The current stage ID */
  stageId?: AgentStageId;
  /** The current stage status */
  stageStatus?: AgentStageStatus;
  /** All stage records collected so far (for live UI updates) */
  stageLog?: StageExecutionRecord[];
}

export interface CfoReviewEvidenceReference {
  type: 'EXCEPTION' | 'ENCOUNTER' | 'CLAIM' | 'SERVICE' | 'CONTROL' | 'METRIC';
  id: string;
  label: string;
  detail?: string;
  /** Which stage produced this reference */
  stageId?: AgentStageId;
}

export interface CfoFinancialReviewBrief {
  briefId: string;
  runId: string;
  generatedAt: string;
  generatedBy: string;
  userRole: UserRole;
  status: CfoReviewStatus;
  approvedAt?: string | null;
  approvedBy?: string | null;
  approvalNotes?: string;
  narrativeSource: CfoReviewNarrativeSource;
  toolsUsed: string[];
  markdownContent: string;
  evidenceReferences: CfoReviewEvidenceReference[];
  /** Structured execution log for every specialist stage */
  stageExecutionLog: StageExecutionRecord[];
  groundedFigures: {
    grossBilling: number;
    totalExpectedAmount: number;
    billingCaptureRate: number;
    potentialExposure: number;
    openExceptionsCount: number;
    criticalExceptionsCount: number;
    highExceptionsCount: number;
    totalAR: number;
    overdueAR: number;
    collectionRate: number;
    tpaPendingAmount: number;
    tpaApprovedAmount: number;
    tpaShortfallAmount: number;
    clearancePercent: number;
    budgetAvailable: boolean;
    budgetRevenueVariance?: number | null;
  };
}
