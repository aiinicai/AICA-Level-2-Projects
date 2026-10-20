// HTML → real PDF: render the print page in a hidden, locked-down window, printToPDF, then the Save dialog.

import { app, BrowserWindow, session } from 'electron'
import { randomUUID } from 'crypto'
import { readdir, rm, writeFile } from 'fs/promises'
import { join } from 'path'
import { pathToFileURL } from 'url'
import { chooseSavePath, writeChosenFile } from './files'
import { withPrintCsp } from './security'

const PARTITION = 'reco-do-pdf-render'
const TEMP_PREFIX = 'reco-do-print-'
let sessionReady = false
/** The print files being rendered right now: the only file: URLs the render session may load. */
const allowedFiles = new Set<string>()

/** Compares file URLs without caring about percent-encoding or letter case (Windows paths). */
function fileKey(url: string): string {
  try {
    return decodeURIComponent(url).toLowerCase()
  } catch {
    return url.toLowerCase()
  }
}

/** A separate session that can load only the print file itself (plus data:/blob:): no network, no other files. */
function renderSession(): Electron.Session {
  const ses = session.fromPartition(PARTITION, { cache: false })
  if (!sessionReady) {
    ses.webRequest.onBeforeRequest((details, callback) => {
      const url = details.url
      callback({ cancel: !(/^(data|blob):/i.test(url) || allowedFiles.has(fileKey(url))) })
    })
    ses.setPermissionRequestHandler((_wc, _permission, callback) => callback(false))
    sessionReady = true
  }
  return ses
}

async function renderPdf(html: string, landscape: boolean): Promise<Buffer> {
  // A temp file rather than a data: URL, because large summaries exceed Chromium's 2 MB URL limit.
  const tempFile = join(app.getPath('temp'), `${TEMP_PREFIX}${randomUUID()}.html`)
  const fileUrl = pathToFileURL(tempFile).href
  await writeFile(tempFile, withPrintCsp(html), 'utf8')
  allowedFiles.add(fileKey(fileUrl))
  const win = new BrowserWindow({
    show: false,
    width: 1123,
    height: 794,
    webPreferences: {
      session: renderSession(),
      javascript: false,
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true
    }
  })
  win.webContents.on('will-navigate', (event) => event.preventDefault())
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  try {
    await win.loadURL(fileUrl)
    // A4 by default; the export HTML's own CSS @page rule (size, margins, "Page X of Y") takes precedence.
    // Margins are left at Chromium's default so @page margins apply.
    return await win.webContents.printToPDF({
      pageSize: 'A4',
      landscape,
      printBackground: true,
      preferCSSPageSize: true,
      displayHeaderFooter: false
    })
  } catch {
    throw new Error('The PDF could not be created. Please try again.')
  } finally {
    allowedFiles.delete(fileKey(fileUrl))
    win.destroy()
    await rm(tempFile, { force: true })
  }
}

export async function htmlToPdf(
  parent: BrowserWindow | null,
  opts: { html: string; defaultName: string; landscape: boolean }
): Promise<{ saved: boolean; path?: string }> {
  const pdf = await renderPdf(opts.html, opts.landscape)
  const path = await chooseSavePath(parent, opts.defaultName, [{ name: 'PDF document', extensions: ['pdf'] }])
  if (!path) return { saved: false }
  await writeChosenFile(path, pdf)
  return { saved: true, path }
}

/** Removes print files left in the temp folder by a crash during an earlier PDF export. Best effort. */
export async function cleanStalePrintFiles(): Promise<void> {
  const dir = app.getPath('temp')
  try {
    const names = await readdir(dir)
    await Promise.all(
      names.filter((n) => n.startsWith(TEMP_PREFIX) && n.endsWith('.html')).map((n) => rm(join(dir, n), { force: true }).catch(() => undefined))
    )
  } catch {
    // The temp folder could not be listed; nothing to clean.
  }
}
