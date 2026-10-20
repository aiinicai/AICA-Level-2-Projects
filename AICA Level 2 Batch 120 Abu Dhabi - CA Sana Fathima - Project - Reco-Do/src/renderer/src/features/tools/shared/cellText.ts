// Display text for table cells in the tool previews (pure, no React).

import type { CellValue, ColumnType } from '@shared/contracts'
import { formatAmount, formatDate } from '@shared/format'

/**
 * Shows a value the way its column reads: amounts as 1,234.50, references and other whole numbers as written
 * (an invoice number 10045 is not "10,045.00"), dates as 03-Sep-2026, text unchanged.
 */
export function cellText(v: CellValue | undefined, type: ColumnType): string {
  if (v === null || v === undefined) return ''
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? '' : formatDate(v)
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) return ''
    if (type === 'amount') return formatAmount(v)
    if (Number.isInteger(v)) return String(v)
    return type === 'number' ? v.toLocaleString('en-US', { maximumFractionDigits: 6 }) : formatAmount(v)
  }
  return v
}

/** True when a cell should be right-aligned: a real number in an amount or quantity column. */
export function isNumericCell(v: CellValue | undefined, type: ColumnType): boolean {
  return typeof v === 'number' && (type === 'amount' || type === 'number')
}
