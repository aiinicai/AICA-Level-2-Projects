// File and sheet naming helpers shared by the workbook builder and the wizard UI.

import type { ReconSession } from '../shared/contracts'
import type { ModuleId } from '../shared/modules'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const MODULE_FILE_TAGS: Record<ModuleId, string> = {
  bank: 'Bank',
  ar: 'AR',
  ap: 'AP',
  general: 'General',
  gl: 'GL',
  cc: 'CC'
}

/** Excel's hard limit for worksheet names. */
export const MAX_SHEET_NAME = 31

/**
 * Makes a string safe as an Excel worksheet name: strips `[ ] : * ? / \`, trims leading/trailing
 * apostrophes and spaces, and cuts it to 31 characters. Never returns an empty string.
 */
export function sanitiseSheetName(name: string, fallback = 'Sheet'): string {
  let s = name.replace(/[[\]:*?/\\]/g, '').replace(/\s+/g, ' ')
  s = s.replace(/^['\s]+|['\s]+$/g, '')
  if (s.length > MAX_SHEET_NAME) s = s.slice(0, MAX_SHEET_NAME).replace(/['\s]+$/g, '')
  return s.length > 0 ? s : fallback.slice(0, MAX_SHEET_NAME)
}

/**
 * Returns a sanitised sheet name that does not collide (case-insensitively) with `taken`.
 * Adds " (2)", " (3)"… inside the 31-character limit when needed, and records the result in `taken`.
 */
export function uniqueSheetName(name: string, taken: Set<string>, fallback = 'Sheet'): string {
  const base = sanitiseSheetName(name, fallback)
  let candidate = base
  let n = 2
  while (taken.has(candidate.toLowerCase())) {
    const suffix = ` (${n})`
    candidate = `${base.slice(0, MAX_SHEET_NAME - suffix.length).replace(/\s+$/, '')}${suffix}`
    n++
  }
  taken.add(candidate.toLowerCase())
  return candidate
}

/** Keeps letters, digits and dashes; spaces and separators become single dashes. */
export function sanitiseFilePart(s: string): string {
  return s
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/['’`".,/\\]/g, '')
    .replace(/[^A-Za-z0-9-]+/g, '-')
    .replace(/-{2,}/g, '-')
    .replace(/^-+|-+$/g, '')
}

function monthIndex(token: string): number {
  const t = token.slice(0, 3).toLowerCase()
  return MONTHS.findIndex((m) => m.toLowerCase() === t)
}

/** Month-and-year candidates found in a period string, in order of appearance. */
function monthYearsIn(period: string): Array<{ month: number; year: number }> {
  const found: Array<{ month: number; year: number; at: number }> = []
  // "Sep 2026", "September-2026", "Sep-26", "Sep'26" (two-digit years only after - or ').
  const named = /\b([A-Za-z]{3,9})(?:[\s\-/.,]*(\d{4})|[-'’](\d{2}))\b/g
  for (let m = named.exec(period); m; m = named.exec(period)) {
    const idx = monthIndex(m[1])
    if (idx >= 0 && (m[1].length === 3 || MONTHS_FULL[idx].startsWith(m[1].toLowerCase()))) {
      const y = m[2] ? Number(m[2]) : 2000 + Number(m[3])
      found.push({ month: idx, year: y, at: m.index })
    }
  }
  const numeric = /\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b/g
  for (let m = numeric.exec(period); m; m = numeric.exec(period)) {
    const month = Number(m[2]) - 1
    if (month >= 0 && month < 12) found.push({ month, year: Number(m[3]), at: m.index })
  }
  const iso = /\b(\d{4})-(\d{2})(?:-(\d{2}))?\b/g
  for (let m = iso.exec(period); m; m = iso.exec(period)) {
    const month = Number(m[2]) - 1
    if (month >= 0 && month < 12) found.push({ month, year: Number(m[1]), at: m.index })
  }
  return found.sort((a, b) => a.at - b.at).map(({ month, year }) => ({ month, year }))
}

const MONTHS_FULL = [
  'january',
  'february',
  'march',
  'april',
  'may',
  'june',
  'july',
  'august',
  'september',
  'october',
  'november',
  'december'
]

/** "September 2026", "01-Sep-2026 to 30-Sep-2026", "2026-09" → "Sep-2026"; otherwise a sanitised copy. */
export function periodFileTag(period: string): string {
  const found = monthYearsIn(period)
  if (found.length > 0) {
    const first = found[0]
    const last = found[found.length - 1]
    const tag = (x: { month: number; year: number }): string => `${MONTHS[x.month]}-${x.year}`
    return first.month === last.month && first.year === last.year ? tag(last) : `${tag(first)}_to_${tag(last)}`
  }
  return sanitiseFilePart(period)
}

/** Local-midnight date only when year/month/day form a real calendar date (no rolling 31-Feb into March). */
function validDate(year: number, monthIndex0: number, day: number): Date | null {
  if (!Number.isInteger(year) || !Number.isInteger(monthIndex0) || !Number.isInteger(day)) return null
  if (monthIndex0 < 0 || monthIndex0 > 11 || day < 1 || day > 31) return null
  const d = new Date(year, monthIndex0, day)
  if (Number.isNaN(d.getTime()) || d.getFullYear() !== year || d.getMonth() !== monthIndex0 || d.getDate() !== day) return null
  return d
}

/**
 * Best-effort end date of a period string (local midnight), used as the ageing as-of date.
 * "September 2026" → 30-Sep-2026; "01-Sep-2026 to 30-Sep-2026" → 30-Sep-2026. Null when not recognisable.
 * The last explicit date in the text is the end date. An impossible one ("31 Feb 2026") is rejected rather than
 * rolled over into March; the period is then read from its month and year (→ 28-Feb-2026).
 */
export function periodEndDate(period: string): Date | null {
  let last: { at: number; date: Date | null } | null = null
  const consider = (at: number, date: Date | null): void => {
    if (!last || at >= last.at) last = { at, date }
  }
  const explicit = /\b(\d{1,2})[\s\-/.]([A-Za-z]{3,9})[\s\-/.,]*(\d{4})\b/g
  for (let m = explicit.exec(period); m; m = explicit.exec(period)) {
    const idx = monthIndex(m[2])
    if (idx >= 0) consider(m.index, validDate(Number(m[3]), idx, Number(m[1])))
  }
  const isoDay = /\b(\d{4})-(\d{2})-(\d{2})\b/g
  for (let m = isoDay.exec(period); m; m = isoDay.exec(period)) {
    consider(m.index, validDate(Number(m[1]), Number(m[2]) - 1, Number(m[3])))
  }
  const chosen = last as { at: number; date: Date | null } | null
  if (chosen && chosen.date) return chosen.date
  const found = monthYearsIn(period)
  if (found.length === 0) return null
  const lastMonth = found[found.length - 1]
  return new Date(lastMonth.year, lastMonth.month + 1, 0)
}

/**
 * Suggested export file name, e.g. `Reco-Do_Bank_ENBD-Current-Ac_Sep-2026.xlsx`.
 * `ext` may be given with or without the leading dot.
 */
export function exportFileName(session: ReconSession, ext: string): string {
  const moduleTag = MODULE_FILE_TAGS[session.result.config.moduleId] ?? 'Recon'
  const parts = ['Reco-Do', moduleTag]
  const account = sanitiseFilePart(session.meta.accountLabel)
  if (account) parts.push(account)
  const period = periodFileTag(session.meta.period)
  if (period) parts.push(period)
  const cleanExt = ext.replace(/^\.+/, '').replace(/[^A-Za-z0-9]/g, '').toLowerCase()
  const base = parts.join('_').slice(0, 150)
  return cleanExt ? `${base}.${cleanExt}` : base
}

const TO_RECONCILE_PREFIX = 'To Reconcile — '

/**
 * "To Reconcile — <side>" kept within 31 characters: a long side name is shortened with an ellipsis
 * ("To Reconcile — General ledger…") rather than cut mid-word at the sheet-name limit.
 */
export function toReconcileBaseName(sideName: string): string {
  const room = MAX_SHEET_NAME - TO_RECONCILE_PREFIX.length
  let side = sanitiseSheetName(sideName, 'File')
  if (side.length > room) side = `${side.slice(0, room - 1).trimEnd()}…`
  return `${TO_RECONCILE_PREFIX}${side}`
}
