// Smart Recon, code side: partial reference matching (master prompt §4 Step 4).
// Tokens are pulled from each line's reference/ID columns (digit runs of 4+ characters and alphanumeric codes)
// and looked for inside the other side's text columns, e.g. bank ref "FT2609ABC" inside GL remarks
// "Rcpt FT2609ABC - Al Noor Trading LLC".

import type { EngineLine, ReconConfig, ReconResult, Side, Suggestion } from '@shared/contracts'
import { rawCellText } from '../keys'
import { amountKeyOf, dateKeyOf, dayNumber, fmtMoney, newId, sideWord, toCents, toleranceCents, upperFirst } from '../util'
import { eligiblePools } from './common'

/** A token found in more lines than this on the other side is too common to identify anything. */
const MAX_TOKEN_HITS = 3

/** Digit runs of 4+ characters and letter+digit codes of 4+ characters; digits lose leading zeros. */
export function extractTokens(text: string): string[] {
  const out = new Set<string>()
  for (const raw of text.toUpperCase().match(/[A-Z0-9]+/g) ?? []) {
    if (raw.length < 4) continue
    const hasDigit = /\d/.test(raw)
    if (!hasDigit) continue
    if (/^\d+$/.test(raw)) {
      out.add(raw.replace(/^0+(?=\d)/, ''))
    } else if (/[A-Z]/.test(raw)) out.add(raw)
  }
  return Array.from(out)
}

function referenceColumns(cfg: ReconConfig, side: Side): string[] {
  return cfg.keys.filter((k) => k.use && (k.type === 'id' || k.type === 'text')).map((k) => (side === 'A' ? k.columnA : k.columnB))
}

function textTokens(l: EngineLine): Map<string, string> {
  // token → the column it came from
  const out = new Map<string, string>()
  for (const [col, v] of Object.entries(l.values)) {
    if (typeof v !== 'string' && typeof v !== 'number') continue
    for (const t of extractTokens(rawCellText(v))) if (!out.has(t)) out.set(t, col)
  }
  return out
}

interface Hit {
  a: EngineLine
  b: EngineLine
  token: string
  fromSide: Side
  column: string
  dateOk: boolean
  confidence: number
}

export function findPartialReferenceMatches(result: ReconResult, opts: { includeDoubtful?: boolean } = {}): Suggestion[] {
  const cfg = result.config
  const pools = eligiblePools(result, opts.includeDoubtful ?? false)
  if (pools.a.length === 0 || pools.b.length === 0) return []
  const amountKey = amountKeyOf(cfg)
  const dateKey = dateKeyOf(cfg)
  const refColsA = referenceColumns(cfg, 'A')
  const refColsB = referenceColumns(cfg, 'B')
  if (refColsA.length === 0 && refColsB.length === 0) return []

  const hits: Hit[] = []
  const scan = (from: EngineLine[], fromCols: string[], to: EngineLine[], fromSide: Side): void => {
    if (fromCols.length === 0) return
    const index = new Map<string, Array<{ line: EngineLine; column: string }>>()
    for (const l of to) {
      for (const [t, col] of textTokens(l)) {
        const list = index.get(t)
        if (list) list.push({ line: l, column: col })
        else index.set(t, [{ line: l, column: col }])
      }
    }
    for (const l of from) {
      const tokens = new Set<string>()
      for (const col of fromCols) for (const t of extractTokens(rawCellText(l.values[col]))) tokens.add(t)
      for (const t of tokens) {
        const list = index.get(t)
        if (!list || list.length > MAX_TOKEN_HITS) continue
        for (const { line: other, column } of list) {
          const a = fromSide === 'A' ? l : other
          const b = fromSide === 'A' ? other : l
          // Lines already together in an open Doubtful pair are still suggested: the token confirms that pair
          // (e.g. reference blank in one column but present in the narration), and approving it closes the pair.
          if (amountKey) {
            if (a.comparableAmount === null || b.comparableAmount === null) continue
            const ca = toCents(a.comparableAmount)
            const cb = toCents(b.comparableAmount)
            // Conservative: with an amount key, a reference hit alone is not enough; the amounts must reconcile.
            if (Math.abs(ca - cb) > toleranceCents(amountKey, ca, cb) + 1e-9) continue
          }
          let dateOk = false
          if (dateKey && a.date && b.date) dateOk = Math.abs(dayNumber(a.date) - dayNumber(b.date)) <= (dateKey.dateToleranceDays ?? 0)
          const confidence = amountKey ? (dateOk ? 85 : 70) : dateOk ? 70 : 60
          hits.push({ a, b, token: t, fromSide, column, dateOk, confidence })
        }
      }
    }
  }
  scan(pools.a, refColsA, pools.b, 'A')
  scan(pools.b, refColsB, pools.a, 'B')

  // Merge both directions: one entry per (a, b), keeping the strongest.
  const byPair = new Map<string, Hit>()
  for (const h of hits) {
    const k = `${h.a.id}|${h.b.id}`
    const prev = byPair.get(k)
    if (!prev || h.confidence > prev.confidence) byPair.set(k, h)
  }
  const unique = Array.from(byPair.values())

  // Never guess: a line with two or more equally strong hits gets no suggestion.
  const top = new Map<string, { confidence: number; count: number }>()
  const note = (id: string, confidence: number): void => {
    const t = top.get(id)
    if (!t || confidence > t.confidence) top.set(id, { confidence, count: 1 })
    else if (confidence === t.confidence) t.count++
  }
  for (const h of unique) {
    note(h.a.id, h.confidence)
    note(h.b.id, h.confidence)
  }
  const ambiguous = new Set<string>()
  for (const [id, t] of top) if (t.count > 1) ambiguous.add(id)

  unique.sort((x, y) => y.confidence - x.confidence || x.a.id.localeCompare(y.a.id) || x.b.id.localeCompare(y.b.id))
  const used = new Set<string>()
  const out: Suggestion[] = []
  for (const h of unique) {
    if (ambiguous.has(h.a.id) || ambiguous.has(h.b.id)) continue
    if (used.has(h.a.id) || used.has(h.b.id)) continue
    used.add(h.a.id)
    used.add(h.b.id)
    out.push({ id: newId('sug-ref'), aIds: [h.a.id], bIds: [h.b.id], confidence: h.confidence, reason: reasonFor(cfg, h), source: 'code-partial-ref', status: 'open' })
  }
  return out
}

function reasonFor(cfg: ReconConfig, h: Hit): string {
  const fromWord = sideWord(cfg, h.fromSide)
  const toWord = sideWord(cfg, h.fromSide === 'A' ? 'B' : 'A')
  const target = h.fromSide === 'A' ? h.b : h.a
  const text = rawCellText(target.values[h.column])
  const shown = text.length > 60 ? `${text.slice(0, 59)}…` : text
  let s = `${upperFirst(fromWord)} reference "${h.token}" found in ${toWord} ${h.column} ("${shown}")`
  if (amountKeyOf(cfg) && h.a.comparableAmount !== null) s += `; amounts agree (${fmtMoney(Math.abs(h.a.comparableAmount))})`
  if (dateKeyOf(cfg)) s += h.dateOk ? '; dates within tolerance' : '; dates outside tolerance'
  return s
}
