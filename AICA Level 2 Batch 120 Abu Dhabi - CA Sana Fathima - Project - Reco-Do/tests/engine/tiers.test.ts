import { describe, expect, it } from 'vitest'
import type { MatchKey } from '@shared/contracts'
import { NO_IDENTIFYING_KEY_MESSAGE, reconcile, validateConfig, amountFlags, isDigitSwap } from '@engine/index'
import { amountKey, config, d, dateKey, refKey, table } from './helpers'

const cols = ['Date', 'Ref', 'Amount']
const T = (rows: Array<[Date | null, string | null, number | null]>) => table(cols, rows)

describe('3+ keys: Matched / Doubtful / Likely / Unmatched', () => {
  const cfg = config([refKey(), dateKey(3), amountKey()])

  it('all keys pass → Matched (accepted); reason notes a date shift within tolerance', () => {
    const r = reconcile(T([[d(2026, 9, 1), 'R1', 100]]), T([[d(2026, 9, 3), 'R1', 100]]), cfg)
    expect(r.pairs).toHaveLength(1)
    expect(r.pairs[0]).toMatchObject({ tier: 'matched', status: 'accepted', origin: 'engine', aIds: ['A:r2'], bIds: ['B:r2'], dateDifferenceDays: 2, amountDifference: 0 })
    expect(r.pairs[0].reason).toBe('Reference, amount and date agree; date 2 days apart (within ±3)')
  })

  it('exactly one key fails → Doubtful (open)', () => {
    const r = reconcile(T([[d(2026, 9, 1), 'R1', 100]]), T([[d(2026, 9, 6), 'R1', 100]]), cfg)
    expect(r.pairs[0]).toMatchObject({ tier: 'doubtful', status: 'open' })
    expect(r.pairs[0].reason).toBe('Reference and amount agree; date differs by 5 days')
    expect(r.pairs[0].keyResults.map((k) => k.pass)).toEqual([true, false, true])
  })

  it('only one identifying key passes → Likely', () => {
    const r = reconcile(T([[d(2026, 9, 1), 'R1', 100]]), T([[d(2026, 9, 20), 'ZZ', 100]]), cfg)
    expect(r.pairs[0].tier).toBe('likely')
    expect(r.pairs[0].reason).toBe("Only amount agrees; reference differs ('R1' vs 'ZZ'); date differs by 19 days")
  })

  it('date-only is never a match', () => {
    const r = reconcile(T([[d(2026, 9, 1), 'R1', 100]]), T([[d(2026, 9, 1), 'R2', 250]]), cfg)
    expect(r.pairs).toHaveLength(0)
    expect(r.unmatchedA).toEqual(['A:r2'])
    expect(r.unmatchedB).toEqual(['B:r2'])
  })

  it('4 keys with 2 failing → Unmatched', () => {
    const qty: MatchKey = { id: 'qty', name: 'Quantity', type: 'number', use: true, columnA: 'Qty', columnB: 'Qty', identifying: true, tolerance: { mode: 'exact' } }
    const c = config([refKey(), dateKey(0), amountKey(), qty])
    const A = table(['Date', 'Ref', 'Amount', 'Qty'], [[d(2026, 9, 1), 'R1', 100, 5]])
    const B = table(['Date', 'Ref', 'Amount', 'Qty'], [[d(2026, 9, 9), 'R1', 100, 7]])
    expect(reconcile(A, B, c).pairs).toHaveLength(0)
  })
})

