import { describe, expect, it, vi } from 'vitest'
import { runWorkerJob, WORKER_READY } from '../../src/renderer/src/lib/workerJob'

type Res = { ok: true; value: number } | { ok: false; message: string }

/** Just enough of a Worker for runWorkerJob; the test drives its events. */
class FakeWorker {
  onmessage: ((e: MessageEvent) => void) | null = null
  onerror: ((e: ErrorEvent) => void) | null = null
  onmessageerror: (() => void) | null = null
  terminated = false
  posted: unknown[] = []
  postMessage(m: unknown): void {
    this.posted.push(m)
  }
  terminate(): void {
    this.terminated = true
  }
  emit(data: unknown): void {
    this.onmessage?.({ data } as MessageEvent)
  }
  fail(): void {
    this.onerror?.({ preventDefault: () => undefined } as unknown as ErrorEvent)
  }
}

function job(w: FakeWorker | null, onMainThread = vi.fn(async () => 99)) {
  return {
    onMainThread,
    promise: runWorkerJob<number, Res, number>({
      start: () => {
        if (!w) throw new Error('Workers are not available')
        return w as unknown as Worker
      },
      request: 7,
      unwrap: (r) => {
        if (r.ok) return r.value
        throw new Error(r.message)
      },
      onMainThread,
      crashMessage: 'It stopped unexpectedly.'
    })
  }
}

describe('runWorkerJob (P14)', () => {
  it('returns the worker result', async () => {
    const w = new FakeWorker()
    const j = job(w)
    w.emit(WORKER_READY)
    w.emit({ ok: true, value: 5 })
    await expect(j.promise).resolves.toBe(5)
    expect(w.posted).toEqual([7])
    expect(w.terminated).toBe(true)
    expect(j.onMainThread).not.toHaveBeenCalled()
  })

  it('falls back to the UI thread when the worker cannot be created or fails before it is ready', async () => {
    const none = job(null)
    await expect(none.promise).resolves.toBe(99)
    const w = new FakeWorker()
    const j = job(w)
    w.fail()
    await expect(j.promise).resolves.toBe(99)
    expect(j.onMainThread).toHaveBeenCalledTimes(1)
  })

  it('reports a crash after start instead of repeating the job on the UI thread', async () => {
    const w = new FakeWorker()
    const j = job(w)
    w.emit(WORKER_READY)
    w.fail()
    await expect(j.promise).rejects.toThrow('It stopped unexpectedly.')
    expect(j.onMainThread).not.toHaveBeenCalled()
  })

  it('passes on a plain-English job error from the worker', async () => {
    const w = new FakeWorker()
    const j = job(w)
    w.emit(WORKER_READY)
    w.emit({ ok: false, message: 'The sheet is empty.' })
    await expect(j.promise).rejects.toThrow('The sheet is empty.')
  })
})
