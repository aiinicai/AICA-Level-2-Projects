// The Data Cleaner actions. Each one works on a CleanTable and returns how many cells/rows it changes;
// with `commit = false` it only counts (the "preview count" shown next to each checkbox).

import type { CellValue } from '@shared/contracts'
import { formatDate } from '@shared/format'
import { detectDecimalSeparator, parseAmount, parseDate, type ParsedAmount } from '@shared/parsing'
import type {
  AmountOptions,
  CleanCell,
  CleanTable,
  DatesOptions,
  DuplicatesOptions,
  FillDownOptions,
  NumbersOptions,
  RemovableReason,
  RemoveRowsOptions,
  TextCase,
  TextCaseOptions,
  TrimOptions
} from './types'

export interface ActionOutcome {
  count: number
  unit: 'cells' | 'rows'
  summary: string
}

export const REASON_LABEL: Record<RemovableReason | 'duplicate', string> = {
  blank: 'Blank row',
  'repeated-header': 'Repeated header row',
  subtotal: 'Subtotal row',
  total: 'Total row',
  'opening-balance': 'Opening balance row',
  'closing-balance': 'Closing balance row',
  duplicate: 'Duplicate row'
}

const REASON_PLURAL: Record<RemovableReason, string> = {
  blank: 'blank',
  'repeated-header': 'repeated header',
  subtotal: 'subtotal',
  total: 'total',
  'opening-balance': 'opening balance',
  'closing-balance': 'closing balance'
}

export const DUPLICATE_COLUMN = 'Duplicate'

export function isBlank(v: CellValue | undefined): boolean {
  return v === null || v === undefined || (typeof v === 'string' && v.trim() === '')
}

export function sameValue(a: CellValue | undefined, b: CellValue | undefined): boolean {
  if (a instanceof Date && b instanceof Date) return a.getTime() === b.getTime()
  return (a ?? null) === (b ?? null)
}

function plural(n: number, one: string, many = `${one}s`): string {
  return `${n.toLocaleString('en-US')} ${n === 1 ? one : many}`
}

function columnIndexes(t: CleanTable, names: string[]): number[] {
  const out: number[] = []
  for (const n of names) {
    const i = t.columns.indexOf(n)
    if (i >= 0 && i !== t.flagColumn && !out.includes(i)) out.push(i)
  }
  return out
}

function setCell(cell: CleanCell, value: CellValue): void {
  cell.value = value
}

// ───────────────────────── Remove junk rows ─────────────────────────

export function removeRows(t: CleanTable, o: RemoveRowsOptions, commit: boolean): ActionOutcome {
  const wanted = new Set(o.reasons)
  const counts = new Map<RemovableReason, number>()
  const keep = []
  for (const row of t.rows) {
    if (row.junk && wanted.has(row.junk)) {
      counts.set(row.junk, (counts.get(row.junk) ?? 0) + 1)
      if (commit) t.removed.push({ sourceRow: row.sourceRow, reason: row.junk, label: REASON_LABEL[row.junk], values: row.cells.map((c) => c.original ?? null) })
    } else keep.push(row)
  }
  if (commit) t.rows = keep
  const total = [...counts.values()].reduce((a, b) => a + b, 0)
  const parts = [...counts.entries()].map(([r, n]) => `${n} ${REASON_PLURAL[r]}`)
  return { count: total, unit: 'rows', summary: total ? `${plural(total, 'row')}: ${parts.join(', ')}` : 'No junk rows found' }
}

// ───────────────────────── Trim spaces and non-printing characters ─────────────────────────

const NON_PRINTING = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F\u00AD\u200B-\u200D\u2060\uFEFF]/g
const ANY_SPACE = /[\s\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000]+/g

/** Removes non-printing characters, turns non-breaking and repeated spaces into one space and trims. */
export function cleanSpaces(s: string): string {
  return s.replace(NON_PRINTING, '').replace(ANY_SPACE, ' ').trim()
}

