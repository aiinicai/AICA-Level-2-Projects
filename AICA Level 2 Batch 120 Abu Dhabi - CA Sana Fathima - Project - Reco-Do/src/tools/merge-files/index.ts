// Merge Files engine. Pure TypeScript, no React.
//
//   const sources = await loadMergeSources(files, { extractPdf: (data, name) => extractPdf(data, { pdfjs, fileName: name }) })
//   let mapping = suggestMapping(sources)                         // "Txn Date" ↔ "Transaction Date" ↔ "Date" …
//   mapping = setColumnTarget(mapping, sources[1].id, 'Ref No', { separate: true })
//   const result = mergeSources(sources, { mapping, sortBy: 'Txn Date' })
//   const xlsx = await mergeToWorkbook(result)
//
// Excel / CSV inputs go through @shared/parsing (header detection, junk-row exclusion). PDFs are converted
// by the PDF → Excel engine, which the caller passes in so this module stays free of pdf.js set-up.

import type { CellValue, ColumnType, ExclusionReason } from '@shared/contracts'
import { formatDate } from '@shared/format'
import { detectDateOrder, inferColumnType, parseAmount, parseDate, parseTable, readWorkbook } from '@shared/parsing'
import { throwIfAborted, ToolError } from '../common'
import type { PdfExclusionReason, PdfExtractResult } from '../pdf-to-excel/types'
import { newWorkbook, uniqueSheetName, workbookBytes, writeTableSheet } from './excel'
import {
  SHEET_PAGE_COLUMN,
  SOURCE_FILE_COLUMN,
  type MergeExcludedRow,
  type MergeOptions,
  type MergeOutputColumn,
  type MergeResult,
  type MergeRow,
  type MergeSource,
  type MergeSourceRow,
  type MergeSummaryLine
} from './types'

export * from './types'
export {
  suggestMapping,
  setColumnTarget,
  renameOutputColumn,
  moveOutputColumn,
  recipeFromMapping,
  mappingFromRecipe,
  columnSimilarity,
  headerConcept,
  headerKey,
  ALIGN_THRESHOLD
} from './align'

const EXCLUSION_LABEL: Record<ExclusionReason, string> = {
  blank: 'Blank row',
  'opening-balance': 'Opening balance row',
  'closing-balance': 'Closing balance row',
  total: 'Total row',
  subtotal: 'Subtotal row',
  'repeated-header': 'Repeated header row',
  duplicate: 'Duplicate row'
}

const PDF_EXCLUSION_LABEL: Record<PdfExclusionReason, string> = {
  'repeated-header': 'Repeated header row',
  'page-header-footer': 'Page header / footer',
  'page-number': 'Page number',
  'outside-table': 'Outside the table'
}

export function exclusionLabel(reason: ExclusionReason): string {
  return EXCLUSION_LABEL[reason]
}

function cellText(v: CellValue): string {
  if (v === null || v === undefined) return ''
  if (v instanceof Date) return formatDate(v)
  return String(v)
}

function rowText(values: CellValue[]): string {
  return values
    .map(cellText)
    .filter((s) => s.trim() !== '')
    .join(' | ')
}

export interface WorkbookSourceOptions {
  /** 0-based index of the file in the list. Default 0. */
  fileIndex?: number
  /** Which sheets to read: 'first' non-empty sheet (default), 'all' non-empty sheets, or names. */
  sheets?: 'first' | 'all' | string[]
  /** Header row per sheet name (0-based); detected when missing. */
  headerRows?: Record<string, number>
}

