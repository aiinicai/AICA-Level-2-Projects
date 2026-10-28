import type { ModuleId } from './modules'

/** One finished (or saved) reconciliation, as stored in recon history. */
export interface HistoryEntry {
  id: string
  moduleId: ModuleId
  accountLabel: string
  finishedAt: string // ISO timestamp
  totalLines: number
  autoMatchedLines: number
  openItemCount: number
  openItemAmount: number
  /** ISO date of the oldest still-open item, if any. */
  oldestOpenItemDate: string | null
}

export interface DashboardKpis {
  reconsThisMonth: number
  reconsLastMonth: number
  avgAutoMatchRate: number | null
  openItemCount: number
  openItemAmount: number
  oldestOpenItem: { days: number; account: string } | null
}

const DAY_MS = 86_400_000

function monthKey(d: Date): number {
  return d.getFullYear() * 12 + d.getMonth()
}

export function computeKpis(history: HistoryEntry[], now: Date): DashboardKpis {
  const thisMonth = monthKey(now)
  let reconsThisMonth = 0
  let reconsLastMonth = 0
  let rateSum = 0
  let rateCount = 0
  let openItemCount = 0
  let openItemAmount = 0
  let oldest: { date: Date; account: string } | null = null

  for (const h of history) {
    const key = monthKey(new Date(h.finishedAt))
    if (key === thisMonth) reconsThisMonth++
    else if (key === thisMonth - 1) reconsLastMonth++

    if (h.totalLines > 0) {
      rateSum += h.autoMatchedLines / h.totalLines
      rateCount++
    }
    openItemCount += h.openItemCount
    openItemAmount += h.openItemAmount

    if (h.oldestOpenItemDate) {
      const d = new Date(h.oldestOpenItemDate)
      if (!oldest || d < oldest.date) oldest = { date: d, account: h.accountLabel }
    }
  }

  return {
    reconsThisMonth,
    reconsLastMonth,
    avgAutoMatchRate: rateCount ? rateSum / rateCount : null,
    openItemCount,
    openItemAmount,
    oldestOpenItem: oldest
      ? { days: Math.floor((now.getTime() - oldest.date.getTime()) / DAY_MS), account: oldest.account }
      : null
  }
}
