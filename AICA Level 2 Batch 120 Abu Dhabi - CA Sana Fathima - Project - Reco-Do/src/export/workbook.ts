// Formatted Excel export of a reconciliation (master prompt §4 Step 5), built with ExcelJS.

import ExcelJS from 'exceljs'
import type { AuditAction, AuditEntry, CellValue, ReconSession, Statement } from '../shared/contracts'
import {
  AGE_BUCKETS,
  FLAG_LABELS,
  OPEN_STATUS_LABELS,
  ORIGIN_LABELS,
  TIER_COLOURS,
  TIER_LABELS,
  buildExportModel,
  cellToText,
  decisionLabel,
  excelRowOf,
  formatDateTime,
  keyMark,
  parseIso,
  round2,
  toSheetDate,
  toSheetDateTime,
  type AgeBucket,
  type DisplayTier,
  type ExportModel,
  type KeyColumn,
  type OpenItem,
  type OpenStatus,
  type PairSideView
} from './model'
import { toReconcileBaseName, uniqueSheetName } from './naming'
import { findUnexplainedIndex, isZero } from './statement'

export const NUM_FMT_AMOUNT = '#,##0.00'
export const NUM_FMT_COUNT = '#,##0'
export const NUM_FMT_DATE = 'dd-mmm-yyyy'
export const NUM_FMT_DATETIME = 'dd-mmm-yyyy hh:mm'

export const SHEET_NAMES = {
  summary: 'Summary',
  statement: 'Reconciliation Statement',
  matched: 'Matched (100%)',
  review: 'Doubtful & Likely',
  assisted: 'AI Assisted',
  audit: 'Audit Log'
} as const

/** Name of a "To Reconcile — <side>" sheet as it will appear in the workbook (sanitised, ≤ 31 chars). */
export function toReconcileSheetName(sideName: string): string {
  return uniqueSheetName(toReconcileBaseName(sideName), new Set(), 'To Reconcile')
}

export interface ExportOptions {
  /** Timestamp printed as "Generated". Defaults to now. */
  generatedAt?: Date
}

type ColKind = 'text' | 'wrap' | 'amount' | 'count' | 'date' | 'datetime' | 'tier'

interface ColSpec {
  header: string
  kind: ColKind
  /** Fixed width; otherwise sized from the header and a sample of values. */
  width?: number
}

type Row = Array<string | number | Date | null | undefined>

const HEADER_FILL: ExcelJS.Fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8ECF2' } }
const HEADER_FONT: Partial<ExcelJS.Font> = { bold: true, color: { argb: 'FF1B2A41' } }
const HEADER_BORDER: Partial<ExcelJS.Borders> = { bottom: { style: 'thin', color: { argb: 'FF8A97AB' } } }
const TOTAL_BORDER: Partial<ExcelJS.Borders> = { top: { style: 'thin', color: { argb: 'FF1B2A41' } } }

function argb(hex: string): string {
  return `FF${hex.replace('#', '').toUpperCase()}`
}

/** Mixes a colour with white; `amount` 0..1 is the share of white. */
function tint(hex: string, amount: number): string {
  const n = parseInt(hex.replace('#', ''), 16)
  const mix = (c: number): number => Math.round(c + (255 - c) * amount)
  const r = mix((n >> 16) & 255)
  const g = mix((n >> 8) & 255)
  const b = mix(n & 255)
  return `FF${[r, g, b].map((c) => c.toString(16).padStart(2, '0')).join('').toUpperCase()}`
}

/** Darkens a colour; `amount` 0..1 is the share of black. */
function shade(hex: string, amount: number): string {
  const n = parseInt(hex.replace('#', ''), 16)
  const mix = (c: number): number => Math.round(c * (1 - amount))
  return `FF${[(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => mix(c).toString(16).padStart(2, '0')).join('').toUpperCase()}`
}

interface TierStyle {
  fill: ExcelJS.Fill
  font: Partial<ExcelJS.Font>
}

const TIER_STYLES: Record<DisplayTier, TierStyle> = (Object.keys(TIER_COLOURS) as DisplayTier[]).reduce(
  (acc, t) => {
    acc[t] = {
      fill: { type: 'pattern', pattern: 'solid', fgColor: { argb: tint(TIER_COLOURS[t], 0.85) } },
      font: { bold: true, color: { argb: shade(TIER_COLOURS[t], 0.25) } }
    }
    return acc
  },
  {} as Record<DisplayTier, TierStyle>
)

