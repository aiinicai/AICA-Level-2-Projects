// Converts parsed table rows into engine lines: one signed amount, a comparable amount in side A's
// sign convention, and the date of the (first) used date key.

import type { AmountLayout, CellValue, EngineLine, ParsedTable, ReconConfig, Side, TableRow } from '@shared/contracts'
import { detectDateOrder, parseAmount, parseDate } from '@shared/parsing'
import { amountKeyOf, dateKeyOf, negate, round2 } from './util'

type DateOrder = 'DMY' | 'MDY'

/**
 * Reads a Dr/Cr indicator cell. Returns +1 for debit, -1 for credit, 0 when the cell says nothing usable.
 */
export function indicatorSign(v: CellValue): 1 | -1 | 0 {
  if (v === null || v === undefined || v instanceof Date) return 0
  if (typeof v === 'number') return v < 0 ? -1 : 0
  const s = v.trim().toUpperCase().replace(/\.$/, '')
  if (s === '') return 0
  if (s === 'D' || s === 'DR' || s === 'DEBIT' || s === 'DB' || s === '+') return 1
  if (s === 'C' || s === 'CR' || s === 'CREDIT' || s === '-') return -1
  if (s.startsWith('DEBIT') || s.startsWith('DR ')) return 1
  if (s.startsWith('CREDIT') || s.startsWith('CR ')) return -1
  return 0
}

/**
 * Converts one row's money to a single signed number using the debit-positive convention:
 *  - signed column: the number as written; a CR/DR suffix inside the cell sets the sign (CR negative).
 *  - debit/credit columns: |debit| − |credit| (written signs ignored; a CR/DR marker in the cell wins). Both blank → null.
 *  - amount + indicator: |amount| with the sign of the indicator (Dr +, Cr −); blank indicator keeps the written sign.
 */
export function signedAmount(values: Record<string, CellValue>, layout: AmountLayout): number | null {
  switch (layout.kind) {
    case 'signed': {
      const p = parseAmount(values[layout.column] ?? null)
      if (!p) return null
      if (p.indicator === 'CR') return round2(-Math.abs(p.value))
      if (p.indicator === 'DR') return round2(Math.abs(p.value))
      return round2(p.value)
    }
    case 'debit-credit': {
      const d = parseAmount(values[layout.debit] ?? null)
      const c = parseAmount(values[layout.credit] ?? null)
      if (!d && !c) return null
      // Accounting judgement: the column says which side the money is on, so the written sign is ignored and
      // the result is |debit| − |credit|. Some systems export credits as negative numbers ("-500" in the Credit
      // column); taking the sign literally would turn that credit into a debit. A column with mixed signs is
      // treated the same way (see detectNegativeCreditColumn for the informational note in the wizard).
      // The only exception is an explicit marker inside the cell: CR in the debit column or DR in the credit
      // column is honoured as written.
      const dv = d ? (d.indicator === 'CR' ? -Math.abs(d.value) : Math.abs(d.value)) : 0
      const cv = c ? (c.indicator === 'DR' ? -Math.abs(c.value) : Math.abs(c.value)) : 0
      return round2(dv - cv)
    }
    case 'amount-indicator': {
      const p = parseAmount(values[layout.amount] ?? null)
      if (!p) return null
      let sign = indicatorSign(values[layout.indicator] ?? null)
      if (sign === 0 && p.indicator) sign = p.indicator === 'DR' ? 1 : -1
      if (sign === 0) return round2(p.value)
      return round2(sign * Math.abs(p.value))
    }
  }
}

export interface NegativeCreditInfo {
  /** The credit column that holds negative numbers. */
  column: string
  negative: number
  positive: number
  /** Both negative and positive numbers in the column. */
  mixed: boolean
}

/**
 * For a debit/credit layout: reports a credit column that contains negative numbers, so the wizard can show an
 * informational note ("negative credits are read as credits"). Returns null for other layouts or when the credit
 * column has no negative numbers. Amounts are still read as |debit| − |credit| (see signedAmount).
 */
export function detectNegativeCreditColumn(table: ParsedTable, layout: AmountLayout | undefined): NegativeCreditInfo | null {
  if (!layout || layout.kind !== 'debit-credit') return null
  let negative = 0
  let positive = 0
  for (const row of table.rows) {
    const p = parseAmount(row.values[layout.credit] ?? null)
    if (!p || p.value === 0 || p.indicator) continue
    if (p.value < 0) negative++
    else positive++
  }
  if (negative === 0) return null
  return { column: layout.credit, negative, positive, mixed: positive > 0 }
}

/**
 * Detects the day/month order of a date column. The whole column is scanned (the check is a cheap regex per
 * cell), so a date-sorted MM/DD file whose first rows all fall on days 1-12 is still recognised by its later rows.
 */
export function detectColumnDateOrder(rows: TableRow[], column: string): DateOrder | 'ambiguous' {
  const values: CellValue[] = new Array(rows.length)
  for (let i = 0; i < rows.length; i++) values[i] = rows[i].values[column] ?? null
  return detectDateOrder(values)
}

/** Picks the day/month order for a date column (ambiguous columns use DMY, the UAE convention). */
export function dateOrderFor(rows: TableRow[], column: string): DateOrder {
  return detectColumnDateOrder(rows, column) === 'MDY' ? 'MDY' : 'DMY'
}

/**
 * Day/month order of the date key's column in each file, for the wizard: 'ambiguous' means the user should be
 * asked (store the answer in ReconConfig.dateOrderA / dateOrderB). Without a date key both are 'DMY'.
 */
export function detectConfigDateOrders(tableA: ParsedTable, tableB: ParsedTable, cfg: ReconConfig): { a: DateOrder | 'ambiguous'; b: DateOrder | 'ambiguous' } {
  const dateKey = dateKeyOf(cfg)
  if (!dateKey) return { a: 'DMY', b: 'DMY' }
  return { a: detectColumnDateOrder(tableA.rows, dateKey.columnA), b: detectColumnDateOrder(tableB.rows, dateKey.columnB) }
}

export function buildLines(table: ParsedTable, side: Side, cfg: ReconConfig): EngineLine[] {
  const amountKey = amountKeyOf(cfg)
  const layout = amountKey ? (side === 'A' ? cfg.amountA : cfg.amountB) : undefined
  const dateKey = dateKeyOf(cfg)
  const dateCol = dateKey ? (side === 'A' ? dateKey.columnA : dateKey.columnB) : undefined
  // Day/month order: the user's choice, else detection over the whole column, else DMY.
  const chosen = side === 'A' ? cfg.dateOrderA : cfg.dateOrderB
  const order: DateOrder = chosen === 'DMY' || chosen === 'MDY' ? chosen : dateCol ? dateOrderFor(table.rows, dateCol) : 'DMY'
  const invert = side === 'B' && cfg.sign === 'inverse'

  const out: EngineLine[] = new Array(table.rows.length)
  for (let i = 0; i < table.rows.length; i++) {
    const row = table.rows[i]
    const amount = layout ? signedAmount(row.values, layout) : null
    const comparableAmount = amount === null ? null : invert ? negate(amount) : amount
    const date = dateCol ? parseDate(row.values[dateCol] ?? null, order) : null
    out[i] = { id: `${side}:${row.id}`, side, rowId: row.id, amount, comparableAmount, date, values: row.values }
  }
  return out
}
