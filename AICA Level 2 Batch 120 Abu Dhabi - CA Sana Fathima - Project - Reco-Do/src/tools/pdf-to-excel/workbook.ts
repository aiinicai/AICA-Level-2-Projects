// PDF → Excel output: a formatted ExcelJS workbook (bold frozen header, autofilter, widths,
// #,##0.00 amounts, dd-mmm-yyyy dates, amber low-confidence OCR cells, "Read me" and "Excluded rows" sheets).

import ExcelJS from 'exceljs'
import type { CellValue } from '@shared/contracts'
import { formatDate } from '@shared/format'
import type { PdfColumn, PdfExtractResult, PdfRow, PdfTable, PdfWorkbookOptions } from './types'

export const AMOUNT_FORMAT = '#,##0.00'
export const DATE_FORMAT = 'dd-mmm-yyyy'
/** Light amber fill for low-confidence OCR cells. */
export const LOW_CONFIDENCE_FILL = 'FFFFE08A'
const HEADER_FILL = 'FF14213D'

/** ExcelJS writes Dates as UTC; parsed dates are local midnight, so move them to UTC midnight. */
function excelDate(d: Date): Date {
  return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()))
}

/** Whole numbers of 12+ digits outside amount / number columns stay text, so Excel never shows 1.23457E+15. */
function isLongIdNumber(v: CellValue, col: PdfColumn | undefined): boolean {
  return typeof v === 'number' && Number.isInteger(v) && Math.abs(v) >= 1e11 && col?.type !== 'amount' && col?.type !== 'number'
}

function excelValue(v: CellValue, col?: PdfColumn): ExcelJS.CellValue {
  if (v instanceof Date) return excelDate(v)
  if (isLongIdNumber(v, col)) return String(v)
  return v
}

function sheetName(name: string, used: Set<string>): string {
  const base = name.replace(/[[\]*?:/\\]/g, ' ').trim().slice(0, 31) || 'Sheet'
  let n = base
  for (let i = 2; used.has(n.toLowerCase()); i++) n = `${base.slice(0, 31 - ` (${i})`.length)} (${i})`
  used.add(n.toLowerCase())
  return n
}

function displayLength(v: CellValue, col: PdfColumn | null): number {
  if (v === null) return 0
  if (v instanceof Date) return 11
  if (typeof v === 'number') return col && (col.type === 'amount' || col.type === 'number') ? v.toFixed(2).length + Math.floor(Math.abs(v).toFixed(0).length / 3) : String(v).length
  return String(v).length
}

interface Block {
  columns: PdfColumn[]
  rows: PdfRow[]
}

/** Writes a header row (optional) and the rows from `startRow`; returns the next free row. */
function writeBlock(ws: ExcelJS.Worksheet, block: Block, startRow: number, addPage: boolean, widths: number[], withHeader = true): number {
  const headers = withHeader ? [...block.columns.map((c) => c.name), ...(addPage ? ['Page'] : [])] : []
  const headerRow = ws.getRow(startRow)
  headers.forEach((h, i) => {
    const cell = headerRow.getCell(i + 1)
    cell.value = h
    cell.font = { bold: true, color: { argb: 'FFFFFFFF' } }
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: HEADER_FILL } }
    cell.alignment = { vertical: 'middle', horizontal: block.columns[i] && (block.columns[i].type === 'amount' || block.columns[i].type === 'number') ? 'right' : 'left' }
    widths[i] = Math.max(widths[i] ?? 0, h.length + 2)
  })
  let r = withHeader ? startRow + 1 : startRow
  for (const row of block.rows) {
    const xr = ws.getRow(r)
    row.cells.forEach((cell, c) => {
      const col = block.columns[c]
      const xc = xr.getCell(c + 1)
      xc.value = excelValue(cell.value, col)
      if (cell.value instanceof Date) xc.numFmt = DATE_FORMAT
      else if (typeof cell.value === 'number' && (col.type === 'amount' || col.type === 'number')) xc.numFmt = AMOUNT_FORMAT
      if (cell.lowConfidence) {
        xc.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: LOW_CONFIDENCE_FILL } }
        if (cell.confidence !== null) xc.note = `OCR confidence ${cell.confidence}%. Check this value against the PDF.`
        else xc.note = 'Read by OCR and corrected automatically. Check this value against the PDF.'
      }
      widths[c] = Math.max(widths[c] ?? 0, displayLength(cell.value, col) + 2)
    })
    if (addPage) {
      xr.getCell(block.columns.length + 1).value = row.page
      widths[block.columns.length] = Math.max(widths[block.columns.length] ?? 0, 6)
    }
    r++
  }
  return r
}

function finishSheet(ws: ExcelJS.Worksheet, widths: number[], columnCount: number, firstHeaderRow: number, lastRow: number): void {
  widths.forEach((w, i) => {
    ws.getColumn(i + 1).width = Math.min(60, Math.max(8, w))
  })
  ws.views = [{ state: 'frozen', ySplit: firstHeaderRow, xSplit: 0 }]
  if (columnCount > 0) ws.autoFilter = { from: { row: firstHeaderRow, column: 1 }, to: { row: Math.max(firstHeaderRow, lastRow), column: columnCount } }
}

