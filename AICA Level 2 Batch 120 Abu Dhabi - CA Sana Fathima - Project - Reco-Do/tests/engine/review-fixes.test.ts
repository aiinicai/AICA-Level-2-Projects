// Regression tests for the engine fixes from the independent review (candidate search, tie grouping,
// negative credits, date order, transposition in cents, record-count check).
import { describe, expect, it } from 'vitest'
import type { CellValue, MatchKey } from '@shared/contracts'
import { amountFlags, buildLines, buildStatement, detectConfigDateOrders, detectNegativeCreditColumn, reconcile, signedAmount } from '@engine/index'
import { amountKey, config, d, dateKey, metaFor, refKey, table } from './helpers'

const qtyKey: MatchKey = { id: 'qty', name: 'Qty', type: 'number', use: true, columnA: 'Qty', columnB: 'Qty', identifying: true, tolerance: { mode: 'exact' } }
const tagKey: MatchKey = { id: 'tag', name: 'Tag', type: 'id', use: true, columnA: 'Tag', columnB: 'Tag', identifying: true, textRule: 'normalised' }

describe('candidate search with a low-variety identifying key', () => {
  it('Tag + Qty (all 1): tags decide, the Qty bucket is never searched in full', () => {
    const N = 2000
    const rowsA: CellValue[][] = []
    const rowsB: CellValue[][] = []
    for (let k = 0; k < N; k++) {
      rowsA.push([`T${k}`, 1])
      rowsB.push([k === 7 ? 'OTHER' : `T${k}`, 1])
    }
    const r = reconcile(table(['Tag', 'Qty'], rowsA), table(['Tag', 'Qty'], rowsB), config([tagKey, qtyKey], { amountA: undefined, amountB: undefined }))
    expect(r.stats.matched).toBe(N - 1)
    // The one line whose tag differs pairs only through Qty → Likely (the only open line on each side).
    const likely = r.pairs.filter((p) => p.tier === 'likely')
    expect(likely).toHaveLength(1)
    expect(likely[0].aIds).toEqual(['A:r9'])
    expect(likely[0].bIds).toEqual(['B:r9'])
    // Only one File B line was still open, so nothing was cut off and the reason carries no limit note.
    expect(likely[0].reason).not.toContain('Candidate search limited')
  })

  it('a repeated amount still finds Doubtful pairs (reference differs, amount and date agree) inside the date window', () => {
    const rowsA: CellValue[][] = []
    const rowsB: CellValue[][] = []
    for (let k = 0; k < 1000; k++) {
      const day = 1 + (k % 28)
      rowsA.push([d(2026, 9, day), `R${k}`, 1000])
      rowsB.push([d(2026, 9, day), k === 500 ? 'ZZZ' : `R${k}`, 1000])
    }
    // An unrelated line far away in time with the same amount must not steal the Doubtful pair.
    rowsB.push([d(2026, 12, 1), 'Q1', 1000])
    const r = reconcile(table(['Date', 'Ref', 'Amount'], rowsA), table(['Date', 'Ref', 'Amount'], rowsB), config([refKey(), dateKey(3), amountKey()]))
    expect(r.stats.matched).toBe(999)
    const doubtful = r.pairs.filter((p) => p.tier === 'doubtful')
    expect(doubtful).toHaveLength(1)
    expect(doubtful[0].aIds).toEqual(['A:r502'])
    expect(doubtful[0].bIds).toEqual(['B:r502'])
    expect(r.unmatchedB).toEqual(['B:r1002'])
  })

  it('one low-variety key only: identical lines are grouped, never guessed, and the run stays fast', () => {
    const rows: CellValue[][] = Array.from({ length: 5000 }, () => [1])
    const t0 = performance.now()
    const r = reconcile(table(['Qty'], rows), table(['Qty'], rows), config([qtyKey], { amountA: undefined, amountB: undefined }))
    expect(performance.now() - t0).toBeLessThan(5000)
    expect(r.stats.matched).toBe(0)
    expect(r.pairs.every((p) => p.flags.includes('multiple-candidates'))).toBe(true)
    expect(r.unmatchedA.length + r.pairs.reduce((s, p) => s + p.aIds.length, 0)).toBe(5000)
  })
})

