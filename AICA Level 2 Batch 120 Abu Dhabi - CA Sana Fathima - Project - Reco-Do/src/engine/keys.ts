// Key preparation, per-key pass/fail tests and the hash indexes used to find candidate pairs.
// Candidates come only from indexes on identifying keys, so rows are never compared all-against-all.

import type { CellValue, EngineLine, MatchKey, ReconConfig, TextRule } from '@shared/contracts'
import { normaliseText, parseAmount } from '@shared/parsing'
import { dayNumber, isIdentifying, toCents, toleranceCents } from './util'

/** Values shorter than this never count as "contained" in another value (too short to identify anything). */
export const MIN_CONTAINS_LENGTH = 3

export type KeyKind = 'text' | 'amount' | 'number' | 'date'

export interface PreparedKey {
  key: MatchKey
  kind: KeyKind
  identifying: boolean
  rule: TextRule
  /** Text: comparable string ('' = missing). Amount: cents. Number: value. Date: day number. null = missing. */
  a: Array<string | number | null>
  b: Array<string | number | null>
  /** Raw display text, for reasons. */
  rawA: string[]
  rawB: string[]
}

export function rawCellText(v: CellValue | undefined): string {
  if (v === null || v === undefined) return ''
  if (v instanceof Date) {
    if (Number.isNaN(v.getTime())) return ''
    const m = String(v.getMonth() + 1).padStart(2, '0')
    const d = String(v.getDate()).padStart(2, '0')
    return `${v.getFullYear()}-${m}-${d}`
  }
  if (typeof v === 'number') return Number.isFinite(v) ? String(v) : ''
  return String(v).replace(/\s+/g, ' ').trim()
}

function textValue(raw: string, rule: TextRule, prefixes: string[]): string {
  if (raw === '') return ''
  switch (rule) {
    case 'exact':
      return raw
    case 'contains':
      return raw.toUpperCase()
    case 'normalised':
      return normaliseText(raw, prefixes)
  }
}

function numberValue(v: CellValue | undefined): number | null {
  if (v === null || v === undefined) return null
  const p = parseAmount(v)
  return p ? p.value : null
}

export function kindOf(k: MatchKey): KeyKind {
  if (k.type === 'amount') return 'amount'
  if (k.type === 'number') return 'number'
  if (k.type === 'date') return 'date'
  return 'text'
}

export function prepareKeys(cfg: ReconConfig, linesA: EngineLine[], linesB: EngineLine[]): PreparedKey[] {
  const prefixes = cfg.referencePrefixes
  return cfg.keys
    .filter((k) => k.use)
    .map((key) => {
      const kind = kindOf(key)
      const rule: TextRule = key.textRule ?? 'normalised'
      const prep = (lines: EngineLine[], col: string): { v: Array<string | number | null>; raw: string[] } => {
        const v: Array<string | number | null> = new Array(lines.length)
        const raw: string[] = new Array(lines.length)
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i]
          if (kind === 'amount') {
            v[i] = line.comparableAmount === null ? null : toCents(line.comparableAmount)
            raw[i] = ''
          } else if (kind === 'date') {
            v[i] = line.date ? dayNumber(line.date) : null
            raw[i] = ''
          } else if (kind === 'number') {
            v[i] = numberValue(line.values[col])
            raw[i] = rawCellText(line.values[col])
          } else {
            const r = rawCellText(line.values[col])
            raw[i] = r
            v[i] = textValue(r, rule, prefixes)
          }
        }
        return { v, raw }
      }
      const pa = prep(linesA, key.columnA)
      const pb = prep(linesB, key.columnB)
      return { key, kind, identifying: isIdentifying(key), rule, a: pa.v, b: pb.v, rawA: pa.raw, rawB: pb.raw }
    })
}

function numberTolerance(k: MatchKey, a: number, b: number): number {
  const t = k.tolerance
  if (!t || t.mode === 'exact') return 1e-9
  if (t.mode === 'fixed') return Math.max(0, t.value) + 1e-9
  return (Math.max(0, t.value) / 100) * Math.min(Math.abs(a), Math.abs(b)) + 1e-9
}

