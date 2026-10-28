import 'fake-indexeddb/auto'
import { IDBFactory } from 'fake-indexeddb'
import { openDB } from 'idb'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import type { EngineLine, ParsedTable, ReconSession, SavedMapping, ToolRecipe } from '../../src/shared/contracts'
import type { HistoryEntry } from '../../src/shared/kpis'
import {
  closeDb,
  DatabaseError,
  DB_NAME,
  DEFAULT_SETTINGS,
  deleteDraft,
  deleteMapping,
  deleteRecipe,
  deleteSession,
  deleteTemplate,
  findMappingByHeaders,
  friendlyDbError,
  getDraft,
  getSession,
  getSources,
  getSettings,
  listDrafts,
  listHistory,
  listMappings,
  listRecipes,
  listSessionSummaries,
  listSessions,
  listSourceIds,
  listTemplates,
  saveDraft,
  saveMapping,
  saveRecipe,
  saveSession,
  saveSettings,
  saveTemplate,
  sessionExists,
  type DraftRecord,
  type SourceFile,
  type SourceFiles
} from '../../src/renderer/src/lib/db'

function history(id: string, finishedAt: string): HistoryEntry {
  return {
    id,
    moduleId: 'bank',
    accountLabel: 'ENBD Current A/c',
    finishedAt,
    totalLines: 100,
    autoMatchedLines: 90,
    openItemCount: 10,
    openItemAmount: 1234.5,
    oldestOpenItemDate: '2026-09-01'
  }
}

