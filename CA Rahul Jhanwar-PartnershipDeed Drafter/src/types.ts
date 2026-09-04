export interface Partner {
  id: string;
  titlePrefix?: 'MR.' | 'MRS.' | 'MISS' | 'SMT.' | 'DR.' | '';
  name: string;
  relationType: 'FATHER' | 'HUSBAND';
  parentName: string;
  pan: string;
  aadhaar?: string;
  dob: string;
  age: string;
  address: string;
  profitShare: string;
  isWorking: boolean;
  salaryMonthly?: string;
  salaryAnnual?: string;
  // Attached KYC documents
  panCardFrontUrl?: string;
  panCardFileName?: string;
  aadhaarCardFrontUrl?: string;
  aadhaarFrontFileName?: string;
  aadhaarCardBackUrl?: string;
  aadhaarBackFileName?: string;
  idOcrStatus?: 'idle' | 'extracting' | 'extracted' | 'error';
  idOcrMessage?: string;
}

export interface CustomClause {
  id: string;
  title: string;
  content: string;
  enabled: boolean;
}

export interface Witness {
  id: string;
  name: string;
  parentName: string;
  address: string;
}

export type DeedType = 'original' | 'supplementary' | 'dissolution';

export interface PriorDeedRecord {
  id: string;
  deedType: 'original' | 'supplementary' | 'reconstitution' | 'amendment';
  deedLabel: string;
  executionDate: string;
  effectiveDate?: string;
  executionCity?: string;
  rofRegistrationNumber?: string;
  keyChangesSummary: string;
  fileName?: string;
}

export interface SupplementaryConfig {
  originalDeedDate: string;
  originalDeedCity: string;
  originalRegistrationNumber: string;
  effectiveDate: string;
  priorDeeds?: PriorDeedRecord[];
  
  // Selected modifications
  changePartners: boolean;
  changeClauses: boolean;
  changeRemuneration: boolean;
  changeOtherConditions: boolean;

  // 1. Change in Partners
  retiringPartnerIds: string[];
  retirementEffectiveDate: string;
  retirementSettlementTerms: string;
  incomingPartners: Partner[];
  admissionEffectiveDate: string;
  admissionTerms: string;
  revisedProfitShares: Record<string, string>; // partnerId -> percentage

  // 2. Change in Clauses
  changeFirmName: boolean;
  newFirmName: string;
  changeAddress: boolean;
  newFirmAddress: string;
  changeObjects: boolean;
  newObjects: string;
  customAmendedClauses: Array<{
    id: string;
    clauseNumberOrTitle: string;
    originalText?: string;
    amendedText: string;
  }>;

  // 3. Change in Remuneration
  remunType: 'it_act_2025' | 'fixed_salary' | 'fixed_ratio' | 'custom';
  remunDistribution: 'ratio' | 'equal';
  partnerSalaries?: Record<string, string>; // partnerId -> monthly salary
  revisedRemunText: string;
  changeInterestRate: boolean;
  revisedInterestRate: string;

  // 4. Any other condition
  changeBankOperation: boolean;
  newBankOperationTerms: string;
  additionalClauses: CustomClause[];
  ratificationClause: string;
}

export interface DissolutionConfig {
  originalDeedDate: string;
  originalDeedCity: string;
  originalRegistrationNumber: string;
  dissolutionDate: string;
  priorDeeds?: PriorDeedRecord[];
  dissolutionReason: 'mutual_consent' | 'completion_of_venture' | 'retirement_no_substitute' | 'custom';
  customReasonText: string;
  cessationOfBusiness: string;
  realizationOfAssets: string;
  dischargeOfLiabilities: string;
  divisionOfSurplus: string;
  custodianPartnerId: string;
  custodianPartnerName: string;
  recordsRetentionYears: string;
  publicNoticeNewspapers: string;
  registrarNotification: boolean;
  mutualIndemnityTerms: string;
  bankAccountSettlement: string;
}

export interface DeedFormData {
  deedType?: DeedType;
  execCity: string;
  execDate: string;
  firmName: string;
  firmPan: string;
  commDate: string;
  interestRate: string;
  firmAddress: string;
  rawBusinessIdea: string;
  firmObjects: string;
  remunType: 'it_act_2025' | 'fixed_salary' | 'fixed_ratio';
  remunDistribution: 'ratio' | 'equal';
  nonCompete: boolean;
  clientOwnership: boolean;
  partners: Partner[];
  witnesses: Witness[];
  customClauses: CustomClause[];
  stampDutyAmount?: string;
  includeStampPlaceholder?: boolean;
  includeCoverPage?: boolean;
  coverPageTitle?: string;
  coverPagePreparedBy?: string;
  includeCoverRegistrationBox?: boolean;
  showPageNumbers?: boolean;
  pageNumberFormat?: 'page_x_of_y' | 'page_x' | 'hyphen_x';
  includeCoverInPageNumbering?: boolean;
  customTotalPages?: string;
  startPageNumber?: number;
  signaturePageBreak?: 'continuous' | 'newPage';
  pageBreakBeforeClauses?: string[];
  documentDensity?: 'standard' | 'compact' | 'tight';
  fontSize?: '11pt' | '12pt' | '13pt';
  // KYC Annexure / Stamp Paper Backside Notary Endorsement Page
  includeKycAnnexure?: boolean;
  kycAnnexureTitle?: string;
  kycAnnexureLayout?: 'per_partner' | 'consolidated';
  includeNotaryAttestationBox?: boolean;
  includeSelfAttestationBox?: boolean;

  // New Formats Configuration
  supplementaryConfig?: SupplementaryConfig;
  dissolutionConfig?: DissolutionConfig;
  priorDeeds?: PriorDeedRecord[];
  uploadedDeedFileName?: string;
  uploadedDeedExtractionStatus?: 'idle' | 'extracting' | 'extracted' | 'error';
  uploadedDeedExtractionNotice?: string;
}

export interface IndustryPreset {
  id: string;
  label: string;
  iconName: string;
  firmName: string;
  businessIdea: string;
  firmObjects: string;
}
