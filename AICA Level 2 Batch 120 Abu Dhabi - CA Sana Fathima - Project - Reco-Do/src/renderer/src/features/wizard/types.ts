// Wizard state shapes. Pure types (no React), shared by the reducer, the helpers and the step screens.

import type { ParsedTable, ReconConfig, ReconSession, Side } from '@shared/contracts'
import type { ModuleId } from '@shared/modules'
import type { WorkbookReadResult } from '@shared/parsing'

/** 0 Upload · 1 Map & Rules · 2 Reconcile · 3 Smart Recon · 4 Review & Export */
export type StepIndex = 0 | 1 | 2 | 3 | 4

export const STEP_TITLES = ['Upload', 'Map & rules', 'Reconcile', 'Smart Recon', 'Review & export'] as const

/** One uploaded file, with the sheet and header row the user settled on. */
export interface LoadedFile {
  fileName: string
  size: number
  /** The workbook as read, including any `warnings` about repairs the reader made. */
  workbook: WorkbookReadResult
  sheetIndex: number
  /** Header row found automatically for the current sheet (0-based). */
  detectedHeaderRow: number
  table: ParsedTable
}

/** Where the current Map & Rules configuration came from. */
export type ConfigSource = { kind: 'suggested' } | { kind: 'mapping'; name: string } | { kind: 'template'; name: string }

export interface WizardState {
  moduleId: ModuleId
  /**
   * Id of this reconciliation: the draft id before Reconcile runs and the session id afterwards (they are the
   * same, so the stored source files follow the draft into the session). '' only in tests.
   */
  reconId: string
  step: StepIndex
  sideAName: string
  sideBName: string
  files: Record<Side, LoadedFile | null>
  accountLabel: string
  period: string
  /** True once the user typed in the field, so automatic guesses stop overwriting it. */
  accountTouched: boolean
  periodTouched: boolean
  config: ReconConfig | null
  configSource: ConfigSource | null
  session: ReconSession | null
  /**
   * 'new' = the files are here, so Upload and Map & rules can be used (a new reconciliation, a reopened draft, or
   * a reopened session saved with its files). 'resumed' = a saved session without its files (saved before files
   * were kept) or a finalised one: only the results can be opened.
   */
  origin: 'new' | 'resumed'
}

export type WizardAction =
  | { type: 'go'; step: StepIndex }
  | { type: 'sideName'; side: Side; name: string }
  /** `freshId`: the id to continue under when this replaces the files of a reconciliation that already ran. */
  | { type: 'loadFile'; side: Side; file: LoadedFile; freshId?: string }
  | { type: 'clearFile'; side: Side; freshId?: string }
  | { type: 'meta'; accountLabel?: string; period?: string }
  | { type: 'autoMeta'; accountLabel: string; period: string }
  | { type: 'setConfig'; config: ReconConfig; source: ConfigSource }
  | { type: 'patchConfig'; patch: Partial<ReconConfig> }
  | { type: 'session'; session: ReconSession }
  /** Opens a saved session. With `files` (stored with it) and not finalised, it stays fully editable. */
  | { type: 'resume'; session: ReconSession; files?: Record<Side, LoadedFile | null> }
  /** Puts back a whole saved state (a reopened draft). */
  | { type: 'restore'; state: WizardState }
  | { type: 'reset'; reconId?: string }
