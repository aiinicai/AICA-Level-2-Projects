export type AssetCategory =
  | 'Plant & Machinery'
  | 'Buildings & Civil Structures'
  | 'IT Hardware & Servers'
  | 'Office & Lab Equipment'
  | 'Vehicles'
  | 'Tooling & Moulds'
  | 'Intangibles (Software)';

export type PlantLocation =
  | 'Pune Plant - Chakan'
  | 'Chennai Automotive Hub'
  | 'Manesar Tooling Hub'
  | 'Sanand EV Plant'
  | 'Bengaluru HQ & Tech Center';

export type RiskLevel = 'Critical' | 'High' | 'Medium' | 'Low' | 'Clean';

export type VerificationStatus =
  | 'Verified'
  | 'Missing'
  | 'Wrong Location'
  | 'Suspected Ghost'
  | 'Pending Verification'
  | 'Requires Inspection';

export type AssetOperationalStatus =
  | 'Active'
  | 'Under Investigation'
  | 'Marked for Disposal'
  | 'Idle'
  | 'Disposed';

export interface AssetComponent {
  id: string;
  name: string;
  costINR: number;
  usefulLifeYears: number;
  depreciationMethod: 'SLM' | 'WDV';
  accumulatedDepINR: number;
  nbvINR: number;
  notes: string;
}

export interface AssetHistoryEvent {
  id: string;
  date: string;
  type: 'Procurement' | 'Capitalisation' | 'Physical Verification' | 'Location Transfer' | 'Maintenance' | 'Audit Finding' | 'Disposal' | 'Component Replacement';
  description: string;
  actor: string;
  referenceDoc?: string;
  status: 'Completed' | 'Pending' | 'Flagged';
}

export interface Asset {
  id: string;
  name: string;
  category: AssetCategory;
  plant: PlantLocation;
  subLocation: string;
  costINR: number;
  accumulatedDepINR: number;
  nbvINR: number;
  capitalisationDate: string;
  usefulLifeYears: number;
  schIILifeYears: number;
  depreciationMethod?: 'SLM' | 'WDV';
  verificationStatus: VerificationStatus;
  lastVerifiedDate: string | null;
  riskLevel: RiskLevel;
  custodian: string;
  department: string;
  serialNumber: string;
  qrCode: string;
  poNumber: string;
  grnNumber: string;
  invoiceNumber: string;
  vendor: string;
  components: AssetComponent[];
  historyEvents: AssetHistoryEvent[];
  anomalies: string[];
  status: AssetOperationalStatus;
  description: string;
  specifications?: Record<string, string>;
  gstPaidINR?: number;
  itcClaimed?: boolean;
}

export interface CapitalisationComponentDetail {
  name: string;
  costRatioPct: number;
  usefulLifeYears: number;
  justification: string;
}

export interface CapitalisationReviewResult {
  recommendation: 'Capitalise' | 'Expense' | 'Mixed / Componentise';
  recommendedCategory: string;
  usefulLifeYears: number;
  salvageValuePct: number;
  componentisationDetails: CapitalisationComponentDetail[];
  gstItcEligibility: 'Eligible' | 'Blocked under Sec 17(5)' | 'Partially Blocked';
  gstAnalysis: string;
  capitalisationDate: string;
  reasoning: string;
  evidenceKeyPoints: string[];
  confidenceScore: number;
  policyReference: string;
  riskWarnings: string[];
}

export interface CapexItem {
  id: string;
  poNumber: string;
  invoiceNumber: string;
  vendor: string;
  description: string;
  amountINR: number;
  invoiceDate: string;
  plant: PlantLocation;
  department: string;
  grnStatus: 'Complete' | 'Partial' | 'Pending';
  technicalInspection: 'Passed' | 'Pending' | 'Failed';
  suggestedCategory: AssetCategory | 'Operating Expense';
  status: 'Pending AI Review' | 'Reviewed - Needs Approval' | 'Approved & Capitalised' | 'Expensed' | 'Rejected';
  aiRecommendation?: CapitalisationReviewResult;
  humanApproval?: {
    approver: string;
    role: string;
    decision: 'Capitalise' | 'Expense' | 'Componentise' | 'Return to Vendor';
    timestamp: string;
    remarks: string;
  };
}

