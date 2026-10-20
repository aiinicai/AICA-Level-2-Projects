// Excel → PDF engine (jsPDF + jspdf-autotable). Pure functions, no React.
//
//   const wb = readWorkbook(buffer, 'Trial_balance.xlsx')               // @shared/parsing
//   const table = parseTable(wb.sheets[0], { fileName: 'Trial_balance.xlsx' })
//   const pdf = sheetToPdf(table, { title: 'Trial balance', subtitle: 'As at 30-Sep-2026', totals: ['Debit (AED)', 'Credit (AED)'] })

import { jsPDF } from 'jspdf'
import { autoTable, type CellHookData, type RowInput, type Styles } from 'jspdf-autotable'
import type { CellValue, ColumnType, ParsedTable } from '@shared/contracts'
import { formatAmount, formatDate } from '@shared/format'
import { detectDateOrder, detectDecimalSeparator, inferColumnType, parseAmount, parseDate, type DateOrder } from '@shared/parsing'
import { ToolError } from '../common'

export type PdfOrientation = 'portrait' | 'landscape' | 'auto'

export interface ExcelToPdfOptions {
  /** 'auto' (default) picks landscape when the columns do not fit portrait at a readable size. */
  orientation?: PdfOrientation
  /** Paper size. Default 'a4'. */
  pageSize?: 'a4' | 'letter' | 'legal'
  /** Shrink the text (down to 6 pt) and wrap so every column fits the page width. Default true.
   *  When false, columns that do not fit continue on extra pages (first column repeated). */
  fitToWidth?: boolean
  /** Repeat the header row at the top of every page. Default true. */
  repeatHeader?: boolean
  /** "Page x of y" at the bottom of every page. Default true. */
  pageNumbers?: boolean
  /** Title line on the first page, e.g. the company name. */
  title?: string
  /** Optional second line, e.g. the period. */
  subtitle?: string
  /** Columns to print, in order. Default: all columns of the table. */
  columns?: string[]
  /** Amount columns to total in a final "Total" row. Default: no totals row. */
  totals?: string[]
  /** Column types; missing ones are inferred with `inferColumnType`. */
  columnTypes?: Record<string, ColumnType>
  /** Format numbers (#,##0.00) and dates (DD-MMM-YYYY). Default true. When false values print as stored. */
  keepFormatting?: boolean
  /** Cell borders. Default true. */
  gridlines?: boolean
  /** Base font size in points. Default 8. */
  fontSize?: number
  /** Stored in the PDF properties. Default: the title or the sheet name. */
  documentTitle?: string
  /**
   * Day/month order for numeric text dates ("03/09/2026") in date columns whose own values do not settle it.
   * Each date column is checked on its own; a column whose values prove the order (a part above 12) uses it.
   * Default 'DMY'; columns that needed this choice are listed in `ambiguousDateColumns`.
   */
  dateOrder?: DateOrder
}

export interface ExcelToPdfResult {
  data: Uint8Array
  pages: number
  orientation: 'portrait' | 'landscape'
  /** Font size actually used after fitting. */
  fontSize: number
  /** Date columns whose numeric dates read either way (e.g. only 03/09/2026-style values); `dateOrder` was used. */
  ambiguousDateColumns: string[]
}

const PAGE_MM: Record<NonNullable<ExcelToPdfOptions['pageSize']>, [number, number]> = {
  a4: [210, 297],
  letter: [215.9, 279.4],
  legal: [215.9, 355.6]
}
const MARGIN = 10 // mm
const PT_TO_MM = 25.4 / 72
/** Average Helvetica glyph width as a share of the font size (digits and mixed text). */
const AVG_CHAR = 0.52
const CELL_PAD = 1.2 // mm, each side
const MIN_FONT = 6
const MAX_NATURAL_CHARS = 60 // long text wraps rather than widening the column forever

interface PreparedColumn {
  name: string
  type: ColumnType
  numeric: boolean
  /** Decimal separator of the column's text amounts ("1.234,56" → ','), when the values show it. */
  decimal?: '.' | ','
  /** Day/month order for the column's numeric text dates. */
  dateOrder: DateOrder
}