export function trim(t: CleanTable, _o: TrimOptions, commit: boolean): ActionOutcome {
  let n = 0
  for (const row of t.rows) {
    for (const cell of row.cells) {
      if (typeof cell.value !== 'string') continue
      const c = cleanSpaces(cell.value)
      if (c === cell.value) continue
      n++
      if (commit) setCell(cell, c === '' ? null : c)
    }
  }
  return { count: n, unit: 'cells', summary: n ? `${plural(n, 'cell')} with extra or hidden spaces` : 'No extra spaces found' }
}

// ───────────────────────── Fill down ─────────────────────────

export function fillDown(t: CleanTable, o: FillDownOptions, commit: boolean): ActionOutcome {
  const cols = columnIndexes(t, o.columns)
  let n = 0
  for (const c of cols) {
    let last: CellValue = null
    for (const row of t.rows) {
      const cell = row.cells[c]
      if (!isBlank(cell.value)) {
        last = cell.value
        continue
      }
      // Never fill a completely blank row (it is a separator, not part of a merged block).
      if (row.cells.every((x) => isBlank(x.value))) continue
      if (last === null) continue
      n++
      if (commit) setCell(cell, last)
    }
  }
  return { count: n, unit: 'cells', summary: cols.length ? `${plural(n, 'blank cell')} filled from above` : 'Choose the columns to fill' }
}

// ───────────────────────── Text numbers → numbers ─────────────────────────

/** Applies a CR / DR marker: with `crNegative` "CR" amounts are negative, otherwise "DR" amounts are. */
export function signedAmount(a: ParsedAmount, crNegative: boolean): number {
  const abs = Math.abs(a.value)
  if (a.indicator === 'CR') return crNegative ? -abs : abs
  if (a.indicator === 'DR') return crNegative ? abs : -abs
  return a.value
}

/** The decimal separator a column's text numbers use ("1.234,56" → ','), so "1.234" there reads as 1234. */
function columnDecimal(t: CleanTable, c: number): '.' | ',' | undefined {
  return detectDecimalSeparator(t.rows.map((r) => r.cells[c]?.value ?? null)) ?? undefined
}

export function numbers(t: CleanTable, o: NumbersOptions, commit: boolean): ActionOutcome {
  const cols = columnIndexes(t, o.columns)
  const decimals = new Map(cols.map((c) => [c, columnDecimal(t, c)]))
  let n = 0
  for (const row of t.rows) {
    for (const c of cols) {
      const cell = row.cells[c]
      if (typeof cell.value !== 'string') continue
      const a = parseAmount(cell.value, { decimal: decimals.get(c) })
      if (!a) continue
      n++
      if (commit) setCell(cell, signedAmount(a, o.crNegative))
    }
  }
  return { count: n, unit: 'cells', summary: cols.length ? `${plural(n, 'text number')} to convert` : 'Choose the columns to convert' }
}

// ───────────────────────── Text dates → dates ─────────────────────────

export function dates(t: CleanTable, o: DatesOptions, commit: boolean): ActionOutcome {
  const cols = columnIndexes(t, o.columns)
  let n = 0
  for (const row of t.rows) {
    for (const c of cols) {
      const cell = row.cells[c]
      if (typeof cell.value !== 'string') continue
      const d = parseDate(cell.value, o.order)
      if (!d) continue
      n++
      if (commit) setCell(cell, d)
    }
  }
  return { count: n, unit: 'cells', summary: cols.length ? `${plural(n, 'text date')} to convert (${o.order === 'DMY' ? 'DD/MM' : 'MM/DD'})` : 'Choose the columns to convert' }
}

// ───────────────────────── Split / combine Debit and Credit ─────────────────────────

function amountOf(v: CellValue, crNegative: boolean, decimal?: '.' | ','): number | null {
  if (typeof v === 'number') return v
  if (typeof v !== 'string') return null
  const a = parseAmount(v, { decimal })
  return a ? signedAmount(a, crNegative) : null
}