/** Pass/fail of one key for line i (side A) and line j (side B). Missing values always fail. */
export function keyPasses(pk: PreparedKey, i: number, j: number): boolean {
  const va = pk.a[i]
  const vb = pk.b[j]
  if (va === null || vb === null || va === '' || vb === '') return false
  switch (pk.kind) {
    case 'text': {
      const sa = va as string
      const sb = vb as string
      if (sa === sb) return true
      if (pk.rule !== 'contains') return false
      if (sa.length >= sb.length) return sb.length >= MIN_CONTAINS_LENGTH && sa.includes(sb)
      return sa.length >= MIN_CONTAINS_LENGTH && sb.includes(sa)
    }
    case 'amount': {
      const a = va as number
      const b = vb as number
      return Math.abs(a - b) <= toleranceCents(pk.key, a, b) + 1e-9
    }
    case 'number': {
      const a = va as number
      const b = vb as number
      return Math.abs(a - b) <= numberTolerance(pk.key, a, b)
    }
    case 'date':
      return Math.abs((va as number) - (vb as number)) <= Math.max(0, pk.key.dateToleranceDays ?? 0)
  }
}

// ───────────────────────── Candidate indexes ─────────────────────────

/** Values contained in more than this many texts on the other side are too generic to identify a record. */
export const MAX_CONTAINS_FANOUT = 1000

/** Something that, given an A line index, yields candidate B line indexes for one identifying key. */
export interface CandidateSource {
  /** Index of the key in the prepared key list. */
  keyIndex: number
  /**
   * Candidate B indexes for A line i, as one or more lists (a superset: every pair is still verified by
   * keyPasses). Returns null when A's value for this key is missing, so the key can never pass for line i.
   * The returned arrays are owned by the index and must not be modified; identical values share one array.
   */
  lists(i: number): number[][] | null
  /** Convenience: adds every candidate from lists(i). */
  collect(i: number, add: (j: number) => void): void
}

function pushTo<K>(m: Map<K, number[]>, key: K, j: number): void {
  const list = m.get(key)
  if (list) list.push(j)
  else m.set(key, [j])
}

function makeSource(keyIndex: number, lists: (i: number) => number[][] | null): CandidateSource {
  return {
    keyIndex,
    lists,
    collect(i, add) {
      const ls = lists(i)
      if (ls) for (const l of ls) for (const j of l) add(j)
    }
  }
}

const EMPTY: number[] = []

/** Exact equality on prepared values (text exact / normalised rules). */
function equalityLookup(pk: PreparedKey): (i: number) => number[] | null {
  const m = new Map<string | number, number[]>()
  for (let j = 0; j < pk.b.length; j++) {
    const v = pk.b[j]
    if (v === null || v === '') continue
    pushTo(m, v, j)
  }
  return (i) => {
    const v = pk.a[i]
    if (v === null || v === '') return null
    return m.get(v) ?? EMPTY
  }
}

function trigrams(s: string): string[] {
  const out = new Set<string>()
  for (let k = 0; k + 3 <= s.length; k++) out.add(s.slice(k, k + 3))
  return Array.from(out)
}

/**
 * "Contains" rule: A's value inside B's text, or B's value inside A's text. Each side's strings are indexed by
 * trigram; a needle is looked up through its rarest trigram and the hits are verified with `includes`, so the
 * lists are exact. A value contained in more than MAX_CONTAINS_FANOUT texts on the other side is skipped in the
 * reverse direction (it is too generic to identify a record, and indexing it would be quadratic).
 */
