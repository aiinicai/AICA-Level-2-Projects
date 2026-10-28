// Master prompt rule 5: 50,000 rows per side in under 10 seconds.
import { describe, expect, it } from 'vitest'
import type { CellValue, MatchKey } from '@shared/contracts'
import { buildStatement, reconcile } from '@engine/index'
import { amountKey, config, d, dateKey, meta, refKey, table } from './helpers'

/** Deterministic PRNG (mulberry32) so the test data is identical on every run. */
function rng(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

describe('performance', () => {
  it('reconciles 50,000 rows per side in under 10 seconds', () => {
    const N = 50_000
    const rand = rng(42)
    const rowsA: CellValue[][] = []
    const rowsB: CellValue[][] = []
    for (let k = 0; k < N; k++) {
      const amount = Math.round(rand() * 5_000_000) / 100 + 1
      const day = 1 + Math.floor(rand() * 28)
      const ref = `INV-${String(100000 + k)}`
      rowsA.push([d(2026, 9, day), ref, amount])
      const variant = rand()
      if (variant < 0.85) rowsB.push([d(2026, 9, Math.min(30, day + Math.floor(rand() * 3))), ref.replace('INV-', 'INV '), amount])
      else if (variant < 0.9) rowsB.push([d(2026, 9, day), ref, Math.round((amount + 9) * 100) / 100]) // amount differs → Doubtful
      else if (variant < 0.95) rowsB.push([d(2026, 9, day), `X${k}`, amount]) // reference differs → Doubtful
      else rowsB.push([d(2026, 9, day), `Y${k}`, Math.round(rand() * 100000) / 100]) // unrelated
    }
    const A = table(['Date', 'Ref', 'Amount'], rowsA)
    const B = table(['Date', 'Ref', 'Amount'], rowsB)
    const cfg = config([refKey(), dateKey(3), amountKey()])
    const t0 = performance.now()
    const r = reconcile(A, B, cfg)
    const elapsed = performance.now() - t0
    const st = buildStatement(r, meta())
    expect(r.linesA).toHaveLength(N)
    expect(r.stats.matched).toBeGreaterThan(0.8 * N)
    expect(r.stats.doubtful).toBeGreaterThan(0.08 * N)
    expect(st.unexplainedDifference).toBe(0)
    expect(elapsed).toBeLessThan(10_000)
  }, 30_000)

  it('a low-variety identifying key (Qty = 1 everywhere) stays linear: 50,000 rows per side in under 10 seconds', () => {
    const N = 50_000
    const tag: MatchKey = { id: 'tag', name: 'Tag', type: 'id', use: true, columnA: 'Tag', columnB: 'Tag', identifying: true, textRule: 'normalised' }
    const qty: MatchKey = { id: 'qty', name: 'Qty', type: 'number', use: true, columnA: 'Qty', columnB: 'Qty', identifying: true, tolerance: { mode: 'exact' } }
    const rowsA: CellValue[][] = []
    const rowsB: CellValue[][] = []
    for (let k = 0; k < N; k++) {
      rowsA.push([`T${100000 + k}`, 1])
      // 1% of tags differ, so those lines can only pair through the low-variety Qty key (Likely).
      rowsB.push([k % 100 === 0 ? `X${k}` : `T${100000 + k}`, 1])
    }
    const A = table(['Tag', 'Qty'], rowsA)
    const B = table(['Tag', 'Qty'], rowsB)
    const cfg = config([tag, qty], { amountA: undefined, amountB: undefined })
    const heap0 = process.memoryUsage().heapUsed
    const t0 = performance.now()
    const r = reconcile(A, B, cfg)
    const elapsed = performance.now() - t0
    const heapGrowth = process.memoryUsage().heapUsed - heap0
    expect(r.stats.matched).toBe(N - N / 100)
    // The 500 differing tags: each A line can only pair through Qty; with nothing to tell them apart they are
    // never guessed (one or more "Multiple identical candidates" groups), and nothing is lost.
    expect(r.stats.matched + r.stats.likely + r.stats.doubtful + r.stats.unmatchedA).toBe(N)
    expect(r.pairs.filter((p) => p.tier !== 'matched').every((p) => p.reason.includes('Candidate search limited'))).toBe(true)
    expect(elapsed).toBeLessThan(10_000)
    // Bounded memory: the old union-of-buckets search needed billions of candidate pairs (out of memory).
    expect(heapGrowth).toBeLessThan(1_000_000_000)
    console.log(`low-variety key: ${Math.round(elapsed)} ms, heap growth ${Math.round(heapGrowth / 1e6)} MB`)
  }, 60_000)
})
