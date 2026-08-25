import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  ChevronDown,
  Hourglass,
  LayoutGrid,
  ListTodo,
  Loader2,
  Plus,
  Rows3,
  TriangleAlert,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  AgeingBadge,
  CategoryBadge,
  EmptyState,
  OverdueBadge,
  PageHeader,
  PriorityBadge,
  StatCard,
  UpcomingBadge,
} from '@/components/common'
import { StagePicker } from '@/components/stage-picker'
import { SelfTaskDialog } from '@/components/self-task-dialog'
import { useAuth } from '@/components/auth-provider'
import { useStages, useTasks } from '@/hooks/use-app-data'
import { friendlyError } from '@/lib/supabase'
import { AGEING_ALERT, STAGE_DROPPED, STAGE_NEED_HELP, stageVar } from '@/lib/constants'
import { cn, formatDate, relativeDueHint } from '@/lib/utils'
import type { Stage, TaskEnriched } from '@/types/db'

export default function MyTasksPage() {
  const { profile } = useAuth()
  const tasksQuery = useTasks()
  const { stages, isLoading: stagesLoading } = useStages()
  const [view, setView] = useState<'cards' | 'table'>('cards')
  const [doneOpen, setDoneOpen] = useState(false)
  const [addOpen, setAddOpen] = useState(false)

  // Visibility now includes tasks the user assigned to colleagues, so this
  // screen filters explicitly to work assigned TO them. What they handed out
  // lives on the Board.
  const tasks = useMemo(
    () =>
      (tasksQuery.data ?? []).filter(
        (t) => !t.stage_is_dropped && t.assigned_to === profile?.id,
      ),
    [tasksQuery.data, profile?.id],
  )

  const stats = useMemo(() => {
    const now = new Date()
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)
    return {
      total: tasks.length,
      pending: tasks.filter((t) => !t.stage_is_terminal).length,
      overdue: tasks.filter((t) => t.is_overdue).length,
      blocked: tasks.filter((t) => t.stage_code === STAGE_NEED_HELP).length,
      completedThisMonth: tasks.filter(
        (t) => t.completed_at && new Date(t.completed_at) >= monthStart,
      ).length,
    }
  }, [tasks])

  const openStages = useMemo(
    () => stages.filter((s) => !s.is_terminal && s.code !== STAGE_DROPPED),
    [stages],
  )
  const doneStages = useMemo(
    () => stages.filter((s) => s.is_terminal && s.code !== STAGE_DROPPED),
    [stages],
  )

  const byStage = useMemo(() => {
    const map = new Map<string, TaskEnriched[]>()
    for (const task of tasks) {
      const list = map.get(task.stage_id) ?? []
      list.push(task)
      map.set(task.stage_id, list)
    }
    // Overdue first, then longest-sitting.
    for (const list of map.values()) {
      list.sort((a, b) => {
        if (a.is_overdue !== b.is_overdue) return a.is_overdue ? -1 : 1
        return b.days_in_stage - a.days_in_stage
      })
    }
    return map
  }, [tasks])

  if (tasksQuery.isLoading || stagesLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="text-muted-foreground size-6 animate-spin" />
      </div>
    )
  }

  if (tasksQuery.error) {
    return (
      <div className="space-y-5">
        <PageHeader title="My Tasks" />
        <div className="text-destructive text-sm">{friendlyError(tasksQuery.error)}</div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="My Tasks"
        description={`${profile?.full_name ?? ''} — ${stats.pending} pending, ${stats.overdue} overdue`}
      >
        <Button onClick={() => setAddOpen(true)}>
          <Plus className="size-4" />
          Add Task
        </Button>
        <div className="flex items-center gap-1 rounded-md border p-0.5">
          <Button
            variant={view === 'cards' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setView('cards')}
          >
            <LayoutGrid className="size-3.5" />
            Cards
          </Button>
          <Button
            variant={view === 'table' ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setView('table')}
          >
            <Rows3 className="size-3.5" />
            Table
          </Button>
        </div>
      </PageHeader>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Assigned to me" value={stats.total} icon={ListTodo} />
        <StatCard label="Pending" value={stats.pending} icon={Hourglass} />
        <StatCard
          label="Overdue"
          value={stats.overdue}
          icon={AlertTriangle}
          tone={stats.overdue > 0 ? 'destructive' : 'default'}
        />
        <StatCard
          label="Waiting on help"
          value={stats.blocked}
          icon={TriangleAlert}
          tone={stats.blocked > 0 ? 'accent' : 'default'}
        />
      </div>

      <SelfTaskDialog open={addOpen} onOpenChange={setAddOpen} />

      {tasks.length === 0 ? (
        <EmptyState
          icon={ListTodo}
          title="Nothing assigned to you yet"
          description="When a partner allocates a job to you it will appear here. You can also add work you have picked up yourself."
          action={
            <Button onClick={() => setAddOpen(true)}>
              <Plus className="size-4" />
              Add Task
            </Button>
          }
        />
      ) : view === 'table' ? (
        <Card className="py-0">
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Task</TableHead>
                    <TableHead>Client</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Due</TableHead>
                    <TableHead className="text-right">In stage</TableHead>
                    <TableHead>Stage</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tasks.map((task) => (
                    <TableRow
                      key={task.id}
                      className={cn(task.is_overdue && 'border-destructive border-l-2')}
                    >
                      <TableCell className="max-w-xs font-medium">
                        <Link to={`/tasks/${task.id}`} className="hover:underline">
                          {task.title}
                        </Link>
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {task.client_name ?? 'Internal'}
                      </TableCell>
                      <TableCell>
                        <CategoryBadge category={task.category} />
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        <span className="flex items-center gap-2">
                          {formatDate(task.due_date)}
                          {task.is_overdue ? (
                            <OverdueBadge days={task.days_to_due} />
                          ) : !task.stage_is_terminal ? (
                            <UpcomingBadge days={task.days_to_due} />
                          ) : null}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <AgeingBadge
                          days={task.days_in_stage}
                          terminal={task.stage_is_terminal}
                        />
                      </TableCell>
                      <TableCell>
                        <StagePicker
                          taskId={task.id}
                          stageId={task.stage_id}
                          currentNote={task.help_note}
                          isCompliance={task.is_compliance}
                          taskTitle={task.title}
                          size="sm"
                          className="w-48"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {openStages.map((stage) => {
            const items = byStage.get(stage.id) ?? []
            if (!items.length) return null
            return (
              <StageSection key={stage.id} stage={stage} items={items} />
            )
          })}

          {doneStages.some((s) => (byStage.get(s.id) ?? []).length) ? (
            <Collapsible open={doneOpen} onOpenChange={setDoneOpen}>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="text-success">
                  <ChevronDown
                    className={cn('size-4 transition-transform', doneOpen && 'rotate-180')}
                  />
                  Completed
                  <span className="text-muted-foreground ml-1 tabular-nums">
                    {doneStages.reduce((sum, s) => sum + (byStage.get(s.id) ?? []).length, 0)}
                  </span>
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 space-y-6">
                {doneStages.map((stage) => {
                  const items = byStage.get(stage.id) ?? []
                  if (!items.length) return null
                  return <StageSection key={stage.id} stage={stage} items={items} />
                })}
              </CollapsibleContent>
            </Collapsible>
          ) : null}
        </div>
      )}
    </div>
  )
}

function StageSection({ stage, items }: { stage: Stage; items: TaskEnriched[] }) {
  return (
    <section className="space-y-2">
      <h2 className="flex items-center gap-2 text-sm font-semibold">
        <span
          className="size-2 rounded-full"
          style={{ backgroundColor: stageVar(stage.code) }}
        />
        <span style={{ color: stageVar(stage.code) }}>{stage.name}</span>
        <span className="text-muted-foreground font-normal tabular-nums">{items.length}</span>
      </h2>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {items.map((task) => (
          <TaskCard key={task.id} task={task} />
        ))}
      </div>
    </section>
  )
}

function TaskCard({ task }: { task: TaskEnriched }) {
  const hint = relativeDueHint(task.due_date)
  const stuck = !task.stage_is_terminal && task.days_in_stage >= AGEING_ALERT

  return (
    <Card
      className={cn(
        'gap-0 py-4 transition-shadow hover:shadow-md',
        task.is_overdue && 'border-l-destructive border-l-2',
      )}
    >
      <CardContent className="space-y-3 px-4">
        <div className="space-y-1">
          <Link to={`/tasks/${task.id}`} className="line-clamp-2 font-medium hover:underline">
            {task.title}
          </Link>
          <p className="text-muted-foreground text-sm">{task.client_name ?? 'Internal'}</p>
        </div>

        {task.help_note ? (
          <p
            className="line-clamp-2 rounded px-2 py-1 text-xs"
            style={{
              backgroundColor: `color-mix(in srgb, ${stageVar(STAGE_NEED_HELP)} 12%, transparent)`,
            }}
          >
            {task.help_note}
          </p>
        ) : null}

        <div className="flex flex-wrap items-center gap-1.5">
          <CategoryBadge category={task.category} />
          <PriorityBadge priority={task.priority} />
          {task.period ? (
            <span className="text-muted-foreground text-xs">{task.period}</span>
          ) : null}
        </div>

        <div className="flex items-center justify-between gap-2 text-sm">
          <div className="min-w-0">
            <p className="whitespace-nowrap">{formatDate(task.due_date)}</p>
            {hint ? (
              <p
                className={cn(
                  'text-xs',
                  task.is_overdue ? 'text-destructive font-medium' : 'text-muted-foreground',
                )}
              >
                {hint}
              </p>
            ) : (
              <p className="text-muted-foreground text-xs">no due date</p>
            )}
          </div>
          {stuck ? (
            <span className="text-destructive flex items-center gap-1 text-xs font-medium">
              <Hourglass className="size-3" />
              {task.days_in_stage}d here
            </span>
          ) : null}
        </div>

        <StagePicker
          taskId={task.id}
          stageId={task.stage_id}
          currentNote={task.help_note}
          isCompliance={task.is_compliance}
          taskTitle={task.title}
          size="sm"
          className="w-full"
        />
      </CardContent>
    </Card>
  )
}