describe('1 key and 2 key rules', () => {
  it('1 key: pass = Matched, fail = Unmatched (no Doubtful or Likely)', () => {
    const cfg = config([refKey()])
    const r = reconcile(T([[null, 'A-1', null], [null, 'B-2', null]]), T([[null, 'a1', null], [null, 'C-3', null]]), cfg)
    expect(r.pairs.map((p) => p.tier)).toEqual(['matched'])
    expect(r.unmatchedA).toEqual(['A:r3'])
    expect(r.unmatchedB).toEqual(['B:r3'])
  })

  it('2 keys: both pass = Matched; only an identifying key = Likely; never Doubtful', () => {
    const cfg = config([refKey(), amountKey()])
    const r = reconcile(T([[null, 'R1', 100], [null, 'R2', 200]]), T([[null, 'R1', 100], [null, 'R2', 999]]), cfg)
    expect(r.pairs.map((p) => p.tier)).toEqual(['matched', 'likely'])
    expect(r.stats.doubtful).toBe(0)
  })

  it('2 keys: only the date passes → Unmatched', () => {
    const cfg = config([dateKey(3), amountKey()])
    const r = reconcile(T([[d(2026, 9, 1), null, 100]]), T([[d(2026, 9, 1), null, 300]]), cfg)
    expect(r.pairs).toHaveLength(0)
  })

  it('2 keys: only a non-ID text key passes → Unmatched', () => {
    const name: MatchKey = { id: 'name', name: 'Name', type: 'text', use: true, columnA: 'Name', columnB: 'Name', identifying: false, textRule: 'normalised' }
    const emp: MatchKey = { id: 'emp', name: 'Employee ID', type: 'id', use: true, columnA: 'Emp', columnB: 'Emp', identifying: true, textRule: 'normalised' }
    const A = table(['Emp', 'Name'], [['001', 'Ali Khan'], ['002', 'Sara Ali']])
    const B = table(['Emp', 'Name'], [['1', 'ALI KHAN'], ['999', 'Sara Ali']])
    const r = reconcile(A, B, config([emp, name]))
    expect(r.pairs.map((p) => [p.tier, p.aIds[0]])).toEqual([['matched', 'A:r2']])
    expect(r.unmatchedA).toEqual(['A:r3'])
  })
})

describe('refusing to run without an identifying key', () => {
  const A = T([[d(2026, 9, 1), 'x', 1]])
  it('validateConfig explains the problem in plain English', () => {
    const nonId: MatchKey = { id: 'n', name: 'Narration', type: 'text', use: true, columnA: 'Ref', columnB: 'Ref', identifying: false, textRule: 'normalised' }
    expect(validateConfig(config([dateKey(3), nonId]), A, A)).toEqual([NO_IDENTIFYING_KEY_MESSAGE])
    expect(validateConfig(config([refKey(), dateKey(), amountKey()]), A, A)).toEqual([])
    expect(validateConfig(config([]), A, A)[0]).toContain('Choose at least one key')
  })
  it('reconcile throws the same message', () => {
    expect(() => reconcile(A, A, config([dateKey(3)]))).toThrow(NO_IDENTIFYING_KEY_MESSAGE)
  })
  it('reports missing columns and amount layouts', () => {
    const errs = validateConfig(config([refKey('Nope', 'Ref'), amountKey()], { amountB: undefined }), A, A)
    expect(errs.some((e) => e.includes('Choose a column in File A'))).toBe(true)
    expect(errs.some((e) => e.includes('Choose how File B shows amounts'))).toBe(true)
  })
})

describe('one-to-one assignment and preferences', () => {
  const cfg = config([refKey(), dateKey(3), amountKey()])
  it('prefers the closest date', () => {
    const r = reconcile(T([[d(2026, 9, 5), 'R1', 100]]), T([[d(2026, 9, 3), 'R1', 100], [d(2026, 9, 5), 'R1', 100]]), cfg)
    expect(r.pairs).toHaveLength(1)
    expect(r.pairs[0].bIds).toEqual(['B:r3'])
    expect(r.unmatchedB).toEqual(['B:r2'])
  })
  it('then the smallest amount difference', () => {
    const c = config([refKey(), dateKey(3), amountKey({ tolerance: { mode: 'fixed', value: 10 } })])
    const r = reconcile(T([[d(2026, 9, 5), 'R1', 100]]), T([[d(2026, 9, 5), 'R1', 108], [d(2026, 9, 5), 'R1', 103]]), c)
    expect(r.pairs[0].bIds).toEqual(['B:r3'])
  })
  it('Matched is assigned before Doubtful', () => {
    // A1 could be Doubtful with B1 (date off) but B1 is an exact match for A2.
    const r = reconcile(T([[d(2026, 9, 1), 'R1', 100], [d(2026, 9, 20), 'R1', 100]]), T([[d(2026, 9, 20), 'R1', 100]]), cfg)
    expect(r.pairs.map((p) => [p.tier, p.aIds[0]])).toEqual([['matched', 'A:r3']])
    expect(r.unmatchedA).toEqual(['A:r2'])
  })
})

