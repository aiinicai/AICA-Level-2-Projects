import { useCallback, useEffect, useRef, useState } from 'react'

export interface AsyncState<T> {
  data: T | undefined
  /** Plain-English message for the user, or null. */
  error: string | null
  /** Technical detail behind `error` (for an expandable "Technical details"), or null. */
  details: string | null
  loading: boolean
  /** Runs the loader again (e.g. after a save or delete). */
  reload: () => Promise<void>
  /** Replace the data locally without reloading. */
  setData: React.Dispatch<React.SetStateAction<T | undefined>>
}

export const GENERIC_ERROR = 'Something went wrong. Please try again.'

/** Built-in error types that only ever carry programmer-facing text. */
const TECHNICAL_NAMES = new Set(['TypeError', 'ReferenceError', 'RangeError', 'SyntaxError', 'EvalError', 'URIError', 'InternalError', 'DataCloneError'])
/** Wording that gives away a programming or runtime error rather than a message written for people. */
const TECHNICAL_TEXT = /is not a function|cannot read propert|cannot set propert|is not defined|is not iterable|unexpected token|maximum call stack|out of memory|\bundefined\b|\bnull\b|\bNaN\b|stack trace|at [\w.]+ \(/i

function isDomException(err: unknown): boolean {
  return typeof DOMException !== 'undefined' && err instanceof DOMException
}

/** True when the error's own text is not fit to show to a user. */
export function isTechnicalError(err: unknown): boolean {
  if (isDomException(err)) return true
  if (err instanceof Error) return TECHNICAL_NAMES.has(err.name) || !err.message || TECHNICAL_TEXT.test(err.message)
  if (typeof err === 'string') return !err || TECHNICAL_TEXT.test(err)
  return true
}

/** Plain-English message from anything thrown. Technical text is replaced by `fallback` (see errorDetails). */
export function errorMessage(err: unknown, fallback = GENERIC_ERROR): string {
  if (isTechnicalError(err)) return fallback
  if (err instanceof Error) return err.message
  return typeof err === 'string' ? err : fallback
}

/** The technical detail worth keeping behind a "Technical details" toggle, or null when there is none. */
export function errorDetails(err: unknown): string | null {
  if (err && typeof err === 'object' && 'detail' in err && typeof (err as { detail: unknown }).detail === 'string') {
    return (err as { detail: string }).detail || null
  }
  if (!isTechnicalError(err)) return null
  if (err instanceof Error || isDomException(err)) {
    const e = err as Error
    return e.message ? `${e.name}: ${e.message}` : e.name
  }
  if (err === undefined || err === null) return null
  return String(err)
}

/**
 * Loads data when the component mounts (and when `deps` change). Ignores results that arrive
 * after the component unmounted or after a newer load started.
 */
export function useAsync<T>(loader: () => Promise<T>, deps: React.DependencyList = [], fallback = GENERIC_ERROR): AsyncState<T> {
  const [data, setData] = useState<T | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)
  const [details, setDetails] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const run = useRef(0)
  const loaderRef = useRef(loader)
  loaderRef.current = loader
  const fallbackRef = useRef(fallback)
  fallbackRef.current = fallback

  const reload = useCallback(async () => {
    const id = ++run.current
    setLoading(true)
    try {
      const value = await loaderRef.current()
      if (id === run.current) {
        setData(value)
        setError(null)
        setDetails(null)
      }
    } catch (err) {
      if (id === run.current) {
        setError(errorMessage(err, fallbackRef.current))
        setDetails(errorDetails(err))
      }
    } finally {
      if (id === run.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
    return () => {
      run.current++
    }
    // The effect re-runs only when the caller's `deps` change; the latest loader is read from a ref.
  }, deps)

  return { data, error, details, loading, reload, setData }
}
