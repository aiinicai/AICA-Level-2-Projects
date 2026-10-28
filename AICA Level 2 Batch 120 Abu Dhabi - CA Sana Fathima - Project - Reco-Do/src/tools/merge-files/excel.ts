// Formatted ExcelJS sheets shared by the Merge Files and Data Cleaner engines:
// bold frozen header, autofilter, column widths, real numbers as #,##0.00 and real dates as dd-mmm-yyyy.

import ExcelJS from 'exceljs'
import type { CellValue, ColumnType } from '@shared/contracts'

export const AMOUNT_FORMAT = '#,##0.00'
export const DATE_FORMAT = 'dd-mmm-yyyy'
export const HEADER_FILL = 'FF14213D'
/** Light amber: cells changed by the Data Cleaner. */
export const CHANGED_FILL = 'FFFFF2CC'
/** Light orange: rows flagged as duplicates. */
export const FLAGGED_FILL = 'FFFDE3CF'

/** ExcelJS writes Dates as UTC; parsed dates are local midnight, so move them to UTC midnight. */
export function excelDate(d: Date): Date {
  return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate(), d.getHours(), d.getMinutes(), d.getSeconds()))
}

/**
 * Whole numbers of 12 or more digits outside amount columns (account numbers, card or reference numbers) are
 * written as text: Excel's General format would show them as 1.23457E+15 and round them past 15 digits.
 */
export function isLongIdNumber(v: CellValue, type?: ColumnType): boolean {
  return typeof v === 'number' && Number.isInteger(v) && Math.abs(v) >= 1e11 && type !== 'amount'
}

export function excelValue(v: CellValue, type?: ColumnType): ExcelJS.CellValue {
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? null : excelDate(v)
  if (isLongIdNumber(v, type)) return String(v)
  return v
}

/** Excel sheet names: max 31 characters, no []*?:/\ and unique (case-insensitive) within the workbook. */
export function uniqueSheetName(name: string, used: Set<string>): string {
  const base = name.replace(/[[\]*?:/\\]/g, ' ').trim().slice(0, 31) || 'Sheet'
  let n = base
  for (let i = 2; used.has(n.toLowerCase()); i++) n = `${base.slice(0, 31 - ` (${i})`.length)} (${i})`
  used.add(n.toLowerCase())
  return n
}

function displayLength(v: CellValue): number {
  if (v === null || v === undefined) return 0
  if (v instanceof Date) return 11
  if (typeof v === 'number') {
    const whole = Math.abs(Math.trunc(v)).toString().length
    return whole + Math.floor((whole - 1) / 3) + 4
  }
  return String(v).length
}

export interface SheetColumn {
  name: string
  type?: ColumnType
}

export interface CellStyle {
  /** ARGB fill colour. */
  fill?: string
  note?: string
}

export interface WriteSheetOptions {
  /** Per-cell styling hook (row and column are 0-based into `rows`). */
  style?: (row: number, col: number) => CellStyle | undefined
  /** Freeze the header and add an autofilter. Default true. */
  table?: boolean
}

/** Writes a header row and data rows from row 1, with all the formatting rules above. */
export function writeTableSheet(ws: ExcelJS.Worksheet, columns: SheetColumn[], rows: CellValue[][], opts: WriteSheetOptions = {}): void {
  const widths = columns.map((c) => Math.max(8, c.name.length + 3))
  const header = ws.getRow(1)
  columns.forEach((c, i) => {
    const cell = header.getCell(i + 1)
    cell.value = c.name
    cell.font = { bold: true, color: { argb: 'FFFFFFFF' } }
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: HEADER_FILL } }
    cell.alignment = { vertical: 'middle', horizontal: c.type === 'amount' || c.type === 'number' ? 'right' : 'left' }
  })
  rows.forEach((values, r) => {
    const xr = ws.getRow(r + 2)
    for (let c = 0; c < columns.length; c++) {
      const v = values[c] ?? null
      const xc = xr.getCell(c + 1)
      xc.value = excelValue(v, columns[c].type)
      if (v instanceof Date) xc.numFmt = DATE_FORMAT
      else if (typeof v === 'number' && !isLongIdNumber(v, columns[c].type)) {
        const t = columns[c].type
        if (t === 'amount' || (t === 'number' && !Number.isInteger(v))) xc.numFmt = AMOUNT_FORMAT
      }
      const s = opts.style?.(r, c)
      if (s?.fill) xc.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: s.fill } }
      if (s?.note) xc.note = s.note
      widths[c] = Math.max(widths[c], displayLength(v) + 2)
    }
  })
  widths.forEach((w, i) => {
    ws.getColumn(i + 1).width = Math.min(60, w)
  })
  if (opts.table ?? true) {
    ws.views = [{ state: 'frozen', ySplit: 1, xSplit: 0 }]
    if (columns.length > 0) ws.autoFilter = { from: { row: 1, column: 1 }, to: { row: Math.max(1, rows.length + 1), column: columns.length } }
  }
}

/** Writes rows exactly as given (no header styling); used for the Data Cleaner's "Original" audit sheet. */
export function writeRawSheet(ws: ExcelJS.Worksheet, rows: CellValue[][]): void {
  const widths: number[] = []
  rows.forEach((values, r) => {
    const xr = ws.getRow(r + 1)
    values.forEach((v, c) => {
      if (v === null || v === undefined) return
      const xc = xr.getCell(c + 1)
      xc.value = excelValue(v)
      if (v instanceof Date) xc.numFmt = DATE_FORMAT
      widths[c] = Math.max(widths[c] ?? 8, Math.min(60, displayLength(v) + 2))
    })
  })
  for (let c = 0; c < widths.length; c++) ws.getColumn(c + 1).width = widths[c] ?? 8
}

export async function workbookBytes(wb: ExcelJS.Workbook): Promise<Uint8Array> {
  const buf = await wb.xlsx.writeBuffer()
  return new Uint8Array(buf as ArrayBuffer)
}

export function newWorkbook(): ExcelJS.Workbook {
  const wb = new ExcelJS.Workbook()
  wb.creator = 'Reco-Do'
  wb.created = new Date()
  return wb
}
