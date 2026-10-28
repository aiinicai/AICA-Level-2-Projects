import { describe, expect, it, vi } from 'vitest'
import type { AiRequest, AiResult, CellValue, ReconResult, Suggestion } from '@shared/contracts'
import { findGroupMatches, reconcile, suggestKeys } from '@engine/index'
import { eligiblePools } from '@engine/smart/common'
import {
  AI_MAX_TOKENS,
  AiResponseError,
  buildAiPayload,
  canMaskParties,
  estimateCost,
  extractJsonArray,
  mergeSuggestions,
  parseAiResponse,
  parseAiResponseDetailed,
  isKnownModel,
  priceFor,
  describePricing,
  modelFor,
  SMART_RECON_EFFORT,
  toAiRequest
} from '@engine/smart/ai'
import { describeDiscarded, runSmartReconBatches } from '../../src/renderer/src/features/smart-recon/runSmartRecon'
import { amountKey, config, d, dateKey, loadSample, refKey, table } from './helpers'

const cols = ['Date', 'Ref', 'Amount', 'Party', 'Secret']
const T = (rows: CellValue[][]): ReturnType<typeof table> => table(cols, rows)
const cfg = config([refKey(), dateKey(3), amountKey()], { partyColumnA: 'Party', partyColumnB: 'Party', sideAName: 'Bank', sideBName: 'Ledger' })

/** A: r2 matches B: r2 exactly; the rest stay unmatched. */
function sample(): ReconResult {
  const A = T([
    [d(2026, 9, 1), 'FT1001', 500, 'Al Noor Trading LLC', 'IBAN AE07 0331 2345'],
    [d(2026, 9, 5), 'salary Sep', 12000, 'Mohd Rafi', 'IBAN AE99 SECRET'],
    [d(2026, 9, 22), 'TT9', 36750, 'Bin Hamdan', 'hidden'],
    [d(2026, 9, 8), 'X-77', 999.99, 'Al Noor Trading LLC', 'hidden']
  ])
  const B = T([
    [d(2026, 9, 1), 'FT1001', 500, 'Al Noor Trading LLC', 'n/a'],
    [d(2026, 9, 6), 'Payroll September', 7000, 'Mohammed Rafi', 'secret note'],
    [d(2026, 9, 6), 'Payroll Sep allowance', 5000, 'Mohammed Rafi', 'secret note'],
    [d(2026, 9, 21), 'INV-811', 12250, 'Bin Hamdan', 'x'],
    [d(2026, 9, 22), 'INV-812', 12250, 'Bin Hamdan', 'x'],
    [d(2026, 9, 23), 'INV-813', 12250, 'Bin Hamdan', 'x'],
    [d(2026, 9, 9), 'Rcpt X-77 al noor trading llc', 1000, 'Unrelated Co', 'x']
  ])
  return reconcile(A, B, cfg)
}

function sentData(payload: ReturnType<typeof buildAiPayload>, i = 0): { columns: string[]; side_a_lines: unknown[][]; side_b_lines: unknown[][]; candidates: Array<Record<string, unknown>> } {
  const content = payload.batches[i].messages[0].content
  return JSON.parse(content.slice(content.indexOf('{'))) as ReturnType<typeof sentData>
}

