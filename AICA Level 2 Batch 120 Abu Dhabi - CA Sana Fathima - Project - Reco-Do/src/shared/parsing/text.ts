// Text normalisation for references and IDs, plus value overlap between two columns.

import type { CellValue } from '../contracts'

/** Prefixes stripped by the "Normalised" rule when they start a word (e.g. "CHQ 004512" → "4512"). */
export const DEFAULT_REFERENCE_PREFIXES: string[] = [
  'CHQ',
  'CHEQUE',
  'CHECK',
  'CHK',
  'FT',
  'TT',
  'INV',
  'INVOICE',
  'REF',
  'REFNO',
  'POS',
  'RCPT',
  'RECEIPT',
  'DD',
  'TRF',
  'NO'
]

const SEPARATORS = /[\s\-–—‒−/\\.·_#:,;'"`|]+/g
const LEADING_ZEROS = /(?<!\d)0+(?=\d)/g

const prefixRegexCache = new Map<string, RegExp | null>()

function prefixRegex(prefixes: string[]): RegExp | null {
  const key = prefixes.join('\u0001')
  const cached = prefixRegexCache.get(key)
  if (cached !== undefined) return cached
  const cleaned = Array.from(
    new Set(prefixes.map((p) => p.trim().toLowerCase()).filter((p) => p.length > 0))
  )
    .sort((a, b) => b.length - a.length)
    .map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  // A prefix counts only at the start of a word and when not followed by another letter
  // ("REF 123", "FT2609ABC", "INV-00123" — but not "REFUND" or "POSITION").
  const re = cleaned.length > 0 ? new RegExp(`(?<![a-z0-9])(?:${cleaned.join('|')})(?![a-z])`, 'g') : null
  if (prefixRegexCache.size > 50) prefixRegexCache.clear()
  prefixRegexCache.set(key, re)
  return re
}

function stripSeparators(s: string): string {
  return s.replace(SEPARATORS, '')
}

/**
 * Normalises a reference or ID for comparison: lower-case; removes the configured prefixes at word starts,
 * then spaces, dashes, slashes and dots (so digit groups joined by separators form one run, e.g. a spaced IBAN),
 * then the leading zeros of each remaining number.
 * "INV-00123" and "123" both become "123"; "CHQ 004512" becomes "4512"; "AE07 0331 2345" equals "AE0703312345". When stripping would leave nothing (e.g. "INV" alone), a less
 * aggressive form is returned so the result stays non-empty.
 */
export function normaliseText(s: string, prefixes: string[] = DEFAULT_REFERENCE_PREFIXES): string {
  if (s === null || s === undefined) return ''
  const lower = String(s).normalize('NFKC').toLowerCase().trim()
  if (lower === '') return ''
  const re = prefixRegex(prefixes)
  const withoutPrefixes = re ? lower.replace(re, ' ') : lower
  const full = stripSeparators(withoutPrefixes).replace(LEADING_ZEROS, '')
  if (full !== '') return full
  const noPrefixStrip = stripSeparators(lower).replace(LEADING_ZEROS, '')
  if (noPrefixStrip !== '') return noPrefixStrip
  return lower
}

/** A comparable key for any cell value (used by value overlap and matching helpers). */
export function cellKey(v: CellValue, prefixes: string[] = DEFAULT_REFERENCE_PREFIXES): string {
  if (v === null || v === undefined) return ''
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) return ''
    if (Number.isInteger(v)) return String(Math.abs(v) === 0 ? 0 : v)
    return String(Math.round(v * 100) / 100)
  }
  if (v instanceof Date) {
    if (Number.isNaN(v.getTime())) return ''
    return `d:${v.getFullYear()}-${v.getMonth() + 1}-${v.getDate()}`
  }
  return normaliseText(v, prefixes)
}

const OVERLAP_SAMPLE = 2000

function keysOf(values: CellValue[]): string[] {
  const out: string[] = []
  for (const v of values) {
    const k = cellKey(v)
    if (k !== '') out.push(k)
  }
  return out
}

/** Deterministic pseudo-random sample of distinct values (fixed seed, so results are repeatable). */
function sampleDistinct(keys: string[], limit: number): string[] {
  const distinct = Array.from(new Set(keys))
  if (distinct.length <= limit) return distinct
  let seed = 0x9e3779b9
  const next = (): number => {
    // mulberry32
    seed = (seed + 0x6d2b79f5) | 0
    let t = seed
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
  // Partial Fisher-Yates shuffle: the first `limit` slots become the sample.
  for (let i = 0; i < limit; i++) {
    const j = i + Math.floor(next() * (distinct.length - i))
    const tmp = distinct[i]
    distinct[i] = distinct[j]
    distinct[j] = tmp
  }
  return distinct.slice(0, limit)
}

export interface ValueOverlapOptions {
  /**
   * Measure in both directions, weighted by rows: the share of A's non-empty values found in B and the share of
   * B's found in A, whichever is lower. A column that repeats one value (e.g. a payroll pay date) that happens to
   * appear on the other side then scores low instead of 100%. Default false.
   */
  mutual?: boolean
}

function rowShare(rows: string[], other: Set<string>): number {
  let hits = 0
  for (const k of rows) if (other.has(k)) hits++
  return hits / rows.length
}

/**
 * Share (0..1) of the smaller column's distinct normalised non-empty values that also appear in the other
 * column. At most 2,000 values of the smaller column are sampled. Empty columns give 0.
 * With `mutual`, see ValueOverlapOptions.
 */
export function valueOverlap(a: CellValue[], b: CellValue[], opts: ValueOverlapOptions = {}): number {
  const ka = keysOf(a)
  const kb = keysOf(b)
  if (ka.length === 0 || kb.length === 0) return 0
  const setA = new Set(ka)
  const setB = new Set(kb)
  if (opts.mutual) return Math.min(rowShare(ka, setB), rowShare(kb, setA))
  const [small, otherSet] = setA.size <= setB.size ? [ka, setB] : [kb, setA]
  const sample = sampleDistinct(small, OVERLAP_SAMPLE)
  let hits = 0
  for (const k of sample) if (otherSet.has(k)) hits++
  return hits / sample.length
}
