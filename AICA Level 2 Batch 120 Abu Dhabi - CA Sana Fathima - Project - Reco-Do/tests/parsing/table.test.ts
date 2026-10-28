import { describe, expect, it } from 'vitest'
import type { CellValue, RawSheet } from '@shared/contracts'
import { buildColumnNames, parseTable } from '@shared/parsing'
import { d } from './helpers'

const sheet = (rows: CellValue[][], name = 'Sheet1'): RawSheet => ({ name, rows })

describe('buildColumnNames', () => {
  it('names blank headers by position and numbers duplicates', () => {
    expect(buildColumnNames(['Date', 'Debit', null, 'Debit', ' ', 'Debit'], 6)).toEqual([
      'Date', 'Debit', 'Column 3', 'Debit (2)', 'Column 5', 'Debit (3)'
    ])
  })
  it('treats duplicates case-insensitively and avoids collisions with real headers', () => {
    expect(buildColumnNames(['Amount', 'AMOUNT', 'Amount (2)'], 3)).toEqual(['Amount', 'AMOUNT (3)', 'Amount (2)'])
    expect(buildColumnNames(['Column 2', null], 2)).toEqual(['Column 2', 'Column 2 (2)'])
  })
  it('pads to the requested width and formats date headers', () => {
    expect(buildColumnNames([d(2026, 9, 1), 5], 3)).toEqual(['2026-09-01', '5', 'Column 3'])
  })
})