describe('buildAiPayload', () => {
  it('sends only unmatched lines and only the allowed fields', () => {
    const r = sample()
    expect(r.pairs.some((p) => p.aIds.includes('A:r2') && p.tier === 'matched')).toBe(true)
    const p = buildAiPayload(r, { includeDoubtful: false, maskParties: false })
    expect(p.batches).toHaveLength(1)
    const data = sentData(p)
    expect(data.columns).toEqual(['id', 'date', 'amount', 'text', 'party'])
    const ids = [...data.side_a_lines, ...data.side_b_lines].map((row) => row[0])
    expect(ids).not.toContain('A:r2')
    expect(ids).not.toContain('B:r2')
    expect(ids).toContain('A:r3')
    const all = p.batches[0].messages[0].content + p.batches[0].system
    // Unmapped columns never leave the computer.
    expect(all).not.toMatch(/SECRET|IBAN|hidden|secret note/i)
    for (const row of p.previewRows) expect(Object.keys(row).sort()).toEqual(['amount', 'batch', 'date', 'id', 'party', 'side', 'text'])
    const a3 = p.previewRows.find((x) => x.id === 'A:r3')
    expect(a3).toMatchObject({ date: '2026-09-05', amount: 12000, text: 'Reference: salary Sep', party: 'Mohd Rafi', side: 'Bank' })
    // The bridge request has exactly the four AiRequest fields.
    expect(Object.keys(toAiRequest(p.batches[0], 'claude-sonnet-5-5')).sort()).toEqual(['maxTokens', 'messages', 'model', 'system'])
    expect(toAiRequest(p.batches[0], 'claude-sonnet-5-5', { effort: 'medium' }).effort).toBe('medium')
    expect(p.batches[0].maxTokens).toBe(AI_MAX_TOKENS)
  })

  it('omits amount and date columns when those keys are not used', () => {
    const c = config([refKey()], { amountA: undefined, amountB: undefined })
    const r = reconcile(table(['Ref'], [['A1'], ['B2']]), table(['Ref'], [['ZZ'], ['B3']]), c)
    const p = buildAiPayload(r, { includeDoubtful: false, maskParties: false })
    expect(sentData(p).columns).toEqual(['id', 'text'])
    expect(p.batches[0].system).toContain('no amount column')
  })

  it('masks party names with stable tokens, also inside the text, and returns the mask map', () => {
    const r = sample()
    const p1 = buildAiPayload(r, { includeDoubtful: false, maskParties: true })
    const p2 = buildAiPayload(r, { includeDoubtful: false, maskParties: true, batchSize: 10 })
    const sent = p1.batches.map((b) => b.messages[0].content).join('\n')
    expect(sent).not.toMatch(/Rafi|Hamdan|Noor|Unrelated/i)
    expect([...p1.maskMap.entries()]).toEqual([...p2.maskMap.entries()])
    expect([...p1.maskMap.keys()].every((k) => /^PARTY_\d{2}$/.test(k))).toBe(true)
    const tokenOf = (name: string): string | undefined => [...p1.maskMap.entries()].find(([, v]) => v === name)?.[0]
    // Same party on both sides → same token; text mention masked too.
    const b8 = p1.previewRows.find((x) => x.id === 'B:r8')
    expect(b8?.text).toBe(`Reference: Rcpt X-77 ${tokenOf('Al Noor Trading LLC')}`)
    const a5 = p1.previewRows.find((x) => x.id === 'A:r5')
    expect(a5?.party).toBe(tokenOf('Al Noor Trading LLC'))
    expect(p1.batches[0].system).toContain('PARTY_01')
    const plain = buildAiPayload(r, { includeDoubtful: false, maskParties: false })
    expect(plain.maskMap.size).toBe(0)
  })

  it('respects the batch limit, keeps candidate groups together and sends candidates without their reason text', () => {
    const rowsA: CellValue[][] = []
    const rowsB: CellValue[][] = []
    for (let i = 0; i < 130; i++) {
      rowsA.push([d(2026, 9, 1 + (i % 28)), `A${i}`, 100 + i, 'P', null])
      rowsB.push([d(2026, 9, 1 + (i % 28)), `B${i}`, 7000 + i, 'P', null])
    }
    const r = reconcile(T(rowsA), T(rowsB), cfg)
    const candidate: Suggestion = { id: 'c1', aIds: ['A:r2', 'A:r100'], bIds: ['B:r50'], confidence: 60, reason: 'Secret Party Name', source: 'code-group', status: 'open' }
    const p = buildAiPayload(r, { includeDoubtful: false, maskParties: false, batchSize: 50, codeCandidates: [candidate] })
    expect(p.batches.length).toBeGreaterThanOrEqual(6)
    for (const b of p.batches) expect(b.lineIds.length).toBeLessThanOrEqual(50)
    const total = p.batches.reduce((s, b) => s + b.lineIds.length, 0)
    expect(total).toBe(260)
    expect(new Set(p.batches.flatMap((b) => b.lineIds)).size).toBe(260)
    const holder = p.batches.find((b) => b.candidateIds.includes('c1'))
    expect(holder?.lineIds).toEqual(expect.arrayContaining(['A:r2', 'A:r100', 'B:r50']))
    expect(p.candidateCount).toBe(1)
    expect(p.batches.map((b) => b.messages[0].content).join('')).not.toContain('Secret Party Name')
    // Even split: sizes differ by little.
    const sizes = p.batches.map((b) => b.lineIds.length)
    expect(Math.max(...sizes) - Math.min(...sizes)).toBeLessThanOrEqual(5)
  })

  it('includes open Doubtful lines only when asked', () => {
    const c = config([refKey(), dateKey(3), amountKey()])
    const A = table(['Date', 'Ref', 'Amount'], [[d(2026, 9, 1), 'R1', 100]])
    const B = table(['Date', 'Ref', 'Amount'], [[d(2026, 9, 20), 'R1', 100]])
    const r = reconcile(A, B, c)
    expect(r.pairs[0]?.tier).toBe('doubtful')
    expect(buildAiPayload(r, { includeDoubtful: false, maskParties: false }).batches).toHaveLength(0)
    expect(buildAiPayload(r, { includeDoubtful: true, maskParties: false }).previewRows.map((x) => x.id)).toEqual(['A:r2', 'B:r2'])
  })

  it('gives a sane token and cost estimate', () => {
    const p = buildAiPayload(sample(), { includeDoubtful: false, maskParties: false, model: 'claude-sonnet-5-5' })
    const chars = p.batches[0].system.length + p.batches[0].messages[0].content.length
    expect(p.estimate.inputTokens).toBeGreaterThan(chars / 5)
    expect(p.estimate.inputTokens).toBeLessThan(chars / 3)
    expect(p.estimate.outputTokens).toBeGreaterThan(0)
    expect(p.estimate.outputTokens).toBeLessThanOrEqual(AI_MAX_TOKENS)
    expect(p.estimate.usd).toBeCloseTo(estimateCost(p.estimate.inputTokens, p.estimate.outputTokens, 'claude-sonnet-5-5') as number, 10)
    expect(p.estimate.usd).toBeGreaterThan(0)
    expect(p.estimate.usd).toBeLessThan(1)
    expect(estimateCost(1_000_000, 0, 'claude-opus-5-5')).toBe(4)
    expect(priceFor('claude-haiku-4-5')?.input).toBe(1)
  })

  it('never guesses a price: unknown models have no estimate', () => {
    expect(priceFor('something-else')).toBeNull()
    expect(estimateCost(1_000_000, 1_000_000, 'something-else')).toBeNull()
    expect(priceFor('gpt-6.1-sol', 'openai')).toEqual({ family: 'GPT-6.1 Sol', input: 2, output: 10 })
    expect(priceFor('gpt-5', 'openai')?.input).toBe(1.25)
    expect(priceFor('gpt-5-2025-08-07', 'openai')?.input).toBe(1.25)
    expect(priceFor('gpt-5.3', 'openai')).toBeNull()
    expect(priceFor('gemini-3.8-flash', 'gemini')).toEqual({ family: 'Gemini 3.8 Flash', input: 0.75, output: 3.75 })
    expect(priceFor('models/gemini-2.5-flash-lite', 'gemini')?.output).toBe(0.4)
    expect(priceFor('deepseek-flash', 'deepseek')?.input).toBe(0.3)
    expect(priceFor('deepseek-v4-flash', 'deepseek')?.input).toBe(0.3)
    // A model is priced only under its own provider.
    expect(priceFor('claude-sonnet-5-5', 'openai')).toBeNull()
    expect(priceFor('gpt-6.1-sol', 'custom')).toBeNull()
  })

  it('describes cost per provider: priced, local server, or not available', () => {
    expect(describePricing('anthropic', 'claude-sonnet-5-5').kind).toBe('priced')
    expect(describePricing('openai', 'my-fine-tune').kind).toBe('unknown')
    expect(describePricing('custom', 'llama3.1:8b', 'http://localhost:11434/v1')).toEqual({ kind: 'local' })
    expect(describePricing('custom', 'openai/gpt-5', 'https://openrouter.ai/api/v1')).toEqual({ kind: 'unknown' })
    const r = sample()
    const unknown = buildAiPayload(r, { includeDoubtful: false, maskParties: false, provider: 'openai', model: 'my-fine-tune' })
    expect(unknown.estimate.usd).toBeNull()
    const local = buildAiPayload(r, { includeDoubtful: false, maskParties: false, provider: 'custom', model: 'llama3.1:8b', baseUrl: 'http://localhost:11434/v1' })
    expect(local.estimate.usd).toBe(0)
    const gemini = buildAiPayload(r, { includeDoubtful: false, maskParties: false, provider: 'gemini' })
    expect(gemini.estimate.usd).toBeCloseTo(estimateCost(gemini.estimate.inputTokens, gemini.estimate.outputTokens, 'gemini-3.8-flash', 'gemini') as number, 10)
  })

  it('builds provider-tagged bridge requests', () => {
    const p = buildAiPayload(sample(), { includeDoubtful: false, maskParties: false })
    const openai = toAiRequest(p.batches[0], 'gpt-6.1-sol', { provider: 'openai', baseUrl: 'https://ignored.example' })
    expect(openai.provider).toBe('openai')
    expect(openai.baseUrl).toBeUndefined()
    const custom = toAiRequest(p.batches[0], 'llama3.1:8b', { provider: 'custom', baseUrl: 'http://localhost:11434/v1' })
    expect(custom.baseUrl).toBe('http://localhost:11434/v1')
    expect(modelFor('openai', '')).toBe('gpt-6.1-sol')
    expect(modelFor('gemini', ' models/gemini-2.5-pro ')).toBe('gemini-2.5-pro')
    expect(modelFor('custom', '')).toBe('')
  })

  it('recognises model names from the price table only', () => {
    expect(isKnownModel('claude-sonnet-5-5')).toBe(true)
    expect(isKnownModel(' claude-opus-5-5 ')).toBe(true)
    expect(isKnownModel('claude-haiku-4-5')).toBe(true)
    expect(isKnownModel('gpt-5')).toBe(false)
    expect(isKnownModel('gpt-5', 'openai')).toBe(true)
    expect(isKnownModel('deepseek-v4-pro', 'deepseek')).toBe(true)
    expect(isKnownModel('claude-sonet-5-5')).toBe(false)
    expect(isKnownModel('')).toBe(false)
  })
})

