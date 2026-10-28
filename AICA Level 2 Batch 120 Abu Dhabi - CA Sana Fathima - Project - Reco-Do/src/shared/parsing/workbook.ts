// Reads .xlsx / .xls / .csv files into raw rows. Works in the renderer (browser) and in Node.

import * as XLSX from 'xlsx'
import type { CellValue, RawSheet, WorkbookData } from '../contracts'
import { parseDate } from './date'

const TEXT_EXTENSIONS = new Set(['csv', 'tsv', 'txt'])

function extensionOf(fileName: string): string {
  const m = /\.([a-z0-9]+)$/i.exec(fileName.trim())
  return m ? m[1].toLowerCase() : ''
}

function startsWith(bytes: Uint8Array, sig: number[]): boolean {
  if (bytes.length < sig.length) return false
  for (let i = 0; i < sig.length; i++) if (bytes[i] !== sig[i]) return false
  return true
}

const ZIP_SIG = [0x50, 0x4b, 0x03, 0x04]
const OLE_SIG = [0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1]
const PDF_SIG = [0x25, 0x50, 0x44, 0x46] // %PDF

/**
 * UTF-16 without a byte-order mark: text that is mostly ASCII has a NUL in every other byte (odd bytes for
 * little-endian, even bytes for big-endian). Returns the encoding, or null when the pattern is not there.
 */
function sniffUtf16(bytes: Uint8Array): 'utf-16le' | 'utf-16be' | null {
  const n = Math.min(bytes.length, 4096) & ~1
  if (n < 4) return null
  let evenNul = 0
  let oddNul = 0
  for (let i = 0; i < n; i += 2) {
    if (bytes[i] === 0) evenNul++
    if (bytes[i + 1] === 0) oddNul++
  }
  const pairs = n / 2
  if (oddNul / pairs >= 0.6 && evenNul / pairs <= 0.1) return 'utf-16le'
  if (evenNul / pairs >= 0.6 && oddNul / pairs <= 0.1) return 'utf-16be'
  return null
}

/** Decodes text bytes: UTF-8 (with or without BOM), UTF-16 (with a BOM, or recognised by its NUL bytes), else Windows-1252. */
export function decodeText(bytes: Uint8Array): string {
  if (startsWith(bytes, [0xef, 0xbb, 0xbf])) return new TextDecoder('utf-8').decode(bytes.subarray(3))
  if (startsWith(bytes, [0xff, 0xfe])) return new TextDecoder('utf-16le').decode(bytes.subarray(2))
  if (startsWith(bytes, [0xfe, 0xff])) return new TextDecoder('utf-16be').decode(bytes.subarray(2))
  const utf16 = sniffUtf16(bytes)
  if (utf16) return new TextDecoder(utf16).decode(bytes)
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes)
  } catch {
    return new TextDecoder('windows-1252').decode(bytes)
  }
}

/** Counts a delimiter on one line, ignoring delimiters inside double quotes. */
function countOutsideQuotes(line: string, delim: string): number {
  let n = 0
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (ch === '"') inQuotes = !inQuotes
    else if (ch === delim && !inQuotes) n++
  }
  return n
}

/** Picks comma, semicolon or tab: the delimiter that appears most consistently across the first lines. */
export function detectDelimiter(text: string): ',' | ';' | '\t' {
  const lines = text
    .split(/\r\n|\n|\r/)
    .filter((l) => l.trim() !== '')
    .slice(0, 30)
  if (lines.length === 0) return ','
  let best: ',' | ';' | '\t' = ','
  let bestScore = -1
  for (const d of [',', ';', '\t'] as const) {
    const counts = lines.map((l) => countOutsideQuotes(l, d))
    const freq = new Map<number, number>()
    for (const c of counts) if (c > 0) freq.set(c, (freq.get(c) ?? 0) + 1)
    let mode = 0
    let modeLines = 0
    for (const [c, f] of freq) {
      if (f > modeLines || (f === modeLines && c > mode)) {
        mode = c
        modeLines = f
      }
    }
    if (mode === 0) continue
    // Consistency first, then the number of fields it produces.
    const score = (modeLines / lines.length) * 1000 + mode
    if (score > bestScore) {
      best = d
      bestScore = score
    }
  }
  return best
}

/**
 * RFC 4180-style CSV parser (quoted fields, doubled quotes, embedded newlines). An opening quote that is never
 * closed would swallow the rest of the file; instead the file is read again with that quote taken as a literal
 * character, and its position is reported through `onUnclosedQuote` (1-based line number).
 */