const TIER_CELL_STYLES: Record<DisplayTier, Partial<ExcelJS.Style>> = (Object.keys(TIER_STYLES) as DisplayTier[]).reduce(
  (acc, t) => {
    acc[t] = Object.freeze({ fill: TIER_STYLES[t].fill, font: TIER_STYLES[t].font })
    return acc
  },
  {} as Record<DisplayTier, Partial<ExcelJS.Style>>
)

const DATE_CELL_STYLE: Partial<ExcelJS.Style> = Object.freeze({ numFmt: 'dd-mmm-yyyy' })

const OPEN_STATUS_TIER:Record<OpenStatus, DisplayTier> = {
  unmatched: 'unmatched',
  rejected: 'unmatched',
  doubtful: 'doubtful',
  likely: 'likely'
}

const AUDIT_ACTION_LABELS: Record<AuditAction, string> = {
  accept: 'Accepted pair',
  reject: 'Rejected pair',
  'manual-match': 'Manual match',
  unmatch: 'Unmatched pair',
  note: 'Added note',
  'approve-suggestion': 'Approved suggestion',
  'reject-suggestion': 'Rejected suggestion',
  finalise: 'Finalised'
}

function numFmtFor(kind: ColKind): string | undefined {
  switch (kind) {
    case 'amount':
      return NUM_FMT_AMOUNT
    case 'count':
      return NUM_FMT_COUNT
    case 'date':
      return NUM_FMT_DATE
    case 'datetime':
      return NUM_FMT_DATETIME
    default:
      return undefined
  }
}

function displayLength(v: Row[number], kind: ColKind): number {
  if (v === null || v === undefined) return 0
  if (kind === 'date') return 11
  if (kind === 'datetime') return 17
  if (typeof v === 'number') return kind === 'amount' ? Math.abs(v).toFixed(2).length * 1.3 + 1 : String(v).length + 1
  if (v instanceof Date) return 11
  return v.length
}

function columnWidths(cols: ColSpec[], rows: Row[], extra: Row[]): number[] {
  const sample = rows.length > 400 ? rows.slice(0, 400) : rows
  return cols.map((c, i) => {
    if (c.width) return c.width
    let w = c.header.length + 2
    for (const r of sample) w = Math.max(w, displayLength(r[i], c.kind) + 2)
    for (const r of extra) w = Math.max(w, displayLength(r[i], c.kind) + 2)
    const max = c.kind === 'wrap' ? 60 : 45
    return Math.min(Math.max(w, c.kind === 'amount' ? 14 : 8), max)
  })
}

/** Whole numbers with this many digits or more are identifiers (card, account, reference numbers), not quantities. */
const LONG_NUMBER_DIGITS = 12

/**
 * Converts a raw cell value from a non-amount column into something ExcelJS writes correctly (calendar-safe
 * dates). Whole numbers of 12+ digits are written as text, so Excel shows 1234567890123456 rather than
 * 1.23457E+15 (and does not round it on the next save).
 */
export function sheetValue(v: CellValue | undefined): string | number | Date | null {
  if (v === null || v === undefined) return null
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? null : toSheetDate(v)
  if (typeof v === 'number' && Number.isInteger(v) && Math.abs(v) >= 10 ** (LONG_NUMBER_DIGITS - 1)) return BigInt(v).toString()
  return v
}

function sheetDate(d: Date | null): Date | null {
  return d && !Number.isNaN(d.getTime()) ? toSheetDate(d) : null
}

interface TableOptions {
  /** Column index (0-based) and row → tier colouring. */
  tierColumn?: number
  tierOf?: (rowIndex: number) => DisplayTier | null
  /** Rows written after a blank line, bold with a top border (excluded from the filter range). */
  totals?: Row[]
  /** Plain note lines written after the totals. */
  notes?: string[]
}

function styleHeader(row: ExcelJS.Row, columns: number): void {
  row.height = 20
  for (let c = 1; c <= columns; c++) {
    const cell = row.getCell(c)
    cell.font = HEADER_FONT
    cell.fill = HEADER_FILL
    cell.border = HEADER_BORDER
    cell.alignment = { vertical: 'middle', wrapText: false }
  }
}

