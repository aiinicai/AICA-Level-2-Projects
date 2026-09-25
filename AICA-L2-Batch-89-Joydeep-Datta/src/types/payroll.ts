export type Gender = 'Male' | 'Female' | 'Other';
export type EmploymentStatus = 'Active' | 'New Joiner' | 'Resigned' | 'Exited' | 'On Leave (LWP)';
export type TaxRegime = 'Old' | 'New';
export type RevisionReason = 'New Appointment' | 'Annual Revision' | 'Promotion' | 'Correction' | 'Exit';
export type PaymentMode = 'Bank Transfer' | 'Cheque' | 'Cash';
export type DeclarationType = 'Proposed' | 'Actual (Proofs Submitted)';
export type ProofStatus = 'Pending' | 'Submitted' | 'Verified' | 'Partially Rejected' | 'Rejected';
export type DisabilityLevel = 'None' | 'Disability' | 'Severe Disability';

export interface EmployeeMaster {
  // Identity
  employeeCode: string;
  employeeName: string;
  pan: string;
  dateOfBirth: string; // YYYY-MM-DD or DD-MM-YYYY
  gender: Gender;

  // Employment
  dateOfJoining: string;
  dateOfLeaving?: string;
  employmentStatus: EmploymentStatus;
  department: string;
  designation: string;
  locationCity: string;
  metroFlag: 'Y' | 'N';
  costCenter: string;

  // Contact
  email: string;
  mobile: string;

  // Bank
  bankName: string;
  bankAccountNo: string;
  ifsc: string;

  // Statutory
  uan: string;
  pfNumber: string;
  pfApplicable: 'Y' | 'N';
  pfWageCeilingApplied: 'Y' | 'N'; // Y = restrict to 15,000, N = actual basic
  esiApplicable: 'Y' | 'N';

  // Tax
  taxRegimeOpted: TaxRegime;
  regimeDeclarationDate?: string;

  // Salary Effective
  salaryEffectiveFrom: string;
  revisionReason: RevisionReason;
  annualCtc: number;

  // Monthly Earnings
  basicMonthly: number;
  hraMonthly: number;
  conveyanceAllowanceMonthly: number;
  childrenEducationAllowanceMonthly: number;
  ltaMonthly: number;
  specialAllowanceMonthly: number;
  otherAllowanceMonthly: number;

  // Annual Earnings
  variablePayAnnual: number;
  joiningBonus: number;

  // Employer Cost
  employerPfMonthly: number;
  employerNpsMonthly: number;
  gratuityProvisionMonthly: number;

  // Deductions
  employeePfMonthly: number;
  professionalTaxMonthly: number; // 0 per instructions
  otherRecurringDeductionMonthly: number;

  // Control
  paymentMode: PaymentMode;
  remarks?: string;
}

export interface EmployeeDeclaration {
  employeeCode: string;
  employeeName?: string;
  pan?: string;
  financialYear: string; // e.g. "2026-27"
  declarationType: DeclarationType;
  declarationDate: string;
  regimeDeclared: TaxRegime;
  proofStatus: ProofStatus;

  // HRA (Old regime)
  rentPaidAnnual: number;
  rentFromDate?: string;
  rentToDate?: string;
  rentedCityMetro: 'Y' | 'N';
  landlordName?: string;
  landlordPan?: string;

  // House Property
  housingLoanInterestSelfOccupied: number; // Sec 24(b) capped at 2,00,000
  letOutPropertyNetIncome: number; // Rent less 30% std ded less interest
  lenderName?: string;
  lenderPan?: string;

  // Sec 80C
  housingLoanPrincipal: number;
  ppf: number;
  licPremium: number;
  elssMutualFund: number;
  nsc: number;
  tuitionFees: number;
  sukanyaSamriddhi: number;
  taxSaverFd5yr: number;
  other80C: number;

  // NPS
  npsSelf80CCD1B: number; // Max 50,000
  optInEmployerNps80CCD2: 'Y' | 'N';

  // Sec 80D
  mediclaimSelfFamily: number;
  mediclaimParents: number;
  parentsSeniorCitizen: 'Y' | 'N';
  preventiveHealthCheckup: number;
  medicalExpenditureSeniorCitizen: number;

  // Other Chapter VI-A
  sec80DDDisabledDependent: DisabilityLevel;
  sec80DDBMedicalTreatment: number;
  sec80EEducationLoanInterest: number;
  sec80EEBEVLoanInterest: number;
  sec80GDonation100pct: number;
  sec80GDonation50pct: number;
  sec80USelfDisability: DisabilityLevel;

  // Exemptions u/s 10
  ltaExemptionClaimed: number;
  otherExemptionSec10: number;

  // Other Income
  savingsBankInterest: number;
  fixedDepositInterest: number;
  otherIncomeDeclared: number;

  // Previous Employer (Mid-year joiners)
  prevEmployerName?: string;
  prevEmployerGrossSalary: number;
  prevEmployerExemptionsSec10: number;
  prevEmployerPfDeducted: number;
  prevEmployerPtDeducted: number;
  prevEmployerTdsDeducted: number;

  remarks?: string;
}

export interface TaxSlab {
  from: number;
  to: number | null;
  rate: number;
}

