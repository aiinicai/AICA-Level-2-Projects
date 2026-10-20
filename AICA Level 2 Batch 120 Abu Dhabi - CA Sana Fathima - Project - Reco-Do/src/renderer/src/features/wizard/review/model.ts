// Pure view-model helpers for the Review & Export screen: KPI totals, tab rows, display columns and search.

import type { CellValue, EngineLine, MatchPair, ReconConfig, ReconResult, ReconSession, Side, Suggestion, Tier } from '@shared/contracts'
import { formatDate } from '@shared/format'

export type ReviewTab = 'matched' | 'doubtful' | 'likely' | 'unmatchedA' | 'unmatchedB' | 'ai'
export const REVIEW_TABS: ReviewTab[] = ['matched', 'doubtful', 'likely', 'unmatchedA', 'unmatchedB', 'ai']

export interface Kpi {
  count: number
  /** Null when the recon has no amount key (counts only). */
  amount: number | null
}

export interface ReviewKpis {
  matched: Kpi
  doubtful: Kpi
  likely: Kpi
  unmatchedA: Kpi
  unmatchedB: Kpi
  aiPending: Kpi
  hasAmount: boolean
}

export function lineIndex(r: ReconResult): Map<string, EngineLine> {
  const m = new Map<string, EngineLine>()
  for (const l of r.linesA) m.set(l.id, l)
  for (const l of r.linesB) m.set(l.id, l)
  return m
}

export function configHasAmount(cfg: ReconConfig): boolean {
  return cfg.keys.some((k) => k.use && k.type === 'amount')
}

const round2 = (n: number): number => Math.round((n + Number.EPSILON) * 100) / 100

function absSum(ids: string[], idx: Map<string, EngineLine>): number {
  let t = 0
  for (const id of ids) t += Math.abs(idx.get(id)?.comparableAmount ?? 0)
  return round2(t)
}

/** KPI cards: File A line counts per tier (README convention), File B for Unmatched B; amounts are absolute sums. */
export function reviewKpis(s: ReconSession, idx: Map<string, EngineLine> = lineIndex(s.result)): ReviewKpis {
  const r = s.result
  const hasAmount = configHasAmount(r.config)
  const tierAmount = (tier: Tier): number | null => (hasAmount ? absSum(r.pairs.filter((p) => p.tier === tier).flatMap((p) => p.aIds), idx) : null)
  const pending = s.suggestions.filter((x) => x.status === 'open')
  return {
    hasAmount,
    matched: { count: r.stats.matched, amount: hasAmount ? r.stats.matchedAmount : null },
    doubtful: { count: r.stats.doubtful, amount: tierAmount('doubtful') },
    likely: { count: r.stats.likely, amount: tierAmount('likely') },
    unmatchedA: { count: r.stats.unmatchedA, amount: hasAmount ? absSum(r.unmatchedA, idx) : null },
    unmatchedB: { count: r.stats.unmatchedB, amount: hasAmount ? absSum(r.unmatchedB, idx) : null },
    aiPending: { count: pending.length, amount: hasAmount ? absSum(pending.flatMap((x) => x.aIds), idx) : null }
  }
}

/** Pairs shown on a tier tab, in File A order. */
export function pairsForTier(r: ReconResult, tier: Exclude<Tier, 'unmatched'>): MatchPair[] {
  const order = new Map<string, number>()
  r.linesA.forEach((l, i) => order.set(l.id, i))
  const pos = (p: MatchPair): number => Math.min(...p.aIds.map((id) => order.get(id) ?? Number.MAX_SAFE_INTEGER))
  return r.pairs.filter((p) => p.tier === tier).sort((x, y) => pos(x) - pos(y))
}

export function unmatchedLines(r: ReconResult, side: Side, idx: Map<string, EngineLine>): EngineLine[] {
  const ids = side === 'A' ? r.unmatchedA : r.unmatchedB
  const out: EngineLine[] = []
  for (const id of ids) {
    const l = idx.get(id)
    if (l) out.push(l)
  }
  return out
}

/** Pending suggestions first (highest confidence first), then decided ones. */
export function sortedSuggestions(list: Suggestion[]): Suggestion[] {
  const rank = (x: Suggestion): number => (x.status === 'open' ? 0 : x.status === 'accepted' ? 1 : 2)
  return [...list].sort((a, b) => rank(a) - rank(b) || b.confidence - a.confidence)
}