function addTableSheet(wb: ExcelJS.Workbook, name: string, cols: ColSpec[], rows: Row[], opts: TableOptions = {}): ExcelJS.Worksheet {
  const ws = wb.addWorksheet(name, { views: [{ state: 'frozen', xSplit: 0, ySplit: 1, activeCell: 'A2' }] })
  const widths = columnWidths(cols, rows, opts.totals ?? [])
  ws.columns = cols.map((c, i) => ({ header: c.header, key: `c${i}`, width: widths[i] }))
  styleHeader(ws.getRow(1), cols.length)

  // Performance: every data cell gets one of a few shared, frozen style objects. ExcelJS caches the
  // style id per style object, so sharing avoids re-processing a style for each of ~1M cells.
  // These objects must never be mutated (so no cell.font = … on data cells below this point).
  const colStyles: Array<Partial<ExcelJS.Style>> = cols.map((c) => {
    const numFmt = numFmtFor(c.kind)
    return Object.freeze(numFmt ? { numFmt } : {})
  })
  const tierCol = opts.tierColumn
  // Empty values become holes so ExcelJS creates no cell for them.
  for (const r of rows) for (let c = 0; c < r.length; c++) if (r[c] === null) r[c] = undefined
  const added = rows.length > 0 ? ws.addRows(rows) : []
  for (let i = 0; i < added.length; i++) {
    const row = added[i]
    const values = rows[i]
    const tier = tierCol !== undefined && opts.tierOf ? opts.tierOf(i) : null
    for (let c = 0; c < cols.length; c++) {
      const v = values[c]
      if (v === null || v === undefined) continue
      const cell = row.getCell(c + 1)
      if (c === tierCol && tier) cell.style = TIER_CELL_STYLES[tier]
      else if (v instanceof Date && cols[c].kind !== 'date' && cols[c].kind !== 'datetime') cell.style = DATE_CELL_STYLE
      else cell.style = colStyles[c]
    }
  }

  const lastDataRow = Math.max(1, rows.length + 1)
  ws.autoFilter = { from: { row: 1, column: 1 }, to: { row: lastDataRow, column: cols.length } }

  if (opts.totals && opts.totals.length > 0) {
    ws.addRow([])
    for (const t of opts.totals) {
      const r = ws.addRow(t)
      for (let c = 1; c <= cols.length; c++) {
        const numFmt = numFmtFor(cols[c - 1].kind)
        r.getCell(c).style = numFmt ? { numFmt, font: { bold: true }, border: TOTAL_BORDER } : { font: { bold: true }, border: TOTAL_BORDER }
      }
    }
  }
  if (opts.notes && opts.notes.length > 0) {
    ws.addRow([])
    for (const n of opts.notes) {
      const r = ws.addRow([n])
      r.getCell(1).font = { italic: true, color: { argb: 'FF5B6B82' } }
    }
  }
  return ws
}

// ───────────────────────── Shared column blocks ─────────────────────────

function sideColumns(m: ExportModel, side: 'A' | 'B', withDate: boolean, keyCols: KeyColumn[]): ColSpec[] {
  const name = side === 'A' ? m.sideAName : m.sideBName
  const cols: ColSpec[] = [{ header: `${name} – Row`, kind: 'text' }]
  if (withDate) cols.push({ header: `${name} – Date`, kind: 'date' })
  for (const k of keyCols) cols.push({ header: `${name} – ${k.column}`, kind: 'text' })
  if (m.hasAmount) cols.push({ header: `${name} – Amount`, kind: 'amount' })
  return cols
}

function sideCells(m: ExportModel, v: PairSideView, withDate: boolean): Row {
  const out: Row = [v.sourceRows || null]
  if (withDate) out.push(sheetDate(v.date))
  for (const kv of v.keyValues) out.push(sheetValue(kv))
  if (m.hasAmount) out.push(v.amount)
  return out
}

function blank(n: number): Row {
  return new Array<null>(n).fill(null)
}

// ───────────────────────── Sheets ─────────────────────────

