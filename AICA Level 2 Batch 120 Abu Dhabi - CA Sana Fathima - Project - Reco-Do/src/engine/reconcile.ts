// Step 3: the deterministic reconciliation (master prompt §4 Step 3). No AI, no randomness.

import type { MatchPair, ParsedTable, ReconConfig, ReconResult, Tier } from '@shared/contracts'
import { buildCandidateSources, prepareKeys, keyPasses, type CandidateSource, type PreparedKey } from './keys'
import { buildLines } from './lines'
import { buildReason, evaluatePair } from './reasons'
import { rebuild } from './stats'
import { validateConfig } from './validate'
import { joinWords, lowerFirst, plural, round2 } from './util'

const TIER_ORDER: Array<Exclude<Tier, 'unmatched'>> = ['matched', 'doubtful', 'likely']
const TIER_CODE = { matched: 0, doubtful: 1, likely: 2 } as const

/**
 * Candidate search limits (master prompt rule 5: never compare every row with every row).
 *
 * An identifying key with little variety (Qty = 1 on every row, a repeated salary, one party everywhere) gives a
 * huge index bucket. Taking the union of every bucket would then be quadratic. Instead, per File A line:
 *  - buckets of up to LARGE_BUCKET lines are searched in full (normal data never gets near this);
 *  - an oversized bucket is never searched in full. Matched pairs pass every key, so they are always found
 *    through the smaller buckets. Doubtful pairs that only an oversized bucket can find (the one selective key
 *    fails) must pass the date key too; they are searched after Matched is assigned, among still-open File B
 *    lines of that bucket within the date window (nearest NEAREST_CAP);
 *  - when every bucket of a line is oversized, the NEAREST_CAP nearest lines (by date, else by amount, else by
 *    row position) of the smallest bucket are compared;
 *  - Likely candidates from oversized buckets are only generated after Matched and Doubtful are assigned, for the
 *    lines still open, and only the LIKELY_CAP nearest still-open lines per bucket are compared;
 *  - a cut-off that falls inside a run of equally near lines takes up to the same number again of tied lines,
 *    so identical candidates are grouped rather than dropped. Beyond that, lines are left Unmatched (shown as
 *    reconciling items), never matched by guess.
 * Pairs whose search was limited say so in their reason. Candidates are evaluated on the fly; only pairs that
 * reach a tier are kept, so memory stays proportional to the number of lines.
 */
export const LARGE_BUCKET = 200
export const NEAREST_CAP = 50
export const LIKELY_CAP = 10

interface Candidate {
  i: number
  j: number
  tier: 0 | 1 | 2
  /** Absolute date difference (0 without a date key; Infinity when a date is missing). */
  dd: number
  /** Absolute amount difference in cents (0 without an amount key; Infinity when an amount is missing). */
  ad: number
  /** Number of keys passed. */
  np: number
}

function cmpNum(a: number, b: number): number {
  return a < b ? -1 : a > b ? 1 : 0
}

/** Rule 1 preference: closest date, then smallest amount difference, then most keys passed. */
function better(p: Candidate, q: Candidate): number {
  return cmpNum(p.dd, q.dd) || cmpNum(p.ad, q.ad) || cmpNum(q.np, p.np)
}

/**
 * Tier for a candidate pair (master prompt §4 Step 3):
 *  1 key: pass = Matched. 2 keys: both = Matched; one identifying key = Likely.
 *  3+ keys: all = Matched; exactly one fails = Doubtful; only one passes and it identifies = Likely.
 * Additionally (conservative reading of "date-only is never a match"): a pair is never a match unless at least
 * one identifying key passes. Candidates come from identifying-key indexes, so this rarely bites.
 */
export function tierFor(pass: boolean[], keys: PreparedKey[]): 0 | 1 | 2 | null {
  const n = keys.length
  let np = 0
  let idPass = false
  for (let k = 0; k < n; k++) {
    if (pass[k]) {
      np++
      if (keys[k].identifying) idPass = true
    }
  }
  if (!idPass) return null
  if (n === 1) return np === 1 ? 0 : null
  if (n === 2) return np === 2 ? 0 : np === 1 ? 2 : null
  if (np === n) return 0
  if (np === n - 1) return 1
  if (np === 1) return 2
  return null
}

