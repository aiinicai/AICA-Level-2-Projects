// Reads an uploaded file into a LoadedFile (sheet + header row + parsed table). Pure apart from SheetJS.

import { detectHeaderRow, parseTable, readWorkbook, type WorkbookReadResult } from '@shared/parsing'
import type { LoadedFile } from '../types'

export const PDF_MESSAGE =
  'This is a PDF. The reconciliation wizard reads Excel and CSV files only. Convert the PDF first with Tools → PDF → Excel, then upload the Excel file here.'

export function isPdfName(name: string): boolean {
  return /\.pdf$/i.test(name)
}

/** The first sheet that has at least two non-empty rows (a header and some data). */
export function firstUsefulSheet(wb: WorkbookReadResult): number {
  const idx = wb.sheets.findIndex((s) => s.rows.filter((r) => r.some((c) => c !== null && String(c).trim() !== '')).length >= 2)
  return idx >= 0 ? idx : 0
}

/** Parses one sheet; `headerRowIndex` null = detect automatically. */
export function parseSheet(wb: WorkbookReadResult, fileName: string, size: number, sheetIndex: number, headerRowIndex: number | null): LoadedFile {
  const sheet = wb.sheets[sheetIndex]
  if (!sheet) throw new Error('That sheet is not in the workbook.')
  const detected = detectHeaderRow(sheet.rows).index
  const table = parseTable(sheet, { fileName, headerRowIndex: headerRowIndex ?? detected })
  return { fileName, size, workbook: wb, sheetIndex, detectedHeaderRow: detected, table }
}

export function readUpload(name: string, data: ArrayBuffer): LoadedFile {
  if (isPdfName(name)) throw new Error(PDF_MESSAGE)
  if (!/\.(xlsx|xlsm|xls|csv)$/i.test(name)) throw new Error(`"${name}" is not an Excel or CSV file. Use .xlsx, .xls or .csv.`)
  let wb: WorkbookReadResult
  try {
    wb = readWorkbook(data, name)
  } catch (err) {
    const detail = err instanceof Error && err.message ? ` (${err.message})` : ''
    throw new Error(`"${name}" could not be read. Check that it is a valid Excel or CSV file and is not password-protected${detail}.`)
  }
  if (wb.sheets.length === 0) throw new Error(`"${name}" has no sheets with data.`)
  // A file with no data rows still loads, so the user can pick another sheet or header row.
  return parseSheet(wb, name, data.byteLength, firstUsefulSheet(wb), null)
}
