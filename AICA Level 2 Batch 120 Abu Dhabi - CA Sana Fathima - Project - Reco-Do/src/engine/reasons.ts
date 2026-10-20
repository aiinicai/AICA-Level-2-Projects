// Plain-English reasons, per-key results and difference flags (transposition, bank charge, rounding).

import type { KeyResult, PairFlag, ReconConfig, Tier } from '@shared/contracts'
import type { PreparedKey } from './keys'
import { keyPasses } from './keys'
import { fmtMoney, joinWords, lowerFirst, plural, sideWord, upperFirst } from './util'

/** True when two amounts (in cents) have the same digits with exactly two of them swapped. */
export function isDigitSwap(aCents: number, bCents: number): boolean {
  const a = String(Math.abs(Math.round(aCents)))
  const b = String(Math.abs(Math.round(bCents)))
  if (a.length !== b.length || a === b) return false
  const diffs: number[] = []
  for (let k = 0; k < a.length; k++) {
    if (a[k] !== b[k]) {
      diffs.push(k)
      if (diffs.length > 2) return false
    }
  }
  return diffs.length === 2 && a[diffs[0]] === b[diffs[1]] && a[diffs[1]] === b[diffs[0]]
}

/**
 * Flags for an amount difference (both in cents, same sign convention). At most one flag, in this order:
 *  - transposition: the digits are the same with two of them swapped, and the difference in cents is divisible
 *    by 9 (always true for a swap; kept as the classic check). Tested on the full cents value, so a swap in the
 *    cents digits (100.12 vs 100.21) is a transposition, not rounding. It wins over the generic labels below
 *    because it is the more specific explanation of a keying error;
 *  - rounding: difference of 1.00 or less;
 *  - bank-charge: a small difference (more than 1.00) within 1% of the larger amount.
 */
export function amountFlags(aCents: number, bCents: number): PairFlag[] {
  const diff = Math.abs(Math.round(aCents) - Math.round(bCents))
  if (diff === 0) return []
  if (diff % 9 === 0 && isDigitSwap(aCents, bCents)) return ['transposition']
  if (diff <= 100) return ['rounding']
  if (diff <= 0.01 * Math.max(Math.abs(aCents), Math.abs(bCents))) return ['bank-charge']
  return []
}

function amountDiffText(cfg: ReconConfig, aCents: number, bCents: number, flags: PairFlag[]): string {
  const diff = Math.abs(aCents - bCents) / 100
  let s = `differs by ${fmtMoney(diff)}`
  if (flags.includes('transposition')) {
    s += ` (possible transposition ${fmtMoney(Math.abs(aCents) / 100)} vs ${fmtMoney(Math.abs(bCents) / 100)})`
  } else if (flags.includes('rounding')) {
    s += ' (possible rounding difference)'
  } else if (flags.includes('bank-charge')) {
    s += cfg.moduleId === 'bank' || cfg.moduleId === 'cc' ? ' (within 1%, possible bank charge)' : ' (small difference within 1%)'
  }
  return s
}

function quote(s: string): string {
  const t = s.length > 40 ? `${s.slice(0, 39)}…` : s
  return `'${t}'`
}

export interface PairEvaluation {
  pass: boolean[]
  keyResults: KeyResult[]
  flags: PairFlag[]
  /** Absolute day difference when a date key is used and both dates exist. */
  dateDiff: number | null
  /** comparable A − comparable B in cents when an amount key is used and both amounts exist. */
  amountDiffCents: number | null
}

/** Full evaluation of one candidate pair: pass/fail per key with plain-English details and flags. */
export function evaluatePair(cfg: ReconConfig, keys: PreparedKey[], i: number, j: number): PairEvaluation {
  const pass: boolean[] = []
  const keyResults: KeyResult[] = []
  let flags: PairFlag[] = []
  let dateDiff: number | null = null
  let amountDiffCents: number | null = null
  const wA = sideWord(cfg, 'A')
  const wB = sideWord(cfg, 'B')
  for (const pk of keys) {
    const ok = keyPasses(pk, i, j)
    pass.push(ok)
    const va = pk.a[i]
    const vb = pk.b[j]
    const missA = va === null || va === ''
    const missB = vb === null || vb === ''
    let detail: string
    if (missA && missB) detail = 'missing on both sides'
    else if (missA) detail = `missing on ${wA} side`
    else if (missB) detail = `missing on ${wB} side`
    else if (pk.kind === 'date') {
      const d = Math.abs((va as number) - (vb as number))
      dateDiff = d
      const tol = pk.key.dateToleranceDays ?? 0
      detail = d === 0 ? 'same date' : ok ? `${plural(d, 'day')} apart (within ±${tol})` : `differs by ${plural(d, 'day')}`
    } else if (pk.kind === 'amount') {
      const a = va as number
      const b = vb as number
      amountDiffCents = a - b
      flags = amountFlags(a, b)
      detail = a === b ? 'equal' : ok ? `${amountDiffText(cfg, a, b, flags)}, within tolerance` : amountDiffText(cfg, a, b, flags)
    } else if (pk.kind === 'number') {
      const d = Math.abs((va as number) - (vb as number))
      detail = d === 0 ? 'equal' : ok ? `differs by ${+d.toFixed(6)}, within tolerance` : `differs by ${+d.toFixed(6)}`
    } else {
      detail = ok ? (pk.rawA[i] === pk.rawB[j] ? 'same' : 'agrees after normalising') : `differs (${quote(pk.rawA[i])} vs ${quote(pk.rawB[j])})`
      if (ok && pk.rule === 'contains' && va !== vb) detail = 'one value contains the other'
    }
    keyResults.push({ keyId: pk.key.id, pass: ok, detail })
  }
  return { pass, keyResults, flags, dateDiff, amountDiffCents }
}

/**
 * Builds the reason sentence. Passing keys are listed identifying keys first, e.g.
 * "Reference and amount agree; date differs by 5 days" or "Only amount agrees; date differs by 12 days".
 */
export function buildReason(tier: Tier, keys: PreparedKey[], ev: PairEvaluation): string {
  const order = keys.map((pk, idx) => ({ pk, idx })).sort((x, y) => Number(y.pk.identifying) - Number(x.pk.identifying) || x.idx - y.idx)
  const passed = order.filter((o) => ev.pass[o.idx]).map((o) => o.pk.key.name)
  const failed = order.filter((o) => !ev.pass[o.idx])
  const failText = failed.map((o) => `${lowerFirst(o.pk.key.name)} ${ev.keyResults[o.idx].detail ?? 'differs'}`)

  // Notes on passing keys that were not identical (date shift within tolerance, amount within tolerance).
  const notes: string[] = []
  for (const o of order) {
    if (!ev.pass[o.idx]) continue
    const d = ev.keyResults[o.idx].detail
    if (o.pk.kind === 'date' && d && d !== 'same date') notes.push(`${lowerFirst(o.pk.key.name)} ${d}`)
    if ((o.pk.kind === 'amount' || o.pk.kind === 'number') && d && d !== 'equal') notes.push(`${lowerFirst(o.pk.key.name)} ${d}`)
  }

  const names = passed.map((n, k) => (k === 0 ? upperFirst(n) : lowerFirst(n)))
  const verb = passed.length === 1 ? 'agrees' : 'agree'
  if (tier === 'likely') {
    return [`Only ${lowerFirst(passed[0] ?? 'one key')} agrees`, ...failText].join('; ')
  }
  return [`${joinWords(names)} ${verb}`, ...notes, ...failText].join('; ')
}
