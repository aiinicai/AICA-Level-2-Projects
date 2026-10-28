import { openDB, type DBSchema, type IDBPDatabase, type IDBPTransaction, type StoreNames } from 'idb'
import type { HistoryEntry } from '@shared/kpis'
import type { EngineLine, GeneralTemplate, ParsedTable, ReconConfig, ReconSession, ReconStats, SavedMapping, ToolRecipe, WorkbookData } from '@shared/contracts'
import type { ModuleId } from '@shared/modules'

// Everything Reco-Do remembers lives in this local database inside the app's user-data folder.
// Nothing here is ever sent anywhere.

export interface Settings {
  preparerName: string
  department: string
  currency: string
  /** Claude model used by Smart Recon. */
  aiModel: string
  /** Default for the "Mask party names before sending" Smart Recon option. */
  maskPartiesDefault: boolean
  /** AI service Smart Recon sends to (Anthropic unless changed in Settings). */
  aiProvider: import('@shared/contracts').AiProvider
  /** Model per provider; an empty or missing entry means that provider's default (aiModel is the Anthropic one). */
  aiModels: Partial<Record<import('@shared/contracts').AiProvider, string>>
  /** Base URL of the "Other (OpenAI-compatible)" provider, e.g. http://localhost:1234/v1. */
  aiBaseUrl: string
}

export const DEFAULT_AI_MODEL = 'claude-sonnet-5-5'

export const DEFAULT_SETTINGS: Settings = {
  preparerName: '',
  department: '',
  currency: 'AED',
  aiModel: DEFAULT_AI_MODEL,
  maskPartiesDefault: false,
  aiProvider: 'anthropic',
  aiModels: {},
  aiBaseUrl: ''
}

export const DB_NAME = 'reco-do'
export const DB_VERSION = 4

/** The heavy, never-changing part of a session (every line of both files), stored once per session. */
interface StoredLines {
  id: string
  linesA: EngineLine[]
  linesB: EngineLine[]
}

/** One source file as the wizard read it: the workbook, the sheet and header row chosen, and the parsed table. */
export interface SourceFile {
  fileName: string
  size: number
  workbook: WorkbookData & { warnings?: string[] }
  sheetIndex: number
  detectedHeaderRow: number
  table: ParsedTable
}

export interface SourceFiles {
  A: SourceFile | null
  B: SourceFile | null
}

/** The source files of a draft or session (same id), stored apart so the small records stay quick to save. */
interface StoredSources extends SourceFiles {
  id: string
}

/**
 * A small summary of a saved session for lists (In progress menu, Dashboard), written with every save so lists
 * never have to read the full sessions.
 */
export interface SessionSummary {
  id: string
  moduleId: ModuleId
  accountLabel: string
  period: string
  sideAName: string
  sideBName: string
  fileA: string
  fileB: string
  preparer: string
  createdAt: string
  updatedAt: string
  finalised: { by: string; at: string } | null
  /** Doubtful / Likely lines still to decide (File A, as on the KPI cards), open Smart Recon suggestions, unmatched lines. */
  open: { doubtful: number; likely: number; suggestions: number; unmatched: number }
  stats: ReconStats
}

/** Light description of a source file kept on the draft record (for lists). */
export interface DraftFileInfo {
  fileName: string
  sheetName: string
  rows: number
}

/**
 * A reconciliation that has not been run yet (Upload / Map & rules). The files themselves are in `sourceTables`
 * under the same id; when Reconcile runs, the draft becomes a session with that id and the draft record goes.
 */
export interface DraftRecord {
  id: string
  moduleId: ModuleId
  createdAt: string
  updatedAt: string
  /** 0 Upload or 1 Map & rules. */
  step: 0 | 1
  sideAName: string
  sideBName: string
  accountLabel: string
  period: string
  accountTouched: boolean
  periodTouched: boolean
  config: ReconConfig | null
  configSource: { kind: 'suggested' } | { kind: 'mapping'; name: string } | { kind: 'template'; name: string } | null
  files: { A: DraftFileInfo | null; B: DraftFileInfo | null }
}

