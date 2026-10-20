// The wizard store: React context + reducer, plus the side effects (file reading, auto-mapping, running the
// engine, saving the draft after every change and the session after every decision).
// `WizardHost` decides which reconciliation of the module is on screen (several can be open; see openRecons.ts)
// and mounts one `WizardProvider` per reconciliation.

import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { OpenedFile, ReconSession, Side } from '@shared/contracts'
import { getModule, type ModuleConfig, type ModuleId } from '@shared/modules'
import { createSession, validateConfig } from '@engine/index'
import { useConfirm, useToast } from '@/components/ui'
import { DEFAULT_SETTINGS, findMappingByHeaders, getDraft, getSession, getSettings, getSources, newId, saveSettings, type Settings, type SourceFiles } from '@/lib/db'
import { closeDraftSaves, flushDraftSaves, persistDraft, removeDraftLater, reopenDraftSaves } from '@/lib/draftSaves'
import { flushSessionSaves, persistSession } from '@/lib/sessionSaves'
import { errorMessage } from '@/lib/useAsync'
import { buildMeta, configFromSaved, finalConfig, suggestedConfig } from './configFactory'
import { draftFromState, filesFromSources, sourcesFromState, stateFromDraft } from './draftState'
import { guessAccountLabel, guessPeriod, pickSampleFiles, type SampleSet } from './helpers'
import type { ReconKind } from './inProgress'
import { forgetRecon, recallWizard, rememberWizard, setShownRecon, shownRecon } from './openRecons'
import { initialState, wizardReducer } from './reducer'
import { runReconcile } from './run/runReconcile'
import type { WizardAction, WizardState } from './types'
import { parseSheet } from './upload/loadFile'
import { readUploadAsync } from './upload/readUploadAsync'
import { PreparerDialog } from './PreparerDialog'

/** A failed draft save is reported at most this often (a draft is saved after every change). */
const DRAFT_ERROR_INTERVAL_MS = 30_000

const WRONG_MODULE = 'This reconciliation belongs to a different module. Open it from Recon History.'

export interface CommitOptions {
  /** When the save fails, put the screen back to the last saved version (review decisions). Default false. */
  revertOnFail?: boolean
  /** The files the session was run on, stored with it (first save after a run). */
  sources?: SourceFiles
}

// ───────────────────────── Which reconciliation is on screen ─────────────────────────

export interface ReconSlotApi {
  /** Id of the reconciliation on screen. */
  reconId: string
  /** Starts a fresh reconciliation for this module; the current one stays saved (as a draft or session). */
  newRecon: (opts?: { quiet?: boolean }) => void
  /** Switches to another draft or session of this module. */
  openRecon: (item: { id: string; kind: ReconKind }) => void
  /** Whether the In progress menu is open (the Dashboard can ask for it to open). */
  menuOpen: boolean
  setMenuOpen: (open: boolean) => void
}

const ReconSlotContext = createContext<ReconSlotApi | null>(null)

/** Internal: lets the provider report that its reconciliation continues under a new id. */
const ReconIdChangeContext = createContext<((id: string) => void) | null>(null)

export function useReconSlot(): ReconSlotApi {
  const ctx = useContext(ReconSlotContext)
  if (!ctx) throw new Error('useReconSlot must be used inside <WizardHost>.')
  return ctx
}

interface Slot {
  id: string
  /** Read it from the database first (opened from a link or the In progress menu, and not in memory). */
  load: ReconKind | null
  /** Changes whenever another reconciliation is put on screen, so its provider mounts fresh. */
  key: number
}

let slotSeq = 0

function targetOf(params: URLSearchParams): { id: string; kind: ReconKind } | null {
  const session = params.get('session')
  if (session) return { id: session, kind: 'session' }
  const draft = params.get('draft')
  return draft ? { id: draft, kind: 'draft' } : null
}

function slotFor(target: { id: string; kind: ReconKind }): Slot {
  return { id: target.id, load: recallWizard(target.id) ? null : target.kind, key: ++slotSeq }
}

/**
 * Picks the reconciliation of the module to show: `?session=<id>` / `?draft=<id>` when given, else the one this
 * module showed last in this window, else a new one. `?inprogress=1` opens the In progress menu.
 */
