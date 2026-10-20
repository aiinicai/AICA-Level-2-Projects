// Pure helpers for the wizard screens: guesses for account and period, step status lines, plain-English texts.

import type { CellValue, ColumnType, ExclusionReason, ParsedTable, ReconConfig, ReconSession, SampleFile } from '@shared/contracts'
import type { ModuleId, SignConvention } from '@shared/modules'
import { formatDate } from '@shared/format'
import { inferColumnType, parseDate } from '@shared/parsing'
import type { WizardState } from './types'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** Words that describe the kind of file rather than the account, dropped from account guesses. */
const FILE_WORDS = new Set(['our', 'ar', 'ap', 'ledger', 'statement', 'soa', 'extract', 'report', 'export', 'file', 'copy', 'final', 'xlsx', 'xls', 'csv'])
const PERIOD_TOKEN = /^(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*[-']?\d{0,4}$|^\d{4}([-_.]?\d{2})?$|^\d{1,2}$/i

/** "ENBD_Current_Statement_Sep2026.xlsx" → "ENBD Current"; "Our_AR_Ledger_AlNoor_Trading.xlsx" → "AlNoor Trading". */
export function accountFromFileName(fileName: string): string {
  const base = fileName.replace(/^.*[\\/]/, '').replace(/\.[^.]+$/, '')
  const words = base
    .split(/[\s_\-.]+/)
    .filter(Boolean)
    .filter((w) => !FILE_WORDS.has(w.toLowerCase()) && !PERIOD_TOKEN.test(w))
  return words.join(' ').trim()
}

export function guessAccountLabel(moduleId: ModuleId, fileA: string | null, sideAName: string, sideBName: string): string {
  if (moduleId === 'general') return sideAName && sideBName ? `${sideAName} vs ${sideBName}` : ''
  return fileA ? accountFromFileName(fileA) : ''
}

/** "Sep 2026" when both dates fall in one month, otherwise "01-Aug-2026 to 30-Sep-2026". */
export function periodFromDates(min: Date, max: Date): string {
  if (min.getFullYear() === max.getFullYear() && min.getMonth() === max.getMonth()) return `${MONTHS[min.getMonth()]} ${min.getFullYear()}`
  return `${formatDate(min)} to ${formatDate(max)}`
}

function sample(table: ParsedTable, col: string, limit = 200): CellValue[] {
  const out: CellValue[] = []
  const step = Math.max(1, Math.floor(table.rows.length / limit))
  for (let i = 0; i < table.rows.length && out.length < limit; i += step) out.push(table.rows[i].values[col] ?? null)
  return out
}

/** Column types for display (sampled, cheap on large files). */
export function columnTypes(table: ParsedTable): Record<string, ColumnType> {
  const out: Record<string, ColumnType> = {}
  for (const c of table.columns) out[c] = inferColumnType(c, sample(table, c))
  return out
}

/** Date range of the first date column (or the given one), or null when the file has no dates. */
export function dateRange(table: ParsedTable, column?: string): { min: Date; max: Date } | null {
  const col = column ?? table.columns.find((c) => inferColumnType(c, sample(table, c)) === 'date')
  if (!col) return null
  let min: Date | null = null
  let max: Date | null = null
  for (const r of table.rows) {
    const d = parseDate(r.values[col] ?? null)
    if (!d || Number.isNaN(d.getTime())) continue
    if (!min || d < min) min = d
    if (!max || d > max) max = d
  }
  return min && max ? { min, max } : null
}

/**
 * Period guess. Looks at every date column of both files and uses the narrowest date range (e.g. the
 * payroll "Pay Date" rather than the employees' join dates). When even that spans more than a quarter,
 * a month-year in the file name wins; otherwise the narrowest range is used.
 */
export function guessPeriod(tables: (ParsedTable | null | undefined)[], fileName: string | null): string {
  let best: { min: Date; max: Date } | null = null
  for (const t of tables) {
    if (!t) continue
    for (const c of t.columns) {
      if (inferColumnType(c, sample(t, c)) !== 'date') continue
      const r = dateRange(t, c)
      if (r && (!best || r.max.getTime() - r.min.getTime() < best.max.getTime() - best.min.getTime())) best = r
    }
  }
  const fromName = fileName ? /(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s_\-']?(\d{4})/i.exec(fileName) : null
  const nameTag = fromName ? `${fromName[1].charAt(0).toUpperCase()}${fromName[1].slice(1, 3).toLowerCase()} ${fromName[2]}` : ''
  if (best && (best.max.getTime() - best.min.getTime() <= 92 * 86_400_000 || !nameTag)) return periodFromDates(best.min, best.max)
  return nameTag
}

/** Shortens long names for tabs and table headers. */
export function clip(name: string, max = 18): string {
  return name.length > max ? `${name.slice(0, max - 1).trimEnd()}…` : name
}

/** Short side names for tabs and KPI labels ("Bank" / "GL"). General uses the user's names. */
export function shortSideNames(moduleId: ModuleId, sideAName: string, sideBName: string): [string, string] {
  switch (moduleId) {
    case 'bank':
      return ['Bank', 'GL']
    case 'ar':
      return ['Ours', 'Customer']
    case 'ap':
      return ['Ours', 'Supplier']
    case 'cc':
      return ['Card', 'Claims']
    default:
      return [sideAName.trim() || 'File A', sideBName.trim() || 'File B']
  }
}

export const EXCLUSION_LABELS: Record<ExclusionReason, string> = {
  blank: 'Blank row',
  'opening-balance': 'Opening balance',
  'closing-balance': 'Closing balance',
  total: 'Total row',
  subtotal: 'Subtotal row',
  'repeated-header': 'Repeated header',
  duplicate: 'Duplicate row'
}

/** Plain-English sign explanation under the toggle. */
export function signExplanation(moduleId: ModuleId, sign: SignConvention, sideA: string, sideB: string): string {
  if (moduleId === 'bank') {
    return sign === 'inverse'
      ? 'Bank Credit = GL Debit. Typical for a bank statement against your cash ledger: money into the bank is a debit in your books.'
      : 'Bank Credit = GL Credit. Use this only when both files show money from the same point of view.'
  }
  if (moduleId === 'ar') {
    return sign === 'inverse'
      ? "Our Debit = customer's Credit. Your invoice is a debit in your ledger and a credit (payable) in the customer's books."
      : "Our Debit = customer's Debit. Use this only when the customer's statement is written from your point of view."
  }
  if (moduleId === 'ap') {
    return sign === 'inverse'
      ? "Our Credit = supplier's Debit. The supplier's invoice is a credit (payable) in your ledger and a debit in their books."
      : "Our Credit = supplier's Credit. Use this only when the supplier's statement is written from your point of view."
  }
  return sign === 'inverse'
    ? `A debit (positive) amount in ${sideA} matches a credit (negative) amount in ${sideB}, e.g. a receivable against the matching payable.`
    : `A positive amount in ${sideA} matches the same positive amount in ${sideB}.`
}

/** The tier rule for the number of keys in use (mockup 4 info box). */
export function tierRuleText(usedKeys: number, hasDate: boolean): string {
  const dateNote = hasDate ? ' A Date key alone can never match.' : ''
  if (usedKeys <= 0) return 'Tick at least one key to match on.'
  if (usedKeys === 1) return `Records match when the key agrees; otherwise they stay unmatched.${dateNote}`
  if (usedKeys === 2) return `Records match when both keys agree. If only one identifying key agrees, the pair is Likely.${dateNote}`
  return `Records match when all ${usedKeys} keys agree. ${usedKeys - 1} of ${usedKeys} = Doubtful. Only one identifying key = Likely.${dateNote}`
}

export function hasAmountKey(cfg: ReconConfig | null | undefined): boolean {
  return !!cfg?.keys.some((k) => k.use && k.type === 'amount')
}

/** The status line under each step label. */
export function stepStatusLines(s: WizardState, configErrors: string[]): string[] {
  const filesRead = (s.files.A ? 1 : 0) + (s.files.B ? 1 : 0)
  const session = s.session
  const upload =
    s.origin === 'resumed' ? (s.session?.finalised ? 'Locked after sign-off' : 'From recon history') : filesRead === 2 ? 'Both files read' : filesRead === 1 ? '1 of 2 files read' : 'Choose two files'
  let map = s.moduleId === 'general' ? 'Pick columns to match' : 'Columns, keys, sign'
  if (s.config && s.origin !== 'resumed') {
    const used = s.config.keys.filter((k) => k.use).length
    map = configErrors.length > 0 ? `${configErrors.length} issue${configErrors.length === 1 ? '' : 's'} to fix` : `${used} key${used === 1 ? '' : 's'} ready`
  } else if (s.origin === 'resumed') {
    map = `${s.config?.keys.filter((k) => k.use).length ?? 0} keys used`
  }
  let run = 'Exact match'
  let smart = 'AI on leftovers'
  let review = 'Excel / PDF'
  if (session) {
    const st = session.result.stats
    run = `${st.matched} matched · ${st.unmatchedA + st.unmatchedB} open`
    const pending = session.suggestions.filter((x) => x.status === 'open').length
    smart = pending > 0 ? `${pending} suggestion${pending === 1 ? '' : 's'} pending` : session.suggestions.length > 0 ? 'Suggestions reviewed' : 'AI on leftovers'
    review = session.finalised ? `Signed off by ${session.finalised.by}` : 'Review, sign off, export'
  }
  return [upload, map, run, smart, review]
}

/** The two sample files for a module ("Try with sample files"). General has two sample sets. */
export interface SampleSet {
  id: string
  label: string
  description: string
  match: [RegExp, RegExp]
  folder: string
  sideNames?: [string, string]
}

export const SAMPLE_SETS: Record<'bank' | 'ar' | 'ap' | 'general', SampleSet[]> = {
  bank: [{ id: 'bank', label: 'ENBD statement vs GL 101200', description: 'Sep 2026 bank statement and GL cash account', folder: 'bank', match: [/enbd|statement/i, /^gl_|ledger|cash/i] }],
  ar: [{ id: 'ar', label: 'Al Noor Trading', description: 'Our AR ledger and the customer SOA', folder: 'ar', match: [/^our_ar|ledger/i, /soa|statement/i] }],
  ap: [{ id: 'ap', label: 'Gulf Supplies', description: 'Our AP ledger and the supplier SOA', folder: 'ap', match: [/^our_ap|ledger/i, /soa|statement/i] }],
  general: [
    {
      id: 'hr',
      label: 'HR master vs WPS payroll (no amount)',
      description: 'Employee ID, IBAN and name, no amount key',
      folder: 'general',
      match: [/hr_employee|employee_master/i, /wps|payroll/i],
      sideNames: ['HR employee master', 'WPS payroll register']
    },
    {
      id: 'intercompany',
      label: 'Intercompany Entity A vs B',
      description: 'IC reference, date and amount',
      folder: 'general',
      match: [/entitya|entity_a/i, /entityb|entity_b/i],
      sideNames: ['Desert Pearl Trading LLC (Dubai)', 'Desert Pearl Industries LLC (Abu Dhabi)']
    }
  ]
}

/** Finds the two sample files of a set in the bundled list. Throws a plain-English error when one is missing. */
export function pickSampleFiles(set: SampleSet, list: SampleFile[]): [SampleFile, SampleFile] {
  const inFolder = list.filter((f) => f.folder === set.folder && /\.(xlsx|xls|csv)$/i.test(f.name))
  const a = inFolder.find((f) => set.match[0].test(f.name))
  const b = inFolder.find((f) => f !== a && set.match[1].test(f.name))
  if (!a || !b) throw new Error('The sample files for this module are missing from this installation.')
  return [a, b]
}

/** True when the session can no longer change. */
export function isLocked(session: ReconSession | null): boolean {
  return !!session?.finalised
}
