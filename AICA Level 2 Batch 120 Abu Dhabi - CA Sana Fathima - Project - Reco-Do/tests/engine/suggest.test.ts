import { describe, expect, it } from 'vitest'
import { detectAmountLayout, detectSignMismatch, previewFirstPair, suggestKeys } from '@engine/index'
import { amountKey, config, d, dateKey, refKey, table } from './helpers'

describe('amount layout detection', () => {
  it('debit/credit columns (balance ignored)', () => {
    const t = table(['Date', 'Narration', 'Debit (AED)', 'Credit (AED)', 'Balance'], [[d(2026, 9, 1), 'x', 10.5, null, 100.25], [d(2026, 9, 2), 'y', null, 20.75, 121]])
    expect(detectAmountLayout(t)).toEqual({ kind: 'debit-credit', debit: 'Debit (AED)', credit: 'Credit (AED)' })
  })
  it('amount plus Dr/Cr indicator', () => {
    const t = table(['Date', 'Amount', 'Dr/Cr'], [[d(2026, 9, 1), 10.5, 'Dr'], [d(2026, 9, 2), 20.25, 'Cr'], [d(2026, 9, 3), 5.5, 'CR']])
    expect(detectAmountLayout(t)).toEqual({ kind: 'amount-indicator', amount: 'Amount', indicator: 'Dr/Cr' })
  })
  it('one signed column', () => {
    const t = table(['Date', 'Amount (AED)'], [[d(2026, 9, 1), 10.5], [d(2026, 9, 2), -20.25]])
    expect(detectAmountLayout(t)).toEqual({ kind: 'signed', column: 'Amount (AED)' })
  })
})

describe('suggestKeys', () => {
  it('Bank/AR/AP default to Reference + Date + Amount with the module date tolerance', () => {
    const A = table(['Txn Date', 'Reference No', 'Debit', 'Credit'], [[d(2026, 9, 1), 'CHQ 0045', 10.5, null], [d(2026, 9, 2), 'FT9', null, 7.25]])
    const B = table(['Posting Date', 'Remarks', 'Doc No', 'Debit', 'Credit'], [[d(2026, 9, 1), 'paid', '45', null, 10.5], [d(2026, 9, 2), 'rcpt', 'FT9', 7.25, null]])
    const s = suggestKeys('ar', A, B)
    expect(s.keys.map((k) => [k.id, k.columnA, k.columnB])).toEqual([
      ['reference', 'Reference No', 'Doc No'],
      ['date', 'Txn Date', 'Posting Date'],
      ['amount', 'Debit / Credit', 'Debit / Credit']
    ])
    expect(s.keys[0]).toMatchObject({ type: 'text', identifying: true, textRule: 'normalised' })
    expect(s.keys[1].dateToleranceDays).toBe(7)
  })
  it('General proposes pairs by name and overlap; amount optional', () => {
    const A = table(['Emp ID', 'Employee Name', 'Join Date'], [['00101', 'Ali Khan', d(2020, 1, 1)], ['00102', 'Sara Ali', d(2021, 2, 2)], ['00103', 'Omar', d(2022, 3, 3)]])
    const B = table(['Employee No', 'Name', 'Pay Date'], [[101, 'Ali Khan', d(2026, 9, 28)], [102, 'Sara Ali', d(2026, 9, 28)], [103, 'Omar', d(2026, 9, 28)]])
    const s = suggestKeys('general', A, B)
    const used = s.keys.filter((k) => k.use).map((k) => [k.columnA, k.columnB])
    expect(used).toContainEqual(['Emp ID', 'Employee No'])
    expect(used).toContainEqual(['Employee Name', 'Name'])
    expect(used).not.toContainEqual(['Join Date', 'Pay Date'])
    expect(s.amountA).toBeUndefined()
  })
})

describe('sign mismatch and preview', () => {
  const A = table(['Ref', 'Amount'], [['R1', 100], ['R2', -50], ['R3', 75], ['R4', 20], ['R5', 30]])
  const B = table(['Ref', 'Amount'], [['R1', -100], ['R2', 50], ['R3', -75], ['R4', -20], ['R5', 30]])
  it('warns when more than 80% of amounts only match with the opposite sign', () => {
    expect(detectSignMismatch(A, B, config([refKey(), amountKey()], { sign: 'same' }))).toEqual({ opposite: 4, same: 1, warn: false })
    const B2 = table(['Ref', 'Amount'], [['R1', -100], ['R2', 50], ['R3', -75], ['R4', -20], ['R5', -30]])
    expect(detectSignMismatch(A, B2, config([refKey(), amountKey()], { sign: 'same' }))).toEqual({ opposite: 5, same: 0, warn: true })
    expect(detectSignMismatch(A, B2, config([refKey(), amountKey()], { sign: 'inverse' })).warn).toBe(false)
  })
  it('previewFirstPair finds the first pair through the reference', () => {
    const p = previewFirstPair(A, B, config([refKey(), dateKey(3, 'Ref', 'Ref', { use: false }), amountKey()], { sign: 'same' }))
    expect(p?.a.id).toBe('A:r2')
    expect(p?.b.id).toBe('B:r2')
    expect(p?.b.comparableAmount).toBe(-100)
    expect(previewFirstPair(A, B, config([dateKey(3, 'Ref', 'Ref')]))).toBeNull()
  })
})