/** Reads an Excel / CSV file into merge sources (one per sheet). Throws a ToolError with a plain-English message. */
export function sourcesFromWorkbook(data: ArrayBuffer, fileName: string, opts: WorkbookSourceOptions = {}): MergeSource[] {
  let wb
  try {
    wb = readWorkbook(data, fileName)
  } catch (e) {
    throw new ToolError('invalid-file', `${fileName}: ${e instanceof Error ? e.message : 'the file could not be read.'}`)
  }
  const fileIndex = opts.fileIndex ?? 0
  const pick = opts.sheets ?? 'first'
  const out: MergeSource[] = []
  for (const sheet of wb.sheets) {
    if (Array.isArray(pick) && !pick.includes(sheet.name)) continue
    if (!sheet.rows.some((r) => r.some((v) => v !== null && v !== ''))) continue
    const table = parseTable(sheet, { fileName, headerRowIndex: opts.headerRows?.[sheet.name] })
    if (table.rows.length === 0 && pick !== 'all' && !Array.isArray(pick)) continue
    const id = `${fileIndex}:${sheet.name}`
    out.push({
      id,
      fileIndex,
      fileName,
      sheetName: sheet.name,
      kind: 'sheet',
      columns: table.columns,
      rows: table.rows.map<MergeSourceRow>((r) => ({ sheetOrPage: sheet.name, location: `Row ${r.sourceRow + 1}`, values: r.values })),
      excluded: table.excluded.map<MergeExcludedRow>((e) => ({
        sourceId: id,
        fileName,
        sheetName: sheet.name,
        location: `Row ${e.sourceRow + 1}`,
        reason: EXCLUSION_LABEL[e.reason],
        text: rowText(e.values)
      })),
      headerRow: table.headerRowIndex + 1,
      sheetCount: wb.sheets.length
    })
    if (pick === 'first') break
  }
  if (out.length === 0) throw new ToolError('empty-result', `${fileName}: no table with data rows was found in this file.`)
  return out
}

/** Turns a PDF → Excel result into merge sources (one per extracted table). */
export function sourcesFromPdf(result: PdfExtractResult, fileIndex = 0): MergeSource[] {
  if (result.tables.length === 0) throw new ToolError('empty-result', `${result.fileName}: no table was found in this PDF.`)
  return result.tables.map((t, ti) => {
    const id = `${fileIndex}:${t.name}`
    const columns = t.columns.map((c) => c.name)
    const excluded: MergeExcludedRow[] =
      ti === 0
        ? result.excluded.map((e) => ({
            sourceId: id,
            fileName: result.fileName,
            sheetName: t.name,
            location: `Page ${e.page}`,
            reason: PDF_EXCLUSION_LABEL[e.reason],
            text: e.text
          }))
        : []
    return {
      id,
      fileIndex,
      fileName: result.fileName,
      sheetName: t.name,
      kind: 'pdf' as const,
      columns,
      rows: t.rows.map<MergeSourceRow>((r) => ({
        sheetOrPage: `Page ${r.page}`,
        location: `Page ${r.page}`,
        values: Object.fromEntries(columns.map((c, i) => [c, r.cells[i]?.value ?? null]))
      })),
      excluded
    }
  })
}

export interface LoadSourcesOptions {
  /** PDF → Excel conversion supplied by the caller (e.g. `extractPdf` with pdf.js and OCR assets). */
  extractPdf?: (data: ArrayBuffer, fileName: string, signal?: AbortSignal) => Promise<PdfExtractResult>
  signal?: AbortSignal
  onProgress?: (p: { file: number; files: number; name: string }) => void
}

function isPdf(data: ArrayBuffer, fileName: string): boolean {
  const b = new Uint8Array(data, 0, Math.min(4, data.byteLength))
  return /\.pdf$/i.test(fileName) || (b[0] === 0x25 && b[1] === 0x50 && b[2] === 0x44 && b[3] === 0x46)
}

/** Reads every file (Excel, CSV or PDF) into merge sources, in the order given. */
export async function loadMergeSources(files: { name: string; data: ArrayBuffer }[], opts: LoadSourcesOptions = {}): Promise<MergeSource[]> {
  if (files.length === 0) throw new ToolError('empty-result', 'Add at least one file to merge.')
  const out: MergeSource[] = []
  for (let i = 0; i < files.length; i++) {
    throwIfAborted(opts.signal)
    const f = files[i]
    opts.onProgress?.({ file: i + 1, files: files.length, name: f.name })
    if (isPdf(f.data, f.name)) {
      if (!opts.extractPdf) throw new ToolError('invalid-option', `${f.name}: PDF files cannot be merged here.`)
      let result: PdfExtractResult
      try {
        result = await opts.extractPdf(f.data, f.name, opts.signal)
      } catch (e) {
        if (e instanceof ToolError && e.code !== 'cancelled' && !e.message.startsWith(f.name)) throw new ToolError(e.code, `${f.name}: ${e.message}`, e.detail)
        throw e
      }
      out.push(...sourcesFromPdf(result, i))
    } else {
      out.push(...sourcesFromWorkbook(f.data, f.name, { fileIndex: i }))
    }
  }
  return out
}