describe('buildAiPayload on the bank sample files', () => {
  it('sends only unresolved lines with mapped values, masked parties and a sane estimate', () => {
    const a = loadSample('bank/ENBD_Current_Statement_Sep2026.xlsx')
    const b = loadSample('bank/GL_101200_Cash_Sep2026.xlsx')
    const s = suggestKeys('bank', a, b)
    const c = config(s.keys, { moduleId: 'bank', sign: 'inverse', amountA: s.amountA, amountB: s.amountB, partyColumnB: s.partyColumnB })
    const r = reconcile(a, b, c)
    const { suggestions } = findGroupMatches(r)
    const p = buildAiPayload(r, { includeDoubtful: true, maskParties: true, codeCandidates: suggestions, model: 'claude-sonnet-5-5' })
    const unresolved = eligiblePools(r, true)
    expect(p.previewRows).toHaveLength(unresolved.a.length + unresolved.b.length)
    for (const batch of p.batches) expect(batch.lineIds.length).toBeLessThanOrEqual(200)
    const sent = p.batches.map((x) => x.messages[0].content).join('\n')
    for (const name of p.maskMap.values()) expect(sent.toUpperCase()).not.toContain(name.toUpperCase())
    const matchedIds = r.pairs.filter((x) => x.tier === 'matched').flatMap((x) => x.aIds)
    for (const id of matchedIds.slice(0, 20)) expect(sent).not.toContain(`"${id}"`)
    expect(p.estimate.usd).toBeGreaterThan(0)
    expect(p.estimate.usd).toBeLessThan(0.5)
  })
})

