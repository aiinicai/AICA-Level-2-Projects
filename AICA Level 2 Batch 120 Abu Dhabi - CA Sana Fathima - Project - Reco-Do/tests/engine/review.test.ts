import { describe, expect, it } from 'vitest'
import type { ReconSession, Suggestion } from '@shared/contracts'
import {
  acceptPair,
  addNote,
  addSuggestions,
  ageingBucket,
  approveSuggestion,
  canFinalise,
  createSession,
  finalise,
  FINALISED_MESSAGE,
  manualMatch,
  reconcile,
  rejectPair,
  rejectSuggestion,
  summariseForHistory,
  unmatchPair
} from '@engine/index'
import { amountKey, config, d, dateKey, meta, refKey, table } from './helpers'

const USER = 'Sana Fathima'
const cols = ['Date', 'Ref', 'Amount']
const A = table(cols, [
  [d(2026, 9, 1), 'R1', 100], // matched
  [d(2026, 9, 1), 'R2', 200], // doubtful (date)
  [d(2026, 9, 2), 'G', 300], // unmatched, group target
  [d(2026, 7, 1), 'OLD', 75] // unmatched, old
])
const B = table(cols, [
  [d(2026, 9, 1), 'R1', 100],
  [d(2026, 9, 20), 'R2', 200],
  [d(2026, 9, 2), 'P1', 101],
  [d(2026, 9, 2), 'P2', 199],
  [d(2026, 9, 3), 'Z', 74]
])
const cfg = config([refKey(), dateKey(3), amountKey()])
const base = (): ReconSession => createSession(reconcile(A, B, cfg), meta())
const pairOf = (s: ReconSession, tier: string) => s.result.pairs.find((p) => p.tier === tier)!

const groupSuggestion = (status: Suggestion['status'] = 'open', source: Suggestion['source'] = 'ai'): Suggestion => ({
  id: 'sug-1',
  aIds: ['A:r4'],
  bIds: ['B:r4', 'B:r5'],
  confidence: 88,
  reason: '100 + 200 = 300',
  source,
  status
})