// ───────────────────────── Merge ─────────────────────────

function isBlank(v: CellValue | undefined): boolean {
  return v === null || v === undefined || (typeof v === 'string' && v.trim() === '')
}

function convert(v: CellValue, type: ColumnType, order: 'DMY' | 'MDY'): CellValue {
  if (isBlank(v)) return null
  if (type === 'date') {
    if (v instanceof Date) return v
    const d = parseDate(v, order)
    return d ?? v
  }
  if (type === 'amount' || type === 'number') {
    if (typeof v === 'number') return v
    const a = parseAmount(v)
    // A CR/DR marker carries meaning the number alone would lose; keep that text as written.
    return a && a.indicator === null ? a.value : v
  }
  return v
}

function sortKey(v: CellValue, type: ColumnType, order: 'DMY' | 'MDY'): number | string | null {
  if (isBlank(v)) return null
  if (v instanceof Date) return v.getTime()
  if (type === 'date') return parseDate(v, order)?.getTime() ?? null
  if (typeof v === 'number') return v
  if (type === 'amount' || type === 'number') return parseAmount(v)?.value ?? null
  return String(v).toLowerCase()
}

/** Stacks the sources into one table according to the mapping. */
export function mergeSources(sources: MergeSource[], opts: MergeOptions): MergeResult {
  const { mapping } = opts
  const addSource = opts.addSourceColumns ?? true
  const convertValues = opts.convertValues ?? true
  const skip = new Set(opts.skipSources ?? [])
  const used = sources.filter((s) => !skip.has(s.id))
  if (used.length === 0) throw new ToolError('empty-result', 'Choose at least one file to merge.')
  if (mapping.columns.length === 0) throw new ToolError('empty-result', 'Every column is set to "Drop". Keep at least one column.')

  // Raw stacked values per output column.
  const raw: Array<{ sourceId: string; fileName: string; sheetOrPage: string; values: CellValue[] }> = []
  const summary: MergeSummaryLine[] = []
  const excluded: MergeExcludedRow[] = []
  for (const src of used) {
    const map = mapping.sources[src.id] ?? {}
    const index = new Map<string, number>()
    mapping.columns.forEach((c, i) => index.set(c, i))
    const cols = src.columns.map((c) => ({ col: c, at: map[c] ? (index.get(map[c] as string) ?? -1) : -1 }))
    for (const r of src.rows) {
      const values: CellValue[] = new Array<CellValue>(mapping.columns.length).fill(null)
      let any = false
      for (const { col, at } of cols) {
        if (at < 0) continue
        const v = r.values[col] ?? null
        values[at] = v
        if (!isBlank(v)) any = true
      }
      if (any) raw.push({ sourceId: src.id, fileName: src.fileName, sheetOrPage: r.sheetOrPage, values })
    }
    excluded.push(...src.excluded)
    summary.push({
      sourceId: src.id,
      fileName: src.fileName,
      sheetName: src.sheetName,
      rowsTaken: raw.filter((x) => x.sourceId === src.id).length,
      rowsExcluded: src.excluded.length,
      droppedColumns: src.columns.filter((c) => !map[c] && !src.rows.every((r) => isBlank(r.values[c])))
    })
  }

  const types: ColumnType[] = mapping.columns.map((name, c) => inferColumnType(name, raw.map((r) => r.values[c])))
  const dateValues: CellValue[] = []
  types.forEach((t, c) => {
    if (t === 'date') for (const r of raw) dateValues.push(r.values[c])
  })
  const detected = detectDateOrder(dateValues)
  const dateOrder = opts.dateOrder ?? (detected === 'MDY' ? 'MDY' : 'DMY')
  const needsDateOrder = detected === 'ambiguous' && !opts.dateOrder

  let rows = raw.map((r) => ({
    ...r,
    values: convertValues ? r.values.map((v, c) => convert(v, types[c], dateOrder)) : r.values
  }))

  let unsortedRows = 0
  if (opts.sortBy) {
    const c = mapping.columns.indexOf(opts.sortBy)
    if (c < 0) throw new ToolError('invalid-option', `There is no column called "${opts.sortBy}" to sort by.`)
    const dir = opts.sortDirection === 'desc' ? -1 : 1
    const keyed = rows.map((r, i) => ({ r, i, k: sortKey(r.values[c], types[c], dateOrder) }))
    keyed.sort((a, b) => {
      if (a.k === null && b.k === null) return a.i - b.i
      if (a.k === null) return 1
      if (b.k === null) return -1
      if (a.k < b.k) return -dir
      if (a.k > b.k) return dir
      return a.i - b.i
    })
    unsortedRows = keyed.filter((x) => x.k === null).length
    rows = keyed.map((x) => x.r)
  }

  const columns: MergeOutputColumn[] = [
    ...(addSource
      ? [
          { name: SOURCE_FILE_COLUMN, type: 'text' as ColumnType, added: true },
          { name: SHEET_PAGE_COLUMN, type: 'text' as ColumnType, added: true }
        ]
      : []),
    ...mapping.columns.map((name, i) => ({ name, type: types[i] }))
  ]
  const outRows: MergeRow[] = rows.map((r) => ({
    sourceId: r.sourceId,
    values: addSource ? [r.fileName, r.sheetOrPage, ...r.values] : r.values
  }))
  if (outRows.length === 0) throw new ToolError('empty-result', 'The files have no data rows to merge.')
  return { columns, rows: outRows, excluded, summary, detectedDateOrder: detected, dateOrder, needsDateOrder, unsortedRows }
}

