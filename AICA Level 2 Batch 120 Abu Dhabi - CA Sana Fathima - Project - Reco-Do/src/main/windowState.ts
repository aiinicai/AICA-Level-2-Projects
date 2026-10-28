import { app, screen, type BrowserWindow, type Rectangle } from 'electron'
import { readFileSync, writeFileSync } from 'fs'
import { join } from 'path'

/** The size the window opens at on screens big enough for it. */
export const PREFERRED_WIDTH = 1440
export const PREFERRED_HEIGHT = 900
/** Below this work area the first window opens maximised. */
const MAXIMISE_BELOW_WIDTH = 1280
const MAXIMISE_BELOW_HEIGHT = 800
/** The smallest window the layout supports. */
export const MIN_WIDTH = 1024
export const MIN_HEIGHT = 640
/** At least this much of a saved window must be on a display for it to be reused. */
const MIN_VISIBLE = 120

const STATE_FILE = 'window-state.json'

export interface WindowState {
  bounds: Rectangle
  maximized: boolean
}

function statePath(): string {
  return join(app.getPath('userData'), STATE_FILE)
}

function isRect(v: unknown): v is Rectangle {
  if (!v || typeof v !== 'object') return false
  const r = v as Record<string, unknown>
  return ['x', 'y', 'width', 'height'].every((k) => typeof r[k] === 'number' && Number.isFinite(r[k]))
}

function readSaved(): WindowState | null {
  try {
    const parsed: unknown = JSON.parse(readFileSync(statePath(), 'utf8'))
    if (!parsed || typeof parsed !== 'object') return null
    const { bounds, maximized } = parsed as Record<string, unknown>
    if (!isRect(bounds)) return null
    return { bounds, maximized: maximized === true }
  } catch {
    // No saved state yet, or the file is unreadable: use the default size.
    return null
  }
}

function overlap(a: Rectangle, b: Rectangle): { w: number; h: number } {
  const w = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x)
  const h = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y)
  return { w: Math.max(0, w), h: Math.max(0, h) }
}

/** Fits the rectangle inside a work area: never bigger than it and fully on it. */
function clampInto(rect: Rectangle, work: Rectangle): Rectangle {
  const width = Math.max(Math.min(rect.width, work.width), Math.min(MIN_WIDTH, work.width))
  const height = Math.max(Math.min(rect.height, work.height), Math.min(MIN_HEIGHT, work.height))
  const x = Math.min(Math.max(rect.x, work.x), work.x + work.width - width)
  const y = Math.min(Math.max(rect.y, work.y), work.y + work.height - height)
  return { x: Math.round(x), y: Math.round(y), width: Math.round(width), height: Math.round(height) }
}

function centredDefault(): WindowState {
  const work = screen.getPrimaryDisplay().workArea
  const width = Math.min(PREFERRED_WIDTH, work.width)
  const height = Math.min(PREFERRED_HEIGHT, work.height)
  return {
    bounds: {
      x: Math.round(work.x + (work.width - width) / 2),
      y: Math.round(work.y + (work.height - height) / 2),
      width,
      height
    },
    maximized: work.width < MAXIMISE_BELOW_WIDTH || work.height < MAXIMISE_BELOW_HEIGHT
  }
}

/**
 * The bounds the window should open with: the last saved position when it is still on a connected display
 * (moved fully onto that display if needed), otherwise a size that fits the primary display, centred.
 */
export function initialWindowState(): WindowState {
  const saved = readSaved()
  if (!saved) return centredDefault()
  const display = screen.getAllDisplays().find((d) => {
    const o = overlap(saved.bounds, d.workArea)
    return o.w >= MIN_VISIBLE && o.h >= MIN_VISIBLE
  })
  if (!display) return centredDefault()
  return { bounds: clampInto(saved.bounds, display.workArea), maximized: saved.maximized }
}

/** Saves the window's normal (restored) bounds and maximised state whenever they change, and on close. */
export function trackWindowState(win: BrowserWindow): void {
  let timer: NodeJS.Timeout | undefined
  const save = (): void => {
    if (win.isDestroyed() || win.isMinimized()) return
    const state: WindowState = { bounds: win.getNormalBounds(), maximized: win.isMaximized() }
    try {
      writeFileSync(statePath(), JSON.stringify(state))
    } catch {
      // Remembering the window size is a convenience; a failed write only means the default size next time.
    }
  }
  const saveSoon = (): void => {
    clearTimeout(timer)
    timer = setTimeout(save, 500)
  }
  win.on('resize', saveSoon)
  win.on('move', saveSoon)
  win.on('maximize', save)
  win.on('unmaximize', save)
  win.on('close', () => {
    clearTimeout(timer)
    save()
  })
}
