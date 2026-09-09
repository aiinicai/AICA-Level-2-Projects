export interface Client {
  id: string;
  gstin: string;
  legalName: string;
  tradeName: string;
  email: string;
  phone: string;
  pan?: string;
  address?: string;
}

export type NoticeFormType =
  | 'DRC-01'
  | 'DRC-01A'
  | 'DRC-07'
  | 'ASMT-10'
  | 'REG-17'
  | 'RFD-08'
  | 'ADT-01'
  | 'INS-01'
  | 'MOV-06'
  | 'SCN'
  | 'OTHER';

export type CaseStatus = 'UNDER_REVIEW' | 'DRAFT_READY' | 'REPLY_FILED' | 'HEARING_SCHEDULED' | 'CLOSED';
export type RiskLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export interface NoticeCase {
  id: string;
  clientId: string;
  noticeNumber: string;
  formType: NoticeFormType;
  financialYear: string;
  period: string;
  noticeDate: string;
  replyDeadline: string;
  hearingDate?: string;
  issuingAuthority: string;
  sectionsMentioned: string;
  principalTax: number;
  interest: number;
  penalty: number;
  totalDemand: number;
  status: CaseStatus;
  rawText?: string;
  pdfDataUrl?: string;
  pdfFileName?: string;
  isCaVerified: boolean;
  din?: string; // Document Identification Number
  createdAt: string;
  updatedAt: string;
}

export interface NoticeIssue {
  id: string;
  caseId: string;
  issueNumber: number;
  title: string;
  allegation: string;
  sectionRule: string;
  pageRef: string;
  taxAmount: number;
  interestAmount: number;
  penaltyAmount: number;
  totalAmount: number;
  probableReason: string;
  figureSource: string;
  dataRequired: string;
  reconciliationRequired: string;
  clientQuestions: string;
  documentsRequired: string;
  defensePoints: string;
  legalPosition: string; // marked with [Verify before use]
  riskLevel: RiskLevel;
  factsCategory?: string;
  calculationSummary?: string;
}

export type ReconStatus = 'MATCH' | 'MISMATCH' | 'MISSING_DATA';

export interface ReconciliationItem {
  id: string;
  caseId: string;
  reconType: string; // e.g. 'GSTR-2B vs GSTR-3B (ITC)', 'GSTR-1 vs GSTR-3B (Turnover)', 'GST Returns vs Books'
  period: string;
  noticeValue: number;
  portalValue: number;
  booksValue: number;
  variance: number;
  varianceReason: string;
  status: ReconStatus;
  hsnCode?: string;
  supplierGstin?: string;
  /** Which extracted issue this schedule supports (for the draft reply). */
  issueNumber?: number;
  /** Human hint of what document/table the portal & books columns should come from. */
  portalHint?: string;
  booksHint?: string;
}

// ─── Portal figure intake (GSTR-3B / 9 / 2B / ledgers / comparison statement) ───

export type GstDocType =
  | 'GSTR-3B' | 'GSTR-1' | 'GSTR-2B' | 'GSTR-2A' | 'GSTR-9' | 'GSTR-9C'
  | 'CASH_LEDGER' | 'CREDIT_LEDGER' | 'COMPARISON' | 'BOOKS' | 'OTHER';

export type TaxHead = 'IGST' | 'CGST' | 'SGST' | 'CESS' | 'TOTAL' | 'VALUE';

export interface ParsedFigure {
  id: string;
  sourceFile: string;
  docType: GstDocType;
  label: string;   // friendly label of what this figure represents
  value: number;
  head?: TaxHead;
}

export interface PortalFigureSet {
  caseId: string;
  figures: ParsedFigure[];
  updatedAt: string;
}

export type DocumentStatus = 'Pending' | 'Received' | 'Partly Received' | 'Clarification Required' | 'Completed';

export interface DocumentItem {
  id: string;
  caseId: string;
  docName: string;
  category: string; // 'Portal Report' | 'Invoices' | 'Ledger' | 'Agreement' | 'Vendor Undertaking'
  status: DocumentStatus;
  requestedDate: string;
  dueDate: string;
  receivedDate?: string;
  remarks?: string;
  period?: string;
  customFields?: Record<string, string>;
}

export interface DocumentMapping {
  id: string;
  templateName: string;
  docNameCol: string;
  categoryCol: string;
  statusCol: string;
  dueDateCol: string;
  remarksCol: string;
  periodCol: string;
}

export interface FigureSourceDetail {
  issueTitle: string;
  disputedAmount: number;
  departmentSource: string;
  portalTableReference: string;
  requiredPortalReport: string;
  verificationStep: string;
  isReportAvailable: boolean;
  missingReportAction: string;
  suggestedPortalPath: string;
}

export interface FirmSettings {
  caFirmName: string;
  caName: string;
  membershipNo: string;
  firmAddress: string;
  contactEmail: string;
  contactPhone: string;
  letterheadHeader?: string;
}
