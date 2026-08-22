import type {
  ClientType,
  Designation,
  Recurrence,
  StageCode,
  TaskPriority,
} from '@/types/db'

export const FIRM_NAME = 'Aggarwal Samir & Co'
export const FIRM_TAGLINE = 'Task Delegation & Practice Management'
export const FIRM_INITIALS = 'AS&Co'

export const DESIGNATIONS: Designation[] = [
  'Partner',
  'Manager',
  'Senior Accountant',
  'Accountant',
  'Paid Assistant',
  'Article Assistant',
  'Intern',
  'Admin Staff',
]

export const CLIENT_TYPES: ClientType[] = [
  'Individual',
  'Proprietorship',
  'Partnership Firm',
  'LLP',
  'Private Limited',
  'Public Limited',
  'HUF',
  'Trust',
  'Society',
  'AOP/BOI',
]

export const PRIORITIES: TaskPriority[] = ['Low', 'Medium', 'High', 'Urgent']

export const RECURRENCES: Recurrence[] = [
  'One-time',
  'Daily',
  'Weekly',
  'Monthly',
  'Quarterly',
  'Half-Yearly',
  'Annual',
]

/** Recurrences that recurring generation can actually produce. */
export const GENERATABLE_RECURRENCES: Recurrence[] = [
  'Daily',
  'Weekly',
  'Monthly',
  'Quarterly',
  'Half-Yearly',
  'Annual',
]

export const FINANCIAL_YEARS = ['2023-24', '2024-25', '2025-26', '2026-27', '2027-28']
export const DEFAULT_FINANCIAL_YEAR = '2026-27'

/** The 9 seeded categories. Users may still type a new one on the master screen. */
export const SEEDED_CATEGORIES = [
  'GST',
  'Income Tax',
  'TDS/TCS',
  'ROC/MCA',
  'Audit',
  'Accounting',
  'Payroll',
  'Registrations',
  'Firm Internal',
]

/*
  Stage codes are stable and live in the database; only names are editable.
  The app keys colour and behaviour off the CODE, never the name, so renaming
  "Need Help" to "Blocked" in the master does not break the board.
*/
export const STAGE_NOT_STARTED: StageCode = '01'
export const STAGE_IN_PROGRESS: StageCode = '02'
export const STAGE_NEED_HELP: StageCode = '03'
export const STAGE_COMPLETED: StageCode = '04'
export const STAGE_DROPPED: StageCode = '05'

export const STAGE_VAR: Record<string, string> = {
  '01': 'var(--stage-01)',
  '02': 'var(--stage-02)',
  '03': 'var(--stage-03)',
  '04': 'var(--stage-04)',
  '05': 'var(--stage-05)',
}

/** Falls back to a neutral colour for any stage an admin adds later. */
export function stageVar(code: string): string {
  return STAGE_VAR[code] ?? 'var(--muted-foreground)'
}

export const PRIORITY_VAR: Record<TaskPriority, string> = {
  Low: 'var(--stage-01)',
  Medium: 'var(--chart-1)',
  High: 'var(--chart-2)',
  Urgent: 'var(--destructive)',
}

export const CHART_VARS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
  'var(--chart-6)',
]

/** Ageing thresholds, in days, for highlighting stuck work. */
export const AGEING_WARN = 7
export const AGEING_ALERT = 14

export const PAN_REGEX = /^[A-Z]{5}[0-9]{4}[A-Z]$/
export const GSTIN_REGEX = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}$/
