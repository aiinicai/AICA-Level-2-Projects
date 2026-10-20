// Header-row detection: files often carry logos, addresses and titles above the real header.

import type { CellValue } from '../contracts'
import { parseAmount } from './amount'
import { isDateLike } from './date'

const SCAN_ROWS = 30
const LOOKAHEAD_ROWS = 6

const HEADER_WORDS = new Set([
  'date', 'txn', 'transaction', 'value', 'posting', 'description', 'details', 'narration', 'particulars', 'remarks',
  'reference', 'ref', 'no', 'number', 'doc', 'document', 'voucher', 'cheque', 'chq', 'invoice', 'inv', 'debit', 'credit',
  'dr', 'cr', 'amount', 'balance', 'withdrawal', 'withdrawals', 'deposit', 'deposits', 'party', 'customer', 'supplier',
  'vendor', 'name', 'id', 'code', 'iban', 'account', 'type', 'status', 'department', 'category', 'qty', 'quantity',
  'rate', 'price', 'total', 'net', 'pay', 'salary', 'employee', 'emp', 'bank', 'currency', 'counterparty', 'paid', 'by',
  'group', 'lpo', 'po', 'running', 'join', 'basic', 'staff'
])

type CellKind = 'empty' | 'label' | 'value'

function kindOf(v: CellValue): CellKind {
  if (v === null || v === undefined) return 'empty'
  if (typeof v === 'number' || v instanceof Date) return 'value'
  const s = v.trim()
  if (s === '') return 'empty'
  if (parseAmount(s) !== null || isDateLike(s)) return 'value'
  return 'label'
}

interface RowInfo {
  filled: number
  labels: string[]
  values: number
}

function describe(row: CellValue[] | undefined): RowInfo {
  const info: RowInfo = { filled: 0, labels: [], values: 0 }
  if (!row) return info
  for (const v of row) {
    const k = kindOf(v)
    if (k === 'empty') continue
    info.filled++
    if (k === 'label') info.labels.push(String(v).trim())
    else info.values++
  }
  return info
}

/** Finer cell kind used to compare a candidate header row with the row below it. */
type FineKind = 'empty' | 'label' | 'date' | 'number'

function fineKind(v: CellValue): FineKind {
  if (v === null || v === undefined) return 'empty'
  if (v instanceof Date) return 'date'
  if (typeof v === 'number') return 'number'
  const s = v.trim()
  if (s === '') return 'empty'
  if (isDateLike(s)) return 'date'
  if (parseAmount(s) !== null) return 'number'
  return 'label'
}

/** A value only data carries: a date, or a number with decimals ("1,234.50", 10.5). Bare integers such as years can be headers. */
function strongValue(v: CellValue): boolean {
  if (v instanceof Date) return true
  if (typeof v === 'number') return !Number.isInteger(v)
  if (typeof v !== 'string') return false
  const s = v.trim()
  if (isDateLike(s)) return true
  return parseAmount(s) !== null && /\d[.,]\d{1,2}(?:\D*)$/.test(s)
}

/**
 * True when a row reads as data rather than column names: at least half its cells are values, one of them a
 * date or a decimal amount, and every filled cell has the same kind (text / date / number) as the next row.
 */
export function looksLikeDataRow(row: CellValue[] | undefined, next: CellValue[] | undefined): boolean {
  if (!row || !next) return false
  const info = describe(row)
  if (info.filled < 2 || info.values / info.filled < 0.5) return false
  if (!row.some(strongValue)) return false
  let compared = 0
  for (let c = 0; c < row.length; c++) {
    const k = fineKind(row[c])
    if (k === 'empty') continue
    const n = fineKind(next[c] ?? null)
    if (n === 'empty') continue
    if (n !== k) return false
    compared++
  }
  return compared >= 2
}

// ───────────────────────── two-row headers ─────────────────────────

function isBlankCell(v: CellValue | undefined): boolean {
  return v === null || v === undefined || (typeof v === 'string' && v.trim() === '')
}

function isLabelCell(v: CellValue | undefined): boolean {
  if (typeof v !== 'string') return false
  const s = v.trim()
  return s !== '' && s.length <= 40 && parseAmount(s) === null && !isDateLike(s)
}

