// Review & sign-off (master prompt §4 Step 5). Every function is pure: it returns a new session, never mutates
// its input, appends an audit entry, and refuses any change once the session is finalised.

import type { AuditAction, AuditEntry, EngineLine, KeyResult, MatchPair, PairOrigin, ReconMeta, ReconResult, ReconSession, Suggestion } from '@shared/contracts'
import { rebuild } from './stats'
import { amountKeyOf, describeTolerance, fmtMoney, newId, round2, toCents, toleranceCents } from './util'

export const FINALISED_MESSAGE = 'This reconciliation has been finalised and is locked. No further changes can be made.'

const TIER_WORD: Record<MatchPair['tier'], string> = { matched: 'Matched', doubtful: 'Doubtful', likely: 'Likely', unmatched: 'Unmatched' }

function nowIso(): string {
  return new Date().toISOString()
}

function assertOpen(s: ReconSession): void {
  if (s.finalised) throw new Error(FINALISED_MESSAGE)
}

function requireUser(user: string): string {
  const u = user.trim()
  if (!u) throw new Error('Enter your name (preparer) before making review decisions.')
  return u
}

function findPair(s: ReconSession, pairId: string): MatchPair {
  const p = s.result.pairs.find((x) => x.id === pairId)
  if (!p) throw new Error('That pair no longer exists. Refresh the list and try again.')
  return p
}

function describePair(p: MatchPair): string {
  const state = p.status === 'accepted' ? 'accepted' : p.status === 'rejected' ? 'rejected' : 'open'
  return `${TIER_WORD[p.tier]} (${state}): ${p.aIds.join(', ')} ↔ ${p.bIds.join(', ')}${p.note ? ` — note: ${p.note}` : ''}`
}

function audit(user: string, action: AuditAction, extra: Partial<AuditEntry>): AuditEntry {
  return { id: newId('audit'), at: nowIso(), user, action, ...extra }
}

/** Applies a new pair list, recomputing unmatched lists and stats. */
function withPairs(s: ReconSession, pairs: MatchPair[], entry: AuditEntry, suggestions = s.suggestions): ReconSession {
  const r = rebuild(s.result.linesA, s.result.linesB, pairs)
  const result: ReconResult = { ...s.result, pairs, unmatchedA: r.unmatchedA, unmatchedB: r.unmatchedB, stats: r.stats }
  return { ...s, result, suggestions, audit: [...s.audit, entry], updatedAt: entry.at }
}

function lineMap(r: ReconResult): Map<string, EngineLine> {
  const m = new Map<string, EngineLine>()
  for (const l of r.linesA) m.set(l.id, l)
  for (const l of r.linesB) m.set(l.id, l)
  return m
}

/** Totals of comparable amounts; null when there is no amount key. */
function totals(r: ReconResult, aIds: string[], bIds: string[]): { a: number; b: number } | null {
  if (!amountKeyOf(r.config)) return null
  const m = lineMap(r)
  let a = 0
  let b = 0
  for (const id of aIds) a += m.get(id)?.comparableAmount ?? 0
  for (const id of bIds) b += m.get(id)?.comparableAmount ?? 0
  return { a: round2(a), b: round2(b) }
}

function totalsAgree(r: ReconResult, t: { a: number; b: number }): boolean {
  const ca = toCents(t.a)
  const cb = toCents(t.b)
  return Math.abs(ca - cb) <= toleranceCents(amountKeyOf(r.config), ca, cb) + 1e-9
}

export function createSession(result: ReconResult, meta: ReconMeta): ReconSession {
  const at = nowIso()
  return { id: newId('recon'), createdAt: at, updatedAt: at, meta, result, suggestions: [], audit: [], finalised: null }
}

/**
 * Accept moves a pair to Matched (tier "matched", status "accepted"); the label records where it came from.
 * A "multiple identical candidates" group can only be accepted as a whole when its totals agree; otherwise
 * the user must pick the right lines with manual match.
 */