function containsLookup(pk: PreparedKey): (i: number) => number[][] | null {
  const buildTri = (vals: Array<string | number | null>): Map<string, number[]> => {
    const m = new Map<string, number[]>()
    for (let x = 0; x < vals.length; x++) {
      const s = vals[x]
      if (typeof s !== 'string' || s.length < MIN_CONTAINS_LENGTH) continue
      for (const t of trigrams(s)) pushTo(m, t, x)
    }
    return m
  }
  const lookup = (tri: Map<string, number[]>, vals: Array<string | number | null>, needle: string): number[] => {
    let best: number[] | undefined
    for (const t of trigrams(needle)) {
      const list = tri.get(t)
      if (!list) return EMPTY
      if (!best || list.length < best.length) best = list
    }
    if (!best) return EMPTY
    const out: number[] = []
    for (const x of best) {
      const s = vals[x]
      if (typeof s === 'string' && s !== needle && s.includes(needle)) out.push(x)
    }
    return out
  }
  const eq = equalityLookup(pk) // short values still match when exactly equal
  const triB = buildTri(pk.b)
  const triA = buildTri(pk.a)
  // Reverse direction (B's value inside A's text), precomputed per A line.
  const reverse = new Map<number, number[]>()
  const reverseByNeedle = new Map<string, number[]>()
  for (let j = 0; j < pk.b.length; j++) {
    const s = pk.b[j]
    if (typeof s !== 'string' || s.length < MIN_CONTAINS_LENGTH) continue
    let hits = reverseByNeedle.get(s)
    if (!hits) {
      hits = lookup(triA, pk.a, s)
      reverseByNeedle.set(s, hits)
    }
    if (hits.length > MAX_CONTAINS_FANOUT) continue
    for (const i of hits) pushTo(reverse, i, j)
  }
  const forwardByNeedle = new Map<string, number[]>()
  return (i) => {
    const e = eq(i)
    if (e === null) return null
    const out: number[][] = [e]
    const s = pk.a[i]
    if (typeof s === 'string' && s.length >= MIN_CONTAINS_LENGTH) {
      let f = forwardByNeedle.get(s)
      if (!f) {
        f = lookup(triB, pk.b, s)
        forwardByNeedle.set(s, f)
      }
      out.push(f)
    }
    const r = reverse.get(i)
    if (r) out.push(r)
    return out
  }
}

/**
 * Numeric buckets that respect the tolerance:
 *  exact → one bucket per value; fixed → buckets of the tolerance width (neighbours searched);
 *  percent → logarithmic buckets of ratio (1 + p), so values within p% sit in the same or a neighbouring bucket.
 * `unitScale` converts the tolerance into value units (100 for amounts held in cents, 1 for numbers).
 */
function numericLookup(pk: PreparedKey, unitScale: number): (i: number) => number[][] | null {
  const t = pk.key.tolerance
  const val = (arr: Array<string | number | null>, x: number): number | null => {
    const v = arr[x]
    return typeof v === 'number' && Number.isFinite(v) ? v : null
  }
  let bucketsOf: (v: number) => Array<string | number>
  let homeOf: (v: number) => string | number
  if (!t || t.mode === 'exact' || !(t.value > 0)) {
    // Amounts are integer cents already; numbers are rounded to 6 decimals to absorb float noise.
    homeOf = unitScale === 100 ? (v) => v : (v) => Math.round(v * 1e6)
    bucketsOf = (v) => [homeOf(v)]
  } else if (t.mode === 'fixed') {
    const width = Math.max(t.value * unitScale, 1e-6)
    homeOf = (v) => Math.floor(v / width)
    bucketsOf = (v) => {
      const b = Math.floor(v / width)
      return [b - 1, b, b + 1]
    }
  } else {
    const logBase = Math.log(1 + t.value / 100)
    homeOf = (v) => (v === 0 ? 'z' : `${v < 0 ? '-' : '+'}${Math.floor(Math.log(Math.abs(v)) / logBase)}`)
    bucketsOf = (v) => {
      if (v === 0) return ['z']
      const sign = v < 0 ? '-' : '+'
      const b = Math.floor(Math.log(Math.abs(v)) / logBase)
      return [`${sign}${b - 1}`, `${sign}${b}`, `${sign}${b + 1}`]
    }
  }
  const m = new Map<string | number, number[]>()
  for (let j = 0; j < pk.b.length; j++) {
    const v = val(pk.b, j)
    if (v !== null) pushTo(m, homeOf(v), j)
  }
  return (i) => {
    const v = val(pk.a, i)
    if (v === null) return null
    const out: number[][] = []
    for (const b of bucketsOf(v)) {
      const list = m.get(b)
      if (list) out.push(list)
    }
    return out
  }
}

/** One candidate source per identifying key (dates and non-ID text never generate candidates). */
export function buildCandidateSources(keys: PreparedKey[]): CandidateSource[] {
  const out: CandidateSource[] = []
  keys.forEach((pk, k) => {
    if (!pk.identifying) return
    if (pk.kind === 'text') {
      if (pk.rule === 'contains') out.push(makeSource(k, containsLookup(pk)))
      else {
        const eq = equalityLookup(pk)
        out.push(
          makeSource(k, (i) => {
            const l = eq(i)
            return l === null ? null : [l]
          })
        )
      }
    } else if (pk.kind === 'amount') out.push(makeSource(k, numericLookup(pk, 100))) // values are integer cents
    else if (pk.kind === 'number') out.push(makeSource(k, numericLookup(pk, 1)))
  })
  return out
}