function addSummarySheet(wb: ExcelJS.Workbook, m: ExportModel, statement: Statement): void {
  const { session } = m
  const { meta } = session
  const ws = wb.addWorksheet(SHEET_NAMES.summary, { views: [{ state: 'frozen', xSplit: 0, ySplit: 1, activeCell: 'A2' }] })
  const amountCols = m.hasAmount ? 5 : 4
  ws.columns = [
    { key: 'a', width: 34 },
    { key: 'b', width: 16 },
    { key: 'c', width: 16 },
    { key: 'd', width: 16 },
    { key: 'e', width: 20 }
  ]
  const header = ws.addRow(['Item', 'Value'])
  styleHeader(header, 2)

  const finalised = session.finalised
  const finalisedAt = finalised ? parseIso(finalised.at) : null
  const info: Array<[string, string | number | Date]> = [
    ['Module', m.moduleName],
    ['Account', meta.accountLabel],
    ['Period', meta.period],
    ['Side A', m.sideAName],
    ['Side B', m.sideBName],
    [`File used – ${m.sideAName}`, `${meta.fileA.name} · sheet "${meta.fileA.sheet}" · ${meta.fileA.rows.toLocaleString('en-US')} rows`],
    [`File used – ${m.sideBName}`, `${meta.fileB.name} · sheet "${meta.fileB.sheet}" · ${meta.fileB.rows.toLocaleString('en-US')} rows`],
    ['Mapping / template used', meta.mappingName || 'None (mapped manually)'],
    ['Matching keys', m.keys.filter((k) => k.use).map((k) => k.name).join(', ') || 'None'],
    ['Currency', m.currency],
    ['Preparer', meta.preparer || 'Not recorded'],
    [
      'Status',
      finalised ? `Finalised by ${finalised.by}${finalisedAt ? ` on ${formatDateTime(finalisedAt)}` : ''}` : 'Draft, not finalised'
    ],
    ['Finalised by', finalised ? finalised.by : 'Draft, not finalised'],
    ['Finalised at', finalisedAt ? toSheetDateTime(finalisedAt) : finalised ? finalised.at : '—'],
    ['Generated', toSheetDateTime(m.generatedAt)],
    ['Generated by', 'Reco-Do'],
    [
      'Ageing as of',
      m.asOf ? toSheetDate(m.asOf) : 'No dates in the data'
    ],
    [
      statement.kind === 'record-count' ? 'Unexplained count difference' : 'Unexplained difference',
      statement.unexplainedDifference
    ]
  ]
  for (const [label, value] of info) {
    const r = ws.addRow([label, value])
    r.getCell(1).font = { bold: true }
    const cell = r.getCell(2)
    if (value instanceof Date) cell.numFmt = label === 'Ageing as of' ? NUM_FMT_DATE : NUM_FMT_DATETIME
    if (typeof value === 'number') {
      cell.numFmt = statement.kind === 'record-count' ? NUM_FMT_COUNT : NUM_FMT_AMOUNT
      const ok = isZero(value, statement.kind)
      cell.font = { bold: true, color: { argb: ok ? argb(TIER_COLOURS.matched) : argb(TIER_COLOURS.unmatched) } }
    }
    cell.alignment = { horizontal: 'left' }
  }

  ws.addRow([])
  const tierHeader = ws.addRow(
    m.hasAmount
      ? ['Tier', 'Pairs', `Lines – ${m.sideAName}`, `Lines – ${m.sideBName}`, `Amount (${m.currency})`]
      : ['Tier', 'Pairs', `Lines – ${m.sideAName}`, `Lines – ${m.sideBName}`]
  )
  styleHeader(tierHeader, amountCols)
  tierHeader.getCell(3).alignment = { wrapText: true, vertical: 'middle' }
  tierHeader.getCell(4).alignment = { wrapText: true, vertical: 'middle' }
  tierHeader.height = 32

  const t = m.totals
  const tierRows: Array<[DisplayTier | null, string, number | null, number | null, number | null, number | null]> = [
    ['matched', 'Matched', t.matched.pairs, t.matched.linesA, t.matched.linesB, t.matched.amount],
    ['doubtful', 'Doubtful (pending review)', t.doubtful.pairs, t.doubtful.linesA, t.doubtful.linesB, t.doubtful.amount],
    ['likely', 'Likely (pending review)', t.likely.pairs, t.likely.linesA, t.likely.linesB, t.likely.amount],
    ['unmatched', `Unmatched – ${m.sideAName}`, null, t.unmatchedA.linesA, null, t.unmatchedA.amount],
    ['unmatched', `Unmatched – ${m.sideBName}`, null, null, t.unmatchedB.linesB, t.unmatchedB.amount],
    ['ai', 'AI assisted (included in Matched)', t.assisted.pairs, t.assisted.linesA, t.assisted.linesB, t.assisted.amount],
    [null, 'Smart Recon suggestions pending', t.aiPending, null, null, null]
  ]
  for (const [tier, label, pairs, la, lb, amount] of tierRows) {
    const values: Row = [label, pairs, la, lb]
    if (m.hasAmount) values.push(amount)
    const r = ws.addRow(values)
    for (let c = 2; c <= 4; c++) r.getCell(c).numFmt = NUM_FMT_COUNT
    if (m.hasAmount) r.getCell(5).numFmt = NUM_FMT_AMOUNT
    if (tier) {
      r.getCell(1).fill = TIER_STYLES[tier].fill
      r.getCell(1).font = TIER_STYLES[tier].font
    }
  }
  if (m.hasAmount) {
    ws.addRow([])
    const note = ws.addRow([
      `Amounts are absolute sums: ${m.sideAName} lines for pairs, each file's own lines for unmatched (as on screen).`
    ])
    note.getCell(1).font = { italic: true, color: { argb: 'FF5B6B82' } }
  }
}

