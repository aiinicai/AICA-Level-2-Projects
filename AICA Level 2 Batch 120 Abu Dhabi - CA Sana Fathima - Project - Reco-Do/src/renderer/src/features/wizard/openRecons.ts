// The reconciliations open in this app window: the wizard state of each one (so switching between them is
// instant and keeps everything on screen) and which one each module shows. Drafts and sessions are also saved
// to the local database, so a state dropped from here (or lost when the app closes) is read back from there.

import type { ModuleId } from '@shared/modules'
import { deleteDraft, deleteSession } from '@/lib/db'
import { closeDraftSaves, reopenDraftSaves } from '@/lib/draftSaves'
import { allowSessionSaves, discardSessionSaves } from '@/lib/sessionSaves'
import type { ReconKind } from './inProgress'
import type { WizardState } from './types'

/** States kept in memory at most (each can hold two large files); older ones are read back from the database. */
export const MAX_OPEN_IN_MEMORY = 6

/** Wizard states by reconciliation id, least recently used first. */
const states = new Map<string, WizardState>()
/** The reconciliation each module shows. */
const shown = new Map<ModuleId, string>()

/** Remembers the newest state of a reconciliation (and marks it most recently used). */
export function rememberWizard(state: WizardState): void {
  if (!state.reconId) return
  states.delete(state.reconId)
  states.set(state.reconId, state)
  if (states.size <= MAX_OPEN_IN_MEMORY) return
  const keep = new Set(shown.values())
  for (const id of states.keys()) {
    if (states.size <= MAX_OPEN_IN_MEMORY) break
    if (!keep.has(id) && id !== state.reconId) states.delete(id)
  }
}

/** The state of a reconciliation open in this window, if it is still in memory. */
export function recallWizard(id: string): WizardState | undefined {
  return states.get(id)
}

/** The reconciliation a module last showed, while its state is still in memory. */
export function shownRecon(moduleId: ModuleId): string | undefined {
  const id = shown.get(moduleId)
  return id && states.has(id) ? id : undefined
}

export function setShownRecon(moduleId: ModuleId, id: string): void {
  shown.set(moduleId, id)
}

/** Drops a reconciliation from memory (when it is deleted, or continues under a new id). */
export function forgetRecon(id: string): void {
  states.delete(id)
  for (const [m, shownId] of shown) if (shownId === id) shown.delete(m)
}

/** Ids held in memory (tests). */
export function openReconIds(): string[] {
  return Array.from(states.keys())
}

/** Forgets everything (tests). */
export function resetOpenRecons(): void {
  states.clear()
  shown.clear()
}

/**
 * Deletes a draft or session for good: pending saves are stopped first so it cannot come back, then the record,
 * its source files (and for a session its lines and history row) are removed and it is dropped from memory.
 */
export async function deleteRecon(id: string, kind: ReconKind): Promise<void> {
  await closeDraftSaves(id)
  if (kind === 'session') await discardSessionSaves(id)
  try {
    if (kind === 'session') await deleteSession(id)
    else await deleteDraft(id)
  } catch (err) {
    reopenDraftSaves(id)
    if (kind === 'session') allowSessionSaves(id)
    throw err
  }
  forgetRecon(id)
}
