import { describe, expect, it } from 'vitest'
import { buildExportModel } from '@export/index'
import { bankFixture } from './fixtures'

describe('export tier amounts', () => {
  it('are absolute sums, the same definition as the on-screen KPIs (stats.matchedAmount)', () => {
    const { session } = bankFixture()
    const m = buildExportModel(session)
    // Matched: |-8,450| + |25,000| + |14,700| (a payment and two receipts never net off).
    expect(m.totals.matched.amount).toBe(48150)
    expect(m.totals.matched.amount).toBe(session.result.stats.matchedAmount)
    expect(m.totals.doubtful.amount).toBe(8540)
    expect(m.totals.likely.amount).toBe(1200)
    expect(m.totals.unmatchedA.amount).toBe(1862.75)
    expect(m.totals.unmatchedB.amount).toBe(10400)
    expect(m.totals.assisted.amount).toBe(14700)
  })
})
