// Turns a raw sheet into a table: unique column names, excluded rows (listed, never dropped silently)
// and the opening / closing balances.

import type { CellValue, ExcludedRow, ExclusionReason, ParsedTable, RawSheet, TableRow } from '../contracts'
import { parseAmount } from './amount'
import { isDateLike } from './date'
import { detectHeaderRow, findTwoRowHeader, mergeHeaderRows } from './header'

export interface ParseTableOptions {
  fileName: string
  /**
   * 0-based header row; detected automatically when omitted. Pass -1 for a file with no header row
   * (every row is data and the columns are named "Column 1", "Column 2", ...).
   */
  headerRowIndex?: number
}

/**
 * Header representation in the returned ParsedTable:
 *  - `headerRowIndex >= 0`: the 0-based row holding the column names. When the header spans two rows
 *    ("Txn" over "Date", "Amount" over "Debit" / "Credit"), `headerRowIndex` is the LOWER of the two rows
 *    (data starts right below it) and the names are joined top-to-bottom: "Txn Date", "Amount Debit".
 *  - `headerRowIndex === -1` (NO_HEADER_ROW): the file has no header row. Every row from row 0 is data and
 *    the columns are named "Column 1", "Column 2", ... (see `buildColumnNames`).
 */
export const NO_HEADER_ROW = -1

// Matched at the start of a cell; a bare "Opening" / "Closing" only when it is the whole cell (GL voucher type).
const OPENING_RE =
  /^(?:opening\s+bal(?:ance)?\b|bal(?:ance)?\s+(?:brought\s+forward|b\s*\/\s*f|b\s*fwd)\b|brought\s+forward\b|b\s*\/\s*f\b|opening$)/i
const CLOSING_RE =
  /^(?:closing\s+bal(?:ance)?\b|bal(?:ance)?\s+(?:carried\s+forward|c\s*\/\s*f|c\s*fwd)\b|carried\s+forward\b|c\s*\/\s*f\b|closing$)/i
const SUBTOTAL_RE = /^sub[\s-]?totals?\b/i
const TOTAL_RE = /^(?:grand\s+)?totals?\b/i
/**
 * Whole-label forms, used for rows that carry a date and a transaction amount: there a description that merely
 * STARTS with a keyword ("TOTAL UAE FUEL STATION", "Opening balance adjustment JV12", "Balance b/f correction")
 * is a real transaction. The label may end with "as at / as on / on / for <date>", a bracketed note or a colon.
 */
const LABEL_TAIL = String.raw`(?:\s+(?:as\s+(?:at|on|of)|on|at|for|of)\b.*|\s*\(.*\))?[\s.:\-]*$`
const OPENING_FULL = new RegExp(
  String.raw`^(?:opening\s+bal(?:ance)?|bal(?:ance)?\s+(?:brought\s+forward|b\s*\/\s*f|b\s*fwd)|brought\s+forward|b\s*\/\s*f|opening)` + LABEL_TAIL,
  'i'
)
const CLOSING_FULL = new RegExp(
  String.raw`^(?:closing\s+bal(?:ance)?|bal(?:ance)?\s+(?:carried\s+forward|c\s*\/\s*f|c\s*fwd)|carried\s+forward|c\s*\/\s*f|closing)` + LABEL_TAIL,
  'i'
)
const SUBTOTAL_FULL = new RegExp(String.raw`^sub[\s-]?totals?` + LABEL_TAIL, 'i')
const TOTAL_FULL = new RegExp(String.raw`^(?:grand\s+)?totals?` + LABEL_TAIL, 'i')
/** Quick filter so only a few cells go through the regexes. */
const KEYWORD_HINT = /bal|forward|total|b\s*\/\s*f|c\s*\/\s*f|opening|closing|fwd/i

function headerName(v: CellValue): string {
  if (v === null || v === undefined) return ''
  if (v instanceof Date) {
    if (Number.isNaN(v.getTime())) return ''
    const mm = String(v.getMonth() + 1).padStart(2, '0')
    const dd = String(v.getDate()).padStart(2, '0')
    return `${v.getFullYear()}-${mm}-${dd}`
  }
  return String(v).replace(/\s+/g, ' ').trim()
}

