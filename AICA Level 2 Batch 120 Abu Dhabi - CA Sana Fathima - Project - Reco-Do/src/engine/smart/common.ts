// Shared helpers for the code side of Smart Recon: which lines are eligible, and small formatting helpers.

import type { EngineLine, ReconResult } from '@shared/contracts'

export interface Pools {
  a: EngineLine[]
  b: EngineLine[]
  /** pair id per line for lines taken from open Doubtful pairs. */
  pairOf: Map<string, string>
}

/** Smart Recon works only on Unmatched lines and, optionally, lines in open Doubtful pairs. */
export function eligiblePools(result: ReconResult, includeDoubtful: boolean): Pools {
  const ids = new Set<string>([...result.unmatchedA, ...result.unmatchedB])
  const pairOf = new Map<string, string>()
  if (includeDoubtful) {
    for (const p of result.pairs) {
      if (p.tier !== 'doubtful' || p.status !== 'open') continue
      for (const id of [...p.aIds, ...p.bIds]) {
        ids.add(id)
        pairOf.set(id, p.id)
      }
    }
  }
  return {
    a: result.linesA.filter((l) => ids.has(l.id)),
    b: result.linesB.filter((l) => ids.has(l.id)),
    pairOf
  }
}