describe('duplicates are never guessed', () => {
  const cfg = config([refKey(), dateKey(3), amountKey()], { moduleId: 'bank', sign: 'same' })
  it('three identical payments on both sides form one Doubtful "Multiple identical candidates" group', () => {
    const rows: Array<[Date, null, number]> = [[d(2026, 9, 15), null, -1000], [d(2026, 9, 15), null, -1000], [d(2026, 9, 15), null, -1000]]
    const r = reconcile(T(rows), T(rows), cfg)
    expect(r.pairs).toHaveLength(1)
    const p = r.pairs[0]
    expect(p).toMatchObject({ tier: 'doubtful', status: 'open', flags: ['multiple-candidates'] })
    expect(p.aIds).toHaveLength(3)
    expect(p.bIds).toHaveLength(3)
    expect(p.candidateIds).toEqual([...p.aIds, ...p.bIds])
    expect(p.reason.startsWith('Multiple identical candidates')).toBe(true)
    expect(p.amountDifference).toBe(0)
  })
  it('the same ID twice in one file (1 key) is Doubtful, not Matched', () => {
    const emp: MatchKey = { id: 'emp', name: 'Employee ID', type: 'id', use: true, columnA: 'Emp', columnB: 'Emp', identifying: true, textRule: 'normalised' }
    const r = reconcile(table(['Emp'], [['00234'], ['00235']]), table(['Emp'], [[234], [234], ['235']]), config([emp]))
    expect(r.pairs.map((p) => [p.tier, p.aIds.length, p.bIds.length])).toEqual([
      ['matched', 1, 1],
      ['doubtful', 1, 2]
    ])
    expect(r.pairs[1].aIds).toEqual(['A:r2'])
  })
  it('a better-dated candidate is not a tie', () => {
    const r = reconcile(T([[d(2026, 9, 15), null, 50]]), T([[d(2026, 9, 15), null, 50], [d(2026, 9, 17), null, 50]]), cfg)
    expect(r.pairs).toHaveLength(1)
    expect(r.pairs[0].flags).toEqual([])
    expect(r.pairs[0].bIds).toEqual(['B:r2'])
  })
})

describe('General recon without an amount', () => {
  it('matches on IDs alone; amounts stay null', () => {
    const emp: MatchKey = { id: 'emp', name: 'Emp ID', type: 'id', use: true, columnA: 'Emp ID', columnB: 'Employee No', identifying: true, textRule: 'normalised' }
    const iban: MatchKey = { id: 'iban', name: 'IBAN', type: 'id', use: true, columnA: 'IBAN', columnB: 'IBAN', identifying: true, textRule: 'normalised' }
    const A = table(['Emp ID', 'IBAN'], [['00174', 'AE070331234567890123456'], ['00175', 'AE11']])
    const B = table(['Employee No', 'IBAN'], [[174, 'AE070331234567890123456'], [175, 'AE99']])
    const r = reconcile(A, B, config([emp, iban], { amountA: undefined, amountB: undefined }))
    expect(r.pairs.map((p) => p.tier)).toEqual(['matched', 'likely'])
    expect(r.pairs.every((p) => p.amountDifference === null)).toBe(true)
    expect(r.linesA.every((l) => l.amount === null)).toBe(true)
    expect(r.pairs[1].reason).toBe("Only emp ID agrees; IBAN differs ('AE11' vs 'AE99')")
  })
})

