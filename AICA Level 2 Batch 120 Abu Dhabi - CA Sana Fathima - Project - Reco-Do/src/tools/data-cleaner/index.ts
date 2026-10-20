// Data Cleaner engine. Pure TypeScript, no React.
//
//   const wb = readWorkbook(buffer, 'Expenses.xlsx')                  // @shared/parsing
//   const prepared = prepareSheet(wb.sheets[0], 'Expenses.xlsx')       // header detection + junk-row kinds
//   const options = suggestOptions(prepared)                          // sensible defaults per column
//   const preview = previewCounts(prepared, options)                  // count per action, shown next to each checkbox
//   const result = runCleaner(prepared, options)                      // cleaned table, changed cells tracked
//   const xlsx = await cleanToWorkbook(prepared, result)              // cleaned sheet (changes highlighted) + "Original"

import type { CellValue, RawSheet } from '@shared/contracts'
import { detectDateOrder, detectHeaderRow, inferColumnType, parseAmount, parseDate, parseTable } from '@shared/parsing'
import { ToolError } from '../common'
import { headerConcept } from '../merge-files/align'
import { CHANGED_FILL, FLAGGED_FILL, newWorkbook, uniqueSheetName, workbookBytes, writeRawSheet, writeTableSheet } from '../merge-files/excel'
import * as A from './actions'
import {
  ACTION_ORDER,
  REMOVABLE_REASONS,
  type ActionReport,
  type CleanerAction,
  type CleanerOptions,
  type CleanResult,
  type CleanRow,
  type CleanTable,
  type PreparedSheet,
  type RemovableReason
} from './types'

export * from './types'
export {
  cleanSpaces,
  changeCase,
  signedAmount,
  sameValue,
  valueText,
  REASON_LABEL,
  DUPLICATE_COLUMN,
  removeRows as countOrRemoveRows,
  trim as countOrTrim,
  fillDown as countOrFillDown,
  numbers as countOrConvertNumbers,
  dates as countOrConvertDates,
  amount as countOrSplitAmount,
  textCase as countOrChangeCase,
  duplicates as countOrFlagDuplicates,
  type ActionOutcome
} from './actions'

/**
 * Reads one sheet for cleaning: detects the header row (or uses the one given) and marks junk rows
 * (blank, repeated header, subtotal, total, opening / closing balance) with the shared parser's rules.
 */
export function prepareSheet(sheet: RawSheet, fileName: string, headerRowIndex?: number): PreparedSheet {
  if (!sheet.rows.some((r) => r.some((v) => v !== null && v !== ''))) {
    throw new ToolError('empty-result', `The sheet "${sheet.name}" is empty.`)
  }
  const detected = detectHeaderRow(sheet.rows)
  const parsed = parseTable(sheet, { fileName, headerRowIndex: headerRowIndex ?? detected.index })
  const junk = new Map<number, RemovableReason>()
  for (const e of parsed.excluded) if (e.reason !== 'duplicate') junk.set(e.sourceRow, e.reason)
  const width = parsed.columns.length
  const rows: CleanRow[] = []
  for (let r = parsed.headerRowIndex + 1; r < sheet.rows.length; r++) {
    const src = sheet.rows[r] ?? []
    const cells = []
    for (let c = 0; c < width; c++) {
      const v = src[c] ?? null
      cells.push({ value: v, original: v })
    }
    rows.push({ sourceRow: r, cells, junk: junk.get(r) ?? null })
  }
  if (rows.length === 0) throw new ToolError('empty-result', 'There are no rows below the header to clean.')
  return {
    fileName,
    sheetName: sheet.name,
    original: sheet.rows,
    headerRowIndex: parsed.headerRowIndex,
    headerConfidence: headerRowIndex === undefined ? detected.confidence : 1,
    table: { fileName, sheetName: sheet.name, headerRowIndex: parsed.headerRowIndex, columns: [...parsed.columns], rows, removed: [] }
  }
}

function dataRows(p: PreparedSheet): CleanRow[] {
  return p.table.rows.filter((r) => r.junk === null)
}

function columnValues(p: PreparedSheet, c: number): CellValue[] {
  return dataRows(p).map((r) => r.cells[c].value)
}

/**
 * Text that must stay text even though it reads as a number: codes with leading zeros ("0101", "001234567890"),
 * phone numbers ("+971 50 123 4567") and space-grouped digit runs without decimals ("4111 1111 1111 1111").
 */
export function isCodeLikeText(v: CellValue): boolean {
  if (typeof v !== 'string') return false
  const s = v.trim()
  return /^0\d/.test(s) || /^\+\s*\d/.test(s) || /^\d+(?:[\s\u00a0]+\d+)+$/.test(s)
}