class UnionFind {
  private parent: Int32Array
  constructor(n: number) {
    this.parent = new Int32Array(n)
    for (let k = 0; k < n; k++) this.parent[k] = k
  }
  find(x: number): number {
    while (this.parent[x] !== x) {
      this.parent[x] = this.parent[this.parent[x]]
      x = this.parent[x]
    }
    return x
  }
  union(a: number, b: number): void {
    const ra = this.find(a)
    const rb = this.find(b)
    if (ra !== rb) this.parent[rb] = ra
  }
}

function now(): number {
  const p = (globalThis as { performance?: { now(): number } }).performance
  return p ? p.now() : Date.now()
}

/** A bucket's B lines sorted by the proximity value (date, amount or row position). */
interface SortedBucket {
  idx: Int32Array
  val: Float64Array
}

function lowerBound(val: Float64Array, t: number): number {
  let lo = 0
  let hi = val.length
  while (lo < hi) {
    const mid = (lo + hi) >>> 1
    if (val[mid] < t) lo = mid + 1
    else hi = mid
  }
  return lo
}

/**
 * Up to `k` entries of a sorted bucket nearest to `target` (|value − target| ≤ window), nearest first.
 * When the k-th entry is tied with the next ones (same distance), up to `k` more tied entries are taken, so
 * equally good lines are not dropped arbitrarily from a "Multiple identical candidates" group.
 * A missing target (NaN) has no distance: with an unlimited window the first entries are taken, otherwise none.
 */
function nearestIn(sb: SortedBucket, target: number, k: number, window: number, skip: (j: number) => boolean, out: number[]): void {
  const n = sb.idx.length
  const base = out.length
  if (Number.isNaN(target)) {
    if (window !== Infinity) return
    for (let p = 0; p < n && out.length - base < k; p++) if (!skip(sb.idx[p])) out.push(sb.idx[p])
    return
  }
  let hi = lowerBound(sb.val, target)
  let lo = hi - 1
  let lastDist = -1
  while (lo >= 0 || hi < n) {
    const dl = lo >= 0 ? target - sb.val[lo] : Infinity
    const dh = hi < n ? sb.val[hi] - target : Infinity
    const dist = Math.min(dl, dh)
    if (dist > window) break
    const taken = out.length - base
    if (taken >= 2 * k || (taken >= k && dist !== lastDist)) break
    const p = dl <= dh && lo >= 0 ? lo-- : hi++
    if (!skip(sb.idx[p])) {
      out.push(sb.idx[p])
      lastDist = dist
    }
  }
}

interface LimitNote {
  keyName: string
  size: number
}