export type RiskType =
  | 'Ghost Asset'
  | 'Duplicate Capitalisation'
  | 'Duplicate Invoice'
  | 'Wrong Location'
  | 'Missing Documents'
  | 'Idle High-Value'
  | 'Abnormal Useful Life'
  | 'Disposed Still Depreciating'
  | 'Potential Impairment';

export type ExceptionWorkflowStage =
  | 'Detected'
  | 'Assigned'
  | 'Investigating'
  | 'Management Review'
  | 'Approved'
  | 'Closed';

export interface AuditTrailEntry {
  timestamp: string;
  user: string;
  action: string;
  note: string;
}

export interface RiskFinding {
  id: string;
  title: string;
  riskType: RiskType;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  assetId: string;
  assetName: string;
  location: PlantLocation;
  financialExposureINR: number;
  explanation: string;
  evidence: string;
  statutoryReference: string;
  recommendedAction: string;
  owner: string;
  status: ExceptionWorkflowStage;
  createdDate: string;
  updatedDate: string;
  auditTrail: AuditTrailEntry[];
}

export interface VerificationScanRecord {
  id: string;
  timestamp: string;
  tagScanned: string;
  assetId: string;
  assetName: string;
  scannedPlant: PlantLocation;
  scannedSubLocation: string;
  registeredPlant: PlantLocation;
  registeredSubLocation: string;
  inspectorName: string;
  detectedStatus: VerificationStatus;
  notes: string;
  gpsCoordinates: string;
  photoUrl?: string;
  discrepancyIdentified: boolean;
  exceptionRaised?: boolean;
}

export interface ReliabilityDriver {
  name: string;
  score: number; // 0-100
  weight: number; // e.g. 0.25
  weightedScore: number;
  status: 'Good' | 'Fair' | 'Critical';
  description: string;
  findingsCount: number;
}

export interface AssetReliabilityScore {
  totalScore: number; // 0-100
  grade: 'A+ (Exemplary)' | 'A (Strong)' | 'B (Moderate Risk)' | 'C (Action Required)' | 'D (Severe Deficiencies)';
  drivers: ReliabilityDriver[];
  summary: string;
  lastCalculated: string;
}

export interface PolicyRule {
  id: string;
  framework: 'Ind AS 16' | 'Companies Act Sch II' | 'Ind AS 36' | 'Income Tax Sec 32' | 'CARO 2020';
  clause: string;
  title: string;
  requirement: string;
  complianceStatus: 'Compliant' | 'Remediation Underway' | 'Non-Compliant' | 'Not Applicable';
  applicableAssetsCount: number;
  impactExplanation: string;
  evidenceRef: string;
}

export type IndustryType =
  | 'Automotive & Precision Engineering'
  | 'Pharmaceuticals & Life Sciences'
  | 'Renewable Energy & Solar Infrastructure'
  | 'Information Technology & Data Centers'
  | 'Chemicals & Process Manufacturing'
  | 'Consumer Goods & FMCG'
  | 'Heavy Infrastructure & Construction'
  | 'Other Enterprise';

export interface Company {
  id: string;
  name: string;
  shortCode: string;
  legalEntityType: 'Public Limited' | 'Private Limited' | 'LLP' | 'Multinational Corporation';
  cin: string;
  gstin: string;
  industry: IndustryType;
  fiscalYear: string;
  depreciationPolicy: 'Companies Act 2013 Sch II (SLM)' | 'Income Tax Act 1961 (WDV)' | 'Dual Depreciation (Both)';
  plants: string[];
  baseCurrency: 'INR' | 'USD' | 'EUR';
  description?: string;
  logoColor?: string;
  createdAt: string;
  isCustom?: boolean;
}

export interface CompanyData {
  company: Company;
  assets: Asset[];
  capexQueue: CapexItem[];
  risks: RiskFinding[];
  scanLogs: VerificationScanRecord[];
}

export interface ParsedDocumentResult {
  documentType: string;
  documentReference?: string;
  vendorName?: string;
  poNumber?: string;
  invoiceNumber?: string;
  documentDate?: string;
  totalGrossAmountINR?: number;
  gstAmountINR?: number;
  currency?: string;
  summaryNote?: string;
  extractedAssets?: Partial<Asset>[];
  extractedCapexItems?: Partial<CapexItem>[];
}

