// Public types of the PDF → Excel engine.

import type { CellValue, ColumnType } from '@shared/contracts'
import type { CanvasFactory, PdfJsOptions } from '../common'

// ───────────────────────── Options ─────────────────────────

/** Columns of the bank statement layout, in output order. */
export const BANK_FIELDS = ['Date', 'Value Date', 'Description', 'Reference', 'Debit', 'Credit', 'Balance'] as const
export type BankField = (typeof BANK_FIELDS)[number]

/** Bank field → source column name (as extracted from the PDF), or null when the PDF has no such column. */
export type BankMapping = Record<BankField, string | null>

/** Per-column changes made in the preview, keyed by the column's default name (source header in 'raw', bank field in 'bank'). */
export type ColumnEdits = Record<string, { name?: string; type?: ColumnType }>

/**
 * Paths to the offline tesseract.js assets (see `src/renderer/src/lib/offlineAssets.ts`). All three are required
 * and must be local (a file path, or a file:, app:, blob: or localhost URL): OCR refuses to start otherwise, so
 * tesseract.js never falls back to downloading them from a CDN.
 */
export interface OcrOptions {
  /** tesseract.js worker script (in Node: `tesseract.js/src/worker-script/node/index.js`). */
  workerPath: string
  /** Folder or file of tesseract.js-core (wasm). In Node the installed `tesseract.js-core` package folder. */
  corePath: string
  /** Folder that holds `eng.traineddata(.gz)`, e.g. `@tesseract.js-data/eng/4.0.0`. */
  langPath: string
  /** True when the traineddata file is gzipped (`eng.traineddata.gz`). Default true. */
  gzip?: boolean
  /** Render resolution for scanned pages. Default 300 dpi. */
  dpi?: number
  /** Cells whose OCR confidence (0-100) is below this are flagged. Default 85. */
  lowConfidenceBelow?: number
}

/** Options that only reshape already-extracted pages (cheap; see `reshapeResult`). */
export interface PdfShapeOptions {
  /** 'raw' keeps the PDF's own headers; 'bank' maps to Date · Value Date · Description · Reference · Debit · Credit · Balance. Default 'raw'. */
  layout?: 'raw' | 'bank'
  /** Overrides for the suggested bank mapping (only the fields given are changed). */
  bankMapping?: Partial<BankMapping>
  /** Join tables that continue across pages (same columns). Default true. */
  joinAcrossPages?: boolean
  /** Drop column-header rows repeated on later pages (listed under excluded rows). Default true. */
  removeRepeatedHeaders?: boolean
  /** Convert text numbers and dates into real values. Default true. */
  convertValues?: boolean
  /** Day/month order for numeric dates such as 03/09/2026. Omit to detect; when ambiguous DMY is used and `needsDateOrder` is set. */
  dateOrder?: 'DMY' | 'MDY'
  /** Renames and type changes from the preview. */
  columnEdits?: ColumnEdits
}

export interface PdfExtractOptions extends PdfShapeOptions, PdfJsOptions {
  /** Pages to read, e.g. "1-3, 5". Default: all pages. */
  pages?: string
  /** OCR settings for scanned pages. Without them scanned pages are skipped with a warning. */
  ocr?: OcrOptions
  /** Canvas factory used to render scanned pages for OCR. Default: pdf.js's own for the environment. */
  canvasFactory?: CanvasFactory
  /** A page with fewer text characters than this is treated as scanned. Default 20. */
  scannedTextThreshold?: number
  /** Source file name, used for sheet names and the Read me sheet. */
  fileName?: string
}

export interface PdfProgress {
  /** 1-based page number being processed. */
  page: number
  /** Number of pages being processed (after the page range). */
  pages: number
  /** 1-based position of this page among the pages being processed (for "3 of 6"). */
  index: number
  stage: 'text' | 'ocr'
}

// ───────────────────────── Page-level extraction (stage 1) ─────────────────────────

/** A word or phrase with its box in PDF points, origin at the top-left of the page. */
export interface PdfWord {
  text: string
  x0: number
  x1: number
  top: number
  bottom: number
  /** Font size (digital) or estimated text height (OCR), in points. */
  size: number
  /** OCR confidence 0-100; undefined for digital text. */
  confidence?: number
}

export type PdfPageMethod = 'text' | 'ocr' | 'scanned-skipped' | 'empty'

export interface PdfPageInfo {
  /** 1-based page number. */
  page: number
  method: PdfPageMethod
  /** Words / text items found on the page. */
  words: number
  /** Mean OCR word confidence 0-100 (OCR pages only). */
  ocrConfidence?: number
}

export type PdfExclusionReason =
  /** The table's column-header row printed again on a later page. */
  | 'repeated-header'
  /** A line printed on most pages (bank name, address, statement period, disclaimers). */
  | 'page-header-footer'
  /** "Page 2 of 6", "Continued", "- 3 -". */
  | 'page-number'
  /** Text above or below the table (titles, notes) that is not a table row. */
  | 'outside-table'