export function reconcile(tableA: ParsedTable, tableB: ParsedTable, cfg: ReconConfig): ReconResult {
  const t0 = now()
  const errors = validateConfig(cfg, tableA, tableB)
  if (errors.length > 0) throw new Error(errors.join(' '))

  const linesA = buildLines(tableA, 'A', cfg)
  const linesB = buildLines(tableB, 'B', cfg)
  const keys = prepareKeys(cfg, linesA, linesB)
  const sources = buildCandidateSources(keys)
  const dateIdx = keys.findIndex((k) => k.kind === 'date')
  const amountIdx = keys.findIndex((k) => k.kind === 'amount')
  const nA = linesA.length
  const nB = linesB.length
  const nKeys = keys.length

  // Proximity used to pick the nearest lines out of an oversized bucket: date, else amount, else row position.
  const proximityKey = dateIdx >= 0 ? keys[dateIdx] : amountIdx >= 0 ? keys[amountIdx] : null
  const proximityWord = dateIdx >= 0 ? 'date' : amountIdx >= 0 ? 'amount' : 'row order'
  const proxA = (i: number): number => {
    if (!proximityKey) return i
    const v = proximityKey.a[i]
    return typeof v === 'number' ? v : NaN
  }
  const proxB = (j: number): number => {
    if (!proximityKey) return j
    const v = proximityKey.b[j]
    return typeof v === 'number' ? v : Infinity // missing values sort last
  }
  const dateWindow = dateIdx >= 0 ? Math.max(0, keys[dateIdx].key.dateToleranceDays ?? 0) : Infinity

  const sortedCache = new WeakMap<number[], SortedBucket>()
  const sorted = (list: number[]): SortedBucket => {
    let sb = sortedCache.get(list)
    if (!sb) {
      const order = list.slice().sort((x, y) => cmpNum(proxB(x), proxB(y)) || x - y)
      sb = { idx: Int32Array.from(order), val: Float64Array.from(order, proxB) }
      sortedCache.set(list, sb)
    }
    return sb
  }
  const nearestFromLists = (lists: number[][], target: number, k: number, window: number, skip: (j: number) => boolean, view: (l: number[]) => SortedBucket): number[] => {
    if (lists.length === 1) {
      const out: number[] = []
      nearestIn(view(lists[0]), target, k, window, skip, out)
      return out
    }
    const all: number[] = []
    for (const l of lists) nearestIn(view(l), target, k, window, skip, all)
    const dist = (j: number): number => (Number.isNaN(target) ? 0 : Math.abs(proxB(j) - target))
    all.sort((x, y) => cmpNum(dist(x), dist(y)) || x - y)
    return all.length > 2 * k ? all.slice(0, 2 * k) : all
  }

  const pass: boolean[] = new Array(nKeys)
  const evaluate = (i: number, j: number): Candidate | null => {
    let np = 0
    for (let k = 0; k < nKeys; k++) {
      pass[k] = keyPasses(keys[k], i, j)
      if (pass[k]) np++
    }
    const tier = tierFor(pass, keys)
    if (tier === null) return null
    let dd = 0
    if (dateIdx >= 0) {
      const a = keys[dateIdx].a[i]
      const b = keys[dateIdx].b[j]
      dd = typeof a === 'number' && typeof b === 'number' ? Math.abs(a - b) : Infinity
    }
    let ad = 0
    if (amountIdx >= 0) {
      const a = keys[amountIdx].a[i]
      const b = keys[amountIdx].b[j]
      ad = typeof a === 'number' && typeof b === 'number' ? Math.abs(a - b) : Infinity
    }
    return { i, j, tier, dd, ad, np }
  }

  // ── 1. Candidate search through the hash indexes (see the limits above); every used key is tested per candidate.
  const candidates: Candidate[] = []
  const candStart = new Int32Array(nA + 1)
  const hasLarge = new Uint8Array(nA)
  const wantDoubtful = new Uint8Array(nA)
  const limited = new Map<number, LimitNote>()
  const stamp = new Int32Array(nB).fill(-1)
  const found: number[] = []
  const noSkip = (): boolean => false
  const noteLimit = (i: number, src: CandidateSource, size: number): void => {
    const prev = limited.get(i)
    if (!prev || size > prev.size) limited.set(i, { keyName: keys[src.keyIndex].key.name, size })
  }
  for (let i = 0; i < nA; i++) {
    candStart[i] = candidates.length
    found.length = 0
    const add = (j: number): void => {
      if (stamp[j] !== i) {
        stamp[j] = i
        found.push(j)
      }
    }
    let smallCount = 0
    let missingCount = 0
    let smallestLarge: { src: CandidateSource; lists: number[][]; size: number } | null = null
    for (const s of sources) {
      const lists = s.lists(i)
      if (lists === null) {
        missingCount++
        continue
      }
      let size = 0
      for (const l of lists) size += l.length
      if (size <= LARGE_BUCKET) {
        smallCount++
        for (const l of lists) for (const j of l) add(j)
      } else {
        const entry = { src: s, lists, size }
        if (!smallestLarge || size < smallestLarge.size) smallestLarge = entry
      }
    }
    if (smallestLarge) {
      hasLarge[i] = 1
      if (smallCount === 0) {
        // Every bucket is oversized: compare the nearest lines of the smallest one.
        for (const j of nearestFromLists(smallestLarge.lists, proxA(i), NEAREST_CAP, Infinity, noSkip, sorted)) add(j)
        noteLimit(i, smallestLarge.src, smallestLarge.size)
      } else if (nKeys >= 3 && smallCount === 1 && missingCount === 0) {
        // A Doubtful pair whose only failing key is the one selective key passes every other key, the date
        // included, so it lies in the smallest oversized bucket within the date window. It can never be
        // Matched, so it is searched after the Matched assignment, among the lines still open (see below).
        wantDoubtful[i] = 1
      }
    }
    for (const j of found) {
      const c = evaluate(i, j)
      if (c) candidates.push(c)
    }
  }
  candStart[nA] = candidates.length

  // ── 2. One-to-one assignment: Matched first, then Doubtful, then Likely.
  const usedA = new Uint8Array(nA)
  const usedB = new Uint8Array(nB)
  const pairs: Array<{ tierOrder: number; firstA: number; pair: MatchPair }> = []
  let seq = 0
  const nextId = (): string => `pair-${++seq}`
  const uf = new UnionFind(nA + nB)
  const limitFor = (aIdx: number[], tierName: Exclude<Tier, 'unmatched'>, dup: boolean): LimitNote | undefined => {
    if (!dup && tierName !== 'likely') return undefined
    for (const i of aIdx) {
      const n = limited.get(i)
      if (n) return n
    }
    return undefined
  }
  const limitText = (n: LimitNote | undefined): string =>
    n ? ` (Candidate search limited: ${n.size.toLocaleString('en-US')} lines in ${cfg.sideBName || 'File B'} share this ${lowerFirst(n.keyName)}; only the nearest by ${proximityWord} were compared.)` : ''


  /**
   * Deferred search of oversized buckets for the lines still open before a tier is assigned. Only lines of
   * File B that are still open are considered, so the nearest-K choice is not wasted on lines already matched.
   * `tier` is the only tier kept: higher tiers were searched completely earlier.
   */
  const expandLarge = (tier: 1 | 2, want: Uint8Array, smallestOnly: boolean, window: number, cap: number): void => {
    const compactCache = new WeakMap<number[], SortedBucket>()
    const compact = (list: number[]): SortedBucket => {
      let sb = compactCache.get(list)
      if (!sb) {
        const full = sorted(list)
        const keep: number[] = []
        for (let p = 0; p < full.idx.length; p++) if (!usedB[full.idx[p]]) keep.push(p)
        sb = { idx: Int32Array.from(keep, (p) => full.idx[p]), val: Float64Array.from(keep, (p) => full.val[p]) }
        compactCache.set(list, sb)
      }
      return sb
    }
    const known = new Set<number>()
    const skip = (j: number): boolean => known.has(j)
    for (let i = 0; i < nA; i++) {
      if (!want[i] || usedA[i]) continue
      known.clear()
      for (let c = candStart[i]; c < candStart[i + 1]; c++) known.add(candidates[c].j)
      const large: Array<{ src: CandidateSource; lists: number[][]; size: number }> = []
      for (const s of sources) {
        const lists = s.lists(i)
        if (!lists) continue
        let size = 0
        for (const l of lists) size += l.length
        if (size > LARGE_BUCKET) large.push({ src: s, lists, size })
      }
      if (smallestOnly && large.length > 1) {
        large.sort((x, y) => x.size - y.size)
        large.length = 1
      }
      for (const { src, lists, size } of large) {
        const picked = nearestFromLists(lists, proxA(i), cap, window, skip, compact)
        for (const j of picked) {
          known.add(j)
          const c = evaluate(i, j)
          if (c && c.tier === tier) candidates.push(c)
        }
        if (picked.length >= cap) noteLimit(i, src, size)
      }
    }
  }

  for (const tierName of TIER_ORDER) {
    const code = TIER_CODE[tierName]

    if (code === 1) expandLarge(1, wantDoubtful, true, dateWindow, NEAREST_CAP)
    if (code === 2 && nKeys >= 2) expandLarge(2, hasLarge, false, Infinity, LIKELY_CAP)

    const tp = candidates.filter((c) => c.tier === code && !usedA[c.i] && !usedB[c.j])
    if (tp.length === 0) continue
    tp.sort((p, q) => better(p, q) || p.i - q.i || p.j - q.j)

    // Rule 1 + rule 3, level by level from the best preference value down. Every edge at the current best level
    // is a top choice for both of its lines (preference values are symmetric), so:
    //  - an edge whose two lines have no other edge at this level is a clear mutual best → paired;
    //  - edges that share a line at this level are genuinely tied at the top → one Doubtful
    //    "Multiple identical candidates" group per connected component (never guessed).
    // Lines used at a better level drop out first, so a clear exact pair is never swallowed by a weaker tie.
    let start = 0
    while (start < tp.length) {
      let end = start + 1
      while (end < tp.length && better(tp[start], tp[end]) === 0) end++
      const level: Candidate[] = []
      for (let k = start; k < end; k++) if (!usedA[tp[k].i] && !usedB[tp[k].j]) level.push(tp[k])
      start = end
      if (level.length === 0) continue
      for (const c of level) uf.union(c.i, nA + c.j)
      const comps = new Map<number, Candidate[]>()
      for (const c of level) {
        const r = uf.find(c.i)
        const list = comps.get(r)
        if (list) list.push(c)
        else comps.set(r, [c])
      }
      for (const comp of comps.values()) {
        if (comp.length === 1) {
          const c = comp[0]
          usedA[c.i] = 1
          usedB[c.j] = 1
          pairs.push({ tierOrder: code, firstA: c.i, pair: singlePair(nextId(), tierName, cfg, keys, linesA, linesB, c, limitText(limitFor([c.i], tierName, false))) })
          continue
        }
        const aSet = new Set<number>()
        const bSet = new Set<number>()
        for (const c of comp) {
          aSet.add(c.i)
          bSet.add(c.j)
        }
        const g = { a: Array.from(aSet).sort((x, y) => x - y), b: Array.from(bSet).sort((x, y) => x - y) }
        for (const i of g.a) usedA[i] = 1
        for (const j of g.b) usedB[j] = 1
        pairs.push({ tierOrder: 1, firstA: g.a[0], pair: duplicatePair(nextId(), cfg, keys, linesA, linesB, g, comp[0], limitText(limitFor(g.a, tierName, true))) })
      }
    }
  }

  pairs.sort((x, y) => x.tierOrder - y.tierOrder || x.firstA - y.firstA)
  const finalPairs = pairs.map((p) => p.pair)
  const { unmatchedA, unmatchedB, stats } = rebuild(linesA, linesB, finalPairs)
  return {
    config: cfg,
    linesA,
    linesB,
    pairs: finalPairs,
    unmatchedA,
    unmatchedB,
    stats,
    durationMs: Math.round(now() - t0)
  }
}