/** Columns that hold text numbers ("1,234.50", "(500.00)", "750.00-", "1,234.50 CR"). Code and phone columns are never suggested. */
export function suggestNumberColumns(p: PreparedSheet): string[] {
  return p.table.columns.filter((name, c) => {
    const vals = columnValues(p, c).filter((v) => !A.isBlank(v))
    if (vals.length === 0) return false
    if (vals.some(isCodeLikeText)) return false
    const type = inferColumnType(name, vals)
    if (type === 'id' || type === 'date') return false
    let text = 0
    let num = 0
    for (const v of vals) {
      if (typeof v === 'number') num++
      else if (typeof v === 'string' && parseAmount(v)) text++
    }
    return text > 0 && (text + num) / vals.length >= 0.6
  })
}

/** Columns that hold text dates. */
export function suggestDateColumns(p: PreparedSheet): string[] {
  return p.table.columns.filter((name, c) => {
    const vals = columnValues(p, c).filter((v) => !A.isBlank(v))
    if (vals.length === 0) return false
    let text = 0
    let ok = 0
    for (const v of vals) {
      if (v instanceof Date) ok++
      else if (typeof v === 'string' && parseDate(v, 'DMY') !== null) {
        ok++
        text++
      }
    }
    return text > 0 && (ok / vals.length >= 0.6 || inferColumnType(name, vals) === 'date')
  })
}

/** Columns that look like a merged-cell layout: a value followed by runs of blanks (e.g. Category). */
export function suggestFillDownColumns(p: PreparedSheet): string[] {
  const rows = dataRows(p).filter((r) => r.cells.some((c) => !A.isBlank(c.value)))
  if (rows.length < 3) return []
  return p.table.columns.filter((_, c) => {
    const vals = rows.map((r) => r.cells[c].value)
    if (A.isBlank(vals[0])) return false
    const filled = vals.filter((v) => !A.isBlank(v))
    const blankShare = 1 - filled.length / vals.length
    if (blankShare < 0.3 || blankShare > 0.97) return false
    return filled.every((v) => typeof v === 'string')
  })
}

export interface DateInfo {
  detected: 'DMY' | 'MDY' | 'ambiguous'
  /** Distinct text dates that read as a valid date both ways (e.g. 03/09/2026). */
  ambiguous: string[]
}

/** Day/month evidence in the chosen columns, for the DD/MM vs MM/DD question. */
export function dateInfo(p: PreparedSheet, columns: string[]): DateInfo {
  const values: CellValue[] = []
  const ambiguous = new Set<string>()
  for (const name of columns) {
    const c = p.table.columns.indexOf(name)
    if (c < 0) continue
    for (const v of columnValues(p, c)) {
      values.push(v)
      if (typeof v !== 'string') continue
      const m = /^\s*(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})\s*$/.exec(v)
      if (!m) continue
      const a = Number(m[1])
      const b = Number(m[2])
      if (a >= 1 && a <= 12 && b >= 1 && b <= 12 && a !== b && parseDate(v, 'DMY') && parseDate(v, 'MDY')) ambiguous.add(v.trim())
    }
  }
  return { detected: detectDateOrder(values), ambiguous: [...ambiguous] }
}

/** Default options for a sheet: junk rows, spaces, text numbers/dates, fill-down columns and duplicate flags on. */
export function suggestOptions(p: PreparedSheet): CleanerOptions {
  const numberCols = suggestNumberColumns(p)
  const dateCols = suggestDateColumns(p)
  const fillCols = suggestFillDownColumns(p)
  const info = dateInfo(p, dateCols)
  const debit = p.table.columns.find((c) => headerConcept(c) === 'debit')
  const credit = p.table.columns.find((c) => headerConcept(c) === 'credit')
  const amountCol = numberCols[0] ?? p.table.columns.find((c) => headerConcept(c) === 'amount') ?? p.table.columns[0]
  return {
    removeRows: { enabled: true, reasons: [...REMOVABLE_REASONS] },
    trim: { enabled: true },
    fillDown: { enabled: fillCols.length > 0, columns: fillCols },
    numbers: { enabled: numberCols.length > 0, columns: numberCols, crNegative: true },
    dates: { enabled: dateCols.length > 0, columns: dateCols, order: info.detected === 'MDY' ? 'MDY' : 'DMY' },
    amount:
      debit && credit
        ? { enabled: false, mode: 'combine', debit, credit, name: 'Amount', positiveIs: 'debit', crNegative: true }
        : { enabled: false, mode: 'split', column: amountCol, debitName: 'Debit', creditName: 'Credit', positiveIs: 'debit', crNegative: true },
    textCase: { enabled: false, columns: [], mode: 'proper' },
    duplicates: { enabled: true, mode: 'flag' }
  }
}

/** Fills in anything missing from stored options (e.g. an older recipe) with the suggestions. */
export function withDefaults(p: PreparedSheet, partial: Partial<CleanerOptions>): CleanerOptions {
  const d = suggestOptions(p)
  const out = { ...d }
  for (const k of ACTION_ORDER) {
    const v = partial[k]
    if (v) (out as Record<CleanerAction, unknown>)[k] = { ...d[k], ...v }
  }
  return out
}

