export interface VerificationRequest {
  question: string;
  aiAnswer: string;
  sourceMaterial?: string;
}

export type ClaimStatus =
  | 'SUPPORTED'
  | 'REQUIRES VERIFICATION'
  | 'POTENTIAL ERROR'
  | 'NOT ESTABLISHED BY SUPPLIED SOURCES';

export interface KeyFact {
  id: string;
  fact: string;
  category: string; // e.g. 'Turnover', 'Payment Mode', 'Entity Type', 'Assessment Year'
}

export interface ProfessionalDomainItem {
  domain: string; // e.g. 'Income Tax', 'GST / Indirect Tax', 'TDS / TCS', 'Companies Act', 'CARO 2020', etc.
  whyItApplies: string;
  relevantProvision: string;
  impact: string;
  aiAddressedStatus: 'Addressed' | 'Partially Addressed' | 'Missed / Omitted';
  verificationRequired: string;
}

export interface SupportedClaim {
  id: string;
  claim: string;
  status: 'SUPPORTED';
  sourceEvidence: string;
  analysis: string;
  professionalImplication: string;
}

export interface QuestionableClaim {
  id: string;
  claim: string;
  status: 'REQUIRES VERIFICATION' | 'NOT ESTABLISHED BY SUPPLIED SOURCES';
  sourceEvidence: string;
  analysis: string;
  professionalImplication: string;
  missingEvidenceNotice?: string;
}

export interface PotentialError {
  id: string;
  errorType: 'statutory_misstatement' | 'numerical_or_threshold_error' | 'factual_contradiction' | 'outdated_provision';
  statementInAIAnswer: string;
  contradictingSourceEvidence: string;
  analysis: string;
  professionalImplication: string;
  severity: 'high' | 'medium';
}

export interface MissedIssue {
  id: string;
  domain: string;
  issueTitle: string;
  applicableProvision: string;
  description: string;
  whyMissedByAI: string;
  consequenceOrPenalty: string;
  severity: 'high' | 'medium' | 'low';
  actionRequired: string;
}

export interface SourceEvidenceItem {
  id: string;
  aiClaim: string;
  status: ClaimStatus;
  sourceHierarchy: 'PRIMARY / AUTHORITATIVE' | 'SECONDARY' | 'NOT SUPPLIED';
  sourceEvidence: string;
  analysis: string;
  professionalImplication: string;
}

export interface ConsequenceAndReportingItem {
  id: string;
  area: string;
  provision: string;
  riskLevel: 'Critical' | 'Moderate' | 'Advisory';
  description: string;
  statutoryPenaltyOrImpact: string;
}

export interface ScoreBreakdown {
  sourceSupport: 'High' | 'Moderate' | 'Low' | 'None';
  completeness: 'Comprehensive' | 'Partial' | 'Significant Omissions';
  professionalRisk: 'Low' | 'Moderate' | 'Elevated' | 'Critical';
}

export interface VerificationReport {
  isLimitedVerification?: boolean;
  limitedVerificationNotice?: string;
  sourceReliability: 'Primary Authoritative' | 'Mixed / Secondary' | 'Limited / Unverified' | 'No Source Supplied';
  sourceReliabilityDetails: string;
  overallStatus: 'High Support' | 'Generally Supported — Verify' | 'Significant Verification Required' | 'Potentially Unreliable';
  verificationScore: number; // Source-Supported Reliability Score 0-100
  scoreExplanation: string;
  scoreBreakdown: ScoreBreakdown;
  executiveVerdict: string;
  keyFacts?: KeyFact[];
  applicableDomains?: ProfessionalDomainItem[];
  supportedClaims?: SupportedClaim[];
  questionableClaims?: QuestionableClaim[];
  potentialErrors?: PotentialError[];
  missedIssues?: MissedIssue[];
  sourceEvidenceList?: SourceEvidenceItem[];
  consequencesAndPenalties?: ConsequenceAndReportingItem[];
  recommendedProfessionalActions?: string[];
  professionalRelianceWarning: string;
  verificationTimestamp: string;
}
