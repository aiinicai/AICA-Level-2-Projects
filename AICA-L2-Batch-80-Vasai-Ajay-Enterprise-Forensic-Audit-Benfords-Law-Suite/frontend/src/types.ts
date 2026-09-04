export interface IngestionResult {
  success: boolean;
  file_path: string;
  file_name: string;
  row_count: number;
  columns: string[];
  column_mapping: {
    amount?: string;
    date?: string;
    vendor?: string;
    invoice_no?: string;
    description?: string;
  };
  dataset_hash: string;
  error_message?: string;
  limitation_warning?: string;
  recommendation?: string;
  sample_records: Record<string, any>[];
  pii_classifications?: Record<string, {
    detected_pii_type: string;
    confidence: string;
    is_pii: boolean;
    recommended_action: string;
    sample_count: number;
  }>;
}

export interface DigitItem {
  digit: number;
  digit_label: string;
  count: number;
  expected_count: number;
  observed_prob: number;
  expected_prob: number;
  observed_pct: number;
  expected_pct: number;
  difference: number;
  abs_diff: number;
  z_score: number;
  is_spike: boolean;
  is_significant_95: boolean;
  is_significant_99: boolean;
  row_indices: number[];
}

export interface DigitTestResult {
  test_type: string;
  mad: number;
  conformity_rating: string;
  risk_level: string;
  badge_color: string;
  chi2_statistic: number;
  chi2_dof: number;
  chi2_p_value: number;
  ks_statistic: number;
  ks_critical_95: number;
  ks_significant: boolean;
  spike_digits: number[];
  items: DigitItem[];
}

export interface MantissaResult {
  mean_mantissa: number;
  expected_mean: number;
  variance_mantissa: number;
  expected_variance: number;
  skewness: number;
  kurtosis: number;
  center_of_gravity_x: number;
  center_of_gravity_y: number;
  center_of_gravity_radius: number;
  is_conforming: boolean;
  status: string;
  histogram: {
    bin_label: string;
    count: number;
    observed_prob: number;
    expected_prob: number;
    difference: number;
  }[];
}

export interface BenfordSuiteResponse {
  success: boolean;
  total_rows: number;
  valid_rows: number;
  excluded_rows: number;
  amount_column: string;
  overall_summary: {
    conformity_rating: string;
    risk_level: string;
    badge_color: string;
    mad_f2d: number;
    mad_1d: number;
    mad_2d: number;
    sample_size_adequate: boolean;
    nigrini_primary_test: string;
  };
  first_digit: DigitTestResult;
  second_digit: DigitTestResult;
  first_two_digits: DigitTestResult;
  first_three_digits: DigitTestResult;
  last_two_digits: DigitTestResult;
  mantissa_arc: MantissaResult;
  error_message?: string;
}

export interface ForensicTestsResponse {
  success: boolean;
  rsf_analysis: {
    available: boolean;
    total_vendors_analyzed: number;
    outlier_vendor_count: number;
    high_risk_vendors: {
      vendor_name: string;
      transaction_count: number;
      total_spend: number;
      largest_amount: number;
      second_largest_amount: number;
      rsf_value: number;
      is_single_transaction: boolean;
      is_outlier: boolean;
      risk_level: string;
      row_indices: number[];
    }[];
    reason?: string;
  };
  duplicate_analysis: {
    exact_duplicate_clusters: number;
    exact_duplicated_rows: number;
    exact_duplicates: {
      vendor: string;
      amount: number;
      duplicate_count: number;
      total_duplicated_value: number;
      row_indices: number[];
    }[];
    fuzzy_duplicates: {
      vendor: string;
      amount: number;
      count: number;
      total_value: number;
      dates: string[];
      invoices: string[];
      row_indices: number[];
    }[];
  };
  split_transaction_analysis: {
    total_split_anomalies: number;
    threshold_evaluations: {
      threshold_limit: number;
      evasion_window: string;
      description: string;
      transaction_count: number;
      row_indices: number[];
      top_vendors: {
        vendor: string;
        count: number;
        row_indices: number[];
      }[];
    }[];
  };
  round_number_analysis: {
    total_round_transactions: number;
    round_percentage: number;
    is_elevated_round_density: boolean;
    breakdown: {
      multiples_of_1Lakh: number;
      multiples_of_50k: number;
      multiples_of_10k: number;
      multiples_of_1k: number;
    };
  };
  temporal_analysis: {
    available: boolean;
    weekend_postings_count: number;
    holiday_postings_count: number;
    fiscal_year_end_count: number;
  };
  composite_risk_summary: {
    total_analyzed: number;
    total_flagged: number;
    risk_distribution: {
      CRITICAL: number;
      HIGH: number;
      MODERATE: number;
      LOW: number;
    };
  };
  flagged_transactions: {
    row_index: number;
    risk_score: number;
    risk_tier: string;
    anomaly_factors: string[];
    amount: any;
    date: string;
    vendor: string;
    invoice_no: string;
    record_data: Record<string, any>;
  }[];
}

export interface AuditBlock {
  index: number;
  timestamp: number;
  datetime: string;
  action: string;
  user_role: string;
  consent_token: string;
  dataset_hash: string;
  details: Record<string, any>;
  prev_hash: string;
  block_hash: string;
}
