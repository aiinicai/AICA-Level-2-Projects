import ExcelJS from 'exceljs'
import { beforeAll, describe, expect, it } from 'vitest'
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs'
import type { PdfJsLib } from '@tools/common'
import { extractPdf } from '@tools/pdf-to-excel'
import {
  columnSimilarity,
  loadMergeSources,
  mappingFromRecipe,
  mergeSources,
  mergeToWorkbook,
  moveOutputColumn,
  recipeFromMapping,
  renameOutputColumn,
  setColumnTarget,
  sourcesFromWorkbook,
  suggestMapping,
  type MergeSource
} from '@tools/merge-files'
import { cents, sample } from './helpers'

const FILES = ['Statement_Jul2026.xlsx', 'Statement_Aug2026.xlsx', 'Statement_Sep2026.xlsx']

describe('Merge Files: column similarity', () => {
  it('aligns synonyms and keeps debit and credit apart', () => {
    expect(columnSimilarity('Txn Date', 'Transaction Date')).toBeGreaterThan(0.85)
    expect(columnSimilarity('Txn Date', 'Date')).toBeGreaterThan(0.85)
    expect(columnSimilarity('Debit', 'Withdrawal')).toBeGreaterThan(0.85)
    expect(columnSimilarity('Debit', 'Debit (AED)')).toBeGreaterThan(columnSimilarity('Debit', 'Withdrawal'))
    expect(columnSimilarity('Debit', 'Deposit')).toBe(0)
    expect(columnSimilarity('Withdrawal', 'Credit (AED)')).toBe(0)
    expect(columnSimilarity('Narration', 'Ref No')).toBe(0)
    expect(columnSimilarity('Balance', 'Running Balance')).toBeGreaterThan(0.85)
    expect(columnSimilarity('Txn Date', 'Value Date')).toBe(0)
  })
})