function addStatementSheet(wb: ExcelJS.Workbook, m: ExportModel, statement: Statement): void {
  const isCount = statement.kind === 'record-count'
  const fmt = isCount ? NUM_FMT_COUNT : NUM_FMT_AMOUNT
  const ws = wb.addWorksheet(SHEET_NAMES.statement, { views: [{ state: 'frozen', xSplit: 0, ySplit: 4, activeCell: 'A5' }] })
  ws.columns = [
    { key: 'label', width: 62 },
    { key: 'value', width: 22, style: { numFmt: fmt } },
    { key: 'items', width: 10, style: { numFmt: NUM_FMT_COUNT } }
  ]
  const title = ws.addRow([statement.title])
  title.getCell(1).font = { bold: true, size: 14, color: { argb: 'FF1B2A41' } }
  const sub = ws.addRow([`${m.session.meta.accountLabel} · ${m.session.meta.period} · ${isCount ? 'record counts' : m.currency}`])
  sub.getCell(1).font = { color: { argb: 'FF5B6B82' } }
  ws.addRow([])
  const header = ws.addRow(['Item', isCount ? 'Records' : `Amount (${m.currency})`, 'Items'])
  styleHeader(header, 3)
  header.getCell(2).alignment = { horizontal: 'right', vertical: 'middle' }
  header.getCell(3).alignment = { horizontal: 'right', vertical: 'middle' }

  const unexplainedIdx = findUnexplainedIndex(statement)
  const paint = (r: ExcelJS.Row, value: number): void => {
    const ok = isZero(value, statement.kind)
    const colour = ok ? TIER_COLOURS.matched : TIER_COLOURS.unmatched
    for (let c = 1; c <= 3; c++) {
      const cell = r.getCell(c)
      cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: tint(colour, 0.85) } }
      cell.font = { bold: true, color: { argb: shade(colour, 0.2) } }
      cell.border = { top: { style: 'thin', color: { argb: argb(colour) } }, bottom: { style: 'double', color: { argb: argb(colour) } } }
    }
  }

  statement.lines.forEach((line, i) => {
    const value = isCount ? Math.round(line.value) : line.value
    const r = ws.addRow([line.label, value, line.lineIds && line.lineIds.length > 0 ? line.lineIds.length : null])
    if (i === unexplainedIdx) {
      paint(r, line.value)
    } else if (line.isTotal) {
      for (let c = 1; c <= 3; c++) {
        r.getCell(c).font = { bold: true }
        r.getCell(c).border = TOTAL_BORDER
      }
    } else {
      r.getCell(1).alignment = { indent: 1 }
    }
  })
  if (unexplainedIdx < 0) {
    const value = isCount ? Math.round(statement.unexplainedDifference) : statement.unexplainedDifference
    const r = ws.addRow([isCount ? 'Unexplained count difference' : 'Unexplained difference', value, null])
    paint(r, statement.unexplainedDifference)
  }
  ws.addRow([])
  const ok = isZero(statement.unexplainedDifference, statement.kind)
  const note = ws.addRow([
    ok
      ? 'The reconciliation ties: the unexplained difference is nil.'
      : 'The reconciliation does not tie yet: investigate the unexplained difference before sign-off.'
  ])
  note.getCell(1).font = { italic: true, color: { argb: ok ? argb(TIER_COLOURS.matched) : argb(TIER_COLOURS.unmatched) } }
}