/** Two or more labels and no values at all. */
function isLabelOnlyRow(row: CellValue[] | undefined): boolean {
  if (!row) return false
  let labels = 0
  for (const v of row) {
    if (isBlankCell(v)) continue
    if (!isLabelCell(v)) return false
    labels++
  }
  return labels >= 2
}

const SUB_HEADER_WORDS =
  /\b(date|dt|txn|transaction|value|posting|description|details|narration|particulars|reference|ref|no|number|doc|voucher|cheque|chq|invoice|debit|credit|dr|cr|amount|amt|balance|running|withdrawals?|deposits?|aed|usd|eur|gbp|sar|currency|code|name|id|type|in|out|paid|received)\b/i

function subHeaderWordShare(row: CellValue[]): number {
  const labels = row.filter((v) => !isBlankCell(v)).map((v) => String(v))
  if (labels.length === 0) return 0
  return labels.filter((l) => SUB_HEADER_WORDS.test(l)).length / labels.length
}

function hasDataBelow(rows: CellValue[][], from: number): boolean {
  for (let j = from; j < rows.length && j <= from + 5; j++) {
    const row = rows[j]
    if (!row || row.every(isBlankCell)) continue
    return row.some((v) => !isBlankCell(v) && !isLabelCell(v))
  }
  return false
}

/** `rows[top]` and `rows[top + 1]` form one header: both label-only, header words in both, data right below. */
function isHeaderPair(rows: CellValue[][], top: number, strictAlignment: boolean): boolean {
  const upper = rows[top]
  const lower = rows[top + 1]
  if (top < 0 || !upper || !lower || !isLabelOnlyRow(upper) || !isLabelOnlyRow(lower)) return false
  if (subHeaderWordShare(lower) < 0.6) return false
  if (strictAlignment) {
    // Found from the lower row: the upper row must look like headers too, with most of its labels sitting
    // above a label of the lower row (a title line above a header does not).
    if (subHeaderWordShare(upper) < 0.6) return false
    let filled = 0
    let stacked = 0
    for (let c = 0; c < upper.length; c++) {
      if (isBlankCell(upper[c])) continue
      filled++
      if (!isBlankCell(lower[c])) stacked++
    }
    if (stacked < 2 || stacked / filled < 0.5) return false
  }
  return hasDataBelow(rows, top + 2)
}

/**
 * Two-row headers ("Txn" over "Date", "Amount" over "Debit" / "Credit"): given the chosen header row, returns
 * the pair's upper and lower rows when the row below (or, for a chosen lower row, the row above) completes the
 * header. Null for an ordinary one-row header.
 */
export function findTwoRowHeader(rows: CellValue[][], h: number): { top: number; lower: number } | null {
  if (isHeaderPair(rows, h, false)) return { top: h, lower: h + 1 }
  if (isHeaderPair(rows, h - 1, true)) return { top: h - 1, lower: h }
  return null
}

function cellName(v: CellValue | undefined): string {
  if (v === null || v === undefined || v instanceof Date) return ''
  return String(v).replace(/\s+/g, ' ').trim()
}

/**
 * Merges a two-row header column by column: "Txn" + "Date" → "Txn Date". A blank upper cell next to a group
 * label that spans several columns ("Amount" over "Debit" and "Credit") takes that group label: "Amount Credit".
 */
export function mergeHeaderRows(upper: CellValue[], lower: CellValue[]): CellValue[] {
  const width = Math.max(upper.length, lower.length)
  const out: CellValue[] = []
  let group = ''
  for (let c = 0; c < width; c++) {
    const t = cellName(upper[c])
    const b = cellName(lower[c])
    if (t !== '') group = b !== '' ? t : ''
    const head = t !== '' ? t : b !== '' ? group : ''
    out.push([head, b].filter((x) => x !== '').join(' ') || null)
  }
  return out
}

function headerWordShare(labels: string[]): number {
  if (labels.length === 0) return 0
  let hits = 0
  for (const l of labels) {
    const words = l.toLowerCase().split(/[^a-z]+/).filter(Boolean)
    if (words.some((w) => HEADER_WORDS.has(w))) hits++
  }
  return hits / labels.length
}

function median(nums: number[]): number {
  if (nums.length === 0) return 0
  const s = [...nums].sort((a, b) => a - b)
  return s[Math.floor(s.length / 2)]
}