describe('parseAiResponse', () => {
  const r = sample()
  const json = (x: unknown): string => JSON.stringify(x)

  it('reads plain JSON, code fences and a lead-in sentence; rejects garbage', () => {
    const one = [{ a_ids: ['A:r3'], b_ids: ['B:r3', 'B:r4'], confidence: 88, reason: 'salary Sep is Payroll September' }]
    expect(parseAiResponse(json(one), r, new Map())).toHaveLength(1)
    expect(parseAiResponse('```json\n' + json(one) + '\n```', r, new Map())).toHaveLength(1)
    expect(parseAiResponse('Here are the matches [see below]:\n' + json(one), r, new Map())).toHaveLength(1)
    expect(parseAiResponse('[]', r, new Map())).toEqual([])
    expect(() => parseAiResponse('I could not find any matches.', r, new Map())).toThrow(AiResponseError)
    expect(() => parseAiResponse('{"a_ids":["A:r3"]}', r, new Map())).toThrow(AiResponseError)
    expect(() => parseAiResponse('', r, new Map())).toThrow(AiResponseError)
    expect(() => extractJsonArray('[{"a_ids": [}')).toThrow(AiResponseError)
  })

  it('returns open AI suggestions with clamped confidence and unmasked reasons', () => {
    const p = buildAiPayload(r, { includeDoubtful: false, maskParties: true })
    const tok = [...p.maskMap.entries()].find(([, v]) => v === 'Mohd Rafi')?.[0] as string
    const out = parseAiResponse(json([{ a_ids: ['A:r3'], b_ids: ['B:r3', 'B:r4'], confidence: 140, reason: `${tok} is the same employee` }]), r, p.maskMap)
    expect(out[0]).toMatchObject({ aIds: ['A:r3'], bIds: ['B:r3', 'B:r4'], confidence: 100, source: 'ai', status: 'open', reason: 'Mohd Rafi is the same employee' })
    expect(out[0].id).toMatch(/^sug-ai-/)
    expect(parseAiResponse(json([{ a_ids: ['A:r3'], b_ids: ['B:r4', 'B:r3'], confidence: '75' }]), r, new Map())[0].confidence).toBe(75)
  })

  it('discards unknown, wrong-side, duplicate, matched and one-sided ids, bad shapes and low confidence', () => {
    const res = parseAiResponseDetailed(
      json([
        { a_ids: ['A:r99'], b_ids: ['B:r3'], confidence: 90, reason: '' },
        { a_ids: ['B:r3'], b_ids: ['A:r3'], confidence: 90, reason: '' },
        { a_ids: ['A:r3', 'A:r3'], b_ids: ['B:r3'], confidence: 90, reason: '' },
        { a_ids: ['A:r2'], b_ids: ['B:r2'], confidence: 90, reason: 'already matched' },
        { a_ids: [], b_ids: ['B:r3'], confidence: 90, reason: '' },
        { a_ids: 'A:r3', b_ids: ['B:r3'], confidence: 90 },
        { a_ids: ['A:r3'], b_ids: ['B:r3'], confidence: 'high' },
        { a_ids: ['A:r3'], b_ids: ['B:r3'], confidence: 30, reason: 'weak' },
        'nonsense'
      ]),
      r,
      new Map()
    )
    expect(res.suggestions).toEqual([])
    expect(res.discarded).toEqual({ 'unknown-id': 2, 'duplicate-id': 1, 'not-available': 1, 'empty-side': 1, 'invalid-shape': 3, 'low-confidence': 1 })
  })

  it('discards suggestions whose totals do not reconcile, checked by code', () => {
    const res = parseAiResponseDetailed(
      json([
        { a_ids: ['A:r5'], b_ids: ['B:r8'], confidence: 95, reason: 'X-77 found in remarks' }, // 999.99 vs 1,000.00
        { a_ids: ['A:r4'], b_ids: ['B:r5', 'B:r6', 'B:r7'], confidence: 92, reason: 'sum match' } // 36,750 = 3 × 12,250
      ]),
      r,
      new Map()
    )
    expect(res.discarded).toEqual({ unbalanced: 1 })
    expect(res.suggestions.map((s) => s.bIds)).toEqual([['B:r5', 'B:r6', 'B:r7']])
    // A fixed tolerance lets the 0.01 difference through.
    const loose = { ...r, config: { ...r.config, keys: r.config.keys.map((k) => (k.type === 'amount' ? { ...k, tolerance: { mode: 'fixed' as const, value: 0.05 } } : k)) } }
    expect(parseAiResponse(json([{ a_ids: ['A:r5'], b_ids: ['B:r8'], confidence: 95, reason: '' }]), loose, new Map())).toHaveLength(1)
  })

  it('keeps the more confident suggestion when two reuse a line', () => {
    const res = parseAiResponseDetailed(
      json([
        { a_ids: ['A:r3'], b_ids: ['B:r3', 'B:r4'], confidence: 70, reason: 'weaker' },
        { a_ids: ['A:r3'], b_ids: ['B:r4', 'B:r3'], confidence: 90, reason: 'stronger' }
      ]),
      r,
      new Map()
    )
    expect(res.suggestions.map((s) => s.reason)).toEqual(['stronger'])
    expect(res.discarded).toEqual({ reused: 1 })
  })

  it('accepts any pairing when the recon has no amount key, and Doubtful lines only when allowed', () => {
    const c = config([refKey(), dateKey(3)], { amountA: undefined, amountB: undefined })
    const nr = reconcile(table(['Date', 'Ref'], [[d(2026, 9, 1), 'Emp 1'], [d(2026, 9, 2), 'Emp 2']]), table(['Date', 'Ref'], [[d(2026, 9, 1), 'Employee One'], [d(2026, 9, 2), 'Employee 2X']]), c)
    const out = parseAiResponse(json([{ a_ids: ['A:r2'], b_ids: ['B:r2', 'B:r3'], confidence: 60, reason: 'names' }]), nr, new Map())
    expect(out).toHaveLength(1)

    const dc = config([refKey(), dateKey(3), amountKey()])
    const dr = reconcile(table(['Date', 'Ref', 'Amount'], [[d(2026, 9, 1), 'R1', 100]]), table(['Date', 'Ref', 'Amount'], [[d(2026, 9, 20), 'R1', 100]]), dc)
    const text = json([{ a_ids: ['A:r2'], b_ids: ['B:r2'], confidence: 80, reason: '' }])
    expect(parseAiResponse(text, dr, new Map())).toHaveLength(0)
    expect(parseAiResponse(text, dr, new Map(), { includeDoubtful: true })).toHaveLength(1)
  })
})