export interface PdfExcludedRow {
  page: number
  text: string
  reason: PdfExclusionReason
  /** Plain-English reason for the preview, e.g. "Repeated on every page". */
  detail: string
}

/** One table row as read from one page, before shaping. */
export interface PdfFragmentRow {
  page: number
  /** Cell text per fragment column. */
  cells: string[]
  /** OCR confidence per cell (minimum of its words), null for digital text or empty cells. */
  confidence: (number | null)[]
  ocr: boolean
  /** Number of PDF text lines merged into this row (2+ when a description wrapped). */
  lines: number
  /** True when this row is the column-header row repeated on a later page. */
  repeatedHeader?: boolean
}

/** The part of a table found on one page. */
export interface PdfFragment {
  page: number
  method: 'text' | 'ocr'
  /** Header texts, one per column ('' where the header cell is empty). */
  header: string[]
  /** False when the page had no header row and the columns came from a previous page or from x-clustering. */
  hasHeader: boolean
  rows: PdfFragmentRow[]
}

// ───────────────────────── Shaped result (stage 2) ─────────────────────────

export interface PdfColumn {
  /** Output name (after renames). */
  name: string
  /** Name before renames: the PDF header in 'raw' layout, the bank field in 'bank' layout. */
  key: string
  type: ColumnType
}

export interface PdfCell {
  /** Converted value (number, Date) when conversion is on and succeeded, else the text; null when empty. */
  value: CellValue
  /** Text as read from the PDF. */
  text: string
  /** OCR confidence 0-100, null for digital text. */
  confidence: number | null
  /** OCR confidence below the threshold: shade amber in the preview and the workbook. */
  lowConfidence: boolean
}

export interface PdfRow {
  /** 1-based page the row came from. */
  page: number
  cells: PdfCell[]
  ocr: boolean
  /** Number of PDF text lines merged into this row (2+ when a description wrapped). */
  lines: number
}

export interface PdfTable {
  /** "Table 1", "Table 2", … */
  name: string
  columns: PdfColumn[]
  rows: PdfRow[]
  /** Pages that contributed rows. */
  pages: number[]
  usedOcr: boolean
}

export interface PdfExtractResult {
  fileName: string
  /** Total pages in the PDF. */
  pageCount: number
  /** Per processed page: how it was read. */
  pages: PdfPageInfo[]
  /** Pages read with OCR (1-based). */
  ocrPages: number[]
  tables: PdfTable[]
  /** Every line that was not turned into a table row, with the reason. */
  excluded: PdfExcludedRow[]
  /** Suggested bank mapping from the first table's headers (always filled, also in 'raw' layout). */
  suggestedBankMapping: BankMapping
  /** Mapping actually used in 'bank' layout (suggestion + overrides). */
  bankMapping: BankMapping | null
  /** Source columns not used by the bank mapping (shown so nothing is lost silently). */
  bankUnmapped: string[]
  /** Day/month order detected from numeric dates. */
  detectedDateOrder: 'DMY' | 'MDY' | 'ambiguous'
  /** Order used for conversion. */
  dateOrder: 'DMY' | 'MDY'
  /** True when dates are ambiguous and no `dateOrder` was given: the UI should ask (DD/MM or MM/DD). */
  needsDateOrder: boolean
  /** Plain-English notes for the user (scanned pages skipped, nothing found on a page, …). */
  warnings: string[]
  /** Low-confidence threshold used (0-100). */
  lowConfidenceBelow: number
  /** Shape options in effect. */
  options: Required<Pick<PdfShapeOptions, 'layout' | 'joinAcrossPages' | 'removeRepeatedHeaders' | 'convertValues'>> & Pick<PdfShapeOptions, 'columnEdits' | 'bankMapping' | 'dateOrder'>
  /** Stage-1 data used by `reshapeResult` to re-apply options without reading the PDF again. */
  fragments: PdfFragment[]
  /** Lines excluded while reading pages (before shaping). */
  pageExcluded: PdfExcludedRow[]
  durationMs: number
}

export interface PdfWorkbookOptions {
  /** One sheet per table (default) or every table on one sheet. */
  oneSheetPerTable?: boolean
  /** Add a "Page" column for traceability. Default true. */
  addPageColumn?: boolean
  /** Add the "Excluded rows" sheet when rows were excluded. Default true. */
  includeExcludedSheet?: boolean
}

/**
 * Everything a "Save settings as recipe" needs for PDF → Excel (store as `ToolRecipe.options`).
 * Runtime-only parts (pdf.js instance, OCR asset paths, canvas factory) are supplied again when the recipe runs.
 */
export type PdfToExcelRecipeOptions = PdfShapeOptions & PdfWorkbookOptions & { pages?: string }
