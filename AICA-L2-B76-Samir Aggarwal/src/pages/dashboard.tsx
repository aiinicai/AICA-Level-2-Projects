import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  Building2,
  CalendarClock,
  ClipboardList,
  Hourglass,
  Layers,
  Loader2,
  RotateCcw,
  TriangleAlert,
  Users,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  AgeingBadge,
  EmptyState,
  OverdueBadge,
  PageHeader,
  StageBadge,
  StatCard,
} from '@/components/common'
import {
  useClientCompliance,
  useClients,
  useComplianceMasters,
  useGstRegistrations,
  useProfiles,
  useStages,
  useTasks,
} from '@/hooks/use-app-data'
import { friendlyError } from '@/lib/supabase'
import {
  AGEING_ALERT,
  AGEING_WARN,
  FINANCIAL_YEARS,
  STAGE_DROPPED,
  STAGE_NEED_HELP,
  stageVar,
} from '@/lib/constants'
import { cn, formatDate } from '@/lib/utils'
import type { TaskEnriched } from '@/types/db'

type GroupBy = 'client' | 'group' | 'staff' | 'category'

interface PivotRow {
  key: string
  label: string
  sublabel?: string
  counts: Record<string, number>
  total: number
  pending: number
  overdue: number
  needHelp: number
  oldest: number
}