describe('tie grouping never swallows a clear mutual best', () => {
  const cfg = config([amountKey(), dateKey(3)])
  const T = (rows: Array<[Date, number]>) => table(['Date', 'Amount'], rows)

  it('A1↔B1 exact pair is matched; A2 then pairs with B2', () => {
    const r = reconcile(T([[d(2026, 9, 5), 1000], [d(2026, 9, 4), 1000]]), T([[d(2026, 9, 5), 1000], [d(2026, 9, 3), 1000]]), cfg)
    expect(r.pairs.map((p) => [p.tier, p.aIds, p.bIds, p.flags])).toEqual([
      ['matched', ['A:r2'], ['B:r2'], []],
      ['matched', ['A:r3'], ['B:r3'], []]
    ])
    expect(r.unmatchedA).toEqual([])
  })

  it('lines genuinely tied at the top are still grouped, without pulling in a clear pair', () => {
    // A1/A2 on 10-Sep and B1/B2 on 10-Sep are identical (a tie); A3↔B3 on 20-Sep is a clear pair.
    const r = reconcile(
      T([[d(2026, 9, 10), 500], [d(2026, 9, 10), 500], [d(2026, 9, 20), 500]]),
      T([[d(2026, 9, 10), 500], [d(2026, 9, 10), 500], [d(2026, 9, 20), 500]]),
      cfg
    )
    expect(r.pairs.map((p) => [p.tier, p.aIds, p.bIds, p.flags])).toEqual([
      ['matched', ['A:r4'], ['B:r4'], []],
      ['doubtful', ['A:r2', 'A:r3'], ['B:r2', 'B:r3'], ['multiple-candidates']]
    ])
  })
})

