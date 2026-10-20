// Recipes: "Save settings as recipe" for PDF → Excel, Merge Files and Data Cleaner.
// Stored in IndexedDB (lib/db.ts) as ToolRecipe; `options` is `unknown` there, so every read is validated here
// and anything malformed is ignored rather than trusted.

import type { ColumnType, RecipeTool, ToolRecipe } from '@shared/contracts'
import type { CleanerOptions, DataCleanerRecipeOptions } from '@tools/data-cleaner'
import { REMOVABLE_REASONS } from '@tools/data-cleaner'
import type { ColumnTarget, MergeFilesRecipeOptions } from '@tools/merge-files'
import { BANK_FIELDS, type BankMapping, type ColumnEdits, type PdfToExcelRecipeOptions } from '@tools/pdf-to-excel'

type Obj = Record<string, unknown>

const isObj = (v: unknown): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v)
const bool = (v: unknown): boolean | undefined => (typeof v === 'boolean' ? v : undefined)
const str = (v: unknown): string | undefined => (typeof v === 'string' ? v : undefined)
const strArr = (v: unknown): string[] | undefined => (Array.isArray(v) && v.every((x) => typeof x === 'string') ? (v as string[]) : undefined)
const oneOf = <T extends string>(v: unknown, values: readonly T[]): T | undefined => (typeof v === 'string' && (values as readonly string[]).includes(v) ? (v as T) : undefined)
const COLUMN_TYPES: ColumnType[] = ['id', 'text', 'amount', 'number', 'date']
const ORDERS = ['DMY', 'MDY'] as const

function defined<T extends Obj>(o: T): T {
  return Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined)) as T
}

export function asPdfToExcelRecipe(v: unknown): PdfToExcelRecipeOptions | null {
  if (!isObj(v)) return null
  let bankMapping: Partial<BankMapping> | undefined
  if (isObj(v.bankMapping)) {
    bankMapping = {}
    for (const f of BANK_FIELDS) {
      const m = v.bankMapping[f]
      if (m === null || typeof m === 'string') bankMapping[f] = m
    }
  }
  let columnEdits: ColumnEdits | undefined
  if (isObj(v.columnEdits)) {
    columnEdits = {}
    for (const [k, e] of Object.entries(v.columnEdits)) {
      if (!isObj(e)) continue
      columnEdits[k] = defined({ name: str(e.name), type: oneOf(e.type, COLUMN_TYPES) })
    }
  }
  return defined({
    layout: oneOf(v.layout, ['raw', 'bank'] as const),
    bankMapping,
    joinAcrossPages: bool(v.joinAcrossPages),
    removeRepeatedHeaders: bool(v.removeRepeatedHeaders),
    convertValues: bool(v.convertValues),
    dateOrder: oneOf(v.dateOrder, ORDERS),
    columnEdits,
    oneSheetPerTable: bool(v.oneSheetPerTable),
    addPageColumn: bool(v.addPageColumn),
    includeExcludedSheet: bool(v.includeExcludedSheet),
    pages: str(v.pages)
  })
}

export function asMergeFilesRecipe(v: unknown): MergeFilesRecipeOptions | null {
  if (!isObj(v)) return null
  const columns = strArr(v.columns)
  if (!columns || !isObj(v.headerMap)) return null
  const headerMap: Record<string, ColumnTarget> = {}
  for (const [k, t] of Object.entries(v.headerMap)) if (t === null || typeof t === 'string') headerMap[k] = t
  return {
    columns,
    headerMap,
    sortBy: typeof v.sortBy === 'string' ? v.sortBy : null,
    sortDirection: oneOf(v.sortDirection, ['asc', 'desc'] as const) ?? 'asc',
    addSourceColumns: bool(v.addSourceColumns) ?? true,
    convertValues: bool(v.convertValues) ?? true,
    ...(oneOf(v.dateOrder, ORDERS) ? { dateOrder: oneOf(v.dateOrder, ORDERS) } : {})
  }
}

/** Data Cleaner recipe with only the parts that validate; combine with `withDefaults` from the engine. */
export function asDataCleanerRecipe(v: unknown): { options: Partial<CleanerOptions>; sheetName?: string } | null {
  if (!isObj(v) || !isObj(v.options)) return null
  const o = v.options
  const out: Partial<CleanerOptions> = {}
  const en = (x: Obj): boolean => x.enabled === true
  if (isObj(o.removeRows)) {
    const reasons = (strArr(o.removeRows.reasons) ?? []).filter((r): r is (typeof REMOVABLE_REASONS)[number] => (REMOVABLE_REASONS as string[]).includes(r))
    out.removeRows = { enabled: en(o.removeRows), reasons }
  }
  if (isObj(o.trim)) out.trim = { enabled: en(o.trim) }
  if (isObj(o.fillDown)) out.fillDown = { enabled: en(o.fillDown), columns: strArr(o.fillDown.columns) ?? [] }
  if (isObj(o.numbers)) out.numbers = { enabled: en(o.numbers), columns: strArr(o.numbers.columns) ?? [], crNegative: bool(o.numbers.crNegative) ?? true }
  if (isObj(o.dates)) out.dates = { enabled: en(o.dates), columns: strArr(o.dates.columns) ?? [], order: oneOf(o.dates.order, ORDERS) ?? 'DMY' }
  if (isObj(o.amount)) {
    const a = o.amount
    const positiveIs = oneOf(a.positiveIs, ['debit', 'credit'] as const) ?? 'debit'
    const crNegative = bool(a.crNegative) ?? true
    if (a.mode === 'combine' && str(a.debit) && str(a.credit)) {
      out.amount = { enabled: en(a), mode: 'combine', debit: str(a.debit) ?? '', credit: str(a.credit) ?? '', name: str(a.name) ?? 'Amount', positiveIs, crNegative }
    } else if (a.mode === 'split' && str(a.column)) {
      out.amount = { enabled: en(a), mode: 'split', column: str(a.column) ?? '', debitName: str(a.debitName) ?? 'Debit', creditName: str(a.creditName) ?? 'Credit', positiveIs, crNegative }
    }
  }
  if (isObj(o.textCase)) out.textCase = { enabled: en(o.textCase), columns: strArr(o.textCase.columns) ?? [], mode: oneOf(o.textCase.mode, ['upper', 'lower', 'proper'] as const) ?? 'proper' }
  if (isObj(o.duplicates)) out.duplicates = { enabled: en(o.duplicates), mode: oneOf(o.duplicates.mode, ['flag', 'remove'] as const) ?? 'flag' }
  return { options: out, ...(str(v.sheetName) ? { sheetName: str(v.sheetName) } : {}) }
}

export function dataCleanerRecipe(options: CleanerOptions, sheetName?: string): DataCleanerRecipeOptions {
  return sheetName ? { options, sheetName } : { options }
}

/** Builds a new or updated recipe record (same name + tool = update, keeping the id and creation date). */
export function buildRecipe(tool: RecipeTool, name: string, options: unknown, existing: ToolRecipe[], newId: () => string, now = new Date()): ToolRecipe {
  const clean = name.replace(/\s+/g, ' ').trim()
  if (clean === '') throw new Error('Give the recipe a name.')
  const same = existing.find((r) => r.tool === tool && r.name.toLowerCase() === clean.toLowerCase())
  const at = now.toISOString()
  // Round-trip through JSON so only plain data is stored (no Dates, functions or class instances).
  const plain: unknown = JSON.parse(JSON.stringify(options))
  return { id: same?.id ?? newId(), name: clean, tool, options: plain, createdAt: same?.createdAt ?? at, updatedAt: at }
}
