// The wizard's own path on the sample files: read upload → suggested mapping → validate → reconcile → session → review model.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { acceptPair, buildStatement, createSession, findGroupMatches, manualMatch, rejectPair, reconcile, validateConfig } from '@engine/index'
import { applySuggestions } from '@/features/wizard/smart/applySuggestions'
import { buildMeta, finalConfig, suggestedConfig } from '@/features/wizard/configFactory'
import { autoComment, buildReconWorkbook, buildSummaryHtml, exportFileName } from '@export/index'
import { readUpload, PDF_MESSAGE, parseSheet } from '@/features/wizard/upload/loadFile'
import {
  applyMany,
  comparableTotal,
  displayColumns,
  lineIndex,
  matchesQuery,
  pairSearchText,
  pairsForTier,
  reviewKpis,
  unmatchedLines
} from '@/features/wizard/review/model'

const SAMPLES = resolve(__dirname, '../../sample-data')
function upload(path: string): ReturnType<typeof readUpload> {
  const buf = readFileSync(resolve(SAMPLES, path))
  return readUpload(path.split('/').pop() ?? path, buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) as ArrayBuffer)
}
const expected = JSON.parse(readFileSync(resolve(SAMPLES, 'expected-results.json'), 'utf8')) as Record<string, { tiers: Record<string, number> }>

function runSample(moduleId: 'bank' | 'ar' | 'ap' | 'general', a: string, b: string, names: [string, string]) {
  const fa = upload(a)
  const fb = upload(b)
  const cfg = finalConfig(suggestedConfig(moduleId, fa.table, fb.table, names[0], names[1], 'AED'), names[0], names[1], 'AED')
  expect(validateConfig(cfg, fa.table, fb.table)).toEqual([])
  const result = reconcile(fa.table, fb.table, cfg)
  const meta = buildMeta({ accountLabel: 'Test', period: 'Sep 2026', tableA: fa.table, tableB: fb.table, preparer: 'Sana Fathima', currency: 'AED' })
  return { fa, fb, cfg, result, session: createSession(result, meta) }
}

describe('upload', () => {
  it('finds the bank header on row 7 and captures balances', () => {
    const f = upload('bank/ENBD_Current_Statement_Sep2026.xlsx')
    expect(f.table.headerRowIndex).toBe(6)
    expect(f.detectedHeaderRow).toBe(6)
    expect(f.table.rows).toHaveLength(301)
    expect(f.table.openingBalance).toBe(1245678.35)
    expect(f.table.closingBalance).toBe(2013838.49)
    expect(f.table.excluded.length).toBeGreaterThan(0)
  })
  it('re-parses with a different header row', () => {
    const f = upload('bank/ENBD_Current_Statement_Sep2026.xlsx')
    const g = parseSheet(f.workbook, f.fileName, f.size, f.sheetIndex, 0)
    expect(g.table.headerRowIndex).toBe(0)
    expect(g.detectedHeaderRow).toBe(6)
  })
  it('refuses PDFs with a pointer to the PDF to Excel tool', () => {
    expect(() => readUpload('statement.pdf', new ArrayBuffer(4))).toThrow(PDF_MESSAGE)
    expect(() => readUpload('notes.docx', new ArrayBuffer(4))).toThrow(/not an Excel or CSV file/)
  })
})

describe('suggested mapping reproduces the expected tiers', () => {
  it('Bank: Matched 255, Doubtful 16, Likely 1, Unmatched 29 / 19', () => {
    const { session, cfg } = runSample('bank', 'bank/ENBD_Current_Statement_Sep2026.xlsx', 'bank/GL_101200_Cash_Sep2026.xlsx', ['Bank statement', 'General ledger extract'])
    expect(cfg.sign).toBe('inverse')
    const k = reviewKpis(session)
    expect([k.matched.count, k.doubtful.count, k.likely.count, k.unmatchedA.count, k.unmatchedB.count]).toEqual([255, 16, 1, 29, 19])
    expect(k.hasAmount).toBe(true)
    expect(k.matched.amount).toBeGreaterThan(0)
    expect(buildStatement(session.result, session.meta).unexplainedDifference).toBe(0)
  })

  it('General HR vs WPS (no amount): counts only', () => {
    const { session } = runSample('general', 'general/HR_Employee_Master.xlsx', 'general/WPS_Payroll_Register_Sep2026.xlsx', ['HR employee master', 'WPS payroll register'])
    const k = reviewKpis(session)
    const t = expected.hr.tiers
    expect([k.matched.count, k.doubtful.count, k.likely.count, k.unmatchedA.count, k.unmatchedB.count]).toEqual([t.matched, t.doubtful, t.likely, t.unmatchedA, t.unmatchedB])
    expect(k.hasAmount).toBe(false)
    expect(k.matched.amount).toBeNull()
    expect(buildStatement(session.result, session.meta).kind).toBe('record-count')
  })

  it('General intercompany (with amount) matches expected-results.json', () => {
    const { session } = runSample('general', 'general/Intercompany_EntityA_Dubai.xlsx', 'general/Intercompany_EntityB_AbuDhabi.xlsx', ['Entity A', 'Entity B'])
    const k = reviewKpis(session)
    const t = expected.intercompany.tiers
    expect([k.matched.count, k.doubtful.count, k.likely.count, k.unmatchedA.count, k.unmatchedB.count]).toEqual([t.matched, t.doubtful, t.likely, t.unmatchedA, t.unmatchedB])
    expect(k.hasAmount).toBe(true)
  })

  for (const [id, a, b] of [
    ['ar', 'ar/Our_AR_Ledger_AlNoor_Trading.xlsx', 'ar/AlNoor_Trading_SOA.xlsx'],
    ['ap', 'ap/Our_AP_Ledger_Gulf_Supplies.xlsx', 'ap/Gulf_Supplies_SOA.xlsx']
  ] as const) {
    it(`${id.toUpperCase()} matches expected-results.json`, () => {
      const { session } = runSample(id, a, b, ['Ours', 'Theirs'])
      const k = reviewKpis(session)
      const t = expected[id].tiers
      expect([k.matched.count, k.doubtful.count, k.likely.count, k.unmatchedA.count, k.unmatchedB.count]).toEqual([t.matched, t.doubtful, t.likely, t.unmatchedA, t.unmatchedB])
    })
  }
})