describe('parseTable', () => {
  const bank: CellValue[][] = [
    ['My Bank PJSC', null, null, null, null, null],
    ['Statement Sep 2026', null, null, null, null, null],
    [null, null, null, null, null, null],
    ['Date', 'Description', 'Reference', 'Debit', 'Credit', 'Balance'],
    [d(2026, 9, 1), 'Opening balance', null, null, null, 1000],
    [d(2026, 9, 2), 'CHQ 001', '001', 100, null, 900],
    [null, null, null, null, null, null],
    [d(2026, 9, 3), 'TT IN', 'TT1', null, 250.5, 1150.5],
    ['Date', 'Description', 'Reference', 'Debit', 'Credit', 'Balance'],
    [d(2026, 9, 4), 'POS', 'P1', 50, null, 1100.5],
    [null, 'Sub total', null, 150, 250.5, null],
    [null, null, null, 150, 250.5, null],
    [null, 'Grand Total', null, 150, 250.5, null],
    [d(2026, 9, 30), 'Closing balance', null, null, null, 1100.5]
  ]

  it('uses the detected header and keeps data rows with Excel-based ids', () => {
    const t = parseTable(sheet(bank), { fileName: 'bank.xlsx' })
    expect(t.fileName).toBe('bank.xlsx')
    expect(t.sheetName).toBe('Sheet1')
    expect(t.headerRowIndex).toBe(3)
    expect(t.columns).toEqual(['Date', 'Description', 'Reference', 'Debit', 'Credit', 'Balance'])
    expect(t.rows.map((r) => r.id)).toEqual(['r6', 'r8', 'r10'])
    expect(t.rows[0].sourceRow).toBe(5)
    expect(t.rows[0].values).toEqual({ Date: d(2026, 9, 2), Description: 'CHQ 001', Reference: '001', Debit: 100, Credit: null, Balance: 900 })
  })

  it('lists every excluded row with its reason', () => {
    const t = parseTable(sheet(bank), { fileName: 'bank.xlsx' })
    expect(t.excluded.map((e) => [e.sourceRow, e.reason])).toEqual([
      [4, 'opening-balance'],
      [6, 'blank'],
      [8, 'repeated-header'],
      [10, 'subtotal'],
      [11, 'total'],
      [12, 'total'],
      [13, 'closing-balance']
    ])
    expect(t.excluded[0].values).toHaveLength(6)
    // nothing is dropped silently
    expect(t.rows.length + t.excluded.length).toBe(bank.length - 4)
  })

  it('captures opening and closing balances from the Balance column', () => {
    const t = parseTable(sheet(bank), { fileName: 'bank.xlsx' })
    expect(t.openingBalance).toBe(1000)
    expect(t.closingBalance).toBe(1100.5)
  })

  it('falls back to the last numeric cell when there is no Balance column', () => {
    const rows: CellValue[][] = [
      ['Posting Date', 'Doc No', 'Remarks', 'Debit', 'Credit', 'Cheque No'],
      [d(2026, 9, 1), null, 'Opening Balance', '1,245,678.35', null, null],
      [d(2026, 9, 2), 'BR-1', 'Receipt', 500, null, 'TT1'],
      [d(2026, 9, 30), null, 'Closing Balance', null, '(20.00)', null]
    ]
    const t = parseTable(sheet(rows), { fileName: 'gl.xlsx' })
    expect(t.openingBalance).toBe(1245678.35)
    expect(t.closingBalance).toBe(-20)
    expect(t.rows).toHaveLength(1)
  })

  it('recognises brought / carried forward wording in any text cell', () => {
    const rows: CellValue[][] = [
      ['Date', 'Doc', 'Description', 'Amount', 'Balance'],
      [d(2026, 8, 1), null, 'Balance brought forward', null, 63907.15],
      [d(2026, 8, 2), 'INV-1', 'Invoice', 100, 64007.15],
      [d(2026, 8, 2), 'INV-2', 'Description mentions total later', 50, 64057.15],
      [null, 'Carried forward', null, null, 64057.15]
    ]
    const t = parseTable(sheet(rows), { fileName: 'x.xlsx' })
    expect(t.excluded.map((e) => e.reason)).toEqual(['opening-balance', 'closing-balance'])
    expect(t.openingBalance).toBe(63907.15)
    expect(t.closingBalance).toBe(64057.15)
    expect(t.rows).toHaveLength(2)
  })

  it('keeps dated transactions whose long description merely starts with "Total"', () => {
    const rows: CellValue[][] = [
      ['Date', 'Description', 'Amount'],
      [d(2026, 9, 1), 'Total Energies fuel station Al Quoz branch', 120],
      [d(2026, 9, 2), 'Shop', 10],
      [null, 'TOTAL', 130]
    ]
    const t = parseTable(sheet(rows), { fileName: 'x.csv' })
    expect(t.rows).toHaveLength(2)
    expect(t.excluded.map((e) => e.reason)).toEqual(['total'])
  })

  it('does not treat amount-only rows as totals in tables without dates', () => {
    const rows: CellValue[][] = [
      ['Code', 'Name', 'Debit'],
      ['10001', 'Land', 100],
      [null, null, 50],
      [null, 'Total', 150]
    ]
    const t = parseTable(sheet(rows), { fileName: 'tb.xlsx' })
    expect(t.rows).toHaveLength(2)
    expect(t.excluded.map((e) => e.reason)).toEqual(['total'])
  })

  it('honours an explicit header row and clamps it into range', () => {
    const t = parseTable(sheet(bank), { fileName: 'bank.xlsx', headerRowIndex: 1 })
    expect(t.headerRowIndex).toBe(1)
    expect(t.columns[0]).toBe('Statement Sep 2026')
    expect(t.columns[1]).toBe('Column 2')
    const t2 = parseTable(sheet(bank), { fileName: 'bank.xlsx', headerRowIndex: 999 })
    expect(t2.headerRowIndex).toBe(bank.length - 1)
    expect(t2.rows).toHaveLength(0)
  })

  it('adds columns for data beyond the header and drops trailing empty columns', () => {
    const rows: CellValue[][] = [
      ['Date', 'Amount', null, null],
      [d(2026, 9, 1), 10, 'extra', null],
      [d(2026, 9, 2), 20, null, null]
    ]
    const t = parseTable(sheet(rows), { fileName: 'x.xlsx' })
    expect(t.columns).toEqual(['Date', 'Amount', 'Column 3'])
    expect(t.rows[0].values['Column 3']).toBe('extra')
    expect(t.rows[1].values['Column 3']).toBeNull()
  })

  it('handles duplicate header names', () => {
    const rows: CellValue[][] = [
      ['Date', 'Debit', 'Debit'],
      [d(2026, 9, 1), 1, 2]
    ]
    const t = parseTable(sheet(rows), { fileName: 'x.xlsx' })
    expect(t.columns).toEqual(['Date', 'Debit', 'Debit (2)'])
    expect(t.rows[0].values).toEqual({ Date: d(2026, 9, 1), Debit: 1, 'Debit (2)': 2 })
  })

  it('copes with an empty sheet and ragged rows', () => {
    const empty = parseTable(sheet([]), { fileName: 'e.xlsx' })
    expect(empty.columns).toEqual([])
    expect(empty.rows).toEqual([])
    expect(empty.openingBalance).toBeNull()
    const ragged = parseTable(sheet([['A', 'B', 'C'], ['x'], ['y', 'z', 'w']]), { fileName: 'r.xlsx' })
    expect(ragged.rows[0].values).toEqual({ A: 'x', B: null, C: null })
  })

  it('treats whitespace-only cells as blank', () => {
    const t = parseTable(sheet([['Name', 'Code'], ['  ', ''], ['Ali', 'E1']]), { fileName: 'x.xlsx' })
    expect(t.excluded).toEqual([{ sourceRow: 1, reason: 'blank', values: ['  ', ''] }])
  })
})
