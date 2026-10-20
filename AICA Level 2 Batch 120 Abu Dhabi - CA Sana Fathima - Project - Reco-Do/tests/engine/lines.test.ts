import { describe, expect, it } from 'vitest'
import { buildLines, reconcile, signedAmount } from '@engine/index'
import { amountKey, config, d, dateKey, refKey, table } from './helpers'

describe('amount layouts become one signed number (debit positive)', () => {
  it('signed column: numbers, brackets, trailing minus and CR/DR suffixes', () => {
    const layout = { kind: 'signed', column: 'Amount' } as const
    expect(signedAmount({ Amount: 1234.5 }, layout)).toBe(1234.5)
    expect(signedAmount({ Amount: '(500.00)' }, layout)).toBe(-500)
    expect(signedAmount({ Amount: '750.00-' }, layout)).toBe(-750)
    expect(signedAmount({ Amount: '1,234.50 CR' }, layout)).toBe(-1234.5)
    expect(signedAmount({ Amount: '1,234.50 Dr' }, layout)).toBe(1234.5)
    expect(signedAmount({ Amount: null }, layout)).toBeNull()
  })

  it('debit and credit columns: debit − credit; both blank gives no amount', () => {
    const layout = { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' } as const
    expect(signedAmount({ Debit: '1,000.00', Credit: null }, layout)).toBe(1000)
    expect(signedAmount({ Debit: null, Credit: 250.25 }, layout)).toBe(-250.25)
    expect(signedAmount({ Debit: 0.1, Credit: 0.3 }, layout)).toBe(-0.2)
    expect(signedAmount({ Debit: null, Credit: '' }, layout)).toBeNull()
  })

  it('amount plus Dr/Cr indicator column', () => {
    const layout = { kind: 'amount-indicator', amount: 'Amount', indicator: 'DrCr' } as const
    expect(signedAmount({ Amount: 500, DrCr: 'Dr' }, layout)).toBe(500)
    expect(signedAmount({ Amount: 500, DrCr: 'CR' }, layout)).toBe(-500)
    expect(signedAmount({ Amount: '500.00', DrCr: 'Credit' }, layout)).toBe(-500)
    expect(signedAmount({ Amount: -500, DrCr: 'D' }, layout)).toBe(500)
    expect(signedAmount({ Amount: -75, DrCr: null }, layout)).toBe(-75)
  })
})

describe('buildLines', () => {
  const A = table(['Date', 'Ref', 'Debit', 'Credit'], [[d(2026, 9, 1), 'R1', 100, null], ['02/09/2026', 'R2', null, 40]])
  it('uses ids "A:r2", parses dates and keeps the row values', () => {
    const cfg = config([refKey(), dateKey(), amountKey()], { amountA: { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' } })
    const lines = buildLines(A, 'A', cfg)
    expect(lines.map((l) => l.id)).toEqual(['A:r2', 'A:r3'])
    expect(lines.map((l) => l.amount)).toEqual([100, -40])
    expect(lines[1].date?.getDate()).toBe(2)
    expect(lines[1].date?.getMonth()).toBe(8)
    expect(lines[0].values.Ref).toBe('R1')
  })

  it('side B comparable amount is negated with the inverse sign convention, kept with same sign', () => {
    const B = table(['Ref', 'Amount'], [['R1', -100]])
    const keys = [refKey(), amountKey()]
    const inverse = buildLines(B, 'B', config(keys, { sign: 'inverse' }))
    expect(inverse[0].amount).toBe(-100)
    expect(inverse[0].comparableAmount).toBe(100)
    const same = buildLines(B, 'B', config(keys, { sign: 'same' }))
    expect(same[0].comparableAmount).toBe(-100)
    // Side A is never negated.
    expect(buildLines(B, 'A', config(keys, { sign: 'inverse' }))[0].comparableAmount).toBe(-100)
  })

  it('amount is null when no amount key is used', () => {
    const lines = buildLines(A, 'A', config([refKey()], { amountA: { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' } }))
    expect(lines[0].amount).toBeNull()
    expect(lines[0].comparableAmount).toBeNull()
  })
})

describe('sign conventions in a reconciliation', () => {
  // Bank credit (deposit) = GL debit. Bank file uses Debit/Credit columns; GL uses amount + indicator.
  const bank = table(['Ref', 'Debit', 'Credit'], [['T1', null, 500], ['T2', 120, null]])
  const gl = table(['Ref', 'Amount', 'DrCr'], [['T1', 500, 'Dr'], ['T2', 120, 'Cr']])
  const keys = [refKey(), amountKey()]
  const layouts = {
    amountA: { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' },
    amountB: { kind: 'amount-indicator', amount: 'Amount', indicator: 'DrCr' }
  } as const

  it('inverse sign matches bank credit with GL debit', () => {
    const r = reconcile(bank, gl, config(keys, { ...layouts, sign: 'inverse', moduleId: 'bank' }))
    expect(r.stats.matched).toBe(2)
  })

  it('same sign on the same data leaves only the reference agreeing (Likely)', () => {
    const r = reconcile(bank, gl, config(keys, { ...layouts, sign: 'same', moduleId: 'bank' }))
    expect(r.stats.matched).toBe(0)
    expect(r.stats.likely).toBe(2)
  })
})