/** Decimal places a value is written with (3 for KWD / BHD / OMR amounts such as "1.234" or 12.345). */
function decimalsOf(v: CellValue, decimal?: '.' | ','): number {
  if (typeof v === 'number') {
    if (!Number.isFinite(v) || Number.isInteger(v)) return 0
    const m = /\.(\d+)$/.exec(String(v))
    return m ? Math.min(6, m[1].length) : 0
  }
  if (typeof v !== 'string') return 0
  const sep = decimal ?? (/,\d{1,3}\D*$/.test(v) && !/\.\d/.test(v) ? ',' : '.')
  const m = new RegExp(`\\${sep}(\\d+)\\D*$`).exec(v)
  return m ? Math.min(6, m[1].length) : 0
}

function uniqueColumn(t: CleanTable, name: string, except: number[] = []): string {
  const taken = new Set(t.columns.filter((_, i) => !except.includes(i)).map((c) => c.toLowerCase()))
  const base = name.trim() || 'Amount'
  if (!taken.has(base.toLowerCase())) return base
  for (let i = 2; ; i++) if (!taken.has(`${base} (${i})`.toLowerCase())) return `${base} (${i})`
}

export function amount(t: CleanTable, o: AmountOptions, commit: boolean): ActionOutcome {
  if (o.mode === 'split') {
    const c = t.columns.indexOf(o.column)
    if (c < 0) return { count: 0, unit: 'rows', summary: 'Choose the amount column to split' }
    let n = 0
    for (const row of t.rows) if (!isBlank(row.cells[c].value)) n++
    if (commit) {
      const debitName = uniqueColumn(t, o.debitName || 'Debit', [c])
      const creditName = uniqueColumn({ ...t, columns: [...t.columns, debitName] }, o.creditName || 'Credit', [c])
      t.columns.splice(c, 1, debitName, creditName)
      for (const row of t.rows) {
        const v = row.cells[c].value
        const a = amountOf(v, o.crNegative)
        let debit: CellValue = null
        let credit: CellValue = null
        if (a !== null && a !== 0) {
          const toDebit = a > 0 === (o.positiveIs === 'debit')
          if (toDebit) debit = Math.abs(a)
          else credit = Math.abs(a)
        } else if (a === 0) {
          debit = 0
        } else if (!isBlank(v)) {
          // Not a number: keep the text where positive amounts go, so nothing is lost.
          if (o.positiveIs === 'debit') debit = v
          else credit = v
        }
        row.cells.splice(c, 1, { value: debit, original: undefined }, { value: credit, original: undefined })
      }
      if (t.flagColumn !== undefined && t.flagColumn > c) t.flagColumn++
    }
    return { count: n, unit: 'rows', summary: `${plural(n, 'amount')} split into ${o.debitName || 'Debit'} / ${o.creditName || 'Credit'}` }
  }
  const d = t.columns.indexOf(o.debit)
  const k = t.columns.indexOf(o.credit)
  if (d < 0 || k < 0 || d === k) return { count: 0, unit: 'rows', summary: 'Choose the Debit and Credit columns' }
  let n = 0
  for (const row of t.rows) if (!isBlank(row.cells[d].value) || !isBlank(row.cells[k].value)) n++
  if (commit) {
    const name = uniqueColumn(t, o.name || 'Amount', [d, k])
    const first = Math.min(d, k)
    const second = Math.max(d, k)
    const decD = columnDecimal(t, d)
    const decK = columnDecimal(t, k)
    for (const row of t.rows) {
      const dv = row.cells[d].value
      const kv = row.cells[k].value
      const da = amountOf(dv, o.crNegative, decD)
      const ka = amountOf(kv, o.crNegative, decK)
      let value: CellValue = null
      if (da !== null || ka !== null) {
        // Keep the precision the amounts are written with (2 for AED, 3 for KWD / BHD / OMR), at least 2.
        const places = Math.max(2, decimalsOf(dv, decD), decimalsOf(kv, decK))
        const scale = 10 ** places
        const net = (da ?? 0) - (ka ?? 0)
        value = Math.round((o.positiveIs === 'debit' ? net : -net) * scale) / scale
        if (value === 0) value = 0
      } else if (!isBlank(dv) || !isBlank(kv)) {
        // Not a number: keep the text (like the split mode does), so nothing is lost.
        value = !isBlank(dv) ? dv : kv
      }
      row.cells.splice(second, 1)
      row.cells.splice(first, 1, { value, original: undefined })
    }
    t.columns.splice(second, 1)
    t.columns.splice(first, 1, name)
    if (t.flagColumn !== undefined && t.flagColumn > second) t.flagColumn--
  }
  return { count: n, unit: 'rows', summary: `${plural(n, 'row')} combined into one signed ${o.name || 'Amount'}` }
}

