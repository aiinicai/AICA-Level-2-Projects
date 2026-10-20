// Regression tests for the parsing review findings (P1, P5, P12, Q3, Q5, Q12, Q13, Q14).
import { describe, expect, it } from 'vitest'
import type { CellValue, RawSheet } from '@shared/contracts'
import {
  detectDecimalSeparator,
  detectHeaderRow,
  NO_HEADER_ROW,
  parseAmount,
  parseCsv,
  parseTable,
  readWorkbook
} from '@shared/parsing'
import { d, textBuffer, toArrayBuffer } from './helpers'

const sheet = (rows: CellValue[][]): RawSheet => ({ name: 'S', rows })

describe('P1: keyword rows vs real transactions', () => {
  it('keeps dated transactions whose description only starts with Total / Opening / Balance b/f', () => {
    const rows: CellValue[][] = [
      ['ABC Bank Statement', null, null, null],
      [null, null, null, null],
      ['Date', 'Description', 'Amount', 'Balance'],
      ['01/09/2026', 'Opening Balance', null, '1000.00'],
      ['02/09/2026', 'TOTAL UAE FUEL STATION', '-150.00', '850.00'],
      ['03/09/2026', 'Opening balance adjustment JV12', '25.00', '875.00'],
      ['04/09/2026', 'Balance b/f correction', '10.00', '885.00'],
      ['05/09/2026', 'Closing fees', '-5.00', '880.00'],
      ['06/09/2026', 'Total Oil UAE - card 1234', '-80.00', '800.00'],
      ['07/09/2026', 'Brought forward correction', '10.00', '810.00'],
      [null, 'Total', '-190.00', null]
    ]
    const t = parseTable(sheet(rows), { fileName: 'a.csv' })
    expect(t.rows.map((r) => r.values.Description)).toEqual([
      'TOTAL UAE FUEL STATION',
      'Opening balance adjustment JV12',
      'Balance b/f correction',
      'Closing fees',
      'Total Oil UAE - card 1234',
      'Brought forward correction'
    ])
    expect(t.excluded.map((e) => e.reason)).toEqual(['opening-balance', 'total'])
    expect(t.openingBalance).toBe(1000)
  })

  it('still excludes whole-label summary rows that carry a date and an amount', () => {
    const rows: CellValue[][] = [
      ['Date', 'Description', 'Debit', 'Credit'],
      [d(2026, 9, 1), 'Opening balance as at 01/09/2026', 5000, null],
      [d(2026, 9, 2), 'Payment', 100, null],
      [d(2026, 9, 30), 'Total', 5100, null],
      [d(2026, 9, 30), 'Closing Balance', 5000, null]
    ]
    const t = parseTable(sheet(rows), { fileName: 'gl.xlsx' })
    expect(t.rows).toHaveLength(1)
    expect(t.excluded.map((e) => e.reason)).toEqual(['opening-balance', 'total', 'closing-balance'])
  })
})

describe('Q3: opening / closing balances apply CR/DR and Debit / Credit', () => {
  it('reads "Dr" balances against a Cr-balance statement as negative', () => {
    const rows: CellValue[][] = [
      ['Date', 'Description', 'Debit', 'Credit', 'Balance'],
      ['01/09/2026', 'Opening Balance', null, null, '12,345.00 Dr'],
      ['02/09/2026', 'Deposit', null, '20,000.00', '7,655.00 Cr'],
      ['03/09/2026', 'Deposit', null, '1,000.00', '8,655.00 Cr'],
      ['30/09/2026', 'Closing Balance', null, null, '8,655.00 Cr']
    ]
    const t = parseTable(sheet(rows), { fileName: 'bank.csv' })
    expect(t.openingBalance).toBe(-12345)
    expect(t.closingBalance).toBe(8655)
  })

  it('reads Dr as positive and Cr as negative when the balance column has no usual marker', () => {
    const rows: CellValue[][] = [
      ['Date', 'Description', 'Amount', 'Balance'],
      ['01/09/2026', 'Opening Balance', null, '500.00 Cr'],
      ['02/09/2026', 'Sale', '100.00', null],
      ['30/09/2026', 'Closing Balance', null, '400.00 Dr']
    ]
    const t = parseTable(sheet(rows), { fileName: 'x.csv' })
    expect(t.openingBalance).toBe(-500)
    expect(t.closingBalance).toBe(400)
  })

  it('uses Debit − Credit when there is no Balance column', () => {
    const gl: CellValue[][] = [
      ['Date', 'Description', 'Debit', 'Credit'],
      ['01/09/2026', 'Opening balance', null, 5000],
      ['02/09/2026', 'Pay', 100, null],
      ['30/09/2026', 'Closing balance', 4900, null]
    ]
    const t = parseTable(sheet(gl), { fileName: 'gl.xlsx' })
    expect(t.openingBalance).toBe(-5000)
    expect(t.closingBalance).toBe(4900)
  })
})