export function acceptPair(s: ReconSession, pairId: string, user: string, note?: string): ReconSession {
  assertOpen(s)
  const u = requireUser(user)
  const p = findPair(s, pairId)
  if (p.status === 'accepted' && p.tier === 'matched') return s
  if (p.flags.includes('multiple-candidates')) {
    const t = totals(s.result, p.aIds, p.bIds)
    const countsDiffer = p.aIds.length !== p.bIds.length
    if ((t && !totalsAgree(s.result, t)) || (!t && countsDiffer)) {
      throw new Error('These lines are duplicates that do not balance as a group. Unmatch the group, then match the correct lines manually.')
    }
  }
  const before = describePair(p)
  const fromTier = TIER_WORD[p.tier]
  const updated: MatchPair = {
    ...p,
    tier: 'matched',
    status: 'accepted',
    label: p.label ?? (p.tier === 'matched' ? undefined : `Matched — accepted from ${fromTier} (approved by ${u})`),
    note: note?.trim() ? note.trim() : p.note
  }
  const pairs = s.result.pairs.map((x) => (x.id === pairId ? updated : x))
  return withPairs(s, pairs, audit(u, 'accept', { pairId, before, after: describePair(updated), note: note?.trim() || undefined }))
}

/** Reject splits the pair: its lines go back to the unmatched lists. The audit entry keeps what it was. */
export function rejectPair(s: ReconSession, pairId: string, user: string, note?: string): ReconSession {
  assertOpen(s)
  const u = requireUser(user)
  const p = findPair(s, pairId)
  const pairs = s.result.pairs.filter((x) => x.id !== pairId)
  return withPairs(s, pairs, audit(u, 'reject', { pairId, before: describePair(p), after: `Unmatched: ${[...p.aIds, ...p.bIds].join(', ')}`, note: note?.trim() || undefined }))
}

/** Unmatch any pair (including a matched one) and return its lines to the unmatched lists. */
export function unmatchPair(s: ReconSession, pairId: string, user: string, note?: string): ReconSession {
  assertOpen(s)
  const u = requireUser(user)
  const p = findPair(s, pairId)
  const pairs = s.result.pairs.filter((x) => x.id !== pairId)
  return withPairs(s, pairs, audit(u, 'unmatch', { pairId, before: describePair(p), after: `Unmatched: ${[...p.aIds, ...p.bIds].join(', ')}`, note: note?.trim() || undefined }))
}

export function addNote(s: ReconSession, pairId: string, user: string, note: string): ReconSession {
  assertOpen(s)
  const u = requireUser(user)
  const text = note.trim()
  if (!text) throw new Error('Write a note before saving it.')
  const p = findPair(s, pairId)
  const updated: MatchPair = { ...p, note: text }
  const pairs = s.result.pairs.map((x) => (x.id === pairId ? updated : x))
  return withPairs(s, pairs, audit(u, 'note', { pairId, before: p.note ?? '(no note)', after: text, note: text }))
}

/**
 * Manual match: any number of lines on each side (1:1, 1:many, many:many). All lines must be unmatched.
 * With an amount key the totals must agree within the amount tolerance, or a reason must be given.
 */