// ───────────────────────── Text case ─────────────────────────

export function changeCase(s: string, mode: TextCase): string {
  if (mode === 'upper') return s.toUpperCase()
  if (mode === 'lower') return s.toLowerCase()
  return s.toLowerCase().replace(/(^|[\s\-/(&.,'"])(\p{L})/gu, (_m, p: string, l: string) => p + l.toUpperCase())
}

export function textCase(t: CleanTable, o: TextCaseOptions, commit: boolean): ActionOutcome {
  const cols = columnIndexes(t, o.columns)
  let n = 0
  for (const row of t.rows) {
    for (const c of cols) {
      const cell = row.cells[c]
      if (typeof cell.value !== 'string') continue
      const next = changeCase(cell.value, o.mode)
      if (next === cell.value) continue
      n++
      if (commit) setCell(cell, next)
    }
  }
  const label = o.mode === 'upper' ? 'UPPER' : o.mode === 'lower' ? 'lower' : 'Proper'
  return { count: n, unit: 'cells', summary: cols.length ? `${plural(n, 'cell')} to ${label} case` : 'Choose the columns to change' }
}

// ───────────────────────── Exact duplicates ─────────────────────────

function rowKey(cells: CleanCell[], skip: number | undefined): string {
  return JSON.stringify(
    cells.map((c, i) => {
      if (i === skip) return 0
      const v = c.value
      if (v instanceof Date) return `d${v.getTime()}`
      if (typeof v === 'number') return `n${v}`
      return v === null || v === undefined ? null : `s${v}`
    })
  )
}

export function duplicates(t: CleanTable, o: DuplicatesOptions, commit: boolean): ActionOutcome {
  const first = new Map<string, number>()
  const dupes: Array<{ index: number; of: number }> = []
  t.rows.forEach((row, i) => {
    if (row.cells.every((c, ci) => ci === t.flagColumn || isBlank(c.value))) return
    const key = rowKey(row.cells, t.flagColumn)
    const seen = first.get(key)
    if (seen === undefined) first.set(key, row.sourceRow + 1)
    else dupes.push({ index: i, of: seen })
  })
  if (commit && dupes.length > 0) {
    if (o.mode === 'remove') {
      const drop = new Set(dupes.map((d) => d.index))
      t.rows = t.rows.filter((row, i) => {
        if (!drop.has(i)) return true
        t.removed.push({ sourceRow: row.sourceRow, reason: 'duplicate', label: REASON_LABEL.duplicate, values: row.cells.map((c) => c.original ?? null) })
        return false
      })
    } else {
      const name = uniqueColumn(t, DUPLICATE_COLUMN)
      t.columns.push(name)
      t.flagColumn = t.columns.length - 1
      const of = new Map(dupes.map((d) => [d.index, d.of]))
      t.rows.forEach((row, i) => {
        const o2 = of.get(i)
        row.duplicateOf = o2
        row.cells.push({ value: o2 !== undefined ? `Duplicate of row ${o2}` : null, original: o2 !== undefined ? undefined : null })
      })
    }
  }
  const verb = o.mode === 'remove' ? 'to remove' : 'to flag'
  return { count: dupes.length, unit: 'rows', summary: dupes.length ? `${plural(dupes.length, 'duplicate row')} ${verb}` : 'No exact duplicates found' }
}

/** Text of a value for notes and lists. */
export function valueText(v: CellValue | undefined): string {
  if (v === null || v === undefined) return ''
  if (v instanceof Date) return formatDate(v)
  return String(v)
}
