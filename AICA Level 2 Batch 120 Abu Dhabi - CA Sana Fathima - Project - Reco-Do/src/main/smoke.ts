// Hooks for the automated smoke scripts in scripts/ (never used by the app itself).
//
// They are inert unless the matching environment variable is set when the app starts, and never in a
// packaged build. The renderer cannot reach them: there is no IPC channel for them, they only change what the
// existing Open and Save dialogs return, and the renderer cannot set the main process's environment.
//
//   RECODO_SMOKE_SAVE_DIR    Save dialogs write to <dir>/<suggested file name> without showing the dialog.
//   RECODO_SMOKE_OPEN_FILES  JSON array of absolute paths. Each Open dialog returns the next path in the list
//                            (or all remaining paths when several files may be chosen) instead of showing.

import { app } from 'electron'
import { basename, isAbsolute, join } from 'path'

function smokeEnv(name: string): string | null {
  if (app.isPackaged) return null
  const v = process.env[name]
  return v && v.trim() ? v.trim() : null
}

/** Where a smoke run saves a file, or null when the real Save dialog should be shown. */
export function smokeSavePath(defaultName: string): string | null {
  const dir = smokeEnv('RECODO_SMOKE_SAVE_DIR')
  if (!dir || !isAbsolute(dir)) return null
  return join(dir, basename(defaultName))
}

let openQueue: string[] | null = null

function loadOpenQueue(): string[] {
  if (openQueue) return openQueue
  openQueue = []
  const raw = smokeEnv('RECODO_SMOKE_OPEN_FILES')
  if (!raw) return openQueue
  try {
    const list: unknown = JSON.parse(raw)
    if (Array.isArray(list)) openQueue = list.filter((p): p is string => typeof p === 'string' && isAbsolute(p))
  } catch {
    openQueue = []
  }
  return openQueue
}

/** Paths a smoke run "chooses" in the Open dialog, or null when the real dialog should be shown. */
export function smokeOpenPaths(multiple: boolean): string[] | null {
  if (!smokeEnv('RECODO_SMOKE_OPEN_FILES')) return null
  const queue = loadOpenQueue()
  if (queue.length === 0) return []
  return multiple ? queue.splice(0, queue.length) : queue.splice(0, 1)
}