describe('key rules', () => {
  const A = T([[null, 'CHQ-004512', null]])
  it('exact vs normalised text', () => {
    const B = T([[null, '4512', null]])
    expect(reconcile(A, B, config([refKey('Ref', 'Ref', { textRule: 'exact' })])).pairs).toHaveLength(0)
    expect(reconcile(A, B, config([refKey('Ref', 'Ref', { textRule: 'normalised' })])).pairs).toHaveLength(1)
  })
  it('contains works in either direction and ignores case', () => {
    const c = config([refKey('Ref', 'Ref', { textRule: 'contains' })])
    expect(reconcile(T([[null, 'FT2609ABC', null]]), T([[null, 'Rcpt ft2609abc - Al Noor', null]]), c).pairs).toHaveLength(1)
    expect(reconcile(T([[null, 'Payment FT2609ABC done', null]]), T([[null, 'FT2609ABC', null]]), c).pairs).toHaveLength(1)
    expect(reconcile(T([[null, 'FT2609ABC', null]]), T([[null, 'FT2609ABD', null]]), c).pairs).toHaveLength(0)
  })
  it('amount ± fixed and ± percent', () => {
    const rowsA = T([[null, null, 1000]])
    const rowsB = T([[null, null, 1004.99]])
    expect(reconcile(rowsA, rowsB, config([amountKey()])).pairs).toHaveLength(0)
    expect(reconcile(rowsA, rowsB, config([amountKey({ tolerance: { mode: 'fixed', value: 5 } })])).pairs).toHaveLength(1)
    expect(reconcile(rowsA, rowsB, config([amountKey({ tolerance: { mode: 'percent', value: 0.5 } })])).pairs).toHaveLength(1)
    expect(reconcile(rowsA, rowsB, config([amountKey({ tolerance: { mode: 'percent', value: 0.4 } })])).pairs).toHaveLength(0)
  })
  it('number keys with tolerance', () => {
    const qty: MatchKey = { id: 'q', name: 'Quantity', type: 'number', use: true, columnA: 'Qty', columnB: 'Qty', identifying: true, tolerance: { mode: 'fixed', value: 1 } }
    const r = reconcile(table(['Qty'], [[10], [20]]), table(['Qty'], [[11], [25]]), config([qty]))
    expect(r.pairs.map((p) => p.aIds[0])).toEqual(['A:r2'])
  })
  it('date ± N days', () => {
    const c0 = config([refKey(), dateKey(0)])
    const c2 = config([refKey(), dateKey(2)])
    const a = T([[d(2026, 9, 1), 'R', null]])
    const b = T([[d(2026, 9, 3), 'R', null]])
    expect(reconcile(a, b, c0).pairs[0].tier).toBe('likely')
    expect(reconcile(a, b, c2).pairs[0].tier).toBe('matched')
  })
})

describe('difference flags', () => {
  it('transposition: difference divisible by 9 with two digits swapped', () => {
    expect(isDigitSwap(845000, 854000)).toBe(true)
    expect(amountFlags(845000, 854000)).toContain('transposition')
    expect(amountFlags(100000, 100900)).not.toContain('transposition') // divisible by 9, but no swap
  })
  it('bank charge: small difference within 1%; rounding: 1.00 or less', () => {
    expect(amountFlags(1847500, 1850000)).toEqual(['bank-charge'])
    expect(amountFlags(731840, 731890)).toEqual(['rounding'])
    expect(amountFlags(1530000, 1500000)).toEqual([])
  })
  it('flags and reasons on pairs', () => {
    const cfg = config([refKey(), dateKey(3), amountKey()], { moduleId: 'bank' })
    const r = reconcile(T([[d(2026, 9, 9), 'TT1', 18475], [d(2026, 9, 17), 'C2', 8450]]), T([[d(2026, 9, 9), 'TT1', 18500], [d(2026, 9, 17), 'C2', 8540]]), cfg)
    expect(r.pairs[0].flags).toEqual(['bank-charge'])
    expect(r.pairs[0].reason).toBe('Reference and date agree; amount differs by 25.00 (within 1%, possible bank charge)')
    expect(r.pairs[1].flags).toEqual(['transposition'])
    expect(r.pairs[1].reason).toBe('Reference and date agree; amount differs by 90.00 (possible transposition 8,450.00 vs 8,540.00)')
  })
})