function addMatchedSheet(wb: ExcelJS.Workbook, m: ExportModel): void {
  const colsA = sideColumns(m, 'A', m.hasDateA, m.keyColumnsA)
  const colsB = sideColumns(m, 'B', m.hasDateB, m.keyColumnsB)
  const cols: ColSpec[] = [{ header: 'Pair ID', kind: 'text' }, { header: 'Tier', kind: 'tier', width: 14 }, ...colsA, ...colsB]
  const amountIdxA = 2 + colsA.length - 1
  const amountIdxB = 2 + colsA.length + colsB.length - 1
  const diffIdx = cols.length
  if (m.hasAmount) cols.push({ header: 'Difference', kind: 'amount' })
  cols.push(
    { header: 'Reason', kind: 'wrap' },
    { header: 'Origin', kind: 'text' },
    { header: 'Label', kind: 'wrap' },
    { header: 'Note', kind: 'wrap' }
  )
  const rows: Row[] = new Array<Row>(m.matched.length)
  let totalA = 0
  let totalB = 0
  let totalDiff = 0
  for (let i = 0; i < m.matched.length; i++) {
    const v = m.matched[i]
    const r: Row = [v.pair.id, TIER_LABELS[v.displayTier], ...sideCells(m, v.a, m.hasDateA), ...sideCells(m, v.b, m.hasDateB)]
    if (m.hasAmount) {
      r.push(v.pair.amountDifference)
      totalA += v.a.amount ?? 0
      totalB += v.b.amount ?? 0
      totalDiff += v.pair.amountDifference ?? 0
    }
    r.push(v.pair.reason, ORIGIN_LABELS[v.pair.origin], v.pair.label ?? null, v.pair.note ?? null)
    rows[i] = r
  }
  const totals: Row[] = []
  if (m.hasAmount) {
    const t = blank(cols.length)
    t[0] = `Total (${m.matched.length.toLocaleString('en-US')} pairs)`
    t[amountIdxA] = round2(totalA)
    t[amountIdxB] = round2(totalB)
    t[diffIdx] = round2(totalDiff)
    totals.push(t)
  } else {
    const t = blank(cols.length)
    t[0] = `Total: ${m.matched.length.toLocaleString('en-US')} pairs`
    totals.push(t)
  }
  addTableSheet(wb, SHEET_NAMES.matched, cols, rows, {
    tierColumn: 1,
    tierOf: (i) => m.matched[i].displayTier,
    totals
  })
}

function amountColumnsOf(m: ExportModel, side: 'A' | 'B'): Set<string> {
  const cfg = m.session.result.config
  const layout = side === 'A' ? cfg.amountA : cfg.amountB
  const out = new Set<string>()
  if (!layout) return out
  if (layout.kind === 'signed') out.add(layout.column)
  else if (layout.kind === 'debit-credit') {
    out.add(layout.debit)
    out.add(layout.credit)
  } else {
    out.add(layout.amount)
    out.add(layout.indicator)
  }
  return out
}

function addToReconcileSheet(wb: ExcelJS.Workbook, m: ExportModel, side: 'A' | 'B', sheetName: string): void {
  const items: OpenItem[] = side === 'A' ? m.openA : m.openB
  const keyCols = side === 'A' ? m.keyColumnsA : m.keyColumnsB
  const hasDate = side === 'A' ? m.hasDateA : m.hasDateB
  const withAgeing = hasDate && m.asOf !== null
  const cfg = m.session.result.config

  // Columns: key columns, then the party column, then the file's other columns (narration etc.).
  const shown = new Set(keyCols.map((k) => k.column))
  const dateKey = cfg.keys.find((k) => k.use && k.type === 'date')
  const dateColumn = dateKey ? (side === 'A' ? dateKey.columnA : dateKey.columnB) : undefined
  const skip = amountColumnsOf(m, side)
  if (dateColumn) skip.add(dateColumn)
  const extraCols: string[] = []
  const party = side === 'A' ? cfg.partyColumnA : cfg.partyColumnB
  if (party && !shown.has(party)) {
    extraCols.push(party)
    shown.add(party)
  }
  const allLines = side === 'A' ? m.session.result.linesA : m.session.result.linesB
  const sampleLine = items[0]?.line ?? allLines[0]
  if (sampleLine) {
    for (const col of Object.keys(sampleLine.values)) {
      if (shown.has(col) || skip.has(col)) continue
      shown.add(col)
      extraCols.push(col)
    }
  }

  const cols: ColSpec[] = [{ header: 'Row', kind: 'text', width: 8 }]
  if (hasDate) cols.push({ header: 'Date', kind: 'date' })
  for (const k of keyCols) cols.push({ header: k.column, kind: 'text' })
  for (const c of extraCols) cols.push({ header: c, kind: 'text' })
  if (m.hasAmount) cols.push({ header: `Amount (${m.currency})`, kind: 'amount' })
  const statusCol = cols.length
  cols.push({ header: 'Status', kind: 'tier', width: 26 }, { header: 'Comment', kind: 'wrap' })
  const ageStart = cols.length
  if (withAgeing) {
    cols.push({ header: 'Age (days)', kind: 'count', width: 11 })
    for (const b of AGE_BUCKETS) cols.push({ header: `${b} days`, kind: m.hasAmount ? 'amount' : 'count' })
  }

  const bucketTotals: Record<AgeBucket, number> = { '0-30': 0, '31-60': 0, '61-90': 0, '90+': 0 }
  let total = 0
  const rows: Row[] = new Array<Row>(items.length)
  for (let i = 0; i < items.length; i++) {
    const it = items[i]
    const l = it.line
    const r: Row = [excelRowOf(l.rowId)]
    if (hasDate) r.push(sheetDate(l.date))
    for (const k of keyCols) r.push(sheetValue(l.values[k.column]))
    for (const c of extraCols) r.push(sheetValue(l.values[c]))
    if (m.hasAmount) {
      r.push(l.amount)
      total += l.amount ?? 0
    }
    r.push(OPEN_STATUS_LABELS[it.status], it.comment || null)
    if (withAgeing) {
      r.push(it.ageDays)
      const unit = m.hasAmount ? (l.amount ?? 0) : 1
      for (const b of AGE_BUCKETS) r.push(it.bucket === b ? unit : null)
      if (it.bucket) bucketTotals[it.bucket] += unit
    }
    rows[i] = r
  }

  const t = blank(cols.length)
  t[0] = `Total (${items.length.toLocaleString('en-US')} items)`
  if (m.hasAmount) t[statusCol - 1] = round2(total)
  if (withAgeing) {
    AGE_BUCKETS.forEach((b, j) => {
      t[ageStart + 1 + j] = m.hasAmount ? round2(bucketTotals[b]) : bucketTotals[b]
    })
  }
  const notes: string[] = []
  if (withAgeing && m.asOf) {
    notes.push(
      `Ageing as of ${cellToText(m.asOf)} (${m.asOfSource === 'period-end' ? 'period end' : 'latest date in the data'}).`
    )
  } else if (!hasDate) {
    notes.push('No dates on this side, so ageing is not shown.')
  }
  if (items.some((it) => it.status === 'doubtful' || it.status === 'likely')) {
    notes.push('Lines pending review stay here until their Doubtful or Likely pair is accepted.')
  }

  addTableSheet(wb, sheetName, cols, rows, {
    tierColumn: statusCol,
    tierOf: (i) => OPEN_STATUS_TIER[items[i].status],
    totals: [t],
    notes
  })
}

