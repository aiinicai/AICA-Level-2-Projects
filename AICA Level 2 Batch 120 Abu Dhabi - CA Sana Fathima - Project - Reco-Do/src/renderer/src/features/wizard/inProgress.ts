// Unfinished reconciliations (drafts not run yet and saved sessions not finalised) for the In progress menu, the
// Dashboard and Recon History. The list builders are pure; `loadInProgress` reads them from the local database.

import type { ReconStats } from '@shared/contracts'
import type { ModuleId } from '@shared/modules'
import { formatDate } from '@shared/format'
import { listDrafts, listSessionSummaries, summariseSession, type DraftRecord, type SessionSummary } from '@/lib/db'
import { draftFromState } from './draftState'
import { STEP_TITLES, type WizardState } from './types'

export type ReconKind = 'draft' | 'session'

/** Draft = not run yet · In review = run, not finalised · Finalised = signed off. */
export type ReconStatus = 'draft' | 'review' | 'finalised'

export interface ReconListItem {
  id: string
  kind: ReconKind
  status: ReconStatus
  moduleId: ModuleId
  accountLabel: string
  period: string
  /** "Bank statement vs General ledger" style line. */
  sides: string
  /** "a.xlsx vs b.xlsx" (a file not read yet shows as "—"). */
  files: string
  /** Where it stands, e.g. "Map & rules" or "Review: 16 doubtful open". */
  stage: string
  createdAt: string
  updatedAt: string
  finalised: { by: string; at: string } | null
  /** Sessions only: the result's counts, and the pairs and suggestions still to decide. */
  stats?: ReconStats
  toReview?: number
  preparer?: string
}

const plural = (n: number, word: string): string => `${n.toLocaleString('en-US')} ${word}${n === 1 ? '' : 's'}`

/** Where a draft stands: its step, and how many files are in on the Upload step. */
export function draftStage(d: DraftRecord): string {
  const files = (d.files.A ? 1 : 0) + (d.files.B ? 1 : 0)
  if (d.step === 0) return files === 2 ? `${STEP_TITLES[0]}: both files read` : `${STEP_TITLES[0]}: ${files} of 2 files read`
  return STEP_TITLES[1]
}

/** Where a saved session stands, e.g. "Review: 16 doubtful open", "Review: 2 suggestions to check". */
export function sessionStage(s: SessionSummary): string {
  if (s.finalised) return 'Finalised'
  const { doubtful, likely, suggestions, unmatched } = s.open
  const toCheck: string[] = []
  if (doubtful) toCheck.push(`${doubtful.toLocaleString('en-US')} doubtful`)
  if (likely) toCheck.push(`${likely.toLocaleString('en-US')} likely`)
  if (toCheck.length) return `Review: ${toCheck.join(', ')} open`
  if (suggestions) return `Review: ${plural(suggestions, 'suggestion')} to check`
  if (unmatched) return `Review: ready to sign off (${unmatched.toLocaleString('en-US')} unmatched)`
  return 'Review: ready to sign off'
}

export function draftItem(d: DraftRecord): ReconListItem {
  return {
    id: d.id,
    kind: 'draft',
    status: 'draft',
    moduleId: d.moduleId,
    accountLabel: d.accountLabel,
    period: d.period,
    sides: `${d.sideAName} vs ${d.sideBName}`,
    files: `${d.files.A?.fileName ?? '—'} vs ${d.files.B?.fileName ?? '—'}`,
    stage: draftStage(d),
    createdAt: d.createdAt,
    updatedAt: d.updatedAt,
    finalised: null
  }
}

export function sessionItem(s: SessionSummary): ReconListItem {
  return {
    id: s.id,
    kind: 'session',
    status: s.finalised ? 'finalised' : 'review',
    moduleId: s.moduleId,
    accountLabel: s.accountLabel,
    period: s.period,
    sides: `${s.sideAName} vs ${s.sideBName}`,
    files: `${s.fileA} vs ${s.fileB}`,
    stage: sessionStage(s),
    createdAt: s.createdAt,
    updatedAt: s.updatedAt,
    finalised: s.finalised,
    stats: s.stats,
    preparer: s.preparer,
    toReview: s.open.doubtful + s.open.likely + s.open.suggestions
  }
}

/**
 * Every draft and session as one list, most recently updated first. A draft and a session never share an id
 * (the draft record is removed when it becomes a session); if one is ever left behind, the session wins.
 */
export function reconItems(drafts: DraftRecord[], sessions: SessionSummary[]): ReconListItem[] {
  const sessionIds = new Set(sessions.map((s) => s.id))
  return [...sessions.map(sessionItem), ...drafts.filter((d) => !sessionIds.has(d.id)).map(draftItem)].sort((a, b) =>
    b.updatedAt.localeCompare(a.updatedAt)
  )
}

/** Only the unfinished ones (drafts and sessions in review), optionally for one module. */
export function unfinishedItems(items: ReconListItem[], moduleId?: ModuleId): ReconListItem[] {
  return items.filter((i) => i.status !== 'finalised' && (!moduleId || i.moduleId === moduleId))
}

/** Unfinished reconciliations per module. */
export function countByModule(items: ReconListItem[]): Partial<Record<ModuleId, number>> {
  const out: Partial<Record<ModuleId, number>> = {}
  for (const i of unfinishedItems(items)) out[i.moduleId] = (out[i.moduleId] ?? 0) + 1
  return out
}

/** The wizard link that opens this reconciliation. */
export function reconLink(item: Pick<ReconListItem, 'id' | 'kind' | 'moduleId'>): string {
  return `/module/${item.moduleId}?${item.kind}=${encodeURIComponent(item.id)}`
}

/** Every draft and saved session (summaries only), newest first. */
export async function loadReconItems(): Promise<ReconListItem[]> {
  const [drafts, sessions] = await Promise.all([listDrafts(), listSessionSummaries()])
  return reconItems(drafts, sessions)
}

/** Unfinished reconciliations, newest first; one module's when `moduleId` is given. */
export async function loadInProgress(moduleId?: ModuleId): Promise<ReconListItem[]> {
  return unfinishedItems(await loadReconItems(), moduleId)
}

export const STATUS_LABEL: Record<ReconStatus, string> = { draft: 'Draft', review: 'In review', finalised: 'Finalised' }

/** "18-Oct-2026 14:05" (local time), or '' for a missing date. */
export function formatWhen(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : `${formatDate(d)} ${d.toTimeString().slice(0, 5)}`
}

/**
 * The reconciliation on screen as a list item (its latest save may still be on the way), or null when there is
 * nothing to list yet (no file read) or it is finalised.
 */
export function itemFromState(s: WizardState, now: string): ReconListItem | null {
  if (s.session) return s.session.finalised ? null : sessionItem(summariseSession(s.session))
  const d = draftFromState(s, now)
  return d ? draftItem(d) : null
}

/** The module's unfinished list with the on-screen reconciliation first (its newest state replaces the stored one). */
export function withCurrent(items: ReconListItem[], current: ReconListItem | null, currentId: string): ReconListItem[] {
  const others = items.filter((i) => i.id !== currentId && i.id !== current?.id)
  return current ? [current, ...others] : others
}
