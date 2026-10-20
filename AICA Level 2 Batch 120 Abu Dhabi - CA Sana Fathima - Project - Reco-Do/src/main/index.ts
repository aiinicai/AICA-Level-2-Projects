import { app, BrowserWindow, ipcMain, protocol, session, shell } from 'electron'
import { join } from 'path'
import { CLOSE_EVENTS } from '../preload/channels'
import { registerIpc } from './ipc'
import { cleanStalePrintFiles } from './pdf'
import { APP_ORIGIN, registerAppProtocol, registerAppScheme } from './protocol'
import { isAllowedAppRequest } from './security'
import { initialWindowState, MIN_HEIGHT, MIN_WIDTH, trackWindowState } from './windowState'

const devServerUrl = !app.isPackaged ? process.env['ELECTRON_RENDERER_URL'] : undefined
const rendererRoot = join(__dirname, '../renderer')

function isAppUrl(url: string): boolean {
  if (devServerUrl && url.startsWith(devServerUrl)) return true
  return url.startsWith(`${APP_ORIGIN}/`)
}

// Must run before the app is ready.
registerAppScheme(protocol)

/** How long a close waits for the page to finish saving before the window closes anyway. */
const CLOSE_TIMEOUT_MS = 15_000

/**
 * Closing the window first asks the page to finish pending work (the last review decision may still be saving),
 * then closes when it answers, or after CLOSE_TIMEOUT_MS. A crashed or unloaded page closes at once.
 */
function holdCloseUntilSaved(win: BrowserWindow): void {
  let allowed = false
  let asked = false
  const closeNow = (): void => {
    if (allowed || win.isDestroyed()) return
    allowed = true
    win.close()
  }
  win.on('close', (event) => {
    if (allowed) return
    const contents = win.webContents
    if (contents.isCrashed() || contents.isLoading()) return
    event.preventDefault()
    if (asked) return
    asked = true
    const timer = setTimeout(() => {
      ipcMain.removeListener(CLOSE_EVENTS.ready, onReady)
      closeNow()
    }, CLOSE_TIMEOUT_MS)
    const onReady = (e: Electron.IpcMainEvent): void => {
      if (e.sender !== contents) return
      ipcMain.removeListener(CLOSE_EVENTS.ready, onReady)
      clearTimeout(timer)
      closeNow()
    }
    ipcMain.on(CLOSE_EVENTS.ready, onReady)
    contents.send(CLOSE_EVENTS.request)
  })
}

function createWindow(): void {
  const state = initialWindowState()
  const win = new BrowserWindow({
    ...state.bounds,
    minWidth: MIN_WIDTH,
    minHeight: MIN_HEIGHT,
    show: false,
    title: 'Reco-Do',
    backgroundColor: '#F4F6F9',
    // Packaged builds take the icon from the .exe itself.
    ...(app.isPackaged ? {} : { icon: join(__dirname, '../../build/icon.png') }),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webviewTag: false
    }
  })

  win.setMenu(null)
  holdCloseUntilSaved(win)
  trackWindowState(win)
  win.once('ready-to-show', () => {
    if (state.maximized) win.maximize()
    win.show()
  })

  // Links to external sites open in the user's browser; the app itself never navigates away.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://')) void shell.openExternal(url)
    return { action: 'deny' }
  })
  win.webContents.on('will-navigate', (event, url) => {
    if (!isAppUrl(url)) event.preventDefault()
  })

  if (devServerUrl) {
    void win.loadURL(devServerUrl)
  } else {
    void win.loadURL(`${APP_ORIGIN}/index.html`)
  }
}

if (!app.requestSingleInstanceLock()) {
  app.quit()
} else {
  app.on('second-instance', () => {
    const [win] = BrowserWindow.getAllWindows()
    if (win) {
      if (win.isMinimized()) win.restore()
      win.focus()
    }
  })

  // No page may embed a <webview>.
  app.on('web-contents-created', (_event, contents) => {
    contents.on('will-attach-webview', (event) => event.preventDefault())
  })

  void app.whenReady().then(() => {
    app.setAppUserModelId('com.recodo.app')
    // No page in the app may ask for camera, microphone, location, notifications and so on.
    session.defaultSession.setPermissionRequestHandler((_wc, _permission, callback) => callback(false))
    // The app window never talks to the network (the CSP says so too); only app files, blob:/data: and DevTools load.
    session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
      callback({ cancel: !isAllowedAppRequest(details.url, devServerUrl) })
    })
    void cleanStalePrintFiles()
    registerAppProtocol(protocol, rendererRoot)
    registerIpc(isAppUrl)
    createWindow()
    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow()
    })
  })
  app.on('window-all-closed', () => app.quit())
}