/** Unique names in file order: blanks become "Column 3", duplicates "Debit (2)". */
export function buildColumnNames(headerCells: CellValue[], width: number): string[] {
  const raw: string[] = []
  for (let c = 0; c < width; c++) raw.push(headerName(headerCells[c] ?? null))
  const taken = new Set<string>()
  for (const r of raw) if (r !== '') taken.add(r.toLowerCase())
  const used = new Set<string>()
  const counts = new Map<string, number>()
  const out: string[] = []
  for (let c = 0; c < width; c++) {
    let name = raw[c]
    if (name === '') {
      name = `Column ${c + 1}`
      let k = 2
      while (used.has(name.toLowerCase()) || taken.has(name.toLowerCase())) name = `Column ${c + 1} (${k++})`
    } else if (used.has(name.toLowerCase())) {
      const base = name
      let k = (counts.get(base.toLowerCase()) ?? 1) + 1
      name = `${base} (${k})`
      while (used.has(name.toLowerCase()) || taken.has(name.toLowerCase())) name = `${base} (${++k})`
      counts.set(base.toLowerCase(), k)
    }
    used.add(name.toLowerCase())
    out.push(name)
  }
  return out
}

function isEmpty(v: CellValue): boolean {
  return v === null || v === undefined || (typeof v === 'string' && v.trim() === '')
}

function lastFilled(cells: CellValue[]): number {
  for (let c = cells.length - 1; c >= 0; c--) if (!isEmpty(cells[c])) return c + 1
  return 0
}

/**
 * Opening / closing / total / subtotal keywords. A row with a date and a transaction amount (a number outside
 * the balance columns) is excluded only when the keyword is the whole label; otherwise the start of a cell is
 * enough (undated summary rows such as "Total for September", "Balance b/f from August").
 */
function keywordReason(cells: CellValue[], hasDate: boolean, hasMovement: boolean): ExclusionReason | null {
  const strict = hasDate && hasMovement
  for (const v of cells) {
    if (typeof v !== 'string') continue
    if (!KEYWORD_HINT.test(v)) continue
    const s = v.replace(/\s+/g, ' ').trim()
    if (strict) {
      if (OPENING_FULL.test(s)) return 'opening-balance'
      if (CLOSING_FULL.test(s)) return 'closing-balance'
      if (SUBTOTAL_FULL.test(s)) return 'subtotal'
      if (TOTAL_FULL.test(s)) return 'total'
      continue
    }
    if (OPENING_RE.test(s)) return 'opening-balance'
    if (CLOSING_RE.test(s)) return 'closing-balance'
    if (SUBTOTAL_RE.test(s)) return 'subtotal'
    // A dated description that merely starts with "Total" is kept unless it is the whole label.
    if (TOTAL_RE.test(s) && (!hasDate || TOTAL_FULL.test(s))) return 'total'
  }
  return null
}

/** True when the row has a number outside the balance columns (a debit, credit or amount, not a running balance). */
function rowHasMovement(cells: CellValue[], balanceCols: number[]): boolean {
  for (let c = 0; c < cells.length; c++) {
    if (balanceCols.includes(c)) continue
    const v = cells[c]
    if (typeof v === 'number') {
      if (v !== 0) return true
      continue
    }
    if (typeof v !== 'string' || isEmpty(v)) continue
    const s = v.trim()
    // Codes such as "004512" or "JV12" are not amounts; a movement has decimals, separators, a sign or a CR/DR marker.
    if (/^0\d/.test(s) || isDateLike(s)) continue
    const a = parseAmount(s)
    if (a !== null && a.value !== 0 && /[.,()\-]|cr|dr/i.test(s)) return true
  }
  return false
}

interface BalanceContext {
  balanceCols: number[]
  /** Debit and Credit columns (by header), used when there is no Balance column. */
  debitCols: number[]
  creditCols: number[]
  /**
   * Per balance column, the CR/DR marker most of its cells carry ("12,345.00 Cr" on a bank statement). Values
   * with that marker are positive (the file's own balance sign); values with the other marker are negative.
   * Null when the column carries no markers or they are split evenly: then Dr is positive and Cr negative
   * (debit - credit, as for a ledger).
   */
  usualIndicator: Map<number, 'DR' | 'CR' | null>
}

