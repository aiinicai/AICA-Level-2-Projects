// Integration tests on the generated sample files with the recommended mapping from sample-data/README.md.
import { describe, expect, it } from 'vitest'
import type { MatchKey, ParsedTable, ReconConfig, ReconResult } from '@shared/contracts'
import { approveSuggestion, buildStatement, createSession, findGroupMatches, findPartialReferenceMatches, addSuggestions, reconcile, suggestKeys } from '@engine/index'
import { expected, loadSample, metaFor, sampleConfig, tierCounts } from './helpers'

const exp = expected()

const ref = (a: string, b: string, type: MatchKey['type'] = 'text', name = 'Reference'): MatchKey => ({
  id: name.toLowerCase().replace(/\s+/g, '-'),
  name,
  type,
  use: true,
  columnA: a,
  columnB: b,
  identifying: true,
  textRule: 'normalised'
})
const date = (a: string, b: string, tol: number): MatchKey => ({ id: 'date', name: 'Date', type: 'date', use: true, columnA: a, columnB: b, identifying: false, dateToleranceDays: tol })
const amount: MatchKey = { id: 'amount', name: 'Amount', type: 'amount', use: true, columnA: '', columnB: '', identifying: true, tolerance: { mode: 'exact' } }

interface Case {
  name: string
  key: string
  fileA: string
  fileB: string
  cfg: ReconConfig
}