interface RecoDoDB extends DBSchema {
  settings: { key: string; value: Partial<Settings> }
  history: { key: string; value: HistoryEntry; indexes: { finishedAt: string } }
  /** Sessions without their lines (`result.linesA` / `result.linesB` are empty here; see `sessionLines`). */
  sessions: { key: string; value: ReconSession; indexes: { updatedAt: string } }
  sessionLines: { key: string; value: StoredLines }
  mappings: { key: string; value: SavedMapping; indexes: { moduleId: ModuleId } }
  templates: { key: string; value: GeneralTemplate; indexes: { updatedAt: string } }
  recipes: { key: string; value: ToolRecipe; indexes: { tool: string } }
  /** Reconciliations not run yet (version 4). */
  drafts: { key: string; value: DraftRecord; indexes: { updatedAt: string; moduleId: ModuleId } }
  /** Source files of drafts and sessions, keyed by the draft / session id (version 4). */
  sourceTables: { key: string; value: StoredSources }
  /** One small summary per session (version 4). */
  sessionSummaries: { key: string; value: SessionSummary }
}

const SETTINGS_KEY = 'app'

/** How long to wait for another Reco-Do window to let go of the database before explaining the delay. */
const BLOCKED_TIMEOUT_MS = 5_000

/** A database failure in plain English. `detail` keeps the browser's own (technical) message. */
export class DatabaseError extends Error {
  readonly detail: string
  constructor(message: string, detail: string) {
    super(message)
    this.name = 'DatabaseError'
    this.detail = detail
  }
}

function errorName(err: unknown): string {
  return err instanceof Error || (typeof DOMException !== 'undefined' && err instanceof DOMException) ? (err as Error).name : ''
}

/** Turns IndexedDB failures (DOMExceptions with technical text) into plain English. */
export function friendlyDbError(err: unknown): Error {
  if (err instanceof DatabaseError) return err
  const name = errorName(err)
  const detail = err instanceof Error ? `${err.name}: ${err.message}` : String(err)
  switch (name) {
    case 'VersionError':
      return new DatabaseError('Your saved data was created by a newer version of Reco-Do. Install the latest version to open it.', detail)
    case 'QuotaExceededError':
      return new DatabaseError('There is not enough free disk space to save. Free up some space on this computer and try again.', detail)
    case 'InvalidStateError':
    case 'TransactionInactiveError':
      return new DatabaseError('The connection to your saved data was interrupted. Please try again.', detail)
    case 'AbortError':
      return new DatabaseError('Saving was interrupted before it finished. Please try again.', detail)
    case 'DataCloneError':
      return new DatabaseError('This item contains data that cannot be saved. Please try again; if it keeps happening, start a new reconciliation.', detail)
    case 'UnknownError':
    case 'NotFoundError':
      return new DatabaseError('Your saved data could not be read. Restart Reco-Do and try again.', detail)
    default:
      // Our own plain-English errors (e.g. the history-id check) pass through unchanged.
      if (err instanceof Error && err.name === 'Error' && err.message) return err
      return new DatabaseError('Your saved data could not be reached. Please try again.', detail)
  }
}

let dbPromise: Promise<IDBPDatabase<RecoDoDB>> | null = null

type UpgradeTx = IDBPTransaction<RecoDoDB, ArrayLike<StoreNames<RecoDoDB>>, 'versionchange'>

/** Moves the lines of every version-2 session into `sessionLines`, leaving a light session behind. */
async function migrateSessionLines(tx: UpgradeTx): Promise<void> {
  const lines = tx.objectStore('sessionLines')
  let cursor = await tx.objectStore('sessions').openCursor()
  while (cursor) {
    const s = cursor.value
    await lines.put({ id: s.id, linesA: s.result.linesA ?? [], linesB: s.result.linesB ?? [] })
    await cursor.update(lightSession(s))
    cursor = await cursor.continue()
  }
}

/** Writes a summary for every session saved before version 4. */
async function buildSessionSummaries(tx: UpgradeTx): Promise<void> {
  const summaries = tx.objectStore('sessionSummaries')
  let cursor = await tx.objectStore('sessions').openCursor()
  while (cursor) {
    await summaries.put(summariseSession(cursor.value))
    cursor = await cursor.continue()
  }
}

/** The list summary of a session. */
export function summariseSession(s: ReconSession): SessionSummary {
  const cfg = s.result.config
  return {
    id: s.id,
    moduleId: cfg.moduleId,
    accountLabel: s.meta.accountLabel,
    period: s.meta.period,
    sideAName: cfg.sideAName,
    sideBName: cfg.sideBName,
    fileA: s.meta.fileA.name,
    fileB: s.meta.fileB.name,
    preparer: s.meta.preparer,
    createdAt: s.createdAt,
    updatedAt: s.updatedAt,
    finalised: s.finalised,
    open: {
      // File A lines still Doubtful / Likely, as on the results screen's KPI cards.
      doubtful: s.result.stats.doubtful,
      likely: s.result.stats.likely,
      suggestions: s.suggestions.filter((x) => x.status === 'open').length,
      unmatched: s.result.unmatchedA.length + s.result.unmatchedB.length
    },
    stats: s.result.stats
  }
}

