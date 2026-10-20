import 'fake-indexeddb/auto'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import type { ParsedTable, ReconConfig, ReconSession } from '@shared/contracts'
import { closeDb, getDraft, getSources, listDrafts, saveSession, type DraftRecord, type SessionSummary } from '@/lib/db'
import { closeDraftSaves, flushDraftSaves, hasPendingDraftSaves, persistDraft, removeDraftLater, reopenDraftSaves } from '@/lib/draftSaves'
import { draftFromState, sourcesFromState, stateFromDraft } from '@/features/wizard/draftState'
import {
  countByModule,
  draftStage,
  itemFromState,
  reconItems,
  reconLink,
  sessionStage,
  unfinishedItems,
  withCurrent
} from '@/features/wizard/inProgress'
import {
  deleteRecon,
  forgetRecon,
  MAX_OPEN_IN_MEMORY,
  openReconIds,
  recallWizard,
  rememberWizard,
  resetOpenRecons,
  setShownRecon,
  shownRecon
} from '@/features/wizard/openRecons'
import { initialState, reachableSteps, wizardReducer } from '@/features/wizard/reducer'
import type { LoadedFile, WizardState } from '@/features/wizard/types'
import { summariseForHistory } from '@engine/index'

function table(name: string, rows = 2): ParsedTable {
  return {
    fileName: name,
    sheetName: 'Sheet1',
    headerRowIndex: 0,
    columns: ['Ref', 'Amount'],
    rows: Array.from({ length: rows }, (_, i) => ({ id: `r${i + 2}`, sourceRow: i + 2, values: { Ref: `R${i}`, Amount: i } })),
    excluded: [],
    openingBalance: null,
    closingBalance: null
  }
}
function file(name: string, rows = 2): LoadedFile {
  return { fileName: name, size: 10, workbook: { fileName: name, sheets: [{ name: 'Sheet1', rows: [['Ref', 'Amount']] }] }, sheetIndex: 0, detectedHeaderRow: 0, table: table(name, rows) }
}
const cfg: ReconConfig = {
  moduleId: 'bank',
  sideAName: 'Bank statement',
  sideBName: 'General ledger',
  keys: [{ id: 'k', name: 'Ref', type: 'id', use: true, columnA: 'Ref', columnB: 'Ref', identifying: true, textRule: 'normalised' }],
  sign: 'inverse',
  referencePrefixes: [],
  currency: 'AED'
}
function session(id: string, over: Partial<ReconSession> = {}): ReconSession {
  return {
    id,
    createdAt: '2026-10-01T00:00:00.000Z',
    updatedAt: '2026-10-01T00:00:00.000Z',
    meta: {
      accountLabel: 'ENBD Current',
      period: 'Sep 2026',
      fileA: { name: 'a.xlsx', sheet: 'Sheet1', rows: 2 },
      fileB: { name: 'b.xlsx', sheet: 'Sheet1', rows: 2 },
      preparer: 'Sana',
      currency: 'AED',
      balances: { openingA: null, closingA: null, openingB: null, closingB: null }
    },
    result: {
      config: cfg,
      linesA: [],
      linesB: [],
      pairs: [],
      unmatchedA: [],
      unmatchedB: [],
      stats: { linesA: 2, linesB: 2, matched: 0, doubtful: 0, likely: 0, unmatchedA: 0, unmatchedB: 0, matchedAmount: 0 },
      durationMs: 1
    },
    suggestions: [],
    audit: [],
    finalised: null,
    ...over
  }
}

/** A Bank wizard with both files read and a configuration, at Map & rules. */
function atMap(id: string, account = 'ENBD Current'): WizardState {
  let s = initialState('bank', id)
  s = wizardReducer(s, { type: 'loadFile', side: 'A', file: file(`${id}-a.xlsx`) })
  s = wizardReducer(s, { type: 'loadFile', side: 'B', file: file(`${id}-b.xlsx`) })
  s = wizardReducer(s, { type: 'setConfig', config: cfg, source: { kind: 'suggested' } })
  s = wizardReducer(s, { type: 'meta', accountLabel: account, period: 'Sep 2026' })
  return wizardReducer(s, { type: 'go', step: 1 })
}

