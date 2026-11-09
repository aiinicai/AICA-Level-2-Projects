export type UserRole = 'admin' | 'analyst' | 'reviewer' | 'client';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  client_id?: string | null;
  created_at: string;
}

export interface Client {
  id: string;
  client_code: string;
  primary_contact_name: string;
  phone: string;
  email: string;
  constitution: string;
  address?: string;
  city?: string;
  state?: string;
  pin_code?: string;
  is_deleted?: boolean;
  created_at: string;
  entities: Entity[];
}

export interface Entity {
  id: string;
  client_id: string;
  legal_name: string;
  trade_name?: string;
  constitution: string;
  pan_masked?: string;
  cin?: string;
  udyam_reg?: string;
  date_of_incorporation?: string;
  business_activity?: string;
  registered_address?: string;
  promoters?: Promoter[];
  gst_registrations?: GSTRegistration[];
  bank_accounts?: BankAccount[];
  existing_facilities?: ExistingFacility[];
}

export interface Promoter {
  id: string;
  entity_id: string;
  name: string;
  role: string;
  pan_masked?: string;
  din?: string;
  ownership_pct: number;
  cibil_score?: number;
  mobile?: string;
  email?: string;
}

export interface GSTRegistration {
  id: string;
  entity_id: string;
  gstin: string;
  gstin_masked?: string;
  state?: string;
  status: string;
  filing_frequency: string;
}

export interface BankAccount {
  id: string;
  entity_id: string;
  bank_name: string;
  branch?: string;
  account_type: string;
  account_number_masked: string;
  ifsc?: string;
  average_monthly_balance: number | string;
  statement_from?: string;
  statement_to?: string;
}

export interface ExistingFacility {
  id: string;
  entity_id: string;
  lender_name: string;
  facility_type: string;
  sanctioned_limit: number | string;
  outstanding_balance: number | string;
  interest_rate: number;
  monthly_emi: number | string;
  residual_tenure_months: number;
  primary_security?: string;
  collateral_security?: string;
  sanction_date?: string;
  renewal_date?: string;
}

export type ProposalStatus = 
  | 'lead' 
  | 'onboarding' 
  | 'proposal_draft' 
  | 'document_collection' 
  | 'extraction_verification' 
  | 'financial_analysis' 
  | 'lender_comparison' 
  | 'reviewer_approval' 
  | 'report_generation' 
  | 'submission_tracking' 
  | 'sanctioned' 
  | 'rejected'
  | 'closed_won'
  | 'closed_lost';

export type ProductType = 
  | 'home_loan' 
  | 'lap' 
  | 'business_loan_secured' 
  | 'business_loan_unsecured' 
  | 'cash_credit_od' 
  | 'working_capital' 
  | 'project_finance_term_loan' 
  | 'balance_transfer_topup';

export interface Proposal {
  id: string;
  proposal_code: string;
  client_id: string;
  entity_id: string;
  product_type: ProductType;
  requested_amount: number | string;
  tenure_months: number;
  purpose?: string;
  target_rate: number;
  status: ProposalStatus;
  assigned_analyst_id?: string;
  assigned_reviewer_id?: string;
  review_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentChecklistItem {
  id: string;
  proposal_id: string;
  document_name: string;
  category: string;
  is_applicable: boolean;
  na_reason?: string;
  is_received: boolean;
  period_required?: string;
  verification_status: 'requested' | 'partially_received' | 'received' | 'verified' | 'rejected' | 'expired' | 'superseded' | 'not_applicable';
  missing_details?: string;
  remarks?: string;
}

export interface ExtractedDataRecord {
  id: string;
  proposal_id: string;
  document_id: string;
  page_or_sheet?: string;
  financial_period?: string;
  metric_name: string;
  raw_value?: string;
  normalized_value?: number | string;
  confidence: number;
  verification_status: 'unverified' | 'verified' | 'adjusted' | 'rejected';
  reviewer_notes?: string;
  created_at: string;
}

export interface FinancialEvaluationResponse {
  proposal_id: string;
  requested_amount: number | string;
  proposed_emi: number | string;
  foir_pct: number;
  ltv_pct: number;
  dscr: number;
  icr: number;
  current_ratio: number;
  quick_ratio: number;
  debt_equity_ratio: number;
  tol_tnw_ratio: number;
  debtor_days: number;
  inventory_days: number;
  creditor_days: number;
  net_working_capital_cycle_days: number;
  eligible_loan_foir: number | string;
  eligible_loan_ltv: number | string;
  eligible_loan_dscr: number | string;
  preliminary_eligible_amount: number | string;
  limiting_factor: string;
  disclaimer: string;
}

export interface PolicyFitEvaluation {
  lender_id: string;
  lender_code: string;
  lender_name: string;
  product_type: string;
  policy_name?: string;
  fit_status: 'ELIGIBLE' | 'BORDERLINE' | 'INELIGIBLE';
  max_eligible_amount: number | string;
  benchmark_rate: number;
  deviations: string[];
  missing_inputs: string[];
  notes?: string;
}

export interface DossierFile {
  relative_path: string;
  filename: string;
  folder: string;
  category: string;
  size_bytes: number;
}

export interface CMAProjectData {
  years: string[];
  operating_statement: Record<string, number[]>;
  balance_sheet: Record<string, number[]>;
  ratios: Record<string, number[]>;
  working_capital_assessment: Array<{
    year: string;
    turnover: number;
    nayak_total_requirement: number;
    nayak_promoter_margin: number;
    nayak_mpbf: number;
    wcg: number;
    tandon_margin: number;
    tandon_mpbf: number;
  }>;
  balance_sheet_balanced: boolean;
  max_discrepancy: number;
}

export interface LocationCity {
  id?: string;
  city: string;
  state: string;
  tier?: string;
}

export interface PANValidationResult {
  pan: string;
  is_valid: boolean;
  status: 'VALID' | 'INVALID';
  entity_type: string;
  entity_type_code: string;
  constitution_match: boolean;
  name_match?: boolean | null;
  expected_constitution?: string | null;
  pan_type: string;
  verification_source: string;
  message: string;
  normalized_pan: string;
}

export interface CompanyProfile {
  id: string;
  company_code: string;
  company_name: string;
  brand_name: string;
  tagline?: string;
  logo_data?: string | null;
  primary_color: string;
  secondary_color: string;
  website?: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  pin_code?: string;
  pan?: string;
  gstin?: string;
  cin?: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
}