const cases: Case[] = [
  {
    name: 'Bank',
    key: 'bank',
    fileA: 'bank/ENBD_Current_Statement_Sep2026.xlsx',
    fileB: 'bank/GL_101200_Cash_Sep2026.xlsx',
    cfg: sampleConfig({
      moduleId: 'bank',
      sign: 'inverse',
      sideAName: 'Bank statement',
      sideBName: 'General ledger extract',
      keys: [ref('Reference No', 'Cheque No'), date('Txn Date', 'Posting Date', 3), amount],
      amountA: { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' },
      amountB: { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' },
      partyColumnB: 'Party'
    })
  },
  {
    name: 'AR',
    key: 'ar',
    fileA: 'ar/Our_AR_Ledger_AlNoor_Trading.xlsx',
    fileB: 'ar/AlNoor_Trading_SOA.xlsx',
    cfg: sampleConfig({
      moduleId: 'ar',
      sign: 'inverse',
      sideAName: 'Our AR ledger (customer account)',
      sideBName: "Customer's statement of account",
      keys: [ref('Invoice / Ref No', 'Supplier Inv / Ref'), date('Date', 'Posting Date', 7), amount],
      amountA: { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' },
      amountB: { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' }
    })
  },
  {
    name: 'AP',
    key: 'ap',
    fileA: 'ap/Our_AP_Ledger_Gulf_Supplies.xlsx',
    fileB: 'ap/Gulf_Supplies_SOA.xlsx',
    cfg: sampleConfig({
      moduleId: 'ap',
      sign: 'inverse',
      sideAName: 'Our AP ledger (supplier account)',
      sideBName: "Supplier's statement of account",
      keys: [ref('Supplier Inv / Ref', 'Invoice / Doc No'), date('Date', 'Date', 7), amount],
      amountA: { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' },
      amountB: { kind: 'debit-credit', debit: 'Debit', credit: 'Credit' }
    })
  },
  {
    name: 'General - HR vs WPS (no amount)',
    key: 'hr',
    fileA: 'general/HR_Employee_Master.xlsx',
    fileB: 'general/WPS_Payroll_Register_Sep2026.xlsx',
    cfg: sampleConfig({
      moduleId: 'general',
      sign: 'same',
      sideAName: 'HR employee master',
      sideBName: 'WPS payroll register',
      keys: [
        ref('Emp ID', 'Employee No', 'id', 'Employee ID'),
        ref('IBAN', 'IBAN', 'id', 'IBAN'),
        { id: 'name', name: 'Name', type: 'text', use: true, columnA: 'Employee Name', columnB: 'Name', identifying: false, textRule: 'normalised' }
      ]
    })
  },
  {
    name: 'General - Intercompany',
    key: 'intercompany',
    fileA: 'general/Intercompany_EntityA_Dubai.xlsx',
    fileB: 'general/Intercompany_EntityB_AbuDhabi.xlsx',
    cfg: sampleConfig({
      moduleId: 'general',
      sign: 'same',
      sideAName: 'Desert Pearl Trading LLC (Dubai)',
      sideBName: 'Desert Pearl Industries LLC (Abu Dhabi)',
      keys: [ref('IC Reference', 'IC Ref', 'id', 'IC Reference'), date('Posting Date', 'Posting Date', 3), amount],
      amountA: { kind: 'signed', column: 'Amount (AED)' },
      amountB: { kind: 'signed', column: 'Amount (AED)' }
    })
  }
]

const loaded = new Map<string, { a: ParsedTable; b: ParsedTable; r: ReconResult }>()
function run(c: Case): { a: ParsedTable; b: ParsedTable; r: ReconResult } {
  const hit = loaded.get(c.key)
  if (hit) return hit
  const a = loadSample(c.fileA)
  const b = loadSample(c.fileB)
  const r = reconcile(a, b, c.cfg)
  const v = { a, b, r }
  loaded.set(c.key, v)
  return v
}

describe('sample data: tier counts match expected-results.json', () => {
  for (const c of cases) {
    it(`${c.name}`, () => {
      const { r } = run(c)
      const want = exp[c.key].tiers
      const got = tierCounts(r)
      const compare: Record<string, number> = {}
      for (const k of Object.keys(want)) compare[k] = got[k]
      expect(compare).toEqual(want)
    })
  }
})

describe('sample data: statements tie to 0.00', () => {
  for (const c of cases) {
    it(`${c.name}`, () => {
      const { a, b, r } = run(c)
      const st = buildStatement(r, metaFor(a, b))
      expect(st.unexplainedDifference).toBe(0)
      if (c.key === 'hr') {
        expect(st.kind).toBe('record-count')
        const want = (exp.hr as unknown as { countStatement: Array<{ count: number }> }).countStatement.map((l) => l.count)
        expect(st.lines.map((l) => l.value)).toEqual(want)
      }
    })
  }
})

describe('sample data: planted scenarios', () => {
  const bank = cases[0]
  it('bank: three identical 1,000.00 payments form one Doubtful "Multiple identical candidates" group (3 + 3 lines)', () => {
    const { r } = run(bank)
    const dup = r.pairs.filter((p) => p.flags.includes('multiple-candidates'))
    expect(dup).toHaveLength(1)
    expect(dup[0].tier).toBe('doubtful')
    expect(dup[0].aIds).toHaveLength(3)
    expect(dup[0].bIds).toHaveLength(3)
    expect(dup[0].reason.startsWith('Multiple identical candidates')).toBe(true)
    expect(dup[0].candidateIds).toHaveLength(6)
  })

  it('bank: transposition and bank-charge pairs are flagged with plain-English reasons', () => {
    const { r } = run(bank)
    const trans = r.pairs.find((p) => p.flags.includes('transposition'))
    expect(trans?.tier).toBe('doubtful')
    expect(trans?.reason).toBe('Reference and date agree; amount differs by 90.00 (possible transposition 8,450.00 vs 8,540.00)')
    const charge = r.pairs.find((p) => p.flags.includes('bank-charge'))
    expect(charge?.amountDifference).toBe(25)
    expect(charge?.reason).toContain('possible bank charge')
  })

  it('bank: date shift beyond tolerance gives "Reference and amount agree; date differs by N days"', () => {
    const { r } = run(bank)
    const reasons = r.pairs.filter((p) => p.tier === 'doubtful').map((p) => p.reason)
    expect(reasons).toContain('Reference and amount agree; date differs by 5 days')
    expect(reasons).toContain('Reference and amount agree; date differs by 4 days')
    expect(reasons.filter((x) => x === 'Amount and date agree; reference missing on bank side')).toHaveLength(4)
  })

  it('bank: Smart Recon sum matching finds the 1:3 split, the 2:1 combination and the six card batches', () => {
    const { r } = run(bank)
    const { suggestions, capped } = findGroupMatches(r)
    expect(capped).toBe(false)
    const amountsOf = (ids: string[]): number[] => ids.map((id) => [...r.linesA, ...r.linesB].find((l) => l.id === id)?.amount ?? 0).map((x) => Math.abs(x)).sort((p, q) => p - q)
    const shapes = suggestions.map((s) => ({ a: amountsOf(s.aIds), b: amountsOf(s.bIds) }))
    expect(shapes).toContainEqual({ a: [36750], b: [12250, 12250, 12250] })
    expect(shapes).toContainEqual({ a: [6187.9, 9412.35], b: [15600.25] })
    const batches = (exp.bank as unknown as { planted: { posBatches: Array<{ parts: number[]; total: number }> } }).planted.posBatches
    for (const p of batches) {
      expect(shapes).toContainEqual({ a: p.parts.map((x) => x / 100).sort((x, y) => x - y), b: [p.total / 100] })
    }
    expect(suggestions).toHaveLength(8)
    expect(suggestions.reduce((s, x) => s + x.aIds.length, 0)).toBe(21)
    expect(suggestions.reduce((s, x) => s + x.bIds.length, 0)).toBe(10)
  })

  it('bank: partial reference finds the three references written differently (Doubtful lines included)', () => {
    const { r } = run(bank)
    const sug = findPartialReferenceMatches(r, { includeDoubtful: true })
    for (const token of ['FT2609ABC', 'FT2609KLM', 'FT2609XRT']) {
      expect(sug.some((s) => s.reason.includes(token))).toBe(true)
    }
  })

  it('bank: after approving the Smart Recon groups the statement matches the README line by line', () => {
    const { a, b, r } = run(bank)
    let s = createSession(r, metaFor(a, b))
    s = addSuggestions(s, findGroupMatches(r).suggestions)
    for (const sug of s.suggestions) s = approveSuggestion(s, sug.id, 'Sana Fathima')
    expect(s.result.unmatchedA).toHaveLength(8)
    expect(s.result.unmatchedB).toHaveLength(9)
    const st = buildStatement(s.result, s.meta)
    const values = st.lines.map((l) => l.value)
    const want = exp.bank.statement!.map((l) => l.amount)
    // README: balance, unpresented, uncredited, bank credits, bank debits, +25 charge, -90 transposition, adjusted, GL, unexplained
    expect(values).toEqual(want)
  })

  it('AR / AP / intercompany statements carry the README reconciling lines', () => {
    for (const k of [1, 2, 4]) {
      const c = cases[k]
      const { a, b, r } = run(c)
      const st = buildStatement(r, metaFor(a, b))
      const items = st.lines.filter((l) => /^(Less|Add)/.test(l.label) && l.value !== 0).map((l) => l.value).sort((x, y) => x - y)
      const want = exp[c.key].statement!.filter((l) => /^(Less|Add)/.test(l.line)).map((l) => l.amount).sort((x, y) => x - y)
      expect(items).toEqual(want)
    }
  })

  it('AP: duplicate SOA invoice is one Doubtful group of 1 line ours and 2 lines theirs', () => {
    const { r } = run(cases[2])
    const dup = r.pairs.filter((p) => p.flags.includes('multiple-candidates'))
    expect(dup).toHaveLength(1)
    expect([dup[0].aIds.length, dup[0].bIds.length]).toEqual([1, 2])
    expect(r.pairs.find((p) => p.flags.includes('rounding'))?.amountDifference).toBe(0.5)
  })

  it('HR: name variants and IBAN mismatch reasons', () => {
    const { r } = run(cases[3])
    const reasons = r.pairs.filter((p) => p.tier === 'doubtful').map((p) => p.reason)
    expect(reasons.filter((x) => x.startsWith('Employee ID and IBAN agree; name differs'))).toHaveLength(6)
    expect(reasons.filter((x) => x.startsWith('Employee ID and name agree; IBAN differs'))).toHaveLength(1)
  })
})

describe('sample data: suggestKeys proposes the recommended mapping', () => {
  it('bank', () => {
    const { a, b } = run(cases[0])
    const s = suggestKeys('bank', a, b)
    const byId = Object.fromEntries(s.keys.map((k) => [k.id, k]))
    expect([byId.reference.columnA, byId.reference.columnB]).toEqual(['Reference No', 'Cheque No'])
    expect([byId.date.columnA, byId.date.columnB]).toEqual(['Txn Date', 'Posting Date'])
    expect(s.amountA).toEqual({ kind: 'debit-credit', debit: 'Debit', credit: 'Credit' })
    expect(s.amountB).toEqual({ kind: 'debit-credit', debit: 'Debit', credit: 'Credit' })
    expect(s.partyColumnB).toBe('Party')
  })
  it('AR and AP', () => {
    const ar = run(cases[1])
    const sAr = suggestKeys('ar', ar.a, ar.b)
    expect(sAr.keys.find((k) => k.id === 'reference')).toMatchObject({ columnA: 'Invoice / Ref No', columnB: 'Supplier Inv / Ref' })
    const ap = run(cases[2])
    const sAp = suggestKeys('ap', ap.a, ap.b)
    expect(sAp.keys.find((k) => k.id === 'reference')).toMatchObject({ columnA: 'Supplier Inv / Ref', columnB: 'Invoice / Doc No' })
  })
  it('General HR: Emp ID ↔ Employee No, IBAN ↔ IBAN, name; no amount', () => {
    const { a, b } = run(cases[3])
    const s = suggestKeys('general', a, b)
    const used = s.keys.filter((k) => k.use).map((k) => [k.columnA, k.columnB, k.type])
    expect(used).toContainEqual(['Emp ID', 'Employee No', 'id'])
    expect(used).toContainEqual(['IBAN', 'IBAN', 'id'])
    expect(used.some(([x, y]) => x === 'Employee Name' && y === 'Name')).toBe(true)
    expect(s.keys.some((k) => k.use && k.type === 'amount')).toBe(false)
    // The single payroll Pay Date also appears among join dates; it must not be ticked as a date key.
    expect(s.keys.some((k) => k.use && k.type === 'date')).toBe(false)
  })
  it('General intercompany: IC Reference ↔ IC Ref, Posting Date, Amount (AED)', () => {
    const { a, b } = run(cases[4])
    const s = suggestKeys('general', a, b)
    const used = s.keys.filter((k) => k.use).map((k) => [k.columnA, k.columnB, k.type])
    expect(used).toContainEqual(['IC Reference', 'IC Ref', 'id'])
    expect(used).toContainEqual(['Posting Date', 'Posting Date', 'date'])
    expect(used).toContainEqual(['Amount (AED)', 'Amount (AED)', 'amount'])
  })
})