describe('review model', () => {
  const bank = runSample('bank', 'bank/ENBD_Current_Statement_Sep2026.xlsx', 'bank/GL_101200_Cash_Sep2026.xlsx', ['Bank statement', 'General ledger extract'])
  const idx = lineIndex(bank.result)

  it('lists pairs per tier in File A order', () => {
    const d = pairsForTier(bank.result, 'doubtful')
    expect(d.every((p) => p.tier === 'doubtful')).toBe(true)
    expect(d.reduce((n, p) => n + p.aIds.length, 0)).toBe(16)
  })

  it('shows the date key, text keys and one descriptive column per side', () => {
    const a = displayColumns(bank.cfg, 'A', bank.fa.table.columns)
    expect(a[0].kind).toBe('date')
    expect(a.some((c) => c.column === 'Description')).toBe(true)
    const b = displayColumns(bank.cfg, 'B', bank.fb.table.columns)
    expect(b.some((c) => c.column === 'Cheque No')).toBe(true)
    expect(b.some((c) => c.column === 'Debit' || c.column === 'Credit')).toBe(false)
  })

  it('search matches words and amounts written with separators', () => {
    const trans = bank.result.pairs.find((p) => p.flags.includes('transposition'))
    expect(trans).toBeDefined()
    if (!trans) return
    const text = pairSearchText(trans, idx)
    expect(matchesQuery(text, '004512')).toBe(true)
    expect(matchesQuery(text, '8,450.00')).toBe(true)
    expect(matchesQuery(text, 'transposition 8540')).toBe(true)
    expect(matchesQuery(text, 'nothing-like-this')).toBe(false)
  })

  it('labels probable bank charges among unmatched bank lines', () => {
    const lines = unmatchedLines(bank.result, 'A', idx)
    const labels = lines.map((l) => autoComment('bank', 'A', l)).filter(Boolean)
    expect(labels).toContain('Probable bank charge – post JV')
    expect(labels).toContain('Probable bank interest – post JV')
  })

  it('bulk decisions collect errors and keep going', () => {
    const open = pairsForTier(bank.result, 'doubtful').map((p) => p.id)
    const r = applyMany(bank.session, open, (s, id) => rejectPair(s, id, 'Sana'))
    expect(r.done).toBe(open.length)
    expect(r.errors).toEqual([])
    expect(r.state.result.stats.doubtful).toBe(0)
    const dup = bank.result.pairs.find((p) => p.flags.includes('multiple-candidates'))
    const again = applyMany(bank.session, [dup?.id ?? '', 'missing'], (s, id) => acceptPair(s, id, 'Sana'))
    expect(again.errors.length).toBeGreaterThan(0)
  })

  it('a wizard session exports to Excel and the PDF summary HTML', async () => {
    const statement = buildStatement(bank.session.result, bank.session.meta)
    const bytes = await buildReconWorkbook(bank.session, statement)
    expect(bytes.byteLength).toBeGreaterThan(10_000)
    expect(buildSummaryHtml(bank.session, statement)).toContain('<html')
    expect(exportFileName(bank.session, 'xlsx')).toMatch(/^Reco-Do_Bank_.*\.xlsx$/)
  })

  it('manual match totals use side A sign convention', () => {
    const a = bank.result.unmatchedA.slice(0, 1)
    const b = bank.result.unmatchedB.slice(0, 1)
    const diff = comparableTotal(a, idx) - comparableTotal(b, idx)
    if (Math.abs(diff) > 0.005) expect(() => manualMatch(bank.session, a, b, 'Sana')).toThrow()
    const next = manualMatch(bank.session, a, b, 'Sana', 'Agreed with treasury')
    expect(next.result.stats.unmatchedA).toBe(28)
  })
})

describe('Smart Recon results during review (R2)', () => {
  it('are added to the newest session, so decisions made while it ran are kept', () => {
    const bank = runSample('bank', 'bank/ENBD_Current_Statement_Sep2026.xlsx', 'bank/GL_101200_Cash_Sep2026.xlsx', ['Bank statement', 'General ledger extract'])
    const atStart = bank.session
    const pairId = pairsForTier(atStart.result, 'doubtful')[0].id
    const latest = rejectPair(atStart, pairId, 'Sana')
    const found = findGroupMatches(atStart.result).suggestions.slice(0, 2)
    const { next, added } = applySuggestions(latest, found)
    expect(added).toBe(found.length)
    expect(next.audit).toHaveLength(1)
    expect(next.result.pairs.find((p) => p.id === pairId)).toBeUndefined()
    expect(applySuggestions(next, found).added).toBe(0)
  })
})
