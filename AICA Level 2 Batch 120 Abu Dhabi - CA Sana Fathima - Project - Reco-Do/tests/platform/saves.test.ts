import 'fake-indexeddb/auto'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import type { ReconSession } from '../../src/shared/contracts'
import { closeDb, getSession, saveSession, sessionExists, deleteSession } from '../../src/renderer/src/lib/db'
import { createLatestWinsSaver } from '../../src/renderer/src/lib/latestWins'
import { allowSessionSaves, discardSessionSaves, flushSessionSaves, hasPendingSessionSaves, persistSession } from '../../src/renderer/src/lib/sessionSaves'
import { summariseForHistory } from '../../src/engine/index'

function deferred(): { promise: Promise<void>; resolve: () => void; reject: (e: unknown) => void } {
  let resolve!: () => void
  let reject!: (e: unknown) => void
  const promise = new Promise<void>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('latest-wins saver', () => {
  it('keeps one write in flight and writes only the newest queued item next', async () => {
    const written: number[] = []
    const gates: Array<ReturnType<typeof deferred>> = []
    const saver = createLatestWinsSaver<number>(async (n) => {
      const g = deferred()
      gates.push(g)
      await g.promise
      written.push(n)
    })
    const p1 = saver.save(1)
    await Promise.resolve()
    const p2 = saver.save(2)
    const p3 = saver.save(3)
    expect(gates).toHaveLength(1) // 2 and 3 wait for 1
    gates[0].resolve()
    await p1
    await new Promise((r) => setTimeout(r, 0))
    expect(gates).toHaveLength(2)
    gates[1].resolve()
    await Promise.all([p2, p3])
    expect(written).toEqual([1, 3]) // 2 was replaced by 3 before it was written
    expect(saver.pending).toBe(false)
  })

  it('rejects the callers of a failed write and carries on afterwards', async () => {
    let fail = true
    const saver = createLatestWinsSaver<string>(async () => {
      if (fail) throw new Error('Disk full')
    })
    await expect(saver.save('a')).rejects.toThrow('Disk full')
    fail = false
    await expect(saver.save('b')).resolves.toBeUndefined()
  })

  it('flush waits for queued work; cancel drops what is not yet written', async () => {
    const written: string[] = []
    const gate = deferred()
    const saver = createLatestWinsSaver<string>(async (x) => {
      if (x === 'first') await gate.promise
      written.push(x)
    })
    void saver.save('first')
    await Promise.resolve()
    const dropped = saver.save('second')
    const cancelled = saver.cancel()
    gate.resolve()
    await cancelled
    await dropped
    expect(written).toEqual(['first'])

    void saver.save('third')
    await saver.flush()
    expect(written).toEqual(['first', 'third'])
  })
})

function session(id: string, updatedAt: string): ReconSession {
  return {
    id,
    createdAt: updatedAt,
    updatedAt,
    meta: {
      accountLabel: 'ENBD Current A/c',
      period: 'Sep 2026',
      fileA: { name: 'a.xlsx', sheet: 'Sheet1', rows: 1 },
      fileB: { name: 'b.xlsx', sheet: 'Sheet1', rows: 1 },
      preparer: 'Sana',
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

describe('session saves', () => {
  beforeEach(async () => {
    await closeDb()
    globalThis.indexedDB = new IDBFactory()
  })
  afterEach(async () => {
    await closeDb()
  })

  it('saves the newest version and can be flushed before closing', async () => {
    const a = persistSession(session('x1', '2026-09-01T10:00:00Z'))
    const b = persistSession({ ...session('x1', '2026-09-01T10:05:00Z'), finalised: { by: 'Sana', at: '2026-09-01T10:05:00Z' } })
    expect(hasPendingSessionSaves()).toBe(true)
    await flushSessionSaves()
    await Promise.all([a, b])
    expect(hasPendingSessionSaves()).toBe(false)
    expect((await getSession('x1'))?.finalised?.by).toBe('Sana')
  })

  it('a deleted session cannot be brought back by a late save (R10)', async () => {
    const s = session('x2', '2026-09-01T10:00:00Z')
    await saveSession(s, summariseForHistory(s))
    const late = persistSession({ ...s, updatedAt: '2026-09-01T10:01:00Z' })
    await discardSessionSaves('x2')
    await deleteSession('x2')
    await late.catch(() => undefined)
    await expect(persistSession({ ...s, updatedAt: '2026-09-01T10:02:00Z' })).rejects.toThrow(/deleted in Recon History/)
    expect(await sessionExists('x2')).toBe(false)
    allowSessionSaves('x2')
    await persistSession(s)
    expect(await sessionExists('x2')).toBe(true)
  })
})