export function WizardHost({ moduleId, children }: { moduleId: ModuleId; children: React.ReactNode }): React.JSX.Element {
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const [slot, setSlot] = useState<Slot>(() => {
    const t = targetOf(params)
    return t ? slotFor(t) : { id: shownRecon(moduleId) ?? newId(), load: null, key: ++slotSeq }
  })
  const slotRef = useRef(slot)
  slotRef.current = slot
  const [menuOpen, setMenuOpen] = useState(params.get('inprogress') === '1')

  const target = targetOf(params)
  const targetId = target?.id ?? null
  const targetKind = target?.kind ?? null
  useEffect(() => {
    // A link to another reconciliation while this page is open (In progress menu, Dashboard, Recon History).
    if (!targetId || !targetKind || targetId === slotRef.current.id) return
    setSlot(slotFor({ id: targetId, kind: targetKind }))
  }, [targetId, targetKind])

  useEffect(() => {
    setShownRecon(moduleId, slot.id)
  }, [moduleId, slot.id])

  useEffect(() => {
    if (params.get('inprogress') !== '1') return
    setMenuOpen(true)
    const next = new URLSearchParams(params)
    next.delete('inprogress')
    setParams(next, { replace: true })
  }, [params, setParams])

  const newRecon = useCallback(
    (opts: { quiet?: boolean } = {}) => {
      const current = recallWizard(slotRef.current.id)
      if (!opts.quiet && current) {
        if (!current.session && (current.files.A || current.files.B)) toast.success('Saved as draft — find it under In progress')
        else if (current.session && !current.session.finalised) toast.success('Saved — find it under In progress')
      }
      setMenuOpen(false)
      setParams({}, { replace: true })
      setSlot({ id: newId(), load: null, key: ++slotSeq })
    },
    [setParams, toast]
  )

  const openRecon = useCallback(
    (item: { id: string; kind: ReconKind }) => {
      setMenuOpen(false)
      if (item.id === slotRef.current.id) return
      setParams({ [item.kind]: item.id })
    },
    [setParams]
  )

  const onReconIdChange = useCallback((id: string) => {
    // Same provider, new id (new files after a run, or a re-run of a finalised one): no remount.
    setSlot((s) => (s.id === id ? s : { ...s, id }))
  }, [])

  const api = useMemo<ReconSlotApi>(() => ({ reconId: slot.id, newRecon, openRecon, menuOpen, setMenuOpen }), [slot.id, newRecon, openRecon, menuOpen])

  return (
    <ReconSlotContext.Provider value={api}>
      <ReconIdChangeContext.Provider value={onReconIdChange}>
        <WizardProvider key={slot.key} moduleId={moduleId} reconId={slot.id} load={slot.load}>
          {children}
        </WizardProvider>
      </ReconIdChangeContext.Provider>
    </ReconSlotContext.Provider>
  )
}

// ───────────────────────── One reconciliation ─────────────────────────

export interface WizardApi {
  state: WizardState
  dispatch: React.Dispatch<WizardAction>
  module: ModuleConfig
  settings: Settings
  /** Validation errors of the current configuration ([] = ready to run). */
  configErrors: string[]
  busy: Record<Side, boolean>
  fileErrors: Record<Side, string | null>
  loadFile: (side: Side, file: OpenedFile) => Promise<void>
  clearFile: (side: Side) => void
  changeSheet: (side: Side, sheetIndex: number) => void
  changeHeaderRow: (side: Side, headerRowIndex: number | null) => void
  loadSampleSet: (set: SampleSet) => Promise<void>
  resuming: boolean
  resumeError: string | null
  running: boolean
  runError: string | null
  run: () => Promise<void>
  /** Saves a new version of the session (state + IndexedDB). Resolves true once it is saved, false if it failed. */
  commit: (next: ReconSession, opts?: CommitOptions) => Promise<boolean>
  /** The newest session, including changes not yet rendered. Read it after an await instead of `state.session`. */
  latestSession: () => ReconSession | null
  /** Runs a review decision with the preparer's name; engine errors become toasts. */
  act: (fn: (s: ReconSession, user: string) => ReconSession, success?: string) => Promise<boolean>
  /** The preparer name from Settings, asking for it (and saving it) the first time. */
  ensureUser: () => Promise<string | null>
  /** Starts a new reconciliation; this one stays saved. */
  startNew: () => void
}

