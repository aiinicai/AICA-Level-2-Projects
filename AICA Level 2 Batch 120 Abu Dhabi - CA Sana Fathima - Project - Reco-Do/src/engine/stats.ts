// Recomputes unmatched lists and tier statistics from a set of pairs.

import type { EngineLine, MatchPair, ReconStats } from '@shared/contracts'
import { round2 } from './util'

export interface Rebuilt {
  unmatchedA: string[]
  unmatchedB: string[]
  stats: ReconStats
}

/**
 * Counts are File A lines per tier (the convention used in sample-data/README.md); unmatchedB counts File B lines.
 * matchedAmount is the sum of absolute comparable File A amounts in matched pairs (0 without an amount key).
 */
export function rebuild(linesA: EngineLine[], linesB: EngineLine[], pairs: MatchPair[]): Rebuilt {
  const usedA = new Set<string>()
  const usedB = new Set<string>()
  let matched = 0
  let doubtful = 0
  let likely = 0
  let matchedAmount = 0
  const amountOf = new Map<string, number | null>()
  for (const l of linesA) amountOf.set(l.id, l.comparableAmount)
  for (const p of pairs) {
    for (const id of p.aIds) usedA.add(id)
    for (const id of p.bIds) usedB.add(id)
    const n = p.aIds.length
    if (p.tier === 'matched') {
      matched += n
      for (const id of p.aIds) matchedAmount += Math.abs(amountOf.get(id) ?? 0)
    } else if (p.tier === 'doubtful') doubtful += n
    else if (p.tier === 'likely') likely += n
  }
  const unmatchedA = linesA.filter((l) => !usedA.has(l.id)).map((l) => l.id)
  const unmatchedB = linesB.filter((l) => !usedB.has(l.id)).map((l) => l.id)
  return {
    unmatchedA,
    unmatchedB,
    stats: {
      linesA: linesA.length,
      linesB: linesB.length,
      matched,
      doubtful,
      likely,
      unmatchedA: unmatchedA.length,
      unmatchedB: unmatchedB.length,
      matchedAmount: round2(matchedAmount)
    }
  }
}
