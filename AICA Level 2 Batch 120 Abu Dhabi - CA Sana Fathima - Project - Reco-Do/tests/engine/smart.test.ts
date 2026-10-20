import { describe, expect, it } from 'vitest'
import type { CellValue } from '@shared/contracts'
import { extractTokens, findGroupMatches, findPartialReferenceMatches, reconcile } from '@engine/index'
import { amountKey, config, d, dateKey, refKey, table } from './helpers'

const cols = ['Date', 'Ref', 'Amount', 'Party', 'Remarks']
const T = (rows: CellValue[][]) => table(cols, rows)
const cfg = config([refKey(), dateKey(3), amountKey()], { partyColumnB: 'Party' })

describe('sum matching (bounded subset-sum)', () => {
  it('finds 1:3 and 2:1 groups within the date window', () => {
    const A = T([
      [d(2026, 9, 22), 'TT1', 36750, null, null],
      [d(2026, 9, 10), 'TT2', 9412.35, null, null],
      [d(2026, 9, 10), 'TT3', 6187.9, null, null]
    ])
    const B = T([
      [d(2026, 9, 21), 'INV-811', 12250, 'Bin Hamdan', null],
      [d(2026, 9, 22), 'INV-812', 12250, 'Bin Hamdan', null],
      [d(2026, 9, 23), 'INV-813', 12250, 'Bin Hamdan', null],
      [d(2026, 9, 10), 'RCPT-9', 15600.25, 'Falcon', null]
    ])
    const r = reconcile(A, B, cfg)
    expect(r.pairs).toHaveLength(0)
    const { suggestions, capped } = findGroupMatches(r)
    expect(capped).toBe(false)
    const shapes = suggestions.map((s) => [s.aIds, s.bIds])
    expect(shapes).toContainEqual([['A:r2'], ['B:r2', 'B:r3', 'B:r4']])
    expect(shapes).toContainEqual([['A:r3', 'A:r4'], ['B:r5']])
    expect(suggestions.every((s) => s.source === 'code-group' && s.status === 'open' && s.confidence === 90)).toBe(true)
    expect(suggestions.find((s) => s.bIds.length === 3)?.reason).toContain('same party (Bin Hamdan)')
  })

  it('respects the date window and the party', () => {
    const A = T([[d(2026, 9, 22), 'TT1', 300, null, null]])
    const far = T([
      [d(2026, 9, 1), 'X', 100, 'P', null],
      [d(2026, 9, 22), 'Y', 200, 'P', null]
    ])
    expect(findGroupMatches(reconcile(A, far, cfg)).suggestions).toHaveLength(0)
    const parties = T([
      [d(2026, 9, 22), 'X', 100, 'P', null],
      [d(2026, 9, 22), 'Y', 200, 'Q', null]
    ])
    expect(findGroupMatches(reconcile(A, parties, cfg)).suggestions).toHaveLength(0)
  })

  it('respects the maximum group size and reports when the search was capped', () => {
    const A = T([[d(2026, 9, 1), 'T', 600, null, null]])
    const B = T([1, 2, 3, 4, 5, 6].map((k) => [d(2026, 9, 1), `B${k}`, 100, 'P', null]))
    const r = reconcile(A, B, cfg)
    expect(findGroupMatches(r, { maxGroupSize: 5 }).suggestions).toHaveLength(0)
    expect(findGroupMatches(r, { maxGroupSize: 6 }).suggestions).toHaveLength(1)
    const capped = findGroupMatches(r, { maxGroupSize: 6, maxCandidates: 3 })
    expect(capped.capped).toBe(true)
  })

  it('needs an amount key', () => {
    const r = reconcile(T([[null, 'R', 1, null, null]]), T([[null, 'R', 1, null, null]]), config([refKey()]))
    expect(findGroupMatches(r)).toEqual({ suggestions: [], capped: false })
  })

  it('lowers confidence when several combinations add up', () => {
    const A = T([[d(2026, 9, 1), 'T', 300, null, null]])
    const B = T([
      [d(2026, 9, 1), 'B1', 100, 'P', null],
      [d(2026, 9, 1), 'B2', 200, 'P', null],
      [d(2026, 9, 1), 'B3', 150, 'P', null],
      [d(2026, 9, 1), 'B4', 150, 'P', null]
    ])
    const s = findGroupMatches(reconcile(A, B, cfg)).suggestions
    expect(s).toHaveLength(1)
    expect(s[0].confidence).toBe(55)
    expect(s[0].reason).toContain('other combination')
  })
})

describe('partial reference', () => {
  it('extracts digit runs of 4+ and alphanumeric codes', () => {
    expect(extractTokens('Rcpt FT2609ABC - Al Noor 2026 CHQ 004512 ab12 xy1')).toEqual(['FT2609ABC', '2026', '4512', 'AB12'])
  })

  it('finds a reference inside the other side’s text when amounts agree', () => {
    const A = T([[d(2026, 9, 5), 'FT2609ABC', 24208.56, null, null]])
    const B = T([
      [d(2026, 9, 5), null, 24208.56, 'Al Noor', 'Rcpt FT2609ABC - Al Noor Trading LLC'],
      [d(2026, 9, 5), null, 999, 'Other', 'Rcpt FT2609ZZZ']
    ])
    const r = reconcile(A, B, config([refKey(), dateKey(3), amountKey()]))
    const doubt = r.pairs.find((p) => p.tier === 'doubtful')
    expect(doubt).toBeDefined()
    expect(findPartialReferenceMatches(r)).toHaveLength(0) // lines are in a Doubtful pair, not unmatched
    const s = findPartialReferenceMatches(r, { includeDoubtful: true })
    expect(s).toHaveLength(1)
    expect(s[0]).toMatchObject({ aIds: ['A:r2'], bIds: ['B:r2'], source: 'code-partial-ref', confidence: 85 })
    expect(s[0].reason).toContain('"FT2609ABC" found in GL Remarks'.replace('GL', 'File B'))
  })

  it('does not guess when a token points to two equally good lines, and needs the amounts to agree', () => {
    const A = T([[d(2026, 9, 5), 'REF 77881', 500, null, null]])
    const twins = T([
      [d(2026, 9, 5), null, 400, null, 'payment 77881 part'],
      [d(2026, 9, 5), null, 500, null, 'payment 77881'],
      [d(2026, 9, 5), null, 500, null, 'again 77881']
    ])
    const r = reconcile(A, twins, config([refKey(), dateKey(3), amountKey()]))
    // the two 500.00 lines form a duplicate group in Step 3 (amount + date agree)
    expect(findPartialReferenceMatches(r, { includeDoubtful: true })).toHaveLength(0)
  })
})