function openDatabase(): Promise<IDBPDatabase<RecoDoDB>> {
  return new Promise<IDBPDatabase<RecoDoDB>>((resolve, reject) => {
    let settled = false
    let blockedTimer: ReturnType<typeof setTimeout> | undefined
    const opening = openDB<RecoDoDB>(DB_NAME, DB_VERSION, {
      upgrade(database, oldVersion, _newVersion, tx) {
        // Version 1: settings + history (first release of the dashboard).
        if (oldVersion < 1) {
          database.createObjectStore('history', { keyPath: 'id' })
          database.createObjectStore('settings')
        }
        // Version 2: sessions, mappings, templates, recipes and indexes. Version 1 data is kept as is.
        if (oldVersion < 2) {
          tx.objectStore('history').createIndex('finishedAt', 'finishedAt')
          database.createObjectStore('sessions', { keyPath: 'id' }).createIndex('updatedAt', 'updatedAt')
          database.createObjectStore('mappings', { keyPath: 'id' }).createIndex('moduleId', 'moduleId')
          database.createObjectStore('templates', { keyPath: 'id' }).createIndex('updatedAt', 'updatedAt')
          database.createObjectStore('recipes', { keyPath: 'id' }).createIndex('tool', 'tool')
        }
        // Version 3: the lines of each session move to their own store, so a review decision saves only the
        // small, changing part of the session.
        if (oldVersion < 3) {
          database.createObjectStore('sessionLines', { keyPath: 'id' })
          if (oldVersion >= 2) {
            migrateSessionLines(tx).catch(() => {
              // Keep version 2 untouched rather than half-migrated sessions; the open then fails cleanly.
              try {
                tx.abort()
              } catch {
                // the upgrade already finished or failed
              }
            })
          }
        }
        // Version 4: unfinished (not yet run) reconciliations and the source files of drafts and sessions, so
        // several reconciliations can be kept open and a saved one can go back to Map & rules. Existing data stays.
        if (oldVersion < 4) {
          const drafts = database.createObjectStore('drafts', { keyPath: 'id' })
          drafts.createIndex('updatedAt', 'updatedAt')
          drafts.createIndex('moduleId', 'moduleId')
          database.createObjectStore('sourceTables', { keyPath: 'id' })
          database.createObjectStore('sessionSummaries', { keyPath: 'id' })
          if (oldVersion >= 2) {
            buildSessionSummaries(tx).catch(() => {
              try {
                tx.abort()
              } catch {
                // the upgrade already finished or failed
              }
            })
          }
        }
      },
      blocked() {
        // An older connection (another Reco-Do window) is still open. Give it a moment, then explain.
        blockedTimer = setTimeout(() => {
          if (settled) return
          settled = true
          reject(new DatabaseError('Your saved data is in use by another Reco-Do window. Close the other window and try again.', 'IndexedDB open blocked'))
        }, BLOCKED_TIMEOUT_MS)
      },
      blocking() {
        // A newer copy of the app wants to upgrade the database: let it.
        void dbPromise?.then((d) => d.close()).catch(() => undefined)
        dbPromise = null
      },
      terminated() {
        // The browser closed the connection abnormally (e.g. the disk went away): open a fresh one next time.
        dbPromise = null
      }
    })
    opening.then(
      (d) => {
        if (blockedTimer) clearTimeout(blockedTimer)
        if (settled) {
          d.close() // this open was already given up on
          return
        }
        settled = true
        resolve(d)
      },
      (err: unknown) => {
        if (blockedTimer) clearTimeout(blockedTimer)
        if (settled) return
        settled = true
        reject(friendlyDbError(err))
      }
    )
  })
}

function db(): Promise<IDBPDatabase<RecoDoDB>> {
  if (!dbPromise) {
    const p = openDatabase()
    dbPromise = p
    // A failed open is not remembered: the next call tries again.
    p.catch(() => {
      if (dbPromise === p) dbPromise = null
    })
  }
  return dbPromise
}

