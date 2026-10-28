import { describe, expect, it } from 'vitest'
import type { ParsedTable, ReconConfig, ReconSession } from '@shared/contracts'
import { initialState, reachableSteps, wizardReducer } from '@/features/wizard/reducer'
import type { LoadedFile, WizardState } from '@/features/wizard/types'

function table(name: string): ParsedTable {
  return { fileName: name, sheetName: 'Sheet1', headerRowIndex: 0, columns: ['Ref', 'Amount'], rows: [], excluded: [], openingBalance: null, closingBalance: null }
}
function file(name: string): LoadedFile {
  return { fileName: name, size: 10, workbook: { fileName: name, sheets: [] }, sheetIndex: 0, detectedHeaderRow: 0, table: table(name) }
}
const cfg: ReconConfig = {
  moduleId: 'general',
  sideAName: 'File A',
  sideBName: 'File B',
  keys: [{ id: 'k', name: 'Ref', type: 'id', use: true, columnA: 'Ref', columnB: 'Ref', identifying: true, textRule: 'normalised' }],
  sign: 'same',
  referencePrefixes: [],
  currency: 'AED'
}
function session(over: Partial<ReconSession> = {}): ReconSession {
  return {
    id: 's1',
    createdAt: '2026-10-01T00:00:00.000Z',
    updatedAt: '2026-10-01T00:00:00.000Z',
    meta: {
      accountLabel: 'Payroll',
      period: 'Sep 2026',
      fileA: { name: 'a.xlsx', sheet: 'S', rows: 0 },
      fileB: { name: 'b.xlsx', sheet: 'S', rows: 0 },
      preparer: 'Sana',
      currency: 'AED',
      balances: { openingA: null, closingA: null, openingB: null, closingB: null }
    },
    result: {
      config: { ...cfg, sideAName: 'HR master', sideBName: 'WPS' },
      linesA: [],
      linesB: [],
      pairs: [],
      unmatchedA: [],
      unmatchedB: [],
      stats: { linesA: 0, linesB: 0, matched: 0, doubtful: 0, likely: 0, unmatchedA: 0, unmatchedB: 0, matchedAmount: 0 },
      durationMs: 1
    },
    suggestions: [],
    audit: [],
    finalised: null,
    ...over
  }
}
const both = (s: WizardState): WizardState =>
  wizardReducer(wizardReducer(s, { type: 'loadFile', side: 'A', file: file('a.xlsx') }), { type: 'loadFile', side: 'B', file: file('b.xlsx') })

describe('wizard reducer', () => {
  it('starts on Upload with the module side names', () => {
    const s = initialState('bank')
    expect(s.step).toBe(0)
    expect(s.sideAName).toBe('Bank statement')
    expect(s.sideBName).toBe('General ledger extract')
    expect([...reachableSteps(s)]).toEqual([0])
  })

  it('opens Map & rules only when both files are loaded', () => {
    let s = initialState('bank')
    s = wizardReducer(s, { type: 'go', step: 1 })
    expect(s.step).toBe(0)
    s = both(s)
    s = wizardReducer(s, { type: 'go', step: 1 })
    expect(s.step).toBe(1)
    expect(wizardReducer(s, { type: 'go', step: 4 }).step).toBe(1)
  })

  it('a new file clears the mapping and any result', () => {
    let s = both(initialState('general'))
    s = wizardReducer(s, { type: 'setConfig', config: cfg, source: { kind: 'suggested' } })
    s = wizardReducer(s, { type: 'session', session: session() })
    expect(reachableSteps(s).has(4)).toBe(true)
    s = wizardReducer(s, { type: 'loadFile', side: 'B', file: file('c.xlsx') })
    expect(s.config).toBeNull()
    expect(s.session).toBeNull()
    expect(reachableSteps(s).has(4)).toBe(false)
  })

  it('clearing a file returns to Upload', () => {
    let s = wizardReducer(both(initialState('ar')), { type: 'go', step: 1 })
    s = wizardReducer(s, { type: 'clearFile', side: 'A' })
    expect(s.step).toBe(0)
    expect(s.files.A).toBeNull()
  })

  it('Reconcile can be entered from Map once there is a config', () => {
    let s = wizardReducer(both(initialState('general')), { type: 'go', step: 2 })
    expect(s.step).toBe(0)
    s = wizardReducer(s, { type: 'setConfig', config: cfg, source: { kind: 'suggested' } })
    expect(wizardReducer(s, { type: 'go', step: 2 }).step).toBe(2)
  })

  it('General side names flow into the config', () => {
    let s = wizardReducer(both(initialState('general')), { type: 'setConfig', config: cfg, source: { kind: 'suggested' } })
    s = wizardReducer(s, { type: 'sideName', side: 'A', name: 'HR employee master' })
    expect(s.sideAName).toBe('HR employee master')
    expect(s.config?.sideAName).toBe('HR employee master')
  })

  it('templates bring their side names for General; fixed modules keep their labels', () => {
    const tpl = { ...cfg, sideAName: 'Payroll', sideBName: 'Bank list' }
    const g = wizardReducer(both(initialState('general')), { type: 'setConfig', config: tpl, source: { kind: 'template', name: 'T' } })
    expect([g.sideAName, g.sideBName]).toEqual(['Payroll', 'Bank list'])
    const b = wizardReducer(both(initialState('bank')), { type: 'setConfig', config: { ...tpl, moduleId: 'bank' }, source: { kind: 'mapping', name: 'M' } })
    expect(b.sideAName).toBe('Bank statement')
    expect(b.config?.sideAName).toBe('Bank statement')
  })

  it('automatic account and period guesses stop once the user edits the field', () => {
    let s = wizardReducer(initialState('bank'), { type: 'autoMeta', accountLabel: 'ENBD Current', period: 'Sep 2026' })
    expect(s.accountLabel).toBe('ENBD Current')
    s = wizardReducer(s, { type: 'meta', accountLabel: 'ENBD 1012' })
    s = wizardReducer(s, { type: 'autoMeta', accountLabel: 'Other', period: 'Oct 2026' })
    expect(s.accountLabel).toBe('ENBD 1012')
    expect(s.period).toBe('Oct 2026')
  })

  it('resume opens the results from history, with Upload and Map unavailable', () => {
    const s = wizardReducer(initialState('general'), { type: 'resume', session: session({ meta: { ...session().meta, mappingName: 'Payroll map' } }) })
    expect(s.step).toBe(4)
    expect(s.origin).toBe('resumed')
    expect(s.sideAName).toBe('HR master')
    expect(s.configSource).toEqual({ kind: 'mapping', name: 'Payroll map' })
    const r = reachableSteps(s)
    expect(r.has(0)).toBe(false)
    expect(r.has(1)).toBe(false)
    expect(r.has(3)).toBe(true)
    expect(wizardReducer(s, { type: 'go', step: 0 }).step).toBe(4)
  })

  it('reset returns to a clean state for the same module', () => {
    const s = wizardReducer(both(initialState('ap')), { type: 'reset' })
    expect(s).toEqual(initialState('ap'))
  })
})
