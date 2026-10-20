import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { History, Search, Trash2 } from 'lucide-react'
import { getModule, MODULES, type ModuleId } from '@shared/modules'
import { formatDate } from '@shared/format'
import { Badge, Button, Card, DataTable, EmptyState, Input, Select, Spinner, TechnicalDetails, Tooltip, useConfirm, useToast, type BadgeTone, type DataColumn } from '@/components/ui'
import { formatWhen, loadReconItems, reconLink, STATUS_LABEL, type ReconListItem, type ReconStatus } from '@/features/wizard/inProgress'
import { deleteRecon } from '@/features/wizard/openRecons'
import { errorMessage, useAsync } from '@/lib/useAsync'

const STATUS_TONE: Record<ReconStatus, BadgeTone> = { draft: 'neutral', review: 'doubtful', finalised: 'matched' }

function ModuleChip({ moduleId }: { moduleId: ModuleId }): React.JSX.Element {
  const m = getModule(moduleId)
  return (
    <span className="flex min-w-0 items-center gap-2">
      <span
        className="grid h-6 w-6 shrink-0 place-items-center rounded-md text-[10px] font-extrabold text-white"
        style={{ background: m?.color ?? '#5B6676' }}
      >
        {m?.code ?? '?'}
      </span>
      <span className="truncate">{m?.name.replace(' Reconciliation', '').replace(' Recon', '') ?? 'Unknown'}</span>
    </span>
  )
}

const count = (n: number | undefined): string => (n ?? 0).toLocaleString('en-US')

