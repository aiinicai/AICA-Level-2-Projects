export interface Client {
  id: number;
  name: string;
  entity_type: string;
  reporting_period: string;
  previous_year_period: string;
  currency: string;
  accounting_framework: string;
  schedule_format: string;
  prepared_by: string;
  reviewed_by: string;
  created_at: string;
}

export interface TrialBalanceLine {
  id: number;
  ledger_code?: string;
  ledger_name: string;
  original_group?: string;
  cy_amount: number;
  py_amount: number;
  type?: string;
  suggested_classification?: string;
  final_classification?: string;
  financial_statement?: string;
  note_number?: string;
  current_non_current?: string;
  user_override: boolean;
}

export interface MappingRule {
  id: number;
  pattern: string;
  target_classification: string;
  target_statement: string;
  note_number?: string;
  current_non_current?: string;
}

export interface BalanceSheetLine {
  particulars: string;
  note_number: string;
  cy_amount: number;
  py_amount: number;
  is_header?: boolean;
  is_subtotal?: boolean;
  is_total?: boolean;
}

export interface ProfitAndLossLine {
  particulars: string;
  note_number: string;
  cy_amount: number;
  py_amount: number;
  is_header?: boolean;
  is_subtotal?: boolean;
  is_total?: boolean;
}

export interface FinancialStatements {
  balance_sheet: BalanceSheetLine[];
  profit_and_loss: ProfitAndLossLine[];
  is_tallied: boolean;
  difference: number;
}

export interface Note {
  id: number;
  note_number: string;
  title: string;
  content: string;
  suggested_content: string;
  table_json?: string;
  is_modified: boolean;
}

export interface AccountingPolicy {
  id: number;
  policy_number: string;
  title: string;
  content: string;
  suggested_content: string;
  is_applicable: boolean;
  is_modified: boolean;
}

export interface RatioItem {
  code: string;
  name: string;
  formula: string;
  cy_value: number;
  py_value: number;
  unit: string;
  movement: string;
  interpretation: string;
}

export interface ValidationItem {
  code: string;
  check_name: string;
  category: string;
  status: 'Passed' | 'Warning' | 'Critical';
  message: string;
  details: string;
}

export interface SupportingSchedules {
  ar: any[];
  ap: any[];
  cwip: any[];
  rpt: any[];
  borrowings: any[];
  contingencies: any[];
}

export type UserRole =
  | 'System Administrator'
  | 'Partner'
  | 'Director'
  | 'Manager'
  | 'Assistant Manager'
  | 'Executive'
  | 'Article Assistant'
  | 'Viewer';

export interface User {
  id: number;
  employee_code: string;
  name: string;
  email: string;
  mobile?: string;
  department: string;
  role: UserRole;
  is_active: boolean;
  last_login?: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
  user: User;
}

