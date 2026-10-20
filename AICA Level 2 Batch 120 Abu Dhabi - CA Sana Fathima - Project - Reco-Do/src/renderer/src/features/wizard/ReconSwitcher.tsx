// "In progress" menu and "New reconciliation" button beside the wizard title: several reconciliations per module
// can be open, and the user switches between them without losing any.

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Popover } from 'radix-ui'
import { ChevronDown, Layers, Plus, Trash2 } from 'lucide-react'
import { Badge, Button, Spinner, Tooltip, useConfirm, useToast } from '@/components/ui'
import { errorMessage } from '@/lib/useAsync'
import { formatWhen, itemFromState, loadInProgress, STATUS_LABEL, withCurrent, type ReconListItem } from './inProgress'
import { deleteRecon } from './openRecons'
import { useReconSlot, useWizard } from './WizardContext'

function ItemRow({
  item,
  onScreen,
  onOpen,
  onDelete
}: {
  item: ReconListItem
  onScreen: boolean
  onOpen: () => void
  onDelete: () => void
}): React.JSX.Element {
  const title = item.accountLabel.trim() || 'Untitled reconciliation'
  return (
    <li className="flex items-start gap-3 rounded-lg px-2.5 py-2 hover:bg-[#F7F9FB]" data-testid="in-progress-item" data-recon-id={item.id}>
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-[13.5px] font-semibold" title={title}>
            {title}
          </span>
          <Badge tone={item.status === 'draft' ? 'neutral' : 'doubtful'} size="sm">
            {STATUS_LABEL[item.status]}
          </Badge>
        </div>
        <div className="truncate text-[12.5px] text-muted" title={item.files}>
          {[item.period, item.stage].filter(Boolean).join(' · ')}
        </div>
        <div className="text-[11.5px] text-muted">Last updated {formatWhen(item.updatedAt)}</div>
      </div>
      <div className="flex shrink-0 items-center gap-1 pt-0.5">
        {onScreen ? (
          <span className="px-2 text-[12px] font-semibold text-matched">On screen</span>
        ) : (
          <Button size="sm" variant="outline" className="h-7 px-2.5" onClick={onOpen} data-testid="in-progress-open">
            Open
          </Button>
        )}
        <Tooltip content="Delete">
          <Button size="icon-sm" variant="ghost" aria-label={`Delete ${title}`} onClick={onDelete}>
            <Trash2 size={15} className="text-unmatched" />
          </Button>
        </Tooltip>
      </div>
    </li>
  )
}

export function ReconSwitcher(): React.JSX.Element {
  const { state, module } = useWizard()
  const { reconId, menuOpen, setMenuOpen, newRecon, openRecon } = useReconSlot()
  const confirm = useConfirm()
  const toast = useToast()
  const [stored, setStored] = useState<ReconListItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      setStored(await loadInProgress(module.id))
      setError(null)
    } catch (err) {
      setError(errorMessage(err, 'The list could not be loaded.'))
    }
  }, [module.id])

  // Fresh list when the menu opens and whenever another reconciliation is put on screen.
  useEffect(() => {
    void reload()
  }, [reload, menuOpen, reconId])

  const current = useMemo(() => itemFromState(state, new Date().toISOString()), [state])
  const items = useMemo(() => (stored ? withCurrent(stored, current, reconId) : null), [stored, current, reconId])

  const remove = async (item: ReconListItem): Promise<void> => {
    setMenuOpen(false)
    const title = item.accountLabel.trim() || 'Untitled reconciliation'
    const ok = await confirm({
      title: 'Delete this reconciliation?',
      description:
        item.kind === 'draft'
          ? `"${title}" has not been run yet. Its files and settings will be removed from this computer.`
          : `"${title}${item.period ? ` — ${item.period}` : ''}", its results and audit trail will be removed from this computer. Exported files are not affected.`,
      confirmLabel: 'Delete',
      tone: 'danger'
    })
    if (!ok) return
    try {
      await deleteRecon(item.id, item.kind)
      if (item.id === reconId) newRecon({ quiet: true })
      setStored((list) => list?.filter((x) => x.id !== item.id) ?? null)
      toast.success('Reconciliation deleted')
    } catch (err) {
      toast.error('It could not be deleted', errorMessage(err))
    }
  }

  const count = items?.length ?? 0

  return (
    <div className="flex items-center gap-2">
      <Popover.Root open={menuOpen} onOpenChange={setMenuOpen}>
        <Popover.Trigger asChild>
          <Button size="sm" variant="secondary" data-testid="in-progress" aria-label={`In progress: ${count} unfinished reconciliation${count === 1 ? '' : 's'}`}>
            <Layers size={14} /> In progress
            <span className="num rounded-full bg-[#EEF1F5] px-1.5 text-[11.5px] font-bold text-ink">{count}</span>
            <ChevronDown size={14} />
          </Button>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            align="start"
            sideOffset={6}
            collisionPadding={8}
            // Focus the list itself rather than its first button, so no tooltip pops up on opening.
            onOpenAutoFocus={(e) => {
              e.preventDefault()
              ;(e.currentTarget as HTMLElement | null)?.focus()
            }}
            tabIndex={-1}
            className="z-50 max-h-[min(520px,var(--radix-popover-content-available-height))] w-[440px] max-w-[calc(100vw-32px)] overflow-y-auto rounded-xl border border-line bg-white p-2 shadow-lg outline-none data-[state=open]:animate-[fade-in_100ms_ease-out]"
            data-testid="in-progress-menu"
          >
            <div className="flex items-baseline justify-between px-2.5 pt-1 pb-2">
              <span className="text-[11.5px] font-bold tracking-[1.2px] text-muted uppercase">In progress · {module.name}</span>
              <Link to="/workspace/history" className="text-[12px] font-semibold text-primary hover:underline" onClick={() => setMenuOpen(false)}>
                Recon History
              </Link>
            </div>
            {error ? (
              <p role="alert" className="px-2.5 py-3 text-[13px] text-unmatched">
                {error}{' '}
                <button type="button" className="font-semibold text-primary hover:underline" onClick={() => void reload()}>
                  Try again
                </button>
              </p>
            ) : !items ? (
              <div className="flex items-center gap-2 px-2.5 py-3 text-[13px] text-muted">
                <Spinner /> Loading…
              </div>
            ) : items.length === 0 ? (
              <p className="px-2.5 py-3 text-[13px] text-muted">
                Nothing in progress yet. Reconciliations you start here are kept until you finalise or delete them, so you can work on several at once.
              </p>
            ) : (
              <ul className="flex flex-col gap-0.5">
                {items.map((item) => (
                  <ItemRow
                    key={item.id}
                    item={item}
                    onScreen={item.id === reconId}
                    onOpen={() => openRecon({ id: item.id, kind: item.kind })}
                    onDelete={() => void remove(item)}
                  />
                ))}
              </ul>
            )}
            <div className="mt-1 border-t border-line px-1 pt-2">
              <Button size="sm" variant="ghost" className="w-full justify-start" onClick={() => newRecon()}>
                <Plus size={14} /> Start a new reconciliation
              </Button>
            </div>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
      <Button size="sm" variant="outline" onClick={() => newRecon()} data-testid="new-recon">
        <Plus size={14} /> New reconciliation
      </Button>
    </div>
  )
}
