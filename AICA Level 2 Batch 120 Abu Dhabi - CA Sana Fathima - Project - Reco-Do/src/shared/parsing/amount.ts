// Amount parsing: turns the many ways accounting files write money into one number.

import type { CellValue } from '../contracts'

export interface ParsedAmount {
  /** The number as written, including any minus sign, brackets or trailing minus. A CR/DR suffix does not change the sign. */
  value: number
  /** Present when the text carries a CR / DR marker ("1,234.50 CR"). */
  indicator: 'DR' | 'CR' | null
}

const EMPTY_MARKERS = new Set(['', '-', '--', '–', '—', '−'])
const CURRENCY_SYMBOLS = /^[$€£¥₹]|[$€£¥₹]$/
const CURRENCY_CODES =
  'AED|USD|EUR|GBP|SAR|QAR|OMR|KWD|BHD|INR|PKR|EGP|JOD|LKR|PHP|BDT|NPR|CHF|JPY|CNY|CAD|AUD|NZD|SGD|HKD|ZAR|TRY|RUB|DHS|DH|RS'
const CURRENCY_CODE_START = new RegExp(String.raw`^(?:${CURRENCY_CODES})\.?\s*(?=[\d(.\-+−])`, 'i')
const CURRENCY_CODE_END = new RegExp(String.raw`(?<=[\d).\-−])\s*(?:${CURRENCY_CODES})\.?$`, 'i')
/** "1,234.50 CR", "1,234.50CR", "1,234.50 Dr." */
const INDICATOR_END = /(?:^|(?<=[\d\s).\-−]))(cr|dr)\.?$/i
/** "CR 1,234.50", "Dr. 500": a space or bracket must follow, so codes like "DR26080001" are not amounts. */
const INDICATOR_START = /^(cr|dr)(?:\.\s*|\s+)(?=[\d(.\-−])|^(cr|dr)(?=\()/i
const MINUS_CHARS = /[−–—]/g
/** "+971 50 123 4567", "+44 20 7946 0958": an international phone number, never an amount. */
const PHONE_LIKE = /^\+\s*\d{1,4}(?:[\s-]\d{2,4}){2,}$/
const GROUP_SPACES = /[\s   ']/g

export interface ParseAmountOptions {
  /**
   * The column's decimal separator, when known (see `detectDecimalSeparator`). With ',' a text like "1.234"
   * reads as 1234 (dot = thousands); with '.' "1,234" is 1234 and a lone comma is never a decimal point.
   * Omitted: decided per value, as before.
   */
  decimal?: '.' | ','
}

/**
 * Parses a money value. Handles numbers, "1,234.50", European "1.234,50" (only when unambiguous),
 * "(500.00)", "750.00-", "-750.00", "1,234.50 CR", "1,234.50 Dr", "AED 1,200.00", "1,200.00 AED".
 * Blank cells and a lone "-" return null, as does anything that is not an amount (including phone numbers
 * such as "+971 50 123 4567").
 */
export function parseAmount(v: CellValue, opts?: ParseAmountOptions): ParsedAmount | null {
  if (v === null || v === undefined) return null
  if (typeof v === 'number') return Number.isFinite(v) ? { value: v === 0 ? 0 : v, indicator: null } : null
  if (v instanceof Date) return null
  return parseAmountText(String(v), opts?.decimal)
}

/**
 * The decimal separator a column uses, judged from values that can only be read one way ("1.234,56", "12,5",
 * "1,234.56", "0.75"). Returns null when the column gives no evidence or the evidence is split evenly.
 */
export function detectDecimalSeparator(values: CellValue[]): '.' | ',' | null {
  let dot = 0
  let comma = 0
  let seen = 0
  for (const v of values) {
    if (typeof v !== 'string') continue
    if (++seen > 2000) break
    const s = v.replace(/[^\d.,]/g, '')
    if (!/\d/.test(s)) continue
    const lastComma = s.lastIndexOf(',')
    const lastDot = s.lastIndexOf('.')
    if (lastComma >= 0 && lastDot >= 0) {
      if (lastDot > lastComma) dot++
      else comma++
    } else if (lastComma >= 0) {
      // "12,5" / "1234,56": a comma followed by 1-2 digits (or more than one comma group mismatch) is a decimal comma.
      if (/^\d+,\d{1,2}$/.test(s)) comma++
    } else if (lastDot >= 0) {
      if (/^\d+\.\d{1,2}$/.test(s) || /^0\.\d+$/.test(s)) dot++
      else if (/^\d{1,3}(\.\d{3}){2,}$/.test(s)) comma++
    }
  }
  if (dot === comma) return null
  return dot > comma ? '.' : ','
}

function parseAmountText(raw: string, decimal?: '.' | ','): ParsedAmount | null {
  let s = raw.trim().replace(MINUS_CHARS, '-')
  if (EMPTY_MARKERS.has(s)) return null
  if (s.length > 40) return null
  if (PHONE_LIKE.test(s)) return null

  let indicator: 'DR' | 'CR' | null = null
  let negative = false

  // Peel off wrappers (currency, CR/DR, brackets, signs) until nothing changes.
  for (let guard = 0; guard < 8; guard++) {
    const before = s
    s = s.trim()
    let m = INDICATOR_END.exec(s)
    if (m && indicator === null) {
      indicator = m[1].toUpperCase() as 'DR' | 'CR'
      s = s.slice(0, m.index)
      continue
    }
    m = INDICATOR_START.exec(s)
    if (m && indicator === null) {
      indicator = (m[1] ?? m[2]).toUpperCase() as 'DR' | 'CR'
      s = s.slice(m[0].length)
      continue
    }
    if (CURRENCY_SYMBOLS.test(s)) {
      s = s.replace(CURRENCY_SYMBOLS, '')
      continue
    }
    if (CURRENCY_CODE_START.test(s)) {
      s = s.replace(CURRENCY_CODE_START, '')
      continue
    }
    if (CURRENCY_CODE_END.test(s)) {
      s = s.replace(CURRENCY_CODE_END, '')
      continue
    }
    if (s.startsWith('(') && s.endsWith(')')) {
      if (negative) return null
      negative = true
      s = s.slice(1, -1)
      continue
    }
    if (s.endsWith('-') && s.length > 1) {
      if (negative) return null
      negative = true
      s = s.slice(0, -1)
      continue
    }
    if (s.startsWith('-')) {
      if (negative) return null
      negative = true
      s = s.slice(1)
      continue
    }
    if (s.startsWith('+')) {
      s = s.slice(1)
      continue
    }
    if (s === before) break
  }

  if (!validSpaceGrouping(s.trim())) return null
  const n = parseNumberBody(s.replace(GROUP_SPACES, ''), decimal)
  if (n === null) return null
  const value = negative ? -n : n
  return { value: value === 0 ? 0 : value, indicator }
}

/** Parses an unsigned number with thousands and decimal separators. */
function parseNumberBody(s: string, decimal?: '.' | ','): number | null {
  if (s === '' || !/^[\d.,]+$/.test(s) || !/\d/.test(s)) return null
  if (decimal) return parseWithSeparator(s, decimal)
  const lastComma = s.lastIndexOf(',')
  const lastDot = s.lastIndexOf('.')
  let normalised: string

  if (lastComma >= 0 && lastDot >= 0) {
    if (lastDot > lastComma) {
      // 1,234.50 — commas group thousands
      // Western (1,234,567.89) or Indian (12,34,567.89) grouping
      if (!/^\d{1,3}(,\d{3})*\.\d*$/.test(s) && !/^\d{1,2}(,\d{2})*,\d{3}\.\d*$/.test(s)) return null
      normalised = s.replace(/,/g, '')
    } else {
      // 1.234,50 — European
      if (!/^\d{1,3}(\.\d{3})*,\d*$/.test(s)) return null
      normalised = s.replace(/\./g, '').replace(',', '.')
    }
  } else if (lastComma >= 0) {
    const commaCount = s.split(',').length - 1
    if (/^\d{1,3}(,\d{3})+$/.test(s) || /^\d{1,2}(,\d{2})+,\d{3}$/.test(s)) {
      normalised = s.replace(/,/g, '') // 1,234 or 1,234,567
    } else if (commaCount === 1 && /^\d*,\d+$/.test(s)) {
      normalised = s.replace(',', '.') // 12,5 or 1234,50 or 1234,567: decimal comma
    } else {
      return null
    }
  } else if (lastDot >= 0) {
    const dotCount = s.split('.').length - 1
    if (dotCount === 1) {
      if (!/^\d*\.\d*$/.test(s)) return null
      normalised = s
    } else if (/^\d{1,3}(\.\d{3})+$/.test(s)) {
      normalised = s.replace(/\./g, '') // 1.234.567 — European thousands
    } else {
      return null
    }
  } else {
    normalised = s
  }

  if (normalised === '.' || normalised === '') return null
  const n = Number(normalised)
  return Number.isFinite(n) ? n : null
}

/**
 * Digits grouped with spaces or apostrophes must be thousands groups ("100 000", "1 234,56", "1'234.50").
 * Other spacing ("050 123 4567", "4111 1111 1111 1111") is a phone or card number, not an amount.
 */
function validSpaceGrouping(s: string): boolean {
  const tokens = s.split(GROUP_SPACES).filter((t) => t !== '')
  if (tokens.length <= 1) return true
  if (!/^\d{1,3}$/.test(tokens[0])) return false
  for (let i = 1; i < tokens.length - 1; i++) if (!/^\d{3}$/.test(tokens[i])) return false
  return /^\d{3}(?:[.,]\d*)?$/.test(tokens[tokens.length - 1])
}

/** Parses with a known decimal separator: the other character may only group thousands (Western or Indian). */
function parseWithSeparator(s: string, decimal: '.' | ','): number | null {
  const group = decimal === '.' ? ',' : '.'
  const parts = s.split(decimal)
  if (parts.length > 2) return null
  const [whole, frac] = parts
  if (frac !== undefined && !/^\d*$/.test(frac)) return null
  let digits: string
  if (whole.includes(group)) {
    // Normalise the grouping character to ',' so one pair of patterns covers both separators.
    const w = group === '.' ? whole.replace(/\./g, ',') : whole
    if (!/^\d{1,3}(,\d{3})+$/.test(w) && !/^\d{1,2}(,\d{2})*,\d{3}$/.test(w)) return null
    digits = w.replace(/,/g, '')
  } else {
    if (!/^\d*$/.test(whole)) return null
    digits = whole
  }
  const normalised = frac !== undefined ? `${digits}.${frac}` : digits
  if (normalised === '.' || normalised === '' || !/\d/.test(normalised)) return null
  const n = Number(normalised)
  return Number.isFinite(n) ? n : null
}
