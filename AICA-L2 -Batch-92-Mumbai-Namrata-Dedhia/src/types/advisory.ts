export type ReviewStatus = 'VERIFIED' | 'REQUIRES PROFESSIONAL VERIFICATION' | 'SUPERSEDED';
export type ProfessionalReviewFlag = 'YES' | 'NO' | 'REVIEW';

export interface FAQRecord {
  faq_id: string;
  category: string;
  subcategory: string;
  user_question: string;
  question_variations: string[];
  short_answer: string;
  detailed_answer: string;
  applicability: string;
  taxpayer_type: string;
  NRI_status: string;
  OCI_status: string;
  resident_status: 'Non-Resident' | 'RNOR' | 'Resident' | 'All';
  conditions: string[];
  exceptions: string[];
  thresholds: string;
  rates: string;
  limits: string;
  relevant_FY: string;
  relevant_AY: string;
  effective_from: string;
  effective_until?: string;
  source_type: 'Statute' | 'Rule' | 'Master Direction' | 'Circular' | 'Notification' | 'Regulation';
  source_authority: 'CBDT / Income Tax Department' | 'Reserve Bank of India (RBI)' | 'Ministry of Finance' | 'FEMA Directorate';
  act_or_regulation: string;
  section_rule_regulation: string;
  circular_notification?: string;
  source_url: string;
  source_excerpt_or_summary: string;
  last_verified: string;
  review_status: ReviewStatus;
  professional_review_required: ProfessionalReviewFlag;
  keywords: string[];
  related_faq_ids: string[];
}

export interface SourceRecord {
  source_id: string;
  authority: string;
  source_title: string;
  source_type: string;
  url: string;
  publication_date: string;
  effective_date: string;
  subject: string;
  last_checked: string;
  notes: string;
}

export interface ChangeLogRecord {
  change_id: string;
  date: string;
  topic: string;
  old_position: string;
  new_position: string;
  source: string;
  reason: string;
  reviewed_by: string;
  review_status: string;
}

export interface ChatLogRecord {
  id: string;
  timestamp: string;
  session_id: string;
  channel: 'pwa' | 'chrome_extension' | 'test_runner';
  user_question: string;
  detected_topic: string;
  matched_faq_ids: string[];
  answer: string;
  source_references: string[];
  confidence: number;
  out_of_scope: boolean;
  escalation_required: boolean;
  response_status: 'SUCCESS' | 'OUT_OF_SCOPE' | 'VALIDATION_FAILED' | 'ERROR';
}

export interface WebhookRequest {
  session_id: string;
  question: string;
  channel: 'pwa' | 'chrome_extension';
  context?: {
    residential_status?: string;
    days_in_india?: number;
    holding_period_months?: number;
  };
  history?: { role: string; text: string }[];
  model?: string;
}

export interface SourceCitation {
  provision: string;
  authority: string;
  source: string;
  url: string;
  applicable_period: string;
  excerpt: string;
}

export interface WebhookResponse {
  answer: string;
  sources: SourceCitation[];
  topic: string;
  matched_faq_ids: string[];
  out_of_scope: boolean;
  escalation_required: boolean;
  disclaimer: string;
  confidence: number;
  clarifications_needed?: string[];
  assumptions?: string[];
}
