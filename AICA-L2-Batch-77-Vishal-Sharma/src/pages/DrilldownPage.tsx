import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchMyVisibleTasks } from '../lib/queries'
import { dueBucketFor, type DueBucket, type TaskWithDueDate } from '../types/database'
import { useDirectory } from '../lib/DirectoryProvider'
import { StatusBadge, UrgencyBadge } from '../components/Badges'
import { Loading } from '../components/Loading'

/** Printable drill-down for a single due-bucket cell clicked on the
 * Dashboard's summary tables — the underlying task list, in table form. */
export function DrilldownPage() {
  const [searchParams] = useSearchParams()
  const field = searchParams.get('field') === 'secondary_assignee_id' ? 'secondary_assignee_id' : 'primary_assignee_id'
  const bucket = searchParams.get('bucket') as DueBucket | null
  const assigneeId = searchParams.get('assignee')

  const { profileName, clientName } = useDirectory()
  const [tasks, setTasks] = useState<TaskWithDueDate[] | null>(null)

  useEffect(() => {
    fetchMyVisibleTasks().then(setTasks)
  }, [])

  if (!tasks || !bucket) return <Loading />

  const filtered = tasks.filter((t) => {
    if (t.status === 'Closed') return false
    if (!t[field]) return false
    if (assigneeId && t[field] !== assigneeId) return false
    return dueBucketFor(t, t.effective_due_date) === bucket
  })

  const roleLabel = field === 'primary_assignee_id' ? 'Primary Assignee' : 'Secondary Assignee'
  const scopeLabel = assigneeId ? profileName(assigneeId) : 'Everyone'

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between print:hidden">
        <Link to="/" className="text-sm text-ink-soft hover:text-ink underline underline-offset-2">
          ← Back to Dashboard
        </Link>
        <button
          onClick={() => window.print()}
          className="text-sm font-medium px-4 py-2 rounded-md bg-bark-gradient text-white transition-colors"
        >
          Print
        </button>
      </div>

      <div>
        <h1 className="font-serif text-2xl font-semibold text-ink">
          {bucket} — {scopeLabel}
        </h1>
        <p className="text-sm text-ink-soft">
          By {roleLabel} · {filtered.length} task{filtered.length === 1 ? '' : 's'}
        </p>
      </div>

      <div className="bg-paper-raised border border-line rounded-lg shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-ink-soft font-mono text-xs uppercase tracking-wide">
              <th className="px-4 py-2 font-medium">Task ID</th>
              <th className="px-4 py-2 font-medium">Description</th>
              <th className="px-4 py-2 font-medium">Client</th>
              <th className="px-4 py-2 font-medium">Primary</th>
              <th className="px-4 py-2 font-medium">Secondary</th>
              <th className="px-4 py-2 font-medium">Due Date</th>
              <th className="px-4 py-2 font-medium">Urgency</th>
              <th className="px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((t) => (
              <tr key={t.id} className="border-b border-line last:border-0">
                <td className="px-4 py-2 font-mono text-xs text-ink-soft whitespace-nowrap">{t.task_number}</td>
                <td className="px-4 py-2 text-ink break-words">{t.description}</td>
                <td className="px-4 py-2 text-ink-soft break-words">{clientName(t.client_id)}</td>
                <td className="px-4 py-2 text-ink-soft break-words">{profileName(t.primary_assignee_id)}</td>
                <td className="px-4 py-2 text-ink-soft break-words">
                  {t.secondary_assignee_id ? profileName(t.secondary_assignee_id) : '—'}
                </td>
                <td className="px-4 py-2 text-ink-soft font-mono tabular-nums whitespace-nowrap">
                  {t.effective_due_date}
                </td>
                <td className="px-4 py-2">
                  <UrgencyBadge urgency={t.urgency} />
                </td>
                <td className="px-4 py-2">
                  <StatusBadge status={t.status} />
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-ink-soft">
                  No tasks in this bucket.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
