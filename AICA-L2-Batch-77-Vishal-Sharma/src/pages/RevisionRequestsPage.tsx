import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { decideRevision, fetchPendingRevisions } from '../lib/queries'
import type { PendingRevisionWithTask } from '../types/database'
import { useDirectory } from '../lib/DirectoryProvider'
import { RevisionRow } from '../components/RevisionRow'
import { Loading } from '../components/Loading'

/** Every pending due-date revision request across every task, in one place —
 * so an Admin can work through the queue without opening tasks one by one. */
export function RevisionRequestsPage() {
  const { profileName, clientName } = useDirectory()
  const [revisions, setRevisions] = useState<PendingRevisionWithTask[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = () => fetchPendingRevisions().then(setRevisions)

  useEffect(() => {
    load()
  }, [])

  const handleDecide = async (
    id: string,
    decision: 'approved' | 'rejected',
    impacts: boolean | null,
    note: string,
  ) => {
    setError(null)
    try {
      await decideRevision(id, decision, impacts, note)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Link to="/tasks" className="text-sm text-ink-soft hover:text-ink underline underline-offset-2 w-fit">
        ← Back to Tasks
      </Link>

      <div>
        <h1 className="font-serif text-2xl font-semibold text-ink">Revision Requests</h1>
        <p className="text-sm text-ink-soft mt-1">
          Every pending due-date revision request, across every task, waiting on a decision.
        </p>
      </div>

      {error && <p className="text-sm text-rust bg-rust-bg rounded-md px-3 py-2">{error}</p>}

      {!revisions && <Loading />}

      {revisions && revisions.length === 0 && (
        <div className="bg-paper-raised border border-line rounded-lg shadow-sm px-4 py-8 text-center text-ink-soft">
          No pending revision requests. All caught up.
        </div>
      )}

      {revisions && revisions.length > 0 && (
        <div className="flex flex-col gap-3">
          {revisions.map((r) => (
            <div key={r.id} className="bg-paper-raised border border-line rounded-lg shadow-sm p-4 flex flex-col gap-2">
              <div className="flex items-center justify-between gap-2 text-xs text-ink-soft font-mono">
                <Link to={`/tasks/${r.task.id}`} className="hover:text-bark">
                  {r.task.task_number}
                </Link>
                <span>{clientName(r.task.client_id)}</span>
              </div>
              <Link to={`/tasks/${r.task.id}`} className="text-sm text-ink hover:text-bark">
                {r.task.description}
              </Link>
              <RevisionRow revision={r} canDecide onDecide={handleDecide} profileName={profileName} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