describe('Q12: two-row headers', () => {
  const multi: CellValue[][] = [
    ['Txn', 'Value', 'Description', 'Amount', null, 'Balance'],
    ['Date', 'Date', null, 'Debit', 'Credit', null],
    ['01/09/2026', '01/09/2026', 'Pay', 10, null, 90],
    ['02/09/2026', '02/09/2026', 'Pay2', null, 20, 110]
  ]
  it('merges the label row below the header into the column names', () => {
    const t = parseTable(sheet(multi), { fileName: 'x' })
    expect(t.columns).toEqual(['Txn Date', 'Value Date', 'Description', 'Amount Debit', 'Amount Credit', 'Balance'])
    expect(t.headerRowIndex).toBe(1)
    expect(t.rows).toHaveLength(2)
    expect(t.rows[1].values['Amount Credit']).toBe(20)
  })
  it('gives the same table whichever of the two rows is chosen as the header', () => {
    expect(detectHeaderRow(multi).index).toBe(1)
    for (const h of [0, 1]) {
      const t = parseTable(sheet(multi), { fileName: 'x', headerRowIndex: h })
      expect(t.headerRowIndex).toBe(1)
      expect(t.columns[0]).toBe('Txn Date')
    }
  })
  it('does not merge a title row or a text data row into a one-row header', () => {
    const titled: CellValue[][] = [
      ['Statement of Account', 'Period September'],
      ['Date', 'Description', 'Amount'],
      ['01/09/2026', 'Pay', 10],
      ['02/09/2026', 'Pay2', 20]
    ]
    const t = parseTable(sheet(titled), { fileName: 'x' })
    expect(t.columns).toEqual(['Date', 'Description', 'Amount'])
    const names: CellValue[][] = [
      ['Name', 'Department'],
      ['Ali Hassan', 'Finance'],
      ['Sara Khan', 'Sales']
    ]
    expect(parseTable(sheet(names), { fileName: 'x' }).rows).toHaveLength(2)
  })
})

describe('Q13: files without a header row', () => {
  const nohdr: CellValue[][] = [
    ['01/09/2026', 'Pay', 10, 90],
    ['02/09/2026', 'Pay2', 20, 110],
    ['03/09/2026', 'Pay3', 30, 140]
  ]
  it('reports headerRowIndex -1, generates "Column N" names and keeps the first transaction', () => {
    expect(detectHeaderRow(nohdr).index).toBe(NO_HEADER_ROW)
    const t = parseTable(sheet(nohdr), { fileName: 'x' })
    expect(t.headerRowIndex).toBe(-1)
    expect(t.columns).toEqual(['Column 1', 'Column 2', 'Column 3', 'Column 4'])
    expect(t.rows).toHaveLength(3)
    expect(t.rows[0]).toMatchObject({ id: 'r1', sourceRow: 0 })
    expect(t.rows[0].values['Column 2']).toBe('Pay')
  })
  it('accepts an explicit headerRowIndex of -1', () => {
    const rows: CellValue[][] = [['Date', 'Amount'], ['01/09/2026', 5]]
    const t = parseTable(sheet(rows), { fileName: 'x', headerRowIndex: -1 })
    expect(t.headerRowIndex).toBe(-1)
    expect(t.rows).toHaveLength(2)
  })
  it('keeps headers made of years or month names', () => {
    expect(detectHeaderRow([['Report', null, null], ['Code', '2025', '2026'], ['A1', 100, 200], ['A2', 300, 400]]).index).toBe(1)
    expect(detectHeaderRow([['Account', 'Name', 'Jan-26', 'Feb-26'], ['1001', 'Cash', 100, 200], ['1002', 'Bank', 300, 400]]).index).toBe(0)
  })
})

