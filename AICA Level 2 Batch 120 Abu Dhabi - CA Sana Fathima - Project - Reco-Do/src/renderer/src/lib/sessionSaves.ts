// Saving reconciliation sessions: one save in flight per session, the latest version wins, and everything still
// pending can be flushed before the window closes. Saves outlive the wizard page, so leaving the page or closing
// the app right after a decision never loses it.

import type { ReconSession } from '@shared/contracts'
import { summariseForHistory } from '@engine/index'
import { saveSession, type SourceFiles } from './db'
import { createLatestWinsSaver, type LatestWinsSaver } from './latestWins'

/** Lets the new state paint (and input be handled) before IndexedDB copies the session. */
const PAINT_DELAY_MS = 50

const savers = new Map<string, LatestWinsSaver<ReconSession>>()
const deleted = new Set<string>()
/** Source files still to be written with a session (kept apart so a newer queued version cannot drop them). */
const pendingSources = new Map<string, SourceFiles>()

async function write(x: ReconSession): Promise<void> {
  const sources = pendingSources.get(x.id)
  await saveSession(x, summariseForHistory(x), { sources })
  if (pendingSources.get(x.id) === sources) pendingSources.delete(x.id)
}

function saverFor(id: string): LatestWinsSaver<ReconSession> {
  let s = savers.get(id)
  if (!s) {
    s = createLatestWinsSaver<ReconSession>(write, { delayMs: PAINT_DELAY_MS })
    savers.set(id, s)
  }
  return s
}

/**
 * Saves this version of the session (or a newer one queued after it). Rejects with a plain-English error.
 * `sources` are the files the session was run on; they are stored with it so it can go back to Map & rules.
 */
export function persistSession(session: ReconSession, sources?: SourceFiles): Promise<void> {
  if (deleted.has(session.id)) {
    return Promise.reject(new Error('This reconciliation was deleted in Recon History, so changes to it are no longer saved.'))
  }
  if (sources) pendingSources.set(session.id, sources)
  return saverFor(session.id).save(session)
}

/** True while any session save is queued or being written. */
export function hasPendingSessionSaves(): boolean {
  for (const s of savers.values()) if (s.pending) return true
  return false
}

/** Waits for every queued and in-flight session save. Never rejects. */
export async function flushSessionSaves(): Promise<void> {
  await Promise.all(Array.from(savers.values(), (s) => s.flush()))
}

/** Call before deleting a session: drops its queued save, waits for one in flight and refuses later saves. */
export async function discardSessionSaves(id: string): Promise<void> {
  deleted.add(id)
  const s = savers.get(id)
  if (s) await s.cancel()
  savers.delete(id)
  pendingSources.delete(id)
}

/** Undoes `discardSessionSaves` when the delete itself failed and the session is still there. */
export function allowSessionSaves(id: string): void {
  deleted.delete(id)
}