export default function StatusBoardPage() {
  const tasksQuery = useTasks()
  const { stages, isLoading: stagesLoading } = useStages()
  const profilesQuery = useProfiles()
  const clientsQuery = useClients()
  const ticksQuery = useClientCompliance()
  const complianceQuery = useComplianceMasters()
  const gstinsQuery = useGstRegistrations()

  const [groupBy, setGroupBy] = useState<GroupBy>('client')
  const [financialYear, setFinancialYear] = useState('all')
  const [category, setCategory] = useState('all')
  const [assignee, setAssignee] = useState('all')
  const [client, setClient] = useState('all')
  const [showDropped, setShowDropped] = useState(false)
  const [overdueOnly, setOverdueOnly] = useState(false)
  const [drill, setDrill] = useState<{ title: string; subtitle: string; tasks: TaskEnriched[] } | null>(
    null,
  )

  const allTasks = tasksQuery.data ?? []

  const visibleStages = useMemo(
    () => stages.filter((s) => showDropped || s.code !== STAGE_DROPPED),
    [stages, showDropped],
  )

  const categories = useMemo(() => {
    const set = new Set<string>()
    for (const task of allTasks) set.add(task.category)
    return [...set].sort((a, b) => a.localeCompare(b))
  }, [allTasks])

  const tasks = useMemo(
    () =>
      allTasks.filter((task) => {
        if (!showDropped && task.stage_is_dropped) return false
        if (financialYear !== 'all' && task.financial_year !== financialYear) return false
        if (category !== 'all' && task.category !== category) return false
        if (assignee !== 'all' && task.assigned_to !== assignee) return false
        if (client !== 'all' && task.client_id !== client) return false
        if (overdueOnly && !task.is_overdue) return false
        return true
      }),
    [allTasks, showDropped, financialYear, category, assignee, client, overdueOnly],
  )

  const hasFilters =
    financialYear !== 'all' ||
    category !== 'all' ||
    assignee !== 'all' ||
    client !== 'all' ||
    overdueOnly ||
    showDropped

  function resetFilters() {
    setFinancialYear('all')
    setCategory('all')
    setAssignee('all')
    setClient('all')
    setOverdueOnly(false)
    setShowDropped(false)
  }

  // ---- headline numbers: one per stage, plus the two that need chasing ----
  const stageCounts = useMemo(() => {
    const map = new Map<string, number>()
    for (const task of tasks) map.set(task.stage_code, (map.get(task.stage_code) ?? 0) + 1)
    return map
  }, [tasks])

  const overdueCount = useMemo(() => tasks.filter((t) => t.is_overdue).length, [tasks])
  const stuckCount = useMemo(
    () => tasks.filter((t) => !t.stage_is_terminal && t.days_in_stage >= AGEING_ALERT).length,
    [tasks],
  )

  // ---- the pivot ----
  const pivot = useMemo<PivotRow[]>(() => {
    const map = new Map<string, PivotRow>()

    for (const task of tasks) {
      let key: string
      let label: string
      let sublabel: string | undefined

      if (groupBy === 'client') {
        key = task.client_id ?? '__internal__'
        label = task.client_name ?? 'Internal / no client'
        sublabel = task.client_code ?? undefined
      } else if (groupBy === 'group') {
        key = task.client_group ?? (task.client_id ? '__ungrouped__' : '__internal__')
        label = task.client_group ?? (task.client_id ? 'Ungrouped clients' : 'Internal / no client')
      } else if (groupBy === 'staff') {
        key = task.assigned_to
        label = task.assignee_name
        sublabel = task.assignee_designation
      } else {
        key = task.category
        label = task.category
      }

      let row = map.get(key)
      if (!row) {
        row = {
          key,
          label,
          sublabel,
          counts: {},
          total: 0,
          pending: 0,
          overdue: 0,
          needHelp: 0,
          oldest: 0,
        }
        map.set(key, row)
      }

      row.counts[task.stage_code] = (row.counts[task.stage_code] ?? 0) + 1
      row.total += 1
      if (!task.stage_is_terminal) {
        row.pending += 1
        row.oldest = Math.max(row.oldest, task.days_in_stage)
      }
      if (task.is_overdue) row.overdue += 1
      if (task.stage_code === STAGE_NEED_HELP) row.needHelp += 1
    }

    // Most pending work first — that is what a partner opens this page to find.
    return [...map.values()].sort((a, b) => b.pending - a.pending || b.total - a.total)
  }, [tasks, groupBy])

  function openDrill(row: PivotRow, stageCode: string | null) {
    const matching = tasks.filter((task) => {
      const rowKey =
        groupBy === 'client'
          ? (task.client_id ?? '__internal__')
          : groupBy === 'group'
            ? (task.client_group ?? (task.client_id ? '__ungrouped__' : '__internal__'))
            : groupBy === 'staff'
              ? task.assigned_to
              : task.category
      if (rowKey !== row.key) return false
      if (stageCode && task.stage_code !== stageCode) return false
      return true
    })
    if (!matching.length) return

    const stageName = stageCode ? stages.find((s) => s.code === stageCode)?.name : null
    setDrill({
      title: row.label,
      subtitle: stageName ? `${stageName} — ${matching.length} task(s)` : `All ${matching.length} task(s)`,
      tasks: matching,
    })
  }

  // Compliance ticks that will silently generate NOTHING: no assignee, or a
  // per-GSTIN rule on a client without an active GSTIN. This is the loud
  // warning the skip-on-blank policy depends on.
  const deadTicks = useMemo(() => {
    const masters = new Map((complianceQuery.data ?? []).map((m) => [m.id, m]))
    const clientById = new Map((clientsQuery.data ?? []).map((c) => [c.id, c.name]))
    const gstinClients = new Set(
      (gstinsQuery.data ?? []).filter((g) => g.is_active).map((g) => g.client_id),
    )
    const issues: { key: string; client: string; rule: string; reason: string }[] = []
    for (const tick of ticksQuery.data ?? []) {
      const master = masters.get(tick.compliance_id)
      if (!master || !master.is_generatable) continue
      const clientName = clientById.get(tick.client_id) ?? 'Unknown client'
      if (!tick.assigned_to) {
        issues.push({
          key: `${tick.id}-a`,
          client: clientName,
          rule: master.name,
          reason: 'no assignee',
        })
      }
      if (master.target_level === 'GSTIN' && !gstinClients.has(tick.client_id)) {
        issues.push({
          key: `${tick.id}-g`,
          client: clientName,
          rule: master.name,
          reason: 'no active GSTIN',
        })
      }
    }
    return issues
  }, [ticksQuery.data, complianceQuery.data, clientsQuery.data, gstinsQuery.data])

  const stuckList = useMemo(
    () =>
      tasks
        .filter((t) => !t.stage_is_terminal)
        .sort((a, b) => b.days_in_stage - a.days_in_stage)
        .slice(0, 12),
    [tasks],
  )

  const needHelpList = useMemo(
    () =>
      tasks
        .filter((t) => t.stage_code === STAGE_NEED_HELP)
        .sort((a, b) => b.days_in_stage - a.days_in_stage),
    [tasks],
  )

  if (tasksQuery.isLoading || stagesLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="text-muted-foreground size-6 animate-spin" />
      </div>
    )
  }

  if (tasksQuery.error) {
    return <div className="text-destructive text-sm">{friendlyError(tasksQuery.error)}</div>
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Status Board"
        description="What is pending, at which stage, and for whom."
      >
        {hasFilters ? (
          <Button variant="outline" size="sm" onClick={resetFilters}>
            <RotateCcw className="size-3.5" />
            Reset
          </Button>
        ) : null}
      </PageHeader>

      {/* One card per stage, then the two that need chasing. */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 xl:grid-cols-7">
        {visibleStages.map((stage) => (
          <Card key={stage.id} className="gap-0 py-4">
            <CardContent className="px-4">
              <div className="flex items-center gap-1.5">
                <span
                  className="size-2 shrink-0 rounded-full"
                  style={{ backgroundColor: stageVar(stage.code) }}
                />
                <p className="text-muted-foreground truncate text-xs font-medium tracking-wide uppercase">
                  {stage.name}
                </p>
              </div>
              <p
                className="mt-1 text-2xl font-semibold tabular-nums"
                style={{ color: stageVar(stage.code) }}
              >
                {stageCounts.get(stage.code) ?? 0}
              </p>
            </CardContent>
          </Card>
        ))}
        <StatCard
          label="Overdue"
          value={overdueCount}
          icon={AlertTriangle}
          tone={overdueCount > 0 ? 'destructive' : 'default'}
        />
        <StatCard
          label={`Stuck ${AGEING_ALERT}d+`}
          value={stuckCount}
          icon={Hourglass}
          tone={stuckCount > 0 ? 'accent' : 'default'}
          hint="in the same stage"
        />
      </div>

      {deadTicks.length ? (
        <Card className="border-destructive/40 py-0">
          <CardContent className="flex flex-col gap-2 p-4">
            <p className="text-destructive flex items-center gap-2 text-sm font-semibold">
              <AlertTriangle className="size-4" />
              {deadTicks.length} compliance tick{deadTicks.length === 1 ? ' is' : 's are'} not
              generating anything
            </p>
            <ul className="text-muted-foreground grid gap-1 text-sm sm:grid-cols-2">
              {deadTicks.slice(0, 8).map((issue) => (
                <li key={issue.key}>
                  <span className="text-foreground font-medium">{issue.client}</span> —{' '}
                  {issue.rule} <span className="text-destructive">({issue.reason})</span>
                </li>
              ))}
              {deadTicks.length > 8 ? <li>+{deadTicks.length - 8} more</li> : null}
            </ul>
            <p className="text-muted-foreground text-xs">
              Fix under Clients → Compliance: set who handles it, or add the missing GSTIN.
            </p>
          </CardContent>
        </Card>
      ) : null}

      {/* Filters */}
      <Card className="py-0">
        <CardContent className="grid gap-2 p-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
          <Select value={financialYear} onValueChange={setFinancialYear}>
            <SelectTrigger>
              <SelectValue placeholder="Financial year" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All years</SelectItem>
              {FINANCIAL_YEARS.map((year) => (
                <SelectItem key={year} value={year}>
                  FY {year}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={client} onValueChange={setClient}>
            <SelectTrigger>
              <SelectValue placeholder="Client" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All clients</SelectItem>
              {(clientsQuery.data ?? []).map((row) => (
                <SelectItem key={row.id} value={row.id}>
                  {row.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={assignee} onValueChange={setAssignee}>
            <SelectTrigger>
              <SelectValue placeholder="Staff" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All staff</SelectItem>
              {(profilesQuery.data ?? []).map((row) => (
                <SelectItem key={row.id} value={row.id}>
                  {row.full_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger>
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {categories.map((row) => (
                <SelectItem key={row} value={row}>
                  {row}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <label className="flex items-center gap-2 text-sm">
            <Switch checked={overdueOnly} onCheckedChange={setOverdueOnly} />
            Overdue only
          </label>
          <label className="flex items-center gap-2 text-sm">
            <Switch checked={showDropped} onCheckedChange={setShowDropped} />
            Show dropped
          </label>
        </CardContent>
      </Card>

      {/* The pivot */}
      <Card className="py-0">
        <CardHeader className="border-b p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="text-base">Pending by stage</CardTitle>
              <CardDescription>
                Click any number to see those tasks. {tasks.length} task(s) in view.
              </CardDescription>
            </div>
            <Tabs value={groupBy} onValueChange={(v) => setGroupBy(v as GroupBy)}>
              <TabsList>
                <TabsTrigger value="client">
                  <Building2 className="size-3.5" />
                  By Client
                </TabsTrigger>
                <TabsTrigger value="group">
                  <Layers className="size-3.5" />
                  By Group
                </TabsTrigger>
                <TabsTrigger value="staff">
                  <Users className="size-3.5" />
                  By Staff
                </TabsTrigger>
                <TabsTrigger value="category">
                  <ClipboardList className="size-3.5" />
                  By Category
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {pivot.length === 0 ? (
            <div className="p-4">
              <EmptyState
                title="Nothing to show"
                description={
                  hasFilters
                    ? 'No tasks match these filters.'
                    : 'Allocate some work and it will appear here, grouped by stage.'
                }
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="min-w-48">
                      {groupBy === 'client'
                        ? 'Client'
                        : groupBy === 'group'
                          ? 'Client Group'
                          : groupBy === 'staff'
                            ? 'Staff'
                            : 'Category'}
                    </TableHead>
                    {visibleStages.map((stage) => (
                      <TableHead key={stage.id} className="text-center">
                        <span className="inline-flex items-center gap-1">
                          <span
                            className="size-1.5 rounded-full"
                            style={{ backgroundColor: stageVar(stage.code) }}
                          />
                          {stage.name}
                        </span>
                      </TableHead>
                    ))}
                    <TableHead className="text-center">Pending</TableHead>
                    <TableHead className="text-center">Overdue</TableHead>
                    <TableHead className="text-center">Oldest</TableHead>
                    <TableHead className="text-center">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pivot.map((row) => (
                    <TableRow key={row.key}>
                      <TableCell className="font-medium">
                        <button
                          type="button"
                          className="text-left hover:underline"
                          onClick={() => openDrill(row, null)}
                        >
                          {row.label}
                        </button>
                        {row.sublabel ? (
                          <p className="text-muted-foreground text-xs font-normal">
                            {row.sublabel}
                          </p>
                        ) : null}
                      </TableCell>

                      {visibleStages.map((stage) => {
                        const count = row.counts[stage.code] ?? 0
                        return (
                          <TableCell key={stage.id} className="text-center">
                            {count ? (
                              <button
                                type="button"
                                onClick={() => openDrill(row, stage.code)}
                                className="inline-flex min-w-8 justify-center rounded-md px-2 py-0.5 text-sm font-semibold tabular-nums hover:underline"
                                style={{
                                  color: stageVar(stage.code),
                                  backgroundColor: `color-mix(in srgb, ${stageVar(stage.code)} 12%, transparent)`,
                                }}
                              >
                                {count}
                              </button>
                            ) : (
                              <span className="text-muted-foreground/40 text-sm">·</span>
                            )}
                          </TableCell>
                        )
                      })}

                      <TableCell className="text-center font-semibold tabular-nums">
                        {row.pending}
                      </TableCell>
                      <TableCell
                        className={cn(
                          'text-center tabular-nums',
                          row.overdue > 0 && 'text-destructive font-semibold',
                        )}
                      >
                        {row.overdue || '·'}
                      </TableCell>
                      <TableCell className="text-center">
                        {row.pending ? (
                          <AgeingBadge days={row.oldest} />
                        ) : (
                          <span className="text-muted-foreground/40 text-sm">·</span>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-center tabular-nums">
                        {row.total}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-3 lg:grid-cols-2">
        {/* Need Help queue preview */}
        <Card className="py-0">
          <CardHeader className="border-b p-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <TriangleAlert className="size-4" style={{ color: stageVar(STAGE_NEED_HELP) }} />
              Need Help
              <Badge variant="secondary" className="tabular-nums">
                {needHelpList.length}
              </Badge>
            </CardTitle>
            <CardDescription>Blocked work, longest waiting first.</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {needHelpList.length === 0 ? (
              <p className="text-muted-foreground p-4 text-sm">Nobody is blocked. </p>
            ) : (
              <ul className="divide-y">
                {needHelpList.slice(0, 6).map((task) => (
                  <li key={task.id} className="px-3 py-2">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <Link
                          to={`/tasks/${task.id}`}
                          title={task.title}
                          className="block truncate text-sm font-medium hover:underline"
                        >
                          {task.title}
                        </Link>
                        <p className="text-muted-foreground truncate text-xs">
                          {task.client_name ?? 'Internal'} · {task.assignee_name}
                        </p>
                        {task.help_note ? (
                          <p className="mt-1 line-clamp-2 text-xs">{task.help_note}</p>
                        ) : null}
                      </div>
                      <AgeingBadge days={task.days_in_stage} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
            {needHelpList.length > 6 ? (
              <div className="border-t p-3">
                <Button variant="ghost" size="sm" asChild>
                  <Link to="/need-help">See all {needHelpList.length}</Link>
                </Button>
              </div>
            ) : null}
          </CardContent>
        </Card>

        {/* Ageing */}
        <Card className="py-0">
          <CardHeader className="border-b p-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <Hourglass className="size-4" />
              Sitting longest
            </CardTitle>
            <CardDescription>
              Open work by days in its current stage. Amber past {AGEING_WARN} days, red past{' '}
              {AGEING_ALERT}.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {stuckList.length === 0 ? (
              <p className="text-muted-foreground p-4 text-sm">No open work.</p>
            ) : (
              <ul className="divide-y">
                {stuckList.map((task) => (
                  <li key={task.id} className="flex items-center justify-between gap-3 px-3 py-2">
                    <div className="min-w-0">
                      <Link
                        to={`/tasks/${task.id}`}
                        title={task.title}
                        className="block truncate text-sm font-medium hover:underline"
                      >
                        {task.title}
                      </Link>
                      <p className="text-muted-foreground truncate text-xs">
                        {task.client_name ?? 'Internal'} · {task.assignee_name}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      {task.is_overdue ? <OverdueBadge days={task.days_to_due} /> : null}
                      <span className="hidden sm:inline-flex">
                        <StageBadge code={task.stage_code} name={task.stage_name} />
                      </span>
                      <AgeingBadge days={task.days_in_stage} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Drill-down */}
      <Sheet open={Boolean(drill)} onOpenChange={(open) => !open && setDrill(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>{drill?.title}</SheetTitle>
            <SheetDescription>{drill?.subtitle}</SheetDescription>
          </SheetHeader>
          <ul className="divide-y px-4 pb-6">
            {drill?.tasks.map((task) => (
              <li key={task.id} className="py-2.5">
                <Link
                  to={`/tasks/${task.id}`}
                  title={task.title}
                  className="block truncate text-sm font-medium hover:underline"
                >
                  {task.title}
                </Link>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <StageBadge code={task.stage_code} name={task.stage_name} />
                  {task.is_overdue ? <OverdueBadge days={task.days_to_due} /> : null}
                  <span className="text-muted-foreground text-xs">
                    {groupBy === 'staff' ? (task.client_name ?? 'Internal') : task.assignee_name}
                  </span>
                </div>
                <div className="text-muted-foreground mt-1 flex items-center gap-3 text-xs">
                  <span className="inline-flex items-center gap-1">
                    <CalendarClock className="size-3" />
                    {formatDate(task.due_date)}
                  </span>
                  <span>
                    in stage <AgeingBadge days={task.days_in_stage} terminal={task.stage_is_terminal} />
                  </span>
                </div>
                {task.help_note ? (
                  <p className="bg-muted mt-2 rounded-md px-2 py-1 text-xs">{task.help_note}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </SheetContent>
      </Sheet>
    </div>
  )
}
