import type { HistoryEntry } from '@shared/kpis'
import { formatDate } from '@shared/format'

/** Dashboard card footer: "Last run: today 14:05", "Last run: 05-Oct-2026" (DD-MMM-YYYY) or "Last run: never". */
export function lastRunLabel(moduleId: string, history: HistoryEntry[], now: Date = new Date()): string {
  const runs = history
    .filter((h) => h.moduleId === moduleId)
    .map((h) => new Date(h.finishedAt).getTime())
    .filter((t) => !Number.isNaN(t))
  if (!runs.length) return 'Last run: never'
  const last = new Date(Math.max(...runs))
  if (last.toDateString() === now.toDateString()) return `Last run: today ${last.toTimeString().slice(0, 5)}`
  return `Last run: ${formatDate(last)}`
}
