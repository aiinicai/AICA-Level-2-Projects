import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  GripVertical,
  Loader2,
  MessageSquare,
  MoveRight,
  RotateCcw,
  TriangleAlert,
} from 'lucide-react'
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
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
  UpcomingBadge,
} from '@/components/common'
import { FilingDialog } from '@/components/filing-dialog'
import { useAuth } from '@/components/auth-provider'
import { useClients, useMoveStage, useProfiles, useStages, useTasks } from '@/hooks/use-app-data'
import { friendlyError } from '@/lib/supabase'
import { STAGE_DROPPED, STAGE_NEED_HELP, stageVar } from '@/lib/constants'
import { cn, formatDate, relativeTime } from '@/lib/utils'
import type { Stage, TaskEnriched } from '@/types/db'

export default function BoardPage() {
  const { isAdmin } = useAuth()
  const tasksQuery = useTasks()
  const { stages, isLoading: stagesLoading } = useStages()
  const profilesQuery = useProfiles()
  const clientsQuery = useClients()
  const move = useMoveStage()

  const [client, setClient] = useState('all')
  const [assignee, setAssignee] = useState('all')
  const [category, setCategory] = useState('all')
  const [showDropped, setShowDropped] = useState(false)
  const [dragging, setDragging] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState<string | null>(null)

  // Set when a move lands on Need Help and we need the blocker first.
  const [pendingHelp, setPendingHelp] = useState<{ task: TaskEnriched; stage: Stage } | null>(null)
  const [note, setNote] = useState('')
  const [noteError, setNoteError] = useState<string | null>(null)
  // Compliance task dropped on Completed: capture the filing details first.
  const [pendingFiling, setPendingFiling] = useState<{ task: TaskEnriched; stage: Stage } | null>(
    null,
  )

  const allTasks = tasksQuery.data ?? []

  const categories = useMemo(() => {
    const set = new Set<string>()
    for (const task of allTasks) set.add(task.category)
    return [...set].sort((a, b) => a.localeCompare(b))
  }, [allTasks])

  const visibleStages = useMemo(
    () => stages.filter((s) => showDropped || s.code !== STAGE_DROPPED),
    [stages, showDropped],
  )

  const tasks = useMemo(
    () =>
      allTasks.filter((task) => {
        if (!showDropped && task.stage_is_dropped) return false
        if (client !== 'all' && task.client_id !== client) return false
        if (assignee !== 'all' && task.assigned_to !== assignee) return false
        if (category !== 'all' && task.category !== category) return false
        return true
      }),
    [allTasks, showDropped, client, assignee, category],
  )

  const columns = useMemo(
    () =>
      visibleStages.map((stage) => ({
        stage,
        items: tasks
          .filter((task) => task.stage_id === stage.id)
          .sort((a, b) => {
            if (a.is_overdue !== b.is_overdue) return a.is_overdue ? -1 : 1
            return b.days_in_stage - a.days_in_stage
          }),
      })),
    [visibleStages, tasks],
  )

  const hasFilters = client !== 'all' || assignee !== 'all' || category !== 'all' || showDropped

  function requestMove(task: TaskEnriched, stage: Stage) {
    if (task.stage_id === stage.id) return
    if (stage.code === STAGE_NEED_HELP) {
      setNote(task.help_note ?? '')
      setNoteError(null)
      setPendingHelp({ task, stage })
      return
    }
    if (task.is_compliance && stage.is_terminal && !stage.is_dropped) {
      setPendingFiling({ task, stage })
      return
    }
    move.mutate({ id: task.id, stageId: stage.id, stageCode: stage.code })
  }

  function confirmHelp() {
    if (!pendingHelp) return
    if (note.trim().length < 5) {
      setNoteError('Describe what you are stuck on, in a sentence.')
      return
    }
    move.mutate(
      {
        id: pendingHelp.task.id,
        stageId: pendingHelp.stage.id,
        stageCode: pendingHelp.stage.code,
        note,
      },
      { onSuccess: () => setPendingHelp(null) },
    )
  }

  function handleDrop(stage: Stage) {
    setDragOver(null)
    const id = dragging
    setDragging(null)
    if (!id) return
    const task = tasks.find((t) => t.id === id)
    if (task) requestMove(task, stage)
  }

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
    <div className="space-y-4">
      <PageHeader
        title="Board"
        description={
          isAdmin
            ? 'Drag a card to move it between stages.'
            : 'Your work, and anything you have assigned to others. Drag a card to change stage.'
        }
      >
        {hasFilters ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setClient('all')
              setAssignee('all')
              setCategory('all')
              setShowDropped(false)
            }}
          >
            <RotateCcw className="size-3.5" />
            Reset
          </Button>
        ) : null}
      </PageHeader>

      <Card className="py-0">
        <CardContent className="grid gap-2 p-3 sm:grid-cols-2 lg:grid-cols-4">
          <Select value={assignee} onValueChange={setAssignee}>
            <SelectTrigger size="sm">
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
          <Select value={client} onValueChange={setClient}>
            <SelectTrigger size="sm">
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
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger size="sm">
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
            <Switch checked={showDropped} onCheckedChange={setShowDropped} />
            Show dropped
          </label>
        </CardContent>
      </Card>

      {tasks.length === 0 ? (
        <EmptyState
          title="Nothing on the board"
          description={
            hasFilters ? 'No tasks match these filters.' : 'Allocated work will appear here.'
          }
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-5">
          {columns.map(({ stage, items }) => (
            <section
              key={stage.id}
              onDragOver={(event) => {
                event.preventDefault()
                setDragOver(stage.id)
              }}
              onDragLeave={() => setDragOver((current) => (current === stage.id ? null : current))}
              onDrop={() => handleDrop(stage)}
              className={cn(
                'bg-muted/40 flex min-h-40 flex-col rounded-lg border transition-colors',
                dragOver === stage.id && 'ring-primary bg-muted ring-2',
              )}
            >
              <header
                className="flex items-center gap-2 border-b px-3 py-2"
                style={{ borderTopColor: stageVar(stage.code), borderTopWidth: 3 }}
              >
                <span
                  className="size-2 shrink-0 rounded-full"
                  style={{ backgroundColor: stageVar(stage.code) }}
                />
                <h2 className="truncate text-sm font-semibold">{stage.name}</h2>
                <Badge variant="secondary" className="ml-auto tabular-nums">
                  {items.length}
                </Badge>
              </header>

              <div className="flex flex-1 flex-col gap-2 p-2">
                {items.length === 0 ? (
                  <p className="text-muted-foreground px-2 py-6 text-center text-xs">
                    Drop a card here
                  </p>
                ) : (
                  items.map((task) => (
                    <BoardCard
                      key={task.id}
                      task={task}
                      stages={visibleStages}
                      dragging={dragging === task.id}
                      onDragStart={() => setDragging(task.id)}
                      onDragEnd={() => setDragging(null)}
                      onMove={(target) => requestMove(task, target)}
                    />
                  ))
                )}
              </div>
            </section>
          ))}
        </div>
      )}

      <FilingDialog
        open={Boolean(pendingFiling)}
        onOpenChange={(open) => !open && setPendingFiling(null)}
        taskTitle={pendingFiling?.task.title ?? ''}
        pending={move.isPending}
        onConfirm={(filingDate, filingLink) => {
          if (!pendingFiling) return
          move.mutate(
            {
              id: pendingFiling.task.id,
              stageId: pendingFiling.stage.id,
              stageCode: pendingFiling.stage.code,
              filingDate,
              filingLink,
            },
            { onSuccess: () => setPendingFiling(null) },
          )
        }}
      />

      <Dialog open={Boolean(pendingHelp)} onOpenChange={(open) => !open && setPendingHelp(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <TriangleAlert className="size-4" style={{ color: stageVar(STAGE_NEED_HELP) }} />
              What do you need help with?
            </DialogTitle>
            <DialogDescription className="line-clamp-2">
              {pendingHelp?.task.title}
            </DialogDescription>
          </DialogHeader>
          <Field label="The blocker" htmlFor="board-help-note" error={noteError} required>
            <Textarea
              id="board-help-note"
              rows={4}
              autoFocus
              placeholder="e.g. Client has not shared the bank statement for March despite two reminders."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </Field>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingHelp(null)}>
              Cancel
            </Button>
            <Button onClick={confirmHelp} disabled={move.isPending}>
              {move.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
              Flag for help
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function BoardCard({
  task,
  stages,
  dragging,
  onDragStart,
  onDragEnd,
  onMove,
}: {
  task: TaskEnriched
  stages: Stage[]
  dragging: boolean
  onDragStart: () => void
  onDragEnd: () => void
  onMove: (stage: Stage) => void
}) {
  return (
    <article
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      className={cn(
        'bg-card group cursor-grab rounded-md border p-2.5 shadow-sm transition-shadow hover:shadow-md active:cursor-grabbing',
        dragging && 'opacity-40',
        task.is_overdue && 'border-l-destructive border-l-2',
      )}
    >
      <div className="flex items-start gap-1.5">
        <GripVertical className="text-muted-foreground/40 mt-0.5 size-3.5 shrink-0" />
        <div className="min-w-0 flex-1">
          <Link to={`/tasks/${task.id}`} className="line-clamp-2 text-sm font-medium hover:underline">
            {task.title}
          </Link>
          <p className="text-muted-foreground mt-0.5 truncate text-xs">
            {task.client_name ?? 'Internal'}
          </p>
        </div>

        {/* Touch fallback — dragging does not work on a phone. */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="size-6 shrink-0"
              aria-label="Move to stage"
            >
              <MoveRight className="size-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Move to</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {stages.map((stage) => (
              <DropdownMenuItem
                key={stage.id}
                disabled={stage.id === task.stage_id}
                onSelect={() => onMove(stage)}
              >
                <span
                  className="size-2 rounded-full"
                  style={{ backgroundColor: stageVar(stage.code) }}
                />
                {stage.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {task.help_note ? (
        <p
          className="mt-2 line-clamp-2 rounded px-1.5 py-1 text-xs"
          style={{
            backgroundColor: `color-mix(in srgb, ${stageVar(STAGE_NEED_HELP)} 12%, transparent)`,
          }}
        >
          {task.help_note}
        </p>
      ) : null}

      {task.latest_comment ? (
        <div className="text-muted-foreground mt-2 text-xs">
          <p className="line-clamp-2">
            <MessageSquare className="mr-1 inline size-3 align-[-1px] opacity-60" />
            {task.latest_comment}
          </p>
          {/* Author on its own line so a long comment can never clip it. */}
          <p className="text-muted-foreground/70 mt-0.5 truncate font-medium">
            — {task.latest_comment_by ?? 'Unknown'}, {relativeTime(task.latest_comment_at)}
          </p>
        </div>
      ) : null}

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {task.is_compliance ? <ComplianceBadge gstin={task.gstin} /> : null}
        <CategoryBadge category={task.category} />
        <PriorityBadge priority={task.priority} />
        {task.is_overdue ? (
          <OverdueBadge days={task.days_to_due} />
        ) : !task.stage_is_terminal ? (
          <UpcomingBadge days={task.days_to_due} />
        ) : null}
      </div>

      <div className="text-muted-foreground mt-2 flex items-center justify-between gap-2 text-xs">
        <span className="truncate">{task.assignee_name}</span>
        <span className="flex shrink-0 items-center gap-2">
          {task.due_date ? <span>{formatDate(task.due_date)}</span> : null}
          <AgeingBadge days={task.days_in_stage} terminal={task.stage_is_terminal} />
        </span>
      </div>
    </article>
  )
}
