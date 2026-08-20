/**
 * AI Client Intelligence & Advisory Agent - Type Definitions (V2 Master Upgrade)
 */

export type NavTab =
  | 'dashboard'
  | 'briefing'
  | 'inbox'
  | 'impact'
  | 'clients'
  | 'matching'
  | 'advisories'
  | 'approval'
  | 'status-studio'
  | 'history'
  | 'settings';

export type OperatingMode = 'DEMO' | 'LIVE';

export type UpdateCategory =
  | 'GST'
  | 'Income Tax'
  | 'TDS / TCS'
  | 'MCA / Companies Act'
  | 'RBI / Banking'
  | 'FEMA / Foreign Exchange'
  | 'SEBI / Capital Markets'
  | 'Labour Law'
  | 'PF'
  | 'ESI'
  | 'Accounting'
  | 'Audit'
  | 'Corporate Finance'
  | 'Economic Development'
  | 'Forex'
  | 'Gold'
  | 'Crude Oil'
  | 'Commodities'
  | 'Equity Market'
  | 'Industry Development'
  | 'Other';

export type UpdateNature =
  | 'New Requirement'
  | 'Amendment'
  | 'Rate Change'
  | 'Deadline'
  | 'Deadline Extension'
  | 'Clarification'
  | 'Procedural Change'
  | 'Exemption'
  | 'Reporting Requirement'
  | 'Judicial Development'
  | 'Draft Proposal'
  | 'Market Development'
  | 'Economic Development'
  | 'Risk Alert'
  | 'Opportunity';

export type SourceVerificationStatus =
  | 'Verified from Authoritative Source'
  | 'Source Identified — Verification Pending'
  | 'Secondary Source Only'
  | 'Unable to Verify'
  | 'Demo / Simulated Data';

export type ConfidenceRating =
  | 'High (90-100%)'
  | 'Moderate (75-89%)'
  | 'Limited (50-74%)'
  | 'Manual Verification Required (<50%)';

export type RiskLevel = 'Critical' | 'High' | 'Medium' | 'Low' | 'Informational';

export type ActionPriority =
  | 'Immediate'
  | 'Within 3 Days'
  | 'Within 7 Days'
  | 'Before Statutory Deadline'
  | 'Monitor'
  | 'Information Only';

export interface SourceProvenance {
  sourceType: 'Gmail' | 'Official Gazette' | 'Manual Entry' | 'Demo Data' | 'RSS/API';
  emailSubject?: string;
  emailReceivedDateTime?: string;
  importedDateTime?: string;
  extractedCount?: number;
  authoritativeSourceCheck?: string;
}

export interface DateClassification {
  notificationDate: string;
  effectiveDate: string;
  statutoryDeadline: string;
  recommendedInternalActionDate: string;
  reviewDate: string;
}

export interface ApplicabilityConditions {
  turnover?: string;
  employeeCount?: string;
  registration?: string;
  industry?: string;
  geography?: string;
  transaction?: string;
  entityType?: string;
  financialThreshold?: string;
}

export interface CAImpactAnalysis {
  whatChanged: string;
  whoIsAffected: string;
  applicabilityConditions: ApplicabilityConditions;
  complianceImpact: string;
  financialImpact: string;
  operationalImpact: string;
  recommendedAction: string;
  deadline: string;
  professionalReviewNote: string;
}

export interface MarketImpactAnalysis {
  natureOfMovement: string;
  likelyBusinessConsequence: string;
  importerImpact: string;
  exporterImpact: string;
  travelSectorImpact: string;
  manufacturingImpact: string;
  costImplications: string;
  marginImplications: string;
  workingCapitalImplications: string;
  treasuryHedgingConsideration: string;
  suggestedManagementQuestions: string[];
}