function session(id: string, updatedAt: string): ReconSession {
  return {
    id,
    createdAt: updatedAt,
    updatedAt,
    meta: {
      accountLabel: 'ENBD Current A/c',
      period: 'Sep 2026',
      fileA: { name: 'a.xlsx', sheet: 'Sheet1', rows: 10 },
      fileB: { name: 'b.xlsx', sheet: 'Sheet1', rows: 12 },
      preparer: 'Sana Fathima',
      currency: 'AED',
      balances: { openingA: null, closingA: null, openingB: null, closingB: null }
    },
    result: {
      config: { moduleId: 'bank', sideAName: 'Bank', sideBName: 'GL', keys: [], sign: 'inverse', referencePrefixes: [], currency: 'AED' },
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
    finalised: null
  }
}

function mapping(id: string, headersA: string[], headersB: string[], updatedAt = '2026-09-01T10:00:00Z'): SavedMapping {
  return {
    id,
    name: `Mapping ${id}`,
    moduleId: 'bank',
    headersA,
    headersB,
    config: { moduleId: 'bank', sideAName: 'Bank', sideBName: 'GL', keys: [], sign: 'inverse', referencePrefixes: [], currency: 'AED' },
    createdAt: updatedAt,
    updatedAt
  }
}

beforeEach(async () => {
  await closeDb()
  // A brand-new, empty IndexedDB for every test.
  globalThis.indexedDB = new IDBFactory()
})

afterEach(async () => {
  await closeDb()
})

describe('settings', () => {
  it('returns defaults when nothing is saved', async () => {
    expect(await getSettings()).toEqual(DEFAULT_SETTINGS)
    expect(DEFAULT_SETTINGS.currency).toBe('AED')
    expect(DEFAULT_SETTINGS.aiModel).toBe('claude-sonnet-5-5')
  })

  it('merges partial updates', async () => {
    await saveSettings({ preparerName: 'Sana Fathima' })
    const s = await saveSettings({ currency: 'USD', maskPartiesDefault: true })
    expect(s).toEqual({ ...DEFAULT_SETTINGS, preparerName: 'Sana Fathima', currency: 'USD', maskPartiesDefault: true })
    expect(await getSettings()).toEqual(s)
  })
})

describe('sessions and history', () => {
  it('saves both records together and lists newest first', async () => {
    await saveSession(session('s1', '2026-09-01T10:00:00Z'), history('s1', '2026-09-01T10:00:00Z'))
    await saveSession(session('s2', '2026-09-05T10:00:00Z'), history('s2', '2026-09-05T10:00:00Z'))
    expect((await listSessions()).map((s) => s.id)).toEqual(['s2', 's1'])
    expect((await listHistory()).map((h) => h.id)).toEqual(['s2', 's1'])
    expect((await getSession('s1'))?.meta.preparer).toBe('Sana Fathima')
  })

  it('overwrites on save and deletes both on delete', async () => {
    await saveSession(session('s1', '2026-09-01T10:00:00Z'), history('s1', '2026-09-01T10:00:00Z'))
    const finalised = { ...session('s1', '2026-09-02T10:00:00Z'), finalised: { by: 'Sana', at: '2026-09-02T10:00:00Z' } }
    await saveSession(finalised, { ...history('s1', '2026-09-02T10:00:00Z'), openItemCount: 0 })
    expect(await listSessions()).toHaveLength(1)
    expect((await getSession('s1'))?.finalised?.by).toBe('Sana')
    expect((await listHistory())[0].openItemCount).toBe(0)

    await deleteSession('s1')
    expect(await getSession('s1')).toBeUndefined()
    expect(await listHistory()).toEqual([])
  })

  it('rejects a history entry with a different id', async () => {
    await expect(saveSession(session('s1', '2026-09-01T10:00:00Z'), history('other', '2026-09-01T10:00:00Z'))).rejects.toThrow()
    expect(await listSessions()).toEqual([])
  })
})

describe('mappings', () => {
  it('lists, filters by module and deletes', async () => {
    await saveMapping(mapping('m1', ['Date'], ['Date'], '2026-09-01T10:00:00Z'))
    await saveMapping({ ...mapping('m2', ['X'], ['Y'], '2026-09-03T10:00:00Z'), moduleId: 'ar' })
    expect((await listMappings()).map((m) => m.id)).toEqual(['m2', 'm1'])
    expect((await listMappings('bank')).map((m) => m.id)).toEqual(['m1'])
    await deleteMapping('m1')
    expect((await listMappings()).map((m) => m.id)).toEqual(['m2'])
  })

  it('finds a mapping by headers regardless of order, case, spaces or side', async () => {
    await saveMapping(mapping('m1', ['Value Date', 'Amount', 'Ref'], ['Posting Date', 'Debit', 'Credit']))
    expect((await findMappingByHeaders('bank', ['ref ', 'AMOUNT', 'value date'], ['Credit', 'Debit', 'Posting Date']))?.id).toBe('m1')
    expect((await findMappingByHeaders('bank', ['Credit', 'Debit', 'Posting Date'], ['Ref', 'Amount', 'Value Date']))?.id).toBe('m1')
    expect(await findMappingByHeaders('bank', ['Ref', 'Amount'], ['Credit', 'Debit', 'Posting Date'])).toBeUndefined()
    expect(await findMappingByHeaders('ar', ['Value Date', 'Amount', 'Ref'], ['Posting Date', 'Debit', 'Credit'])).toBeUndefined()
  })

  it('returns the most recently updated mapping when several match', async () => {
    await saveMapping(mapping('old', ['A'], ['B'], '2026-08-01T10:00:00Z'))
    await saveMapping(mapping('new', ['A'], ['B'], '2026-09-01T10:00:00Z'))
    expect((await findMappingByHeaders('bank', ['A'], ['B']))?.id).toBe('new')
  })
})

describe('templates and recipes', () => {
  it('saves, lists and deletes templates', async () => {
    await saveTemplate({ ...mapping('t1', ['Emp ID'], ['Employee No'], '2026-09-01T10:00:00Z'), moduleId: 'general' })
    await saveTemplate({ ...mapping('t2', ['IBAN'], ['IBAN'], '2026-09-02T10:00:00Z'), moduleId: 'general' })
    expect((await listTemplates()).map((t) => t.id)).toEqual(['t2', 't1'])
    await deleteTemplate('t2')
    expect((await listTemplates()).map((t) => t.id)).toEqual(['t1'])
  })

  it('saves, filters and deletes recipes', async () => {
    const r = (id: string, tool: ToolRecipe['tool'], updatedAt: string): ToolRecipe => ({
      id,
      name: id,
      tool,
      options: { trim: true },
      createdAt: updatedAt,
      updatedAt
    })
    await saveRecipe(r('r1', 'data-cleaner', '2026-09-01T10:00:00Z'))
    await saveRecipe(r('r2', 'merge-files', '2026-09-02T10:00:00Z'))
    expect((await listRecipes()).map((x) => x.id)).toEqual(['r2', 'r1'])
    expect((await listRecipes('data-cleaner')).map((x) => x.id)).toEqual(['r1'])
    expect((await listRecipes('data-cleaner'))[0].options).toEqual({ trim: true })
    await deleteRecipe('r1')
    expect((await listRecipes()).map((x) => x.id)).toEqual(['r2'])
  })
})

function line(side: 'A' | 'B', n: number): EngineLine {
  return { id: `${side}:r${n}`, side, rowId: `r${n}`, amount: n, comparableAmount: n, date: new Date(Date.UTC(2026, 8, 1)), values: { Ref: `REF${n}`, Amount: n } }
}

function withLines(s: ReconSession, n: number): ReconSession {
  const linesA = Array.from({ length: n }, (_, i) => line('A', i + 2))
  const linesB = Array.from({ length: n }, (_, i) => line('B', i + 2))
  return { ...s, result: { ...s.result, linesA, linesB } }
}

async function rawRecord<T>(store: string, key: string): Promise<T | undefined> {
  const d = await openDB(DB_NAME)
  try {
    return (await d.get(store, key)) as T | undefined
  } finally {
    d.close()
  }
}

describe('session lines stored once (version 3)', () => {
  it('keeps the lines in their own store and reassembles them on read', async () => {
    const s = withLines(session('s1', '2026-09-01T10:00:00Z'), 3)
    await saveSession(s, history('s1', '2026-09-01T10:00:00Z'))
    const light = await rawRecord<ReconSession>('sessions', 's1')
    expect(light?.result.linesA).toEqual([])
    expect(light?.result.linesB).toEqual([])
    const stored = await rawRecord<{ linesA: EngineLine[] }>('sessionLines', 's1')
    expect(stored?.linesA.map((l) => l.id)).toEqual(['A:r2', 'A:r3', 'A:r4'])

    const back = await getSession('s1')
    expect(back?.result.linesA.map((l) => l.id)).toEqual(['A:r2', 'A:r3', 'A:r4'])
    expect(back?.result.linesB).toHaveLength(3)
    expect(back?.result.linesA[0].date).toEqual(new Date(Date.UTC(2026, 8, 1)))
  })

  it('writes only the light part on a decision that keeps the same lines', async () => {
    const s = withLines(session('s1', '2026-09-01T10:00:00Z'), 2)
    await saveSession(s, history('s1', '2026-09-01T10:00:00Z'))
    // Change the stored lines behind the app's back: a light save must not overwrite them.
    const d = await openDB(DB_NAME)
    await d.put('sessionLines', { id: 's1', linesA: [line('A', 99)], linesB: [] })
    d.close()
    const decided: ReconSession = { ...s, updatedAt: '2026-09-01T11:00:00Z', audit: [{ id: 'a1', at: '2026-09-01T11:00:00Z', user: 'Sana', action: 'accept', pairId: 'p1' }] }
    await saveSession(decided, history('s1', '2026-09-01T11:00:00Z'))
    expect((await rawRecord<{ linesA: EngineLine[] }>('sessionLines', 's1'))?.linesA.map((l) => l.id)).toEqual(['A:r99'])
    expect((await rawRecord<ReconSession>('sessions', 's1'))?.audit).toHaveLength(1)

    // New lines (a re-run) are written again.
    const rerun = withLines({ ...decided, updatedAt: '2026-09-01T12:00:00Z' }, 1)
    await saveSession(rerun, history('s1', '2026-09-01T12:00:00Z'))
    expect((await getSession('s1'))?.result.linesA.map((l) => l.id)).toEqual(['A:r2'])
  })

  it('writes the lines again if they went missing', async () => {
    const s = withLines(session('s1', '2026-09-01T10:00:00Z'), 2)
    await saveSession(s, history('s1', '2026-09-01T10:00:00Z'))
    const d = await openDB(DB_NAME)
    await d.delete('sessionLines', 's1')
    d.close()
    await saveSession({ ...s, updatedAt: '2026-09-01T11:00:00Z' }, history('s1', '2026-09-01T11:00:00Z'))
    expect((await getSession('s1'))?.result.linesA).toHaveLength(2)
  })

  it('lists sessions without lines by default and with them on request; delete removes the lines too', async () => {
    await saveSession(withLines(session('s1', '2026-09-01T10:00:00Z'), 2), history('s1', '2026-09-01T10:00:00Z'))
    expect((await listSessions())[0].result.linesA).toEqual([])
    expect((await listSessions({ withLines: true }))[0].result.linesA).toHaveLength(2)
    expect(await sessionExists('s1')).toBe(true)
    await deleteSession('s1')
    expect(await sessionExists('s1')).toBe(false)
    expect(await rawRecord('sessionLines', 's1')).toBeUndefined()
  })
})

describe('upgrade from version 2', () => {
  it('moves the lines of existing sessions into the new store', async () => {
    const v2 = await openDB(DB_NAME, 2, {
      upgrade(database) {
        database.createObjectStore('history', { keyPath: 'id' }).createIndex('finishedAt', 'finishedAt')
        database.createObjectStore('settings')
        database.createObjectStore('sessions', { keyPath: 'id' }).createIndex('updatedAt', 'updatedAt')
        database.createObjectStore('mappings', { keyPath: 'id' }).createIndex('moduleId', 'moduleId')
        database.createObjectStore('templates', { keyPath: 'id' }).createIndex('updatedAt', 'updatedAt')
        database.createObjectStore('recipes', { keyPath: 'id' }).createIndex('tool', 'tool')
      }
    })
    await v2.put('sessions', withLines(session('old1', '2026-08-01T10:00:00Z'), 4))
    await v2.put('sessions', withLines(session('old2', '2026-08-02T10:00:00Z'), 1))
    await v2.put('history', history('old1', '2026-08-01T10:00:00Z'))
    v2.close()

    expect((await getSession('old1'))?.result.linesA).toHaveLength(4)
    expect((await getSession('old2'))?.result.linesB.map((l) => l.id)).toEqual(['B:r2'])
    expect((await listSessions()).map((s) => [s.id, s.result.linesA.length])).toEqual([
      ['old2', 0],
      ['old1', 0]
    ])
    expect((await listHistory()).map((h) => h.id)).toEqual(['old1'])
    await closeDb()
    expect((await rawRecord<ReconSession>('sessions', 'old1'))?.result.linesA).toEqual([])
  })
})

describe('errors', () => {
  it('explains a database from a newer version in plain English', async () => {
    const newer = await openDB(DB_NAME, 99)
    newer.close()
    await expect(getSettings()).rejects.toThrow(/newer version of Reco-Do/)
    // A failed open is not remembered: once the problem is gone, the next call works.
    globalThis.indexedDB = new IDBFactory()
    expect(await getSettings()).toEqual(DEFAULT_SETTINGS)
  })

  it('maps browser errors to plain English and keeps the detail', () => {
    const quota = friendlyDbError(new DOMException('The quota has been exceeded.', 'QuotaExceededError'))
    expect(quota).toBeInstanceOf(DatabaseError)
    expect(quota.message).toMatch(/not enough free disk space/)
    expect((quota as DatabaseError).detail).toContain('QuotaExceededError')
    expect(friendlyDbError(new Error('The history entry must have the same id as the session.')).message).toBe('The history entry must have the same id as the session.')
    expect(friendlyDbError(new TypeError('x is undefined')).message).toMatch(/could not be reached/)
  })
})

describe('settings transaction', () => {
  it('does not lose a field when two saves overlap', async () => {
    await Promise.all([saveSettings({ preparerName: 'Sana' }), saveSettings({ currency: 'USD' })])
    const s = await getSettings()
    expect(s.preparerName).toBe('Sana')
    expect(s.currency).toBe('USD')
  })
})

describe('upgrade from version 1', () => {
  it('keeps existing history and settings and adds the new stores', async () => {
    const v1 = await openDB(DB_NAME, 1, {
      upgrade(database) {
        database.createObjectStore('history', { keyPath: 'id' })
        database.createObjectStore('settings')
      }
    })
    await v1.put('history', history('old', '2026-08-15T10:00:00Z'))
    await v1.put('settings', { preparerName: 'Ravi', department: 'Finance', currency: 'SAR' }, 'app')
    v1.close()

    expect((await listHistory()).map((h) => h.id)).toEqual(['old'])
    expect(await getSettings()).toEqual({ ...DEFAULT_SETTINGS, preparerName: 'Ravi', department: 'Finance', currency: 'SAR' })
    expect(await listSessions()).toEqual([])
    expect(await listMappings()).toEqual([])
    expect(await listTemplates()).toEqual([])
    expect(await listRecipes()).toEqual([])
  })
})

// ───────────────────────── Version 4: drafts, source files and session summaries ─────────────────────────

function sourceFile(name: string, rows: number): SourceFile {
  const table: ParsedTable = {
    fileName: name,
    sheetName: 'Sheet1',
    headerRowIndex: 0,
    columns: ['Date', 'Ref', 'Amount'],
    rows: Array.from({ length: rows }, (_, i) => ({
      id: `r${i + 2}`,
      sourceRow: i + 2,
      values: { Date: new Date(Date.UTC(2026, 8, 1 + (i % 28))), Ref: `REF${i}`, Amount: i * 10.5 }
    })),
    excluded: [],
    openingBalance: 1000,
    closingBalance: null
  }
  return {
    fileName: name,
    size: 2048,
    workbook: { fileName: name, sheets: [{ name: 'Sheet1', rows: [['Date', 'Ref', 'Amount'], ...table.rows.map((r) => [r.values.Date, r.values.Ref, r.values.Amount])] }] },
    sheetIndex: 0,
    detectedHeaderRow: 0,
    table
  }
}

function draft(id: string, updatedAt: string, over: Partial<DraftRecord> = {}): DraftRecord {
  return {
    id,
    moduleId: 'bank',
    createdAt: updatedAt,
    updatedAt,
    step: 1,
    sideAName: 'Bank statement',
    sideBName: 'General ledger',
    accountLabel: 'ENBD Current',
    period: 'Sep 2026',
    accountTouched: false,
    periodTouched: true,
    config: { moduleId: 'bank', sideAName: 'Bank statement', sideBName: 'General ledger', keys: [], sign: 'inverse', referencePrefixes: ['CHQ'], currency: 'AED' },
    configSource: { kind: 'suggested' },
    files: { A: { fileName: 'a.xlsx', sheetName: 'Sheet1', rows: 3 }, B: { fileName: 'b.xlsx', sheetName: 'Sheet1', rows: 2 } },
    ...over
  }
}

function pair(id: string, tier: 'doubtful' | 'likely', status: 'open' | 'accepted'): ReconSession['result']['pairs'][number] {
  return { id, tier, aIds: [`A:${id}`], bIds: [`B:${id}`], keyResults: [], amountDifference: 0, dateDifferenceDays: 0, reason: '', flags: [], origin: 'engine', status }
}

describe('drafts (version 4)', () => {
  it('saves a draft with its files and reads both back, dates and all', async () => {
    const sources: SourceFiles = { A: sourceFile('a.xlsx', 3), B: sourceFile('b.xlsx', 2) }
    await saveDraft(draft('d1', '2026-10-01T10:00:00Z'), sources)
    const back = await getDraft('d1')
    expect(back?.draft.accountLabel).toBe('ENBD Current')
    expect(back?.draft.config?.referencePrefixes).toEqual(['CHQ'])
    expect(back?.sources.A?.table.rows).toHaveLength(3)
    expect(back?.sources.A?.table.rows[1].values.Date).toEqual(new Date(Date.UTC(2026, 8, 2)))
    expect(back?.sources.B?.workbook.sheets[0].rows).toHaveLength(3)
    expect(back?.sources.A?.table.openingBalance).toBe(1000)
    // The small record does not carry the tables.
    const raw = await rawRecord<Record<string, unknown>>('drafts', 'd1')
    expect(raw && ('sources' in raw || 'table' in raw)).toBe(false)
    expect(await getDraft('missing')).toBeUndefined()
  })

  it('keeps the first createdAt, lists newest first and filters by module', async () => {
    const sources: SourceFiles = { A: sourceFile('a.xlsx', 1), B: null }
    await saveDraft(draft('d1', '2026-10-01T10:00:00Z'), sources)
    await saveDraft(draft('d2', '2026-10-02T10:00:00Z', { moduleId: 'ar' }), sources)
    await saveDraft(draft('d1', '2026-10-03T10:00:00Z', { createdAt: '2026-10-03T10:00:00Z', step: 0 }), sources)
    const all = await listDrafts()
    expect(all.map((d) => d.id)).toEqual(['d1', 'd2'])
    expect(all[0].createdAt).toBe('2026-10-01T10:00:00Z')
    expect(all[0].step).toBe(0)
    expect((await listDrafts('ar')).map((d) => d.id)).toEqual(['d2'])
  })

  it('writes the files only when they change, and removes them when both are cleared', async () => {
    const sources: SourceFiles = { A: sourceFile('a.xlsx', 2), B: sourceFile('b.xlsx', 2) }
    await saveDraft(draft('d1', '2026-10-01T10:00:00Z'), sources)
    // Change the stored files behind the app's back: a save with the same file objects must not rewrite them.
    const d = await openDB(DB_NAME)
    await d.put('sourceTables', { id: 'd1', A: sourceFile('changed.xlsx', 1), B: null })
    d.close()
    await saveDraft(draft('d1', '2026-10-01T10:01:00Z', { accountLabel: 'Typed' }), sources)
    expect((await rawRecord<SourceFiles>('sourceTables', 'd1'))?.A?.fileName).toBe('changed.xlsx')
    expect((await getDraft('d1'))?.draft.accountLabel).toBe('Typed')
    // New file objects are written.
    const replaced: SourceFiles = { A: sourceFile('new.xlsx', 4), B: sources.B }
    await saveDraft(draft('d1', '2026-10-01T10:02:00Z'), replaced)
    expect((await getDraft('d1'))?.sources.A?.fileName).toBe('new.xlsx')
    await saveDraft(draft('d1', '2026-10-01T10:03:00Z', { files: { A: null, B: null } }), { A: null, B: null })
    expect(await rawRecord('sourceTables', 'd1')).toBeUndefined()
  })

  it('deletes a draft and its files', async () => {
    await saveDraft(draft('d1', '2026-10-01T10:00:00Z'), { A: sourceFile('a.xlsx', 1), B: sourceFile('b.xlsx', 1) })
    await deleteDraft('d1')
    expect(await getDraft('d1')).toBeUndefined()
    expect(await listDrafts()).toEqual([])
    expect(await rawRecord('sourceTables', 'd1')).toBeUndefined()
  })

  it('stores large tables (50,000 rows) and reads them back', async () => {
    const big: SourceFiles = { A: sourceFile('big-a.xlsx', 50_000), B: sourceFile('big-b.xlsx', 50_000) }
    await saveDraft(draft('big', '2026-10-01T10:00:00Z'), big)
    const back = await getDraft('big')
    expect(back?.sources.A?.table.rows).toHaveLength(50_000)
    expect(back?.sources.B?.table.rows[49_999].values.Ref).toBe('REF49999')
  })
})

describe('session with its source files (version 4)', () => {
  it('turns a draft into a session: same id, the draft record goes, the files stay with the session', async () => {
    const sources: SourceFiles = { A: sourceFile('a.xlsx', 3), B: sourceFile('b.xlsx', 3) }
    await saveDraft(draft('r1', '2026-10-01T10:00:00Z'), sources)
    const s = withLines(session('r1', '2026-10-01T10:05:00Z'), 3)
    await saveSession(s, history('r1', '2026-10-01T10:05:00Z'), { sources })
    expect(await listDrafts()).toEqual([])
    expect((await getSession('r1'))?.result.linesA).toHaveLength(3)
    const files = await getSources('r1')
    expect(files?.A?.table.rows.map((r) => r.values.Ref)).toEqual(['REF0', 'REF1', 'REF2'])
    expect(files?.B?.fileName).toBe('b.xlsx')
    expect(await listSourceIds()).toEqual(new Set(['r1']))
  })

  it('stores the files with a session that never was a draft, and rewrites them if they went missing', async () => {
    const sources: SourceFiles = { A: sourceFile('a.xlsx', 1), B: sourceFile('b.xlsx', 2) }
    const s = session('r2', '2026-10-01T10:00:00Z')
    await saveSession(s, history('r2', '2026-10-01T10:00:00Z'), { sources })
    expect((await getSources('r2'))?.B?.table.rows).toHaveLength(2)
    const d = await openDB(DB_NAME)
    await d.delete('sourceTables', 'r2')
    d.close()
    await saveSession({ ...s, updatedAt: '2026-10-01T10:01:00Z' }, history('r2', '2026-10-01T10:01:00Z'), { sources })
    expect((await getSources('r2'))?.A?.fileName).toBe('a.xlsx')
  })

  it('has no files for sessions saved without them (older sessions)', async () => {
    await saveSession(session('old', '2026-09-01T10:00:00Z'), history('old', '2026-09-01T10:00:00Z'))
    expect(await getSources('old')).toBeUndefined()
  })

  it('deleting a session removes its lines, files, summary, history row and any draft with its id', async () => {
    const sources: SourceFiles = { A: sourceFile('a.xlsx', 1), B: sourceFile('b.xlsx', 1) }
    await saveSession(withLines(session('r3', '2026-10-01T10:00:00Z'), 1), history('r3', '2026-10-01T10:00:00Z'), { sources })
    // A stray draft with the same id (e.g. written by a save that was still queued).
    await saveDraft(draft('r3', '2026-10-01T10:01:00Z'), sources)
    await deleteSession('r3')
    for (const store of ['sessions', 'sessionLines', 'history', 'drafts', 'sourceTables', 'sessionSummaries']) expect(await rawRecord(store, 'r3')).toBeUndefined()
  })

  it('deleting a draft keeps the files when a session with that id still uses them', async () => {
    const sources: SourceFiles = { A: sourceFile('a.xlsx', 1), B: sourceFile('b.xlsx', 1) }
    await saveSession(session('r4', '2026-10-01T10:00:00Z'), history('r4', '2026-10-01T10:00:00Z'), { sources })
    await deleteDraft('r4')
    expect((await getSources('r4'))?.A?.fileName).toBe('a.xlsx')
  })

  it('keeps a small summary per session for lists', async () => {
    const s = session('r5', '2026-10-02T10:00:00Z')
    const pairs = [pair('p1', 'doubtful', 'open'), pair('p2', 'doubtful', 'accepted'), pair('p3', 'likely', 'open')]
    const stats = { ...s.result.stats, doubtful: 1, likely: 1, unmatchedA: 1 }
    await saveSession({ ...s, result: { ...s.result, pairs, stats, unmatchedA: ['A:r9'], unmatchedB: [] } }, history('r5', '2026-10-02T10:00:00Z'))
    await saveSession(session('r6', '2026-10-01T10:00:00Z'), history('r6', '2026-10-01T10:00:00Z'))
    const list = await listSessionSummaries()
    expect(list.map((x) => x.id)).toEqual(['r5', 'r6'])
    expect(list[0].open).toEqual({ doubtful: 1, likely: 1, suggestions: 0, unmatched: 1 })
    expect(list[0]).toMatchObject({ moduleId: 'bank', accountLabel: 'ENBD Current A/c', period: 'Sep 2026', fileA: 'a.xlsx', preparer: 'Sana Fathima', finalised: null })
  })
})

describe('upgrade from version 3', () => {
  it('keeps every session, line, history row and setting, adds the new stores and builds the session summaries', async () => {
    const v3 = await openDB(DB_NAME, 3, {
      upgrade(database) {
        database.createObjectStore('history', { keyPath: 'id' }).createIndex('finishedAt', 'finishedAt')
        database.createObjectStore('settings')
        database.createObjectStore('sessions', { keyPath: 'id' }).createIndex('updatedAt', 'updatedAt')
        database.createObjectStore('mappings', { keyPath: 'id' }).createIndex('moduleId', 'moduleId')
        database.createObjectStore('templates', { keyPath: 'id' }).createIndex('updatedAt', 'updatedAt')
        database.createObjectStore('recipes', { keyPath: 'id' }).createIndex('tool', 'tool')
        database.createObjectStore('sessionLines', { keyPath: 'id' })
      }
    })
    const old = withLines(session('v3a', '2026-09-10T10:00:00Z'), 2)
    await v3.put('sessions', { ...old, result: { ...old.result, linesA: [], linesB: [] } })
    await v3.put('sessionLines', { id: 'v3a', linesA: old.result.linesA, linesB: old.result.linesB })
    await v3.put('sessions', { ...session('v3b', '2026-09-11T10:00:00Z'), finalised: { by: 'Ravi', at: '2026-09-11T10:00:00Z' } })
    await v3.put('history', history('v3a', '2026-09-10T10:00:00Z'))
    await v3.put('settings', { preparerName: 'Ravi' }, 'app')
    v3.close()

    expect((await getSession('v3a'))?.result.linesA).toHaveLength(2)
    expect((await listHistory()).map((h) => h.id)).toEqual(['v3a'])
    expect((await getSettings()).preparerName).toBe('Ravi')
    expect(await listDrafts()).toEqual([])
    expect(await getSources('v3a')).toBeUndefined()
    const summaries = await listSessionSummaries()
    expect(summaries.map((x) => [x.id, x.finalised?.by ?? null])).toEqual([
      ['v3b', 'Ravi'],
      ['v3a', null]
    ])
    // New drafts can be saved straight away.
    await saveDraft(draft('new', '2026-10-01T10:00:00Z'), { A: sourceFile('a.xlsx', 1), B: null })
    expect((await listDrafts()).map((d) => d.id)).toEqual(['new'])
  })
})
