// Suggests a match-key type for a column from its header and a sample of values.

import type { CellValue, ColumnType } from '../contracts'
import { parseAmount } from './amount'
import { EXCEL_SERIAL_MAX, EXCEL_SERIAL_MIN, isDateLike } from './date'

const SAMPLE_LIMIT = 500

const DATE_HEADER = /\b(date|dated|dt|day)\b/
const AMOUNT_HEADER =
  /\b(amount|amt|debit|credit|dr|cr|balance|bal|withdrawals?|deposits?|net pay|pay|salary|salaries|basic|allowance|gross|price|rate|total|paid|payments?|receipts?|charges?|fees?|vat|tax|cost|value|outstanding|due|net)\b/
const ID_HEADER =
  /\b(id|code|no|num|number|ref|reference|iban|account|acct|ac|invoice|inv|voucher|doc|document|cheque|chq|emp|employee|staff|serial|sr|lpo|po|order|trn|swift|bic)\b/
const NUMBER_HEADER = /\b(qty|quantity|count|units?|pcs|pieces|days|hours|hrs|age|nos|items?|cartons?|boxes|weight|kg|percent|pct)\b/

type Kind = 'date' | 'money' | 'int' | 'code' | 'text'

function headerText(h: string): string {
  return String(h ?? '')
    .toLowerCase()
    .replace(/a\/c/g, 'account')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

const CODE_RE = /^[A-Za-z0-9][A-Za-z0-9\-/_.#]*$/

function classify(v: CellValue, dateHeader: boolean): Kind | null {
  if (v === null) return null
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? null : 'date'
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) return null
    if (dateHeader && Number.isInteger(v) && v >= EXCEL_SERIAL_MIN && v <= EXCEL_SERIAL_MAX) return 'date'
    return Number.isInteger(v) ? 'int' : 'money'
  }
  const s = v.trim()
  if (s === '') return null
  if (/^\d+$/.test(s)) {
    // Digits stored as text: leading zeros or long runs are codes (employee no., cheque no.).
    if (s.length > 1 && s.startsWith('0')) return 'code'
    if (s.length >= 6) return 'code'
    return 'int'
  }
  if (isDateLike(s)) return 'date'
  const amt = parseAmount(s)
  if (amt !== null) return Number.isInteger(amt.value) && !/[.,]\d{1,2}\b/.test(s) && amt.indicator === null && !/[()]/.test(s) ? 'int' : 'money'
  if (s.length <= 34 && CODE_RE.test(s) && /\d/.test(s)) return 'code'
  return 'text'
}

function sample(values: CellValue[]): CellValue[] {
  const nonEmpty = values.filter((v) => v !== null && !(typeof v === 'string' && v.trim() === ''))
  if (nonEmpty.length <= SAMPLE_LIMIT) return nonEmpty
  const step = nonEmpty.length / SAMPLE_LIMIT
  const out: CellValue[] = []
  for (let i = 0; i < SAMPLE_LIMIT; i++) out.push(nonEmpty[Math.floor(i * step)])
  return out
}

function uniqueness(values: CellValue[]): number {
  if (values.length === 0) return 0
  const set = new Set(values.map((v) => (v instanceof Date ? `d${v.getTime()}` : String(v).trim().toLowerCase())))
  return set.size / values.length
}

function medianDigits(values: CellValue[]): number {
  const lens = values
    .map((v) => String(typeof v === 'number' ? Math.abs(Math.trunc(v)) : String(v).replace(/\D/g, '')).length)
    .sort((a, b) => a - b)
  return lens.length ? lens[Math.floor(lens.length / 2)] : 0
}

/**
 * Suggests the type of a column: 'date', 'amount' (money: decimals, CR/DR, brackets, or Debit/Credit/Amount/
 * Balance-style headers), 'id' (codes, IBANs, invoice or employee numbers — mostly unique), 'number'
 * (quantities and integers that are not IDs) or 'text'.
 */
export function inferColumnType(header: string, values: CellValue[]): ColumnType {
  const h = headerText(header)
  const dateHeader = DATE_HEADER.test(h)
  const amountHeader = AMOUNT_HEADER.test(h) && !dateHeader
  const idHeader = ID_HEADER.test(h)
  const numberHeader = NUMBER_HEADER.test(h)

  const vals = sample(values)
  if (vals.length === 0) {
    if (dateHeader) return 'date'
    if (amountHeader) return 'amount'
    if (idHeader) return 'id'
    if (numberHeader) return 'number'
    return 'text'
  }

  const counts: Record<Kind, number> = { date: 0, money: 0, int: 0, code: 0, text: 0 }
  for (const v of vals) {
    const k = classify(v, dateHeader)
    if (k) counts[k]++
  }
  const n = vals.length
  const share = (k: number): number => k / n
  const numeric = counts.money + counts.int

  if (share(counts.date) >= 0.8) return 'date'

  if (share(numeric) >= 0.8) {
    if (amountHeader && !(idHeader && counts.money === 0 && !/\b(amount|debit|credit|balance)\b/.test(h))) return 'amount'
    if (numberHeader) return 'number'
    if (counts.money / numeric >= 0.2) return idHeader && counts.money === 0 ? 'id' : 'amount'
    if (idHeader) return 'id'
    const uniq = uniqueness(vals)
    if (n >= 5 && uniq >= 0.95 && medianDigits(vals) >= 4) return 'id'
    return 'number'
  }

  const codeLike = counts.code + counts.int
  if (counts.code > 0 && share(codeLike) >= 0.8) {
    if (idHeader || uniqueness(vals) >= 0.5) return 'id'
  }
  if (idHeader && counts.code > 0 && share(codeLike) >= 0.6) return 'id'

  if (amountHeader && share(numeric) >= 0.5) return 'amount'
  if (dateHeader && share(counts.date) >= 0.5) return 'date'
  return 'text'
}
