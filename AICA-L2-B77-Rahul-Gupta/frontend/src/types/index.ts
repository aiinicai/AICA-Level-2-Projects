/** Shared API types. */

export interface RunSummary {
  id: string;
  enterprise_value: number | null;
  equity_value: number | null;
  central_estimate: number | null;
  range_low: number | null;
  range_high: number | null;
  per_share_value: number | null;
  confidence_label: string;
  confidence_score: number;
  readiness_score: number;
  methods: string[] | Record<string, MethodResult>;
  created_at: string;
  run_label?: string;
  analyst?: string;
  assumptions?: Record<string, number>;
  weights?: Record<string, number>;
  detail?: RunDetail;
  is_current?: boolean;
}

export interface MethodResult {
  enterprise_value: number | null;
  equity_value: number | null;
  per_share_value: number | null;
  weight: number;
  key_driver: string;
}

export interface RunDetail {
  result: {
    methods: Record<string, any>;
    weights: Record<string, number>;
    bridge: { total_debt: number; cash: number; shares_outstanding: number };
  };
  scenarios: Record<string, Scenario>;
  sensitivity_heatmap: Heatmap;
  tornado: TornadoRow[];
  assumption_impacts: ImpactRow[];
  confidence: { score: number; label: string; basis: Record<string, number> };
  readiness: Readiness;
  inputs: Record<string, number | null>;
}

export interface Scenario {
  assumptions: Record<string, number>;
  enterprise_value: number;
  equity_value: number;
  vs_base_pct: number | null;
}

export interface Heatmap {
  wacc_values: number[];
  growth_values: number[];
  grid: (number | null)[][];
  output: string;
}

export interface TornadoRow {
  key: string;
  label: string;
  delta: number;
  low: number | null;
  high: number | null;
  base: number;
  span: number;
}

export interface ImpactRow {
  key: string;
  label: string;
  change: string;
  impact: number;
  impact_pct: number | null;
}

export interface Readiness {
  score: number;
  label: string;
  band: string;
  components: Record<string, number>;
}

export interface CaseSummary {
  id: string;
  company_id: string;
  company_name: string;
  industry: string;
  entity_type: string;
  country: string;
  valuation_date: string;
  currency: string;
  units: string;
  purpose: string;
  promoter_holding_pct: number;
  total_shares: number;
  notes: string;
  status: string;
  financials_locked: boolean;
  updated_at: string | null;
  current_run: RunSummary | null;
  readiness?: Readiness;
}

export interface DashboardData {
  total_cases: number;
  completed: number;
  in_progress: number;
  avg_valuation: number | null;
  readiness: number;
  recent: CaseSummary[];
  trend: { month: string; value: number }[];
  method_comparison: { method: string; value: number }[];
  active_case_id: string | null;
}

export interface LineItem {
  id: string;
  statement?: string;
  metric: string;
  label: string;
  period_label: string;
  python_value: number | null;
  ai_visual_value: number | null;
  approved_value: number | null;
  original_label: string;
  original_display: string;
  unit: string;
  source_document_id: string | null;
  source_page: number;
  verification_status: string;
  confidence: number;
  review_note: string;
}

export interface FinancialsData {
  locked: boolean;
  periods: string[];
  items: Record<string, LineItem[]>;
  counts: {
    total: number;
    verified: number;
    needs_review: number;
    low_confidence: number;
    unverified: number;
  };
  validation: {
    checks: { code: string; name: string; period: string; status: string; detail: string }[];
    passed: number;
    failed: number;
    skipped: number;
    ok: boolean;
  };
  documents: DocumentInfo[];
  extraction_counts: { raw_items: number; verifications: number };
}

export interface DocumentInfo {
  id: string;
  original_filename: string;
  fiscal_year_label: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  status: string;
  page_count: number;
  has_native_text: boolean;
  error: string;
  uploaded_at: string;
}

export interface Question {
  id: string;
  code: string;
  category: string;
  category_label: string;
  priority: string;
  reason: string;
  trigger_rule: string;
  question: string;
  type: string;
  options: string[];
  valuation_impact: string[];
  status: string;
  order_index: number;
}

export interface InterviewState {
  session: { id: string; status: string; total: number; answered: number } | null;
  current_question: Question | null;
  current_number: number;
  categories: { category: string; total: number; answered: number }[];
  financial_context: {
    revenue_latest: number | null;
    revenue_cagr: number | null;
    revenue_growth: number | null;
    ebitda_margin: number | null;
    pat_latest: number | null;
    latest_period: string | null;
  };
  readiness: Readiness;
  interpretation_so_far: string;
  answers: { question_id: string; value: unknown; signal: string; interpretation: string }[];
}

export interface Assumption {
  key: string;
  label: string;
  kind: string;
  min: number;
  max: number;
  value: number | null;
  source: string;
  status: string;
  ai_recommended_value: number | null;
  ai_reason: string;
}

export interface SimulationResult {
  enterprise_value: number;
  equity_value: number;
  per_share_value: number | null;
  range_low: number;
  range_high: number;
  methods: Record<string, { enterprise_value: number; equity_value: number }>;
  bridge: { total_debt: number; cash: number; shares_outstanding: number };
  vs_current_pct: number | null;
  tornado: TornadoRow[];
  assumption_impacts: ImpactRow[];
  scenarios: Record<string, Scenario>;
}

export interface Insight {
  id: string;
  section: string;
  title: string;
  body: string;
  severity: string;
  source: string;
  data: Record<string, unknown>;
}

export interface ReportInfo {
  id: string;
  case_id: string;
  template: string;
  title: string;
  status: string;
  has_pdf: boolean;
  has_html: boolean;
  created_at: string;
}

export interface Trigger {
  rule_code: string;
  metric: string;
  observed_value: number | null;
  threshold: number | null;
  severity: string;
  action: string;
  message: string;
  status: string;
}

export interface AIConfig {
  provider: string;
  model: string;
  model_display: string;
  temperature: number;
  structured_output: boolean;
  visual_verification: boolean;
  ai_final_report: boolean;
  key_set: boolean;
  key_tail: string;
  connected: boolean;
  test_error?: string;
}

export interface SettingsData {
  ai: AIConfig;
  profile: {
    name: string;
    role: string;
    email: string;
    timezone: string;
    date_format: string;
    number_format: string;
  };
  preferences: Record<string, string | number | boolean>;
}
