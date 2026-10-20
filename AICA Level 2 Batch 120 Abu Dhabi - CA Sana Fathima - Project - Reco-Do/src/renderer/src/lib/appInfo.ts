import { useEffect, useState } from 'react'
import { formatDate } from '@shared/format'

export interface AppInfo {
  version: string
  /** This user's data folder (IndexedDB, settings, saved keys). */
  dataPath: string
}

// Asked once per window: the answer never changes while the app runs.
let pending: Promise<AppInfo> | null = null

function loadAppInfo(): Promise<AppInfo> {
  if (!pending) {
    pending = window.recoDo.appInfo().catch((err: unknown) => {
      pending = null
      throw err
    })
  }
  return pending
}

/** The app version and data folder, or null while loading (or if the bridge is unavailable). */
export function useAppInfo(): AppInfo | null {
  const [info, setInfo] = useState<AppInfo | null>(null)
  useEffect(() => {
    let live = true
    loadAppInfo()
      .then((i) => live && setInfo(i))
      .catch(() => undefined)
    return () => {
      live = false
    }
  }, [])
  return info
}

/** The build date fixed at build time (electron.vite.config.ts), as DD-MMM-YYYY, or null when unknown. */
export function buildDate(): string | null {
  const raw = typeof __RECODO_BUILD_DATE__ === 'string' ? __RECODO_BUILD_DATE__ : ''
  const d = new Date(raw)
  return raw && !Number.isNaN(d.getTime()) ? formatDate(d) : null
}
