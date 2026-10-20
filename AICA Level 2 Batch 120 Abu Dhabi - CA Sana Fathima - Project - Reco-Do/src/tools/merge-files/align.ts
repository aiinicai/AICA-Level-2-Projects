// Column alignment for Merge Files: suggests which columns of each file are "the same" column,
// and edits the mapping (map / keep separate / drop).

import type { CellValue } from '@shared/contracts'
import { headerSimilarity } from '@shared/parsing'
import type { ColumnTarget, MergeFilesRecipeOptions, MergeMapping, MergeSource } from './types'
import { SHEET_PAGE_COLUMN, SOURCE_FILE_COLUMN } from './types'

/**
 * Accounting meaning of a header. Two headers with different meanings are never aligned, even when the
 * generic similarity says they are close (e.g. "Withdrawal" and "Credit" are both "amount" words).
 * Order matters: the first pattern that matches wins.
 */
const CONCEPTS: Array<[string, RegExp]> = [
  ['value-date', /\bvalue\s*date\b|\bval\s*dt\b/],
  ['date', /\b(date|dated|dt)\b/],
  ['balance', /\b(bal|balance)\b/],
  ['debit', /\b(debit|debits|dr|withdrawals?|payments?|paid\s*out|money\s*out|outflows?)\b/],
  ['credit', /\b(credit|credits|cr|deposits?|receipts?|paid\s*in|money\s*in|inflows?)\b/],
  ['reference', /\b(ref|refs|reference|cheque|chq|check|instrument|voucher|doc\s*no|document\s*no|invoice|inv)\b/],
  ['description', /\b(description|desc|narration|narrative|details?|particulars|remarks?|memo)\b/],
  ['amount', /\b(amount|amt)\b/]
]

