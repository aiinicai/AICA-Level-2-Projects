export type SeverityLevel = 'Critical' | 'High' | 'Medium' | 'Low';

export type ObservationStatus = 
  | 'Open'
  | 'Under Discussion'
  | 'Management Response Awaited'
  | 'Rectified'
  | 'Closed'
  | 'Not Accepted';

export type RectificationStatus = 
  | 'Not Started'
  | 'In Progress'
  | 'Rectified'
  | 'Not Rectified'
  | 'Not Applicable';

export type EngagementStatus = 
  | 'Planning'
  | 'In Progress'
  | 'Fieldwork Complete'
  | 'Report Issued'
  | 'Closed';

export interface AuditType {
  id: string;
  name: string;
  code: string; // e.g. "SA" for Stock Audit, "TA" for Tax Audit, "CAG" for CAG Audit, "CA" for Concurrent Audit
  isDefault?: boolean;
  description?: string;
  color?: string;
}

export interface Engagement {
  id: string; // e.g. "ENG-2025-001"
  clientName: string;
  clientPanGstin?: string;
  clientCode: string; // short code for ref numbers e.g. "ABC", "TSL"
  auditTypeId: string;
  financialYear: string; // e.g. "2024-25", "2025-26"
  teamMembers: string[];
  engagementPartner: string;
  startDate: string; // YYYY-MM-DD
  endDate: string; // YYYY-MM-DD
  branchLocation?: string;
  overallStatus: EngagementStatus;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Observation {
  id: string;
  referenceNo: string; // format: <AuditTypeCode>-<FY>-<ClientCode>-<Sequence>, e.g. SA-2526-ABC-001
  engagementId: string;
  dateOfObservation: string; // YYYY-MM-DD
  areaProcess: string;
  description: string;
  severity: SeverityLevel;
  financialImpact?: number; // amount in INR (₹)
  rootCause?: string;
  recommendation: string;
  discussionStakeholder?: string;
  dateOfDiscussion?: string; // YYYY-MM-DD
  managementResponse?: string;
  status: ObservationStatus;
  rectificationStatus: RectificationStatus;
  targetRectificationDate?: string; // YYYY-MM-DD
  actualRectificationDate?: string; // YYYY-MM-DD
  personResponsible: string;
  attachments?: string; // filenames or notes
  remarks?: string;
  createdAt: string;
  updatedAt: string;
}

export interface AuditChecklistItem {
  id: string;
  auditTypeId: string; // ID of the AuditType
  category: string; // e.g. "Physical Verification", "Statutory Compliance (MSME/TDS)", "Internal Controls", "Documentation & Vouching"
  itemNumber?: string; // e.g. "1.1", "2.1", "CL-01"
  checkPoint: string; // Specific audit checkpoint or question
  procedureGuidance?: string; // Verification guidance / audit procedure
  statutoryReference?: string; // e.g. "CARO 2020 3(ii)(a)", "Sec 43B(h) Income Tax Act", "RBI IRAC Norms"
  riskLevel: SeverityLevel; // 'Critical' | 'High' | 'Medium' | 'Low'
  isMandatory: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface ParsedChecklistRow {
  auditTypeCode: string;
  auditTypeName?: string;
  category: string;
  itemNumber?: string;
  checkPoint: string;
  procedureGuidance?: string;
  statutoryReference?: string;
  riskLevel: SeverityLevel;
  isMandatory: boolean;
  isValid: boolean;
  validationError?: string;
}

export interface ParsedEngagementRow {
  clientName: string;
  clientCode: string;
  auditTypeCodeOrName: string;
  financialYear: string;
  clientPanGstin?: string;
  engagementPartner?: string;
  teamMembers?: string;
  startDate?: string;
  endDate?: string;
  branchLocation?: string;
  overallStatus: EngagementStatus;
  notes?: string;
  isValid: boolean;
  validationError?: string;
  matchedAuditTypeId?: string;
  matchedAuditTypeName?: string;
}

export interface FirmProfile {
  firmName: string;
  frn: string; // Firm Registration Number
  address: string;
  city: string;
  phone: string;
  email: string;
  partnerName: string;
  membershipNo: string;
  website?: string;
}

export interface ObservationFilterState {
  searchQuery: string;
  engagementId: string;
  auditTypeId: string;
  financialYear: string;
  severity: SeverityLevel[];
  status: ObservationStatus[];
  rectificationStatus: RectificationStatus[];
  stakeholder: string;
  areaProcess: string;
  dateFrom: string;
  dateTo: string;
  hasFinancialImpactOnly: boolean;
  minFinancialImpact?: number;
}
