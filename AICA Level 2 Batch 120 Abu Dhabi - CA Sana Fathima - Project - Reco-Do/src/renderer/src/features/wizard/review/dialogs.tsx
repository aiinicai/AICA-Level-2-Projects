import { useEffect, useId, useState } from 'react'
import { AlertCircle, CheckCircle2, Lock } from 'lucide-react'
import type { EngineLine } from '@shared/contracts'
import { formatAmount, formatDate } from '@shared/format'
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Field,
  KeyValue,
  Textarea
} from '@/components/ui'
import { cn } from '@/lib/cn'
import { rowLabel } from './model'
import { Money } from './Money'

export function NoteDialog({
  open,
  initial,
  onOpenChange,
  onSave
}: {
  open: boolean
  initial: string
  onOpenChange: (o: boolean) => void
  onSave: (note: string) => Promise<void>
}): React.JSX.Element {
  const [note, setNote] = useState(initial)
  const [saving, setSaving] = useState(false)
  const id = useId()
  useEffect(() => {
    if (open) setNote(initial)
  }, [open, initial])
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent width={480}>
        <form
          onSubmit={async (e) => {
            e.preventDefault()
            if (!note.trim()) return
            setSaving(true)
            try {
              await onSave(note.trim())
            } finally {
              setSaving(false)
            }
          }}
        >
          <DialogHeader>
            <DialogTitle>{initial ? 'Edit note' : 'Add note'}</DialogTitle>
            <DialogDescription>The note is saved with the pair, shown in the export and recorded in the audit trail.</DialogDescription>
          </DialogHeader>
          <DialogBody>
            <Field label="Note" htmlFor={id}>
              <Textarea id={id} autoFocus value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Confirmed with treasury; bank charge to be posted" />
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!note.trim()} loading={saving}>
              Save note
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function LineList({ title, lines, hasAmount }: { title: string; lines: EngineLine[]; hasAmount: boolean }): React.JSX.Element {
  return (
    <div className="min-w-0 flex-1">
      <div className="mb-1 truncate text-[12.5px] font-semibold text-muted" title={title}>
        {title} ({lines.length})
      </div>
      <ul className="max-h-40 overflow-y-auto rounded-lg border border-line text-[12.5px]">
        {lines.map((l) => (
          <li key={l.id} className="flex justify-between gap-2 border-b border-line px-2.5 py-1 last:border-b-0">
            <span className="text-muted">
              {rowLabel(l.id)}
              {l.date ? ` · ${formatDate(l.date)}` : ''}
            </span>
            {hasAmount && (
              <span className="num">
                <Money n={l.amount} />
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Confirms a manual match; a reason is required when the totals differ. */
export function ManualMatchDialog({
  open,
  onOpenChange,
  linesA,
  linesB,
  nameA,
  nameB,
  hasAmount,
  totalA,
  totalB,
  currency,
  onConfirm
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  linesA: EngineLine[]
  linesB: EngineLine[]
  nameA: string
  nameB: string
  hasAmount: boolean
  /** Comparable totals (side A's sign convention). */
  totalA: number
  totalB: number
  currency: string
  onConfirm: (reason: string) => Promise<void>
}): React.JSX.Element {
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const id = useId()
  useEffect(() => {
    if (open) setReason('')
  }, [open])
  const diff = Math.round((totalA - totalB) * 100) / 100
  const differs = hasAmount && Math.abs(diff) >= 0.005
  const ok = !differs || reason.trim().length > 0
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent width={620}>
        <form
          onSubmit={async (e) => {
            e.preventDefault()
            if (!ok) return
            setSaving(true)
            try {
              await onConfirm(reason.trim())
            } finally {
              setSaving(false)
            }
          }}
        >
          <DialogHeader>
            <DialogTitle>Match selected lines</DialogTitle>
            <DialogDescription>
              {linesA.length} line{linesA.length === 1 ? '' : 's'} from {nameA} with {linesB.length} line{linesB.length === 1 ? '' : 's'} from {nameB}. The pair goes to Matched and the decision is recorded in the audit trail.
            </DialogDescription>
          </DialogHeader>
          <DialogBody className="flex flex-col gap-4">
            <div className="flex gap-3">
              <LineList title={nameA} lines={linesA} hasAmount={hasAmount} />
              <LineList title={nameB} lines={linesB} hasAmount={hasAmount} />
            </div>
            {hasAmount && (
              <KeyValue
                dense
                items={[
                  { label: `Total ${nameA}`, value: `${currency} ${formatAmount(totalA)}`, numeric: true },
                  { label: `Total ${nameB} (in ${nameA}'s sign)`, value: `${currency} ${formatAmount(totalB)}`, numeric: true },
                  { label: 'Difference', value: `${currency} ${formatAmount(diff)}`, numeric: true, total: true, tone: differs ? 'unmatched' : 'matched' }
                ]}
              />
            )}
            <div className={cn('flex items-center gap-2 text-[13px] font-semibold', differs ? 'text-unmatched' : 'text-matched')}>
              {differs ? <AlertCircle size={15} /> : <CheckCircle2 size={15} />}
              {differs ? 'The totals do not agree. Enter a reason to match them anyway.' : hasAmount ? 'The totals agree.' : 'No amount key: the lines are matched on your judgement.'}
            </div>
            <Field label={differs ? 'Reason (required)' : 'Reason (optional)'} htmlFor={id}>
              <Textarea id={id} value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Bank charge of 25.00 deducted by the correspondent bank" />
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!ok} loading={saving}>
              Match
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

/** Sign-off: lists what still blocks it, or confirms and locks the reconciliation. */
export function FinaliseDialog({
  open,
  onOpenChange,
  reasons,
  preparer,
  onConfirm
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  reasons: string[]
  preparer: string
  onConfirm: () => Promise<void>
}): React.JSX.Element {
  const [saving, setSaving] = useState(false)
  const blocked = reasons.length > 0
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent width={500}>
        <DialogHeader>
          <DialogTitle>{blocked ? 'Not ready to sign off' : 'Finalise and sign off?'}</DialogTitle>
          <DialogDescription>
            {blocked
              ? 'The Doubtful and AI Suggested tabs must be empty (every item accepted or rejected) before the reconciliation can be finalised.'
              : `Signed off by ${preparer} on ${formatDate(new Date())}. Matched items are locked and no further changes can be made. Exports stay available.`}
          </DialogDescription>
        </DialogHeader>
        <DialogBody>
          {blocked ? (
            <ul className="list-disc space-y-1 pl-5 text-[13.5px] text-ink">
              {reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          ) : (
            <div className="flex items-center gap-2 rounded-lg bg-[#F4F6F9] px-3 py-2.5 text-[13px] text-muted">
              <Lock size={15} /> This cannot be undone.
            </div>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            {blocked ? 'Close' : 'Cancel'}
          </Button>
          {!blocked && (
            <Button
              variant="teal"
              loading={saving}
              onClick={async () => {
                setSaving(true)
                try {
                  await onConfirm()
                } finally {
                  setSaving(false)
                }
              }}
            >
              Finalise &amp; sign off
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
