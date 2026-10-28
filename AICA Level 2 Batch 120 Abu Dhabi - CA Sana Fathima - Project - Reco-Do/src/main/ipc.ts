// Registers one handler per bridge method. Each handler checks who is calling and validates its input.

import { app, BrowserWindow, ipcMain, shell, type IpcMainInvokeEvent } from 'electron'
import { IPC, type IpcEnvelope } from '../preload/channels'
import { cancelAi, completeAi } from './ai'
import { openFiles, saveFile } from './files'
import { htmlToPdf } from './pdf'
import { listSamples, readSample } from './samples'
import { forgetApiKey, keyStatus, saveApiKey, saveCustomBaseUrl } from './secrets'
import { aiProviderArg, aiRequest, aiRequestId, apiKeyRequest, asRecord, customBaseUrl, binaryData, fileFilters, optionalBoolean, optionalString, pdfRequest, safeFileName } from './validate'

type Handler = (event: IpcMainInvokeEvent, ...args: unknown[]) => unknown

/** Only the app's own page may call the bridge (not the hidden PDF window or anything else). */
function isTrustedSender(event: IpcMainInvokeEvent, isTrustedUrl: (url: string) => boolean): boolean {
  const url = event.senderFrame?.url
  return typeof url === 'string' && isTrustedUrl(url)
}

function windowOf(event: IpcMainInvokeEvent): BrowserWindow | null {
  return BrowserWindow.fromWebContents(event.sender)
}

const UNEXPECTED = 'Something went wrong. Please try again.'

export function registerIpc(isTrustedUrl: (url: string) => boolean): void {
  // Results travel in an envelope so expected, plain-English failures (validation, file errors) reach the UI
  // as messages instead of being thrown across IPC (which Electron also logs as handler crashes).
  const handle = (channel: string, handler: Handler): void => {
    ipcMain.handle(channel, async (event, ...args): Promise<IpcEnvelope> => {
      if (!isTrustedSender(event, isTrustedUrl)) return { ok: false, error: 'This request is not allowed.' }
      try {
        return { ok: true, value: await handler(event, ...args) }
      } catch (err) {
        return { ok: false, error: err instanceof Error && err.message ? err.message : UNEXPECTED }
      }
    })
  }

  handle(IPC.appInfo, () => ({ version: __RECODO_VERSION__, dataPath: app.getPath('userData') }))
  // Takes no arguments: the folder is always this user's data folder, never a path chosen by the page.
  handle(IPC.openDataFolder, async () => {
    const problem = await shell.openPath(app.getPath('userData'))
    if (problem) throw new Error('The data folder could not be opened.')
  })

  handle(IPC.filesOpen, (event, raw) => {
    const r = asRecord(raw ?? {}, 'open file')
    return openFiles(windowOf(event), {
      title: optionalString(r.title, 'title', 200),
      filters: fileFilters(r.filters),
      multiple: optionalBoolean(r.multiple, 'multiple')
    })
  })

  handle(IPC.filesSave, (event, raw) => {
    const r = asRecord(raw, 'save file')
    return saveFile(windowOf(event), { defaultName: safeFileName(r.defaultName), filters: fileFilters(r.filters), data: binaryData(r.data) })
  })

  handle(IPC.samplesList, () => listSamples())
  handle(IPC.samplesRead, (_event, path) => readSample(path))

  handle(IPC.pdfFromHtml, (event, raw) => htmlToPdf(windowOf(event), pdfRequest(raw)))

  handle(IPC.secretsStatus, () => keyStatus())
  handle(IPC.secretsSet, async (_event, raw) => {
    const { provider, key, warning } = apiKeyRequest(raw)
    await saveApiKey(provider, key)
    return { warning }
  })
  handle(IPC.secretsForget, (_event, raw) => forgetApiKey(aiProviderArg(raw)))

  handle(IPC.aiComplete, (_event, raw) => completeAi(aiRequest(raw)))
  handle(IPC.aiCancel, (_event, raw) => cancelAi(aiRequestId(raw)))
  handle(IPC.aiSetCustomBaseUrl, async (_event, raw) => {
    const url = customBaseUrl(raw)
    await saveCustomBaseUrl(url)
    return url
  })
}