describe('mergeSuggestions', () => {
  it('skips what the session already has and folds AI confirmations into fresh code candidates', () => {
    const base = { source: 'code-group' as const, status: 'open' as const }
    const existing: Suggestion[] = [{ id: 'e', aIds: ['A:r1'], bIds: ['B:r1'], confidence: 90, reason: 'old', ...base, status: 'rejected' }]
    const code: Suggestion[] = [
      { id: 'c1', aIds: ['A:r2'], bIds: ['B:r3', 'B:r2'], confidence: 90, reason: 'sum', ...base },
      { id: 'c2', aIds: ['A:r1'], bIds: ['B:r1'], confidence: 90, reason: 'dup', ...base }
    ]
    const ai: Suggestion[] = [
      { id: 'a1', aIds: ['A:r2'], bIds: ['B:r2', 'B:r3'], confidence: 70, reason: 'same supplier', source: 'ai', status: 'open' },
      { id: 'a2', aIds: ['A:r1'], bIds: ['B:r1'], confidence: 70, reason: 'rejected before', source: 'ai', status: 'open' },
      { id: 'a3', aIds: ['A:r9'], bIds: ['B:r9'], confidence: 70, reason: 'new', source: 'ai', status: 'open' }
    ]
    const out = mergeSuggestions(existing, code, ai)
    expect(out.map((s) => s.id)).toEqual(['c1', 'a3'])
    expect(out[0]).toMatchObject({ source: 'code-group', confidence: 80, reason: 'sum. AI review: same supplier' })
  })
})

