// Pure edits to the match-key list on the Map & Rules step.

import type { AmountLayout, ColumnType, MatchKey, ReconConfig, Tolerance } from '@shared/contracts'
import { getModule } from '@shared/modules'

export const TYPE_LABELS: Record<ColumnType, string> = {
  id: 'ID / code',
  text: 'Text',
  amount: 'Amount',
  number: 'Number / Qty',
  date: 'Date'
}

export function layoutColumns(l: AmountLayout | undefined): string[] {
  if (!l) return []
  if (l.kind === 'signed') return [l.column]
  if (l.kind === 'debit-credit') return [l.debit, l.credit]
  return [l.amount, l.indicator]
}

export function layoutLabel(l: AmountLayout | undefined): string {
  if (!l) return 'Not set'
  if (l.kind === 'signed') return l.column || 'Choose a column'
  if (l.kind === 'debit-credit') return `${l.debit || '?'} / ${l.credit || '?'}`
  return `${l.amount || '?'} + ${l.indicator || '?'}`
}

/** Switches an amount layout to another kind, keeping what columns it can. */
export function convertLayout(l: AmountLayout | undefined, kind: AmountLayout['kind'], fallbackColumn = ''): AmountLayout {
  const first = layoutColumns(l)[0] ?? fallbackColumn
  if (kind === 'signed') return { kind, column: first }
  if (kind === 'debit-credit') return l?.kind === 'debit-credit' ? l : { kind, debit: first, credit: '' }
  return l?.kind === 'amount-indicator' ? l : { kind, amount: first, indicator: '' }
}

function uniqueKeyId(keys: MatchKey[]): string {
  let n = keys.length + 1
  while (keys.some((k) => k.id === `key-${n}`)) n++
  return `key-${n}`
}

export function newKey(cfg: ReconConfig): MatchKey {
  return { id: uniqueKeyId(cfg.keys), name: `Key ${cfg.keys.length + 1}`, type: 'text', use: true, columnA: '', columnB: '', identifying: false, textRule: 'normalised' }
}

export function updateKey(cfg: ReconConfig, id: string, patch: Partial<MatchKey>): ReconConfig {
  return { ...cfg, keys: cfg.keys.map((k) => (k.id === id ? { ...k, ...patch } : k)) }
}

export function removeKey(cfg: ReconConfig, id: string): ReconConfig {
  return { ...cfg, keys: cfg.keys.filter((k) => k.id !== id) }
}

export function addKey(cfg: ReconConfig): ReconConfig {
  return { ...cfg, keys: [...cfg.keys, newKey(cfg)] }
}

/**
 * Changes a key's type and resets the rule fields to that type's defaults
 * (ID/Amount/Number identify a record; Date never does; Text only when ticked).
 * Making a key the Amount key also sets signed amount layouts from its columns when none exist.
 */
export function changeKeyType(cfg: ReconConfig, id: string, type: ColumnType): ReconConfig {
  const key = cfg.keys.find((k) => k.id === id)
  if (!key) return cfg
  const dateTol = getModule(cfg.moduleId)?.dateToleranceDays ?? 3
  const base: MatchKey = { id: key.id, name: key.name, use: key.use, columnA: key.columnA, columnB: key.columnB, type, identifying: false }
  let next: MatchKey
  switch (type) {
    case 'id':
      next = { ...base, identifying: true, textRule: key.textRule ?? 'normalised' }
      break
    case 'text':
      next = { ...base, identifying: false, textRule: key.textRule ?? 'normalised' }
      break
    case 'amount':
    case 'number':
      next = { ...base, identifying: true, tolerance: key.tolerance ?? { mode: 'exact' } }
      break
    case 'date':
      next = { ...base, identifying: false, dateToleranceDays: key.dateToleranceDays ?? dateTol }
      break
  }
  let out: ReconConfig = { ...cfg, keys: cfg.keys.map((k) => (k.id === id ? next : k)) }
  if (type === 'amount') {
    out = {
      ...out,
      amountA: out.amountA ?? { kind: 'signed', column: key.columnA },
      amountB: out.amountB ?? { kind: 'signed', column: key.columnB }
    }
  }
  return out
}

/** Keeps the amount key's display columns in step with the layouts. */
export function syncAmountKey(cfg: ReconConfig): ReconConfig {
  const k = cfg.keys.find((x) => x.type === 'amount')
  if (!k) return cfg
  return updateKey(cfg, k.id, { columnA: layoutLabel(cfg.amountA), columnB: layoutLabel(cfg.amountB) })
}

export function toleranceLabel(t: Tolerance | undefined, currency: string): string {
  if (!t || t.mode === 'exact') return 'Exact'
  if (t.mode === 'fixed') return `± ${currency} ${t.value}`
  return `± ${t.value}%`
}

/** Comma/space separated list → clean upper-case prefixes. */
export function parsePrefixes(text: string): string[] {
  const seen = new Set<string>()
  for (const p of text.split(/[\s,;]+/)) {
    const t = p.trim().toUpperCase()
    if (t) seen.add(t)
  }
  return [...seen]
}

/** Header list used for saved mappings (sorted, as findMappingByHeaders compares). */
export function sortedHeaders(columns: string[]): string[] {
  return [...columns].sort((a, b) => a.localeCompare(b))
}

/** Does a saved config fit these files? Returns the columns it needs that the files lack. */
export function missingColumns(cfg: ReconConfig, colsA: string[], colsB: string[]): string[] {
  const a = new Set(colsA)
  const b = new Set(colsB)
  const missing: string[] = []
  for (const k of cfg.keys) {
    if (!k.use || k.type === 'amount') continue
    if (k.columnA && !a.has(k.columnA)) missing.push(k.columnA)
    if (k.columnB && !b.has(k.columnB)) missing.push(k.columnB)
  }
  if (cfg.keys.some((k) => k.use && k.type === 'amount')) {
    for (const c of layoutColumns(cfg.amountA)) if (c && !a.has(c)) missing.push(c)
    for (const c of layoutColumns(cfg.amountB)) if (c && !b.has(c)) missing.push(c)
  }
  return [...new Set(missing)]
}
