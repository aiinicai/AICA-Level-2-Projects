// Native Open / Save dialogs. The renderer never sees file-system paths it did not get from the user's own choice.

import { app, dialog, type BrowserWindow, type FileFilter as ElectronFilter } from 'electron'
import { readFile, stat, writeFile } from 'fs/promises'
import { basename, dirname, join } from 'path'
import type { FileFilter, OpenedFile } from '../shared/contracts'
import { smokeOpenPaths, smokeSavePath } from './smoke'
import { MAX_FILE_BYTES } from './validate'

let lastFolder: string | null = null

function startFolder(): string {
  return lastFolder ?? app.getPath('documents')
}

export async function openFiles(
  win: BrowserWindow | null,
  opts: { title?: string; filters?: FileFilter[]; multiple: boolean }
): Promise<OpenedFile[]> {
  const properties: Array<'openFile' | 'multiSelections'> = opts.multiple ? ['openFile', 'multiSelections'] : ['openFile']
  const options: Electron.OpenDialogOptions = {
    title: opts.title ?? 'Choose a file',
    defaultPath: startFolder(),
    filters: (opts.filters ?? []) as ElectronFilter[],
    properties
  }
  const smoke = smokeOpenPaths(opts.multiple)
  const result = smoke ? { canceled: false, filePaths: smoke } : win ? await dialog.showOpenDialog(win, options) : await dialog.showOpenDialog(options)
  if (result.canceled || result.filePaths.length === 0) return []
  lastFolder = dirname(result.filePaths[0])

  const files: OpenedFile[] = []
  for (const path of result.filePaths) {
    const info = await stat(path).catch(() => {
      throw new Error(`"${basename(path)}" could not be found or opened.`)
    })
    if (info.size > MAX_FILE_BYTES) throw new Error(`"${basename(path)}" is larger than 512 MB and cannot be opened.`)
    let buf: Buffer
    try {
      buf = await readFile(path)
    } catch {
      throw new Error(`"${basename(path)}" could not be read. It may be open in another program.`)
    }
    files.push({ name: basename(path), data: buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) as ArrayBuffer })
  }
  return files
}

/** Shows the Save dialog and returns the chosen path, or null when cancelled. */
export async function chooseSavePath(win: BrowserWindow | null, defaultName: string, filters?: FileFilter[]): Promise<string | null> {
  const smoke = smokeSavePath(defaultName)
  if (smoke) return smoke
  const options = { defaultPath: join(startFolder(), defaultName), filters: (filters ?? []) as ElectronFilter[] }
  const result = win ? await dialog.showSaveDialog(win, options) : await dialog.showSaveDialog(options)
  if (result.canceled || !result.filePath) return null
  lastFolder = dirname(result.filePath)
  return result.filePath
}

export async function writeChosenFile(path: string, data: Uint8Array): Promise<void> {
  try {
    await writeFile(path, data)
  } catch {
    throw new Error(`Could not save "${basename(path)}". If the file is open in Excel or a PDF viewer, close it and try again.`)
  }
}

export async function saveFile(
  win: BrowserWindow | null,
  opts: { defaultName: string; filters?: FileFilter[]; data: Uint8Array }
): Promise<{ saved: boolean; path?: string }> {
  const path = await chooseSavePath(win, opts.defaultName, opts.filters)
  if (!path) return { saved: false }
  await writeChosenFile(path, opts.data)
  return { saved: true, path }
}