describe('runSmartReconBatches (mocked bridge)', () => {
  const r = sample()
  const ok = (text: string): AiResult => ({ ok: true, response: { text, inputTokens: 100, outputTokens: 20 } })

  function payload(): ReturnType<typeof buildAiPayload> {
    const { suggestions } = findGroupMatches(r)
    return buildAiPayload(r, { includeDoubtful: false, maskParties: false, batchSize: 3, codeCandidates: suggestions })
  }

  it('sends each batch with the model, parses replies and keeps partial results when a later batch fails', async () => {
    const p = payload()
    expect(p.batches.length).toBeGreaterThanOrEqual(2)
    const target = p.batches.findIndex((b) => b.lineIds.includes('A:r3') && b.lineIds.includes('B:r3') && b.lineIds.includes('B:r4'))
    expect(target).toBeGreaterThanOrEqual(0)
    const complete = vi.fn(async (req: AiRequest): Promise<AiResult> => {
      const call = complete.mock.calls.length - 1
      expect(req.model).toBe('claude-sonnet-5-5')
      expect(req.effort).toBe(SMART_RECON_EFFORT)
      if (call === target) return ok('```json\n[{"a_ids":["A:r3"],"b_ids":["B:r3","B:r4"],"confidence":85,"reason":"salary"}]\n```')
      if (call > target) return { ok: false, code: 'rate-limit', message: 'The Claude API rate limit was reached.' }
      return ok('not json')
    })
    const progress: number[] = []
    const out = await runSmartReconBatches({ batches: p.batches, model: 'claude-sonnet-5-5', result: r, maskMap: p.maskMap, includeDoubtful: false, complete, onProgress: (x) => progress.push(x.done) })
    expect(out.suggestions.map((s) => s.aIds)).toEqual([['A:r3']])
    expect(out.unreadable).toBe(target)
    if (target < p.batches.length - 1) expect(out.stop).toEqual({ code: 'rate-limit', message: 'The Claude API rate limit was reached.' })
    expect(out.usage.inputTokens).toBe(100 * (target + 1))
    expect(progress[0]).toBe(0)
  })

  it('stops on cancel and on bridge errors with the error code', async () => {
    const p = payload()
    const controller = new AbortController()
    const complete = vi.fn(async (): Promise<AiResult> => {
      controller.abort()
      return new Promise<AiResult>(() => undefined) // never answers
    })
    const out = await runSmartReconBatches({ batches: p.batches, model: 'm', result: r, maskMap: p.maskMap, includeDoubtful: false, complete, signal: controller.signal })
    expect(out.stop?.code).toBe('cancelled')
    expect(complete).toHaveBeenCalledTimes(1)

    const bad = await runSmartReconBatches({
      batches: p.batches,
      model: 'm',
      result: r,
      maskMap: p.maskMap,
      includeDoubtful: false,
      complete: async () => ({ ok: false, code: 'bad-key', message: 'Your Claude API key was not accepted.' })
    })
    expect(bad).toMatchObject({ completed: 0, stop: { code: 'bad-key' }, suggestions: [] })
  })

  it('skips an unreadable reply and carries on with the next batch', async () => {
    const p = payload()
    const replies = ['Sorry, here is my analysis without JSON.', '[]', '[]', '[]', '[]']
    const out = await runSmartReconBatches({
      batches: p.batches,
      model: 'm',
      result: r,
      maskMap: p.maskMap,
      includeDoubtful: false,
      complete: async () => ok(replies.shift() ?? '[]')
    })
    expect(out).toMatchObject({ unreadable: 1, completed: p.batches.length, stop: null })
  })

  it('describes discarded proposals in plain English', () => {
    expect(describeDiscarded({})).toBeNull()
    expect(describeDiscarded({ unbalanced: 2, reused: 1 })).toBe("3 AI proposals were discarded by the app's checks: totals don't reconcile (2); line reused in another suggestion (1).")
  })
})

