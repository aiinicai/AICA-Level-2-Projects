import { describe, expect, it } from 'vitest'
import type { CellValue } from '@shared/contracts'
import { inferColumnType } from '@shared/parsing'
import { d } from './helpers'

const range = (n: number, f: (i: number) => CellValue): CellValue[] => Array.from({ length: n }, (_, i) => f(i))

describe('inferColumnType', () => {
  it('detects dates from Date cells and date text', () => {
    expect(inferColumnType('Txn Date', range(20, (i) => d(2026, 9, 1 + i)))).toBe('date')
    expect(inferColumnType('When', range(20, (i) => `${String(i + 1).padStart(2, '0')}/09/2026`))).toBe('date')
    expect(inferColumnType('Posting Date', range(20, (i) => 46260 + i))).toBe('date')
  })

  it('does not take numbers in serial range as dates without a date header', () => {
    expect(inferColumnType('Debit', range(20, (i) => 46260 + i))).toBe('amount')
  })

  it('detects amounts from decimals, formatting and money headers', () => {
    expect(inferColumnType('Value', range(20, (i) => i * 10.25 + 0.5))).toBe('amount')
    expect(inferColumnType('Amount', ['4,487.50', '1,937.92 DR', '(2,881.00)', '2,041.61-', 3486.2])).toBe('amount')
    expect(inferColumnType('Basic Salary', range(20, (i) => 3000 + i * 50))).toBe('amount')
    expect(inferColumnType('Debit', [null, null, 100, null, 200])).toBe('amount')
    expect(inferColumnType('Credit', [])).toBe('amount')
  })

  it('detects IDs: codes, IBANs, employee numbers', () => {
    expect(inferColumnType('Emp ID', range(30, (i) => String(102 + i).padStart(5, '0')))).toBe('id')
    expect(inferColumnType('IBAN', range(30, (i) => `AE07026000101245870010${i}`))).toBe('id')
    expect(inferColumnType('Doc No', range(30, (i) => `BR-2609-${String(i).padStart(4, '0')}`))).toBe('id')
    expect(inferColumnType('Employee No', [...range(20, (i) => String(102 + i).padStart(5, '0')), 108, 174])).toBe('id')
    expect(inferColumnType('Account Code', range(30, (i) => String(10001 + i)))).toBe('id')
    expect(inferColumnType('Cheque No', ['004479', 'TT26094310', 'FT2609JEY', '652755191601', '004478'])).toBe('id')
    expect(inferColumnType('Something', range(30, (i) => 128700 + i * 37))).toBe('id')
  })

  it('detects plain numbers (quantities)', () => {
    expect(inferColumnType('Qty', range(30, (i) => (i % 7) + 1))).toBe('number')
    expect(inferColumnType('Cartons', range(30, (i) => i % 4))).toBe('number')
    expect(inferColumnType('Count', range(30, (i) => 1000 + i))).toBe('number')
  })

  it('falls back to text', () => {
    expect(inferColumnType('Description', ['Taxi fare to DXB', 'Hotel - Abu Dhabi', 'Fuel - pool car'])).toBe('text')
    expect(inferColumnType('Status', range(10, () => 'Active'))).toBe('text')
    expect(inferColumnType('Counterparty', range(10, () => 'DPI-AUH'))).toBe('text')
    expect(inferColumnType('Paid By', ['Petty cash', 'Reimbursed', 'Company card'])).toBe('text')
    expect(inferColumnType('Notes', [])).toBe('text')
  })

  it('uses the header when there are no values', () => {
    expect(inferColumnType('Value Date', [])).toBe('date')
    expect(inferColumnType('Invoice No', [null, ''])).toBe('id')
    expect(inferColumnType('Quantity', [])).toBe('number')
  })
})
