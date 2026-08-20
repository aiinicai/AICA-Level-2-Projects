/**
 * Hand-written mirror of the SQL in supabase/. Keep in step with those files —
 * the database is the source of truth and the app never migrates it.
 */

export type AppRole = 'admin' | 'employee'

export type Designation =
  | 'Partner'
  | 'Manager'
  | 'Senior Accountant'
  | 'Accountant'
  | 'Paid Assistant'
  | 'Article Assistant'
  | 'Intern'
  | 'Admin Staff'

/** Codes are stable; names are editable in the stage master. */
export type StageCode = '01' | '02' | '03' | '04' | '05'

export interface Stage {
  id: string
  code: string
  name: string
  sort_order: number
  /** Finished work — excluded from "pending" counts. */
  is_terminal: boolean
  /** Cancelled work — terminal, and hidden from the board by default. */
  is_dropped: boolean
  description: string | null
  is_active: boolean
  created_at: string
}

export type TaskPriority = 'Low' | 'Medium' | 'High' | 'Urgent'

export type Recurrence =
  | 'One-time'
  | 'Daily'
  | 'Weekly'
  | 'Monthly'
  | 'Quarterly'
  | 'Half-Yearly'
  | 'Annual'

export type ClientType =
  | 'Individual'
  | 'Proprietorship'
  | 'Partnership Firm'
  | 'LLP'
  | 'Private Limited'
  | 'Public Limited'
  | 'HUF'
  | 'Trust'
  | 'Society'
  | 'AOP/BOI'

export interface AllowedEmail {
  id: string
  email: string
  full_name: string | null
  designation: Designation
  invited_by: string | null
  is_used: boolean
  created_at: string
}

export interface Profile {
  id: string
  email: string
  full_name: string
  designation: Designation
  phone: string | null
  date_of_joining: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Client {
  id: string
  client_code: string | null
  /** Family / business group, e.g. "Agarwal Group". Free text, offered as a combobox. */
  client_group: string | null
  name: string
  client_type: ClientType
  pan: string | null
  gstin: string | null
  contact_person: string | null
  email: string | null
  phone: string | null
  address: string | null
  city: string | null
  state: string | null
  relationship_manager: string | null
  is_active: boolean
  notes: string | null
  created_by: string | null
  created_at: string
}

export interface TaskMaster {
  id: string
  name: string
  category: string
  description: string | null
  default_priority: TaskPriority
  recurrence: Recurrence
  statutory_due: string | null
  estimated_hours: number | null
  is_active: boolean
  created_at: string
}

export interface Task {
  id: string
  title: string
  task_master_id: string | null
  client_id: string | null
  assigned_to: string
  assigned_by: string
  stage_id: string
  stage_since: string
  help_note: string | null
  priority: TaskPriority
  description: string | null
  financial_year: string | null
  period: string | null
  start_date: string | null
  due_date: string | null
  completed_at: string | null
  is_adhoc: boolean
  created_at: string
  updated_at: string
}

/** public.v_tasks_enriched — security_invoker, so RLS already applies. */
export interface TaskEnriched {
  id: string
  title: string
  priority: TaskPriority
  description: string | null
  financial_year: string | null
  period: string | null
  start_date: string | null
  due_date: string | null
  completed_at: string | null
  is_adhoc: boolean
  created_at: string
  updated_at: string
  assigned_to: string
  assigned_by: string | null
  client_id: string | null
  task_master_id: string | null

  compliance_id: string | null
  gstin: string | null
  filing_date: string | null
  filing_link: string | null
  compliance_code: string | null
  compliance_name: string | null
  compliance_law: string | null
  is_compliance: boolean

  latest_comment: string | null
  latest_comment_at: string | null
  latest_comment_by: string | null

  stage_id: string
  stage_since: string
  help_note: string | null
  stage_code: string
  stage_name: string
  stage_sort: number
  stage_is_terminal: boolean
  stage_is_dropped: boolean

  assignee_name: string
  assignee_designation: Designation
  assigner_name: string | null
  client_name: string | null
  client_code: string | null
  client_group: string | null
  master_task_name: string | null
  category: string

  /** The two numbers this app exists to show. */
  days_in_stage: number
  is_overdue: boolean
  days_to_due: number | null
}

export interface GstRegistration {
  id: string
  client_id: string
  gstin: string
  state: string | null
  trade_name: string | null
  is_active: boolean
  registered_on: string | null
  notes: string | null
  created_by: string | null
  created_at: string
}

export interface ComplianceMaster {
  id: string
  code: string
  name: string
  law: string | null
  entity_types: string | null
  target_level: 'Client' | 'GSTIN'
  alt_group: string | null
  frequency: string | null
  frequency_overridable: boolean
  period_basis: string | null
  due_rule_type: string | null
  due_anchor: string | null
  due_day: number | null
  due_month: number | null
  due_event: string | null
  due_offset_days: number | null
  period_due_dates: string | null
  due_rule_text: string | null
  /** false = event-driven; created manually from the Task Master instead. */
  is_generatable: boolean
  default_applicable: boolean
  active: boolean
  notes: string | null
  created_at: string
}

export interface ClientCompliance {
  id: string
  client_id: string
  compliance_id: string
  start_date: string | null
  assigned_to: string | null
  frequency_override: string | null
  notes: string | null
  created_by: string | null
  created_at: string
}

export interface TaskComment {
  id: string
  task_id: string
  user_id: string
  comment: string
  created_at: string
}

export interface TaskActivity {
  id: string
  task_id: string
  changed_by: string | null
  field: string
  old_value: string | null
  new_value: string | null
  created_at: string
}

export interface TaskStageHistory {
  id: string
  task_id: string
  from_stage_id: string | null
  to_stage_id: string
  note: string | null
  changed_by: string | null
  created_at: string
}

export interface RecurringAssignment {
  id: string
  task_master_id: string
  client_id: string | null
  assigned_to: string | null
  /** The schedule's own cadence. Null falls back to the master's recurrence. */
  recurrence: Recurrence | null
  is_active: boolean
  notes: string | null
  created_by: string | null
  created_at: string
}