function cloneTable(t: CleanTable): CleanTable {
  return {
    ...t,
    columns: [...t.columns],
    removed: [...t.removed],
    rows: t.rows.map((r) => ({ ...r, cells: r.cells.map((c) => ({ ...c })) }))
  }
}

function step(action: CleanerAction, t: CleanTable, o: CleanerOptions, commit: boolean): A.ActionOutcome {
  switch (action) {
    case 'removeRows':
      return A.removeRows(t, o.removeRows, commit)
    case 'trim':
      return A.trim(t, o.trim, commit)
    case 'fillDown':
      return A.fillDown(t, o.fillDown, commit)
    case 'numbers':
      return A.numbers(t, o.numbers, commit)
    case 'dates':
      return A.dates(t, o.dates, commit)
    case 'amount':
      return A.amount(t, o.amount, commit)
    case 'textCase':
      return A.textCase(t, o.textCase, commit)
    case 'duplicates':
      return A.duplicates(t, o.duplicates, commit)
  }
}

export function isChanged(cell: { value: CellValue; original: CellValue | undefined }): boolean {
  return cell.original === undefined ? cell.value !== null : !A.sameValue(cell.value, cell.original)
}

/**
 * Runs the enabled actions in order (remove rows, trim, fill down, numbers, dates, split/combine, case,
 * duplicates). Each report's count is taken at the action's place in that order, so the numbers next to
 * the checkboxes match what Download will do; a disabled action reports what it would change if ticked.
 */
export function runCleaner(p: PreparedSheet, o: CleanerOptions): CleanResult {
  const t = cloneTable(p.table)
  const reports: ActionReport[] = []
  for (const action of ACTION_ORDER) {
    const enabled = o[action].enabled
    const outcome = step(action, t, o, enabled)
    reports.push({ action, enabled, ...outcome })
  }
  let changedCells = 0
  for (const r of t.rows) for (const c of r.cells) if (isChanged(c)) changedCells++
  return { table: t, reports, changedCells }
}

/** Count per action (cells or rows it will change) without keeping the cleaned table. */
export function previewCounts(p: PreparedSheet, o: CleanerOptions): Record<CleanerAction, ActionReport> {
  const { reports } = runCleaner(p, o)
  return Object.fromEntries(reports.map((r) => [r.action, r])) as Record<CleanerAction, ActionReport>
}

// ───────────────────────── Output ─────────────────────────

/** Notes are written for at most this many changed cells (Excel slows down with very many notes). */
const MAX_NOTES = 5000

/**
 * Cleaned workbook: the cleaned sheet with changed cells shaded amber (with a note showing the value before),
 * the original sheet as "Original" for audit, and a "Removed rows" sheet listing every row taken out.
 */
export async function cleanToWorkbook(p: PreparedSheet, result: CleanResult): Promise<Uint8Array> {
  const t = result.table
  if (t.rows.length === 0) throw new ToolError('empty-result', 'Every row was removed, so there is nothing to save.')
  const wb = newWorkbook()
  const used = new Set<string>()
  const cleanName = uniqueSheetName(p.sheetName.toLowerCase() === 'original' ? 'Cleaned' : p.sheetName, used)
  const ws = wb.addWorksheet(cleanName)
  const types = t.columns.map((name, c) => inferColumnType(name, t.rows.map((r) => r.cells[c].value)))
  let notes = 0
  writeTableSheet(
    ws,
    t.columns.map((name, c) => ({ name, type: types[c] })),
    t.rows.map((r) => r.cells.map((c) => c.value)),
    {
      style: (r, c) => {
        const row = t.rows[r]
        const cell = row.cells[c]
        if (c === t.flagColumn && row.duplicateOf !== undefined) return { fill: FLAGGED_FILL }
        if (!isChanged(cell)) return undefined
        if (cell.original === undefined || notes >= MAX_NOTES) return { fill: CHANGED_FILL }
        notes++
        const before = A.valueText(cell.original)
        return { fill: CHANGED_FILL, note: before === '' ? 'Was blank before cleaning.' : `Before cleaning: ${before}` }
      }
    }
  )

  const orig = wb.addWorksheet(uniqueSheetName('Original', used))
  writeRawSheet(orig, p.original)

  if (t.removed.length > 0) {
    const rem = wb.addWorksheet(uniqueSheetName('Removed rows', used))
    writeTableSheet(
      rem,
      [{ name: 'Excel row', type: 'number' }, { name: 'Reason', type: 'text' }, ...p.table.columns.map((name) => ({ name }))],
      [...t.removed].sort((a, b) => a.sourceRow - b.sourceRow).map((x) => [x.sourceRow + 1, x.label, ...p.table.columns.map((_, c) => p.original[x.sourceRow]?.[c] ?? null)])
    )
  }
  return workbookBytes(wb)
}
