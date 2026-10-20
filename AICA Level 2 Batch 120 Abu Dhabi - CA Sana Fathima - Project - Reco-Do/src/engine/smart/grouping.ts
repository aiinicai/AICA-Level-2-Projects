// Smart Recon, code side: one-to-many / many-to-one sum matching (master prompt §4 Step 4).
// For each eligible line, a bounded subset-sum search looks for 2..maxGroupSize lines on the other side whose
// total equals it within the amount tolerance, inside the date window and, where the "many" side has a party
// column, for one party. The search is pruned and capped; `capped` reports when a cap cut the search short.

import type { EngineLine, ReconConfig, ReconResult, Side, Suggestion } from '@shared/contracts'
import { normaliseText } from '@shared/parsing'
import { rawCellText } from '../keys'
import { amountKeyOf, dateKeyOf, dayNumber, fmtDate, fmtMoney, newId, plural, sideWord, toCents, toleranceCents, upperFirst } from '../util'
import { eligiblePools } from './common'

export interface GroupMatchOptions {
  /** Largest group on the "many" side (default 5, minimum 2). */
  maxGroupSize?: number
  /** Most candidate lines considered for one target line (default 40); more than this sets `capped`. */
  maxCandidates?: number
  includeDoubtful?: boolean
}

/** Search steps allowed per target line before the search is cut short (and `capped` is reported). */
const NODE_BUDGET = 50_000
/** Distinct groupings collected per target line before stopping. */
const MAX_SOLUTIONS_PER_TARGET = 5

interface Item {
  line: EngineLine
  cents: number
  abs: number
  day: number | null
  party: string | null
}

interface Solution {
  target: Item
  targetSide: Side
  members: Item[]
  diff: number
  spread: number
  alternatives: number
}

function partyOf(cfg: ReconConfig, l: EngineLine): string | null {
  const col = l.side === 'A' ? cfg.partyColumnA : cfg.partyColumnB
  if (!col) return null
  return normaliseText(rawCellText(l.values[col]), [])
}

function toItems(cfg: ReconConfig, lines: EngineLine[]): Item[] {
  const out: Item[] = []
  for (const line of lines) {
    if (line.comparableAmount === null) continue
    const cents = toCents(line.comparableAmount)
    if (cents === 0) continue
    out.push({ line, cents, abs: Math.abs(cents), day: line.date ? dayNumber(line.date) : null, party: partyOf(cfg, line) })
  }
  return out
}

export function findGroupMatches(result: ReconResult, opts: GroupMatchOptions = {}): { suggestions: Suggestion[]; capped: boolean } {
  const cfg = result.config
  const amountKey = amountKeyOf(cfg)
  if (!amountKey) return { suggestions: [], capped: false }
  const maxGroup = Math.max(2, Math.floor(opts.maxGroupSize ?? 5))
  const maxCandidates = Math.max(2, Math.floor(opts.maxCandidates ?? 40))
  const dateKey = dateKeyOf(cfg)
  const window = dateKey ? Math.max(0, dateKey.dateToleranceDays ?? 0) : null
  const pools = eligiblePools(result, opts.includeDoubtful ?? false)
  const itemsA = toItems(cfg, pools.a)
  const itemsB = toItems(cfg, pools.b)
  let capped = false
  const solutions: Solution[] = []

  const run = (targets: Item[], members: Item[], targetSide: Side): void => {
    const memberSide: Side = targetSide === 'A' ? 'B' : 'A'
    const memberHasParty = memberSide === 'A' ? !!cfg.partyColumnA : !!cfg.partyColumnB
    // Members sorted by day for the date-window lookup.
    const byDay = window === null ? members : members.filter((m) => m.day !== null).sort((x, y) => (x.day as number) - (y.day as number))
    const lowerBound = (day: number): number => {
      let lo = 0
      let hi = byDay.length
      while (lo < hi) {
        const mid = (lo + hi) >> 1
        if ((byDay[mid].day as number) < day) lo = mid + 1
        else hi = mid
      }
      return lo
    }
    for (const t of targets) {
      if (window !== null && t.day === null) continue
      let pool: Item[]
      if (window === null) pool = byDay
      else {
        pool = []
        const from = lowerBound((t.day as number) - window)
        for (let k = from; k < byDay.length && (byDay[k].day as number) <= (t.day as number) + window; k++) pool.push(byDay[k])
      }
      const tol = toleranceCents(amountKey, t.cents, t.cents)
      // Conservative choice: members carry the same sign as the target (no netting of mixed signs) and none is
      // larger than the target. Where the "many" side has a party column, a group forms only from lines of one
      // party. The target's own party is not compared: the two files often name the party differently
      // (e.g. intercompany files each name the other entity), which is exactly what code cannot judge.
      let eligible = pool.filter((m) => Math.sign(m.cents) === Math.sign(t.cents) && m.abs <= t.abs + tol)
      if (eligible.length < 2) continue
      if (eligible.length > maxCandidates) {
        capped = true
        eligible = eligible
          .slice()
          .sort((x, y) => Math.abs((x.day ?? 0) - (t.day ?? 0)) - Math.abs((y.day ?? 0) - (t.day ?? 0)) || y.abs - x.abs)
          .slice(0, maxCandidates)
      }
      const buckets = new Map<string, Item[]>()
      for (const m of eligible) {
        const key = memberHasParty ? (m.party ?? '') : ''
        const list = buckets.get(key)
        if (list) list.push(m)
        else buckets.set(key, [m])
      }
      const found: Item[][] = []
      for (const list of buckets.values()) {
        if (list.length < 2) continue
        list.sort((x, y) => y.abs - x.abs || x.line.id.localeCompare(y.line.id))
        if (search(list, t.abs, tol, maxGroup, found)) capped = true
        if (found.length >= MAX_SOLUTIONS_PER_TARGET) break
      }
      if (found.length === 0) continue
      const ranked = found
        .map((members) => {
          const total = members.reduce((s, m) => s + m.abs, 0)
          const spread = t.day === null ? 0 : Math.max(...members.map((m) => (m.day === null ? 0 : Math.abs(m.day - (t.day as number)))))
          return { members, diff: Math.abs(total - t.abs), spread }
        })
        .sort((x, y) => x.diff - y.diff || x.members.length - y.members.length || x.spread - y.spread)
      const best = ranked[0]
      solutions.push({ target: t, targetSide, members: best.members, diff: best.diff, spread: best.spread, alternatives: ranked.length - 1 })
    }
  }

  run(itemsA, itemsB, 'A')
  run(itemsB, itemsA, 'B')

  // Keep a set of suggestions that never share a line: best confidence first, then smaller groups.
  const scored = solutions.map((s) => ({ s, confidence: s.alternatives > 0 ? 55 : s.diff === 0 ? 90 : 75 }))
  scored.sort((x, y) => y.confidence - x.confidence || x.s.members.length - y.s.members.length || x.s.spread - y.s.spread || x.s.target.line.id.localeCompare(y.s.target.line.id))
  const used = new Set<string>()
  const suggestions: Suggestion[] = []
  for (const { s, confidence } of scored) {
    const ids = [s.target.line.id, ...s.members.map((m) => m.line.id)]
    if (ids.some((id) => used.has(id))) continue
    for (const id of ids) used.add(id)
    const memberIds = s.members.map((m) => m.line.id)
    suggestions.push({
      id: newId('sug-group'),
      aIds: s.targetSide === 'A' ? [s.target.line.id] : memberIds,
      bIds: s.targetSide === 'A' ? memberIds : [s.target.line.id],
      confidence,
      reason: groupReason(cfg, s, window),
      source: 'code-group',
      status: 'open'
    })
  }
  return { suggestions, capped }
}

