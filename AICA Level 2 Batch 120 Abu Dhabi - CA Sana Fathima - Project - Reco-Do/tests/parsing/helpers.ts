import { readFileSync } from 'fs'
import { join } from 'path'
import * as XLSX from 'xlsx'
import type { CellValue, WorkbookData } from '@shared/contracts'
import { readWorkbook } from '@shared/parsing'

export function toArrayBuffer(buf: Uint8Array): ArrayBuffer {
  const out = new ArrayBuffer(buf.byteLength)
  new Uint8Array(out).set(buf)
  return out
}

export function loadSample(relPath: string): WorkbookData {
  const buf = readFileSync(join('sample-data', relPath))
  return readWorkbook(toArrayBuffer(buf), relPath.split('/').pop() ?? relPath)
}

/** Builds a workbook file in memory from arrays of arrays (Date objects become date cells). */
export function makeWorkbook(
  sheets: Record<string, Array<Array<CellValue | boolean>>>,
  bookType: XLSX.BookType = 'xlsx',
  merges?: Record<string, XLSX.Range[]>
): ArrayBuffer {
  const wb = XLSX.utils.book_new()
  for (const [name, rows] of Object.entries(sheets)) {
    const ws = XLSX.utils.aoa_to_sheet(rows, { cellDates: true })
    if (merges?.[name]) ws['!merges'] = merges[name]
    XLSX.utils.book_append_sheet(wb, ws, name)
  }
  const out = XLSX.write(wb, { type: 'array', bookType }) as ArrayBuffer
  return out
}

export function textBuffer(text: string): ArrayBuffer {
  return toArrayBuffer(new TextEncoder().encode(text))
}

export const d = (y: number, m: number, day: number): Date => new Date(y, m - 1, day)
