import { supabase } from './supabase'
import type {
  Client,
  PendingRevisionWithTask,
  Profile,
  TaskComment,
  TaskRevision,
  TaskWithDueDate,
} from '../types/database'

export async function fetchProfiles(): Promise<Profile[]> {
  const { data, error } = await supabase.from('profiles').select('*').order('full_name')
  if (error) throw error
  return data
}

export async function fetchClients(): Promise<Client[]> {
  const { data, error } = await supabase.from('clients').select('*').order('name')
  if (error) throw error
  return data
}

export async function createClient(name: string): Promise<Client> {
  const { data, error } = await supabase.from('clients').insert({ name }).select().single()
  if (error) throw error
  return data
}

/** All tasks visible to the current user under RLS (their own, or everything if Admin). */
export async function fetchMyVisibleTasks(): Promise<TaskWithDueDate[]> {
  const { data, error } = await supabase
    .from('tasks_with_due_date')
    .select('*')
    .order('effective_due_date')
  if (error) throw error
  return data
}

export async function fetchTask(id: string): Promise<TaskWithDueDate> {
  const { data, error } = await supabase.from('tasks_with_due_date').select('*').eq('id', id).single()
  if (error) throw error
  return data
}

export interface NewTaskInput {
  client_id: string
  description: string
  assignor_id: string
  primary_assignee_id: string
  secondary_assignee_id: string | null
  urgency: 'Low' | 'Medium' | 'High'
  planned_date: string
}

export async function createTask(input: NewTaskInput) {
  const { data, error } = await supabase.from('tasks').insert(input).select().single()
  if (error) throw error
  return data
}

export async function updateTaskStatus(taskId: string, status: string) {
  const { error } = await supabase.from('tasks').update({ status }).eq('id', taskId)
  if (error) throw error
}

/** Admin-only per the enforce_task_update_rules trigger — everyone else gets
 * "Only an Admin can edit this field" back from Postgres. */
export async function updateTaskDescription(taskId: string, description: string) {
  const { error } = await supabase.from('tasks').update({ description }).eq('id', taskId)
  if (error) throw error
}

/** Admin-only per the enforce_task_update_rules trigger — a single
 * overwritable field, distinct from the task_comments thread. */
export async function updateTaskAdminRemark(taskId: string, adminRemark: string) {
  const { error } = await supabase.from('tasks').update({ admin_remark: adminRemark }).eq('id', taskId)
  if (error) throw error
}

export async function delegateSecondaryAssignee(taskId: string, secondaryAssigneeId: string) {
  const { error } = await supabase
    .from('tasks')
    .update({ secondary_assignee_id: secondaryAssigneeId })
    .eq('id', taskId)
  if (error) throw error
}

export async function reopenTask(taskId: string) {
  const { error } = await supabase
    .from('tasks')
    .update({ status: 'Open', closed_at: null, closed_by: null })
    .eq('id', taskId)
  if (error) throw error
}

export async function deleteTask(taskId: string) {
  const { error } = await supabase.from('tasks').delete().eq('id', taskId)
  if (error) throw error
}

export async function fetchRevisions(taskId: string): Promise<TaskRevision[]> {
  const { data, error } = await supabase
    .from('task_revisions')
    .select('*')
    .eq('task_id', taskId)
    .order('created_at', { ascending: false })
  if (error) throw error
  return data
}

/** Every pending revision request across every task — the Admin-wide
 * queue, not scoped to a single task's page. RLS's task_revisions_select
 * policy already grants Admin every row regardless of task involvement. */
export async function fetchPendingRevisions(): Promise<PendingRevisionWithTask[]> {
  const { data, error } = await supabase
    .from('task_revisions')
    .select('*, task:tasks(id, task_number, description, client_id)')
    .eq('status', 'pending')
    .order('created_at', { ascending: true })
  if (error) throw error
  return data as unknown as PendingRevisionWithTask[]
}

export async function fetchPendingRevisionsCount(): Promise<number> {
  const { count, error } = await supabase
    .from('task_revisions')
    .select('id', { count: 'exact', head: true })
    .eq('status', 'pending')
  if (error) throw error
  return count ?? 0
}

export async function requestRevision(taskId: string, proposedDate: string, reason: string) {
  const { data: userData } = await supabase.auth.getUser()
  const { error } = await supabase.from('task_revisions').insert({
    task_id: taskId,
    requested_by: userData.user!.id,
    proposed_date: proposedDate,
    reason,
  })
  if (error) throw error
}

export async function decideRevision(
  revisionId: string,
  decision: 'approved' | 'rejected',
  impactsPerformance: boolean | null,
  decisionNote: string
) {
  const { error } = await supabase
    .from('task_revisions')
    .update({
      status: decision,
      impacts_performance: decision === 'approved' ? impactsPerformance : null,
      decision_note: decisionNote,
    })
    .eq('id', revisionId)
  if (error) throw error
}

export async function fetchComments(taskId: string): Promise<TaskComment[]> {
  const { data, error } = await supabase
    .from('task_comments')
    .select('*')
    .eq('task_id', taskId)
    .order('created_at')
  if (error) throw error
  return data
}

export async function addComment(taskId: string, body: string) {
  const { data: userData } = await supabase.auth.getUser()
  const { error } = await supabase.from('task_comments').insert({
    task_id: taskId,
    author_id: userData.user!.id,
    body,
  })
  if (error) throw error
}