/**
 * Bounded subset-sum over `items` (sorted by absolute amount, largest first). Appends every group of 2..maxSize
 * whose total is within `tol` of `target`. Returns true when the node budget ran out.
 */
function search(items: Item[], target: number, tol: number, maxSize: number, out: Item[][]): boolean {
  const n = items.length
  const amounts = items.map((x) => x.abs)
  let nodes = 0
  let exhausted = false
  const chosen: number[] = []
  const dfs = (start: number, sum: number): void => {
    if (exhausted || out.length >= MAX_SOLUTIONS_PER_TARGET) return
    for (let k = start; k < n; k++) {
      if (++nodes > NODE_BUDGET) {
        exhausted = true
        return
      }
      const next = sum + amounts[k]
      if (next > target + tol) continue // too big; smaller items follow
      // Upper bound: even the largest remaining items cannot reach the target → nothing further can.
      const slots = maxSize - chosen.length
      let best = next
      for (let q = k + 1; q < n && q < k + slots; q++) best += amounts[q]
      if (best < target - tol) return
      chosen.push(k)
      if (chosen.length >= 2 && Math.abs(next - target) <= tol) out.push(chosen.map((c) => items[c]))
      if (chosen.length < maxSize) dfs(k + 1, next)
      chosen.pop()
      if (exhausted || out.length >= MAX_SOLUTIONS_PER_TARGET) return
    }
  }
  dfs(0, 0)
  return exhausted
}

function groupReason(cfg: ReconConfig, s: Solution, window: number | null): string {
  const targetWord = sideWord(cfg, s.targetSide)
  const memberWord = sideWord(cfg, s.targetSide === 'A' ? 'B' : 'A')
  const parts = s.members.map((m) => fmtMoney(m.abs / 100)).join(' + ')
  const total = s.members.reduce((x, m) => x + m.abs, 0)
  const date = s.target.line.date ? ` on ${fmtDate(s.target.line.date)}` : ''
  let text = `${upperFirst(plural(s.members.length, `${memberWord} line`))} add up to one ${targetWord} line: ${parts} = ${fmtMoney(total / 100)} vs ${fmtMoney(s.target.abs / 100)}${date}`
  if (s.diff > 0) text += ` (difference ${fmtMoney(s.diff / 100)}, within tolerance)`
  if (window !== null) text += `; all dates within ±${window} days`
  const party = s.members[0]?.party
  if (party) {
    const col = s.members[0].line.side === 'A' ? cfg.partyColumnA : cfg.partyColumnB
    const name = col ? rawCellText(s.members[0].line.values[col]) : ''
    if (name) text += `; same party (${name})`
  }
  if (s.alternatives > 0) text += `. ${plural(s.alternatives, 'other combination')} also add up, so check carefully`
  return text
}