const WizardContext = createContext<WizardApi | null>(null)

export function useWizard(): WizardApi {
  const ctx = useContext(WizardContext)
  if (!ctx) throw new Error('useWizard must be used inside <WizardProvider>.')
  return ctx
}

export function WizardProvider({
  moduleId,
  reconId,
  load,
  children
}: {
  moduleId: ModuleId
  reconId: string
  /** Read this draft / session from the database on mount (it is not in memory). */
  load: ReconKind | null
  children: React.ReactNode
}): React.JSX.Element {
  const module = getModule(moduleId) as ModuleConfig
  const toast = useToast()
  const confirm = useConfirm()
  const slot = useContext(ReconSlotContext)
  const onReconIdChange = useContext(ReconIdChangeContext)
  const [params, setParams] = useSearchParams()
  const [recalled] = useState(() => recallWizard(reconId))
  const [state, dispatch] = useReducer(wizardReducer, null, () => recalled ?? initialState(moduleId, reconId))
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS)
  const settingsRef = useRef(settings)
  settingsRef.current = settings
  const stateRef = useRef(state)
  stateRef.current = state
  const sessionRef = useRef<ReconSession | null>(state.session)
  /** The last version known to be in IndexedDB (to undo a decision whose save failed). */
  const savedRef = useRef<ReconSession | null>(state.session)

  const [busy, setBusy] = useState<Record<Side, boolean>>({ A: false, B: false })
  const [fileErrors, setFileErrors] = useState<Record<Side, string | null>>({ A: null, B: null })
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)
  const [resuming, setResuming] = useState(!recalled && !!load)
  const [resumeError, setResumeError] = useState<string | null>(null)
  const [userPrompt, setUserPrompt] = useState<((name: string | null) => void) | null>(null)

  /** The state as it was read back (from memory or the database): opening alone is not a change to save. */
  const unchangedRef = useRef<WizardState | null>(recalled ?? null)
  /** True once a draft may be stored for this id (so clearing both files removes it). */
  const draftStoredRef = useRef(!!recalled && !!draftFromState(recalled, ''))
  const draftErrorAtRef = useRef(0)
  const idRef = useRef(state.reconId)

  // ── The reconciliation continues under a new id (new files after a run, or a re-run of a finalised one) ──
  useEffect(() => {
    if (state.reconId === idRef.current) return
    forgetRecon(idRef.current)
    idRef.current = state.reconId
    draftStoredRef.current = false
    onReconIdChange?.(state.reconId)
    if (params.has('session') || params.has('draft')) setParams({}, { replace: true })
  }, [state.reconId, onReconIdChange, params, setParams])

  // ── Keep the state in memory, and save the draft (before Reconcile) after every change ──
  useEffect(() => {
    sessionRef.current = state.session
    if (resuming || resumeError) return
    rememberWizard(state)
    if (state === unchangedRef.current) return
    unchangedRef.current = null
    const report = (err: unknown): void => {
      const now = Date.now()
      if (now - draftErrorAtRef.current < DRAFT_ERROR_INTERVAL_MS) return
      draftErrorAtRef.current = now
      toast.error('This draft could not be saved', `${errorMessage(err)} It is still on screen; run the reconciliation or try again before closing the app.`)
    }
    const draft = draftFromState(state, new Date().toISOString())
    if (draft) {
      draftStoredRef.current = true
      persistDraft(draft, sourcesFromState(state)).catch(report)
    } else if (draftStoredRef.current && !state.session && !state.files.A && !state.files.B) {
      // Both files were removed: nothing is left to keep as a draft.
      draftStoredRef.current = false
      removeDraftLater(state.reconId).catch(report)
    }
  }, [state, resuming, resumeError, toast])

  useEffect(() => {
    let alive = true
    getSettings()
      .then((s) => {
        if (alive) setSettings(s)
      })
      .catch(() => undefined)
    return () => {
      alive = false
    }
  }, [])

  // ── Open a saved draft or session that is not in memory (link, In progress menu, Recon History) ──
  const loadRef = useRef(resuming ? load : null)
  useEffect(() => {
    const kind = loadRef.current
    if (!kind) return
    let alive = true
    const id = reconId
    const openSession = async (): Promise<boolean> => {
      const s = await getSession(id)
      if (!s) return false
      if (s.result.config.moduleId !== moduleId) throw new Error(WRONG_MODULE)
      // Unfinished sessions saved with their files can go back to Map & rules; finalised ones stay read-only.
      const sources = s.finalised ? undefined : await getSources(id)
      if (!alive) return true
      savedRef.current = s
      sessionRef.current = s
      dispatch({ type: 'resume', session: s, files: sources ? filesFromSources(sources) : undefined })
      return true
    }
    const openDraft = async (): Promise<boolean> => {
      const found = await getDraft(id)
      if (!found) return false
      if (found.draft.moduleId !== moduleId) throw new Error(WRONG_MODULE)
      if (!alive) return true
      const restored = stateFromDraft(found.draft, found.sources)
      unchangedRef.current = restored
      draftStoredRef.current = true
      dispatch({ type: 'restore', state: restored })
      return true
    }
    void (async () => {
      try {
        // A save still queued for it (e.g. it was just switched away from) must land before it is read back.
        await Promise.all([flushDraftSaves(id), flushSessionSaves()])
        // A draft link is out of date once the draft has been run (it is a session now), and the other way round.
        const opened = kind === 'session' ? (await openSession()) || (await openDraft()) : (await openDraft()) || (await openSession())
        if (alive && !opened) setResumeError('This reconciliation was not found. It may have been deleted.')
      } catch (err) {
        if (!alive) return
        const msg = errorMessage(err)
        setResumeError(msg === WRONG_MODULE ? msg : `The saved reconciliation could not be opened. ${msg}`)
      } finally {
        if (alive) setResuming(false)
      }
    })()
    return () => {
      alive = false
    }
  }, [reconId, moduleId])

  // ── Starting configuration once both files are in: a saved mapping for the same headers, else suggestions ──
  const tableA = state.files.A?.table
  const tableB = state.files.B?.table
  useEffect(() => {
    if (!tableA || !tableB || state.config || state.origin !== 'new') return
    let alive = true
    void (async () => {
      const s = stateRef.current
      const currency = settingsRef.current.currency || 'AED'
      let saved
      try {
        saved = await findMappingByHeaders(moduleId, tableA.columns, tableB.columns)
      } catch {
        saved = undefined
      }
      if (!alive) return
      if (saved) {
        dispatch({ type: 'setConfig', config: configFromSaved(saved, moduleId, currency), source: { kind: 'mapping', name: saved.name } })
        toast.success(`Saved mapping '${saved.name}' loaded`, 'Check the keys on the Map & rules step before running.')
        return
      }
      try {
        dispatch({ type: 'setConfig', config: suggestedConfig(moduleId, tableA, tableB, s.sideAName, s.sideBName, currency), source: { kind: 'suggested' } })
      } catch (err) {
        toast.error('Match keys could not be suggested', `${errorMessage(err)} You can still add keys by hand.`)
      }
    })()
    return () => {
      alive = false
    }
  }, [tableA, tableB, state.config, state.origin, moduleId, toast])

  // ── Account label and period guesses (until the user edits them) ──
  useEffect(() => {
    if (state.origin !== 'new' || (!tableA && !tableB)) return
    dispatch({
      type: 'autoMeta',
      accountLabel: guessAccountLabel(moduleId, state.files.A?.fileName ?? state.files.B?.fileName ?? null, state.sideAName, state.sideBName),
      period: guessPeriod([tableA, tableB], state.files.A?.fileName ?? state.files.B?.fileName ?? null)
    })
  }, [tableA, tableB, state.sideAName, state.sideBName, state.origin, state.files.A?.fileName, state.files.B?.fileName, moduleId])

  const configErrors = useMemo(() => {
    if (!state.config || !tableA || !tableB) return []
    return validateConfig(finalConfig(state.config, state.sideAName, state.sideBName, settings.currency), tableA, tableB)
  }, [state.config, tableA, tableB, state.sideAName, state.sideBName, settings.currency])

  // ── Files ── (new files after a run continue as a new reconciliation: `freshId`)
  const loadFile = useCallback(async (side: Side, file: OpenedFile) => {
    setBusy((b) => ({ ...b, [side]: true }))
    setFileErrors((e) => ({ ...e, [side]: null }))
    try {
      dispatch({ type: 'loadFile', side, file: await readUploadAsync(file.name, file.data), freshId: newId() })
    } catch (err) {
      setFileErrors((e) => ({ ...e, [side]: errorMessage(err, 'The file could not be read.') }))
    } finally {
      setBusy((b) => ({ ...b, [side]: false }))
    }
  }, [])

  const clearFile = useCallback((side: Side) => {
    setFileErrors((e) => ({ ...e, [side]: null }))
    dispatch({ type: 'clearFile', side, freshId: newId() })
  }, [])

  const reparse = useCallback(
    (side: Side, sheetIndex: number, headerRowIndex: number | null) => {
      const f = stateRef.current.files[side]
      if (!f) return
      try {
        dispatch({ type: 'loadFile', side, file: parseSheet(f.workbook, f.fileName, f.size, sheetIndex, headerRowIndex), freshId: newId() })
        setFileErrors((e) => ({ ...e, [side]: null }))
      } catch (err) {
        toast.error('The sheet could not be read', errorMessage(err))
      }
    },
    [toast]
  )
  const changeSheet = useCallback((side: Side, sheetIndex: number) => reparse(side, sheetIndex, null), [reparse])
  const changeHeaderRow = useCallback(
    (side: Side, headerRowIndex: number | null) => {
      const f = stateRef.current.files[side]
      if (f) reparse(side, f.sheetIndex, headerRowIndex)
    },
    [reparse]
  )

  const loadSampleSet = useCallback(
    async (set: SampleSet) => {
      setBusy({ A: true, B: true })
      setFileErrors({ A: null, B: null })
      try {
        const list = await window.recoDo.samples.list()
        const [fa, fb] = pickSampleFiles(set, list)
        const [da, db] = await Promise.all([window.recoDo.samples.read(fa.path), window.recoDo.samples.read(fb.path)])
        const [loadedA, loadedB] = await Promise.all([readUploadAsync(fa.name, da), readUploadAsync(fb.name, db)])
        if (set.sideNames && module.editableSideNames) {
          dispatch({ type: 'sideName', side: 'A', name: set.sideNames[0] })
          dispatch({ type: 'sideName', side: 'B', name: set.sideNames[1] })
        }
        const freshId = newId()
        dispatch({ type: 'loadFile', side: 'A', file: loadedA, freshId })
        dispatch({ type: 'loadFile', side: 'B', file: loadedB, freshId })
        toast.success('Sample files loaded', `${fa.name} and ${fb.name}`)
      } catch (err) {
        toast.error('The sample files could not be loaded', errorMessage(err))
      } finally {
        setBusy({ A: false, B: false })
      }
    },
    [module.editableSideNames, toast]
  )

  // ── Session persistence ──
  const commit = useCallback(
    async (next: ReconSession, opts: CommitOptions = {}): Promise<boolean> => {
      sessionRef.current = next
      dispatch({ type: 'session', session: next })
      // Saves run one at a time and the newest version wins (lib/sessionSaves). Each save writes only the small,
      // changing part of the session; the lines (and source files) are written once per run.
      try {
        await persistSession(next, opts.sources)
        if (savedRef.current === null || savedRef.current.id !== next.id || savedRef.current.updatedAt <= next.updatedAt) savedRef.current = next
        return true
      } catch (err) {
        const saved = savedRef.current
        // Undo only when nothing newer was done meanwhile and there is a saved version of this session to return to.
        if (opts.revertOnFail && sessionRef.current === next && saved && saved.id === next.id) {
          sessionRef.current = saved
          dispatch({ type: 'session', session: saved })
          toast.error('That change could not be saved, so it was undone', `${errorMessage(err)} Please try again.`)
        } else {
          toast.error('Your latest change could not be saved', `${errorMessage(err)} It is still on screen; try again before closing the app.`)
        }
        return false
      }
    },
    [toast]
  )

  const latestSession = useCallback(() => sessionRef.current, [])

  const ensureUser = useCallback(async (): Promise<string | null> => {
    const name = settingsRef.current.preparerName.trim()
    if (name) return name
    return new Promise<string | null>((resolve) => setUserPrompt(() => resolve))
  }, [])

  const act = useCallback(
    async (fn: (s: ReconSession, user: string) => ReconSession, success?: string) => {
      const s = sessionRef.current
      if (!s) return false
      const user = await ensureUser()
      if (!user) return false
      try {
        const next = fn(sessionRef.current ?? s, user)
        // A failed save is reported (and undone) by commit; no success message then, and dialogs stay open.
        if (!(await commit(next, { revertOnFail: true }))) return false
        if (success) toast.success(success)
        return true
      } catch (err) {
        toast.error('That change was not made', errorMessage(err))
        return false
      }
    },
    [commit, ensureUser, toast]
  )

  const run = useCallback(async () => {
    const s = stateRef.current
    const a = s.files.A?.table
    const b = s.files.B?.table
    if (!a || !b || !s.config) return
    const currency = settingsRef.current.currency || 'AED'
    const cfg = finalConfig(s.config, s.sideAName, s.sideBName, currency)
    const errors = validateConfig(cfg, a, b)
    if (errors.length > 0) {
      toast.error('Fix the mapping before running', errors[0])
      return
    }
    const previous = s.session
    if (previous && previous.audit.length > 0 && !previous.finalised) {
      const ok = await confirm({
        title: 'Run the reconciliation again?',
        description: `This replaces the current results and the ${previous.audit.length} review decision${previous.audit.length === 1 ? '' : 's'} already made.`,
        confirmLabel: 'Run again',
        tone: 'danger'
      })
      if (!ok) return
    }
    // The draft becomes a session with the same id, so stop saving it as a draft first. A finalised result is
    // never changed: running again then starts a new session.
    const sessionId = previous?.finalised ? newId() : s.reconId
    const sources = sourcesFromState(s)
    await closeDraftSaves(s.reconId)
    dispatch({ type: 'go', step: 2 })
    setRunning(true)
    setRunError(null)
    try {
      const result = await runReconcile(a, b, cfg)
      const src = s.configSource
      const meta = buildMeta({
        accountLabel: s.accountLabel,
        period: s.period,
        tableA: a,
        tableB: b,
        mappingName: src && src.kind !== 'suggested' ? src.name : undefined,
        preparer: settingsRef.current.preparerName.trim(),
        currency
      })
      let session: ReconSession = { ...createSession(result, meta), id: sessionId }
      if (previous && !previous.finalised) session = { ...session, createdAt: previous.createdAt }
      await commit(session, { sources })
    } catch (err) {
      setRunError(errorMessage(err, 'The reconciliation could not be completed.'))
      // No result: it is still a draft, so keep saving it as one.
      reopenDraftSaves(s.reconId)
      const now = stateRef.current
      const draft = draftFromState(now, new Date().toISOString())
      if (draft) persistDraft(draft, sourcesFromState(now)).catch(() => undefined)
    } finally {
      setRunning(false)
    }
  }, [commit, confirm, toast])

  const startNew = useCallback(() => {
    if (slot) {
      slot.newRecon()
      return
    }
    dispatch({ type: 'reset', reconId: newId() })
    setResumeError(null)
  }, [slot])

  const api: WizardApi = {
    state,
    dispatch,
    module,
    settings,
    configErrors,
    busy,
    fileErrors,
    loadFile,
    clearFile,
    changeSheet,
    changeHeaderRow,
    loadSampleSet,
    resuming,
    resumeError,
    running,
    runError,
    run,
    commit,
    latestSession,
    act,
    ensureUser,
    startNew
  }

  return (
    <WizardContext.Provider value={api}>
      {children}
      <PreparerDialog
        open={!!userPrompt}
        onCancel={() => {
          userPrompt?.(null)
          setUserPrompt(null)
        }}
        onSave={async (name) => {
          try {
            const next = await saveSettings({ preparerName: name })
            setSettings(next)
            settingsRef.current = next
          } catch (err) {
            toast.error('Your name could not be saved in Settings', errorMessage(err))
          }
          userPrompt?.(name)
          setUserPrompt(null)
        }}
      />
    </WizardContext.Provider>
  )
}