function singlePair(
  id: string,
  tier: Exclude<Tier, 'unmatched'>,
  cfg: ReconConfig,
  keys: PreparedKey[],
  linesA: ReconResult['linesA'],
  linesB: ReconResult['linesB'],
  c: Candidate,
  note: string
): MatchPair {
  const ev = evaluatePair(cfg, keys, c.i, c.j)
  const a = linesA[c.i]
  const b = linesB[c.j]
  const amountDifference = a.comparableAmount !== null && b.comparableAmount !== null ? round2(a.comparableAmount - b.comparableAmount) : null
  return {
    id,
    tier,
    aIds: [a.id],
    bIds: [b.id],
    keyResults: ev.keyResults,
    amountDifference: keys.some((k) => k.kind === 'amount') ? amountDifference : null,
    dateDifferenceDays: ev.dateDiff,
    reason: buildReason(tier, keys, ev) + note,
    flags: ev.flags,
    origin: 'engine',
    status: tier === 'matched' ? 'accepted' : 'open'
  }
}

function duplicatePair(
  id: string,
  cfg: ReconConfig,
  keys: PreparedKey[],
  linesA: ReconResult['linesA'],
  linesB: ReconResult['linesB'],
  g: { a: number[]; b: number[] },
  rep: Candidate | undefined,
  note: string
): MatchPair {
  const aIds = g.a.map((i) => linesA[i].id)
  const bIds = g.b.map((j) => linesB[j].id)
  const ev = rep ? evaluatePair(cfg, keys, rep.i, rep.j) : null
  const basis = ev ? buildReason(rep && rep.tier === 2 ? 'likely' : rep && rep.tier === 1 ? 'doubtful' : 'matched', keys, ev) : ''
  const hasAmount = keys.some((k) => k.kind === 'amount')
  let amountDifference: number | null = null
  if (hasAmount) {
    let sum = 0
    let ok = true
    for (const i of g.a) {
      const v = linesA[i].comparableAmount
      if (v === null) ok = false
      else sum += v
    }
    for (const j of g.b) {
      const v = linesB[j].comparableAmount
      if (v === null) ok = false
      else sum -= v
    }
    amountDifference = ok ? round2(sum) : null
  }
  const nameA = cfg.sideAName || 'File A'
  const nameB = cfg.sideBName || 'File B'
  const counts = joinWords([`${plural(aIds.length, 'line')} in ${nameA}`, `${plural(bIds.length, 'line')} in ${nameB}`])
  return {
    id,
    tier: 'doubtful',
    aIds,
    bIds,
    keyResults: ev ? ev.keyResults : [],
    amountDifference,
    dateDifferenceDays: ev ? ev.dateDiff : null,
    reason: `Multiple identical candidates: ${counts} are equally good matches${basis ? ` (${lowerFirst(basis)})` : ''}. Review them: accept the group, or unmatch it and match the right lines manually.${note}`,
    flags: ['multiple-candidates'],
    origin: 'engine',
    status: 'open',
    candidateIds: [...aIds, ...bIds]
  }
}
