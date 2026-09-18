import { useState } from 'react'
import type { TaskRevision } from '../types/database'

/** One revision request card: shown read-only once decided, or with the
 * approve/reject decision controls (impacts-performance flag + note) while
 * pending. Shared by Task Detail's own list and the admin-wide Revision
 * Requests queue — the decision rule ("impacts_performance must be set to
 * approve") is enforced server-side either way. */
export function RevisionRow({
  revision,
  canDecide,
  onDecide,
  profileName,
}: {
  revision: TaskRevision
  canDecide: boolean
  onDecide: (id: string, decision: 'approved' | 'rejected', impacts: boolean | null, note: string) => void
  profileName: (id: string) => string
}) {
  const [impacts, setImpacts] = useState(true)
  const [note, setNote] = useState('')

  const toneClass =
    revision.status === 'approved'
      ? 'border-moss/40 bg-moss-bg'
      : revision.status === 'rejected'
        ? 'border-rust/40 bg-rust-bg'
        : 'border-line bg-paper'

  return (
    <div className={`rounded-md border px-3 py-2.5 text-sm ${toneClass}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-ink">
          <strong>{profileName(revision.requested_by)}</strong> proposed <strong>{revision.proposed_date}</strong>
        </span>
        <span className="text-xs font-mono uppercase text-ink-soft">{revision.status}</span>
      </div>
      {revision.reason && <p className="text-ink-soft mt-1">{revision.reason}</p>}

      {revision.status === 'pending' && canDecide && (
        <div className="mt-2 flex flex-col gap-2 border-t border-line pt-2">
          <label className="flex items-center gap-2 text-xs text-ink-soft">
            <input
              type="checkbox"
              checked={impacts}
              onChange={(e) => setImpacts(e.target.checked)}
              className="h-4 w-4 accent-bark cursor-pointer"
            />
            Impacts performance (uncheck if the delay wasn't their fault)
          </label>
          <input
            type="text"
            placeholder="Decision note (required if rejecting)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="rounded-md border border-line bg-paper px-2 py-1 text-xs text-ink transition-colors focus:outline-none focus:border-bark focus:ring-2 focus:ring-bark/15"
          />
          <div className="flex gap-2">
            <button
              onClick={() => onDecide(revision.id, 'approved', impacts, note)}
              className="text-xs font-medium px-3 py-1 rounded-md bg-moss text-white hover:opacity-90"
            >
              Approve
            </button>
            <button
              onClick={() => onDecide(revision.id, 'rejected', null, note)}
              className="text-xs font-medium px-3 py-1 rounded-md border border-rust text-rust hover:bg-rust-bg"
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {revision.status !== 'pending' && (
        <p className="text-xs text-ink-soft mt-1">
          Decided by {profileName(revision.decided_by!)}
          {revision.decision_note ? ` — ${revision.decision_note}` : ''}
        </p>
      )}
    </div>
  )
}