function addReviewSheet(wb: ExcelJS.Workbook, m: ExportModel): void {
  const usedKeys = m.keys.filter((k) => k.use)
  const anyCandidates = m.review.some((v) => (v.pair.candidateIds?.length ?? 0) > 0)
  const cols: ColSpec[] = [
    { header: 'Pair ID', kind: 'text' },
    { header: 'Tier', kind: 'tier', width: 12 },
    ...sideColumns(m, 'A', m.hasDateA, m.keyColumnsA),
    ...sideColumns(m, 'B', m.hasDateB, m.keyColumnsB),
    ...usedKeys.map<ColSpec>((k) => ({ header: `${k.name} ✓/✗`, kind: 'text' }))
  ]
  if (m.hasAmount) cols.push({ header: 'Difference', kind: 'amount' })
  if (m.hasDateA && m.hasDateB) cols.push({ header: 'Date difference (days)', kind: 'count' })
  cols.push({ header: 'Flags', kind: 'text' }, { header: 'Reason', kind: 'wrap' })
  if (anyCandidates) cols.push({ header: 'Other candidates (rows)', kind: 'text' })
  cols.push({ header: 'Decision', kind: 'text', width: 11 }, { header: 'Note', kind: 'wrap' })

  const rows: Row[] = m.review.map((v) => {
    const p = v.pair
    const r: Row = [p.id, TIER_LABELS[p.tier], ...sideCells(m, v.a, m.hasDateA), ...sideCells(m, v.b, m.hasDateB)]
    for (const k of usedKeys) r.push(keyMark(p, k.id) || null)
    if (m.hasAmount) r.push(p.amountDifference)
    if (m.hasDateA && m.hasDateB) r.push(p.dateDifferenceDays)
    r.push(p.flags.map((f) => FLAG_LABELS[f]).join(', ') || null, p.reason)
    if (anyCandidates) {
      const cands = (p.candidateIds ?? []).map((id) => {
        const l = m.lineById.get(id)
        return l ? `${l.side === 'A' ? m.sideAName : m.sideBName} row ${excelRowOf(l.rowId)}` : id
      })
      r.push(cands.join(', ') || null)
    }
    r.push(decisionLabel(p), p.note ?? null)
    return r
  })
  addTableSheet(wb, SHEET_NAMES.review, cols, rows, {
    tierColumn: 1,
    tierOf: (i) => m.review[i].pair.tier
  })
}