describe('review functions are pure and audited', () => {
  it('createSession starts empty and unlocked; engine matched pairs start accepted', () => {
    const s = base()
    expect(s.audit).toEqual([])
    expect(s.finalised).toBeNull()
    expect(pairOf(s, 'matched').status).toBe('accepted')
  })

  it('acceptPair moves a Doubtful pair to Matched with status accepted, without mutating the input', () => {
    const s = base()
    const before = JSON.stringify(s)
    const p = pairOf(s, 'doubtful')
    const s2 = acceptPair(s, p.id, USER, 'Bank posted late')
    expect(JSON.stringify(s)).toBe(before)
    const p2 = s2.result.pairs.find((x) => x.id === p.id)!
    expect(p2).toMatchObject({ tier: 'matched', status: 'accepted', note: 'Bank posted late' })
    expect(p2.label).toBe(`Matched — accepted from Doubtful (approved by ${USER})`)
    expect(s2.result.stats.matched).toBe(2)
    expect(s2.result.stats.doubtful).toBe(0)
    const e = s2.audit[0]
    expect(e).toMatchObject({ user: USER, action: 'accept', pairId: p.id, note: 'Bank posted late' })
    expect(typeof e.id).toBe('string')
    expect(new Date(e.at).toISOString()).toBe(e.at)
    expect(e.before).toContain('Doubtful')
    expect(e.after).toContain('Matched')
  })

  it('rejectPair and unmatchPair send the lines back to Unmatched', () => {
    const s = base()
    const s2 = rejectPair(s, pairOf(s, 'doubtful').id, USER)
    expect(s2.result.unmatchedA).toContain('A:r3')
    expect(s2.result.unmatchedB).toContain('B:r3')
    expect(s2.audit.at(-1)?.action).toBe('reject')
    const s3 = unmatchPair(s2, pairOf(s2, 'matched').id, USER, 'wrong pairing')
    expect(s3.result.pairs).toHaveLength(0)
    expect(s3.result.stats.unmatchedA).toBe(4)
    expect(s3.audit.at(-1)).toMatchObject({ action: 'unmatch', note: 'wrong pairing' })
  })

  it('addNote records before and after', () => {
    const s = base()
    const id = pairOf(s, 'matched').id
    const s2 = addNote(addNote(s, id, USER, 'first'), id, USER, 'second')
    expect(s2.result.pairs.find((p) => p.id === id)?.note).toBe('second')
    expect(s2.audit.at(-1)).toMatchObject({ action: 'note', before: 'first', after: 'second' })
    expect(() => addNote(s, id, USER, '  ')).toThrow('Write a note')
  })

  it('manualMatch allows 1:many when totals agree', () => {
    const s = manualMatch(base(), ['A:r4'], ['B:r4', 'B:r5'], USER)
    const p = s.result.pairs.at(-1)!
    expect(p).toMatchObject({ tier: 'matched', status: 'accepted', origin: 'manual', aIds: ['A:r4'], bIds: ['B:r4', 'B:r5'], amountDifference: 0 })
    expect(s.result.unmatchedA).toEqual(['A:r5'])
    expect(s.audit.at(-1)?.action).toBe('manual-match')
  })

  it('manualMatch needs a reason when totals differ, and refuses lines already paired', () => {
    const s = base()
    expect(() => manualMatch(s, ['A:r5'], ['B:r6'], USER)).toThrow('The totals differ by 1.00 (File A 75.00 vs File B 74.00). Enter a reason to match them anyway.')
    const s2 = manualMatch(s, ['A:r5'], ['B:r6'], USER, 'Rounding agreed with supplier')
    expect(s2.result.pairs.at(-1)).toMatchObject({ amountDifference: 1, note: 'Rounding agreed with supplier' })
    expect(() => manualMatch(s, ['A:r2'], ['B:r6'], USER, 'x')).toThrow('already in a pair')
    expect(() => manualMatch(s, [], ['B:r6'], USER)).toThrow('Tick at least one line')
  })

  it('approveSuggestion creates an accepted Matched pair with exactly the suggestion ids and the AI label', () => {
    const s = addSuggestions(base(), [groupSuggestion()])
    const s2 = approveSuggestion(s, 'sug-1', USER)
    const p = s2.result.pairs.at(-1)!
    expect(p).toMatchObject({ tier: 'matched', status: 'accepted', origin: 'ai', aIds: ['A:r4'], bIds: ['B:r4', 'B:r5'], confidence: 88 })
    expect(p.label).toBe(`Matched — AI assisted (approved by ${USER})`)
    expect(s2.result.unmatchedA).not.toContain('A:r4')
    expect(s2.result.unmatchedB).not.toContain('B:r4')
    expect(s2.suggestions[0].status).toBe('accepted')
    expect(s2.audit.at(-1)).toMatchObject({ action: 'approve-suggestion', suggestionId: 'sug-1' })
    expect(() => approveSuggestion(s2, 'sug-1', USER)).toThrow('already been approved')
  })

  it('approveSuggestion keeps the origin of code suggestions and dissolves open Doubtful pairs it absorbs', () => {
    const s = base()
    const doubt = pairOf(s, 'doubtful')
    const sug: Suggestion = { id: 'sug-2', aIds: ['A:r3'], bIds: ['B:r3'], confidence: 85, reason: 'token', source: 'code-partial-ref', status: 'open' }
    const s2 = approveSuggestion(addSuggestions(s, [sug]), 'sug-2', USER)
    expect(s2.result.pairs.some((p) => p.id === doubt.id)).toBe(false)
    expect(s2.result.pairs.at(-1)).toMatchObject({ origin: 'code-partial-ref', tier: 'matched' })
  })

  it('rejectSuggestion leaves lines unmatched', () => {
    const s2 = rejectSuggestion(addSuggestions(base(), [groupSuggestion()]), 'sug-1', USER)
    expect(s2.suggestions[0].status).toBe('rejected')
    expect(s2.result.unmatchedA).toContain('A:r4')
    expect(s2.audit.at(-1)?.action).toBe('reject-suggestion')
  })

  it('canFinalise requires no open Doubtful pairs or suggestions; finalise locks everything', () => {
    let s = addSuggestions(base(), [groupSuggestion()])
    const check = canFinalise(s)
    expect(check.ok).toBe(false)
    expect(check.reasons).toHaveLength(2)
    expect(() => finalise(s, USER)).toThrow('cannot be finalised yet')
    s = acceptPair(s, pairOf(s, 'doubtful').id, USER)
    s = rejectSuggestion(s, 'sug-1', USER)
    expect(canFinalise(s)).toEqual({ ok: true, reasons: [] })
    const f = finalise(s, USER)
    expect(f.finalised?.by).toBe(USER)
    expect(f.audit.at(-1)?.action).toBe('finalise')
    const id = f.result.pairs[0].id
    expect(() => acceptPair(f, id, USER)).toThrow(FINALISED_MESSAGE)
    expect(() => rejectPair(f, id, USER)).toThrow(FINALISED_MESSAGE)
    expect(() => unmatchPair(f, id, USER)).toThrow(FINALISED_MESSAGE)
    expect(() => addNote(f, id, USER, 'x')).toThrow(FINALISED_MESSAGE)
    expect(() => manualMatch(f, ['A:r4'], ['B:r4'], USER, 'x')).toThrow(FINALISED_MESSAGE)
    expect(() => approveSuggestion(f, 'sug-1', USER)).toThrow(FINALISED_MESSAGE)
    expect(() => finalise(f, USER)).toThrow(FINALISED_MESSAGE)
  })

  it('a duplicate group that does not balance cannot be accepted as a whole', () => {
    const rows = table(cols, [[d(2026, 9, 15), 'INV-9', 50]])
    const two = table(cols, [[d(2026, 9, 15), 'INV-9', 50], [d(2026, 9, 15), 'INV-9', 50]])
    const s = createSession(reconcile(rows, two, cfg), meta())
    const dup = s.result.pairs[0]
    expect(dup.flags).toEqual(['multiple-candidates'])
    expect(() => acceptPair(s, dup.id, USER)).toThrow('do not balance')
  })
})

describe('history and ageing', () => {
  it('summariseForHistory counts lines on both sides', () => {
    const s = base()
    const h = summariseForHistory(s)
    expect(h).toMatchObject({ id: s.id, moduleId: 'general', accountLabel: 'Test account', totalLines: 9, autoMatchedLines: 2 })
    // open: doubtful pair (2 lines) + unmatched A 2 + unmatched B 3
    expect(h.openItemCount).toBe(7)
    // |300| + |75| + |101| + |199| + |74| + doubtful difference 0
    expect(h.openItemAmount).toBe(749)
    expect(h.oldestOpenItemDate).toBe('2026-07-01')
  })

  it('ageingBucket', () => {
    const asOf = d(2026, 9, 30)
    expect(ageingBucket(d(2026, 9, 30), asOf)).toBe('0-30')
    expect(ageingBucket(d(2026, 8, 31), asOf)).toBe('0-30')
    expect(ageingBucket(d(2026, 8, 30), asOf)).toBe('31-60')
    expect(ageingBucket(d(2026, 7, 2), asOf)).toBe('61-90')
    expect(ageingBucket(d(2026, 6, 1), asOf)).toBe('90+')
    expect(ageingBucket(d(2026, 10, 5), asOf)).toBe('0-30')
  })
})