function summary(id: string, over: Partial<SessionSummary> = {}): SessionSummary {
  return {
    id,
    moduleId: 'bank',
    accountLabel: 'ENBD Current',
    period: 'Sep 2026',
    sideAName: 'Bank statement',
    sideBName: 'General ledger',
    fileA: 'a.xlsx',
    fileB: 'b.xlsx',
    preparer: 'Sana',
    createdAt: '2026-10-01T10:00:00Z',
    updatedAt: '2026-10-01T10:00:00Z',
    finalised: null,
    open: { doubtful: 0, likely: 0, suggestions: 0, unmatched: 0 },
    stats: { linesA: 2, linesB: 2, matched: 2, doubtful: 0, likely: 0, unmatchedA: 0, unmatchedB: 0, matchedAmount: 0 },
    ...over
  }
}

beforeEach(async () => {
  await closeDb()
  globalThis.indexedDB = new IDBFactory()
  resetOpenRecons()
})

afterEach(async () => {
  await flushDraftSaves()
  await closeDb()
})

describe('reconciliation id in the wizard state', () => {
  it('starts with the given id and keeps it while the draft is edited', () => {
    const s = atMap('d1')
    expect(s.reconId).toBe('d1')
    expect(wizardReducer(s, { type: 'loadFile', side: 'A', file: file('other.xlsx'), freshId: 'NEW' }).reconId).toBe('d1')
  })

  it('takes the session id once Reconcile has run', () => {
    const s = wizardReducer(atMap('d1'), { type: 'session', session: session('d1') })
    expect(s.reconId).toBe('d1')
    expect(wizardReducer(atMap('d1'), { type: 'session', session: session('s9') }).reconId).toBe('s9')
  })

  it('continues under a new id when the files of a reconciliation that already ran change', () => {
    const ran = wizardReducer(atMap('d1'), { type: 'session', session: session('d1') })
    const replaced = wizardReducer(ran, { type: 'loadFile', side: 'B', file: file('new.xlsx'), freshId: 'fresh' })
    expect(replaced.reconId).toBe('fresh')
    expect(replaced.session).toBeNull()
    expect(wizardReducer(ran, { type: 'clearFile', side: 'A', freshId: 'fresh2' }).reconId).toBe('fresh2')
  })

  it('reopens a saved session with its files as fully editable, and without them (or finalised) read-only', () => {
    const files = { A: file('a.xlsx'), B: file('b.xlsx') }
    const editable = wizardReducer(initialState('bank'), { type: 'resume', session: session('s1'), files })
    expect(editable.origin).toBe('new')
    expect(editable.reconId).toBe('s1')
    expect(editable.files.A?.fileName).toBe('a.xlsx')
    expect([...reachableSteps(editable)].sort()).toEqual([0, 1, 2, 3, 4])

    const old = wizardReducer(initialState('bank'), { type: 'resume', session: session('s1') })
    expect(old.origin).toBe('resumed')
    expect(old.files).toEqual({ A: null, B: null })

    const signedOff = wizardReducer(initialState('bank'), { type: 'resume', session: session('s1', { finalised: { by: 'Sana', at: '2026-10-02T00:00:00Z' } }), files })
    expect(signedOff.origin).toBe('resumed')
    expect(signedOff.files.A).toBeNull()
  })

  it('restores a whole saved state of the same module only', () => {
    const saved = atMap('d1')
    expect(wizardReducer(initialState('bank', 'x'), { type: 'restore', state: saved })).toBe(saved)
    const ar = initialState('ar', 'y')
    expect(wizardReducer(ar, { type: 'restore', state: saved })).toBe(ar)
  })

  it('keeps the same state when the automatic guesses do not change anything', () => {
    const s = atMap('d1')
    expect(wizardReducer(s, { type: 'autoMeta', accountLabel: 'x', period: 'y' })).toBe(s)
  })
})

describe('draft state', () => {
  it('turns a wizard at Map & rules into a draft and back', () => {
    const s = atMap('d1', 'Typed account')
    const d = draftFromState(s, '2026-10-05T10:00:00Z') as DraftRecord
    expect(d).toMatchObject({ id: 'd1', moduleId: 'bank', step: 1, accountLabel: 'Typed account', accountTouched: true, updatedAt: '2026-10-05T10:00:00Z' })
    expect(d.files.A).toEqual({ fileName: 'd1-a.xlsx', sheetName: 'Sheet1', rows: 2 })
    const back = stateFromDraft(d, sourcesFromState(s))
    expect(back).toMatchObject({ reconId: 'd1', step: 1, origin: 'new', session: null, accountLabel: 'Typed account', config: s.config })
    expect(back.files.A).toBe(s.files.A)
  })

  it('keeps nothing as a draft without files, after a run, or for a read-only session', () => {
    expect(draftFromState(initialState('bank', 'd1'), 'now')).toBeNull()
    expect(draftFromState(wizardReducer(atMap('d1'), { type: 'session', session: session('d1') }), 'now')).toBeNull()
    expect(draftFromState({ ...atMap('d1'), reconId: '' }, 'now')).toBeNull()
  })

  it('resumes at Map & rules when saved while a run was starting, and at Upload when a file is missing', () => {
    const starting = wizardReducer(atMap('d1'), { type: 'go', step: 2 })
    expect(draftFromState(starting, 'now')?.step).toBe(1)
    const d = draftFromState(atMap('d1'), 'now') as DraftRecord
    const oneFile = stateFromDraft(d, { A: file('a.xlsx'), B: null })
    expect(oneFile.step).toBe(0)
    expect(oneFile.config).toBeNull()
  })
})