export function parseCsv(text: string, delim: string, onUnclosedQuote?: (line: number) => void): string[][] {
  const literal = new Set<number>()
  for (;;) {
    const r = parseCsvOnce(text, delim, literal)
    if (r.unclosedAt < 0) return r.rows
    literal.add(r.unclosedAt)
    onUnclosedQuote?.(lineOf(text, r.unclosedAt))
  }
}

function lineOf(text: string, index: number): number {
  let line = 1
  for (let i = 0; i < index; i++) {
    const ch = text.charCodeAt(i)
    if (ch === 10 || (ch === 13 && text.charCodeAt(i + 1) !== 10)) line++
  }
  return line
}

function parseCsvOnce(text: string, delim: string, literal: Set<number>): { rows: string[][]; unclosedAt: number } {
  const rows: string[][] = []
  let quoteAt = -1
  let row: string[] = []
  let field = ''
  let inQuotes = false
  let i = 0
  const n = text.length
  while (i < n) {
    const ch = text[i]
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"'
          i += 2
          continue
        }
        inQuotes = false
        i++
        continue
      }
      field += ch
      i++
      continue
    }
    if (ch === '"' && field.trim() === '' && !literal.has(i)) {
      inQuotes = true
      quoteAt = i
      field = ''
      i++
      continue
    }
    if (ch === delim) {
      row.push(field)
      field = ''
      i++
      continue
    }
    if (ch === '\r' || ch === '\n') {
      row.push(field)
      rows.push(row)
      row = []
      field = ''
      if (ch === '\r' && text[i + 1] === '\n') i++
      i++
      continue
    }
    field += ch
    i++
  }
  if (inQuotes) return { rows, unclosedAt: quoteAt }
  if (field !== '' || row.length > 0) {
    row.push(field)
    rows.push(row)
  }
  return { rows, unclosedAt: -1 }
}

