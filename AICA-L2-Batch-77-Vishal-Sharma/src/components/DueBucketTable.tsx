import { useNavigate } from 'react-router-dom'
import { dueBucketFor, type DueBucket, type TaskWithDueDate } from '../types/database'
import { useDirectory } from '../lib/DirectoryProvider'

const BUCKETS: DueBucket[] = ['Overdue', 'Due in 3 days', 'Due in 4-6 days', '7 days & more', 'Others']
// "Others" (Hold-status tasks, mainly) is still counted internally, just not
// given its own column — it's a small, low-signal catch-all next to the
// date-driven buckets.
const DISPLAY_BUCKETS = BUCKETS.filter((b) => b !== 'Others')

type Tone = 'rust' | 'gold' | 'neutral'

const bucketTone: Record<DueBucket, Tone> = {
  Overdue: 'rust',
  'Due in 3 days': 'gold',
  'Due in 4-6 days': 'gold',
  '7 days & more': 'neutral',
  Others: 'neutral',
}

// Heat intensity: 0 = empty cell, 1 = soft tint, 2+ = solid fill — so a
// column gets visibly hotter the more tasks pile up in it, instead of just
// showing a bare number.
const heatClass = (count: number, tone: Tone) => {
  if (count === 0) return 'bg-slate-bg/40 text-ink-soft/40'
  if (tone === 'rust') return count === 1 ? 'bg-rust-bg text-rust' : 'bg-rust text-white'
  if (tone === 'gold') return count === 1 ? 'bg-gold-bg text-gold-ink' : 'bg-gold-ink text-white'
  return count === 1 ? 'bg-slate-bg text-slate' : 'bg-slate text-white'
}

/** Recreates the old "Task due summary report" pivot: due-bucket counts
 * broken out by assignee, for either the Primary or Secondary column. Closed
 * tasks are excluded entirely per the Part 5 decision. Each non-zero count
 * links to a printable drill-down list of the underlying tasks, and a
 * Rating dot flags anyone currently carrying an overdue task. */
export function DueBucketTable({
  tasks,
  assigneeField,
  title,
}: {
  tasks: TaskWithDueDate[]
  assigneeField: 'primary_assignee_id' | 'secondary_assignee_id'
  title: string
}) {
  const { profileName } = useDirectory()
  const navigate = useNavigate()

  const open = tasks.filter((t) => t.status !== 'Closed' && t[assigneeField])

  const byAssignee = new Map<string, Record<DueBucket, number>>()
  for (const t of open) {
    const assigneeId = t[assigneeField] as string
    const bucket = dueBucketFor(t, t.effective_due_date)
    if (!byAssignee.has(assigneeId)) {
      byAssignee.set(assigneeId, { Overdue: 0, 'Due in 3 days': 0, 'Due in 4-6 days': 0, '7 days & more': 0, Others: 0 })
    }
    byAssignee.get(assigneeId)![bucket]++
  }

  const rows = [...byAssignee.entries()].sort((a, b) => profileName(a[0]).localeCompare(profileName(b[0])))

  const totals: Record<DueBucket, number> = {
    Overdue: 0,
    'Due in 3 days': 0,
    'Due in 4-6 days': 0,
    '7 days & more': 0,
    Others: 0,
  }
  for (const [, counts] of rows) {
    for (const b of BUCKETS) totals[b] += counts[b]
  }

  const goToDrilldown = (assigneeId: string | null, bucket: DueBucket) => {
    const params = new URLSearchParams({ field: assigneeField, bucket })
    if (assigneeId) params.set('assignee', assigneeId)
    navigate(`/dashboard/drilldown?${params.toString()}`)
  }

  const heatCell = (count: number, assigneeId: string | null, bucket: DueBucket) => {
    const classes = `flex h-8 w-full items-center justify-center rounded-md font-mono text-xs font-semibold tabular-nums ${heatClass(count, bucketTone[bucket])}`
    if (!count) return <div className={classes}>0</div>
    return (
      <button
        type="button"
        onClick={() => goToDrilldown(assigneeId, bucket)}
        className={`${classes} hover:opacity-80 focus:outline-none focus-visible:ring-1 focus-visible:ring-bark/40`}
      >
        {count}
      </button>
    )
  }

  return (
    <div className="self-start bg-paper-raised border border-line rounded-lg shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-line">
        <h3 className="font-serif text-base font-semibold text-ink">{title}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="text-sm">
          <thead>
            <tr className="bg-bark-gradient text-white">
              <th className="text-left font-medium px-4 py-2">Name</th>
              {DISPLAY_BUCKETS.map((b) => (
                <th key={b} className="text-center font-medium px-1.5 py-2 whitespace-nowrap font-mono text-xs">
                  {b}
                </th>
              ))}
              <th className="text-center font-medium px-3 py-2 whitespace-nowrap font-mono text-xs">Rating</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={DISPLAY_BUCKETS.length + 2} className="px-4 py-6 text-center text-ink-soft">
                  No open tasks.
                </td>
              </tr>
            )}
            {rows.map(([assigneeId, counts], i) => (
              <tr key={assigneeId} className={i % 2 ? 'bg-paper' : ''}>
                <td className="px-4 py-1.5 text-ink font-medium whitespace-nowrap">{profileName(assigneeId)}</td>
                {DISPLAY_BUCKETS.map((b) => (
                  <td key={b} className="px-1.5 py-1.5">
                    {heatCell(counts[b], assigneeId, b)}
                  </td>
                ))}
                <td className="text-center px-3 py-1.5">
                  <span
                    title={counts.Overdue > 0 ? 'Has overdue tasks' : 'No overdue tasks'}
                    className="inline-block h-6 w-6 rounded-full"
                    style={{ background: counts.Overdue > 0 ? '#FF3B30' : '#22C55E' }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
          {rows.length > 0 && (
            <tfoot>
              <tr className="border-t border-line font-semibold">
                <td className="px-4 py-2 text-ink">Grand Total</td>
                {DISPLAY_BUCKETS.map((b) => (
                  <td key={b} className="px-1.5 py-2">
                    {heatCell(totals[b], null, b)}
                  </td>
                ))}
                <td></td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  )
}
