import ExcelJS from 'exceljs'
import { beforeAll, describe, expect, it } from 'vitest'
import type { RawSheet } from '@shared/contracts'
import { readWorkbook } from '@shared/parsing'
import {
  changeCase,
  cleanSpaces,
  cleanToWorkbook,
  dateInfo,
  prepareSheet,
  previewCounts,
  runCleaner,
  suggestOptions,
  withDefaults,
  type CleanerOptions,
  type CleanResult,
  type PreparedSheet
} from '@tools/data-cleaner'
import { cents, sample } from './helpers'

const FILE = 'Messy_Data_for_Cleaner.xlsx'

/** Every action off, so each test switches on only what it checks. */
function none(p: PreparedSheet): CleanerOptions {
  const o = suggestOptions(p)
  return {
    removeRows: { ...o.removeRows, enabled: false },
    trim: { enabled: false },
    fillDown: { ...o.fillDown, enabled: false },
    numbers: { ...o.numbers, enabled: false },
    dates: { ...o.dates, enabled: false },
    amount: { ...o.amount, enabled: false },
    textCase: { ...o.textCase, enabled: false },
    duplicates: { ...o.duplicates, enabled: false }
  }
}

function col(r: CleanResult, name: string): number {
  const i = r.table.columns.indexOf(name)
  if (i < 0) throw new Error(`no column ${name}`)
  return i
}

