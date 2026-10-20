import { describe, expect, it } from 'vitest'
import { decodeText, detectDelimiter, parseCsv, readWorkbook } from '@shared/parsing'
import { d, makeWorkbook, textBuffer, toArrayBuffer } from './helpers'

describe('readWorkbook (.xlsx / .xls)', () => {
  const rows = [
    ['Date', 'Amount', 'ID', 'Note'],
    [d(2026, 9, 3), 1234.5, '00102', '  padded  '],
    [d(2026, 12, 31), -20, '00103', null]
  ]

  for (const bookType of ['xlsx', 'biff8', 'xlsb', 'ods'] as const) {
    it(`reads ${bookType} with local Date cells, numbers and trimmed strings`, () => {
      const wb = readWorkbook(makeWorkbook({ Data: rows, Second: [['Only']] }, bookType), `file.${bookType === 'biff8' ? 'xls' : bookType}`)
      expect(wb.sheets.map((s) => s.name)).toEqual(['Data', 'Second'])
      const r = wb.sheets[0].rows
      expect(r[1][0]).toBeInstanceOf(Date)
      expect(r[1][0]).toEqual(d(2026, 9, 3))
      expect((r[1][0] as Date).getHours()).toBe(0)
      expect(r[2][0]).toEqual(d(2026, 12, 31))
      expect(r[1][1]).toBe(1234.5)
      expect(r[2][1]).toBe(-20)
      expect(r[1][2]).toBe('00102')
      expect(r[1][3]).toBe('padded')
      expect(r[2][3]).toBeNull()
      expect(wb.sheets[1].rows).toEqual([['Only']])
    })
  }

  it('keeps row 0 = Excel row 1 even when the used range starts lower, and pads columns', () => {
    const wb = readWorkbook(makeWorkbook({ S: [[null, null], [null, 'B2'], [null, null, 'C3']] }), 'x.xlsx')
    expect(wb.sheets[0].rows[1][1]).toBe('B2')
    expect(wb.sheets[0].rows[2][2]).toBe('C3')
    expect(wb.sheets[0].rows.every((r) => r.length === 3)).toBe(true)
  })

  it('leaves merged cells null except the top-left one', () => {
    const data = [
      ['Category', 'Item'],
      ['Travel', 'Taxi'],
      ['Travel', 'Hotel'],
      ['Office', 'Toner']
    ]
    const wb = readWorkbook(makeWorkbook({ S: data }, 'xlsx', { S: [{ s: { r: 1, c: 0 }, e: { r: 2, c: 0 } }] }), 'm.xlsx')
    const r = wb.sheets[0].rows
    expect(r[1][0]).toBe('Travel')
    expect(r[2][0]).toBeNull()
    expect(r[3][0]).toBe('Office')
  })

  it('converts booleans to text and drops empty strings', () => {
    const wb = readWorkbook(makeWorkbook({ S: [['Flag', 'Blank'], [true, '   ']] }), 'b.xlsx')
    expect(wb.sheets[0].rows[1]).toEqual(['TRUE', null])
  })

  it('throws plain-English errors for unreadable files', () => {
    expect(() => readWorkbook(new ArrayBuffer(0), 'x.xlsx')).toThrow('This file is empty.')
    expect(() => readWorkbook(textBuffer('%PDF-1.7 ...'), 'x.pdf')).toThrow(/PDF → Excel tool/)
    const broken = new Uint8Array([0x50, 0x4b, 0x03, 0x04, 1, 2, 3, 4, 5, 6, 7, 8])
    expect(() => readWorkbook(toArrayBuffer(broken), 'x.xlsx')).toThrow(/could not be read/)
  })
})

describe('readWorkbook (.csv)', () => {
  it('reads comma CSV, converting plain numbers and ISO / month-name dates', () => {
    const csv = 'Date,Ref,Amount,Code,Text Date\r\n2026-09-03,INV-1,1234.50,00102,03/09/2026\r\n3-Sep-2026,"A, B",-5,7,\r\n'
    const wb = readWorkbook(textBuffer(csv), 'bank export.csv')
    expect(wb.fileName).toBe('bank export.csv')
    expect(wb.sheets).toHaveLength(1)
    expect(wb.sheets[0].name).toBe('bank export')
    expect(wb.sheets[0].rows).toEqual([
      ['Date', 'Ref', 'Amount', 'Code', 'Text Date'],
      [d(2026, 9, 3), 'INV-1', 1234.5, '00102', '03/09/2026'],
      [d(2026, 9, 3), 'A, B', -5, 7, null]
    ])
  })

  it('detects semicolon and tab delimiters', () => {
    const semi = readWorkbook(textBuffer('Date;Amount;Note\n03/09/2026;1.234,50;x\n04/09/2026;12,00;y\n'), 'eu.csv')
    expect(semi.sheets[0].rows[0]).toEqual(['Date', 'Amount', 'Note'])
    expect(semi.sheets[0].rows[1]).toEqual(['03/09/2026', '1.234,50', 'x'])
    const tab = readWorkbook(textBuffer('A\tB\n1\t2\n'), 'x.tsv')
    expect(tab.sheets[0].rows).toEqual([['A', 'B'], [1, 2]])
  })

  it('handles a UTF-8 BOM, quotes, embedded newlines and ragged lines', () => {
    const csv = '﻿Name,Comment\n"Ali ""Junior""","line1\nline2"\nSara\n'
    const wb = readWorkbook(textBuffer(csv), 'q.csv')
    expect(wb.sheets[0].rows).toEqual([
      ['Name', 'Comment'],
      ['Ali "Junior"', 'line1\nline2'],
      ['Sara', null]
    ])
  })

  it('decodes UTF-16 and Windows-1252 text', () => {
    const utf16 = new Uint8Array([0xff, 0xfe, 0x41, 0x00, 0x2c, 0x00, 0x42, 0x00])
    expect(decodeText(utf16)).toBe('A,B')
    const cp1252 = new Uint8Array([0x43, 0x61, 0x66, 0xe9])
    expect(decodeText(cp1252)).toBe('Café')
  })

  it('exposes the delimiter detection and CSV parser', () => {
    expect(detectDelimiter('a,b,c\n1,2,3')).toBe(',')
    expect(detectDelimiter('a;b;c\n1,5;2,5;3')).toBe(';')
    expect(detectDelimiter('a\tb\n1\t2')).toBe('\t')
    expect(detectDelimiter('"x;y",b\n"1;2",3')).toBe(',')
    expect(detectDelimiter('')).toBe(',')
    expect(parseCsv('a,b\r\n1,2', ',')).toEqual([['a', 'b'], ['1', '2']])
  })
})