/** Local calendar date as YYYY-MM-DD (toISOString would shift local-midnight dates a day back east of UTC). */
function isoLocal(d: Date): string {
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** "1,234.50 Dr": the amount with its CR/DR marker kept, so a printed credit never looks like a debit. */
function amountText(value: number, indicator: 'DR' | 'CR' | null): string {
  if (indicator === null) return formatAmount(value)
  return `${formatAmount(value)} ${indicator === 'DR' ? 'Dr' : 'Cr'}`
}

function cellText(v: CellValue, col: PreparedColumn, keepFormatting: boolean): string {
  if (v === null || v === undefined) return ''
  if (!keepFormatting) return v instanceof Date ? isoLocal(v) : String(v)
  if (v instanceof Date) return formatDate(v)
  if (col.type === 'amount') {
    const a = parseAmount(v, { decimal: col.decimal })
    return a ? amountText(a.value, a.indicator) : String(v)
  }
  if (col.type === 'number') {
    if (typeof v === 'number') return v.toLocaleString('en-US', { maximumFractionDigits: 2 })
    const a = parseAmount(v, { decimal: col.decimal })
    return a ? a.value.toLocaleString('en-US', { maximumFractionDigits: 2 }) : String(v)
  }
  if (col.type === 'date') {
    const d = parseDate(v, col.dateOrder)
    return d ? formatDate(d) : String(v)
  }
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : formatAmount(v)
  return String(v)
}

/** Estimated natural width (mm) of each column at the given font size. */
function naturalWidths(head: string[], body: string[][], fontSize: number): number[] {
  const charMm = fontSize * PT_TO_MM * AVG_CHAR
  return head.map((h, c) => {
    let chars = Math.min(MAX_NATURAL_CHARS, longestWord(h) * 1.1 + 1)
    const step = Math.max(1, Math.floor(body.length / 400))
    for (let r = 0; r < body.length; r += step) chars = Math.max(chars, Math.min(MAX_NATURAL_CHARS, body[r][c].length))
    return chars * charMm + 2 * CELL_PAD
  })
}

function longestWord(s: string): number {
  return s.split(/\s+/).reduce((m, w) => Math.max(m, w.length), 0)
}

/** Renders one parsed sheet as a PDF and returns the bytes. See `ExcelToPdfOptions` for defaults. */
export function sheetToPdf(table: ParsedTable, opts: ExcelToPdfOptions = {}): Uint8Array {
  return sheetToPdfDetailed(table, opts).data
}

/** Same as `sheetToPdf` but also returns the page count, orientation and font size used (for the preview). */
export function sheetToPdfDetailed(table: ParsedTable, opts: ExcelToPdfOptions = {}): ExcelToPdfResult {
  const keepFormatting = opts.keepFormatting ?? true
  const fitToWidth = opts.fitToWidth ?? true
  const repeatHeader = opts.repeatHeader ?? true
  const pageNumbers = opts.pageNumbers ?? true
  const gridlines = opts.gridlines ?? true
  const baseFont = Math.max(MIN_FONT, Math.min(14, opts.fontSize ?? 8))

  const names = opts.columns && opts.columns.length ? opts.columns : table.columns
  for (const n of names) {
    if (!table.columns.includes(n)) throw new ToolError('invalid-option', `Column "${n}" is not in the sheet.`)
  }
  if (names.length === 0) throw new ToolError('empty-result', 'The sheet has no columns to print.')
  if (table.rows.length === 0) throw new ToolError('empty-result', 'The sheet has no rows to print.')

  const ambiguousDateColumns: string[] = []
  const cols: PreparedColumn[] = names.map((name) => {
    const values = table.rows.map((r) => r.values[name] ?? null)
    const type = opts.columnTypes?.[name] ?? inferColumnType(name, values)
    const numeric = type === 'amount' || type === 'number'
    let dateOrder: DateOrder = opts.dateOrder ?? 'DMY'
    if (type === 'date') {
      const detected = detectDateOrder(values)
      if (detected === 'ambiguous') ambiguousDateColumns.push(name)
      else dateOrder = detected
    }
    return { name, type, numeric, decimal: numeric ? (detectDecimalSeparator(values) ?? undefined) : undefined, dateOrder }
  })
  const head = cols.map((c) => c.name)
  const body = table.rows.map((r) => cols.map((c) => cellText(r.values[c.name] ?? null, c, keepFormatting)))

  // Totals row.
  const totalCols = new Set(opts.totals ?? [])
  for (const t of totalCols) if (!names.includes(t)) throw new ToolError('invalid-option', `Totals column "${t}" is not being printed.`)
  let foot: string[] | null = null
  if (totalCols.size > 0) {
    // CR/DR markers count: Dr adds, Cr subtracts, and the total keeps the marker ("100.00 Cr").
    const sums = cols.map((c): string | null => {
      if (!totalCols.has(c.name)) return null
      let cents = 0
      let marked = false
      for (const r of table.rows) {
        const a = parseAmount(r.values[c.name] ?? null, { decimal: c.decimal })
        if (!a) continue
        if (a.indicator === null) cents += Math.round(a.value * 100)
        else {
          marked = true
          const abs = Math.round(Math.abs(a.value) * 100)
          cents += a.indicator === 'DR' ? abs : -abs
        }
      }
      const total = cents / 100
      if (!marked) return formatAmount(total)
      return total === 0 ? formatAmount(0) : amountText(Math.abs(total), total > 0 ? 'DR' : 'CR')
    })
    // "Total" goes in the first text column that is not totalled (else the first column that is not totalled).
    let labelAt = cols.findIndex((c, i) => sums[i] === null && !c.numeric)
    if (labelAt < 0) labelAt = sums.findIndex((s) => s === null)
    foot = sums.map((s, i) => (s !== null ? s : i === labelAt ? 'Total' : ''))
  }

  // Orientation and font size.
  const [pw, ph] = PAGE_MM[opts.pageSize ?? 'a4']
  const usable = (o: 'portrait' | 'landscape'): number => (o === 'portrait' ? pw : ph) - 2 * MARGIN
  const allRows = foot ? [...body, foot] : body
  const widthAt = (size: number): number => naturalWidths(head, allRows, size).reduce((a, b) => a + b, 0)
  let orientation: 'portrait' | 'landscape'
  if (opts.orientation === 'portrait' || opts.orientation === 'landscape') orientation = opts.orientation
  else orientation = widthAt(baseFont) <= usable('portrait') ? 'portrait' : 'landscape'
  let fontSize = baseFont
  if (fitToWidth) {
    const natural = widthAt(baseFont)
    const avail = usable(orientation)
    if (natural > avail) fontSize = Math.max(MIN_FONT, Math.floor(((baseFont * avail) / natural) * 2) / 2)
  }

  const doc = new jsPDF({ orientation, unit: 'mm', format: opts.pageSize ?? 'a4', compress: true })
  doc.setProperties({ title: opts.documentTitle ?? opts.title ?? table.sheetName, creator: 'Reco-Do' })

  let y = MARGIN
  if (opts.title) {
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(14)
    doc.setTextColor(20, 33, 61)
    doc.text(opts.title, MARGIN, y + 5)
    y += 8
  }
  if (opts.subtitle) {
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(10)
    doc.setTextColor(80, 80, 80)
    doc.text(opts.subtitle, MARGIN, y + 4)
    y += 7
  }
  if (opts.title || opts.subtitle) y += 2

  const columnStyles: Record<number, Partial<Styles>> = {}
  cols.forEach((c, i) => {
    if (c.numeric) columnStyles[i] = { halign: 'right' }
  })
  const lineColor: [number, number, number] = [190, 190, 190]

  autoTable(doc, {
    head: [head],
    body: body as RowInput[],
    foot: foot ? [foot] : undefined,
    startY: y,
    margin: { top: MARGIN, bottom: MARGIN + (pageNumbers ? 6 : 0), left: MARGIN, right: MARGIN },
    theme: gridlines ? 'grid' : 'plain',
    showHead: repeatHeader ? 'everyPage' : 'firstPage',
    showFoot: 'lastPage',
    tableWidth: fitToWidth ? 'auto' : 'wrap',
    horizontalPageBreak: !fitToWidth,
    horizontalPageBreakRepeat: fitToWidth ? undefined : 0,
    rowPageBreak: 'avoid',
    styles: {
      font: 'helvetica',
      fontSize,
      cellPadding: CELL_PAD,
      overflow: 'linebreak',
      textColor: [20, 20, 20],
      lineColor,
      lineWidth: gridlines ? 0.1 : 0
    },
    headStyles: { fillColor: [20, 33, 61], textColor: 255, fontStyle: 'bold', halign: 'left' },
    footStyles: { fillColor: [235, 238, 244], textColor: [20, 20, 20], fontStyle: 'bold' },
    columnStyles,
    didParseCell: (data: CellHookData) => {
      if ((data.section === 'head' || data.section === 'foot') && cols[data.column.index]?.numeric) data.cell.styles.halign = 'right'
    }
  })

  const pages = doc.getNumberOfPages()
  if (pageNumbers) {
    const [w, h] = orientation === 'portrait' ? [pw, ph] : [ph, pw]
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    doc.setTextColor(90, 90, 90)
    for (let i = 1; i <= pages; i++) {
      doc.setPage(i)
      doc.text(`Page ${i} of ${pages}`, w / 2, h - MARGIN / 2 - 1, { align: 'center' })
    }
  }
  return { data: new Uint8Array(doc.output('arraybuffer')), pages, orientation, fontSize, ambiguousDateColumns }
}