describe('several reconciliations open at once', () => {
  it('keeps each reconciliation and switches between them without losing any', () => {
    const a = atMap('A', 'ENBD Current')
    rememberWizard(a)
    setShownRecon('bank', 'A')
    // New reconciliation: B is shown, A stays as it was.
    const b = wizardReducer(atMap('B', 'ADCB Payroll'), { type: 'session', session: session('B') })
    rememberWizard(b)
    setShownRecon('bank', 'B')
    expect(shownRecon('bank')).toBe('B')
    expect(recallWizard('A')).toBe(a)
    expect(recallWizard('A')?.step).toBe(1)
    expect(recallWizard('B')?.session?.id).toBe('B')
    // Another module has its own.
    rememberWizard(atMap('C'))
    setShownRecon('ar', 'C')
    expect(shownRecon('bank')).toBe('B')
    // Switch back to A.
    setShownRecon('bank', 'A')
    expect(recallWizard(shownRecon('bank') as string)?.accountLabel).toBe('ENBD Current')
  })

  it('drops the least recently used ones from memory first, never one that is on screen', () => {
    rememberWizard(atMap('shown'))
    setShownRecon('bank', 'shown')
    for (let i = 0; i < MAX_OPEN_IN_MEMORY + 3; i++) rememberWizard(atMap(`r${i}`))
    expect(openReconIds()).toHaveLength(MAX_OPEN_IN_MEMORY)
    expect(recallWizard('shown')).toBeDefined()
    expect(recallWizard('r0')).toBeUndefined()
    expect(recallWizard(`r${MAX_OPEN_IN_MEMORY + 2}`)).toBeDefined()
  })

  it('forgets a deleted reconciliation, including where a module showed it', () => {
    rememberWizard(atMap('A'))
    setShownRecon('bank', 'A')
    forgetRecon('A')
    expect(recallWizard('A')).toBeUndefined()
    expect(shownRecon('bank')).toBeUndefined()
  })
})