/** Runs one database operation, turning failures into plain-English errors. */
async function run<T>(op: (d: IDBPDatabase<RecoDoDB>) => Promise<T>): Promise<T> {
  try {
    return await op(await db())
  } catch (err) {
    throw friendlyDbError(err)
  }
}

/** Closes the connection (used by tests and before deleting the database). */
export async function closeDb(): Promise<void> {
  storedLines.clear()
  storedSources.clear()
  const p = dbPromise
  dbPromise = null
  if (!p) return
  try {
    const d = await p
    d.close()
  } catch {
    // the open had failed; nothing to close
  }
}

const byUpdatedDesc = <T extends { updatedAt: string }>(a: T, b: T): number => b.updatedAt.localeCompare(a.updatedAt)

/** Unique id for new records. */
export function newId(): string {
  return crypto.randomUUID()
}

// ───────────────────────── Settings ─────────────────────────

export async function getSettings(): Promise<Settings> {
  const stored = (await run((d) => d.get('settings', SETTINGS_KEY))) ?? {}
  return { ...DEFAULT_SETTINGS, ...stored }
}

/** Saves a partial update and returns the full, merged settings (read and write in one transaction). */
export async function saveSettings(patch: Partial<Settings>): Promise<Settings> {
  return run(async (d) => {
    const tx = d.transaction('settings', 'readwrite')
    const stored = (await tx.store.get(SETTINGS_KEY)) ?? {}
    const next: Settings = { ...DEFAULT_SETTINGS, ...stored, ...patch }
    await Promise.all([tx.store.put(next, SETTINGS_KEY), tx.done])
    return next
  })
}

// ───────────────────────── History and sessions ─────────────────────────

/** Recon history, newest first. */
export async function listHistory(): Promise<HistoryEntry[]> {
  const all = await run((d) => d.getAll('history'))
  return all.sort((a, b) => b.finishedAt.localeCompare(a.finishedAt))
}

/** The session as kept in the `sessions` store: everything except the lines. */
function lightSession(s: ReconSession): ReconSession {
  return { ...s, result: { ...s.result, linesA: [], linesB: [] } }
}

/**
 * The line arrays last written (or read) per session id. Review decisions never change the lines (the engine
 * keeps the same arrays), so while a session still holds them only its light part is written again.
 */
const storedLines = new Map<string, { a: EngineLine[]; b: EngineLine[] }>()

/**
 * The source files last written (or read) per draft / session id. A draft is saved after every change, but its
 * files change rarely, so they are written again only when they are different objects.
 */
const storedSources = new Map<string, SourceFiles>()

function sameSources(id: string, sources: SourceFiles): boolean {
  const known = storedSources.get(id)
  return !!known && known.A === sources.A && known.B === sources.B
}

function sourcesRecord(id: string, sources: SourceFiles): StoredSources {
  return { id, A: sources.A, B: sources.B }
}

/**
 * Saves the session and its history row in one transaction. The lines are written only when they are new
 * (first save, a re-run, or missing from the database); a review decision writes just the small part.
 * `sources` (the files the session was run on) are written when given and new. Any draft with the same id is
 * removed in the same transaction: once Reconcile has run, the draft has become this session.
 */
export async function saveSession(session: ReconSession, historyEntry: HistoryEntry, opts: { sources?: SourceFiles } = {}): Promise<void> {
  if (historyEntry.id !== session.id) throw new Error('The history entry must have the same id as the session.')
  const known = storedLines.get(session.id)
  const sameLines = !!known && known.a === session.result.linesA && known.b === session.result.linesB
  const sources = opts.sources && !sameSources(session.id, opts.sources) ? opts.sources : undefined
  await run(async (d) => {
    const tx = d.transaction(['sessions', 'sessionLines', 'history', 'drafts', 'sourceTables', 'sessionSummaries'], 'readwrite')
    const lines = tx.objectStore('sessionLines')
    const record: StoredLines = { id: session.id, linesA: session.result.linesA, linesB: session.result.linesB }
    const writes: Promise<unknown>[] = [
      tx.objectStore('sessions').put(lightSession(session)),
      tx.objectStore('history').put(historyEntry),
      tx.objectStore('drafts').delete(session.id),
      tx.objectStore('sessionSummaries').put(summariseSession(session))
    ]
    if (!sameLines) writes.push(lines.put(record))
    else {
      // Cheap safety net: if the lines are missing (e.g. removed elsewhere), write them after all.
      writes.push(lines.getKey(session.id).then((k) => (k === undefined ? lines.put(record) : undefined)))
    }
    const srcStore = tx.objectStore('sourceTables')
    if (sources) writes.push(srcStore.put(sourcesRecord(session.id, sources)))
    else if (opts.sources) {
      // Same safety net for the files: write them if they went missing.
      const given = opts.sources
      writes.push(srcStore.getKey(session.id).then((k) => (k === undefined ? srcStore.put(sourcesRecord(session.id, given)) : undefined)))
    }
    await Promise.all([...writes, tx.done])
  })
  storedLines.set(session.id, { a: session.result.linesA, b: session.result.linesB })
  if (opts.sources) storedSources.set(session.id, opts.sources)
}

