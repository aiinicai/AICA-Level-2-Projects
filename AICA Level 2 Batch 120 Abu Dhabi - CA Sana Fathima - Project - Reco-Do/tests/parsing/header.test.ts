import { describe, expect, it } from 'vitest'
import type { CellValue } from '@shared/contracts'
import { detectHeaderRow } from '@shared/parsing'
import { d, loadSample } from './helpers'

const dataRows = (n: number): CellValue[][] =>
  Array.from({ length: n }, (_, i) => [d(2026, 9, 1 + (i % 28)), `Payment ${i}`, `REF${1000 + i}`, 100 + i, null, 5000 - i])

describe('detectHeaderRow (synthetic)', () => {
  it('returns index 0 with zero confidence for an empty sheet', () => {
    expect(detectHeaderRow([])).toEqual({ index: 0, confidence: 0 })
    expect(detectHeaderRow([[null, null], []])).toEqual({ index: 0, confidence: 0 })
  })

  it('finds a header on the first row', () => {
    const rows = [['Date', 'Description', 'Reference', 'Debit', 'Credit', 'Balance'], ...dataRows(20)]
    const r = detectHeaderRow(rows)
    expect(r.index).toBe(0)
    expect(r.confidence).toBeGreaterThan(0.6)
  })

  it('skips title, address and blank rows above the header', () => {
    const rows: CellValue[][] = [
      ['Some Bank PJSC', null, null, null, null, null],
      ['P.O. Box 1, Dubai', null, null, null, null, null],
      ['Account: 123-456', null, 'Currency: AED', null, null, null],
      [null, null, null, null, null, null],
      ['Txn Date', 'Narration', 'Ref No', 'Withdrawals', 'Deposits', 'Balance'],
      ...dataRows(15)
    ]
    expect(detectHeaderRow(rows).index).toBe(4)
  })

  it('prefers the first occurrence when the header repeats on a page break', () => {
    const header = ['Date', 'Description', 'Reference', 'Debit', 'Credit', 'Balance']
    const rows = [header, [d(2026, 9, 1), 'Opening balance', null, null, null, 100], ...dataRows(10), header, ...dataRows(10)]
    expect(detectHeaderRow(rows).index).toBe(0)
  })

  it('handles blank header cells and text-only tables', () => {
    const rows: CellValue[][] = [
      ['Report title'],
      ['Name', 'Department', 'Status', null],
      ['Anil', 'IT', 'Active', null],
      ['Layla', 'Finance', 'Active', null],
      ['Majid', 'Logistics', 'Left', null]
    ]
    expect(detectHeaderRow(rows).index).toBe(1)
  })

  it('only scans the first 30 rows', () => {
    const rows: CellValue[][] = [...Array.from({ length: 35 }, (): CellValue[] => [null]), ['Date', 'Amount'], [d(2026, 1, 1), 5]]
    expect(detectHeaderRow(rows).index).toBeLessThan(30)
  })
})

describe('detectHeaderRow (sample files)', () => {
  const expected: Array<[string, number]> = [
    ['bank/ENBD_Current_Statement_Sep2026.xlsx', 6],
    ['bank/GL_101200_Cash_Sep2026.xlsx', 0],
    ['ar/AlNoor_Trading_SOA.xlsx', 6],
    ['ar/Our_AR_Ledger_AlNoor_Trading.xlsx', 3],
    ['ap/Gulf_Supplies_SOA.xlsx', 5],
    ['ap/Our_AP_Ledger_Gulf_Supplies.xlsx', 3],
    ['general/HR_Employee_Master.xlsx', 1],
    ['general/Intercompany_EntityA_Dubai.xlsx', 0],
    ['general/Intercompany_EntityB_AbuDhabi.xlsx', 3],
    ['general/WPS_Payroll_Register_Sep2026.xlsx', 0],
    ['tools/Statement_Jul2026.xlsx', 4],
    ['tools/Statement_Aug2026.xlsx', 0],
    ['tools/Statement_Sep2026.xlsx', 2],
    ['tools/Messy_Data_for_Cleaner.xlsx', 3],
    ['tools/Sheet_to_print.xlsx', 2]
  ]
  for (const [file, index] of expected) {
    it(`${file} → row ${index + 1}`, () => {
      const wb = loadSample(file)
      const r = detectHeaderRow(wb.sheets[0].rows)
      expect(r.index).toBe(index)
      expect(r.confidence).toBeGreaterThan(0.5)
      expect(r.confidence).toBeLessThanOrEqual(1)
    })
  }
})