export interface DisplayColumn {
  label: string
  column: string
  kind: 'date' | 'key' | 'detail'
}

const DETAIL_HEADER = /desc|narrat|remark|particular|detail|memo|party|customer|supplier|name/i

/**
 * Columns shown for one side in the result rows: the date key, the text/ID/number keys, then one
 * descriptive column (Description, Remarks, Narration…) when the file has one that is not already shown.
 */
export function displayColumns(cfg: ReconConfig, side: Side, available: string[]): DisplayColumn[] {
  const out: DisplayColumn[] = []
  const seen = new Set<string>()
  const col = (k: { columnA: string; columnB: string }): string => (side === 'A' ? k.columnA : k.columnB)
  const used = cfg.keys.filter((k) => k.use)
  const dateKey = used.find((k) => k.type === 'date')
  if (dateKey && col(dateKey)) {
    out.push({ label: col(dateKey), column: col(dateKey), kind: 'date' })
    seen.add(col(dateKey))
  }
  for (const k of used) {
    if (k.type === 'amount' || k.type === 'date') continue
    const c = col(k)
    if (!c || seen.has(c)) continue
    seen.add(c)
    out.push({ label: c, column: c, kind: 'key' })
  }
  const amountCols = new Set<string>()
  const layout = side === 'A' ? cfg.amountA : cfg.amountB
  if (layout) for (const c of Object.values(layout)) if (typeof c === 'string') amountCols.add(c)
  const detail = available.find((c) => !seen.has(c) && !amountCols.has(c) && DETAIL_HEADER.test(c))
  if (detail) out.push({ label: detail, column: detail, kind: 'detail' })
  return out
}

export function cellText(v: CellValue | undefined): string {
  if (v === null || v === undefined) return ''
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? '' : formatDate(v)
  if (typeof v === 'number') return String(v)
  return v
}

/** Every value of the given lines, lower-cased, for the per-tab search box. */
export function lineSearchText(lines: EngineLine[]): string {
  const parts: string[] = []
  for (const l of lines) {
    for (const v of Object.values(l.values)) {
      const t = cellText(v)
      if (t) parts.push(t)
    }
    if (l.amount !== null) parts.push(l.amount.toFixed(2), Math.abs(l.amount).toFixed(2))
  }
  return parts.join(' ').toLowerCase()
}

export function pairSearchText(p: MatchPair, idx: Map<string, EngineLine>): string {
  const lines = [...p.aIds, ...p.bIds].map((id) => idx.get(id)).filter((l): l is EngineLine => !!l)
  return `${lineSearchText(lines)} ${p.reason} ${p.note ?? ''} ${p.label ?? ''}`.toLowerCase()
}

/** True when every word of the query appears somewhere in the text. Amount-like words ignore thousand separators. */
export function matchesQuery(text: string, query: string): boolean {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  return words.every((w) => text.includes(/^[\d,.-]+$/.test(w) ? w.replace(/,/g, '') : w))
}

/** Sum of comparable amounts (side A's sign convention) of a set of lines. */
export function comparableTotal(ids: Iterable<string>, idx: Map<string, EngineLine>): number {
  let t = 0
  for (const id of ids) t += idx.get(id)?.comparableAmount ?? 0
  return round2(t)
}

/** Sum of own-terms amounts of a set of lines. */
export function ownTotal(ids: Iterable<string>, idx: Map<string, EngineLine>): number {
  let t = 0
  for (const id of ids) t += idx.get(id)?.amount ?? 0
  return round2(t)
}

/** "Bank r12" style label from a line id such as "A:r12" → "row 12". */
export function rowLabel(lineId: string): string {
  const m = /:r(\d+)$/.exec(lineId)
  return m ? `row ${m[1]}` : lineId
}

/** Runs an action on many ids, collecting plain-English errors instead of stopping at the first. */
export function applyMany<S>(state: S, ids: string[], fn: (s: S, id: string) => S): { state: S; done: number; errors: string[] } {
  let cur = state
  let done = 0
  const errors: string[] = []
  for (const id of ids) {
    try {
      cur = fn(cur, id)
      done++
    } catch (err) {
      errors.push(err instanceof Error ? err.message : String(err))
    }
  }
  return { state: cur, done, errors }
}
