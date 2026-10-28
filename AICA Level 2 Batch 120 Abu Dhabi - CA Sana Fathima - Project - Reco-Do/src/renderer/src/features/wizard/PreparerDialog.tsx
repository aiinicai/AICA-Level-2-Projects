import { useEffect, useId, useState } from 'react'
import { Button, Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, Field, Input } from '@/components/ui'

/** Asks for the preparer's name once; it is saved in Settings and used for every review decision. */
export function PreparerDialog({
  open,
  onCancel,
  onSave
}: {
  open: boolean
  onCancel: () => void
  onSave: (name: string) => void | Promise<void>
}): React.JSX.Element {
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)
  const id = useId()
  useEffect(() => {
    if (open) setName('')
  }, [open])
  const trimmed = name.trim()
  const submit = async (): Promise<void> => {
    if (!trimmed) return
    setSaving(true)
    try {
      await onSave(trimmed)
    } finally {
      setSaving(false)
    }
  }
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <DialogContent width={460}>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            void submit()
          }}
        >
          <DialogHeader>
            <DialogTitle>Who is preparing this reconciliation?</DialogTitle>
            <DialogDescription>
              Every decision is recorded in the audit trail with your name and the time. Your name is saved in Settings, so you are asked only once.
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            <Field label="Preparer name" htmlFor={id}>
              <Input id={id} autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Sana Fathima" maxLength={80} />
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" disabled={!trimmed} loading={saving}>
              Save and continue
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
