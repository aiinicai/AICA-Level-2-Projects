import { useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { CalendarPlus, Loader2, Pencil, Play, Plus, Repeat, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { EmptyState, Field, PageHeader, StatCard, TableSkeleton } from '@/components/common'
import { Combobox } from '@/components/combobox'
import { useAuth } from '@/components/auth-provider'
import {
  QK,
  useClients,
  useProfiles,
  useRecurringAssignments,
  useTaskMasters,
} from '@/hooks/use-app-data'
import { friendlyError, supabase } from '@/lib/supabase'
import {
  DEFAULT_FINANCIAL_YEAR,
  FINANCIAL_YEARS,
  GENERATABLE_RECURRENCES,
} from '@/lib/constants'
import { todayISO } from '@/lib/utils'
import type { Recurrence, RecurringAssignment, TaskMaster } from '@/types/db'

interface Draft {
  id?: string
  task_master_id: string | null
  client_id: string | null
  assigned_to: string | null
  recurrence: Recurrence | null
  notes: string
}

const EMPTY: Draft = {
  task_master_id: null,
  client_id: null,
  assigned_to: null,
  recurrence: null,
  notes: '',
}

/** "Apr-2026" — the period label an Indian CA office actually writes. */
function currentPeriodLabel(): string {
  const d = new Date()
  return `${d.toLocaleDateString('en-IN', { month: 'short' })}-${d.getFullYear()}`
}

/** "14-Aug-2026" — matches to_char(date,'DD-Mon-YYYY') used by the morning cron. */
function dailyPeriodLabel(): string {
  const d = new Date()
  return `${String(d.getDate()).padStart(2, '0')}-${d.toLocaleDateString('en-IN', { month: 'short' })}-${d.getFullYear()}`
}

export default function RecurringPage() {
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const assignmentsQuery = useRecurringAssignments()
  const mastersQuery = useTaskMasters()
  const clientsQuery = useClients()
  const profilesQuery = useProfiles()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [draft, setDraft] = useState<Draft>(EMPTY)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [deleting, setDeleting] = useState<RecurringAssignment | null>(null)

  const [period, setPeriod] = useState(currentPeriodLabel())
  const [financialYear, setFinancialYear] = useState(DEFAULT_FINANCIAL_YEAR)
  const [dueDate, setDueDate] = useState('')
  const [recurrenceFilter, setRecurrenceFilter] = useState<string>('Monthly')
  const [lastResult, setLastResult] = useState<number | null>(null)

  const masterById = useMemo(() => {
    const map = new Map<string, TaskMaster>()
    for (const master of mastersQuery.data ?? []) map.set(master.id, master)
    return map
  }, [mastersQuery.data])

  const clientById = useMemo(() => {
    const map = new Map<string, string>()
    for (const client of clientsQuery.data ?? []) map.set(client.id, client.name)
    return map
  }, [clientsQuery.data])

  const profileById = useMemo(() => {
    const map = new Map<string, string>()
    for (const profile of profilesQuery.data ?? []) map.set(profile.id, profile.full_name)
    return map
  }, [profilesQuery.data])

  // Any active master can be scheduled at any cadence — the job is the job;
  // how often it recurs belongs to the client arrangement below.
  const masterOptions = useMemo(
    () =>
      (mastersQuery.data ?? [])
        .filter((m) => m.is_active)
        .map((m) => ({ value: m.id, label: m.name, group: m.category })),
    [mastersQuery.data],
  )

  const clientOptions = useMemo(
    () =>
      (clientsQuery.data ?? [])
        .filter((c) => c.is_active)
        .map((c) => ({ value: c.id, label: c.name, hint: c.client_code ?? undefined })),
    [clientsQuery.data],
  )

  const staffOptions = useMemo(
    () =>
      (profilesQuery.data ?? [])
        .filter((p) => p.is_active)
        .map((p) => ({ value: p.id, label: `${p.full_name} — ${p.designation}` })),
    [profilesQuery.data],
  )

  const save = useMutation({
    mutationFn: async (payload: Draft) => {
      const row = {
        task_master_id: payload.task_master_id,
        client_id: payload.client_id,
        assigned_to: payload.assigned_to,
        recurrence: payload.recurrence,
        notes: payload.notes.trim() || null,
      }
      if (payload.id) {
        const { error } = await supabase
          .from('recurring_assignments')
          .update(row)
          .eq('id', payload.id)
        if (error) throw error
      } else {
        const { error } = await supabase
          .from('recurring_assignments')
          .insert({ ...row, created_by: session?.user.id ?? null })
        if (error) throw error
      }
    },
    onSuccess: (_d, variables) => {
      void queryClient.invalidateQueries({ queryKey: QK.recurring })
      setDialogOpen(false)
      toast.success(variables.id ? 'Schedule updated' : 'Schedule added')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const toggleActive = useMutation({
    mutationFn: async (payload: { id: string; is_active: boolean }) => {
      const { error } = await supabase
        .from('recurring_assignments')
        .update({ is_active: payload.is_active })
        .eq('id', payload.id)
      if (error) throw error
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: QK.recurring }),
    onError: (error) => toast.error(friendlyError(error)),
  })

  const remove = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.from('recurring_assignments').delete().eq('id', id)
      if (error) throw error
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QK.recurring })
      setDeleting(null)
      toast.success('Schedule removed')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const runNow = useMutation({
    mutationFn: async () => {
      const { data, error } = await supabase.rpc('generate_morning_tasks')
      if (error) throw error
      return (data as number) ?? 0
    },
    onSuccess: (count) => {
      void queryClient.invalidateQueries({ queryKey: QK.tasks })
      toast.success(
        count === 0
          ? 'Nothing new — everything due is already created.'
          : `${count} task(s) created (recurring + compliance)`,
      )
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const generate = useMutation({
    mutationFn: async () => {
      const { data, error } = await supabase.rpc('generate_recurring_tasks', {
        _period: period.trim(),
        _financial_year: financialYear,
        _due_date: dueDate || null,
        _recurrence: recurrenceFilter === 'all' ? null : recurrenceFilter,
      })
      if (error) throw error
      return (data as number) ?? 0
    },
    onSuccess: (count) => {
      setLastResult(count)
      void queryClient.invalidateQueries({ queryKey: QK.tasks })
      if (count === 0) {
        toast.info('Nothing new to create — those tasks already exist for this period.')
      } else {
        toast.success(`${count} task(s) created for ${period}`)
      }
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const rows = assignmentsQuery.data ?? []
  const activeCount = rows.filter((r) => r.is_active).length
  const missingAssignee = rows.filter((r) => r.is_active && !r.assigned_to).length

  function openAdd() {
    setDraft(EMPTY)
    setErrors({})
    setDialogOpen(true)
  }

  function openEdit(row: RecurringAssignment) {
    const master = masterById.get(row.task_master_id)
    setDraft({
      id: row.id,
      task_master_id: row.task_master_id,
      client_id: row.client_id,
      assigned_to: row.assigned_to,
      recurrence: row.recurrence ?? master?.recurrence ?? null,
      notes: row.notes ?? '',
    })
    setErrors({})
    setDialogOpen(true)
  }

  function submit(event: React.FormEvent) {
    event.preventDefault()
    const next: Record<string, string> = {}
    if (!draft.task_master_id) next.master = 'Choose the recurring task.'
    if (!draft.recurrence) next.recurrence = 'Choose how often this repeats.'
    if (!draft.assigned_to) next.assignee = 'Choose who normally does this job.'
    setErrors(next)
    if (Object.keys(next).length) return
    save.mutate(draft)
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Recurring Work"
        description="Standing instructions, turned into real tasks each period."
      >
        <Button
          variant="outline"
          disabled={runNow.isPending}
          onClick={() => runNow.mutate()}
          title="Runs the same job the scheduler runs at 8:00 IST — recurring and compliance together"
        >
          {runNow.isPending ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
          Run morning job now
        </Button>
        <Button onClick={openAdd}>
          <Plus className="size-4" />
          Add Schedule
        </Button>
      </PageHeader>

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label="Schedules" value={rows.length} icon={Repeat} />
        <StatCard label="Active" value={activeCount} icon={Repeat} tone="success" />
        <StatCard
          label="Missing assignee"
          value={missingAssignee}
          icon={Repeat}
          tone={missingAssignee ? 'destructive' : 'default'}
          hint="skipped when generating"
        />
      </div>

      {/* Generate */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <CalendarPlus className="size-4" />
            Generate for a period
          </CardTitle>
          <CardDescription>
            Every cycle now generates itself each morning at 8:00 IST — daily, weekly, monthly,
            quarterly, half-yearly and annual alike. This panel is only for catch-up runs or a
            custom period label, and running it twice is safe: anything already created for the
            same period is skipped.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Field label="Recurrence">
              <Select
                value={recurrenceFilter}
                onValueChange={(value) => {
                  // A daily run is dated, not monthly — swap the period label
                  // to match so the duplicate check lines up with the cron's.
                  if (value === 'Daily') setPeriod(dailyPeriodLabel())
                  else if (recurrenceFilter === 'Daily') setPeriod(currentPeriodLabel())
                  setRecurrenceFilter(value)
                }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All recurring</SelectItem>
                  {GENERATABLE_RECURRENCES.map((r) => (
                    <SelectItem key={r} value={r}>
                      {r}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Period" htmlFor="gen-period" hint="e.g. Apr-2026, Q1" required>
              <Input
                id="gen-period"
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
              />
            </Field>
            <Field label="Financial Year">
              <Select value={financialYear} onValueChange={setFinancialYear}>
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
            <Field label="Due Date" htmlFor="gen-due" hint="applied to all created tasks">
              <Input
                id="gen-due"
                type="date"
                min={todayISO()}
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </Field>
            <div className="flex items-end">
              <Button
                className="w-full"
                onClick={() => generate.mutate()}
                disabled={generate.isPending || !period.trim() || activeCount === 0}
              >
                {generate.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Play className="size-4" />
                )}
                Generate
              </Button>
            </div>
          </div>

          {lastResult !== null ? (
            <p className="text-muted-foreground mt-3 text-sm">
              Last run created <span className="text-foreground font-medium">{lastResult}</span>{' '}
              task(s).
            </p>
          ) : null}
        </CardContent>
      </Card>

      {/* Schedules */}
      <Card className="py-0">
        <CardContent className="p-0">
          {assignmentsQuery.isLoading ? (
            <TableSkeleton cols={6} />
          ) : assignmentsQuery.error ? (
            <div className="text-destructive p-6 text-sm">
              {friendlyError(assignmentsQuery.error)}
            </div>
          ) : rows.length === 0 ? (
            <div className="p-4">
              <EmptyState
                icon={Repeat}
                title="No recurring schedules yet"
                description="Add one per client and recurring job — GSTR-3B for each GST client, say — then generate them all at the start of every month instead of allocating by hand."
                action={
                  <Button onClick={openAdd}>
                    <Plus className="size-4" />
                    Add Schedule
                  </Button>
                }
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Task</TableHead>
                    <TableHead>Client</TableHead>
                    <TableHead>Recurrence</TableHead>
                    <TableHead>Normally done by</TableHead>
                    <TableHead className="text-center">Active</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row) => {
                    const master = masterById.get(row.task_master_id)
                    return (
                      <TableRow key={row.id}>
                        <TableCell className="font-medium">
                          {master?.name ?? '—'}
                          {master ? (
                            <p className="text-muted-foreground text-xs font-normal">
                              {master.category}
                            </p>
                          ) : null}
                        </TableCell>
                        <TableCell className="whitespace-nowrap">
                          {row.client_id ? (clientById.get(row.client_id) ?? '—') : 'Internal'}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary" className="font-normal">
                            {row.recurrence ?? master?.recurrence ?? '—'}
                          </Badge>
                        </TableCell>
                        <TableCell className="whitespace-nowrap">
                          {row.assigned_to ? (
                            (profileById.get(row.assigned_to) ?? '—')
                          ) : (
                            <span className="text-destructive text-sm">Not set — will skip</span>
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          <Switch
                            checked={row.is_active}
                            onCheckedChange={(checked) =>
                              toggleActive.mutate({ id: row.id, is_active: checked })
                            }
                            aria-label="Toggle schedule"
                          />
                        </TableCell>
                        <TableCell>
                          <div className="flex justify-end gap-1">
                            <Button variant="ghost" size="sm" onClick={() => openEdit(row)}>
                              <Pencil className="size-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:text-destructive"
                              onClick={() => setDeleting(row)}
                            >
                              <Trash2 className="size-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{draft.id ? 'Edit Schedule' : 'Add Schedule'}</DialogTitle>
            <DialogDescription>
              Pick the job and how often it repeats for this client. A new instance is created
              automatically at the start of each cycle.
            </DialogDescription>
          </DialogHeader>
          <form className="space-y-4" onSubmit={submit} noValidate>
            <Field label="Task" error={errors.master} required>
              <Combobox
                options={masterOptions}
                value={draft.task_master_id}
                onChange={(value) => {
                  const master = (mastersQuery.data ?? []).find((m) => m.id === value)
                  setDraft((prev) => ({
                    ...prev,
                    task_master_id: value,
                    // Default the cadence from the master, but never overwrite a
                    // choice the user has already made in this dialog.
                    recurrence:
                      prev.recurrence ??
                      (master && GENERATABLE_RECURRENCES.includes(master.recurrence)
                        ? master.recurrence
                        : null),
                  }))
                }}
                placeholder="Search the task catalogue…"
                emptyText="No master task matches."
              />
            </Field>
            <Field
              label="Periodicity"
              error={errors.recurrence}
              hint="Daily appears each morning, Weekly on Monday, Monthly on the 1st, and so on."
              required
            >
              <Select
                value={draft.recurrence ?? ''}
                onValueChange={(value) =>
                  setDraft({ ...draft, recurrence: value as Recurrence })
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="How often?" />
                </SelectTrigger>
                <SelectContent>
                  {GENERATABLE_RECURRENCES.map((recurrence) => (
                    <SelectItem key={recurrence} value={recurrence}>
                      {recurrence}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Client" hint="Leave blank for an internal recurring job.">
              <Combobox
                options={clientOptions}
                value={draft.client_id}
                onChange={(value) => setDraft({ ...draft, client_id: value })}
                placeholder="No client (internal)"
                allowClear
                clearLabel="No client (internal)"
              />
            </Field>
            <Field label="Normally done by" error={errors.assignee} required>
              <Combobox
                options={staffOptions}
                value={draft.assigned_to}
                onChange={(value) => setDraft({ ...draft, assigned_to: value })}
                placeholder="Select an employee"
              />
            </Field>
            <Field label="Notes" htmlFor="recurring-notes">
              <Input
                id="recurring-notes"
                value={draft.notes}
                onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
              />
            </Field>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={save.isPending}>
                {save.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
                {draft.id ? 'Save' : 'Add Schedule'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(deleting)} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove this schedule?</AlertDialogTitle>
            <AlertDialogDescription>
              Tasks already generated from it are unaffected. Only future generation stops.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleting && remove.mutate(deleting.id)}>
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
