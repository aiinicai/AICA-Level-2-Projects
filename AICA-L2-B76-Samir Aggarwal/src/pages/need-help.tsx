import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, Loader2, MessageSquare, PlayCircle, TriangleAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AgeingBadge,
  CategoryBadge,
  ComplianceBadge,
  EmptyState,
  OverdueBadge,
  PageHeader,
  StatCard,
} from '@/components/common'
import { FilingDialog } from '@/components/filing-dialog'
import { useClients, useMoveStage, useProfiles, useStages, useTasks } from '@/hooks/use-app-data'
import { friendlyError } from '@/lib/supabase'
import {
  AGEING_ALERT,
  AGEING_WARN,
  STAGE_COMPLETED,
  STAGE_IN_PROGRESS,
  STAGE_NEED_HELP,
  stageVar,
} from '@/lib/constants'
import { formatDate, relativeTime } from '@/lib/utils'

/**
 * The point of stage 03. Without this screen "Need Help" is a colour on a
 * board; with it, it is a queue the partner works through, oldest first.
 */
export default function NeedHelpPage() {
  const tasksQuery = useTasks()
  const { byCode, isLoading: stagesLoading } = useStages()
  const profilesQuery = useProfiles()
  const clientsQuery = useClients()
  const move = useMoveStage()

  const [assignee, setAssignee] = useState('all')
  const [client, setClient] = useState('all')
  const [filingFor, setFilingFor] = useState<import('@/types/db').TaskEnriched | null>(null)

  const blocked = useMemo(() => {
    return (tasksQuery.data ?? [])
      .filter((task) => task.stage_code === STAGE_NEED_HELP)
      .filter((task) => (assignee === 'all' ? true : task.assigned_to === assignee))
      .filter((task) => (client === 'all' ? true : task.client_id === client))
      .sort((a, b) => b.days_in_stage - a.days_in_stage)
  }, [tasksQuery.data, assignee, client])

  const stats = useMemo(
    () => ({
      total: blocked.length,
      overdue: blocked.filter((t) => t.is_overdue).length,
      stale: blocked.filter((t) => t.days_in_stage >= AGEING_WARN).length,
      worst: blocked[0]?.days_in_stage ?? 0,
    }),
    [blocked],
  )

  const inProgress = byCode.get(STAGE_IN_PROGRESS)
  const completed = byCode.get(STAGE_COMPLETED)

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
        title="Need Help"
        description="Blocked work, longest waiting first. Unblock it or take it back."
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="Blocked"
          value={stats.total}
          icon={TriangleAlert}
          tone={stats.total ? 'accent' : 'default'}
        />
        <StatCard
          label={`Waiting ${AGEING_WARN}d+`}
          value={stats.stale}
          icon={TriangleAlert}
          tone={stats.stale ? 'destructive' : 'default'}
        />
        <StatCard
          label="Also overdue"
          value={stats.overdue}
          icon={TriangleAlert}
          tone={stats.overdue ? 'destructive' : 'default'}
        />
        <StatCard
          label="Longest wait"
          value={stats.worst ? `${stats.worst}d` : '—'}
          icon={TriangleAlert}
          tone={stats.worst >= AGEING_ALERT ? 'destructive' : 'default'}
        />
      </div>

      <Card className="py-0">
        <CardContent className="grid gap-2 p-3 sm:grid-cols-2">
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
        </CardContent>
      </Card>

      {blocked.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="Nobody is blocked"
          description="When someone flags a task as Need Help, it lands here with what they are stuck on and how long they have been waiting."
        />
      ) : (
        <ul className="space-y-3">
          {blocked.map((task) => (
            <li key={task.id}>
              <Card
                className="gap-0 py-4"
                style={{
                  borderLeftColor: stageVar(STAGE_NEED_HELP),
                  borderLeftWidth: 3,
                }}
              >
                <CardContent className="space-y-3 px-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <Link
                        to={`/tasks/${task.id}`}
                        className="font-medium hover:underline"
                      >
                        {task.title}
                      </Link>
                      <p className="text-muted-foreground mt-0.5 text-sm">
                        {task.client_name ?? 'Internal'} · {task.assignee_name}
                        <span className="text-muted-foreground/70">
                          {' '}
                          ({task.assignee_designation})
                        </span>
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-wrap items-center gap-2">
                      {task.is_compliance ? <ComplianceBadge gstin={task.gstin} /> : null}
                      <CategoryBadge category={task.category} />
                      {task.is_overdue ? <OverdueBadge days={task.days_to_due} /> : null}
                      <Badge
                        variant="outline"
                        className="gap-1"
                        style={{
                          color: stageVar(STAGE_NEED_HELP),
                          borderColor: stageVar(STAGE_NEED_HELP),
                        }}
                      >
                        waiting <AgeingBadge days={task.days_in_stage} />
                      </Badge>
                    </div>
                  </div>

                  {task.help_note ? (
                    <div
                      className="flex gap-2 rounded-md px-3 py-2 text-sm"
                      style={{
                        backgroundColor: `color-mix(in srgb, ${stageVar(STAGE_NEED_HELP)} 10%, transparent)`,
                      }}
                    >
                      <MessageSquare className="mt-0.5 size-3.5 shrink-0 opacity-60" />
                      <p className="whitespace-pre-wrap">{task.help_note}</p>
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-sm italic">
                      No blocker recorded — flagged before notes were required.
                    </p>
                  )}

                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-muted-foreground text-xs">
                      Due {formatDate(task.due_date)} · flagged {relativeTime(task.stage_since)}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {inProgress ? (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={move.isPending}
                          onClick={() =>
                            move.mutate({
                              id: task.id,
                              stageId: inProgress.id,
                              stageCode: inProgress.code,
                            })
                          }
                        >
                          <PlayCircle className="size-3.5" />
                          Unblock
                        </Button>
                      ) : null}
                      {completed ? (
                        <Button
                          size="sm"
                          disabled={move.isPending}
                          onClick={() => {
                            if (task.is_compliance) {
                              setFilingFor(task)
                              return
                            }
                            move.mutate({
                              id: task.id,
                              stageId: completed.id,
                              stageCode: completed.code,
                            })
                          }}
                        >
                          <CheckCircle2 className="size-3.5" />
                          Mark complete
                        </Button>
                      ) : null}
                      <Button size="sm" variant="ghost" asChild>
                        <Link to={`/tasks/${task.id}`}>Open</Link>
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <FilingDialog
        open={Boolean(filingFor)}
        onOpenChange={(open) => !open && setFilingFor(null)}
        taskTitle={filingFor?.title ?? ''}
        pending={move.isPending}
        onConfirm={(filingDate, filingLink) => {
          if (!filingFor || !completed) return
          move.mutate(
            {
              id: filingFor.id,
              stageId: completed.id,
              stageCode: completed.code,
              filingDate,
              filingLink,
            },
            { onSuccess: () => setFilingFor(null) },
          )
        }}
      />
    </div>
  )
}
