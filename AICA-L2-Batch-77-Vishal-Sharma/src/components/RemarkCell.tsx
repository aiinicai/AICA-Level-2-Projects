import * as Popover from '@radix-ui/react-popover'
import { useState, type FormEvent } from 'react'

/** Latest remark, shown truncated with a click-to-add popover — lets anyone
 * with remark rights on a task post a new one without opening the task.
 * Remarks are an append-only thread (see Task Detail's Remarks section);
 * this never edits or overwrites the shown remark, only adds the next one. */
export function RemarkCell({
  latestRemark,
  canAdd,
  onAdd,
}: {
  latestRemark: string | null
  canAdd: boolean
  onAdd: (body: string) => Promise<void>
}) {
  const [open, setOpen] = useState(false)
  const [body, setBody] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const trimmed = body.trim()
    if (!trimmed) return
    setSaving(true)
    try {
      await onAdd(trimmed)
      setBody('')
      setOpen(false)
    } finally {
      setSaving(false)
    }
  }

  if (!canAdd) {
    return <span className="block break-words text-ink-soft">{latestRemark ?? '—'}</span>
  }

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          className="block w-full break-words text-left text-ink-soft hover:text-bark focus:outline-none"
        >
          {latestRemark ?? <span className="italic text-ink-soft/60">Add remark…</span>}
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
              placeholder="Add a remark…"
              value={body}
              onChange={(e) => setBody(e.target.value)}
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
                disabled={saving || !body.trim()}
                className="text-xs font-medium px-3 py-1.5 rounded-md bg-bark-gradient text-white transition-colors disabled:opacity-50"
              >
                Post
              </button>
            </div>
          </form>
          <Popover.Arrow className="fill-paper-raised" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