function signed(a: { value: number; indicator: 'DR' | 'CR' | null }, usual: 'DR' | 'CR' | null): number {
  if (a.indicator === null) return a.value
  const abs = Math.abs(a.value)
  const positive = usual === null ? a.indicator === 'DR' : a.indicator === usual
  const v = positive ? abs : -abs
  return v === 0 ? 0 : v
}

/**
 * Balance on an opening/closing row: the Balance column (CR/DR applied), else Debit - Credit when the table has
 * Debit / Credit columns, else the last numeric cell (CR/DR applied).
 */
function balanceOf(cells: CellValue[], ctx: BalanceContext): number | null {
  for (const c of ctx.balanceCols) {
    const a = parseAmount(cells[c] ?? null)
    if (a !== null) return signed(a, ctx.usualIndicator.get(c) ?? null)
  }
  if (ctx.debitCols.length > 0 || ctx.creditCols.length > 0) {
    let found = false
    let total = 0
    for (const c of ctx.debitCols) {
      const a = parseAmount(cells[c] ?? null)
      if (a === null) continue
      found = true
      total += a.indicator === null ? a.value : signed(a, null)
    }
    for (const c of ctx.creditCols) {
      const a = parseAmount(cells[c] ?? null)
      if (a === null) continue
      found = true
      // A marker in the Credit column states the side itself; otherwise the column is the credit side. Brackets or
      // a minus there ("(20.00)") restate that it is a credit, so they do not flip it back to a debit.
      total += a.indicator === null ? -Math.abs(a.value) : signed(a, null)
    }
    if (found) return Math.round(total * 100) / 100 || 0
  }
  for (let c = cells.length - 1; c >= 0; c--) {
    const v = cells[c]
    if (v instanceof Date || isEmpty(v)) continue
    if (typeof v === 'string' && isDateLike(v)) continue
    const a = parseAmount(v)
    if (a !== null) return signed(a, null)
  }
  return null
}

const DEBIT_HEADER = /\b(debit|debits|dr|withdrawals?|paid\s*out|money\s*out)\b/i
const CREDIT_HEADER = /\b(credit|credits|cr|deposits?|paid\s*in|money\s*in)\b/i

function rowHasDate(cells: CellValue[]): boolean {
  for (const v of cells) {
    if (v instanceof Date) return true
    if (typeof v === 'string' && v.length >= 6 && v.length <= 40 && isDateLike(v)) return true
  }
  return false
}

/**
 * Builds a ParsedTable from a raw sheet. Rows above the header are titles and are not part of the table.
 * Below the header, blank rows, opening/closing balance rows, total and subtotal rows and repeated header
 * rows are moved to `excluded` with a reason. Opening and closing balances are captured from their rows.
 */
