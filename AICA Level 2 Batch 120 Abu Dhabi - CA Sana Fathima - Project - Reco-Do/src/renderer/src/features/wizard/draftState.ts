// Turning the wizard state into a stored draft and back. Pure: no React, no database.

import type { DraftFileInfo, DraftRecord, SourceFiles } from '@/lib/db'
import { initialState } from './reducer'
import type { LoadedFile, WizardState } from './types'

function fileInfo(f: LoadedFile | null): DraftFileInfo | null {
  return f ? { fileName: f.fileName, sheetName: f.table.sheetName, rows: f.table.rows.length } : null
}

/**
 * The draft to store for this state, or null when there is nothing to keep as a draft: no file read yet, a
 * reconciliation that already ran (it is a session now), or a session reopened without its files.
 */
export function draftFromState(s: WizardState, now: string): DraftRecord | null {
  if (!s.reconId || s.session || s.origin !== 'new' || (!s.files.A && !s.files.B)) return null
  return {
    id: s.reconId,
    moduleId: s.moduleId,
    createdAt: now,
    updatedAt: now,
    // Reconcile (step 2) can only be on screen without a session while a run is starting: resume at Map & rules.
    step: s.step === 0 ? 0 : 1,
    sideAName: s.sideAName,
    sideBName: s.sideBName,
    accountLabel: s.accountLabel,
    period: s.period,
    accountTouched: s.accountTouched,
    periodTouched: s.periodTouched,
    config: s.config,
    configSource: s.configSource,
    files: { A: fileInfo(s.files.A), B: fileInfo(s.files.B) }
  }
}

/** The source files of the state, for storing beside the draft or session. */
export function sourcesFromState(s: WizardState): SourceFiles {
  return { A: s.files.A, B: s.files.B }
}

/** Source files as the wizard uses them (the stored shape is the same as a loaded file). */
export function filesFromSources(sources: SourceFiles): WizardState['files'] {
  return { A: sources.A, B: sources.B }
}

/** The wizard state of a reopened draft. A file missing from the store leaves its side empty. */
export function stateFromDraft(d: DraftRecord, sources: SourceFiles): WizardState {
  const files = filesFromSources(sources)
  const both = !!files.A && !!files.B
  return {
    ...initialState(d.moduleId, d.id),
    step: both ? d.step : 0,
    sideAName: d.sideAName,
    sideBName: d.sideBName,
    files,
    accountLabel: d.accountLabel,
    period: d.period,
    accountTouched: d.accountTouched,
    periodTouched: d.periodTouched,
    // A mapping belongs to both files; without both it is suggested again once they are back.
    config: both ? d.config : null,
    configSource: both ? d.configSource : null
  }
}
