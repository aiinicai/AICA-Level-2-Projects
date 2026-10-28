// Saving draft reconciliations (Upload / Map & rules, before Reconcile runs). Each draft has one save queue:
// changes made in quick succession are combined (a short pause before each write), one write runs at a time and
// the newest version wins. Everything still pending can be flushed before the window closes.

import { deleteDraft, saveDraft, type DraftRecord, type SourceFiles } from './db'
import { createLatestWinsSaver, type LatestWinsSaver } from './latestWins'

/** Typing in a field or ticking keys is saved together once the user pauses. */
export const DRAFT_SAVE_DELAY_MS = 400

type DraftJob = { kind: 'save'; draft: DraftRecord; sources: SourceFiles } | { kind: 'remove'; id: string }

const savers = new Map<string, LatestWinsSaver<DraftJob>>()
const closed = new Set<string>()

function writeJob(job: DraftJob): Promise<void> {
  return job.kind === 'save' ? saveDraft(job.draft, job.sources) : deleteDraft(job.id)
}

function saverFor(id: string, delayMs: number): LatestWinsSaver<DraftJob> {
  let s = savers.get(id)
  if (!s) {
    s = createLatestWinsSaver<DraftJob>(writeJob, { delayMs })
    savers.set(id, s)
  }
  return s
}

/** Queues this version of the draft (debounced). Resolves once it or a newer version is saved; rejects in plain English. */
export function persistDraft(draft: DraftRecord, sources: SourceFiles, opts: { delayMs?: number } = {}): Promise<void> {
  if (closed.has(draft.id)) return Promise.resolve()
  return saverFor(draft.id, opts.delayMs ?? DRAFT_SAVE_DELAY_MS).save({ kind: 'save', draft, sources })
}

/** Queues removal of the draft (e.g. both files were cleared), after any save queued before it. */
export function removeDraftLater(id: string): Promise<void> {
  if (closed.has(id)) return Promise.resolve()
  return saverFor(id, DRAFT_SAVE_DELAY_MS).save({ kind: 'remove', id })
}

/** True while any draft save is queued or being written. */
export function hasPendingDraftSaves(): boolean {
  for (const s of savers.values()) if (s.pending) return true
  return false
}

/** Waits for every queued and in-flight draft save (only this draft's when `id` is given). Never rejects. */
export async function flushDraftSaves(id?: string): Promise<void> {
  if (id !== undefined) {
    await savers.get(id)?.flush()
    return
  }
  await Promise.all(Array.from(savers.values(), (s) => s.flush()))
}

/**
 * Stops saving this draft: drops a queued save, waits for one in flight, and ignores later saves. Call before
 * deleting the draft, and when Reconcile turns it into a session.
 */
export async function closeDraftSaves(id: string): Promise<void> {
  closed.add(id)
  const s = savers.get(id)
  if (s) await s.cancel()
  savers.delete(id)
}

/** Undoes `closeDraftSaves` (the delete failed, or the run did not produce a session). */
export function reopenDraftSaves(id: string): void {
  closed.delete(id)
}
