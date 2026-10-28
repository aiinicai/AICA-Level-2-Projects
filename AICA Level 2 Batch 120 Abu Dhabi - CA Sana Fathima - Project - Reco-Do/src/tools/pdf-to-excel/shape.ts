// Stage 2 of PDF → Excel: page fragments → final tables (join across pages, bank layout, types,
// value conversion, renames). Pure and fast, so the preview can re-run it on every option change.

import type { CellValue, ColumnType } from '@shared/contracts'
import { formatAmount } from '@shared/format'
import { buildColumnNames, detectDateOrder, headerSimilarity, inferColumnType, parseAmount, parseDate } from '@shared/parsing'
import { resolveBankMapping, suggestBankMapping } from './bank'
import { isAmountText } from './layout'
import {
  BANK_FIELDS,
  type BankField,
  type BankMapping,
  type PdfCell,
  type PdfColumn,
  type PdfExcludedRow,
  type PdfExtractResult,
  type PdfFragment,
  type PdfFragmentRow,
  type PdfRow,
  type PdfShapeOptions,
  type PdfTable
} from './types'

const BANK_TYPES: Record<BankField, ColumnType> = {
  Date: 'date',
  'Value Date': 'date',
  Description: 'text',
  Reference: 'id',
  Debit: 'amount',
  Credit: 'amount',
  Balance: 'amount'
}

export type ShapedParts = Pick<
  PdfExtractResult,
  'tables' | 'excluded' | 'suggestedBankMapping' | 'bankMapping' | 'bankUnmapped' | 'detectedDateOrder' | 'dateOrder' | 'needsDateOrder' | 'options'
>

interface RawTable {
  names: string[]
  rows: PdfFragmentRow[]
}

function normaliseHeader(h: string): string {
  return h.toLowerCase().replace(/[^a-z0-9]+/g, '')
}

/** True when two header rows name the same columns (exact after normalising, or very similar for OCR misreads). */
export function headersMatch(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false
  let score = 0
  for (let i = 0; i < a.length; i++) {
    const x = normaliseHeader(a[i])
    const y = normaliseHeader(b[i])
    score += x === y ? 1 : x === '' || y === '' ? 0.5 : headerSimilarity(a[i], b[i])
  }
  return score / a.length >= 0.75
}

/** Unique, non-empty column names: blanks become "Column 3", duplicates "Debit (2)" (the shared parser's rules). */
export function uniqueColumnNames(header: string[]): string[] {
  return buildColumnNames(header, header.length)
}

function headerRowExclusion(row: PdfFragmentRow | { page: number; cells: string[] }): PdfExcludedRow {
  return { page: row.page, text: row.cells.filter((c) => c !== '').join('  '), reason: 'repeated-header', detail: 'Column headers repeated on a later page' }
}

function joinFragments(fragments: PdfFragment[], join: boolean, removeRepeated: boolean, excluded: PdfExcludedRow[]): RawTable[] {
  const tables: RawTable[] = []
  let last: (RawTable & { header: string[] }) | null = null
  for (const f of fragments) {
    const rows: PdfFragmentRow[] = []
    for (const r of f.rows) {
      if (r.repeatedHeader && removeRepeated) excluded.push(headerRowExclusion(r))
      else rows.push(r.repeatedHeader ? { ...r, repeatedHeader: false } : r)
    }
    const continues = join && last !== null && last.header.length === f.header.length && (!f.hasHeader || headersMatch(last.header, f.header))
    if (continues && last) {
      if (f.hasHeader) {
        const headerRow: PdfFragmentRow = { page: f.page, cells: f.header, confidence: f.header.map(() => null), ocr: f.method === 'ocr', lines: 1 }
        if (removeRepeated) excluded.push(headerRowExclusion(headerRow))
        else last.rows.push(headerRow)
      }
      last.rows.push(...rows)
    } else {
      last = { header: f.header, names: uniqueColumnNames(f.header), rows }
      tables.push(last)
    }
  }
  return tables.filter((t) => t.rows.length > 0)
}

/** Share of a column's non-empty texts that are well-formed amounts with 2 decimals. */
function twoDecimalShare(texts: string[]): number {
  const filled = texts.filter((t) => t !== '')
  if (filled.length === 0) return 0
  return filled.filter((t) => isAmountText(t) && /\d[.,]\d{2}\b/.test(t)).length / filled.length
}

/**
 * Repairs an OCR'd amount in a column where amounts carry 2 decimals: "2142117" → "21,421.17",
 * "8,724 50" → "8,724.50", "429 959 56" → "429,959.56". Returns null when the text is fine or not repairable.
 */
