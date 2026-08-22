export type FundType = 'PF' | 'ESI';

export type ComplianceStatus = 'ON_TIME' | 'DELAYED' | 'UNPAID';

export interface ChallanRecord {
  id: string;
  fundType: FundType;
  establishmentName: string;
  establishmentId: string; // Est ID or Employer Code
  wageMonth: string; // e.g. "April 2024" or "04/2024"
  wageMonthKey: string; // e.g. "2024-04" for chronological sorting
  financialYear: string; // e.g. "2024-2025"
  statutoryDueDate: string; // YYYY-MM-DD (e.g. "2024-05-15")
  actualPaymentDate: string; // YYYY-MM-DD (e.g. "2024-05-12")
  challanReference: string; // TRRN for PF, CRN/Challan No for ESI
  
  // Amounts
  employeeContribution: number; // Critical for 36(1)(va)
  employerContribution: number;
  adminOtherCharges: number;
  totalChallanAmount: number;
  
  // Tax Audit 3CD Clause 20(b) calculation
  status: ComplianceStatus;
  delayDays: number; // 0 if on time, >0 if delayed
  disallowableAmount: number; // Employee share if delayed, 0 if on-time
  
  // Metadata
  fileName?: string;
  fileType?: string;
  confidence?: number;
  rawExtractedNotes?: string;
}

export interface AssesseeDetails {
  name: string;
  pan: string;
  assessmentYear: string;
  financialYear: string;
  auditorName: string; // "CA Ietikka Gupta"
  auditorDesignation: string;
  membershipNumber?: string;
  firmName?: string;
  dateOfReport: string;
}

export interface AnalysisResponse {
  success: boolean;
  records: ChallanRecord[];
  warnings?: string[];
  message?: string;
}
