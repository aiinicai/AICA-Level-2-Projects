export type ComplianceScore = 'High' | 'Moderate' | 'Needs Immediate Revision';
export type RiskLevel = 'High' | 'Medium' | 'Low';
export type DisclosureStatus = 'Complied' | 'Missing' | 'Partial' | 'Not Applicable';

export interface DisclosureItem {
  standard: string; // e.g., "Ind AS 24", "Ind AS 37", "Ind AS 16"
  standardName?: string; // e.g., "Related Party Disclosures"
  requirement: string;
  status: DisclosureStatus;
  observation: string;
  applicableParagraph?: string;
}

export interface InconsistencyItem {
  lineItem: string;
  primaryFigure: string;
  noteFigure: string;
  noteRef?: string;
  discrepancy: string;
  riskLevel: RiskLevel;
  type?: 'numerical_mismatch' | 'casting_error' | 'text_table_contradiction' | 'missing_note' | 'prior_period_mismatch';
}

export interface NoteProofreadingItem {
  noteNumber: string;
  noteTitle: string;
  proofreadingStatus: 'Complied' | 'Observations Found' | 'Missing Mandatory Clauses';
  observations: string;
  mandatoryClausesChecked: string;
  draftingOrArithmeticIssues?: string;
}

export interface ScheduleIIIGuidanceItem {
  clause: string;
  requirement: string;
  complianceStatus: 'Complied' | 'Non-Compliant' | 'Not Disclosed' | 'Not Applicable';
  detailedFinding: string;
  guidanceNoteReference: string;
}

export interface ExecutiveSummary {
  overallComplianceScore: ComplianceScore;
  totalDiscrepancies: number;
  missingDisclosuresCount: number;
  numericalMismatchesCount: number;
  keyRiskAreas: string;
  entityName?: string;
  reportingPeriod?: string;
  reportingScale?: string; // e.g. "₹ in Lakhs", "₹ in Crores"
  frameworkIdentified?: string; // e.g. "Ind AS (Schedule III Division II)"
}

export interface AuditRecommendation {
  id: string;
  priority: 'Immediate' | 'Pre-Signing' | 'Management Letter';
  category: string;
  recommendation: string;
  statutoryReference?: string;
  actionFor: string; // e.g., "Audit Senior", "Partner", "CFO / Management"
}

export interface AuditReportData {
  id: string;
  timestamp: string;
  documentTitle: string;
  summary: ExecutiveSummary;
  part1Disclosures: DisclosureItem[];
  part2Inconsistencies: InconsistencyItem[];
  noteProofreading?: NoteProofreadingItem[];
  scheduleIIIGuidanceFindings?: ScheduleIIIGuidanceItem[];
  part3Recommendations: AuditRecommendation[];
  rawMarkdownReport?: string;
  financialHighlights?: {
    totalRevenue?: string;
    pat?: string;
    totalAssets?: string;
    totalDebt?: string;
    netWorth?: string;
  };
  caroObservations?: string[];
}

export interface SampleFinancialStatement {
  id: string;
  title: string;
  companyName: string;
  period: string;
  framework: string;
  description: string;
  previewSnippet: string;
  fullText: string;
  knownIssuesSummary: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  content: string;
  suggestions?: string[];
}
