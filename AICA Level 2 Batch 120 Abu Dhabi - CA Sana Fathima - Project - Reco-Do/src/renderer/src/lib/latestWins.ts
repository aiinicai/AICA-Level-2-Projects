// A save queue with one write in flight at a time where the latest item wins: while a write runs, newer items
// replace each other and only the newest is written next. Pure TypeScript (no DOM), unit-tested.

export interface LatestWinsSaver<T> {
  /**
   * Queues `item`. Resolves once it, or a newer item that replaced it, has been written; rejects with the
   * write's error if that write failed.
   */
  save(item: T): Promise<void>
  /** Waits until nothing is queued or being written. Never rejects. */
  flush(): Promise<void>
  /** Drops the queued item (its callers resolve without a write) and waits for a write in flight. */
  cancel(): Promise<void>
  /** True while an item is queued or being written. */
  readonly pending: boolean
}

interface Waiter {
  resolve: () => void
  reject: (err: unknown) => void
}

export function createLatestWinsSaver<T>(write: (item: T) => Promise<void>, opts: { delayMs?: number } = {}): LatestWinsSaver<T> {
  const delayMs = opts.delayMs ?? 0
  let queued: { item: T; waiters: Waiter[] } | null = null
  let running: Promise<void> | null = null

  const pump = (): void => {
    if (running || !queued) return
    running = (async () => {
      while (queued) {
        // A short pause lets the screen paint (and newer items arrive) before the write copies the data.
        if (delayMs > 0) await new Promise((r) => setTimeout(r, delayMs))
        const job = queued
        if (!job) break // cancelled during the pause
        queued = null
        try {
          await write(job.item)
          for (const w of job.waiters) w.resolve()
        } catch (err) {
          for (const w of job.waiters) w.reject(err)
        }
      }
    })().finally(() => {
      running = null
      pump()
    })
  }

  return {
    save(item: T): Promise<void> {
      return new Promise<void>((resolve, reject) => {
        if (queued) {
          queued.item = item
          queued.waiters.push({ resolve, reject })
        } else {
          queued = { item, waiters: [{ resolve, reject }] }
        }
        pump()
      })
    },
    async flush(): Promise<void> {
      while (running) await running.catch(() => undefined)
    },
    async cancel(): Promise<void> {
      const job = queued
      queued = null
      if (job) for (const w of job.waiters) w.resolve()
      while (running) await running.catch(() => undefined)
    },
    get pending(): boolean {
      return running !== null || queued !== null
    }
  }
}
