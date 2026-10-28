// Public types of the Merge Files engine.

import type { CellValue, ColumnType } from '@shared/contracts'

/** One table taken from one input: a sheet of an Excel/CSV file or a table extracted from a PDF. */
export interface MergeSource {
  /** Unique within one merge, e.g. "0:Jul 2026" (file index + sheet). */
  id: string
  /** Position of the input file in the list (0-based), used to keep sources of one file together. */
  fileIndex: number
  fileName: string
  /** Sheet name (Excel / CSV) or table name (PDF, e.g. "Table 1"). */
  sheetName: string
  kind: 'sheet' | 'pdf'
  /** Column headers as found in the file (unique). */
  columns: string[]
  rows: MergeSourceRow[]
  /** Rows dropped while reading the file (blank, repeated header, total, opening / closing balance…). */
  excluded: MergeExcludedRow[]
  /** 1-based Excel row of the header (sheets only). */
  headerRow?: number
  /** Header detection confidence 0..1 (sheets only). */
  headerConfidence?: number
  /** Total number of sheets in the workbook (sheets only), so the UI can offer the others. */
  sheetCount?: number
}

export interface MergeSourceRow {
  /** Value of the "Sheet / Page" column: the sheet name, or "Page 3" for PDFs. */
  sheetOrPage: string
  /** Where the row came from, for messages: "Row 12" or "Page 3". */
  location: string
  values: Record<string, CellValue>
}

export interface MergeExcludedRow {
  sourceId: string
  fileName: string
  sheetName: string
  /** "Row 31" (Excel row number) or "Page 2". */
  location: string
  /** Plain-English reason, e.g. "Repeated header row", "Total row". */
  reason: string
  /** The row's text, cells joined with " | ". */
  text: string
}

/** Output column, or null to drop the source column. */
export type ColumnTarget = string | null

/**
 * How source columns land in the output. `columns` is the output order (without the added
 * "Source file" and "Sheet / Page" columns). `sources[sourceId][sourceColumn]` is an output column name or null (dropped).
 */
export interface MergeMapping {
  columns: string[]
  sources: Record<string, Record<string, ColumnTarget>>
}

export interface MergeOptions {
  mapping: MergeMapping
  /** Output column to sort by (dates are sorted as dates). Null / omitted keeps the file order. */
  sortBy?: string | null
  sortDirection?: 'asc' | 'desc'
  /** Day/month order for numeric text dates. Omit to detect (DMY when ambiguous; `needsDateOrder` is set). */
  dateOrder?: 'DMY' | 'MDY'
  /** Add "Source file" and "Sheet / Page" columns. Default true. */
  addSourceColumns?: boolean
  /** Turn text numbers and text dates into real values. Default true. */
  convertValues?: boolean
  /** Sources to leave out (ids). */
  skipSources?: string[]
}

export interface MergeOutputColumn {
  name: string
  type: ColumnType
  /** True for the added "Source file" / "Sheet / Page" columns. */
  added?: boolean
}

export interface MergeRow {
  sourceId: string
  values: CellValue[]
}

export interface MergeSummaryLine {
  sourceId: string
  fileName: string
  sheetName: string
  rowsTaken: number
  rowsExcluded: number
  /** Source columns that were dropped. */
  droppedColumns: string[]
}

export interface MergeResult {
  columns: MergeOutputColumn[]
  rows: MergeRow[]
  excluded: MergeExcludedRow[]
  summary: MergeSummaryLine[]
  detectedDateOrder: 'DMY' | 'MDY' | 'ambiguous'
  dateOrder: 'DMY' | 'MDY'
  /** True when numeric text dates are ambiguous and no order was given: ask DD/MM or MM/DD. */
  needsDateOrder: boolean
  /** Rows without a usable value in the sort column (kept at the end). */
  unsortedRows: number
}

/**
 * Everything "Save settings as recipe" keeps for Merge Files (stored as `ToolRecipe.options`).
 * Column choices are kept by header name so they apply to next month's files.
 */
export interface MergeFilesRecipeOptions {
  /** Output columns in order. */
  columns: string[]
  /** Normalised source header (see `headerKey`) → output column, or null to drop it. */
  headerMap: Record<string, ColumnTarget>
  sortBy: string | null
  sortDirection: 'asc' | 'desc'
  addSourceColumns: boolean
  convertValues: boolean
  dateOrder?: 'DMY' | 'MDY'
}

export const SOURCE_FILE_COLUMN = 'Source file'
export const SHEET_PAGE_COLUMN = 'Sheet / Page'