// ───────────────────────── Output ─────────────────────────

export interface MergeWorkbookOptions {
  /** Name of the merged sheet. Default "Merged". */
  sheetName?: string
  /** Add the "Summary" sheet (rows taken / excluded per file). Default true. */
  includeSummary?: boolean
  /** Add the "Excluded rows" sheet. Default true. */
  includeExcluded?: boolean
}

/** Formatted .xlsx: merged sheet (bold frozen header, autofilter, widths, #,##0.00, dd-mmm-yyyy), Summary and Excluded rows. */
export async function mergeToWorkbook(result: MergeResult, opts: MergeWorkbookOptions = {}): Promise<Uint8Array> {
  const wb = newWorkbook()
  const used = new Set<string>()
  const ws = wb.addWorksheet(uniqueSheetName(opts.sheetName ?? 'Merged', used))
  writeTableSheet(
    ws,
    result.columns.map((c) => ({ name: c.name, type: c.type })),
    result.rows.map((r) => r.values)
  )

  if (opts.includeSummary ?? true) {
    const s = wb.addWorksheet(uniqueSheetName('Summary', used))
    const rows: CellValue[][] = result.summary.map((l) => [l.fileName, l.sheetName, l.rowsTaken, l.rowsExcluded, l.droppedColumns.join(', ')])
    rows.push(['Total', null, result.rows.length, result.excluded.length, null])
    writeTableSheet(
      s,
      [
        { name: 'File', type: 'text' },
        { name: 'Sheet / Table', type: 'text' },
        { name: 'Rows taken', type: 'number' },
        { name: 'Rows excluded', type: 'number' },
        { name: 'Columns dropped', type: 'text' }
      ],
      rows,
      { table: false }
    )
    s.getRow(rows.length + 1).font = { bold: true }
  }

  if ((opts.includeExcluded ?? true) && result.excluded.length > 0) {
    const e = wb.addWorksheet(uniqueSheetName('Excluded rows', used))
    writeTableSheet(
      e,
      [
        { name: 'File', type: 'text' },
        { name: 'Sheet / Table', type: 'text' },
        { name: 'Where', type: 'text' },
        { name: 'Reason', type: 'text' },
        { name: 'Row content', type: 'text' }
      ],
      result.excluded.map((x) => [x.fileName, x.sheetName, x.location, x.reason, x.text])
    )
  }
  return workbookBytes(wb)
}