describe('Q14: per-column decimal separator', () => {
  it('detects the separator from unambiguous values', () => {
    expect(detectDecimalSeparator(['1.234,56', '1.234', '12,50'])).toBe(',')
    expect(detectDecimalSeparator(['1,234.56', '1,234', '0.75'])).toBe('.')
    expect(detectDecimalSeparator(['1,234', '1.234'])).toBeNull()
  })
  it('reads "1.234" as 1234 when the column uses a decimal comma, and as before otherwise', () => {
    expect(parseAmount('1.234', { decimal: ',' })?.value).toBe(1234)
    expect(parseAmount('1.234,56', { decimal: ',' })?.value).toBe(1234.56)
    expect(parseAmount('12,5', { decimal: ',' })?.value).toBe(12.5)
    expect(parseAmount('1,234', { decimal: '.' })?.value).toBe(1234)
    expect(parseAmount('12,5', { decimal: '.' })).toBeNull()
    expect(parseAmount('(1.234,00) CR', { decimal: ',' })).toEqual({ value: -1234, indicator: 'CR' })
    expect(parseAmount('1.234')?.value).toBe(1.234)
  })
})

describe('Q5: phone numbers are not amounts', () => {
  it('rejects +-prefixed and oddly spaced digit groups, keeps thousands spacing', () => {
    expect(parseAmount('+971 50 123 4567')).toBeNull()
    expect(parseAmount('050 123 4567')).toBeNull()
    expect(parseAmount('4111 1111 1111 1111')).toBeNull()
    expect(parseAmount('100 000')?.value).toBe(100000)
    expect(parseAmount('1 234,56')?.value).toBe(1234.56)
    expect(parseAmount("1'234.50")?.value).toBe(1234.5)
    expect(parseAmount('+500.00')?.value).toBe(500)
  })
})

describe('P5: long numerals in CSV stay exact', () => {
  it('keeps numerals with more than 15 significant digits as text', () => {
    const wb = readWorkbook(textBuffer('Ref,Amount\n1234567890123456,1.10\n12345678901234567,2\n123456789012345,3\n'), 'a.csv')
    const rows = wb.sheets[0].rows
    expect(rows[1][0]).toBe('1234567890123456')
    expect(rows[2][0]).toBe('12345678901234567')
    expect(rows[3][0]).toBe(123456789012345)
    expect(rows[1][1]).toBe(1.1)
  })
})

describe('P12: UTF-16 without BOM and unclosed quotes', () => {
  const s = 'Date,Amount\n03/09/2026,5\n'
  it('decodes UTF-16 LE and BE without a byte-order mark', () => {
    const le = new Uint8Array(s.length * 2)
    const be = new Uint8Array(s.length * 2)
    for (let i = 0; i < s.length; i++) {
      le[2 * i] = s.charCodeAt(i)
      be[2 * i + 1] = s.charCodeAt(i)
    }
    for (const bytes of [le, be]) {
      const wb = readWorkbook(toArrayBuffer(bytes), 'u.csv')
      expect(wb.sheets[0].rows).toEqual([['Date', 'Amount'], ['03/09/2026', 5]])
    }
  })
  it('reads an unclosed opening quote as a literal character and warns', () => {
    const wb = readWorkbook(textBuffer('a,b\n"x,1\n2,3\n4,5\n'), 'u.csv')
    expect(wb.sheets[0].rows).toEqual([['a', 'b'], ['"x', 1], [2, 3], [4, 5]])
    expect(wb.warnings).toHaveLength(1)
    expect(wb.warnings?.[0]).toMatch(/Line 2/)
    const lines: number[] = []
    expect(parseCsv('a\n"b\nc\n', ',', (l) => lines.push(l))).toEqual([['a'], ['"b'], ['c']])
    expect(lines).toEqual([2])
  })
  it('has no warnings for well-formed files', () => {
    expect(readWorkbook(textBuffer('a,b\n"x, y",1\n'), 'ok.csv').warnings).toBeUndefined()
  })
})
