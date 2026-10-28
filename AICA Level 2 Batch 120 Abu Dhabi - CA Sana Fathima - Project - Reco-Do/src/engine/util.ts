// Small shared helpers for the engine: money in cents, calendar days, ids, plain-English joining.

import type { CellValue, MatchKey, ReconConfig, Side } from '@shared/contracts'
import { formatAmount, formatDate } from '@shared/format'

const DAY_MS = 86_400_000

/** Money is compared in integer cents so that 0.1 + 0.2 never breaks a match. */
export function toCents(n: number): number {
  return Math.round(n * 100)
}

/** Rounds to 2 decimals and removes negative zero. */
export function round2(n: number): number {
  const r = Math.round(n * 100) / 100
  return r === 0 ? 0 : r
}

/** Negates without producing -0. */
export function negate(n: number): number {
  return n === 0 ? 0 : -n
}

/** Local calendar day number (days since 1970-01-01 in local time). */
export function dayNumber(d: Date): number {
  return Math.floor((d.getTime() - d.getTimezoneOffset() * 60_000) / DAY_MS)
}

/** ISO calendar date "2026-09-30" in local time. */
export function isoDay(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

export function fmtMoney(n: number): string {
  return formatAmount(n)
}

export function fmtDate(d: Date): string {
  return formatDate(d)
}

let fallbackCounter = 0

/** Random unique id (crypto.randomUUID where available; Node 22 and Electron both have it). */
export function newId(prefix: string): string {
  const c = (globalThis as { crypto?: { randomUUID?: () => string } }).crypto
  if (c && typeof c.randomUUID === 'function') return `${prefix}-${c.randomUUID()}`
  fallbackCounter++
  return `${prefix}-${Date.now().toString(36)}-${fallbackCounter.toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

/** Display text of a cell, used for references in reasons and statements. */
export function cellText(v: CellValue | undefined): string {
  if (v === null || v === undefined) return ''
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? '' : formatDate(v)
  if (typeof v === 'number') return Number.isFinite(v) ? String(v) : ''
  return String(v).trim()
}

/** "a", "a and b", "a, b and c". */
export function joinWords(words: string[]): string {
  if (words.length <= 1) return words.join('')
  return `${words.slice(0, -1).join(', ')} and ${words[words.length - 1]}`
}

/** Lower-cases the first letter unless the word looks like an acronym ("IBAN", "IC Ref"). */
export function lowerFirst(s: string): string {
  if (s.length === 0) return s
  if (s.length > 1 && s[1] === s[1].toUpperCase() && s[1] !== s[1].toLowerCase()) return s
  return s[0].toLowerCase() + s.slice(1)
}

export function upperFirst(s: string): string {
  return s.length === 0 ? s : s[0].toUpperCase() + s.slice(1)
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`
}

/** Text, ID, amount and number keys can identify a record; dates never can; text only with "ID key" ticked. */
export function isIdentifying(k: MatchKey): boolean {
  if (k.type === 'date') return false
  if (k.type === 'text') return k.identifying
  return true
}

export function usedKeys(cfg: ReconConfig): MatchKey[] {
  return cfg.keys.filter((k) => k.use)
}

export function amountKeyOf(cfg: ReconConfig): MatchKey | undefined {
  return cfg.keys.find((k) => k.use && k.type === 'amount')
}

export function dateKeyOf(cfg: ReconConfig): MatchKey | undefined {
  return cfg.keys.find((k) => k.use && k.type === 'date')
}

/** Short side words for sentences: "bank"/"GL", "our"/"their", or the General side names. */
export function sideWord(cfg: ReconConfig, side: Side): string {
  switch (cfg.moduleId) {
    case 'bank':
      return side === 'A' ? 'bank' : 'GL'
    case 'cc':
      return side === 'A' ? 'card statement' : 'GL'
    case 'ar':
    case 'ap':
      return side === 'A' ? 'our' : 'their'
    default:
      return side === 'A' ? cfg.sideAName || 'File A' : cfg.sideBName || 'File B'
  }
}

/** Absolute amount tolerance in cents for a pair of amounts (exact → 0; percent of the smaller amount). */
export function toleranceCents(k: MatchKey | undefined, aCents: number, bCents: number): number {
  const t = k?.tolerance
  if (!t || t.mode === 'exact') return 0
  if (t.mode === 'fixed') return Math.max(0, Math.round(t.value * 100))
  // Conservative choice (spec is silent): the percentage is applied to the smaller of the two amounts.
  return (Math.max(0, t.value) / 100) * Math.min(Math.abs(aCents), Math.abs(bCents))
}

export function describeTolerance(k: MatchKey | undefined): string {
  const t = k?.tolerance
  if (!t || t.mode === 'exact') return 'exact'
  if (t.mode === 'fixed') return `±${fmtMoney(t.value)}`
  return `±${t.value}%`
}