/** Summaries of every saved session, most recently updated first (cheap: no pairs or lines are read). */
export async function listSessionSummaries(): Promise<SessionSummary[]> {
  return (await run((d) => d.getAll('sessionSummaries'))).sort(byUpdatedDesc)
}

/** The source files kept with a draft or session, or undefined (sessions saved before version 4 have none). */
export async function getSources(id: string): Promise<SourceFiles | undefined> {
  const rec = await run((d) => d.get('sourceTables', id))
  if (!rec || (!rec.A && !rec.B)) return undefined
  const sources: SourceFiles = { A: rec.A, B: rec.B }
  storedSources.set(id, sources)
  return sources
}

/** Ids of every draft and session that has its source files stored. */
export async function listSourceIds(): Promise<Set<string>> {
  return new Set(await run((d) => d.getAllKeys('sourceTables')))
}

/** The full session, lines included. */
export async function getSession(id: string): Promise<ReconSession | undefined> {
  const found = await run(async (d) => {
    const tx = d.transaction(['sessions', 'sessionLines'], 'readonly')
    const [s, lines] = await Promise.all([tx.objectStore('sessions').get(id), tx.objectStore('sessionLines').get(id), tx.done])
    return s ? { s, lines } : undefined
  })
  if (!found) return undefined
  const { s, lines } = found
  if (!lines) return s
  storedLines.set(id, { a: lines.linesA, b: lines.linesB })
  return { ...s, result: { ...s.result, linesA: lines.linesA, linesB: lines.linesB } }
}

/**
 * All saved sessions, most recently updated first. For speed the lines are left out (`result.linesA` and
 * `result.linesB` are empty) unless `withLines` is set: lists only need the meta, config and stats.
 */
export async function listSessions(opts: { withLines?: boolean } = {}): Promise<ReconSession[]> {
  const all = (await run((d) => d.getAll('sessions'))).sort(byUpdatedDesc)
  if (!opts.withLines) return all
  const full = await Promise.all(all.map((s) => getSession(s.id)))
  return full.filter((s): s is ReconSession => !!s)
}

/** True when a session with this id is saved. */
export async function sessionExists(id: string): Promise<boolean> {
  return (await run((d) => d.getKey('sessions', id))) !== undefined
}

/** Deletes a session, its lines, its source files, any draft with its id and its history row. */
export async function deleteSession(id: string): Promise<void> {
  await run(async (d) => {
    const tx = d.transaction(['sessions', 'sessionLines', 'history', 'drafts', 'sourceTables', 'sessionSummaries'], 'readwrite')
    await Promise.all([
      tx.objectStore('sessionSummaries').delete(id),
      tx.objectStore('sessions').delete(id),
      tx.objectStore('sessionLines').delete(id),
      tx.objectStore('history').delete(id),
      tx.objectStore('drafts').delete(id),
      tx.objectStore('sourceTables').delete(id),
      tx.done
    ])
  })
  storedLines.delete(id)
  storedSources.delete(id)
}

// ───────────────────────── Drafts (reconciliations not run yet) ─────────────────────────

/**
 * Saves a draft and, when they changed, its source files, in one transaction. The first save's `createdAt` is
 * kept. With no files at all the stored files are removed.
 */
export async function saveDraft(draft: DraftRecord, sources: SourceFiles): Promise<void> {
  const writeSources = !sameSources(draft.id, sources)
  const empty = !sources.A && !sources.B
  await run(async (d) => {
    const tx = d.transaction(['drafts', 'sourceTables'], 'readwrite')
    const store = tx.objectStore('drafts')
    const writes: Promise<unknown>[] = [
      store.get(draft.id).then((old) => store.put(old ? { ...draft, createdAt: old.createdAt } : draft))
    ]
    if (writeSources) writes.push(empty ? tx.objectStore('sourceTables').delete(draft.id) : tx.objectStore('sourceTables').put(sourcesRecord(draft.id, sources)))
    await Promise.all([...writes, tx.done])
  })
  if (writeSources) storedSources.set(draft.id, sources)
}