function sameColumns(a: PdfTable, b: PdfTable): boolean {
  return a.columns.length === b.columns.length && a.columns.every((c, i) => c.name === b.columns[i].name)
}

/**
 * Builds the .xlsx bytes. One sheet per table (default) or all tables on one sheet (tables with the same
 * columns are appended; different ones are stacked with their own header row). Adds "Excluded rows" and,
 * when OCR was used, a "Read me" sheet.
 */
export async function toWorkbook(result: PdfExtractResult, opts: PdfWorkbookOptions = {}): Promise<Uint8Array> {
  const addPage = opts.addPageColumn ?? true
  const oneSheetPerTable = opts.oneSheetPerTable ?? true
  const includeExcluded = opts.includeExcludedSheet ?? true

  const wb = new ExcelJS.Workbook()
  wb.creator = 'Reco-Do'
  wb.created = new Date()
  const used = new Set<string>()

  if (result.tables.length === 0) {
    const ws = wb.addWorksheet(sheetName('Data', used))
    ws.getCell('A1').value = 'No table rows were found in the selected pages.'
  } else if (oneSheetPerTable || result.tables.length === 1) {
    for (const t of result.tables) {
      const ws = wb.addWorksheet(sheetName(result.tables.length === 1 ? 'Data' : t.name, used))
      const widths: number[] = []
      const last = writeBlock(ws, t, 1, addPage, widths) - 1
      finishSheet(ws, widths, t.columns.length + (addPage ? 1 : 0), 1, last)
    }
  } else {
    const ws = wb.addWorksheet(sheetName('Data', used))
    const widths: number[] = []
    let row = 1
    let firstCols = 0
    let firstLast = 1
    let inFirstBlock = true
    result.tables.forEach((t, i) => {
      const prev = result.tables[i - 1]
      if (prev && sameColumns(prev, t)) {
        // Same columns as the block above: append the rows under it without a new header.
        row = writeBlock(ws, t, row, addPage, widths, false)
      } else {
        if (i > 0) {
          inFirstBlock = false
          row++ // blank row between blocks
        }
        if (i === 0) firstCols = t.columns.length + (addPage ? 1 : 0)
        row = writeBlock(ws, t, row, addPage, widths)
      }
      if (inFirstBlock) firstLast = row - 1
    })
    finishSheet(ws, widths, firstCols, 1, firstLast)
  }

  if (includeExcluded && result.excluded.length > 0) {
    const ws = wb.addWorksheet(sheetName('Excluded rows', used))
    const widths = [6, 26, 40, 80]
    ;['Page', 'Reason', 'Detail', 'Text'].forEach((h, i) => {
      const c = ws.getCell(1, i + 1)
      c.value = h
      c.font = { bold: true, color: { argb: 'FFFFFFFF' } }
      c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: HEADER_FILL } }
    })
    result.excluded.forEach((e, i) => {
      const r = ws.getRow(i + 2)
      r.getCell(1).value = e.page
      r.getCell(2).value = reasonLabel(e.reason)
      r.getCell(3).value = e.detail
      r.getCell(4).value = e.text
    })
    finishSheet(ws, widths, 4, 1, result.excluded.length + 1)
  }

  if (result.ocrPages.length > 0) addReadMe(wb, result, used)

  const buf = await wb.xlsx.writeBuffer()
  return new Uint8Array(buf as ArrayBuffer)
}

function reasonLabel(r: PdfExtractResult['excluded'][number]['reason']): string {
  switch (r) {
    case 'repeated-header':
      return 'Repeated column headers'
    case 'page-header-footer':
      return 'Page header / footer'
    case 'page-number':
      return 'Page number'
    case 'outside-table':
      return 'Outside the table'
  }
}

function addReadMe(wb: ExcelJS.Workbook, result: PdfExtractResult, used: Set<string>): void {
  const ws = wb.addWorksheet(sheetName('Read me', used))
  const low = result.tables.reduce((n, t) => n + t.rows.reduce((m, r) => m + r.cells.filter((c) => c.lowConfidence).length, 0), 0)
  const pageList = result.ocrPages.join(', ')
  const conf = result.pages
    .filter((p) => p.method === 'ocr')
    .map((p) => `Page ${p.page}: average OCR confidence ${p.ocrConfidence ?? 0}%`)
  const lines: string[] = [
    'Read me - text recognition (OCR)',
    '',
    `Source file: ${result.fileName}`,
    `Converted: ${formatDate(new Date())}`,
    '',
    `Page${result.ocrPages.length === 1 ? '' : 's'} ${pageList} had no text layer (scanned image), so the text was read with on-device OCR.`,
    ...conf,
    '',
    `Cells shaded amber (${low}) were read with OCR confidence below ${result.lowConfidenceBelow}% or were corrected automatically`,
    '(for example a missing decimal point). Check them against the PDF before relying on them.',
    'Each shaded cell has a note with its confidence.',
    '',
    'OCR runs entirely on this computer. Nothing was uploaded.'
  ]
  lines.forEach((t, i) => {
    const c = ws.getCell(i + 1, 1)
    c.value = t
    if (i === 0) c.font = { bold: true, size: 13 }
  })
  const sample = ws.getCell(lines.length + 2, 1)
  sample.value = 'Example of a low-confidence cell'
  sample.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: LOW_CONFIDENCE_FILL } }
  ws.getColumn(1).width = 110
}