describe('Merge Files: three monthly statements', () => {
  let sources: MergeSource[]
  beforeAll(async () => {
    sources = await loadMergeSources(FILES.map((name) => ({ name, data: sample(name) })))
  })

  it('detects each header row and reads the transactions', () => {
    expect(sources.map((s) => s.headerRow)).toEqual([5, 1, 3])
    expect(sources.map((s) => s.rows.length)).toEqual([44, 51, 47])
  })

  it('aligns the different headers into six columns', () => {
    const m = suggestMapping(sources)
    expect(m.columns).toEqual(['Txn Date', 'Narration', 'Reference', 'Debit', 'Credit', 'Balance'])
    expect(m.sources[sources[1].id]).toEqual({
      'Transaction Date': 'Txn Date',
      Description: 'Narration',
      'Ref No': 'Reference',
      Withdrawal: 'Debit',
      Deposit: 'Credit',
      Balance: 'Balance'
    })
    expect(m.sources[sources[2].id]).toEqual({
      Date: 'Txn Date',
      Details: 'Narration',
      'Reference No.': 'Reference',
      'Debit (AED)': 'Debit',
      'Credit (AED)': 'Credit',
      'Running Balance': 'Balance'
    })
  })

  it('merges 142 transaction rows and lists the Aug repeated header and the Sep total', () => {
    const r = mergeSources(sources, { mapping: suggestMapping(sources) })
    expect(r.rows).toHaveLength(142)
    expect(r.summary.map((s) => s.rowsTaken)).toEqual([44, 51, 47])
    const aug = r.excluded.filter((e) => e.fileName === 'Statement_Aug2026.xlsx')
    expect(aug.some((e) => e.reason === 'Repeated header row' && e.location === 'Row 29')).toBe(true)
    const sep = r.excluded.filter((e) => e.fileName === 'Statement_Sep2026.xlsx')
    expect(sep.some((e) => e.reason === 'Total row' && e.text.includes('Total'))).toBe(true)
    // Opening / closing rows are excluded too (and listed).
    expect(r.excluded.filter((e) => e.reason === 'Opening balance row')).toHaveLength(3)
    expect(r.excluded.filter((e) => e.reason === 'Closing balance row')).toHaveLength(3)
    expect(r.columns.map((c) => c.name)).toEqual(['Source file', 'Sheet / Page', 'Txn Date', 'Narration', 'Reference', 'Debit', 'Credit', 'Balance'])
    expect(r.columns.map((c) => c.type).slice(2)).toEqual(['date', 'text', 'id', 'amount', 'amount', 'amount'])
    const first = r.rows[0].values
    expect(first[0]).toBe('Statement_Jul2026.xlsx')
    expect(first[1]).toBe('Jul 2026')
    expect(first[2]).toBeInstanceOf(Date)
    // Balances run on: last July row is 497,147.20, last row of the merge is September's closing 355,331.29.
    expect(cents(r.rows[43].values[7])).toBe(49714720)
    expect(cents(r.rows[141].values[7])).toBe(35533129)
    // Debit + credit totals of September match its Total row.
    const sepRows = r.rows.filter((x) => x.sourceId === sources[2].id)
    const sum = (c: number): number => sepRows.reduce((n, x) => n + (typeof x.values[c] === 'number' ? Math.round((x.values[c] as number) * 100) : 0), 0)
    expect(sum(5)).toBe(31311836)
    expect(sum(6)).toBe(35317336)
  })

  it('sorts by a date column (descending) and keeps file order for ties', () => {
    const r = mergeSources(sources, { mapping: suggestMapping(sources), sortBy: 'Txn Date', sortDirection: 'desc' })
    const times = r.rows.map((x) => (x.values[2] as Date).getTime())
    for (let i = 1; i < times.length; i++) expect(times[i]).toBeLessThanOrEqual(times[i - 1])
    expect(r.unsortedRows).toBe(0)
  })

  it('lets the user keep a column separate, drop one, rename and reorder', () => {
    let m = suggestMapping(sources)
    m = setColumnTarget(m, sources[1].id, 'Ref No', { separate: true })
    expect(m.columns).toContain('Ref No')
    m = setColumnTarget(m, sources[2].id, 'Running Balance', null)
    m = renameOutputColumn(m, 'Txn Date', 'Date')
    m = moveOutputColumn(m, 'Balance', -1)
    expect(m.columns.slice(0, 2)).toEqual(['Date', 'Narration'])
    expect(() => renameOutputColumn(m, 'Narration', 'date')).toThrow(/already a column/)
    const r = mergeSources(sources, { mapping: m, addSourceColumns: false })
    const refNo = r.columns.findIndex((c) => c.name === 'Ref No')
    const reference = r.columns.findIndex((c) => c.name === 'Reference')
    const augRow = r.rows.find((x) => x.sourceId === sources[1].id)!
    expect(augRow.values[refNo]).toBe('DR26080001')
    expect(augRow.values[reference]).toBeNull()
    const sepRow = r.rows.find((x) => x.sourceId === sources[2].id)!
    expect(sepRow.values[r.columns.findIndex((c) => c.name === 'Balance')]).toBeNull()
    expect(r.summary[2].droppedColumns).toEqual(['Running Balance'])
    // Mapping a column onto a target another column of the same file uses moves that one out.
    const back = setColumnTarget(m, sources[1].id, 'Ref No', 'Reference')
    expect(back.columns).not.toContain('Ref No')
  })

  it('re-applies a recipe to next month by header name', () => {
    let m = suggestMapping(sources)
    m = renameOutputColumn(m, 'Narration', 'Description')
    m = setColumnTarget(m, sources[0].id, 'Balance', null)
    m = setColumnTarget(m, sources[1].id, 'Balance', null)
    m = setColumnTarget(m, sources[2].id, 'Running Balance', null)
    const recipe = recipeFromMapping(m, sources, { sortBy: 'Txn Date', sortDirection: 'asc', addSourceColumns: true, convertValues: true })
    expect(recipe.headerMap['running balance']).toBeNull()
    const next = sourcesFromWorkbook(sample('Statement_Sep2026.xlsx'), 'Statement_Sep2026.xlsx')
    const again = mappingFromRecipe(next, recipe)
    expect(again.columns).toEqual(['Txn Date', 'Description', 'Reference', 'Debit', 'Credit'])
    expect(again.sources[next[0].id]['Details']).toBe('Description')
    expect(again.sources[next[0].id]['Running Balance']).toBeNull()
  })

  it('writes a formatted workbook', async () => {
    const r = mergeSources(sources, { mapping: suggestMapping(sources), sortBy: 'Txn Date' })
    const bytes = await mergeToWorkbook(r)
    const wb = new ExcelJS.Workbook()
    await wb.xlsx.load(bytes.buffer as ArrayBuffer)
    expect(wb.worksheets.map((w) => w.name)).toEqual(['Merged', 'Summary', 'Excluded rows'])
    const ws = wb.getWorksheet('Merged')!
    expect(ws.rowCount).toBe(143)
    expect(ws.getCell('A1').font?.bold).toBe(true)
    expect(ws.views[0]).toMatchObject({ state: 'frozen', ySplit: 1 })
    expect(ws.autoFilter).toBeTruthy()
    expect(ws.getCell('C2').numFmt).toBe('dd-mmm-yyyy')
    expect(ws.getCell('C2').value).toBeInstanceOf(Date)
    const debitCol = 6
    const numbered = ws.getColumn(debitCol).values.filter((v) => typeof v === 'number')
    expect(numbered.length).toBeGreaterThan(40)
    expect(ws.getCell(2, 8).numFmt).toBe('#,##0.00')
    const excl = wb.getWorksheet('Excluded rows')!
    expect(excl.rowCount).toBe(r.excluded.length + 1)
  })

  it('refuses a damaged file with a plain-English message', () => {
    const bad = new TextEncoder().encode('not a spreadsheet at all').buffer as ArrayBuffer
    expect(() => sourcesFromWorkbook(bad, 'broken.xlsx')).toThrow(/broken\.xlsx/)
  })
})

describe('Merge Files: PDF input via the PDF → Excel engine', () => {
  it('merges a PDF table with Excel statements', async () => {
    const lib = pdfjs as unknown as PdfJsLib
    const sources = await loadMergeSources(
      [
        { name: 'Bank_Statement_6_pages_digital.pdf', data: sample('Bank_Statement_6_pages_digital.pdf') },
        { name: 'Statement_Sep2026.xlsx', data: sample('Statement_Sep2026.xlsx') }
      ],
      { extractPdf: (data, fileName, signal) => extractPdf(data, { pdfjs: lib, fileName }, undefined, signal) }
    )
    expect(sources[0].kind).toBe('pdf')
    const m = suggestMapping(sources)
    const r = mergeSources(sources, { mapping: m })
    const pdfRows = r.rows.filter((x) => x.sourceId === sources[0].id)
    expect(pdfRows.length).toBeGreaterThanOrEqual(220)
    expect(pdfRows[0].values[1]).toMatch(/^Page \d$/)
    // Withdrawals / Deposits line up with Debit (AED) / Credit (AED).
    expect(m.sources[sources[1].id]['Debit (AED)']).toBe(m.sources[sources[0].id]['Withdrawals'])
    expect(m.sources[sources[1].id]['Credit (AED)']).toBe(m.sources[sources[0].id]['Deposits'])
  })
})
