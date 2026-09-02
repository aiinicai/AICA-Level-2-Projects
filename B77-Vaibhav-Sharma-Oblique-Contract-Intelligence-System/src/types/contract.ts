export type AttentionLevel = 'RED' | 'AMBER' | 'BLUE' | 'GREY';

export type FindingStatus = 'New' | 'Under Review' | 'Cleared' | 'Requires Information' | 'Escalated';

export type AnalysisDomain = 
  | 'Accounting'
  | 'Financial Reporting'
  | 'GST'
  | 'TDS'
  | 'Tax'
  | 'MSME'
  | 'Related Party'
  | 'Audit'
  | 'Disclosure'
  | 'Legal/Contractual Risk'
  | 'Working Capital'
  | 'Internal Control'
  | 'Other';

export interface SourceReference {
  page: number;
  clause: string;
  clauseTitle?: string;
  extractedText: string;
}

export interface CAComment {
  id: string;
  author: string;
  timestamp: string;
  text: string;
  actionTaken?: FindingStatus;
}

export interface Finding {
  id: string;
  title: string;
  attention: AttentionLevel;
  domains: AnalysisDomain[];
  source: SourceReference;
  whyItMatters: string;
  potentialImpact: string;
  whatToVerify: string[];
  evidenceRequired: string[];
  managementQuestions: string[];
  frameworkToConfirm: string[];
  confidence: 'High' | 'Medium' | 'Low';
  status: FindingStatus;
  userConclusion?: string;
  comments: CAComment[];
  isCrossClause?: boolean;
  relatedClauseIds?: string[];
}

export interface ContractParty {
  name: string;
  role: 'Buyer/Customer' | 'Seller/Vendor/Service Provider' | 'Subcontractor' | 'Guarantor' | 'Related Entity' | 'Other';
  legalEntityType?: string;
  jurisdiction?: string;
  panOrGstin?: string;
  isRelatedPartyIndicator?: boolean;
}

export interface ContractIdentity {
  title: string;
  contractNumber?: string;
  contractType?: string;
  effectiveDate?: string;
  executionDate?: string;
  commencementDate?: string;
  expiryDate?: string;
  renewalPeriod?: string;
  governingLaw?: string;
  jurisdiction?: string;
  disputeResolution?: string;
}

export interface CommercialTerms {
  contractValue: string;
  currency: string;
  pricingMechanism: string;
  taxesTreatment: string;
  discountsAndRebates?: string;
  escalationClause?: string;
  retentionMoney?: {
    percentage?: string;
    amount?: string;
    conditions?: string;
  };
  advances?: {
    percentage?: string;
    amount?: string;
    recoveryTerms?: string;
  };
  securityDeposit?: string;
  paymentTerms: string;
  creditPeriodDays?: number;
  milestonesSummary?: string;
  penaltiesAndLiquidatedDamages?: string;
  warrantyPeriod?: string;
  indemnitiesAndLiabilityCap?: string;
}

export interface ExtractedClause {
  id: string;
  clauseNumber: string;
  title: string;
  text: string;
  pageNumber: number;
  categories: AnalysisDomain[];
  isMaterial: boolean;
  associatedFindingIds: string[];
}

export interface CrossClauseInsight {
  id: string;
  title: string;
  involvedClauses: {
    clauseNumber: string;
    pageNumber: number;
    summary: string;
  }[];
  combinedAttention: AttentionLevel;
  combinedImpact: string;
  whyItMatters: string;
  whatToVerify: string[];
  managementQuestions: string[];
  recommendedAction: string;
}

export interface InvoiceData {
  invoiceNumber: string;
  invoiceDate: string;
  vendorName: string;
  customerName: string;
  itemDescription: string;
  quantity?: number;
  unitPrice?: number;
  baseAmount: number;
  gstRate: number;
  gstAmount: number;
  retentionDeduction?: number;
  advanceAdjustment?: number;
  discountAmount?: number;
  netPayableAmount: number;
  paymentDueDate?: string;
  creditDaysOffered?: number;
}

export interface InvoiceDiscrepancy {
  field: string;
  contractValue: string;
  invoiceValue: string;
  status: 'RED' | 'AMBER' | 'GREEN';
  contractClauseRef: string;
  observation: string;
  accountingImpact: string;
  gstOrTdsImpact?: string;
}

export interface InvoiceComparisonResult {
  invoiceData: InvoiceData;
  discrepancies: InvoiceDiscrepancy[];
  overallMatchStatus: 'Matching' | 'Variances Found' | 'Significant Non-Compliance';
  caReviewNotes?: string;
}

export interface ContractDocument {
  id: string;
  fileName: string;
  fileSize: number;
  fileType: 'pdf' | 'docx' | 'txt';
  uploadedAt: string;
  rawText: string;
  pageCount: number;
  pages: {
    pageNumber: number;
    text: string;
  }[];
  parties: ContractParty[];
  identity: ContractIdentity;
  commercialTerms: CommercialTerms;
  clauses: ExtractedClause[];
  findings: Finding[];
  crossClauseInsights: CrossClauseInsight[];
  selectedFramework: 'Ind AS' | 'Accounting Standards (AS)' | 'Company Financial Reporting' | 'To Be Confirmed';
  invoiceComparisons: InvoiceComparisonResult[];
  executiveSummary: string;
}

export interface AnalysisProgressStage {
  id: string;
  name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  detail?: string;
}

export interface ComplianceRule {
  id: string;
  ruleName?: string;
  title: string;
  jurisdiction?: string;
  domain: AnalysisDomain;
  effectiveDate?: string;
  statutoryReference?: string;
  statutoryCitation: string;
  applicabilitySummary?: string;
  summary: string;
  triggerKeywords: string[];
  keyVerificationPoints?: string[];
  caVerificationSteps: string[];
  requiredEvidence: string[];
  managementQuestions: string[];
  lastReviewedDate?: string;
}
