// Public types of the Data Cleaner engine.

import type { CellValue, ExclusionReason } from '@shared/contracts'

/** Row kinds the "remove rows" action can take out (listed, never silent). */
export type RemovableReason = Exclude<ExclusionReason, 'duplicate'>

export const REMOVABLE_REASONS: RemovableReason[] = ['blank', 'repeated-header', 'subtotal', 'total', 'opening-balance', 'closing-balance']

export interface RemoveRowsOptions {
  enabled: boolean
  /** Which kinds of junk rows to remove. Default: all of them. */
  reasons: RemovableReason[]
}

export interface TrimOptions {
  enabled: boolean
}

export interface NumbersOptions {
  enabled: boolean
  /** Columns whose text numbers become real numbers. */
  columns: string[]
  /** "1,234.50 CR" becomes negative (true, default) or "DR" becomes negative (false). */
  crNegative: boolean
}

export interface DatesOptions {
  enabled: boolean
  columns: string[]
  /** Day/month order for numeric text dates such as 03/09/2026. */
  order: 'DMY' | 'MDY'
}

export type AmountOptions =
  | {
      enabled: boolean
      mode: 'split'
      /** Signed amount column to split. */
      column: string
      debitName: string
      creditName: string
      /** Positive amounts go to Debit (default) or Credit. */
      positiveIs: 'debit' | 'credit'
      crNegative: boolean
    }
  | {
      enabled: boolean
      mode: 'combine'
      debit: string
      credit: string
      name: string
      /** Signed amount = Debit - Credit (default 'debit') or Credit - Debit ('credit'). */
      positiveIs: 'debit' | 'credit'
      crNegative: boolean
    }

export interface FillDownOptions {
  enabled: boolean
  columns: string[]
}

export interface DuplicatesOptions {
  enabled: boolean
  /** Flag (default, adds a "Duplicate" column) or remove the second and later copies. */
  mode: 'flag' | 'remove'
}

export type TextCase = 'upper' | 'lower' | 'proper'

export interface TextCaseOptions {
  enabled: boolean
  columns: string[]
  mode: TextCase
}

export interface CleanerOptions {
  removeRows: RemoveRowsOptions
  trim: TrimOptions
  fillDown: FillDownOptions
  numbers: NumbersOptions
  dates: DatesOptions
  amount: AmountOptions
  textCase: TextCaseOptions
  duplicates: DuplicatesOptions
}

export type CleanerAction = keyof CleanerOptions

/** Actions in the order they are applied. */
export const ACTION_ORDER: CleanerAction[] = ['removeRows', 'trim', 'fillDown', 'numbers', 'dates', 'amount', 'textCase', 'duplicates']

/**
 * Everything "Save settings as recipe" keeps for the Data Cleaner (stored as `ToolRecipe.options`).
 * Columns are kept by header name so the recipe applies to next month's export.
 */
export interface DataCleanerRecipeOptions {
  options: CleanerOptions
  /** Preferred sheet name (used when the new file has a sheet with this name). */
  sheetName?: string
}

// ───────────────────────── Working table ─────────────────────────

export interface CleanCell {
  value: CellValue
  /** Value before cleaning; undefined for cells of a column added by the cleaner. */
  original: CellValue | undefined
}

export interface CleanRow {
  /** 0-based row in the source sheet (Excel row = sourceRow + 1). */
  sourceRow: number
  cells: CleanCell[]
  /** Junk-row kind found by the shared parser, if any. */
  junk: RemovableReason | null
  /** Excel row number of the first copy when this row is an exact duplicate (after cleaning). */
  duplicateOf?: number
}

export interface RemovedRow {
  sourceRow: number
  reason: RemovableReason | 'duplicate'
  /** Plain-English reason, e.g. "Subtotal row". */
  label: string
  values: CellValue[]
}

/** A table being cleaned: header + rows below it (rows above the header are titles and stay in "Original"). */
export interface CleanTable {
  fileName: string
  sheetName: string
  headerRowIndex: number
  columns: string[]
  rows: CleanRow[]
  removed: RemovedRow[]
  /** Index of the "Duplicate" flag column, when added. */
  flagColumn?: number
}

export interface PreparedSheet {
  fileName: string
  sheetName: string
  /** The sheet exactly as read (for the "Original" audit sheet). */
  original: CellValue[][]
  headerRowIndex: number
  headerConfidence: number
  table: CleanTable
}

export interface ActionReport {
  action: CleanerAction
  enabled: boolean
  /** Cells or rows the action changes (or would change, when disabled) at its place in the sequence. */
  count: number
  unit: 'cells' | 'rows'
  /** Short plain-English summary, e.g. "9 rows: 4 blank, 4 subtotal, 1 total". */
  summary: string
}

export interface CleanResult {
  table: CleanTable
  reports: ActionReport[]
  /** Number of cells whose value differs from the original (including new columns). */
  changedCells: number
}