describe('masking without a party column (names in text keys)', () => {
  const hrCols = ['Emp No', 'Employee Name', 'Remarks', 'Amount']
  const H = (rows: CellValue[][]): ReturnType<typeof table> => table(hrCols, rows)
  const nameKey = refKey('Employee Name', 'Employee Name', { id: 'name', name: 'Employee Name', identifying: false })
  const remarksKey = refKey('Remarks', 'Remarks', { id: 'remarks', name: 'Remarks', identifying: false })
  const empKey = refKey('Emp No', 'Emp No', { id: 'emp', name: 'Employee No', type: 'id' })
  const hrCfg = config([empKey, nameKey, remarksKey, amountKey()])
  const longRemark = `${'x'.repeat(225)} paid to Fatima Al Zahra`

  function hr(): ReconResult {
    const A = H([
      ['E1', 'Fatima Al Zahra', longRemark, 100],
      ['E2', 'Jo', 'bonus for Jo', 200],
      ['E3', 'A', 'cash', 300]
    ])
    const B = H([
      ['E9', 'FATIMA  AL ZAHRA', 'salary', 100],
      ['E8', 'Jo', 'cash', 250]
    ])
    return reconcile(A, B, hrCfg)
  }

  it('masks the values of name-like text keys with stable tokens (R7)', () => {
    const p = buildAiPayload(hr(), { includeDoubtful: false, maskParties: true })
    const sent = p.batches.map((b) => b.messages[0].content).join('\n')
    expect(sent).not.toMatch(/Fatima|Zahra/i)
    expect(sent).not.toMatch(/Employee Name: Jo/)
    const tok = [...p.maskMap.entries()].find(([, v]) => v.toUpperCase().startsWith('FATIMA'))?.[0]
    expect(tok).toMatch(/^PARTY_\d{2}$/)
    // The same name on both sides (case and spacing ignored) gets the same token.
    const data = sentData(p)
    const texts = [...data.side_a_lines, ...data.side_b_lines].map((l) => String(l[data.columns.indexOf('text')]))
    expect(texts.filter((t) => t.includes(`Employee Name: ${tok}`))).toHaveLength(2)
    // IDs are never treated as names.
    expect(sent).toContain('E1')
  })

  it('masks before shortening, so a name cut at the 240-character limit cannot leak (R8)', () => {
    const p = buildAiPayload(hr(), { includeDoubtful: false, maskParties: true })
    const sent = p.batches.map((b) => b.messages[0].content).join('\n')
    expect(sent).not.toMatch(/Fat|Zah/i)
  })

  it('masks short names: whole values always, two-letter names inside text too', () => {
    const p = buildAiPayload(hr(), { includeDoubtful: false, maskParties: true })
    const data = sentData(p)
    const texts = [...data.side_a_lines, ...data.side_b_lines].map((l) => String(l[data.columns.indexOf('text')]))
    expect(texts.some((t) => /Jo/.test(t))).toBe(false)
    expect(texts.some((t) => t.startsWith('Employee Name: A |'))).toBe(false)
    // Ordinary words are not mistaken for the one-letter name "A".
    expect(texts.some((t) => t.includes('Remarks: cash'))).toBe(true)
  })

  it('reports whether masking can hide anything', () => {
    expect(canMaskParties(hrCfg)).toBe(true)
    expect(canMaskParties(config([empKey, remarksKey, amountKey()]))).toBe(false)
    expect(canMaskParties(config([empKey, amountKey()], { partyColumnA: 'Party' }))).toBe(true)
  })
})

describe('Smart Recon cancel', () => {
  it('asks the main process to stop the request in flight', async () => {
    const r = sample()
    const p = buildAiPayload(r, { includeDoubtful: false, maskParties: false })
    const controller = new AbortController()
    const sent: AiRequest[] = []
    const cancel = vi.fn()
    const complete = vi.fn(async (req: AiRequest): Promise<AiResult> => {
      sent.push(req)
      setTimeout(() => controller.abort(), 0)
      return new Promise<AiResult>(() => undefined)
    })
    const out = await runSmartReconBatches({ batches: p.batches, model: 'm', result: r, maskMap: p.maskMap, includeDoubtful: false, complete, cancel, signal: controller.signal })
    expect(out.stop?.code).toBe('cancelled')
    expect(sent[0].requestId).toMatch(/^[A-Za-z0-9-]{1,64}$/)
    expect(cancel).toHaveBeenCalledWith(sent[0].requestId)
  })
})