/**
 * Picks the row (0-based) that looks most like a header among the first 30 rows: many non-empty, unique,
 * short text cells with few numbers or dates, followed by rows that contain dates or numbers.
 * `confidence` (0..1) reflects how good the best row looks and how clearly it beats the runner-up.
 *
 * For a two-row header ("Txn" over "Date") the LOWER row is returned; `parseTable` merges the pair.
 * Returns `index: -1` when the file has no header row: the best candidate is itself a data row (mostly values,
 * including a date or a decimal amount, shaped like the row below). `parseTable` then names the columns
 * "Column 1", "Column 2", ... and keeps every row as data.
 */
export function detectHeaderRow(rows: CellValue[][]): { index: number; confidence: number } {
  const limit = Math.min(rows.length, SCAN_ROWS)
  if (limit === 0) return { index: 0, confidence: 0 }

  const infos: RowInfo[] = []
  const scanEnd = Math.min(rows.length, SCAN_ROWS + LOOKAHEAD_ROWS)
  for (let i = 0; i < scanEnd; i++) infos.push(describe(rows[i]))

  // Typical width of the table body: median filled-cell count of the non-empty scanned rows.
  const typicalWidth = Math.max(1, median(infos.filter((r) => r.filled > 0).map((r) => r.filled)))
  const maxWidth = Math.max(1, ...infos.map((r) => r.filled))

  const scores: number[] = []
  for (let i = 0; i < limit; i++) {
    const r = infos[i]
    if (r.filled === 0 || r.labels.length === 0) {
      scores.push(0)
      continue
    }
    const labelShare = r.labels.length / r.filled
    const unique = new Set(r.labels.map((l) => l.toLowerCase())).size / r.labels.length
    const short = r.labels.filter((l) => l.length <= 30).length / r.labels.length
    const coverage = Math.min(1, r.filled / Math.max(typicalWidth, maxWidth * 0.75))

    // Rows below: share of the next non-empty rows that contain a date or a number.
    let below = 0
    let seen = 0
    let widthMatch = 0
    for (let j = i + 1; j < infos.length && seen < LOOKAHEAD_ROWS; j++) {
      const n = infos[j]
      if (n.filled === 0) continue
      seen++
      if (n.values > 0) below++
      widthMatch += Math.min(n.filled, r.filled) / Math.max(n.filled, r.filled)
    }
    const dataBelow = seen ? below / seen : 0
    const widthFit = seen ? widthMatch / seen : 0

    let score =
      0.3 * coverage +
      0.2 * labelShare +
      0.1 * unique +
      0.05 * short +
      0.15 * dataBelow +
      0.1 * widthFit +
      0.1 * headerWordShare(r.labels)
    if (r.filled === 1) score *= 0.5 // a single cell is a title, rarely a header
    scores.push(score)
  }

  let best = 0
  for (let i = 1; i < limit; i++) if (scores[i] > scores[best] + 1e-9) best = i
  // A header repeated further down (page breaks) must not win over its first occurrence.
  const signature = (r: RowInfo): string => r.labels.map((l) => l.toLowerCase()).join('')
  const bestSig = signature(infos[best])
  for (let i = 0; i < best; i++) {
    if (infos[i].labels.length > 0 && signature(infos[i]) === bestSig) {
      best = i
      break
    }
  }
  let second = 0
  for (let i = 0; i < limit; i++) {
    if (i === best || signature(infos[i]) === bestSig) continue
    if (scores[i] > second) second = scores[i]
  }

  const top = scores[best]
  if (top === 0) return { index: 0, confidence: 0 }
  const margin = Math.min(1, (top - second) / 0.25)
  const confidence = Math.round(Math.max(0, Math.min(1, 0.6 * top + 0.4 * margin)) * 100) / 100
  if (looksLikeDataRow(rows[best], nextNonEmpty(rows, best))) return { index: -1, confidence }
  // Two-row header: report the lower row (data starts right below it); parseTable merges the pair.
  const pair = findTwoRowHeader(rows, best)
  return { index: pair ? pair.lower : best, confidence }
}

function nextNonEmpty(rows: CellValue[][], i: number): CellValue[] | undefined {
  for (let j = i + 1; j < rows.length && j <= i + LOOKAHEAD_ROWS; j++) {
    if (describe(rows[j]).filled > 0) return rows[j]
  }
  return undefined
}