/** A draft with its source files. */
export async function getDraft(id: string): Promise<{ draft: DraftRecord; sources: SourceFiles } | undefined> {
  const found = await run(async (d) => {
    const tx = d.transaction(['drafts', 'sourceTables'], 'readonly')
    const [draft, rec] = await Promise.all([tx.objectStore('drafts').get(id), tx.objectStore('sourceTables').get(id), tx.done])
    return draft ? { draft, rec } : undefined
  })
  if (!found) return undefined
  const sources: SourceFiles = { A: found.rec?.A ?? null, B: found.rec?.B ?? null }
  storedSources.set(id, sources)
  return { draft: found.draft, sources }
}

/** Drafts (without their files), most recently updated first; only one module's when `moduleId` is given. */
export async function listDrafts(moduleId?: ModuleId): Promise<DraftRecord[]> {
  const rows = await run((d) => (moduleId ? d.getAllFromIndex('drafts', 'moduleId', moduleId) : d.getAll('drafts')))
  return rows.sort(byUpdatedDesc)
}

/** Deletes a draft and its source files (the files stay when a session with the same id still uses them). */
export async function deleteDraft(id: string): Promise<void> {
  await run(async (d) => {
    const tx = d.transaction(['drafts', 'sourceTables', 'sessions'], 'readwrite')
    const sessionKey = await tx.objectStore('sessions').getKey(id)
    const writes: Promise<unknown>[] = [tx.objectStore('drafts').delete(id)]
    if (sessionKey === undefined) writes.push(tx.objectStore('sourceTables').delete(id))
    await Promise.all([...writes, tx.done])
    if (sessionKey === undefined) storedSources.delete(id)
  })
}

// ───────────────────────── Saved mappings ─────────────────────────

export async function listMappings(moduleId?: ModuleId): Promise<SavedMapping[]> {
  const rows = await run((d) => (moduleId ? d.getAllFromIndex('mappings', 'moduleId', moduleId) : d.getAll('mappings')))
  return rows.sort(byUpdatedDesc)
}

export async function saveMapping(mapping: SavedMapping): Promise<void> {
  await run((d) => d.put('mappings', mapping))
}

export async function deleteMapping(id: string): Promise<void> {
  await run((d) => d.delete('mappings', id))
}

function sortedHeaderKey(headers: string[]): string {
  return headers
    .map((h) => h.trim().toLowerCase())
    .sort()
    .join('\u0001')
}

/**
 * Finds a saved mapping for the same pair of files (same headers, in any order, ignoring case and outer spaces).
 * Also matches when the files were loaded the other way round. Returns the most recently updated match.
 */
export async function findMappingByHeaders(moduleId: ModuleId, headersA: string[], headersB: string[]): Promise<SavedMapping | undefined> {
  const a = sortedHeaderKey(headersA)
  const b = sortedHeaderKey(headersB)
  const candidates = await listMappings(moduleId)
  return (
    candidates.find((m) => sortedHeaderKey(m.headersA) === a && sortedHeaderKey(m.headersB) === b) ??
    candidates.find((m) => sortedHeaderKey(m.headersA) === b && sortedHeaderKey(m.headersB) === a)
  )
}

// ───────────────────────── General templates ─────────────────────────

/** General Reconciliation templates, most recently updated first. */
export async function listTemplates(): Promise<GeneralTemplate[]> {
  return (await run((d) => d.getAll('templates'))).sort(byUpdatedDesc)
}

export async function saveTemplate(template: GeneralTemplate): Promise<void> {
  await run((d) => d.put('templates', template))
}

export async function deleteTemplate(id: string): Promise<void> {
  await run((d) => d.delete('templates', id))
}

// ───────────────────────── Tool recipes ─────────────────────────

export async function listRecipes(tool?: ToolRecipe['tool']): Promise<ToolRecipe[]> {
  const rows = await run((d) => (tool ? d.getAllFromIndex('recipes', 'tool', tool) : d.getAll('recipes')))
  return rows.sort(byUpdatedDesc)
}

export async function saveRecipe(recipe: ToolRecipe): Promise<void> {
  await run((d) => d.put('recipes', recipe))
}

export async function deleteRecipe(id: string): Promise<void> {
  await run((d) => d.delete('recipes', id))
}