function addAssistedSheet(wb: ExcelJS.Workbook, m: ExportModel): void {
  const cols: ColSpec[] = [
    { header: 'ID', kind: 'text' },
    { header: 'Tier', kind: 'tier', width: 13 },
    { header: 'Source', kind: 'text' },
    { header: 'Confidence (%)', kind: 'count', width: 15 },
    ...sideColumns(m, 'A', m.hasDateA, m.keyColumnsA),
    ...sideColumns(m, 'B', m.hasDateB, m.keyColumnsB)
  ]
  if (m.hasAmount) cols.push({ header: 'Difference', kind: 'amount' })
  cols.push({ header: 'Reason', kind: 'wrap' }, { header: 'Label', kind: 'wrap' }, { header: 'Status', kind: 'text', width: 11 })
  const rows: Row[] = m.assisted.map((a) => {
    const r: Row = [a.id, TIER_LABELS.ai, a.source, a.confidence, ...sideCells(m, a.a, m.hasDateA), ...sideCells(m, a.b, m.hasDateB)]
    if (m.hasAmount) r.push(a.difference)
    r.push(a.reason, a.label || null, a.status)
    return r
  })
  addTableSheet(wb, SHEET_NAMES.assisted, cols, rows, {
    tierColumn: 1,
    tierOf: () => 'ai',
    notes: rows.length === 0 ? ['No AI assisted or Smart Recon matches were approved in this reconciliation.'] : []
  })
}

function addAuditSheet(wb: ExcelJS.Workbook, entries: AuditEntry[]): void {
  const cols: ColSpec[] = [
    { header: 'Timestamp', kind: 'datetime' },
    { header: 'User', kind: 'text' },
    { header: 'Action', kind: 'text' },
    { header: 'Pair', kind: 'text' },
    { header: 'Suggestion', kind: 'text' },
    { header: 'Before', kind: 'wrap' },
    { header: 'After', kind: 'wrap' },
    { header: 'Note', kind: 'wrap' }
  ]
  const sorted = [...entries].sort((a, b) => a.at.localeCompare(b.at))
  const rows: Row[] = sorted.map((e) => {
    const at = parseIso(e.at)
    return [
      at ? toSheetDateTime(at) : e.at,
      e.user,
      AUDIT_ACTION_LABELS[e.action] ?? e.action,
      e.pairId ?? null,
      e.suggestionId ?? null,
      e.before ?? null,
      e.after ?? null,
      e.note ?? null
    ]
  })
  addTableSheet(wb, SHEET_NAMES.audit, cols, rows, {
    notes: rows.length === 0 ? ['No review decisions have been recorded yet.'] : []
  })
}

/** Builds the formatted reconciliation workbook (.xlsx bytes). */
export async function buildReconWorkbook(
  session: ReconSession,
  statement: Statement,
  options: ExportOptions = {}
): Promise<Uint8Array> {
  const m = buildExportModel(session, { generatedAt: options.generatedAt })
  const wb = new ExcelJS.Workbook()
  wb.creator = 'Reco-Do'
  wb.lastModifiedBy = session.meta.preparer || 'Reco-Do'
  wb.created = m.generatedAt
  wb.modified = m.generatedAt
  wb.title = `${m.moduleName} – ${session.meta.accountLabel} – ${session.meta.period}`
  wb.subject = statement.title
  wb.company = 'Reco-Do'
  wb.description = 'Reconciliation export generated by Reco-Do.'

  const taken = new Set<string>(Object.values(SHEET_NAMES).map((n) => n.toLowerCase()))
  const sheetA = uniqueSheetName(toReconcileBaseName(m.sideAName), taken, 'To Reconcile A')
  const sheetB = uniqueSheetName(toReconcileBaseName(m.sideBName), taken, 'To Reconcile B')

  addSummarySheet(wb, m, statement)
  addStatementSheet(wb, m, statement)
  addMatchedSheet(wb, m)
  addToReconcileSheet(wb, m, 'A', sheetA)
  addToReconcileSheet(wb, m, 'B', sheetB)
  addReviewSheet(wb, m)
  addAssistedSheet(wb, m)
  addAuditSheet(wb, session.audit)

  // ExcelJS returns a Node Buffer (a Uint8Array) in Node and an ArrayBuffer in the browser build.
  // Fast deflate level: large exports are several times quicker for a slightly bigger file.
  const buf: unknown = await wb.xlsx.writeBuffer({ zip: { compression: 'DEFLATE', compressionOptions: { level: 1 } } } as Partial<ExcelJS.XlsxWriteOptions>)
  if (buf instanceof Uint8Array) return new Uint8Array(buf.buffer, buf.byteOffset, buf.byteLength)
  return new Uint8Array(buf as ArrayBuffer)
}
