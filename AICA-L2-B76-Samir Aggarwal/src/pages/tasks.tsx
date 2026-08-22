import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ClipboardList,
  Download,
  Loader2,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  UserCog,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import {
  AgeingBadge,
  CategoryBadge,
  ComplianceBadge,
  EmptyState,
  Field,
  OverdueBadge,
  PageHeader,
  PriorityBadge,
  StageBadge,
  TableSkeleton,
  UpcomingBadge,
} from '@/components/common'
import { Combobox, CreatableCombobox } from '@/components/combobox'
import { StagePicker } from '@/components/stage-picker'
import { useAuth } from '@/components/auth-provider'
import {
  QK,
  useClients,
  useProfiles,
  useStages,
  useTaskMasters,
  useTasks,
} from '@/hooks/use-app-data'
import { friendlyError, supabase } from '@/lib/supabase'
import {
  DEFAULT_FINANCIAL_YEAR,
  FINANCIAL_YEARS,
  PRIORITIES,
  RECURRENCES,
  SEEDED_CATEGORIES,
  STAGE_DROPPED,
  stageVar,
} from '@/lib/constants'
import { cn, downloadCSV, formatDate, todayISO } from '@/lib/utils'
import type { Recurrence, TaskEnriched, TaskPriority } from '@/types/db'

