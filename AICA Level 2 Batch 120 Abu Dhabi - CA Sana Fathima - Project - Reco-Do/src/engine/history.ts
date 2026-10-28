// History summary for the dashboard KPIs, and ageing buckets for open items.

import type { EngineLine, ReconSession } from '@shared/contracts'
import type { HistoryEntry } from '@shared/kpis'
import { dayNumber, isoDay, round2 } from './util'

export type AgeingBucket = '0-30' | '31-60' | '61-90' | '90+'

/** Age in whole calendar days from `date` to `asOf`; future dates count as 0 days old. */
export function ageingBucket(date: Date, asOf: Date): AgeingBucket {
  const days = Math.max(0, dayNumber(asOf) - dayNumber(date))
  if (days <= 30) return '0-30'
  if (days <= 60) return '31-60'
  if (days <= 90) return '61-90'
  return '90+'
}

/**
 * - totalLines: File A lines + File B lines.
 * - autoMatchedLines: lines on both sides inside accepted Matched pairs.
 * - openItemCount: unmatched lines on both sides plus the lines inside open Doubtful/Likely pairs.
 * - openItemAmount: Σ |amount| of unmatched lines plus Σ |difference| of open pairs (0 without an amount key).
 * - oldestOpenItemDate: the earliest date among those open lines.
 */
export function summariseForHistory(s: ReconSession): HistoryEntry {
  const r = s.result
  const byId = new Map<string, EngineLine>()
  for (const l of r.linesA) byId.set(l.id, l)
  for (const l of r.linesB) byId.set(l.id, l)

  let autoMatchedLines = 0
  let openItemCount = 0
  let openItemAmount = 0
  let oldest: Date | null = null
  const consider = (id: string): void => {
    const d = byId.get(id)?.date
    if (d && (!oldest || d.getTime() < oldest.getTime())) oldest = d
  }
  for (const p of r.pairs) {
    if (p.tier === 'matched' && p.status === 'accepted') autoMatchedLines += p.aIds.length + p.bIds.length
    else if (p.status === 'open') {
      openItemCount += p.aIds.length + p.bIds.length
      openItemAmount += Math.abs(p.amountDifference ?? 0)
      for (const id of [...p.aIds, ...p.bIds]) consider(id)
    }
  }
  for (const id of [...r.unmatchedA, ...r.unmatchedB]) {
    openItemCount++
    openItemAmount += Math.abs(byId.get(id)?.comparableAmount ?? 0)
    consider(id)
  }
  const oldestDate = oldest as Date | null
  return {
    id: s.id,
    moduleId: r.config.moduleId,
    accountLabel: s.meta.accountLabel,
    finishedAt: s.finalised?.at ?? s.updatedAt,
    totalLines: r.linesA.length + r.linesB.length,
    autoMatchedLines,
    openItemCount,
    openItemAmount: round2(openItemAmount),
    oldestOpenItemDate: oldestDate ? isoDay(oldestDate) : null
  }
}
