import { describe, expect, it } from 'vitest'
import type { ReconConfig } from '@shared/contracts'
import { addKey, changeKeyType, convertLayout, layoutLabel, missingColumns, parsePrefixes, removeKey, syncAmountKey } from '@/features/wizard/keys'

const base: ReconConfig = {
  moduleId: 'bank',
  sideAName: 'Bank statement',
  sideBName: 'General ledger extract',
  keys: [{ id: 'reference', name: 'Reference', type: 'text', use: true, columnA: 'Ref', columnB: 'Cheque No', identifying: true, textRule: 'normalised' }],
  sign: 'inverse',
  referencePrefixes: ['CHQ'],
  currency: 'AED'
}

describe('match-key edits', () => {
  it('adds and removes keys with unique ids', () => {
    const a = addKey(addKey(base))
    expect(a.keys.map((k) => k.id)).toEqual(['reference', 'key-2', 'key-3'])
    expect(removeKey(a, 'key-2').keys.map((k) => k.id)).toEqual(['reference', 'key-3'])
  })
  it('changing type resets the rule fields to that type', () => {
    const d = changeKeyType(base, 'reference', 'date')
    expect(d.keys[0]).toMatchObject({ type: 'date', identifying: false, dateToleranceDays: 3 })
    expect(d.keys[0].textRule).toBeUndefined()
    const id = changeKeyType(base, 'reference', 'id')
    expect(id.keys[0]).toMatchObject({ type: 'id', identifying: true, textRule: 'normalised' })
    expect(changeKeyType(id, 'reference', 'text').keys[0].identifying).toBe(false)
  })
  it('making a key the Amount key creates signed layouts from its columns', () => {
    const c = changeKeyType({ ...base, keys: [{ ...base.keys[0], columnA: 'Amt', columnB: 'Value' }] }, 'reference', 'amount')
    expect(c.amountA).toEqual({ kind: 'signed', column: 'Amt' })
    expect(c.amountB).toEqual({ kind: 'signed', column: 'Value' })
    expect(c.keys[0].tolerance).toEqual({ mode: 'exact' })
  })
  it('layout conversion keeps the first column', () => {
    expect(convertLayout({ kind: 'signed', column: 'Amount' }, 'debit-credit')).toEqual({ kind: 'debit-credit', debit: 'Amount', credit: '' })
    expect(convertLayout({ kind: 'debit-credit', debit: 'Dr', credit: 'Cr' }, 'signed')).toEqual({ kind: 'signed', column: 'Dr' })
    expect(layoutLabel({ kind: 'amount-indicator', amount: 'Amt', indicator: 'D/C' })).toBe('Amt + D/C')
  })
  it('syncs the amount key label with the layouts', () => {
    const c = syncAmountKey({
      ...base,
      keys: [{ id: 'amount', name: 'Amount', type: 'amount', use: true, columnA: '', columnB: '', identifying: true }],
      amountA: { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' },
      amountB: { kind: 'signed', column: 'Net' }
    })
    expect([c.keys[0].columnA, c.keys[0].columnB]).toEqual(['Debit / Credit', 'Net'])
  })
  it('parses reference prefixes', () => {
    expect(parsePrefixes('chq, FT;  inv  chq')).toEqual(['CHQ', 'FT', 'INV'])
  })
  it('lists columns a saved mapping needs but the files lack', () => {
    const cfg: ReconConfig = {
      ...base,
      keys: [...base.keys, { id: 'amount', name: 'Amount', type: 'amount', use: true, columnA: '', columnB: '', identifying: true }],
      amountA: { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' },
      amountB: { kind: 'signed', column: 'Amount' }
    }
    expect(missingColumns(cfg, ['Ref', 'Debit', 'Credit'], ['Cheque No', 'Amount'])).toEqual([])
    expect(missingColumns(cfg, ['Ref', 'Debit'], ['Amount'])).toEqual(['Cheque No', 'Credit'])
  })
})