export interface RegulatoryUpdate {
  id: string;
  briefingDate: string;
  title: string;
  category: UpdateCategory;
  subCategory: string;
  nature: UpdateNature;
  issuingAuthority: string;
  source: string;
  referenceNo: string;
  dates: DateClassification;
  originalSummary: string;
  sourceFacts: string; // Fact 1: What authoritative source actually states
  aiImpactAnalysisText: string; // Fact 2: AI interpretation of business consequences
  caRecommendedAction: string; // Fact 3: Suggested CA professional actions
  keyDevelopment: string;
  importantAmounts: string;
  importantPercentages: string;
  importantThresholds: string;
  industryRelevance: string;
  entityRelevance: string;
  sourceUrl?: string;
  verificationStatus: SourceVerificationStatus;
  provenance: SourceProvenance;
  unconfirmedNotice?: string; // Anti-hallucination note if references/dates unconfirmed
  confidenceScore: number;
  confidenceRating: ConfidenceRating;
  riskLevel: RiskLevel;
  actionPriority: ActionPriority;
  isMarketItem: boolean;
  impactAnalysis: CAImpactAnalysis;
  marketImpactAnalysis?: MarketImpactAnalysis;
  createdAt: string;
  sourceType: 'Gmail' | 'Manual' | 'Demo';
}

export type EntityType =
  | 'Private Limited'
  | 'Public Limited'
  | 'LLP'
  | 'Partnership'
  | 'Sole Proprietorship'
  | 'Individual'
  | 'Trust/NGO';

export type ExposureLevel = 'None' | 'Low' | 'Medium' | 'High';

export type CommunicationLanguage =
  | 'English'
  | 'Malayalam'
  | 'Hindi'
  | 'Tamil'
  | 'English + Malayalam'
  | 'English + Hindi'
  | 'English + Tamil';

export type CommunicationDetailLevel = 'Quick Alert' | 'Standard' | 'Detailed';

export interface ClientMaster {
  id: string;
  clientName: string;
  entityType: EntityType;
  industry: string;
  businessDescription?: string;
  state: string;
  annualTurnoverRange: string;
  gstRegistered: boolean;
  gstin?: string;
  incomeTaxAssessee?: boolean;
  msmeStatus?: 'Micro' | 'Small' | 'Medium' | 'Non-MSME';
  udyamRegistration?: boolean;
  udyamRegNo?: string;
  tdsApplicable: boolean;
  mcaApplicable: boolean;
  payroll: boolean;
  numberOfEmployees: number;
  employeeCountRange?: string;
  pfApplicable: boolean;
  esiApplicable: boolean;
  importer: boolean;
  exporter: boolean;
  hasImportExport?: boolean;
  femaExposure: ExposureLevel;
  hasFemaExposure?: boolean;
  forexExposure: ExposureLevel;
  hasForeignCurrencyExposure?: boolean;
  crudeSensitivity: ExposureLevel;
  commoditySensitivity: ExposureLevel;
  borrowings: ExposureLevel;
  borrowingsAmount?: string;
  rbiApplicability?: boolean;
  listed?: boolean;
  isListed?: boolean;
  riskCategory: 'Low' | 'Medium' | 'High';
  primaryContact?: string;
  clientEmail: string;
  mobileWhatsApp?: string;
  preferredLanguage?: CommunicationLanguage;
  communicationDetailLevel?: CommunicationDetailLevel;
  keyComplianceAreas?: string[];
  preferredCommunicationStyle?: 'Formal Advisory' | 'Short WhatsApp Alert' | 'Management Executive Note';
  notes: string;

  // DEMO Compliance Profile Fields (V2.2 Upgrade)
  tanAvailable?: 'Yes' | 'No' | 'Unknown';
  tanNumber?: string;
  tdsApplicableStatus?: 'Yes' | 'No' | 'Unknown';
  tcsApplicableStatus?: 'Yes' | 'No' | 'Unknown';
  activeDeductorCollector?: 'Yes' | 'No' | 'Unknown';
  relevantPeriodActivity?: 'Yes' | 'No' | 'Unknown';
  tdsTcsAmountPayable?: 'Amount Outstanding' | 'Nil' | 'Unknown' | string;
  depositStatus?: 'Paid' | 'Unpaid' | 'Partially Paid' | 'Unknown';
  lastDepositDate?: string;
  complianceDataLastVerified?: string;
}

export type MatchStatus =
  | 'MATCHED / ACTION REQUIRED'
  | 'MATCHED / ALREADY COMPLIED'
  | 'POSSIBLY RELEVANT — DATA VERIFICATION REQUIRED'
  | 'NOT APPLICABLE'
  | 'Highly Relevant'
  | 'Relevant'
  | 'Possibly Relevant';

