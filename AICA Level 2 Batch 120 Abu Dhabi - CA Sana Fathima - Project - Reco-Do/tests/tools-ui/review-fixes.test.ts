// Regression tests for the Data Cleaner / Merge Files / tool-screen review findings (Q5, Q10, Q11, Q13, Q14, Q16, Q24, P5).
import ExcelJS from 'exceljs'
import { describe, expect, it } from 'vitest'
import type { CellValue, RawSheet } from '@shared/contracts'
import { countOrConvertNumbers, countOrSplitAmount, prepareSheet, runCleaner, suggestOptions, type CleanTable } from '@tools/data-cleaner'
import { columnSimilarity, headersConflict, suggestMapping } from '@tools/merge-files/align'
import { newWorkbook, workbookBytes, writeTableSheet } from '@tools/merge-files/excel'
import { ToolError } from '@tools/common'
import { cellText, isNumericCell } from '../../src/renderer/src/features/tools/shared/cellText'
import { GENERIC_TOOL_ERROR, toolErrorInfo } from '../../src/renderer/src/features/tools/shared/useToolTask'

const sheet = (rows: CellValue[][]): RawSheet => ({ name: 'S', rows })

function cleanTable(columns: string[], rows: CellValue[][]): CleanTable {
  return {
    fileName: 'x.xlsx',
    sheetName: 'S',
    headerRowIndex: 0,
    columns,
    rows: rows.map((r, i) => ({ sourceRow: i + 1, junk: null, cells: r.map((v) => ({ value: v, original: v })) })),
    removed: []
  }
}

describe('Q5: Data Cleaner leaves codes and phone numbers alone', () => {
  const rows: CellValue[][] = [
    ['Date', 'Cost Centre', 'Mobile', 'Amount', 'Account No', 'Card', 'Description'],
    ['03/09/2026', '0101', '+971 50 123 4567', '1,234.50', '001234567890', '4111 1111 1111 1111', 'Fuel'],
    ['04/09/2026', '0102', '+971 50 123 4567', '500.00 CR', '001234567891', '4111 1111 1111 1112', 'Total Energies'],
    ['05/09/2026', '0101', '055 111 2222', '(20.00)', '001234567892', '4111 1111 1111 1113', 'Rent'],
    ['06/09/2026', '0101', '055 111 2222', '30.00', '001234567893', '4111 1111 1111 1114', 'x']
  ]
  it('suggests only the real amount column and never converts codes', () => {
    const p = prepareSheet(sheet(rows), 'm.xlsx')
    const o = suggestOptions(p)
    expect(o.numbers.columns).toEqual(['Amount'])
    const r = runCleaner(p, o)
    expect(r.table.rows.map((row) => row.cells[1].value)).toEqual(['0101', '0102', '0101', '0101'])
    expect(r.table.rows[0].cells[2].value).toBe('+971 50 123 4567')
    expect(r.table.rows.map((row) => row.cells[3].value)).toEqual([1234.5, -500, -20, 30])
  })
  it('does not convert phone numbers even when the column is ticked by hand', () => {
    const t = cleanTable(['Mobile'], [['+971 50 123 4567'], ['055 111 2222']])
    expect(countOrConvertNumbers(t, { enabled: true, columns: ['Mobile'], crNegative: true }, true).count).toBe(0)
    expect(t.rows[0].cells[0].value).toBe('+971 50 123 4567')
  })
})

describe('Q11: combining Debit and Credit keeps precision and text', () => {
  it('keeps 3 decimals (KWD / BHD / OMR) and keeps non-numeric text', () => {
    const t = cleanTable(['Debit', 'Credit'], [['1.234', null], ['n/a', null], [null, 12.345], ['10.5', '0.25']])
    countOrSplitAmount(t, { enabled: true, mode: 'combine', debit: 'Debit', credit: 'Credit', name: 'Amount', positiveIs: 'debit', crNegative: true }, true)
    expect(t.columns).toEqual(['Amount'])
    expect(t.rows.map((r) => r.cells[0].value)).toEqual([1.234, 'n/a', -12.345, 10.25])
  })
})

describe('Q14: text numbers in a decimal-comma column', () => {
  it('reads "1.234" as 1234 when the column also has "1.234,56"', () => {
    const t = cleanTable(['Betrag'], [['1.234,56'], ['1.234'], ['12,50']])
    countOrConvertNumbers(t, { enabled: true, columns: ['Betrag'], crNegative: true }, true)
    expect(t.rows.map((r) => r.cells[0].value)).toEqual([1234.56, 1234, 12.5])
  })
})

