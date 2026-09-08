import * as Popover from '@radix-ui/react-popover'
import { useState, type FormEvent } from 'react'

/** The single, overwritable Admin's Remark field — visible to everyone who
 * can see the task, but only an Admin can set/change it (also enforced by
 * the enforce_task_update_rules trigger). Distinct from RemarkCell, which
 * appends to the timestamped task_comments thread instead of overwriting. */
export function AdminRemarkCell({
  value,
  isAdmin,
  onSave,
}: {
  value: string | null
  isAdmin: boolean
  onSave: (body: string) => Promise<void>
}) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)

  const startEditing = () => {
    setDraft(value ?? '')
    setOpen(true)
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await onSave(draft.trim())
      setOpen(false)
    } finally {
      setSaving(false)
    }
  }

  if (!isAdmin) {
    return <span className="block break-words text-ink-soft">{value || '—'}</span>
  }

  return (
    <Popover.Root
      open={open}
      onOpenChange={(next) => {
        if (next) startEditing()
        else setOpen(false)
      }}
    >
      <Popover.Trigger asChild>
        <button type="button" className="block w-full break-words text-left text-ink-soft hover:text-bark focus:outline-none">
          {value || <span className="italic text-ink-soft/60">Add admin remark…</span>}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={4}
          collisionPadding={8}
          className="z-50 w-72 rounded-md border border-line bg-paper-raised shadow-lg p-3"
        >
          <form onSubmit={submit} className="flex flex-col gap-2">
            <textarea
              autoFocus
              rows={3}
              placeholder="Admin's remark…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="w-full resize-none rounded-md border border-line bg-paper px-3 py-1.5 text-sm text-ink transition-colors focus:outline-none focus:border-bark focus:ring-2 focus:ring-bark/15"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="text-xs font-medium px-3 py-1.5 rounded-md text-ink-soft hover:text-ink transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="text-xs font-medium px-3 py-1.5 rounded-md bg-bark-gradient text-white transition-colors disabled:opacity-50"
              >
                Save
              </button>
            </div>
          </form>
          <Popover.Arrow className="fill-paper-raised" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