export interface ClientMatch {
  id: string;
  updateId: string;
  clientId: string;
  clientName: string;
  relevanceStatus: MatchStatus;
  relevanceScore: number; // 0 - 100
  matchReasons: string[];
  exclusionReasons: string[];
  missingInformation: string[];
  recommendedNextStep: string;
  needForProfessionalReview: string;
  canGenerateAdvisory?: boolean;
}

export interface FormalAdvisory {
  subject: string;
  development: string;
  authoritativeSource: string;
  applicability: string;
  clientSpecificImpact: string;
  financialImpact: string;
  operationalImpact: string;
  requiredAction: string;
  statutoryDate: string;
  recommendedInternalActionDate: string;
  documentsRequired: string;
  verificationNotes: string;
  disclaimer: string;
}

export interface PlainLanguageClientCommunication {
  whatHappened: string;
  doesThisAffectMyBusiness: string;
  whyDoesItMatter: string;
  whatShouldIDo: string;
  byWhen: string;
  whatWillMyCaDo: string;
  regionalLanguageText?: {
    language: 'Malayalam' | 'Hindi' | 'Tamil';
    languageHeader: string; // e.g. "മലയാളത്തിൽ"
    summary: string;
  };
}

export interface ShortWhatsAppAlert {
  title: string;
  whatChanged: string;
  businessImpact: string;
  action: string;
  importantDate: string;
  ourTeamAction: string;
  sourceNote: string;
  fullFormattedText: string;
}

export interface ManagementNote {
  issue: string;
  risk: string;
  financialImplication: string;
  recommendedAction: string;
  responsibleFunction: string;
  timeline: string;
}

export interface CAInternalAction {
  client: string;
  update: string;
  action: string;
  priority: 'High' | 'Medium' | 'Low';
  deadline: string;
  status: 'Pending' | 'In Progress' | 'Completed';
}

export type ApprovalStatus =
  | 'Draft'
  | 'Pending Review'
  | 'Approved'
  | 'Revised'
  | 'Rejected'
  | 'Hold'
  | 'Not Applicable';

export interface ClientAdvisory {
  id: string;
  updateId: string;
  clientId: string;
  clientName: string;
  originalFormalAdvisory?: FormalAdvisory;
  formalAdvisory: FormalAdvisory;
  plainLanguageCommunication: PlainLanguageClientCommunication;
  shortAlert: ShortWhatsAppAlert;
  managementNote: ManagementNote;
  caInternalAction: CAInternalAction;
  approvalStatus: ApprovalStatus;
  reviewerNotes?: string;
  reviewDate?: string;
  reviewedBy?: string;
  dispatchStatus?: 'Not Dispatched' | 'Queued' | 'Sent via Email' | 'Sent via WhatsApp';
  createdAt: string;
}

export interface BrandSettings {
  firmName: string;
  caName: string;
  membershipNo: string;
  contactEmail: string;
  contactPhone: string;
  firmAddress: string;
  disclaimer: string;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  action: string;
  performedBy: string;
  targetTitle: string;
  details: string;
}

export type BriefingSource = 'GMAIL' | 'DEMO' | 'NONE';

export interface GmailDiagnosticCandidate {
  id: string;
  subject: string;
  dateHeader: string;
  normalizedSubject: string;
  extractedBriefingDate: string;
  subjectMatch: 'PASS' | 'FAIL';
  dateMatch: 'PASS' | 'FAIL';
}

export interface GmailSearchDiagnostics {
  connectedAccount: string;
  targetDate: string;
  broadGmailQuery: string;
  candidateMessagesFound: number;
  candidates: GmailDiagnosticCandidate[];
}

export interface ActiveBriefingInfo {
  source: BriefingSource;
  targetDate: string;
  expectedSubject: string;
  actualSubject?: string;
  emailReceivedDate?: string;
  gmailMessageId?: string;
  connectedAccount?: string;
  importedDateTime?: string;
  dateMatch: 'PASS' | 'FAIL' | 'DEMO';
}

export interface IntegrationStatus {
  geminiConnected: boolean;
  gmailConnected: boolean;
  clientDatabaseLive: boolean;
  sourceVerificationLive: boolean;
  whatsappExportReady: boolean;
  approvalWorkflowActive: boolean;
}
