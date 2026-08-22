import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Download, Loader2, Printer } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  AgeingBadge,
  CategoryBadge,
  EmptyState,
  OverdueBadge,
  PageHeader,
  StageBadge,
} from '@/components/common'
import { Combobox } from '@/components/combobox'
import { useClients, useStages, useTasks } from '@/hooks/use-app-data'
import { friendlyError } from '@/lib/supabase'
import { FIRM_NAME, STAGE_DROPPED, stageVar } from '@/lib/constants'
import { downloadCSV, formatDate, todayISO } from '@/lib/utils'

/**
 * One page per client, listing every job and where it has got to. Designed to
 * be printed or emailed to the client as-is, so it carries no internal
 * commentary — blockers stay on the Need Help queue.
 */
export default function ClientStatusPage() {
  const { clientId } = useParams<{ clientId: string }>()
  const navigate = useNavigate()
  const clientsQuery = useClients()
  const tasksQuery = useTasks()
  const { stages } = useStages()
  const [showDropped, setShowDropped] = useState(false)
  const [showCompleted, setShowCompleted] = useState(true)

  const client = useMemo(
    () => (clientsQuery.data ?? []).find((c) => c.id === clientId) ?? null,
    [clientsQuery.data, clientId],
  )

  const clientOptions = useMemo(
    () =>
      (clientsQuery.data ?? []).map((c) => ({
        value: c.id,
        label: c.name,
        hint: c.client_code ?? undefined,
      })),
    [clientsQuery.data],
  )

  const tasks = useMemo(() => {
    if (!clientId) return []
    return (tasksQuery.data ?? [])
      .filter((task) => task.client_id === clientId)
      .filter((task) => (showDropped ? true : !task.stage_is_dropped))
      .filter((task) => (showCompleted ? true : !task.stage_is_terminal))
      .sort(
        (a, b) =>
          a.stage_sort - b.stage_sort ||
          (a.due_date ?? '9999').localeCompare(b.due_date ?? '9999'),
      )
  }, [tasksQuery.data, clientId, showDropped, showCompleted])

  const counts = useMemo(() => {
    const map = new Map<string, number>()
    for (const task of tasks) map.set(task.stage_code, (map.get(task.stage_code) ?? 0) + 1)
    return map
  }, [tasks])

  const visibleStages = useMemo(
    () => stages.filter((s) => showDropped || s.code !== STAGE_DROPPED),
    [stages, showDropped],
  )

  function exportCSV() {
    if (!client) return
    const header = [
      'Task',
      'Category',
      'Assigned To',
      'Stage',
      'Days in Stage',
      'Financial Year',
      'Period',
      'Due Date',
      'Overdue',
    ]
    const rows = tasks.map((task) => [
      task.title,
      task.category,
      task.assignee_name,
      `${task.stage_code} ${task.stage_name}`,
      task.stage_is_terminal ? '' : task.days_in_stage,
      task.financial_year ?? '',
      task.period ?? '',
      task.due_date ?? '',
      task.is_overdue ? 'Yes' : 'No',
    ])
    downloadCSV(`status-${client.name.replace(/[^\w-]+/g, '-')}-${todayISO()}.csv`, [
      header,
      ...rows,
    ])
  }

  if (clientsQuery.isLoading || tasksQuery.isLoading) {
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
      <div className="no-print space-y-4">
        <PageHeader
          title="Client Status Sheet"
          description="Every job for one client and where it has got to. Printable, or export to CSV."
        >
          <Button variant="outline" onClick={exportCSV} disabled={!client || !tasks.length}>
            <Download className="size-4" />
            CSV
          </Button>
          <Button onClick={() => window.print()} disabled={!client}>
            <Printer className="size-4" />
            Print
          </Button>
        </PageHeader>

        <Card className="py-0">
          <CardContent className="grid gap-3 p-4 sm:grid-cols-3">
            <div className="sm:col-span-1">
              <Combobox
                options={clientOptions}
                value={clientId ?? null}
                onChange={(value) => navigate(value ? `/client-status/${value}` : '/client-status')}
                placeholder="Choose a client…"
                searchPlaceholder="Search clients…"
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <Switch checked={showCompleted} onCheckedChange={setShowCompleted} />
              Include completed
            </label>
            <label className="flex items-center gap-2 text-sm">
              <Switch checked={showDropped} onCheckedChange={setShowDropped} />
              Include dropped
            </label>
          </CardContent>
        </Card>
      </div>

      {!client ? (
        <EmptyState
          title="Pick a client"
          description="Choose a client above to see every job allocated for them and its current stage."
        />
      ) : (
        <div className="print-area space-y-4">
          {/* Header — this is what prints at the top of the sheet */}
          <div className="flex flex-wrap items-start justify-between gap-4 border-b pb-4">
            <div>
              <p className="text-muted-foreground text-xs tracking-wide uppercase">{FIRM_NAME}</p>
              <h2 className="mt-0.5 text-xl font-semibold">{client.name}</h2>
              <p className="text-muted-foreground mt-1 text-sm">
                {[
                  client.client_code,
                  client.client_type,
                  client.pan ? `PAN ${client.pan}` : null,
                  client.gstin ? `GSTIN ${client.gstin}` : null,
                ]
                  .filter(Boolean)
                  .join('  ·  ')}
              </p>
            </div>
            <div className="text-right">
              <p className="text-muted-foreground text-xs">Status as at</p>
              <p className="font-medium">{formatDate(todayISO())}</p>
            </div>
          </div>

          {/* Stage summary */}
          <div className="flex flex-wrap gap-2">
            {visibleStages.map((stage) => (
              <span
                key={stage.id}
                className="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm"
                style={{ borderColor: stageVar(stage.code) }}
              >
                <span
                  className="size-2 rounded-full"
                  style={{ backgroundColor: stageVar(stage.code) }}
                />
                {stage.name}
                <span className="font-semibold tabular-nums" style={{ color: stageVar(stage.code) }}>
                  {counts.get(stage.code) ?? 0}
                </span>
              </span>
            ))}
          </div>

          {tasks.length === 0 ? (
            <EmptyState
              title="No jobs for this client"
              description="Nothing has been allocated against them yet."
            />
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Task</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Handled by</TableHead>
                    <TableHead>Stage</TableHead>
                    <TableHead className="text-right">In stage</TableHead>
                    <TableHead>Period</TableHead>
                    <TableHead>Due</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tasks.map((task) => (
                    <TableRow key={task.id}>
                      <TableCell className="font-medium">
                        <Link to={`/tasks/${task.id}`} className="hover:underline">
                          {task.title}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <CategoryBadge category={task.category} />
                      </TableCell>
                      <TableCell className="whitespace-nowrap">{task.assignee_name}</TableCell>
                      <TableCell>
                        <StageBadge code={task.stage_code} name={task.stage_name} showCode />
                      </TableCell>
                      <TableCell className="text-right">
                        <AgeingBadge
                          days={task.days_in_stage}
                          terminal={task.stage_is_terminal}
                        />
                      </TableCell>
                      <TableCell className="text-muted-foreground whitespace-nowrap text-sm">
                        {[task.period, task.financial_year].filter(Boolean).join(' · ') || '—'}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        <span className="flex items-center gap-2">
                          {formatDate(task.due_date)}
                          {task.is_overdue ? <OverdueBadge days={task.days_to_due} /> : null}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          <p className="text-muted-foreground pt-2 text-xs">
            Generated from {FIRM_NAME} practice management on {formatDate(todayISO())}.
            {client.relationship_manager ? null : ' No relationship manager is set for this client.'}
          </p>
        </div>
      )}
    </div>
  )
}
