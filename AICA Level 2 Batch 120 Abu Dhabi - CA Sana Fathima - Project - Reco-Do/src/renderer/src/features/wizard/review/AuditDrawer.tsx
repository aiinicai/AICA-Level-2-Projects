import { useMemo } from 'react'
import { ScrollText } from 'lucide-react'
import type { AuditAction, AuditEntry } from '@shared/contracts'
import { formatDate } from '@shared/format'
import { Badge, Dialog, DialogBody, DialogContent, DialogDescription, DialogHeader, DialogTitle, EmptyState, type BadgeTone } from '@/components/ui'

const ACTION: Record<AuditAction, { label: string; tone: BadgeTone }> = {
  accept: { label: 'Accepted', tone: 'matched' },
  reject: { label: 'Rejected', tone: 'unmatched' },
  'manual-match': { label: 'Manual match', tone: 'info' },
  unmatch: { label: 'Unmatched', tone: 'unmatched' },
  note: { label: 'Note', tone: 'neutral' },
  'approve-suggestion': { label: 'Suggestion approved', tone: 'ai' },
  'reject-suggestion': { label: 'Suggestion rejected', tone: 'neutral' },
  finalise: { label: 'Finalised', tone: 'teal' }
}

function when(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${formatDate(d)} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

/** Right-hand drawer listing every review decision, newest first. */
export function AuditDrawer({ open, onOpenChange, entries }: { open: boolean; onOpenChange: (o: boolean) => void; entries: AuditEntry[] }): React.JSX.Element {
  const list = useMemo(() => [...entries].reverse(), [entries])
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        width={520}
        className="top-0 right-0 left-auto h-full max-h-none translate-x-0 translate-y-0 rounded-none rounded-l-xl data-[state=open]:animate-[fade-in_120ms_ease-out]"
      >
        <DialogHeader>
          <DialogTitle>Audit trail</DialogTitle>
          <DialogDescription>
            {entries.length} decision{entries.length === 1 ? '' : 's'} recorded with user, time, before and after.
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="pb-6">
          {list.length === 0 ? (
            <EmptyState icon={<ScrollText size={22} />} title="No decisions yet" description="Accepting, rejecting, matching, notes, Smart Recon approvals and sign-off are all logged here." />
          ) : (
            <ol className="flex flex-col gap-2.5">
              {list.map((e) => {
                const a = ACTION[e.action]
                return (
                  <li key={e.id} className="rounded-lg border border-line px-3.5 py-2.5 text-[12.5px]">
                    <div className="flex items-center justify-between gap-2">
                      <Badge tone={a.tone} size="sm">
                        {a.label}
                      </Badge>
                      <span className="num text-muted">{when(e.at)}</span>
                    </div>
                    <div className="mt-1 font-semibold text-ink">{e.user}</div>
                    {e.before && (
                      <div className="mt-1 text-muted">
                        <span className="font-semibold text-ink">Before:</span> {e.before}
                      </div>
                    )}
                    {e.after && (
                      <div className="text-muted">
                        <span className="font-semibold text-ink">After:</span> {e.after}
                      </div>
                    )}
                    {e.note && (
                      <div className="mt-1 text-ink">
                        <span className="font-semibold">Note:</span> {e.note}
                      </div>
                    )}
                  </li>
                )
              })}
            </ol>
          )}
        </DialogBody>
      </DialogContent>
    </Dialog>
  )
}