describe('negative values in a Credit column', () => {
  const layout = { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' } as const
  it('reads |debit| − |credit|, so a credit written as −500 stays a credit', () => {
    expect(signedAmount({ Debit: null, Credit: -500 }, layout)).toBe(-500)
    expect(signedAmount({ Debit: null, Credit: '(500.00)' }, layout)).toBe(-500)
    expect(signedAmount({ Debit: -500, Credit: null }, layout)).toBe(500)
    expect(signedAmount({ Debit: null, Credit: 500 }, layout)).toBe(-500)
    // An explicit marker inside the cell still wins.
    expect(signedAmount({ Debit: null, Credit: '500.00 DR' }, layout)).toBe(500)
    expect(signedAmount({ Debit: '500.00 CR', Credit: null }, layout)).toBe(-500)
  })
  it('detectNegativeCreditColumn reports negative and mixed credit columns', () => {
    const neg = table(['Debit', 'Credit'], [[100, null], [null, -50], [null, -20]])
    expect(detectNegativeCreditColumn(neg, layout)).toEqual({ column: 'Credit', negative: 2, positive: 0, mixed: false })
    const mixed = table(['Debit', 'Credit'], [[null, -50], [null, 20]])
    expect(detectNegativeCreditColumn(mixed, layout)).toEqual({ column: 'Credit', negative: 1, positive: 1, mixed: true })
    expect(detectNegativeCreditColumn(table(['Debit', 'Credit'], [[null, 20]]), layout)).toBeNull()
    expect(detectNegativeCreditColumn(neg, { kind: 'signed', column: 'Debit' })).toBeNull()
  })
})

describe('date order', () => {
  const keys = [refKey(), dateKey(3)]
  const A = table(['Date', 'Ref'], [['03/04/2026', 'R1']])

  it('buildLines honours dateOrderA / dateOrderB, falling back to detection and then DMY', () => {
    expect(buildLines(A, 'A', config(keys))[0].date?.getMonth()).toBe(3) // ambiguous → DMY: 3 April
    expect(buildLines(A, 'A', config(keys, { dateOrderA: 'MDY' }))[0].date?.getMonth()).toBe(2) // 4 March
    expect(buildLines(A, 'B', config(keys, { dateOrderB: 'MDY' }))[0].date?.getMonth()).toBe(2)
    expect(buildLines(A, 'B', config(keys, { dateOrderA: 'MDY' }))[0].date?.getMonth()).toBe(3)
  })

  it('detects MDY from evidence beyond the first 2,000 rows of a date-sorted file', () => {
    const rows: CellValue[][] = []
    for (let k = 0; k < 3000; k++) rows.push([`01/${String(1 + Math.floor((k * 12) / 3000)).padStart(2, '0')}/2026`, `R${k}`])
    rows.push(['01/25/2026', 'LATE']) // only this row proves month-first
    const t = table(['Date', 'Ref'], rows)
    const orders = detectConfigDateOrders(t, A, config(keys))
    expect(orders).toEqual({ a: 'MDY', b: 'ambiguous' })
    const lines = buildLines(t, 'A', config(keys))
    expect(lines[lines.length - 1].date?.getDate()).toBe(25)
    expect(lines[0].date?.getMonth()).toBe(0) // 01/01 → January
  })

  it('without a date key there is nothing to ask', () => {
    expect(detectConfigDateOrders(A, A, config([refKey()]))).toEqual({ a: 'DMY', b: 'DMY' })
  })
})

describe('transposition in the cents digits', () => {
  it('100.12 vs 100.21 is a transposition, not rounding', () => {
    expect(amountFlags(10012, 10021)).toEqual(['transposition'])
    expect(amountFlags(10000, 10009)).toEqual(['rounding']) // divisible by 9 but no swap
    expect(amountFlags(845000, 854000)).toEqual(['transposition'])
  })
  it('the pair reason names the transposition', () => {
    const r = reconcile(table(['Ref', 'Amount'], [['R1', 100.12]]), table(['Ref', 'Amount'], [['R1', 100.21]]), config([refKey(), amountKey()]))
    expect(r.pairs[0].flags).toEqual(['transposition'])
    expect(r.pairs[0].reason).toContain('possible transposition 100.12 vs 100.21')
  })
})

describe('record-count statement check line', () => {
  const emp: MatchKey = { id: 'e', name: 'Emp ID', type: 'id', use: true, columnA: 'Emp', columnB: 'Emp', identifying: true, textRule: 'normalised' }
  const A = table(['Emp'], [['1'], ['2'], ['3']])
  const B = table(['Emp'], [['1'], ['2']])
  const cfg = config([emp], { amountA: undefined, amountB: undefined })

  it('is 0 when every parsed row is accounted for once', () => {
    expect(buildStatement(reconcile(A, B, cfg), metaFor(A, B)).unexplainedDifference).toBe(0)
  })
  it('shows a difference when a line is counted twice or is missing', () => {
    const r = reconcile(A, B, cfg)
    const twice = { ...r, unmatchedA: [...r.unmatchedA, 'A:r2'] } // A:r2 is also in a matched pair
    const st = buildStatement(twice, metaFor(A, B))
    expect(st.lines.find((l) => l.label === 'Count difference (File A)')?.value).toBe(-1)
    expect(st.unexplainedDifference).toBe(1)
    const missing = { ...r, unmatchedA: [] }
    expect(buildStatement(missing, metaFor(A, B)).lines.find((l) => l.label === 'Count difference (File A)')?.value).toBe(1)
    // The parsed row count is the reference, not the engine's own line list.
    const short = metaFor(A, B, { fileA: { name: 'a', sheet: 's', rows: 4 } })
    expect(buildStatement(r, short).unexplainedDifference).toBe(1)
  })
})