interface AllocateDraft {
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

const EMPTY_ALLOCATE: AllocateDraft = {
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

export default function TasksPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { session } = useAuth()

  const tasksQuery = useTasks()
  const { stages } = useStages()
  const profilesQuery = useProfiles()
  const clientsQuery = useClients()
  const mastersQuery = useTaskMasters()

  const [search, setSearch] = useState('')
  const [assigneeFilter, setAssigneeFilter] = useState('all')
  const [clientFilter, setClientFilter] = useState('all')
  const [stageFilter, setStageFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [dueFrom, setDueFrom] = useState('')
  const [dueTo, setDueTo] = useState('')
  const [showDropped, setShowDropped] = useState(false)
  const [natureFilter, setNatureFilter] = useState<'all' | 'compliance' | 'manual'>('all')
  const [groupFilter, setGroupFilter] = useState('all')

  type SortKey = 'title' | 'client' | 'assignee' | 'category' | 'stage' | 'days' | 'due'
  const [sortKey, setSortKey] = useState<SortKey>('stage')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((dir) => (dir === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const [allocateOpen, setAllocateOpen] = useState(false)
  const [draft, setDraft] = useState<AllocateDraft>(EMPTY_ALLOCATE)
  const [bulkMode, setBulkMode] = useState(false)
  const [bulkAssignees, setBulkAssignees] = useState<string[]>([])
  const [allocateErrors, setAllocateErrors] = useState<Record<string, string>>({})

  // Creating a catalogue entry without leaving the allocation flow. Without
  // this the only escape for an unlisted job is "Ad-hoc", which is one-off and
  // never becomes reusable.
  const [newMasterOpen, setNewMasterOpen] = useState(false)
  const [newMaster, setNewMaster] = useState({
    name: '',
    category: '',
    recurrence: 'One-time' as Recurrence,
    default_priority: 'Medium' as TaskPriority,
    statutory_due: '',
    description: '',
  })
  const [newMasterErrors, setNewMasterErrors] = useState<Record<string, string>>({})

  const [editing, setEditing] = useState<TaskEnriched | null>(null)
  const [reassigning, setReassigning] = useState<TaskEnriched | null>(null)
  const [reassignTo, setReassignTo] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<TaskEnriched | null>(null)

  const activeProfiles = useMemo(
    () => (profilesQuery.data ?? []).filter((p) => p.is_active),
    [profilesQuery.data],
  )

  const assigneeOptions = useMemo(
    () => activeProfiles.map((p) => ({ value: p.id, label: `${p.full_name} — ${p.designation}` })),
    [activeProfiles],
  )

  const clientOptions = useMemo(
    () =>
      (clientsQuery.data ?? [])
        .filter((c) => c.is_active)
        .map((c) => ({ value: c.id, label: c.name, hint: c.client_code ?? undefined })),
    [clientsQuery.data],
  )

  const masterOptions = useMemo(
    () =>
      (mastersQuery.data ?? [])
        .filter((m) => m.is_active)
        .map((m) => ({ value: m.id, label: m.name, group: m.category })),
    [mastersQuery.data],
  )

  const categories = useMemo(() => {
    const set = new Set<string>()
    for (const task of tasksQuery.data ?? []) set.add(task.category)
    return [...set].sort((a, b) => a.localeCompare(b))
  }, [tasksQuery.data])

  const clientGroups = useMemo(() => {
    const set = new Set<string>()
    for (const client of clientsQuery.data ?? []) {
      if (client.client_group) set.add(client.client_group)
    }
    return [...set].sort((a, b) => a.localeCompare(b))
  }, [clientsQuery.data])

  /** Categories offered when creating a master task — seeded plus whatever exists. */
  const masterCategories = useMemo(() => {
    const set = new Set(SEEDED_CATEGORIES)
    for (const master of mastersQuery.data ?? []) set.add(master.category)
    return [...set].sort((a, b) => a.localeCompare(b))
  }, [mastersQuery.data])

  const invalidate = () => void queryClient.invalidateQueries({ queryKey: QK.tasks })

  const allocate = useMutation({
    mutationFn: async (payload: { draft: AllocateDraft; assignees: string[] }) => {
      const base = {
        title: payload.draft.title.trim(),
        task_master_id: payload.draft.source === 'master' ? payload.draft.task_master_id : null,
        is_adhoc: payload.draft.source === 'adhoc',
        client_id: payload.draft.client_id,
        assigned_by: session?.user.id ?? '',
        priority: payload.draft.priority,
        description: payload.draft.description.trim() || null,
        financial_year: payload.draft.financial_year || null,
        period: payload.draft.period.trim() || null,
        start_date: payload.draft.start_date || null,
        due_date: payload.draft.due_date || null,
      }
      // stage_id is left to the column default: everything starts at 01.
      const rows = payload.assignees.map((assigned_to) => ({ ...base, assigned_to }))
      const { error } = await supabase.from('tasks').insert(rows)
      if (error) throw error
      return rows.length
    },
    onSuccess: (count) => {
      invalidate()
      setAllocateOpen(false)
      toast.success(count === 1 ? 'Task allocated' : `${count} tasks allocated`)
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const createMaster = useMutation({
    mutationFn: async () => {
      const { data, error } = await supabase
        .from('task_master')
        .insert({
          name: newMaster.name.trim(),
          category: newMaster.category.trim(),
          recurrence: newMaster.recurrence,
          default_priority: newMaster.default_priority,
          statutory_due: newMaster.statutory_due.trim() || null,
          description: newMaster.description.trim() || null,
        })
        .select('id, name, default_priority, description')
        .single()
      if (error) throw error
      return data as {
        id: string
        name: string
        default_priority: TaskPriority
        description: string | null
      }
    },
    onSuccess: (master) => {
      void queryClient.invalidateQueries({ queryKey: QK.masters })
      // Select it straight away, so the partner carries on allocating.
      setDraft((prev) => ({
        ...prev,
        source: 'master',
        task_master_id: master.id,
        title: master.name,
        priority: master.default_priority,
        description: master.description ?? prev.description,
      }))
      setAllocateErrors((prev) => ({ ...prev, master: '' }))
      setNewMasterOpen(false)
      toast.success('Added to the task master and selected')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const updateTask = useMutation({
    mutationFn: async (payload: TaskEnriched) => {
      const { error } = await supabase
        .from('tasks')
        .update({
          title: payload.title.trim(),
          description: payload.description,
          client_id: payload.client_id,
          assigned_to: payload.assigned_to,
          priority: payload.priority,
          financial_year: payload.financial_year,
          period: payload.period,
          start_date: payload.start_date || null,
          due_date: payload.due_date || null,
        })
        .eq('id', payload.id)
      if (error) throw error
    },
    onSuccess: () => {
      invalidate()
      setEditing(null)
      toast.success('Task updated')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const reassign = useMutation({
    mutationFn: async (payload: { id: string; assigned_to: string }) => {
      const { error } = await supabase
        .from('tasks')
        .update({ assigned_to: payload.assigned_to })
        .eq('id', payload.id)
      if (error) throw error
    },
    onSuccess: () => {
      invalidate()
      setReassigning(null)
      toast.success('Task reassigned')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const deleteTask = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.from('tasks').delete().eq('id', id)
      if (error) throw error
    },
    onSuccess: () => {
      invalidate()
      setDeleting(null)
      toast.success('Task deleted')
    },
    onError: (error) => toast.error(friendlyError(error)),
  })

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return (tasksQuery.data ?? []).filter((task) => {
      if (!showDropped && task.stage_is_dropped) return false
      if (natureFilter === 'compliance' && !task.is_compliance) return false
      if (natureFilter === 'manual' && task.is_compliance) return false
      if (groupFilter === '__none__' && task.client_group) return false
      if (groupFilter !== 'all' && groupFilter !== '__none__' && task.client_group !== groupFilter)
        return false
      if (assigneeFilter !== 'all' && task.assigned_to !== assigneeFilter) return false
      if (clientFilter !== 'all' && task.client_id !== clientFilter) return false
      if (stageFilter !== 'all' && task.stage_id !== stageFilter) return false
      if (priorityFilter !== 'all' && task.priority !== priorityFilter) return false
      if (categoryFilter !== 'all' && task.category !== categoryFilter) return false
      if (dueFrom && (!task.due_date || task.due_date < dueFrom)) return false
      if (dueTo && (!task.due_date || task.due_date > dueTo)) return false
      if (!term) return true
      return (
        task.title.toLowerCase().includes(term) ||
        (task.client_name ?? '').toLowerCase().includes(term)
      )
    })
  }, [
    tasksQuery.data,
    search,
    showDropped,
    natureFilter,
    groupFilter,
    assigneeFilter,
    clientFilter,
    stageFilter,
    priorityFilter,
    categoryFilter,
    dueFrom,
    dueTo,
  ])

  const sorted = useMemo(() => {
    const value = (task: TaskEnriched): string | number => {
      switch (sortKey) {
        case 'title':
          return task.title.toLowerCase()
        case 'client':
          return (task.client_name ?? '').toLowerCase()
        case 'assignee':
          return task.assignee_name.toLowerCase()
        case 'category':
          return task.category.toLowerCase()
        case 'stage':
          return task.stage_sort
        case 'days':
          return task.days_in_stage
        case 'due':
          return task.due_date ?? '9999-12-31'
      }
    }
    const factor = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      const av = value(a)
      const bv = value(b)
      const cmp =
        typeof av === 'number' && typeof bv === 'number'
          ? av - bv
          : String(av).localeCompare(String(bv))
      if (cmp !== 0) return cmp * factor
      // Stable tie-break: nearest due date first.
      return (a.due_date ?? '9999').localeCompare(b.due_date ?? '9999')
    })
  }, [filtered, sortKey, sortDir])

  function SortHead({
    label,
    k,
    className,
  }: {
    label: string
    k: SortKey
    className?: string
  }) {
    const active = sortKey === k
    const Icon = active ? (sortDir === 'asc' ? ArrowUp : ArrowDown) : ArrowUpDown
    return (
      <TableHead className={className}>
        <button
          type="button"
          onClick={() => toggleSort(k)}
          className={cn(
            'hover:text-foreground inline-flex items-center gap-1',
            active && 'text-foreground',
          )}
        >
          {label}
          <Icon className={cn('size-3', !active && 'opacity-40')} />
        </button>
      </TableHead>
    )
  }

  const hasFilters =
    Boolean(search) ||
    assigneeFilter !== 'all' ||
    clientFilter !== 'all' ||
    stageFilter !== 'all' ||
    priorityFilter !== 'all' ||
    categoryFilter !== 'all' ||
    Boolean(dueFrom) ||
    Boolean(dueTo) ||
    showDropped ||
    natureFilter !== 'all' ||
    groupFilter !== 'all'

  function resetFilters() {
    setSearch('')
    setAssigneeFilter('all')
    setClientFilter('all')
    setStageFilter('all')
    setPriorityFilter('all')
    setCategoryFilter('all')
    setDueFrom('')
    setDueTo('')
    setShowDropped(false)
    setNatureFilter('all')
    setGroupFilter('all')
  }

  function exportCSV() {
    const header = [
      'Task',
      'Client',
      'Client Code',
      'Assignee',
      'Designation',
      'Category',
      'Priority',
      'Stage Code',
      'Stage',
      'Days In Stage',
      'Blocker',
      'Financial Year',
      'Period',
      'Start Date',
      'Due Date',
      'Overdue',
      'Assigned By',
    ]
    const rows = filtered.map((task) => [
      task.title,
      task.client_name ?? '',
      task.client_code ?? '',
      task.assignee_name,
      task.assignee_designation,
      task.category,
      task.priority,
      task.stage_code,
      task.stage_name,
      task.stage_is_terminal ? '' : task.days_in_stage,
      task.help_note ?? '',
      task.financial_year ?? '',
      task.period ?? '',
      task.start_date ?? '',
      task.due_date ?? '',
      task.is_overdue ? 'Yes' : 'No',
      task.assigner_name ?? '',
    ])
    downloadCSV(`tasks-${todayISO()}.csv`, [header, ...rows])
    toast.success(`Exported ${rows.length} tasks`)
  }

  function openAllocate() {
    setDraft(EMPTY_ALLOCATE)
    setBulkMode(false)
    setBulkAssignees([])
    setAllocateErrors({})
    setAllocateOpen(true)
  }

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

  function submitAllocate(event: React.FormEvent) {
    event.preventDefault()
    const errors: Record<string, string> = {}
    const assignees = bulkMode ? bulkAssignees : draft.assigned_to ? [draft.assigned_to] : []

    if (draft.source === 'master' && !draft.task_master_id) {
      errors.master = 'Choose a task from the master list.'
    }
    if (!draft.title.trim()) errors.title = 'Title is required.'
    if (!assignees.length) {
      errors.assignee = bulkMode ? 'Select at least one employee.' : 'Assign the task to someone.'
    }
    setAllocateErrors(errors)
    if (Object.keys(errors).length) return

    allocate.mutate({ draft, assignees })
  }

  const set = <K extends keyof AllocateDraft>(key: K, value: AllocateDraft[K]) =>
    setDraft((prev) => ({ ...prev, [key]: value }))

  return (
    <div className="space-y-5">
      <PageHeader title="All Tasks" description="Every job allocated across the firm.">
        <Button variant="outline" onClick={exportCSV} disabled={!filtered.length}>
          <Download className="size-4" />
          Export CSV
        </Button>
        <Button onClick={openAllocate}>
          <Plus className="size-4" />
          Allocate Task
        </Button>
      </PageHeader>

      <Card className="py-0">
        <CardContent className="space-y-3 p-4">
          <div className="relative">
            <Search className="text-muted-foreground absolute top-1/2 left-2.5 size-4 -translate-y-1/2" />
            <Input
              placeholder="Search task title or client…"
              className="pl-8"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
            <Select value={stageFilter} onValueChange={setStageFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Stage" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All stages</SelectItem>
                {stages.map((stage) => (
                  <SelectItem key={stage.id} value={stage.id}>
                    <span className="flex items-center gap-2">
                      <span
                        className="size-2 rounded-full"
                        style={{ backgroundColor: stageVar(stage.code) }}
                      />
                      {stage.name}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={assigneeFilter} onValueChange={setAssigneeFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Assignee" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All assignees</SelectItem>
                {activeProfiles.map((profile) => (
                  <SelectItem key={profile.id} value={profile.id}>
                    {profile.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={clientFilter} onValueChange={setClientFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Client" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All clients</SelectItem>
                {(clientsQuery.data ?? []).map((client) => (
                  <SelectItem key={client.id} value={client.id}>
                    {client.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={natureFilter}
              onValueChange={(value) => setNatureFilter(value as typeof natureFilter)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Nature" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Compliance + Tasks</SelectItem>
                <SelectItem value="compliance">Compliance only</SelectItem>
                <SelectItem value="manual">Tasks only</SelectItem>
              </SelectContent>
            </Select>
            <Select value={groupFilter} onValueChange={setGroupFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Client group" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All groups</SelectItem>
                <SelectItem value="__none__">No group / internal</SelectItem>
                {clientGroups.map((group) => (
                  <SelectItem key={group} value={group}>
                    {group}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {categories.map((category) => (
                  <SelectItem key={category} value={category}>
                    {category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All priorities</SelectItem>
                {PRIORITIES.map((priority) => (
                  <SelectItem key={priority} value={priority}>
                    {priority}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex items-center gap-1">
              <Input
                type="date"
                aria-label="Due from"
                value={dueFrom}
                onChange={(e) => setDueFrom(e.target.value)}
              />
              <span className="text-muted-foreground text-xs">to</span>
              <Input
                type="date"
                aria-label="Due to"
                value={dueTo}
                onChange={(e) => setDueTo(e.target.value)}
              />
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-muted-foreground text-sm">
              Showing <span className="text-foreground font-medium">{filtered.length}</span> of{' '}
              {tasksQuery.data?.length ?? 0} tasks
            </p>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={showDropped}
                  onCheckedChange={(checked) => setShowDropped(Boolean(checked))}
                />
                Show dropped
              </label>
              {hasFilters ? (
                <Button variant="ghost" size="sm" onClick={resetFilters}>
                  <RotateCcw className="size-3.5" />
                  Reset
                </Button>
              ) : null}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="py-0">
        <CardContent className="p-0">
          {tasksQuery.isLoading ? (
            <TableSkeleton cols={8} />
          ) : tasksQuery.error ? (
            <div className="text-destructive p-6 text-sm">{friendlyError(tasksQuery.error)}</div>
          ) : filtered.length === 0 ? (
            <div className="p-4">
              <EmptyState
                icon={ClipboardList}
                title={hasFilters ? 'No tasks match those filters' : 'No tasks allocated yet'}
                description={
                  hasFilters
                    ? 'Reset the filters to see the full list.'
                    : 'Allocate the first job to a team member to get started.'
                }
                action={
                  hasFilters ? (
                    <Button variant="outline" onClick={resetFilters}>
                      <RotateCcw className="size-4" />
                      Reset filters
                    </Button>
                  ) : (
                    <Button onClick={openAllocate}>
                      <Plus className="size-4" />
                      Allocate Task
                    </Button>
                  )
                }
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <SortHead label="Task" k="title" />
                    <SortHead label="Client" k="client" />
                    <SortHead label="Assignee" k="assignee" />
                    <SortHead label="Category" k="category" />
                    <SortHead label="Stage" k="stage" />
                    <SortHead label="In stage" k="days" className="text-right" />
                    <SortHead label="Due Date" k="due" />
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sorted.map((task) => (
                    <TableRow
                      key={task.id}
                      className={cn(
                        'cursor-pointer',
                        task.is_overdue && 'border-destructive border-l-2',
                      )}
                      onClick={() => navigate(`/tasks/${task.id}`)}
                    >
                      <TableCell className="max-w-xs font-medium">
                        <span className="line-clamp-2">{task.title}</span>
                        <span className="text-muted-foreground flex items-center gap-1.5 text-xs font-normal">
                          {task.is_adhoc ? 'Ad-hoc' : null}
                          {task.is_compliance ? <ComplianceBadge gstin={task.gstin} /> : null}
                          <PriorityBadge priority={task.priority} />
                        </span>
                      </TableCell>
                      <TableCell
                        className="max-w-44 truncate whitespace-nowrap"
                        title={task.client_name ?? 'Internal'}
                      >
                        {task.client_name ?? 'Internal'}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">{task.assignee_name}</TableCell>
                      <TableCell>
                        <CategoryBadge category={task.category} />
                      </TableCell>
                      <TableCell>
                        <StageBadge code={task.stage_code} name={task.stage_name} />
                      </TableCell>
                      <TableCell className="text-right">
                        <AgeingBadge
                          days={task.days_in_stage}
                          terminal={task.stage_is_terminal}
                        />
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {formatDate(task.due_date)}
                          {task.is_overdue ? (
                            <OverdueBadge days={task.days_to_due} />
                          ) : !task.stage_is_terminal ? (
                            <UpcomingBadge days={task.days_to_due} />
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell onClick={(event) => event.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1">
                          <StagePicker
                            taskId={task.id}
                            stageId={task.stage_id}
                            currentNote={task.help_note}
                            isCompliance={task.is_compliance}
                            taskTitle={task.title}
                            size="sm"
                            className="w-40"
                          />
                          <Button variant="ghost" size="sm" onClick={() => setEditing({ ...task })}>
                            <Pencil className="size-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setReassigning(task)
                              setReassignTo(task.assigned_to)
                            }}
                            aria-label="Reassign"
                          >
                            <UserCog className="size-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:text-destructive"
                            onClick={() => setDeleting(task)}
                            aria-label="Delete"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ---------------- Allocate ---------------- */}
      <Dialog open={allocateOpen} onOpenChange={setAllocateOpen}>
        <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Allocate Task</DialogTitle>
            <DialogDescription>
              Everything starts at stage 01, assigned but not started.
            </DialogDescription>
          </DialogHeader>

          <form className="space-y-4" onSubmit={submitAllocate} noValidate>
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
              <Field
                label="Master Task"
                error={allocateErrors.master}
                hint="Not in the list? Add it to the catalogue so it is reusable next time."
                required
              >
                <div className="flex gap-2">
                  <div className="min-w-0 flex-1">
                    <Combobox
                      options={masterOptions}
                      value={draft.task_master_id}
                      onChange={pickMaster}
                      placeholder="Search the task catalogue…"
                      emptyText="No active master task matches."
                    />
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    className="shrink-0"
                    onClick={() => {
                      setNewMaster({
                        name: '',
                        category: '',
                        recurrence: 'One-time',
                        default_priority: 'Medium',
                        statutory_due: '',
                        description: '',
                      })
                      setNewMasterErrors({})
                      setNewMasterOpen(true)
                    }}
                  >
                    <Plus className="size-4" />
                    New task
                  </Button>
                </div>
              </Field>
            ) : null}

            <Field label="Title" htmlFor="allocate-title" error={allocateErrors.title} required>
              <Input
                id="allocate-title"
                value={draft.title}
                onChange={(e) => set('title', e.target.value)}
                placeholder="e.g. GSTR-3B Monthly Filing"
              />
            </Field>

            <Field label="Description" htmlFor="allocate-description">
              <Textarea
                id="allocate-description"
                rows={2}
                value={draft.description}
                onChange={(e) => set('description', e.target.value)}
              />
            </Field>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Client" hint="Leave blank for internal work.">
                <Combobox
                  options={clientOptions}
                  value={draft.client_id}
                  onChange={(value) => set('client_id', value)}
                  placeholder="No client"
                  allowClear
                  clearLabel="No client (internal)"
                />
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
            </div>

            <div className="rounded-lg border p-3">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">Assign To</p>
                  <p className="text-muted-foreground text-xs">
                    Bulk allocate creates one identical task per employee.
                  </p>
                </div>
                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <Checkbox
                    checked={bulkMode}
                    onCheckedChange={(checked) => {
                      setBulkMode(Boolean(checked))
                      setBulkAssignees([])
                    }}
                  />
                  Bulk allocate
                </label>
              </div>

              {bulkMode ? (
                <div>
                  <ScrollArea className="h-44 rounded-md border">
                    <div className="space-y-1 p-2">
                      {activeProfiles.map((profile) => (
                        <label
                          key={profile.id}
                          className="hover:bg-muted flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm"
                        >
                          <Checkbox
                            checked={bulkAssignees.includes(profile.id)}
                            onCheckedChange={(checked) =>
                              setBulkAssignees((prev) =>
                                checked
                                  ? [...prev, profile.id]
                                  : prev.filter((id) => id !== profile.id),
                              )
                            }
                          />
                          <span className="font-medium">{profile.full_name}</span>
                          <span className="text-muted-foreground text-xs">
                            {profile.designation}
                          </span>
                        </label>
                      ))}
                    </div>
                  </ScrollArea>
                  <div className="mt-2 flex items-center justify-between">
                    <p className="text-muted-foreground text-xs">{bulkAssignees.length} selected</p>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setBulkAssignees(activeProfiles.map((p) => p.id))}
                      >
                        Select all
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setBulkAssignees([])}
                      >
                        Clear
                      </Button>
                    </div>
                  </div>
                  {allocateErrors.assignee ? (
                    <p className="text-destructive mt-1 text-xs">{allocateErrors.assignee}</p>
                  ) : null}
                </div>
              ) : (
                <Field label="Employee" error={allocateErrors.assignee} required>
                  <Combobox
                    options={assigneeOptions}
                    value={draft.assigned_to}
                    onChange={(value) => set('assigned_to', value)}
                    placeholder="Select an employee"
                  />
                </Field>
              )}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
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
              <Field label="Period" htmlFor="allocate-period" hint="e.g. Apr-2026 or Q1">
                <Input
                  id="allocate-period"
                  value={draft.period}
                  onChange={(e) => set('period', e.target.value)}
                />
              </Field>
              <Field label="Start Date" htmlFor="allocate-start">
                <Input
                  id="allocate-start"
                  type="date"
                  value={draft.start_date}
                  onChange={(e) => set('start_date', e.target.value)}
                />
              </Field>
              <Field label="Due Date" htmlFor="allocate-due">
                <Input
                  id="allocate-due"
                  type="date"
                  value={draft.due_date}
                  onChange={(e) => set('due_date', e.target.value)}
                />
              </Field>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAllocateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={allocate.isPending}>
                {allocate.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
                {bulkMode && bulkAssignees.length > 1
                  ? `Allocate to ${bulkAssignees.length} employees`
                  : 'Allocate Task'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ------- New master task, opened from inside allocation ------- */}
      <Dialog open={newMasterOpen} onOpenChange={setNewMasterOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Add to Task Master</DialogTitle>
            <DialogDescription>
              This adds a reusable entry to the firm's catalogue, then selects it for the task you
              are allocating.
            </DialogDescription>
          </DialogHeader>
          <form
            className="space-y-4"
            noValidate
            onSubmit={(event) => {
              event.preventDefault()
              const next: Record<string, string> = {}
              if (!newMaster.name.trim()) next.name = 'Task name is required.'
              if (!newMaster.category.trim()) next.category = 'Pick a category or type a new one.'
              setNewMasterErrors(next)
              if (Object.keys(next).length) return
              createMaster.mutate()
            }}
          >
            <Field label="Task Name" htmlFor="nm-name" error={newMasterErrors.name} required>
              <Input
                id="nm-name"
                autoFocus
                value={newMaster.name}
                onChange={(e) => setNewMaster({ ...newMaster, name: e.target.value })}
                placeholder="e.g. Scrutiny Assessment Representation"
              />
            </Field>
            <Field label="Category" error={newMasterErrors.category} required>
              <CreatableCombobox
                options={masterCategories}
                value={newMaster.category}
                onChange={(value) => setNewMaster({ ...newMaster, category: value })}
                createLabel="Create category"
              />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Recurrence">
                <Select
                  value={newMaster.recurrence}
                  onValueChange={(value) =>
                    setNewMaster({ ...newMaster, recurrence: value as Recurrence })
                  }
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
              <Field label="Default Priority">
                <Select
                  value={newMaster.default_priority}
                  onValueChange={(value) =>
                    setNewMaster({ ...newMaster, default_priority: value as TaskPriority })
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
            </div>
            <Field
              label="Statutory Due"
              htmlFor="nm-due"
              hint="Free text, e.g. “30 days from order”. Optional."
            >
              <Input
                id="nm-due"
                value={newMaster.statutory_due}
                onChange={(e) => setNewMaster({ ...newMaster, statutory_due: e.target.value })}
              />
            </Field>
            <Field label="Description" htmlFor="nm-description">
              <Textarea
                id="nm-description"
                rows={2}
                value={newMaster.description}
                onChange={(e) => setNewMaster({ ...newMaster, description: e.target.value })}
              />
            </Field>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setNewMasterOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMaster.isPending}>
                {createMaster.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
                Add and select
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ---------------- Edit ---------------- */}
      <Dialog open={Boolean(editing)} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Task</DialogTitle>
            <DialogDescription>
              Stage is changed from the board or the row, so it always records why.
            </DialogDescription>
          </DialogHeader>
          {editing ? (
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault()
                updateTask.mutate(editing)
              }}
            >
              <Field label="Title" htmlFor="edit-title" required>
                <Input
                  id="edit-title"
                  value={editing.title}
                  onChange={(e) => setEditing({ ...editing, title: e.target.value })}
                />
              </Field>
              <Field label="Description" htmlFor="edit-description">
                <Textarea
                  id="edit-description"
                  rows={2}
                  value={editing.description ?? ''}
                  onChange={(e) => setEditing({ ...editing, description: e.target.value })}
                />
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Client">
                  <Combobox
                    options={clientOptions}
                    value={editing.client_id}
                    onChange={(value) => setEditing({ ...editing, client_id: value })}
                    placeholder="No client"
                    allowClear
                    clearLabel="No client (internal)"
                  />
                </Field>
                <Field label="Assignee">
                  <Combobox
                    options={assigneeOptions}
                    value={editing.assigned_to}
                    onChange={(value) => value && setEditing({ ...editing, assigned_to: value })}
                    placeholder="Select an employee"
                  />
                </Field>
                <Field label="Priority">
                  <Select
                    value={editing.priority}
                    onValueChange={(value) =>
                      setEditing({ ...editing, priority: value as TaskPriority })
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
                    value={editing.financial_year ?? DEFAULT_FINANCIAL_YEAR}
                    onValueChange={(value) => setEditing({ ...editing, financial_year: value })}
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
                <Field label="Period" htmlFor="edit-period">
                  <Input
                    id="edit-period"
                    value={editing.period ?? ''}
                    onChange={(e) => setEditing({ ...editing, period: e.target.value })}
                  />
                </Field>
                <Field label="Start Date" htmlFor="edit-start">
                  <Input
                    id="edit-start"
                    type="date"
                    value={editing.start_date ?? ''}
                    onChange={(e) => setEditing({ ...editing, start_date: e.target.value })}
                  />
                </Field>
                <Field label="Due Date" htmlFor="edit-due">
                  <Input
                    id="edit-due"
                    type="date"
                    value={editing.due_date ?? ''}
                    onChange={(e) => setEditing({ ...editing, due_date: e.target.value })}
                  />
                </Field>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setEditing(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={updateTask.isPending}>
                  {updateTask.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
                  Save changes
                </Button>
              </DialogFooter>
            </form>
          ) : null}
        </DialogContent>
      </Dialog>

      {/* ---------------- Reassign ---------------- */}
      <Dialog open={Boolean(reassigning)} onOpenChange={(open) => !open && setReassigning(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Reassign Task</DialogTitle>
            <DialogDescription className="line-clamp-2">{reassigning?.title}</DialogDescription>
          </DialogHeader>
          <Field label="New assignee" hint={`Currently with ${reassigning?.assignee_name ?? '—'}`}>
            <Combobox
              options={assigneeOptions}
              value={reassignTo}
              onChange={setReassignTo}
              placeholder="Select an employee"
            />
          </Field>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReassigning(null)}>
              Cancel
            </Button>
            <Button
              disabled={!reassignTo || reassignTo === reassigning?.assigned_to || reassign.isPending}
              onClick={() =>
                reassigning &&
                reassignTo &&
                reassign.mutate({ id: reassigning.id, assigned_to: reassignTo })
              }
            >
              {reassign.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
              Reassign
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ---------------- Delete ---------------- */}
      <AlertDialog open={Boolean(deleting)} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this task?</AlertDialogTitle>
            <AlertDialogDescription>
              “{deleting?.title}” and its comments and history will be removed permanently. If you
              only want it off the board, move it to {STAGE_DROPPED} Dropped instead.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleting && deleteTask.mutate(deleting.id)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
