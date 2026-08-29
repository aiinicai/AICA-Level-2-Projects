import type { DueBucket, TaskStatus, Urgency } from '../types/database'

const statusStyles: Record<TaskStatus, string> = {
  Open: 'bg-paper text-ink-soft border border-line',
  'In Process': 'bg-gold-bg text-gold-ink',
  'Pending at Client': 'bg-rust-bg text-rust',
  'Pending at Department': 'bg-rust-bg text-rust',
  Hold: 'bg-slate-bg text-slate',
  Closed: 'bg-moss-bg text-moss',
}

export function StatusBadge({ status }: { status: TaskStatus }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium text-center leading-snug ${statusStyles[status]}`}
    >
      {status}
    </span>
  )
}

const urgencyStyles: Record<Urgency, string> = {
  Low: 'bg-paper text-ink-soft border border-line',
  Medium: 'bg-gold-bg text-gold-ink',
  High: 'bg-rust-bg text-rust',
}

export function UrgencyBadge({ urgency }: { urgency: Urgency }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${urgencyStyles[urgency]}`}
    >
      {urgency}
    </span>
  )
}

const bucketStyles: Record<DueBucket, string> = {
  Overdue: 'bg-rust-bg text-rust',
  'Due in 3 days': 'bg-gold-bg text-gold-ink',
  'Due in 4-6 days': 'bg-gold-bg text-gold-ink',
  '7 days & more': 'bg-moss-bg text-moss',
  Others: 'bg-paper text-ink-soft border border-line',
}

export function DueBucketBadge({ bucket }: { bucket: DueBucket }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${bucketStyles[bucket]}`}
    >
      {bucket}
    </span>
  )
}
