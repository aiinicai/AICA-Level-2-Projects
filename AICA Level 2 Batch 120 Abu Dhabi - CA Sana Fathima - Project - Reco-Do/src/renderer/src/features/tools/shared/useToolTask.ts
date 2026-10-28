import { useCallback, useEffect, useRef, useState } from 'react'
import { isToolError } from '@tools/common'

export interface TaskProgress {
  label: string
  /** 0-100; omit for an indeterminate bar. */
  value?: number
  /** Right-hand text, e.g. "Page 3 of 6". */
  detail?: string
}

export type ReportProgress = (p: Partial<TaskProgress>) => void

export interface ToolTask {
  running: boolean
  /** Set only once a task has run for longer than the grace period, so quick jobs do not flash a bar. */
  progress: TaskProgress | null
  error: string | null
  /** Technical detail behind `error` (for the "Technical details" disclosure); null when there is none. */
  errorDetail: string | null
  setError: (message: string | null) => void
  /** Runs `fn`; returns undefined when it failed or was cancelled (the error is kept in `error`). */
  run: <T>(label: string, fn: (signal: AbortSignal, report: ReportProgress) => Promise<T>) => Promise<T | undefined>
  cancel: () => void
}

/** Lets React paint (spinner, progress bar) before heavy synchronous work starts. */
export function nextFrame(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 16))
}

export const GENERIC_TOOL_ERROR = 'Something went wrong while processing the file. Please try again.'

/** Messages written by programs rather than for people ("Cannot read properties of undefined", "ENOENT: ..."). */
const TECHNICAL_TEXT =
  /\b(undefined|null|NaN|is not a function|is not defined|cannot read propert\w*|unexpected token|stack|errno|ENOENT|EACCES|EPERM|EBUSY|ECONN\w*|out of memory|maximum call stack|failed to fetch|worker|wasm|DataCloneError|DOMException)\b|[{}<>]|\bat \S+:\d+/i

/**
 * What to show for anything a tool throws: ToolError messages are written for users and shown as they are;
 * other errors with technical wording get a plain-English message, with the original text kept as `detail`.
 */
export function toolErrorInfo(e: unknown): { message: string; detail: string | null } {
  if (isToolError(e)) return { message: e.message, detail: e.detail ?? null }
  const raw = e instanceof Error ? e.message : typeof e === 'string' ? e : ''
  const name = e instanceof Error ? e.name : ''
  const plainError = name === '' || name === 'Error'
  if (raw && plainError && !TECHNICAL_TEXT.test(raw) && raw.length <= 300) return { message: raw, detail: null }
  const detail = e instanceof Error ? `${e.name}: ${e.message}` : raw || String(e)
  return { message: GENERIC_TOOL_ERROR, detail: detail || null }
}

/** Plain-English text for anything a tool throws (see `toolErrorInfo`). */
export function toolErrorMessage(e: unknown): string {
  return toolErrorInfo(e).message
}

function isCancel(e: unknown): boolean {
  return (isToolError(e) && e.code === 'cancelled') || (e instanceof DOMException && e.name === 'AbortError')
}

const GRACE_MS = 400

/** Runs one job at a time with progress, Cancel and plain-English errors. */
export function useToolTask(): ToolTask {
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState<TaskProgress | null>(null)
  const [error, setErrorState] = useState<string | null>(null)
  const [errorDetail, setErrorDetail] = useState<string | null>(null)
  const setError = useCallback((message: string | null) => {
    setErrorState(message)
    setErrorDetail(null)
  }, [])
  const ctrl = useRef<AbortController | null>(null)
  const latest = useRef<TaskProgress>({ label: '' })
  const timer = useRef<number | undefined>(undefined)

  useEffect(
    () => () => {
      ctrl.current?.abort()
      window.clearTimeout(timer.current)
    },
    []
  )

  const run = useCallback(async <T>(label: string, fn: (signal: AbortSignal, report: ReportProgress) => Promise<T>): Promise<T | undefined> => {
    ctrl.current?.abort()
    const c = new AbortController()
    ctrl.current = c
    latest.current = { label }
    setError(null)
    setRunning(true)
    setProgress(null)
    window.clearTimeout(timer.current)
    let shown = false
    timer.current = window.setTimeout(() => {
      shown = true
      if (ctrl.current === c) setProgress({ ...latest.current })
    }, GRACE_MS)
    const report: ReportProgress = (p) => {
      latest.current = { ...latest.current, ...p }
      if (shown && ctrl.current === c) setProgress({ ...latest.current })
    }
    try {
      await nextFrame()
      const value = await fn(c.signal, report)
      if (c.signal.aborted) return undefined
      return value
    } catch (e) {
      if (ctrl.current === c && !isCancel(e) && !c.signal.aborted) {
        const info = toolErrorInfo(e)
        setErrorState(info.message)
        setErrorDetail(info.detail)
      }
      return undefined
    } finally {
      if (ctrl.current === c) {
        window.clearTimeout(timer.current)
        ctrl.current = null
        setRunning(false)
        setProgress(null)
      }
    }
  }, [setError])

  const cancel = useCallback(() => {
    const c = ctrl.current
    if (!c) return
    c.abort()
    ctrl.current = null
    window.clearTimeout(timer.current)
    setRunning(false)
    setProgress(null)
  }, [])

  return { running, progress, error, errorDetail, setError, run, cancel }
}
