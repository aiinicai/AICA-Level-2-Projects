import { useState } from 'react'
import { Loader2, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Field } from '@/components/common'
import { FilingDialog } from '@/components/filing-dialog'
import { useMoveStage, useStages } from '@/hooks/use-app-data'
import { STAGE_NEED_HELP, stageVar } from '@/lib/constants'
import type { Stage } from '@/types/db'

/**
 * Stage dropdown that intercepts a move into "Need Help" and insists on a
 * sentence explaining the blocker. Without that, stage 03 is just a colour and
 * the partner has to chase every one of them by phone.
 */
export function StagePicker({
  taskId,
  stageId,
  currentNote,
  isCompliance = false,
  taskTitle = '',
  size = 'default',
  className,
}: {
  taskId: string
  stageId: string
  currentNote?: string | null
  /** Compliance tasks capture a filing date + link on completion. */
  isCompliance?: boolean
  taskTitle?: string
  size?: 'sm' | 'default'
  className?: string
}) {
  const { stages } = useStages()
  const move = useMoveStage()
  const [pending, setPending] = useState<Stage | null>(null)
  const [note, setNote] = useState('')
  const [noteError, setNoteError] = useState<string | null>(null)
  const [filingFor, setFilingFor] = useState<Stage | null>(null)

  function handleChange(nextId: string) {
    if (nextId === stageId) return
    const stage = stages.find((s) => s.id === nextId)
    if (!stage) return

    if (stage.code === STAGE_NEED_HELP) {
      setNote(currentNote ?? '')
      setNoteError(null)
      setPending(stage)
      return
    }
    if (isCompliance && stage.is_terminal && !stage.is_dropped) {
      setFilingFor(stage)
      return
    }
    move.mutate({ id: taskId, stageId: stage.id, stageCode: stage.code })
  }

  function submitNote() {
    if (!pending) return
    if (note.trim().length < 5) {
      setNoteError('Describe what you are stuck on, in a sentence.')
      return
    }
    move.mutate(
      { id: taskId, stageId: pending.id, stageCode: pending.code, note },
      { onSuccess: () => setPending(null) },
    )
  }

  return (
    <>
      <Select value={stageId} onValueChange={handleChange}>
        <SelectTrigger size={size} className={className ?? 'w-56'}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {stages.map((stage) => (
            <SelectItem key={stage.id} value={stage.id}>
              <span className="flex items-center gap-2">
                <span
                  className="size-2 shrink-0 rounded-full"
                  style={{ backgroundColor: stageVar(stage.code) }}
                />
                {stage.name}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <FilingDialog
        open={Boolean(filingFor)}
        onOpenChange={(open) => !open && setFilingFor(null)}
        taskTitle={taskTitle}
        pending={move.isPending}
        onConfirm={(filingDate, filingLink) => {
          if (!filingFor) return
          move.mutate(
            {
              id: taskId,
              stageId: filingFor.id,
              stageCode: filingFor.code,
              filingDate,
              filingLink,
            },
            { onSuccess: () => setFilingFor(null) },
          )
        }}
      />

      <Dialog open={Boolean(pending)} onOpenChange={(open) => !open && setPending(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <TriangleAlert className="size-4" style={{ color: stageVar(STAGE_NEED_HELP) }} />
              What do you need help with?
            </DialogTitle>
            <DialogDescription>
              This goes straight to the partner's Need Help queue, with the number of days it has
              been waiting.
            </DialogDescription>
          </DialogHeader>

          <Field label="The blocker" htmlFor="help-note" error={noteError} required>
            <Textarea
              id="help-note"
              rows={4}
              autoFocus
              placeholder="e.g. Client has not shared the bank statement for March despite two reminders."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </Field>

          <DialogFooter>
            <Button variant="outline" onClick={() => setPending(null)}>
              Cancel
            </Button>
            <Button onClick={submitNote} disabled={move.isPending}>
              {move.isPending ? <Loader2 className="size-4 animate-spin" /> : null}
              Flag for help
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
