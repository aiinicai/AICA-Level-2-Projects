import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ArrowLeft, History, Loader2, MessageSquare, Send, TriangleAlert } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import {
  AgeingBadge,
  CategoryBadge,
  ComplianceBadge,
  EmptyState,
  Field,
  OverdueBadge,
  PriorityBadge,
  StageBadge,
} from '@/components/common'
import { Combobox } from '@/components/combobox'
import { StagePicker } from '@/components/stage-picker'
import { useAuth } from '@/components/auth-provider'
import { QK, useClients, useProfiles, useStages } from '@/hooks/use-app-data'
import { friendlyError, supabase } from '@/lib/supabase'
import {
  DEFAULT_FINANCIAL_YEAR,
  FINANCIAL_YEARS,
  PRIORITIES,
  STAGE_NEED_HELP,
  stageVar,
} from '@/lib/constants'
import { formatDate, formatDateTime, initials, relativeTime } from '@/lib/utils'
import type {
  Profile,
  TaskActivity,
  TaskComment,
  TaskEnriched,
  TaskPriority,
  TaskStageHistory,
} from '@/types/db'

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { session, isAdmin } = useAuth()
  const { byId: stageById } = useStages()

  const [draft, setDraft] = useState<TaskEnriched | null>(null)
  const [comment, setComment] = useState('')

  const taskQuery = useQuery({
    queryKey: ['task', id],
    enabled: Boolean(id),
    retry: false,
    queryFn: async () => {
      const { data, error } = await supabase
        .from('v_tasks_enriched')
        .select('*')
        .eq('id', id!)
        .maybeSingle()
      if (error) throw error
      return (data as TaskEnriched | null) ?? null
    },
  })

  const profilesQuery = useProfiles()
  const clientsQuery = useClients()

  const commentsQuery = useQuery({
    queryKey: ['task_comments', id],
    enabled: Boolean(id),
    queryFn: async () => {
      const { data, error } = await supabase
        .from('task_comments')
        .select('*')
        .eq('task_id', id!)
        .order('created_at', { ascending: true })
      if (error) throw error
      return data as TaskComment[]
    },
  })

  const historyQuery = useQuery({
    queryKey: ['task_stage_history', id],
    enabled: Boolean(id),
    queryFn: async () => {
      const { data, error } = await supabase
        .from('task_stage_history')
        .select('*')
        .eq('task_id', id!)
        .order('created_at', { ascending: false })
      if (error) throw error
      return data as TaskStageHistory[]
    },
  })

  // Due-date and reassignment changes. Stage rows are excluded here — the
  // stage history table already carries those, with the blocker note.
  const activityQuery = useQuery({
    queryKey: ['task_activity', id],
    enabled: Boolean(id),
    queryFn: async () => {
      const { data, error } = await supabase
        .from('task_activity')
        .select('*')
        .eq('task_id', id!)
        .neq('field', 'stage')
        .order('created_at', { ascending: false })
      if (error) throw error
      return data as TaskActivity[]
    },
  })

  useEffect(() => {
    if (taskQuery.data) setDraft({ ...taskQuery.data })
  }, [taskQuery.data])

  // Stage changes invalidate the task and its history together.
  useEffect(() => {
    if (!taskQuery.data) return
    void queryClient.invalidateQueries({ queryKey: ['task_stage_history', id] })
  }, [taskQuery.data?.stage_id, taskQuery.data, queryClient, id])

  const profileById = useMemo(() => {
    const map = new Map<string, Profile>()
    for (const profile of profilesQuery.data ?? []) map.set(profile.id, profile)
    return map
  }, [profilesQuery.data])

  const assigneeOptions = useMemo(
    () =>
      (profilesQuery.data ?? [])
        .filter((p) => p.is_active)
        .map((p) => ({ value: p.id, label: `${p.full_name} — ${p.designation}` })),
    [profilesQuery.data],
  )

  const clientOptions = useMemo(
    () =>
      (clientsQuery.data ?? [])
        .filter((c) => c.is_active)
        .map((c) => ({ value: c.id, label: c.name, hint: c.client_code ?? undefined })),
    [clientsQuery.data],
  )

  // Reassignment stays with an admin or the person who assigned the task.
  const canReassign =
    isAdmin || taskQuery.data?.assigned_by === session?.user.id

  const saveTask = useMutation({
    mutationFn: async (payload: TaskEnriched) => {
      // Dates and details are open to everyone who can see the task; a date
      // change is logged by the database, not blocked. Only the assignee field
      // is held back unless this user may reassign.
      const update: Record<string, unknown> = {
        title: payload.title.trim(),
        description: payload.description,
        client_id: payload.client_id,
        priority: payload.priority,
        financial_year: payload.financial_year,
        period: payload.period,
        start_date: payload.start_date || null,
        due_date: payload.due_date || null,
      }
      if (canReassign) update.assigned_to = payload.assigned_to

      const { error } = await supabase.from('tasks').update(update).eq('id', payload.id)
      if (error) throw error
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['task', id] })
      void queryClient.invalidateQueries({ queryKey: ['task_activity', id] })
      void queryClient.invalidateQueries({ queryKey: QK.tasks })
      toast.success('Task saved')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const postComment = useMutation({
    mutationFn: async (text: string) => {
      const { error } = await supabase.from('task_comments').insert({
        task_id: id!,
        user_id: session?.user.id ?? '',
        comment: text.trim(),
      })
      if (error) throw error
    },
    onSuccess: () => {
      setComment('')
      void queryClient.invalidateQueries({ queryKey: ['task_comments', id] })
      // The board shows each task's latest comment, so refresh the list too.
      void queryClient.invalidateQueries({ queryKey: QK.tasks })
      toast.success('Comment posted')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  if (taskQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-5 lg:grid-cols-3">
          <Skeleton className="h-80 lg:col-span-2" />
          <Skeleton className="h-80" />
        </div>
      </div>
    )
  }

  if (taskQuery.error || !taskQuery.data || !draft) {
    return (
      <EmptyState
        title="Task not found or you do not have access"
        description="It may have been deleted, or it belongs to a colleague. Only an administrator can see the whole firm's tasks."
        action={
          <Button variant="outline" onClick={() => navigate(-1)}>
            <ArrowLeft className="size-4" />
            Go back
          </Button>
        }
      />
    )
  }

  const task = taskQuery.data

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="size-4" />
          Back
        </Button>
        <div className="flex flex-wrap items-center gap-2">
          {task.is_compliance ? <ComplianceBadge gstin={task.gstin} /> : null}
          <CategoryBadge category={task.category} />
          <StageBadge code={task.stage_code} name={task.stage_name} showCode />
          <PriorityBadge priority={task.priority} />
          {task.is_overdue ? <OverdueBadge days={task.days_to_due} /> : null}
        </div>
        <div className="ml-auto">
          <StagePicker
            taskId={task.id}
            stageId={task.stage_id}
            currentNote={task.help_note}
            isCompliance={task.is_compliance}
            taskTitle={task.title}
            className="w-56"
          />
        </div>
      </div>

      {task.stage_code === STAGE_NEED_HELP && task.help_note ? (
        <div
          className="flex gap-3 rounded-lg border p-3"
          style={{
            borderColor: stageVar(STAGE_NEED_HELP),
            backgroundColor: `color-mix(in srgb, ${stageVar(STAGE_NEED_HELP)} 8%, transparent)`,
          }}
        >
          <TriangleAlert
            className="mt-0.5 size-4 shrink-0"
            style={{ color: stageVar(STAGE_NEED_HELP) }}
          />
          <div>
            <p className="text-sm font-medium">Blocked — waiting {task.days_in_stage} day(s)</p>
            <p className="mt-0.5 text-sm whitespace-pre-wrap">{task.help_note}</p>
          </div>
        </div>
      ) : null}

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg leading-snug">{task.title}</CardTitle>
              {!canReassign ? (
                <p className="text-muted-foreground text-xs">
                  Any date change is recorded in the history below. Reassigning is for{' '}
                  {task.assigner_name ?? 'the assigner'} or a partner.
                </p>
              ) : null}
            </CardHeader>
            <CardContent>
              <form
                className="grid gap-4 sm:grid-cols-2"
                onSubmit={(event) => {
                  event.preventDefault()
                  saveTask.mutate(draft)
                }}
              >
                <Field label="Title" htmlFor="detail-title" className="sm:col-span-2" required>
                  <Input
                    id="detail-title"
                    value={draft.title}
                    onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                  />
                </Field>
                {canReassign ? (
                  <Field label="Assignee">
                    <Combobox
                      options={assigneeOptions}
                      value={draft.assigned_to}
                      onChange={(value) => value && setDraft({ ...draft, assigned_to: value })}
                      placeholder="Select an employee"
                    />
                  </Field>
                ) : null}
                <Field label="Client">
                      <Combobox
                        options={clientOptions}
                        value={draft.client_id}
                        onChange={(value) => setDraft({ ...draft, client_id: value })}
                        placeholder="No client"
                        allowClear
                        clearLabel="No client (internal)"
                      />
                    </Field>
                    <Field label="Priority">
                      <Select
                        value={draft.priority}
                        onValueChange={(value) =>
                          setDraft({ ...draft, priority: value as TaskPriority })
                        }
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {PRIORITIES.map((priority) => (
                            <SelectItem key={priority} value={priority}>
                              {priority}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </Field>
                    <Field label="Financial Year">
                      <Select
                        value={draft.financial_year ?? DEFAULT_FINANCIAL_YEAR}
                        onValueChange={(value) => setDraft({ ...draft, financial_year: value })}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {FINANCIAL_YEARS.map((year) => (
                            <SelectItem key={year} value={year}>
                              {year}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </Field>
                    <Field label="Period" htmlFor="detail-period">
                      <Input
                        id="detail-period"
                        value={draft.period ?? ''}
                        onChange={(e) => setDraft({ ...draft, period: e.target.value })}
                      />
                    </Field>
                    <Field label="Start Date" htmlFor="detail-start">
                      <Input
                        id="detail-start"
                        type="date"
                        value={draft.start_date ?? ''}
                        onChange={(e) => setDraft({ ...draft, start_date: e.target.value })}
                      />
                    </Field>
                    <Field
                      label="Due Date"
                      htmlFor="detail-due"
                      hint="Changing this is recorded in the history."
                    >
                      <Input
                        id="detail-due"
                        type="date"
                        value={draft.due_date ?? ''}
                        onChange={(e) => setDraft({ ...draft, due_date: e.target.value })}
                      />
                    </Field>

                <Field
                  label="Description / Notes"
                  htmlFor="detail-description"
                  className="sm:col-span-2"
                >
                  <Textarea
                    id="detail-description"
                    rows={4}
                    value={draft.description ?? ''}
                    onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                  />
                </Field>

                <div className="sm:col-span-2">
                  <Button type="submit" disabled={saveTask.isPending}>
                    {saveTask.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
                    Save changes
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Comments */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <MessageSquare className="size-4" />
                Comments
                <span className="text-muted-foreground font-normal tabular-nums">
                  {commentsQuery.data?.length ?? 0}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {commentsQuery.isLoading ? (
                <Skeleton className="h-20 w-full" />
              ) : commentsQuery.data?.length ? (
                <ul className="space-y-4">
                  {commentsQuery.data.map((item) => {
                    const author = profileById.get(item.user_id)
                    return (
                      <li key={item.id} className="flex gap-3">
                        <Avatar className="size-8 shrink-0">
                          <AvatarFallback className="bg-secondary text-secondary-foreground text-xs font-semibold">
                            {initials(author?.full_name)}
                          </AvatarFallback>
                        </Avatar>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-baseline gap-2">
                            <span className="text-sm font-medium">
                              {author?.full_name ?? 'Unknown user'}
                            </span>
                            <span className="text-muted-foreground text-xs">
                              {relativeTime(item.created_at)}
                            </span>
                          </div>
                          <p className="mt-0.5 text-sm whitespace-pre-wrap">{item.comment}</p>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              ) : (
                <p className="text-muted-foreground text-sm">
                  No comments yet. Use this to record progress, queries raised with the client, or
                  why a filing slipped.
                </p>
              )}

              <Separator />

              <form
                className="space-y-2"
                onSubmit={(event) => {
                  event.preventDefault()
                  if (comment.trim()) postComment.mutate(comment)
                }}
              >
                <Textarea
                  rows={3}
                  placeholder="Add a progress note…"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                />
                <Button type="submit" size="sm" disabled={!comment.trim() || postComment.isPending}>
                  {postComment.isPending ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Send className="size-3.5" />
                  )}
                  Post Comment
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* History — stage moves, date extensions, reassignments */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <History className="size-4" />
                History
              </CardTitle>
            </CardHeader>
            <CardContent>
              {historyQuery.isLoading || activityQuery.isLoading ? (
                <Skeleton className="h-16 w-full" />
              ) : (
                (() => {
                  type Entry = { key: string; when: string; node: React.ReactNode }
                  const entries: Entry[] = []

                  for (const entry of historyQuery.data ?? []) {
                    const from = entry.from_stage_id ? stageById.get(entry.from_stage_id) : null
                    const to = stageById.get(entry.to_stage_id)
                    const actor = entry.changed_by ? profileById.get(entry.changed_by) : undefined
                    entries.push({
                      key: `stage-${entry.id}`,
                      when: entry.created_at,
                      node: (
                        <li key={`stage-${entry.id}`} className="flex gap-3 text-sm">
                          <span
                            className="mt-1.5 size-2 shrink-0 rounded-full"
                            style={{ backgroundColor: stageVar(to?.code ?? '') }}
                          />
                          <div className="min-w-0">
                            <p>
                              {from ? (
                                <>
                                  <span className="font-medium">{from.name}</span> →{' '}
                                </>
                              ) : (
                                'Created at '
                              )}
                              <span className="font-medium">{to?.name ?? 'Unknown stage'}</span>
                              {actor ? (
                                <>
                                  {' '}
                                  by <span className="font-medium">{actor.full_name}</span>
                                </>
                              ) : null}
                            </p>
                            {entry.note ? (
                              <p className="bg-muted mt-1 rounded px-2 py-1 text-xs">
                                {entry.note}
                              </p>
                            ) : null}
                            <p className="text-muted-foreground text-xs">
                              {formatDateTime(entry.created_at)}
                            </p>
                          </div>
                        </li>
                      ),
                    })
                  }

                  for (const entry of activityQuery.data ?? []) {
                    const actor = entry.changed_by ? profileById.get(entry.changed_by) : undefined
                    const isDate = entry.field === 'due_date'
                    const oldLabel = isDate
                      ? formatDate(entry.old_value)
                      : (profileById.get(entry.old_value ?? '')?.full_name ?? '—')
                    const newLabel = isDate
                      ? formatDate(entry.new_value)
                      : (profileById.get(entry.new_value ?? '')?.full_name ?? '—')
                    entries.push({
                      key: `act-${entry.id}`,
                      when: entry.created_at,
                      node: (
                        <li key={`act-${entry.id}`} className="flex gap-3 text-sm">
                          <span className="bg-border mt-1.5 size-2 shrink-0 rounded-full" />
                          <div className="min-w-0">
                            <p>
                              {isDate ? 'Due date' : 'Assignee'} changed from{' '}
                              <span className="font-medium">{oldLabel}</span> to{' '}
                              <span className="font-medium">{newLabel}</span>
                              {actor ? (
                                <>
                                  {' '}
                                  by <span className="font-medium">{actor.full_name}</span>
                                </>
                              ) : null}
                            </p>
                            <p className="text-muted-foreground text-xs">
                              {formatDateTime(entry.created_at)}
                            </p>
                          </div>
                        </li>
                      ),
                    })
                  }

                  entries.sort((a, b) => b.when.localeCompare(a.when))

                  return entries.length ? (
                    <ol className="space-y-3">{entries.map((entry) => entry.node)}</ol>
                  ) : (
                    <p className="text-muted-foreground text-sm">Nothing recorded yet.</p>
                  )
                })()
              )}
            </CardContent>
          </Card>
        </div>

        {/* Summary */}
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-3 text-sm">
                <SummaryRow label="Stage">
                  <StageBadge code={task.stage_code} name={task.stage_name} />
                </SummaryRow>
                <SummaryRow label="In this stage">
                  <AgeingBadge days={task.days_in_stage} terminal={task.stage_is_terminal} />
                </SummaryRow>
                <SummaryRow label="Since">{formatDate(task.stage_since)}</SummaryRow>
                <Separator />
                <SummaryRow label="Client">
                  {task.client_name ? (
                    <span>
                      {task.client_name}
                      {task.client_code ? (
                        <span className="text-muted-foreground ml-1 font-mono text-xs">
                          {task.client_code}
                        </span>
                      ) : null}
                    </span>
                  ) : (
                    'Internal'
                  )}
                </SummaryRow>
                <SummaryRow label="Category">{task.category}</SummaryRow>
                <SummaryRow label="Master task">
                  {task.compliance_name ?? task.master_task_name ?? 'Ad-hoc'}
                </SummaryRow>
                {task.gstin ? (
                  <SummaryRow label="GSTIN">
                    <span className="font-mono text-xs">{task.gstin}</span>
                  </SummaryRow>
                ) : null}
                {task.is_compliance ? (
                  <SummaryRow label="Filing date">{formatDate(task.filing_date)}</SummaryRow>
                ) : null}
                {task.filing_link ? (
                  <SummaryRow label="Acknowledgment">
                    <a
                      href={task.filing_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline underline-offset-2"
                    >
                      open link
                    </a>
                  </SummaryRow>
                ) : null}
                <SummaryRow label="Assigned to">
                  {task.assignee_name}
                  <span className="text-muted-foreground block text-xs">
                    {task.assignee_designation}
                  </span>
                </SummaryRow>
                <SummaryRow label="Assigned by">{task.assigner_name ?? '—'}</SummaryRow>
                <Separator />
                <SummaryRow label="Financial year">{task.financial_year ?? '—'}</SummaryRow>
                <SummaryRow label="Period">{task.period ?? '—'}</SummaryRow>
                <SummaryRow label="Start date">{formatDate(task.start_date)}</SummaryRow>
                <SummaryRow label="Due date">{formatDate(task.due_date)}</SummaryRow>
                <SummaryRow label="Completed">{formatDateTime(task.completed_at)}</SummaryRow>
                <SummaryRow label="Created">{formatDate(task.created_at)}</SummaryRow>
              </dl>
            </CardContent>
          </Card>

          <Button variant="outline" asChild className="w-full">
            <Link to={isAdmin ? '/tasks' : '/my-tasks'}>
              {isAdmin ? 'Back to All Tasks' : 'Back to My Tasks'}
            </Link>
          </Button>
        </div>
      </div>
    </div>
  )
}

function SummaryRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-muted-foreground shrink-0">{label}</dt>
      <dd className="text-right font-medium">{children}</dd>
    </div>
  )
}
