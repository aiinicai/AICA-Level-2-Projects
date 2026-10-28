// Configuration checks run before every reconciliation. Messages are shown to users as written.

import type { AmountLayout, MatchKey, ParsedTable, ReconConfig } from '@shared/contracts'
import { isIdentifying } from './util'

export const NO_IDENTIFYING_KEY_MESSAGE = 'Add at least one ID, Amount, Number or ID-key Text column.'

function layoutColumns(l: AmountLayout): string[] {
  switch (l.kind) {
    case 'signed':
      return [l.column]
    case 'debit-credit':
      return [l.debit, l.credit]
    case 'amount-indicator':
      return [l.amount, l.indicator]
  }
}

function checkTolerance(k: MatchKey, errors: string[]): void {
  const t = k.tolerance
  if (t && t.mode !== 'exact' && !(Number.isFinite(t.value) && t.value >= 0)) {
    errors.push(`The tolerance for "${k.name}" must be a number of zero or more.`)
  }
  if (k.type === 'date' && k.dateToleranceDays !== undefined) {
    if (!(Number.isInteger(k.dateToleranceDays) && k.dateToleranceDays >= 0)) {
      errors.push(`The date tolerance for "${k.name}" must be a whole number of days, zero or more.`)
    }
  }
}

export function validateConfig(cfg: ReconConfig, tableA: ParsedTable, tableB: ParsedTable): string[] {
  const errors: string[] = []
  const nameA = cfg.sideAName || 'File A'
  const nameB = cfg.sideBName || 'File B'
  const used = cfg.keys.filter((k) => k.use)
  if (used.length === 0) {
    errors.push(`Choose at least one key to match on. ${NO_IDENTIFYING_KEY_MESSAGE}`)
    return errors
  }
  if (!used.some(isIdentifying)) errors.push(NO_IDENTIFYING_KEY_MESSAGE)

  const colsA = new Set(tableA.columns)
  const colsB = new Set(tableB.columns)
  const amountKeys = used.filter((k) => k.type === 'amount')
  if (amountKeys.length > 1) errors.push('Use only one Amount key. Add other money columns as Number keys.')

  for (const k of used) {
    checkTolerance(k, errors)
    if (k.type === 'amount') continue
    if (!k.columnA || !colsA.has(k.columnA)) errors.push(`Choose a column in ${nameA} for "${k.name}".`)
    if (!k.columnB || !colsB.has(k.columnB)) errors.push(`Choose a column in ${nameB} for "${k.name}".`)
  }

  if (amountKeys.length > 0) {
    const sides: Array<[AmountLayout | undefined, Set<string>, string]> = [
      [cfg.amountA, colsA, nameA],
      [cfg.amountB, colsB, nameB]
    ]
    for (const [layout, cols, name] of sides) {
      if (!layout) {
        errors.push(`Choose how ${name} shows amounts: one signed column, separate Debit and Credit columns, or an amount with a Dr/Cr column.`)
        continue
      }
      const missing = layoutColumns(layout).filter((c) => !c || !cols.has(c))
      if (missing.length > 0) errors.push(`The amount column${missing.length > 1 ? 's' : ''} chosen for ${name} ${missing.length > 1 ? 'are' : 'is'} not in the file. Choose again.`)
    }
  }
  return errors
}