function cleanHeader(h: string): string {
  return h
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

/** Key used to remember a header in recipes: lower case, single spaces, no punctuation. */
export function headerKey(h: string): string {
  return cleanHeader(h)
}

export function headerConcept(h: string): string | null {
  const c = cleanHeader(h)
  for (const [name, re] of CONCEPTS) if (re.test(c)) return name
  return null
}

const CURRENCY_CODES = new Set([
  'aed', 'usd', 'eur', 'gbp', 'sar', 'qar', 'omr', 'kwd', 'bhd', 'inr', 'pkr', 'egp', 'jod', 'lkr', 'php', 'bdt', 'npr',
  'chf', 'jpy', 'cny', 'cad', 'aud', 'nzd', 'sgd', 'hkd', 'zar', 'try', 'rub'
])
const CURRENCY_SYMBOLS: Record<string, string> = { '$': 'usd', '€': 'eur', '£': 'gbp', '¥': 'jpy', '₹': 'inr' }

/** Currency named in a header: "Amount (USD)" → "usd", "Amount €" → "eur"; null when there is none. */
export function headerCurrency(h: string): string | null {
  for (const [sym, code] of Object.entries(CURRENCY_SYMBOLS)) if (h.includes(sym)) return code
  for (const w of cleanHeader(h).split(' ')) if (CURRENCY_CODES.has(w)) return w
  return null
}

/** Word pairs that make two otherwise similar headers different columns ("Opening Balance" vs "Closing Balance"). */
const OPPOSITES: Array<[RegExp, RegExp]> = [
  [/\b(opening|open|beginning|brought)\b/, /\b(closing|close|ending|carried)\b/],
  [/\b(supplier|vendor|creditor|payee)\b/, /\b(customer|client|debtor|buyer)\b/],
  [/\b(start|from)\b/, /\b(end|to)\b/],
  [/\b(debit|dr)\b/, /\b(credit|cr)\b/]
]

/** True when the headers carry opposite words or different currencies, so they must never be stacked. */
export function headersConflict(a: string, b: string): boolean {
  const ca = cleanHeader(a)
  const cb = cleanHeader(b)
  const ka = headerCurrency(a)
  const kb = headerCurrency(b)
  if (ka && kb && ka !== kb) return true
  for (const [x, y] of OPPOSITES) {
    if ((x.test(ca) && y.test(cb) && !y.test(ca) && !x.test(cb)) || (y.test(ca) && x.test(cb) && !x.test(ca) && !y.test(cb))) return true
  }
  return false
}

/** 0..1: how likely two headers name the same column. */
export function columnSimilarity(a: string, b: string): number {
  const ca = cleanHeader(a)
  const cb = cleanHeader(b)
  if (ca === '' || cb === '') return 0
  if (ca === cb) return 1
  if (headersConflict(a, b)) return 0
  const ka = headerConcept(a)
  const kb = headerConcept(b)
  const lexical = headerSimilarity(a, b)
  if (ka && kb) return ka === kb ? 0.85 + 0.1 * lexical : 0
  return lexical
}

/** Minimum similarity for an automatic match. */
export const ALIGN_THRESHOLD = 0.6

function isBlankColumn(source: MergeSource, col: string): boolean {
  return source.rows.every((r) => {
    const v: CellValue | undefined = r.values[col]
    return v === null || v === undefined || (typeof v === 'string' && v.trim() === '')
  })
}

function uniqueName(name: string, taken: Iterable<string>): string {
  const used = new Set([...taken].map((t) => t.toLowerCase()))
  used.add(SOURCE_FILE_COLUMN.toLowerCase())
  used.add(SHEET_PAGE_COLUMN.toLowerCase())
  if (!used.has(name.toLowerCase())) return name
  for (let i = 2; ; i++) {
    const n = `${name} (${i})`
    if (!used.has(n.toLowerCase())) return n
  }
}

/**
 * Suggests a mapping: the first source's columns become the output columns; every later source's
 * columns are matched one-to-one to the best output column (highest similarity first, threshold 0.6).
 * Columns with no match become separate output columns; completely empty columns are dropped.
 */
export function suggestMapping(sources: MergeSource[]): MergeMapping {
  const columns: string[] = []
  /** Every header already mapped to each output column (to compare new headers against). */
  const aliases = new Map<string, string[]>()
  const out: MergeMapping['sources'] = {}

  for (const src of sources) {
    const map: Record<string, ColumnTarget> = {}
    const live = src.columns.filter((c) => {
      if (isBlankColumn(src, c)) {
        map[c] = null
        return false
      }
      return true
    })
    const pairs: Array<{ col: string; target: string; score: number }> = []
    for (const col of live) {
      for (const target of columns) {
        const score = Math.max(...(aliases.get(target) ?? [target]).map((h) => columnSimilarity(col, h)))
        if (score >= ALIGN_THRESHOLD) pairs.push({ col, target, score })
      }
    }
    pairs.sort((x, y) => y.score - x.score)
    const usedTargets = new Set<string>()
    for (const p of pairs) {
      if (p.col in map || usedTargets.has(p.target)) continue
      map[p.col] = p.target
      usedTargets.add(p.target)
    }
    for (const col of live) {
      if (col in map) continue
      const name = uniqueName(col, columns)
      columns.push(name)
      aliases.set(name, [col])
      map[col] = name
    }
    for (const col of live) {
      const t = map[col]
      if (t && !aliases.get(t)?.includes(col)) aliases.get(t)?.push(col)
    }
    out[src.id] = map
  }
  return { columns, sources: out }
}

/** Removes output columns no source maps to any more. */
function prune(mapping: MergeMapping): MergeMapping {
  const used = new Set<string>()
  for (const m of Object.values(mapping.sources)) for (const t of Object.values(m)) if (t) used.add(t)
  return { ...mapping, columns: mapping.columns.filter((c) => used.has(c)) }
}

/**
 * Changes where one source column goes: an existing output column, `{ separate: true }` for a new
 * column of its own, or null to drop it. Output columns left without any source are removed.
 */
export function setColumnTarget(
  mapping: MergeMapping,
  sourceId: string,
  column: string,
  target: string | null | { separate: true }
): MergeMapping {
  const sources = { ...mapping.sources, [sourceId]: { ...(mapping.sources[sourceId] ?? {}) } }
  let columns = [...mapping.columns]
  if (target !== null && typeof target === 'object') {
    const name = uniqueName(column, columns)
    const prev = sources[sourceId][column]
    const at = prev ? columns.indexOf(prev) : -1
    if (at >= 0) columns.splice(at + 1, 0, name)
    else columns.push(name)
    sources[sourceId][column] = name
  } else {
    if (target !== null && !columns.includes(target)) throw new Error(`There is no output column called "${target}".`)
    // One source column per output column: whatever else of this source pointed there becomes separate.
    if (target !== null) {
      for (const [c, t] of Object.entries(sources[sourceId])) {
        if (c !== column && t === target) {
          const name = uniqueName(c, columns)
          columns.push(name)
          sources[sourceId][c] = name
        }
      }
    }
    sources[sourceId][column] = target
  }
  columns = columns.filter((c, i) => columns.indexOf(c) === i)
  return prune({ columns, sources })
}

/** Renames an output column everywhere. Throws a plain-English Error for a blank or duplicate name. */
export function renameOutputColumn(mapping: MergeMapping, from: string, to: string): MergeMapping {
  const name = to.replace(/\s+/g, ' ').trim()
  if (name === '') throw new Error('A column name cannot be blank.')
  if (name === from) return mapping
  const clash = [...mapping.columns, SOURCE_FILE_COLUMN, SHEET_PAGE_COLUMN].some((c) => c !== from && c.toLowerCase() === name.toLowerCase())
  if (clash) throw new Error(`There is already a column called "${name}".`)
  const sources: MergeMapping['sources'] = {}
  for (const [id, m] of Object.entries(mapping.sources)) {
    sources[id] = Object.fromEntries(Object.entries(m).map(([c, t]) => [c, t === from ? name : t]))
  }
  return { columns: mapping.columns.map((c) => (c === from ? name : c)), sources }
}

/** Moves an output column one place left (-1) or right (+1). */
export function moveOutputColumn(mapping: MergeMapping, column: string, delta: -1 | 1): MergeMapping {
  const i = mapping.columns.indexOf(column)
  const j = i + delta
  if (i < 0 || j < 0 || j >= mapping.columns.length) return mapping
  const columns = [...mapping.columns]
  ;[columns[i], columns[j]] = [columns[j], columns[i]]
  return { ...mapping, columns }
}

/** Keeps the column choices by header name so they can be re-applied to other files. */
export function recipeFromMapping(
  mapping: MergeMapping,
  sources: MergeSource[],
  opts: Omit<MergeFilesRecipeOptions, 'columns' | 'headerMap'>
): MergeFilesRecipeOptions {
  const headerMap: Record<string, ColumnTarget> = {}
  for (const src of sources) {
    for (const [col, target] of Object.entries(mapping.sources[src.id] ?? {})) {
      const key = headerKey(col)
      if (key && !(key in headerMap)) headerMap[key] = target
    }
  }
  return { ...opts, columns: [...mapping.columns], headerMap }
}

/**
 * Builds a mapping for new files from a recipe: headers the recipe knows go where the recipe says;
 * others follow the automatic suggestion. The recipe's column order is kept.
 */
export function mappingFromRecipe(sources: MergeSource[], recipe: MergeFilesRecipeOptions): MergeMapping {
  const auto = suggestMapping(sources)
  const columns = [...recipe.columns]
  const out: MergeMapping['sources'] = {}
  for (const src of sources) {
    const map: Record<string, ColumnTarget> = {}
    const taken = new Set<string>()
    for (const col of src.columns) {
      const key = headerKey(col)
      if (key in recipe.headerMap) {
        const t = recipe.headerMap[key]
        if (t === null || (columns.includes(t) && !taken.has(t))) {
          map[col] = t
          if (t) taken.add(t)
        }
      }
    }
    for (const col of src.columns) {
      if (col in map) continue
      const suggested = auto.sources[src.id]?.[col] ?? null
      if (suggested === null) {
        map[col] = null
        continue
      }
      // Re-find the best recipe column for this header; else keep it as its own column.
      let best: string | null = null
      let bestScore = ALIGN_THRESHOLD
      for (const c of columns) {
        if (taken.has(c)) continue
        const s = columnSimilarity(col, c)
        if (s >= bestScore) {
          best = c
          bestScore = s
        }
      }
      if (!best) {
        best = uniqueName(col, columns)
        columns.push(best)
      }
      map[col] = best
      taken.add(best)
    }
    out[src.id] = map
  }
  return prune({ columns, sources: out })
}
