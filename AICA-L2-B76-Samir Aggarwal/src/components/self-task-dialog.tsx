import { useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
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
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { Field } from '@/components/common'
import { Combobox } from '@/components/combobox'
import { useAuth } from '@/components/auth-provider'
import { QK, useClients, useProfiles, useTaskMasters } from '@/hooks/use-app-data'
import { friendlyError, supabase } from '@/lib/supabase'
import { DEFAULT_FINANCIAL_YEAR, FINANCIAL_YEARS, PRIORITIES } from '@/lib/constants'
import { todayISO } from '@/lib/utils'
import type { TaskPriority } from '@/types/db'

interface Draft {
  source: 'master' | 'adhoc'
  task_master_id: string | null
  title: string
  description: string
  client_id: string | null
  assigned_to: string | null
  priority: TaskPriority
  financial_year: string
  period: string
  start_date: string
  due_date: string
}

const EMPTY: Draft = {
  source: 'master',
  task_master_id: null,
  title: '',
  description: '',
  client_id: null,
  assigned_to: null,
  priority: 'Medium',
  financial_year: DEFAULT_FINANCIAL_YEAR,
  period: '',
  start_date: todayISO(),
  due_date: '',
}

/**
 * Any user creating and assigning a task — to themselves by default, or to a
 * colleague. The signed-in user is always recorded as the assigner; the
 * database refuses a spoofed assigned_by, so that is a fact, not a convention.
 */
export function SelfTaskDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { session, profile } = useAuth()
  const queryClient = useQueryClient()
  const clientsQuery = useClients()
  const mastersQuery = useTaskMasters()
  const profilesQuery = useProfiles()

  const [draft, setDraft] = useState<Draft>(EMPTY)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const assigneeOptions = useMemo(
    () =>
      (profilesQuery.data ?? [])
        .filter((p) => p.is_active)
        .map((p) => ({
          value: p.id,
          label: p.id === session?.user.id ? `${p.full_name} (me)` : p.full_name,
          hint: p.designation,
        })),
    [profilesQuery.data, session?.user.id],
  )

  const effectiveAssignee = draft.assigned_to ?? session?.user.id ?? null

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
        .map((c) => ({
          value: c.id,
          label: c.name,
          hint: c.client_group ?? c.client_code ?? undefined,
        })),
    [clientsQuery.data],
  )

  const create = useMutation({
    mutationFn: async () => {
      const uid = session?.user.id
      if (!uid) throw new Error('Not signed in.')

      const { error } = await supabase.from('tasks').insert({
        title: draft.title.trim(),
        task_master_id: draft.source === 'master' ? draft.task_master_id : null,
        is_adhoc: draft.source === 'adhoc',
        client_id: draft.client_id,
        assigned_to: effectiveAssignee ?? uid,
        assigned_by: uid,
        priority: draft.priority,
        description: draft.description.trim() || null,
        financial_year: draft.financial_year || null,
        period: draft.period.trim() || null,
        start_date: draft.start_date || null,
        due_date: draft.due_date || null,
      })
      if (error) throw error
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QK.tasks })
      setDraft(EMPTY)
      setErrors({})
      onOpenChange(false)
      toast.success(
        effectiveAssignee && effectiveAssignee !== session?.user.id
          ? 'Task assigned'
          : 'Task added to your list',
      )
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  function pickMaster(masterId: string | null) {
    const master = (mastersQuery.data ?? []).find((m) => m.id === masterId)
    setDraft((prev) => ({
      ...prev,
      task_master_id: masterId,
      title: master?.name ?? prev.title,
      priority: master?.default_priority ?? prev.priority,
      description: master?.description ?? prev.description,
    }))
  }

  function submit(event: React.FormEvent) {
    event.preventDefault()
    const next: Record<string, string> = {}
    if (draft.source === 'master' && !draft.task_master_id) {
      next.master = 'Choose the job from the list.'
    }
    if (!draft.title.trim()) next.title = 'Title is required.'
    setErrors(next)
    if (Object.keys(next).length) return
    create.mutate()
  }

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((prev) => ({ ...prev, [key]: value }))

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setDraft(EMPTY)
          setErrors({})
        }
        onOpenChange(next)
      }}
    >
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Add Task</DialogTitle>
          <DialogDescription>
            Starts at stage 01. You ({profile?.full_name ?? 'you'}) are recorded as the assigner,
            and any date change later is logged in the task's history.
          </DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={submit} noValidate>
          <Tabs
            value={draft.source}
            onValueChange={(value) =>
              setDraft((prev) => ({
                ...prev,
                source: value as 'master' | 'adhoc',
                task_master_id: value === 'adhoc' ? null : prev.task_master_id,
              }))
            }
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="master">From Task Master</TabsTrigger>
              <TabsTrigger value="adhoc">Ad-hoc Task</TabsTrigger>
            </TabsList>
          </Tabs>

          {draft.source === 'master' ? (
            <Field label="Job" error={errors.master} required>
              <Combobox
                options={masterOptions}
                value={draft.task_master_id}
                onChange={pickMaster}
                placeholder="Search the firm's task list…"
                emptyText="No matching job. Use the Ad-hoc tab instead."
              />
            </Field>
          ) : null}

          <Field label="Title" htmlFor="self-title" error={errors.title} required>
            <Input
              id="self-title"
              value={draft.title}
              onChange={(e) => set('title', e.target.value)}
              placeholder="What are you doing?"
            />
          </Field>

          <Field label="Description / Notes" htmlFor="self-description">
            <Textarea
              id="self-description"
              rows={2}
              value={draft.description}
              onChange={(e) => set('description', e.target.value)}
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Assign To" hint="Yourself, or a colleague.">
              <Combobox
                options={assigneeOptions}
                value={effectiveAssignee}
                onChange={(value) => set('assigned_to', value)}
                placeholder="Select an employee"
              />
            </Field>
            <Field label="Client" hint="Leave blank for internal or firm work.">
              <Combobox
                options={clientOptions}
                value={draft.client_id}
                onChange={(value) => set('client_id', value)}
                placeholder="No client"
                allowClear
                clearLabel="No client (internal)"
              />
            </Field>
            <Field label="Priority">
              <Select
                value={draft.priority}
                onValueChange={(value) => set('priority', value as TaskPriority)}
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
                value={draft.financial_year}
                onValueChange={(value) => set('financial_year', value)}
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
            <Field label="Period" htmlFor="self-period" hint="e.g. Apr-2026, Q1, or leave blank">
              <Input
                id="self-period"
                value={draft.period}
                onChange={(e) => set('period', e.target.value)}
              />
            </Field>
            <Field label="Start Date" htmlFor="self-start">
              <Input
                id="self-start"
                type="date"
                value={draft.start_date}
                onChange={(e) => set('start_date', e.target.value)}
              />
            </Field>
            <Field label="Target Date" htmlFor="self-due">
              <Input
                id="self-due"
                type="date"
                value={draft.due_date}
                onChange={(e) => set('due_date', e.target.value)}
              />
            </Field>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
              Add to my tasks
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