export interface TaxConfig {
  schemaVersion: string;
  financialYear: string;
  assessmentYear: string;
  status: 'APPROVED' | 'DRAFT';
  approval: {
    approvedBy: string;
    approvedOn: string;
    sourceUrl: string;
    sourceDocument: string;
    sourceRetrievedOn: string;
    sourceSha256: string;
    basis: string;
    contentSha256: string;
    notes: string;
  };
  regimes: {
    OLD: {
      label: string;
      standardDeduction: number;
      slabs: {
        NORMAL: TaxSlab[];
        SENIOR: TaxSlab[];
        SUPER_SENIOR: TaxSlab[];
      };
      rebate87A: {
        incomeCeiling: number;
        maxRebate: number;
        marginalRelief: boolean;
      };
      surcharge: TaxSlab[];
      cessRate: number;
      allows: {
        hraExemption: boolean;
        ltaExemption: boolean;
        sec24bSelfOccupiedCap: number;
        chapterVia: boolean;
        sec80CCD2EmployerNpsPctOfBasic: number;
        childrenEducationAllowancePerChildPm: number;
        maxChildrenForCea: number;
      };
      chapterViaCaps: Record<string, number>;
    };
    NEW: {
      label: string;
      standardDeduction: number;
      slabs: {
        ALL: TaxSlab[];
      };
      rebate87A: {
        incomeCeiling: number;
        maxRebate: number;
        marginalRelief: boolean;
      };
      surcharge: TaxSlab[];
      cessRate: number;
      allows: {
        hraExemption: boolean;
        ltaExemption: boolean;
        sec24bSelfOccupiedCap: number;
        chapterVia: boolean;
        sec80CCD2EmployerNpsPctOfBasic: number;
        childrenEducationAllowancePerChildPm: number;
        maxChildrenForCea: number;
      };
      chapterViaCaps: Record<string, number>;
    };
  };
  common: {
    seniorAge: number;
    superSeniorAge: number;
    surchargeMarginalRelief: boolean;
    noPanTdsRate206AA: number;
    hraMetroPctOfBasic: number;
    hraNonMetroPctOfBasic: number;
    hraRentLessPctOfBasic: number;
    landlordPanRequiredAboveAnnualRent: number;
    pfWageCeiling: number;
    pfEmployeeRate: number;
    pfEmployerRate: number;
    employerPfNpsSuperTaxableThreshold: number;
  };
}

export interface TaxCalculationBreakdown {
  regime: TaxRegime;
  annualGrossSalary: number;
  exemptionsSec10: {
    hra: number;
    cea: number;
    lta: number;
    other: number;
    total: number;
  };
  grossSalaryAfterSec10: number;
  standardDeduction: number;
  incomeUnderHeadSalaries: number;
  incomeFromHouseProperty: number; // Loss is negative, capped at 2L Old regime
  incomeFromOtherSources: number;
  grossTotalIncome: number;
  chapterViaDeductions: {
    sec80C: number;
    sec80CCD1B: number;
    sec80CCD2: number;
    sec80D: number;
    sec80E: number;
    sec80EEB: number;
    sec80G: number;
    sec80DD: number;
    sec80U: number;
    sec80TTA_TTB: number;
    total: number;
  };
  netTaxableIncome: number;
  taxOnIncome: number;
  rebate87A: number;
  taxAfterRebate: number;
  surcharge: number;
  cess: number;
  totalAnnualTaxLiability: number;
  tdsCreditPreviousEmployer: number;
  tdsDeductedYtd: number;
  remainingTaxToDeduct: number;
  remainingMonths: number;
  currentMonthTds: number;
}

export interface MonthlySalaryRecord {
  employeeCode: string;
  employeeName: string;
  designation: string;
  department: string;
  pan: string;
  bankAccountNo: string;
  bankName: string;
  ifsc: string;
  employmentStatus: EmploymentStatus;
  
  // Proration details
  month: number; // 1 = April, 12 = March (Indian FY)
  monthName: string;
  year: number;
  totalDaysInMonth: number;
  payableDays: number;
  lopDays: number;
  prorationFactor: number;

  // Earnings (Prorated)
  basicEarned: number;
  hraEarned: number;
  conveyanceEarned: number;
  ceaEarned: number;
  ltaEarned: number;
  specialAllowanceEarned: number;
  otherAllowanceEarned: number;
  variablePayEarned: number;
  joiningBonusEarned: number;
  grossEarned: number;

  // Deductions
  employeePf: number;
  esi: number;
  professionalTax: number; // 0
  otherDeductions: number;
  tdsDeducted: number;
  totalDeductions: number;

  // Net Pay
  netPay: number;

  // Employer contributions
  employerPf: number;
  employerNps: number;
  gratuityProvision: number;
  totalEmployerCost: number;

  // Tax Info
  regimeApplied: TaxRegime;
  annualTaxLiability: number;
  oldRegimeTax: number;
  newRegimeTax: number;
  regimeSavingRecommendation: string;
  taxCalculation: TaxCalculationBreakdown;
}

export interface PayrollRunSummary {
  financialYear: string;
  month: number; // 1-12 (1 = April)
  monthLabel: string;
  runDate: string;
  headcount: number;
  totalGross: number;
  totalPf: number;
  totalEsi: number;
  totalTds: number;
  totalOtherDeductions: number;
  totalDeductions: number;
  totalNetPayout: number;
  totalEmployerCost: number;
  records: MonthlySalaryRecord[];
}