export function repairOcrAmount(text: string): string | null {
  const t = text.trim()
  if (t === '' || isAmountText(t)) return null
  const fixed = t.replace(/[Oo]/g, '0').replace(/[lI|]/g, '1')
  const m = /^([(\-]?)\s*([\d][\d.,\s'’]*\d)\s*([)\-]?)\s*(CR|DR)?\.?$/i.exec(fixed)
  if (!m) return null
  const digits = m[2].replace(/\D/g, '')
  if (digits.length < 3) return null
  const value = Number(digits) / 100
  const negative = m[1] !== '' || m[3] !== ''
  const body = formatAmount(value)
  const indicator = m[4] ? ` ${m[4].toUpperCase()}` : ''
  return `${negative ? '-' : ''}${body}${indicator}`
}

/** Converts a cell's text to a real value for its column type; returns the text when it does not convert. */
export function convertCell(text: string, type: ColumnType, order: 'DMY' | 'MDY'): CellValue {
  if (text === '') return null
  if (type === 'amount' || type === 'number') {
    const a = parseAmount(text)
    if (!a) return text
    if (a.indicator === 'DR') return -Math.abs(a.value)
    if (a.indicator === 'CR') return Math.abs(a.value)
    return a.value
  }
  if (type === 'date') return parseDate(text, order) ?? text
  return text
}

/** Applies the shape options to stage-1 fragments. */
export function shapeTables(fragments: PdfFragment[], pageExcluded: PdfExcludedRow[], opts: PdfShapeOptions, lowConfidenceBelow: number): ShapedParts {
  const options: ShapedParts['options'] = {
    layout: opts.layout ?? 'raw',
    joinAcrossPages: opts.joinAcrossPages ?? true,
    removeRepeatedHeaders: opts.removeRepeatedHeaders ?? true,
    convertValues: opts.convertValues ?? true,
    columnEdits: opts.columnEdits,
    bankMapping: opts.bankMapping,
    dateOrder: opts.dateOrder
  }
  const excluded: PdfExcludedRow[] = [...pageExcluded]
  const raw = joinFragments(fragments, options.joinAcrossPages, options.removeRepeatedHeaders, excluded)

  const suggestedBankMapping = suggestBankMapping(raw[0]?.names ?? [])
  let bankMapping: BankMapping | null = null
  let bankUnmapped: string[] = []

  // Layout: column keys + cell texts per table.
  interface Draft {
    keys: string[]
    types: ColumnType[]
    rows: { page: number; ocr: boolean; lines: number; texts: string[]; conf: (number | null)[] }[]
  }
  const drafts: Draft[] = raw.map((t, ti) => {
    if (options.layout === 'bank') {
      const mapping = resolveBankMapping(t.names, options.bankMapping)
      if (ti === 0) {
        bankMapping = mapping
        const used = new Set(Object.values(mapping).filter((v): v is string => v !== null))
        bankUnmapped = t.names.filter((n) => !used.has(n))
      }
      const idx = BANK_FIELDS.map((f) => (mapping[f] === null ? -1 : t.names.indexOf(mapping[f] as string)))
      return {
        keys: [...BANK_FIELDS],
        types: BANK_FIELDS.map((f) => BANK_TYPES[f]),
        rows: t.rows.map((r) => ({
          page: r.page,
          ocr: r.ocr,
          lines: r.lines,
          texts: idx.map((i) => (i >= 0 ? r.cells[i] ?? '' : '')),
          conf: idx.map((i) => (i >= 0 ? r.confidence[i] ?? null : null))
        }))
      }
    }
    return {
      keys: t.names,
      types: t.names.map((n, c) => inferColumnType(n, t.rows.map((r) => r.cells[c] || null))),
      rows: t.rows.map((r) => ({ page: r.page, ocr: r.ocr, lines: r.lines, texts: t.names.map((_, c) => r.cells[c] ?? ''), conf: t.names.map((_, c) => r.confidence[c] ?? null) }))
    }
  })

  // Type overrides from the preview.
  for (const d of drafts) {
    d.keys.forEach((k, c) => {
      const t = options.columnEdits?.[k]?.type
      if (t) d.types[c] = t
    })
  }

  // Day/month order across every date column.
  const dateTexts: string[] = []
  for (const d of drafts) d.types.forEach((t, c) => t === 'date' && d.rows.forEach((r) => r.texts[c] && dateTexts.push(r.texts[c])))
  const detectedDateOrder = detectDateOrder(dateTexts)
  const dateOrder = options.dateOrder ?? (detectedDateOrder === 'MDY' ? 'MDY' : 'DMY')
  const needsDateOrder = detectedDateOrder === 'ambiguous' && !options.dateOrder

  const tables: PdfTable[] = drafts.map((d, ti) => {
    const repairable = d.types.map((t, c) => (t === 'amount' || t === 'number') && twoDecimalShare(d.rows.map((r) => r.texts[c])) >= 0.6)
    const rows: PdfRow[] = d.rows.map((r) => ({
      page: r.page,
      ocr: r.ocr,
      lines: r.lines,
      cells: r.texts.map((text, c): PdfCell => {
        const confidence = r.conf[c]
        let t = text
        let repaired = false
        if (r.ocr && repairable[c]) {
          const fix = repairOcrAmount(text)
          if (fix !== null) {
            t = fix
            repaired = true
          }
        }
        const value = options.convertValues ? convertCell(t, d.types[c], dateOrder) : t === '' ? null : t
        const low = t !== '' && (repaired || (confidence !== null && confidence < lowConfidenceBelow))
        return { value, text: t, confidence, lowConfidence: low }
      })
    }))
    const names = uniqueColumnNames(d.keys.map((k) => options.columnEdits?.[k]?.name?.trim() || k))
    const columns: PdfColumn[] = d.keys.map((key, c) => ({ key, name: names[c], type: d.types[c] }))
    const pages = [...new Set(rows.map((r) => r.page))].sort((a, b) => a - b)
    return { name: `Table ${ti + 1}`, columns, rows, pages, usedOcr: rows.some((r) => r.ocr) }
  })

  excluded.sort((a, b) => a.page - b.page)
  return { tables, excluded, suggestedBankMapping, bankMapping, bankUnmapped, detectedDateOrder, dateOrder, needsDateOrder, options }
}