describe('Q13: Data Cleaner on a file without a header row', () => {
  it('keeps the first row as data with Column N names', () => {
    const p = prepareSheet(sheet([['01/09/2026', 'Pay', 10.5], ['02/09/2026', 'Pay2', 20.25], ['03/09/2026', 'Pay3', 30.75]]), 'n.csv')
    expect(p.headerRowIndex).toBe(-1)
    expect(p.table.columns).toEqual(['Column 1', 'Column 2', 'Column 3'])
    expect(p.table.rows).toHaveLength(3)
    expect(p.table.rows[0].sourceRow).toBe(0)
  })
})

describe('Q10: Merge Files never stacks opposite or different-currency columns', () => {
  it('scores conflicting headers 0 and keeps them apart in the suggested mapping', () => {
    expect(headersConflict('Amount (USD)', 'Amount (AED)')).toBe(true)
    expect(headersConflict('Closing Balance', 'Opening Balance')).toBe(true)
    expect(headersConflict('Supplier Name', 'Customer Name')).toBe(true)
    expect(columnSimilarity('Amount (USD)', 'Amount (AED)')).toBe(0)
    expect(columnSimilarity('Amount (AED)', 'Amount AED')).toBe(1)
    expect(columnSimilarity('Txn Date', 'Posting Date')).toBeGreaterThan(0.8)
    const mk = (id: string, columns: string[], row: CellValue[]): Parameters<typeof suggestMapping>[0][number] => ({
      id,
      fileIndex: 0,
      fileName: id,
      sheetName: 'S',
      kind: 'sheet',
      columns,
      rows: [{ sheetOrPage: 'S', location: 'R2', values: Object.fromEntries(columns.map((c, i) => [c, row[i]])) }],
      excluded: []
    })
    const m = suggestMapping([
      mk('a', ['Date', 'Customer Name', 'Amount (AED)', 'Opening Balance'], ['03/09/2026', 'ACME', 100, 5]),
      mk('b', ['Date', 'Supplier Name', 'Amount (USD)', 'Closing Balance'], ['04/09/2026', 'Foo', 50, 7])
    ])
    expect(m.sources.b).toEqual({ Date: 'Date', 'Supplier Name': 'Supplier Name', 'Amount (USD)': 'Amount (USD)', 'Closing Balance': 'Closing Balance' })
  })
})

describe('P5: long ID numbers in Merge Files / Data Cleaner output', () => {
  it('writes 12+ digit whole numbers outside amount columns as text, amounts as numbers', async () => {
    const wb = newWorkbook()
    const ws = wb.addWorksheet('S')
    writeTableSheet(ws, [{ name: 'Card', type: 'id' }, { name: 'Amount', type: 'amount' }], [[1234567890123456, 123456789012.5], [4321, 10]])
    const back = new ExcelJS.Workbook()
    const bytes = await workbookBytes(wb)
    await back.xlsx.load(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer)
    const s = back.worksheets[0]
    expect(s.getCell('A2').value).toBe('1234567890123456')
    expect(s.getCell('A3').value).toBe(4321)
    expect(s.getCell('B2').value).toBe(123456789012.5)
  })
})

describe('Q24: Data Cleaner preview formats each column by its type', () => {
  it('shows invoice numbers as written and amounts with two decimals', () => {
    expect(cellText(10045, 'id')).toBe('10045')
    expect(cellText(10045, 'number')).toBe('10045')
    expect(cellText(1234.5, 'amount')).toBe('1,234.50')
    expect(cellText(new Date(2026, 8, 3), 'date')).toBe('03-Sep-2026')
    expect(cellText('ABC', 'text')).toBe('ABC')
    expect(isNumericCell(10045, 'id')).toBe(false)
    expect(isNumericCell(1234.5, 'amount')).toBe(true)
  })
})

describe('Q16: plain-English tool errors', () => {
  it('keeps ToolError and plain messages, replaces technical ones and keeps the detail', () => {
    expect(toolErrorInfo(new ToolError('invalid-pdf', 'This file is not a valid PDF.', 'InvalidPDFException'))).toEqual({
      message: 'This file is not a valid PDF.',
      detail: 'InvalidPDFException'
    })
    expect(toolErrorInfo(new Error('This workbook is password-protected. Remove the password in Excel, save it and try again.')).detail).toBeNull()
    const raw = toolErrorInfo(new TypeError("Cannot read properties of undefined (reading 'rows')"))
    expect(raw.message).toBe(GENERIC_TOOL_ERROR)
    expect(raw.detail).toContain('Cannot read properties of undefined')
    expect(toolErrorInfo(new Error('ENOENT: no such file or directory')).message).toBe(GENERIC_TOOL_ERROR)
  })
})