const PLAIN_NUMBER = /^-?(?:0|[1-9]\d*)(?:\.\d+)?$/
const ISO_DATE = /^\d{4}-\d{1,2}-\d{1,2}(?:[T ]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?$/
const MONTH_NAME_DATE = /^\d{1,2}[\s\-/]+[A-Za-z]{3,9}[\s\-/]+\d{2,4}$/

/** Digits a double holds exactly: longer numerals (card numbers, 16-digit references) stay text. */
const MAX_EXACT_DIGITS = 15

/**
 * CSV cells arrive as text. Plain numerals become numbers (codes with leading zeros, and numerals with more than
 * 15 significant digits, stay text so nothing is rounded);
 * ISO and month-name dates ("2026-09-03", "3-Sep-2026") become Date objects. Numeric dates like "03/09/2026"
 * stay text because their day/month order must be decided per column (see detectDateOrder).
 */
function csvCell(raw: string): CellValue {
  const s = raw.trim()
  if (s === '') return null
  if (s.length <= 40 && PLAIN_NUMBER.test(s)) {
    const significant = s.replace(/^-/, '').replace('.', '').replace(/^0+/, '').length
    const n = Number(s)
    const exact = significant <= MAX_EXACT_DIGITS && (s.includes('.') || Number.isSafeInteger(n))
    if (exact && Number.isFinite(n)) return n
  }
  if (ISO_DATE.test(s) || MONTH_NAME_DATE.test(s)) {
    const d = parseDate(s)
    if (d) return d
  }
  return s
}

/** WorkbookData plus notes about anything the reader had to repair. */
export interface WorkbookReadResult extends WorkbookData {
  /** Plain-English notes, e.g. a quote that was never closed. Absent when there is nothing to report. */
  warnings?: string[]
}

function readCsv(bytes: Uint8Array, fileName: string): WorkbookReadResult {
  const text = decodeText(bytes)
  const delim = detectDelimiter(text)
  const warnings: string[] = []
  const parsed = parseCsv(text, delim, (line) =>
    warnings.push(`Line ${line} opens a quote (") that is never closed. The quote was read as an ordinary character; check that row.`)
  )
  let width = 0
  for (const r of parsed) if (r.length > width) width = r.length
  const rows: CellValue[][] = parsed.map((r) => {
    const out = new Array<CellValue>(width).fill(null)
    for (let c = 0; c < r.length; c++) out[c] = csvCell(r[c])
    return out
  })
  // Drop trailing blank lines (an artefact of the final newline).
  while (rows.length > 0 && rows[rows.length - 1].every((v) => v === null)) rows.pop()
  const base = fileName.replace(/\.[^.]+$/, '') || 'Sheet1'
  const out: WorkbookReadResult = { fileName, sheets: [{ name: base.slice(0, 31), rows }] }
  if (warnings.length > 0) out.warnings = warnings
  return out
}

/**
 * SheetJS stores date cells so that their UTC fields hold the calendar values. Convert to a local Date with
 * the same calendar fields, rounding away floating-point drift (e.g. 23:59:59.999).
 */
function toLocalDate(d: Date): Date | null {
  const t = d.getTime()
  if (Number.isNaN(t)) return null
  const r = new Date(Math.round(t / 1000) * 1000)
  return new Date(
    r.getUTCFullYear(),
    r.getUTCMonth(),
    r.getUTCDate(),
    r.getUTCHours(),
    r.getUTCMinutes(),
    r.getUTCSeconds()
  )
}

function convertCell(cell: XLSX.CellObject | undefined): CellValue {
  if (!cell) return null
  switch (cell.t) {
    case 'n':
      return typeof cell.v === 'number' && Number.isFinite(cell.v) ? cell.v : null
    case 's': {
      const s = cell.v === undefined || cell.v === null ? '' : String(cell.v).trim()
      return s === '' ? null : s
    }
    case 'd': {
      const v = cell.v
      if (v instanceof Date) return toLocalDate(v)
      if (typeof v === 'string') {
        const d = new Date(v)
        return Number.isNaN(d.getTime()) ? null : toLocalDate(d)
      }
      return null
    }
    case 'b':
      return cell.v ? 'TRUE' : 'FALSE'
    case 'e':
      return cell.w ? cell.w : null
    default:
      return null
  }
}

function sheetRows(ws: XLSX.WorkSheet): CellValue[][] {
  const ref = ws['!ref']
  if (!ref) return []
  const range = XLSX.utils.decode_range(ref)
  const width = range.e.c + 1
  const height = range.e.r + 1
  const dense = (ws as XLSX.DenseWorkSheet)['!data']
  const rows: CellValue[][] = new Array<CellValue[]>(height)
  for (let r = 0; r < height; r++) {
    const out = new Array<CellValue>(width).fill(null)
    if (r >= range.s.r) {
      const srcRow = dense ? dense[r] : undefined
      for (let c = range.s.c; c < width; c++) {
        const cell = dense ? srcRow?.[c] : (ws as XLSX.Sheet)[XLSX.utils.encode_cell({ r, c })] as XLSX.CellObject | undefined
        out[c] = convertCell(cell)
      }
    }
    rows[r] = out
  }
  // Merged cells: keep the value only in the top-left cell.
  for (const m of ws['!merges'] ?? []) {
    for (let r = m.s.r; r <= Math.min(m.e.r, height - 1); r++) {
      for (let c = m.s.c; c <= Math.min(m.e.c, width - 1); c++) {
        if (r === m.s.r && c === m.s.c) continue
        rows[r][c] = null
      }
    }
  }
  // Drop trailing rows that are completely empty.
  let end = rows.length
  while (end > 0 && rows[end - 1].every((v) => v === null)) end--
  rows.length = end
  return rows
}

function friendlyReadError(err: unknown): Error {
  const msg = err instanceof Error ? err.message : String(err)
  if (/password-protected|encrypted file|encryptedpackage/i.test(msg)) {
    return new Error('This workbook is password-protected. Remove the password in Excel, save it and try again.')
  }
  return new Error(
    'This file could not be read as a spreadsheet. It may be damaged or in an unsupported format. Save it as .xlsx or .csv and try again.'
  )
}

/**
 * Reads an .xlsx, .xls or .csv file. Every sheet's rows are returned as CellValue[][] (row 0 = Excel row 1):
 * Date objects for date cells (local time), numbers as numbers, trimmed strings, null for empty cells.
 * Merged areas keep their value only in the top-left cell. Throws an Error with a plain-English message
 * when the file cannot be read.
 */
export function readWorkbook(data: ArrayBuffer, fileName: string): WorkbookReadResult {
  const bytes = new Uint8Array(data)
  if (bytes.length === 0) throw new Error('This file is empty.')
  if (startsWith(bytes, PDF_SIG)) {
    throw new Error(
      'This is a PDF. The reconciliation reads Excel or CSV files. Convert it first with the PDF → Excel tool in the Tools section.'
    )
  }
  const ext = extensionOf(fileName)
  const isBinary = startsWith(bytes, ZIP_SIG) || startsWith(bytes, OLE_SIG)
  if (!isBinary && TEXT_EXTENSIONS.has(ext)) return readCsv(bytes, fileName)

  let wb: XLSX.WorkBook
  try {
    wb = XLSX.read(bytes, { type: 'array', cellDates: true, dense: true, cellNF: false, cellHTML: false })
  } catch (err) {
    throw friendlyReadError(err)
  }
  const sheets: RawSheet[] = wb.SheetNames.map((name) => ({ name, rows: sheetRows(wb.Sheets[name]) }))
  if (sheets.length === 0) throw friendlyReadError(new Error('no sheets'))
  return { fileName, sheets }
}
