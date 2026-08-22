import { useEffect, useState } from 'react'
import { CalendarCheck, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Field } from '@/components/common'
import { todayISO } from '@/lib/utils'

/**
 * Shown when a compliance-tagged task is marked Completed. Captures the
 * statutory filing date (which is rarely the same day the task is closed)
 * and an optional link to wherever the acknowledgment lives.
 */
export function FilingDialog({
  open,
  onOpenChange,
  taskTitle,
  pending,
  onConfirm,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  taskTitle: string
  pending: boolean
  onConfirm: (filingDate: string, filingLink: string | null) => void
}) {
  const [date, setDate] = useState(todayISO())
  const [link, setLink] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setDate(todayISO())
      setLink('')
      setError(null)
    }
  }, [open])

  function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!date) {
      setError('Enter the date the filing was made.')
      return
    }
    onConfirm(date, link.trim() || null)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CalendarCheck className="text-success size-4" />
            Filed — record the details
          </DialogTitle>
          <DialogDescription className="line-clamp-2">{taskTitle}</DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={submit} noValidate>
          <Field
            label="Filing Date"
            htmlFor="filing-date"
            error={error}
            hint="The statutory date, not necessarily today."
            required
          >
            <Input
              id="filing-date"
              type="date"
              max={todayISO()}
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </Field>
          <Field
            label="Acknowledgment Link"
            htmlFor="filing-link"
            hint="Optional — Google Drive, portal ARN, anywhere the proof lives."
          >
            <Input
              id="filing-link"
              type="url"
              placeholder="https://…"
              value={link}
              onChange={(e) => setLink(e.target.value)}
            />
          </Field>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={pending}>
              {pending ? <Loader2 className="size-4 animate-spin" /> : null}
              Mark filed
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
