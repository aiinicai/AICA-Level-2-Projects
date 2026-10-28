// Date parsing: Date cells, Excel serial numbers and the common text formats. Results are local dates at midnight.

import type { CellValue } from '../contracts'

export type DateOrder = 'DMY' | 'MDY'

/** Excel serials accepted as dates: 1-Jan-1950 (18264) to 31-Dec-2099 (73050). */
export const EXCEL_SERIAL_MIN = 18264
export const EXCEL_SERIAL_MAX = 73050

const MONTHS: Record<string, number> = {
  jan: 1, january: 1,
  feb: 2, february: 2,
  mar: 3, march: 3,
  apr: 4, april: 4,
  may: 5,
  jun: 6, june: 6,
  jul: 7, july: 7,
  aug: 8, august: 8,
  sep: 9, sept: 9, september: 9,
  oct: 10, october: 10,
  nov: 11, november: 11,
  dec: 12, december: 12
}

const WEEKDAY_PREFIX = /^(mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*\.?,?\s+/i
const TIME_SUFFIX = /(?:[T\s]+\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?\s*(?:[ap]\.?m\.?)?(?:Z|[+-]\d{2}:?\d{2})?)$/i
const RE_ISO = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/
const RE_NUMERIC = /^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})$/
const RE_DAY_MONTH_NAME = /^(\d{1,2})(?:st|nd|rd|th)?[\s\-/.,]*([a-z]{3,9})\.?[\s\-/.,]*(\d{2}|\d{4})$/i
const RE_MONTH_NAME_DAY = /^([a-z]{3,9})\.?[\s\-/.]*(\d{1,2})(?:st|nd|rd|th)?,?[\s\-/.,]*(\d{2}|\d{4})$/i
const RE_COMPACT = /^(19|20|21)(\d{2})(\d{2})(\d{2})$/

/** Builds a local date at midnight, or null when the parts are not a real calendar date. */
export function makeDate(year: number, month: number, day: number): Date | null {
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) return null
  if (year < 1900 || year > 2199 || month < 1 || month > 12 || day < 1 || day > 31) return null
  const d = new Date(year, month - 1, day)
  if (d.getFullYear() !== year || d.getMonth() !== month - 1 || d.getDate() !== day) return null
  return d
}

function expandYear(y: string): number {
  const n = Number(y)
  if (y.length === 4) return n
  return n < 50 ? 2000 + n : 1900 + n
}

/** Converts an Excel serial number (1900 date system) to a local date at midnight. */
export function excelSerialToDate(serial: number): Date | null {
  if (!Number.isFinite(serial) || serial < EXCEL_SERIAL_MIN || serial > EXCEL_SERIAL_MAX) return null
  const whole = Math.floor(serial)
  return new Date(1899, 11, 30 + whole)
}

/**
 * Parses a date. Accepts Date objects, Excel serials in a plausible range (1950-2099) and text such as
 * "03/09/2026", "3-Sep-2026", "03-SEP-26", "2026-09-03", "Sep 3, 2026", "03.09.2026".
 * Numeric text uses `order` (default DMY, the UAE convention); when a part cannot be a month
 * (e.g. "09/23/2026" read as DMY) the other order is used. Returns null for anything invalid.
 */
export function parseDate(v: CellValue, order: DateOrder = 'DMY'): Date | null {
  if (v === null || v === undefined) return null
  if (v instanceof Date) {
    const t = v.getTime()
    if (Number.isNaN(t)) return null
    return makeDate(v.getFullYear(), v.getMonth() + 1, v.getDate())
  }
  if (typeof v === 'number') return excelSerialToDate(v)
  return parseDateText(String(v), order)
}

function parseDateText(raw: string, order: DateOrder): Date | null {
  let s = raw.trim()
  if (s.length < 6 || s.length > 40) return null
  s = s.replace(WEEKDAY_PREFIX, '')
  s = s.replace(TIME_SUFFIX, '').trim()

  let m = RE_ISO.exec(s)
  if (m) return makeDate(Number(m[1]), Number(m[2]), Number(m[3]))

  m = RE_NUMERIC.exec(s)
  if (m) {
    const a = Number(m[1])
    const b = Number(m[2])
    const y = expandYear(m[3])
    const primary = order === 'DMY' ? makeDate(y, b, a) : makeDate(y, a, b)
    if (primary) return primary
    // Fall back to the other order only when the preferred order is impossible (a part above 12).
    if (a > 12 || b > 12) return order === 'DMY' ? makeDate(y, a, b) : makeDate(y, b, a)
    return null
  }

  m = RE_DAY_MONTH_NAME.exec(s)
  if (m) {
    const month = MONTHS[m[2].toLowerCase()]
    return month ? makeDate(expandYear(m[3]), month, Number(m[1])) : null
  }

  m = RE_MONTH_NAME_DAY.exec(s)
  if (m) {
    const month = MONTHS[m[1].toLowerCase()]
    return month ? makeDate(expandYear(m[3]), month, Number(m[2])) : null
  }

  m = RE_COMPACT.exec(s)
  if (m) return makeDate(Number(m[1] + m[2]), Number(m[3]), Number(m[4]))

  return null
}

/** True when the text looks like a date in one of the supported formats (any order). */
export function isDateText(s: string): boolean {
  return parseDateText(s, 'DMY') !== null || parseDateText(s, 'MDY') !== null
}

/**
 * Looks at numeric text dates ("03/09/2026") and decides the day/month order.
 * Returns 'DMY' or 'MDY' when values prove it (a part above 12), 'ambiguous' when every numeric text date
 * could be read either way or the evidence conflicts. When no value needs an order (only Date cells,
 * month-name or ISO dates) the UAE default 'DMY' is returned because nothing has to be asked.
 */
export function detectDateOrder(values: CellValue[]): 'DMY' | 'MDY' | 'ambiguous' {
  let dmy = 0
  let mdy = 0
  let undecided = 0
  for (const v of values) {
    if (typeof v !== 'string') continue
    let s = v.trim().replace(WEEKDAY_PREFIX, '')
    s = s.replace(TIME_SUFFIX, '').trim()
    const m = RE_NUMERIC.exec(s)
    if (!m) continue
    const a = Number(m[1])
    const b = Number(m[2])
    const y = expandYear(m[3])
    const asDmy = makeDate(y, b, a) !== null
    const asMdy = makeDate(y, a, b) !== null
    if (asDmy && !asMdy) dmy++
    else if (asMdy && !asDmy) mdy++
    else if (asDmy && asMdy) undecided++
  }
  if (dmy === 0 && mdy === 0) return undecided > 0 ? 'ambiguous' : 'DMY'
  if (mdy === 0) return 'DMY'
  if (dmy === 0) return 'MDY'
  // Conflicting evidence: accept a clear majority (≥ 95%), otherwise ask.
  const total = dmy + mdy
  if (dmy / total >= 0.95) return 'DMY'
  if (mdy / total >= 0.95) return 'MDY'
  return 'ambiguous'
}

/** True when a value is a date (Date cell or date-like text). Numbers are never treated as dates here. */
export function isDateLike(v: CellValue): boolean {
  if (v instanceof Date) return !Number.isNaN(v.getTime())
  if (typeof v === 'string') {
    const s = v.trim()
    if (s.length < 6 || s.length > 40) return false
    const c = s.charCodeAt(0)
    // Quick reject: dates start with a digit or a letter.
    if (!((c >= 48 && c <= 57) || (c >= 65 && c <= 90) || (c >= 97 && c <= 122))) return false
    return isDateText(s)
  }
  return false
}