export function manualMatch(s: ReconSession, aIds: string[], bIds: string[], user: string, reason?: string): ReconSession {
  assertOpen(s)
  const u = requireUser(user)
  const a = Array.from(new Set(aIds))
  const b = Array.from(new Set(bIds))
  const r = s.result
  const nameA = r.config.sideAName || 'File A'
  const nameB = r.config.sideBName || 'File B'
  if (a.length === 0 || b.length === 0) throw new Error(`Tick at least one line in ${nameA} and one line in ${nameB}.`)
  const openA = new Set(r.unmatchedA)
  const openB = new Set(r.unmatchedB)
  const known = lineMap(r)
  for (const id of a) {
    if (!known.has(id) || known.get(id)?.side !== 'A') throw new Error(`Line ${id} is not a ${nameA} line.`)
    if (!openA.has(id)) throw new Error(`Line ${id} is already in a pair. Unmatch that pair first.`)
  }
  for (const id of b) {
    if (!known.has(id) || known.get(id)?.side !== 'B') throw new Error(`Line ${id} is not a ${nameB} line.`)
    if (!openB.has(id)) throw new Error(`Line ${id} is already in a pair. Unmatch that pair first.`)
  }
  const why = reason?.trim() ?? ''
  const t = totals(r, a, b)
  let amountDifference: number | null = null
  const keyResults: KeyResult[] = []
  if (t) {
    amountDifference = round2(t.a - t.b)
    const agree = totalsAgree(r, t)
    const ak = amountKeyOf(r.config)
    keyResults.push({ keyId: ak?.id ?? 'amount', pass: agree, detail: agree ? (amountDifference === 0 ? 'totals equal' : `totals differ by ${fmtMoney(Math.abs(amountDifference))}, within tolerance (${describeTolerance(ak)})`) : `totals differ by ${fmtMoney(Math.abs(amountDifference))}` })
    if (!agree && !why) {
      throw new Error(`The totals differ by ${fmtMoney(Math.abs(amountDifference))} (${nameA} ${fmtMoney(Math.abs(t.a))} vs ${nameB} ${fmtMoney(Math.abs(t.b))}). Enter a reason to match them anyway.`)
    }
  }
  const reasonText = why
    ? `Matched manually by ${u}: ${why}`
    : `Matched manually by ${u}${t ? '; totals agree' : ''}`
  const pair: MatchPair = {
    id: newId('pair-manual'),
    tier: 'matched',
    aIds: a,
    bIds: b,
    keyResults,
    amountDifference,
    dateDifferenceDays: null,
    reason: reasonText,
    flags: [],
    origin: 'manual',
    status: 'accepted',
    label: `Matched — manual (by ${u})`,
    note: why || undefined
  }
  return withPairs(s, [...r.pairs, pair], audit(u, 'manual-match', { pairId: pair.id, before: `Unmatched: ${[...a, ...b].join(', ')}`, after: describePair(pair), note: why || undefined }))
}

/** Adds Smart Recon suggestions (code or AI) to the session; duplicates of existing suggestions are skipped. */
export function addSuggestions(s: ReconSession, suggestions: Suggestion[]): ReconSession {
  assertOpen(s)
  const key = (x: Suggestion): string => `${[...x.aIds].sort().join(',')}|${[...x.bIds].sort().join(',')}`
  const seen = new Set(s.suggestions.map(key))
  const fresh: Suggestion[] = []
  for (const x of suggestions) {
    const k = key(x)
    if (seen.has(k)) continue
    seen.add(k)
    fresh.push(x)
  }
  if (fresh.length === 0) return s
  return { ...s, suggestions: [...s.suggestions, ...fresh], updatedAt: nowIso() }
}

const ORIGIN_OF: Record<Suggestion['source'], PairOrigin> = { 'code-group': 'code-group', 'code-partial-ref': 'code-partial-ref', ai: 'ai' }

function suggestionLabel(source: Suggestion['source'], user: string): string {
  if (source === 'ai') return `Matched — AI assisted (approved by ${user})`
  if (source === 'code-group') return `Matched — Smart Recon sum match (approved by ${user})`
  return `Matched — Smart Recon partial reference (approved by ${user})`
}

/**
 * Approve turns a suggestion into an accepted Matched pair. Its lines must be unmatched, or sit in an open
 * Doubtful/Likely pair (Smart Recon may run on Doubtful lines); such pairs are dissolved and their other lines
 * return to the unmatched lists.
 */