export function parseTable(sheet: RawSheet, opts: ParseTableOptions): ParsedTable {
  const rows = sheet.rows
  let headerRowIndex: number
  if (opts.headerRowIndex !== undefined) {
    headerRowIndex = opts.headerRowIndex < 0 ? NO_HEADER_ROW : Math.min(Math.floor(opts.headerRowIndex), Math.max(0, rows.length - 1))
  } else {
    headerRowIndex = detectHeaderRow(rows).index
  }

  let headerCells: CellValue[] = headerRowIndex >= 0 ? (rows[headerRowIndex] ?? []) : []
  if (headerRowIndex >= 0) {
    const pair = findTwoRowHeader(rows, headerRowIndex)
    if (pair) {
      headerCells = mergeHeaderRows(rows[pair.top] ?? [], rows[pair.lower] ?? [])
      headerRowIndex = pair.lower
    }
  }

  // Width: last column holding anything in the header or below it.
  let width = lastFilled(headerCells)
  for (let r = Math.max(0, headerRowIndex); r < rows.length; r++) {
    const row = rows[r]
    if (!row) continue
    for (let c = row.length - 1; c >= width; c--) {
      if (!isEmpty(row[c])) {
        width = c + 1
        break
      }
    }
  }

  const columns = buildColumnNames(headerCells, width)
  const debitCols: number[] = []
  const creditCols: number[] = []
  const headerKeys: Array<string | null> = []
  let headerFilled = 0
  for (let c = 0; c < width; c++) {
    const name = headerName(headerCells[c] ?? null)
    headerKeys.push(name === '' ? null : name.toLowerCase())
    if (name !== '') headerFilled++
  }
  const balanceCols: number[] = []
  columns.forEach((name, c) => {
    if (/^(running\s+)?balance\b/i.test(name)) balanceCols.push(c)
  })
  columns.forEach((name, c) => {
    if (!balanceCols.includes(c) && /\bbalance\b/i.test(name)) balanceCols.push(c)
  })
  if (headerRowIndex >= 0) {
    columns.forEach((name, c) => {
      if (balanceCols.includes(c)) return
      if (DEBIT_HEADER.test(name) && !CREDIT_HEADER.test(name)) debitCols.push(c)
      else if (CREDIT_HEADER.test(name) && !DEBIT_HEADER.test(name)) creditCols.push(c)
    })
  }

  // Pass 1: slice rows and note which have dates (to decide whether the table is date-driven).
  const sliced: CellValue[][] = []
  const hasDate: boolean[] = []
  let nonBlank = 0
  let dated = 0
  for (let r = headerRowIndex + 1; r < rows.length; r++) {
    const src = rows[r] ?? []
    const cells: CellValue[] = new Array<CellValue>(width)
    let filled = false
    for (let c = 0; c < width; c++) {
      const v = src[c]
      const val = v === undefined ? null : v
      cells[c] = val
      if (!filled && !isEmpty(val)) filled = true
    }
    sliced.push(cells)
    const d = filled && rowHasDate(cells)
    hasDate.push(d)
    if (filled) {
      nonBlank++
      if (d) dated++
    }
  }
  const dateDriven = nonBlank > 0 && dated / nonBlank >= 0.5

  // The CR/DR marker most cells of each balance column carry (the file's own balance sign).
  const usualIndicator = new Map<number, 'DR' | 'CR' | null>()
  for (const c of balanceCols) {
    let dr = 0
    let cr = 0
    for (const cells of sliced) {
      const v = cells[c]
      if (typeof v !== 'string' || !/cr|dr/i.test(v)) continue
      const a = parseAmount(v)
      if (a?.indicator === 'DR') dr++
      else if (a?.indicator === 'CR') cr++
    }
    usualIndicator.set(c, dr === cr ? null : dr > cr ? 'DR' : 'CR')
  }
  const balanceCtx: BalanceContext = { balanceCols, debitCols, creditCols, usualIndicator }

  const out: TableRow[] = []
  const excluded: ExcludedRow[] = []
  let openingBalance: number | null = null
  let closingBalance: number | null = null

  for (let i = 0; i < sliced.length; i++) {
    const cells = sliced[i]
    const sourceRow = headerRowIndex + 1 + i
    let reason: ExclusionReason | null = null

    let filled = 0
    let textCells = 0
    let numericCells = 0
    let headerHits = 0
    for (let c = 0; c < width; c++) {
      const v = cells[c]
      if (isEmpty(v)) continue
      filled++
      if (typeof v === 'number') numericCells++
      else if (typeof v === 'string') {
        if (parseAmount(v) !== null) numericCells++
        else textCells++
        const hk = headerKeys[c]
        if (hk !== null && v.replace(/\s+/g, ' ').trim().toLowerCase() === hk) headerHits++
      }
    }

    if (filled === 0) reason = 'blank'
    else {
      reason = keywordReason(cells, hasDate[i], rowHasMovement(cells, balanceCols))
      if (reason === null && headerFilled >= 2 && headerHits >= Math.max(2, Math.ceil(headerFilled * 0.6))) {
        reason = 'repeated-header'
      }
      if (reason === null && dateDriven && !hasDate[i] && numericCells > 0 && textCells === 0) {
        reason = 'total'
      }
    }

    if (reason === null) {
      const values: Record<string, CellValue> = {}
      for (let c = 0; c < width; c++) values[columns[c]] = cells[c]
      out.push({ id: `r${sourceRow + 1}`, sourceRow, values })
      continue
    }

    excluded.push({ sourceRow, reason, values: cells })
    if (reason === 'opening-balance' && openingBalance === null) openingBalance = balanceOf(cells, balanceCtx)
    if (reason === 'closing-balance') {
      const b = balanceOf(cells, balanceCtx)
      if (b !== null) closingBalance = b
    }
  }

  return {
    fileName: opts.fileName,
    sheetName: sheet.name,
    headerRowIndex,
    columns,
    rows: out,
    excluded,
    openingBalance,
    closingBalance
  }
}
