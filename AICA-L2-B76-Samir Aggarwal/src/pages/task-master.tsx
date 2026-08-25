import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ListChecks, Loader2, Pencil, Plus, Search } from 'lucide-react'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
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
import { Textarea } from '@/components/ui/textarea'
import {
  EmptyState,
  Field,
  PageHeader,
  PriorityBadge,
  StatCard,
  TableSkeleton,
} from '@/components/common'
import { CreatableCombobox } from '@/components/combobox'
import { friendlyError, supabase } from '@/lib/supabase'
import { PRIORITIES, RECURRENCES, SEEDED_CATEGORIES } from '@/lib/constants'
import { cn } from '@/lib/utils'
import type { Recurrence, TaskMaster, TaskPriority } from '@/types/db'

interface MasterDraft {
  id?: string
  name: string
  category: string
  description: string
  default_priority: TaskPriority
  recurrence: Recurrence
  statutory_due: string
}

const EMPTY_DRAFT: MasterDraft = {
  name: '',
  category: '',
  description: '',
  default_priority: 'Medium',
  recurrence: 'One-time',
  statutory_due: '',
}

export default function TaskMasterPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [draft, setDraft] = useState<MasterDraft>(EMPTY_DRAFT)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [openSections, setOpenSections] = useState<string[]>([])
  const [touchedSections, setTouchedSections] = useState(false)

  const mastersQuery = useQuery({
    queryKey: ['task_master'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('task_master')
        .select('*')
        .order('category')
        .order('name')
      if (error) throw error
      return data as TaskMaster[]
    },
  })

  const saveMaster = useMutation({
    mutationFn: async (payload: MasterDraft) => {
      const row = {
        name: payload.name.trim(),
        category: payload.category.trim(),
        description: payload.description.trim() || null,
        default_priority: payload.default_priority,
        recurrence: payload.recurrence,
        statutory_due: payload.statutory_due.trim() || null,
      }
      if (payload.id) {
        const { error } = await supabase.from('task_master').update(row).eq('id', payload.id)
        if (error) throw error
      } else {
        const { error } = await supabase.from('task_master').insert(row)
        if (error) throw error
      }
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['task_master'] })
      setDialogOpen(false)
      toast.success(variables.id ? 'Task updated' : 'Task added to the master list')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const toggleActive = useMutation({
    mutationFn: async (payload: { id: string; is_active: boolean }) => {
      const { error } = await supabase
        .from('task_master')
        .update({ is_active: payload.is_active })
        .eq('id', payload.id)
      if (error) throw error
    },
    onSuccess: (_d, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['task_master'] })
      toast.success(
        variables.is_active
          ? 'Task activated'
          : 'Task deactivated — it will no longer appear when allocating',
      )
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const term = search.trim().toLowerCase()

  const grouped = useMemo(() => {
    const map = new Map<string, TaskMaster[]>()
    for (const master of mastersQuery.data ?? []) {
      if (
        term &&
        !master.name.toLowerCase().includes(term) &&
        !master.category.toLowerCase().includes(term) &&
        !(master.description ?? '').toLowerCase().includes(term)
      ) {
        continue
      }
      const list = map.get(master.category) ?? []
      list.push(master)
      map.set(master.category, list)
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [mastersQuery.data, term])

  const categories = useMemo(() => {
    const found = new Set(SEEDED_CATEGORIES)
    for (const master of mastersQuery.data ?? []) found.add(master.category)
    return [...found].sort((a, b) => a.localeCompare(b))
  }, [mastersQuery.data])

  // A search auto-expands every section that still has a hit; otherwise only
  // the first section is open, as the brief asks.
  const defaultOpen = grouped.length ? [grouped[0][0]] : []
  const value = term ? grouped.map(([category]) => category) : touchedSections ? openSections : defaultOpen

  const summary = useMemo(() => {
    const all = mastersQuery.data ?? []
    return {
      total: all.length,
      active: all.filter((m) => m.is_active).length,
      categories: new Set(all.map((m) => m.category)).size,
    }
  }, [mastersQuery.data])

  function openAdd() {
    setDraft(EMPTY_DRAFT)
    setErrors({})
    setDialogOpen(true)
  }

  function openEdit(master: TaskMaster) {
    setDraft({
      id: master.id,
      name: master.name,
      category: master.category,
      description: master.description ?? '',
      default_priority: master.default_priority,
      recurrence: master.recurrence,
      statutory_due: master.statutory_due ?? '',
    })
    setErrors({})
    setDialogOpen(true)
  }

  function submit(event: React.FormEvent) {
    event.preventDefault()
    const next: Record<string, string> = {}
    if (!draft.name.trim()) next.name = 'Task name is required.'
    if (!draft.category.trim()) next.category = 'Pick a category or type a new one.'
    setErrors(next)
    if (Object.keys(next).length) return
    saveMaster.mutate(draft)
  }

  const set = <K extends keyof MasterDraft>(key: K, val: MasterDraft[K]) =>
    setDraft((prev) => ({ ...prev, [key]: val }))

  return (
    <div className="space-y-5">
      <PageHeader
        title="Task Master"
        description="The firm's standard job catalogue. Allocation pulls its defaults from here."
      >
        <Button onClick={openAdd}>
          <Plus className="size-4" />
          Add Task
        </Button>
      </PageHeader>

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label="Master Tasks" value={summary.total} icon={ListChecks} />
        <StatCard label="Active" value={summary.active} icon={ListChecks} tone="success" />
        <StatCard label="Categories" value={summary.categories} icon={ListChecks} />
      </div>

      <div className="relative">
        <Search className="text-muted-foreground absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
        <Input
          placeholder="Search all categories…"
          className="pl-8"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {mastersQuery.isLoading ? (
        <Card className="py-0">
          <CardContent className="p-0">
            <TableSkeleton cols={6} />
          </CardContent>
        </Card>
      ) : mastersQuery.error ? (
        <div className="text-destructive text-sm">{friendlyError(mastersQuery.error)}</div>
      ) : grouped.length === 0 ? (
        <EmptyState
          icon={ListChecks}
          title={term ? 'Nothing matches that search' : 'The task master is empty'}
          description={
            term
              ? 'Try a shorter search term.'
              : 'Run 02-seed-task-master.sql in Supabase to load the 89 standard CA tasks, or add them here one by one.'
          }
          action={
            term ? null : (
              <Button onClick={openAdd}>
                <Plus className="size-4" />
                Add Task
              </Button>
            )
          }
        />
      ) : (
        <Accordion
          type="multiple"
          value={value}
          onValueChange={(next) => {
            setTouchedSections(true)
            setOpenSections(next)
          }}
          className="space-y-2"
        >
          {grouped.map(([category, items]) => (
            <AccordionItem
              key={category}
              value={category}
              className="bg-card rounded-lg border px-4 last:border-b"
            >
              <AccordionTrigger className="hover:no-underline">
                <span className="flex items-center gap-2">
                  <span className="font-medium">{category}</span>
                  <Badge variant="secondary" className="tabular-nums">
                    {items.length}
                  </Badge>
                  {items.some((i) => !i.is_active) ? (
                    <span className="text-muted-foreground text-xs">
                      {items.filter((i) => !i.is_active).length} inactive
                    </span>
                  ) : null}
                </span>
              </AccordionTrigger>
              <AccordionContent className="pb-2">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Task Name</TableHead>
                        <TableHead>Recurrence</TableHead>
                        <TableHead>Default Priority</TableHead>
                        <TableHead>Statutory Due</TableHead>
                        <TableHead className="text-center">Active</TableHead>
                        <TableHead className="text-right">Edit</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {items.map((master) => (
                        <TableRow key={master.id} className={cn(!master.is_active && 'opacity-50')}>
                          <TableCell className="font-medium">
                            {master.name}
                            {master.description ? (
                              <p className="text-muted-foreground mt-0.5 text-xs font-normal">
                                {master.description}
                              </p>
                            ) : null}
                          </TableCell>
                          <TableCell className="whitespace-nowrap">{master.recurrence}</TableCell>
                          <TableCell>
                            <PriorityBadge priority={master.default_priority} />
                          </TableCell>
                          <TableCell className="text-muted-foreground text-sm">
                            {master.statutory_due ?? '—'}
                          </TableCell>
                          <TableCell className="text-center">
                            <Switch
                              checked={master.is_active}
                              onCheckedChange={(checked) =>
                                toggleActive.mutate({ id: master.id, is_active: checked })
                              }
                              aria-label={`Toggle ${master.name}`}
                            />
                          </TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm" onClick={() => openEdit(master)}>
                              <Pencil className="size-3.5" />
                              Edit
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{draft.id ? 'Edit Master Task' : 'Add Master Task'}</DialogTitle>
            <DialogDescription>
              These defaults pre-fill the allocation form. They stay editable per task.
            </DialogDescription>
          </DialogHeader>
          <form className="grid gap-4 sm:grid-cols-2" onSubmit={submit} noValidate>
            <Field
              label="Task Name"
              htmlFor="master-name"
              error={errors.name}
              className="sm:col-span-2"
              required
            >
              <Input
                id="master-name"
                value={draft.name}
                onChange={(e) => set('name', e.target.value)}
                placeholder="e.g. GSTR-3B Monthly Filing"
              />
            </Field>
            <Field label="Category" error={errors.category} required>
              <CreatableCombobox
                options={categories}
                value={draft.category}
                onChange={(val) => set('category', val)}
              />
            </Field>
            <Field label="Recurrence" required>
              <Select
                value={draft.recurrence}
                onValueChange={(val) => set('recurrence', val as Recurrence)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {RECURRENCES.map((recurrence) => (
                    <SelectItem key={recurrence} value={recurrence}>
                      {recurrence}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Default Priority" required>
              <Select
                value={draft.default_priority}
                onValueChange={(val) => set('default_priority', val as TaskPriority)}
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
            <Field
              label="Statutory Due"
              htmlFor="master-due"
              hint="Free text, e.g. “20th of following month”."
              className="sm:col-span-2"
            >
              <Input
                id="master-due"
                value={draft.statutory_due}
                onChange={(e) => set('statutory_due', e.target.value)}
              />
            </Field>
            <Field label="Description" htmlFor="master-description" className="sm:col-span-2">
              <Textarea
                id="master-description"
                rows={2}
                value={draft.description}
                onChange={(e) => set('description', e.target.value)}
              />
            </Field>
            <DialogFooter className="sm:col-span-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saveMaster.isPending}>
                {saveMaster.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
                {draft.id ? 'Save changes' : 'Add Task'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
