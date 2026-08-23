/**
 * ITR Word Generator - Type Definitions
 * Covers personal info, income heads, Chapter VI-A deductions, tax computation,
 * taxes paid & refund, and Word Document (.docx) template configuration.
 */

export interface ITRPersonalInfo {
  pan: string;
  aadhaar?: string;
  name: string;
  fatherName?: string;
  dob?: string;
  formType: 'ITR-1' | 'ITR-2' | 'ITR-3' | 'ITR-4' | 'ITR-5' | 'ITR-6' | 'ITR-7' | 'ITR-V' | 'Computation';
  assessmentYear: string; // e.g. "2024-25"
  financialYear: string;  // e.g. "2023-24"
  filingStatus: string;   // e.g. "139(1) - On or before due date"
  filingType: string;     // e.g. "Original" | "Revised" | "Defective" | "Updated"
  taxRegime: 'Old Regime' | 'New Regime';
  ackNumber?: string;
  filingDate?: string;
  address?: string;
  city?: string;
  state?: string;
  pincode?: string;
  mobile?: string;
  email?: string;
  status: 'Individual' | 'HUF' | 'Firm' | 'Company' | 'AOP/BOI' | 'Others';
  residentialStatus: 'Resident' | 'Non-Resident' | 'Resident but Not Ordinarily Resident (RNOR)';
  bankName?: string;
  bankAccountNumber?: string;
  bankIfsc?: string;
}

export interface ITRIncomeHeads {
  // 1. Income from Salary
  salaryGross: number;
  salaryExemptAllowances: number;
  salaryStandardDeduction: number;
  salaryProfessionalTax: number;
  salaryNet: number;

  // 2. Income from House Property
  housePropertyGross: number;
  housePropertyTaxes: number;
  housePropertyStandardDeduction: number; // 30% of NAV
  housePropertyInterest: number; // u/s 24(b)
  housePropertyNet: number;

  // 3. Profits and Gains of Business or Profession (PGBP)
  businessGrossReceipts: number;
  businessGrossProfit: number;
  businessExpenses: number;
  businessNetProfit: number;
  businessPresumptive44AD: number;
  businessPresumptive44ADA: number;

  // 4. Capital Gains
  capitalGainsSTCG_15Pct: number; // u/s 111A (pre-July 2024 or normal)
  capitalGainsSTCG_20Pct?: number; // u/s 111A @ 20% (Budget 2024 onwards)
  capitalGainsSTCG_Slab: number;
  capitalGainsLTCG_10Pct: number; // u/s 112A / without indexation
  capitalGainsLTCG_20Pct: number; // u/s 112 with indexation
  capitalGainsLTCG_12_5Pct: number; // Post July 2024 budget (12.5% u/s 112A)
  capitalGainsNet: number;

  // 5. Income from Other Sources
  otherSourcesInterestSavings: number;
  otherSourcesInterestDeposits: number;
  otherSourcesDividends: number;
  otherSourcesFamilyPension: number;
  otherSourcesOthers: number;
  otherSourcesDeductions: number; // u/s 57
  otherSourcesNet: number;

  // Gross Total Income (Sum of 1+2+3+4+5)
  grossTotalIncome: number;
}

export interface ITRDeductions {
  sec80C: number;
  sec80CCC: number;
  sec80CCD1: number;
  sec80CCD1B: number; // NPS additional 50k
  sec80CCD2: number;  // Employer NPS
  sec80D: number;     // Medical Insurance
  sec80DD: number;    // Handicapped Dependent
  sec80DDB: number;   // Medical Treatment
  sec80E: number;     // Education Loan Interest
  sec80EE: number;    // First Home Loan Interest
  sec80EEA: number;   // Affordable Housing
  sec80G: number;     // Donations
  sec80GG: number;    // Rent Paid
  sec80GGA: number;   // Scientific Research
  sec80TTA: number;   // Savings Interest (max 10,000)
  sec80TTB: number;   // Senior Citizen Interest (max 50,000)
  sec80U: number;     // Self Disability
  otherDeductions: number;
  totalDeductions: number;
}

export interface ITRTaxComputation {
  totalTaxableIncome: number; // Rounded off u/s 288A
  taxOnTotalIncome: number;
  specialRateTax: number;     // STCG 15%, LTCG 10%/20%
  rebate87A: number;
  taxAfterRebate: number;
  surcharge: number;
  cess: number;               // 4% Health and Education Cess
  grossTaxLiability: number;
  relief89: number;           // Relief u/s 89 (Salary arrears)
  relief90_91: number;        // Foreign tax relief
  netTaxLiability: number;
  interest234A: number;       // Delay in filing
  interest234B: number;       // Advance tax default
  interest234C: number;       // Advance tax deferment
  fee234F: number;            // Late filing fee
  totalTaxAndInterest: number;
}

export interface ITRTaxesPaid {
  advanceTax: number;
  tdsSalary: number;
  tdsNonSalary: number;
  tcs: number;
  selfAssessmentTax: number;
  totalTaxesPaid: number;
  refundDue: number;          // Refund if paid > liability
  taxPayable: number;         // Balance tax payable if liability > paid (Rounded u/s 288B)
}

export interface CASignatoryDetails {
  includeCASection: boolean;
  caName: string;
  firmName: string;
  membershipNo: string;
  firmRegistrationNo: string;
  udin: string;
  place: string;
  date: string;
}

export interface DocxStyleConfig {
  documentTitle: string;
  subtitle: string;
  themeColor: 'navy' | 'slate' | 'emerald' | 'burgundy' | 'classic';
  fontFamily: 'Calibri' | 'Arial' | 'Times New Roman' | 'Segoe UI' | 'Garamond';
  includeHeaderFooter: boolean;
  includeIndianRupeeWords: boolean;
  includeTaxComputationTable: boolean;
  includeDeductionsBreakdown: boolean;
  includeTaxesPaidBreakdown: boolean;
  includeBankDetails: boolean;
  includeVerificationClause: boolean;
  includeRegimeComparison?: boolean;
  watermarkText?: string;
  fontSize: 'standard' | 'compact' | 'large';
  layoutType: 'standard_computation' | 'audit_detailed' | 'executive_summary' | 'bank_loan_format';
}

export interface FieldSourceTrace {
  raw?: string;
  page?: number;
  confidence: 'high' | 'medium' | 'low' | 'manual';
}

export interface CompleteITRData {
  id: string;
  sourceFileName?: string;
  extractionConfidence?: number;
  extractionMethod?: 'pdf_text' | 'json_efiling' | 'gemini_ai' | 'manual_sample';
  fieldSources?: Record<string, FieldSourceTrace>;
  personalInfo: ITRPersonalInfo;
  incomeHeads: ITRIncomeHeads;
  deductions: ITRDeductions;
  taxComputation: ITRTaxComputation;
  taxesPaid: ITRTaxesPaid;
  caDetails: CASignatoryDetails;
  styleConfig: DocxStyleConfig;
  notes?: string;
}

export interface ExtractionStatus {
  step: 'idle' | 'reading_file' | 'extracting_text' | 'parsing_fields' | 'validating_math' | 'ready' | 'error';
  progress: number; // 0 to 100
  message: string;
  extractedFieldsCount: number;
  warnings: string[];
  error?: string;
}