export function HistoryPage(): React.JSX.Element {
  const navigate = useNavigate()
  const toast = useToast()
  const confirm = useConfirm()
  const { data, error, details, loading, setData } = useAsync(loadReconItems, [], 'Recon history could not be loaded. Please try again.')
  const [query, setQuery] = useState('')
  const [moduleFilter, setModuleFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (data ?? []).filter(
      (r) =>
        (moduleFilter === 'all' || r.moduleId === moduleFilter) &&
        (statusFilter === 'all' || (statusFilter === 'unfinished' ? r.status !== 'finalised' : r.status === statusFilter)) &&
        (!q || `${r.accountLabel} ${r.period} ${r.files} ${r.sides} ${r.preparer ?? ''} ${r.finalised?.by ?? ''}`.toLowerCase().includes(q))
    )
  }, [data, query, moduleFilter, statusFilter])

  const remove = async (r: ReconListItem): Promise<void> => {
    const title = r.accountLabel || 'Untitled'
    const ok = await confirm({
      title: 'Delete this reconciliation?',
      description:
        r.kind === 'draft'
          ? `"${title}" has not been run yet. Its files and settings will be removed from this computer.`
          : `"${title}${r.period ? ` — ${r.period}` : ''}" and its audit trail will be removed from this computer. Exported files are not affected.`,
      confirmLabel: 'Delete',
      tone: 'danger'
    })
    if (!ok) return
    try {
      // Stops any save still queued for it first, so the deleted reconciliation cannot come back.
      await deleteRecon(r.id, r.kind)
      setData((list) => list?.filter((x) => x.id !== r.id))
      toast.success('Reconciliation deleted')
    } catch (err) {
      toast.error('It could not be deleted', errorMessage(err))
    }
  }

  const open = (r: ReconListItem): void => {
    void navigate(reconLink(r))
  }

  const columns: DataColumn<ReconListItem>[] = [
    { id: 'module', header: 'Module', width: 108, cell: (r) => <ModuleChip moduleId={r.moduleId} /> },
    {
      id: 'account',
      header: 'Account / sides',
      minWidth: 160,
      cell: (r) => (
        <span className="min-w-0">
          <span className="block truncate font-semibold">{r.accountLabel || 'Untitled'}</span>
          <span className="block truncate text-[11.5px] text-muted">
            {r.sides}
            {r.stats ? ` · ${count(r.stats.linesA)} / ${count(r.stats.linesB)} lines` : ` · ${r.stage}`}
          </span>
        </span>
      ),
      title: (r) => r.files
    },
    { id: 'period', header: 'Period', width: 86, value: (r) => r.period },
    {
      id: 'matched',
      header: 'Matched',
      width: 80,
      numeric: true,
      cell: (r) => (r.stats ? <span className="text-matched">{count(r.stats.matched)}</span> : <span className="text-muted">—</span>)
    },
    {
      id: 'review',
      header: 'To review',
      width: 92,
      numeric: true,
      cell: (r) => (r.stats ? <span className={r.toReview ? 'text-doubtful' : 'text-muted'}>{count(r.toReview)}</span> : <span className="text-muted">—</span>)
    },
    {
      id: 'unmatched',
      header: 'Unmatched',
      width: 100,
      numeric: true,
      cell: (r) =>
        r.stats ? (
          <span className={r.stats.unmatchedA + r.stats.unmatchedB ? 'text-unmatched' : 'text-muted'}>
            {count(r.stats.unmatchedA)} / {count(r.stats.unmatchedB)}
          </span>
        ) : (
          <span className="text-muted">—</span>
        )
    },
    {
      id: 'status',
      header: 'Status',
      width: 104,
      cell: (r) => {
        const chip = (
          <Badge tone={STATUS_TONE[r.status]} data-testid="status-chip">
            {STATUS_LABEL[r.status]}
          </Badge>
        )
        const tip = r.finalised ? `Signed off by ${r.finalised.by} on ${formatWhen(r.finalised.at)}` : r.stage
        return (
          <Tooltip content={tip}>
            <span tabIndex={0}>{chip}</span>
          </Tooltip>
        )
      }
    },
    {
      id: 'updated',
      header: 'Last saved',
      width: 116,
      cell: (r) => <span className="num text-muted">{formatDate(new Date(r.updatedAt))}</span>,
      title: (r) => formatWhen(r.updatedAt)
    },
    {
      id: 'actions',
      header: <span className="sr-only">Actions</span>,
      width: 96,
      align: 'right',
      cell: (r) => (
        <span className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <Button size="sm" variant="outline" className="h-7 px-2.5" onClick={() => open(r)}>
            Open
          </Button>
          <Tooltip content="Delete">
            <Button size="icon-sm" variant="ghost" aria-label={`Delete ${r.accountLabel || 'Untitled'}`} onClick={() => void remove(r)}>
              <Trash2 size={15} className="text-unmatched" />
            </Button>
          </Tooltip>
        </span>
      )
    }
  ]

  if (loading && !data) {
    return (
      <Card className="grid h-64 place-items-center">
        <Spinner />
      </Card>
    )
  }
  if (error) {
    return (
      <Card>
        <EmptyState title="Recon history could not be loaded" description={error} action={<TechnicalDetails details={details} />} />
      </Card>
    )
  }
  if (!data?.length) {
    return (
      <Card>
        <EmptyState
          icon={<History size={22} />}
          title="No reconciliations yet"
          description="Reconciliations appear here as soon as you read their files, so you can reopen drafts, continue a review, look at the audit trail or export again."
          action={
            <Button asChild>
              <Link to="/">Start a reconciliation</Link>
            </Button>
          }
        />
      </Card>
    )
  }

  const tableHeight = Math.min(620, 44 + Math.max(rows.length, 3) * 52)
  const unfinished = data.filter((r) => r.status !== 'finalised').length

  return (
    <Card className="p-5">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative w-[300px]">
          <Search size={15} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted" />
          <Input
            aria-label="Search history"
            placeholder="Search account, period, file or preparer"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select
          aria-label="Filter by module"
          value={moduleFilter}
          onValueChange={setModuleFilter}
          className="w-[200px]"
          options={[{ value: 'all', label: 'All modules' }, ...MODULES.filter((m) => m.status === 'live').map((m) => ({ value: m.id, label: m.name }))]}
        />
        <Select
          aria-label="Filter by status"
          value={statusFilter}
          onValueChange={setStatusFilter}
          className="w-[170px]"
          options={[
            { value: 'all', label: 'All statuses' },
            { value: 'unfinished', label: `In progress (${unfinished})` },
            { value: 'draft', label: 'Draft' },
            { value: 'review', label: 'In review' },
            { value: 'finalised', label: 'Finalised' }
          ]}
        />
        <span className="ml-auto text-[12.5px] text-muted">
          {rows.length} of {data.length} reconciliation{data.length === 1 ? '' : 's'}
        </span>
      </div>
      <DataTable
        aria-label="Recon history"
        rows={rows}
        columns={columns}
        rowKey={(r) => r.id}
        rowHeight={52}
        height={tableHeight}
        onRowClick={open}
        empty="No reconciliations match your search."
      />
    </Card>
  )
}
