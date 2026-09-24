// Application state: who is signed in, which entity and as-on date the whole
// app is looking at, and the trace drawer that every clickable number opens.
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { api, getToken, onRestricted, setScope } from './api'

const AppCtx = createContext(null)
export const useApp = () => useContext(AppCtx)

export function AppProvider({ children }) {
  const [user, setUser] = useState(null)
  const [booting, setBooting] = useState(true)
  const [entities, setEntities] = useState([])
  const [entityId, setEntityId] = useState(null)
  const [asOn, setAsOn] = useState(null)
  const [strip, setStrip] = useState(null)
  const [trace, setTrace] = useState(null)          // the drill-down drawer
  const [toast, setToast] = useState(null)
  const [rev, setRev] = useState(0)                 // bump to refetch everything
  const [restricted, setRestricted] = useState([])  // board: what this screen withheld
  const [onboarding, setOnboarding] = useState(null)

  const refresh = useCallback(() => setRev((r) => r + 1), [])

  // Reset on navigation, so a notice never outlives the screen it described.
  useEffect(() => {
    onRestricted((labels) => setRestricted((prev) =>
      (labels.length && JSON.stringify(prev) !== JSON.stringify(labels)) ? labels : prev))
  }, [])

  // Boot: who am I, what can I look at
  useEffect(() => {
    let live = true
    ;(async () => {
      if (!getToken()) { setBooting(false); return }
      try {
        const me = await api.get('/api/auth/me', {}, { scoped: false })
        if (!live) return
        setUser(me)
        // Is anything set up at all? This decides whether the app or the
        // first-run screen is what the person should be looking at.
        try {
          const ob = await api.get('/api/onboarding/status', {}, { scoped: false })
          if (live) setOnboarding(ob)
        } catch { /* treat as set up rather than block the app */ }
        const ents = await api.get('/api/entities', {}, { scoped: false })
        if (!live) return
        setEntities(ents)
        const saved = Number(localStorage.getItem('cashrunway.entity')) || null
        const chosen = ents.find((e) => e.id === saved) || ents[0]
        if (chosen) {
          setEntityId(chosen.id)
          setScope({ entity_id: chosen.id })
        }
      } catch { /* token invalid — the api layer redirects */ }
      if (live) setBooting(false)
    })()
    return () => { live = false }
  }, [])

  // Keep the api scope in step, then reload the top strip
  useEffect(() => {
    if (!entityId) return
    setScope({ entity_id: entityId, as_on: asOn })
    try { localStorage.setItem('cashrunway.entity', String(entityId)) } catch { /* ignore */ }
    let live = true
    api.get('/api/top-strip').then((s) => live && setStrip(s)).catch(() => {})
    return () => { live = false }
  }, [entityId, asOn, rev])

  const signIn = useCallback(async (email, password) => {
    const me = await api.login(email, password)
    setUser(me)
    try { setOnboarding(await api.get('/api/onboarding/status', {}, { scoped: false })) }
    catch { /* ignore */ }
    const ents = await api.get('/api/entities', {}, { scoped: false })
    setEntities(ents)
    if (ents[0]) { setEntityId(ents[0].id); setScope({ entity_id: ents[0].id }) }
    return me
  }, [])

  const signOut = useCallback(() => {
    api.logout()
    setUser(null)
    setStrip(null)
    window.location.href = '/login'
  }, [])

  const notify = useCallback((message, tone = 'ok') => {
    setToast({ message, tone, id: Date.now() })
    setTimeout(() => setToast((t) => (t && Date.now() - t.id > 3400 ? null : t)), 3600)
  }, [])

  /** Open the drill-down for a figure's `trace` descriptor. */
  const openTrace = useCallback((descriptor, title) => {
    if (!descriptor) return
    setTrace({ descriptor, title, loading: true, data: null, error: null })
    api.get('/api/trace', descriptor)
      .then((data) => setTrace((t) => (t ? { ...t, loading: false, data } : t)))
      .catch((e) => setTrace((t) => (t ? { ...t, loading: false, error: e.message } : t)))
  }, [])

  const value = useMemo(() => ({
    user, booting, entities, entityId, setEntityId, asOn, setAsOn,
    strip, refresh, rev, signIn, signOut,
    trace, openTrace, closeTrace: () => setTrace(null),
    toast, notify,
    onboarding, restricted, clearRestricted: () => setRestricted([]),
    firstRun: !!onboarding?.first_run,
    canWrite: !!user && user.role !== 'Board Read-Only',
    canApprove: !!user && ['Admin', 'CFO'].includes(user.role),
    // When the confidence banner is up, every headline number carries the dot.
    indicative: !!strip && strip.confidence?.level !== 'High',
  }), [user, booting, entities, entityId, asOn, strip, rev, trace, toast,
       onboarding, restricted, refresh, signIn, signOut, openTrace, notify])

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>
}

/**
 * Fetch-on-mount with the app's entity/as-on scope, refetching whenever the
 * scope or a write changes. Returns { data, loading, error, reload }.
 */
export function useEndpoint(path, params, deps = []) {
  const { entityId, asOn, rev } = useApp()
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const seq = useRef(0)
  const key = JSON.stringify(params || {})

  const load = useCallback(() => {
    if (!entityId) return
    const mine = ++seq.current
    setState((s) => ({ ...s, loading: true, error: null }))
    api.get(path, params)
      .then((data) => { if (mine === seq.current) setState({ data, loading: false, error: null }) })
      .catch((e) => { if (mine === seq.current) setState({ data: null, loading: false, error: e.message }) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, key, entityId, asOn])

  useEffect(load, [load, rev, ...deps])
  return { ...state, reload: load }
}