describe('Data Cleaner on Messy_Data_for_Cleaner.xlsx', () => {
  let p: PreparedSheet
  beforeAll(() => {
    const wb = readWorkbook(sample(FILE), FILE)
    p = prepareSheet(wb.sheets[0], FILE)
  })

  it('detects the header on row 4 and suggests the right columns', () => {
    expect(p.headerRowIndex).toBe(3)
    expect(p.table.columns).toEqual(['Category', 'Txn Date', 'Description', 'Ref', 'Amount', 'Paid By'])
    const o = suggestOptions(p)
    expect(o.numbers.columns).toEqual(['Amount'])
    expect(o.dates.columns).toEqual(['Txn Date'])
    expect(o.fillDown.columns).toEqual(['Category'])
    expect(o.duplicates).toEqual({ enabled: true, mode: 'flag' })
  })

  it('removes 4 blank rows, 4 subtotal rows and the TOTAL row, listing each', () => {
    const o = none(p)
    o.removeRows.enabled = true
    const r = runCleaner(p, o)
    expect(r.reports[0]).toMatchObject({ action: 'removeRows', count: 9, unit: 'rows' })
    expect(r.table.rows).toHaveLength(42)
    const by = (reason: string): number => r.table.removed.filter((x) => x.reason === reason).length
    expect([by('blank'), by('subtotal'), by('total')]).toEqual([4, 4, 1])
    expect(r.table.removed.find((x) => x.reason === 'total')?.values).toContain('TOTAL')
    // Only some kinds can be chosen.
    o.removeRows.reasons = ['total']
    expect(runCleaner(p, o).table.rows).toHaveLength(50)
  })

  it('trims extra spaces inside descriptions', () => {
    const o = none(p)
    o.trim.enabled = true
    const r = runCleaner(p, o)
    expect(r.reports[1].count).toBe(7)
    const d = col(r, 'Description')
    expect(r.table.rows[0].cells[d].value).toBe('Taxi fare to DXB airport')
    expect(cleanSpaces('  A4  paper​ (10 boxes)\t')).toBe('A4 paper (10 boxes)')
  })

  it('converts text numbers incl. CR/DR, brackets and trailing minus; total = 18,468.07', () => {
    const o = none(p)
    o.removeRows.enabled = true
    o.numbers.enabled = true
    const r = runCleaner(p, o)
    expect(r.reports[3].count).toBe(37)
    const a = col(r, 'Amount')
    const values = r.table.rows.map((x) => x.cells[a].value)
    expect(values.every((v) => typeof v === 'number')).toBe(true)
    expect(values.reduce<number>((n, v) => n + cents(v), 0)).toBe(1846807)
    const byRef = (ref: string): unknown => r.table.rows.find((x) => x.cells[3].value === ref)?.cells[a].value
    expect(byRef('EXP-03001')).toBe(4487.5) // "4,487.50"
    expect(byRef('EXP-03002')).toBe(1937.92) // "1,937.92 DR"
    expect(byRef('EXP-03003')).toBe(-2483.24) // "2,483.24 CR"
    expect(byRef('EXP-03004')).toBe(-2881) // "(2,881.00)"
    expect(byRef('EXP-03005')).toBe(-2041.61) // "2,041.61-"
    expect(byRef('EXP-03007')).toBe(3791) // " 3,791.00 "
    // DR negative instead.
    o.numbers.crNegative = false
    const r2 = runCleaner(p, o)
    expect(r2.table.rows.find((x) => x.cells[3].value === 'EXP-03002')?.cells[a].value).toBe(-1937.92)
  })

  it('converts text dates, asking DD/MM vs MM/DD for the ambiguous ones', () => {
    const info = dateInfo(p, ['Txn Date'])
    expect(info.detected).toBe('DMY')
    expect(info.ambiguous.sort()).toEqual(['01/09/2026', '03/09/2026', '11/08/2026'])
    const o = none(p)
    o.removeRows.enabled = true
    o.dates.enabled = true
    const r = runCleaner(p, o)
    expect(r.reports[4].count).toBe(31)
    const d = col(r, 'Txn Date')
    expect(r.table.rows.every((x) => x.cells[d].value instanceof Date)).toBe(true)
    const of = (ref: string, res = r): Date => res.table.rows.find((x) => x.cells[3].value === ref)?.cells[d].value as Date
    expect([of('EXP-03005').getDate(), of('EXP-03005').getMonth() + 1]).toEqual([3, 9]) // 03/09/2026 = 3 Sep
    o.dates.order = 'MDY'
    const mdy = runCleaner(p, o)
    expect([of('EXP-03005', mdy).getDate(), of('EXP-03005', mdy).getMonth() + 1]).toEqual([9, 3]) // 9 Mar
    expect([of('EXP-03001', mdy).getDate(), of('EXP-03001', mdy).getMonth() + 1]).toEqual([18, 8]) // 18/08 only works as DD/MM
  })

  it('splits the signed amount into Debit / Credit and combines them back', () => {
    const o = none(p)
    o.removeRows.enabled = true
    o.amount = { enabled: true, mode: 'split', column: 'Amount', debitName: 'Debit', creditName: 'Credit', positiveIs: 'debit', crNegative: true }
    const r = runCleaner(p, o)
    expect(r.reports[5]).toMatchObject({ count: 42, unit: 'rows' })
    expect(r.table.columns).toEqual(['Category', 'Txn Date', 'Description', 'Ref', 'Debit', 'Credit', 'Paid By'])
    const sum = (c: number): number => r.table.rows.reduce((n, x) => n + (typeof x.cells[c].value === 'number' ? cents(x.cells[c].value) : 0), 0)
    expect(sum(4) - sum(5)).toBe(1846807)
    const row3 = r.table.rows.find((x) => x.cells[3].value === 'EXP-03003')!
    expect([row3.cells[4].value, row3.cells[5].value]).toEqual([null, 2483.24])

    // Combine on a Debit/Credit sheet.
    const sheet: RawSheet = {
      name: 'GL',
      rows: [
        ['Date', 'Narration', 'Debit', 'Credit'],
        ['01/09/2026', 'Sale', '1,000.00', null],
        ['02/09/2026', 'Receipt', null, 400],
        ['03/09/2026', 'Fee', 25, null]
      ]
    }
    const gl = prepareSheet(sheet, 'gl.csv')
    const go = suggestOptions(gl)
    expect(go.amount.mode).toBe('combine')
    go.amount.enabled = true
    const gr = runCleaner(gl, go)
    expect(gr.table.columns).toEqual(['Date', 'Narration', 'Amount'])
    expect(gr.table.rows.map((x) => x.cells[2].value)).toEqual([1000, -400, 25])
  })

  it('fills down the merged Category cells (4 blocks)', () => {
    const o = none(p)
    o.removeRows.enabled = true
    o.fillDown.enabled = true
    const r = runCleaner(p, o)
    expect(r.reports[2].count).toBe(38)
    const c = col(r, 'Category')
    const cats = r.table.rows.map((x) => x.cells[c].value)
    expect(cats.filter((v) => v === 'Travel')).toHaveLength(10)
    expect(cats.filter((v) => v === 'Office')).toHaveLength(11)
    expect(cats.filter((v) => v === 'Staff welfare')).toHaveLength(8)
    expect(cats.filter((v) => v === 'Repairs')).toHaveLength(13)
    // Without removing junk rows, blank separator rows are never filled.
    const o2 = none(p)
    o2.fillDown.enabled = true
    const r2 = runCleaner(p, o2)
    expect(r2.table.rows.filter((x) => x.junk === 'blank').every((x) => x.cells[c].value === null)).toBe(true)
  })

  it('flags the 2 exact duplicates by default, or removes them', () => {
    const o = none(p)
    o.removeRows.enabled = true
    o.duplicates.enabled = true
    const r = runCleaner(p, o)
    expect(r.reports[7].count).toBe(2)
    const f = col(r, 'Duplicate')
    const flagged = r.table.rows.filter((x) => x.cells[f].value !== null)
    expect(flagged.map((x) => x.cells[f].value)).toEqual(['Duplicate of row 18', 'Duplicate of row 41'])
    o.duplicates.mode = 'remove'
    const r2 = runCleaner(p, o)
    expect(r2.table.rows).toHaveLength(40)
    expect(r2.table.removed.filter((x) => x.reason === 'duplicate')).toHaveLength(2)
  })

  it('changes text case for chosen columns', () => {
    const o = none(p)
    o.removeRows.enabled = true
    o.textCase = { enabled: true, columns: ['Paid By'], mode: 'upper' }
    const r = runCleaner(p, o)
    expect(r.reports[6].count).toBe(42)
    expect(r.table.rows[0].cells[5].value).toBe('PETTY CASH')
    expect(changeCase('al noor TRADING llc - dubai', 'proper')).toBe('Al Noor Trading Llc - Dubai')
    expect(changeCase('Petty Cash', 'lower')).toBe('petty cash')
  })

  it('preview counts for disabled actions show what they would change', () => {
    const counts = previewCounts(p, none(p))
    expect(counts.removeRows).toMatchObject({ enabled: false, count: 9 })
    // With junk rows kept, the 4 subtotal amounts and the TOTAL are text numbers too (37 + 5).
    expect(counts.numbers.count).toBe(42)
    expect(counts.duplicates.count).toBe(2)
  })

  it('writes the cleaned sheet with highlighted changes plus Original and Removed rows sheets', async () => {
    const o = suggestOptions(p)
    const r = runCleaner(p, o)
    expect(r.table.rows).toHaveLength(42)
    expect(r.changedCells).toBeGreaterThan(100)
    const bytes = await cleanToWorkbook(p, r)
    const wb = new ExcelJS.Workbook()
    await wb.xlsx.load(bytes.buffer as ArrayBuffer)
    expect(wb.worksheets.map((w) => w.name)).toEqual(['Expense export', 'Original', 'Removed rows'])
    const ws = wb.worksheets[0]
    expect(ws.rowCount).toBe(43)
    expect(ws.getCell('A1').font?.bold).toBe(true)
    expect(ws.views[0]).toMatchObject({ state: 'frozen', ySplit: 1 })
    // B2: "18/08/2026" became a real date, shaded and annotated.
    expect(ws.getCell('B2').value).toBeInstanceOf(Date)
    expect(ws.getCell('B2').numFmt).toBe('dd-mmm-yyyy')
    expect((ws.getCell('B2').fill as ExcelJS.FillPattern).fgColor?.argb).toBe('FFFFF2CC')
    expect(String(ws.getCell('B2').note)).toContain('18/08/2026')
    // E2: "4,487.50" became a number with #,##0.00.
    expect(ws.getCell('E2').value).toBe(4487.5)
    expect(ws.getCell('E2').numFmt).toBe('#,##0.00')
    // A real number cell (3,486.20) did not change, so it is not shaded.
    const unchanged = ws.getColumn(5).values.findIndex((v) => v === 3486.2)
    expect((ws.getCell(unchanged, 5).fill as ExcelJS.FillPattern | undefined)?.pattern ?? 'none').toBe('none')
    expect(wb.getWorksheet('Original')!.getCell('A1').value).toBe('EXPENSE REGISTER - EXPORTED FROM LEGACY SYSTEM')
    expect(wb.getWorksheet('Removed rows')!.rowCount).toBe(10)
  })

  it('fills missing options from a recipe with the suggestions', () => {
    const o = withDefaults(p, { duplicates: { enabled: true, mode: 'remove' } })
    expect(o.duplicates.mode).toBe('remove')
    expect(o.numbers.columns).toEqual(['Amount'])
  })
})
