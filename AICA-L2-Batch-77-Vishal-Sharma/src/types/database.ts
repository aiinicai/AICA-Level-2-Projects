export type Urgency = 'Low' | 'Medium' | 'High'

export type TaskStatus =
  | 'Open'
  | 'In Process'
  | 'Pending at Client'
  | 'Pending at Department'
  | 'Hold'
  | 'Closed'

export type RevisionStatus = 'pending' | 'approved' | 'rejected'

export interface Profile {
  id: string
  email: string
  full_name: string
  is_admin: boolean
  can_create_and_assign: boolean
  is_approved: boolean
  created_at: string
}

export interface Client {
  id: string
  name: string
  created_at: string
}

export interface Task {
  id: string
  task_number: string
  client_id: string
  description: string
  assignor_id: string
  primary_assignee_id: string
  secondary_assignee_id: string | null
  urgency: Urgency
  status: TaskStatus
  start_date: string | null
  planned_date: string
  closed_at: string | null
  closed_by: string | null
  admin_remark: string | null
  created_at: string
}

export interface TaskWithDueDate extends Task {
  effective_due_date: string
  latest_revised_date: string | null
  latest_remark: string | null
}

export interface TaskRevision {
  id: string
  task_id: string
  requested_by: string
  proposed_date: string
  reason: string
  status: RevisionStatus
  decided_by: string | null
  decided_at: string | null
  decision_note: string | null
  impacts_performance: boolean | null
  created_at: string
}

/** A pending revision plus just enough of its parent task to render it
 * outside the task's own page (the admin-wide Revision Requests list). */
export interface PendingRevisionWithTask extends TaskRevision {
  task: {
    id: string
    task_number: string
    description: string
    client_id: string
  }
}

export interface TaskComment {
  id: string
  task_id: string
  author_id: string
  body: string
  created_at: string
}

/** The 4 due-urgency buckets used on the Admin dashboard (Part 5). */
export type DueBucket = 'Overdue' | 'Due in 3 days' | 'Due in 4-6 days' | '7 days & more' | 'Others'

export function dueBucketFor(task: Pick<Task, 'status'>, effectiveDueDate: string): DueBucket {
  if (task.status === 'Pending at Client' || task.status === 'Pending at Department' || task.status === 'Hold') {
    return 'Others'
  }
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(effectiveDueDate)
  const diffDays = Math.round((due.getTime() - today.getTime()) / 86_400_000)

  if (diffDays < 0) return 'Overdue'
  if (diffDays <= 3) return 'Due in 3 days'
  if (diffDays <= 6) return 'Due in 4-6 days'
  return '7 days & more'
}