describe('in progress lists', () => {
  const d1: DraftRecord = draftFromState(atMap('d1'), '2026-10-03T10:00:00Z') as DraftRecord
  const d0: DraftRecord = { ...d1, id: 'd0', moduleId: 'ar', step: 0, files: { A: d1.files.A, B: null }, updatedAt: '2026-10-01T09:00:00Z' }

  it('describes where each one stands in plain English', () => {
    expect(draftStage(d1)).toBe('Map & rules')
    expect(draftStage(d0)).toBe('Upload: 1 of 2 files read')
    expect(sessionStage(summary('s', { open: { doubtful: 16, likely: 0, suggestions: 3, unmatched: 48 } }))).toBe('Review: 16 doubtful open')
    expect(sessionStage(summary('s', { open: { doubtful: 2, likely: 1, suggestions: 0, unmatched: 0 } }))).toBe('Review: 2 doubtful, 1 likely open')
    expect(sessionStage(summary('s', { open: { doubtful: 0, likely: 0, suggestions: 1, unmatched: 0 } }))).toBe('Review: 1 suggestion to check')
    expect(sessionStage(summary('s', { open: { doubtful: 0, likely: 0, suggestions: 0, unmatched: 5 } }))).toBe('Review: ready to sign off (5 unmatched)')
    expect(sessionStage(summary('s', { finalised: { by: 'Sana', at: 'x' } }))).toBe('Finalised')
  })

  it('merges drafts and sessions newest first, with clear statuses, and counts the unfinished per module', () => {
    const items = reconItems(
      [d1, d0],
      [summary('s1', { updatedAt: '2026-10-02T10:00:00Z' }), summary('s2', { updatedAt: '2026-10-04T10:00:00Z', finalised: { by: 'Sana', at: 'x' } })]
    )
    expect(items.map((i) => [i.id, i.status])).toEqual([
      ['s2', 'finalised'],
      ['d1', 'draft'],
      ['s1', 'review'],
      ['d0', 'draft']
    ])
    expect(unfinishedItems(items).map((i) => i.id)).toEqual(['d1', 's1', 'd0'])
    expect(unfinishedItems(items, 'bank').map((i) => i.id)).toEqual(['d1', 's1'])
    expect(countByModule(items)).toEqual({ bank: 2, ar: 1 })
    expect(reconLink(items[1])).toBe('/module/bank?draft=d1')
    expect(reconLink(items[2])).toBe('/module/bank?session=s1')
  })

  it('lists a session rather than a leftover draft with the same id', () => {
    const items = reconItems([{ ...d1, id: 'same' }], [summary('same')])
    expect(items.map((i) => i.kind)).toEqual(['session'])
  })

  it('puts the reconciliation on screen first, with its newest state', () => {
    const stored = reconItems([d1], [summary('s1')])
    const current = itemFromState(wizardReducer(atMap('d1', 'Renamed'), { type: 'go', step: 0 }), '2026-10-09T00:00:00Z')
    const list = withCurrent(stored, current, 'd1')
    expect(list.map((i) => [i.id, i.accountLabel, i.stage])).toEqual([
      ['d1', 'Renamed', 'Upload: both files read'],
      ['s1', 'ENBD Current', 'Review: ready to sign off']
    ])
    // A wizard with nothing to keep yet is not listed, and its old entry is hidden.
    expect(withCurrent(stored, itemFromState(initialState('bank', 'd1'), 'now'), 'd1').map((i) => i.id)).toEqual(['s1'])
  })
})

describe('draft saves', () => {
  it('combines quick changes into one save and keeps the newest', async () => {
    const s = atMap('d1')
    const first = draftFromState(s, '2026-10-01T10:00:00Z') as DraftRecord
    const second = { ...first, accountLabel: 'Second', updatedAt: '2026-10-01T10:00:01Z' }
    const p1 = persistDraft(first, sourcesFromState(s), { delayMs: 20 })
    const p2 = persistDraft(second, sourcesFromState(s), { delayMs: 20 })
    expect(hasPendingDraftSaves()).toBe(true)
    await Promise.all([p1, p2])
    const back = await getDraft('d1')
    expect(back?.draft.accountLabel).toBe('Second')
    expect(back?.sources.B?.fileName).toBe('d1-b.xlsx')
    expect(hasPendingDraftSaves()).toBe(false)
  })

  it('removes the draft after both files are cleared', async () => {
    const s = atMap('d1')
    await persistDraft(draftFromState(s, 'now') as DraftRecord, sourcesFromState(s), { delayMs: 0 })
    await removeDraftLater('d1')
    expect(await getDraft('d1')).toBeUndefined()
  })

  it('stops saving a draft once it is closed (Reconcile ran or it was deleted) until reopened', async () => {
    const s = atMap('d1')
    const d = draftFromState(s, 'now') as DraftRecord
    const queued = persistDraft(d, sourcesFromState(s), { delayMs: 30 })
    await closeDraftSaves('d1')
    await queued
    await persistDraft(d, sourcesFromState(s))
    expect(await listDrafts()).toEqual([])
    reopenDraftSaves('d1')
    await persistDraft(d, sourcesFromState(s), { delayMs: 0 })
    expect((await listDrafts()).map((x) => x.id)).toEqual(['d1'])
  })

  it('deleting cancels a pending save so the draft cannot come back, and removes its files', async () => {
    const s = atMap('gone')
    rememberWizard(s)
    void persistDraft(draftFromState(s, 'now') as DraftRecord, sourcesFromState(s), { delayMs: 30 })
    await deleteRecon('gone', 'draft')
    await flushDraftSaves()
    await new Promise((r) => setTimeout(r, 50))
    expect(await getDraft('gone')).toBeUndefined()
    expect(await getSources('gone')).toBeUndefined()
    expect(recallWizard('gone')).toBeUndefined()
  })

  it('deleting a session also removes its source files', async () => {
    const s = atMap('s1')
    const ses = session('s1')
    await saveSession(ses, summariseForHistory(ses), { sources: sourcesFromState(s) })
    expect(await getSources('s1')).toBeDefined()
    await deleteRecon('s1', 'session')
    expect(await getSources('s1')).toBeUndefined()
  })
})
