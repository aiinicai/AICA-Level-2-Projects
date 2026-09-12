export type UserRole = 'ADMIN' | 'STANDARD_USER';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Company {
  id: number;
  name: string;
  short_name: string;
  logo_path?: string;
  address?: string;
  asset_id_prefix: string;
  numbering_format: string;
  starting_number: number;
  current_number: number;
  is_active: boolean;
  created_at: string;
}

export type AssetType = 'FIXED_ASSET' | 'STOCK';
export type CodeType = 'BARCODE' | 'QR_CODE';
export type AssetStatus = 'GENERATED' | 'PRINTED' | 'REPRINTED' | 'CANCELLED';

export interface Asset {
  id: number;
  company_id: number;
  company_name?: string;
  company_logo_path?: string;
  asset_id: string;
  asset_type: AssetType;
  description?: string;
  location?: string;
  sap_number?: string;
  serial_number?: string;
  department?: string;
  cost_centre?: string;
  custodian?: string;
  purchase_date?: string;
  code_type: CodeType;
  status: AssetStatus;
  print_count: number;
  is_override: boolean;
  override_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface DuplicateCheckResult {
  is_duplicate: boolean;
  existing_asset?: {
    id: number;
    asset_id: string;
    company_id: number;
    company_name: string;
    description: string;
    asset_type: string;
    location?: string;
    status: string;
    created_at: string;
    created_by: string;
  };
}

export interface BulkValidationRow {
  row_number: number;
  company_name?: string;
  company_id?: number;
  asset_id?: string;
  asset_type: string;
  sap_number?: string;
  description?: string;
  location?: string;
  serial_number?: string;
  department?: string;
  cost_centre?: string;
  custodian?: string;
  purchase_date?: string;
  code_type: string;
  status: 'VALID' | 'DUPLICATE_DB' | 'DUPLICATE_BATCH' | 'MISSING_REQUIRED' | 'INVALID_FORMAT';
  error_message?: string;
  existing_record?: any;
  override_reason?: string;
}

export interface BulkValidationSummary {
  total_rows: number;
  valid_count: number;
  duplicate_count: number;
  missing_fields_count: number;
  invalid_format_count: number;
  rows: BulkValidationRow[];
}

export interface TagTemplate {
  id: number;
  template_name: string;
  company_id?: number;
  width_mm: number;
  height_mm: number;
  code_type: CodeType;
  code_position: 'BOTTOM' | 'RIGHT';
  show_logo: boolean;
  show_company_name: boolean;
  field_visibility: Record<string, boolean>;
  font_settings: Record<string, any>;
  is_default: boolean;
}

export interface LabelSize {
  id: number;
  name: string;
  category: string;
  width_mm: number;
  height_mm: number;
  gap_mm: number;
  orientation: 'PORTRAIT' | 'LANDSCAPE';
  dpi: number;
  is_preset: boolean;
}

export interface PrinterInfo {
  name: string;
  is_default: boolean;
  driver_name: string;
  port: string;
}

export interface AuditLog {
  id: number;
  user_id?: number;
  user_email?: string;
  action: string;
  entity_type?: string;
  entity_id?: string;
  details?: string;
  result: string;
  ip_address?: string;
  created_at: string;
}

export interface DashboardStats {
  total_companies: number;
  total_tags_generated: number;
  tags_generated_today: number;
  fixed_assets_count: number;
  stock_assets_count: number;
  duplicate_attempts_count: number;
  duplicate_overrides_count: number;
  recent_activity: Array<{
    id: number;
    action: string;
    details: string;
    result: string;
    time: string;
    user: string;
  }>;
}

export interface CompanyStat {
  company_id: number;
  company_name: string;
  short_name: string;
  total_tags: number;
  fixed_assets: number;
  stock_assets: number;
  tags_today: number;
  last_asset_id?: string;
}
