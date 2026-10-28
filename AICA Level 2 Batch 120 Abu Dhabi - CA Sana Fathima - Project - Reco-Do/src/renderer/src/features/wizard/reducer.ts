// The wizard store's reducer. Pure: no React, no database, no engine calls.

import { getModule, type ModuleId } from '@shared/modules'
import type { StepIndex, WizardAction, WizardState } from './types'

export function initialState(moduleId: ModuleId, reconId = ''): WizardState {
  const m = getModule(moduleId)
  return {
    moduleId,
    reconId,
    step: 0,
    sideAName: m?.sideA ?? 'File A',
    sideBName: m?.sideB ?? 'File B',
    files: { A: null, B: null },
    accountLabel: '',
    period: '',
    accountTouched: false,
    periodTouched: false,
    config: null,
    configSource: null,
    session: null,
    origin: 'new'
  }
}

/** Steps the user may open right now (finished steps and the next one). */
export function reachableSteps(s: WizardState): Set<StepIndex> {
  const out = new Set<StepIndex>()
  if (s.origin === 'resumed') {
    out.add(3)
    out.add(4)
    out.add(2)
    return out
  }
  out.add(0)
  if (s.files.A && s.files.B) out.add(1)
  if (s.session) {
    out.add(2)
    out.add(3)
    out.add(4)
  }
  return out
}

export function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case 'go': {
      // Step 2 (Reconcile) can also be entered from Map & Rules to start a run.
      const startRun = action.step === 2 && !!state.files.A && !!state.files.B && !!state.config
      return reachableSteps(state).has(action.step) || startRun ? { ...state, step: action.step } : state
    }
    case 'sideName': {
      const key = action.side === 'A' ? 'sideAName' : 'sideBName'
      const config = state.config ? { ...state.config, [action.side === 'A' ? 'sideAName' : 'sideBName']: action.name } : null
      return { ...state, [key]: action.name, config }
    }
    case 'loadFile': {
      const files = { ...state.files, [action.side]: action.file }
      // New data invalidates the mapping (columns may differ) and any earlier result. The saved session stays as it
      // was, so the new files continue as a new reconciliation (a new id) once a session exists.
      return { ...state, reconId: continueId(state, action.freshId), files, config: null, configSource: null, session: null, origin: 'new' }
    }
    case 'clearFile': {
      const files = { ...state.files, [action.side]: null }
      return { ...state, reconId: continueId(state, action.freshId), files, config: null, configSource: null, session: null, step: 0, origin: 'new' }
    }
    case 'meta': {
      const next = { ...state }
      if (action.accountLabel !== undefined) {
        next.accountLabel = action.accountLabel
        next.accountTouched = true
      }
      if (action.period !== undefined) {
        next.period = action.period
        next.periodTouched = true
      }
      return next
    }
    case 'autoMeta': {
      const accountLabel = state.accountTouched ? state.accountLabel : action.accountLabel
      const period = state.periodTouched ? state.period : action.period
      // Same guesses: keep the same state, so nothing re-renders or is saved again.
      return accountLabel === state.accountLabel && period === state.period ? state : { ...state, accountLabel, period }
    }
    case 'setConfig': {
      const m = getModule(state.moduleId)
      const editable = !!m?.editableSideNames
      // Templates and saved General mappings carry their side names; fixed modules keep the module labels.
      const sideAName = editable && action.source.kind !== 'suggested' && action.config.sideAName ? action.config.sideAName : state.sideAName
      const sideBName = editable && action.source.kind !== 'suggested' && action.config.sideBName ? action.config.sideBName : state.sideBName
      return { ...state, sideAName, sideBName, config: { ...action.config, sideAName, sideBName }, configSource: action.source }
    }
    case 'patchConfig':
      if (!state.config) return state
      return { ...state, config: { ...state.config, ...action.patch } }
    case 'session':
      return { ...state, session: action.session, reconId: action.session.id }
    case 'resume': {
      const s = action.session
      const cfg = s.result.config
      const files = action.files
      const editable = !s.finalised && !!files?.A && !!files?.B
      return {
        ...initialState(cfg.moduleId, s.id),
        files: editable && files ? files : { A: null, B: null },
        sideAName: cfg.sideAName,
        sideBName: cfg.sideBName,
        accountLabel: s.meta.accountLabel,
        period: s.meta.period,
        accountTouched: true,
        periodTouched: true,
        config: cfg,
        configSource: s.meta.mappingName ? { kind: 'mapping', name: s.meta.mappingName } : { kind: 'suggested' },
        session: s,
        origin: editable ? 'new' : 'resumed',
        step: 4
      }
    }
    case 'restore':
      return action.state.moduleId === state.moduleId ? action.state : state
    case 'reset':
      return initialState(state.moduleId, action.reconId ?? state.reconId)
  }
}

/** The id to keep after the files change: a new one when the old id already belongs to a saved session. */
function continueId(state: WizardState, freshId: string | undefined): string {
  return state.session && freshId ? freshId : state.reconId
}
