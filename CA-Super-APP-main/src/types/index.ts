export type UserRole = 'admin' | 'staff';

export interface TaskAttachment {
  name: string;
  url: string;
  type: 'pdf' | 'image' | 'file';
  size: string;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  assignedTo?: string; // e.g. "Aman Deep", "Pooja Sharma", "Harpreet Singh", "Rohit Kumar", "All Staff"
  deadline?: string; // YYYY-MM-DD
  isUrgent?: boolean;
  completed: boolean;
  completedAt?: string;
  completedBy?: string;
  attachments: TaskAttachment[];
  createdAt: string;
  updatedAt?: string;
}

export type EventCategory = 'GST' | 'INCOME_TAX' | 'PUNJAB_FESTIVAL' | 'HOLIDAY' | 'GAZETTED_HOLIDAY' | 'STATUTORY';

export interface StatutoryEvent {
  id: string;
  title: string;
  date: string; // YYYY-MM-DD
  category: EventCategory;
  description: string;
  urgency: 'HIGH' | 'MEDIUM' | 'NORMAL';
  portalLink?: string;
}

export interface PartnerCredentials {
  name: string;
  membershipNo: string;
  userId: string;
  passwordHash: string;
  mobile: string;
  email: string;
}

export interface MSMEFixedDefaults {
  enterpriseType: string;
  organizationType: string;
  majorActivity: string;
  defaultNicCode: string;
  officeDistrict: string;
  officeState: string;
  defaultIfsc: string;
  depreciationMethod: string;
}

export interface ExtractedMsmeData {
  applicantName: string;
  panNumber: string;
  aadhaarMasked: string;
  mobileNumber: string;
  emailId: string;
  businessType: string;
  bankAccountNo: string;
  ifscCode: string;
  dateOfCommencement: string;
  plantMachineryInvestmentLakhs: string;
  annualTurnoverLakhs: string;
  nicCode: string;
  unitAddress: string;
  extractedFromDocCount?: number;
  confidenceScore?: number;
  notes?: string;
}

export interface AifAnalysisResult {
  eligibleProject: boolean;
  projectType: string;
  location: string;
  totalProjectCostLakhs: string;
  eligibleTermLoanLakhs: string;
  promoterContributionLakhs: string;
  interestSubventionRatePercent: number;
  subventionCapCrores: number;
  tenureYears: number;
  cgtmseCoverage: string;
  annualInterestSavingsLakhs: string;
  totalInterestSaved7YearsLakhs: string;
  eligibilityChecklist: Array<{ item: string; status: 'PASSED' | 'WARNING' | 'REQUIRED' }>;
  summaryRecommendation: string;
}