export function approveSuggestion(s: ReconSession, suggestionId: string, user: string): ReconSession {
  assertOpen(s)
  const u = requireUser(user)
  const sug = s.suggestions.find((x) => x.id === suggestionId)
  if (!sug) throw new Error('That suggestion no longer exists.')
  if (sug.status !== 'open') throw new Error(`That suggestion has already been ${sug.status === 'accepted' ? 'approved' : 'rejected'}.`)
  const r = s.result
  const free = new Set([...r.unmatchedA, ...r.unmatchedB])
  const dissolve = new Set<string>()
  for (const id of [...sug.aIds, ...sug.bIds]) {
    if (free.has(id)) continue
    const holder = r.pairs.find((p) => p.aIds.includes(id) || p.bIds.includes(id))
    if (!holder) throw new Error(`Line ${id} is not part of this reconciliation.`)
    if (holder.status !== 'open' || holder.tier === 'matched') throw new Error(`Line ${id} has already been matched. Reject this suggestion or unmatch that pair first.`)
    dissolve.add(holder.id)
  }
  if (sug.aIds.length === 0 || sug.bIds.length === 0) throw new Error('A suggestion needs at least one line on each side.')
  const t = totals(r, sug.aIds, sug.bIds)
  const amountDifference = t ? round2(t.a - t.b) : null
  const ak = amountKeyOf(r.config)
  const keyResults: KeyResult[] = t && ak ? [{ keyId: ak.id, pass: totalsAgree(r, t), detail: amountDifference === 0 ? 'totals equal' : `totals differ by ${fmtMoney(Math.abs(amountDifference ?? 0))}` }] : []
  const pair: MatchPair = {
    id: newId('pair-smart'),
    tier: 'matched',
    aIds: [...sug.aIds],
    bIds: [...sug.bIds],
    keyResults,
    amountDifference,
    dateDifferenceDays: null,
    reason: sug.reason,
    flags: [],
    origin: ORIGIN_OF[sug.source],
    status: 'accepted',
    confidence: sug.confidence,
    label: suggestionLabel(sug.source, u)
  }
  const pairs = [...r.pairs.filter((p) => !dissolve.has(p.id)), pair]
  const suggestions = s.suggestions.map((x) => (x.id === suggestionId ? { ...x, status: 'accepted' as const } : x))
  const dissolvedText = dissolve.size > 0 ? ` (replaces ${Array.from(dissolve).join(', ')})` : ''
  return withPairs(s, pairs, audit(u, 'approve-suggestion', { suggestionId, pairId: pair.id, before: `Suggested (${sug.source}, ${sug.confidence}%): ${sug.aIds.join(', ')} ↔ ${sug.bIds.join(', ')}${dissolvedText}`, after: describePair(pair) }), suggestions)
}

export function rejectSuggestion(s: ReconSession, suggestionId: string, user: string): ReconSession {
  assertOpen(s)
  const u = requireUser(user)
  const sug = s.suggestions.find((x) => x.id === suggestionId)
  if (!sug) throw new Error('That suggestion no longer exists.')
  if (sug.status !== 'open') throw new Error(`That suggestion has already been ${sug.status === 'accepted' ? 'approved' : 'rejected'}.`)
  const suggestions = s.suggestions.map((x) => (x.id === suggestionId ? { ...x, status: 'rejected' as const } : x))
  const entry = audit(u, 'reject-suggestion', { suggestionId, before: `Suggested (${sug.source}, ${sug.confidence}%): ${sug.aIds.join(', ')} ↔ ${sug.bIds.join(', ')}`, after: 'Rejected; lines stay unmatched' })
  return { ...s, suggestions, audit: [...s.audit, entry], updatedAt: entry.at }
}

/** Sign-off needs the Doubtful tab and the AI Suggested tab to be empty (everything accepted or rejected). */
export function canFinalise(s: ReconSession): { ok: boolean; reasons: string[] } {
  const reasons: string[] = []
  if (s.finalised) reasons.push(`Already finalised by ${s.finalised.by}.`)
  const doubtful = s.result.pairs.filter((p) => p.tier === 'doubtful' && p.status === 'open').length
  if (doubtful > 0) reasons.push(`${doubtful} Doubtful ${doubtful === 1 ? 'pair needs' : 'pairs need'} a decision (accept or reject).`)
  const pending = s.suggestions.filter((x) => x.status === 'open').length
  if (pending > 0) reasons.push(`${pending} Smart Recon ${pending === 1 ? 'suggestion needs' : 'suggestions need'} a decision (approve or reject).`)
  return { ok: reasons.length === 0, reasons }
}

export function finalise(s: ReconSession, user: string): ReconSession {
  assertOpen(s)
  const u = requireUser(user)
  const check = canFinalise(s)
  if (!check.ok) throw new Error(`The reconciliation cannot be finalised yet. ${check.reasons.join(' ')}`)
  const at = nowIso()
  const entry: AuditEntry = { id: newId('audit'), at, user: u, action: 'finalise', before: 'Open for review', after: `Finalised and signed off by ${u}` }
  return { ...s, finalised: { by: u, at }, audit: [...s.audit, entry], updatedAt: at }
}
